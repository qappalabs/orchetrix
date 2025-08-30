"""
Kubernetes API Service - Handles API client initialization and management
Split from kubernetes_client.py for better architecture
"""

import logging
import threading
from typing import Optional, Dict, Any
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


class ThreadSafeAPIClient:
    """Thread-safe wrapper for Kubernetes API clients with proper error isolation"""
    
    def __init__(self, api_class):
        self.api_class = api_class
        self._instance = None
        self._lock = threading.RLock()  # Use RLock for better thread safety
        self._initialization_failed = False
        self._initialization_error = None
        self._creation_attempts = 0
        self._max_attempts = 3
    
    def get_instance(self):
        """Thread-safe instance getter with proper error isolation"""
        # Fast path: if we already have an instance, return it
        if self._instance is not None:
            return self._instance
            
        # Slow path: need to create instance
        with self._lock:
            # Double-check pattern with proper error handling
            if self._instance is not None:
                return self._instance
                
            # Check if we've permanently failed
            if self._initialization_failed:
                raise self._initialization_error
                
            # Attempt to create instance
            try:
                self._creation_attempts += 1
                if self._creation_attempts > self._max_attempts:
                    self._initialization_failed = True
                    self._initialization_error = Exception(
                        f"Max initialization attempts ({self._max_attempts}) exceeded for {self.api_class.__name__}"
                    )
                    raise self._initialization_error
                
                logging.debug(f"Creating API client instance: {self.api_class.__name__} (attempt {self._creation_attempts})")
                self._instance = self.api_class()
                logging.debug(f"Successfully initialized {self.api_class.__name__}")
                return self._instance
                
            except Exception as e:
                logging.error(f"Failed to initialize {self.api_class.__name__} (attempt {self._creation_attempts}): {e}")
                
                # On final attempt, mark as permanently failed
                if self._creation_attempts >= self._max_attempts:
                    self._initialization_failed = True
                    self._initialization_error = Exception(
                        f"Failed to initialize {self.api_class.__name__} after {self._creation_attempts} attempts: {str(e)}"
                    )
                    raise self._initialization_error
                
                # For non-final attempts, re-raise the original exception
                raise
    
    def __getattr__(self, name):
        """Delegate attribute access to the API client instance"""
        instance = self.get_instance()
        return getattr(instance, name)
    
    def reset(self):
        """Reset the cached instance and error state"""
        with self._lock:
            self._instance = None
            self._initialization_failed = False
            self._initialization_error = None
            self._creation_attempts = 0
            logging.debug(f"Reset {self.api_class.__name__} API client")
    
    def is_initialized(self):
        """Check if the API client is initialized without triggering initialization"""
        return self._instance is not None
    
    def has_failed(self):
        """Check if initialization has permanently failed"""
        return self._initialization_failed


class KubernetesAPIService:
    """Service for managing Kubernetes API clients"""
    
    def __init__(self):
        self._api_clients: Dict[str, ThreadSafeAPIClient] = {}
        self._cached_clients = False
        self._cached_context = None
        self._setup_lazy_clients()
    
    def _setup_lazy_clients(self):
        """Initialize thread-safe API clients"""
        self._api_clients = {
            'CoreV1Api': ThreadSafeAPIClient(client.CoreV1Api),
            'AppsV1Api': ThreadSafeAPIClient(client.AppsV1Api),
            'NetworkingV1Api': ThreadSafeAPIClient(client.NetworkingV1Api),
            'StorageV1Api': ThreadSafeAPIClient(client.StorageV1Api),
            'RbacAuthorizationV1Api': ThreadSafeAPIClient(client.RbacAuthorizationV1Api),
            'BatchV1Api': ThreadSafeAPIClient(client.BatchV1Api),
            'AutoscalingV1Api': ThreadSafeAPIClient(client.AutoscalingV1Api),
            'AutoscalingV2Api': ThreadSafeAPIClient(client.AutoscalingV2Api),
            'PolicyV1Api': ThreadSafeAPIClient(client.PolicyV1Api),
            'SchedulingV1Api': ThreadSafeAPIClient(client.SchedulingV1Api),
            'NodeV1Api': ThreadSafeAPIClient(client.NodeV1Api),
            'AdmissionregistrationV1Api': ThreadSafeAPIClient(client.AdmissionregistrationV1Api),
            'CoordinationV1Api': ThreadSafeAPIClient(client.CoordinationV1Api),
            'ApiextensionsV1Api': ThreadSafeAPIClient(client.ApiextensionsV1Api),
            'CustomObjectsApi': ThreadSafeAPIClient(client.CustomObjectsApi),
            'VersionApi': ThreadSafeAPIClient(client.VersionApi),
        }
    
    def load_kube_config(self, context_name: Optional[str] = None):
        """Load kubernetes configuration with connection optimization"""
        try:
            if context_name:
                config.load_kube_config(context=context_name)
                logging.info(f"Loaded kubeconfig for context: {context_name}")
            else:
                config.load_kube_config()
                logging.info("Loaded default kubeconfig")
            
            # Configure API client settings for better performance and reliability
            configuration = client.Configuration.get_default_copy()
            
            # Connection pooling settings for better performance
            configuration.connection_pool_maxsize = 10  # Increase connection pool size
            
            # Timeout settings for better reliability with slow clusters
            configuration.socket_timeout = 30  # 30 seconds socket timeout
            configuration.request_timeout = 60  # 60 seconds request timeout
            
            # Retry settings for better reliability
            configuration.retries = 3
            
            # Apply optimized configuration
            client.Configuration.set_default(configuration)
            logging.debug("Applied optimized Kubernetes API client configuration")
            
            # Reset clients when context changes
            if self._cached_context != context_name:
                self.reset_clients()
                self._cached_context = context_name
                self._cached_clients = True
                
            return True
            
        except ConfigException as e:
            logging.error(f"Failed to load kubeconfig: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error loading kubeconfig: {e}")
            return False
    
    def reset_clients(self):
        """Reset all API clients - useful when switching contexts"""
        logging.debug("Resetting all API clients")
        for client_name, api_client in self._api_clients.items():
            try:
                api_client.reset()
            except Exception as e:
                logging.error(f"Error resetting {client_name}: {e}")
        
        self._cached_clients = False
        self._cached_context = None
    
    def get_api_client(self, client_type: str) -> ThreadSafeAPIClient:
        """Get a specific API client by type"""
        if client_type not in self._api_clients:
            raise ValueError(f"Unknown API client type: {client_type}")
        
        return self._api_clients[client_type]
    
    def is_connected(self) -> bool:
        """Check if API clients are properly initialized with improved error handling"""
        try:
            # Try to access the version API as a connectivity test with timeout
            version_info = self.version_api.get_code(_request_timeout=10)
            logging.debug(f"Kubernetes API connectivity test successful: {version_info}")
            return version_info is not None
        except Exception as e:
            # Classify error types for better handling
            error_type = type(e).__name__
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                logging.warning(f"Kubernetes API connectivity timeout: {e}")
            elif "connection" in str(e).lower() or "refused" in str(e).lower():
                logging.warning(f"Kubernetes API connection refused: {e}")
            elif "unauthorized" in str(e).lower() or "forbidden" in str(e).lower():
                logging.error(f"Kubernetes API authentication/authorization error: {e}")
            else:
                logging.error(f"Kubernetes API connectivity check failed: {error_type}: {e}")
            return False
    
    def get_cluster_version(self) -> Optional[str]:
        """Get Kubernetes cluster version"""
        try:
            version_info = self.version_api.get_code()
            return f"{version_info.major}.{version_info.minor}"
        except Exception as e:
            logging.error(f"Failed to get cluster version: {e}")
            return None
    
    # API client properties for backward compatibility
    @property
    def v1(self):
        """Get CoreV1Api client"""
        return self.get_api_client('CoreV1Api').get_instance()
    
    @property
    def apps_v1(self):
        """Get AppsV1Api client"""
        return self.get_api_client('AppsV1Api').get_instance()
    
    @property
    def networking_v1(self):
        """Get NetworkingV1Api client"""
        return self.get_api_client('NetworkingV1Api').get_instance()
    
    @property
    def storage_v1(self):
        """Get StorageV1Api client"""
        return self.get_api_client('StorageV1Api').get_instance()
    
    @property
    def rbac_v1(self):
        """Get RbacAuthorizationV1Api client"""
        return self.get_api_client('RbacAuthorizationV1Api').get_instance()
    
    @property
    def batch_v1(self):
        """Get BatchV1Api client"""
        return self.get_api_client('BatchV1Api').get_instance()
    
    @property
    def autoscaling_v1(self):
        """Get AutoscalingV1Api client"""
        return self.get_api_client('AutoscalingV1Api').get_instance()
    
    @property
    def autoscaling_v2(self):
        """Get AutoscalingV2Api client"""
        return self.get_api_client('AutoscalingV2Api').get_instance()
    
    @property
    def policy_v1(self):
        """Get PolicyV1Api client"""
        return self.get_api_client('PolicyV1Api').get_instance()
    
    @property
    def scheduling_v1(self):
        """Get SchedulingV1Api client"""
        return self.get_api_client('SchedulingV1Api').get_instance()
    
    @property
    def node_v1(self):
        """Get NodeV1Api client"""
        return self.get_api_client('NodeV1Api').get_instance()
    
    @property
    def admissionregistration_v1(self):
        """Get AdmissionregistrationV1Api client"""
        return self.get_api_client('AdmissionregistrationV1Api').get_instance()
    
    @property
    def coordination_v1(self):
        """Get CoordinationV1Api client"""
        return self.get_api_client('CoordinationV1Api').get_instance()
    
    @property
    def apiextensions_v1(self):
        """Get ApiextensionsV1Api client"""
        return self.get_api_client('ApiextensionsV1Api').get_instance()
    
    @property
    def custom_objects_api(self):
        """Get CustomObjectsApi client"""
        return self.get_api_client('CustomObjectsApi').get_instance()
    
    @property
    def version_api(self):
        """Get VersionApi client"""
        return self.get_api_client('VersionApi').get_instance()
    
    def cleanup(self):
        """Cleanup API service resources"""
        logging.debug("Cleaning up KubernetesAPIService")
        self.reset_clients()
        self._api_clients.clear()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            if hasattr(self, '_api_clients'):
                self.cleanup()
        except Exception as e:
            logging.error(f"Error in KubernetesAPIService destructor: {e}")


# Singleton instance
_api_service_instance = None

def get_kubernetes_api_service() -> KubernetesAPIService:
    """Get or create Kubernetes API service singleton"""
    global _api_service_instance
    if _api_service_instance is None:
        _api_service_instance = KubernetesAPIService()
    return _api_service_instance

def reset_kubernetes_api_service():
    """Reset the singleton instance"""
    global _api_service_instance
    if _api_service_instance:
        _api_service_instance.cleanup()
    _api_service_instance = None


# Backward compatibility alias
LazyAPIClient = ThreadSafeAPIClient