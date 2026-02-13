"""
Kubernetes API Configuration - Centralized settings for API client behavior
"""

# API Client Connection Settings
class APIClientConfig:
    """Centralized configuration for Kubernetes API clients"""
    
    # Connection Pool Settings
    CONNECTION_POOL_MAXSIZE = 10  # Maximum connections in pool
    
    # Timeout Settings (in seconds)
    SOCKET_TIMEOUT = 15  # Socket timeout for faster failure detection
    REQUEST_TIMEOUT = 30  # Request timeout for API calls
    CONNECT_TIMEOUT = 10  # Connection establishment timeout
    CONNECTIVITY_TEST_TIMEOUT = 10  # Timeout for connectivity tests
    
    # Specific Operation Timeouts
    DEPLOYMENT_OPERATION_TIMEOUT = 10  # Timeout for deployment operations
    ROLLBACK_OPERATION_TIMEOUT = 15  # Timeout for rollback operations
    NAMESPACE_OPERATION_TIMEOUT = 10  # Timeout for namespace operations
    METRICS_COLLECTION_TIMEOUT = 30  # Timeout for metrics collection
    RESOURCE_LIST_TIMEOUT = 10  # Timeout for resource listing operations
    SERVICE_DISCOVERY_TIMEOUT = 10  # Timeout for service discovery
    
    # Heavy Load Timeouts (for large clusters)
    HEAVY_LOAD_TIMEOUT = 20  # Timeout for operations under heavy load
    BATCH_OPERATION_TIMEOUT = 30  # Timeout for batch operations
    
    # Quick Operations
    VERSION_CHECK_TIMEOUT = 5  # Quick version check timeout
    
    # Retry Settings
    RETRIES = 5  # Number of retries for failed requests
    
    # Error Handling Settings
    MAX_CONSECUTIVE_TIMEOUTS = 3  # Max timeouts before stopping attempts
    MAX_INITIALIZATION_ATTEMPTS = 3  # Max attempts to initialize API clients
    
    @classmethod
    def get_optimized_configuration(cls):
        """Get optimized configuration dictionary for Kubernetes client"""
        return {
            'connection_pool_maxsize': cls.CONNECTION_POOL_MAXSIZE,
            'socket_timeout': cls.SOCKET_TIMEOUT,
            'request_timeout': cls.REQUEST_TIMEOUT,
            'connect_timeout': cls.CONNECT_TIMEOUT,
            'retries': cls.RETRIES
        }