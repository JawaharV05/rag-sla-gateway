import pytest
import fakeredis
import circuit_breaker


@pytest.fixture(autouse=True)
def fresh_breaker(monkeypatch):
    """
    Before every test, replace the real Redis connection with a fake,
    in-memory one, so tests don't depend on Docker/Redis actually running,
    and each test starts with a clean, empty state.
    """
    fake_r = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(circuit_breaker, "r", fake_r)
    yield


def test_starts_closed():
    assert circuit_breaker.get_breaker_state() == "CLOSED"


def test_stays_closed_under_threshold():
    for _ in range(4):
        circuit_breaker.record_failure()
    assert circuit_breaker.get_breaker_state() == "CLOSED"
    assert circuit_breaker.can_attempt_call() is True


def test_trips_open_at_threshold():
    for _ in range(5):
        circuit_breaker.record_failure()
    assert circuit_breaker.get_breaker_state() == "OPEN"
    assert circuit_breaker.can_attempt_call() is False


def test_success_resets_to_closed():
    for _ in range(5):
        circuit_breaker.record_failure()
    assert circuit_breaker.get_breaker_state() == "OPEN"

    circuit_breaker.record_success()
    assert circuit_breaker.get_breaker_state() == "CLOSED"
    assert circuit_breaker.can_attempt_call() is True