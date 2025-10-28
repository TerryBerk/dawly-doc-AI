"""
Ingestion API - PDF upload and processing
"""

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import logging
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)

router = APIRouter()


class IngestionStatus(BaseModel):
    """Status of PDF ingestion"""
    job_id: str
    status: str  # pending, processing, completed, failed
    filename: str
    progress: float
    message: Optional[str] = None


class IngestionResult(BaseModel):
    """Result of PDF ingestion"""
    job_id: str
    filename: str
    doc_id: str
    device_id: Optional[str]
    status: str
    chunk_count: int
    entity_count: int
    processed_pages: int
    total_pages: int


@router.post("/ingest", response_model=IngestionResult)
async def ingest_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to process"),
    device_name: str = Form(..., description="Device name"),
    manufacturer: str = Form(..., description="Manufacturer name"),
    device_type: Optional[str] = Form(None, description="Device type"),
):
    """
    Upload and process PDF documentation
    
    Process flow:
    1. Validate PDF file
    2. Save to docs_data directory
    3. Run ingestion pipeline (background)
    4. Extract entities and index to OpenSPG
    5. Return processing status
    """
    logger.info(f"Ingesting PDF: {file.filename} for {device_name}")
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Check file size (max 100MB)
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    
    # Create docs_data directory if not exists
    docs_dir = Path("./docs_data")
    docs_dir.mkdir(exist_ok=True)
    
    # Save file
    file_path = docs_dir / file.filename
    
    try:
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(chunk_size):
                file_size += len(chunk)
                if file_size > 100 * 1024 * 1024:  # 100MB limit
                    raise HTTPException(
                        status_code=413,
                        detail="File too large (max 100MB)"
                    )
                buffer.write(chunk)
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail="Error saving file")
    
    # Generate job ID
    import uuid
    job_id = str(uuid.uuid4())[:8]
    doc_id = file_path.stem
    
    # TODO: Run ingestion pipeline in background
    # background_tasks.add_task(process_pdf, file_path, device_name, manufacturer)
    
    logger.info(f"PDF saved: {file_path} (job: {job_id})")
    
    return IngestionResult(
        job_id=job_id,
        filename=file.filename,
        doc_id=doc_id,
        device_id=None,  # Will be generated after processing
        status="pending",
        chunk_count=0,
        entity_count=0,
        processed_pages=0,
        total_pages=0,
    )


@router.get("/ingest/status/{job_id}", response_model=IngestionStatus)
async def get_ingestion_status(job_id: str):
    """
    Get status of PDF ingestion job
    
    Args:
        job_id: Job identifier
        
    Returns:
        Current status of ingestion job
    """
    # TODO: Query job status from database
    
    return IngestionStatus(
        job_id=job_id,
        status="pending",
        filename="unknown.pdf",
        progress=0.0,
        message="Job status tracking not yet implemented"
    )


@router.get("/ingest/jobs")
async def list_ingestion_jobs(
    status: Optional[str] = None,
    limit: int = 10
):
    """
    List recent ingestion jobs
    
    Args:
        status: Filter by status (pending, processing, completed, failed)
        limit: Number of jobs to return
        
    Returns:
        List of ingestion jobs
    """
    # TODO: Query jobs from database
    
    return {
        "jobs": [],
        "total": 0,
        "status": status,
        "limit": limit
    }
