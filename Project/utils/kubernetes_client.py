import os
import json
import yaml
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

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

class KubernetesClient(QObject):
    """Client for interacting with Kubernetes clusters"""
    clusters_loaded = pyqtSignal(list)
    cluster_info_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.threadpool = QThreadPool()
        self.clusters = []
        self.current_cluster = None
        self._default_kubeconfig = os.path.expanduser("~/.kube/config")
    
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
            return info
            
        except Exception as e:
            self.error_occurred.emit(f"Error getting cluster info: {str(e)}")
            return None
    
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
                nodes.append({"name": node_name, "status": status})
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

# Singleton instance
_instance = None

def get_kubernetes_client():
    """Get or create Kubernetes client singleton"""
    global _instance
    if _instance is None:
        _instance = KubernetesClient()
    return _instance