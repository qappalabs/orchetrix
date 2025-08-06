"""
Kubernetes API Service - Handles API client initialization and management
Split from kubernetes_client.py for better architecture
"""

import logging
import threading
from typing import Optional, Dict, Any
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


class LazyAPIClient:
    """Lazy initialization wrapper for Kubernetes API clients with thread safety"""
    
    def __init__(self, api_class):
        self.api_class = api_class
        self._instance = None
        self._lock = threading.Lock()
        self._initialization_failed = False
        self._last_error = None
    
    def __getattr__(self, name):
        # FIXED: Proper double-checked locking pattern
        if self._instance is None and not self._initialization_failed:
            with self._lock:
                # Double-check pattern to prevent race conditions
                if self._instance is None and not self._initialization_failed:
                    try:
                        # FIXED: Add proper error handling for API client creation
                        self._instance = self.api_class()
                        logging.debug(f"Successfully initialized {self.api_class.__name__}")
                    except Exception as e:
                        self._initialization_failed = True
                        self._last_error = str(e)
                        logging.error(f"Failed to initialize {self.api_class.__name__}: {e}")
                        # Don't raise here, let the check below handle it
        
        if self._initialization_failed:
            raise Exception(f"API client initialization failed: {self._last_error}")
            
        if self._instance is None:
            raise Exception(f"API client not initialized: {self.api_class.__name__}")
            
        return getattr(self._instance, name)
    
    def reset(self):
        """Reset the cached instance"""
        with self._lock:
            self._instance = None
            self._initialization_failed = False
            self._last_error = None
            logging.debug(f"Reset {self.api_class.__name__} lazy client")


class KubernetesAPIService:
    """Service for managing Kubernetes API clients"""
    
    def __init__(self):
        self._api_clients: Dict[str, LazyAPIClient] = {}
        self._cached_clients = False
        self._cached_context = None
        self._setup_lazy_clients()
    
    def _setup_lazy_clients(self):
        """Initialize lazy API clients"""
        self.v1 = LazyAPIClient(client.CoreV1Api)
        self.apps_v1 = LazyAPIClient(client.AppsV1Api)
        self.networking_v1 = LazyAPIClient(client.NetworkingV1Api)
        self.storage_v1 = LazyAPIClient(client.StorageV1Api)
        self.rbac_v1 = LazyAPIClient(client.RbacAuthorizationV1Api)
        self.batch_v1 = LazyAPIClient(client.BatchV1Api)
        self.autoscaling_v1 = LazyAPIClient(client.AutoscalingV1Api)
        self.custom_objects_api = LazyAPIClient(client.CustomObjectsApi)
        self.version_api = LazyAPIClient(client.VersionApi)
        
        self._api_clients = {
            'v1': self.v1,
            'apps_v1': self.apps_v1,
            'networking_v1': self.networking_v1,
            'storage_v1': self.storage_v1,
            'rbac_v1': self.rbac_v1,
            'batch_v1': self.batch_v1,
            'autoscaling_v1': self.autoscaling_v1,
            'custom_objects_api': self.custom_objects_api,
            'version_api': self.version_api,
        }
    
    def load_kube_config(self, context_name: Optional[str] = None):
        """Load kubernetes configuration for the specified context"""
        try:
            if context_name:
                config.load_kube_config(context=context_name)
                logging.info(f"Loaded kubeconfig for context: {context_name}")
            else:
                config.load_kube_config()
                logging.info("Loaded default kubeconfig")
            
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
    
    def get_api_client(self, client_type: str) -> LazyAPIClient:
        """Get a specific API client by type"""
        if client_type not in self._api_clients:
            raise ValueError(f"Unknown API client type: {client_type}")
        
        return self._api_clients[client_type]
    
    def is_connected(self) -> bool:
        """Check if API clients are properly initialized"""
        try:
            # Try to access the version API as a connectivity test
            version_info = self.version_api.get_code()
            logging.debug(f"Kubernetes API connectivity test successful: {version_info}")
            return version_info is not None
        except Exception as e:
            logging.error(f"Kubernetes API connectivity check failed: {type(e).__name__}: {e}")
            return False
    
    def get_cluster_version(self) -> Optional[str]:
        """Get Kubernetes cluster version"""
        try:
            version_info = self.version_api.get_code()
            return f"{version_info.major}.{version_info.minor}"
        except Exception as e:
            logging.error(f"Failed to get cluster version: {e}")
            return None
    
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