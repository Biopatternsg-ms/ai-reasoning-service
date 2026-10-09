import json
import logging
import re
import httpx
from typing import Dict, Any
from src.domain.ports.llm_reasoning_port import LLMReasoningPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class NvidiaAdapter(LLMReasoningPort):
    """
    Driven adapter implementing LLMReasoningPort using the NVIDIA NIM API
    (OpenAI-compatible /v1/chat/completions endpoint with robust JSON extraction).
    """

    def __init__(self):
        self.api_key = settings.nvidia_api_key
        self.model = settings.nvidia_model_name or "nvidia/nemotron-3.5-lightning-30b-a3b"
        self.endpoint = settings.nvidia_api_url or "https://integrate.api.nvidia.com/v1/chat/completions"

    async def generate_json(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        """
        Calls NVIDIA NIM API requesting structured JSON output with Nemotron reasoning support.
        """
        if not self.api_key:
            logger.error("NVIDIA_API_KEY is not configured in the environment.")
            raise ValueError("NVIDIA_API_KEY not configured. Please define it in environment variables.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": f"{system_instruction}\n\nIMPORTANT: You MUST respond ONLY with a raw, valid JSON object without markdown fences or additional commentary."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "response_format": {
                "type": "json_object"
            },
            "temperature": settings.nvidia_temperature,
            "top_p": settings.nvidia_top_p,
            "max_tokens": settings.nvidia_max_tokens
        }

        # If thinking / reasoning budget is enabled (specifically for Nemotron)
        # Note: In the OpenAI Python SDK extra_body is unpacked into the root JSON payload.
        # In raw HTTP requests, these fields go directly at the root of the JSON body.
        if settings.nvidia_enable_thinking:
            payload["chat_template_kwargs"] = {
                "enable_thinking": True
            }
            if settings.nvidia_reasoning_budget:
                payload["reasoning_budget"] = settings.nvidia_reasoning_budget

        payload["stream"] = True

        logger.info(f"[OUTBOUND HTTP] Calling LLM API at URL: {self.endpoint} (model: '{self.model}')")

        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                content_chunks = []
                reasoning_chunks = []

                async with client.stream("POST", self.endpoint, headers=headers, json=payload) as response:
                    logger.info(f"[OUTBOUND HTTP] LLM API responded with status {response.status_code} for URL: {self.endpoint}")
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            choices = chunk_data.get("choices", [])
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            if "reasoning_content" in delta and delta["reasoning_content"]:
                                reasoning_chunks.append(delta["reasoning_content"])
                            if "content" in delta and delta["content"]:
                                content_chunks.append(delta["content"])
                        except Exception:
                            continue

                raw_content = "".join(content_chunks).strip()
                if not raw_content:
                    raise ValueError("NVIDIA NIM streamed an empty response.")

                # Robust JSON cleanup in case model wraps output in markdown fences
                cleaned_content = raw_content
                if cleaned_content.startswith("```"):
                    cleaned_content = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned_content)
                    cleaned_content = re.sub(r"\n?```$", "", cleaned_content).strip()

                return json.loads(cleaned_content)

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error from NVIDIA API ({e.response.status_code}): {e.response.text}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON response from NVIDIA: {raw_content}")
                raise ValueError(f"Invalid JSON response from NVIDIA: {str(e)}")
            except Exception as e:
                logger.error(f"Error during NVIDIA inference: {str(e)}")
                raise
