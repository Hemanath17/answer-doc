from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import time
import asyncio
import json

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from sse_starlette.sse import EventSourceResponse

from pipeline import answer_question, answer_question_stream

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="AnswerDoc API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

FRONTEND_ORIGINS = [
    "http://localhost:5173",       # local Vite dev server
    "http://localhost:3000",       # local CRA/Next dev server, if used
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REQUEST_TIMEOUT_SECONDS = 30.0


class QueryRequest(BaseModel):
    question: str


class SourceItem(BaseModel):
    page: int
    preview: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    has_image: bool
    image_url: Optional[str]
    processing_time_ms: int


# ─── Health check endpoint ──────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok"}


# ─── Non-streaming query endpoint ───────────────────────────────────

@app.post("/query", response_model=QueryResponse)
@limiter.limit("10/minute")
async def query(request: Request, body: QueryRequest):
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    start_time = time.time()

    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, answer_question, body.question
            ),
            timeout=REQUEST_TIMEOUT_SECONDS
        )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="The request took too long to process. Please try again."
        )
    except Exception as e:
        print(f"Unexpected error in /query: {e}")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while processing your question."
        )

    elapsed_ms = int((time.time() - start_time) * 1000)

    return QueryResponse(
        answer=result["answer"],
        sources=[SourceItem(**s) for s in result["sources"]],
        has_image=result["has_image"],
        image_url=result["image_url"],
        processing_time_ms=elapsed_ms
    )


# ─── Streaming query endpoint (SSE) ─────────────────────────────────

async def sse_event_generator(question: str):

    try:
        async for chunk in answer_question_stream(question):
            if chunk["type"] == "token":
                yield {
                    "event": "token",
                    "data": chunk["content"]
                }
            elif chunk["type"] == "done":
                yield {
                    "event": "done",
                    "data": json.dumps({
                        "sources": chunk["sources"],
                        "has_image": chunk["has_image"],
                        "image_url": chunk["image_url"]
                    })
                }
    except Exception as e:
        print(f"Unexpected error in stream: {e}")
        yield {
            "event": "error",
            "data": json.dumps({
                "message": "Something went wrong while generating the answer."
            })
        }


@app.post("/query/stream")
@limiter.limit("10/minute")
async def query_stream(request: Request, body: QueryRequest):
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    return EventSourceResponse(sse_event_generator(body.question))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)