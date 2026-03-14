"""
API v1 routes.

This module aggregates all v1 API routers into a single router that can be
mounted to the main FastAPI application.
"""

from fastapi import APIRouter

# Import routers as we create them
from app.api.v1 import chat, documents, feedback, ingest, rate_limit, stats, threads, users

# Create main v1 router
router = APIRouter()

# Include all sub-routers
# Note: Each sub-router already has its own prefix, so we don't add one here
router.include_router(users.router, tags=["users"])
router.include_router(ingest.router, tags=["ingestion"])
router.include_router(documents.router, tags=["documents"])
router.include_router(chat.router, tags=["chat"])
router.include_router(threads.router, tags=["threads"])
router.include_router(stats.router, tags=["stats"])
router.include_router(feedback.router, tags=["feedback"])
router.include_router(rate_limit.router)
