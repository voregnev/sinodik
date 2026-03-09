"""
OpenAI-compatible embedding service.

Calls a remote embedding API. Disabled when embedding_url is not configured.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    return bool(settings.embedding_url and settings.embedding_model)


async def embed_name_async(name: str) -> list[float] | None:
    """Return embedding vector for a name via OpenAI-compatible API, or None if unavailable."""
    if not _is_configured():
        return None
    try:
        headers = {"Content-Type": "application/json"}
        if settings.embedding_api_key:
            headers["Authorization"] = f"Bearer {settings.embedding_api_key}"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.embedding_url}/embeddings",
                headers=headers,
                json={"model": settings.embedding_model, "input": name},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"Embedding failed for '{name}': {e}")
        return None


