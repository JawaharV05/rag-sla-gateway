import httpx
import pytest
import time

GATEWAY_URL = "http://127.0.0.1:8001"
RAG_CORE_URL = "http://127.0.0.1:8000"
ADMIN_KEY = "admin-key-789"


def ask_admin(question="how do I reset my password?"):
    return httpx.post(
        f"{GATEWAY_URL}/gateway/answer",
        headers={"x-api-key": ADMIN_KEY},
        json={"question": question, "top_k": 3},
        timeout=15.0
    )


def set_simulated_failure(enabled: bool):
    httpx.post(f"{RAG_CORE_URL}/test/toggle_failure", params={"enabled": enabled}, timeout=5.0)


def test_system_never_hard_crashes_on_malformed_input():
    response = httpx.post(
        f"{GATEWAY_URL}/gateway/answer",
        headers={"x-api-key": ADMIN_KEY},
        json={"question": "", "top_k": 3},
        timeout=15.0
    )
    assert response.status_code != 500


def test_system_rejects_missing_api_key_gracefully():
    response = httpx.post(
        f"{GATEWAY_URL}/gateway/answer",
        json={"question": "how do I reset my password?", "top_k": 3},
        timeout=15.0
    )
    assert response.status_code in (401, 422)


def test_circuit_breaker_trips_and_recovers_under_real_simulated_outage():
    """
    Turns on a real simulated LLM outage, fires enough requests to trip the
    breaker, confirms it blocks further attempts, then turns the outage off
    and confirms the system recovers after the cooldown.
    """
    set_simulated_failure(True)
    try:
        results = []
        for _ in range(6):
            response = ask_admin()
            assert response.status_code != 500  # never a hard crash, even while "broken"
            results.append(response.json())

        # By the last request, the breaker should have tripped
        last_meta = results[-1]["_meta"]
        assert last_meta["breaker_blocked"] is True
        assert last_meta["degraded"] is True

    finally:
        # Always turn the simulation back off, even if the test fails
        set_simulated_failure(False)

    # Wait for the circuit breaker's cooldown period to pass
    time.sleep(31)

    response = ask_admin()
    data = response.json()
    assert data["_meta"]["breaker_blocked"] is False
    assert data["_meta"]["degraded"] is False