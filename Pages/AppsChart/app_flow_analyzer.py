"""
AppFlowAnalyzer - Thread for analyzing Kubernetes application flows and creating comprehensive graphs.

This module contains the AppFlowAnalyzer class which analyzes Kubernetes workloads and their
relationships to create comprehensive application flow diagrams. It supports various workload
types including deployments, statefulsets, daemonsets, pods, jobs, and cronjobs.

The analyzer discovers and maps relationships between:
- Workloads (deployments, statefulsets, etc.)
- Services that target the workloads
- Ingresses that route to the services
- Pods created by the workloads
- ConfigMaps, Secrets, and PVCs used by the workloads
- Connection flows between all these resources
"""

from PyQt6.QtCore import QThread, pyqtSignal
from Utils.kubernetes_client import get_kubernetes_client
from kubernetes.client.rest import ApiException
import logging


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
        if namespace == "All Namespaces":
            if "(" in self.resource_name and ")" in self.resource_name:
                # Extract namespace from resource name format: "resource-name (namespace)"
                parts = self.resource_name.split(" (")
                self.resource_name = parts[0]
                self.namespace = parts[1].rstrip(")")
            else:
                # For "All Namespaces" without namespace suffix, we need to find the actual namespace
                # This is an error case - we cannot proceed without knowing the specific namespace
                self.namespace = None
                self.resource_name = self.resource_name
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
            
            # If namespace is None (All Namespaces without suffix), find the actual namespace
            if self.namespace is None:
                self.progress_updated.emit(f"Finding namespace for {self.resource_name}...")
                actual_namespace = self._find_resource_namespace()
                if not actual_namespace:
                    self.error_occurred.emit(f"Could not find {self.workload_type} '{self.resource_name}' in any namespace")
                    return
                self.namespace = actual_namespace
                logging.info(f"Found {self.resource_name} in namespace: {self.namespace}")
                
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
    
    def _find_resource_namespace(self):
        """Find the namespace where the resource exists when 'All Namespaces' is selected"""
        try:
            if self.workload_type == "deployments":
                resources = self.kube_client.apps_v1.list_deployment_for_all_namespaces()
            elif self.workload_type == "statefulsets":
                resources = self.kube_client.apps_v1.list_stateful_set_for_all_namespaces()
            elif self.workload_type == "daemonsets":
                resources = self.kube_client.apps_v1.list_daemon_set_for_all_namespaces()
            elif self.workload_type == "pods":
                resources = self.kube_client.v1.list_pod_for_all_namespaces()
            elif self.workload_type == "replicasets":
                resources = self.kube_client.apps_v1.list_replica_set_for_all_namespaces()
            elif self.workload_type == "jobs":
                resources = self.kube_client.batch_v1.list_job_for_all_namespaces()
            elif self.workload_type == "cronjobs":
                resources = self.kube_client.batch_v1.list_cron_job_for_all_namespaces()
            elif self.workload_type == "replicationcontrollers":
                resources = self.kube_client.v1.list_replication_controller_for_all_namespaces()
            else:
                logging.error(f"Unsupported workload type for namespace search: {self.workload_type}")
                return None
            
            # Search for the resource by name
            for resource in resources.items:
                if resource.metadata.name == self.resource_name:
                    return resource.metadata.namespace
            
            return None
            
        except ApiException as e:
            logging.error(f"API error finding namespace for {self.resource_name}: {e.reason}")
            return None
        except Exception as e:
            logging.error(f"Failed to find namespace for {self.resource_name}: {e}")
            return None
    
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