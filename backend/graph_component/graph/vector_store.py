import os
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, ScoredPoint
)
from sentence_transformers import SentenceTransformer
import uuid

qdrant = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)

embedder = SentenceTransformer("all-MiniLM-L6-v2")

# ── Two separate collections ──────────────────────────────────
WEB_COLLECTION = "research_results"      # existing
DOCS_COLLECTION = "private_documents"    # new

SIMILARITY_THRESHOLD = 0.82
DOCS_THRESHOLD = 0.75   # slightly lower — private docs may use different phrasing


def ensure_collection(name: str):
    try:
        qdrant.get_collection(name)
    except Exception:
        qdrant.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        print(f"[QDRANT] Created collection '{name}'")


# ── Existing web research functions (unchanged) ───────────────
def search_similar(sub_question: str) -> dict | None:
    ensure_collection(WEB_COLLECTION)
    query_vector = embedder.encode(sub_question).tolist()
    results = qdrant.query_points(
        collection_name=WEB_COLLECTION,
        query=query_vector,
        limit=1,
        score_threshold=SIMILARITY_THRESHOLD
    ).points
    if results:
        print(f"[QDRANT HIT] score={results[0].score:.3f} | {sub_question[:60]}...")
        return results[0].payload
    return None


def store_result(sub_question: str, result: dict) -> None:
    ensure_collection(WEB_COLLECTION)
    vector = embedder.encode(sub_question).tolist()
    qdrant.upsert(
        collection_name=WEB_COLLECTION,
        points=[PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={"question": result["question"], "summary": result["summary"]}
        )]
    )
    print(f"[QDRANT STORE] {sub_question[:60]}...")


# ── New private document functions ───────────────────────────
def store_document_chunks(chunks: list[dict]) -> int:
    """
    Store document chunks in private collection.
    Each chunk: {"text": str, "source": str, "page": int}
    Returns number of chunks stored.
    """
    ensure_collection(DOCS_COLLECTION)

    points = []
    for chunk in chunks:
        vector = embedder.encode(chunk["text"]).tolist()
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "text": chunk["text"],
                "source": chunk["source"],
                "page": chunk.get("page", 0)
            }
        ))

    qdrant.upsert(collection_name=DOCS_COLLECTION, points=points)
    print(f"[DOCS] Stored {len(points)} chunks from '{chunks[0]['source']}'")
    return len(points)


def search_private_docs(query: str, top_k: int = 3) -> list[dict]:
    """
    Search private document collection.
    Returns list of relevant chunks with source info.
    """
    ensure_collection(DOCS_COLLECTION)

    query_vector = embedder.encode(query).tolist()
    results = qdrant.query_points(
        collection_name=DOCS_COLLECTION,
        query=query_vector,
        limit=top_k,
        score_threshold=DOCS_THRESHOLD
    ).points

    if results:
        print(f"[DOCS HIT] {len(results)} chunks for: {query[:60]}...")
        return [r.payload for r in results]
    return []


def list_uploaded_documents() -> list[str]:
    """Return list of unique source filenames in private collection."""
    ensure_collection(DOCS_COLLECTION)
    try:
        # Scroll through all points to get unique sources
        points, _ = qdrant.scroll(
            collection_name=DOCS_COLLECTION,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        sources = list(set(p.payload.get("source", "") for p in points))
        return sources
    except Exception:
        return []


def delete_document(source_name: str) -> int:
    """Delete all chunks belonging to a specific document."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    ensure_collection(DOCS_COLLECTION)
    qdrant.delete(
        collection_name=DOCS_COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(
                key="source",
                match=MatchValue(value=source_name)
            )]
        )
    )
    print(f"[DOCS] Deleted '{source_name}'")
    return 1