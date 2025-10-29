"""
Background job processing service for PDF ingestion
"""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import traceback

import redis

from app.config import get_settings
from app.services.pdf_extractor import PDFExtractor, PDFDocument
from app.services.text_chunker import TextChunker
from app.services.embedding_service import get_embedding_service
from app.services.elasticsearch_service import get_elasticsearch_service
from app.services.device_extractor import DeviceExtractor

logger = logging.getLogger(__name__)


class IngestionJobProcessor:
    """Process PDF ingestion jobs in background"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        settings = get_settings()
        
        # Redis client for job status
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        
        # Initialize services
        self.pdf_extractor = PDFExtractor()
        self.text_chunker = TextChunker(chunk_size=512, overlap=128)
        self.embedding_service = get_embedding_service()
        self.elasticsearch_service = get_elasticsearch_service()
        self.device_extractor = DeviceExtractor()
    
    async def process_pdf_ingestion(
        self,
        job_id: str,
        file_path: str,
        device_name: str,
        manufacturer: str,
        device_type: Optional[str] = None
    ):
        """
        Full ingestion pipeline
        
        Steps:
        1. Extract text from PDF
        2. Chunk text
        3. Generate embeddings
        4. Index in Elasticsearch
        5. Extract and store device metadata
        6. Update job status
        
        Args:
            job_id: Unique job identifier
            file_path: Path to PDF file
            device_name: Device name
            manufacturer: Manufacturer name
            device_type: Optional device type
        """
        self.logger.info(f"Starting ingestion job {job_id}")
        
        try:
            # Update status: processing
            self.update_job_status(job_id, "processing", 0, 
                                 message="Starting PDF processing")
            
            # Step 1: Extract text from PDF
            self.logger.info(f"[{job_id}] Extracting PDF text")
            pdf_doc = self.pdf_extractor.extract_text(file_path)
            
            self.update_job_status(job_id, "processing", 20,
                                 message=f"Extracted {pdf_doc.total_pages} pages",
                                 total_pages=pdf_doc.total_pages)
            
            # Step 2: Extract device metadata
            self.logger.info(f"[{job_id}] Extracting device metadata")
            device_info = self.device_extractor.extract_device_info(
                pdf_doc.full_text,
                pdf_doc.filename,
                device_name,
                manufacturer
            )
            
            self.update_job_status(job_id, "processing", 30,
                                 message="Extracted device metadata",
                                 device_id=device_info.device_id)
            
            # Step 3: Chunk text
            self.logger.info(f"[{job_id}] Chunking text")
            
            # Prepare pages for chunking
            pages_data = [
                {
                    'text': page.text,
                    'page_number': page.page_number,
                    'section': None
                }
                for page in pdf_doc.pages
            ]
            
            chunks = self.text_chunker.chunk_document(pages_data, device_info.device_id)
            
            self.update_job_status(job_id, "processing", 50,
                                 message=f"Created {len(chunks)} text chunks",
                                 chunk_count=len(chunks))
            
            # Step 4: Generate embeddings
            self.logger.info(f"[{job_id}] Generating embeddings")
            
            # Prepare chunks for embedding
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_service.generate_embeddings(
                chunk_texts,
                batch_size=32,
                show_progress=False
            )
            
            self.update_job_status(job_id, "processing", 70,
                                 message="Generated embeddings")
            
            # Step 5: Prepare chunks for indexing
            self.logger.info(f"[{job_id}] Preparing for indexing")
            
            es_chunks = []
            for chunk, embedding in zip(chunks, embeddings):
                es_chunk = {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "embedding": embedding.tolist(),
                    "device_id": device_info.device_id,
                    "device_name": device_name,
                    "manufacturer": manufacturer,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "chunk_index": chunk.chunk_index,
                    "token_count": chunk.token_count,
                    "char_count": chunk.char_count,
                    "doc_id": device_info.device_id,
                    "filename": pdf_doc.filename
                }
                es_chunks.append(es_chunk)
            
            # Step 6: Index in Elasticsearch
            self.logger.info(f"[{job_id}] Indexing in Elasticsearch")
            
            index_result = self.elasticsearch_service.bulk_index_chunks(es_chunks)
            
            self.update_job_status(job_id, "processing", 90,
                                 message=f"Indexed {index_result['success']} chunks")
            
            # Step 7: Store device metadata (would go to PostgreSQL)
            # TODO: Implement PostgreSQL storage
            self.logger.info(f"[{job_id}] Storing device metadata")
            
            # Step 8: Complete
            self.update_job_status(
                job_id, 
                "completed", 
                100,
                message="Ingestion completed successfully",
                device_id=device_info.device_id,
                doc_id=device_info.device_id,
                chunk_count=len(chunks),
                entity_count=len(device_info.connections),
                processed_pages=pdf_doc.total_pages,
                total_pages=pdf_doc.total_pages
            )
            
            self.logger.info(f"[{job_id}] Ingestion completed successfully")
        
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            
            self.logger.error(f"[{job_id}] Ingestion failed: {error_msg}")
            self.logger.error(error_trace)
            
            self.update_job_status(
                job_id,
                "failed",
                0,
                message=f"Ingestion failed: {error_msg}",
                error=error_msg,
                error_trace=error_trace
            )
            
            raise
    
    def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: int,
        message: Optional[str] = None,
        **kwargs
    ):
        """
        Update job status in Redis
        
        Args:
            job_id: Job identifier
            status: Job status (pending, processing, completed, failed)
            progress: Progress percentage (0-100)
            message: Status message
            **kwargs: Additional fields to store
        """
        job_data = {
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "message": message or "",
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Add additional fields
        job_data.update(kwargs)
        
        # Add completed_at for final states
        if status in ["completed", "failed"]:
            job_data["completed_at"] = datetime.utcnow().isoformat()
        
        # Store in Redis with 24 hour expiry
        key = f"job:{job_id}"
        self.redis_client.setex(
            key,
            86400,  # 24 hours
            json.dumps(job_data)
        )
        
        self.logger.debug(f"Job {job_id}: {status} ({progress}%) - {message}")
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status from Redis
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job data dictionary or None if not found
        """
        key = f"job:{job_id}"
        data = self.redis_client.get(key)
        
        if data:
            return json.loads(data)
        
        return None
    
    def delete_job(self, job_id: str):
        """Delete job from Redis"""
        key = f"job:{job_id}"
        self.redis_client.delete(key)
        self.logger.info(f"Deleted job {job_id}")
    
    def list_jobs(self, limit: int = 100) -> list:
        """
        List recent jobs
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job data dictionaries
        """
        keys = self.redis_client.keys("job:*")
        jobs = []
        
        for key in keys[:limit]:
            data = self.redis_client.get(key)
            if data:
                jobs.append(json.loads(data))
        
        # Sort by updated_at descending
        jobs.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        
        return jobs


# Singleton instance
_job_processor = None


def get_job_processor() -> IngestionJobProcessor:
    """Get or create job processor singleton"""
    global _job_processor
    if _job_processor is None:
        _job_processor = IngestionJobProcessor()
    return _job_processor

