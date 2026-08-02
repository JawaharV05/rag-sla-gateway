import pytest
import fakeredis
import priority_queue


@pytest.fixture(autouse=True)
def fresh_queue(monkeypatch):
    fake_r = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(priority_queue, "r", fake_r)
    yield


def test_empty_queue_returns_none():
    assert priority_queue.dequeue_next() is None


def test_single_item_roundtrip():
    priority_queue.enqueue_request("admin_tool", {"question": "test question"})
    item = priority_queue.dequeue_next()
    assert item is not None
    assert item["payload"]["question"] == "test question"


def test_higher_priority_dequeued_first():
    priority_queue.enqueue_request("mobile_app", {"question": "mobile-1"})
    priority_queue.enqueue_request("mobile_app", {"question": "mobile-2"})
    priority_queue.enqueue_request("admin_tool", {"question": "admin-1"})

    first = priority_queue.dequeue_next()
    assert first["payload"]["question"] == "admin-1"


def test_same_priority_preserves_insertion_order():
    priority_queue.enqueue_request("mobile_app", {"question": "mobile-1"})
    priority_queue.enqueue_request("mobile_app", {"question": "mobile-2"})

    first = priority_queue.dequeue_next()
    second = priority_queue.dequeue_next()
    assert first["payload"]["question"] == "mobile-1"
    assert second["payload"]["question"] == "mobile-2"


def test_queue_length_tracks_correctly():
    assert priority_queue.queue_length() == 0
    priority_queue.enqueue_request("web_widget", {"question": "q1"})
    priority_queue.enqueue_request("web_widget", {"question": "q2"})
    assert priority_queue.queue_length() == 2
    priority_queue.dequeue_next()
    assert priority_queue.queue_length() == 1


def test_unknown_client_gets_lowest_priority():
    priority_queue.enqueue_request("admin_tool", {"question": "admin-1"})
    priority_queue.enqueue_request("mystery_client", {"question": "mystery-1"})

    first = priority_queue.dequeue_next()
    assert first["payload"]["question"] == "admin-1"