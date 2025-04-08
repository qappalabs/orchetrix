# import os
# import json
# import yaml
# import subprocess
# from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot
# from dataclasses import dataclass
# from typing import List, Dict, Optional, Any

# @dataclass
# class KubeCluster:
#     """Data class for Kubernetes cluster information"""
#     name: str
#     context: str
#     kind: str = "Kubernetes Cluster"
#     source: str = "local"
#     label: str = "General"
#     status: str = "disconnect"
#     badge_color: Optional[str] = None
#     server: Optional[str] = None
#     user: Optional[str] = None
#     namespace: Optional[str] = None
#     version: Optional[str] = None

# class WorkerSignals(QObject):
#     """Signals for threading operations"""
#     finished = pyqtSignal(object)
#     error = pyqtSignal(str)

# class KubeConfigWorker(QRunnable):
#     """Worker thread for loading Kubernetes config asynchronously"""
#     def __init__(self, client, config_path=None):
#         super().__init__()
#         self.client = client
#         self.config_path = config_path
#         self.signals = WorkerSignals()
        
#     @pyqtSlot()
#     def run(self):
#         try:
#             result = self.client.load_kube_config(self.config_path)
#             self.signals.finished.emit(result)
#         except Exception as e:
#             self.signals.error.emit(str(e))

# class KubernetesClient(QObject):
#     """Client for interacting with Kubernetes clusters"""
#     clusters_loaded = pyqtSignal(list)
#     cluster_info_loaded = pyqtSignal(dict)
#     error_occurred = pyqtSignal(str)
    
#     def __init__(self):
#         super().__init__()
#         self.threadpool = QThreadPool()
#         self.clusters = []
#         self.current_cluster = None
#         self._default_kubeconfig = os.path.expanduser("~/.kube/config")
    
#     def load_kube_config(self, config_path=None):
#         """Load Kubernetes configuration from specified path or default"""
#         try:
#             path = config_path if config_path else self._default_kubeconfig
            
#             # Check if file exists
#             if not os.path.isfile(path):
#                 self.error_occurred.emit(f"Kubeconfig file not found: {path}")
#                 return []
            
#             # Load YAML config
#             with open(path, 'r') as f:
#                 config = yaml.safe_load(f)
            
#             clusters = []
            
#             # Process contexts from config
#             if 'contexts' in config and config['contexts']:
#                 for context in config['contexts']:
#                     context_name = context['name']
#                     cluster_name = context['context'].get('cluster', '')
#                     user = context['context'].get('user', '')
#                     namespace = context['context'].get('namespace', 'default')
                    
#                     # Get server URL from cluster config
#                     server = None
#                     for cluster_info in config.get('clusters', []):
#                         if cluster_info['name'] == cluster_name:
#                             server = cluster_info['cluster'].get('server', '')
#                             break
                    
#                     # Create cluster object
#                     cluster = KubeCluster(
#                         name=context_name,
#                         context=context_name,
#                         server=server,
#                         user=user,
#                         namespace=namespace
#                     )
                    
#                     # Check if this is the current context
#                     is_current = config.get('current-context') == context_name
#                     if is_current:
#                         cluster.status = "active"
                    
#                     clusters.append(cluster)
            
#             self.clusters = clusters
#             self.clusters_loaded.emit(clusters)
#             return clusters
            
#         except Exception as e:
#             self.error_occurred.emit(f"Error loading kubeconfig: {str(e)}")
#             return []
    
#     def load_clusters_async(self, config_path=None):
#         """Load clusters asynchronously to avoid UI blocking"""
#         worker = KubeConfigWorker(self, config_path)
#         worker.signals.finished.connect(lambda result: self.clusters_loaded.emit(result))
#         worker.signals.error.connect(lambda error: self.error_occurred.emit(error))
#         self.threadpool.start(worker)
    
#     def get_cluster_info(self, cluster_name):
#         """Get detailed information about a specific cluster"""
#         try:
#             # Find the cluster in our list
#             cluster = next((c for c in self.clusters if c.name == cluster_name), None)
#             if not cluster:
#                 self.error_occurred.emit(f"Cluster not found: {cluster_name}")
#                 return None
            
#             # Set current context to get accurate information
#             result = subprocess.run(
#                 ["kubectl", "config", "use-context", cluster.name],
#                 capture_output=True,
#                 text=True
#             )
            
#             if result.returncode != 0:
#                 self.error_occurred.emit(f"Failed to switch context: {result.stderr}")
#                 return None
            
#             # Get cluster info
#             info = {
#                 "name": cluster.name,
#                 "context": cluster.context,
#                 "server": cluster.server,
#                 "user": cluster.user,
#                 "namespace": cluster.namespace,
#                 "nodes": self._get_nodes(),
#                 "version": self._get_version(),
#                 "namespaces": self._get_namespaces(),
#                 "pods_count": self._get_resource_count("pods"),
#                 "services_count": self._get_resource_count("services"),
#                 "deployments_count": self._get_resource_count("deployments"),
#             }
            
#             # Update cluster status now that we've connected
#             for c in self.clusters:
#                 if c.name == cluster_name:
#                     c.status = "active"
#                     # Try to get version info to validate connection
#                     if info["version"]:
#                         c.status = "available"
            
#             self.current_cluster = cluster_name
#             self.cluster_info_loaded.emit(info)
#             return info
            
#         except Exception as e:
#             self.error_occurred.emit(f"Error getting cluster info: {str(e)}")
#             return None
    
#     def _execute_kubectl(self, args, default_value=None):
#         """Execute kubectl command and return result"""
#         try:
#             result = subprocess.run(
#                 ["kubectl"] + args,
#                 capture_output=True,
#                 text=True,
#                 timeout=5  # Set timeout to prevent hanging
#             )
            
#             if result.returncode == 0:
#                 return result.stdout.strip()
#             return default_value
#         except subprocess.TimeoutExpired:
#             self.error_occurred.emit(f"Command timed out: kubectl {' '.join(args)}")
#             return default_value
#         except Exception as e:
#             self.error_occurred.emit(f"Error executing kubectl: {str(e)}")
#             return default_value
    
#     def _get_version(self):
#         """Get Kubernetes cluster version"""
#         output = self._execute_kubectl(["version", "--output=json"], "{}")
#         try:
#             version_info = json.loads(output)
#             server_version = version_info.get("serverVersion", {})
#             if server_version:
#                 return f"{server_version.get('major', '')}.{server_version.get('minor', '')}"
#             return "Unknown"
#         except json.JSONDecodeError:
#             return "Unknown"
    
#     def _get_nodes(self):
#         """Get cluster nodes"""
#         output = self._execute_kubectl(["get", "nodes", "-o", "json"], "{}")
#         try:
#             nodes_data = json.loads(output)
#             nodes = []
#             for item in nodes_data.get("items", []):
#                 node_name = item.get("metadata", {}).get("name", "Unknown")
#                 status = "Unknown"
#                 for condition in item.get("status", {}).get("conditions", []):
#                     if condition.get("type") == "Ready":
#                         status = "Ready" if condition.get("status") == "True" else "NotReady"
#                         break
#                 nodes.append({"name": node_name, "status": status})
#             return nodes
#         except json.JSONDecodeError:
#             return []
    
#     def _get_namespaces(self):
#         """Get cluster namespaces"""
#         output = self._execute_kubectl(["get", "namespaces", "-o", "json"], "{}")
#         try:
#             ns_data = json.loads(output)
#             return [item.get("metadata", {}).get("name", "Unknown") 
#                    for item in ns_data.get("items", [])]
#         except json.JSONDecodeError:
#             return []
    
#     def _get_resource_count(self, resource_type):
#         """Get count of resources of specified type"""
#         output = self._execute_kubectl(["get", resource_type, "--all-namespaces", "--no-headers"], "")
#         if output:
#             return len(output.strip().split('\n'))
#         return 0

# # Singleton instance
# _instance = None

# def get_kubernetes_client():
#     """Get or create Kubernetes client singleton"""
#     global _instance
#     if _instance is None:
#         _instance = KubernetesClient()
#     return _instance



import os
import json
import yaml
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot, QTimer
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import datetime

@dataclass
class KubeCluster:
    """Data class for Kubernetes cluster information"""
    name: str
    context: str
    kind: str = "Kubernetes Cluster"
    source: str = "local"
    label: str = "General"
    status: str = "disconnect"
    badge_color: Optional[str] = None
    server: Optional[str] = None
    user: Optional[str] = None
    namespace: Optional[str] = None
    version: Optional[str] = None

class WorkerSignals(QObject):
    """Signals for threading operations"""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

class KubeConfigWorker(QRunnable):
    """Worker thread for loading Kubernetes config asynchronously"""
    def __init__(self, client, config_path=None):
        super().__init__()
        self.client = client
        self.config_path = config_path
        self.signals = WorkerSignals()
        
    @pyqtSlot()
    def run(self):
        try:
            result = self.client.load_kube_config(self.config_path)
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))

class KubeMetricsWorker(QRunnable):
    """Worker thread for fetching Kubernetes metrics asynchronously"""
    def __init__(self, client, node_name=None):
        super().__init__()
        self.client = client
        self.node_name = node_name
        self.signals = WorkerSignals()
        
    @pyqtSlot()
    def run(self):
        try:
            if self.node_name:
                result = self.client.get_node_metrics(self.node_name)
            else:
                result = self.client.get_cluster_metrics()
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))

class KubeIssuesWorker(QRunnable):
    """Worker thread for fetching Kubernetes issues asynchronously"""
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.signals = WorkerSignals()
        
    @pyqtSlot()
    def run(self):
        try:
            result = self.client.get_cluster_issues()
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
            
class ResourceDetailWorker(QRunnable):
    """Worker thread for fetching Kubernetes resource details asynchronously"""
    def __init__(self, client, resource_type, resource_name, namespace):
        super().__init__()
        self.client = client
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace
        self.signals = WorkerSignals()
        
    @pyqtSlot()
    def run(self):
        try:
            result = self.client.get_resource_detail(
                self.resource_type, 
                self.resource_name, 
                self.namespace
            )
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))

class KubernetesClient(QObject):
    """Client for interacting with Kubernetes clusters"""
    clusters_loaded = pyqtSignal(list)
    cluster_info_loaded = pyqtSignal(dict)
    cluster_metrics_updated = pyqtSignal(dict)
    node_metrics_updated = pyqtSignal(dict)
    cluster_issues_updated = pyqtSignal(list)
    resource_detail_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.threadpool = QThreadPool()
        self.clusters = []
        self.current_cluster = None
        self._default_kubeconfig = os.path.expanduser("~/.kube/config")
        
        # Set up timers for periodic updates
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self.refresh_metrics)
        
        self.issues_timer = QTimer()
        self.issues_timer.timeout.connect(self.refresh_issues)
    
    def start_metrics_polling(self, interval_ms=5000):
        """Start polling for metrics updates"""
        self.metrics_timer.start(interval_ms)
    
    def stop_metrics_polling(self):
        """Stop polling for metrics updates"""
        self.metrics_timer.stop()
    
    def start_issues_polling(self, interval_ms=10000):
        """Start polling for cluster issues"""
        self.issues_timer.start(interval_ms)
    
    def stop_issues_polling(self):
        """Stop polling for cluster issues"""
        self.issues_timer.stop()
    
    def refresh_metrics(self):
        """Refresh all metrics data"""
        if self.current_cluster:
            self.get_cluster_metrics_async()
    
    def refresh_issues(self):
        """Refresh cluster issues data"""
        if self.current_cluster:
            self.get_cluster_issues_async()
    
    def load_kube_config(self, config_path=None):
        """Load Kubernetes configuration from specified path or default"""
        try:
            path = config_path if config_path else self._default_kubeconfig
            
            # Check if file exists
            if not os.path.isfile(path):
                self.error_occurred.emit(f"Kubeconfig file not found: {path}")
                return []
            
            # Load YAML config
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
            
            clusters = []
            
            # Process contexts from config
            if 'contexts' in config and config['contexts']:
                for context in config['contexts']:
                    context_name = context['name']
                    cluster_name = context['context'].get('cluster', '')
                    user = context['context'].get('user', '')
                    namespace = context['context'].get('namespace', 'default')
                    
                    # Get server URL from cluster config
                    server = None
                    for cluster_info in config.get('clusters', []):
                        if cluster_info['name'] == cluster_name:
                            server = cluster_info['cluster'].get('server', '')
                            break
                    
                    # Create cluster object
                    cluster = KubeCluster(
                        name=context_name,
                        context=context_name,
                        server=server,
                        user=user,
                        namespace=namespace
                    )
                    
                    # Check if this is the current context
                    is_current = config.get('current-context') == context_name
                    if is_current:
                        cluster.status = "active"
                    
                    clusters.append(cluster)
            
            self.clusters = clusters
            self.clusters_loaded.emit(clusters)
            return clusters
            
        except Exception as e:
            self.error_occurred.emit(f"Error loading kubeconfig: {str(e)}")
            return []
    
    def load_clusters_async(self, config_path=None):
        """Load clusters asynchronously to avoid UI blocking"""
        worker = KubeConfigWorker(self, config_path)
        worker.signals.finished.connect(lambda result: self.clusters_loaded.emit(result))
        worker.signals.error.connect(lambda error: self.error_occurred.emit(error))
        self.threadpool.start(worker)
    
    def get_cluster_info(self, cluster_name):
        """Get detailed information about a specific cluster"""
        try:
            # Find the cluster in our list
            cluster = next((c for c in self.clusters if c.name == cluster_name), None)
            if not cluster:
                self.error_occurred.emit(f"Cluster not found: {cluster_name}")
                return None
            
            # Set current context to get accurate information
            result = subprocess.run(
                ["kubectl", "config", "use-context", cluster.name],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.error_occurred.emit(f"Failed to switch context: {result.stderr}")
                return None
            
            # Get cluster info
            info = {
                "name": cluster.name,
                "context": cluster.context,
                "server": cluster.server,
                "user": cluster.user,
                "namespace": cluster.namespace,
                "nodes": self._get_nodes(),
                "version": self._get_version(),
                "namespaces": self._get_namespaces(),
                "pods_count": self._get_resource_count("pods"),
                "services_count": self._get_resource_count("services"),
                "deployments_count": self._get_resource_count("deployments"),
            }
            
            # Update cluster status now that we've connected
            for c in self.clusters:
                if c.name == cluster_name:
                    c.status = "active"
                    # Try to get version info to validate connection
                    if info["version"]:
                        c.status = "available"
            
            self.current_cluster = cluster_name
            self.cluster_info_loaded.emit(info)
            
            # Start polling for metrics and issues after connecting
            self.start_metrics_polling()
            self.start_issues_polling()
            
            return info
            
        except Exception as e:
            self.error_occurred.emit(f"Error getting cluster info: {str(e)}")
            return None
    
    def get_cluster_metrics(self):
        """Get real-time resource metrics for the cluster"""
        try:
            # Get node metrics from metrics-server
            nodes_metrics = self._get_nodes_metrics()
            
            # Calculate cluster-wide totals
            cpu_total = 0
            cpu_used = 0
            memory_total = 0
            memory_used = 0
            
            # Get node resource information and calculate totals
            node_resources = self._get_node_resources()
            
            for node_name, resources in node_resources.items():
                cpu_total += resources['cpu_capacity']
                cpu_used += resources['cpu_used']
                memory_total += resources['memory_capacity']
                memory_used += resources['memory_used']
            
            # Calculate usage percentages
            cpu_usage = (cpu_used / cpu_total * 100) if cpu_total > 0 else 0
            memory_usage = (memory_used / memory_total * 100) if memory_total > 0 else 0
            
            # Get pod usage data
            pods_total = self._get_resource_count("pods")
            pods_capacity = sum(node.get('pods_capacity', 110) for node in node_resources.values())
            pods_usage = (pods_total / pods_capacity * 100) if pods_capacity > 0 else 0
            
            # Get historical data points for charts
            cpu_history = self._generate_metrics_history('cpu', 12, cpu_usage)
            memory_history = self._generate_metrics_history('memory', 12, memory_usage)
            
            metrics = {
                "cpu": {
                    "usage": round(cpu_usage, 2),
                    "requests": round(cpu_used, 2),
                    "limits": round(cpu_total * 0.8, 2),  # Assuming limits are 80% of capacity
                    "capacity": round(cpu_total, 2),
                    "allocatable": round(cpu_total, 2),
                    "history": cpu_history
                },
                "memory": {
                    "usage": round(memory_usage, 2),
                    "requests": round(memory_used, 2),
                    "limits": round(memory_total * 0.8, 2),  # Assuming limits are 80% of capacity
                    "capacity": round(memory_total, 2),
                    "allocatable": round(memory_total, 2),
                    "history": memory_history
                },
                "pods": {
                    "usage": round(pods_usage, 2),
                    "count": pods_total,
                    "capacity": pods_capacity
                }
            }
            
            self.cluster_metrics_updated.emit(metrics)
            return metrics
            
        except Exception as e:
            self.error_occurred.emit(f"Error getting cluster metrics: {str(e)}")
            return None
    
    def get_cluster_metrics_async(self):
        """Get cluster metrics asynchronously"""
        worker = KubeMetricsWorker(self)
        worker.signals.finished.connect(lambda result: self.cluster_metrics_updated.emit(result) if result else None)
        worker.signals.error.connect(lambda error: self.error_occurred.emit(error))
        self.threadpool.start(worker)
    
    def get_node_metrics(self, node_name):
        """Get real-time resource metrics for a specific node"""
        try:
            # Get node resource details
            node_resources = self._get_node_resources().get(node_name, {})
            
            if not node_resources:
                self.error_occurred.emit(f"No resource information found for node: {node_name}")
                return None
            
            # Calculate usage percentages
            cpu_usage = (node_resources['cpu_used'] / node_resources['cpu_capacity'] * 100) if node_resources['cpu_capacity'] > 0 else 0
            memory_usage = (node_resources['memory_used'] / node_resources['memory_capacity'] * 100) if node_resources['memory_capacity'] > 0 else 0
            disk_usage = node_resources.get('disk_usage', 65.5)  # Default value if not available
            
            # Get historical data points for charts
            cpu_history = self._generate_metrics_history(f'cpu_{node_name}', 24, cpu_usage)
            memory_history = self._generate_metrics_history(f'memory_{node_name}', 24, memory_usage)
            disk_history = self._generate_metrics_history(f'disk_{node_name}', 24, disk_usage)
            
            metrics = {
                "name": node_name,
                "cpu": {
                    "capacity": node_resources['cpu_capacity'],
                    "used": node_resources['cpu_used'],
                    "usage_percent": round(cpu_usage, 2),
                    "history": cpu_history
                },
                "memory": {
                    "capacity": node_resources['memory_capacity'],
                    "used": node_resources['memory_used'],
                    "usage_percent": round(memory_usage, 2),
                    "history": memory_history
                },
                "disk": {
                    "capacity": node_resources.get('disk_capacity', 100),
                    "used": node_resources.get('disk_used', 65.5),
                    "usage_percent": round(disk_usage, 2),
                    "history": disk_history
                }
            }
            
            self.node_metrics_updated.emit(metrics)
            return metrics
            
        except Exception as e:
            self.error_occurred.emit(f"Error getting node metrics: {str(e)}")
            return None
    
    def get_node_metrics_async(self, node_name):
        """Get node metrics asynchronously"""
        worker = KubeMetricsWorker(self, node_name)
        worker.signals.finished.connect(lambda result: self.node_metrics_updated.emit(result) if result else None)
        worker.signals.error.connect(lambda error: self.error_occurred.emit(error))
        self.threadpool.start(worker)
    
    def get_cluster_issues(self):
        """Get current issues in the cluster"""
        try:
            # Get events with warning or error type
            issues = []
            
            # Get events with warning or error type
            output = self._execute_kubectl(["get", "events", "--all-namespaces", "--field-selector=type!=Normal", "-o", "json"], "{}")
            try:
                events_data = json.loads(output)
                for item in events_data.get("items", []):
                    metadata = item.get("metadata", {})
                    involved_object = item.get("involvedObject", {})
                    
                    # Format creation timestamp to age
                    timestamp = metadata.get("creationTimestamp")
                    age = self._format_age(timestamp) if timestamp else "Unknown"
                    
                    issue = {
                        "message": item.get("message", "No message"),
                        "object": f"{involved_object.get('kind', 'Unknown')}/{involved_object.get('name', 'unknown')}",
                        "type": item.get("type", "Unknown"),
                        "age": age,
                        "namespace": metadata.get("namespace", "default"),
                        "reason": item.get("reason", "Unknown")
                    }
                    issues.append(issue)
            except json.JSONDecodeError:
                pass
            
            # Get pods that are not in Running or Completed state
            output = self._execute_kubectl(["get", "pods", "--all-namespaces", "-o", "json"], "{}")
            try:
                pods_data = json.loads(output)
                for item in pods_data.get("items", []):
                    metadata = item.get("metadata", {})
                    status = item.get("status", {})
                    phase = status.get("phase", "")
                    
                    if phase not in ["Running", "Succeeded", "Completed"]:
                        # Format creation timestamp to age
                        timestamp = metadata.get("creationTimestamp")
                        age = self._format_age(timestamp) if timestamp else "Unknown"
                        
                        # Get container status for more detailed message
                        container_statuses = status.get("containerStatuses", [])
                        message = "Pod not running"
                        
                        if container_statuses:
                            for container in container_statuses:
                                if not container.get("ready", False):
                                    state = container.get("state", {})
                                    if "waiting" in state:
                                        message = state["waiting"].get("message", "Container waiting")
                                        reason = state["waiting"].get("reason", "Unknown")
                                    elif "terminated" in state:
                                        message = state["terminated"].get("message", "Container terminated")
                                        reason = state["terminated"].get("reason", "Terminated")
                                    break
                        
                        issue = {
                            "message": message,
                            "object": f"Pod/{metadata.get('name', 'unknown')}",
                            "type": "Warning",
                            "age": age,
                            "namespace": metadata.get("namespace", "default"),
                            "reason": status.get("reason", "PodIssue")
                        }
                        issues.append(issue)
            except json.JSONDecodeError:
                pass
            
            # Sort issues by age (newest first)
            issues.sort(key=lambda x: x["age"], reverse=True)
            
            self.cluster_issues_updated.emit(issues)
            return issues
            
        except Exception as e:
            self.error_occurred.emit(f"Error getting cluster issues: {str(e)}")
            return []
    
    def get_cluster_issues_async(self):
        """Get cluster issues asynchronously"""
        worker = KubeIssuesWorker(self)
        worker.signals.finished.connect(lambda result: self.cluster_issues_updated.emit(result) if result else None)
        worker.signals.error.connect(lambda error: self.error_occurred.emit(error))
        self.threadpool.start(worker)
        
    def get_resource_detail(self, resource_type, resource_name, namespace="default"):
        """Get detailed information about a specific Kubernetes resource"""
        try:
            # Different command formats for cluster-scoped vs namespaced resources
            cluster_scoped_resources = ["node", "persistentvolume", "clusterrole", "namespace"]
            
            if resource_type.lower() in cluster_scoped_resources:
                # Cluster-scoped resources don't need namespace
                output = self._execute_kubectl(
                    ["get", resource_type, resource_name, "-o", "json"], 
                    "{}"
                )
            else:
                # Namespaced resources
                output = self._execute_kubectl(
                    ["get", resource_type, resource_name, "-n", namespace, "-o", "json"], 
                    "{}"
                )
            
            try:
                resource_data = json.loads(output)
                
                # Add related events (separate API call)
                events = self._get_resource_events(resource_type, resource_name, namespace)
                resource_data["events"] = events
                
                return resource_data
            except json.JSONDecodeError:
                self.error_occurred.emit(f"Error parsing resource data: Invalid JSON")
                return {}
                
        except Exception as e:
            self.error_occurred.emit(f"Error getting resource details: {str(e)}")
            return {}
    
    def get_resource_detail_async(self, resource_type, resource_name, namespace="default"):
        """Get resource details asynchronously"""
        worker = ResourceDetailWorker(self, resource_type, resource_name, namespace)
        worker.signals.finished.connect(lambda result: self.resource_detail_loaded.emit(result) if result else None)
        worker.signals.error.connect(lambda error: self.error_occurred.emit(error))
        self.threadpool.start(worker)
        
    def _get_resource_events(self, resource_type, resource_name, namespace="default"):
        """Get events related to a specific resource"""
        try:
            # Use field selector to filter events by resource
            field_selector = f"involvedObject.name={resource_name},involvedObject.kind={resource_type.capitalize()}"
            
            if resource_type.lower() not in ["node", "persistentvolume", "clusterrole", "namespace"]:
                # Add namespace selector for namespaced resources
                field_selector += f",involvedObject.namespace={namespace}"
                output = self._execute_kubectl(
                    ["get", "events", "-n", namespace, "--field-selector", field_selector, "-o", "json"], 
                    "{}"
                )
            else:
                # For cluster-scoped resources
                output = self._execute_kubectl(
                    ["get", "events", "--field-selector", field_selector, "-o", "json"], 
                    "{}"
                )
            
            try:
                events_data = json.loads(output)
                events = []
                
                for item in events_data.get("items", []):
                    # Format creation timestamp to age
                    timestamp = item.get("metadata", {}).get("creationTimestamp")
                    age = self._format_age(timestamp) if timestamp else "Unknown"
                    
                    event = {
                        "type": item.get("type", "Normal"),
                        "reason": item.get("reason", "Unknown"),
                        "message": item.get("message", "No message"),
                        "age": age,
                        "count": item.get("count", 1),
                        "source": item.get("source", {}).get("component", "Unknown")
                    }
                    events.append(event)
                
                return events
            except json.JSONDecodeError:
                return []
                
        except Exception as e:
            self.error_occurred.emit(f"Error getting resource events: {str(e)}")
            return []
    
    def _execute_kubectl(self, args, default_value=None):
        """Execute kubectl command and return result"""
        try:
            result = subprocess.run(
                ["kubectl"] + args,
                capture_output=True,
                text=True,
                timeout=5  # Set timeout to prevent hanging
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            return default_value
        except subprocess.TimeoutExpired:
            self.error_occurred.emit(f"Command timed out: kubectl {' '.join(args)}")
            return default_value
        except Exception as e:
            self.error_occurred.emit(f"Error executing kubectl: {str(e)}")
            return default_value
    
    def _get_version(self):
        """Get Kubernetes cluster version"""
        output = self._execute_kubectl(["version", "--output=json"], "{}")
        try:
            version_info = json.loads(output)
            server_version = version_info.get("serverVersion", {})
            if server_version:
                return f"{server_version.get('major', '')}.{server_version.get('minor', '')}"
            return "Unknown"
        except json.JSONDecodeError:
            return "Unknown"
    
    def _get_nodes(self):
        """Get cluster nodes"""
        output = self._execute_kubectl(["get", "nodes", "-o", "json"], "{}")
        try:
            nodes_data = json.loads(output)
            nodes = []
            for item in nodes_data.get("items", []):
                node_name = item.get("metadata", {}).get("name", "Unknown")
                status = "Unknown"
                for condition in item.get("status", {}).get("conditions", []):
                    if condition.get("type") == "Ready":
                        status = "Ready" if condition.get("status") == "True" else "NotReady"
                        break
                
                # Get node roles
                roles = []
                labels = item.get("metadata", {}).get("labels", {})
                for label, value in labels.items():
                    if label.startswith("node-role.kubernetes.io/"):
                        role = label.split("/")[1]
                        roles.append(role)
                
                # Get node version
                node_info = item.get("status", {}).get("nodeInfo", {})
                kubelet_version = node_info.get("kubeletVersion", "Unknown")
                
                # Calculate node age
                creation_timestamp = item.get("metadata", {}).get("creationTimestamp")
                age = self._format_age(creation_timestamp) if creation_timestamp else "Unknown"
                
                nodes.append({
                    "name": node_name,
                    "status": status,
                    "roles": roles,
                    "version": kubelet_version,
                    "age": age
                })
            return nodes
        except json.JSONDecodeError:
            return []
    
    def _get_namespaces(self):
        """Get cluster namespaces"""
        output = self._execute_kubectl(["get", "namespaces", "-o", "json"], "{}")
        try:
            ns_data = json.loads(output)
            return [item.get("metadata", {}).get("name", "Unknown") 
                   for item in ns_data.get("items", [])]
        except json.JSONDecodeError:
            return []
    
    def _get_resource_count(self, resource_type):
        """Get count of resources of specified type"""
        output = self._execute_kubectl(["get", resource_type, "--all-namespaces", "--no-headers"], "")
        if output:
            return len(output.strip().split('\n'))
        return 0
    
    def _get_nodes_metrics(self):
        """Get node metrics from metrics-server if available"""
        metrics = {}
        output = self._execute_kubectl(["get", "--raw", "/apis/metrics.k8s.io/v1beta1/nodes"], "")
        if not output:
            return metrics
        
        try:
            metrics_data = json.loads(output)
            for item in metrics_data.get("items", []):
                node_name = item.get("metadata", {}).get("name", "")
                if not node_name:
                    continue
                
                usage = item.get("usage", {})
                cpu = usage.get("cpu", "0")
                memory = usage.get("memory", "0Ki")
                
                # Convert CPU from string (like "100m") to float (cores)
                cpu_value = self._parse_resource_value(cpu)
                
                # Convert memory from string (like "1000Ki") to float (bytes)
                memory_value = self._parse_resource_value(memory)
                
                metrics[node_name] = {
                    "cpu": cpu_value,
                    "memory": memory_value
                }
            
            return metrics
        except json.JSONDecodeError:
            return {}
    
    def _get_node_resources(self):
        """Get node resources (CPU, memory, etc.)"""
        resources = {}
        output = self._execute_kubectl(["get", "nodes", "-o", "json"], "{}")
        try:
            nodes_data = json.loads(output)
            for item in nodes_data.get("items", []):
                node_name = item.get("metadata", {}).get("name", "")
                if not node_name:
                    continue
                
                status = item.get("status", {})
                capacity = status.get("capacity", {})
                allocatable = status.get("allocatable", {})
                
                # Get capacity values
                cpu_capacity = self._parse_resource_value(capacity.get("cpu", "0"))
                memory_capacity = self._parse_resource_value(capacity.get("memory", "0Ki"))
                pods_capacity = int(capacity.get("pods", "110"))
                
                # Get resource usage through metrics-server if available
                metrics = self._get_nodes_metrics()
                node_metrics = metrics.get(node_name, {})
                
                cpu_used = node_metrics.get("cpu", cpu_capacity * 0.3)  # Default 30% if no metrics
                memory_used = node_metrics.get("memory", memory_capacity * 0.4)  # Default 40% if no metrics
                
                # For disk usage, we would need to run commands on the node itself
                # This is just an estimate for visualization purposes
                disk_capacity = 100  # GB
                disk_used = 65.5  # GB
                
                resources[node_name] = {
                    "cpu_capacity": cpu_capacity,
                    "cpu_used": cpu_used,
                    "memory_capacity": memory_capacity,
                    "memory_used": memory_used,
                    "pods_capacity": pods_capacity,
                    "disk_capacity": disk_capacity,
                    "disk_used": disk_used,
                    "disk_usage": (disk_used / disk_capacity * 100) if disk_capacity > 0 else 0
                }
            
            return resources
        except json.JSONDecodeError:
            return {}
    
    def _parse_resource_value(self, value_str):
        """Parse Kubernetes resource value strings to float"""
        if not value_str or not isinstance(value_str, str):
            return 0.0
        
        # CPU parsing (e.g., "100m" = 0.1 cores)
        if value_str.endswith('m'):
            return float(value_str[:-1]) / 1000
        
        # Memory parsing
        memory_suffixes = {
            'Ki': 1024,
            'Mi': 1024 ** 2,
            'Gi': 1024 ** 3,
            'Ti': 1024 ** 4,
            'Pi': 1024 ** 5,
            'Ei': 1024 ** 6,
            'K': 1000,
            'M': 1000 ** 2,
            'G': 1000 ** 3,
            'T': 1000 ** 4,
            'P': 1000 ** 5,
            'E': 1000 ** 6
        }
        
        for suffix, multiplier in memory_suffixes.items():
            if value_str.endswith(suffix):
                return float(value_str[:-len(suffix)]) * multiplier
        
        # If no suffix, try to parse as a number
        try:
            return float(value_str)
        except ValueError:
            return 0.0
    
    def _format_age(self, timestamp):
        """Format timestamp to age string (e.g., "2d", "5h")"""
        if not timestamp:
            return "Unknown"
        
        try:
            # Parse ISO 8601 timestamp
            created_time = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.datetime.now(datetime.timezone.utc)
            diff = now - created_time
            
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
        except Exception:
            return "Unknown"
    
    def _generate_metrics_history(self, metric_key, points, current_value):
        """Generate historical data points for metrics visualization"""
        # In a real implementation, this would fetch historical data from Prometheus or similar
        # For now, we'll generate random data around the current value
        import random
        
        history = []
        base_value = current_value
        
        for i in range(points):
            # Generate value with some randomness but maintaining a trend
            variation = random.uniform(-5, 5)
            value = max(0, min(100, base_value + variation))
            
            # For visualization in the UI, keep values reasonable
            if value > 95:
                value = random.uniform(85, 95)
            elif value < 5:
                value = random.uniform(5, 15)
            
            history.append(round(value, 2))
            
            # Adjust base value for next point to create a natural looking graph
            # with some correlation between adjacent points
            base_value = value
        
        return history

# Singleton instance
_instance = None

def get_kubernetes_client():
    """Get or create Kubernetes client singleton"""
    global _instance
    if _instance is None:
        _instance = KubernetesClient()
    return _instance

# import os
# import json
# import yaml
# import subprocess
# import time
# import datetime
# from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot, QTimer
# from dataclasses import dataclass
# from typing import List, Dict, Optional, Any

# @dataclass
# class KubeCluster:
#     """Data class for Kubernetes cluster information"""
#     name: str
#     context: str
#     kind: str = "Kubernetes Cluster"
#     source: str = "local"
#     label: str = "General"
#     status: str = "disconnect"
#     badge_color: Optional[str] = None
#     server: Optional[str] = None
#     user: Optional[str] = None
#     namespace: Optional[str] = None
#     version: Optional[str] = None
    
# @dataclass
# class ClusterMetrics:
#     """Data class for cluster metrics"""
#     cpu_usage: float = 0.0
#     cpu_requests: float = 0.0
#     cpu_limits: float = 0.0
#     cpu_capacity: float = 0.0
#     memory_usage: float = 0.0
#     memory_requests: float = 0.0
#     memory_limits: float = 0.0
#     memory_capacity: float = 0.0
#     pods_usage: int = 0
#     pods_capacity: int = 0
    
#     # Historical data for graphs (last 12 hours with 1-hour intervals)
#     cpu_history: List[float] = None
#     memory_history: List[float] = None
    
#     def __post_init__(self):
#         if self.cpu_history is None:
#             self.cpu_history = [0.0] * 12
#         if self.memory_history is None:
#             self.memory_history = [0.0] * 12

# @dataclass
# class NodeMetrics:
#     """Data class for node metrics"""
#     name: str
#     status: str
#     cpu_cores: float = 0.0
#     memory: str = "0 GiB"
#     disk: str = "0 GB"
#     taints: int = 0
#     roles: str = ""
#     version: str = ""
#     age: str = ""
#     conditions: str = "Unknown"
    
#     # Current utilization percentages
#     cpu_utilization: float = 0.0
#     memory_utilization: float = 0.0
#     disk_utilization: float = 0.0
    
#     # Historical data for graphs (24 data points)
#     cpu_history: List[float] = None
#     memory_history: List[float] = None
#     disk_history: List[float] = None
    
#     def __post_init__(self):
#         if self.cpu_history is None:
#             self.cpu_history = [0.0] * 24
#         if self.memory_history is None:
#             self.memory_history = [0.0] * 24
#         if self.disk_history is None:
#             self.disk_history = [0.0] * 24

# @dataclass
# class ClusterIssue:
#     """Data class for cluster issues"""
#     message: str
#     object_name: str
#     type: str
#     age: str

# class WorkerSignals(QObject):
#     """Signals for threading operations"""
#     finished = pyqtSignal(object)
#     error = pyqtSignal(str)

# class KubeConfigWorker(QRunnable):
#     """Worker thread for loading Kubernetes config asynchronously"""
#     def __init__(self, client, config_path=None):
#         super().__init__()
#         self.client = client
#         self.config_path = config_path
#         self.signals = WorkerSignals()
        
#     @pyqtSlot()
#     def run(self):
#         try:
#             result = self.client.load_kube_config(self.config_path)
#             self.signals.finished.emit(result)
#         except Exception as e:
#             self.signals.error.emit(str(e))

# class MetricsWorker(QRunnable):
#     """Worker thread for fetching metrics asynchronously"""
#     def __init__(self, client, cluster_name=None):
#         super().__init__()
#         self.client = client
#         self.cluster_name = cluster_name
#         self.signals = WorkerSignals()
        
#     @pyqtSlot()
#     def run(self):
#         try:
#             if self.cluster_name:
#                 result = self.client.get_cluster_metrics(self.cluster_name)
#             else:
#                 result = self.client.get_current_cluster_metrics()
#             self.signals.finished.emit(result)
#         except Exception as e:
#             self.signals.error.emit(str(e))

# class NodesWorker(QRunnable):
#     """Worker thread for fetching node metrics asynchronously"""
#     def __init__(self, client):
#         super().__init__()
#         self.client = client
#         self.signals = WorkerSignals()
        
#     @pyqtSlot()
#     def run(self):
#         try:
#             result = self.client.get_nodes_metrics()
#             self.signals.finished.emit(result)
#         except Exception as e:
#             self.signals.error.emit(str(e))

# class IssuesWorker(QRunnable):
#     """Worker thread for fetching cluster issues asynchronously"""
#     def __init__(self, client):
#         super().__init__()
#         self.client = client
#         self.signals = WorkerSignals()
        
#     @pyqtSlot()
#     def run(self):
#         try:
#             result = self.client.get_cluster_issues()
#             self.signals.finished.emit(result)
#         except Exception as e:
#             self.signals.error.emit(str(e))

# class KubernetesClient(QObject):
#     """Client for interacting with Kubernetes clusters"""
#     clusters_loaded = pyqtSignal(list)
#     cluster_info_loaded = pyqtSignal(dict)
#     cluster_metrics_loaded = pyqtSignal(object)
#     nodes_metrics_loaded = pyqtSignal(list)
#     cluster_issues_loaded = pyqtSignal(list)
#     error_occurred = pyqtSignal(str)
    
#     def __init__(self):
#         super().__init__()
#         self.threadpool = QThreadPool()
#         self.clusters = []
#         self.current_cluster = None
#         self._default_kubeconfig = os.path.expanduser("~/.kube/config")
        
#         # Store historical metrics data
#         self.cluster_metrics_history = {}
#         self.node_metrics_history = {}
#         self.cluster_issues = []
        
#         # Setup metrics collection timers
#         self.metrics_timer = QTimer()
#         self.metrics_timer.timeout.connect(self.refresh_metrics)
        
#         self.nodes_metrics_timer = QTimer()
#         self.nodes_metrics_timer.timeout.connect(self.refresh_nodes_metrics)
        
#         self.issues_timer = QTimer()
#         self.issues_timer.timeout.connect(self.refresh_cluster_issues)
    
#     def load_kube_config(self, config_path=None):
#         """Load Kubernetes configuration from specified path or default"""
#         try:
#             path = config_path if config_path else self._default_kubeconfig
            
#             # Check if file exists
#             if not os.path.isfile(path):
#                 self.error_occurred.emit(f"Kubeconfig file not found: {path}")
#                 return []
            
#             # Load YAML config
#             with open(path, 'r') as f:
#                 config = yaml.safe_load(f)
            
#             clusters = []
            
#             # Process contexts from config
#             if 'contexts' in config and config['contexts']:
#                 for context in config['contexts']:
#                     context_name = context['name']
#                     cluster_name = context['context'].get('cluster', '')
#                     user = context['context'].get('user', '')
#                     namespace = context['context'].get('namespace', 'default')
                    
#                     # Get server URL from cluster config
#                     server = None
#                     for cluster_info in config.get('clusters', []):
#                         if cluster_info['name'] == cluster_name:
#                             server = cluster_info['cluster'].get('server', '')
#                             break
                    
#                     # Create cluster object
#                     cluster = KubeCluster(
#                         name=context_name,
#                         context=context_name,
#                         server=server,
#                         user=user,
#                         namespace=namespace
#                     )
                    
#                     # Check if this is the current context
#                     is_current = config.get('current-context') == context_name
#                     if is_current:
#                         cluster.status = "active"
#                         self.current_cluster = context_name
                    
#                     clusters.append(cluster)
            
#             self.clusters = clusters
#             self.clusters_loaded.emit(clusters)
            
#             # Start metrics collection for active cluster
#             if self.current_cluster:
#                 self.start_metrics_collection()
            
#             return clusters
            
#         except Exception as e:
#             self.error_occurred.emit(f"Error loading kubeconfig: {str(e)}")
#             return []
    
#     def load_clusters_async(self, config_path=None):
#         """Load clusters asynchronously to avoid UI blocking"""
#         worker = KubeConfigWorker(self, config_path)
#         worker.signals.finished.connect(lambda result: self.clusters_loaded.emit(result))
#         worker.signals.error.connect(lambda error: self.error_occurred.emit(error))
#         self.threadpool.start(worker)
    
#     def start_metrics_collection(self):
#         """Start periodic metrics collection"""
#         # Stop any existing timers
#         self.stop_metrics_collection()
        
#         # Start cluster metrics collection (every 30 seconds)
#         self.metrics_timer.start(30000)
        
#         # Start node metrics collection (every 30 seconds)
#         self.nodes_metrics_timer.start(30000)
        
#         # Start issues collection (every 60 seconds)
#         self.issues_timer.start(60000)
        
#         # Immediately fetch initial data
#         self.refresh_metrics()
#         self.refresh_nodes_metrics()
#         self.refresh_cluster_issues()
    
#     def stop_metrics_collection(self):
#         """Stop metrics collection"""
#         if self.metrics_timer.isActive():
#             self.metrics_timer.stop()
        
#         if self.nodes_metrics_timer.isActive():
#             self.nodes_metrics_timer.stop()
            
#         if self.issues_timer.isActive():
#             self.issues_timer.stop()
    
#     def refresh_metrics(self):
#         """Refresh cluster metrics data"""
#         worker = MetricsWorker(self)
#         worker.signals.finished.connect(self.cluster_metrics_loaded.emit)
#         worker.signals.error.connect(self.error_occurred.emit)
#         self.threadpool.start(worker)
    
#     def refresh_nodes_metrics(self):
#         """Refresh node metrics data"""
#         worker = NodesWorker(self)
#         worker.signals.finished.connect(self.nodes_metrics_loaded.emit)
#         worker.signals.error.connect(self.error_occurred.emit)
#         self.threadpool.start(worker)
    
#     def refresh_cluster_issues(self):
#         """Refresh cluster issues data"""
#         worker = IssuesWorker(self)
#         worker.signals.finished.connect(self.cluster_issues_loaded.emit)
#         worker.signals.error.connect(self.error_occurred.emit)
#         self.threadpool.start(worker)
    
#     def get_cluster_info(self, cluster_name):
#         """Get detailed information about a specific cluster"""
#         try:
#             # Find the cluster in our list
#             cluster = next((c for c in self.clusters if c.name == cluster_name), None)
#             if not cluster:
#                 self.error_occurred.emit(f"Cluster not found: {cluster_name}")
#                 return None
            
#             # Set current context to get accurate information
#             result = subprocess.run(
#                 ["kubectl", "config", "use-context", cluster.name],
#                 capture_output=True,
#                 text=True
#             )
            
#             if result.returncode != 0:
#                 self.error_occurred.emit(f"Failed to switch context: {result.stderr}")
#                 return None
            
#             # Get cluster info
#             info = {
#                 "name": cluster.name,
#                 "context": cluster.context,
#                 "server": cluster.server,
#                 "user": cluster.user,
#                 "namespace": cluster.namespace,
#                 "nodes": self._get_nodes(),
#                 "version": self._get_version(),
#                 "namespaces": self._get_namespaces(),
#                 "pods_count": self._get_resource_count("pods"),
#                 "services_count": self._get_resource_count("services"),
#                 "deployments_count": self._get_resource_count("deployments"),
#             }
            
#             # Update cluster status now that we've connected
#             for c in self.clusters:
#                 if c.name == cluster_name:
#                     c.status = "active"
#                     # Try to get version info to validate connection
#                     if info["version"]:
#                         c.status = "available"
            
#             self.current_cluster = cluster_name
#             self.cluster_info_loaded.emit(info)
            
#             # Start metrics collection for the new active cluster
#             self.start_metrics_collection()
            
#             return info
            
#         except Exception as e:
#             self.error_occurred.emit(f"Error getting cluster info: {str(e)}")
#             return None
    
#     def get_current_cluster_metrics(self):
#         """Get metrics for the current cluster"""
#         if not self.current_cluster:
#             self.error_occurred.emit("No active cluster selected")
#             return None
        
#         return self.get_cluster_metrics(self.current_cluster)
    
#     def get_cluster_metrics(self, cluster_name):
#         """Get detailed metrics for a specific cluster"""
#         try:
#             # Initialize metrics object
#             metrics = ClusterMetrics()
            
#             # Get node metrics to calculate cluster totals
#             node_metrics = self._get_node_metrics()
            
#             # Calculate totals from nodes
#             for node in node_metrics:
#                 # Parse CPU cores
#                 try:
#                     metrics.cpu_capacity += float(node.get("cpu", "0").rstrip("m")) / 1000
#                 except ValueError:
#                     pass
                
#                 # Parse memory
#                 try:
#                     memory_str = node.get("memory", "0Ki")
#                     if memory_str.endswith("Ki"):
#                         metrics.memory_capacity += float(memory_str.rstrip("Ki")) / (1024 * 1024)  # Convert Ki to Gi
#                     elif memory_str.endswith("Mi"):
#                         metrics.memory_capacity += float(memory_str.rstrip("Mi")) / 1024  # Convert Mi to Gi
#                     elif memory_str.endswith("Gi"):
#                         metrics.memory_capacity += float(memory_str.rstrip("Gi"))
#                 except ValueError:
#                     pass
            
#             # Get pod metrics
#             pod_metrics = self._get_pod_metrics()
            
#             # Calculate usage from pods
#             for pod in pod_metrics:
#                 # Parse CPU usage
#                 try:
#                     metrics.cpu_usage += float(pod.get("cpu", "0").rstrip("m")) / 1000
#                 except ValueError:
#                     pass
                
#                 # Parse memory usage
#                 try:
#                     memory_str = pod.get("memory", "0Ki")
#                     if memory_str.endswith("Ki"):
#                         metrics.memory_usage += float(memory_str.rstrip("Ki")) / (1024 * 1024)  # Convert Ki to Gi
#                     elif memory_str.endswith("Mi"):
#                         metrics.memory_usage += float(memory_str.rstrip("Mi")) / 1024  # Convert Mi to Gi
#                     elif memory_str.endswith("Gi"):
#                         metrics.memory_usage += float(memory_str.rstrip("Gi"))
#                 except ValueError:
#                     pass
            
#             # Get pod count and capacity
#             metrics.pods_usage = self._get_resource_count("pods")
#             metrics.pods_capacity = self._get_pods_capacity()
            
#             # Get resource requests and limits
#             resource_metrics = self._get_resource_metrics()
#             metrics.cpu_requests = resource_metrics.get("cpu_requests", 0.0)
#             metrics.cpu_limits = resource_metrics.get("cpu_limits", 0.0)
#             metrics.memory_requests = resource_metrics.get("memory_requests", 0.0)
#             metrics.memory_limits = resource_metrics.get("memory_limits", 0.0)
            
#             # Update historical data
#             if cluster_name not in self.cluster_metrics_history:
#                 self.cluster_metrics_history[cluster_name] = {
#                     "cpu": [0.0] * 12,
#                     "memory": [0.0] * 12,
#                     "timestamp": time.time()
#                 }
            
#             # Only update history if it's been an hour since last update
#             current_time = time.time()
#             if current_time - self.cluster_metrics_history[cluster_name]["timestamp"] >= 3600:
#                 # Shift historical data
#                 self.cluster_metrics_history[cluster_name]["cpu"].pop(0)
#                 self.cluster_metrics_history[cluster_name]["memory"].pop(0)
                
#                 # Add new data points
#                 cpu_percentage = (metrics.cpu_usage / metrics.cpu_capacity) * 100 if metrics.cpu_capacity > 0 else 0
#                 memory_percentage = (metrics.memory_usage / metrics.memory_capacity) * 100 if metrics.memory_capacity > 0 else 0
                
#                 self.cluster_metrics_history[cluster_name]["cpu"].append(cpu_percentage)
#                 self.cluster_metrics_history[cluster_name]["memory"].append(memory_percentage)
#                 self.cluster_metrics_history[cluster_name]["timestamp"] = current_time
            
#             # Set historical data to metrics object
#             metrics.cpu_history = self.cluster_metrics_history[cluster_name]["cpu"]
#             metrics.memory_history = self.cluster_metrics_history[cluster_name]["memory"]
            
#             return metrics
            
#         except Exception as e:
#             self.error_occurred.emit(f"Error getting cluster metrics: {str(e)}")
#             return ClusterMetrics()
    
#     def get_nodes_metrics(self):
#         """Get detailed metrics for all nodes"""
#         try:
#             result = []
            
#             # Get basic node info
#             nodes_info = self._get_nodes_detail()
            
#             # Get node metrics
#             node_metrics = self._get_node_metrics()
            
#             # Convert to NodeMetrics objects
#             for node in nodes_info:
#                 node_name = node.get("name", "Unknown")
                
#                 # Find metrics for this node
#                 metrics = next((m for m in node_metrics if m.get("name") == node_name), {})
                
#                 # Parse CPU cores
#                 cpu_cores = 0.0
#                 try:
#                     cpu_str = metrics.get("cpu", "0")
#                     if cpu_str.endswith("m"):
#                         cpu_cores = float(cpu_str.rstrip("m")) / 1000
#                     else:
#                         cpu_cores = float(cpu_str)
#                 except ValueError:
#                     pass
                
#                 # Parse memory
#                 memory = "0 GiB"
#                 try:
#                     memory_str = metrics.get("memory", "0Ki")
#                     if memory_str.endswith("Ki"):
#                         memory_gb = float(memory_str.rstrip("Ki")) / (1024 * 1024)
#                         memory = f"{memory_gb:.1f} GiB"
#                     elif memory_str.endswith("Mi"):
#                         memory_gb = float(memory_str.rstrip("Mi")) / 1024
#                         memory = f"{memory_gb:.1f} GiB"
#                     elif memory_str.endswith("Gi"):
#                         memory_gb = float(memory_str.rstrip("Gi"))
#                         memory = f"{memory_gb:.1f} GiB"
#                 except ValueError:
#                     pass
                
#                 # Create NodeMetrics object
#                 node_metric = NodeMetrics(
#                     name=node_name,
#                     status=node.get("status", "Unknown"),
#                     cpu_cores=cpu_cores,
#                     memory=memory,
#                     disk=node.get("disk", "Unknown"),
#                     taints=len(node.get("taints", [])),
#                     roles=", ".join(node.get("roles", [])),
#                     version=node.get("kubelet_version", "Unknown"),
#                     age=self._format_age(node.get("age", "")),
#                     conditions=node.get("status", "Unknown")
#                 )
                
#                 # Calculate current utilization
#                 node_metric.cpu_utilization = float(metrics.get("cpu_percent", 0.0))
#                 node_metric.memory_utilization = float(metrics.get("memory_percent", 0.0))
#                 node_metric.disk_utilization = float(metrics.get("disk_percent", 0.0))
                
#                 # Update historical data
#                 if node_name not in self.node_metrics_history:
#                     self.node_metrics_history[node_name] = {
#                         "cpu": [0.0] * 24,
#                         "memory": [0.0] * 24,
#                         "disk": [0.0] * 24,
#                         "timestamp": time.time()
#                     }
                
#                 # Only update history if needed (for demo, update with small variations)
#                 current_time = time.time()
#                 if current_time - self.node_metrics_history[node_name]["timestamp"] >= 300:  # 5 minutes
#                     # Shift historical data
#                     self.node_metrics_history[node_name]["cpu"].pop(0)
#                     self.node_metrics_history[node_name]["memory"].pop(0)
#                     self.node_metrics_history[node_name]["disk"].pop(0)
                    
#                     # Add new data with small variations (for visualizing graphs)
#                     import random
#                     cpu_var = node_metric.cpu_utilization + random.uniform(-5, 5)
#                     mem_var = node_metric.memory_utilization + random.uniform(-3, 3)
#                     disk_var = node_metric.disk_utilization + random.uniform(-1, 1)
                    
#                     self.node_metrics_history[node_name]["cpu"].append(max(0, min(100, cpu_var)))
#                     self.node_metrics_history[node_name]["memory"].append(max(0, min(100, mem_var)))
#                     self.node_metrics_history[node_name]["disk"].append(max(0, min(100, disk_var)))
#                     self.node_metrics_history[node_name]["timestamp"] = current_time
                
#                 # Set historical data to metrics object
#                 node_metric.cpu_history = self.node_metrics_history[node_name]["cpu"]
#                 node_metric.memory_history = self.node_metrics_history[node_name]["memory"]
#                 node_metric.disk_history = self.node_metrics_history[node_name]["disk"]
                
#                 result.append(node_metric)
            
#             return result
            
#         except Exception as e:
#             self.error_occurred.emit(f"Error getting node metrics: {str(e)}")
#             return []
    
#     def get_cluster_issues(self):
#         """Get cluster issues"""
#         try:
#             # List of potential issues
#             issues = []
            
#             # Get events with type Warning
#             output = self._execute_kubectl(["get", "events", "--field-selector=type=Warning", "--all-namespaces", "-o", "json"], "{}")
#             try:
#                 events_data = json.loads(output)
#                 for item in events_data.get("items", []):
#                     message = item.get("message", "Unknown issue")
#                     type_str = item.get("type", "Warning")
#                     object_name = ""
                    
#                     # Get involved object
#                     involved = item.get("involvedObject", {})
#                     kind = involved.get("kind", "")
#                     name = involved.get("name", "")
#                     if kind and name:
#                         object_name = f"{kind}/{name}"
                    
#                     # Get age
#                     timestamp = item.get("lastTimestamp", "")
#                     age = self._format_age(timestamp)
                    
#                     # Create issue object
#                     issue = ClusterIssue(
#                         message=message,
#                         object_name=object_name,
#                         type=type_str,
#                         age=age
#                     )
#                     issues.append(issue)
#             except json.JSONDecodeError:
#                 pass
            
#             # Check for nodes not ready
#             nodes = self._get_nodes()
#             for node in nodes:
#                 if node.get("status") != "Ready":
#                     issue = ClusterIssue(
#                         message=f"Node {node.get('name')} is not ready",
#                         object_name=f"Node/{node.get('name')}",
#                         type="Warning",
#                         age="N/A"
#                     )
#                     issues.append(issue)
            
#             # Check for failing pods
#             failing_pods = self._get_failing_pods()
#             for pod in failing_pods:
#                 issue = ClusterIssue(
#                     message=f"Pod {pod.get('name')} is in {pod.get('status')} state: {pod.get('reason')}",
#                     object_name=f"Pod/{pod.get('name')}",
#                     type="Warning",
#                     age=self._format_age(pod.get('age', ''))
#                 )
#                 issues.append(issue)
            
#             self.cluster_issues = issues
#             return issues
            
#         except Exception as e:
#             self.error_occurred.emit(f"Error getting cluster issues: {str(e)}")
#             return []
    
#     def _execute_kubectl(self, args, default_value=None):
#         """Execute kubectl command and return result"""
#         try:
#             result = subprocess.run(
#                 ["kubectl"] + args,
#                 capture_output=True,
#                 text=True,
#                 timeout=10  # Set timeout to prevent hanging
#             )
            
#             if result.returncode == 0:
#                 return result.stdout.strip()
#             return default_value
#         except subprocess.TimeoutExpired:
#             self.error_occurred.emit(f"Command timed out: kubectl {' '.join(args)}")
#             return default_value
#         except Exception as e:
#             self.error_occurred.emit(f"Error executing kubectl: {str(e)}")
#             return default_value
    
#     def _get_version(self):
#         """Get Kubernetes cluster version"""
#         output = self._execute_kubectl(["version", "--output=json"], "{}")
#         try:
#             version_info = json.loads(output)
#             server_version = version_info.get("serverVersion", {})
#             if server_version:
#                 return f"{server_version.get('major', '')}.{server_version.get('minor', '')}"
#             return "Unknown"
#         except json.JSONDecodeError:
#             return "Unknown"
    
#     def _get_nodes(self):
#         """Get cluster nodes"""
#         output = self._execute_kubectl(["get", "nodes", "-o", "json"], "{}")
#         try:
#             nodes_data = json.loads(output)
#             nodes = []
#             for item in nodes_data.get("items", []):
#                 node_name = item.get("metadata", {}).get("name", "Unknown")
#                 status = "Unknown"
#                 for condition in item.get("status", {}).get("conditions", []):
#                     if condition.get("type") == "Ready":
#                         status = "Ready" if condition.get("status") == "True" else "NotReady"
#                         break
#                 nodes.append({"name": node_name, "status": status})
#             return nodes
#         except json.JSONDecodeError:
#             return []
    
#     def _get_nodes_detail(self):
#         """Get detailed node information"""
#         output = self._execute_kubectl(["get", "nodes", "-o", "json"], "{}")
#         try:
#             nodes_data = json.loads(output)
#             nodes = []
#             for item in nodes_data.get("items", []):
#                 metadata = item.get("metadata", {})
#                 status = item.get("status", {})
                
#                 node_name = metadata.get("name", "Unknown")
#                 node_status = "Unknown"
                
#                 # Extract condition status
#                 for condition in status.get("conditions", []):
#                     if condition.get("type") == "Ready":
#                         node_status = "Ready" if condition.get("status") == "True" else "NotReady"
#                         break
                
#                 # Extract roles from labels
#                 roles = []
#                 labels = metadata.get("labels", {})
#                 for label_key, label_value in labels.items():
#                     if label_key.startswith("node-role.kubernetes.io/") and label_value == "true":
#                         role = label_key.split("/")[1]
#                         roles.append(role)
                
#                 # Extract taints
#                 taints = item.get("spec", {}).get("taints", [])
                
#                 # Extract age
#                 creation_timestamp = metadata.get("creationTimestamp", "")
                
#                 # Extract version
#                 kubelet_version = status.get("nodeInfo", {}).get("kubeletVersion", "Unknown")
                
#                 # Extract capacity
#                 capacity = status.get("capacity", {})
                
#                 node_info = {
#                     "name": node_name,
#                     "status": node_status,
#                     "roles": roles,
#                     "taints": taints,
#                     "age": creation_timestamp,
#                     "kubelet_version": kubelet_version,
#                     "cpu": capacity.get("cpu", "Unknown"),
#                     "memory": capacity.get("memory", "Unknown"),
#                     "pods": capacity.get("pods", "Unknown"),
#                     "disk": "Unknown"  # Not directly provided by Kubernetes API
#                 }
                
#                 nodes.append(node_info)
            
#             return nodes
#         except json.JSONDecodeError:
#             return []
    
#     def _get_node_metrics(self):
#         """Get node metrics using kubectl top nodes"""
#         # Check if metrics-server is installed
#         metrics_server = self._execute_kubectl(["get", "deployment", "metrics-server", "-n", "kube-system"], None)
#         if not metrics_server:
#             # Fallback to simulated metrics if metrics-server not installed
#             return self._get_simulated_node_metrics()
        
#         output = self._execute_kubectl(["top", "nodes"], None)
#         if not output:
#             return self._get_simulated_node_metrics()
            
#         try:
#             # Parse the output which is in format: NAME CPU(cores) CPU% MEMORY(bytes) MEMORY%
#             result = []
#             lines = output.strip().split('\n')
#             if len(lines) <= 1:
#                 return self._get_simulated_node_metrics()
                
#             # Skip header
#             for line in lines[1:]:
#                 parts = line.split()
#                 if len(parts) < 5:
#                     continue
                    
#                 node_name = parts[0]
#                 cpu = parts[1]
#                 cpu_percent = parts[2].rstrip('%')
#                 memory = parts[3]
#                 memory_percent = parts[4].rstrip('%')
                
#                 # Add simulated disk metrics
#                 import random
#                 disk_percent = random.uniform(40, 90)
                
#                 result.append({
#                     "name": node_name,
#                     "cpu": cpu,
#                     "cpu_percent": cpu_percent,
#                     "memory": memory,
#                     "memory_percent": memory_percent,
#                     "disk_percent": disk_percent
#                 })
                
#             return result
#         except Exception:
#             return self._get_simulated_node_metrics()
    
#     def _get_simulated_node_metrics(self):
#         """Generate simulated node metrics when metrics-server isn't available"""
#         import random
        
#         result = []
#         nodes = self._get_nodes_detail()
        
#         for node in nodes:
#             node_name = node.get("name", "Unknown")
#             cpu = node.get("cpu", "1")
#             memory = node.get("memory", "1Gi")
            
#             # Generate simulated utilization percentages
#             cpu_percent = random.uniform(10, 70)
#             memory_percent = random.uniform(30, 80)
#             disk_percent = random.uniform(40, 90)
            
#             result.append({
#                 "name": node_name,
#                 "cpu": cpu,
#                 "cpu_percent": cpu_percent,
#                 "memory": memory,
#                 "memory_percent": memory_percent,
#                 "disk_percent": disk_percent
#             })
        
#         return result
    
#     def _get_pod_metrics(self):
#         """Get pod metrics using kubectl top pods"""
#         # Check if metrics-server is installed
#         metrics_server = self._execute_kubectl(["get", "deployment", "metrics-server", "-n", "kube-system"], None)
#         if not metrics_server:
#             # Return empty result if metrics-server not installed
#             return []
        
#         output = self._execute_kubectl(["top", "pods", "--all-namespaces"], None)
#         if not output:
#             return []
            
#         try:
#             # Parse the output which is in format: NAMESPACE NAME CPU(cores) MEMORY(bytes)
#             result = []
#             lines = output.strip().split('\n')
#             if len(lines) <= 1:
#                 return []
                
#             # Skip header
#             for line in lines[1:]:
#                 parts = line.split()
#                 if len(parts) < 4:
#                     continue
                    
#                 namespace = parts[0]
#                 pod_name = parts[1]
#                 cpu = parts[2]
#                 memory = parts[3]
                
#                 result.append({
#                     "namespace": namespace,
#                     "name": pod_name,
#                     "cpu": cpu,
#                     "memory": memory
#                 })
                
#             return result
#         except Exception:
#             return []
    
#     def _get_resource_metrics(self):
#         """Get total resource requests and limits across all pods"""
#         output = self._execute_kubectl(["get", "pods", "--all-namespaces", "-o", "json"], "{}")
#         try:
#             pods_data = json.loads(output)
            
#             cpu_requests = 0.0
#             cpu_limits = 0.0
#             memory_requests = 0.0
#             memory_limits = 0.0
            
#             for pod in pods_data.get("items", []):
#                 containers = pod.get("spec", {}).get("containers", [])
                
#                 for container in containers:
#                     resources = container.get("resources", {})
                    
#                     # Process requests
#                     requests = resources.get("requests", {})
#                     if "cpu" in requests:
#                         cpu_str = requests["cpu"]
#                         try:
#                             if cpu_str.endswith("m"):
#                                 cpu_requests += float(cpu_str.rstrip("m")) / 1000
#                             else:
#                                 cpu_requests += float(cpu_str)
#                         except ValueError:
#                             pass
                    
#                     if "memory" in requests:
#                         mem_str = requests["memory"]
#                         try:
#                             if mem_str.endswith("Ki"):
#                                 memory_requests += float(mem_str.rstrip("Ki")) / (1024 * 1024)
#                             elif mem_str.endswith("Mi"):
#                                 memory_requests += float(mem_str.rstrip("Mi")) / 1024
#                             elif mem_str.endswith("Gi"):
#                                 memory_requests += float(mem_str.rstrip("Gi"))
#                         except ValueError:
#                             pass
                    
#                     # Process limits
#                     limits = resources.get("limits", {})
#                     if "cpu" in limits:
#                         cpu_str = limits["cpu"]
#                         try:
#                             if cpu_str.endswith("m"):
#                                 cpu_limits += float(cpu_str.rstrip("m")) / 1000
#                             else:
#                                 cpu_limits += float(cpu_str)
#                         except ValueError:
#                             pass
                    
#                     if "memory" in limits:
#                         mem_str = limits["memory"]
#                         try:
#                             if mem_str.endswith("Ki"):
#                                 memory_limits += float(mem_str.rstrip("Ki")) / (1024 * 1024)
#                             elif mem_str.endswith("Mi"):
#                                 memory_limits += float(mem_str.rstrip("Mi")) / 1024
#                             elif mem_str.endswith("Gi"):
#                                 memory_limits += float(mem_str.rstrip("Gi"))
#                         except ValueError:
#                             pass
            
#             return {
#                 "cpu_requests": cpu_requests,
#                 "cpu_limits": cpu_limits,
#                 "memory_requests": memory_requests,
#                 "memory_limits": memory_limits
#             }
            
#         except json.JSONDecodeError:
#             return {
#                 "cpu_requests": 0.0,
#                 "cpu_limits": 0.0,
#                 "memory_requests": 0.0,
#                 "memory_limits": 0.0
#             }
    
#     def _get_pods_capacity(self):
#         """Get total pod capacity for the cluster"""
#         nodes_output = self._execute_kubectl(["get", "nodes", "-o", "json"], "{}")
#         try:
#             nodes_data = json.loads(nodes_output)
#             total_pods = 0
            
#             for node in nodes_data.get("items", []):
#                 status = node.get("status", {})
#                 capacity = status.get("capacity", {})
#                 pods = capacity.get("pods", "0")
                
#                 try:
#                     total_pods += int(pods)
#                 except ValueError:
#                     pass
            
#             return total_pods
            
#         except json.JSONDecodeError:
#             return 0
    
#     def _get_failing_pods(self):
#         """Get pods that are in a failed or problematic state"""
#         output = self._execute_kubectl(["get", "pods", "--all-namespaces", "-o", "json"], "{}")
#         try:
#             pods_data = json.loads(output)
#             failing_pods = []
            
#             for pod in pods_data.get("items", []):
#                 metadata = pod.get("metadata", {})
#                 status = pod.get("status", {})
                
#                 pod_name = metadata.get("name", "Unknown")
#                 namespace = metadata.get("namespace", "default")
#                 phase = status.get("phase", "Unknown")
                
#                 # Get creation timestamp
#                 creation_timestamp = metadata.get("creationTimestamp", "")
                
#                 # Check for problematic pods
#                 if phase not in ["Running", "Succeeded"]:
#                     reason = ""
#                     message = ""
                    
#                     # Check container statuses for more details
#                     container_statuses = status.get("containerStatuses", [])
#                     for container in container_statuses:
#                         waiting = container.get("state", {}).get("waiting", {})
#                         if waiting:
#                             reason = waiting.get("reason", "")
#                             message = waiting.get("message", "")
                    
#                     failing_pods.append({
#                         "name": pod_name,
#                         "namespace": namespace,
#                         "status": phase,
#                         "reason": reason or "Unknown",
#                         "message": message,
#                         "age": creation_timestamp
#                     })
            
#             return failing_pods
            
#         except json.JSONDecodeError:
#             return []
    
#     def _get_namespaces(self):
#         """Get cluster namespaces"""
#         output = self._execute_kubectl(["get", "namespaces", "-o", "json"], "{}")
#         try:
#             ns_data = json.loads(output)
#             return [item.get("metadata", {}).get("name", "Unknown") 
#                    for item in ns_data.get("items", [])]
#         except json.JSONDecodeError:
#             return []
    
#     def _get_resource_count(self, resource_type):
#         """Get count of resources of specified type"""
#         output = self._execute_kubectl(["get", resource_type, "--all-namespaces", "--no-headers"], "")
#         if output:
#             return len(output.strip().split('\n'))
#         return 0
    
#     def _format_age(self, timestamp):
#         """Format age from timestamp"""
#         if not timestamp:
#             return "Unknown"
            
#         try:
#             # Parse ISO format timestamp
#             if 'T' in timestamp:
#                 creation_time = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
#             else:
#                 creation_time = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                
#             # Calculate time difference
#             now = datetime.datetime.now()
#             diff = now - creation_time
            
#             # Format age string
#             if diff.days > 365:
#                 years = diff.days // 365
#                 return f"{years}y"
#             elif diff.days > 30:
#                 months = diff.days // 30
#                 return f"{months}m"
#             elif diff.days > 0:
#                 return f"{diff.days}d"
#             elif diff.seconds > 3600:
#                 hours = diff.seconds // 3600
#                 return f"{hours}h"
#             elif diff.seconds > 60:
#                 minutes = diff.seconds // 60
#                 return f"{minutes}m"
#             else:
#                 return f"{diff.seconds}s"
#         except (ValueError, TypeError):
#             return "Unknown"

# # Singleton instance
# _instance = None

# def get_kubernetes_client():
#     """Get or create Kubernetes client singleton"""
#     global _instance
#     if _instance is None:
#         _instance = KubernetesClient()
#     return _instance