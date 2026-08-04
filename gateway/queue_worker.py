import asyncio
import time
import redis
import json

from priority_queue import enqueue_request, dequeue_next, queue_length
from database import get_client_by_api_key, log_request
from app_logic import process_request  # we'll create this next

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

RESULT_KEY_PREFIX = "gateway:result:"
RESULT_TTL_SECONDS = 30  # results expire after 30s if never picked up


async def worker_loop():
    """Continuously processes the highest-priority item in the queue."""
    print("Queue worker started, watching for requests...")
    while True:
        item = dequeue_next()
        if item is None:
            await asyncio.sleep(0.05)  # nothing to do, check again shortly
            continue

        request_id = item["request_id"]
        payload = item["payload"]

        try:
            result = await process_request(payload["client_id"], payload["question"], payload["top_k"])
        except Exception as e:
            result = {"error": str(e)}

        r.setex(f"{RESULT_KEY_PREFIX}{request_id}", RESULT_TTL_SECONDS, json.dumps(result))


async def submit_and_wait(client_id: str, question: str, top_k: int, max_wait_seconds: float = 30.0):
    """
    Enqueues a request and waits for the worker to produce a result.
    """
    request_id = enqueue_request(client_id, {"client_id": client_id, "question": question, "top_k": top_k})

    start = time.time()
    while time.time() - start < max_wait_seconds:
        result_raw = r.get(f"{RESULT_KEY_PREFIX}{request_id}")
        if result_raw:
            r.delete(f"{RESULT_KEY_PREFIX}{request_id}")
            return json.loads(result_raw)
        await asyncio.sleep(0.02)  # check every 20ms

    return {"error": "Timed out waiting for queue processing"}