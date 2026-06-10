from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from onepilot.core.config import get_settings
from onepilot.core.errors import OnePilotError
from onepilot.core.logging import get_logger, request_id_ctx

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.validate_startup_config()
    logger.info("app_startup", env=settings.APP_ENV, app=settings.APP_NAME)

    # Initialize tracing
    from onepilot.observability.tracing import initialize_tracing

    initialize_tracing(
        langsmith_enabled=settings.LANGSMITH_TRACING,
        langsmith_api_key=settings.LANGSMITH_API_KEY if settings.LANGSMITH_API_KEY else None,
        langsmith_project=settings.LANGSMITH_PROJECT,
        langsmith_endpoint=settings.LANGSMITH_ENDPOINT if settings.LANGSMITH_ENDPOINT else None,
    )

    yield
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.is_dev else None,
        redoc_url="/redoc" if settings.is_dev else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_ctx.set(rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        logger.info("request_started", method=request.method, path=request.url.path)
        response = await call_next(request)
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        )
        return response

    @app.exception_handler(OnePilotError)
    async def onepilot_error_handler(_request: Request, exc: OnePilotError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", error=str(exc), error_type=type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
        )

    _register_routers(app)
    return app


def _register_routers(app: FastAPI) -> None:
    from onepilot.api.routers import (
        admin,
        approvals,
        auth,
        chat,
        demo,
        documents,
        evaluation,
        health,
        knowledge,
        leads,
        memory,
        organizations,
        billing,
        plans,
        speech,
        usage,
        users,
    )

    app.include_router(health.router)
    app.include_router(evaluation.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(organizations.router)
    app.include_router(plans.router)
    app.include_router(billing.router)
    app.include_router(usage.router)
    app.include_router(documents.router)
    app.include_router(knowledge.router)
    app.include_router(chat.router)
    app.include_router(chat.conversations_router)
    app.include_router(approvals.router)
    app.include_router(leads.router)
    app.include_router(memory.router)
    app.include_router(speech.router)
    app.include_router(admin.router)
    app.include_router(demo.router)


app = create_app()
