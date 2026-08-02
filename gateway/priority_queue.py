import redis
import json
import uuid

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

QUEUE_KEY = "gateway:priority_queue"

PRIORITY_MAP = {
    "admin_tool": 1,
    "web_widget": 2,
    "mobile_app": 3,
}


def enqueue_request(client_id: str, payload: dict) -> str:
    """
    Adds a request to the priority queue.
    Returns a unique request_id that can be used to look it up later.
    """
    request_id = str(uuid.uuid4())
    priority = PRIORITY_MAP.get(client_id, 99)  # unknown clients get lowest priority

    # Store the actual request data separately, keyed by its ID
    r.set(f"gateway:request_data:{request_id}", json.dumps(payload))

    # A strictly increasing counter, so same-priority items are ordered by
    # arrival time, not by their random request_id's alphabetical value.
    sequence = r.incr("gateway:priority_queue:counter")

    # Combine priority and sequence into one score: priority dominates,
    # but within the same priority, lower sequence (earlier arrival) sorts first.
    score = (priority * 1_000_000_000) + sequence
    r.zadd(QUEUE_KEY, {request_id: score})

    return request_id


def dequeue_next():
    """
    Removes and returns the highest-priority (lowest score) request from the queue.
    Returns None if the queue is empty.
    """
    result = r.zpopmin(QUEUE_KEY, count=1)
    if not result:
        return None

    request_id, priority = result[0]
    data_raw = r.get(f"gateway:request_data:{request_id}")
    r.delete(f"gateway:request_data:{request_id}")

    if data_raw:
        return {"request_id": request_id, "priority": priority, "payload": json.loads(data_raw)}
    return None


def queue_length():
    return r.zcard(QUEUE_KEY)


if __name__ == "__main__":
    # Quick manual test: enqueue out of priority order, confirm dequeue comes out correctly sorted
    print("Enqueueing requests in this order: mobile_app, mobile_app, admin_tool, web_widget, mobile_app")

    enqueue_request("mobile_app", {"question": "mobile request 1"})
    enqueue_request("mobile_app", {"question": "mobile request 2"})
    enqueue_request("admin_tool", {"question": "admin request 1"})
    enqueue_request("web_widget", {"question": "web request 1"})
    enqueue_request("mobile_app", {"question": "mobile request 3"})

    print(f"Queue length: {queue_length()}\n")

    print("Dequeuing in priority order:")
    while queue_length() > 0:
        item = dequeue_next()
        print(f"  Priority {item['priority']}: {item['payload']['question']}")