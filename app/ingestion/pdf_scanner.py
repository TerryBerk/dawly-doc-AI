"""
PDF Scanner - Handles PDF file discovery and validation
"""

import os
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class PDFScanner:
    """
    Scans directories for PDF files and validates them
    """
    
    def __init__(self, docs_directory: str = "./docs_data"):
        self.docs_directory = Path(docs_directory)
        self.supported_extensions = [".pdf"]
        
    def scan(self, recursive: bool = True) -> List[Path]:
        """
        Scan directory for PDF files
        
        Args:
            recursive: Whether to scan subdirectories
            
        Returns:
            List of PDF file paths
        """
        pdf_files = []
        
        if not self.docs_directory.exists():
            logger.warning(f"Directory does not exist: {self.docs_directory}")
            return pdf_files
            
        pattern = "**/*.pdf" if recursive else "*.pdf"
        
        for pdf_path in self.docs_directory.glob(pattern):
            if self.validate_pdf(pdf_path):
                pdf_files.append(pdf_path)
                logger.info(f"Found PDF: {pdf_path.name}")
            else:
                logger.warning(f"Invalid PDF skipped: {pdf_path.name}")
                
        logger.info(f"Found {len(pdf_files)} valid PDF files")
        return pdf_files
    
    def validate_pdf(self, pdf_path: Path, max_size_mb: int = 100) -> bool:
        """
        Validate PDF file
        
        Args:
            pdf_path: Path to PDF file
            max_size_mb: Maximum file size in MB
            
        Returns:
            True if valid, False otherwise
        """
        if not pdf_path.exists():
            return False
            
        if not pdf_path.is_file():
            return False
            
        if pdf_path.suffix.lower() not in self.supported_extensions:
            return False
            
        # Check file size
        size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            logger.warning(f"PDF too large: {size_mb:.1f}MB (max {max_size_mb}MB)")
            return False
            
        return True
    
    def get_pdf_info(self, pdf_path: Path) -> dict:
        """
        Get basic PDF file information
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with file info
        """
        stat = pdf_path.stat()
        
        return {
            "filename": pdf_path.name,
            "path": str(pdf_path.absolute()),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": stat.st_mtime,
        }
