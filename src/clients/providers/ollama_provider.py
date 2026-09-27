import json
import logging
import httpx
from typing import Dict, Any
from src.config import settings
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    def __init__(self):
        self.base_url = settings.ollama_api_url.rstrip("/")
        self.model = settings.ollama_model_name or "gemma2:9b"

    async def generate_json(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        """
        Calls the local Ollama endpoint (/api/generate) enforcing JSON format.
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_instruction,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                raw_response = data.get("response", "{}")
                return json.loads(raw_response)
            except Exception as e:
                logger.error(f"Error during local inference with Ollama ({url}): {str(e)}")
                raise
