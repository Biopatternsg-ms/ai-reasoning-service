import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.infrastructure.config.settings import settings
from src.infrastructure.delivery.rest.controllers import alignment_router, health_router

# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BioPatternsG - AI Reasoning Service",
    description="Biomedical entity alignment, disambiguation, and AI reasoning microservice (Hexagonal Architecture).",
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

# Register routers from infrastructure.delivery.rest
app.include_router(alignment_router)
app.include_router(health_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.app_port, reload=True)
