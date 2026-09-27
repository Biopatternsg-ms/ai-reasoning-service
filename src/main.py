import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.routers.alignment_router import router as alignment_router

# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BioPatternsG - AI Reasoning Service",
    description="Biomedical entity alignment, disambiguation, and AI reasoning microservice.",
    version="1.0.0",
    docs_url="/ai-reasoning/docs",
    openapi_url="/ai-reasoning/openapi.json"
)

# CORS configuration for biopatternsg-ui and API Gateway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(alignment_router)


@app.get("/ai-reasoning/health", tags=["Health"])
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


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.app_name,
        "status": "running",
        "health": "/ai-reasoning/health",
        "docs": "/ai-reasoning/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.app_port, reload=True)
