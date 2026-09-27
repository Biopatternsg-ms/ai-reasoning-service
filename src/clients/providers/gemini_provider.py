import json
import logging
import httpx
from typing import Dict, Any
from src.config import settings
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.llm_model_name or "gemini-1.5-flash"
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    async def generate_json(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        """
        Calls the Google Gemini REST API requesting strict JSON output.
        """
        if not self.api_key:
            logger.error("GEMINI_API_KEY is not configured in the environment.")
            raise ValueError("GEMINI_API_KEY not configured. Please define it in environment variables.")

        url = f"{self.endpoint}?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system_instruction}
                ]
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError("Gemini returned no response candidates.")

                raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                return json.loads(raw_text)

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error from Gemini API ({e.response.status_code}): {e.response.text}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON response from Gemini: {raw_text}")
                raise ValueError(f"Invalid JSON response from Gemini: {str(e)}")
            except Exception as e:
                logger.error(f"Error during Gemini inference: {str(e)}")
                raise
