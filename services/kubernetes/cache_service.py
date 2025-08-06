"""
Kubernetes Cache Service - Handles caching with TTL and size limits
Split from kubernetes_client.py for better architecture
"""

import gc
import logging
import time
from typing import Any, Optional
from cachetools import TTLCache

# Cache configuration constants
CACHE_MAX_SIZE = 100  # Maximum cache entries
CACHE_TTL = 300  # Cache TTL in seconds
METRICS_CACHE_TTL = 10  # Metrics cache TTL - shorter for real-time data


class KubernetesCacheService:
    """Service for managing Kubernetes data caches with TTL and size limits"""
    
    def __init__(self):
        # FIXED: Use TTL caches to prevent memory leaks
        self._metrics_cache = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=METRICS_CACHE_TTL)
        self._issues_cache = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
        
        # Resource detail cache with shorter TTL
        self._resource_detail_cache = TTLCache(maxsize=50, ttl=60)
        
        # Cluster info cache
        self._cluster_info_cache = TTLCache(maxsize=10, ttl=300)
        
        # Additional specialized caches
        self._resource_list_cache = TTLCache(maxsize=200, ttl=120)
        self._namespace_cache = TTLCache(maxsize=50, ttl=600)  # Namespaces change less frequently
        
        logging.debug("KubernetesCacheService initialized with TTL caches")
    
    def get_metrics_cache(self) -> TTLCache:
        """Get the metrics cache"""
        return self._metrics_cache
    
    def get_issues_cache(self) -> TTLCache:
        """Get the issues cache"""
        return self._issues_cache
    
    def get_resource_detail_cache(self) -> TTLCache:
        """Get the resource detail cache"""
        return self._resource_detail_cache
    
    def get_cluster_info_cache(self) -> TTLCache:
        """Get the cluster info cache"""
        return self._cluster_info_cache
    
    def get_resource_list_cache(self) -> TTLCache:
        """Get the resource list cache"""
        return self._resource_list_cache
    
    def get_namespace_cache(self) -> TTLCache:
        """Get the namespace cache"""
        return self._namespace_cache
    
    def get_cached_metrics(self, cluster_name: str) -> Optional[Any]:
        """Get cached metrics for a cluster"""
        return self._metrics_cache.get(cluster_name)
    
    def cache_metrics(self, cluster_name: str, metrics: Any) -> None:
        """Cache metrics for a cluster"""
        self._metrics_cache[cluster_name] = metrics
        logging.debug(f"Cached metrics for cluster: {cluster_name}")
    
    def get_cached_issues(self, cluster_name: str) -> Optional[Any]:
        """Get cached issues for a cluster"""
        return self._issues_cache.get(cluster_name)
    
    def cache_issues(self, cluster_name: str, issues: Any) -> None:
        """Cache issues for a cluster"""
        self._issues_cache[cluster_name] = issues
        logging.debug(f"Cached issues for cluster: {cluster_name}")
    
    def get_cached_resource_detail(self, resource_key: str) -> Optional[Any]:
        """Get cached resource detail"""
        return self._resource_detail_cache.get(resource_key)
    
    def cache_resource_detail(self, resource_key: str, detail: Any) -> None:
        """Cache resource detail"""
        self._resource_detail_cache[resource_key] = detail
        logging.debug(f"Cached resource detail: {resource_key}")
    
    def get_cached_cluster_info(self, cluster_name: str) -> Optional[Any]:
        """Get cached cluster info"""
        return self._cluster_info_cache.get(cluster_name)
    
    def cache_cluster_info(self, cluster_name: str, info: Any) -> None:
        """Cache cluster info"""
        self._cluster_info_cache[cluster_name] = info
        logging.debug(f"Cached cluster info: {cluster_name}")
    
    def get_cached_resource_list(self, resource_key: str) -> Optional[Any]:
        """Get cached resource list"""
        return self._resource_list_cache.get(resource_key)
    
    def cache_resource_list(self, resource_key: str, resources: Any) -> None:
        """Cache resource list"""
        self._resource_list_cache[resource_key] = resources
        logging.debug(f"Cached resource list: {resource_key}")
    
    def get_cached_namespaces(self, cluster_name: str) -> Optional[Any]:
        """Get cached namespaces"""
        return self._namespace_cache.get(cluster_name)
    
    def cache_namespaces(self, cluster_name: str, namespaces: Any) -> None:
        """Cache namespaces"""
        self._namespace_cache[cluster_name] = namespaces
        logging.debug(f"Cached namespaces for cluster: {cluster_name}")
    
    def invalidate_cluster_cache(self, cluster_name: str) -> None:
        """Invalidate all cache entries for a specific cluster"""
        # Remove cluster-specific entries
        keys_to_remove = []
        
        # Check metrics cache
        if cluster_name in self._metrics_cache:
            keys_to_remove.append(('metrics', cluster_name))
        
        # Check issues cache
        if cluster_name in self._issues_cache:
            keys_to_remove.append(('issues', cluster_name))
        
        # Check cluster info cache
        if cluster_name in self._cluster_info_cache:
            keys_to_remove.append(('cluster_info', cluster_name))
        
        # Check namespace cache
        if cluster_name in self._namespace_cache:
            keys_to_remove.append(('namespaces', cluster_name))
        
        # Remove entries
        for cache_type, key in keys_to_remove:
            try:
                if cache_type == 'metrics':
                    del self._metrics_cache[key]
                elif cache_type == 'issues':
                    del self._issues_cache[key]
                elif cache_type == 'cluster_info':
                    del self._cluster_info_cache[key]
                elif cache_type == 'namespaces':
                    del self._namespace_cache[key]
                logging.debug(f"Invalidated {cache_type} cache for cluster: {cluster_name}")
            except KeyError:
                pass  # Key might have already expired
    
    def cleanup_cache(self) -> None:
        """Clean up cache entries and force garbage collection"""
        # FIXED: TTL caches handle cleanup automatically, just force GC
        gc.collect()
        
        # Log cache sizes for monitoring
        logging.debug(f"Cache sizes - Metrics: {len(self._metrics_cache)}, "
                     f"Issues: {len(self._issues_cache)}, "
                     f"Resource details: {len(self._resource_detail_cache)}, "
                     f"Cluster info: {len(self._cluster_info_cache)}, "
                     f"Resource lists: {len(self._resource_list_cache)}, "
                     f"Namespaces: {len(self._namespace_cache)}")
    
    def clear_all_caches(self) -> None:
        """Clear all caches"""
        self._metrics_cache.clear()
        self._issues_cache.clear()
        self._resource_detail_cache.clear()
        self._cluster_info_cache.clear()
        self._resource_list_cache.clear()
        self._namespace_cache.clear()
        
        # Force garbage collection
        gc.collect()
        logging.info("All caches cleared")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        return {
            'metrics_cache': {
                'size': len(self._metrics_cache),
                'maxsize': self._metrics_cache.maxsize,
                'ttl': self._metrics_cache.ttl
            },
            'issues_cache': {
                'size': len(self._issues_cache),
                'maxsize': self._issues_cache.maxsize,
                'ttl': self._issues_cache.ttl
            },
            'resource_detail_cache': {
                'size': len(self._resource_detail_cache),
                'maxsize': self._resource_detail_cache.maxsize,
                'ttl': self._resource_detail_cache.ttl
            },
            'cluster_info_cache': {
                'size': len(self._cluster_info_cache),
                'maxsize': self._cluster_info_cache.maxsize,
                'ttl': self._cluster_info_cache.ttl
            },
            'resource_list_cache': {
                'size': len(self._resource_list_cache),
                'maxsize': self._resource_list_cache.maxsize,
                'ttl': self._resource_list_cache.ttl
            },
            'namespace_cache': {
                'size': len(self._namespace_cache),
                'maxsize': self._namespace_cache.maxsize,
                'ttl': self._namespace_cache.ttl
            }
        }
    
    def cleanup(self) -> None:
        """Cleanup cache service resources"""
        logging.debug("Cleaning up KubernetesCacheService")
        self.clear_all_caches()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            if hasattr(self, '_metrics_cache'):
                self.cleanup()
        except Exception as e:
            logging.error(f"Error in KubernetesCacheService destructor: {e}")


# Singleton instance
_cache_service_instance = None

# Utility functions for resource parsing and formatting
def parse_resource_value(value_str: str) -> float:
    """Parse Kubernetes resource values (CPU, memory) to numeric form"""
    if not value_str:
        return 0.0
    
    try:
        # Handle CPU values (e.g., "100m", "1", "1.5")
        if value_str.endswith('m'):
            return float(value_str[:-1]) / 1000.0
        elif value_str.endswith('n'):
            return float(value_str[:-1]) / 1_000_000_000.0
        elif value_str.endswith('u'):
            return float(value_str[:-1]) / 1_000_000.0
        
        # Handle memory values (e.g., "1Gi", "512Mi", "1024Ki")
        if value_str.endswith('Ki'):
            return float(value_str[:-2]) * 1024
        elif value_str.endswith('Mi'):
            return float(value_str[:-2]) * 1024 * 1024
        elif value_str.endswith('Gi'):
            return float(value_str[:-2]) * 1024 * 1024 * 1024
        elif value_str.endswith('Ti'):
            return float(value_str[:-2]) * 1024 * 1024 * 1024 * 1024
        
        # Handle bytes values
        if value_str.endswith('K'):
            return float(value_str[:-1]) * 1000
        elif value_str.endswith('M'):
            return float(value_str[:-1]) * 1000 * 1000
        elif value_str.endswith('G'):
            return float(value_str[:-1]) * 1000 * 1000 * 1000
        elif value_str.endswith('T'):
            return float(value_str[:-1]) * 1000 * 1000 * 1000 * 1000
        
        # Plain numeric value
        return float(value_str)
        
    except (ValueError, TypeError):
        logging.warning(f"Could not parse resource value: {value_str}")
        return 0.0

def format_age(timestamp) -> str:
    """Format age from timestamp"""
    if not timestamp:
        return "Unknown"
    
    try:
        from datetime import datetime
        if isinstance(timestamp, str):
            created = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            created = timestamp
        
        now = datetime.now(created.tzinfo or datetime.now().astimezone().tzinfo)
        diff = now - created
        
        if diff.days > 0:
            return f"{diff.days}d"
        elif diff.seconds >= 3600:
            return f"{diff.seconds // 3600}h"
        else:
            return f"{diff.seconds // 60}m"
            
    except Exception as e:
        logging.error(f"Error formatting age: {e}")
        return "Unknown"

def clear_lru_caches():
    """Clear all LRU caches in the cache service"""
    # This function would clear any @lru_cache decorated functions
    # For now, it's a placeholder
    logging.debug("LRU caches cleared")


def get_kubernetes_cache_service() -> KubernetesCacheService:
    """Get or create Kubernetes cache service singleton"""
    global _cache_service_instance
    if _cache_service_instance is None:
        _cache_service_instance = KubernetesCacheService()
    return _cache_service_instance

def reset_kubernetes_cache_service():
    """Reset the singleton instance"""
    global _cache_service_instance
    if _cache_service_instance:
        _cache_service_instance.cleanup()
    _cache_service_instance = None