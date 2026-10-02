from abc import ABC, abstractmethod
from typing import Dict, Any


class LLMReasoningPort(ABC):
    """
    Driven / Outbound port for performing biomedical reasoning and disambiguation
    via an LLM provider (Google Gemini, Ollama, etc.).
    """

    @abstractmethod
    async def generate_json(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        """
        Executes a prompt against the configured LLM engine and returns the parsed JSON response.
        
        :param prompt: The input micro-prompt containing entities and scientific guidelines.
        :param system_instruction: The system-level persona and constraints.
        :return: Dict representation of the structured LLM output.
        """
        pass
