"""
Health check endpoints
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict
import asyncio

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    version: str
    services: Dict[str, str]

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "services": {
            "api": "up",
            "database": "checking...",
            "elasticsearch": "checking...",
            "redis": "checking..."
        }
    }

@router.get("/ready")
async def readiness_check():
    """Readiness check for k8s"""
    # TODO: Check all dependencies
    return {"status": "ready"}

@router.get("/live")
async def liveness_check():
    """Liveness check for k8s"""
    return {"status": "alive"}
