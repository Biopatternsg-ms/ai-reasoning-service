#
# Copyright © 2026 biopatternsg (biopatternsg@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import json
import logging
import httpx
from typing import Dict, Any
from src.domain.ports.llm_reasoning_port import LLMReasoningPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class DeepSeekAdapter(LLMReasoningPort):
    """
    Driven adapter implementing LLMReasoningPort using the DeepSeek API
    (OpenAI-compatible /chat/completions endpoint with JSON output mode).
    """

    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.model = settings.deepseek_model_name or "deepseek-chat"
        self.endpoint = settings.deepseek_api_url or "https://api.deepseek.com/chat/completions"

    async def generate_json(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        """
        Calls DeepSeek API requesting structured JSON output.
        """
        if not self.api_key:
            logger.error("DEEPSEEK_API_KEY is not configured in the environment.")
            raise ValueError("DEEPSEEK_API_KEY not configured. Please define it in environment variables.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_instruction
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "response_format": {
                "type": "json_object"
            },
            "temperature": 0.1
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.post(self.endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                choices = data.get("choices", [])
                if not choices:
                    raise ValueError("DeepSeek returned no choices in response.")

                content = choices[0].get("message", {}).get("content", "{}")
                return json.loads(content)

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error from DeepSeek API ({e.response.status_code}): {e.response.text}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON response from DeepSeek: {content}")
                raise ValueError(f"Invalid JSON response from DeepSeek: {str(e)}")
            except Exception as e:
                logger.error(f"Error during DeepSeek inference: {str(e)}")
                raise
