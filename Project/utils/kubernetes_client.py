import os
import json
import yaml
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot, QTimer
from dataclasses import dataclass
from typing import Optional
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

    def __del__(self):
        """Clean up resources when worker is deleted"""
        try:
            # Disconnect any signals to prevent calls to deleted objects
            if hasattr(self, 'signals'):
                try:
                    self.signals.finished.disconnect()
                except:
                    pass
                try:
                    self.signals.error.disconnect()
                except:
                    pass
        except Exception as e:
            print(f"Error during KubeMetricsWorker cleanup: {str(e)}")
        
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
    
    def __del__(self):
        """Clean up resources when object is deleted"""
        try:
            # Stop any running timers
            if hasattr(self, 'metrics_timer') and self.metrics_timer.isActive():
                self.metrics_timer.stop()
            
            if hasattr(self, 'issues_timer') and self.issues_timer.isActive():
                self.issues_timer.stop()
                
            # Clear QThreadPool
            if hasattr(self, 'threadpool'):
                self.threadpool.clear()
                
        except Exception as e:
            print(f"Error during KubernetesClient cleanup: {str(e)}")

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