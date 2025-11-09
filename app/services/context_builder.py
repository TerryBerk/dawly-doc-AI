"""
Context building service for LLM
"""

import logging
from typing import List, Optional
import tiktoken

from app.services.search_service import SearchResult

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Build context from search results for LLM"""
    
    def __init__(
        self,
        max_tokens: int = 3000,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize context builder
        
        Args:
            max_tokens: Maximum tokens for context
            encoding_name: Tiktoken encoding
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.max_tokens = max_tokens
        self.encoding = tiktoken.get_encoding(encoding_name)
    
    def build_context(
        self,
        results: List[SearchResult],
        device_id: Optional[str] = None,
        device_name: Optional[str] = None
    ) -> str:
        """
        Build formatted context for LLM
        
        Format:
        ---
        Device: Digitakt II (Elektron)
        Documentation Context:
        
        [Page 42 - MIDI Connections]
        The Digitakt II features 5-pin MIDI IN and MIDI OUT...
        
        [Page 43 - MIDI Configuration]
        To configure MIDI channels, navigate to...
        ---
        
        Args:
            results: Search results
            device_id: Optional device ID
            device_name: Optional device name
            
        Returns:
            Formatted context string
        """
        if not results:
            return "No relevant documentation found."
        
        self.logger.debug(f"Building context from {len(results)} results")
        
        # Start with header
        context_parts = []
        
        # Add device information if available
        if device_name or (results and results[0].device_name):
            device = device_name or results[0].device_name
            manufacturer = results[0].manufacturer if results else ""
            context_parts.append(f"Device: {device}")
            if manufacturer:
                context_parts.append(f"Manufacturer: {manufacturer}")
            context_parts.append("")
        
        context_parts.append("Documentation Context:")
        context_parts.append("")
        
        # Add chunks with citations
        total_tokens = self._count_tokens("\n".join(context_parts))
        
        for result in results:
            # Format chunk with citation
            chunk_text = self._format_chunk(result)
            chunk_tokens = self._count_tokens(chunk_text)
            
            # Check if adding this chunk exceeds limit
            if total_tokens + chunk_tokens > self.max_tokens:
                self.logger.debug(f"Reached token limit at {total_tokens} tokens")
                break
            
            context_parts.append(chunk_text)
            context_parts.append("")  # Empty line between chunks
            total_tokens += chunk_tokens
        
        context = "\n".join(context_parts)
        
        # Truncate if still over limit
        if total_tokens > self.max_tokens:
            context = self.truncate_to_token_limit(context, self.max_tokens)
        
        self.logger.debug(f"Built context: {total_tokens} tokens")
        return context
    
    def _format_chunk(self, result: SearchResult) -> str:
        """
        Format chunk with citation
        
        Format: [Page X - Section] Text...
        """
        # Build citation
        citation_parts = [f"Page {result.page_number}"]
        
        if result.section:
            citation_parts.append(result.section)
        
        citation = " - ".join(citation_parts)
        
        # Format with citation and text
        formatted = f"[{citation}]\n{result.text}"
        
        return formatted
    
    def build_sources(
        self,
        results: List[SearchResult]
    ) -> List[dict]:
        """
        Build source list for response
        
        Args:
            results: Search results
            
        Returns:
            List of source dictionaries
        """
        sources = []
        
        for result in results:
            source = {
                "page": result.page_number,
                "section": result.section,
                "confidence": result.score,
                "excerpt": self._create_excerpt(result.text, max_length=150),
                "device_name": result.device_name,
                "manufacturer": result.manufacturer
            }
            sources.append(source)
        
        return sources
    
    def _create_excerpt(self, text: str, max_length: int = 150) -> str:
        """
        Create text excerpt
        
        Args:
            text: Full text
            max_length: Maximum excerpt length
            
        Returns:
            Truncated excerpt with ellipsis
        """
        if len(text) <= max_length:
            return text
        
        # Try to break at sentence
        excerpt = text[:max_length]
        
        # Find last sentence end
        for delimiter in ['. ', '! ', '? ']:
            last_delim = excerpt.rfind(delimiter)
            if last_delim > max_length * 0.6:  # At least 60% of target length
                return excerpt[:last_delim + 1]
        
        # Break at word boundary
        last_space = excerpt.rfind(' ')
        if last_space > 0:
            excerpt = excerpt[:last_space]
        
        return excerpt + "..."
    
    def truncate_to_token_limit(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to token limit
        
        Args:
            text: Input text
            max_tokens: Maximum tokens
            
        Returns:
            Truncated text
        """
        tokens = self.encoding.encode(text)
        
        if len(tokens) <= max_tokens:
            return text
        
        # Truncate tokens
        truncated_tokens = tokens[:max_tokens]
        
        # Decode back to text
        truncated_text = self.encoding.decode(truncated_tokens)
        
        return truncated_text + "\n\n[Context truncated due to length...]"
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if not text:
            return 0
        return len(self.encoding.encode(text))
    
    def add_device_context(
        self,
        context: str,
        device_metadata: dict
    ) -> str:
        """
        Add device-specific context
        
        Args:
            context: Existing context
            device_metadata: Device metadata dictionary
            
        Returns:
            Context with device info prepended
        """
        device_info_parts = ["Device Information:"]
        
        if device_metadata.get('name'):
            device_info_parts.append(f"Name: {device_metadata['name']}")
        
        if device_metadata.get('manufacturer'):
            device_info_parts.append(f"Manufacturer: {device_metadata['manufacturer']}")
        
        if device_metadata.get('device_type'):
            device_info_parts.append(f"Type: {device_metadata['device_type']}")
        
        if device_metadata.get('connections'):
            device_info_parts.append("\nConnections:")
            for conn in device_metadata['connections']:
                conn_type = conn.get('type', 'Unknown')
                ports_in = conn.get('ports_in', 0)
                ports_out = conn.get('ports_out', 0)
                device_info_parts.append(f"  - {conn_type}: {ports_in} IN, {ports_out} OUT")
        
        device_info = "\n".join(device_info_parts)
        
        return f"{device_info}\n\n{context}"
    
    def format_for_streaming(
        self,
        context: str,
        chunks: int = 10
    ) -> List[str]:
        """
        Split context into chunks for streaming
        
        Args:
            context: Full context
            chunks: Number of chunks
            
        Returns:
            List of context chunks
        """
        if not context:
            return []
        
        # Split by paragraphs
        paragraphs = context.split('\n\n')
        
        # Group paragraphs into chunks
        chunk_size = max(1, len(paragraphs) // chunks)
        
        context_chunks = []
        for i in range(0, len(paragraphs), chunk_size):
            chunk = '\n\n'.join(paragraphs[i:i + chunk_size])
            context_chunks.append(chunk)
        
        return context_chunks

