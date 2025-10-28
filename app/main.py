"""Main FastAPI application for Dawly Documentation AI"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from typing import Dict

from app.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Dawly Documentation AI",
    description="KAG-based documentation retrieval for music hardware",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "dawly-doc-ai",
        "version": "0.1.0"
    }


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {
        "message": "Dawly Documentation AI",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("Starting Dawly Documentation AI")
    logger.info(f"API Host: {settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"CORS Origins: {settings.ALLOWED_ORIGINS}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Shutting down Dawly Documentation AI")
