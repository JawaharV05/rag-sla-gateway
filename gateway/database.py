from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://raguser:ragpassword@localhost:5432/ragdb"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db_session():
    return SessionLocal()

def setup_gateway_tables():
    """Creates the clients table and requests_log table if they don't exist yet."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS clients (
                client_id TEXT PRIMARY KEY,
                api_key TEXT UNIQUE NOT NULL,
                max_latency_ms INTEGER NOT NULL,
                degradation_strategy TEXT NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS requests_log (
                id SERIAL PRIMARY KEY,
                client_id TEXT NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT now(),
                latency_ms INTEGER,
                within_sla BOOLEAN
            );
        """))
        conn.commit()
    print("Gateway tables ready.")
def setup_audit_table():
    """Creates the permanent audit_log table if it doesn't already exist."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                request_id UUID NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT now(),
                client_id TEXT,
                question TEXT,
                outcome TEXT,
                blocked_by TEXT,
                degraded BOOLEAN,
                breaker_blocked BOOLEAN,
                grounded BOOLEAN,
                pii_redacted BOOLEAN,
                latency_ms INTEGER,
                within_sla BOOLEAN
            );
        """))
        conn.commit()
    print("Audit log table ready.")


def log_audit_entry(
    request_id: str,
    client_id: str,
    question: str,
    outcome: str,
    blocked_by: str = None,
    degraded: bool = None,
    breaker_blocked: bool = None,
    grounded: bool = None,
    pii_redacted: bool = None,
    latency_ms: int = None,
    within_sla: bool = None,
):
    """
    Writes one permanent, append-only entry to the audit log.
    This function NEVER updates or deletes existing rows — only ever inserts new ones.
    """
    db = get_db_session()
    db.execute(
        text("""
            INSERT INTO audit_log
                (request_id, client_id, question, outcome, blocked_by,
                 degraded, breaker_blocked, grounded, pii_redacted, latency_ms, within_sla)
            VALUES
                (:request_id, :client_id, :question, :outcome, :blocked_by,
                 :degraded, :breaker_blocked, :grounded, :pii_redacted, :latency_ms, :within_sla)
        """),
        {
            "request_id": request_id,
            "client_id": client_id,
            "question": question,
            "outcome": outcome,
            "blocked_by": blocked_by,
            "degraded": degraded,
            "breaker_blocked": breaker_blocked,
            "grounded": grounded,
            "pii_redacted": pii_redacted,
            "latency_ms": latency_ms,
            "within_sla": within_sla,
        }
    )
    db.commit()
    db.close()

def seed_clients():
    """Insert our 3 test clients if they don't already exist."""
    db = get_db_session()
    clients = [
        {"client_id": "mobile_app", "api_key": "mobile-key-123", "max_latency_ms": 1000, "degradation_strategy": "return_snippet_only"},
        {"client_id": "web_widget", "api_key": "web-key-456", "max_latency_ms": 3000, "degradation_strategy": "shorter_generation"},
        {"client_id": "admin_tool", "api_key": "admin-key-789", "max_latency_ms": 5000, "degradation_strategy": "full_answer_always"},
    ]
    for c in clients:
        db.execute(
            text("""
                INSERT INTO clients (client_id, api_key, max_latency_ms, degradation_strategy)
                VALUES (:client_id, :api_key, :max_latency_ms, :degradation_strategy)
                ON CONFLICT (client_id) DO NOTHING
            """),
            c
        )
    db.commit()
    db.close()
    print("Clients seeded.")

def get_client_by_api_key(api_key: str):
    db = get_db_session()
    result = db.execute(
        text("SELECT client_id, max_latency_ms, degradation_strategy FROM clients WHERE api_key = :api_key"),
        {"api_key": api_key}
    ).fetchone()
    db.close()
    if result:
        return {"client_id": result.client_id, "max_latency_ms": result.max_latency_ms, "degradation_strategy": result.degradation_strategy}
    return None

def log_request(client_id: str, latency_ms: int, within_sla: bool):
    db = get_db_session()
    db.execute(
        text("""
            INSERT INTO requests_log (client_id, latency_ms, within_sla)
            VALUES (:client_id, :latency_ms, :within_sla)
        """),
        {"client_id": client_id, "latency_ms": latency_ms, "within_sla": within_sla}
    )
    db.commit()
    db.close()

if __name__ == "__main__":
    setup_gateway_tables()
    seed_clients()
    setup_audit_table()