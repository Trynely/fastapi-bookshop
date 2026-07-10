import aiohttp
from app.core.config.base import get_settings
import logging
from typing import List

logger = logging.getLogger(__name__)

async def get_embedding(
    embedding_model: str,
    text: str, 
    http_client: aiohttp.ClientSession
) -> List[float]:
    settings = get_settings()
    
    payload = {
        "model": embedding_model,
        "input": text
    }
    
    try:
        async with http_client.post(
            f"{settings.ollama.url}/api/embed",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            response.raise_for_status()
            data = await response.json()
            embeddings = data.get("embeddings")

            if not isinstance(embeddings, list) or not embeddings:
                raise ValueError(f"Ollama returned unexpected format: {data}")

            return embeddings[0]
    except aiohttp.ClientError as e:
        logger.error(f"Network error while fetching embedding: {e}")
        raise
    except Exception as e:
        logger.exception("Unexpected error")
        raise