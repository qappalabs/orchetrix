"""
Unified High-Performance Cache System
Consolidates bounded_cache.py and cache_service.py into one optimized system.
Designed for maximum performance with intelligent eviction and memory management.
"""

import threading
import time
import logging
import gc
from typing import Dict, Any, Optional, List, Tuple, Callable, Union
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from functools import wraps
from datetime import datetime, timezone
import weakref


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata"""
    value: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: Optional[float] = None
    size_bytes: int = 0
    
    def is_expired(self, current_time: float) -> bool:
        """Check if entry is expired based on TTL"""
        if self.ttl is None:
            return False
        return (current_time - self.created_at) > self.ttl
    
    def update_access(self, current_time: float):
        """Update access statistics"""
        self.last_accessed = current_time
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache statistics for monitoring and optimization"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_entries: int = 0
    memory_usage: int = 0
    hit_rate: float = 0.0
    
    def update_hit_rate(self):
        """Update hit rate calculation"""
        total_requests = self.hits + self.misses
        self.hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0.0


class HighPerformanceCache:
    """
    High-performance cache with advanced features:
    - LRU + TTL eviction
    - Memory usage tracking
    - Access pattern optimization
    - Thread safety
    - Performance monitoring
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300, max_memory_mb: int = 100):
        # Core cache storage
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
        # Configuration
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # Statistics
        self.stats = CacheStats()
        
        # Performance optimization
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # seconds
        self._access_patterns = defaultdict(list)
        
        # Memory tracking
        self._current_memory_usage = 0
        
        logging.debug(f"High-performance cache initialized: max_size={max_size}, ttl={default_ttl}s, max_memory={max_memory_mb}MB")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache with performance optimizations"""
        current_time = time.time()
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self.stats.misses += 1
                self.stats.update_hit_rate()
                return None
            
            # Check expiration
            if entry.is_expired(current_time):
                self._remove_entry(key, entry)
                self.stats.misses += 1
                self.stats.update_hit_rate()
                return None
            
            # Update access statistics
            entry.update_access(current_time)
            
            # Move to end for LRU (most recently used)
            self._cache.move_to_end(key)
            
            # Track access patterns
            self._access_patterns[key].append(current_time)
            
            # Update stats
            self.stats.hits += 1
            self.stats.update_hit_rate()
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in cache with intelligent eviction"""
        current_time = time.time()
        
        # Estimate memory usage
        estimated_size = self._estimate_memory_size(value)
        
        with self._lock:
            # Check if we need to make space
            if key not in self._cache:
                self._ensure_capacity(estimated_size, current_time)
            
            # Create cache entry
            entry = CacheEntry(
                value=value,
                created_at=current_time,
                last_accessed=current_time,
                ttl=ttl or self.default_ttl,
                size_bytes=estimated_size
            )
            
            # Remove old entry if exists
            if key in self._cache:
                old_entry = self._cache[key]
                self._current_memory_usage -= old_entry.size_bytes
            
            # Add new entry
            self._cache[key] = entry
            self._current_memory_usage += estimated_size
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            
            # Update stats
            self.stats.total_entries = len(self._cache)
            self.stats.memory_usage = self._current_memory_usage
            
            # Periodic cleanup
            if current_time - self._last_cleanup > self._cleanup_interval:
                self._cleanup_expired(current_time)
                self._last_cleanup = current_time
            
            return True
    
    def _ensure_capacity(self, new_entry_size: int, current_time: float):
        """Ensure cache has capacity for new entry"""
        # Check memory limit
        while (self._current_memory_usage + new_entry_size > self.max_memory_bytes 
               and self._cache):
            self._evict_lru_entry()
        
        # Check size limit
        while len(self._cache) >= self.max_size and self._cache:
            self._evict_lru_entry()
        
        # Clean up expired entries
        self._cleanup_expired(current_time)
    
    def _evict_lru_entry(self):
        """Evict least recently used entry"""
        if not self._cache:
            return
        
        # Get LRU entry (first in OrderedDict)
        key, entry = self._cache.popitem(last=False)
        self._remove_entry_data(key, entry)
        self.stats.evictions += 1
        
        logging.debug(f"Evicted LRU cache entry: {key}")
    
    def _remove_entry(self, key: str, entry: CacheEntry):
        """Remove entry from cache"""
        self._cache.pop(key, None)
        self._remove_entry_data(key, entry)
    
    def _remove_entry_data(self, key: str, entry: CacheEntry):
        """Remove entry data and update statistics"""
        self._current_memory_usage -= entry.size_bytes
        self._access_patterns.pop(key, None)
        self.stats.total_entries = len(self._cache)
        self.stats.memory_usage = self._current_memory_usage
    
    def _cleanup_expired(self, current_time: float):
        """Clean up expired entries"""
        expired_keys = []
        
        for key, entry in self._cache.items():
            if entry.is_expired(current_time):
                expired_keys.append((key, entry))
        
        for key, entry in expired_keys:
            self._remove_entry(key, entry)
        
        if expired_keys:
            logging.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _estimate_memory_size(self, obj: Any) -> int:
        """Estimate memory size of object"""
        try:
            import sys
            
            if isinstance(obj, (str, int, float, bool)):
                return sys.getsizeof(obj)
            elif isinstance(obj, (list, tuple)):
                return sys.getsizeof(obj) + sum(sys.getsizeof(item) for item in obj[:10])  # Sample first 10
            elif isinstance(obj, dict):
                size = sys.getsizeof(obj)
                for k, v in list(obj.items())[:5]:  # Sample first 5 key-value pairs
                    size += sys.getsizeof(k) + sys.getsizeof(v)
                return size
            else:
                return sys.getsizeof(obj)
        except Exception:
            return 1024  # Default estimate
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        with self._lock:
            entry = self._cache.pop(key, None)
            if entry:
                self._remove_entry_data(key, entry)
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_patterns.clear()
            self._current_memory_usage = 0
            self.stats = CacheStats()
            
        logging.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            self.stats.total_entries = len(self._cache)
            self.stats.memory_usage = self._current_memory_usage
            self.stats.update_hit_rate()
            
            return {
                'hits': self.stats.hits,
                'misses': self.stats.misses,
                'evictions': self.stats.evictions,
                'hit_rate': round(self.stats.hit_rate, 2),
                'total_entries': self.stats.total_entries,
                'max_size': self.max_size,
                'memory_usage_mb': round(self.stats.memory_usage / 1024 / 1024, 2),
                'max_memory_mb': round(self.max_memory_bytes / 1024 / 1024, 2),
                'memory_utilization': round((self.stats.memory_usage / self.max_memory_bytes) * 100, 2)
            }
    
    def get_top_accessed_keys(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most frequently accessed keys"""
        with self._lock:
            key_access_counts = []
            
            for key, entry in self._cache.items():
                key_access_counts.append((key, entry.access_count))
            
            # Sort by access count descending
            key_access_counts.sort(key=lambda x: x[1], reverse=True)
            
            return key_access_counts[:limit]


class UnifiedCacheSystem:
    """
    Unified cache system that consolidates all caching needs.
    Provides specialized caches for different data types with optimal configurations.
    """
    
    def __init__(self):
        # Specialized cache instances
        self._resource_cache = HighPerformanceCache(
            max_size=2000,
            default_ttl=300,  # 5 minutes
            max_memory_mb=50
        )
        
        self._metrics_cache = HighPerformanceCache(
            max_size=500,
            default_ttl=30,   # 30 seconds
            max_memory_mb=20
        )
        
        self._age_cache = HighPerformanceCache(
            max_size=1000,
            default_ttl=600,  # 10 minutes
            max_memory_mb=10
        )
        
        self._formatted_data_cache = HighPerformanceCache(
            max_size=1500,
            default_ttl=300,  # 5 minutes
            max_memory_mb=30
        )
        
        # Global lock for cache operations
        self._global_lock = threading.RLock()
        
        # Cache registry
        self._caches = {
            'resource': self._resource_cache,
            'metrics': self._metrics_cache,
            'age': self._age_cache,
            'formatted_data': self._formatted_data_cache
        }
        
        logging.info("Unified cache system initialized with specialized caches")
    
    # Resource caching methods
    def cache_resources(self, resource_type: str, cache_key: str, resources: List[Dict], ttl_seconds: int = 300):
        """Cache Kubernetes resources"""
        key = f"resource:{resource_type}:{cache_key}"
        return self._resource_cache.set(key, resources, ttl_seconds)
    
    def get_cached_resources(self, resource_type: str, cache_key: str, max_age_seconds: int = 300) -> Optional[List[Dict]]:
        """Get cached Kubernetes resources"""
        key = f"resource:{resource_type}:{cache_key}"
        return self._resource_cache.get(key)
    
    def clear_resource_cache(self, resource_type: str = None):
        """Clear resource cache"""
        if resource_type:
            # Clear specific resource type
            with self._resource_cache._lock:
                keys_to_remove = [k for k in self._resource_cache._cache.keys() 
                                 if k.startswith(f"resource:{resource_type}:")]
                for key in keys_to_remove:
                    self._resource_cache.delete(key)
            logging.info(f"Cleared cache for resource type: {resource_type}")
        else:
            self._resource_cache.clear()
            logging.info("Cleared all resource cache")
    
    # Metrics caching methods
    def cache_metrics(self, cluster_name: str, metrics: Dict[str, Any], ttl_seconds: int = 30):
        """Cache cluster metrics"""
        key = f"metrics:{cluster_name}"
        return self._metrics_cache.set(key, metrics, ttl_seconds)
    
    def get_cached_metrics(self, cluster_name: str) -> Optional[Dict[str, Any]]:
        """Get cached cluster metrics"""
        key = f"metrics:{cluster_name}"
        return self._metrics_cache.get(key)
    
    # Age formatting cache methods
    def cache_age_format(self, timestamp_str: str, formatted_age: str, ttl_seconds: int = 600):
        """Cache age formatting results"""
        key = f"age:{timestamp_str}"
        return self._age_cache.set(key, formatted_age, ttl_seconds)
    
    def get_cached_age_format(self, timestamp_str: str) -> Optional[str]:
        """Get cached age formatting result"""
        key = f"age:{timestamp_str}"
        return self._age_cache.get(key)
    
    # Formatted data cache methods
    def cache_formatted_data(self, data_key: str, formatted_data: Any, ttl_seconds: int = 300):
        """Cache formatted data"""
        return self._formatted_data_cache.set(data_key, formatted_data, ttl_seconds)
    
    def get_cached_formatted_data(self, data_key: str) -> Optional[Any]:
        """Get cached formatted data"""
        return self._formatted_data_cache.get(data_key)
    
    # Global cache management
    def get_global_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches"""
        stats = {}
        for cache_name, cache_instance in self._caches.items():
            stats[cache_name] = cache_instance.get_stats()
        
        # Calculate totals
        total_entries = sum(s['total_entries'] for s in stats.values())
        total_memory_mb = sum(s['memory_usage_mb'] for s in stats.values())
        avg_hit_rate = sum(s['hit_rate'] for s in stats.values()) / len(stats)
        
        stats['totals'] = {
            'total_entries': total_entries,
            'total_memory_mb': round(total_memory_mb, 2),
            'avg_hit_rate': round(avg_hit_rate, 2)
        }
        
        return stats
    
    def clear_all_caches(self):
        """Clear all caches"""
        for cache_instance in self._caches.values():
            cache_instance.clear()
        
        logging.info("Cleared all caches in unified system")
    
    def optimize_caches(self):
        """Optimize all caches by cleaning up expired entries"""
        current_time = time.time()
        
        for cache_name, cache_instance in self._caches.items():
            with cache_instance._lock:
                cache_instance._cleanup_expired(current_time)
        
        # Force garbage collection
        gc.collect()
        
        logging.info("Optimized all caches")
    
    def get_cache_recommendations(self) -> List[str]:
        """Get performance recommendations based on cache usage"""
        recommendations = []
        stats = self.get_global_stats()
        
        for cache_name, cache_stats in stats.items():
            if cache_name == 'totals':
                continue
            
            hit_rate = cache_stats['hit_rate']
            memory_util = cache_stats['memory_utilization']
            
            if hit_rate < 70:
                recommendations.append(f"{cache_name} cache has low hit rate ({hit_rate}%) - consider increasing TTL")
            
            if memory_util > 90:
                recommendations.append(f"{cache_name} cache is near memory limit ({memory_util}%) - consider increasing max memory")
            
            if cache_stats['evictions'] > cache_stats['hits'] * 0.1:
                recommendations.append(f"{cache_name} cache has high eviction rate - consider increasing cache size")
        
        return recommendations


# Global unified cache instance
_unified_cache_instance = None

def get_unified_cache() -> UnifiedCacheSystem:
    """Get or create unified cache system singleton"""
    global _unified_cache_instance
    if _unified_cache_instance is None:
        _unified_cache_instance = UnifiedCacheSystem()
    return _unified_cache_instance

def clear_all_unified_caches():
    """Clear all unified caches"""
    cache_system = get_unified_cache()
    cache_system.clear_all_caches()

def get_unified_cache_stats() -> Dict[str, Any]:
    """Get unified cache statistics"""
    cache_system = get_unified_cache()
    return cache_system.get_global_stats()

def optimize_unified_caches():
    """Optimize all unified caches"""
    cache_system = get_unified_cache()
    cache_system.optimize_caches()


# Backward compatibility functions
def get_kubernetes_cache_service():
    """Backward compatibility - get unified cache system"""
    return get_unified_cache()

def get_age_cache():
    """Backward compatibility - get age cache"""
    return get_unified_cache()

def get_formatted_data_cache():
    """Backward compatibility - get formatted data cache"""
    return get_unified_cache()

def clear_all_caches():
    """Backward compatibility - clear all caches"""
    clear_all_unified_caches()