"""
In-memory cache for customer preferences to reduce OpenSearch query latency.

This module provides a TTL-based cache that stores customer memory data,
reducing the need for repeated OpenSearch queries for the same customer
within a short time window.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import threading


class MemoryCache:
    """Thread-safe TTL cache for customer preferences."""

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize the memory cache.

        Args:
            ttl_seconds: Time-to-live for cached entries in seconds (default: 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, customer_id: str) -> Optional[str]:
        """
        Retrieve customer memory from cache if available and not expired.

        Args:
            customer_id: The customer ID to lookup

        Returns:
            Cached memory string if available and fresh, None otherwise
        """
        with self._lock:
            if customer_id not in self._cache:
                self._misses += 1
                return None

            cached_data, timestamp = self._cache[customer_id]

            # Check if cache entry has expired
            if datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds):
                # Remove expired entry
                del self._cache[customer_id]
                self._misses += 1
                return None

            self._hits += 1
            return cached_data

    def set(self, customer_id: str, memory_data: str) -> None:
        """
        Store customer memory in cache with current timestamp.

        Args:
            customer_id: The customer ID
            memory_data: The memory data to cache
        """
        with self._lock:
            self._cache[customer_id] = (memory_data, datetime.now())

    def invalidate(self, customer_id: str) -> None:
        """
        Remove a customer's memory from cache.

        Args:
            customer_id: The customer ID to invalidate
        """
        with self._lock:
            if customer_id in self._cache:
                del self._cache[customer_id]

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache hit rate and other metrics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total_requests,
                "hit_rate_percent": round(hit_rate, 2),
                "cache_size": len(self._cache),
                "ttl_seconds": self.ttl_seconds
            }

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        with self._lock:
            current_time = datetime.now()
            expired_keys = [
                key for key, (_, timestamp) in self._cache.items()
                if current_time - timestamp > timedelta(seconds=self.ttl_seconds)
            ]

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)


# Global cache instance
_customer_memory_cache = MemoryCache(ttl_seconds=300)  # 5 minutes default


def get_customer_memory_cache() -> MemoryCache:
    """Get the global customer memory cache instance."""
    return _customer_memory_cache
