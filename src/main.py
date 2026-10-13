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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.infrastructure.config.settings import settings
from src.infrastructure.config.interceptors import HeadersInterceptor
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

# Interceptor: Inbound headers validation (e.g. x-user-id)
app.add_middleware(HeadersInterceptor)

# Register routers from infrastructure.delivery.rest
app.include_router(alignment_router)
app.include_router(health_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.app_port, reload=True)
