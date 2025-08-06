"""
Resource Loader - Thread for loading resources based on namespace and workload type
Split from AppsChartPage.py for better architecture
"""

from PyQt6.QtCore import QThread, pyqtSignal
from utils.kubernetes_client import get_kubernetes_client
from kubernetes.client.rest import ApiException


class ResourceLoader(QThread):
    """Thread for loading resources based on namespace and workload type"""
    resources_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, namespace, workload_type, parent=None):
        super().__init__(parent)
        self.namespace = namespace
        self.workload_type = workload_type.lower()
        self.kube_client = get_kubernetes_client()
    
    def run(self):
        try:
            if not self.kube_client or not self.kube_client.v1 or not self.kube_client.apps_v1:
                self.error_occurred.emit("Kubernetes client not initialized")
                return
            
            resources = []
            
            if self.workload_type == "pods":
                if self.namespace == "All Namespaces":
                    resource_list = self.kube_client.v1.list_pod_for_all_namespaces()
                else:
                    resource_list = self.kube_client.v1.list_namespaced_pod(namespace=self.namespace)
                resources = [f"{item.metadata.name} ({item.metadata.namespace})" if self.namespace == "All Namespaces" else item.metadata.name for item in resource_list.items]
                
            elif self.workload_type == "deployments":
                if self.namespace == "All Namespaces":
                    resource_list = self.kube_client.apps_v1.list_deployment_for_all_namespaces()
                else:
                    resource_list = self.kube_client.apps_v1.list_namespaced_deployment(namespace=self.namespace)
                resources = [f"{item.metadata.name} ({item.metadata.namespace})" if self.namespace == "All Namespaces" else item.metadata.name for item in resource_list.items]
                
            elif self.workload_type == "statefulsets":
                if self.namespace == "All Namespaces":
                    resource_list = self.kube_client.apps_v1.list_stateful_set_for_all_namespaces()
                else:
                    resource_list = self.kube_client.apps_v1.list_namespaced_stateful_set(namespace=self.namespace)
                resources = [f"{item.metadata.name} ({item.metadata.namespace})" if self.namespace == "All Namespaces" else item.metadata.name for item in resource_list.items]
                
            elif self.workload_type == "daemonsets":
                if self.namespace == "All Namespaces":
                    resource_list = self.kube_client.apps_v1.list_daemon_set_for_all_namespaces()
                else:
                    resource_list = self.kube_client.apps_v1.list_namespaced_daemon_set(namespace=self.namespace)
                resources = [f"{item.metadata.name} ({item.metadata.namespace})" if self.namespace == "All Namespaces" else item.metadata.name for item in resource_list.items]
                
            elif self.workload_type == "replicasets":
                if self.namespace == "All Namespaces":
                    resource_list = self.kube_client.apps_v1.list_replica_set_for_all_namespaces()
                else:
                    resource_list = self.kube_client.apps_v1.list_namespaced_replica_set(namespace=self.namespace)
                resources = [f"{item.metadata.name} ({item.metadata.namespace})" if self.namespace == "All Namespaces" else item.metadata.name for item in resource_list.items]
                
            elif self.workload_type == "jobs":
                if self.namespace == "All Namespaces":
                    resource_list = self.kube_client.batch_v1.list_job_for_all_namespaces()
                else:
                    resource_list = self.kube_client.batch_v1.list_namespaced_job(namespace=self.namespace)
                resources = [f"{item.metadata.name} ({item.metadata.namespace})" if self.namespace == "All Namespaces" else item.metadata.name for item in resource_list.items]
                
            elif self.workload_type == "cronjobs":
                if self.namespace == "All Namespaces":
                    resource_list = self.kube_client.batch_v1.list_cron_job_for_all_namespaces()
                else:
                    resource_list = self.kube_client.batch_v1.list_namespaced_cron_job(namespace=self.namespace)
                resources = [f"{item.metadata.name} ({item.metadata.namespace})" if self.namespace == "All Namespaces" else item.metadata.name for item in resource_list.items]
                
            elif self.workload_type == "replicationcontrollers":
                if self.namespace == "All Namespaces":
                    resource_list = self.kube_client.v1.list_replication_controller_for_all_namespaces()
                else:
                    resource_list = self.kube_client.v1.list_namespaced_replication_controller(namespace=self.namespace)
                resources = [f"{item.metadata.name} ({item.metadata.namespace})" if self.namespace == "All Namespaces" else item.metadata.name for item in resource_list.items]
            
            # Sort resources alphabetically
            resources.sort()
            self.resources_loaded.emit(resources)
            
        except ApiException as e:
            self.error_occurred.emit(f"API error: {e.reason}")
        except Exception as e:
            self.error_occurred.emit(f"Failed to load {self.workload_type}: {str(e)}")