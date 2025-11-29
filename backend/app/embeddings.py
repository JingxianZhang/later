from typing import List
from openai import AsyncOpenAI
from .config import settings

BATCH_SIZE = 64


async def embed_texts(texts: List[str]) -> list[list[float]]:
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        resp = await client.embeddings.create(model=settings.embeddings_model, input=batch, timeout=30.0)
        embeddings.extend([d.embedding for d in resp.data])  # type: ignore[attr-defined]
    return embeddings

