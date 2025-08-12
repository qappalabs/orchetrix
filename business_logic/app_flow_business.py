"""
Business logic module for app flow analysis and graph data processing.
Separates business logic from UI components for better maintainability.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class ResourceType(Enum):
    INGRESS = "ingress"
    SERVICE = "service"
    DEPLOYMENT = "deployment"
    POD = "pod"
    CONFIGMAP = "configmap"
    SECRET = "secret"
    PVC = "pvc"

class GraphLayout(Enum):
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    CIRCULAR = "circular"

@dataclass
class ResourceInfo:
    """Standardized resource information structure"""
    name: str
    namespace: str
    resource_type: ResourceType
    metadata: Dict[str, Any]
    status: str = "Unknown"
    
@dataclass
class ConnectionInfo:
    """Connection between resources"""
    from_resource: str
    to_resource: str
    connection_type: str
    metadata: Dict[str, Any] = None

@dataclass
class GraphPosition:
    """Position information for graph elements"""
    x: float
    y: float
    width: float
    height: float

@dataclass
class K8sIconInfo:
    """Kubernetes icon information"""
    resource_type: ResourceType
    icon_path: str
    color: str
    bg_color: str

class AppFlowBusinessLogic:
    """Business logic for app flow analysis and graph generation"""
    
    def __init__(self):
        self.k8s_icons = self._initialize_k8s_icons()
        self.graph_layout = GraphLayout.HORIZONTAL
        
    def _initialize_k8s_icons(self) -> Dict[ResourceType, K8sIconInfo]:
        """Initialize Kubernetes resource icons mapping"""
        return {
            ResourceType.INGRESS: K8sIconInfo(
                ResourceType.INGRESS, "icons/ingress.png", "#E91E63", "#4A1628"
            ),
            ResourceType.SERVICE: K8sIconInfo(
                ResourceType.SERVICE, "icons/service.png", "#28a745", "#1e4d2b"
            ),
            ResourceType.DEPLOYMENT: K8sIconInfo(
                ResourceType.DEPLOYMENT, "icons/deployment.png", "#007acc", "#1e3a5f"
            ),
            ResourceType.POD: K8sIconInfo(
                ResourceType.POD, "icons/pod.png", "#4CAF50", "#2E7D32"
            ),
            ResourceType.CONFIGMAP: K8sIconInfo(
                ResourceType.CONFIGMAP, "icons/configmap.png", "#4CAF50", "#2E7D32"
            ),
            ResourceType.SECRET: K8sIconInfo(
                ResourceType.SECRET, "icons/secret.png", "#FF9800", "#F57C00"
            ),
            ResourceType.PVC: K8sIconInfo(
                ResourceType.PVC, "icons/pvc.png", "#9C27B0", "#6A1B9A"
            )
        }
    
    def set_graph_layout(self, layout: GraphLayout):
        """Set the graph layout orientation"""
        self.graph_layout = layout
        logging.info(f"Graph layout set to: {layout.value}")
    
    def process_app_flow_data(self, raw_app_flow: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw app flow data into standardized format"""
        try:
            processed_data = {
                "namespace": raw_app_flow.get("namespace", "default"),
                "workload_type": raw_app_flow.get("workload_type", "deployment"),
                "main_resource": raw_app_flow.get("main_resource", {}),
                "resources": self._process_resources(raw_app_flow),
                "connections": self._process_connections(raw_app_flow),
                "layout": self.graph_layout.value
            }
            
            logging.info(f"Processed app flow data with {len(processed_data['resources'])} resources")
            return processed_data
            
        except Exception as e:
            logging.error(f"Error processing app flow data: {e}")
            raise
    
    def _process_resources(self, raw_app_flow: Dict[str, Any]) -> List[ResourceInfo]:
        """Process all resources from raw app flow data"""
        resources = []
        
        # Process ingresses
        for ingress in raw_app_flow.get("ingresses", []):
            resources.append(ResourceInfo(
                name=ingress["name"],
                namespace=ingress["namespace"],
                resource_type=ResourceType.INGRESS,
                metadata=ingress,
                status="Active"
            ))
        
        # Process services
        for service in raw_app_flow.get("services", []):
            resources.append(ResourceInfo(
                name=service["name"],
                namespace=service["namespace"],
                resource_type=ResourceType.SERVICE,
                metadata=service,
                status="Active"
            ))
        
        # Process deployments
        for deployment in raw_app_flow.get("deployments", []):
            ready = deployment.get("ready_replicas", 0)
            total = deployment.get("replicas", 1)
            status = "Ready" if ready == total else f"{ready}/{total}"
            
            resources.append(ResourceInfo(
                name=deployment["name"],
                namespace=deployment["namespace"],
                resource_type=ResourceType.DEPLOYMENT,
                metadata=deployment,
                status=status
            ))
        
        # Process pods
        for pod in raw_app_flow.get("pods", []):
            resources.append(ResourceInfo(
                name=pod["name"],
                namespace=pod["namespace"],
                resource_type=ResourceType.POD,
                metadata=pod,
                status=pod.get("phase", "Unknown")
            ))
        
        # Process configmaps
        for config in raw_app_flow.get("configmaps", []):
            resources.append(ResourceInfo(
                name=config["name"],
                namespace=config["namespace"],
                resource_type=ResourceType.CONFIGMAP,
                metadata=config,
                status="Active"
            ))
        
        # Process secrets
        for secret in raw_app_flow.get("secrets", []):
            resources.append(ResourceInfo(
                name=secret["name"],
                namespace=secret["namespace"],
                resource_type=ResourceType.SECRET,
                metadata=secret,
                status="Active"
            ))
        
        # Process PVCs
        for pvc in raw_app_flow.get("pvcs", []):
            resources.append(ResourceInfo(
                name=pvc["name"],
                namespace=pvc["namespace"],
                resource_type=ResourceType.PVC,
                metadata=pvc,
                status="Bound"
            ))
        
        return resources
    
    def _process_connections(self, raw_app_flow: Dict[str, Any]) -> List[ConnectionInfo]:
        """Process connections from raw app flow data"""
        connections = []
        
        for conn in raw_app_flow.get("connections", []):
            connections.append(ConnectionInfo(
                from_resource=conn["from"],
                to_resource=conn["to"],
                connection_type=conn["type"],
                metadata=conn
            ))
        
        return connections
    
    def calculate_horizontal_layout(self, resources: List[ResourceInfo]) -> Dict[str, Tuple[float, float]]:
        """Calculate horizontal layout positions for resources"""
        positions = {}
        
        # Group resources by type in horizontal layers
        layers = {
            ResourceType.INGRESS: [r for r in resources if r.resource_type == ResourceType.INGRESS],
            ResourceType.SERVICE: [r for r in resources if r.resource_type == ResourceType.SERVICE],
            ResourceType.DEPLOYMENT: [r for r in resources if r.resource_type == ResourceType.DEPLOYMENT],
            ResourceType.POD: [r for r in resources if r.resource_type == ResourceType.POD],
        }
        
        # Add config resources to bottom layer
        config_resources = [r for r in resources if r.resource_type in 
                          [ResourceType.CONFIGMAP, ResourceType.SECRET, ResourceType.PVC]]
        if config_resources:
            layers[ResourceType.CONFIGMAP] = config_resources
        
        # Layout constants for horizontal arrangement - optimized for enhanced boxes with external text
        LAYER_SPACING_X = 220  # Horizontal spacing between layers (adjusted for enhanced boxes)
        ITEM_SPACING_Y = 60    # Reduced vertical spacing between items for pods
        START_X = 50
        START_Y = 50
        
        layer_x = START_X
        
        for layer_type, layer_resources in layers.items():
            if not layer_resources:
                continue
                
            # Position items vertically within the layer
            layer_y = START_Y
            for resource in layer_resources:
                key = f"{resource.resource_type.value}:{resource.name}"
                positions[key] = (layer_x, layer_y)
                layer_y += ITEM_SPACING_Y
            
            layer_x += LAYER_SPACING_X
        
        return positions
    
    def get_resource_icon_info(self, resource_type: ResourceType) -> K8sIconInfo:
        """Get icon information for a resource type"""
        return self.k8s_icons.get(resource_type, self.k8s_icons[ResourceType.POD])
    
    def generate_export_data(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data structure for export functionality"""
        export_data = {
            "title": f"App Flow - {processed_data.get('namespace', 'default')}",
            "layout": processed_data.get("layout", "horizontal"),
            "resources": [],
            "connections": [],
            "metadata": {
                "workload_type": processed_data.get("workload_type", "deployment"),
                "namespace": processed_data.get("namespace", "default"),
                "total_resources": len(processed_data.get("resources", [])),
                "total_connections": len(processed_data.get("connections", []))
            }
        }
        
        # Prepare resource data for export
        for resource in processed_data.get("resources", []):
            export_data["resources"].append({
                "name": resource.name,
                "type": resource.resource_type.value,
                "namespace": resource.namespace,
                "status": resource.status
            })
        
        # Prepare connection data for export
        for connection in processed_data.get("connections", []):
            export_data["connections"].append({
                "from": connection.from_resource,
                "to": connection.to_resource,
                "type": connection.connection_type
            })
        
        return export_data
    
    def validate_app_flow_data(self, app_flow_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate app flow data structure"""
        errors = []
        
        # Check required fields
        required_fields = ["namespace", "workload_type"]
        for field in required_fields:
            if field not in app_flow_data:
                errors.append(f"Missing required field: {field}")
        
        # Check resource arrays
        resource_arrays = ["ingresses", "services", "deployments", "pods", "configmaps", "secrets", "pvcs"]
        for array_name in resource_arrays:
            if array_name not in app_flow_data:
                errors.append(f"Missing resource array: {array_name}")
            elif not isinstance(app_flow_data[array_name], list):
                errors.append(f"Resource array {array_name} must be a list")
        
        # Check connections
        if "connections" not in app_flow_data:
            errors.append("Missing connections array")
        elif not isinstance(app_flow_data["connections"], list):
            errors.append("Connections must be a list")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def calculate_graph_dimensions(self, resources: List[ResourceInfo]) -> Tuple[float, float]:
        """Calculate total dimensions needed for the graph"""
        if self.graph_layout == GraphLayout.HORIZONTAL:
            # For horizontal layout: width = layers * spacing, height = max items per layer * spacing
            resource_counts_by_type = {}
            for resource in resources:
                resource_counts_by_type[resource.resource_type] = \
                    resource_counts_by_type.get(resource.resource_type, 0) + 1
            
            num_layers = len(resource_counts_by_type)
            max_items_per_layer = max(resource_counts_by_type.values()) if resource_counts_by_type else 1
            
            width = num_layers * 220 + 100  # Layer spacing + margins (adjusted for enhanced boxes)
            height = max_items_per_layer * 140 + 100  # Item spacing + margins (adjusted for enhanced text layout)
            
        else:  # Vertical layout
            # For vertical layout: height = layers * spacing, width = max items per layer * spacing
            num_layers = len(set(r.resource_type for r in resources))
            max_items_per_layer = max([
                len([r for r in resources if r.resource_type == rt]) 
                for rt in set(r.resource_type for r in resources)
            ]) if resources else 1
            
            width = max_items_per_layer * 200 + 100  # Item width + margins
            height = num_layers * 120 + 100  # Layer height + margins
        
        return width, height