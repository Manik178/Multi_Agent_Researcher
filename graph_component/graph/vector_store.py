import os
# pyrefly: ignore [missing-import]
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, ScoredPoint
)
from sentence_transformers import SentenceTransformer
import uuid

# ── Init clients ─────────────────────────────────────────────
qdrant = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)

embedder = SentenceTransformer("all-MiniLM-L6-v2")
# Small, fast, 384-dim embeddings — perfect for this use case

COLLECTION_NAME = "research_results"
SIMILARITY_THRESHOLD = 0.82  # tune this — higher = stricter matching


def ensure_collection():
    """Create collection if it doesn't exist."""
    try:
        qdrant.get_collection(COLLECTION_NAME)
    except Exception:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE
            )
        )
        print(f"[QDRANT] Created collection '{COLLECTION_NAME}'")

def search_similar(sub_question: str) -> dict | None:
    ensure_collection()

    query_vector = embedder.encode(sub_question).tolist()

    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=1,
        score_threshold=SIMILARITY_THRESHOLD
    ).points

    if results:
        print(f"[QDRANT HIT] score={results[0].score:.3f} | {sub_question[:60]}...")
        return results[0].payload
    return None

def store_result(sub_question: str, result: dict) -> None:
    """Embed and store a research result in Qdrant."""
    ensure_collection()

    vector = embedder.encode(sub_question).tolist()

    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "question": result["question"],
                    "summary": result["summary"]
                }
            )
        ]
    )
    print(f"[QDRANT STORE] {sub_question[:60]}...")