"""Qdrant-backed shared memory for the worker swarm."""
import logging
import os
import time
import uuid

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

logger = logging.getLogger("worker.memory")

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "models/gemini-embedding-001")
COLLECTION_NAME = "agent_memory"
EMBEDDING_DIM = 768  # truncated via output_dimensionality to match this Qdrant collection

_qdrant = QdrantClient(url=QDRANT_URL)
_embeddings = GoogleGenerativeAIEmbeddings(model=GEMINI_EMBED_MODEL, google_api_key=GEMINI_API_KEY)


def _ensure_collection() -> None:
    existing = [c.name for c in _qdrant.get_collections().collections]
    if COLLECTION_NAME not in existing:
        _qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection '%s'", COLLECTION_NAME)


def get_job_context(job_id: str, limit: int = 20) -> str:
    """Return prior completed task outputs for this job, oldest first. Empty string on any failure."""
    try:
        _ensure_collection()
        points, _ = _qdrant.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(must=[FieldCondition(key="job_id", match=MatchValue(value=job_id))]),
            limit=limit,
            with_payload=True,
        )
        if not points:
            return ""
        points.sort(key=lambda p: p.payload.get("created_at", 0))
        logger.info("Retrieved %d prior result(s) from Qdrant for job %s", len(points), job_id)
        return "\n".join(f"- [{p.payload.get('step')}]: {p.payload.get('output')}" for p in points)
    except Exception as exc:
        logger.warning("Failed to read context from Qdrant for job %s: %s", job_id, exc)
        return ""


def store_task_result(job_id: str, task_id: str, step: str, output: str) -> None:
    """Embed and upsert this task's output so later tasks in the same job can retrieve it."""
    try:
        _ensure_collection()
        vector = _embeddings.embed_query(output[:4000], output_dimensionality=EMBEDDING_DIM)
        _qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "job_id": job_id,
                        "task_id": task_id,
                        "step": step,
                        "output": output[:4000],
                        "created_at": time.time(),
                    },
                )
            ],
        )
        logger.info("Stored result for task %s (job %s) in Qdrant", task_id, job_id)
    except Exception as exc:
        logger.warning("Failed to store result in Qdrant for task %s (job %s): %s", task_id, job_id, exc)
