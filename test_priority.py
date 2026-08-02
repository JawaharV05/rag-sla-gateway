import asyncio
import httpx
import time

GATEWAY_URL = "http://127.0.0.1:8001/gateway/answer"

CLIENTS = {
    "mobile_app": "mobile-key-123",
    "web_widget": "web-key-456",
    "admin_tool": "admin-key-789",
}


async def send_request(client_name: str, api_key: str, label: str):
    start = time.time()
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        response = await http_client.post(
            GATEWAY_URL,
            headers={"x-api-key": api_key},
            json={"question": "how do I reset my password?", "top_k": 3}
        )
    elapsed = time.time() - start
    print(f"[{elapsed:.2f}s] {label} ({client_name}) finished")


async def main():
    # Fire a burst: several mobile requests, then admin, then web — all at nearly the same instant
    tasks = [
        send_request("mobile_app", CLIENTS["mobile_app"], "mobile-1"),
        send_request("mobile_app", CLIENTS["mobile_app"], "mobile-2"),
        send_request("mobile_app", CLIENTS["mobile_app"], "mobile-3"),
        send_request("admin_tool", CLIENTS["admin_tool"], "admin-1"),
        send_request("web_widget", CLIENTS["web_widget"], "web-1"),
        send_request("mobile_app", CLIENTS["mobile_app"], "mobile-4"),
    ]
    print("Firing 6 requests simultaneously...\n")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())