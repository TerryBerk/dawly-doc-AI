"""
Document ingestion API endpoints
"""

import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import logging
import shutil

from app.services.job_processor import get_job_processor

logger = logging.getLogger(__name__)
router = APIRouter()

# Temporary file storage directory
TEMP_DIR = Path("/tmp/dawly_uploads")
TEMP_DIR.mkdir(exist_ok=True)

# Max file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


class IngestionResult(BaseModel):
    """Ingestion result model"""
    job_id: str
    filename: str
    doc_id: Optional[str] = None
    device_id: Optional[str] = None
    status: str
    chunk_count: int = 0
    entity_count: int = 0
    processed_pages: int = 0
    total_pages: int = 0
    message: str = ""


class JobStatus(BaseModel):
    """Job status model"""
    job_id: str
    status: str
    progress: int
    message: str
    filename: Optional[str] = None
    device_id: Optional[str] = None
    chunk_count: Optional[int] = None
    total_pages: Optional[int] = None
    processed_pages: Optional[int] = None
    error: Optional[str] = None


@router.post("/ingest", response_model=IngestionResult)
async def ingest_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    device_name: str = Form(...),
    manufacturer: str = Form(...),
    device_type: Optional[str] = Form(None)
):
    """
    Upload and ingest PDF documentation
    
    Processes the PDF in background:
    1. Extracts text from PDF with page numbers
    2. Chunks text with overlap
    3. Generates embeddings
    4. Indexes in Elasticsearch
    5. Extracts device metadata
    
    Returns job_id for status tracking.
    """
    try:
        logger.info(f"Ingesting PDF: {file.filename} for {device_name}")
        
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
            )
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Save file temporarily
        temp_file = TEMP_DIR / f"{job_id}_{file.filename}"
        
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Saved temporary file: {temp_file}")
        
        # Initialize job processor
        job_processor = get_job_processor()
        
        # Create initial job status
        job_processor.update_job_status(
            job_id,
            "pending",
            0,
            message="Job queued for processing",
            filename=file.filename,
            device_name=device_name,
            manufacturer=manufacturer,
            created_at=None
        )
        
        # Start background processing
        background_tasks.add_task(
            job_processor.process_pdf_ingestion,
            job_id=job_id,
            file_path=str(temp_file),
            device_name=device_name,
            manufacturer=manufacturer,
            device_type=device_type
        )
        
        # Clean up temp file after processing
        background_tasks.add_task(cleanup_temp_file, temp_file)
        
        logger.info(f"Started background job: {job_id}")
        
        return IngestionResult(
            job_id=job_id,
            filename=file.filename,
            status="pending",
            message="Processing started. Use /ingest/status/{job_id} to check progress."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingest/status/{job_id}", response_model=JobStatus)
async def get_ingestion_status(job_id: str):
    """
    Check ingestion job status
    
    Returns current status, progress percentage, and details.
    """
    try:
        job_processor = get_job_processor()
        job_data = job_processor.get_job_status(job_id)
        
        if not job_data:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found. Jobs expire after 24 hours."
            )
        
        return JobStatus(**job_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ingest/job/{job_id}")
async def delete_job(job_id: str):
    """Delete job from tracking (job expires after 24h anyway)"""
    try:
        job_processor = get_job_processor()
        job_data = job_processor.get_job_status(job_id)
        
        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job_processor.delete_job(job_id)
        
        return {"message": f"Job {job_id} deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job deletion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingest/jobs")
async def list_jobs(limit: int = 20):
    """List recent ingestion jobs"""
    try:
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        job_processor = get_job_processor()
        jobs = job_processor.list_jobs(limit=limit)
        
        return {"jobs": jobs, "count": len(jobs)}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job list error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def cleanup_temp_file(file_path: Path):
    """Delete temporary file"""
    try:
        if file_path.exists():
            os.remove(file_path)
            logger.info(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to clean up temp file {file_path}: {e}")
