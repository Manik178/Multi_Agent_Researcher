# Remove this:
from graph_component.graph.graph import research_graph

# Add this:
import importlib.util, sys, os

def _load_graph():
    base = os.path.join(os.path.dirname(__file__), '..', 'graph_component')
    sys.path.insert(0, os.path.abspath(base))
    from graph_component.graph.graph import research_graph
    return research_graph

research_graph = _load_graph()

import json
import asyncio
# pyrefly: ignore [missing-import]
from fastapi import APIRouter
# pyrefly: ignore [missing-import]
from fastapi.responses import StreamingResponse
# pyrefly: ignore [missing-import]
from sse_starlette.sse import EventSourceResponse
from .schemas import ResearchRequest
# pyrefly: ignore [missing-import]
# from graph.graph import research_graph

router = APIRouter()


import uuid

# ── POST endpoint ─────────────────────────────────────────────
@router.post("/research", response_model=None)
async def research(request: ResearchRequest):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = await asyncio.to_thread(
        research_graph.invoke,
        {"question": request.question},
        config
    )

    verified = result.get("verified_claims", [])
    total_claims = len(verified)
    verified_count = sum(1 for c in verified if c.get("verified"))
    cache_hits = result.get("cache_hits", 0)
    qdrant_hits = result.get("qdrant_hits", 0)
    total_sources = result.get("total_sources", 0)
    total_retrievals = cache_hits + qdrant_hits + total_sources

    dashboard = {
        "critic_confidence": result.get("critic_confidence", 0.0),
        "citation_score": round(verified_count / total_claims, 2) if total_claims > 0 else 0,
        "verified_claims": verified_count,
        "total_claims": total_claims,
        "cache_hits": cache_hits,
        "qdrant_hits": qdrant_hits,
        "web_searches": total_sources,
        "iterations_needed": result.get("iteration", 1),
        "retrieval_efficiency": round(
            (cache_hits + qdrant_hits) / total_retrievals, 2
        ) if total_retrievals > 0 else 0
    }

    return {
        "thread_id": thread_id,
        "question": request.question,
        "sub_questions": result["sub_questions"],
        "iterations": result["iteration"],
        "critic_verdict": result["critic_verdict"],
        "final_answer": result["final_answer"],
        "verified_claims": verified,
        "follow_up_questions": result.get("follow_up_questions", []),
        "dashboard": dashboard
    }

# ── SSE streaming endpoint ────────────────────────────────────
@router.get("/research/stream")
async def research_stream(question: str, thread_id: str = None):
    if not thread_id:
        thread_id = str(uuid.uuid4())

    config = {"configurable": {"thread_id": thread_id}}

    async def event_generator():
        import asyncio
        import threading
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def producer():
            try:
                for event in research_graph.stream(
                    {"question": question},
                    config=config,
                    stream_mode="updates"
                ):
                    loop.call_soon_threadsafe(queue.put_nowait, event)
                loop.call_soon_threadsafe(queue.put_nowait, None)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, e)

        threading.Thread(target=producer, daemon=True).start()

        while True:
            event = await queue.get()
            if event is None:
                break
            if isinstance(event, Exception):
                break

            node_name = list(event.keys())[0]
            node_output = event[node_name]

            status_map = {
                "planner":    "Planning sub-questions...",
                "researcher": "Researching...",
                "critic":     "Reviewing research quality...",
                "writer":     "Writing final answer..."
            }

            payload = {
                "type": "node_update",
                "node": node_name,
                "status": status_map.get(node_name, "Processing..."),
                "data": node_output,
                "thread_id": thread_id
            }

            yield {"event": "message", "data": json.dumps(payload)}

        yield {"event": "done", "data": json.dumps({"type": "done", "thread_id": thread_id})}

    return EventSourceResponse(event_generator())

@router.get("/health")
async def health():
    return {"status": "ok"}

import shutil
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'graph_component'))

from fastapi import UploadFile, File, HTTPException
from ingestion import ingest_document
from vector_store import list_uploaded_documents, delete_document

UPLOAD_DIR = "/tmp/research_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and ingest a PDF or text document."""
    allowed = [".pdf", ".txt", ".md"]
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {allowed}"
        )

    # Save file temporarily
    temp_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Ingest
    try:
        chunks_stored = await asyncio.to_thread(
            ingest_document, temp_path, file.filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.remove(temp_path)  # clean up temp file

    return {
        "filename": file.filename,
        "chunks_stored": chunks_stored,
        "status": "ingested"
    }


@router.get("/documents")
async def get_documents():
    """List all uploaded documents."""
    sources = await asyncio.to_thread(list_uploaded_documents)
    return {"documents": sources}


@router.delete("/documents/{filename}")
async def remove_document(filename: str):
    """Delete a document from the private collection."""
    await asyncio.to_thread(delete_document, filename)
    return {"filename": filename, "status": "deleted"}

# ── Confidence dashboard endpoint ─────────────────────────────
@router.get("/sessions/{thread_id}")
async def get_session(thread_id: str):
    """Fetch a past research session by thread_id."""
    config = {"configurable": {"thread_id": thread_id}}

    try:
        state = await asyncio.to_thread(
            research_graph.get_state,
            config
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")

    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Session not found")

    values = state.values

    # ── Build confidence dashboard ────────────────────────────
    verified = values.get("verified_claims", [])
    total_claims = len(verified)
    verified_count = sum(1 for c in verified if c.get("verified"))
    citation_score = (verified_count / total_claims) if total_claims > 0 else 0

    cache_hits = values.get("cache_hits", 0)
    qdrant_hits = values.get("qdrant_hits", 0)
    total_sources = values.get("total_sources", 0)
    total_retrievals = cache_hits + qdrant_hits + total_sources

    dashboard = {
        "critic_confidence": values.get("critic_confidence", 0.0),
        "citation_score": round(citation_score, 2),
        "verified_claims": verified_count,
        "total_claims": total_claims,
        "cache_hits": cache_hits,
        "qdrant_hits": qdrant_hits,
        "web_searches": total_sources,
        "total_retrievals": total_retrievals,
        "iterations_needed": values.get("iteration", 1),
        "retrieval_efficiency": round(
            (cache_hits + qdrant_hits) / total_retrievals, 2
        ) if total_retrievals > 0 else 0
    }

    return {
        "thread_id": thread_id,
        "question": values.get("question", ""),
        "final_answer": values.get("final_answer", ""),
        "follow_up_questions": values.get("follow_up_questions", []),
        "verified_claims": verified,
        "dashboard": dashboard
    }