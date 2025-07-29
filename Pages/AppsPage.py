"""
Simple Apps page with namespace dropdown and basic key-value inputs.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, 
    QPushButton, QFrame, QSizePolicy, QTextEdit, QScrollArea, QGraphicsView,
    QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
    QMessageBox, QProgressDialog, QGraphicsPixmapItem, QFileDialog, QMenu, QToolButton
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
        
        # Deployment -> Pod connections
        for deployment in app_flow["deployments"]:
            for pod in app_flow["pods"]:
                connections.append({
                    "from": f"deployment:{deployment['name']}",
                    "to": f"pod:{pod['name']}",
                    "type": "deployment_to_pod"
                })
        
        # Pod -> Config connections
        for pod in app_flow["pods"]:
            for config in app_flow["configmaps"]:
                connections.append({
                    "from": f"pod:{pod['name']}",
                    "to": f"configmap:{config['name']}",
                    "type": "pod_to_config"
                })
            for secret in app_flow["secrets"]:
                connections.append({
                    "from": f"pod:{pod['name']}",
                    "to": f"secret:{secret['name']}",
                    "type": "pod_to_secret"
                })
            for pvc in app_flow["pvcs"]:
                connections.append({
                    "from": f"pod:{pod['name']}",
                    "to": f"pvc:{pvc['name']}",
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
        self.setup_ui()
        
        # Set horizontal layout by default
        self.business_logic.set_graph_layout(GraphLayout.HORIZONTAL)
        
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
        
        # Clear the diagram when selection changes
        self.diagram_scene.clear()
        
        # Reset diagram title
        self.diagram_title.setText("App Diagram")
        
        # Reset status text
        self.status_text.setPlainText("Loading resources...")
        
        # Stop any running analyzer
        if hasattr(self, 'app_flow_analyzer') and self.app_flow_analyzer.isRunning():
            self.app_flow_analyzer.terminate()
            self.app_flow_analyzer.wait()
        
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
        
        # Stop any running analyzers
        if hasattr(self, 'app_flow_analyzer') and self.app_flow_analyzer.isRunning():
            self.app_flow_analyzer.terminate()
            self.app_flow_analyzer.wait()
        
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
        
        # Create graphics view for diagram
        self.diagram_view = QGraphicsView()
        self.diagram_scene = QGraphicsScene()
        self.diagram_view.setScene(self.diagram_scene)
        self.diagram_view.setStyleSheet(f"""
            QGraphicsView {{
                background-color: {AppColors.BG_DARK};
                border: 1px solid {AppColors.BORDER_LIGHT};
                border-radius: 4px;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        """)
        self.diagram_view.setMinimumHeight(350)
        diagram_layout.addWidget(self.diagram_view)
        
        # Status text area
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(50)
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {AppColors.BG_DARK};
                border: 1px solid {AppColors.BORDER_LIGHT};
                border-radius: 4px;
                color: {AppColors.TEXT_SECONDARY};
                font-size: 12px;
                padding: 8px;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        """)
        self.status_text.setPlainText("Select a namespace and click Refresh to view apps")
        diagram_layout.addWidget(self.status_text)
        
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
    
    def draw_resource_with_icon(self, resource: ResourceInfo, x: float, y: float):
        """Draw enhanced resource box with Kubernetes icon and visual improvements"""
        icon_info = self.business_logic.get_resource_icon_info(resource.resource_type)
        
        # Resource box dimensions
        box_width = 200
        box_height = 90
        corner_radius = 8
        
        # Create main box with rounded corners and gradient effect
        main_rect = self.diagram_scene.addRect(
            x, y, box_width, box_height,
            QPen(QColor(icon_info.color), 2), 
            QBrush(QColor(icon_info.bg_color))
        )
        
        # Add subtle inner border for depth
        inner_rect = self.diagram_scene.addRect(
            x + 2, y + 2, box_width - 4, box_height - 4,
            QPen(QColor(icon_info.color).lighter(120), 1), 
            QBrush(Qt.BrushStyle.NoBrush)
        )
        
        # Header section with darker background
        header_rect = self.diagram_scene.addRect(
            x, y, box_width, 25,
            QPen(QColor(icon_info.color)), 
            QBrush(QColor(icon_info.color).darker(150))
        )
        
        # Try to load and display K8s icon with better positioning
        icon_path = self.get_resource_icon_path(resource.resource_type)
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                # Scale icon to fit with better quality
                scaled_pixmap = pixmap.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon_item = self.diagram_scene.addPixmap(scaled_pixmap)
                icon_item.setPos(x + 6, y + 3)
        
        # Resource name with better font
        name_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        name_text = self.diagram_scene.addText(resource.name[:20] + "..." if len(resource.name) > 20 else resource.name, name_font)
        name_text.setDefaultTextColor(QColor("#ffffff"))
        name_text.setPos(x + 32, y + 4)
        
        # Resource type badge
        type_font = QFont("Segoe UI", 7, QFont.Weight.Normal)
        type_text = self.diagram_scene.addText(resource.resource_type.value.upper(), type_font)
        type_text.setDefaultTextColor(QColor("#e0e0e0"))
        type_text.setPos(x + 8, y + 32)
        
        # Status with color coding
        status_color = self.get_status_color(resource.status)
        status_font = QFont("Segoe UI", 7, QFont.Weight.Bold)
        status_text = self.diagram_scene.addText(f"● {resource.status}", status_font)
        status_text.setDefaultTextColor(QColor(status_color))
        status_text.setPos(x + 8, y + 50)
        
        # Additional metadata if available
        if hasattr(resource, 'metadata') and resource.metadata:
            namespace = resource.metadata.get('namespace', resource.namespace)
            if namespace and namespace != 'default':
                ns_font = QFont("Segoe UI", 6, QFont.Weight.Normal)
                ns_text = self.diagram_scene.addText(f"ns: {namespace}", ns_font)
                ns_text.setDefaultTextColor(QColor("#999999"))
                ns_text.setPos(x + 8, y + 68)
    
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
        
        # Calculate connection points with better positioning
        from_point_x = from_x + 200  # Right edge of from box
        from_point_y = from_y + 45   # Middle of from box (adjusted for new height)
        to_point_x = to_x            # Left edge of to box  
        to_point_y = to_y + 45       # Middle of to box (adjusted for new height)
        
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
        
        # Draw connection with curved line for better visuals
        if abs(from_point_y - to_point_y) < 10:  # Same level - straight line
            # Main line with gradient effect
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
        else:
            # Curved connection for different levels
            control_x = from_point_x + (to_point_x - from_point_x) / 2
            
            # Draw bezier-like curve using multiple line segments
            segments = 20
            for i in range(segments):
                t1 = i / segments
                t2 = (i + 1) / segments
                
                # Simple bezier curve calculation
                x1 = from_point_x + t1 * (control_x - from_point_x) + t1 * t1 * (to_point_x - control_x)
                y1 = from_point_y + t1 * (to_point_y - from_point_y)
                x2 = from_point_x + t2 * (control_x - from_point_x) + t2 * t2 * (to_point_x - control_x)
                y2 = from_point_y + t2 * (to_point_y - from_point_y)
                
                segment = self.diagram_scene.addLine(x1, y1, x2, y2, QPen(QColor(color), 2))
        
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
        """Export graph as image (PNG/JPEG)"""
        try:
            # Get scene bounding rect
            scene_rect = self.diagram_scene.itemsBoundingRect()
            
            # Ensure scene has content
            if scene_rect.isEmpty():
                raise Exception("No content to export")
            
            # Create pixmap with scene size
            pixmap = QPixmap(int(scene_rect.width() + 40), int(scene_rect.height() + 40))
            pixmap.fill(QColor(AppColors.BG_DARK))
            
            # Render scene to pixmap with proper painter management
            painter = QPainter()
            if painter.begin(pixmap):
                try:
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    # Convert QRect to QRectF for proper rendering
                    target_rect = QRectF(pixmap.rect())
                    self.diagram_scene.render(painter, target_rect, scene_rect)
                finally:
                    painter.end()
            else:
                raise Exception("Failed to initialize painter")
            
            # Save pixmap
            if not pixmap.save(file_path, format_type):
                raise Exception(f"Failed to save image as {format_type}")
                
        except Exception as e:
            raise Exception(f"Export failed: {str(e)}")
    
    def export_as_pdf(self, file_path: str):
        """Export graph as PDF"""
        try:
            from PyQt6.QtPrintSupport import QPrinter
            from PyQt6.QtGui import QPageSize, QPageLayout
            
            # Get scene bounding rect
            scene_rect = self.diagram_scene.itemsBoundingRect()
            
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
                    self.diagram_scene.render(painter, page_rect, scene_rect)
                finally:
                    painter.end()
            else:
                raise Exception("Failed to initialize PDF painter")
                
        except Exception as e:
            raise Exception(f"PDF export failed: {str(e)}")

    def add_text_to_scene(self, text, x, y, color):
        """Add text to the scene"""
        text_item = self.diagram_scene.addText(text, QFont("Arial", 12))
        text_item.setDefaultTextColor(color)
        text_item.setPos(x, y)