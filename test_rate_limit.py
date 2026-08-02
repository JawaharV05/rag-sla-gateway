import asyncio
import httpx

GATEWAY_URL = "http://127.0.0.1:8001/gateway/answer"
API_KEY = "mobile-key-123"


async def send_one(i: int):
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        response = await http_client.post(
            GATEWAY_URL,
            headers={"x-api-key": API_KEY},
            json={"question": "how do I reset my password?", "top_k": 3}
        )
        data = response.json()
        blocked = data.get("_meta", {}).get("blocked_by")
        print(f"Request {i}: {'BLOCKED (' + blocked + ')' if blocked else 'allowed'}")


async def main():
    for i in range(1, 14):
        await send_one(i)


if __name__ == "__main__":
    asyncio.run(main())