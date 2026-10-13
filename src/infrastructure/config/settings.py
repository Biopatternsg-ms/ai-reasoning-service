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
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    app_port: int = 8000
    app_name: str = "ai-reasoning-service"

    # pubmed-integration (Quarkus service)
    pubmed_integration_url: str = "http://pubmed-integration:8080"
    pubmed_timeout_seconds: float = 30.0

    # search-biological-objects (Quarkus service)
    biological_objects_url: Optional[str] = None
    search_biological_objects_url: str = "http://search-biological-objects:8080"
    search_biological_objects_timeout_seconds: float = 15.0

    @property
    def effective_biological_objects_url(self) -> str:
        """Returns biological_objects_url if set, otherwise falls back to search_biological_objects_url."""
        return self.biological_objects_url or self.search_biological_objects_url

    # LLM Settings
    llm_provider: str = "gemini"  # "gemini", "deepseek", "nvidia", or "ollama"
    gemini_api_key: Optional[str] = None
    llm_model_name: str = "gemini-3.5-flash-lite"

    # DeepSeek Settings
    deepseek_api_key: Optional[str] = None
    deepseek_api_url: str = "https://api.deepseek.com/chat/completions"
    deepseek_model_name: str = "deepseek-chat"

    # NVIDIA NIM Settings
    nvidia_api_key: Optional[str] = None
    nvidia_api_url: str = "https://integrate.api.nvidia.com/v1/chat/completions"
    nvidia_model_name: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    nvidia_temperature: float = 0.6
    nvidia_top_p: float = 0.95
    nvidia_max_tokens: int = 16384
    nvidia_enable_thinking: bool = True
    nvidia_reasoning_budget: int = 16384

    # Ollama Settings (fallback / local)
    ollama_api_url: str = "http://localhost:11434"
    ollama_model_name: str = "gemma2:9b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
