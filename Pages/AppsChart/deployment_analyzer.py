"""
Deployment Analyzer - Thread for analyzing deployments and creating app diagrams
Split from AppsChartPage.py for better architecture
"""

import logging
from PyQt6.QtCore import QThread, pyqtSignal
from Utils.kubernetes_client import get_kubernetes_client
from kubernetes.client.rest import ApiException


class DeploymentAnalyzer(QThread):
    """Thread for analyzing deployments and creating app diagrams"""
    analysis_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    def __init__(self, namespace, key_filter, value_filter, parent=None):
        super().__init__(parent)
        self.namespace = namespace
        self.key_filter = key_filter.strip()
        self.value_filter = value_filter.strip()
        self.kube_client = get_kubernetes_client()
    
    def run(self):
        try:
            if not self.kube_client or not self.kube_client.v1 or not self.kube_client.apps_v1:
                self.error_occurred.emit("Kubernetes client not initialized")
                return
            
            self.progress_updated.emit("Fetching deployments...")
            
            # Fetch deployments from the specified namespace
            if self.namespace == "All Namespaces":
                deployments = self.kube_client.apps_v1.list_deployment_for_all_namespaces()
            else:
                deployments = self.kube_client.apps_v1.list_namespaced_deployment(namespace=self.namespace)
            
            self.progress_updated.emit(f"Found {len(deployments.items)} deployments. Analyzing...")
            
            # Filter deployments by labels if provided
            filtered_deployments = []
            for deployment in deployments.items:
                if self._matches_label_filter(deployment):
                    filtered_deployments.append(deployment)
            
            if not filtered_deployments:
                self.error_occurred.emit(f"No deployments found matching labels {self.key_filter}={self.value_filter}")
                return
            
            self.progress_updated.emit(f"Analyzing {len(filtered_deployments)} matching deployments...")
            
            # Analyze deployments and create diagram data
            diagram_data = self._analyze_deployments(filtered_deployments)
            
            self.progress_updated.emit("Analysis complete!")
            self.analysis_completed.emit(diagram_data)
            
        except ApiException as e:
            self.error_occurred.emit(f"API error: {e.reason}")
        except Exception as e:
            self.error_occurred.emit(f"Analysis failed: {str(e)}")
    
    def _matches_label_filter(self, deployment):
        """Check if deployment matches the label filter"""
        if not self.key_filter or not self.value_filter:
            return True  # No filter specified, include all
        
        labels = deployment.metadata.labels or {}
        return labels.get(self.key_filter) == self.value_filter
    
    def _analyze_deployments(self, deployments):
        """Analyze deployments and create diagram structure"""
        diagram_data = {
            "deployments": [],
            "services": [],
            "connections": [],
            "namespace": self.namespace,
            "filter": f"{self.key_filter}={self.value_filter}" if self.key_filter and self.value_filter else "No filter"
        }
        
        for deployment in deployments:
            # Analyze deployment details
            dep_info = self._analyze_deployment(deployment)
            diagram_data["deployments"].append(dep_info)
            
            # Find related services
            services = self._find_related_services(deployment)
            diagram_data["services"].extend(services)
            
            # Create connections
            for service in services:
                diagram_data["connections"].append({
                    "from": dep_info["name"],
                    "to": service["name"],
                    "type": "service"
                })
        
        return diagram_data
    
    def _analyze_deployment(self, deployment):
        """Analyze a single deployment"""
        spec = deployment.spec
        status = deployment.status
        metadata = deployment.metadata
        
        return {
            "name": metadata.name,
            "namespace": metadata.namespace,
            "replicas": spec.replicas or 1,
            "ready_replicas": status.ready_replicas or 0,
            "labels": metadata.labels or {},
            "selector": spec.selector.match_labels or {},
            "containers": [{
                "name": container.name,
                "image": container.image,
                "ports": [p.container_port for p in (container.ports or [])]
            } for container in spec.template.spec.containers],
            "created": metadata.creation_timestamp.isoformat() if metadata.creation_timestamp else "Unknown"
        }
    
    def _find_related_services(self, deployment):
        """Find services that target this deployment"""
        services = []
        try:
            # Get services from the same namespace
            if deployment.metadata.namespace:
                svc_list = self.kube_client.v1.list_namespaced_service(namespace=deployment.metadata.namespace)
            else:
                svc_list = self.kube_client.v1.list_service_for_all_namespaces()
            
            deployment_labels = deployment.spec.selector.match_labels or {}
            
            for service in svc_list.items:
                service_selector = service.spec.selector or {}
                
                # Check if service selector matches deployment labels
                if self._selectors_match(service_selector, deployment_labels):
                    services.append({
                        "name": service.metadata.name,
                        "namespace": service.metadata.namespace,
                        "type": service.spec.type,
                        "ports": [{
                            "port": p.port,
                            "target_port": p.target_port,
                            "protocol": p.protocol
                        } for p in (service.spec.ports or [])]
                    })
        
        except Exception as e:
            logging.warning(f"Could not fetch services for deployment {deployment.metadata.name}: {e}")
        
        return services
    
    def _selectors_match(self, service_selector, deployment_labels):
        """Check if service selector matches deployment labels"""
        if not service_selector:
            return False
        
        for key, value in service_selector.items():
            if deployment_labels.get(key) != value:
                return False
        return True