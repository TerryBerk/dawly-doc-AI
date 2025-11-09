"""
Query processing service for embedding and preprocessing
"""

import logging
import re
from typing import Optional
from dataclasses import dataclass

import numpy as np

from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


@dataclass
class ProcessedQuery:
    """Processed query with embedding and metadata"""
    original_query: str
    cleaned_query: str
    embedding: np.ndarray
    language: str
    expanded_queries: list
    device_id: Optional[str] = None


class QueryProcessor:
    """Process and embed user queries"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.embedding_service = get_embedding_service()
        
        # Common question patterns
        self.question_patterns = {
            'how': r'how\s+(do|to|can|does)',
            'what': r'what\s+(is|are|does)',
            'where': r'where\s+(is|are|do)',
            'when': r'when\s+(do|does|should)',
            'why': r'why\s+(do|does|is)',
            'which': r'which',
        }
    
    def process_query(
        self,
        question: str,
        device_id: Optional[str] = None,
        expand: bool = True
    ) -> ProcessedQuery:
        """
        Process user question
        
        Steps:
        1. Clean and normalize text
        2. Detect language
        3. Generate embedding
        4. Optional query expansion
        
        Args:
            question: User question
            device_id: Optional device filter
            expand: Enable query expansion
            
        Returns:
            ProcessedQuery with embedding and metadata
        """
        self.logger.debug(f"Processing query: {question[:100]}")
        
        # Clean query
        cleaned = self._clean_query(question)
        
        # Detect language (simple heuristic)
        language = self._detect_language(cleaned)
        
        # Generate embedding
        embedding = self.embedding_service.generate_embedding(cleaned)
        
        # Expand query if enabled
        expanded = []
        if expand:
            expanded = self.expand_query(cleaned)
        
        return ProcessedQuery(
            original_query=question,
            cleaned_query=cleaned,
            embedding=embedding,
            language=language,
            expanded_queries=expanded,
            device_id=device_id
        )
    
    def _clean_query(self, query: str) -> str:
        """
        Clean and normalize query text
        
        - Remove extra whitespace
        - Normalize punctuation
        - Lowercase (preserving important capitalization)
        """
        if not query:
            return ""
        
        # Remove extra whitespace
        query = ' '.join(query.split())
        
        # Remove multiple punctuation
        query = re.sub(r'([?!.]){2,}', r'\1', query)
        
        # Ensure question ends with punctuation
        if not query.endswith(('?', '.', '!')):
            # If query starts with question word, add ?
            if any(re.match(pattern, query, re.IGNORECASE) 
                   for pattern in self.question_patterns.values()):
                query += '?'
        
        return query.strip()
    
    def _detect_language(self, text: str) -> str:
        """
        Simple language detection (English/Russian)
        
        More sophisticated detection can use langdetect library
        """
        # Check for Cyrillic characters
        cyrillic_pattern = re.compile('[а-яА-Я]')
        if cyrillic_pattern.search(text):
            return 'ru'
        
        return 'en'
    
    def expand_query(self, question: str) -> list:
        """
        Generate alternative phrasings for better recall
        
        Args:
            question: Original question
            
        Returns:
            List of expanded queries
        """
        expanded = []
        
        # Synonyms and variations
        expansions = {
            'connect': ['hook up', 'link', 'interface', 'attach'],
            'connection': ['port', 'interface', 'jack', 'socket'],
            'midi': ['MIDI', 'Musical Instrument Digital Interface'],
            'audio': ['sound', 'audio output', 'output'],
            'power': ['electricity', 'power supply', 'voltage'],
            'how': ['how to', 'how do I', 'how can I'],
            'setup': ['set up', 'configure', 'initialize'],
            'volume': ['loudness', 'level', 'gain'],
        }
        
        # Create variations by replacing terms
        words = question.lower().split()
        
        for word in words:
            if word in expansions:
                for synonym in expansions[word][:2]:  # Limit to 2 variations per word
                    new_query = question.lower().replace(word, synonym)
                    if new_query != question.lower() and new_query not in expanded:
                        expanded.append(new_query)
        
        # Add without question mark for keyword search
        if '?' in question:
            expanded.append(question.replace('?', ''))
        
        return expanded[:3]  # Limit to 3 expansions
    
    def extract_intent(self, question: str) -> str:
        """
        Extract query intent
        
        Returns intent type: 'how', 'what', 'where', 'specification', 'general'
        """
        question_lower = question.lower()
        
        for intent, pattern in self.question_patterns.items():
            if re.search(pattern, question_lower):
                return intent
        
        # Check for specification queries
        spec_keywords = ['spec', 'specification', 'detail', 'technical', 'feature']
        if any(keyword in question_lower for keyword in spec_keywords):
            return 'specification'
        
        return 'general'
    
    def is_connection_query(self, question: str) -> bool:
        """
        Check if query is about connections
        
        Returns True if query relates to MIDI, Audio, or Power connections
        """
        connection_keywords = [
            'connect', 'connection', 'cable', 'port', 'interface',
            'midi', 'audio', 'power', 'plug', 'jack', 'socket',
            'input', 'output', 'in', 'out', 'link', 'hook up'
        ]
        
        question_lower = question.lower()
        
        return any(keyword in question_lower for keyword in connection_keywords)
    
    def extract_device_mention(self, question: str) -> Optional[str]:
        """
        Try to extract device name mentioned in question
        
        Returns device name if found, None otherwise
        """
        # Common device name patterns
        # e.g., "Digitakt II", "Analog Four", "Octatrack"
        
        # Elektron devices
        elektron_devices = [
            'digitakt', 'digitone', 'octatrack', 'analog four',
            'analog rytm', 'syntakt', 'analog heat'
        ]
        
        question_lower = question.lower()
        
        for device in elektron_devices:
            if device in question_lower:
                return device.title()
        
        return None

