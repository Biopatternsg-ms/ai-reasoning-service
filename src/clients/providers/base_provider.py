from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_json(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        """
        Executes inference enforcing structured JSON output.
        """
        pass
