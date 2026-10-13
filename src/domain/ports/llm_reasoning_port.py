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
