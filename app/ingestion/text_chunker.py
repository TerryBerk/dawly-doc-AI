"""
Text Chunker - Splits text into manageable chunks for processing
"""

import logging
import re
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text"""
    chunk_id: str
    text: str
    page_number: int
    start_index: int
    end_index: int
    metadata: Dict[str, Any]


class TextChunker:
    """
    Chunks text into smaller pieces for KAG processing
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n\n"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
        
    def chunk(
        self,
        text: str,
        page_number: int,
        doc_id: str
    ) -> List[TextChunk]:
        """
        Split text into chunks with overlap
        
        Args:
            text: Text to chunk
            page_number: Source page number
            doc_id: Document identifier
            
        Returns:
            List of TextChunks
        """
        if not text or not text.strip():
            return []
            
        # Split by separator first
        sections = self._split_by_separator(text)
        
        chunks = []
        current_chunk = ""
        chunk_start = 0
        chunk_count = 0
        
        for section in sections:
            # If section alone exceeds chunk_size, split it further
            if len(section) > self.chunk_size:
                # Save current chunk if exists
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk,
                        page_number,
                        doc_id,
                        chunk_count,
                        chunk_start,
                        chunk_start + len(current_chunk)
                    ))
                    chunk_count += 1
                    current_chunk = ""
                
                # Split large section
                sub_chunks = self._split_large_section(section)
                for sub_chunk in sub_chunks:
                    chunks.append(self._create_chunk(
                        sub_chunk,
                        page_number,
                        doc_id,
                        chunk_count,
                        chunk_start,
                        chunk_start + len(sub_chunk)
                    ))
                    chunk_count += 1
                    chunk_start += len(sub_chunk)
                    
            else:
                # Check if adding this section exceeds chunk_size
                if len(current_chunk) + len(section) > self.chunk_size:
                    # Save current chunk
                    if current_chunk:
                        chunks.append(self._create_chunk(
                            current_chunk,
                            page_number,
                            doc_id,
                            chunk_count,
                            chunk_start,
                            chunk_start + len(current_chunk)
                        ))
                        chunk_count += 1
                        
                        # Start new chunk with overlap
                        overlap_text = self._get_overlap(current_chunk)
                        current_chunk = overlap_text + section
                        chunk_start += len(current_chunk) - len(overlap_text)
                    else:
                        current_chunk = section
                else:
                    current_chunk += section
        
        # Add final chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                current_chunk,
                page_number,
                doc_id,
                chunk_count,
                chunk_start,
                chunk_start + len(current_chunk)
            ))
        
        logger.info(f"Created {len(chunks)} chunks from page {page_number}")
        return chunks
    
    def _split_by_separator(self, text: str) -> List[str]:
        """Split text by separator"""
        return [s + self.separator for s in text.split(self.separator) if s.strip()]
    
    def _split_large_section(self, section: str) -> List[str]:
        """Split large section by sentences"""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', section)
        
        chunks = []
        current = ""
        
        for sentence in sentences:
            if len(current) + len(sentence) > self.chunk_size:
                if current:
                    chunks.append(current)
                current = sentence
            else:
                current += " " + sentence if current else sentence
        
        if current:
            chunks.append(current)
            
        return chunks
    
    def _get_overlap(self, text: str) -> str:
        """Get overlap text from end of chunk"""
        if len(text) <= self.chunk_overlap:
            return text
        return text[-self.chunk_overlap:]
    
    def _create_chunk(
        self,
        text: str,
        page_number: int,
        doc_id: str,
        chunk_count: int,
        start_index: int,
        end_index: int
    ) -> TextChunk:
        """Create TextChunk object"""
        chunk_id = f"{doc_id}-p{page_number}-c{chunk_count}"
        
        return TextChunk(
            chunk_id=chunk_id,
            text=text.strip(),
            page_number=page_number,
            start_index=start_index,
            end_index=end_index,
            metadata={
                "doc_id": doc_id,
                "chunk_number": chunk_count,
                "char_count": len(text),
            }
        )
