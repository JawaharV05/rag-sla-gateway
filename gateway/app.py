import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from prometheus_client import make_asgi_app

from database import get_client_by_api_key
from queue_worker import worker_loop, submit_and_wait


@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs once, when the server starts up
    worker_task = asyncio.create_task(worker_loop())
    yield
    # This runs when the server shuts down (cleanup)
    worker_task.cancel()


app = FastAPI(title="RAG SLA Gateway", lifespan=lifespan)


@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


class QuestionRequest(BaseModel):
    question: str
    top_k: int = 5


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/gateway/answer")
async def gateway_answer(request: QuestionRequest, x_api_key: str = Header(...)):
    client = get_client_by_api_key(x_api_key)
    if not client:
        raise HTTPException(status_code=401, detail="Invalid API key")

    result = await submit_and_wait(
        client["client_id"], request.question, request.top_k
    )
    return result