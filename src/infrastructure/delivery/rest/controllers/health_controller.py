from fastapi import APIRouter
from src.infrastructure.config.settings import settings

router = APIRouter(tags=["Health"])


@router.get("/ai-reasoning/health", summary="Health check endpoint")
async def health_check():
    """
    Health check endpoint returning service status and active provider configuration.
    """
    return {
        "status": "UP",
        "service": settings.app_name,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model_name if settings.llm_provider == "gemini" else settings.ollama_model_name,
        "pubmed_integration_url": settings.pubmed_integration_url
    }


@router.get("/", summary="Root status endpoint")
async def root():
    return {
        "service": settings.app_name,
        "status": "running",
        "health": "/ai-reasoning/health",
        "docs": "/ai-reasoning/docs"
    }
