"""
Kubernetes Resource Loader - Optimized resource loading with incremental support
Split from base_resource_page.py for better architecture
"""

import logging
from kubernetes import client
from utils.enhanced_worker import EnhancedBaseWorker
from utils.kubernetes_client import get_kubernetes_client


class KubernetesResourceLoader(EnhancedBaseWorker):
    """Optimized resource loader with incremental loading support"""
    
    def __init__(self, resource_type, namespace=None, limit=None, continue_token=None):
        super().__init__(f"resource_load_{resource_type}_{namespace or 'all'}")
        self.resource_type = resource_type
        self.namespace = namespace
        self.limit = limit or 500  # Even higher default limit for faster loading
        self.continue_token = continue_token
        self.kube_client = get_kubernetes_client()
        self._timeout = 15  # Balanced timeout

    def execute(self):
        if self.is_cancelled():
            return ([], self.resource_type, "")
        
        try:
            # Use optimized loading method
            resources, next_token = self._load_resources()
            
            if self.is_cancelled():
                return ([], self.resource_type, "")
            
            return (resources, self.resource_type, next_token or "")
            
        except Exception as e:
            if self.is_cancelled():
                return ([], self.resource_type, "")
            logging.error(f"Error loading {self.resource_type}: {e}")
            raise e
        
    def _load_resources(self):
        """Optimized resource loading with minimal API calls"""
        # Map resource type to loader method
        loaders = {
            "pods": self._load_pods,
            "services": self._load_services,
            "deployments": self._load_deployments,
            "nodes": self._load_nodes,
            "namespaces": self._load_namespaces,
            "configmaps": self._load_configmaps,
            "secrets": self._load_secrets,
            "events": self._load_events,
            "persistentvolumes": self._load_persistent_volumes,
            "persistentvolumeclaims": self._load_persistent_volume_claims,
            "ingresses": self._load_ingresses,
            "daemonsets": self._load_daemonsets,
            "statefulsets": self._load_statefulsets,
            "replicasets": self._load_replicasets,
            "jobs": self._load_jobs,
            "cronjobs": self._load_cronjobs,
            "replicationcontrollers": self._load_replication_controllers,
            "resourcequotas": self._load_resource_quotas,
            "limitranges": self._load_limit_ranges,
            "horizontalpodautoscalers": self._load_horizontal_pod_autoscalers,
            "poddisruptionbudgets": self._load_pod_disruption_budgets,
            "priorityclasses": self._load_priority_classes,
            "runtimeclasses": self._load_runtime_classes,
            "leases": self._load_leases,
            "mutatingwebhookconfigurations": self._load_mutating_webhook_configurations,
            "validatingwebhookconfigurations": self._load_validating_webhook_configurations,
            "endpoints": self._load_endpoints,
            "ingressclasses": self._load_ingress_classes,
            "networkpolicies": self._load_network_policies,
            "storageclasses": self._load_storage_classes,
            "serviceaccounts": self._load_service_accounts,
            "clusterroles": self._load_cluster_roles,
            "roles": self._load_roles,
            "clusterrolebindings": self._load_cluster_role_bindings,
            "rolebindings": self._load_role_bindings,
            "customresourcedefinitions": self._load_custom_resource_definitions,
            # Add more resource types as needed
        }
        
        loader = loaders.get(self.resource_type)
        if loader:
            return loader()
        else:
            # Fallback to generic loader
            return self._load_generic_optimized()
        
    def _get_continue_token(self, response_object):
        """Helper to extract continue token from response metadata."""
        if hasattr(response_object, 'metadata') and hasattr(response_object.metadata, '_continue') and response_object.metadata._continue:
            return response_object.metadata._continue
        return None

    def _format_age(self, timestamp):
        """Format age of Kubernetes resource"""
        if not timestamp:
            return "Unknown"
        
        from datetime import datetime
        try:
            if isinstance(timestamp, str):
                created = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                created = timestamp
            
            now = datetime.now(created.tzinfo or datetime.now().astimezone().tzinfo)
            diff = now - created
            
            if diff.days > 0:
                return f"{diff.days}d"
            elif diff.seconds >= 3600:
                return f"{diff.seconds // 3600}h"
            else:
                return f"{diff.seconds // 60}m"
                
        except:
            return "Unknown"

    def _load_pods(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        # Remove None values from kwargs to avoid issues with the API client
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            pods_list = self.kube_client.v1.list_namespaced_pod(namespace=self.namespace, **api_kwargs)
        else:
            pods_list = self.kube_client.v1.list_pod_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(pods_list)
        for pod in pods_list.items:
            resource = {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace or "default",
                "age": self._format_age(pod.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(pod)
            }
            if pod.spec and pod.spec.containers:
                resource["containers"] = len(pod.spec.containers)
            if pod.status and pod.status.container_statuses:
                restart_count = sum(cs.restart_count or 0 for cs in pod.status.container_statuses)
                resource["restarts"] = restart_count
            if pod.spec and pod.spec.node_name:
                resource["node"] = pod.spec.node_name
            resources.append(resource)
        return resources, next_token

    def _load_services(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            services_list = self.kube_client.v1.list_namespaced_service(namespace=self.namespace, **api_kwargs)
        else:
            services_list = self.kube_client.v1.list_service_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(services_list)
        for service in services_list.items:
            resource = {
                "name": service.metadata.name,
                "namespace": service.metadata.namespace or "default",
                "age": self._format_age(service.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(service)
            }
            if service.spec:
                resource["type"] = service.spec.type or "ClusterIP"
                resource["cluster_ip"] = service.spec.cluster_ip or "<none>"
                if service.spec.ports:
                    ports_desc = [f"{p.port}:{p.target_port}/{p.protocol}" for p in service.spec.ports if p.port and p.target_port and p.protocol]
                    resource["ports"] = ", ".join(ports_desc) if ports_desc else "<none>"
                else:
                    resource["ports"] = "<none>"
            resources.append(resource)
        return resources, next_token

    def _load_deployments(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            deployments_list = self.kube_client.apps_v1.list_namespaced_deployment(namespace=self.namespace, **api_kwargs)
        else:
            deployments_list = self.kube_client.apps_v1.list_deployment_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(deployments_list)
        for deployment in deployments_list.items:
            resource = {
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace or "default",
                "age": self._format_age(deployment.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(deployment)
            }
            if deployment.spec:
                resource["replicas"] = deployment.spec.replicas or 0
            if deployment.status:
                resource["ready"] = deployment.status.ready_replicas or 0
                resource["up_to_date"] = deployment.status.updated_replicas or 0
                resource["available"] = deployment.status.available_replicas or 0
            resources.append(resource)
        return resources, next_token

    def _load_nodes(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        nodes_list = self.kube_client.v1.list_node(**api_kwargs)
        next_token = self._get_continue_token(nodes_list)
        
        for node in nodes_list.items:
            resource = {
                "name": node.metadata.name,
                "namespace": "",  # Nodes are cluster-scoped
                "age": self._format_age(node.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(node)
            }
            
            # Add node-specific info
            if node.status:
                if node.status.conditions:
                    ready_condition = next((c for c in node.status.conditions if c.type == "Ready"), None)
                    resource["status"] = "Ready" if ready_condition and ready_condition.status == "True" else "NotReady"
                if node.status.node_info:
                    resource["version"] = node.status.node_info.kubelet_version
                    resource["os"] = f"{node.status.node_info.operating_system}/{node.status.node_info.architecture}"
            
            # Add roles
            roles = []
            if node.metadata.labels:
                for label_key in node.metadata.labels:
                    if label_key.startswith("node-role.kubernetes.io/"):
                        role = label_key.split("/", 1)[1] or "master"
                        roles.append(role)
            resource["roles"] = ",".join(roles) if roles else "<none>"
            
            resources.append(resource)
        return resources, next_token

    def _load_namespaces(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        namespaces_list = self.kube_client.v1.list_namespace(**api_kwargs)
        next_token = self._get_continue_token(namespaces_list)
        
        for namespace in namespaces_list.items:
            resource = {
                "name": namespace.metadata.name,
                "namespace": "",  # Namespaces are cluster-scoped
                "age": self._format_age(namespace.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(namespace)
            }
            if namespace.status:
                resource["status"] = namespace.status.phase or "Unknown"
            resources.append(resource)
        return resources, next_token

    def _load_configmaps(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            configmaps_list = self.kube_client.v1.list_namespaced_config_map(namespace=self.namespace, **api_kwargs)
        else:
            configmaps_list = self.kube_client.v1.list_config_map_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(configmaps_list)
        for configmap in configmaps_list.items:
            resource = {
                "name": configmap.metadata.name,
                "namespace": configmap.metadata.namespace or "default",
                "age": self._format_age(configmap.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(configmap)
            }
            if configmap.data:
                resource["data_keys"] = len(configmap.data)
            else:
                resource["data_keys"] = 0
            resources.append(resource)
        return resources, next_token

    def _load_secrets(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            secrets_list = self.kube_client.v1.list_namespaced_secret(namespace=self.namespace, **api_kwargs)
        else:
            secrets_list = self.kube_client.v1.list_secret_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(secrets_list)
        for secret in secrets_list.items:
            resource = {
                "name": secret.metadata.name,
                "namespace": secret.metadata.namespace or "default",
                "age": self._format_age(secret.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(secret)
            }
            resource["type"] = secret.type or "Opaque"
            if secret.data:
                resource["data_keys"] = len(secret.data)
            else:
                resource["data_keys"] = 0
            resources.append(resource)
        return resources, next_token

    def _load_events(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            events_list = self.kube_client.v1.list_namespaced_event(namespace=self.namespace, **api_kwargs)
        else:
            events_list = self.kube_client.v1.list_event_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(events_list)
        for event in events_list.items:
            resource = {
                "name": event.metadata.name,
                "namespace": event.metadata.namespace or "default",
                "age": self._format_age(event.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(event)
            }
            resource["type"] = event.type or "Normal"
            resource["reason"] = event.reason or "Unknown"
            resource["message"] = (event.message or "")[:100]  # Truncate long messages
            if event.involved_object:
                resource["object"] = f"{event.involved_object.kind}/{event.involved_object.name}"
            resources.append(resource)
        return resources, next_token

    def _load_persistent_volumes(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        pvs_list = self.kube_client.v1.list_persistent_volume(**api_kwargs)
        next_token = self._get_continue_token(pvs_list)
        
        for pv in pvs_list.items:
            resource = {
                "name": pv.metadata.name,
                "namespace": "",  # PVs are cluster-scoped
                "age": self._format_age(pv.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(pv)
            }
            if pv.spec:
                resource["capacity"] = pv.spec.capacity.get('storage', 'Unknown') if pv.spec.capacity else 'Unknown'
                resource["access_modes"] = ','.join(pv.spec.access_modes) if pv.spec.access_modes else 'Unknown'
                resource["reclaim_policy"] = pv.spec.persistent_volume_reclaim_policy or 'Unknown'
            if pv.status:
                resource["status"] = pv.status.phase or 'Unknown'
            resources.append(resource)
        return resources, next_token

    def _load_persistent_volume_claims(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            pvcs_list = self.kube_client.v1.list_namespaced_persistent_volume_claim(namespace=self.namespace, **api_kwargs)
        else:
            pvcs_list = self.kube_client.v1.list_persistent_volume_claim_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(pvcs_list)
        for pvc in pvcs_list.items:
            resource = {
                "name": pvc.metadata.name,
                "namespace": pvc.metadata.namespace or "default",
                "age": self._format_age(pvc.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(pvc)
            }
            if pvc.status:
                resource["status"] = pvc.status.phase or 'Unknown'
            if pvc.spec:
                resource["volume"] = pvc.spec.volume_name or 'Unknown'
                if pvc.spec.resources and pvc.spec.resources.requests:
                    resource["capacity"] = pvc.spec.resources.requests.get('storage', 'Unknown')
                resource["access_modes"] = ','.join(pvc.spec.access_modes) if pvc.spec.access_modes else 'Unknown'
            resources.append(resource)
        return resources, next_token

    def _load_ingresses(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            ingresses_list = self.kube_client.networking_v1.list_namespaced_ingress(namespace=self.namespace, **api_kwargs)
        else:
            ingresses_list = self.kube_client.networking_v1.list_ingress_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(ingresses_list)
        for ingress in ingresses_list.items:
            resource = {
                "name": ingress.metadata.name,
                "namespace": ingress.metadata.namespace or "default",
                "age": self._format_age(ingress.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(ingress)
            }
            if ingress.spec and ingress.spec.rules:
                hosts = [rule.host for rule in ingress.spec.rules if rule.host]
                resource["hosts"] = ','.join(hosts) if hosts else '*'
            else:
                resource["hosts"] = '*'
            resources.append(resource)
        return resources, next_token

    # Continue with remaining loader methods...
    def _load_daemonsets(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            daemonsets_list = self.kube_client.apps_v1.list_namespaced_daemon_set(namespace=self.namespace, **api_kwargs)
        else:
            daemonsets_list = self.kube_client.apps_v1.list_daemon_set_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(daemonsets_list)
        for ds in daemonsets_list.items:
            resource = {
                "name": ds.metadata.name,
                "namespace": ds.metadata.namespace or "default",
                "age": self._format_age(ds.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(ds)
            }
            if ds.status:
                resource["desired"] = ds.status.desired_number_scheduled or 0
                resource["current"] = ds.status.current_number_scheduled or 0
                resource["ready"] = ds.status.number_ready or 0
                resource["up_to_date"] = ds.status.updated_number_scheduled or 0
                resource["available"] = ds.status.number_available or 0
            resources.append(resource)
        return resources, next_token

    def _load_statefulsets(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            statefulsets_list = self.kube_client.apps_v1.list_namespaced_stateful_set(namespace=self.namespace, **api_kwargs)
        else:
            statefulsets_list = self.kube_client.apps_v1.list_stateful_set_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(statefulsets_list)
        for ss in statefulsets_list.items:
            resource = {
                "name": ss.metadata.name,
                "namespace": ss.metadata.namespace or "default",
                "age": self._format_age(ss.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(ss)
            }
            if ss.spec:
                resource["replicas"] = ss.spec.replicas or 0
            if ss.status:
                resource["ready"] = ss.status.ready_replicas or 0
            resources.append(resource)
        return resources, next_token

    def _load_replicasets(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            replicasets_list = self.kube_client.apps_v1.list_namespaced_replica_set(namespace=self.namespace, **api_kwargs)
        else:
            replicasets_list = self.kube_client.apps_v1.list_replica_set_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(replicasets_list)
        for rs in replicasets_list.items:
            resource = {
                "name": rs.metadata.name,
                "namespace": rs.metadata.namespace or "default",
                "age": self._format_age(rs.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(rs)
            }
            if rs.spec:
                resource["desired"] = rs.spec.replicas or 0
            if rs.status:
                resource["current"] = rs.status.replicas or 0
                resource["ready"] = rs.status.ready_replicas or 0
            resources.append(resource)
        return resources, next_token

    def _load_jobs(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            jobs_list = self.kube_client.batch_v1.list_namespaced_job(namespace=self.namespace, **api_kwargs)
        else:
            jobs_list = self.kube_client.batch_v1.list_job_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(jobs_list)
        for job in jobs_list.items:
            resource = {
                "name": job.metadata.name,
                "namespace": job.metadata.namespace or "default",
                "age": self._format_age(job.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(job)
            }
            if job.status:
                resource["completions"] = f"{job.status.succeeded or 0}/{job.spec.completions or 1}"
                resource["duration"] = self._format_duration(job.status.start_time, job.status.completion_time)
            resources.append(resource)
        return resources, next_token

    def _load_cronjobs(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            cronjobs_list = self.kube_client.batch_v1.list_namespaced_cron_job(namespace=self.namespace, **api_kwargs)
        else:
            cronjobs_list = self.kube_client.batch_v1.list_cron_job_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(cronjobs_list)
        for cronjob in cronjobs_list.items:
            resource = {
                "name": cronjob.metadata.name,
                "namespace": cronjob.metadata.namespace or "default",
                "age": self._format_age(cronjob.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(cronjob)
            }
            if cronjob.spec:
                resource["schedule"] = cronjob.spec.schedule or "Unknown"
                resource["suspend"] = str(cronjob.spec.suspend or False)
            if cronjob.status:
                resource["active"] = len(cronjob.status.active) if cronjob.status.active else 0
                if cronjob.status.last_schedule_time:
                    resource["last_schedule"] = self._format_age(cronjob.status.last_schedule_time)
            resources.append(resource)
        return resources, next_token

    def _load_generic_optimized(self):
        """Generic optimized loader for unknown resource types"""
        # This would implement a generic K8s resource loader
        # For now, return empty results
        logging.warning(f"Generic loader not fully implemented for {self.resource_type}")
        return [], None

    def _format_duration(self, start_time, end_time):
        """Format duration between two timestamps"""
        if not start_time:
            return "Unknown"
        
        from datetime import datetime
        try:
            if not end_time:
                end_time = datetime.now(start_time.tzinfo or datetime.now().astimezone().tzinfo)
            
            duration = end_time - start_time
            if duration.days > 0:
                return f"{duration.days}d"
            elif duration.seconds >= 3600:
                return f"{duration.seconds // 3600}h"
            else:
                return f"{duration.seconds // 60}m"
        except:
            return "Unknown"

    # Implemented methods for remaining resource types
    def _load_replication_controllers(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            rcs_list = self.kube_client.v1.list_namespaced_replication_controller(namespace=self.namespace, **api_kwargs)
        else:
            rcs_list = self.kube_client.v1.list_replication_controller_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(rcs_list)
        for rc in rcs_list.items:
            resource = {
                "name": rc.metadata.name,
                "namespace": rc.metadata.namespace or "default",
                "age": self._format_age(rc.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(rc)
            }
            if rc.spec:
                resource["replicas"] = rc.spec.replicas or 0
            if rc.status:
                resource["ready"] = rc.status.ready_replicas or 0
            resources.append(resource)
        return resources, next_token

    def _load_resource_quotas(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            quotas_list = self.kube_client.v1.list_namespaced_resource_quota(namespace=self.namespace, **api_kwargs)
        else:
            quotas_list = self.kube_client.v1.list_resource_quota_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(quotas_list)
        for quota in quotas_list.items:
            resource = {
                "name": quota.metadata.name,
                "namespace": quota.metadata.namespace or "default",
                "age": self._format_age(quota.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(quota)
            }
            if quota.status and quota.status.hard:
                resource["hard_limits"] = len(quota.status.hard)
            resources.append(resource)
        return resources, next_token

    def _load_limit_ranges(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            limits_list = self.kube_client.v1.list_namespaced_limit_range(namespace=self.namespace, **api_kwargs)
        else:
            limits_list = self.kube_client.v1.list_limit_range_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(limits_list)
        for limit_range in limits_list.items:
            resource = {
                "name": limit_range.metadata.name,
                "namespace": limit_range.metadata.namespace or "default",
                "age": self._format_age(limit_range.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(limit_range)
            }
            resources.append(resource)
        return resources, next_token

    def _load_horizontal_pod_autoscalers(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            hpas_list = self.kube_client.autoscaling_v1.list_namespaced_horizontal_pod_autoscaler(namespace=self.namespace, **api_kwargs)
        else:
            hpas_list = self.kube_client.autoscaling_v1.list_horizontal_pod_autoscaler_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(hpas_list)
        for hpa in hpas_list.items:
            resource = {
                "name": hpa.metadata.name,
                "namespace": hpa.metadata.namespace or "default",
                "age": self._format_age(hpa.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(hpa)
            }
            if hpa.spec:
                resource["min_replicas"] = hpa.spec.min_replicas or 1
                resource["max_replicas"] = hpa.spec.max_replicas or 1
            if hpa.status:
                resource["current_replicas"] = hpa.status.current_replicas or 0
            resources.append(resource)
        return resources, next_token

    def _load_pod_disruption_budgets(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            if self.namespace and self.namespace != "all":
                pdbs_list = self.kube_client.policy_v1.list_namespaced_pod_disruption_budget(namespace=self.namespace, **api_kwargs)
            else:
                pdbs_list = self.kube_client.policy_v1.list_pod_disruption_budget_for_all_namespaces(**api_kwargs)

            next_token = self._get_continue_token(pdbs_list)
            for pdb in pdbs_list.items:
                resource = {
                    "name": pdb.metadata.name,
                    "namespace": pdb.metadata.namespace or "default",
                    "age": self._format_age(pdb.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(pdb)
                }
                resources.append(resource)
        except Exception as e:
            # policy_v1 API might not be available in some clusters
            logging.warning(f"Pod disruption budgets not available: {e}")
        return resources, next_token

    def _load_priority_classes(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            priority_classes_list = self.kube_client.scheduling_v1.list_priority_class(**api_kwargs)
            next_token = self._get_continue_token(priority_classes_list)
            
            for pc in priority_classes_list.items:
                resource = {
                    "name": pc.metadata.name,
                    "namespace": "",  # Priority classes are cluster-scoped
                    "age": self._format_age(pc.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(pc)
                }
                resource["value"] = pc.value or 0
                resource["global_default"] = pc.global_default or False
                resources.append(resource)
        except Exception as e:
            logging.warning(f"Priority classes not available: {e}")
        return resources, next_token

    def _load_runtime_classes(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            runtime_classes_list = self.kube_client.node_v1.list_runtime_class(**api_kwargs)
            next_token = self._get_continue_token(runtime_classes_list)
            
            for rc in runtime_classes_list.items:
                resource = {
                    "name": rc.metadata.name,
                    "namespace": "",  # Runtime classes are cluster-scoped
                    "age": self._format_age(rc.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(rc)
                }
                resource["handler"] = rc.handler or "Unknown"
                resources.append(resource)
        except Exception as e:
            logging.warning(f"Runtime classes not available: {e}")
        return resources, next_token

    def _load_leases(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            if self.namespace and self.namespace != "all":
                leases_list = self.kube_client.coordination_v1.list_namespaced_lease(namespace=self.namespace, **api_kwargs)
            else:
                leases_list = self.kube_client.coordination_v1.list_lease_for_all_namespaces(**api_kwargs)

            next_token = self._get_continue_token(leases_list)
            for lease in leases_list.items:
                resource = {
                    "name": lease.metadata.name,
                    "namespace": lease.metadata.namespace or "default",
                    "age": self._format_age(lease.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(lease)
                }
                resources.append(resource)
        except Exception as e:
            logging.warning(f"Leases not available: {e}")
        return resources, next_token

    def _load_mutating_webhook_configurations(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            webhooks_list = self.kube_client.admissionregistration_v1.list_mutating_webhook_configuration(**api_kwargs)
            next_token = self._get_continue_token(webhooks_list)
            
            for webhook in webhooks_list.items:
                resource = {
                    "name": webhook.metadata.name,
                    "namespace": "",  # Webhook configs are cluster-scoped
                    "age": self._format_age(webhook.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(webhook)
                }
                if webhook.webhooks:
                    resource["webhooks_count"] = len(webhook.webhooks)
                resources.append(resource)
        except Exception as e:
            logging.warning(f"Mutating webhook configurations not available: {e}")
        return resources, next_token

    def _load_validating_webhook_configurations(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            webhooks_list = self.kube_client.admissionregistration_v1.list_validating_webhook_configuration(**api_kwargs)
            next_token = self._get_continue_token(webhooks_list)
            
            for webhook in webhooks_list.items:
                resource = {
                    "name": webhook.metadata.name,
                    "namespace": "",  # Webhook configs are cluster-scoped
                    "age": self._format_age(webhook.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(webhook)
                }
                if webhook.webhooks:
                    resource["webhooks_count"] = len(webhook.webhooks)
                resources.append(resource)
        except Exception as e:
            logging.warning(f"Validating webhook configurations not available: {e}")
        return resources, next_token

    def _load_endpoints(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            endpoints_list = self.kube_client.v1.list_namespaced_endpoints(namespace=self.namespace, **api_kwargs)
        else:
            endpoints_list = self.kube_client.v1.list_endpoints_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(endpoints_list)
        for endpoint in endpoints_list.items:
            resource = {
                "name": endpoint.metadata.name,
                "namespace": endpoint.metadata.namespace or "default",
                "age": self._format_age(endpoint.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(endpoint)
            }
            if endpoint.subsets:
                addresses_count = sum(len(subset.addresses or []) for subset in endpoint.subsets)
                resource["endpoints"] = addresses_count
            else:
                resource["endpoints"] = 0
            resources.append(resource)
        return resources, next_token

    def _load_ingress_classes(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            ingress_classes_list = self.kube_client.networking_v1.list_ingress_class(**api_kwargs)
            next_token = self._get_continue_token(ingress_classes_list)
            
            for ingress_class in ingress_classes_list.items:
                resource = {
                    "name": ingress_class.metadata.name,
                    "namespace": "",  # Ingress classes are cluster-scoped
                    "age": self._format_age(ingress_class.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(ingress_class)
                }
                if ingress_class.spec:
                    resource["controller"] = ingress_class.spec.controller or "Unknown"
                resources.append(resource)
        except Exception as e:
            logging.warning(f"Ingress classes not available: {e}")
        return resources, next_token

    def _load_network_policies(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            if self.namespace and self.namespace != "all":
                policies_list = self.kube_client.networking_v1.list_namespaced_network_policy(namespace=self.namespace, **api_kwargs)
            else:
                policies_list = self.kube_client.networking_v1.list_network_policy_for_all_namespaces(**api_kwargs)

            next_token = self._get_continue_token(policies_list)
            for policy in policies_list.items:
                resource = {
                    "name": policy.metadata.name,
                    "namespace": policy.metadata.namespace or "default",
                    "age": self._format_age(policy.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(policy)
                }
                resources.append(resource)
        except Exception as e:
            logging.warning(f"Network policies not available: {e}")
        return resources, next_token

    def _load_storage_classes(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            storage_classes_list = self.kube_client.storage_v1.list_storage_class(**api_kwargs)
            next_token = self._get_continue_token(storage_classes_list)
            
            for sc in storage_classes_list.items:
                resource = {
                    "name": sc.metadata.name,
                    "namespace": "",  # Storage classes are cluster-scoped
                    "age": self._format_age(sc.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(sc)
                }
                resource["provisioner"] = sc.provisioner or "Unknown"
                resource["reclaim_policy"] = sc.reclaim_policy or "Delete"
                resource["volume_binding_mode"] = sc.volume_binding_mode or "Immediate"
                resources.append(resource)
        except Exception as e:
            logging.warning(f"Storage classes not available: {e}")
        return resources, next_token

    def _load_service_accounts(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            sa_list = self.kube_client.v1.list_namespaced_service_account(namespace=self.namespace, **api_kwargs)
        else:
            sa_list = self.kube_client.v1.list_service_account_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(sa_list)
        for sa in sa_list.items:
            resource = {
                "name": sa.metadata.name,
                "namespace": sa.metadata.namespace or "default",
                "age": self._format_age(sa.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(sa)
            }
            if sa.secrets:
                resource["secrets"] = len(sa.secrets)
            else:
                resource["secrets"] = 0
            resources.append(resource)
        return resources, next_token

    def _load_cluster_roles(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            cluster_roles_list = self.kube_client.rbac_authorization_v1.list_cluster_role(**api_kwargs)
            next_token = self._get_continue_token(cluster_roles_list)
            
            for cr in cluster_roles_list.items:
                resource = {
                    "name": cr.metadata.name,
                    "namespace": "",  # Cluster roles are cluster-scoped
                    "age": self._format_age(cr.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(cr)
                }
                if cr.rules:
                    resource["rules"] = len(cr.rules)
                resources.append(resource)
        except Exception as e:
            logging.warning(f"Cluster roles not available: {e}")
        return resources, next_token

    def _load_roles(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            if self.namespace and self.namespace != "all":
                roles_list = self.kube_client.rbac_authorization_v1.list_namespaced_role(namespace=self.namespace, **api_kwargs)
            else:
                roles_list = self.kube_client.rbac_authorization_v1.list_role_for_all_namespaces(**api_kwargs)

            next_token = self._get_continue_token(roles_list)
            for role in roles_list.items:
                resource = {
                    "name": role.metadata.name,
                    "namespace": role.metadata.namespace or "default",
                    "age": self._format_age(role.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(role)
                }
                if role.rules:
                    resource["rules"] = len(role.rules)
                resources.append(resource)
        except Exception as e:
            logging.warning(f"Roles not available: {e}")
        return resources, next_token

    def _load_cluster_role_bindings(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            crb_list = self.kube_client.rbac_authorization_v1.list_cluster_role_binding(**api_kwargs)
            next_token = self._get_continue_token(crb_list)
            
            for crb in crb_list.items:
                resource = {
                    "name": crb.metadata.name,
                    "namespace": "",  # Cluster role bindings are cluster-scoped
                    "age": self._format_age(crb.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(crb)
                }
                if crb.subjects:
                    resource["subjects"] = len(crb.subjects)
                if crb.role_ref:
                    resource["role"] = crb.role_ref.name
                resources.append(resource)
        except Exception as e:
            logging.warning(f"Cluster role bindings not available: {e}")
        return resources, next_token

    def _load_role_bindings(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            if self.namespace and self.namespace != "all":
                rb_list = self.kube_client.rbac_authorization_v1.list_namespaced_role_binding(namespace=self.namespace, **api_kwargs)
            else:
                rb_list = self.kube_client.rbac_authorization_v1.list_role_binding_for_all_namespaces(**api_kwargs)

            next_token = self._get_continue_token(rb_list)
            for rb in rb_list.items:
                resource = {
                    "name": rb.metadata.name,
                    "namespace": rb.metadata.namespace or "default",
                    "age": self._format_age(rb.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(rb)
                }
                if rb.subjects:
                    resource["subjects"] = len(rb.subjects)
                if rb.role_ref:
                    resource["role"] = rb.role_ref.name
                resources.append(resource)
        except Exception as e:
            logging.warning(f"Role bindings not available: {e}")
        return resources, next_token

    def _load_custom_resource_definitions(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        try:
            crd_list = self.kube_client.apiextensions_v1.list_custom_resource_definition(**api_kwargs)
            next_token = self._get_continue_token(crd_list)
            
            for crd in crd_list.items:
                resource = {
                    "name": crd.metadata.name,
                    "namespace": "",  # CRDs are cluster-scoped
                    "age": self._format_age(crd.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(crd)
                }
                if crd.spec:
                    resource["group"] = crd.spec.group or "Unknown"
                    resource["scope"] = crd.spec.scope or "Unknown"
                    if crd.spec.versions:
                        resource["versions"] = len(crd.spec.versions)
                resources.append(resource)
        except Exception as e:
            logging.warning(f"Custom resource definitions not available: {e}")
        return resources, next_token