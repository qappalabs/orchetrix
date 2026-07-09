"""
Unified Cache System
Provides a bounded, thread-safe in-memory cache backed by cachetools.TTLCache.
Each resource type gets its own TTLCache with automatic TTL expiry and LRU eviction.
"""

import logging
import threading
from typing import Dict, Any, Optional

from cachetools import TTLCache


class UnifiedCache:
    """Thread-safe, bounded in-memory cache system.

    Storage is organized hierarchically: resource_type -> cache_key -> data.
    Each resource_type bucket is a TTLCache with automatic expiry and LRU eviction.
    All operations are protected by a reentrant lock.
    """

    def __init__(self, default_ttl: int = 300, default_maxsize: int = 256):
        self._buckets: Dict[str, TTLCache] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl        # 5 minutes
        self._default_maxsize = default_maxsize  # per resource type

    def _get_bucket(self, resource_type: str) -> TTLCache:
        """Get or create the TTLCache bucket for a resource type. Caller must hold _lock."""
        if resource_type not in self._buckets:
            self._buckets[resource_type] = TTLCache(
                maxsize=self._default_maxsize, ttl=self._default_ttl
            )
        return self._buckets[resource_type]

    def cache_resources(self, resource_type: str, cache_key: str, data: Any) -> None:
        """Cache data. TTLCache handles expiry timestamps and LRU eviction automatically."""
        with self._lock:
            bucket = self._get_bucket(resource_type)
            bucket[cache_key] = data
        logging.debug(f"Cached {resource_type}:{cache_key}")

    def get_cached_resources(self, resource_type: str, cache_key: str) -> Optional[Any]:
        """Get cached data if present and not expired."""
        with self._lock:
            bucket = self._buckets.get(resource_type)
            if bucket is not None:
                return bucket.get(cache_key)
        return None

    def clear_resource_cache(self, resource_type: str, cache_key: str) -> None:
        """Clear a specific cache entry."""
        with self._lock:
            bucket = self._buckets.get(resource_type)
            if bucket is not None:
                bucket.pop(cache_key, None)
        logging.debug(f"Cleared cache {resource_type}:{cache_key}")

    def optimize_caches(self) -> None:
        """Proactively sweep expired entries from all buckets.

        Called by external timers (cluster_connector every 5 min,
        resource_loader every 1 min). Without this, TTLCache only
        removes expired items lazily on mutation.
        """
        total_expired = 0
        with self._lock:
            for resource_type, bucket in self._buckets.items():
                expired = bucket.expire()
                total_expired += len(expired)

        if total_expired:
            logging.debug(f"Cleaned up {total_expired} expired cache entries")

    def clear_empty_entries(self) -> int:
        """Clear cache entries that never loaded (None values only).

        Called on startup or theme change to remove stale data. Empty
        collections (empty list/dict) are preserved: they represent a
        successfully loaded result with zero items, which is a valid cache
        hit and must stay distinguishable from a cache miss.
        """
        empty_keys = []
        with self._lock:
            for resource_type, bucket in self._buckets.items():
                # TTLCache.keys() filters expired entries, so .get() here only sees live values.
                for cache_key in list(bucket.keys()):
                    data = bucket.get(cache_key)
                    if data is None:
                        empty_keys.append((resource_type, cache_key))

            for resource_type, cache_key in empty_keys:
                bucket = self._buckets.get(resource_type)
                if bucket is not None:
                    bucket.pop(cache_key, None)

        if empty_keys:
            logging.info(
                f"Cleared {len(empty_keys)} empty cache entries: "
                f"{[f'{rt}:{ck}' for rt, ck in empty_keys[:5]]}"
                f"{'...' if len(empty_keys) > 5 else ''}"
            )

        return len(empty_keys)


# Global cache instance
_cache_instance = None
_cache_instance_lock = threading.Lock()


def get_unified_cache() -> UnifiedCache:
    """Get the unified cache singleton (thread-safe)."""
    global _cache_instance
    if _cache_instance is None:
        with _cache_instance_lock:
            if _cache_instance is None:
                _cache_instance = UnifiedCache()
    return _cache_instance
