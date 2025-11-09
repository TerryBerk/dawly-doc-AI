"""
Result re-ranking service for improving relevance
"""

import logging
import re
from typing import List
from dataclasses import dataclass

from app.services.search_service import SearchResult

logger = logging.getLogger(__name__)


class Reranker:
    """Re-rank search results for better relevance"""
    
    def __init__(
        self,
        relevance_threshold: float = 0.1,
        boost_factors: dict = None
    ):
        """
        Initialize reranker
        
        Args:
            relevance_threshold: Minimum score threshold
            boost_factors: Score boost factors for different signals
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.relevance_threshold = relevance_threshold
        
        # Default boost factors
        self.boost_factors = boost_factors or {
            'exact_match': 1.5,
            'section_match': 1.2,
            'page_proximity': 1.1,
            'length_penalty': 0.9
        }
    
    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Re-rank search results
        
        Scoring factors:
        - Original search score
        - Query-document similarity
        - Document length
        - Page proximity (nearby pages get boost)
        - Section relevance
        
        Args:
            query: Original query
            results: Search results
            top_k: Number of results to return
            
        Returns:
            Top-k re-ranked results
        """
        if not results:
            return []
        
        self.logger.debug(f"Re-ranking {len(results)} results")
        
        # Calculate relevance scores
        scored_results = []
        
        for result in results:
            # Base score from search
            base_score = result.score
            
            # Apply boosts
            boost = 1.0
            
            # Exact match boost
            if self._has_exact_match(query, result.text):
                boost *= self.boost_factors['exact_match']
            
            # Section relevance boost
            if self._is_section_relevant(query, result.section):
                boost *= self.boost_factors['section_match']
            
            # Length penalty for very short or very long chunks
            length_factor = self._calculate_length_factor(result.text)
            boost *= length_factor
            
            # Calculate final score
            final_score = base_score * boost
            
            # Update result score
            result.score = final_score
            scored_results.append(result)
        
        # Sort by score
        scored_results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply relevance threshold
        filtered_results = [
            r for r in scored_results
            if r.score >= self.relevance_threshold
        ]
        
        # Apply page proximity boost (results from nearby pages)
        if filtered_results:
            filtered_results = self._boost_page_proximity(filtered_results)
        
        # Return top-k
        top_results = filtered_results[:top_k]
        
        self.logger.debug(f"Re-ranked to {len(top_results)} results")
        return top_results
    
    def _has_exact_match(self, query: str, text: str) -> bool:
        """Check if text contains exact query phrase"""
        # Normalize
        query_lower = query.lower().strip('?!.')
        text_lower = text.lower()
        
        # Check for exact phrase match
        if query_lower in text_lower:
            return True
        
        # Check for multi-word match
        query_words = query_lower.split()
        if len(query_words) >= 2:
            # Check if all query words appear in text
            return all(word in text_lower for word in query_words if len(word) > 3)
        
        return False
    
    def _is_section_relevant(self, query: str, section: str) -> bool:
        """Check if section name is relevant to query"""
        if not section:
            return False
        
        # Connection-related queries
        connection_keywords = [
            'connect', 'connection', 'cable', 'port', 'midi', 'audio', 'power'
        ]
        connection_sections = ['connection', 'specifications', 'setup', 'interface']
        
        query_lower = query.lower()
        section_lower = section.lower()
        
        # Check if query is about connections and section is relevant
        if any(keyword in query_lower for keyword in connection_keywords):
            if any(section_keyword in section_lower for section_keyword in connection_sections):
                return True
        
        # Check for section mention in query
        if section_lower in query_lower:
            return True
        
        return False
    
    def _calculate_length_factor(self, text: str) -> float:
        """
        Calculate length penalty/boost
        
        Prefer medium-length chunks (200-800 chars)
        Penalize very short (<100) or very long (>1500) chunks
        """
        length = len(text)
        
        if length < 100:
            return 0.8  # Too short, might lack context
        elif length < 200:
            return 0.9
        elif length <= 800:
            return 1.0  # Ideal length
        elif length <= 1500:
            return 0.95
        else:
            return 0.85  # Too long, might be unfocused
    
    def _boost_page_proximity(
        self,
        results: List[SearchResult],
        proximity_window: int = 2
    ) -> List[SearchResult]:
        """
        Boost results from nearby pages
        
        If top result is from page N, boost results from pages N-2 to N+2
        
        Args:
            results: Search results
            proximity_window: Page range to boost
            
        Returns:
            Results with proximity boost applied
        """
        if not results:
            return results
        
        # Get top result page
        top_page = results[0].page_number
        
        # Boost nearby pages
        boosted_results = []
        for result in results:
            page_diff = abs(result.page_number - top_page)
            
            if page_diff <= proximity_window and page_diff > 0:
                # Apply proximity boost
                boost = self.boost_factors['page_proximity']
                # Diminishing boost for further pages
                boost = boost * (1.0 - (page_diff / (proximity_window + 1)) * 0.3)
                result.score *= boost
            
            boosted_results.append(result)
        
        # Re-sort after boosting
        boosted_results.sort(key=lambda x: x.score, reverse=True)
        
        return boosted_results
    
    def calculate_relevance_score(
        self,
        query: str,
        document: str,
        original_score: float
    ) -> float:
        """
        Calculate final relevance score
        
        Args:
            query: Query text
            document: Document text
            original_score: Original search score
            
        Returns:
            Final relevance score
        """
        # Start with original score
        score = original_score
        
        # Exact match bonus
        if self._has_exact_match(query, document):
            score *= 1.3
        
        # Length factor
        length_factor = self._calculate_length_factor(document)
        score *= length_factor
        
        # Query term coverage
        query_words = set(query.lower().split())
        doc_words = set(document.lower().split())
        
        if query_words:
            coverage = len(query_words & doc_words) / len(query_words)
            score *= (0.8 + coverage * 0.4)  # Scale: 0.8 to 1.2
        
        return score
    
    def remove_duplicates(
        self,
        results: List[SearchResult],
        similarity_threshold: float = 0.9
    ) -> List[SearchResult]:
        """
        Remove duplicate or very similar results
        
        Args:
            results: Search results
            similarity_threshold: Text similarity threshold
            
        Returns:
            Deduplicated results
        """
        if not results:
            return []
        
        unique_results = [results[0]]
        
        for result in results[1:]:
            is_duplicate = False
            
            for unique_result in unique_results:
                # Check text similarity (simple word overlap)
                similarity = self._calculate_text_similarity(
                    result.text,
                    unique_result.text
                )
                
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_results.append(result)
        
        return unique_results
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity using word overlap"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0

