"""
API v1 routes.

This module aggregates all v1 API routers into a single router that can be
mounted to the main FastAPI application.

Phase 5: Includes health, ingest, chat, and documents endpoints (no auth)
Phase 6: Will add authentication middleware to protect endpoints
"""

from fastapi import APIRouter

# Import routers as we create them
from app.api.v1 import chat, documents, ingest, threads, users, stats, feedback

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

# TODO: Add health router when we extract it from main.py
# from app.api.v1 import health
# router.include_router(health.router, tags=["health"])
