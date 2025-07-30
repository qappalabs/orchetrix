"""
Simple Apps page with namespace dropdown and basic key-value inputs.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, 
    QPushButton, QFrame, QSizePolicy, QTextEdit, QScrollArea, QGraphicsView,
    QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
    QMessageBox, QProgressDialog, QGraphicsPixmapItem, QFileDialog, QMenu, QToolButton,
    QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QRectF, QPointF
from PyQt6.QtGui import QFont, QPen, QBrush, QColor, QPainter, QPixmap, QIcon, QAction

from UI.Styles import AppStyles, AppColors
from utils.kubernetes_client import get_kubernetes_client
from kubernetes.client.rest import ApiException
from business_logic.app_flow_business import (
    AppFlowBusinessLogic, ResourceType, GraphLayout, ResourceInfo, ConnectionInfo
)
import logging
import json
import os
from datetime import datetime


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


class NamespaceLoader(QThread):
    """Thread for loading namespaces asynchronously"""
    namespaces_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.kube_client = get_kubernetes_client()
    
    def run(self):
        try:
            if not self.kube_client or not self.kube_client.v1:
                self.error_occurred.emit("Kubernetes client not initialized")
                return
            
            # Load all namespaces
            namespaces_list = self.kube_client.v1.list_namespace()
            namespace_names = []
            
            for ns in namespaces_list.items:
                if ns.metadata and ns.metadata.name:
                    namespace_names.append(ns.metadata.name)
            
            # Sort namespaces alphabetically
            namespace_names.sort()
            self.namespaces_loaded.emit(namespace_names)
            
        except ApiException as e:
            self.error_occurred.emit(f"API error: {e.reason}")
        except Exception as e:
            self.error_occurred.emit(f"Failed to load namespaces: {str(e)}")


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


class AppFlowAnalyzer(QThread):
    """Thread for analyzing app flow and creating comprehensive graph"""
    analysis_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    def __init__(self, namespace, workload_type, resource_name, parent=None):
        super().__init__(parent)
        self.workload_type = workload_type.lower()
        self.resource_name = resource_name
        
        # Handle namespace and resource name extraction
        if namespace == "All Namespaces" and "(" in self.resource_name and ")" in self.resource_name:
            # Extract namespace from resource name format: "resource-name (namespace)"
            parts = self.resource_name.split(" (")
            self.resource_name = parts[0]
            self.namespace = parts[1].rstrip(")")
        else:
            # Use provided namespace and clean resource name
            self.namespace = namespace
            if "(" in self.resource_name and ")" in self.resource_name:
                self.resource_name = self.resource_name.split(" (")[0]
        
        self.kube_client = get_kubernetes_client()
        logging.info(f"AppFlowAnalyzer initialized: namespace={self.namespace}, workload_type={self.workload_type}, resource_name={self.resource_name}")
    
    def run(self):
        try:
            if not self.kube_client:
                self.error_occurred.emit("Kubernetes client not initialized")
                return
                
            self.progress_updated.emit(f"Analyzing {self.resource_name}...")
            
            # Get the main resource
            main_resource = self._get_main_resource()
            if not main_resource:
                self.error_occurred.emit(f"Could not find {self.workload_type} {self.resource_name}")
                return
            
            # Build comprehensive app flow
            app_flow = {
                "main_resource": main_resource,
                "ingresses": [],
                "services": [],
                "deployments": [],
                "pods": [],
                "configmaps": [],
                "secrets": [],
                "pvcs": [],
                "connections": [],
                "namespace": self.namespace,
                "workload_type": self.workload_type
            }
            
            # Analyze based on workload type
            if self.workload_type in ["deployments", "statefulsets", "daemonsets", "replicasets"]:
                self._analyze_workload_flow(main_resource, app_flow)
            elif self.workload_type == "pods":
                self._analyze_pod_flow(main_resource, app_flow)
            elif self.workload_type in ["jobs", "cronjobs"]:
                self._analyze_job_flow(main_resource, app_flow)
            elif self.workload_type == "replicationcontrollers":
                self._analyze_workload_flow(main_resource, app_flow)
            else:
                # For other types, just show the main resource as a deployment-like object
                main_info = self._extract_workload_info(main_resource)
                app_flow["deployments"].append(main_info)
            
            self.progress_updated.emit("Analysis complete!")
            self.analysis_completed.emit(app_flow)
            
        except Exception as e:
            self.error_occurred.emit(f"Analysis failed: {str(e)}")
    
    def _get_main_resource(self):
        """Get the main resource object"""
        try:
            logging.info(f"Trying to get {self.workload_type} '{self.resource_name}' from namespace '{self.namespace}'")
            
            if self.workload_type == "deployments":
                return self.kube_client.apps_v1.read_namespaced_deployment(
                    name=self.resource_name, namespace=self.namespace)
            elif self.workload_type == "statefulsets":
                return self.kube_client.apps_v1.read_namespaced_stateful_set(
                    name=self.resource_name, namespace=self.namespace)
            elif self.workload_type == "daemonsets":
                return self.kube_client.apps_v1.read_namespaced_daemon_set(
                    name=self.resource_name, namespace=self.namespace)
            elif self.workload_type == "pods":
                return self.kube_client.v1.read_namespaced_pod(
                    name=self.resource_name, namespace=self.namespace)
            elif self.workload_type == "replicasets":
                return self.kube_client.apps_v1.read_namespaced_replica_set(
                    name=self.resource_name, namespace=self.namespace)
            elif self.workload_type == "jobs":
                return self.kube_client.batch_v1.read_namespaced_job(
                    name=self.resource_name, namespace=self.namespace)
            elif self.workload_type == "cronjobs":
                return self.kube_client.batch_v1.read_namespaced_cron_job(
                    name=self.resource_name, namespace=self.namespace)
            elif self.workload_type == "replicationcontrollers":
                return self.kube_client.v1.read_namespaced_replication_controller(
                    name=self.resource_name, namespace=self.namespace)
            else:
                logging.error(f"Unsupported workload type: {self.workload_type}")
                return None
                
        except ApiException as e:
            logging.error(f"API error getting {self.workload_type} '{self.resource_name}' from namespace '{self.namespace}': {e.reason}")
            return None
        except Exception as e:
            logging.error(f"Failed to get main resource: {e}")
            return None
    
    def _analyze_workload_flow(self, workload, app_flow):
        """Analyze flow for deployment-like workloads"""
        self.progress_updated.emit("Finding related services...")
        
        # Add the workload itself
        workload_info = self._extract_workload_info(workload)
        app_flow["deployments"].append(workload_info)
        
        # Find services that target this workload
        services = self._find_related_services(workload)
        app_flow["services"].extend(services)
        
        # Find ingresses that target the services
        ingresses = self._find_related_ingresses(services)
        app_flow["ingresses"].extend(ingresses)
        
        # Find pods created by this workload
        pods = self._find_related_pods(workload)
        app_flow["pods"].extend(pods)
        
        # Find config and secrets
        configs = self._find_related_configs(workload)
        app_flow["configmaps"].extend(configs.get("configmaps", []))
        app_flow["secrets"].extend(configs.get("secrets", []))
        app_flow["pvcs"].extend(configs.get("pvcs", []))
        
        # Create connections
        self._create_connections(app_flow)
    
    def _analyze_pod_flow(self, pod, app_flow):
        """Analyze flow for a single pod"""
        pod_info = self._extract_pod_info(pod)
        app_flow["pods"].append(pod_info)
        
        # Find services that might target this pod
        services = self._find_services_for_pod(pod)
        app_flow["services"].extend(services)
        
        # Find configs and secrets used by pod
        configs = self._find_pod_configs(pod)
        app_flow["configmaps"].extend(configs.get("configmaps", []))
        app_flow["secrets"].extend(configs.get("secrets", []))
        app_flow["pvcs"].extend(configs.get("pvcs", []))
        
        self._create_connections(app_flow)
    
    def _analyze_job_flow(self, job, app_flow):
        """Analyze flow for job-like workloads"""
        self.progress_updated.emit("Finding related pods...")
        
        # Add the job itself as a deployment-like object
        job_info = self._extract_workload_info(job)
        app_flow["deployments"].append(job_info)
        
        # Find pods created by this job
        pods = self._find_related_pods(job)
        app_flow["pods"].extend(pods)
        
        # Find config and secrets
        configs = self._find_related_configs(job)
        app_flow["configmaps"].extend(configs.get("configmaps", []))
        app_flow["secrets"].extend(configs.get("secrets", []))
        app_flow["pvcs"].extend(configs.get("pvcs", []))
        
        # Create connections
        self._create_connections(app_flow)
    
    def _extract_workload_info(self, workload):
        """Extract information from workload resource"""
        metadata = workload.metadata
        spec = workload.spec
        status = getattr(workload, 'status', None)
        
        # Handle different workload types
        containers = []
        selector = {}
        replicas = 1
        ready_replicas = 0
        
        if hasattr(spec, 'template') and spec.template and spec.template.spec:
            # Deployment-like resources
            containers = self._extract_containers(spec.template.spec.containers)
            if hasattr(spec, 'selector') and spec.selector:
                selector = getattr(spec.selector, 'match_labels', {})
            replicas = getattr(spec, 'replicas', 1)
            ready_replicas = getattr(status, 'ready_replicas', 0) if status else 0
        elif hasattr(spec, 'jobTemplate') and spec.jobTemplate:
            # CronJob
            if spec.jobTemplate.spec.template and spec.jobTemplate.spec.template.spec:
                containers = self._extract_containers(spec.jobTemplate.spec.template.spec.containers)
            replicas = 1
            ready_replicas = 1 if status and getattr(status, 'active', 0) > 0 else 0
        elif hasattr(spec, 'containers'):
            # Pod-like resources
            containers = self._extract_containers(spec.containers)
            replicas = 1
            ready_replicas = 1 if status and getattr(status, 'phase', '') == 'Running' else 0
        
        return {
            "name": metadata.name,
            "namespace": metadata.namespace,
            "type": self.workload_type,
            "labels": metadata.labels or {},
            "selector": selector,
            "replicas": replicas,
            "ready_replicas": ready_replicas,
            "containers": containers
        }
    
    def _extract_pod_info(self, pod):
        """Extract information from pod resource"""
        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "type": "pod",
            "labels": pod.metadata.labels or {},
            "phase": pod.status.phase if pod.status else "Unknown",
            "containers": self._extract_containers(pod.spec.containers)
        }
    
    def _extract_containers(self, containers):
        """Extract container information"""
        if not containers:
            return []
        
        container_list = []
        for container in containers:
            try:
                container_info = {
                    "name": getattr(container, 'name', 'unknown'),
                    "image": getattr(container, 'image', 'unknown'),
                    "ports": []
                }
                
                if hasattr(container, 'ports') and container.ports:
                    container_info["ports"] = [
                        getattr(p, 'container_port', 0) for p in container.ports
                    ]
                
                container_list.append(container_info)
            except Exception as e:
                logging.warning(f"Error extracting container info: {e}")
                container_list.append({
                    "name": "unknown",
                    "image": "unknown", 
                    "ports": []
                })
        
        return container_list
    
    def _find_related_services(self, workload):
        """Find services that target this workload"""
        services = []
        try:
            svc_list = self.kube_client.v1.list_namespaced_service(namespace=self.namespace)
            workload_labels = workload.spec.selector.match_labels if hasattr(workload.spec, 'selector') else {}
            
            for service in svc_list.items:
                service_selector = service.spec.selector or {}
                if self._selectors_match(service_selector, workload_labels):
                    services.append({
                        "name": service.metadata.name,
                        "namespace": service.metadata.namespace,
                        "type": service.spec.type,
                        "cluster_ip": service.spec.cluster_ip,
                        "ports": [{
                            "port": p.port,
                            "target_port": p.target_port,
                            "protocol": p.protocol
                        } for p in (service.spec.ports or [])]
                    })
        except Exception as e:
            logging.warning(f"Could not fetch services: {e}")
        return services
    
    def _find_related_ingresses(self, services):
        """Find ingresses that target the services"""
        ingresses = []
        try:
            ing_list = self.kube_client.networking_v1.list_namespaced_ingress(namespace=self.namespace)
            service_names = [svc["name"] for svc in services]
            
            for ingress in ing_list.items:
                if ingress.spec.rules:
                    for rule in ingress.spec.rules:
                        if rule.http and rule.http.paths:
                            for path in rule.http.paths:
                                if path.backend.service and path.backend.service.name in service_names:
                                    ingresses.append({
                                        "name": ingress.metadata.name,
                                        "namespace": ingress.metadata.namespace,
                                        "host": rule.host or "N/A",
                                        "path": path.path,
                                        "service": path.backend.service.name,
                                        "port": path.backend.service.port.number if path.backend.service.port else "N/A"
                                    })
                                    break
        except Exception as e:
            logging.warning(f"Could not fetch ingresses: {e}")
        return ingresses
    
    def _find_related_pods(self, workload):
        """Find pods created by this workload"""
        pods = []
        try:
            pod_list = self.kube_client.v1.list_namespaced_pod(namespace=self.namespace)
            workload_labels = workload.spec.selector.match_labels if hasattr(workload.spec, 'selector') else {}
            
            for pod in pod_list.items:
                pod_labels = pod.metadata.labels or {}
                if self._selectors_match(workload_labels, pod_labels):
                    pods.append(self._extract_pod_info(pod))
        except Exception as e:
            logging.warning(f"Could not fetch pods: {e}")
        return pods
    
    def _find_related_configs(self, workload):
        """Find configmaps, secrets, and PVCs used by workload"""
        configs = {"configmaps": [], "secrets": [], "pvcs": []}
        
        try:
            # Extract from pod template
            if hasattr(workload.spec, 'template') and workload.spec.template.spec:
                pod_spec = workload.spec.template.spec
                
                # Check volumes
                if pod_spec.volumes:
                    for volume in pod_spec.volumes:
                        if volume.config_map:
                            configs["configmaps"].append({
                                "name": volume.config_map.name,
                                "namespace": self.namespace,
                                "type": "configmap"
                            })
                        elif volume.secret:
                            configs["secrets"].append({
                                "name": volume.secret.secret_name,
                                "namespace": self.namespace,
                                "type": "secret"
                            })
                        elif volume.persistent_volume_claim:
                            configs["pvcs"].append({
                                "name": volume.persistent_volume_claim.claim_name,
                                "namespace": self.namespace,
                                "type": "pvc"
                            })
                
                # Check environment variables
                for container in pod_spec.containers:
                    if container.env:
                        for env in container.env:
                            if env.value_from:
                                if env.value_from.config_map_key_ref:
                                    config_name = env.value_from.config_map_key_ref.name
                                    if not any(c["name"] == config_name for c in configs["configmaps"]):
                                        configs["configmaps"].append({
                                            "name": config_name,
                                            "namespace": self.namespace,
                                            "type": "configmap"
                                        })
                                elif env.value_from.secret_key_ref:
                                    secret_name = env.value_from.secret_key_ref.name
                                    if not any(s["name"] == secret_name for s in configs["secrets"]):
                                        configs["secrets"].append({
                                            "name": secret_name,
                                            "namespace": self.namespace,
                                            "type": "secret"
                                        })
        except Exception as e:
            logging.warning(f"Could not analyze configs: {e}")
        
        return configs
    
    def _find_services_for_pod(self, pod):
        """Find services that might target this pod"""
        services = []
        try:
            svc_list = self.kube_client.v1.list_namespaced_service(namespace=self.namespace)
            pod_labels = pod.metadata.labels or {}
            
            for service in svc_list.items:
                service_selector = service.spec.selector or {}
                if self._selectors_match(service_selector, pod_labels):
                    services.append({
                        "name": service.metadata.name,
                        "namespace": service.metadata.namespace,
                        "type": service.spec.type,
                        "ports": [{"port": p.port, "target_port": p.target_port} for p in (service.spec.ports or [])]
                    })
        except Exception as e:
            logging.warning(f"Could not fetch services for pod: {e}")
        return services
    
    def _find_pod_configs(self, pod):
        """Find configs used by a pod"""
        configs = {"configmaps": [], "secrets": [], "pvcs": []}
        
        try:
            if pod.spec.volumes:
                for volume in pod.spec.volumes:
                    if volume.config_map:
                        configs["configmaps"].append({
                            "name": volume.config_map.name,
                            "namespace": self.namespace,
                            "type": "configmap"
                        })
                    elif volume.secret:
                        configs["secrets"].append({
                            "name": volume.secret.secret_name,
                            "namespace": self.namespace,
                            "type": "secret"
                        })
                    elif volume.persistent_volume_claim:
                        configs["pvcs"].append({
                            "name": volume.persistent_volume_claim.claim_name,
                            "namespace": self.namespace,
                            "type": "pvc"
                        })
        except Exception as e:
            logging.warning(f"Could not analyze pod configs: {e}")
        
        return configs
    
    def _selectors_match(self, selector, labels):
        """Check if selector matches labels"""
        if not selector:
            return False
        for key, value in selector.items():
            if labels.get(key) != value:
                return False
        return True
    
    def _create_connections(self, app_flow):
        """Create connection information for graph drawing"""
        connections = []
        
        # Ingress -> Service connections
        for ingress in app_flow["ingresses"]:
            connections.append({
                "from": f"ingress:{ingress['name']}",
                "to": f"service:{ingress['service']}",
                "type": "ingress_to_service"
            })
        
        # Service -> Deployment connections
        for service in app_flow["services"]:
            for deployment in app_flow["deployments"]:
                connections.append({
                    "from": f"service:{service['name']}",
                    "to": f"deployment:{deployment['name']}",
                    "type": "service_to_deployment"
                })
        
        # Deployment -> Pod connections (single arrow)
        if app_flow["deployments"] and app_flow["pods"]:
            # Use first deployment and first pod as representatives
            connections.append({
                "from": f"deployment:{app_flow['deployments'][0]['name']}",
                "to": f"pod:{app_flow['pods'][0]['name']}",
                "type": "deployment_to_pod"
            })
        
        # Pod -> Config connections (single arrow per config type)
        if app_flow["pods"]:
            first_pod = app_flow["pods"][0]["name"]
            
            if app_flow["configmaps"]:
                connections.append({
                    "from": f"pod:{first_pod}",
                    "to": f"configmap:{app_flow['configmaps'][0]['name']}",
                    "type": "pod_to_config"
                })
            
            if app_flow["secrets"]:
                connections.append({
                    "from": f"pod:{first_pod}",
                    "to": f"secret:{app_flow['secrets'][0]['name']}",
                    "type": "pod_to_secret"
                })
            
            if app_flow["pvcs"]:
                connections.append({
                    "from": f"pod:{first_pod}",
                    "to": f"pvc:{app_flow['pvcs'][0]['name']}",
                    "type": "pod_to_pvc"
                })
        
        app_flow["connections"] = connections


class AppsPage(QWidget):
    """Simple Apps page with proper header layout matching other pages"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.business_logic = AppFlowBusinessLogic()
        self.current_app_flow_data = None
        self.current_resource_positions = {}  # Store current positions for live updates
        self.live_monitoring_enabled = False
        self.setup_ui()
        
        # Set horizontal layout by default
        self.business_logic.set_graph_layout(GraphLayout.HORIZONTAL)
        
        # Setup live monitoring timer
        self.live_monitor_timer = QTimer()
        self.live_monitor_timer.timeout.connect(self.update_live_monitoring)
        self.live_monitor_timer.setInterval(5000)  # Update every 5 seconds
        
        # Load namespaces after UI is set up
        QTimer.singleShot(100, self.load_namespaces)
        
        # Connect dropdown change events
        self.namespace_combo.currentTextChanged.connect(self.on_selection_changed)
        self.workload_combo.currentTextChanged.connect(self.on_selection_changed)
    
    def setup_ui(self):
        """Setup the UI mimicking BaseResourcePage header layout"""
        # Main layout with reduced margins and spacing
        page_main_layout = QVBoxLayout(self)
        page_main_layout.setContentsMargins(12, 8, 12, 12)
        page_main_layout.setSpacing(8)
        
        # Create header layout (single line) exactly like BaseResourcePage
        header_controls_layout = QHBoxLayout()
        
        # Title and count (left side)
        self._create_title_and_count(header_controls_layout)
        
        # Filter controls (middle)
        self._add_filter_controls(header_controls_layout)
        
        # Stretch to push buttons to right
        header_controls_layout.addStretch(1)
        
        # Remove labels controls - keeping only namespace dropdown
        
        # Live monitoring button
        self.live_monitor_btn = QPushButton("▶ Start Live")
        self.live_monitor_btn.setStyleSheet("""
            QPushButton { 
                background-color: #28a745; 
                color: #ffffff; 
                border: 1px solid #34ce57;
                border-radius: 4px; 
                padding: 5px 10px; 
                font-weight: bold;
            }
            QPushButton:hover { 
                background-color: #34ce57; 
            }
            QPushButton:pressed { 
                background-color: #1e7e34; 
            }
            QPushButton:disabled {
                background-color: #6c757d;
                border-color: #6c757d;
                color: #adb5bd;
            }
        """)
        self.live_monitor_btn.clicked.connect(self.toggle_live_monitoring)
        header_controls_layout.addWidget(self.live_monitor_btn)
        
        # Add some spacing
        header_controls_layout.addSpacing(10)
        
        # Refresh button (far right) - optional, matching other pages
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton { 
                background-color: #2d2d2d; 
                color: #ffffff; 
                border: 1px solid #3d3d3d;
                border-radius: 4px; 
                padding: 5px 10px; 
            }
            QPushButton:hover { 
                background-color: #3d3d3d; 
            }
            QPushButton:pressed { 
                background-color: #1e1e1e; 
            }
        """)
        refresh_btn.clicked.connect(self.refresh_page)
        header_controls_layout.addWidget(refresh_btn)
        
        # Add header to main layout
        page_main_layout.addLayout(header_controls_layout)
        
        # Create diagram area
        self.create_diagram_area(page_main_layout)
    
    def _create_title_and_count(self, layout):
        """Create title label only"""
        title_label = QLabel("Apps")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        
        layout.addWidget(title_label)
    
    def _add_filter_controls(self, header_layout):
        """Add namespace control in header"""
        filters_widget = QWidget()
        filters_layout = QHBoxLayout(filters_widget)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(10)
        
        # Add spacing to shift namespace right
        filters_layout.addSpacing(20)
        
        # Namespace control
        namespace_label = QLabel("Namespace:")
        namespace_label.setStyleSheet("color: #ffffff; font-size: 13px; margin-right: 5px;")
        filters_layout.addWidget(namespace_label)
        
        self.namespace_combo = QComboBox()
        self.namespace_combo.setFixedHeight(30)
        self.namespace_combo.setMinimumWidth(150)
        # Configure dropdown behavior to prevent upward opening
        self._configure_dropdown_behavior(self.namespace_combo)
        
        # Use the exact same style as other pages from AppStyles
        self.namespace_combo.setStyleSheet(AppStyles.COMBO_BOX_STYLE)
        self.namespace_combo.addItem("Loading...")
        self.namespace_combo.setEnabled(False)
        filters_layout.addWidget(self.namespace_combo)
        
        # Add spacing between dropdowns
        filters_layout.addSpacing(15)
        
        # Workload control
        workload_label = QLabel("Workload:")
        workload_label.setStyleSheet("color: #ffffff; font-size: 13px; margin-right: 5px;")
        filters_layout.addWidget(workload_label)
        
        self.workload_combo = QComboBox()
        self.workload_combo.setFixedHeight(30)
        self.workload_combo.setMinimumWidth(150)
        # Configure dropdown behavior to prevent upward opening
        self._configure_dropdown_behavior(self.workload_combo)
        
        # Use the exact same style as other pages from AppStyles
        self.workload_combo.setStyleSheet(AppStyles.COMBO_BOX_STYLE)
        
        # Add workload items
        workload_items = [
            "Pods", 
            "Deployments",
            "StatefulSets", 
            "DaemonSets",
            "ReplicaSets",
            "Jobs",
            "CronJobs",
            "ReplicationControllers"
        ]
        self.workload_combo.addItems(workload_items)
        self.workload_combo.setCurrentText("Deployments")
        filters_layout.addWidget(self.workload_combo)
        
        # Add spacing between dropdowns
        filters_layout.addSpacing(15)
        
        # Resource instances control
        resource_label = QLabel("Resource:")
        resource_label.setStyleSheet("color: #ffffff; font-size: 13px; margin-right: 5px;")
        filters_layout.addWidget(resource_label)
        
        self.resource_combo = QComboBox()
        self.resource_combo.setFixedHeight(30)
        self.resource_combo.setMinimumWidth(200)
        # Configure dropdown behavior to prevent upward opening
        self._configure_dropdown_behavior(self.resource_combo)
        
        # Use the exact same style as other pages from AppStyles
        self.resource_combo.setStyleSheet(AppStyles.COMBO_BOX_STYLE)
        self.resource_combo.addItem("Select namespace and workload first")
        self.resource_combo.setEnabled(False)
        # Connect resource selection change
        self.resource_combo.currentTextChanged.connect(self.on_resource_selected)
        filters_layout.addWidget(self.resource_combo)
        
        header_layout.addWidget(filters_widget)
    
    
    def _configure_dropdown_behavior(self, combo_box):
        """Configure dropdown behavior to prevent upward opening (like other pages)"""
        try:
            # Set view to list view for consistency
            combo_box.view().setMinimumWidth(combo_box.minimumWidth())
            # Set maximum visible items
            combo_box.setMaxVisibleItems(10)
        except Exception as e:
            logging.debug(f"Could not configure dropdown behavior: {e}")
    
    # Diagram functionality added above
    
    def load_namespaces(self):
        """Load namespaces asynchronously"""
        self.namespace_loader = NamespaceLoader(self)
        self.namespace_loader.namespaces_loaded.connect(self.on_namespaces_loaded)
        self.namespace_loader.error_occurred.connect(self.on_namespace_error)
        self.namespace_loader.start()
    
    def on_namespaces_loaded(self, namespaces):
        """Handle loaded namespaces"""
        self.namespace_combo.blockSignals(True)
        self.namespace_combo.clear()
        self.namespace_combo.addItem("All Namespaces")
        self.namespace_combo.addItems(namespaces)
        
        # Set default namespace if available
        if "default" in namespaces:
            self.namespace_combo.setCurrentText("default")
        elif namespaces:
            self.namespace_combo.setCurrentIndex(1)
        else:
            self.namespace_combo.setCurrentText("All Namespaces")
        
        self.namespace_combo.blockSignals(False)
        self.namespace_combo.setEnabled(True)
        logging.info(f"Loaded {len(namespaces)} namespaces for Apps page")
        
        # Trigger initial resource loading
        QTimer.singleShot(100, self.on_selection_changed)
    
    def on_namespace_error(self, error_message):
        """Handle namespace loading error"""
        self.namespace_combo.blockSignals(True)
        self.namespace_combo.clear()
        self.namespace_combo.addItem("All Namespaces")
        self.namespace_combo.addItem("default")
        self.namespace_combo.setCurrentText("default")
        self.namespace_combo.blockSignals(False)
        self.namespace_combo.setEnabled(True)
        logging.error(f"Failed to load namespaces for Apps page: {error_message}")
    
    def on_selection_changed(self):
        """Handle namespace or workload selection change"""
        namespace = self.namespace_combo.currentText()
        workload_type = self.workload_combo.currentText()
        
        # Check if we have valid selections
        if not namespace or namespace == "Loading..." or not workload_type:
            return
        
        # Stop live monitoring if active when selection changes
        if self.live_monitoring_enabled:
            self.toggle_live_monitoring()
        
        # Clear the diagram when selection changes
        self.diagram_scene.clear()
        
        # Reset diagram title
        self.diagram_title.setText("App Diagram")
        
        # Reset status text
        self.status_text.setPlainText("Loading resources...")
        
        # Disable live monitoring button
        self.live_monitor_btn.setEnabled(False)
        
        # Stop any running analyzer
        if hasattr(self, 'app_flow_analyzer') and self.app_flow_analyzer.isRunning():
            self.app_flow_analyzer.terminate()
            self.app_flow_analyzer.wait()
        
        if hasattr(self, 'live_app_flow_analyzer') and self.live_app_flow_analyzer.isRunning():
            self.live_app_flow_analyzer.terminate()
            self.live_app_flow_analyzer.wait()
        
        # Reset resource dropdown
        self.resource_combo.blockSignals(True)
        self.resource_combo.clear()
        self.resource_combo.addItem("Loading...")
        self.resource_combo.setEnabled(False)
        self.resource_combo.blockSignals(False)
        
        # Start loading resources
        self.load_resources(namespace, workload_type)
    
    def load_resources(self, namespace, workload_type):
        """Load resources based on namespace and workload type"""
        try:
            # Stop any existing resource loader
            if hasattr(self, 'resource_loader') and self.resource_loader.isRunning():
                self.resource_loader.terminate()
                self.resource_loader.wait()
            
            # Start new resource loader
            self.resource_loader = ResourceLoader(namespace, workload_type, self)
            self.resource_loader.resources_loaded.connect(self.on_resources_loaded)
            self.resource_loader.error_occurred.connect(self.on_resource_error)
            self.resource_loader.start()
            
        except Exception as e:
            logging.error(f"Error starting resource loader: {e}")
            self.on_resource_error(f"Error loading resources: {str(e)}")
    
    def on_resources_loaded(self, resources):
        """Handle loaded resources"""
        self.resource_combo.blockSignals(True)
        self.resource_combo.clear()
        
        if resources:
            self.resource_combo.addItems(resources)
            logging.info(f"Loaded {len(resources)} resources for Apps page")
            
            # Auto-select and generate graph if there's only one resource
            if len(resources) == 1:
                self.resource_combo.setCurrentIndex(0)
                self.resource_combo.blockSignals(False)
                self.resource_combo.setEnabled(False)  # Disable dropdown since there's only one option
                
                # Auto-trigger graph generation
                QTimer.singleShot(100, self.on_resource_selected)
                logging.info(f"Auto-selected single resource: {resources[0]}")
            else:
                self.resource_combo.blockSignals(False)
                self.resource_combo.setEnabled(True)
                logging.info(f"Multiple resources found, user selection required")
        else:
            self.resource_combo.addItem("No resources found")
            self.resource_combo.blockSignals(False)
            self.resource_combo.setEnabled(False)
    
    def on_resource_error(self, error_message):
        """Handle resource loading error"""
        self.resource_combo.blockSignals(True)
        self.resource_combo.clear()
        self.resource_combo.addItem("Error loading resources")
        self.resource_combo.blockSignals(False)
        self.resource_combo.setEnabled(False)
        logging.error(f"Failed to load resources for Apps page: {error_message}")
    
    def refresh_page(self):
        """Refresh the page - clear everything and reload namespaces"""
        logging.info("Refreshing Apps page...")
        
        # Stop live monitoring if active
        if self.live_monitoring_enabled:
            self.toggle_live_monitoring()
        
        # Clear the diagram
        self.diagram_scene.clear()
        
        # Reset diagram title
        self.diagram_title.setText("App Diagram")
        
        # Reset status text
        self.status_text.setPlainText("Select a namespace and click Refresh to view apps")
        
        # Reset resource dropdown
        self.resource_combo.blockSignals(True)
        self.resource_combo.clear()
        self.resource_combo.addItem("Select namespace and workload first")
        self.resource_combo.setEnabled(False)
        self.resource_combo.blockSignals(False)
        
        # Disable live monitoring button
        self.live_monitor_btn.setEnabled(False)
        
        # Stop any running analyzers
        if hasattr(self, 'app_flow_analyzer') and self.app_flow_analyzer.isRunning():
            self.app_flow_analyzer.terminate()
            self.app_flow_analyzer.wait()
        
        if hasattr(self, 'live_app_flow_analyzer') and self.live_app_flow_analyzer.isRunning():
            self.live_app_flow_analyzer.terminate()
            self.live_app_flow_analyzer.wait()
        
        if hasattr(self, 'resource_loader') and self.resource_loader.isRunning():
            self.resource_loader.terminate()
            self.resource_loader.wait()
        
        # Reload namespaces
        self.load_namespaces()
    
    def on_resource_selected(self):
        """Handle resource selection change"""
        namespace = self.namespace_combo.currentText()
        workload_type = self.workload_combo.currentText()
        resource_name = self.resource_combo.currentText()
        
        logging.info(f"Resource selected: namespace='{namespace}', workload_type='{workload_type}', resource_name='{resource_name}'")
        
        # Check if we have valid selections
        if (not namespace or namespace == "Loading..." or 
            not workload_type or 
            not resource_name or resource_name in ["Loading...", "Select namespace and workload first", "No resources found", "Error loading resources"]):
            logging.info("Invalid selection, skipping analysis")
            return
        
        # Clear previous diagram
        self.diagram_scene.clear()
        self.status_text.setPlainText("Analyzing app flow...")
        
        # Update diagram title
        display_name = resource_name.split(" (")[0] if "(" in resource_name else resource_name
        self.diagram_title.setText(f"App Flow - {display_name} ({workload_type})")
        
        # Start app flow analysis
        self.start_app_flow_analysis(namespace, workload_type, resource_name)
    
    def start_app_flow_analysis(self, namespace, workload_type, resource_name):
        """Start app flow analysis in background thread"""
        try:
            # Stop any existing analyzer
            if hasattr(self, 'app_flow_analyzer') and self.app_flow_analyzer.isRunning():
                self.app_flow_analyzer.terminate()
                self.app_flow_analyzer.wait()
            
            # Start new analyzer
            self.app_flow_analyzer = AppFlowAnalyzer(namespace, workload_type, resource_name, self)
            self.app_flow_analyzer.analysis_completed.connect(self.on_app_flow_completed)
            self.app_flow_analyzer.error_occurred.connect(self.on_app_flow_error)
            self.app_flow_analyzer.progress_updated.connect(self.on_app_flow_progress)
            self.app_flow_analyzer.start()
            
        except Exception as e:
            logging.error(f"Error starting app flow analyzer: {e}")
            self.on_app_flow_error(f"Error analyzing app flow: {str(e)}")
    
    def on_app_flow_progress(self, message):
        """Handle app flow analysis progress"""
        self.status_text.append(message)
    
    def on_app_flow_completed(self, app_flow):
        """Handle completed app flow analysis"""
        # Store current app flow data for export
        self.current_app_flow_data = app_flow
        
        # Update status
        total_resources = (len(app_flow["ingresses"]) + len(app_flow["services"]) + 
                          len(app_flow["deployments"]) + len(app_flow["pods"]) + 
                          len(app_flow["configmaps"]) + len(app_flow["secrets"]) + len(app_flow["pvcs"]))
        
        self.status_text.append(f"\nApp flow analysis complete!")
        self.status_text.append(f"Found {total_resources} related resources")
        
        # Process app flow data through business logic
        processed_data = self.business_logic.process_app_flow_data(app_flow)
        
        # Create visual app flow diagram with horizontal layout
        self.create_horizontal_app_flow_diagram(processed_data)
    
    def on_app_flow_error(self, error_message):
        """Handle app flow analysis error"""
        self.status_text.append(f"\nError: {error_message}")
        self.diagram_scene.clear()
        self.add_text_to_scene("App flow analysis failed", 10, 10, QColor("#ff4444"))
    
    def toggle_live_monitoring(self):
        """Toggle live monitoring on/off"""
        if self.live_monitoring_enabled:
            # Stop live monitoring
            self.live_monitor_timer.stop()
            self.live_monitoring_enabled = False
            self.live_monitor_btn.setText("▶ Start Live")
            self.live_monitor_btn.setStyleSheet("""
                QPushButton { 
                    background-color: #28a745; 
                    color: #ffffff; 
                    border: 1px solid #34ce57;
                    border-radius: 4px; 
                    padding: 5px 10px; 
                    font-weight: bold;
                }
                QPushButton:hover { 
                    background-color: #34ce57; 
                }
                QPushButton:pressed { 
                    background-color: #1e7e34; 
                }
            """)
            # Remove live indicator from diagram title
            current_title = self.diagram_title.text()
            if "🔴 LIVE - " in current_title:
                self.diagram_title.setText(current_title.replace("🔴 LIVE - ", ""))
            self.status_text.append("Live monitoring stopped")
        else:
            # Start live monitoring
            if hasattr(self, 'current_resources') and self.current_resources:
                self.live_monitor_timer.start()
                self.live_monitoring_enabled = True
                self.live_monitor_btn.setText("⏸ Stop Live")
                self.live_monitor_btn.setStyleSheet("""
                    QPushButton { 
                        background-color: #dc3545; 
                        color: #ffffff; 
                        border: 1px solid #dc3545;
                        border-radius: 4px; 
                        padding: 5px 10px; 
                        font-weight: bold;
                    }
                    QPushButton:hover { 
                        background-color: #c82333; 
                    }
                    QPushButton:pressed { 
                        background-color: #bd2130; 
                    }
                """)
                # Update diagram title to show live monitoring status
                current_title = self.diagram_title.text()
                if "🔴 LIVE" not in current_title:
                    self.diagram_title.setText(f"🔴 LIVE - {current_title}")
                self.status_text.append("Live monitoring started - updating every 5 seconds")
    
    def update_live_monitoring(self):
        """Update the graph with live data"""
        if not self.live_monitoring_enabled or not hasattr(self, 'current_resources'):
            return
            
        try:
            # Get current namespace, workload type, and resource name
            namespace = self.namespace_combo.currentText()
            workload_type = self.workload_combo.currentText()
            resource_name = self.resource_combo.currentText()
            
            if not all([namespace, workload_type, resource_name]) or resource_name in ["Loading...", "Select namespace and workload first", "No resources found", "Error loading resources"]:
                return
            
            # Start background analysis for live update
            self.start_live_app_flow_analysis(namespace, workload_type, resource_name)
            
        except Exception as e:
            logging.error(f"Live monitoring update failed: {e}")
            self.status_text.append(f"Live monitoring error: {str(e)}")
    
    def start_live_app_flow_analysis(self, namespace, workload_type, resource_name):
        """Start app flow analysis for live monitoring (non-blocking)"""
        try:
            # Stop any existing live analyzer
            if hasattr(self, 'live_app_flow_analyzer') and self.live_app_flow_analyzer.isRunning():
                self.live_app_flow_analyzer.terminate()
                self.live_app_flow_analyzer.wait()
            
            # Start new live analyzer
            self.live_app_flow_analyzer = AppFlowAnalyzer(namespace, workload_type, resource_name, self)
            self.live_app_flow_analyzer.analysis_completed.connect(self.on_live_app_flow_completed)
            self.live_app_flow_analyzer.error_occurred.connect(self.on_live_app_flow_error)
            self.live_app_flow_analyzer.start()
            
        except Exception as e:
            logging.error(f"Error starting live app flow analyzer: {e}")
    
    def on_live_app_flow_completed(self, app_flow):
        """Handle completed live app flow analysis - update existing elements"""
        if not self.live_monitoring_enabled:
            return
            
        try:
            # Store updated app flow data
            self.current_app_flow_data = app_flow
            
            # Process app flow data through business logic
            processed_data = self.business_logic.process_app_flow_data(app_flow)
            
            # Update existing graph elements instead of full redraw
            self.update_existing_graph_elements(processed_data)
            
            # Add timestamp to status
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.status_text.append(f"[{timestamp}] Live update completed")
            
        except Exception as e:
            logging.error(f"Live app flow update failed: {e}")
            self.status_text.append(f"Live update error: {str(e)}")
    
    def on_live_app_flow_error(self, error_message):
        """Handle live app flow analysis error"""
        if self.live_monitoring_enabled:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.status_text.append(f"[{timestamp}] Live update error: {error_message}")
    
    def update_existing_graph_elements(self, processed_data):
        """Update existing graph elements with comprehensive live changes"""
        if not hasattr(self, 'current_resource_positions'):
            # No previous graph exists, create fresh diagram
            self.create_horizontal_app_flow_diagram(processed_data)
            return
            
        current_resources = processed_data.get("resources", [])
        
        # Check if significant changes require full redraw
        if self.requires_full_redraw(current_resources):
            self.create_horizontal_app_flow_diagram(processed_data)
            return
        
        # Perform incremental updates for minor changes
        self.perform_incremental_updates(current_resources)
    
    def requires_full_redraw(self, current_resources):
        """Check if changes require full diagram redraw"""
        if not hasattr(self, 'current_resources') or not self.current_resources:
            return True
            
        # Get previous resource identifiers
        previous_resource_ids = {
            (r.resource_type.value, r.name, r.namespace) for r in self.current_resources
        }
        
        # Get current resource identifiers  
        current_resource_ids = {
            (r.resource_type.value, r.name, r.namespace) for r in current_resources
        }
        
        # Check for added or removed resources
        added_resources = current_resource_ids - previous_resource_ids
        removed_resources = previous_resource_ids - current_resource_ids
        
        # Redraw if resources were added or removed
        if added_resources or removed_resources:
            return True
            
        # Check for significant status changes that affect layout
        # (e.g., deployment replica count changes)
        for current_resource in current_resources:
            # Find matching previous resource
            for prev_resource in self.current_resources:
                if (current_resource.resource_type == prev_resource.resource_type and
                    current_resource.name == prev_resource.name and
                    current_resource.namespace == prev_resource.namespace):
                    
                    # Check for replica count changes in deployments/statefulsets
                    if current_resource.resource_type.value.lower() in ['deployment', 'statefulset', 'daemonset']:
                        if getattr(current_resource, 'replicas', 0) != getattr(prev_resource, 'replicas', 0):
                            return True
                    break
        
        return False
    
    def perform_incremental_updates(self, current_resources):
        """Perform incremental updates to existing graph elements"""
        # Update existing resources with status/color changes
        for item in self.diagram_scene.items():
            if hasattr(item, 'data') and item.data(0):
                item_data = item.data(0)
                if isinstance(item_data, dict) and 'resource' in item_data:
                    stored_resource = item_data['resource']
                    
                    # Find matching resource in new data
                    for new_resource in current_resources:
                        if (new_resource.name == stored_resource.name and 
                            new_resource.resource_type == stored_resource.resource_type and
                            new_resource.namespace == stored_resource.namespace):
                            
                            # Update pod colors if status changed
                            if (new_resource.resource_type.value.lower() == 'pod' and 
                                new_resource.status != stored_resource.status):
                                self.update_pod_color(item, new_resource.status)
                                
                            # Update all resource tooltips with latest information
                            if hasattr(item, 'setToolTip'):
                                tooltip_text = self.create_detailed_tooltip(new_resource)
                                item.setToolTip(tooltip_text)
                                
                            # Update stored resource data
                            item_data['resource'] = new_resource
                            item.setData(0, item_data)
                            break
        
        # Update stored current resources for next comparison
        self.current_resources = current_resources
    
    def update_pod_color(self, pod_item, new_status):
        """Update pod circle color based on new status"""
        try:
            # Get new color based on status
            new_color = self.get_pod_status_color(new_status)
            
            # Update the pod circle brush and pen
            if hasattr(pod_item, 'setBrush') and hasattr(pod_item, 'setPen'):
                pod_item.setBrush(QBrush(QColor(new_color)))
                pod_item.setPen(QPen(QColor(new_color).darker(150), 2))
                
                # Update tooltip with new status
                if hasattr(pod_item, 'data') and pod_item.data(0):
                    item_data = pod_item.data(0)
                    if 'resource' in item_data:
                        resource = item_data['resource']
                        resource.status = new_status  # Update status
                        tooltip_text = self.create_detailed_tooltip(resource)
                        pod_item.setToolTip(tooltip_text)
                        
        except Exception as e:
            logging.warning(f"Failed to update pod color: {e}")
    
    def create_diagram_area(self, main_layout):
        """Create the diagram visualization area"""
        # Create diagram container
        diagram_frame = QFrame()
        diagram_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.BG_MEDIUM};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
                margin-top: 10px;
            }}
        """)
        
        diagram_layout = QVBoxLayout(diagram_frame)
        diagram_layout.setContentsMargins(8, 2, 8, 8)
        diagram_layout.setSpacing(2)
        
        # Header with title and export button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Diagram title - minimal height
        self.diagram_title = QLabel("App Diagram")
        self.diagram_title.setMaximumHeight(18)
        self.diagram_title.setMinimumHeight(16)
        self.diagram_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.diagram_title.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.TEXT_LIGHT};
                font-size: 11px;
                font-weight: bold;
                margin: 0px;
                padding: 0px;
                max-height: 16px;
            }}
        """)
        header_layout.addWidget(self.diagram_title)
        
        # Add stretch to push export button to right
        header_layout.addStretch(1)
        
        # Export button with dropdown menu
        self.export_btn = QToolButton()
        self.export_btn.setText("⬇")
        self.export_btn.setToolTip("Export Graph")
        self.export_btn.setStyleSheet("""
            QToolButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #5d5d5d;
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 12px;
                min-width: 20px;
                max-height: 16px;
            }
            QToolButton:hover {
                background-color: #4d4d4d;
            }
            QToolButton:pressed {
                background-color: #2d2d2d;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        
        # Create export menu
        export_menu = QMenu(self.export_btn)
        export_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {AppColors.BG_MEDIUM};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 4px;
                padding: 2px;
            }}
            QMenu::item {{
                background-color: transparent;
                color: {AppColors.TEXT_LIGHT};
                padding: 4px 12px;
                border-radius: 2px;
            }}
            QMenu::item:selected {{
                background-color: {AppColors.BG_LIGHT};
            }}
        """)
        
        # Add export actions
        export_image_action = QAction("📷 Export as Image", self)
        export_image_action.triggered.connect(self.export_as_image_dialog)
        export_menu.addAction(export_image_action)
        
        export_pdf_action = QAction("📄 Export as PDF", self)
        export_pdf_action.triggered.connect(self.export_as_pdf_dialog)
        export_menu.addAction(export_pdf_action)
        
        self.export_btn.setMenu(export_menu)
        self.export_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        header_layout.addWidget(self.export_btn)
        
        diagram_layout.addLayout(header_layout)
        
        # Create enhanced graphics view for diagram
        self.diagram_view = QGraphicsView()
        self.diagram_scene = QGraphicsScene()
        self.diagram_view.setScene(self.diagram_scene)
        
        # Enhanced view settings for better interaction
        self.diagram_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.diagram_view.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.diagram_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.diagram_view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.diagram_view.setInteractive(True)
        
        # Enable mouse wheel zooming
        self.diagram_view.wheelEvent = self.enhanced_wheel_event
        
        self.diagram_view.setStyleSheet(f"""
            QGraphicsView {{
                background-color: {AppColors.BG_DARK};
                border: 1px solid {AppColors.BORDER_LIGHT};
                border-radius: 4px;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        """)
        self.diagram_view.setMinimumHeight(350)
        # Create splitter for diagram and status text
        diagram_splitter = QSplitter(Qt.Orientation.Vertical)
        diagram_splitter.setStyleSheet(f"""
            QSplitter {{
                background-color: {AppColors.BG_MEDIUM};
            }}
            QSplitter::handle {{
                background-color: {AppColors.BORDER_LIGHT};
                height: 3px;
                border-radius: 1px;
                margin: 2px 0px;
            }}
            QSplitter::handle:hover {{
                background-color: {AppColors.ACCENT_BLUE};
            }}
            QSplitter::handle:pressed {{
                background-color: {AppColors.ACCENT_BLUE};
            }}
        """)
        
        # Add diagram view to splitter
        diagram_splitter.addWidget(self.diagram_view)
        
        # Create status text area with resizable container
        status_container = QFrame()
        status_container.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.BG_MEDIUM};
                border: none;
                margin: 0px;
            }}
        """)
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 5, 0, 0)
        status_layout.setSpacing(2)
        
        # Status area header
        status_header = QLabel("Analysis Log")
        status_header.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.TEXT_LIGHT};
                font-size: 10px;
                font-weight: bold;
                margin: 2px 8px;
                padding: 0px;
            }}
        """)
        status_layout.addWidget(status_header)
        
        # Status text area (resizable)
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {AppColors.BG_DARK};
                border: 1px solid {AppColors.BORDER_LIGHT};
                border-radius: 4px;
                color: {AppColors.TEXT_SECONDARY};
                font-size: 12px;
                padding: 8px;
                margin: 0px 2px 2px 2px;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        """)
        self.status_text.setPlainText("Select a namespace and click Refresh to view apps")
        status_layout.addWidget(self.status_text)
        
        # Add status container to splitter
        diagram_splitter.addWidget(status_container)
        
        # Set splitter properties and constraints
        diagram_splitter.setCollapsible(0, False)  # Diagram view cannot be collapsed
        diagram_splitter.setCollapsible(1, False)  # Status text cannot be collapsed
        
        # Set initial sizes: diagram view takes most space, status text gets smaller portion
        diagram_splitter.setSizes([300, 80])  # Initial sizes
        
        # Set size constraints for the status area
        status_container.setMinimumHeight(50)   # Minimum height
        status_container.setMaximumHeight(200)  # Maximum height
        
        # Add splitter to main layout
        diagram_layout.addWidget(diagram_splitter)
        
        main_layout.addWidget(diagram_frame)
    
    
    
    def create_app_flow_diagram(self, app_flow):
        """Create visual representation of the app flow diagram (deprecated - use horizontal layout)"""
        # Redirect to horizontal layout method
        processed_data = self.business_logic.process_app_flow_data(app_flow)
        self.create_horizontal_app_flow_diagram(processed_data)
    
    
    def create_horizontal_app_flow_diagram(self, processed_data):
        """Create horizontal app flow diagram with Kubernetes icons"""
        self.diagram_scene.clear()
        
        resources = processed_data.get("resources", [])
        if not resources:
            self.add_text_to_scene("No resources found in app flow", 10, 10, QColor(AppColors.TEXT_SECONDARY))
            return
        
        # Calculate positions using business logic
        positions = self.business_logic.calculate_horizontal_layout(resources)
        
        # Store positions and resources for live monitoring
        self.current_resource_positions = positions
        self.current_resources = resources
        
        # Draw simple box around pods first
        pod_resources = [r for r in resources if r.resource_type.value.lower() == 'pod']
        if pod_resources:
            self.draw_simple_pod_box(pod_resources, positions)
        
        # Draw resources with K8s icons
        for resource in resources:
            key = f"{resource.resource_type.value}:{resource.name}"
            if key in positions:
                x, y = positions[key]
                self.draw_resource_with_icon(resource, x, y)
        
        # Draw connections
        for connection in processed_data.get("connections", []):
            from_key = connection.from_resource
            to_key = connection.to_resource
            if from_key in positions and to_key in positions:
                from_pos = positions[from_key]
                to_pos = positions[to_key]
                self.draw_horizontal_connection(from_pos, to_pos, connection.connection_type)
        
        # Enable live monitoring button if we have a valid graph
        if resources:
            self.live_monitor_btn.setEnabled(True)
    
    def draw_simple_pod_box(self, pod_resources, positions):
        """Draw a simple box around all pods"""
        if not pod_resources:
            self.pod_container_bounds = None
            return
        
        # Calculate bounding box for all pods
        pod_positions = []
        for pod in pod_resources:
            key = f"{pod.resource_type.value}:{pod.name}"
            if key in positions:
                x, y = positions[key]
                # Account for pod circle (25x25) and text below (about 20px height)
                pod_positions.extend([(x, y), (x + 25, y + 45)])
        
        if not pod_positions:
            self.pod_container_bounds = None
            return
        
        # Calculate box dimensions with small padding (text is now on right)
        min_x = min(pos[0] for pos in pod_positions) - 10   # Small padding on left
        max_x = max(pos[0] for pos in pod_positions) + 120  # Extra space for text on right
        min_y = min(pos[1] for pos in pod_positions) - 25   # More padding above to center with other boxes
        max_y = max(pos[1] for pos in pod_positions) + 25   # More padding below to center with other boxes
        
        box_width = max_x - min_x
        box_height = max_y - min_y
        
        # Store pod container bounds for connection drawing
        self.pod_container_bounds = {
            'min_x': min_x,
            'max_x': max_x,
            'min_y': min_y,
            'max_y': max_y,
            'width': box_width,
            'height': box_height
        }
        
        # Draw simple box border only
        container_box = self.diagram_scene.addRect(
            min_x, min_y, box_width, box_height,
            QPen(QColor("#666666"), 1),  # Simple gray border
            QBrush(Qt.BrushStyle.NoBrush)  # No fill
        )
        container_box.setZValue(-1)  # Put behind everything
    
    def draw_resource_with_icon(self, resource: ResourceInfo, x: float, y: float):
        """Draw resource with icon - pods without box, others with box"""
        icon_info = self.business_logic.get_resource_icon_info(resource.resource_type)
        
        # Check if this is a pod resource
        is_pod = resource.resource_type.value.lower() == 'pod'
        
        if is_pod:
            # Pod: Draw colored circle based on status
            icon_width = 25
            icon_height = 25
            
            # Determine pod color based on status
            pod_color = self.get_pod_status_color(resource.status)
            
            # Create colored circle for pod
            pod_circle = self.diagram_scene.addEllipse(
                x, y, icon_width, icon_height,
                QPen(QColor(pod_color).darker(150), 2), 
                QBrush(QColor(pod_color))
            )
            
            # Enable hover events and tooltip on the circle
            pod_circle.setAcceptHoverEvents(True)
            tooltip_text = self.create_detailed_tooltip(resource)
            pod_circle.setToolTip(tooltip_text)
            icon_item = pod_circle
            
            # Text positioning for pod (icon only)
            width_for_text = icon_width
            height_for_text = icon_height
            
        else:
            # Other resources: Draw with enhanced box
            box_width = 70
            box_height = 70
            
            # Create main box with enhanced gradient effect
            main_rect = self.diagram_scene.addRect(
                x, y, box_width, box_height,
                QPen(QColor(icon_info.color), 3), 
                QBrush(QColor(icon_info.bg_color))
            )
            
            # Add gradient-like effect with multiple layers
            for i in range(3):
                inner_rect = self.diagram_scene.addRect(
                    x + i + 1, y + i + 1, box_width - 2*(i+1), box_height - 2*(i+1),
                    QPen(QColor(icon_info.color).lighter(120 + i*10), 1), 
                    QBrush(Qt.BrushStyle.NoBrush)
                )
            
            # Add subtle shadow effect
            shadow_color = QColor("#000000")
            shadow_color.setAlpha(30)  # Set transparency
            shadow_rect = self.diagram_scene.addRect(
                x + 2, y + 2, box_width, box_height,
                QPen(QColor("#000000"), 1), 
                QBrush(shadow_color)
            )
            shadow_rect.setZValue(-1)  # Put shadow behind main box
            
            # Try to load and display K8s icon centered in the box
            icon_path = self.get_resource_icon_path(resource.resource_type)
            icon_item = None
            if icon_path and os.path.exists(icon_path):
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    # Scale icon to fit nicely in the enhanced box
                    scaled_pixmap = pixmap.scaled(35, 35, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    icon_item = self.diagram_scene.addPixmap(scaled_pixmap)
                    # Center the icon in the box
                    icon_item.setPos(x + (box_width - 35) // 2, y + (box_height - 35) // 2)
            
            # Create interactive group for hover effects
            main_rect.setAcceptHoverEvents(True)
            tooltip_text = self.create_detailed_tooltip(resource)
            main_rect.setToolTip(tooltip_text)
            icon_item = main_rect
            
            # Text positioning for other resources (with box)
            width_for_text = box_width
            height_for_text = box_height
        
        # Resource name positioning - left side for pods, below for others
        name_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        display_name = resource.name[:12] + "..." if len(resource.name) > 12 else resource.name
        name_text = self.diagram_scene.addText(display_name, name_font)
        name_text.setDefaultTextColor(QColor("#ffffff"))
        
        if is_pod:
            # For pods: position text on the right side of the circle
            name_text.setPos(x + width_for_text + 5, y + (height_for_text - name_text.boundingRect().height()) // 2)
        else:
            # For other resources: center text below
            text_width = name_text.boundingRect().width()
            name_text.setPos(x + (width_for_text - text_width) // 2, y + height_for_text + 8)
        
        # For non-pod resources, show additional information
        if not is_pod:
            # Resource type positioned outside and below the name with better styling
            type_font = QFont("Segoe UI", 6, QFont.Weight.Normal)
            type_text = self.diagram_scene.addText(resource.resource_type.value.upper(), type_font)
            type_text.setDefaultTextColor(QColor(icon_info.color).lighter(150))
            # Center type text below the name
            type_text_width = type_text.boundingRect().width()
            type_text.setPos(x + (width_for_text - type_text_width) // 2, y + height_for_text + 25)
            
            # Status positioned outside and below the type with enhanced styling
            status_color = self.get_status_color(resource.status)
            status_font = QFont("Segoe UI", 6, QFont.Weight.Bold)
            status_text = self.diagram_scene.addText(f"● {resource.status}", status_font)
            status_text.setDefaultTextColor(QColor(status_color))
            # Center status text below the type
            status_text_width = status_text.boundingRect().width()
            status_text.setPos(x + (width_for_text - status_text_width) // 2, y + height_for_text + 40)
        
        # Store full resource info for export purposes
        icon_item.setData(0, {
            'resource': resource,
            'full_name': resource.name,
            'export_data': self.create_export_resource_data(resource)
        })
    
    def get_status_color(self, status: str) -> str:
        """Get color based on resource status"""
        status_colors = {
            "Running": "#4CAF50",
            "Ready": "#4CAF50", 
            "Active": "#4CAF50",
            "Bound": "#4CAF50",
            "Pending": "#FF9800",
            "Failed": "#F44336",
            "Error": "#F44336",
            "Unknown": "#9E9E9E"
        }
        
        # Check for fraction status like "2/3"
        if "/" in status:
            parts = status.split("/")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                ready = int(parts[0])
                total = int(parts[1])
                if ready == total:
                    return "#4CAF50"  # All ready
                elif ready > 0:
                    return "#FF9800"  # Partially ready
                else:
                    return "#F44336"  # None ready
        
        return status_colors.get(status, "#9E9E9E")
    
    def get_pod_status_color(self, status: str) -> str:
        """Get color for pod circles - green for running, red for problems"""
        # Green for running/healthy pods
        healthy_statuses = ["Running", "Succeeded", "Ready"]
        
        # Red for problematic pods
        problem_statuses = ["Failed", "Error", "CrashLoopBackOff", "ImagePullBackOff", 
                           "ErrImagePull", "InvalidImageName", "CreateContainerConfigError",
                           "CreateContainerError", "RunContainerError", "KillContainerError",
                           "VerifyNonRootError", "RunInitContainerError", "CreatePodSandboxError",
                           "ConfigPodSandboxError", "KillPodSandboxError", "SetupNetworkError",
                           "TeardownNetworkError"]
        
        # Check if status indicates healthy pod
        if status in healthy_statuses:
            return "#4CAF50"  # Green
        
        # Check if status indicates problematic pod
        if status in problem_statuses:
            return "#F44336"  # Red
        
        # For other statuses like "Pending", "ContainerCreating", etc. use yellow/orange
        return "#FF9800"  # Orange/Yellow for unknown or transitional states
    
    def create_interactive_resource_group(self, main_rect, icon_item, resource: ResourceInfo, x: float, y: float, width: float, height: float):
        """Create interactive group with hover tooltips"""
        from PyQt6.QtWidgets import QGraphicsItemGroup, QGraphicsProxyWidget, QLabel
        
        # Enable hover events on the main rectangle
        main_rect.setAcceptHoverEvents(True)
        
        # Create detailed tooltip content
        tooltip_text = self.create_detailed_tooltip(resource)
        main_rect.setToolTip(tooltip_text)
        
        return main_rect
    
    def create_detailed_tooltip(self, resource: ResourceInfo) -> str:
        """Create detailed tooltip with all resource information"""
        tooltip_lines = [
            f"<b>{resource.name}</b>",
            f"<b>Type:</b> {resource.resource_type.value.title()}",
            f"<b>Namespace:</b> {resource.namespace}",
            f"<b>Status:</b> {resource.status}"
        ]
        
        # Add metadata information if available
        if hasattr(resource, 'metadata') and resource.metadata:
            metadata = resource.metadata
            
            # Add specific information based on resource type
            if resource.resource_type.value == 'deployment':
                if 'replicas' in metadata:
                    tooltip_lines.append(f"<b>Replicas:</b> {metadata.get('ready_replicas', 0)}/{metadata.get('replicas', 1)}")
                if 'containers' in metadata:
                    container_names = [c.get('name', 'unknown') for c in metadata['containers']]
                    tooltip_lines.append(f"<b>Containers:</b> {', '.join(container_names)}")
            
            elif resource.resource_type.value == 'service':
                if 'type' in metadata:
                    tooltip_lines.append(f"<b>Service Type:</b> {metadata['type']}")
                if 'ports' in metadata:
                    ports = [str(p.get('port', '?')) for p in metadata['ports']]
                    tooltip_lines.append(f"<b>Ports:</b> {', '.join(ports)}")
            
            elif resource.resource_type.value == 'pod':
                if 'phase' in metadata:
                    tooltip_lines.append(f"<b>Phase:</b> {metadata['phase']}")
                if 'containers' in metadata:
                    container_names = [c.get('name', 'unknown') for c in metadata['containers']]
                    tooltip_lines.append(f"<b>Containers:</b> {', '.join(container_names)}")
            
            elif resource.resource_type.value == 'ingress':
                if 'host' in metadata:
                    tooltip_lines.append(f"<b>Host:</b> {metadata['host']}")
                if 'path' in metadata:
                    tooltip_lines.append(f"<b>Path:</b> {metadata['path']}")
            
            # Add labels if available
            if 'labels' in metadata and metadata['labels']:
                labels_str = ', '.join([f"{k}={v}" for k, v in list(metadata['labels'].items())[:3]])
                if len(metadata['labels']) > 3:
                    labels_str += "..."
                tooltip_lines.append(f"<b>Labels:</b> {labels_str}")
        
        return "<br>".join(tooltip_lines)
    
    def create_export_resource_data(self, resource: ResourceInfo) -> dict:
        """Create comprehensive resource data for export"""
        export_data = {
            'name': resource.name,  # Full name, not truncated
            'type': resource.resource_type.value,
            'namespace': resource.namespace,
            'status': resource.status
        }
        
        # Add detailed metadata for export
        if hasattr(resource, 'metadata') and resource.metadata:
            export_data['metadata'] = resource.metadata
        
        return export_data
    
    def get_resource_icon_path(self, resource_type: ResourceType) -> str:
        """Get icon path for resource type"""
        icon_mapping = {
            ResourceType.INGRESS: "network.png",
            ResourceType.SERVICE: "network.png", 
            ResourceType.DEPLOYMENT: "workloads.png",
            ResourceType.POD: "workloads.png",
            ResourceType.CONFIGMAP: "config.png",
            ResourceType.SECRET: "config.png",
            ResourceType.PVC: "storage.png"
        }
        
        icon_name = icon_mapping.get(resource_type, "workloads.png")
        return os.path.join("icons", icon_name)
    
    def draw_horizontal_connection(self, from_pos: tuple, to_pos: tuple, connection_type: str):
        """Draw enhanced horizontal connection between resources"""
        from_x, from_y = from_pos
        to_x, to_y = to_pos
        
        # Default dimensions for boxes
        box_width = 70
        box_height = 70
        # Pod dimensions (circle)
        pod_width = 25
        pod_height = 25
        
        # Determine connection points based on resource types
        if connection_type == "deployment_to_pod":
            # From deployment (box) to pod container box - use deployment center Y for straight line
            from_point_x = from_x + box_width   # Right edge of deployment box
            from_point_y = from_y + box_height // 2   # Center of deployment box
            
            # Connect to left edge of pod container box
            if hasattr(self, 'pod_container_bounds') and self.pod_container_bounds:
                to_point_x = self.pod_container_bounds['min_x']  # Left edge of pod container
                # Use deployment center Y for both points to make straight line
                to_point_y = from_point_y
            else:
                to_point_x = to_x   # Fallback to individual pod position
                to_point_y = from_point_y  # Same Y for straight line
                
        elif connection_type in ["pod_to_config", "pod_to_secret", "pod_to_pvc"]:
            # From pod container box to config (box) - use config center Y for straight line
            to_point_x = to_x                   # Left edge of config box
            to_point_y = to_y + box_height // 2 # Center of config box
            
            if hasattr(self, 'pod_container_bounds') and self.pod_container_bounds:
                from_point_x = self.pod_container_bounds['max_x']  # Right edge of pod container
                # Use config center Y for both points to make straight line
                from_point_y = to_point_y
            else:
                from_point_x = from_x + pod_width   # Fallback to individual pod position
                from_point_y = to_point_y  # Same Y for straight line
            
        else:
            # Default: box to box connections
            from_point_x = from_x + box_width   # Right edge of from resource
            from_point_y = from_y + box_height // 2   # Middle of from resource
            to_point_x = to_x                   # Left edge of to resource  
            to_point_y = to_y + box_height // 2 # Middle of to resource
        
        # Color mapping for connection types with improved colors
        color_map = {
            "ingress_to_service": "#E91E63",
            "service_to_deployment": "#28a745", 
            "deployment_to_pod": "#007acc",
            "pod_to_config": "#4CAF50",
            "pod_to_secret": "#FF9800",
            "pod_to_pvc": "#9C27B0"
        }
        
        color = color_map.get(connection_type, "#666666")
        
        # Draw straight line connection
        # Main line
        main_line = self.diagram_scene.addLine(
            from_point_x, from_point_y,
            to_point_x, to_point_y,
            QPen(QColor(color), 3)
        )
        
        # Add subtle shadow line
        shadow_line = self.diagram_scene.addLine(
            from_point_x, from_point_y + 1,
            to_point_x, to_point_y + 1,
            QPen(QColor(color).darker(200), 1)
        )
        
        # Draw enhanced arrow head
        self.draw_enhanced_arrow_head(to_point_x, to_point_y, from_point_x, from_point_y, color)
        
        # Add connection label for better understanding
        mid_x = from_point_x + (to_point_x - from_point_x) / 2
        mid_y = from_point_y + (to_point_y - from_point_y) / 2 - 10
        
        # Connection type label
        connection_label = connection_type.replace("_", " ").replace("to", "→")
        label_font = QFont("Segoe UI", 6, QFont.Weight.Normal)
        label_text = self.diagram_scene.addText(connection_label, label_font)
        label_text.setDefaultTextColor(QColor(color).lighter(150))
        label_text.setPos(mid_x - 20, mid_y)
    
    def draw_enhanced_arrow_head(self, to_x: float, to_y: float, from_x: float, from_y: float, color: str):
        """Draw enhanced arrow head at target point"""
        import math
        
        dx = to_x - from_x
        dy = to_y - from_y
        
        if dx != 0 or dy != 0:
            angle = math.atan2(dy, dx)
            arrow_length = 15
            arrow_angle = math.pi / 5
            
            # Calculate arrow head points
            arrow_x1 = to_x - arrow_length * math.cos(angle - arrow_angle)
            arrow_y1 = to_y - arrow_length * math.sin(angle - arrow_angle)
            arrow_x2 = to_x - arrow_length * math.cos(angle + arrow_angle)
            arrow_y2 = to_y - arrow_length * math.sin(angle + arrow_angle)
            
            # Draw filled arrow head using polygon
            from PyQt6.QtGui import QPolygonF
            from PyQt6.QtCore import QPointF
            
            arrow_polygon = QPolygonF([
                QPointF(to_x, to_y),
                QPointF(arrow_x1, arrow_y1),
                QPointF(arrow_x2, arrow_y2)
            ])
            
            arrow_item = self.diagram_scene.addPolygon(
                arrow_polygon,
                QPen(QColor(color), 1),
                QBrush(QColor(color))
            )
    
    def export_as_image_dialog(self):
        """Show dialog to export graph as image"""
        if not self.current_app_flow_data:
            QMessageBox.warning(self, "Export Error", "No graph data available to export. Please generate a graph first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Graph as Image",
            f"app_flow_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            "PNG Image (*.png);;JPEG Image (*.jpg)"
        )
        
        if file_path:
            try:
                format_type = "JPEG" if file_path.endswith('.jpg') else "PNG"
                self.export_as_image(file_path, format_type)
                QMessageBox.information(self, "Export Success", f"Graph exported successfully to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export graph:\n{str(e)}")
    
    def export_as_pdf_dialog(self):
        """Show dialog to export graph as PDF"""
        if not self.current_app_flow_data:
            QMessageBox.warning(self, "Export Error", "No graph data available to export. Please generate a graph first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Graph as PDF",
            f"app_flow_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            "PDF Document (*.pdf)"
        )
        
        if file_path:
            try:
                self.export_as_pdf(file_path)
                QMessageBox.information(self, "Export Success", f"Graph exported successfully to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export graph:\n{str(e)}")
    
    def export_as_image(self, file_path: str, format_type: str):
        """Export enhanced graph as image with full details (PNG/JPEG)"""
        try:
            # Create enhanced export version with full names
            self.create_export_version_of_graph()
            
            # Get scene bounding rect
            scene_rect = self.diagram_scene.itemsBoundingRect()
            
            # Ensure scene has content
            if scene_rect.isEmpty():
                raise Exception("No content to export")
            
            # Create high-quality pixmap with extra margins
            margin = 60
            pixmap = QPixmap(int(scene_rect.width() + margin*2), int(scene_rect.height() + margin*2))
            pixmap.fill(QColor("#ffffff"))  # Use white background for export
            
            # Render scene to pixmap with enhanced quality
            painter = QPainter()
            if painter.begin(pixmap):
                try:
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                    
                    # Create target rect with margins
                    target_rect = QRectF(margin, margin, scene_rect.width(), scene_rect.height())
                    self.diagram_scene.render(painter, target_rect, scene_rect)
                    
                    # Add export metadata
                    self.add_export_metadata_to_image(painter, pixmap.width(), pixmap.height())
                    
                finally:
                    painter.end()
            else:
                raise Exception("Failed to initialize painter")
            
            # Save high-quality pixmap
            if not pixmap.save(file_path, format_type, 95):  # High quality
                raise Exception(f"Failed to save image as {format_type}")
                
        except Exception as e:
            raise Exception(f"Export failed: {str(e)}")
        finally:
            # Restore original view after export
            self.restore_original_graph()
    
    def export_as_pdf(self, file_path: str):
        """Export graph as PDF"""
        try:
            from PyQt6.QtPrintSupport import QPrinter
            from PyQt6.QtGui import QPageSize, QPageLayout
            
            # Create enhanced export version with full names
            self.create_export_version_of_graph()
            
            # Get scene bounding rect with padding to prevent clipping
            scene_rect = self.diagram_scene.itemsBoundingRect()
            
            # Add padding to ensure all content is visible (especially right side)
            padding = 50
            scene_rect = scene_rect.adjusted(-padding, -padding, padding, padding)
            
            # Ensure scene has content
            if scene_rect.isEmpty():
                raise Exception("No content to export")
            
            # Create printer with PyQt6 API
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_path)
            
            # Use QPageSize and QPageLayout for PyQt6 compatibility
            page_size = QPageSize(QPageSize.PageSizeId.A4)
            
            # Create margins using QMarginsF
            from PyQt6.QtCore import QMarginsF
            margins = QMarginsF(10, 10, 10, 10)  # 10mm margins on all sides
            
            page_layout = QPageLayout(page_size, QPageLayout.Orientation.Landscape, 
                                    margins, QPageLayout.Unit.Millimeter)
            printer.setPageLayout(page_layout)
            
            # Proper painter management for PDF
            painter = QPainter()
            if painter.begin(printer):
                try:
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    
                    # Convert page rect to QRectF for proper rendering
                    page_rect = QRectF(printer.pageRect(QPrinter.Unit.DevicePixel))
                    
                    # Add title heading to PDF
                    painter.setPen(QColor("#000000"))
                    painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
                    deployment_name = self.resource_combo.currentText() if self.resource_combo.currentText() != "Select namespace and workload first" else "Unknown"
                    title = f"Kubernetes App Flow - {deployment_name}"
                    painter.drawText(20, 40, title)
                    
                    # Adjust page rect to account for title space
                    adjusted_page_rect = QRectF(page_rect.x(), page_rect.y() + 60, page_rect.width(), page_rect.height() - 60)
                    
                    # Render the diagram
                    self.diagram_scene.render(painter, adjusted_page_rect, scene_rect)
                    
                    # Add timestamp at bottom
                    painter.setFont(QFont("Segoe UI", 10))
                    timestamp = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    painter.drawText(20, int(page_rect.height() - 20), timestamp)
                    
                finally:
                    painter.end()
            else:
                raise Exception("Failed to initialize PDF painter")
                
        except Exception as e:
            raise Exception(f"PDF export failed: {str(e)}")
        finally:
            # Restore original view after export
            self.restore_original_graph()
    
    def create_export_version_of_graph(self):
        """Create export version with full names and enhanced details"""
        # Store original state
        self.original_scene_items = []
        for item in self.diagram_scene.items():
            if hasattr(item, 'data') and item.data(0):
                self.original_scene_items.append((item, item.data(0)))
        
        # Clear and redraw with full details for export
        if self.current_app_flow_data:
            processed_data = self.business_logic.process_app_flow_data(self.current_app_flow_data)
            self.create_export_horizontal_diagram(processed_data)
    
    def create_export_horizontal_diagram(self, processed_data):
        """Create horizontal diagram optimized for export with full names"""
        self.diagram_scene.clear()
        
        resources = processed_data.get("resources", [])
        if not resources:
            return
        
        # Calculate positions using business logic
        positions = self.business_logic.calculate_horizontal_layout(resources)
        
        # Draw simple box around pods first (same as normal diagram)
        pod_resources = [r for r in resources if r.resource_type.value.lower() == 'pod']
        if pod_resources:
            self.draw_export_pod_box(pod_resources, positions)
        
        # Draw resources with full names for export
        for resource in resources:
            key = f"{resource.resource_type.value}:{resource.name}"
            if key in positions:
                x, y = positions[key]
                self.draw_export_resource_with_icon(resource, x, y)
        
        # Draw connections
        for connection in processed_data.get("connections", []):
            from_key = connection.from_resource
            to_key = connection.to_resource
            if from_key in positions and to_key in positions:
                from_pos = positions[from_key]
                to_pos = positions[to_key]
                self.draw_horizontal_connection(from_pos, to_pos, connection.connection_type)
    
    def draw_export_pod_box(self, pod_resources, positions):
        """Draw pod container box optimized for export with darker border"""
        if not pod_resources:
            return
        
        # Calculate bounding box for all pods
        pod_positions = []
        for pod in pod_resources:
            key = f"{pod.resource_type.value}:{pod.name}"
            if key in positions:
                x, y = positions[key]
                # Account for pod circle (25x25) and status/type text on right (about 80px width)
                pod_positions.extend([(x, y), (x + 25 + 80, y + 25)])  # Include text space on right
        
        if not pod_positions:
            return
        
        # Calculate box dimensions with padding for export visibility
        min_x = min(pos[0] for pos in pod_positions) - 15   # More padding for export
        max_x = max(pos[0] for pos in pod_positions) + 15   # Padding on right
        min_y = min(pos[1] for pos in pod_positions) - 30   # More padding above
        max_y = max(pos[1] for pos in pod_positions) + 30   # More padding below
        
        box_width = max_x - min_x
        box_height = max_y - min_y
        
        # Draw container box with darker border for export visibility
        container_box = self.diagram_scene.addRect(
            min_x, min_y, box_width, box_height,
            QPen(QColor("#333333"), 2),  # Darker, thicker border for export visibility
            QBrush(Qt.BrushStyle.NoBrush)  # No fill
        )
        container_box.setZValue(-1)  # Put behind everything
    
    def draw_export_resource_with_icon(self, resource: ResourceInfo, x: float, y: float):
        """Draw resource for export - pods without box, others with box"""
        icon_info = self.business_logic.get_resource_icon_info(resource.resource_type)
        
        # Check if this is a pod resource
        is_pod = resource.resource_type.value.lower() == 'pod'
        
        if is_pod:
            # Pod: Draw colored circle based on status for export
            icon_width = 25
            icon_height = 25
            
            # Determine pod color based on status
            pod_color = self.get_pod_status_color(resource.status)
            
            # Create colored circle for pod in export
            pod_circle = self.diagram_scene.addEllipse(
                x, y, icon_width, icon_height,
                QPen(QColor(pod_color).darker(150), 2), 
                QBrush(QColor(pod_color))
            )
            
            # Text positioning for pod
            width_for_text = icon_width
            height_for_text = icon_height
            
        else:
            # Other resources: Draw with enhanced box for export
            box_width = 80
            box_height = 80
            
            # Create main box with enhanced gradient effect
            main_rect = self.diagram_scene.addRect(
                x, y, box_width, box_height,
                QPen(QColor(icon_info.color), 3), 
                QBrush(QColor(icon_info.bg_color))
            )
            
            # Add gradient layers
            for i in range(3):
                inner_rect = self.diagram_scene.addRect(
                    x + i + 1, y + i + 1, box_width - 2*(i+1), box_height - 2*(i+1),
                    QPen(QColor(icon_info.color).lighter(120 + i*10), 1), 
                    QBrush(Qt.BrushStyle.NoBrush)
                )
            
            # Add shadow
            shadow_color = QColor("#000000")
            shadow_color.setAlpha(30)
            shadow_rect = self.diagram_scene.addRect(
                x + 2, y + 2, box_width, box_height,
                QPen(QColor("#000000"), 1), 
                QBrush(shadow_color)
            )
            shadow_rect.setZValue(-1)
            
            # Icon in box
            icon_path = self.get_resource_icon_path(resource.resource_type)
            if icon_path and os.path.exists(icon_path):
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    icon_item = self.diagram_scene.addPixmap(scaled_pixmap)
                    icon_item.setPos(x + (box_width - 40) // 2, y + (box_height - 40) // 2)
            
            # Text positioning for other resources
            width_for_text = box_width
            height_for_text = box_height
        
        if is_pod:
            # For pods: show info (status and type) to the right, but NO pod name
            # Pod status
            status_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            status_text = self.diagram_scene.addText(f"● {resource.status}", status_font)
            status_color = self.get_status_color(resource.status)
            status_text.setDefaultTextColor(QColor(status_color))
            status_text.setPos(x + width_for_text + 5, y + (height_for_text - status_text.boundingRect().height()) // 2 - 8)
            
            # Pod type
            type_font = QFont("Segoe UI", 7, QFont.Weight.Normal)
            type_text = self.diagram_scene.addText("POD", type_font)
            type_text.setDefaultTextColor(QColor("#333333"))
            type_text.setPos(x + width_for_text + 5, y + (height_for_text - type_text.boundingRect().height()) // 2 + 8)
            
        else:
            # For non-pod resources: show full information including name
            name_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            name_text = self.diagram_scene.addText(resource.name, name_font)
            name_text.setDefaultTextColor(QColor("#000000"))  # Dark color for PDF visibility
            text_width = name_text.boundingRect().width()
            name_text.setPos(x + (width_for_text - text_width) // 2, y + height_for_text + 10)
            # Resource type with better font - Use darker color for PDF visibility
            type_font = QFont("Segoe UI", 7, QFont.Weight.Normal)
            type_text = self.diagram_scene.addText(resource.resource_type.value.upper(), type_font)
            type_text.setDefaultTextColor(QColor("#333333"))  # Changed to dark gray for PDF visibility
            type_text_width = type_text.boundingRect().width()
            type_text.setPos(x + (width_for_text - type_text_width) // 2, y + height_for_text + 28)
            
            # Enhanced status display
            status_color = self.get_status_color(resource.status)
            status_font = QFont("Segoe UI", 7, QFont.Weight.Bold)
            status_text = self.diagram_scene.addText(f"● {resource.status}", status_font)
            status_text.setDefaultTextColor(QColor(status_color))
            status_text_width = status_text.boundingRect().width()
            status_text.setPos(x + (width_for_text - status_text_width) // 2, y + height_for_text + 45)
            
            # Add namespace for clarity in export
            if resource.namespace and resource.namespace != 'default':
                ns_font = QFont("Segoe UI", 6, QFont.Weight.Normal)
                ns_text = self.diagram_scene.addText(f"ns: {resource.namespace}", ns_font)
                ns_text.setDefaultTextColor(QColor("#555555"))  # Changed to darker gray for PDF visibility
                ns_text_width = ns_text.boundingRect().width()
                ns_text.setPos(x + (width_for_text - ns_text_width) // 2, y + height_for_text + 60)
    
    def add_export_metadata_to_image(self, painter: QPainter, width: int, height: int):
        """Add metadata information to exported image"""
        # Add title and timestamp - Use dark color for PDF visibility
        painter.setPen(QColor("#000000"))  # Changed to black for PDF visibility
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        
        # Use deployment name instead of namespace in title
        deployment_name = self.resource_combo.currentText() if self.resource_combo.currentText() != "Select namespace and workload first" else "Unknown"
        title = f"Kubernetes App Flow - {deployment_name}"
        painter.drawText(20, 30, title)
        
        # Add timestamp
        painter.setFont(QFont("Segoe UI", 8))
        timestamp = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        painter.drawText(20, height - 20, timestamp)
        
        # Add resource count
        if self.current_app_flow_data:
            total_resources = (len(self.current_app_flow_data.get("ingresses", [])) + 
                             len(self.current_app_flow_data.get("services", [])) + 
                             len(self.current_app_flow_data.get("deployments", [])) + 
                             len(self.current_app_flow_data.get("pods", [])) + 
                             len(self.current_app_flow_data.get("configmaps", [])) + 
                             len(self.current_app_flow_data.get("secrets", [])) + 
                             len(self.current_app_flow_data.get("pvcs", [])))
            
            resource_info = f"Total Resources: {total_resources}"
            painter.drawText(width - 200, height - 20, resource_info)
    
    def restore_original_graph(self):
        """Restore the original graph after export"""
        if self.current_app_flow_data:
            processed_data = self.business_logic.process_app_flow_data(self.current_app_flow_data)
            self.create_horizontal_app_flow_diagram(processed_data)

    def enhanced_wheel_event(self, event):
        """Enhanced wheel event for smooth zooming"""
        try:
            # Check if Ctrl is pressed for zooming
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Zoom in/out
                zoom_in_factor = 1.25
                zoom_out_factor = 1 / zoom_in_factor
                
                # Save the scene pos
                old_pos = self.diagram_view.mapToScene(event.position().toPoint())
                
                # Zoom
                if event.angleDelta().y() > 0:
                    zoom_factor = zoom_in_factor
                else:
                    zoom_factor = zoom_out_factor
                
                self.diagram_view.scale(zoom_factor, zoom_factor)
                
                # Get the new position
                new_pos = self.diagram_view.mapToScene(event.position().toPoint())
                
                # Move scene to old position
                delta = new_pos - old_pos
                self.diagram_view.translate(delta.x(), delta.y())
                
                event.accept()
            else:
                # Default scroll behavior
                super(QGraphicsView, self.diagram_view).wheelEvent(event)
        except Exception as e:
            logging.warning(f"Wheel event error: {e}")
            super(QGraphicsView, self.diagram_view).wheelEvent(event)
    
    def add_text_to_scene(self, text, x, y, color):
        """Add text to the scene"""
        text_item = self.diagram_scene.addText(text, QFont("Arial", 12))
        text_item.setDefaultTextColor(color)
        text_item.setPos(x, y)