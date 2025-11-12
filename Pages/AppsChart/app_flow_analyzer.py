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
        """Analyze flow for deployment-like workloads - Enhanced to find ALL related resources"""
        self.progress_updated.emit("Finding related services...")
        
        # Add the workload itself
        workload_info = self._extract_workload_info(workload)
        app_flow["deployments"].append(workload_info)
        
        # Find ALL services that target this workload
        services = self._find_related_services(workload)
        app_flow["services"].extend(services)
        
        # Find ALL ingresses in the namespace (not just those targeting discovered services)
        self.progress_updated.emit("Finding related ingresses...")
        all_ingresses = self._find_all_related_ingresses(services)
        app_flow["ingresses"].extend(all_ingresses)
        
        # Find ALL pods created by this workload
        self.progress_updated.emit("Finding related pods...")
        pods = self._find_related_pods(workload)
        app_flow["pods"].extend(pods)
        
        # Find ONLY config resources actually used by the workload
        self.progress_updated.emit("Finding configuration resources...")
        workload_configs = self._find_related_configs(workload)
        app_flow["configmaps"].extend(workload_configs.get("configmaps", []))
        app_flow["secrets"].extend(workload_configs.get("secrets", []))
        app_flow["pvcs"].extend(workload_configs.get("pvcs", []))
        logging.info(f"Found workload-specific configs: {len(workload_configs.get('configmaps', []))} ConfigMaps, {len(workload_configs.get('secrets', []))} Secrets, {len(workload_configs.get('pvcs', []))} PVCs")
        
        # Create comprehensive connections showing all relationships
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
        """Find ONLY services that actually target this workload's pods"""
        services = []
        try:
            svc_list = self.kube_client.v1.list_namespaced_service(namespace=self.namespace)
            workload_labels = workload.spec.selector.match_labels if hasattr(workload.spec, 'selector') else {}
            
            for service in svc_list.items:
                # Skip system services
                if service.metadata.name in ['kubernetes']:
                    continue
                
                service_selector = service.spec.selector or {}
                
                # Only include services that select this workload's pods
                if self._selectors_match_workload(service_selector, workload_labels):
                    service_info = {
                        "name": service.metadata.name,
                        "namespace": service.metadata.namespace,
                        "type": service.spec.type,
                        "cluster_ip": service.spec.cluster_ip,
                        "selector": service_selector,
                        "ports": [{
                            "port": p.port,
                            "target_port": p.target_port,
                            "protocol": p.protocol
                        } for p in (service.spec.ports or [])]
                    }
                    
                    services.append(service_info)
                    logging.info(f"Found related service: {service.metadata.name} (selector: {service_selector})")
                
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
    
    def _find_all_related_ingresses(self, services):
        """Find ALL ingresses in the namespace, not just those targeting discovered services"""
        ingresses = []
        try:
            ing_list = self.kube_client.networking_v1.list_namespaced_ingress(namespace=self.namespace)
            
            for ingress in ing_list.items:
                # Add all ingresses in the namespace to get comprehensive view
                ingress_info = {
                    "name": ingress.metadata.name,
                    "namespace": ingress.metadata.namespace,
                    "hosts": [],
                    "services": []
                }
                
                if ingress.spec.rules:
                    for rule in ingress.spec.rules:
                        if rule.host:
                            ingress_info["hosts"].append(rule.host)
                        
                        if rule.http and rule.http.paths:
                            for path in rule.http.paths:
                                if path.backend.service:
                                    service_info = {
                                        "name": path.backend.service.name,
                                        "path": path.path,
                                        "port": path.backend.service.port.number if path.backend.service.port else "N/A"
                                    }
                                    ingress_info["services"].append(service_info)
                                    # Set primary service for connections
                                    if not ingress_info.get("service"):
                                        ingress_info["service"] = path.backend.service.name
                
                # Set default values
                ingress_info["host"] = ingress_info["hosts"][0] if ingress_info["hosts"] else "N/A"
                ingress_info["path"] = "/"
                
                ingresses.append(ingress_info)
                
        except Exception as e:
            logging.warning(f"Could not fetch all ingresses: {e}")
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
    
    def _find_all_related_configs(self, workload, pods):
        """Find ALL config resources that could be used by workload and pods - Enhanced Discovery"""
        configs = {"configmaps": [], "secrets": [], "pvcs": []}
        
        try:
            # Get ALL configmaps in the namespace
            self.progress_updated.emit("Scanning all configmaps...")
            try:
                cm_list = self.kube_client.v1.list_namespaced_config_map(namespace=self.namespace)
                for cm in cm_list.items:
                    configs["configmaps"].append({
                        "name": cm.metadata.name,
                        "namespace": cm.metadata.namespace,
                        "type": "configmap",
                        "data_keys": list(cm.data.keys()) if cm.data else []
                    })
            except Exception as e:
                logging.warning(f"Could not fetch configmaps: {e}")
            
            # Get ALL secrets in the namespace (excluding system secrets)
            self.progress_updated.emit("Scanning all secrets...")
            try:
                secret_list = self.kube_client.v1.list_namespaced_secret(namespace=self.namespace)
                for secret in secret_list.items:
                    # Filter out system secrets
                    if not secret.metadata.name.startswith(('default-token-', 'kube-root-ca')):
                        configs["secrets"].append({
                            "name": secret.metadata.name,
                            "namespace": secret.metadata.namespace,
                            "type": "secret",
                            "secret_type": secret.type
                        })
            except Exception as e:
                logging.warning(f"Could not fetch secrets: {e}")
            
            # Get ALL PVCs in the namespace
            self.progress_updated.emit("Scanning all PVCs...")
            try:
                pvc_list = self.kube_client.v1.list_namespaced_persistent_volume_claim(namespace=self.namespace)
                for pvc in pvc_list.items:
                    configs["pvcs"].append({
                        "name": pvc.metadata.name,
                        "namespace": pvc.metadata.namespace,
                        "type": "pvc",
                        "status": pvc.status.phase if pvc.status else "Unknown"
                    })
            except Exception as e:
                logging.warning(f"Could not fetch PVCs: {e}")
            
            # Also include the original workload-specific configs for accurate connections
            original_configs = self._find_related_configs(workload)
            
            # Merge without duplicates
            for config_type in ["configmaps", "secrets", "pvcs"]:
                existing_names = {c["name"] for c in configs[config_type]}
                for config in original_configs.get(config_type, []):
                    if config["name"] not in existing_names:
                        configs[config_type].append(config)
                        
        except Exception as e:
            logging.warning(f"Could not analyze all configs: {e}")
        
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
    
    def _names_suggest_relationship(self, name1, name2):
        """Check if two resource names suggest they're related"""
        # Remove common prefixes/suffixes and compare
        import re
        
        # Extract base names by removing common patterns
        base1 = re.sub(r'(-service|-svc|-controller|-deployment|-deploy)$', '', name1)
        base2 = re.sub(r'(-service|-svc|-controller|-deployment|-deploy)$', '', name2)
        
        # Check if base names match or one contains the other
        if base1 == base2:
            return True
        if base1 in base2 or base2 in base1:
            return True
        
        # Check if they share a significant common prefix (more than 3 chars)
        common_prefix = ""
        for i in range(min(len(base1), len(base2))):
            if base1[i] == base2[i]:
                common_prefix += base1[i]
            else:
                break
        
        return len(common_prefix) >= 4
    
    def _selectors_match_workload(self, service_selector, workload_labels):
        """Check if service selector matches workload labels"""
        if not service_selector:
            return False
        
        # Check if all service selector criteria are met by workload labels
        for key, value in service_selector.items():
            if workload_labels.get(key) != value:
                return False
        return True
    
    def _create_connections(self, app_flow):
        """Create optimized connection information for readable graph - Smart Connection Management"""
        connections = []
        
        # Debug logging
        logging.info(f"Creating connections for app flow with: {len(app_flow.get('ingresses', []))} ingresses, {len(app_flow.get('services', []))} services, {len(app_flow.get('deployments', []))} deployments, {len(app_flow.get('pods', []))} pods")
        
        # Ingress -> Service connections (all ingresses to their services)
        for ingress in app_flow["ingresses"]:
            service_name = ingress.get('service')
            if service_name:
                connection = {
                    "from": f"ingress:{ingress['name']}",
                    "to": f"service:{service_name}",
                    "type": "ingress_to_service"
                }
                connections.append(connection)
                logging.info(f"Added ingress->service connection: {connection}")
        
        # Service -> Deployment connections (improved matching to show all logical connections)
        for service in app_flow["services"]:
            for deployment in app_flow["deployments"]:
                service_selector = service.get('selector', {})
                deployment_labels = deployment.get('labels', {})
                
                # More flexible matching - check for any overlap or if they're related to the same workload
                should_connect = False
                
                # Check if selectors match
                if self._selectors_match(service_selector, deployment_labels):
                    should_connect = True
                
                # Also connect if names are similar (same workload pattern)
                elif self._names_suggest_relationship(service['name'], deployment['name']):
                    should_connect = True
                    
                # Connect ALL services to deployment if there's only one deployment (common in single-app flows)
                elif len(app_flow["deployments"]) == 1:
                    should_connect = True
                
                if should_connect:
                    connection = {
                        "from": f"service:{service['name']}",
                        "to": f"deployment:{deployment['name']}",
                        "type": "service_to_deployment"
                    }
                    connections.append(connection)
                    logging.info(f"Added service->deployment connection: {connection}")
        
        # Deployment -> Pod connections (smart grouping to reduce clutter)
        deployment_to_pod_connections = self._create_smart_deployment_pod_connections(app_flow["deployments"], app_flow["pods"])
        connections.extend(deployment_to_pod_connections)
        
        # Pod -> Config connections (optimized to show representative connections)
        pod_config_connections = self._create_smart_pod_config_connections(app_flow["pods"], app_flow["configmaps"], app_flow["secrets"], app_flow["pvcs"])
        connections.extend(pod_config_connections)
        
        app_flow["connections"] = connections
        logging.info(f"Created {len(connections)} optimized connections for better readability")
    
    def _create_smart_deployment_pod_connections(self, deployments, pods):
        """Create smart deployment-to-pod connections to reduce visual clutter"""
        connections = []
        
        for deployment in deployments:
            deployment_selector = deployment.get('selector', {})
            related_pods = []
            
            # Find all pods related to this deployment
            for pod in pods:
                pod_labels = pod.get('labels', {})
                if self._selectors_match(deployment_selector, pod_labels):
                    related_pods.append(pod)
            
            # Smart connection strategy based on number of pods
            if len(related_pods) == 0:
                continue
            elif len(related_pods) <= 3:
                # Show all connections for small numbers
                for pod in related_pods:
                    connections.append({
                        "from": f"deployment:{deployment['name']}",
                        "to": f"pod:{pod['name']}",
                        "type": "deployment_to_pod"
                    })
            else:
                # For many pods, show connection to first few pods to indicate relationship
                # without overwhelming the diagram
                for pod in related_pods[:2]:  # Show only first 2 pods as representatives
                    connections.append({
                        "from": f"deployment:{deployment['name']}",
                        "to": f"pod:{pod['name']}",
                        "type": "deployment_to_pod"
                    })
        
        return connections
    
    def _create_smart_pod_config_connections(self, pods, configmaps, secrets, pvcs):
        """Create smart pod-to-config connections showing logical relationships"""
        connections = []
        
        # Strategy: Show actual logical connections but limit to prevent overcrowding
        # Prioritize showing different types of relationships
        
        # Show connections from first pod to demonstrate relationships
        if pods:
            pod = pods[0]  # Use first pod for connections
            
            # Debug logging to see counts
            logging.info(f"Pod-to-config connections: {len(configmaps)} ConfigMaps, {len(secrets)} Secrets, {len(pvcs)} PVCs")
            
            # Connect to ALL ConfigMaps for comprehensive view (up to 20)
            if configmaps:
                for configmap in configmaps[:20]:  # Show up to 20 configmaps for comprehensive view
                    connections.append({
                        "from": f"pod:{pod['name']}",
                        "to": f"configmap:{configmap['name']}",
                        "type": "pod_to_config"
                    })
            
            # Connect to ALL Secrets for comprehensive view (up to 20)
            if secrets:
                for secret in secrets[:20]:  # Show up to 20 secrets for comprehensive view
                    connections.append({
                        "from": f"pod:{pod['name']}",
                        "to": f"secret:{secret['name']}",
                        "type": "pod_to_secret"
                    })
            
            # Connect to ALL PVCs for comprehensive view (up to 10)
            if pvcs:
                for pvc in pvcs[:10]:  # Show up to 10 PVCs for comprehensive view
                    connections.append({
                        "from": f"pod:{pod['name']}",
                        "to": f"pvc:{pvc['name']}",
                        "type": "pod_to_pvc"
                    })
        
        return connections
    
    def _pod_uses_config(self, pod, config_resource, config_type):
        """Check if a pod actually uses a specific config resource - Enhanced Logic"""
        config_name = config_resource.get("name", "")
        
        # For comprehensive view: show potential relationships based on namespace coexistence
        # This gives users visibility into all available resources they could connect
        
        # Actual usage checking could be implemented by:
        # 1. Checking pod.spec.volumes for configMap/secret references
        # 2. Checking pod.spec.containers[].env for configMapKeyRef/secretKeyRef
        # 3. Checking pod.spec.containers[].envFrom for configMapRef/secretRef
        
        # For now, show all configs to give comprehensive application view
        # but exclude obvious system configs
        if config_type == "secret" and config_name.startswith(('default-token-', 'kube-root-ca')):
            return False
        
        # Show all other resources for comprehensive view
        return True