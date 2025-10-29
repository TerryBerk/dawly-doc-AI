"""
Confidence scoring service for answer quality assessment
"""

import logging
from typing import List
import numpy as np

from app.services.search_service import SearchResult

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Calculate confidence scores for answers"""
    
    def __init__(
        self,
        high_threshold: float = 0.7,
        medium_threshold: float = 0.4
    ):
        """
        Initialize confidence scorer
        
        Args:
            high_threshold: Threshold for high confidence
            medium_threshold: Threshold for medium confidence
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
    
    def calculate_confidence(
        self,
        results: List[SearchResult],
        reranked_results: List[SearchResult],
        context: str,
        query: str = ""
    ) -> float:
        """
        Calculate overall confidence (0.0 - 1.0)
        
        Factors:
        - Average search score
        - Number of results above threshold
        - Score distribution (variance)
        - Context completeness
        - Top result score
        
        Args:
            results: Original search results
            reranked_results: Re-ranked results
            context: Built context string
            query: Original query
            
        Returns:
            Confidence score (0.0 - 1.0)
        """
        if not reranked_results:
            return 0.0
        
        self.logger.debug("Calculating confidence score")
        
        # Factor 1: Top result score (40% weight)
        top_score = reranked_results[0].score
        top_score_factor = min(top_score, 1.0)
        
        # Factor 2: Average of top-3 scores (30% weight)
        top_3_scores = [r.score for r in reranked_results[:3]]
        avg_top_3 = np.mean(top_3_scores) if top_3_scores else 0.0
        avg_score_factor = min(avg_top_3, 1.0)
        
        # Factor 3: Number of good results (15% weight)
        good_results = [r for r in reranked_results if r.score > 0.3]
        result_count_factor = min(len(good_results) / 5.0, 1.0)  # Ideal: 5+ results
        
        # Factor 4: Score consistency (10% weight)
        consistency_factor = self._calculate_consistency(reranked_results)
        
        # Factor 5: Context quality (5% weight)
        context_factor = self._calculate_context_quality(context)
        
        # Weighted combination
        confidence = (
            top_score_factor * 0.40 +
            avg_score_factor * 0.30 +
            result_count_factor * 0.15 +
            consistency_factor * 0.10 +
            context_factor * 0.05
        )
        
        # Ensure in range [0, 1]
        confidence = max(0.0, min(1.0, confidence))
        
        self.logger.debug(f"Confidence: {confidence:.3f} (level: {self.get_confidence_level(confidence)})")
        
        return confidence
    
    def _calculate_consistency(self, results: List[SearchResult]) -> float:
        """
        Calculate score consistency
        
        More consistent scores (lower variance) = higher confidence
        """
        if len(results) < 2:
            return 1.0
        
        scores = [r.score for r in results[:5]]  # Top 5
        
        if not scores:
            return 0.0
        
        # Calculate coefficient of variation (std / mean)
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        
        if mean_score == 0:
            return 0.0
        
        cv = std_score / mean_score
        
        # Lower CV = higher consistency
        # CV typically ranges from 0 to 1 for scores
        consistency = max(0.0, 1.0 - cv)
        
        return consistency
    
    def _calculate_context_quality(self, context: str) -> float:
        """
        Assess context quality
        
        Factors:
        - Length (not too short, not too long)
        - Diversity (multiple sources)
        - Completeness
        """
        if not context:
            return 0.0
        
        context_length = len(context)
        
        # Ideal length: 500-2000 chars
        if context_length < 200:
            length_factor = context_length / 200.0
        elif context_length <= 2000:
            length_factor = 1.0
        else:
            length_factor = max(0.7, 2000.0 / context_length)
        
        # Check for multiple sources (by counting [Page X] citations)
        page_citations = context.count('[Page ')
        source_diversity = min(page_citations / 3.0, 1.0)  # Ideal: 3+ sources
        
        # Combined quality
        quality = (length_factor * 0.6 + source_diversity * 0.4)
        
        return quality
    
    def get_confidence_level(self, score: float) -> str:
        """
        Convert confidence score to category
        
        Args:
            score: Confidence score (0.0 - 1.0)
            
        Returns:
            Category: 'high', 'medium', 'low'
        """
        if score >= self.high_threshold:
            return "high"
        elif score >= self.medium_threshold:
            return "medium"
        else:
            return "low"
    
    def should_answer(self, confidence: float, min_confidence: float = 0.3) -> bool:
        """
        Determine if confidence is sufficient to answer
        
        Args:
            confidence: Confidence score
            min_confidence: Minimum required confidence
            
        Returns:
            True if should answer, False otherwise
        """
        return confidence >= min_confidence
    
    def get_confidence_message(self, confidence: float) -> str:
        """
        Get user-friendly confidence message
        
        Args:
            confidence: Confidence score
            
        Returns:
            Message describing confidence level
        """
        level = self.get_confidence_level(confidence)
        
        messages = {
            "high": "I'm confident this answer is accurate based on the documentation.",
            "medium": "This answer is based on the documentation, but please verify important details.",
            "low": "I found limited information. You may want to check the full manual for details."
        }
        
        return messages.get(level, "")
    
    def calculate_source_confidence(
        self,
        result: SearchResult,
        query: str = ""
    ) -> float:
        """
        Calculate confidence for individual source
        
        Args:
            result: Search result
            query: Original query
            
        Returns:
            Confidence score for this source
        """
        # Base score from search
        confidence = result.score
        
        # Boost for exact matches
        if query and query.lower() in result.text.lower():
            confidence *= 1.2
        
        # Boost for section relevance
        if result.section and any(keyword in result.section.lower() 
                                  for keyword in ['specification', 'connection', 'setup']):
            confidence *= 1.1
        
        # Cap at 1.0
        confidence = min(confidence, 1.0)
        
        return confidence
    
    def aggregate_confidences(self, confidences: List[float]) -> float:
        """
        Aggregate multiple confidence scores
        
        Uses weighted average with exponential decay
        
        Args:
            confidences: List of confidence scores
            
        Returns:
            Aggregated confidence
        """
        if not confidences:
            return 0.0
        
        # Weight first results more heavily
        weights = [0.5 ** i for i in range(len(confidences))]
        weighted_sum = sum(c * w for c, w in zip(confidences, weights))
        weight_sum = sum(weights)
        
        if weight_sum == 0:
            return 0.0
        
        return weighted_sum / weight_sum

