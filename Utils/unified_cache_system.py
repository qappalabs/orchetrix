"""
Unified Cache System
Provides a simple in-memory cache for the application.
"""

import logging
import time
from typing import Dict, Any, Optional
from collections import defaultdict


class UnifiedCache:
    """Simple in-memory cache system"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._metadata: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        self._max_age = 300  # 5 minutes default

    def cache_resources(self, resource_type: str, cache_key: str, data: Any) -> None:
        """Cache data with metadata"""
        self._cache[resource_type][cache_key] = data
        self._metadata[resource_type][cache_key] = {
            'timestamp': time.time(),
            'size': len(str(data)) if data else 0
        }
        logging.debug(f"Cached {resource_type}:{cache_key}")

    def get_cached_resources(self, resource_type: str, cache_key: str) -> Optional[Any]:
        """Get cached data if not expired"""
        if resource_type in self._cache and cache_key in self._cache[resource_type]:
            # Check if expired
            if resource_type in self._metadata and cache_key in self._metadata[resource_type]:
                metadata = self._metadata[resource_type][cache_key]
                if time.time() - metadata['timestamp'] < self._max_age:
                    return self._cache[resource_type][cache_key]
                else:
                    # Remove expired entry
                    del self._cache[resource_type][cache_key]
                    del self._metadata[resource_type][cache_key]
        return None

    def clear_resource_cache(self, resource_type: str, cache_key: str) -> None:
        """Clear specific cache entry"""
        if resource_type in self._cache and cache_key in self._cache[resource_type]:
            del self._cache[resource_type][cache_key]
        if resource_type in self._metadata and cache_key in self._metadata[resource_type]:
            del self._metadata[resource_type][cache_key]
        logging.debug(f"Cleared cache {resource_type}:{cache_key}")

    def optimize_caches(self) -> None:
        """Clean up expired entries"""
        current_time = time.time()
        expired_keys = []

        for resource_type, cache_data in self._cache.items():
            for cache_key in list(cache_data.keys()):  # Use list() to allow modification during iteration
                if (resource_type in self._metadata and
                    cache_key in self._metadata[resource_type]):
                    metadata = self._metadata[resource_type][cache_key]
                    if current_time - metadata['timestamp'] >= self._max_age:
                        expired_keys.append((resource_type, cache_key))

        # Remove expired entries
        for resource_type, cache_key in expired_keys:
            del self._cache[resource_type][cache_key]
            del self._metadata[resource_type][cache_key]

        if expired_keys:
            logging.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def clear_empty_entries(self) -> int:
        """Clear all empty cache entries - call on startup or theme change to remove stale data"""
        empty_keys = []

        for resource_type, cache_data in self._cache.items():
            for cache_key, data in list(cache_data.items()):
                # Check if data is empty (None, empty list, empty dict)
                if data is None or (isinstance(data, (list, dict)) and not data):
                    empty_keys.append((resource_type, cache_key))

        # Remove empty entries
        for resource_type, cache_key in empty_keys:
            if resource_type in self._cache and cache_key in self._cache[resource_type]:
                del self._cache[resource_type][cache_key]
            if resource_type in self._metadata and cache_key in self._metadata[resource_type]:
                del self._metadata[resource_type][cache_key]

        if empty_keys:
            logging.info(f"Cleared {len(empty_keys)} empty cache entries: {[f'{rt}:{ck}' for rt, ck in empty_keys[:5]]}{'...' if len(empty_keys) > 5 else ''}")

        return len(empty_keys)


# Global cache instance
_cache_instance = None


def get_unified_cache() -> UnifiedCache:
    """Get the unified cache singleton"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = UnifiedCache()
    return _cache_instance
