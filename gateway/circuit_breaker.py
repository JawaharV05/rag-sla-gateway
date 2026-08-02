import time
import redis
from metrics import BREAKER_STATE

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

FAILURE_THRESHOLD = 5      # trip the breaker after this many failures
COOLDOWN_SECONDS = 30      # how long to stay OPEN before testing again


def get_breaker_state():
    state = r.get("breaker:state")
    return state if state else "CLOSED"


def record_success():
    """Call this whenever a Gemini call succeeds."""
    r.set("breaker:failure_count", 0)
    r.set("breaker:state", "CLOSED")
    BREAKER_STATE.set(0)


def record_failure():
    """Call this whenever a Gemini call fails."""
    count = r.incr("breaker:failure_count")
    if count >= FAILURE_THRESHOLD:
        r.set("breaker:state", "OPEN")
        r.set("breaker:opened_at", time.time())
        BREAKER_STATE.set(2)


def can_attempt_call():
    """
    Returns True if we should attempt calling Gemini right now.
    Returns False if the breaker is OPEN and we should skip straight to fallback.
    """
    state = get_breaker_state()

    if state == "CLOSED":
        return True

    if state == "OPEN":
        opened_at = float(r.get("breaker:opened_at") or 0)
        if time.time() - opened_at > COOLDOWN_SECONDS:
            r.set("breaker:state", "HALF_OPEN")
            BREAKER_STATE.set(1)
            return True  # allow exactly one test call through
        return False

    if state == "HALF_OPEN":
        return True  # already testing, allow it

    return True


if __name__ == "__main__":
    # Quick manual test
    print("Initial state:", get_breaker_state())
    for i in range(6):
        record_failure()
        print(f"After failure {i+1}: state = {get_breaker_state()}, can_attempt = {can_attempt_call()}")