"""
PDF Reader - Extracts text and metadata from PDF files
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import pdfplumber
import PyPDF2
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PDFPage:
    """Represents a single PDF page"""
    page_number: int
    text: str
    tables: List[List[List[str]]]
    metadata: Dict[str, Any]


@dataclass
class PDFDocument:
    """Represents a complete PDF document"""
    filename: str
    title: Optional[str]
    author: Optional[str]
    pages: List[PDFPage]
    total_pages: int
    metadata: Dict[str, Any]


class PDFReader:
    """
    Reads PDF files and extracts text, tables, and metadata
    """
    
    def __init__(self, preserve_tables: bool = True):
        self.preserve_tables = preserve_tables
        
    def read(self, pdf_path: Path) -> PDFDocument:
        """
        Read PDF file and extract all content
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            PDFDocument with extracted content
        """
        logger.info(f"Reading PDF: {pdf_path.name}")
        
        # Extract metadata using PyPDF2
        metadata = self._extract_metadata(pdf_path)
        
        # Extract text and tables using pdfplumber
        pages = self._extract_pages(pdf_path)
        
        document = PDFDocument(
            filename=pdf_path.name,
            title=metadata.get("title"),
            author=metadata.get("author"),
            pages=pages,
            total_pages=len(pages),
            metadata=metadata,
        )
        
        logger.info(f"Extracted {len(pages)} pages from {pdf_path.name}")
        return document
    
    def _extract_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract PDF metadata"""
        try:
            with open(pdf_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                metadata = pdf_reader.metadata or {}
                
                return {
                    "title": metadata.get("/Title", ""),
                    "author": metadata.get("/Author", ""),
                    "subject": metadata.get("/Subject", ""),
                    "creator": metadata.get("/Creator", ""),
                    "producer": metadata.get("/Producer", ""),
                    "pages": len(pdf_reader.pages),
                }
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {}
    
    def _extract_pages(self, pdf_path: Path) -> List[PDFPage]:
        """Extract text and tables from all pages"""
        pages = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract text
                    text = page.extract_text() or ""
                    
                    # Extract tables if enabled
                    tables = []
                    if self.preserve_tables:
                        page_tables = page.extract_tables()
                        if page_tables:
                            tables = page_tables
                    
                    # Create page object
                    pdf_page = PDFPage(
                        page_number=page_num,
                        text=text,
                        tables=tables,
                        metadata={
                            "width": page.width,
                            "height": page.height,
                        },
                    )
                    pages.append(pdf_page)
                    
        except Exception as e:
            logger.error(f"Error extracting pages: {e}")
            
        return pages
    
    def extract_connection_sections(self, document: PDFDocument) -> List[Dict[str, Any]]:
        """
        Extract sections related to connections (MIDI, Audio, Power)
        
        Args:
            document: PDFDocument to analyze
            
        Returns:
            List of connection-related sections
        """
        connection_keywords = [
            "midi", "audio", "power", "connection", "connect", "cable",
            "input", "output", "in", "out", "thru", "interface",
            "cv", "gate", "clock", "sync", "usb", "ethernet"
        ]
        
        sections = []
        
        for page in document.pages:
            text_lower = page.text.lower()
            
            # Check if page contains connection-related content
            relevance_score = sum(
                text_lower.count(keyword) for keyword in connection_keywords
            )
            
            if relevance_score > 0:
                sections.append({
                    "page_number": page.page_number,
                    "text": page.text,
                    "tables": page.tables,
                    "relevance_score": relevance_score,
                })
        
        # Sort by relevance
        sections.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        logger.info(f"Found {len(sections)} connection-related sections")
        return sections
