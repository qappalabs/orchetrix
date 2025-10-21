"""
Resource Deletion Threads - Single and batch resource deletion
Split from base_resource_page.py for better architecture
"""

import logging
from PyQt6.QtCore import QThread, pyqtSignal
from kubernetes import client
from kubernetes.client.rest import ApiException
from Utils.kubernetes_client import get_kubernetes_client


class ResourceDeleterThread(QThread):
    """Thread for deleting a single Kubernetes resource"""
    delete_completed = pyqtSignal(bool, str, str, str)
    
    def __init__(self, resource_type, resource_name, namespace, parent=None):
        super().__init__(parent)
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace
        self.kube_client = get_kubernetes_client()
        self._is_running = True

    def stop(self):
        """Stop the deletion thread"""
        self._is_running = False

    def run(self):
        """Execute the resource deletion"""
        if not self._is_running:
            return
            
        try:
            delete_options = client.V1DeleteOptions()

            if self.resource_type == "pods":
                if self.namespace:
                    self.kube_client.v1.delete_namespaced_pod(
                        name=self.resource_name, 
                        namespace=self.namespace, 
                        body=delete_options
                    )
            elif self.resource_type == "services":
                self.kube_client.v1.delete_namespaced_service(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "deployments":
                self.kube_client.apps_v1.delete_namespaced_deployment(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "configmaps":
                self.kube_client.v1.delete_namespaced_config_map(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "secrets":
                self.kube_client.v1.delete_namespaced_secret(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "persistentvolumeclaims":
                self.kube_client.v1.delete_namespaced_persistent_volume_claim(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "persistentvolumes":
                self.kube_client.v1.delete_persistent_volume(
                    name=self.resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "ingresses":
                self.kube_client.networking_v1.delete_namespaced_ingress(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "daemonsets":
                self.kube_client.apps_v1.delete_namespaced_daemon_set(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "statefulsets":
                self.kube_client.apps_v1.delete_namespaced_stateful_set(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "replicasets":
                self.kube_client.apps_v1.delete_namespaced_replica_set(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "jobs":
                self.kube_client.batch_v1.delete_namespaced_job(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "cronjobs":
                self.kube_client.batch_v1.delete_namespaced_cron_job(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "namespaces":
                self.kube_client.v1.delete_namespace(
                    name=self.resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "nodes":
                self.kube_client.v1.delete_node(
                    name=self.resource_name, 
                    body=delete_options
                )
            # RBAC resources
            elif self.resource_type == "roles":
                self.kube_client.rbac_v1.delete_namespaced_role(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "rolebindings":
                self.kube_client.rbac_v1.delete_namespaced_role_binding(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "clusterroles":
                self.kube_client.rbac_v1.delete_cluster_role(
                    name=self.resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "clusterrolebindings":
                self.kube_client.rbac_v1.delete_cluster_role_binding(
                    name=self.resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "serviceaccounts":
                self.kube_client.v1.delete_namespaced_service_account(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            # Storage resources
            elif self.resource_type == "storageclasses":
                self.kube_client.storage_v1.delete_storage_class(
                    name=self.resource_name, 
                    body=delete_options
                )
            # Network resources
            elif self.resource_type == "networkpolicies":
                self.kube_client.networking_v1.delete_namespaced_network_policy(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "ingressclasses":
                self.kube_client.networking_v1.delete_ingress_class(
                    name=self.resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "endpoints":
                self.kube_client.v1.delete_namespaced_endpoints(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            # Config resources
            elif self.resource_type == "resourcequotas":
                self.kube_client.v1.delete_namespaced_resource_quota(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "limitranges":
                self.kube_client.v1.delete_namespaced_limit_range(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "horizontalpodautoscalers":
                self.kube_client.autoscaling_v1.delete_namespaced_horizontal_pod_autoscaler(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "poddisruptionbudgets":
                self.kube_client.policy_v1.delete_namespaced_pod_disruption_budget(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "events":
                self.kube_client.v1.delete_namespaced_event(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            elif self.resource_type == "leases":
                self.kube_client.coordination_v1.delete_namespaced_lease(
                    name=self.resource_name, 
                    namespace=self.namespace, 
                    body=delete_options
                )
            # Custom Resource Definitions
            elif self.resource_type == "customresourcedefinitions":
                self.kube_client.apiextensions_v1.delete_custom_resource_definition(
                    name=self.resource_name, 
                    body=delete_options
                )
            # Webhook configurations
            elif self.resource_type == "validatingwebhookconfigurations":
                self.kube_client.admissionregistration_v1.delete_validating_admission_webhook_configuration(
                    name=self.resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "mutatingwebhookconfigurations":
                self.kube_client.admissionregistration_v1.delete_mutating_admission_webhook_configuration(
                    name=self.resource_name, 
                    body=delete_options
                )
            # Priority and Runtime classes
            elif self.resource_type == "priorityclasses":
                self.kube_client.scheduling_v1.delete_priority_class(
                    name=self.resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "runtimeclasses":
                self.kube_client.node_v1.delete_runtime_class(
                    name=self.resource_name, 
                    body=delete_options
                )
            else:
                if not self._is_running:
                    return
                self.delete_completed.emit(
                    False, 
                    f"Deletion not implemented for {self.resource_type}", 
                    self.resource_name, 
                    self.namespace
                )
                return
                
            if not self._is_running:
                return
                
            self.delete_completed.emit(
                True, 
                f"{self.resource_type}/{self.resource_name} deleted", 
                self.resource_name, 
                self.namespace
            )
            
        except ApiException as e:
            if not self._is_running:
                return
            self.delete_completed.emit(
                False, 
                f"API error deleting: {e.reason}", 
                self.resource_name, 
                self.namespace
            )
        except Exception as e:
            if not self._is_running:
                return
            self.delete_completed.emit(
                False, 
                f"Error deleting: {str(e)}", 
                self.resource_name, 
                self.namespace
            )


class BatchResourceDeleterThread(QThread):
    """Thread for deleting multiple Kubernetes resources in batch"""
    batch_delete_progress = pyqtSignal(int, int)
    batch_delete_completed = pyqtSignal(list, list)
    
    def __init__(self, resource_type, resources_to_delete, parent=None):
        super().__init__(parent)
        self.resource_type = resource_type
        self.resources_to_delete = resources_to_delete
        self.kube_client = get_kubernetes_client()
        self._is_running = True

    def stop(self):
        """Stop the batch deletion thread"""
        self._is_running = False

    def run(self):
        """Execute batch resource deletion"""
        if not self._is_running:
            return
            
        success_list = []
        error_list = []
        total_count = len(self.resources_to_delete)
        
        for index, (resource_name, namespace) in enumerate(self.resources_to_delete):
            if not self._is_running:
                break
                
            try:
                # Emit progress update
                self.batch_delete_progress.emit(index, total_count)
                
                # Perform deletion based on resource type
                success = self._delete_single_resource(resource_name, namespace)
                
                if success:
                    success_list.append((resource_name, namespace))
                else:
                    error_list.append((resource_name, namespace, "Deletion method not implemented"))
                    
            except ApiException as e:
                if e.status == 404:
                    # Resource not found - log as warning instead of error for better UX
                    logging.warning(f"Resource {self.resource_type}/{resource_name} not found during delete (may have been deleted already)")
                    error_list.append((resource_name, namespace, f"Resource not found (may have been deleted already)"))
                else:
                    logging.error(f"API error deleting {self.resource_type}/{resource_name}: {e.reason}")
                    error_list.append((resource_name, namespace, f"API error: {e.reason}"))
            except Exception as e:
                logging.error(f"Unexpected error deleting {self.resource_type}/{resource_name}: {str(e)}")
                error_list.append((resource_name, namespace, f"Error: {str(e)}"))
        
        if self._is_running:
            # Emit final progress
            self.batch_delete_progress.emit(total_count, total_count)
            # Emit completion signal
            self.batch_delete_completed.emit(success_list, error_list)

    def _delete_single_resource(self, resource_name, namespace):
        """Delete a single resource based on type"""
        delete_options = client.V1DeleteOptions()
        
        try:
            if self.resource_type == "pods":
                if namespace:
                    self.kube_client.v1.delete_namespaced_pod(
                        name=resource_name, 
                        namespace=namespace, 
                        body=delete_options
                    )
            elif self.resource_type == "services":
                self.kube_client.v1.delete_namespaced_service(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "deployments":
                self.kube_client.apps_v1.delete_namespaced_deployment(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "configmaps":
                self.kube_client.v1.delete_namespaced_config_map(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "secrets":
                self.kube_client.v1.delete_namespaced_secret(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "persistentvolumeclaims":
                self.kube_client.v1.delete_namespaced_persistent_volume_claim(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "persistentvolumes":
                self.kube_client.v1.delete_persistent_volume(
                    name=resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "ingresses":
                self.kube_client.networking_v1.delete_namespaced_ingress(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "daemonsets":
                self.kube_client.apps_v1.delete_namespaced_daemon_set(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "statefulsets":
                self.kube_client.apps_v1.delete_namespaced_stateful_set(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "replicasets":
                self.kube_client.apps_v1.delete_namespaced_replica_set(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "jobs":
                self.kube_client.batch_v1.delete_namespaced_job(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "cronjobs":
                self.kube_client.batch_v1.delete_namespaced_cron_job(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "namespaces":
                self.kube_client.v1.delete_namespace(
                    name=resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "nodes":
                self.kube_client.v1.delete_node(
                    name=resource_name, 
                    body=delete_options
                )
            # RBAC resources
            elif self.resource_type == "roles":
                self.kube_client.rbac_v1.delete_namespaced_role(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "rolebindings":
                self.kube_client.rbac_v1.delete_namespaced_role_binding(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "clusterroles":
                self.kube_client.rbac_v1.delete_cluster_role(
                    name=resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "clusterrolebindings":
                self.kube_client.rbac_v1.delete_cluster_role_binding(
                    name=resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "serviceaccounts":
                self.kube_client.v1.delete_namespaced_service_account(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            # Storage resources
            elif self.resource_type == "storageclasses":
                self.kube_client.storage_v1.delete_storage_class(
                    name=resource_name, 
                    body=delete_options
                )
            # Network resources
            elif self.resource_type == "networkpolicies":
                self.kube_client.networking_v1.delete_namespaced_network_policy(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "ingressclasses":
                self.kube_client.networking_v1.delete_ingress_class(
                    name=resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "endpoints":
                self.kube_client.v1.delete_namespaced_endpoints(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            # Config resources
            elif self.resource_type == "resourcequotas":
                self.kube_client.v1.delete_namespaced_resource_quota(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "limitranges":
                self.kube_client.v1.delete_namespaced_limit_range(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "horizontalpodautoscalers":
                self.kube_client.autoscaling_v1.delete_namespaced_horizontal_pod_autoscaler(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "poddisruptionbudgets":
                self.kube_client.policy_v1.delete_namespaced_pod_disruption_budget(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "events":
                self.kube_client.v1.delete_namespaced_event(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            elif self.resource_type == "leases":
                self.kube_client.coordination_v1.delete_namespaced_lease(
                    name=resource_name, 
                    namespace=namespace, 
                    body=delete_options
                )
            # Custom Resource Definitions
            elif self.resource_type == "customresourcedefinitions":
                self.kube_client.apiextensions_v1.delete_custom_resource_definition(
                    name=resource_name, 
                    body=delete_options
                )
            # Webhook configurations
            elif self.resource_type == "validatingwebhookconfigurations":
                self.kube_client.admissionregistration_v1.delete_validating_admission_webhook_configuration(
                    name=resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "mutatingwebhookconfigurations":
                self.kube_client.admissionregistration_v1.delete_mutating_admission_webhook_configuration(
                    name=resource_name, 
                    body=delete_options
                )
            # Priority and Runtime classes
            elif self.resource_type == "priorityclasses":
                self.kube_client.scheduling_v1.delete_priority_class(
                    name=resource_name, 
                    body=delete_options
                )
            elif self.resource_type == "runtimeclasses":
                self.kube_client.node_v1.delete_runtime_class(
                    name=resource_name, 
                    body=delete_options
                )
            else:
                # Resource type not supported
                logging.warning(f"Delete operation not implemented for resource type: {self.resource_type}")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Error deleting {resource_name}: {e}")
            raise e