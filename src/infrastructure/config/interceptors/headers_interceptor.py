import logging
from typing import Set
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger(__name__)


class HeadersInterceptor(BaseHTTPMiddleware):
    """
    HTTP Inbound Request Interceptor / Middleware.
    Validates mandatory inbound headers (such as 'x-user-id') for secured endpoints.
    Public endpoints such as health checks, docs, and openapi specifications are exempt.
    """

    EXEMPT_PATHS: Set[str] = {
        "/",
        "/ai-reasoning/health",
        "/ai-reasoning/docs",
        "/ai-reasoning/openapi.json",
        "/docs",
        "/openapi.json"
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Allow CORS preflight requests without validation
        if request.method == "OPTIONS":
            return await call_next(request)

        # Allow public/exempt paths
        path = request.url.path.rstrip("/")
        if path in self.EXEMPT_PATHS or path == "" or path.startswith("/ai-reasoning/docs"):
            return await call_next(request)

        # Extract and validate 'x-user-id' header
        user_id = request.headers.get("x-user-id")
        if not user_id or not user_id.strip():
            logger.warning(
                f"[INBOUND INTERCEPTOR] Rejected {request.method} {request.url.path}: "
                f"Missing or empty 'x-user-id' header."
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Header 'x-user-id' is required."}
            )

        # Store validated user_id in request.state for convenient downstream access
        request.state.user_id = user_id.strip()

        logger.debug(
            f"[INBOUND INTERCEPTOR] Verified x-user-id for {request.method} {request.url.path} "
            f"(user: {request.state.user_id})"
        )

        return await call_next(request)
