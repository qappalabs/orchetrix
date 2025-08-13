"""
Kubernetes Metrics Service - Handles cluster metrics calculation and processing
Split from kubernetes_client.py for better architecture
"""

import logging
from typing import Dict, Any, Optional
from functools import lru_cache
from kubernetes.client.rest import ApiException


class KubernetesMetricsService:
    """Service for calculating and managing Kubernetes cluster metrics"""
    
    def __init__(self, api_service, cache_service):
        self.api_service = api_service
        self.cache_service = cache_service
        logging.debug("KubernetesMetricsService initialized")
    
    def get_cluster_metrics(self, cluster_name: str) -> Optional[Dict[str, Any]]:
        """Get cluster metrics with caching"""
        # Check cache first
        cached_metrics = self.cache_service.get_cached_resources('metrics', f'cluster_{cluster_name}')
        if cached_metrics:
            logging.debug(f"Using cached metrics for {cluster_name}")
            return cached_metrics
        
        try:
            # Calculate fresh metrics
            metrics = self._calculate_cluster_metrics()
            
            # Cache the results
            self.cache_service.cache_resources('metrics', f'cluster_{cluster_name}', metrics)
            
            logging.info(f"Calculated fresh metrics for {cluster_name}")
            return metrics
            
        except Exception as e:
            logging.error(f"Error getting cluster metrics: {e}")
            return self._get_default_metrics()
    
    def _calculate_cluster_metrics(self) -> Dict[str, Any]:
        """Calculate cluster metrics efficiently with real data"""
        try:
            # Get nodes with their actual resource information
            nodes_list = self.api_service.v1.list_node()
            
            # Initialize totals
            cpu_total_cores = 0
            memory_total_bytes = 0
            pods_capacity_total = 0
            cpu_allocatable_cores = 0
            memory_allocatable_bytes = 0
            
            for node in nodes_list.items:
                if node.status and node.status.capacity:
                    # CPU capacity and allocatable
                    cpu_capacity = self._parse_cpu_value(node.status.capacity.get('cpu', '0'))
                    cpu_total_cores += cpu_capacity
                    
                    if node.status.allocatable:
                        cpu_allocatable = self._parse_cpu_value(node.status.allocatable.get('cpu', '0'))
                        cpu_allocatable_cores += cpu_allocatable
                    else:
                        cpu_allocatable_cores += cpu_capacity
                    
                    # Memory capacity and allocatable
                    memory_capacity = self._parse_memory_value(node.status.capacity.get('memory', '0Ki'))
                    memory_total_bytes += memory_capacity
                    
                    if node.status.allocatable:
                        memory_allocatable = self._parse_memory_value(node.status.allocatable.get('memory', '0Ki'))
                        memory_allocatable_bytes += memory_allocatable
                    else:
                        memory_allocatable_bytes += memory_capacity
                    
                    # Pod capacity
                    pods_capacity_total += int(node.status.capacity.get('pods', '110'))
            
            # Get actual pod resource usage
            pods_list = self.api_service.v1.list_pod_for_all_namespaces()
            
            # Calculate actual resource requests and usage
            cpu_requests_total = 0
            memory_requests_total = 0
            cpu_limits_total = 0
            memory_limits_total = 0
            running_pods_count = 0
            
            for pod in pods_list.items:
                # Only count running pods
                if pod.status and pod.status.phase == "Running":
                    running_pods_count += 1
                    
                    if pod.spec and pod.spec.containers:
                        for container in pod.spec.containers:
                            if container.resources:
                                # CPU requests
                                if container.resources.requests:
                                    cpu_request = container.resources.requests.get('cpu', '0')
                                    cpu_requests_total += self._parse_cpu_value(cpu_request)
                                    
                                    memory_request = container.resources.requests.get('memory', '0')
                                    memory_requests_total += self._parse_memory_value(memory_request)
                                
                                # CPU limits
                                if container.resources.limits:
                                    cpu_limit = container.resources.limits.get('cpu', '0')
                                    cpu_limits_total += self._parse_cpu_value(cpu_limit)
                                    
                                    memory_limit = container.resources.limits.get('memory', '0')
                                    memory_limits_total += self._parse_memory_value(memory_limit)
            
            # Calculate usage percentages based on requests vs capacity
            cpu_usage_percent = (cpu_requests_total / cpu_total_cores * 100) if cpu_total_cores > 0 else 0
            memory_usage_percent = (memory_requests_total / memory_total_bytes * 100) if memory_total_bytes > 0 else 0
            pods_usage_percent = (running_pods_count / pods_capacity_total * 100) if pods_capacity_total > 0 else 0
            
            # Ensure values are reasonable
            cpu_usage_percent = min(cpu_usage_percent, 100)
            memory_usage_percent = min(memory_usage_percent, 100)
            pods_usage_percent = min(pods_usage_percent, 100)
            
            metrics = {
                "cpu": {
                    "usage": round(cpu_usage_percent, 2),
                    "requests": round(cpu_requests_total, 2),
                    "limits": round(cpu_limits_total, 2),
                    "allocatable": round(cpu_allocatable_cores, 2),
                    "capacity": round(cpu_total_cores, 2)
                },
                "memory": {
                    "usage": round(memory_usage_percent, 2),
                    "requests": round(memory_requests_total / (1024**2), 2),  # Convert to MB
                    "limits": round(memory_limits_total / (1024**2), 2),      # Convert to MB
                    "allocatable": round(memory_allocatable_bytes / (1024**2), 2),  # Convert to MB
                    "capacity": round(memory_total_bytes / (1024**2), 2)     # Convert to MB
                },
                "pods": {
                    "usage": round(pods_usage_percent, 2),
                    "count": running_pods_count,
                    "capacity": pods_capacity_total
                }
            }
            
            logging.info(f"Calculated real cluster metrics: CPU {cpu_usage_percent:.1f}%, Memory {memory_usage_percent:.1f}%, Pods {pods_usage_percent:.1f}%")
            return metrics
            
        except Exception as e:
            logging.error(f"Error calculating cluster metrics: {e}")
            return self._get_default_metrics()
    
    @lru_cache(maxsize=128)
    def _parse_cpu_value(self, cpu_str: str) -> float:
        """Parse CPU values (cores, millicores) to cores with caching"""
        if not cpu_str or not isinstance(cpu_str, str):
            return 0.0
        
        cpu_str = cpu_str.strip()
        
        # Handle millicores (e.g., "500m" = 0.5 cores)
        if cpu_str.endswith('m'):
            try:
                return float(cpu_str[:-1]) / 1000.0
            except ValueError:
                return 0.0
        
        # Handle cores (e.g., "2" = 2 cores)
        try:
            return float(cpu_str)
        except ValueError:
            return 0.0
    
    @lru_cache(maxsize=128)
    def _parse_memory_value(self, memory_str: str) -> int:
        """Parse memory values to bytes with caching"""
        if not memory_str or not isinstance(memory_str, str):
            return 0
        
        memory_str = memory_str.strip()
        
        # Memory unit multipliers
        multipliers = {
            'Ki': 1024,
            'Mi': 1024**2,
            'Gi': 1024**3,
            'Ti': 1024**4,
            'K': 1000,
            'M': 1000**2,
            'G': 1000**3,
            'T': 1000**4
        }
        
        # Check for unit suffixes
        for suffix, multiplier in multipliers.items():
            if memory_str.endswith(suffix):
                try:
                    value = float(memory_str[:-len(suffix)])
                    return int(value * multiplier)
                except ValueError:
                    return 0
        
        # Handle plain numbers (assume bytes)
        try:
            return int(float(memory_str))
        except ValueError:
            return 0
    
    def _get_default_metrics(self) -> Dict[str, Any]:
        """Return default metrics when calculation fails"""
        return {
            "cpu": {"usage": 0, "requests": 0, "limits": 0, "allocatable": 0, "capacity": 1},
            "memory": {"usage": 0, "requests": 0, "limits": 0, "allocatable": 0, "capacity": 1024},
            "pods": {"usage": 0, "count": 0, "capacity": 100}
        }
    
    def get_node_metrics(self, node_name: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific node"""
        try:
            node = self.api_service.v1.read_node(name=node_name)
            
            if not node.status or not node.status.capacity:
                return None
            
            # Parse node capacity and allocatable resources
            cpu_capacity = self._parse_cpu_value(node.status.capacity.get('cpu', '0'))
            memory_capacity = self._parse_memory_value(node.status.capacity.get('memory', '0Ki'))
            pods_capacity = int(node.status.capacity.get('pods', '110'))
            
            cpu_allocatable = cpu_capacity
            memory_allocatable = memory_capacity
            
            if node.status.allocatable:
                cpu_allocatable = self._parse_cpu_value(node.status.allocatable.get('cpu', '0'))
                memory_allocatable = self._parse_memory_value(node.status.allocatable.get('memory', '0Ki'))
            
            # Get pods running on this node
            pods_list = self.api_service.v1.list_pod_for_all_namespaces(
                field_selector=f"spec.nodeName={node_name}"
            )
            
            cpu_requests = 0
            memory_requests = 0
            running_pods = 0
            
            for pod in pods_list.items:
                if pod.status and pod.status.phase == "Running":
                    running_pods += 1
                    
                    if pod.spec and pod.spec.containers:
                        for container in pod.spec.containers:
                            if container.resources and container.resources.requests:
                                cpu_requests += self._parse_cpu_value(container.resources.requests.get('cpu', '0'))
                                memory_requests += self._parse_memory_value(container.resources.requests.get('memory', '0'))
            
            # Calculate usage percentages
            cpu_usage_percent = (cpu_requests / cpu_capacity * 100) if cpu_capacity > 0 else 0
            memory_usage_percent = (memory_requests / memory_capacity * 100) if memory_capacity > 0 else 0
            pods_usage_percent = (running_pods / pods_capacity * 100) if pods_capacity > 0 else 0
            
            return {
                "name": node_name,
                "cpu": {
                    "usage": round(cpu_usage_percent, 2),
                    "requests": round(cpu_requests, 2),
                    "capacity": round(cpu_capacity, 2),
                    "allocatable": round(cpu_allocatable, 2)
                },
                "memory": {
                    "usage": round(memory_usage_percent, 2),
                    "requests": round(memory_requests / (1024**2), 2),  # Convert to MB
                    "capacity": round(memory_capacity / (1024**2), 2),
                    "allocatable": round(memory_allocatable / (1024**2), 2)
                },
                "pods": {
                    "usage": round(pods_usage_percent, 2),
                    "count": running_pods,
                    "capacity": pods_capacity
                }
            }
            
        except ApiException as e:
            logging.error(f"API error getting node metrics for {node_name}: {e}")
            return None
        except Exception as e:
            logging.error(f"Error getting node metrics for {node_name}: {e}")
            return None
    
    def clear_cache(self):
        """Clear all cached parsing results"""
        self._parse_cpu_value.cache_clear()
        self._parse_memory_value.cache_clear()
        logging.debug("Cleared metrics parsing cache")
    
    def cleanup(self):
        """Cleanup metrics service resources"""
        logging.debug("Cleaning up KubernetesMetricsService")
        self.clear_cache()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            if hasattr(self, '_parse_cpu_value'):
                self.cleanup()
        except Exception as e:
            logging.error(f"Error in KubernetesMetricsService destructor: {e}")


# Factory function
def create_kubernetes_metrics_service(api_service, cache_service) -> KubernetesMetricsService:
    """Create a new Kubernetes metrics service instance"""
    return KubernetesMetricsService(api_service, cache_service)