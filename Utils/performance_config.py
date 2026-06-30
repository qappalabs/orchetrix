"""
Performance Configuration – Centralized settings for optimal performance.

# NOTE: Currently unused – kept for potential future centralized performance management.
# The application currently uses simpler direct constants in individual files.
"""
import logging
import os

__all__ = ["get_performance_config", "apply_performance_optimizations", "PERFORMANCE_PROFILES"]

# Table Rendering Performance
TABLE_BATCH_SIZE = 25  # Smaller batches for responsive UI
TABLE_PROGRESSIVE_THRESHOLD = 250  # When to use progressive rendering
TABLE_RENDER_INTERVAL = 5  # Milliseconds between render batches

# Heavy Data Performance - Optimized for large deployments
HEAVY_DATA_THRESHOLD = 50   # Lower threshold for earlier optimizations
VIRTUAL_SCROLLING_THRESHOLD = 100  # Earlier virtual scrolling activation
PROGRESSIVE_LOADING_THRESHOLD = 100  # Earlier progressive loading
PROGRESSIVE_CHUNK_SIZE = 75   # Larger chunks for efficiency
MAX_INITIAL_DISPLAY = 150     # Show more items initially for better UX

# Graph and Chart Performance
GRAPH_UPDATE_INTERVAL = 45000  # 45 seconds between graph updates
GRAPH_DATA_THROTTLE = 20000  # 20 seconds minimum between data updates
GRAPH_PAINT_OPTIMIZATION = True  # Use optimized painting

# Data Loading Performance - Optimized for heavy loads
OVERVIEW_REFRESH_INTERVAL = 180000  # 3 minutes between overview refreshes for heavy loads
INITIAL_LOAD_DELAY = 1000  # Reduced delay for faster initial response
RESOURCE_FETCH_TIMEOUT = 45000  # Extended timeout for heavy loads

# Memory Management
MAX_CACHED_RESOURCES = 1000  # Maximum resources to keep in memory
CACHE_CLEANUP_INTERVAL = 300  # 5 minutes between cache cleanups
AGE_CACHE_SIZE = 5000  # Maximum age format cache entries

# UI Responsiveness
PROCESS_EVENTS_FREQUENCY = 200  # Process UI events every N operations
SEARCH_DEBOUNCE_MS = 300  # 300ms debounce for search
SCROLL_DEBOUNCE_MS = 100  # 100ms debounce for scrolling

# Thread Management - Optimized for heavy loads
MAX_CONCURRENT_WORKERS = 6  # Increased workers for parallel processing
WORKER_TIMEOUT_MS = 45000   # Extended timeout for heavy calculations

# Performance Profiles
# Profile naming convention:
#   - "resource_constrained": For systems with limited CPU/memory - uses larger batches
#     and less frequent updates to reduce overhead
#   - "balanced": Middle ground for typical systems
#   - "resource_rich": For high-spec systems - smaller batches and more frequent updates
#     for maximum UI responsiveness
PERFORMANCE_PROFILES = {
    "resource_constrained": {
        "table_batch_size": 75,  # Larger batches to reduce overhead
        "graph_update_interval": 90000,  # Less frequent updates
        "overview_refresh_interval": 240000,  # 4 minutes for reduced load
        "max_cached_resources": 2000,  # More caching to reduce re-fetches
        "enable_virtual_scrolling": True,
        "progressive_loading_threshold": 100,
        "progressive_chunk_size": 100
    },
    "balanced": {
        "table_batch_size": 50,  # Moderate batch size
        "graph_update_interval": 60000,  # Moderate frequency
        "overview_refresh_interval": 180000,  # 3 minutes
        "max_cached_resources": 1500,  # Moderate cache
        "enable_virtual_scrolling": True,
        "progressive_loading_threshold": 75,
        "progressive_chunk_size": 75
    },
    "resource_rich": {
        "table_batch_size": 25,  # Smaller batches for smoother UI
        "graph_update_interval": 45000,  # More frequent updates
        "enable_virtual_scrolling": True,
        "progressive_loading_threshold": 50,
        "progressive_chunk_size": 50,
        "overview_refresh_interval": 120000,  # 2 minutes
        "max_cached_resources": 2000
    }
}

def get_performance_config(profile="balanced"):
    """Get performance configuration for specified profile"""
    if profile in PERFORMANCE_PROFILES:
        config = PERFORMANCE_PROFILES[profile].copy()
        # Add default values
        config.update({
            "search_debounce_ms": SEARCH_DEBOUNCE_MS,
            "scroll_debounce_ms": SCROLL_DEBOUNCE_MS,
            "process_events_frequency": PROCESS_EVENTS_FREQUENCY
        })
        return config
    else:
        return PERFORMANCE_PROFILES["balanced"]

def apply_performance_optimizations():
    """Apply performance optimizations based on system capabilities

    Note: psutil is an optional dependency. If not available, falls back to
    basic CPU count detection only.

    Returns:
        dict: Performance configuration for the detected system profile
            - resource_rich: High-spec systems (16GB+ RAM, 8+ CPUs)
            - balanced: Typical systems (8GB+ RAM, 4+ CPUs)
            - resource_constrained: Limited systems or detection failures
    """
    logger = logging.getLogger(__name__)

    try:
        import psutil
    except ImportError:
        # Fallback: psutil not available, use resource-constrained profile
        logger.debug("psutil not available, using resource_constrained profile")
        return get_performance_config("resource_constrained")

    # Detect system resources
    cpu_count = os.cpu_count() or 4
    try:
        memory_gb = psutil.virtual_memory().total / (1024**3)
    except (AttributeError, PermissionError, OSError) as e:
        # psutil might be available but not working due to permissions or OS issues
        logger.warning("Failed to detect memory: %s. Using default 8GB assumption.", e)
        memory_gb = 8  # Assume balanced system

    # Choose profile based on system resources
    if memory_gb >= 16 and cpu_count >= 8:
        return get_performance_config("resource_rich")
    elif memory_gb >= 8 and cpu_count >= 4:
        return get_performance_config("balanced")
    else:
        return get_performance_config("resource_constrained")
