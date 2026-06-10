# pyrefly: ignore [missing-import]
import redis
import json
import hashlib
import os

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

CACHE_TTL = 86400  # 24 hours


def make_key(sub_question: str) -> str:
    """Hash the sub-question to create a stable cache key."""
    return "research:" + hashlib.md5(sub_question.encode()).hexdigest()


def get_cached(sub_question: str) -> dict | None:
    key = make_key(sub_question)
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
    return None


def set_cached(sub_question: str, result: dict) -> None:
    key = make_key(sub_question)
    redis_client.setex(key, CACHE_TTL, json.dumps(result))