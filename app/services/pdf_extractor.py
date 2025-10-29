"""
PDF text extraction service with page tracking
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

import PyPDF2
import pdfplumber
from pypdf import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class PDFPage:
    """Single PDF page with text and metadata"""
    page_number: int
    text: str
    char_count: int
    word_count: int


@dataclass
class PDFDocument:
    """Complete PDF document with all pages"""
    filename: str
    total_pages: int
    pages: List[PDFPage]
    metadata: Dict[str, str]
    full_text: str


class PDFExtractor:
    """Extract text from PDF files with page tracking"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def extract_text(self, file_path: str) -> PDFDocument:
        """
        Extract text from PDF with page numbers
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            PDFDocument with pages, text, and metadata
            
        Raises:
            ValueError: If file doesn't exist or is not a valid PDF
            Exception: For other extraction errors
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")
        
        if file_path.suffix.lower() != '.pdf':
            raise ValueError(f"Not a PDF file: {file_path}")
        
        self.logger.info(f"Extracting text from: {file_path.name}")
        
        try:
            # Try pdfplumber first (better text extraction)
            return self._extract_with_pdfplumber(file_path)
        except Exception as e:
            self.logger.warning(f"pdfplumber failed: {e}, falling back to PyPDF2")
            try:
                return self._extract_with_pypdf2(file_path)
            except Exception as e2:
                self.logger.error(f"All extraction methods failed: {e2}")
                raise Exception(f"Failed to extract PDF text: {e2}")
    
    def _extract_with_pdfplumber(self, file_path: Path) -> PDFDocument:
        """Extract text using pdfplumber (preferred method)"""
        pages = []
        
        with pdfplumber.open(file_path) as pdf:
            # Extract metadata
            metadata = self._extract_metadata_pdfplumber(pdf)
            
            # Extract text from each page
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                
                # Clean text
                text = self._clean_text(text)
                
                pages.append(PDFPage(
                    page_number=i,
                    text=text,
                    char_count=len(text),
                    word_count=len(text.split())
                ))
                
                if i % 10 == 0:
                    self.logger.debug(f"Processed {i}/{len(pdf.pages)} pages")
        
        full_text = "\n\n".join(page.text for page in pages)
        
        return PDFDocument(
            filename=file_path.name,
            total_pages=len(pages),
            pages=pages,
            metadata=metadata,
            full_text=full_text
        )
    
    def _extract_with_pypdf2(self, file_path: Path) -> PDFDocument:
        """Extract text using PyPDF2 (fallback method)"""
        pages = []
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Extract metadata
            metadata = self._extract_metadata_pypdf2(pdf_reader)
            
            # Extract text from each page
            for i, page in enumerate(pdf_reader.pages, start=1):
                text = page.extract_text() or ""
                
                # Clean text
                text = self._clean_text(text)
                
                pages.append(PDFPage(
                    page_number=i,
                    text=text,
                    char_count=len(text),
                    word_count=len(text.split())
                ))
        
        full_text = "\n\n".join(page.text for page in pages)
        
        return PDFDocument(
            filename=file_path.name,
            total_pages=len(pages),
            pages=pages,
            metadata=metadata,
            full_text=full_text
        )
    
    def _extract_metadata_pdfplumber(self, pdf) -> Dict[str, str]:
        """Extract metadata from pdfplumber PDF object"""
        metadata = pdf.metadata or {}
        
        return {
            'title': metadata.get('Title', ''),
            'author': metadata.get('Author', ''),
            'subject': metadata.get('Subject', ''),
            'creator': metadata.get('Creator', ''),
            'producer': metadata.get('Producer', ''),
            'creation_date': str(metadata.get('CreationDate', '')),
        }
    
    def _extract_metadata_pypdf2(self, pdf_reader: PyPDF2.PdfReader) -> Dict[str, str]:
        """Extract metadata from PyPDF2 reader"""
        metadata = pdf_reader.metadata or {}
        
        return {
            'title': metadata.get('/Title', ''),
            'author': metadata.get('/Author', ''),
            'subject': metadata.get('/Subject', ''),
            'creator': metadata.get('/Creator', ''),
            'producer': metadata.get('/Producer', ''),
            'creation_date': str(metadata.get('/CreationDate', '')),
        }
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text
        
        - Normalize whitespace
        - Remove excessive newlines
        - Fix common extraction artifacts
        """
        if not text:
            return ""
        
        # Replace multiple spaces with single space
        text = ' '.join(text.split())
        
        # Replace multiple newlines with double newline
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        text = '\n'.join(cleaned_lines)
        
        # Remove common PDF artifacts
        text = text.replace('\x00', '')  # Null bytes
        text = text.replace('\ufeff', '')  # BOM
        
        return text
    
    def extract_metadata(self, file_path: str) -> Dict[str, str]:
        """
        Extract only PDF metadata without full text
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary with metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")
        
        try:
            with pdfplumber.open(file_path) as pdf:
                return self._extract_metadata_pdfplumber(pdf)
        except Exception:
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    return self._extract_metadata_pypdf2(pdf_reader)
            except Exception as e:
                self.logger.error(f"Failed to extract metadata: {e}")
                return {}
    
    def get_page_count(self, file_path: str) -> int:
        """
        Get number of pages without extracting text
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Number of pages
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")
        
        try:
            with pdfplumber.open(file_path) as pdf:
                return len(pdf.pages)
        except Exception:
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    return len(pdf_reader.pages)
            except Exception as e:
                raise Exception(f"Failed to get page count: {e}")

