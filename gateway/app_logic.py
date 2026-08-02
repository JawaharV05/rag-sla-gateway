import time
import asyncio
import uuid
import httpx

from database import get_client_by_api_key, log_request, log_audit_entry
from circuit_breaker import can_attempt_call, record_success, record_failure
from guardrails import check_prompt_injection, detect_pii, redact_pii, check_rate_limit, check_grounding
from metrics import REQUEST_LATENCY, REQUESTS_TOTAL, SLA_COMPLIANCE, DEGRADED_TOTAL, BREAKER_STATE

RAG_CORE_URL = "http://127.0.0.1:8000"
MIN_TIME_FOR_GENERATION_MS = 800


async def call_retrieve(question: str, top_k: int):
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        response = await http_client.post(
            f"{RAG_CORE_URL}/retrieve",
            json={"question": question, "top_k": top_k}
        )
        return response.json()["chunks"]


async def call_generate(question: str, chunks: list):
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        response = await http_client.post(
            f"{RAG_CORE_URL}/generate",
            json={"question": question, "chunks": chunks}
        )
        response.raise_for_status()
        return response.json()["answer"]


def degrade(chunks: list):
    if not chunks:
        return "No relevant information found."
    return chunks[0]["content"]


async def process_request(client_id: str, question: str, top_k: int):
    """
    The full processing pipeline: guardrails, SLA timing, circuit breaker, retrieval, generation.
    This is called by the queue worker, not directly by the API endpoint.
    """
    request_id = str(uuid.uuid4())

    # --- INPUT GUARDRAILS ---

    # 1. Rate limiting
    rate_result = check_rate_limit(client_id)
    if not rate_result["allowed"]:
        log_audit_entry(request_id, client_id, question, outcome="blocked_rate_limit", blocked_by="rate_limit")
        REQUESTS_TOTAL.labels(client_id=client_id, outcome="blocked_rate_limit").inc()
        return {
            "error": "Rate limit exceeded",
            "_meta": {"client_id": client_id, "blocked_by": "rate_limit", "current_count": rate_result["current_count"]}
        }

    # 2. Prompt injection detection
    if check_prompt_injection(question):
        log_audit_entry(request_id, client_id, question, outcome="blocked_injection", blocked_by="injection_check")
        REQUESTS_TOTAL.labels(client_id=client_id, outcome="blocked_injection").inc()
        return {
            "error": "Request blocked: potential prompt injection detected",
            "_meta": {"client_id": client_id, "blocked_by": "injection_check"}
        }

    # 3. PII detection — we don't block, but we redact before using/logging the question
    pii_result = detect_pii(question)
    if pii_result["has_pii"]:
        question = redact_pii(question)

    # --- EXISTING PIPELINE: retrieve client details ---
    from database import get_db_session
    from sqlalchemy import text

    db = get_db_session()
    row = db.execute(
        text("SELECT max_latency_ms, degradation_strategy FROM clients WHERE client_id = :cid"),
        {"cid": client_id}
    ).fetchone()
    db.close()

    if not row:
        log_audit_entry(request_id, client_id, question, outcome="error", blocked_by="unknown_client")
        return {"error": "Unknown client"}

    budget_ms = row.max_latency_ms
    strategy = row.degradation_strategy
    start_time = time.time()

    chunks = await call_retrieve(question, top_k)

    elapsed_ms = int((time.time() - start_time) * 1000)
    remaining_ms = budget_ms - elapsed_ms

    breaker_blocked = False
    degraded = False

    if strategy == "full_answer_always":
        if not can_attempt_call():
            answer_text, degraded, breaker_blocked = degrade(chunks), True, True
        else:
            try:
                answer_text = await call_generate(question, chunks)
                record_success()
            except Exception:
                record_failure()
                answer_text, degraded = degrade(chunks), True

    elif remaining_ms < MIN_TIME_FOR_GENERATION_MS:
        answer_text, degraded = degrade(chunks), True

    else:
        if not can_attempt_call():
            answer_text, degraded, breaker_blocked = degrade(chunks), True, True
        else:
            try:
                answer_text = await asyncio.wait_for(
                    call_generate(question, chunks),
                    timeout=remaining_ms / 1000
                )
                record_success()
            except asyncio.TimeoutError:
                record_failure()
                answer_text, degraded = degrade(chunks), True
            except Exception:
                record_failure()
                answer_text, degraded = degrade(chunks), True

    # --- OUTPUT GUARDRAIL: Grounding Verification ---
    grounding_result = check_grounding(answer_text, chunks)

    total_elapsed_ms = int((time.time() - start_time) * 1000)
    within_sla = total_elapsed_ms <= budget_ms
    log_request(client_id, total_elapsed_ms, within_sla)

    # --- METRICS ---
    REQUEST_LATENCY.labels(client_id=client_id).observe(total_elapsed_ms)
    REQUESTS_TOTAL.labels(client_id=client_id, outcome="answered").inc()
    SLA_COMPLIANCE.labels(client_id=client_id, within_sla=str(within_sla)).inc()
    if degraded:
        DEGRADED_TOTAL.labels(client_id=client_id).inc()

    log_audit_entry(
        request_id, client_id, question,
        outcome="answered",
        degraded=degraded,
        breaker_blocked=breaker_blocked,
        grounded=grounding_result["grounded"],
        pii_redacted=pii_result["has_pii"],
        latency_ms=total_elapsed_ms,
        within_sla=within_sla,
    )

    return {
        "answer": answer_text,
        "sources": chunks,
        "_meta": {
            "client_id": client_id,
            "latency_ms": total_elapsed_ms,
            "within_sla": within_sla,
            "max_latency_ms": budget_ms,
            "degraded": degraded,
            "breaker_blocked": breaker_blocked,
            "grounded": grounding_result["grounded"],
            "grounding_overlap_ratio": grounding_result["overlap_ratio"],
            "pii_redacted": pii_result["has_pii"]
        }
    }