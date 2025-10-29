"""
Semantic search service using Elasticsearch
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import numpy as np

from app.services.elasticsearch_service import get_elasticsearch_service

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result"""
    chunk_id: str
    text: str
    score: float
    device_id: str
    device_name: str
    manufacturer: str
    page_number: int
    section: Optional[str]
    chunk_index: int
    filename: str


class SearchService:
    """Elasticsearch semantic and hybrid search"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.es_service = get_elasticsearch_service()
    
    async def search(
        self,
        query_embedding: np.ndarray,
        query_text: str,
        device_id: Optional[str] = None,
        k: int = 10,
        use_hybrid: bool = True
    ) -> List[SearchResult]:
        """
        Hybrid search: semantic + keyword
        
        Args:
            query_embedding: Query embedding vector
            query_text: Original query text
            device_id: Optional device filter
            k: Number of results
            use_hybrid: Use both semantic and keyword search
            
        Returns:
            List of search results with scores
        """
        if use_hybrid:
            # Combine semantic and keyword search
            return await self.hybrid_search(
                query_embedding,
                query_text,
                device_id,
                k
            )
        else:
            # Pure semantic search
            return await self.semantic_search(
                query_embedding,
                device_id,
                k
            )
    
    async def semantic_search(
        self,
        query_embedding: np.ndarray,
        device_id: Optional[str] = None,
        k: int = 10
    ) -> List[SearchResult]:
        """
        Pure k-NN vector search
        
        Args:
            query_embedding: Query embedding vector
            device_id: Optional device filter
            k: Number of results
            
        Returns:
            List of search results
        """
        self.logger.debug(f"Semantic search (k={k}, device_id={device_id})")
        
        # Use Elasticsearch service for k-NN search
        es_results = self.es_service.search_by_embedding(
            query_embedding=query_embedding,
            k=k,
            device_id=device_id
        )
        
        # Convert to SearchResult objects
        results = []
        for es_result in es_results:
            result = SearchResult(
                chunk_id=es_result.get('chunk_id', ''),
                text=es_result.get('text', ''),
                score=es_result.get('score', 0.0),
                device_id=es_result.get('device_id', ''),
                device_name=es_result.get('device_name', ''),
                manufacturer=es_result.get('manufacturer', ''),
                page_number=es_result.get('page_number', 0),
                section=es_result.get('section'),
                chunk_index=es_result.get('chunk_index', 0),
                filename=es_result.get('filename', '')
            )
            results.append(result)
        
        self.logger.debug(f"Found {len(results)} results")
        return results
    
    async def hybrid_search(
        self,
        query_embedding: np.ndarray,
        query_text: str,
        device_id: Optional[str] = None,
        k: int = 10,
        semantic_weight: float = 0.7
    ) -> List[SearchResult]:
        """
        Hybrid search combining semantic and keyword search
        
        Args:
            query_embedding: Query embedding vector
            query_text: Original query text
            device_id: Optional device filter
            k: Number of results
            semantic_weight: Weight for semantic score (0-1)
            
        Returns:
            List of search results with combined scores
        """
        self.logger.debug(f"Hybrid search (k={k}, device_id={device_id})")
        
        # Get semantic results
        semantic_results = await self.semantic_search(
            query_embedding,
            device_id,
            k=k * 2  # Get more for merging
        )
        
        # Get keyword results
        keyword_results = await self.keyword_search(
            query_text,
            device_id,
            k=k * 2
        )
        
        # Merge and re-score
        merged = self._merge_results(
            semantic_results,
            keyword_results,
            semantic_weight=semantic_weight
        )
        
        # Return top-k
        return merged[:k]
    
    async def keyword_search(
        self,
        query_text: str,
        device_id: Optional[str] = None,
        k: int = 10
    ) -> List[SearchResult]:
        """
        BM25 keyword search
        
        Args:
            query_text: Query text
            device_id: Optional device filter
            k: Number of results
            
        Returns:
            List of search results
        """
        self.logger.debug(f"Keyword search: {query_text[:50]}")
        
        # Build Elasticsearch query
        query = {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query_text,
                            "fields": ["text^2", "section"],
                            "type": "best_fields"
                        }
                    }
                ]
            }
        }
        
        # Add device filter
        if device_id:
            query["bool"]["filter"] = [
                {"term": {"device_id": device_id}}
            ]
        
        # Execute search
        try:
            response = self.es_service.client.search(
                index=self.es_service.index_name,
                body={
                    "query": query,
                    "size": k
                }
            )
            
            # Convert results
            results = []
            for hit in response['hits']['hits']:
                result = SearchResult(
                    chunk_id=hit['_id'],
                    text=hit['_source'].get('text', ''),
                    score=hit['_score'],
                    device_id=hit['_source'].get('device_id', ''),
                    device_name=hit['_source'].get('device_name', ''),
                    manufacturer=hit['_source'].get('manufacturer', ''),
                    page_number=hit['_source'].get('page_number', 0),
                    section=hit['_source'].get('section'),
                    chunk_index=hit['_source'].get('chunk_index', 0),
                    filename=hit['_source'].get('filename', '')
                )
                results.append(result)
            
            return results
        
        except Exception as e:
            self.logger.error(f"Keyword search failed: {e}")
            return []
    
    def _merge_results(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        semantic_weight: float = 0.7
    ) -> List[SearchResult]:
        """
        Merge semantic and keyword results with combined scoring
        
        Uses Reciprocal Rank Fusion (RRF) for combining rankings
        """
        # Create dict of chunk_id -> combined_score
        chunk_scores = {}
        chunk_objects = {}
        
        # Add semantic results
        for i, result in enumerate(semantic_results):
            rank = i + 1
            # RRF score: 1 / (k + rank), k=60 is common
            rrf_score = 1.0 / (60 + rank)
            chunk_scores[result.chunk_id] = semantic_weight * rrf_score
            chunk_objects[result.chunk_id] = result
        
        # Add keyword results
        keyword_weight = 1.0 - semantic_weight
        for i, result in enumerate(keyword_results):
            rank = i + 1
            rrf_score = 1.0 / (60 + rank)
            
            if result.chunk_id in chunk_scores:
                chunk_scores[result.chunk_id] += keyword_weight * rrf_score
            else:
                chunk_scores[result.chunk_id] = keyword_weight * rrf_score
                chunk_objects[result.chunk_id] = result
        
        # Sort by combined score
        sorted_chunks = sorted(
            chunk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Create merged results
        merged = []
        for chunk_id, score in sorted_chunks:
            result = chunk_objects[chunk_id]
            # Update score to combined score
            result.score = score
            merged.append(result)
        
        return merged
    
    def filter_by_section(
        self,
        results: List[SearchResult],
        section_keywords: List[str]
    ) -> List[SearchResult]:
        """
        Filter results by section keywords
        
        Args:
            results: Search results
            section_keywords: Keywords to match in section name
            
        Returns:
            Filtered results
        """
        if not section_keywords:
            return results
        
        filtered = []
        for result in results:
            if result.section:
                section_lower = result.section.lower()
                if any(keyword.lower() in section_lower for keyword in section_keywords):
                    filtered.append(result)
        
        return filtered if filtered else results  # Return all if none match


# Singleton instance
_search_service = None


def get_search_service() -> SearchService:
    """Get or create search service singleton"""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service

