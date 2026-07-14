"""
Kubernetes API Service - Handles API client initialization and management
Split from kubernetes_client.py for better architecture
"""

import logging
import threading
from typing import Optional, Dict, Any

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

from .api_config import APIClientConfig

__all__ = [
    'ThreadSafeAPIClient',
    'KubernetesAPIService',
    'get_kubernetes_api_service',
    'reset_kubernetes_api_service',
    'LazyAPIClient'
]

class ThreadSafeAPIClient:
    """Thread-safe wrapper for Kubernetes API clients with proper error isolation"""

    def __init__(self, api_class):
        self.api_class = api_class
        self._instance = None
        self._lock = threading.RLock()  # Use RLock for better thread safety
        self._initialization_failed = False
        self._initialization_error = None
        self._creation_attempts = 0
        self._max_attempts = APIClientConfig.MAX_INITIALIZATION_ATTEMPTS

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

class KubernetesAPIService:
    """Service for managing Kubernetes API clients"""

    def __init__(self):
        self._api_clients: Dict[str, ThreadSafeAPIClient] = {}
        self._cached_clients = False
        self._cached_context = None
        self._consecutive_timeouts = 0
        self._max_consecutive_timeouts = APIClientConfig.MAX_CONSECUTIVE_TIMEOUTS
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

            # Apply optimized configuration from centralized config
            config_values = APIClientConfig.get_optimized_configuration()
            
            # Connection pooling settings for better performance
            configuration.connection_pool_maxsize = config_values['connection_pool_maxsize']

            # Timeout settings for better reliability with slow clusters
            configuration.socket_timeout = config_values['socket_timeout']
            configuration.request_timeout = config_values['request_timeout']

            # Retry settings for better reliability
            configuration.retries = config_values['retries']

            # Additional timeout configurations
            if hasattr(configuration, 'connect_timeout'):
                configuration.connect_timeout = config_values['connect_timeout']

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
        logging.debug(f"API Service: Getting API client for type: {client_type}")
        if client_type not in self._api_clients:
            logging.error(f"API Service: Unknown API client type requested: {client_type}")
            raise ValueError(f"Unknown API client type: {client_type}")

        logging.debug(f"API Service: Successfully retrieved {client_type} client")
        return self._api_clients[client_type]

    def is_connected(self) -> bool:
        """Check if API clients are properly initialized with improved error handling"""
        # Skip check if we've had too many consecutive timeouts
        if self._consecutive_timeouts >= self._max_consecutive_timeouts:
            logging.debug("API Service: Skipping connectivity check due to consecutive timeout limit")
            return False

        logging.debug("API Service: Checking Kubernetes API connectivity for node operations")
        try:
            # Try to access the version API as a connectivity test with timeout
            logging.debug("API Service: Attempting to connect to Kubernetes API server")
            version_info = self.version_api.get_code(_request_timeout=APIClientConfig.CONNECTIVITY_TEST_TIMEOUT)
            logging.debug(f"API Service: Kubernetes API connectivity test successful: {version_info}")
            logging.info("API Service: Successfully connected to Kubernetes API - nodes API ready")

            # Reset timeout counters on successful connection
            self._consecutive_timeouts = 0

            return version_info is not None
        except Exception as e:
            # Classify error types for better handling
            error_type = type(e).__name__
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                self._consecutive_timeouts += 1
                logging.warning(f"API Service: Kubernetes API connectivity timeout #{self._consecutive_timeouts} - node operations unavailable: {e}")

                # Stop trying after max consecutive timeouts to prevent resource exhaustion
                if self._consecutive_timeouts >= self._max_consecutive_timeouts:
                    logging.error(f"API Service: Maximum consecutive timeouts ({self._max_consecutive_timeouts}) reached. Stopping connection attempts to prevent resource exhaustion.")
                    return False
            elif "connection" in str(e).lower() or "refused" in str(e).lower():
                logging.warning(f"API Service: Kubernetes API connection refused - cluster may be down: {e}")
            elif "unauthorized" in str(e).lower() or "forbidden" in str(e).lower():
                logging.error(f"API Service: Kubernetes API authentication/authorization error - check kubeconfig: {e}")
            else:
                logging.error(f"API Service: Kubernetes API connectivity check failed: {error_type}: {e}")
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
        logging.debug("API Service: Accessing CoreV1Api client for node operations")
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

    def delete_resource(self, resource_type: str, name: str, namespace: Optional[str] = None) -> bool:
        """
        Unified method to delete a Kubernetes resource by type, name, and namespace.
        Returns True on success, raises Exception on failure.
        """
        namespaced_types = {
            "pods", "services", "deployments", "configmaps", "secrets",
            "persistentvolumeclaims", "ingresses", "daemonsets", "statefulsets",
            "replicasets", "jobs", "cronjobs", "roles", "rolebindings",
            "serviceaccounts", "networkpolicies", "endpoints", "resourcequotas",
            "limitranges", "horizontalpodautoscalers", "poddisruptionbudgets",
            "events", "leases"
        }
        if resource_type in namespaced_types and not namespace:
            raise ValueError(
                f"Namespace is required to delete a namespaced resource: {resource_type}/{name}"
            )

        try:
            delete_options = client.V1DeleteOptions()
            api_client = self._get_client_for_deletion(resource_type)

            # Map resource types to specific deletion methods
            # Namespaced resources
            if resource_type == "pods":
                api_client.delete_namespaced_pod(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "services":
                api_client.delete_namespaced_service(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "deployments":
                api_client.delete_namespaced_deployment(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "configmaps":
                api_client.delete_namespaced_config_map(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "secrets":
                api_client.delete_namespaced_secret(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "persistentvolumeclaims":
                api_client.delete_namespaced_persistent_volume_claim(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "ingresses":
                api_client.delete_namespaced_ingress(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "daemonsets":
                api_client.delete_namespaced_daemon_set(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "statefulsets":
                api_client.delete_namespaced_stateful_set(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "replicasets":
                api_client.delete_namespaced_replica_set(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "jobs":
                api_client.delete_namespaced_job(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "cronjobs":
                api_client.delete_namespaced_cron_job(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "roles":
                api_client.delete_namespaced_role(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "rolebindings":
                api_client.delete_namespaced_role_binding(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "serviceaccounts":
                api_client.delete_namespaced_service_account(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "networkpolicies":
                api_client.delete_namespaced_network_policy(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "endpoints":
                api_client.delete_namespaced_endpoints(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "resourcequotas":
                api_client.delete_namespaced_resource_quota(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "limitranges":
                api_client.delete_namespaced_limit_range(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "horizontalpodautoscalers":
                api_client.delete_namespaced_horizontal_pod_autoscaler(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "poddisruptionbudgets":
                api_client.delete_namespaced_pod_disruption_budget(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "events":
                api_client.delete_namespaced_event(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "leases":
                api_client.delete_namespaced_lease(name=name, namespace=namespace, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)

            # Cluster-wide resources
            elif resource_type == "namespaces":
                api_client.delete_namespace(name=name, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "nodes":
                api_client.delete_node(name=name, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "persistentvolumes":
                api_client.delete_persistent_volume(name=name, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "clusterroles":
                api_client.delete_cluster_role(name=name, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "clusterrolebindings":
                api_client.delete_cluster_role_binding(name=name, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "storageclasses":
                api_client.delete_storage_class(name=name, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "ingressclasses":
                api_client.delete_ingress_class(name=name, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "customresourcedefinitions":
                api_client.delete_custom_resource_definition(name=name, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "validatingwebhookconfigurations":
                api_client.delete_validating_admission_webhook_configuration(name=name, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "mutatingwebhookconfigurations":
                api_client.delete_mutating_admission_webhook_configuration(name=name, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "priorityclasses":
                api_client.delete_priority_class(name=name, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            elif resource_type == "runtimeclasses":
                api_client.delete_runtime_class(name=name, body=delete_options, _request_timeout=APIClientConfig.REQUEST_TIMEOUT)
            else:
                logging.error(f"Deletion logic not implemented for resource type: {resource_type}")
                raise ValueError(f"Unsupported resource type for deletion: {resource_type}")

            location = f"{resource_type}/{name}"
            if namespace:
                location += f" in namespace {namespace}"
            logging.info(f"Successfully deleted {location}")
            return True

        except Exception as e:
            logging.error(f"Failed to delete {resource_type}/{name}: {e}")
            raise

    def _get_client_for_deletion(self, resource_type: str):
        """Map resource type to the appropriate API client instance."""
        v1_types = [
            "pods", "services", "namespaces", "nodes", "configmaps", "secrets",
            "persistentvolumes", "persistentvolumeclaims", "serviceaccounts",
            "endpoints", "resourcequotas", "limitranges", "events"
        ]
        apps_v1_types = ["deployments", "daemonsets", "statefulsets", "replicasets"]
        batch_v1_types = ["jobs", "cronjobs"]
        networking_v1_types = ["ingresses", "ingressclasses", "networkpolicies"]
        rbac_v1_types = ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
        storage_v1_types = ["storageclasses"]
        policy_v1_types = ["poddisruptionbudgets"]
        autoscaling_v1_types = ["horizontalpodautoscalers"] # Can be v1 or v2, v1 is common for delete
        coordination_v1_types = ["leases"]
        apiextensions_v1_types = ["customresourcedefinitions"]
        admission_v1_types = ["validatingwebhookconfigurations", "mutatingwebhookconfigurations"]
        scheduling_v1_types = ["priorityclasses"]
        node_v1_types = ["runtimeclasses"]

        if resource_type in v1_types:
            return self.v1
        if resource_type in apps_v1_types:
            return self.apps_v1
        if resource_type in batch_v1_types:
            return self.batch_v1
        if resource_type in networking_v1_types:
            return self.networking_v1
        if resource_type in rbac_v1_types:
            return self.rbac_v1
        if resource_type in storage_v1_types:
            return self.storage_v1
        if resource_type in policy_v1_types:
            return self.policy_v1
        if resource_type in autoscaling_v1_types:
            return self.autoscaling_v1
        if resource_type in coordination_v1_types:
            return self.coordination_v1
        if resource_type in apiextensions_v1_types:
            return self.apiextensions_v1
        if resource_type in admission_v1_types:
            return self.admissionregistration_v1
        if resource_type in scheduling_v1_types:
            return self.scheduling_v1
        if resource_type in node_v1_types:
            return self.node_v1
            
        raise ValueError(f"No API client mapping for resource type: {resource_type}")

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


# Singleton instance with thread-safe initialization
_api_service_instance = None

# Utilizing RLock rather than standard Lock defensively. While no direct
# recursive acquisition currently exists within the module, future cleanup
# routines, audit logging, and potential PyQt6 GUI event hooks originating
# from within the locked section might indirectly re-query the service getter.
# An RLock prevents catastrophic silent self-deadlocking in these complex nested scenarios.
_api_service_lock = threading.RLock()

def get_kubernetes_api_service() -> KubernetesAPIService:
    """Get or create Kubernetes API service singleton with thread-safe initialization"""
    global _api_service_instance
    
    # Fast path: if instance exists, return it
    if _api_service_instance is not None:
        return _api_service_instance
    
    # Slow path: need to create instance with thread safety
    with _api_service_lock:
        # Double-checked locking: re-check after acquiring lock
        if _api_service_instance is None:
            _api_service_instance = KubernetesAPIService()
        return _api_service_instance

def reset_kubernetes_api_service():
    """Reset the singleton instance safely across multiple threads."""
    global _api_service_instance
    with _api_service_lock:
        if _api_service_instance:
            try:
                _api_service_instance.cleanup()
            finally:
                _api_service_instance = None


# Backward compatibility alias
LazyAPIClient = ThreadSafeAPIClient
