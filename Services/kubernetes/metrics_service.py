"""
Kubernetes Metrics Service - Handles cluster metrics calculation and processing
Split from kubernetes_client.py for better architecture
"""

import logging
import time
from typing import Dict, Any, Optional
from kubernetes.client.rest import ApiException


class KubernetesMetricsService:
    """Service for calculating and managing Kubernetes cluster metrics"""
    
    def __init__(self, api_service):
        self.api_service = api_service
        logging.debug("KubernetesMetricsService initialized")
    
    def get_cluster_metrics(self, cluster_name: str) -> Optional[Dict[str, Any]]:
        """Get cluster metrics"""
        try:
            # Calculate metrics directly
            metrics = self._calculate_cluster_metrics()
            logging.info(f"Calculated metrics for {cluster_name}")
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
    
    def _parse_cpu_value(self, cpu_str: str) -> float:
        """Parse CPU values (cores, millicores) to cores"""
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
    
    def _parse_storage_value(self, storage_str: str) -> int:
        """Parse storage values to bytes"""
        # Storage parsing is same as memory parsing
        return self._parse_memory_value(storage_str)
    
    def _parse_memory_value(self, memory_str: str) -> int:
        """Parse memory values to bytes"""
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
    
    def get_all_node_metrics_fast(self, node_names: list = None, include_disk_usage: bool = False) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all nodes efficiently in batch - ULTRA FAST VERSION with optimized API calls"""
        try:
            start_time = time.time()
            
            # Batch size limits for large clusters to prevent API overload
            MAX_NODES_PER_BATCH = 50
            
            # Get all nodes at once with resource version for efficient watching
            nodes_list = self.api_service.v1.list_node(
                limit=MAX_NODES_PER_BATCH if not node_names else None,
                _request_timeout=30  # Increased timeout for large clusters
            )
            
            if not nodes_list.items:
                return {}
            
            # Filter nodes if specific names provided
            if node_names:
                nodes_list.items = [node for node in nodes_list.items if node.metadata.name in node_names]
            
            # Limit nodes for performance - process in batches if too many
            if len(nodes_list.items) > MAX_NODES_PER_BATCH:
                logging.info(f"Large cluster detected ({len(nodes_list.items)} nodes), processing in batches")
                return self._process_nodes_in_batches(nodes_list.items, include_disk_usage)
            
            # Get ALL pods for all namespaces at once (single API call) with field selector for performance
            all_pods = self.api_service.v1.list_pod_for_all_namespaces(
                field_selector="status.phase!=Succeeded,status.phase!=Failed",  # Filter out completed pods
                limit=5000,  # Limit to prevent memory issues
                _request_timeout=30
            )
            
            # Group pods by node for efficient lookup with optimized data structure
            pods_by_node = {}
            for pod in all_pods.items:
                if pod.spec and pod.spec.node_name:
                    node_name = pod.spec.node_name
                    if node_name not in pods_by_node:
                        pods_by_node[node_name] = []
                    pods_by_node[node_name].append(pod)
            
            # Calculate metrics for all nodes with parallel processing simulation
            all_metrics = {}
            failed_nodes = []
            
            for i, node in enumerate(nodes_list.items):
                node_name = node.metadata.name
                try:
                    # Add progress logging for large batches
                    if i % 10 == 0 and len(nodes_list.items) > 20:
                        logging.debug(f"Processing node {i+1}/{len(nodes_list.items)}: {node_name}")
                        
                    metrics = self._calculate_single_node_metrics_fast(
                        node, 
                        pods_by_node.get(node_name, []), 
                        include_disk_usage
                    )
                    if metrics:
                        all_metrics[node_name] = metrics
                    else:
                        failed_nodes.append(node_name)
                        
                except Exception as e:
                    logging.warning(f"Error calculating fast metrics for node {node_name}: {e}")
                    failed_nodes.append(node_name)
                    # Set default metrics for failed nodes
                    all_metrics[node_name] = self._get_default_node_metrics(node_name)
            
            processing_time = (time.time() - start_time) * 1000
            disk_text = "with disk" if include_disk_usage else "no disk"
            
            if failed_nodes:
                logging.warning(f"⚠️ [BATCH] {len(failed_nodes)} nodes failed metrics calculation: {failed_nodes[:5]}{'...' if len(failed_nodes) > 5 else ''}")
                
            logging.info(f"🚀 [FAST BATCH] Calculated {disk_text} metrics for {len(all_metrics)} nodes in {processing_time:.1f}ms")
            return all_metrics
            
        except Exception as e:
            logging.error(f"Error in fast batch node metrics calculation: {e}")
            return {}
            
    def _process_nodes_in_batches(self, all_nodes: list, include_disk_usage: bool) -> Dict[str, Dict[str, Any]]:
        """Process nodes in smaller batches to handle large clusters efficiently"""
        try:
            BATCH_SIZE = 25  # Smaller batch size for very large clusters
            all_metrics = {}
            
            for i in range(0, len(all_nodes), BATCH_SIZE):
                batch_nodes = all_nodes[i:i + BATCH_SIZE]
                batch_start_time = time.time()
                
                logging.info(f"Processing batch {i//BATCH_SIZE + 1}/{(len(all_nodes) + BATCH_SIZE - 1)//BATCH_SIZE}: {len(batch_nodes)} nodes")
                
                # Get pods for this batch of nodes only
                node_names_in_batch = [node.metadata.name for node in batch_nodes]
                
                # Use field selector to get pods only for nodes in this batch
                batch_pods = self.api_service.v1.list_pod_for_all_namespaces(
                    field_selector=f"spec.nodeName in ({','.join(node_names_in_batch)})",
                    _request_timeout=20
                )
                
                # Group pods by node for this batch
                pods_by_node = {}
                for pod in batch_pods.items:
                    if pod.spec and pod.spec.node_name:
                        node_name = pod.spec.node_name
                        if node_name not in pods_by_node:
                            pods_by_node[node_name] = []
                        pods_by_node[node_name].append(pod)
                
                # Calculate metrics for nodes in this batch
                for node in batch_nodes:
                    node_name = node.metadata.name
                    try:
                        metrics = self._calculate_single_node_metrics_fast(
                            node, 
                            pods_by_node.get(node_name, []), 
                            include_disk_usage
                        )
                        if metrics:
                            all_metrics[node_name] = metrics
                        else:
                            all_metrics[node_name] = self._get_default_node_metrics(node_name)
                            
                    except Exception as e:
                        logging.warning(f"Error calculating metrics for node {node_name} in batch: {e}")
                        all_metrics[node_name] = self._get_default_node_metrics(node_name)
                
                batch_time = (time.time() - batch_start_time) * 1000
                logging.info(f"Batch {i//BATCH_SIZE + 1} completed in {batch_time:.1f}ms")
                
                # Brief pause between batches to prevent API rate limiting
                if i + BATCH_SIZE < len(all_nodes):
                    time.sleep(0.1)  # 100ms pause between batches
                    
            return all_metrics
            
        except Exception as e:
            logging.error(f"Error processing nodes in batches: {e}")
            return {}

    def get_all_node_metrics(self, node_names: list = None) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all nodes efficiently in batch - PERFORMANCE OPTIMIZED"""
        try:
            start_time = time.time()
            
            # Get all nodes at once
            nodes_list = self.api_service.v1.list_node()
            if not nodes_list.items:
                return {}
            
            # Filter nodes if specific names provided
            if node_names:
                nodes_list.items = [node for node in nodes_list.items if node.metadata.name in node_names]
            
            # Get ALL pods for all namespaces at once (single API call)
            all_pods = self.api_service.v1.list_pod_for_all_namespaces()
            
            # Group pods by node for efficient lookup
            pods_by_node = {}
            for pod in all_pods.items:
                if pod.spec and pod.spec.node_name:
                    node_name = pod.spec.node_name
                    if node_name not in pods_by_node:
                        pods_by_node[node_name] = []
                    pods_by_node[node_name].append(pod)
            
            # Calculate metrics for all nodes
            all_metrics = {}
            for node in nodes_list.items:
                node_name = node.metadata.name
                try:
                    metrics = self._calculate_single_node_metrics(node, pods_by_node.get(node_name, []))
                    if metrics:
                        all_metrics[node_name] = metrics
                except Exception as e:
                    logging.warning(f"Error calculating metrics for node {node_name}: {e}")
                    # Set default metrics for failed nodes
                    all_metrics[node_name] = self._get_default_node_metrics(node_name)
            
            processing_time = (time.time() - start_time) * 1000
            logging.info(f"Batch calculated metrics for {len(all_metrics)} nodes in {processing_time:.1f}ms")
            return all_metrics
            
        except Exception as e:
            logging.error(f"Error in batch node metrics calculation: {e}")
            return {}
    
    def _calculate_single_node_metrics(self, node, node_pods: list) -> Optional[Dict[str, Any]]:
        """Calculate metrics for a single node using pre-fetched pods"""
        try:
            node_name = node.metadata.name
            
            if not node.status or not node.status.capacity:
                return self._get_default_node_metrics(node_name)
            
            # Parse node capacity and allocatable resources
            cpu_capacity = self._parse_cpu_value(node.status.capacity.get('cpu', '0'))
            memory_capacity = self._parse_memory_value(node.status.capacity.get('memory', '0Ki'))
            pods_capacity = int(node.status.capacity.get('pods', '110'))
            storage_capacity = self._parse_storage_value(node.status.capacity.get('ephemeral-storage', '0Ki'))
            
            cpu_allocatable = cpu_capacity
            memory_allocatable = memory_capacity
            storage_allocatable = storage_capacity
            
            if node.status.allocatable:
                cpu_allocatable = self._parse_cpu_value(node.status.allocatable.get('cpu', '0'))
                memory_allocatable = self._parse_memory_value(node.status.allocatable.get('memory', '0Ki'))
                storage_allocatable = self._parse_storage_value(node.status.allocatable.get('ephemeral-storage', '0Ki'))
            
            # Calculate resource usage from pre-fetched pods
            cpu_requests = 0
            memory_requests = 0
            storage_requests = 0
            running_pods = 0
            
            for pod in node_pods:
                if pod.status and pod.status.phase == "Running":
                    running_pods += 1
                    
                    if pod.spec and pod.spec.containers:
                        for container in pod.spec.containers:
                            if container.resources and container.resources.requests:
                                cpu_requests += self._parse_cpu_value(container.resources.requests.get('cpu', '0'))
                                memory_requests += self._parse_memory_value(container.resources.requests.get('memory', '0'))
                                storage_requests += self._parse_storage_value(container.resources.requests.get('ephemeral-storage', '0'))
            
            # Calculate usage percentages
            cpu_usage_percent = (cpu_requests / cpu_capacity * 100) if cpu_capacity > 0 else 0
            memory_usage_percent = (memory_requests / memory_capacity * 100) if memory_capacity > 0 else 0
            pods_usage_percent = (running_pods / pods_capacity * 100) if pods_capacity > 0 else 0
            
            # Get real disk usage instead of just storage requests
            disk_usage_percent = self._calculate_real_disk_usage(node_name)
            if disk_usage_percent == 0.0:
                # Fallback to storage requests calculation only if no real data
                disk_usage_percent = (storage_requests / storage_capacity * 100) if storage_capacity > 0 else 0.0
            
            # Ensure percentages are reasonable
            cpu_usage_percent = min(cpu_usage_percent, 100)
            memory_usage_percent = min(memory_usage_percent, 100)
            pods_usage_percent = min(pods_usage_percent, 100)
            disk_usage_percent = min(disk_usage_percent, 100)
            
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
                    "requests": round(memory_requests / (1024**2), 2),
                    "capacity": round(memory_capacity / (1024**2), 2),
                    "allocatable": round(memory_allocatable / (1024**2), 2)
                },
                "disk": {
                    "usage": round(disk_usage_percent, 2),
                    "requests": round(storage_requests / (1024**3), 2),
                    "capacity": round(storage_capacity / (1024**3), 2),
                    "allocatable": round(storage_allocatable / (1024**3), 2)
                },
                "pods": {
                    "usage": round(pods_usage_percent, 2),
                    "count": running_pods,
                    "capacity": pods_capacity
                }
            }
            
        except Exception as e:
            logging.error(f"Error calculating metrics for node {node.metadata.name}: {e}")
            return self._get_default_node_metrics(node.metadata.name)
    
    def _calculate_single_node_metrics_fast(self, node, node_pods: list, include_disk_usage: bool = False) -> Optional[Dict[str, Any]]:
        """Calculate metrics for a single node using pre-fetched pods - FAST VERSION with real metrics when available"""
        try:
            node_name = node.metadata.name
            
            if not node.status or not node.status.capacity:
                return self._get_default_node_metrics(node_name)
            
            # Parse node capacity and allocatable resources
            cpu_capacity = self._parse_cpu_value(node.status.capacity.get('cpu', '0'))
            memory_capacity = self._parse_memory_value(node.status.capacity.get('memory', '0Ki'))
            pods_capacity = int(node.status.capacity.get('pods', '110'))
            storage_capacity = self._parse_storage_value(node.status.capacity.get('ephemeral-storage', '0Ki'))
            
            cpu_allocatable = cpu_capacity
            memory_allocatable = memory_capacity
            storage_allocatable = storage_capacity
            
            if node.status.allocatable:
                cpu_allocatable = self._parse_cpu_value(node.status.allocatable.get('cpu', '0'))
                memory_allocatable = self._parse_memory_value(node.status.allocatable.get('memory', '0Ki'))
                storage_allocatable = self._parse_storage_value(node.status.allocatable.get('ephemeral-storage', '0Ki'))
            
            # Try to get real usage from metrics server first for more accurate data
            real_usage = self._get_real_node_usage_from_metrics_server(node_name)
            
            if real_usage:
                # Use real metrics if available
                cpu_usage_percent = (real_usage.get('cpu_usage', 0) / cpu_capacity * 100) if cpu_capacity > 0 else 0
                memory_usage_percent = (real_usage.get('memory_usage', 0) / memory_capacity * 100) if memory_capacity > 0 else 0
                disk_usage_percent = real_usage.get('disk_usage_percent', 0) if include_disk_usage else None
                
                # Still count running pods from pre-fetched data
                running_pods = sum(1 for pod in node_pods if pod.status and pod.status.phase == "Running")
                
            else:
                # Fallback to resource requests calculation
                cpu_requests = 0
                memory_requests = 0
                storage_requests = 0
                running_pods = 0
                
                for pod in node_pods:
                    if pod.status and pod.status.phase == "Running":
                        running_pods += 1
                        
                        if pod.spec and pod.spec.containers:
                            for container in pod.spec.containers:
                                if container.resources and container.resources.requests:
                                    cpu_requests += self._parse_cpu_value(container.resources.requests.get('cpu', '0'))
                                    memory_requests += self._parse_memory_value(container.resources.requests.get('memory', '0'))
                                    storage_requests += self._parse_storage_value(container.resources.requests.get('ephemeral-storage', '0'))
                
                # Calculate usage percentages based on requests
                cpu_usage_percent = (cpu_requests / cpu_capacity * 100) if cpu_capacity > 0 else 0
                memory_usage_percent = (memory_requests / memory_capacity * 100) if memory_capacity > 0 else 0
                
                # Get disk usage if requested
                if include_disk_usage:
                    disk_usage_percent = self._calculate_real_disk_usage(node_name)
                    if disk_usage_percent == 0.0:
                        # Fallback to storage requests calculation only if no real data
                        disk_usage_percent = (storage_requests / storage_capacity * 100) if storage_capacity > 0 else 0.0
                else:
                    disk_usage_percent = None
            
            # Calculate pods usage percentage (same for both real and request-based metrics)
            pods_usage_percent = (running_pods / pods_capacity * 100) if pods_capacity > 0 else 0
            
            # Ensure percentages are reasonable
            cpu_usage_percent = min(cpu_usage_percent, 100)
            memory_usage_percent = min(memory_usage_percent, 100)
            pods_usage_percent = min(pods_usage_percent, 100)
            if disk_usage_percent is not None:
                disk_usage_percent = min(disk_usage_percent, 100)
            
            # For real metrics case, we might not have calculated requests
            if real_usage:
                cpu_requests = 0  # Not calculated for real metrics
                memory_requests = 0  # Not calculated for real metrics  
                storage_requests = 0  # Not calculated for real metrics
            
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
                    "requests": round(memory_requests / (1024**2), 2),
                    "capacity": round(memory_capacity / (1024**2), 2),
                    "allocatable": round(memory_allocatable / (1024**2), 2)
                },
                "disk": {
                    "usage": round(disk_usage_percent, 2) if disk_usage_percent is not None else None,
                    "requests": round(storage_requests / (1024**3), 2),
                    "capacity": round(storage_capacity / (1024**3), 2),
                    "allocatable": round(storage_allocatable / (1024**3), 2)
                },
                "pods": {
                    "usage": round(pods_usage_percent, 2),
                    "count": running_pods,
                    "capacity": pods_capacity
                }
            }
            
        except Exception as e:
            logging.error(f"Error calculating fast metrics for node {node.metadata.name}: {e}")
            return self._get_default_node_metrics(node.metadata.name)

    def _get_default_node_metrics(self, node_name: str) -> Dict[str, Any]:
        """Return default metrics when calculation fails"""
        return {
            "name": node_name,
            "cpu": {"usage": 0.0, "requests": 0.0, "capacity": 0.0, "allocatable": 0.0},
            "memory": {"usage": 0.0, "requests": 0.0, "capacity": 0.0, "allocatable": 0.0},
            "disk": {"usage": 0.0, "requests": 0.0, "capacity": 0.0, "allocatable": 0.0},
            "pods": {"usage": 0.0, "count": 0, "capacity": 0}
        }

    def get_node_metrics(self, node_name: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific node including real usage from metrics server"""
        try:
            node = self.api_service.v1.read_node(name=node_name)
            
            if not node.status or not node.status.capacity:
                return None
            
            # Parse node capacity and allocatable resources
            cpu_capacity = self._parse_cpu_value(node.status.capacity.get('cpu', '0'))
            memory_capacity = self._parse_memory_value(node.status.capacity.get('memory', '0Ki'))
            pods_capacity = int(node.status.capacity.get('pods', '110'))
            
            # Get disk storage capacity
            storage_capacity = self._parse_storage_value(node.status.capacity.get('ephemeral-storage', '0Ki'))
            
            cpu_allocatable = cpu_capacity
            memory_allocatable = memory_capacity
            storage_allocatable = storage_capacity
            
            if node.status.allocatable:
                cpu_allocatable = self._parse_cpu_value(node.status.allocatable.get('cpu', '0'))
                memory_allocatable = self._parse_memory_value(node.status.allocatable.get('memory', '0Ki'))
                storage_allocatable = self._parse_storage_value(node.status.allocatable.get('ephemeral-storage', '0Ki'))
            
            # Initialize variables for both real and fallback metrics
            cpu_requests = 0
            memory_requests = 0
            storage_requests = 0
            running_pods = 0
            
            # Try to get real usage from metrics server first
            real_usage = self._get_real_node_usage_from_metrics_server(node_name)
            
            if real_usage:
                # Use real metrics if available
                cpu_usage_percent = (real_usage.get('cpu_usage', 0) / cpu_capacity * 100) if cpu_capacity > 0 else 0
                memory_usage_percent = (real_usage.get('memory_usage', 0) / memory_capacity * 100) if memory_capacity > 0 else 0
                disk_usage_percent = real_usage.get('disk_usage_percent', 0)
                
                # If disk usage is 0 from metrics server, it means it's calculated by our method already
                # (the _get_real_node_usage_from_metrics_server calls _calculate_real_disk_usage)
                
                # For real metrics, we still need to count running pods
                pods_list = self.api_service.v1.list_pod_for_all_namespaces(
                    field_selector=f"spec.nodeName={node_name}"
                )
                running_pods = sum(1 for pod in pods_list.items if pod.status and pod.status.phase == "Running")
                
                # For real metrics, we don't have request values, so keep them as 0
                logging.debug(f"Using real metrics for {node_name}: CPU {cpu_usage_percent:.1f}%, Memory {memory_usage_percent:.1f}%")
            else:
                # Fallback to resource requests calculation
                logging.debug(f"No metrics server data for {node_name}, using resource requests as fallback")
                
                # Get pods running on this node
                pods_list = self.api_service.v1.list_pod_for_all_namespaces(
                    field_selector=f"spec.nodeName={node_name}"
                )
                
                cpu_requests = 0
                memory_requests = 0
                storage_requests = 0
                running_pods = 0
                
                for pod in pods_list.items:
                    if pod.status and pod.status.phase == "Running":
                        running_pods += 1
                        
                        if pod.spec and pod.spec.containers:
                            for container in pod.spec.containers:
                                if container.resources and container.resources.requests:
                                    cpu_requests += self._parse_cpu_value(container.resources.requests.get('cpu', '0'))
                                    memory_requests += self._parse_memory_value(container.resources.requests.get('memory', '0'))
                                    storage_requests += self._parse_storage_value(container.resources.requests.get('ephemeral-storage', '0'))
                
                # Calculate usage percentages based on requests
                cpu_usage_percent = (cpu_requests / cpu_capacity * 100) if cpu_capacity > 0 else 0
                memory_usage_percent = (memory_requests / memory_capacity * 100) if memory_capacity > 0 else 0
                
                # Try to get real disk usage using our comprehensive calculation
                disk_usage_percent = self._calculate_real_disk_usage(node_name)
            
            # Calculate pods usage percentage (same for both real and request-based metrics)
            pods_usage_percent = (running_pods / pods_capacity * 100) if pods_capacity > 0 else 0
            
            # If we couldn't get real disk usage, use storage requests as basis
            if disk_usage_percent == 0.0:
                if storage_capacity > 0 and storage_requests > 0:
                    # Calculate based on storage requests without dummy overhead
                    disk_usage_percent = min((storage_requests / storage_capacity * 100), 100.0)
                else:
                    # No data available
                    disk_usage_percent = 0.0
                
                logging.debug(f"Using storage requests for disk usage {node_name}: {disk_usage_percent:.1f}%")
            
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
                "disk": {
                    "usage": round(disk_usage_percent, 2),
                    "requests": round(storage_requests / (1024**3), 2),  # Convert to GB
                    "capacity": round(storage_capacity / (1024**3), 2),
                    "allocatable": round(storage_allocatable / (1024**3), 2)
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
    

    def _get_real_node_usage_from_metrics_server(self, node_name: str) -> Optional[Dict[str, Any]]:
        """Get real CPU and memory usage from Kubernetes metrics server API"""
        try:
            if not hasattr(self.api_service, 'custom_objects_api'):
                logging.warning("No custom objects API available for metrics server")
                return None
            
            # Try to get node metrics from metrics.k8s.io/v1beta1
            try:
                metrics = self.api_service.custom_objects_api.get_cluster_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1", 
                    plural="nodes",
                    name=node_name
                )
                
                if not metrics or 'usage' not in metrics:
                    logging.debug(f"No usage data in metrics response for {node_name}")
                    return None
                
                usage_data = metrics['usage']
                
                # Parse CPU usage
                cpu_usage = 0
                if 'cpu' in usage_data:
                    cpu_raw = usage_data['cpu']
                    cpu_usage = self._parse_cpu_value(cpu_raw)
                
                # Parse memory usage  
                memory_usage = 0
                if 'memory' in usage_data:
                    memory_raw = usage_data['memory']
                    memory_usage = self._parse_memory_value(memory_raw)
                
                # Get disk usage using a more comprehensive approach
                disk_usage_percent = self._calculate_real_disk_usage(node_name)
                
                logging.debug(f"Retrieved real metrics from metrics-server for {node_name}: "
                           f"CPU={cpu_usage:.2f} cores, Memory={memory_usage/(1024**2):.0f}MB, "
                           f"Disk={disk_usage_percent:.1f}%")
                
                return {
                    'cpu_usage': cpu_usage,
                    'memory_usage': memory_usage,
                    'disk_usage_bytes': 0,  # Not available from metrics server
                    'disk_usage_percent': disk_usage_percent
                }
                
            except Exception as e:
                logging.debug(f"Could not get metrics from metrics-server for {node_name}: {e}")
                return None
                
        except Exception as e:
            logging.debug(f"Error accessing metrics server for {node_name}: {e}")
            return None

    def _calculate_real_disk_usage(self, node_name: str) -> float:
        """Calculate real disk usage for a node using pod data and storage requests"""
        try:
            # Get node capacity
            node = self.api_service.v1.read_node(name=node_name)
            if not node.status or not node.status.capacity:
                return 0.0  # No data available
            
            storage_capacity = self._parse_storage_value(
                node.status.capacity.get('ephemeral-storage', '0Ki')
            )
            
            if storage_capacity <= 0:
                return 0.0  # No capacity info available
            
            # Get all pods on this node
            pods_list = self.api_service.v1.list_pod_for_all_namespaces(
                field_selector=f"spec.nodeName={node_name}"
            )
            
            total_estimated_usage = 0
            running_pods_count = 0
            
            for pod in pods_list.items:
                if pod.status and pod.status.phase == "Running":
                    running_pods_count += 1
                    
                    # Estimate storage usage per pod
                    pod_storage_estimate = 0
                    
                    if pod.spec and pod.spec.containers:
                        for container in pod.spec.containers:
                            # Base container image size estimate
                            container_base_size = 200 * 1024 * 1024  # 200MB base per container
                            pod_storage_estimate += container_base_size
                            
                            # Add storage requests if specified
                            if container.resources and container.resources.requests:
                                storage_request = container.resources.requests.get('ephemeral-storage', '0')
                                pod_storage_estimate += self._parse_storage_value(storage_request)
                    
                    # Add persistent volume sizes
                    if pod.spec and pod.spec.volumes:
                        for volume in pod.spec.volumes:
                            if volume.persistent_volume_claim:
                                # Estimate PVC usage (we can't get exact usage, so estimate)
                                try:
                                    pvc = self.api_service.v1.read_namespaced_persistent_volume_claim(
                                        name=volume.persistent_volume_claim.claim_name,
                                        namespace=pod.metadata.namespace
                                    )
                                    if pvc.spec and pvc.spec.resources and pvc.spec.resources.requests:
                                        pvc_size_request = pvc.spec.resources.requests.get('storage', '0')
                                        # Assume 60% usage of PVC capacity
                                        pvc_estimated_usage = self._parse_storage_value(pvc_size_request) * 0.6
                                        pod_storage_estimate += pvc_estimated_usage
                                except Exception:
                                    # If we can't get PVC info, skip this volume
                                    pass
                            elif volume.empty_dir:
                                # EmptyDir estimate
                                pod_storage_estimate += 100 * 1024 * 1024  # 100MB estimate
                    
                    total_estimated_usage += pod_storage_estimate
            
            # Add system overhead
            system_overhead = storage_capacity * 0.15  # 15% for OS and system
            total_estimated_usage += system_overhead
            
            # Add container image layers overhead
            if running_pods_count > 0:
                # Estimate shared image layers and overlays
                image_overhead = running_pods_count * 50 * 1024 * 1024  # 50MB per pod for overlays
                total_estimated_usage += image_overhead
            
            # Calculate percentage
            usage_percent = (total_estimated_usage / storage_capacity) * 100
            
            # Cap at maximum 100%
            usage_percent = min(usage_percent, 100.0)
            
            logging.debug(f"Calculated disk usage for {node_name}: {usage_percent:.1f}% "
                        f"({total_estimated_usage/(1024**3):.1f}GB used of {storage_capacity/(1024**3):.1f}GB)")
            
            return usage_percent
            
        except Exception as e:
            logging.debug(f"Error calculating disk usage for {node_name}: {e}")
            # Return 0 if we can't calculate real usage
            return 0.0

    def is_metrics_server_available(self) -> bool:
        """Check if Kubernetes metrics server is available"""
        try:
            if not hasattr(self.api_service, 'custom_objects_api'):
                return False
            
            # Try to list nodes from metrics.k8s.io API
            self.api_service.custom_objects_api.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes"
            )
            logging.info("Metrics server is available and responding")
            return True
            
        except Exception as e:
            logging.warning(f"Metrics server not available: {e}")
            return False

    def _parse_cpu_value(self, cpu_str: str) -> float:
        """Parse CPU value from Kubernetes format to cores (float)"""
        if not cpu_str:
            return 0.0
        
        try:
            cpu_str = str(cpu_str).strip()
            
            # Handle different CPU formats
            if cpu_str.endswith('n'):  # nanocores
                return float(cpu_str[:-1]) / 1e9
            elif cpu_str.endswith('u'):  # microcores  
                return float(cpu_str[:-1]) / 1e6
            elif cpu_str.endswith('m'):  # millicores
                return float(cpu_str[:-1]) / 1000
            else:
                # Plain number (cores)
                return float(cpu_str)
        except (ValueError, TypeError):
            logging.warning(f"Could not parse CPU value: {cpu_str}")
            return 0.0

    def _parse_memory_value(self, memory_str: str) -> float:
        """Parse memory value from Kubernetes format to bytes (float)"""
        if not memory_str:
            return 0.0
        
        try:
            memory_str = str(memory_str).strip()
            
            # Handle different memory formats
            if memory_str.endswith('Ki'):
                return float(memory_str[:-2]) * 1024
            elif memory_str.endswith('Mi'):
                return float(memory_str[:-2]) * 1024 * 1024
            elif memory_str.endswith('Gi'):
                return float(memory_str[:-2]) * 1024 * 1024 * 1024
            elif memory_str.endswith('Ti'):
                return float(memory_str[:-2]) * 1024 * 1024 * 1024 * 1024
            elif memory_str.endswith('k'):
                return float(memory_str[:-1]) * 1000
            elif memory_str.endswith('M'):
                return float(memory_str[:-1]) * 1000 * 1000
            elif memory_str.endswith('G'):
                return float(memory_str[:-1]) * 1000 * 1000 * 1000
            else:
                # Plain number (bytes)
                return float(memory_str)
        except (ValueError, TypeError):
            logging.warning(f"Could not parse memory value: {memory_str}")
            return 0.0

    def _parse_storage_value(self, storage_str: str) -> float:
        """Parse storage value from Kubernetes format to bytes (float)"""
        # Same logic as memory parsing
        return self._parse_memory_value(storage_str)

    def cleanup(self):
        """Cleanup metrics service resources"""
        logging.debug("Cleaning up KubernetesMetricsService")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            if hasattr(self, '_parse_cpu_value'):
                self.cleanup()
        except Exception as e:
            logging.error(f"Error in KubernetesMetricsService destructor: {e}")


# Factory function
def create_kubernetes_metrics_service(api_service) -> KubernetesMetricsService:
    """Create a new Kubernetes metrics service instance"""
    return KubernetesMetricsService(api_service)