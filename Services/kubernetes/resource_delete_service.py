"""
Kubernetes Resource Delete Service (MVC Model Layer)
Handles all delete operations for Kubernetes resources following MVC architecture
"""

import logging
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from kubernetes import client
from kubernetes.client.rest import ApiException
from Utils.kubernetes_client import get_kubernetes_client


@dataclass
class DeleteResult:
    """Result of a delete operation"""
    success: bool
    resource_name: str
    resource_type: str
    namespace: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0


@dataclass
class BatchDeleteResult:
    """Result of a batch delete operation"""
    total_requested: int
    successful_deletes: List[DeleteResult]
    failed_deletes: List[DeleteResult]
    execution_time_ms: float = 0
    
    @property
    def success_count(self) -> int:
        return len(self.successful_deletes)
    
    @property
    def failure_count(self) -> int:
        return len(self.failed_deletes)
    
    @property
    def overall_success(self) -> bool:
        return self.failure_count == 0


class KubernetesResourceDeleteService:
    """
    Service layer for deleting Kubernetes resources (MVC Model)
    Handles all delete operations with proper error handling and logging
    """
    
    def __init__(self):
        self.kube_client = get_kubernetes_client()
        self._delete_method_mapping = self._build_delete_method_mapping()
    
    def _build_delete_method_mapping(self) -> Dict[str, Dict[str, any]]:
        """Build mapping of resource types to their delete methods"""
        return {
            # Core v1 resources (namespaced)
            'pods': {
                'api': self.kube_client.v1,
                'method': 'delete_namespaced_pod',
                'namespaced': True
            },
            'services': {
                'api': self.kube_client.v1,
                'method': 'delete_namespaced_service',
                'namespaced': True
            },
            'configmaps': {
                'api': self.kube_client.v1,
                'method': 'delete_namespaced_config_map',
                'namespaced': True
            },
            'secrets': {
                'api': self.kube_client.v1,
                'method': 'delete_namespaced_secret',
                'namespaced': True
            },
            'endpoints': {
                'api': self.kube_client.v1,
                'method': 'delete_namespaced_endpoints',
                'namespaced': True
            },
            'events': {
                'api': self.kube_client.v1,
                'method': 'delete_namespaced_event',
                'namespaced': True
            },
            'persistentvolumeclaims': {
                'api': self.kube_client.v1,
                'method': 'delete_namespaced_persistent_volume_claim',
                'namespaced': True
            },
            'resourcequotas': {
                'api': self.kube_client.v1,
                'method': 'delete_namespaced_resource_quota',
                'namespaced': True
            },
            'limitranges': {
                'api': self.kube_client.v1,
                'method': 'delete_namespaced_limit_range',
                'namespaced': True
            },
            'serviceaccounts': {
                'api': self.kube_client.v1,
                'method': 'delete_namespaced_service_account',
                'namespaced': True
            },
            
            # Core v1 resources (cluster-scoped)
            'nodes': {
                'api': self.kube_client.v1,
                'method': 'delete_node',
                'namespaced': False
            },
            'namespaces': {
                'api': self.kube_client.v1,
                'method': 'delete_namespace',
                'namespaced': False
            },
            'persistentvolumes': {
                'api': self.kube_client.v1,
                'method': 'delete_persistent_volume',
                'namespaced': False
            },
            
            # Apps v1 resources
            'deployments': {
                'api': self.kube_client.apps_v1,
                'method': 'delete_namespaced_deployment',
                'namespaced': True
            },
            'replicasets': {
                'api': self.kube_client.apps_v1,
                'method': 'delete_namespaced_replica_set',
                'namespaced': True
            },
            'daemonsets': {
                'api': self.kube_client.apps_v1,
                'method': 'delete_namespaced_daemon_set',
                'namespaced': True
            },
            'statefulsets': {
                'api': self.kube_client.apps_v1,
                'method': 'delete_namespaced_stateful_set',
                'namespaced': True
            },
            
            # Networking v1 resources
            'ingresses': {
                'api': self.kube_client.networking_v1,
                'method': 'delete_namespaced_ingress',
                'namespaced': True
            },
            'networkpolicies': {
                'api': self.kube_client.networking_v1,
                'method': 'delete_namespaced_network_policy',
                'namespaced': True
            },
            'ingressclasses': {
                'api': self.kube_client.networking_v1,
                'method': 'delete_ingress_class',
                'namespaced': False
            },
            
            # Storage v1 resources
            'storageclasses': {
                'api': self.kube_client.storage_v1,
                'method': 'delete_storage_class',
                'namespaced': False
            },
            
            # Batch v1 resources
            'jobs': {
                'api': self.kube_client.batch_v1,
                'method': 'delete_namespaced_job',
                'namespaced': True
            },
            'cronjobs': {
                'api': self.kube_client.batch_v1,
                'method': 'delete_namespaced_cron_job',
                'namespaced': True
            },
            
            # RBAC v1 resources
            'roles': {
                'api': self.kube_client.rbac_v1,
                'method': 'delete_namespaced_role',
                'namespaced': True
            },
            'rolebindings': {
                'api': self.kube_client.rbac_v1,
                'method': 'delete_namespaced_role_binding',
                'namespaced': True
            },
            'clusterroles': {
                'api': self.kube_client.rbac_v1,
                'method': 'delete_cluster_role',
                'namespaced': False
            },
            'clusterrolebindings': {
                'api': self.kube_client.rbac_v1,
                'method': 'delete_cluster_role_binding',
                'namespaced': False
            },
            
            # Policy v1 resources
            'poddisruptionbudgets': {
                'api': self.kube_client.policy_v1,
                'method': 'delete_namespaced_pod_disruption_budget',
                'namespaced': True
            },
            
            # Autoscaling v1/v2 resources
            'horizontalpodautoscalers': {
                'api': self.kube_client.autoscaling_v1,
                'method': 'delete_namespaced_horizontal_pod_autoscaler',
                'namespaced': True
            },
            
            # Custom Resources
            'customresourcedefinitions': {
                'api': self.kube_client.apiextensions_v1,
                'method': 'delete_custom_resource_definition',
                'namespaced': False
            }
        }
    
    def delete_resource(self, resource_type: str, resource_name: str, namespace: Optional[str] = None) -> DeleteResult:
        """
        Delete a single Kubernetes resource
        
        Args:
            resource_type: Type of resource (e.g., 'pods', 'services')
            resource_name: Name of the resource to delete
            namespace: Namespace (required for namespaced resources)
            
        Returns:
            DeleteResult with success/failure information
        """
        start_time = time.time()
        
        try:
            # Get delete method configuration
            delete_config = self._delete_method_mapping.get(resource_type.lower())
            if not delete_config:
                return DeleteResult(
                    success=False,
                    resource_name=resource_name,
                    resource_type=resource_type,
                    namespace=namespace,
                    error_message=f"Delete operation not supported for resource type: {resource_type}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Validate namespace requirement
            if delete_config['namespaced'] and not namespace:
                return DeleteResult(
                    success=False,
                    resource_name=resource_name,
                    resource_type=resource_type,
                    namespace=namespace,
                    error_message=f"Namespace is required for resource type: {resource_type}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Execute delete operation
            api_client = delete_config['api']
            delete_method = getattr(api_client, delete_config['method'])
            
            # Create delete options
            delete_options = client.V1DeleteOptions(
                grace_period_seconds=30,  # Allow graceful shutdown
                propagation_policy='Foreground'  # Ensure dependent resources are deleted
            )
            
            # Call appropriate delete method
            if delete_config['namespaced']:
                delete_method(
                    name=resource_name,
                    namespace=namespace,
                    body=delete_options
                )
            else:
                delete_method(
                    name=resource_name,
                    body=delete_options
                )
            
            execution_time = (time.time() - start_time) * 1000
            logging.info(f"Successfully deleted {resource_type} '{resource_name}' in {execution_time:.1f}ms")
            
            return DeleteResult(
                success=True,
                resource_name=resource_name,
                resource_type=resource_type,
                namespace=namespace,
                execution_time_ms=execution_time
            )
            
        except ApiException as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Kubernetes API error: {e.status} - {e.reason}"
            
            # Handle specific error codes
            if e.status == 404:
                error_msg = f"Resource '{resource_name}' not found"
            elif e.status == 403:
                error_msg = f"Permission denied to delete '{resource_name}'"
            elif e.status == 409:
                error_msg = f"Conflict while deleting '{resource_name}' - resource may have dependencies"
            
            logging.error(f"Failed to delete {resource_type} '{resource_name}': {error_msg}")
            
            return DeleteResult(
                success=False,
                resource_name=resource_name,
                resource_type=resource_type,
                namespace=namespace,
                error_message=error_msg,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Unexpected error: {str(e)}"
            logging.error(f"Failed to delete {resource_type} '{resource_name}': {error_msg}")
            
            return DeleteResult(
                success=False,
                resource_name=resource_name,
                resource_type=resource_type,
                namespace=namespace,
                error_message=error_msg,
                execution_time_ms=execution_time
            )
    
    def delete_resources_batch(self, resource_type: str, resource_items: List[Tuple[str, str]]) -> BatchDeleteResult:
        """
        Delete multiple resources in batch
        
        Args:
            resource_type: Type of resources to delete
            resource_items: List of (resource_name, namespace) tuples
            
        Returns:
            BatchDeleteResult with detailed results for each resource
        """
        start_time = time.time()
        successful_deletes = []
        failed_deletes = []
        
        logging.info(f"Starting batch delete of {len(resource_items)} {resource_type}")
        
        for resource_name, namespace in resource_items:
            result = self.delete_resource(resource_type, resource_name, namespace)
            
            if result.success:
                successful_deletes.append(result)
            else:
                failed_deletes.append(result)
            
            # Small delay between deletes to avoid overwhelming the API
            time.sleep(0.1)
        
        execution_time = (time.time() - start_time) * 1000
        
        logging.info(f"Batch delete completed: {len(successful_deletes)} successful, {len(failed_deletes)} failed in {execution_time:.1f}ms")
        
        return BatchDeleteResult(
            total_requested=len(resource_items),
            successful_deletes=successful_deletes,
            failed_deletes=failed_deletes,
            execution_time_ms=execution_time
        )
    
    def is_delete_supported(self, resource_type: str) -> bool:
        """Check if delete operation is supported for the resource type"""
        return resource_type.lower() in self._delete_method_mapping
    
    def get_supported_resource_types(self) -> List[str]:
        """Get list of all supported resource types for deletion"""
        return list(self._delete_method_mapping.keys())


# Global service instance
_resource_delete_service = None

def get_resource_delete_service() -> KubernetesResourceDeleteService:
    """Get the global resource delete service instance"""
    global _resource_delete_service
    if _resource_delete_service is None:
        _resource_delete_service = KubernetesResourceDeleteService()
    return _resource_delete_service