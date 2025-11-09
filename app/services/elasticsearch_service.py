"""
Elasticsearch service for document indexing and search
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import NotFoundError, RequestError
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)


class ElasticsearchService:
    """Manage Elasticsearch indexing and search"""
    
    def __init__(self):
        """Initialize Elasticsearch client"""
        self.logger = logging.getLogger(self.__class__.__name__)
        settings = get_settings()
        
        # Initialize Elasticsearch client
        self.client = Elasticsearch(
            [f"{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"],
            basic_auth=(settings.ELASTICSEARCH_USER, settings.ELASTICSEARCH_PASSWORD)
            if settings.ELASTICSEARCH_USER else None,
            verify_certs=False,
            request_timeout=30
        )
        
        # Test connection
        try:
            info = self.client.info()
            self.logger.info(f"Connected to Elasticsearch {info['version']['number']}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise
        
        self.index_name = "device_docs"
        self.embedding_dim = 384  # for all-MiniLM-L6-v2
    
    def create_index(self, index_name: Optional[str] = None) -> bool:
        """
        Create index with dense_vector mapping
        
        Args:
            index_name: Index name (default: self.index_name)
            
        Returns:
            True if created, False if already exists
        """
        index_name = index_name or self.index_name
        
        # Check if index exists
        if self.client.indices.exists(index=index_name):
            self.logger.info(f"Index '{index_name}' already exists")
            return False
        
        # Index mapping
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index": {
                    "similarity": {
                        "default": {
                            "type": "BM25"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "chunk_id": {
                        "type": "keyword"
                    },
                    "text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "embedding": {
                        "type": "dense_vector",
                        "dims": self.embedding_dim,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "device_id": {
                        "type": "keyword"
                    },
                    "device_name": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "manufacturer": {
                        "type": "keyword"
                    },
                    "page_number": {
                        "type": "integer"
                    },
                    "section": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "chunk_index": {
                        "type": "integer"
                    },
                    "token_count": {
                        "type": "integer"
                    },
                    "char_count": {
                        "type": "integer"
                    },
                    "doc_id": {
                        "type": "keyword"
                    },
                    "filename": {
                        "type": "keyword"
                    },
                    "indexed_at": {
                        "type": "date"
                    }
                }
            }
        }
        
        # Create index
        try:
            self.client.indices.create(index=index_name, body=mapping)
            self.logger.info(f"Created index '{index_name}'")
            return True
        except RequestError as e:
            self.logger.error(f"Failed to create index: {e}")
            raise
    
    def delete_index(self, index_name: Optional[str] = None) -> bool:
        """
        Delete index
        
        Args:
            index_name: Index name (default: self.index_name)
            
        Returns:
            True if deleted
        """
        index_name = index_name or self.index_name
        
        try:
            if self.client.indices.exists(index=index_name):
                self.client.indices.delete(index=index_name)
                self.logger.info(f"Deleted index '{index_name}'")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete index: {e}")
            raise
    
    def index_chunk(
        self,
        chunk: Dict[str, Any],
        index_name: Optional[str] = None
    ) -> str:
        """
        Index single chunk
        
        Args:
            chunk: Chunk dictionary with text, embedding, metadata
            index_name: Index name (default: self.index_name)
            
        Returns:
            Document ID
        """
        index_name = index_name or self.index_name
        
        # Ensure index exists
        if not self.client.indices.exists(index=index_name):
            self.create_index(index_name)
        
        # Prepare document
        doc = {
            "chunk_id": chunk.get("chunk_id"),
            "text": chunk.get("text"),
            "embedding": chunk.get("embedding"),
            "device_id": chunk.get("device_id"),
            "device_name": chunk.get("device_name"),
            "manufacturer": chunk.get("manufacturer"),
            "page_number": chunk.get("page_number"),
            "section": chunk.get("section"),
            "chunk_index": chunk.get("chunk_index"),
            "token_count": chunk.get("token_count"),
            "char_count": chunk.get("char_count"),
            "doc_id": chunk.get("doc_id"),
            "filename": chunk.get("filename"),
            "indexed_at": datetime.utcnow().isoformat()
        }
        
        # Index document
        result = self.client.index(
            index=index_name,
            id=chunk.get("chunk_id"),
            document=doc
        )
        
        return result['_id']
    
    def bulk_index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        index_name: Optional[str] = None,
        chunk_size: int = 500
    ) -> Dict[str, int]:
        """
        Bulk index chunks
        
        Args:
            chunks: List of chunk dictionaries
            index_name: Index name (default: self.index_name)
            chunk_size: Number of documents per bulk request
            
        Returns:
            Dictionary with success and error counts
        """
        index_name = index_name or self.index_name
        
        # Ensure index exists
        if not self.client.indices.exists(index=index_name):
            self.create_index(index_name)
        
        # Prepare bulk actions
        actions = []
        for chunk in chunks:
            action = {
                "_index": index_name,
                "_id": chunk.get("chunk_id"),
                "_source": {
                    "chunk_id": chunk.get("chunk_id"),
                    "text": chunk.get("text"),
                    "embedding": chunk.get("embedding"),
                    "device_id": chunk.get("device_id"),
                    "device_name": chunk.get("device_name"),
                    "manufacturer": chunk.get("manufacturer"),
                    "page_number": chunk.get("page_number"),
                    "section": chunk.get("section"),
                    "chunk_index": chunk.get("chunk_index"),
                    "token_count": chunk.get("token_count"),
                    "char_count": chunk.get("char_count"),
                    "doc_id": chunk.get("doc_id"),
                    "filename": chunk.get("filename"),
                    "indexed_at": datetime.utcnow().isoformat()
                }
            }
            actions.append(action)
        
        # Bulk index
        success_count = 0
        error_count = 0
        
        try:
            success, errors = helpers.bulk(
                self.client,
                actions,
                chunk_size=chunk_size,
                raise_on_error=False
            )
            success_count = success
            
            if errors:
                error_count = len(errors)
                self.logger.warning(f"Bulk indexing had {error_count} errors")
                for error in errors[:5]:  # Log first 5 errors
                    self.logger.error(f"Indexing error: {error}")
        
        except Exception as e:
            self.logger.error(f"Bulk indexing failed: {e}")
            raise
        
        self.logger.info(f"Indexed {success_count} chunks, {error_count} errors")
        
        return {
            "success": success_count,
            "errors": error_count,
            "total": len(chunks)
        }
    
    def search_by_embedding(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        device_id: Optional[str] = None,
        index_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        k-NN vector search
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results
            device_id: Optional device filter
            index_name: Index name (default: self.index_name)
            
        Returns:
            List of search results with scores
        """
        index_name = index_name or self.index_name
        
        # Convert to list if numpy array
        if isinstance(query_embedding, np.ndarray):
            query_embedding = query_embedding.tolist()
        
        # Build query
        knn_query = {
            "field": "embedding",
            "query_vector": query_embedding,
            "k": k,
            "num_candidates": k * 10  # Search more candidates for better results
        }
        
        # Add filter if device_id provided
        query_body = {"knn": knn_query}
        
        if device_id:
            query_body["query"] = {
                "term": {"device_id": device_id}
            }
        
        # Execute search
        try:
            response = self.client.search(
                index=index_name,
                body=query_body,
                size=k
            )
            
            # Format results
            results = []
            for hit in response['hits']['hits']:
                result = {
                    "chunk_id": hit['_id'],
                    "score": hit['_score'],
                    **hit['_source']
                }
                results.append(result)
            
            return results
        
        except NotFoundError:
            self.logger.warning(f"Index '{index_name}' not found")
            return []
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            raise
    
    def delete_by_device(self, device_id: str, index_name: Optional[str] = None):
        """
        Delete all chunks for a device
        
        Args:
            device_id: Device ID
            index_name: Index name (default: self.index_name)
        """
        index_name = index_name or self.index_name
        
        try:
            result = self.client.delete_by_query(
                index=index_name,
                body={
                    "query": {
                        "term": {"device_id": device_id}
                    }
                }
            )
            deleted = result.get('deleted', 0)
            self.logger.info(f"Deleted {deleted} chunks for device {device_id}")
            return deleted
        except Exception as e:
            self.logger.error(f"Delete by device failed: {e}")
            raise
    
    def get_index_stats(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get index statistics
        
        Args:
            index_name: Index name (default: self.index_name)
            
        Returns:
            Dictionary with index stats
        """
        index_name = index_name or self.index_name
        
        try:
            if not self.client.indices.exists(index=index_name):
                return {"exists": False}
            
            stats = self.client.indices.stats(index=index_name)
            count = self.client.count(index=index_name)
            
            return {
                "exists": True,
                "doc_count": count['count'],
                "size_in_bytes": stats['_all']['total']['store']['size_in_bytes'],
                "index_name": index_name
            }
        except Exception as e:
            self.logger.error(f"Failed to get index stats: {e}")
            return {"exists": False, "error": str(e)}


# Singleton instance
_elasticsearch_service = None


def get_elasticsearch_service() -> ElasticsearchService:
    """Get or create Elasticsearch service singleton"""
    global _elasticsearch_service
    if _elasticsearch_service is None:
        _elasticsearch_service = ElasticsearchService()
    return _elasticsearch_service

