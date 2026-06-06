import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'graph_component'))

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
from graph.graph import research_graph

router = APIRouter()


# ── Non-streaming endpoint (simple, good for testing) ────────
@router.post("/research", response_model=None)
async def research(request: ResearchRequest):
    result = await asyncio.to_thread(
        research_graph.invoke,
        {"question": request.question}
    )
    return {
        "question": request.question,
        "sub_questions": result["sub_questions"],
        "iterations": result["iteration"],
        "critic_verdict": result["critic_verdict"],
        "final_answer": result["final_answer"]
    }


# ── Streaming endpoint (SSE) ──────────────────────────────────
@router.get("/research/stream")
async def research_stream(question: str):
    """
    SSE endpoint — streams agent updates as they happen.
    Each event is a JSON object with 'type' and 'data' fields.
    """

    async def event_generator():
        # stream=True tells LangGraph to yield after each node
        async for event in research_graph.astream(
            {"question": question},
            stream_mode="updates"   # yields state diff after each node
        ):
            node_name = list(event.keys())[0]
            node_output = event[node_name]

            # Map node name to a human-readable status
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
                "data": node_output
            }

            yield {
                "event": "message",
                "data": json.dumps(payload)
            }

        # Signal completion
        yield {
            "event": "done",
            "data": json.dumps({"type": "done"})
        }

    return EventSourceResponse(event_generator())


@router.get("/health")
async def health():
    return {"status": "ok"}