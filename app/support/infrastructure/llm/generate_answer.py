import logging
import aiohttp
from app.core.config.base import get_settings
from app.core.config.support.llm.model import LLM_MODEL

logger = logging.getLogger(__name__)

async def send_to_llm(
    prompt: str, 
    http_client: aiohttp.ClientSession,
) -> str:
    settings = get_settings()

    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with http_client.post(
            f"{settings.ollama.url}/api/generate",
            json=payload,
            timeout=timeout
        ) as response:
            response.raise_for_status()
            data = await response.json()
            
            answer = data.get("response")
            
            if not answer:
                logger.warning(f"Ollama returned empty response for prompt: {prompt[:50]}...")
                return "Sorry, the LLM sent an empty response"
                
            return answer
    except aiohttp.ClientError as e:
        logger.error(f"Ollama connection error: {e}")
        return "Something went wrong with network"
    except Exception as e:
        logger.exception("Unexpected error in send_to_llm")
        return "Something went wrong with LLM"