"""
Hybrid Search Service - Combines Semantic and Keyword Search
Uses Reciprocal Rank Fusion (RRF) to merge results
"""

from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
import numpy as np
from .embedder import EmbedderService
from .elasticsearch_service import ElasticsearchService


class HybridSearchService:
    """
    Combines semantic search (k-NN) with keyword search (BM25)
    using Reciprocal Rank Fusion for better results
    """
    
    def __init__(
        self,
        embedder_service: EmbedderService,
        es_service: ElasticsearchService,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
        k: int = 60,  # RRF constant
    ):
        self.embedder = embedder_service
        self.es = es_service
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        self.k = k
        
    async def search(
        self,
        query: str,
        device_id: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword approaches
        
        Args:
            query: Search query
            device_id: Optional device ID to filter results
            top_k: Number of results to return
            
        Returns:
            List of search results with RRF scores
        """
        # 1. Semantic search (k-NN with embeddings)
        semantic_results = await self._semantic_search(
            query, device_id, top_k=top_k * 2
        )
        
        # 2. Keyword search (BM25)
        keyword_results = await self._keyword_search(
            query, device_id, top_k=top_k * 2
        )
        
        # 3. Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(
            semantic_results, keyword_results
        )
        
        # 4. Sort by RRF score and return top_k
        fused_results.sort(key=lambda x: x['rrf_score'], reverse=True)
        
        return fused_results[:top_k]
    
    async def _semantic_search(
        self,
        query: str,
        device_id: Optional[str] = None,
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using embeddings"""
        # Generate query embedding
        query_embedding = self.embedder.embed_text(query)
        
        # Build Elasticsearch query
        es_query = {
            "size": top_k,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": query_embedding}
                    }
                }
            }
        }
        
        # Add device filter if provided
        if device_id:
            es_query["query"]["script_score"]["query"] = {
                "term": {"device_id": device_id}
            }
        
        # Execute search
        response = await self.es.search(
            index="documents",
            body=es_query
        )
        
        # Format results
        results = []
        for idx, hit in enumerate(response['hits']['hits']):
            results.append({
                'id': hit['_id'],
                'text': hit['_source']['text'],
                'page': hit['_source'].get('page', 0),
                'section': hit['_source'].get('section'),
                'device_id': hit['_source'].get('device_id'),
                'semantic_score': hit['_score'],
                'semantic_rank': idx + 1,
            })
        
        return results
    
    async def _keyword_search(
        self,
        query: str,
        device_id: Optional[str] = None,
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """Perform keyword search using BM25"""
        # Build Elasticsearch BM25 query
        es_query = {
            "size": top_k,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["text^2", "section"],
                                "type": "best_fields",
                                "operator": "or",
                                "fuzziness": "AUTO",
                            }
                        }
                    ]
                }
            }
        }
        
        # Add device filter if provided
        if device_id:
            es_query["query"]["bool"]["filter"] = [
                {"term": {"device_id": device_id}}
            ]
        
        # Execute search
        response = await self.es.search(
            index="documents",
            body=es_query
        )
        
        # Format results
        results = []
        for idx, hit in enumerate(response['hits']['hits']):
            results.append({
                'id': hit['_id'],
                'text': hit['_source']['text'],
                'page': hit['_source'].get('page', 0),
                'section': hit['_source'].get('section'),
                'device_id': hit['_source'].get('device_id'),
                'keyword_score': hit['_score'],
                'keyword_rank': idx + 1,
            })
        
        return results
    
    def _reciprocal_rank_fusion(
        self,
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Merge results using Reciprocal Rank Fusion (RRF)
        
        RRF score = sum(1 / (k + rank)) for each result list
        where k is a constant (typically 60)
        """
        # Create a dictionary to store merged results
        merged = {}
        
        # Process semantic results
        for result in semantic_results:
            doc_id = result['id']
            rrf_score = self.semantic_weight / (self.k + result['semantic_rank'])
            
            merged[doc_id] = {
                **result,
                'rrf_score': rrf_score,
                'in_semantic': True,
                'in_keyword': False,
            }
        
        # Process keyword results
        for result in keyword_results:
            doc_id = result['id']
            rrf_score = self.keyword_weight / (self.k + result['keyword_rank'])
            
            if doc_id in merged:
                # Document appears in both - combine scores
                merged[doc_id]['rrf_score'] += rrf_score
                merged[doc_id]['in_keyword'] = True
                merged[doc_id]['keyword_score'] = result['keyword_score']
                merged[doc_id]['keyword_rank'] = result['keyword_rank']
            else:
                # Document only in keyword results
                merged[doc_id] = {
                    **result,
                    'rrf_score': rrf_score,
                    'in_semantic': False,
                    'in_keyword': True,
                }
        
        return list(merged.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about search performance"""
        return {
            'semantic_weight': self.semantic_weight,
            'keyword_weight': self.keyword_weight,
            'rrf_constant': self.k,
        }

