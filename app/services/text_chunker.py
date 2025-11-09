"""
Text chunking service with semantic overlap
"""

import logging
import re
from typing import List, Optional
from dataclasses import dataclass

import tiktoken

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Single text chunk with metadata"""
    chunk_id: str
    text: str
    page_number: int
    section: Optional[str]
    token_count: int
    char_count: int
    chunk_index: int


class TextChunker:
    """Split text into semantic chunks with overlap"""
    
    def __init__(
        self, 
        chunk_size: int = 512,
        overlap: int = 128,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize text chunker
        
        Args:
            chunk_size: Target tokens per chunk (default: 512)
            overlap: Overlap tokens between chunks (default: 128)
            encoding_name: Tiktoken encoding (default: cl100k_base for GPT-4)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def chunk_text(
        self,
        text: str,
        page_number: int = 1,
        section: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> List[TextChunk]:
        """
        Chunk text with overlap for better context
        
        Args:
            text: Input text
            page_number: Source page number
            section: Optional section name
            document_id: Optional document identifier
            
        Returns:
            List of TextChunk objects
        """
        if not text or not text.strip():
            return []
        
        # Split into sentences for semantic chunking
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_tokens = len(self.encoding.encode(sentence))
            
            # If single sentence exceeds chunk_size, split it
            if sentence_tokens > self.chunk_size:
                # Save current chunk if exists
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    chunks.append(self._create_chunk(
                        chunk_text, 
                        page_number, 
                        section, 
                        chunk_index,
                        document_id
                    ))
                    chunk_index += 1
                
                # Split long sentence by words
                sub_chunks = self._split_long_sentence(sentence, page_number, section, chunk_index, document_id)
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
                
                current_chunk = []
                current_tokens = 0
                continue
            
            # Check if adding sentence exceeds chunk_size
            if current_tokens + sentence_tokens > self.chunk_size:
                # Save current chunk
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    chunks.append(self._create_chunk(
                        chunk_text, 
                        page_number, 
                        section, 
                        chunk_index,
                        document_id
                    ))
                    chunk_index += 1
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk, self.overlap)
                current_chunk = overlap_sentences
                current_tokens = self._count_tokens(" ".join(current_chunk))
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(self._create_chunk(
                chunk_text, 
                page_number, 
                section, 
                chunk_index,
                document_id
            ))
        
        self.logger.debug(f"Created {len(chunks)} chunks from page {page_number}")
        return chunks
    
    def chunk_document(
        self,
        pages: List[dict],
        document_id: str
    ) -> List[TextChunk]:
        """
        Chunk entire document (all pages)
        
        Args:
            pages: List of page dictionaries with 'text' and 'page_number'
            document_id: Document identifier
            
        Returns:
            List of all chunks from all pages
        """
        all_chunks = []
        
        for page in pages:
            text = page.get('text', '')
            page_number = page.get('page_number', 1)
            section = page.get('section')
            
            chunks = self.chunk_text(
                text,
                page_number=page_number,
                section=section,
                document_id=document_id
            )
            all_chunks.extend(chunks)
        
        self.logger.info(f"Created {len(all_chunks)} chunks from {len(pages)} pages")
        return all_chunks
    
    def _create_chunk(
        self,
        text: str,
        page_number: int,
        section: Optional[str],
        chunk_index: int,
        document_id: Optional[str] = None
    ) -> TextChunk:
        """Create a TextChunk object"""
        token_count = self._count_tokens(text)
        
        # Generate chunk ID
        if document_id:
            chunk_id = f"{document_id}-page{page_number}-chunk{chunk_index}"
        else:
            chunk_id = f"page{page_number}-chunk{chunk_index}"
        
        return TextChunk(
            chunk_id=chunk_id,
            text=text,
            page_number=page_number,
            section=section,
            token_count=token_count,
            char_count=len(text),
            chunk_index=chunk_index
        )
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences
        
        Handles:
        - Standard sentence endings (. ! ?)
        - Abbreviations (Dr., Mr., etc.)
        - Decimal numbers
        """
        # Basic sentence splitting pattern
        # Matches . ! ? followed by space and capital letter
        pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+(?=[A-Z])'
        
        sentences = re.split(pattern, text)
        
        # Clean and filter
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _split_long_sentence(
        self,
        sentence: str,
        page_number: int,
        section: Optional[str],
        chunk_index: int,
        document_id: Optional[str]
    ) -> List[TextChunk]:
        """Split a sentence that's longer than chunk_size by words"""
        words = sentence.split()
        chunks = []
        current_words = []
        current_tokens = 0
        sub_index = 0
        
        for word in words:
            word_tokens = len(self.encoding.encode(word))
            
            if current_tokens + word_tokens > self.chunk_size:
                if current_words:
                    chunk_text = " ".join(current_words)
                    chunks.append(self._create_chunk(
                        chunk_text,
                        page_number,
                        section,
                        chunk_index + sub_index,
                        document_id
                    ))
                    sub_index += 1
                
                # Start new with overlap
                overlap_words = current_words[-(self.overlap // 4):] if len(current_words) > self.overlap // 4 else []
                current_words = overlap_words
                current_tokens = self._count_tokens(" ".join(current_words))
            
            current_words.append(word)
            current_tokens += word_tokens
        
        if current_words:
            chunk_text = " ".join(current_words)
            chunks.append(self._create_chunk(
                chunk_text,
                page_number,
                section,
                chunk_index + sub_index,
                document_id
            ))
        
        return chunks
    
    def _get_overlap_sentences(self, sentences: List[str], overlap_tokens: int) -> List[str]:
        """Get sentences for overlap from end of chunk"""
        if not sentences:
            return []
        
        overlap_sentences = []
        total_tokens = 0
        
        # Work backwards from end
        for sentence in reversed(sentences):
            sentence_tokens = self._count_tokens(sentence)
            
            if total_tokens + sentence_tokens > overlap_tokens:
                break
            
            overlap_sentences.insert(0, sentence)
            total_tokens += sentence_tokens
        
        return overlap_sentences
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if not text:
            return 0
        return len(self.encoding.encode(text))
    
    def estimate_chunk_count(self, text: str) -> int:
        """
        Estimate number of chunks that will be created
        
        Args:
            text: Input text
            
        Returns:
            Estimated chunk count
        """
        if not text:
            return 0
        
        total_tokens = self._count_tokens(text)
        effective_chunk_size = self.chunk_size - self.overlap
        
        if effective_chunk_size <= 0:
            return 1
        
        return max(1, (total_tokens + effective_chunk_size - 1) // effective_chunk_size)

