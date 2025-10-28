"""
Ingestion Pipeline - Orchestrates PDF processing workflow
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from .pdf_scanner import PDFScanner
from .pdf_reader import PDFReader, PDFDocument
from .text_chunker import TextChunker, TextChunk
from .entity_extractor import EntityExtractor

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Complete PDF ingestion pipeline for KAG system
    """
    
    def __init__(
        self,
        docs_directory: str = "./docs_data",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        use_llm_extraction: bool = True,
    ):
        self.scanner = PDFScanner(docs_directory)
        self.reader = PDFReader(preserve_tables=True)
        self.chunker = TextChunker(chunk_size, chunk_overlap)
        self.extractor = EntityExtractor(use_llm=use_llm_extraction)
        
        logger.info("Ingestion pipeline initialized")
    
    def process_all(
        self,
        recursive: bool = True,
        focus_connections: bool = True
    ) -> Dict[str, Any]:
        """
        Process all PDFs in the docs directory
        
        Args:
            recursive: Scan subdirectories
            focus_connections: Extract connection-focused sections
            
        Returns:
            Dictionary with processing results
        """
        logger.info("Starting batch PDF processing")
        
        # Scan for PDFs
        pdf_files = self.scanner.scan(recursive=recursive)
        
        if not pdf_files:
            logger.warning("No PDF files found")
            return {
                "processed_count": 0,
                "documents": [],
                "errors": [],
            }
        
        results = {
            "processed_count": 0,
            "documents": [],
            "errors": [],
            "total_chunks": 0,
            "total_entities": 0,
        }
        
        # Process each PDF
        for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
            try:
                result = self.process_single(pdf_path, focus_connections)
                results["documents"].append(result)
                results["processed_count"] += 1
                results["total_chunks"] += result.get("chunk_count", 0)
                results["total_entities"] += result.get("entity_count", 0)
            except Exception as e:
                logger.error(f"Error processing {pdf_path.name}: {e}")
                results["errors"].append({
                    "file": pdf_path.name,
                    "error": str(e),
                })
        
        logger.info(
            f"Processed {results['processed_count']}/{len(pdf_files)} PDFs, "
            f"{results['total_chunks']} chunks, "
            f"{results['total_entities']} entities"
        )
        
        return results
    
    def process_single(
        self,
        pdf_path: Path,
        focus_connections: bool = True
    ) -> Dict[str, Any]:
        """
        Process a single PDF file
        
        Args:
            pdf_path: Path to PDF file
            focus_connections: Extract connection-focused sections
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing: {pdf_path.name}")
        
        # Step 1: Read PDF
        document = self.reader.read(pdf_path)
        
        # Step 2: Extract connection sections (if enabled)
        sections_to_process = document.pages
        if focus_connections:
            connection_sections = self.reader.extract_connection_sections(document)
            if connection_sections:
                sections_to_process = [
                    page for page in document.pages
                    if any(s["page_number"] == page.page_number for s in connection_sections)
                ]
        
        # Step 3: Chunk text
        all_chunks = []
        doc_id = pdf_path.stem
        
        for page in sections_to_process:
            if page.text:
                chunks = self.chunker.chunk(
                    text=page.text,
                    page_number=page.page_number,
                    doc_id=doc_id
                )
                all_chunks.extend(chunks)
        
        # Step 4: Extract entities
        all_entities = {
            "devices": [],
            "ports": [],
            "procedures": [],
            "specifications": [],
        }
        
        for page in sections_to_process:
            if page.text:
                entities = self.extractor.extract_all(page.text, page.page_number)
                for entity_type, entity_list in entities.items():
                    if entity_type != "specifications":
                        all_entities[entity_type].extend(entity_list)
                    else:
                        # Specifications is a dict, not a list
                        if entity_list:
                            all_entities[entity_type].append(entity_list)
        
        result = {
            "filename": pdf_path.name,
            "doc_id": doc_id,
            "title": document.title,
            "total_pages": document.total_pages,
            "processed_pages": len(sections_to_process),
            "chunk_count": len(all_chunks),
            "entity_count": sum(
                len(v) if isinstance(v, list) else 1
                for v in all_entities.values()
            ),
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                    "page_number": chunk.page_number,
                }
                for chunk in all_chunks[:5]  # First 5 chunks preview
            ],
            "entities": {
                k: v[:5] if isinstance(v, list) else v  # First 5 entities preview
                for k, v in all_entities.items()
            },
        }
        
        logger.info(
            f"Completed {pdf_path.name}: "
            f"{len(all_chunks)} chunks, "
            f"{result['entity_count']} entities"
        )
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics
        
        Returns:
            Dictionary with stats
        """
        pdf_files = self.scanner.scan(recursive=True)
        
        return {
            "total_pdfs": len(pdf_files),
            "docs_directory": str(self.scanner.docs_directory),
            "chunk_size": self.chunker.chunk_size,
            "chunk_overlap": self.chunker.chunk_overlap,
        }
