"""
Performance Configuration - Centralized settings for optimal performance
"""

# Table Rendering Performance
TABLE_BATCH_SIZE = 25  # Smaller batches for responsive UI
TABLE_PROGRESSIVE_THRESHOLD = 250  # When to use progressive rendering
TABLE_RENDER_INTERVAL = 5  # Milliseconds between render batches

# Graph and Chart Performance
GRAPH_UPDATE_INTERVAL = 45000  # 45 seconds between graph updates
GRAPH_DATA_THROTTLE = 20000  # 20 seconds minimum between data updates
GRAPH_PAINT_OPTIMIZATION = True  # Use optimized painting

# Data Loading Performance  
OVERVIEW_REFRESH_INTERVAL = 60000  # 60 seconds between overview refreshes
INITIAL_LOAD_DELAY = 2500  # Delay before initial data load
RESOURCE_FETCH_TIMEOUT = 30000  # 30 seconds timeout for resource fetching

# Memory Management
MAX_CACHED_RESOURCES = 1000  # Maximum resources to keep in memory
CACHE_CLEANUP_INTERVAL = 300  # 5 minutes between cache cleanups
AGE_CACHE_SIZE = 5000  # Maximum age format cache entries

# UI Responsiveness
PROCESS_EVENTS_FREQUENCY = 200  # Process UI events every N operations
SEARCH_DEBOUNCE_MS = 300  # 300ms debounce for search
SCROLL_DEBOUNCE_MS = 100  # 100ms debounce for scrolling

# Thread Management
MAX_CONCURRENT_WORKERS = 3  # Maximum concurrent background workers
WORKER_TIMEOUT_MS = 30000  # 30 second timeout for workers

# Performance Profiles
PERFORMANCE_PROFILES = {
    "high_performance": {
        "table_batch_size": 50,
        "graph_update_interval": 60000,
        "overview_refresh_interval": 90000,
        "max_cached_resources": 500
    },
    "balanced": {
        "table_batch_size": 25,
        "graph_update_interval": 45000, 
        "overview_refresh_interval": 60000,
        "max_cached_resources": 1000
    },
    "responsive": {
        "table_batch_size": 15,
        "graph_update_interval": 30000,
        "overview_refresh_interval": 45000,
        "max_cached_resources": 1500
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
    """Apply performance optimizations based on system capabilities"""
    import psutil
    import os
    
    # Detect system resources
    cpu_count = os.cpu_count() or 4
    memory_gb = psutil.virtual_memory().total / (1024**3)
    
    # Choose profile based on system resources
    if memory_gb >= 16 and cpu_count >= 8:
        return get_performance_config("responsive")
    elif memory_gb >= 8 and cpu_count >= 4:
        return get_performance_config("balanced") 
    else:
        return get_performance_config("high_performance")