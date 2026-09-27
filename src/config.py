from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    app_port: int = 8000
    app_name: str = "ai-reasoning-service"

    # pubmed-integration (Quarkus service)
    pubmed_integration_url: str = "http://pubmed-integration:8080"
    pubmed_timeout_seconds: float = 30.0

    # LLM Settings
    llm_provider: str = "gemini"  # "gemini" or "ollama"
    gemini_api_key: Optional[str] = None
    llm_model_name: str = "gemini-1.5-flash"

    # Ollama Settings (fallback / future)
    ollama_api_url: str = "http://localhost:11434"
    ollama_model_name: str = "gemma2:9b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
