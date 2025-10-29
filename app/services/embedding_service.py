"""
Embedding generation service using sentence-transformers
"""

import logging
import hashlib
import pickle
from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer
import redis

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate vector embeddings for text chunks"""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        """Singleton pattern to avoid loading model multiple times"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        cache_enabled: bool = True
    ):
        """
        Initialize embedding service
        
        Args:
            model_name: Sentence transformer model name
            cache_enabled: Enable Redis caching
        """
        if self._model is None:
            self.logger = logging.getLogger(self.__class__.__name__)
            self.model_name = model_name
            self.cache_enabled = cache_enabled
            
            # Load model
            self.logger.info(f"Loading embedding model: {model_name}")
            self._model = SentenceTransformer(model_name)
            self.embedding_dim = self._model.get_sentence_embedding_dimension()
            self.logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")
            
            # Setup Redis cache
            if self.cache_enabled:
                try:
                    settings = get_settings()
                    self.redis_client = redis.Redis(
                        host=settings.REDIS_HOST,
                        port=settings.REDIS_PORT,
                        db=settings.REDIS_DB,
                        decode_responses=False  # Binary mode for pickle
                    )
                    self.redis_client.ping()
                    self.logger.info("Redis cache connected")
                except Exception as e:
                    self.logger.warning(f"Redis cache unavailable: {e}")
                    self.cache_enabled = False
                    self.redis_client = None
            else:
                self.redis_client = None
    
    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of text strings
            batch_size: Batch size for processing
            show_progress: Show progress bar
            
        Returns:
            numpy array of embeddings (n_texts, embedding_dim)
        """
        if not texts:
            return np.array([])
        
        self.logger.debug(f"Generating embeddings for {len(texts)} texts")
        
        # Check cache for each text
        embeddings = []
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(texts):
            if self.cache_enabled:
                cached = self._get_from_cache(text)
                if cached is not None:
                    embeddings.append(cached)
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(text)
                    embeddings.append(None)
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
                embeddings.append(None)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            self.logger.debug(f"Generating {len(uncached_texts)} new embeddings")
            new_embeddings = self._model.encode(
                uncached_texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=True  # Normalize for cosine similarity
            )
            
            # Cache new embeddings and insert into result
            for idx, text, embedding in zip(uncached_indices, uncached_texts, new_embeddings):
                if self.cache_enabled:
                    self._save_to_cache(text, embedding)
                embeddings[idx] = embedding
        
        # Convert to numpy array
        embeddings = np.array(embeddings)
        
        self.logger.debug(f"Generated embeddings shape: {embeddings.shape}")
        return embeddings
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for single text
        
        Args:
            text: Text string
            
        Returns:
            numpy array of embedding (embedding_dim,)
        """
        if not text:
            return np.zeros(self.embedding_dim)
        
        # Check cache
        if self.cache_enabled:
            cached = self._get_from_cache(text)
            if cached is not None:
                return cached
        
        # Generate embedding
        embedding = self._model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # Cache
        if self.cache_enabled:
            self._save_to_cache(text, embedding)
        
        return embedding
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text"""
        # Use hash of text as key
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return f"embedding:{self.model_name}:{text_hash}"
    
    def _get_from_cache(self, text: str) -> Optional[np.ndarray]:
        """Get embedding from cache"""
        if not self.redis_client:
            return None
        
        try:
            key = self._get_cache_key(text)
            cached = self.redis_client.get(key)
            
            if cached:
                embedding = pickle.loads(cached)
                return embedding
        except Exception as e:
            self.logger.warning(f"Cache read error: {e}")
        
        return None
    
    def _save_to_cache(self, text: str, embedding: np.ndarray, ttl: int = 86400 * 30):
        """
        Save embedding to cache
        
        Args:
            text: Text string
            embedding: Embedding array
            ttl: Time to live in seconds (default: 30 days)
        """
        if not self.redis_client:
            return
        
        try:
            key = self._get_cache_key(text)
            value = pickle.dumps(embedding)
            self.redis_client.setex(key, ttl, value)
        except Exception as e:
            self.logger.warning(f"Cache write error: {e}")
    
    def clear_cache(self, pattern: Optional[str] = None):
        """
        Clear embedding cache
        
        Args:
            pattern: Optional pattern to match keys (default: all embeddings for this model)
        """
        if not self.redis_client:
            return
        
        try:
            if pattern is None:
                pattern = f"embedding:{self.model_name}:*"
            
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                self.logger.info(f"Cleared {len(keys)} cached embeddings")
        except Exception as e:
            self.logger.error(f"Cache clear error: {e}")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        if not self.redis_client:
            return {"cache_enabled": False}
        
        try:
            pattern = f"embedding:{self.model_name}:*"
            keys = self.redis_client.keys(pattern)
            
            return {
                "cache_enabled": True,
                "cached_embeddings": len(keys),
                "model": self.model_name,
                "embedding_dim": self.embedding_dim
            }
        except Exception as e:
            self.logger.error(f"Cache stats error: {e}")
            return {"cache_enabled": False, "error": str(e)}
    
    def batch_embed_chunks(
        self,
        chunks: List[dict],
        text_field: str = 'text',
        batch_size: int = 32
    ) -> List[dict]:
        """
        Add embeddings to chunk dictionaries
        
        Args:
            chunks: List of chunk dictionaries
            text_field: Field name containing text
            batch_size: Batch size for processing
            
        Returns:
            Chunks with 'embedding' field added
        """
        if not chunks:
            return []
        
        texts = [chunk[text_field] for chunk in chunks]
        embeddings = self.generate_embeddings(texts, batch_size=batch_size)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding.tolist()
        
        return chunks


# Singleton instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service singleton"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

