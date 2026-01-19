"""
FastAPI application initialization and configuration.

This is the main entry point for the Integration Forge backend API.
"""

import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.database.client import SupabaseClient
from app.schemas.base import ErrorResponse, HealthResponse
from app.utils.errors import AppError
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application.
    This is the modern way to handle lifecycle events in FastAPI.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    logger.info(
        "Starting Integration Forge backend",
        environment=settings.environment,
        version="0.1.0",
    )

    try:
        # Initialize Supabase client (for side effects)
        SupabaseClient.get_client()
        logger.info("Database client initialized successfully")

        # Verify database connection
        is_healthy = SupabaseClient.health_check()
        if not is_healthy:
            logger.warning("Database health check failed during startup")
        else:
            logger.info("Database health check passed")

    except Exception as e:
        logger.error(
            "Failed to initialize application",
            error=str(e),
            exc_info=True,
        )
        # We log but don't fail startup - let health endpoint show the issue
        pass

    yield

    # Shutdown
    logger.info("Shutting down Integration Forge backend")
    SupabaseClient.close()
    logger.info("Application shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="Integration Forge API",
    description="Advanced RAG system for synthesizing integration code from API documentation",
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan,
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next: Any) -> Any:
    """
    Log all incoming requests and responses.

    This middleware logs request details and response times for observability.

    Args:
        request: Incoming HTTP request
        call_next: Next middleware/route handler

    Returns:
        Response from the next handler
    """
    start_time = time.time()

    # Log request
    logger.info(
        "Incoming request",
        method=request.method,
        path=request.url.path,
        client_host=request.client.host if request.client else None,
    )

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )

    return response


# Global exception handlers


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """
    Handle custom application errors.

    Args:
        request: HTTP request that caused the error
        exc: Custom application error

    Returns:
        JSONResponse with error details
    """
    logger.error(
        "Application error",
        error=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="ApplicationError",
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details or {},
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: HTTP request that caused the error
        exc: Pydantic validation error

    Returns:
        JSONResponse with validation error details
    """
    errors = exc.errors()

    logger.warning(
        "Request validation failed",
        path=request.url.path,
        errors=errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="ValidationError",
            message="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"validation_errors": errors},
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected errors.

    Args:
        request: HTTP request that caused the error
        exc: Unexpected exception

    Returns:
        JSONResponse with generic error message
    """
    logger.error(
        "Unexpected error",
        error=str(exc),
        path=request.url.path,
        exc_info=True,
    )

    # Don't leak internal errors in production
    error_message = (
        "An unexpected error occurred"
        if settings.environment == "production"
        else str(exc)
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message=error_message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={},
        ).model_dump(),
    )


# Health check endpoint


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint",
)
async def health_check() -> HealthResponse:
    """
    Check application health status.

    This endpoint verifies:
    - Application is running
    - Database connection is healthy
    - Configuration is loaded

    Returns:
        HealthResponse with service status
    """
    # Check database health
    db_healthy = SupabaseClient.health_check()

    # Determine overall status
    is_healthy = db_healthy
    status_value = "healthy" if is_healthy else "unhealthy"

    # Build service details
    services = {
        "database": "healthy" if db_healthy else "unhealthy",
        "api": "healthy",
    }

    logger.debug("Health check completed",
                 status=status_value, services=services)

    return HealthResponse(
        status=status_value,
        environment=settings.environment,
        version="0.1.0",
        services=services,
    )


# Root endpoint


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """
    Root endpoint with API information.

    Returns:
        API metadata
    """
    return {
        "name": "Integration Forge API",
        "version": "0.1.0",
        "environment": settings.environment,
        "docs": "/docs" if settings.environment != "production" else "disabled",
    }


# TODO: Register API routers here as they are implemented
# Example:
# from app.api.v1 import documents, chat, ingestion
# app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
# app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
# app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Ingestion"])
