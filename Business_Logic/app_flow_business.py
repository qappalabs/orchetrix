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
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class GraphPosition:
    """Position information for graph elements"""
    x: float
    y: float
    width: float
    height: float

class AppFlowBusinessLogic:
    """Business logic for app flow analysis and graph generation"""

    def __init__(self):
        self.graph_layout = GraphLayout.HORIZONTAL

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
            name = ingress.get("name")
            namespace = ingress.get("namespace")
            if not name or not namespace:
                logging.warning(f"Skipping ingress with missing required fields: name={name}, namespace={namespace}")
                continue
            resources.append(ResourceInfo(
                name=name,
                namespace=namespace,
                resource_type=ResourceType.INGRESS,
                metadata=ingress,
                status="Active"
            ))

        # Process services
        for service in raw_app_flow.get("services", []):
            name = service.get("name")
            namespace = service.get("namespace")
            if not name or not namespace:
                logging.warning(f"Skipping service with missing required fields: name={name}, namespace={namespace}")
                continue
            resources.append(ResourceInfo(
                name=name,
                namespace=namespace,
                resource_type=ResourceType.SERVICE,
                metadata=service,
                status="Active"
            ))

        # Process deployments
        for deployment in raw_app_flow.get("deployments", []):
            name = deployment.get("name")
            namespace = deployment.get("namespace")
            if not name or not namespace:
                logging.warning(f"Skipping deployment with missing required fields: name={name}, namespace={namespace}")
                continue
            ready = deployment.get("ready_replicas", 0)
            total = deployment.get("replicas", 1)
            status = "Ready" if ready == total else f"{ready}/{total}"

            resources.append(ResourceInfo(
                name=name,
                namespace=namespace,
                resource_type=ResourceType.DEPLOYMENT,
                metadata=deployment,
                status=status
            ))

        # Process pods
        for pod in raw_app_flow.get("pods", []):
            name = pod.get("name")
            namespace = pod.get("namespace")
            if not name or not namespace:
                logging.warning(f"Skipping pod with missing required fields: name={name}, namespace={namespace}")
                continue
            resources.append(ResourceInfo(
                name=name,
                namespace=namespace,
                resource_type=ResourceType.POD,
                metadata=pod,
                status=pod.get("phase", "Unknown")
            ))

        # Process configmaps
        for config in raw_app_flow.get("configmaps", []):
            name = config.get("name")
            namespace = config.get("namespace")
            if not name or not namespace:
                logging.warning(f"Skipping configmap with missing required fields: name={name}, namespace={namespace}")
                continue
            resources.append(ResourceInfo(
                name=name,
                namespace=namespace,
                resource_type=ResourceType.CONFIGMAP,
                metadata=config,
                status="Active"
            ))

        # Process secrets
        for secret in raw_app_flow.get("secrets", []):
            name = secret.get("name")
            namespace = secret.get("namespace")
            if not name or not namespace:
                logging.warning(f"Skipping secret with missing required fields: name={name}, namespace={namespace}")
                continue
            resources.append(ResourceInfo(
                name=name,
                namespace=namespace,
                resource_type=ResourceType.SECRET,
                metadata=secret,
                status="Active"
            ))

        # Process PVCs
        for pvc in raw_app_flow.get("pvcs", []):
            name = pvc.get("name")
            namespace = pvc.get("namespace")
            if not name or not namespace:
                logging.warning(f"Skipping PVC with missing required fields: name={name}, namespace={namespace}")
                continue
            resources.append(ResourceInfo(
                name=name,
                namespace=namespace,
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

    # Default viewport height for vertical centering calculations
    DEFAULT_VIEWPORT_HEIGHT = 400

    def calculate_horizontal_layout(
        self, resources: List[ResourceInfo], viewport_height: Optional[float] = None
    ) -> Dict[str, Tuple[float, float]]:
        """Calculate horizontal layout positions for ALL resources - Enhanced Layout

        Args:
            resources: List of ResourceInfo objects to layout
            viewport_height: Optional viewport height for vertical centering.
                            Defaults to DEFAULT_VIEWPORT_HEIGHT if not provided.
        """
        positions = {}
        effective_viewport_height = viewport_height or self.DEFAULT_VIEWPORT_HEIGHT

        # Group resources by type in horizontal layers
        layers = {
            ResourceType.INGRESS: [r for r in resources if r.resource_type == ResourceType.INGRESS],
            ResourceType.SERVICE: [r for r in resources if r.resource_type == ResourceType.SERVICE],
            ResourceType.DEPLOYMENT: [r for r in resources if r.resource_type == ResourceType.DEPLOYMENT],
            ResourceType.POD: [r for r in resources if r.resource_type == ResourceType.POD],
        }

        # Separate config resources by type for better organization
        configmaps = [r for r in resources if r.resource_type == ResourceType.CONFIGMAP]
        secrets = [r for r in resources if r.resource_type == ResourceType.SECRET]
        pvcs = [r for r in resources if r.resource_type == ResourceType.PVC]

        # Add config layers if resources exist
        if configmaps:
            layers[ResourceType.CONFIGMAP] = configmaps
        if secrets:
            layers[ResourceType.SECRET] = secrets
        if pvcs:
            layers[ResourceType.PVC] = pvcs

        # Layout constants optimized for readability with many resources
        LAYER_SPACING_X = 400  # Increased spacing between resource type layers to reduce overlap
        ITEM_SPACING_Y = 70    # Optimized spacing between items in same layer
        START_X = 60
        START_Y = 60

        layer_x = START_X

        # Define layer order for proper flow visualization
        layer_order = [
            ResourceType.INGRESS,
            ResourceType.SERVICE,
            ResourceType.DEPLOYMENT,
            ResourceType.POD,
            ResourceType.CONFIGMAP,
            ResourceType.SECRET,
            ResourceType.PVC
        ]

        for layer_type in layer_order:
            layer_resources = layers.get(layer_type, [])
            if not layer_resources:
                continue

            # Calculate starting Y position to center the layer vertically
            layer_start_y = START_Y

            # Smart spacing based on resource count to prevent overcrowding
            resource_count = len(layer_resources)

            if resource_count > 10:
                # Very dense layout for many resources
                dynamic_spacing = max(45, ITEM_SPACING_Y - (resource_count - 10) * 2)
            elif resource_count > 6:
                # Moderately dense layout
                dynamic_spacing = max(55, ITEM_SPACING_Y - (resource_count - 6) * 3)
            elif resource_count > 3:
                # Slightly reduced spacing
                dynamic_spacing = ITEM_SPACING_Y - 10
            else:
                # Standard spacing for few resources
                dynamic_spacing = ITEM_SPACING_Y

            # Apply smart centering for better visual balance
            total_height = resource_count * dynamic_spacing
            layer_start_y = START_Y + max(0, (effective_viewport_height - total_height) // 2)  # Center vertically in viewport

            layer_y = layer_start_y
            for i, resource in enumerate(layer_resources):
                key = f"{resource.resource_type.value}:{resource.name}"
                positions[key] = (layer_x, layer_y)
                layer_y += dynamic_spacing

            layer_x += LAYER_SPACING_X

        logging.info(f"Calculated layout positions for {len(positions)} resources across {len([layer for layer in layers.values() if layer])} layers")
        return positions
