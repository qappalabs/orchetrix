"""
Kubernetes Resource Parsers
Extracted from unified_resource_loader.py to enforce separation of concerns.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from Utils.kubernetes_client import get_kubernetes_client

class KubernetesResourceParser:
    """Centralized parsing logic for Kubernetes resources"""

    @staticmethod
    def add_resource_specific_fields(processed_item: Dict[str, Any], item: Any, preloaded_metrics: Optional[Dict[str, Any]] = None):
        """Add resource-specific fields efficiently"""
        resource_type = processed_item.get('resource_type')

        if resource_type == 'pods':
            KubernetesResourceParser.add_pod_fields(processed_item, item)
        elif resource_type == 'nodes':
            logging.debug(f"Unified Resource Loader: Adding node-specific fields for {processed_item.get('name', 'unknown')}")
            KubernetesResourceParser.add_node_fields(processed_item, item, preloaded_metrics)
        elif resource_type == 'services':
            KubernetesResourceParser.add_service_fields(processed_item, item)
        elif resource_type in ['deployments', 'replicasets', 'statefulsets']:
            KubernetesResourceParser.add_workload_fields(processed_item, item)
        elif resource_type == 'daemonsets':
            KubernetesResourceParser.add_daemonset_fields(processed_item, item)
        elif resource_type == 'replicationcontrollers':
            KubernetesResourceParser.add_replicationcontroller_fields(processed_item, item)
        elif resource_type == 'configmaps':
            KubernetesResourceParser.add_configmap_fields(processed_item, item)
        elif resource_type == 'secrets':
            KubernetesResourceParser.add_secret_fields(processed_item, item)
        elif resource_type == 'resourcequotas':
            KubernetesResourceParser.add_resourcequota_fields(processed_item, item)
        elif resource_type == 'limitranges':
            KubernetesResourceParser.add_limitrange_fields(processed_item, item)
        elif resource_type == 'horizontalpodautoscalers':
            KubernetesResourceParser.add_hpa_fields(processed_item, item)
        elif resource_type == 'poddisruptionbudgets':
            KubernetesResourceParser.add_pdb_fields(processed_item, item)
        elif resource_type == 'priorityclasses':
            KubernetesResourceParser.add_priorityclass_fields(processed_item, item)
        elif resource_type == 'runtimeclasses':
            KubernetesResourceParser.add_runtimeclass_fields(processed_item, item)
        elif resource_type == 'leases':
            KubernetesResourceParser.add_lease_fields(processed_item, item)
        elif resource_type == 'mutatingwebhookconfigurations':
            KubernetesResourceParser.add_mutatingwebhook_fields(processed_item, item)
        elif resource_type == 'validatingwebhookconfigurations':
            KubernetesResourceParser.add_validatingwebhook_fields(processed_item, item)
        elif resource_type == 'serviceaccounts':
            KubernetesResourceParser.add_serviceaccount_fields(processed_item, item)
        elif resource_type == 'endpoints':
            KubernetesResourceParser.add_endpoints_fields(processed_item, item)
        elif resource_type in ['roles', 'clusterroles']:
            KubernetesResourceParser.add_role_fields(processed_item, item)
        elif resource_type in ['rolebindings', 'clusterrolebindings']:
            KubernetesResourceParser.add_rolebinding_fields(processed_item, item)
        elif resource_type == 'customresourcedefinitions':
            KubernetesResourceParser.add_crd_fields(processed_item, item)

    @staticmethod
    def add_pod_fields(processed_item: Dict[str, Any], pod: Any):
        """Add pod-specific fields efficiently"""
        status = pod.status
        spec = pod.spec

        # Enhanced status determination with more detail
        pod_status = 'Unknown'
        if status:
            pod_status = status.phase or 'Unknown'

            # Check for more specific container states
            if status.container_statuses:
                for cs in status.container_statuses:
                    if cs.state:
                        if cs.state.waiting:
                            reason = cs.state.waiting.reason
                            if reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                                pod_status = reason
                                break
                        elif cs.state.terminated:
                            if cs.state.terminated.exit_code != 0:
                                pod_status = "Error"
                                break

        processed_item.update({
            'status': pod_status,
            'ready': KubernetesResourceParser.get_pod_ready_status(status),
            'restarts': KubernetesResourceParser.get_pod_restart_count(status),
            'node_name': spec.node_name if spec else None,
            'host_ip': status.host_ip if status else None,
            'pod_ip': status.pod_ip if status else None,
            'containers': len(spec.containers) if spec and spec.containers else 0,
            'init_containers': len(spec.init_containers) if spec and spec.init_containers else 0,
        })

    @staticmethod
    def add_node_fields(processed_item: Dict[str, Any], node: Any, preloaded_metrics: Optional[Dict[str, Any]] = None):
        """Add node-specific fields efficiently - optimized for heavy data"""
        status = node.status

        # Quick exit for invalid nodes
        if not status:
            processed_item.update({
                'status': 'Unknown',
                'conditions': 'Unknown',
                'roles': ['<none>'],
                'version': 'Unknown',
                'os': 'Unknown',
                'kernel': 'Unknown',
                'taints': '0',
                'cpu_usage': 0.0,
                'memory_usage': 0.0,
                'disk_usage': 0.0,
                'cpu_capacity': '',
                'memory_capacity': '',
                'disk_capacity': ''
            })
            return

        # Process node conditions using helper method from the loader class
        node_status, conditions_text = KubernetesResourceParser.process_node_conditions(status.conditions if status else None)

        # Extract node roles using helper method from the loader class
        roles = KubernetesResourceParser.extract_node_roles(node.metadata.labels if node.metadata else None)

        # Get taints count
        taints_count = 0
        if node.spec and node.spec.taints:
            taints_count = len(node.spec.taints)

        # Format capacity information using helper method from the loader class
        memory_capacity = ''
        disk_capacity = ''
        if status and status.capacity:
            memory_capacity = KubernetesResourceParser.format_capacity(status.capacity.get('memory', ''))
            disk_capacity = KubernetesResourceParser.format_capacity(status.capacity.get('ephemeral-storage', ''))

        # Don't simulate disk usage - leave as None to be filled by real metrics
        estimated_disk_usage = None

        processed_item.update({
            'status': node_status,
            'conditions': conditions_text,
            'roles': roles,
            'version': status.node_info.kubelet_version if status and status.node_info else 'Unknown',
            'os': status.node_info.operating_system if status and status.node_info else 'Unknown',
            'kernel': status.node_info.kernel_version if status and status.node_info else 'Unknown',
            'taints': str(taints_count),
            'cpu_usage': None,  # Will be filled by metrics if available
            'memory_usage': None,  # Will be filled by metrics if available
            'disk_usage': estimated_disk_usage,  # Estimated usage, will be replaced by real metrics if available
        })

        # Add capacity information
        if status and status.capacity:
            processed_item.update({
                'cpu_capacity': status.capacity.get('cpu', ''),
                'memory_capacity': memory_capacity,
                'disk_capacity': disk_capacity,
                'pods_capacity': status.capacity.get('pods', ''),
            })

        # Use preloaded metrics if available, otherwise set defaults
        cpu_usage = 0.0
        memory_usage = 0.0
        disk_usage = 0.0

        if preloaded_metrics:
            cpu_usage = preloaded_metrics.get("cpu", {}).get("usage", 0.0)
            memory_usage = preloaded_metrics.get("memory", {}).get("usage", 0.0)
            disk_usage_val = preloaded_metrics.get("disk", {}).get("usage")
            disk_usage = disk_usage_val if disk_usage_val is not None else 0.0

            logging.debug(f"Using preloaded metrics for {processed_item.get('name', 'unknown')}: "
                        f"CPU {cpu_usage:.1f}%, Memory {memory_usage:.1f}%, Disk {disk_usage:.1f}%")

        processed_item.update({
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'disk_usage': disk_usage
        })

    @staticmethod
    def add_service_fields(processed_item: Dict[str, Any], service: Any):
        """Add service-specific fields efficiently"""
        spec = service.spec
        status = service.status

        processed_item.update({
            'type': spec.type if spec else 'Unknown',
            'cluster_ip': spec.cluster_ip if spec else None,
            'external_ip': KubernetesResourceParser.get_service_external_ip(spec, status),
            'ports': len(spec.ports) if spec and spec.ports else 0,
        })

    @staticmethod
    def add_workload_fields(processed_item: Dict[str, Any], workload: Any):
        """Add workload-specific fields efficiently"""
        spec = workload.spec
        status = workload.status

        # Get replicas info
        replicas = getattr(spec, 'replicas', 1) if spec else 1
        ready_replicas = getattr(status, 'ready_replicas', 0) if status else 0

        processed_item.update({
            'replicas': f"{ready_replicas}/{replicas}",
            'ready_replicas': ready_replicas,
            'total_replicas': replicas,
        })

    @staticmethod
    def add_daemonset_fields(processed_item: Dict[str, Any], daemonset: Any):
        """Add DaemonSet-specific fields.

        DaemonSets have no spec.replicas; the displayed count comes from the
        status scheduling fields (number_ready / desired_number_scheduled).
        """
        status = daemonset.status

        desired = getattr(status, 'desired_number_scheduled', 0) or 0 if status else 0
        ready = getattr(status, 'number_ready', 0) or 0 if status else 0

        processed_item.update({
            'replicas': f"{ready}/{desired}",
            'ready_replicas': ready,
            'total_replicas': desired,
        })

    @staticmethod
    def format_age_fast(creation_timestamp) -> str:
        """Fast age calculation with comprehensive timestamp handling"""
        if not creation_timestamp:
            return 'Unknown'

        try:
            # Handle different timestamp formats
            if hasattr(creation_timestamp, 'timestamp'):
                # Kubernetes datetime object
                created = datetime.fromtimestamp(creation_timestamp.timestamp(), tz=timezone.utc)
            elif isinstance(creation_timestamp, str):
                # ISO string format
                if creation_timestamp.endswith('Z'):
                    created = datetime.fromisoformat(creation_timestamp.replace('Z', '+00:00'))
                else:
                    created = datetime.fromisoformat(creation_timestamp)
                # Ensure timezone aware
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
            elif isinstance(creation_timestamp, datetime):
                # Already a datetime object
                created = creation_timestamp
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
            else:
                # Try to convert to string and parse
                created = datetime.fromisoformat(str(creation_timestamp).replace('Z', '+00:00'))

            # Calculate age
            now = datetime.now(timezone.utc)
            age_delta = now - created

            days = age_delta.days
            hours = age_delta.seconds // 3600
            minutes = (age_delta.seconds % 3600) // 60

            # Format age
            if days > 365:
                years = days // 365
                return f"{years}y"
            elif days > 30:
                months = days // 30
                return f"{months}mo"
            elif days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            elif minutes > 0:
                return f"{minutes}m"
            else:
                return "<1m"

        except Exception as e:
            logging.warning(f"Error calculating age for timestamp {creation_timestamp}: {e}")
            return 'Unknown'

    @staticmethod
    def get_pod_ready_status(status) -> str:
        """Get pod ready status efficiently"""
        if not status or not status.container_statuses:
            return '0/0'

        ready_count = sum(1 for cs in status.container_statuses if cs.ready)
        total_count = len(status.container_statuses)

        return f"{ready_count}/{total_count}"

    @staticmethod
    def get_pod_restart_count(status) -> int:
        """Get pod restart count efficiently"""
        if not status or not status.container_statuses:
            return 0

        return sum(cs.restart_count for cs in status.container_statuses if cs.restart_count)

    @staticmethod
    def get_service_external_ip(spec, status) -> Optional[str]:
        """Get service external IP efficiently"""
        external_ips = []

        # Check for explicit external IPs
        if spec and spec.external_i_ps:
            external_ips.extend(spec.external_i_ps)

        # Check for LoadBalancer ingress IPs and hostnames
        if spec and spec.type == 'LoadBalancer' and status and status.load_balancer:
            if status.load_balancer.ingress:
                for ing in status.load_balancer.ingress:
                    if ing.ip:
                        external_ips.append(ing.ip)
                    elif ing.hostname:
                        external_ips.append(ing.hostname)

        # Check for NodePort external access
        if spec and spec.type == 'NodePort':
            # For NodePort services, indicate they are externally accessible
            # We could show actual node IPs but that would require additional API calls
            external_ips.append("<NodePort>")

        # Check for ExternalName services
        if spec and spec.type == 'ExternalName' and spec.external_name:
            external_ips.append(spec.external_name)

        return ', '.join(external_ips) if external_ips else None

    @staticmethod
    def add_replicationcontroller_fields(processed_item: Dict[str, Any], item: Any):
        """Add ReplicationController-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            replicas = getattr(spec, 'replicas', 0) if spec else 0
            ready_replicas = getattr(status, 'replicas', 0) if status else 0

            processed_item.update({
                'replicas': ready_replicas,
                'desired_replicas': replicas,
                'selector': ', '.join([f"{k}={v}" for k, v in (spec.selector or {}).items()]) if spec and spec.selector else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing ReplicationController fields: {e}")

    @staticmethod
    def add_configmap_fields(processed_item: Dict[str, Any], item: Any):
        """Add ConfigMap-specific fields"""
        try:
            data = item.data or {}
            processed_item.update({
                'keys': ', '.join(data.keys()) if data else '<none>',
                'data_count': len(data),
            })
        except Exception as e:
            logging.debug(f"Error processing ConfigMap fields: {e}")

    @staticmethod
    def add_secret_fields(processed_item: Dict[str, Any], item: Any):
        """Add Secret-specific fields"""
        try:
            data = item.data or {}
            secret_type = getattr(item, 'type', 'Opaque')
            processed_item.update({
                'type': secret_type,
                'keys': ', '.join(data.keys()) if data else '<none>',
                'data_count': len(data),
            })
        except Exception as e:
            logging.debug(f"Error processing Secret fields: {e}")

    @staticmethod
    def add_resourcequota_fields(processed_item: Dict[str, Any], item: Any):
        """Add ResourceQuota-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            # Get hard limits from spec
            hard_limits = spec.hard if spec and hasattr(spec, 'hard') else {}
            used_resources = status.used if status and hasattr(status, 'used') else {}

            processed_item.update({
                'hard_limits': len(hard_limits),
                'used_resources': len(used_resources),
                'resources': ', '.join(hard_limits.keys()) if hard_limits else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing ResourceQuota fields: {e}")

    @staticmethod
    def add_limitrange_fields(processed_item: Dict[str, Any], item: Any):
        """Add LimitRange-specific fields"""
        try:
            spec = item.spec
            limits = spec.limits if spec and hasattr(spec, 'limits') else []
            processed_item.update({
                'limits_count': len(limits),
                'types': ', '.join(sorted(set(limit.type for limit in limits if hasattr(limit, 'type')))) if limits else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing LimitRange fields: {e}")

    @staticmethod
    def add_hpa_fields(processed_item: Dict[str, Any], item: Any):
        """Add HorizontalPodAutoscaler-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            min_replicas = getattr(spec, 'min_replicas', 1) if spec else 1
            max_replicas = getattr(spec, 'max_replicas', 1) if spec else 1
            current_replicas = getattr(status, 'current_replicas', 0) if status else 0

            processed_item.update({
                'min_replicas': min_replicas,
                'max_replicas': max_replicas,
                'current_replicas': current_replicas,
                'target_ref': f"{spec.scale_target_ref.kind}/{spec.scale_target_ref.name}" if spec and hasattr(spec, 'scale_target_ref') else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing HPA fields: {e}")

    @staticmethod
    def add_pdb_fields(processed_item: Dict[str, Any], item: Any):
        """Add PodDisruptionBudget-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            min_available = getattr(spec, 'min_available', None) if spec else None
            max_unavailable = getattr(spec, 'max_unavailable', None) if spec else None

            processed_item.update({
                'min_available': str(min_available) if min_available is not None else '<none>',
                'max_unavailable': str(max_unavailable) if max_unavailable is not None else '<none>',
                'current_healthy': getattr(status, 'current_healthy', 0) if status else 0,
                'desired_healthy': getattr(status, 'desired_healthy', 0) if status else 0,
            })
        except Exception as e:
            logging.debug(f"Error processing PDB fields: {e}")

    @staticmethod
    def add_priorityclass_fields(processed_item: Dict[str, Any], item: Any):
        """Add PriorityClass-specific fields"""
        try:
            value = getattr(item, 'value', 0)
            global_default = getattr(item, 'global_default', False)
            description = getattr(item, 'description', '')

            processed_item.update({
                'value': value,
                'global_default': global_default,
                'description': description or '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing PriorityClass fields: {e}")

    @staticmethod
    def add_runtimeclass_fields(processed_item: Dict[str, Any], item: Any):
        """Add RuntimeClass-specific fields"""
        try:
            handler = getattr(item, 'handler', '')
            processed_item.update({
                'handler': handler or '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing RuntimeClass fields: {e}")

    @staticmethod
    def add_lease_fields(processed_item: Dict[str, Any], item: Any):
        """Add Lease-specific fields"""
        try:
            spec = item.spec
            holder_identity = getattr(spec, 'holder_identity', '') if spec else ''
            lease_duration = getattr(spec, 'lease_duration_seconds', 0) if spec else 0

            processed_item.update({
                'holder_identity': holder_identity or '<none>',
                'holder': holder_identity or '<none>',  # For compatibility with LeasesPage
                'lease_duration': f"{lease_duration}s" if lease_duration else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing Lease fields: {e}")

    @staticmethod
    def add_mutatingwebhook_fields(processed_item: Dict[str, Any], item: Any):
        """Add MutatingWebhookConfiguration-specific fields"""
        try:
            webhooks = getattr(item, 'webhooks', [])
            processed_item.update({
                'webhooks_count': len(webhooks),
                'webhooks': ', '.join([w.name for w in webhooks if hasattr(w, 'name')]) if webhooks else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing MutatingWebhookConfiguration fields: {e}")

    @staticmethod
    def add_validatingwebhook_fields(processed_item: Dict[str, Any], item: Any):
        """Add ValidatingWebhookConfiguration-specific fields"""
        try:
            webhooks = getattr(item, 'webhooks', [])
            processed_item.update({
                'webhooks_count': len(webhooks),
                'webhooks': ', '.join([w.name for w in webhooks if hasattr(w, 'name')]) if webhooks else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing ValidatingWebhookConfiguration fields: {e}")

    @staticmethod
    def add_serviceaccount_fields(processed_item: Dict[str, Any], item: Any):
        """Add ServiceAccount-specific fields"""
        try:
            secrets = getattr(item, 'secrets', []) or []
            image_pull_secrets = getattr(item, 'image_pull_secrets', []) or []

            processed_item.update({
                'secrets_count': len(secrets),
                'image_pull_secrets_count': len(image_pull_secrets),
                'automount_token': getattr(item, 'automount_service_account_token', True),
            })
        except Exception as e:
            logging.debug(f"Error processing ServiceAccount fields: {e}")

    @staticmethod
    def add_endpoints_fields(processed_item: Dict[str, Any], item: Any):
        """Add Endpoints-specific fields"""
        try:
            subsets = getattr(item, 'subsets', [])

            # Get addresses and ports more comprehensively
            all_addresses = []
            all_ports = []

            for subset in subsets:
                addresses = getattr(subset, 'addresses', []) or []
                ports = getattr(subset, 'ports', []) or []

                # Collect IP addresses
                for addr in addresses:
                    if hasattr(addr, 'ip') and addr.ip:
                        all_addresses.append(addr.ip)

                # Collect port information
                for port in ports:
                    port_info = f"{getattr(port, 'port', 'unknown')}"
                    if hasattr(port, 'protocol'):
                        port_info += f"/{port.protocol}"
                    if hasattr(port, 'name') and port.name:
                        port_info += f" ({port.name})"
                    all_ports.append(port_info)

            processed_item.update({
                'endpoints_count': len(all_addresses),
                'endpoints': ', '.join(all_addresses[:3]) + ('...' if len(all_addresses) > 3 else '') if all_addresses else '<none>',
                'ports': ', '.join(all_ports) if all_ports else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing Endpoints fields: {e}")

    @staticmethod
    def add_role_fields(processed_item: Dict[str, Any], item: Any):
        """Add Role/ClusterRole-specific fields"""
        try:
            rules = getattr(item, 'rules', []) or []
            processed_item.update({
                'rules_count': len(rules),
            })
        except Exception as e:
            logging.debug(f"Error processing Role fields: {e}")

    @staticmethod
    def add_rolebinding_fields(processed_item: Dict[str, Any], item: Any):
        """Add RoleBinding/ClusterRoleBinding-specific fields"""
        try:
            subjects = getattr(item, 'subjects', []) or []
            role_ref = getattr(item, 'role_ref', None)

            processed_item.update({
                'subjects_count': len(subjects),
                'role_ref': f"{role_ref.kind}/{role_ref.name}" if role_ref and hasattr(role_ref, 'kind') and hasattr(role_ref, 'name') else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing RoleBinding fields: {e}")

    @staticmethod
    def add_crd_fields(processed_item: Dict[str, Any], item: Any):
        """Add CustomResourceDefinition-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            group = getattr(spec, 'group', '') if spec else ''
            scope = getattr(spec, 'scope', 'Namespaced') if spec else 'Namespaced'

            processed_item.update({
                'group': group or '<none>',
                'scope': scope,
                'established': 'True' if status and getattr(status, 'conditions', None) and any(c.type == 'Established' and c.status == 'True' for c in status.conditions) else 'False',
            })
        except Exception as e:
            logging.debug(f"Error processing CRD fields: {e}")

    @staticmethod
    def format_capacity(raw_value: str) -> str:
        """Format Kubernetes capacity values to human-readable format"""
        if not raw_value:
            return ''

        if 'Ki' in raw_value:
            # Convert from Ki to GB
            ki_value = int(raw_value.replace('Ki', ''))
            gb_value = ki_value / (1024 * 1024)
            return f"{gb_value:.1f}GB"
        elif 'Gi' in raw_value:
            # Convert from Gi to GB
            gi_value = int(raw_value.replace('Gi', ''))
            return f"{gi_value}GB"
        else:
            return raw_value

    @staticmethod
    def process_node_conditions(conditions) -> tuple:
        """Process node conditions and return (status, conditions_text)"""
        node_status = 'Unknown'
        conditions_list = []

        if conditions:
            for condition in conditions:
                if condition.type == 'Ready':
                    if condition.status == 'True':
                        node_status = 'Ready'
                    elif condition.status == 'False':
                        node_status = 'NotReady'
                    else:
                        # 'Unknown' (kubelet stopped reporting / node unreachable)
                        # is distinct from a confirmed NotReady node.
                        node_status = 'Unknown'

                # Format condition for display: Type=Status
                condition_display = f"{condition.type}={condition.status}"

                # Add reason if available for non-True conditions
                if condition.status != 'True' and hasattr(condition, 'reason') and condition.reason:
                    condition_display += f" ({condition.reason})"

                conditions_list.append(condition_display)

        conditions_text = ", ".join(conditions_list) if conditions_list else "Unknown"
        return node_status, conditions_text

    @staticmethod
    def extract_node_roles(labels) -> list:
        """Extract node roles from Kubernetes labels"""
        roles = []
        if labels:
            for label_key in labels:
                if 'node-role.kubernetes.io/' in label_key:
                    role = label_key.replace('node-role.kubernetes.io/', '')
                    if role:
                        roles.append(role)
        return roles if roles else ['<none>']

