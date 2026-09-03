from fastapi import FastAPI, Request, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
import time
import asyncio
import json
import os
import tempfile

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from sse_starlette.sse import EventSourceResponse

from pipeline import answer_question, answer_question_stream

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

ACCEPTED_EXTENSIONS = {".pdf", ".txt", ".csv"}

_doc_state: dict = {"status": "none", "filename": None, "error": None, "chunk_count": 0}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _doc_state
    try:
        from vector_storage import get_stats
        stats = await asyncio.to_thread(get_stats)
        if stats.get("total_vectors", 0) > 0:
            filename = "Uploaded document"
            chunk_count = 0
            chunks_path = os.path.join(BACKEND_DIR, "chunks.jsonl")
            if os.path.exists(chunks_path):
                with open(chunks_path, "r") as f:
                    lines = f.readlines()
                    chunk_count = len(lines)
                    if lines:
                        chunk = json.loads(lines[0].strip())
                        filename = chunk.get("source", filename)
            _doc_state = {"status": "ready", "filename": filename, "error": None, "chunk_count": chunk_count}
            print(f"Startup: restored '{filename}' ({stats['total_vectors']} vectors, {chunk_count} chunks).")
        else:
            print("Startup: no vectors found — waiting for upload.")
    except Exception as exc:
        print(f"Startup check failed (non-fatal): {exc}")
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="AnswerDoc API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_extra = os.getenv("ALLOWED_ORIGINS", "")
FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    *[o.strip() for o in _extra.split(",") if o.strip()],
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


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
@limiter.limit("30/minute")
async def query(request: Request, body: QueryRequest):
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    start_time = time.time()

    try:
        result = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(
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


async def sse_event_generator(question: str):
    try:
        async for chunk in answer_question_stream(question):
            if chunk["type"] == "token":
                yield {"event": "token", "data": chunk["content"]}
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
            "data": json.dumps({"message": "Something went wrong while generating the answer."})
        }


@app.post("/query/stream")
@limiter.limit("30/minute")
async def query_stream(request: Request, body: QueryRequest):
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    return EventSourceResponse(sse_event_generator(body.question))


def _run_pipeline(pdf_path: str, filename: str, file_ext: str) -> None:
    global _doc_state
    try:
        for cache in ["parsed_pages.jsonl", "chunks.jsonl"]:
            p = os.path.join(BACKEND_DIR, cache)
            if os.path.exists(p):
                os.remove(p)

        from parsing import parse_file
        from chunking import chunk_pages
        from vector_storage import delete_all
        from embedding import embed_and_store

        pages = parse_file(pdf_path, file_ext)
        chunks = chunk_pages(pages, source_name=filename)
        chunks_dicts = [c.model_dump() for c in chunks]

        delete_all()
        embed_and_store(chunks_dicts)

        _doc_state = {
            "status": "ready",
            "filename": filename,
            "error": None,
            "chunk_count": len(chunks_dicts)
        }
    except Exception as exc:
        print(f"Upload pipeline error: {exc}")
        _doc_state = {"status": "error", "filename": filename, "error": str(exc), "chunk_count": 0}
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    global _doc_state

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ACCEPTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Accepted: {', '.join(ACCEPTED_EXTENSIONS)}"
        )

    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=ext, dir=BACKEND_DIR, prefix="upload_"
    )
    try:
        tmp.write(await file.read())
    finally:
        tmp.close()

    _doc_state = {"status": "processing", "filename": file.filename, "error": None, "chunk_count": 0}
    background_tasks.add_task(_run_pipeline, tmp.name, file.filename, ext)
    return _doc_state


@app.get("/doc/status")
def doc_status():
    return _doc_state


def _run_ingest_pipeline(records: list, source_name: str) -> None:
    global _doc_state
    try:
        from parsing import ParsedPage
        from chunking import chunk_pages
        from vector_storage import delete_all
        from embedding import embed_and_store

        pages = []
        for i, rec in enumerate(records):
            img_url = rec.get("metadata", {}).get("image_url") or ""
            pages.append(ParsedPage(
                page_number=i + 1,
                text=rec["text"],
                tables=[],
                images=[img_url] if img_url else [],
                has_image=bool(img_url),
                char_count=len(rec["text"]),
                image_descriptions=[]
            ))

        for cache in ["parsed_pages.jsonl", "chunks.jsonl"]:
            p = os.path.join(BACKEND_DIR, cache)
            if os.path.exists(p):
                os.remove(p)

        chunks = chunk_pages(pages, source_name=source_name)
        chunks_dicts = [c.model_dump() for c in chunks]

        delete_all()
        embed_and_store(chunks_dicts)

        _doc_state = {"status": "ready", "filename": source_name, "error": None, "chunk_count": len(chunks_dicts)}
    except Exception as exc:
        print(f"Ingest pipeline error: {exc}")
        _doc_state = {"status": "error", "filename": source_name, "error": str(exc), "chunk_count": 0}


class IngestUrlRequest(BaseModel):
    url: str



class IngestTextRequest(BaseModel):
    title: str
    content: str


@app.post("/ingest/url")
async def ingest_url(body: IngestUrlRequest, background_tasks: BackgroundTasks):
    global _doc_state
    try:
        from additionalfiles import ingest_source
        records = await asyncio.to_thread(ingest_source, "url", url=body.url)
        source_name = records[0]["metadata"].get("title", body.url) if records else body.url
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _doc_state = {"status": "processing", "filename": source_name, "error": None, "chunk_count": 0}
    background_tasks.add_task(_run_ingest_pipeline, records, source_name)
    return _doc_state



@app.post("/ingest/text")
async def ingest_text(body: IngestTextRequest, background_tasks: BackgroundTasks):
    global _doc_state
    try:
        from additionalfiles import ingest_source
        records = await asyncio.to_thread(ingest_source, "text", title=body.title, content=body.content)
        source_name = body.title or "Pasted Text"
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _doc_state = {"status": "processing", "filename": source_name, "error": None, "chunk_count": 0}
    background_tasks.add_task(_run_ingest_pipeline, records, source_name)
    return _doc_state


@app.delete("/doc/clear")
async def doc_clear():
    global _doc_state
    try:
        from vector_storage import delete_all
        await asyncio.to_thread(delete_all)

        for cache in ["parsed_pages.jsonl", "chunks.jsonl"]:
            p = os.path.join(BACKEND_DIR, cache)
            if os.path.exists(p):
                os.remove(p)

        _doc_state = {"status": "none", "filename": None, "error": None, "chunk_count": 0}
        return {"cleared": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to clear: {exc}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("ENVIRONMENT", "development") == "development"
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
        reload_excludes=["*.jsonl", "upload_*.pdf", "upload_*.txt", "upload_*.csv"],
    )
