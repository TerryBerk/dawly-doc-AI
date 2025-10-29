"""
Cache Manager Service - Redis-based caching for query results
"""

from typing import Optional, Dict, Any, List
import json
import hashlib
from datetime import timedelta
import redis.asyncio as redis


class CacheManager:
    """
    Manages caching of query results using Redis
    Reduces latency for frequent queries
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        ttl_seconds: int = 3600,  # 1 hour default
        key_prefix: str = "kag:query:",
    ):
        self.redis_url = redis_url
        self.ttl = ttl_seconds
        self.key_prefix = key_prefix
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection"""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    def _generate_cache_key(
        self,
        query: str,
        device_id: Optional[str] = None,
        top_k: int = 10,
    ) -> str:
        """
        Generate unique cache key for query
        
        Args:
            query: Search query
            device_id: Optional device filter
            top_k: Number of results
            
        Returns:
            Cache key string
        """
        # Create a unique string from parameters
        cache_params = f"{query}|{device_id or 'all'}|{top_k}"
        
        # Hash for consistent key length
        cache_hash = hashlib.md5(cache_params.encode()).hexdigest()
        
        return f"{self.key_prefix}{cache_hash}"
    
    async def get(
        self,
        query: str,
        device_id: Optional[str] = None,
        top_k: int = 10,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached results for query
        
        Returns:
            Cached results if found, None otherwise
        """
        if not self.redis_client:
            await self.connect()
        
        cache_key = self._generate_cache_key(query, device_id, top_k)
        
        try:
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                # Parse JSON and return
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        query: str,
        results: List[Dict[str, Any]],
        device_id: Optional[str] = None,
        top_k: int = 10,
        ttl: Optional[int] = None,
    ):
        """
        Cache query results
        
        Args:
            query: Search query
            results: Query results to cache
            device_id: Optional device filter
            top_k: Number of results
            ttl: Optional custom TTL in seconds
        """
        if not self.redis_client:
            await self.connect()
        
        cache_key = self._generate_cache_key(query, device_id, top_k)
        ttl_seconds = ttl or self.ttl
        
        try:
            # Serialize results to JSON
            cached_data = json.dumps(results)
            
            # Store with TTL
            await self.redis_client.setex(
                cache_key,
                ttl_seconds,
                cached_data
            )
            
        except Exception as e:
            print(f"Cache set error: {e}")
    
    async def delete(
        self,
        query: str,
        device_id: Optional[str] = None,
        top_k: int = 10,
    ):
        """Delete cached results for query"""
        if not self.redis_client:
            await self.connect()
        
        cache_key = self._generate_cache_key(query, device_id, top_k)
        
        try:
            await self.redis_client.delete(cache_key)
        except Exception as e:
            print(f"Cache delete error: {e}")
    
    async def clear_all(self):
        """Clear all cached queries"""
        if not self.redis_client:
            await self.connect()
        
        try:
            # Find all keys with our prefix
            cursor = 0
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor,
                    match=f"{self.key_prefix}*",
                    count=100
                )
                
                if keys:
                    await self.redis_client.delete(*keys)
                
                if cursor == 0:
                    break
                    
        except Exception as e:
            print(f"Cache clear error: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis_client:
            await self.connect()
        
        try:
            info = await self.redis_client.info("stats")
            
            # Count our cached keys
            cursor = 0
            key_count = 0
            
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor,
                    match=f"{self.key_prefix}*",
                    count=100
                )
                key_count += len(keys)
                
                if cursor == 0:
                    break
            
            return {
                'total_cached_queries': key_count,
                'ttl_seconds': self.ttl,
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': (
                    info.get('keyspace_hits', 0) / 
                    (info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1))
                ) * 100,
            }
            
        except Exception as e:
            print(f"Cache stats error: {e}")
            return {}

