import logging
from typing import Dict, Any
from src.config import settings
from .providers import BaseLLMProvider, GeminiProvider, OllamaProvider

logger = logging.getLogger(__name__)


class LLMGateway:
    """
    Provider-agnostic facade for interacting with the configured LLM engine.
    Allows seamless switching between Google Gemini and Ollama via environment variables.
    """
    def __init__(self):
        provider_name = settings.llm_provider.lower().strip()
        logger.info(f"Initializing LLMGateway with provider: {provider_name}")

        if provider_name == "gemini":
            self.provider: BaseLLMProvider = GeminiProvider()
        elif provider_name == "ollama":
            self.provider: BaseLLMProvider = OllamaProvider()
        else:
            logger.warning(f"Unknown provider '{provider_name}'. Defaulting to GeminiProvider.")
            self.provider: BaseLLMProvider = GeminiProvider()

    async def generate_json(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        return await self.provider.generate_json(prompt=prompt, system_instruction=system_instruction)
