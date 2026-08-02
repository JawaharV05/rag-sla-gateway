import os
SIMULATE_FAILURE = os.getenv("SIMULATE_FAILURE") == "true"
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from retrieval import retrieve_chunks
from generation import generate_answer

app = FastAPI(title="RAG Core Service")


class QuestionRequest(BaseModel):
    question: str
    top_k: int = 5


class AnswerResponse(BaseModel):
    answer: str
    sources: list


class RetrieveResponse(BaseModel):
    chunks: list


class GenerateRequest(BaseModel):
    question: str
    chunks: list


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/answer", response_model=AnswerResponse)
def answer(request: QuestionRequest):
    chunks = retrieve_chunks(request.question, top_k=request.top_k)
    generated_answer = generate_answer(request.question, chunks)
    return AnswerResponse(answer=generated_answer, sources=chunks)


@app.post("/retrieve", response_model=RetrieveResponse)
def retrieve(request: QuestionRequest):
    chunks = retrieve_chunks(request.question, top_k=request.top_k)
    return RetrieveResponse(chunks=chunks)


@app.post("/generate", response_model=AnswerResponse)
def generate(request: GenerateRequest):
    global SIMULATE_FAILURE
    if SIMULATE_FAILURE:
        raise HTTPException(status_code=500, detail="Simulated failure for testing")
    generated_answer = generate_answer(request.question, request.chunks)
    return AnswerResponse(answer=generated_answer, sources=request.chunks)


@app.post("/test/toggle_failure")
def toggle_failure(enabled: bool):
    """Testing-only endpoint: flip the simulated failure on/off without restarting the server."""
    global SIMULATE_FAILURE
    SIMULATE_FAILURE = enabled
    return {"simulate_failure": SIMULATE_FAILURE}