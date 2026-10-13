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
import logging
from src.domain.ports.llm_reasoning_port import LLMReasoningPort
from src.infrastructure.config.settings import settings
from .gemini_adapter import GeminiAdapter
from .ollama_adapter import OllamaAdapter
from .deepseek_adapter import DeepSeekAdapter
from .nvidia_adapter import NvidiaAdapter

logger = logging.getLogger(__name__)


class LLMAdapterFactory:
    """
    Factory creating the appropriate LLMReasoningPort adapter
    according to environment configuration.
    """

    @staticmethod
    def create_adapter() -> LLMReasoningPort:
        provider = settings.llm_provider.lower().strip()
        logger.info(f"Instantiating LLM adapter for provider: '{provider}'")

        if provider == "gemini":
            return GeminiAdapter()
        elif provider == "deepseek":
            return DeepSeekAdapter()
        elif provider == "nvidia":
            return NvidiaAdapter()
        elif provider == "ollama":
            return OllamaAdapter()
        else:
            logger.warning(f"Unknown LLM provider '{provider}'. Defaulting to GeminiAdapter.")
            return GeminiAdapter()
