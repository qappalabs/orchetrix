"""
Bounded Cache System with LRU eviction and TTL support
Replaces unbounded caches to prevent memory leaks
"""

import threading
import time
import weakref
import sys
import gc
from typing import Dict, Any, Optional, List, Tuple
from collections import OrderedDict
from dataclasses import dataclass
import logging


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    size_estimate: int


class BoundedCache:
    """
    Thread-safe bounded cache with LRU eviction and TTL support.
    Prevents memory leaks by enforcing size limits and automatic cleanup.
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300, max_memory_mb: int = 50):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # Thread-safe storage
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._cleanups = 0
        
        # Cleanup management
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # Cleanup every 60 seconds
        
        logging.info(f"BoundedCache initialized: max_size={max_size}, ttl={ttl_seconds}s, max_memory={max_memory_mb}MB")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache with LRU and TTL checks"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            current_time = time.time()
            
            # Check TTL
            if current_time - entry.created_at > self.ttl_seconds:
                del self._cache[key]
                self._misses += 1
                return None
            
            # Update access info and move to end (LRU)
            entry.last_accessed = current_time
            entry.access_count += 1
            self._cache.move_to_end(key)
            
            self._hits += 1
            return entry.value
    
    def set(self, key: str, value: Any) -> bool:
        """Set value in cache with automatic cleanup"""
        with self._lock:
            current_time = time.time()
            
            # Estimate size
            size_estimate = self._estimate_size(value)
            
            # Check if single item is too large
            if size_estimate > self.max_memory_bytes:
                logging.warning(f"Cache item too large: {size_estimate} bytes > {self.max_memory_bytes}")
                return False
            
            # Cleanup if needed
            self._cleanup_if_needed()
            
            # Remove oldest entries if at capacity
            while len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            # Ensure memory limit
            while self._get_memory_usage() + size_estimate > self.max_memory_bytes and self._cache:
                self._evict_lru()
            
            # Create new entry
            entry = CacheEntry(
                value=value,
                created_at=current_time,
                last_accessed=current_time,
                access_count=1,
                size_estimate=size_estimate
            )
            
            # Add to cache
            if key in self._cache:
                # Update existing entry
                self._cache[key] = entry
                self._cache.move_to_end(key)
            else:
                # Add new entry
                self._cache[key] = entry
            
            return True
    
    def remove(self, key: str) -> bool:
        """Remove specific key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            logging.info("BoundedCache cleared")
    
    def clear_pattern(self, pattern: str):
        """Clear cache entries matching pattern"""
        with self._lock:
            keys_to_remove = [key for key in self._cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self._cache[key]
            logging.info(f"Cleared {len(keys_to_remove)} entries matching pattern '{pattern}'")
    
    def _cleanup_if_needed(self):
        """Perform cleanup if interval has passed"""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = current_time
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self._cache.items():
            if current_time - entry.created_at > self.ttl_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            self._cleanups += 1
            logging.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _evict_lru(self):
        """Evict least recently used entry"""
        if self._cache:
            key, entry = self._cache.popitem(last=False)  # Remove from beginning (oldest)
            self._evictions += 1
            logging.debug(f"Evicted LRU cache entry: {key}")
    
    def _get_memory_usage(self) -> int:
        """Estimate current memory usage"""
        return sum(entry.size_estimate for entry in self._cache.values())
    
    def _estimate_size(self, obj: Any) -> int:
        """Estimate object size in bytes"""
        try:
            return sys.getsizeof(obj)
        except:
            # Fallback estimation
            if isinstance(obj, str):
                return len(obj) * 2  # Unicode characters
            elif isinstance(obj, (int, float)):
                return 24
            elif isinstance(obj, (list, tuple)):
                return 64 + sum(self._estimate_size(item) for item in obj[:10])  # Sample first 10
            elif isinstance(obj, dict):
                return 144 + sum(self._estimate_size(k) + self._estimate_size(v) for k, v in list(obj.items())[:10])
            else:
                return 64  # Default estimate
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate_percent': round(hit_rate, 2),
                'evictions': self._evictions,
                'cleanups': self._cleanups,
                'memory_usage_bytes': self._get_memory_usage(),
                'memory_usage_mb': round(self._get_memory_usage() / (1024 * 1024), 2),
                'max_memory_mb': round(self.max_memory_bytes / (1024 * 1024), 2)
            }
    
    def __len__(self) -> int:
        """Return number of cached items"""
        with self._lock:
            return len(self._cache)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in cache"""
        with self._lock:
            return key in self._cache
    
    def keys(self) -> List[str]:
        """Get all cache keys"""
        with self._lock:
            return list(self._cache.keys())


class GlobalCacheManager:
    """
    Manages global bounded caches to replace unbounded ones.
    Provides centralized cache management and cleanup.
    """
    
    def __init__(self):
        self._caches: Dict[str, BoundedCache] = {}
        self._lock = threading.Lock()
        
        # Create commonly used caches
        self.age_cache = self.get_cache('age', max_size=5000, ttl_seconds=60)
        self.icon_cache = self.get_cache('icons', max_size=1000, ttl_seconds=1800) 
        self.formatted_data_cache = self.get_cache('formatted_data', max_size=10000, ttl_seconds=300)
        self.resource_cache = self.get_cache('resources', max_size=2000, ttl_seconds=600)
        
        logging.info("GlobalCacheManager initialized with bounded caches")
    
    def get_cache(self, name: str, max_size: int = 1000, ttl_seconds: int = 300, 
                  max_memory_mb: int = 50) -> BoundedCache:
        """Get or create a named cache"""
        with self._lock:
            if name not in self._caches:
                self._caches[name] = BoundedCache(max_size, ttl_seconds, max_memory_mb)
                logging.info(f"Created cache '{name}': max_size={max_size}, ttl={ttl_seconds}s")
            return self._caches[name]
    
    def clear_all_caches(self):
        """Clear all managed caches"""
        with self._lock:
            for cache in self._caches.values():
                cache.clear()
            logging.info("Cleared all managed caches")
    
    def clear_cache(self, name: str):
        """Clear specific cache"""
        with self._lock:
            if name in self._caches:
                self._caches[name].clear()
                logging.info(f"Cleared cache '{name}'")
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches"""
        with self._lock:
            return {name: cache.get_stats() for name, cache in self._caches.items()}
    
    def cleanup_all(self):
        """Force cleanup of all caches"""
        with self._lock:
            for cache in self._caches.values():
                cache._cleanup_expired()
            
            # Force garbage collection
            collected = gc.collect()
            logging.info(f"Cache cleanup completed, garbage collected {collected} objects")
    
    def get_total_memory_usage(self) -> int:
        """Get total memory usage across all caches"""
        with self._lock:
            return sum(cache._get_memory_usage() for cache in self._caches.values())


# Global cache manager instance
_cache_manager = None
_cache_manager_lock = threading.Lock()

def get_cache_manager() -> GlobalCacheManager:
    """Get global cache manager singleton"""
    global _cache_manager
    with _cache_manager_lock:
        if _cache_manager is None:
            _cache_manager = GlobalCacheManager()
        return _cache_manager


# Convenient access to common caches
def get_age_cache() -> BoundedCache:
    """Get the global age cache"""
    return get_cache_manager().age_cache

def get_icon_cache() -> BoundedCache:
    """Get the global icon cache"""
    return get_cache_manager().icon_cache

def get_formatted_data_cache() -> BoundedCache:
    """Get the global formatted data cache"""
    return get_cache_manager().formatted_data_cache

def get_resource_cache() -> BoundedCache:
    """Get the global resource cache"""
    return get_cache_manager().resource_cache


# Cache decorators for easy use
def cached(cache_name: str, ttl_seconds: int = 300):
    """Decorator to cache function results"""
    def decorator(func):
        cache = get_cache_manager().get_cache(cache_name, ttl_seconds=ttl_seconds)
        
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        
        return wrapper
    return decorator


def clear_all_caches():
    """Clear all global caches"""
    get_cache_manager().clear_all_caches()


def get_cache_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all caches"""
    return get_cache_manager().get_all_stats()


def force_cache_cleanup():
    """Force cleanup of all caches and garbage collection"""
    get_cache_manager().cleanup_all()


# Automatic cleanup on module exit
import atexit
atexit.register(clear_all_caches)