"""
Simple Apps page with namespace dropdown and basic key-value inputs.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, 
    QPushButton, QFrame, QSizePolicy, QTextEdit, QScrollArea, QGraphicsView,
    QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
    QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QRectF, QPointF
from PyQt6.QtGui import QFont, QPen, QBrush, QColor, QPainter

from UI.Styles import AppStyles, AppColors
from utils.kubernetes_client import get_kubernetes_client
from kubernetes.client.rest import ApiException
import logging
import json


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


class AppsPage(QWidget):
    """Simple Apps page with proper header layout matching other pages"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()
        
        # Load namespaces after UI is set up
        QTimer.singleShot(100, self.load_namespaces)
    
    def setup_ui(self):
        """Setup the UI mimicking BaseResourcePage header layout"""
        # Main layout with standard margins and spacing (like BaseResourcePage)
        page_main_layout = QVBoxLayout(self)
        page_main_layout.setContentsMargins(16, 16, 16, 16)
        page_main_layout.setSpacing(16)
        
        # Create header layout (single line) exactly like BaseResourcePage
        header_controls_layout = QHBoxLayout()
        
        # Title and count (left side)
        self._create_title_and_count(header_controls_layout)
        
        # Filter controls (middle)
        self._add_filter_controls(header_controls_layout)
        
        # Stretch to push buttons to right
        header_controls_layout.addStretch(1)
        
        # Labels controls (right side, before refresh)
        self._add_labels_controls(header_controls_layout)
        
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
        
        header_layout.addWidget(filters_widget)
    
    def _add_labels_controls(self, header_layout):
        """Add Labels controls with input fields to header"""
        # Labels label
        labels_label = QLabel("Labels:")
        labels_label.setStyleSheet("color: #ffffff; font-size: 13px; margin-right: 8px;")
        header_layout.addWidget(labels_label)
        
        # Key input (right side of Labels text)
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("key")
        self.key_input.setFixedHeight(30)
        self.key_input.setFixedWidth(100)  # Smaller width
        self.key_input.setStyleSheet("""
            QLineEdit { 
                padding: 3px 5px; 
                border: 1px solid #555; 
                border-radius: 4px; 
                background-color: #333; 
                color: white; 
                font-size: 12px;
            }
        """)
        header_layout.addWidget(self.key_input)
        
        # Add spacing between key and value inputs
        header_layout.addSpacing(5)
        
        # Value input (right side of key input)
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("value")
        self.value_input.setFixedHeight(30)
        self.value_input.setFixedWidth(100)  # Smaller width
        self.value_input.setStyleSheet("""
            QLineEdit { 
                padding: 3px 5px; 
                border: 1px solid #555; 
                border-radius: 4px; 
                background-color: #333; 
                color: white; 
                font-size: 12px;
            }
        """)
        header_layout.addWidget(self.value_input)
        
        # Plus button (right side of input fields)
        self.add_labels_btn = QPushButton("+")
        self.add_labels_btn.setFixedSize(30, 30)
        self.add_labels_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 15px;
                font-weight: bold;
                font-size: 18px;
                text-align: center;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        # Add some spacing before the button
        header_layout.addSpacing(8)
        header_layout.addWidget(self.add_labels_btn)
        
        # Connect button click
        self.add_labels_btn.clicked.connect(self.generate_diagram)
    
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
        diagram_layout.setContentsMargins(15, 15, 15, 15)
        diagram_layout.setSpacing(10)
        
        # Diagram title
        self.diagram_title = QLabel("App Diagram")
        self.diagram_title.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.TEXT_LIGHT};
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 5px;
            }}
        """)
        diagram_layout.addWidget(self.diagram_title)
        
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
        """)
        self.diagram_view.setMinimumHeight(400)
        diagram_layout.addWidget(self.diagram_view)
        
        # Status text area
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
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
        """)
        self.status_text.setPlainText("Enter namespace and labels, then click + to generate app diagram")
        diagram_layout.addWidget(self.status_text)
        
        main_layout.addWidget(diagram_frame)
    
    def generate_diagram(self):
        """Generate app diagram based on current inputs"""
        namespace = self.namespace_combo.currentText()
        key = self.key_input.text().strip()
        value = self.value_input.text().strip()
        
        # Validation
        if not namespace or namespace == "Loading...":
            QMessageBox.warning(self, "Warning", "Please select a namespace first.")
            return
        
        if not key or not value:
            reply = QMessageBox.question(
                self, "Confirm", 
                "No labels specified. This will analyze all deployments in the namespace. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Clear previous diagram
        self.diagram_scene.clear()
        self.status_text.setPlainText("Starting analysis...")
        
        # Start analysis in background thread
        self.analyzer = DeploymentAnalyzer(namespace, key, value, self)
        self.analyzer.analysis_completed.connect(self.on_analysis_completed)
        self.analyzer.error_occurred.connect(self.on_analysis_error)
        self.analyzer.progress_updated.connect(self.on_progress_updated)
        self.analyzer.start()
        
        # Disable button during analysis
        self.add_labels_btn.setEnabled(False)
        self.add_labels_btn.setText("...")
    
    def on_progress_updated(self, message):
        """Handle progress updates"""
        self.status_text.append(message)
    
    def on_analysis_completed(self, diagram_data):
        """Handle completed analysis and create diagram"""
        self.add_labels_btn.setEnabled(True)
        self.add_labels_btn.setText("+")
        
        # Update title
        namespace = diagram_data["namespace"]
        filter_text = diagram_data["filter"]
        self.diagram_title.setText(f"App Diagram - {namespace} ({filter_text})")
        
        # Create visual diagram
        self.create_visual_diagram(diagram_data)
        
        # Update status
        deployments_count = len(diagram_data["deployments"])
        services_count = len(diagram_data["services"])
        self.status_text.append(f"\nDiagram created successfully!")
        self.status_text.append(f"Found {deployments_count} deployments and {services_count} services")
    
    def on_analysis_error(self, error_message):
        """Handle analysis errors"""
        self.add_labels_btn.setEnabled(True)
        self.add_labels_btn.setText("+")
        
        self.status_text.append(f"\nError: {error_message}")
        QMessageBox.critical(self, "Analysis Error", error_message)
    
    def create_visual_diagram(self, diagram_data):
        """Create visual representation of the app diagram"""
        self.diagram_scene.clear()
        
        deployments = diagram_data["deployments"]
        services = diagram_data["services"]
        connections = diagram_data["connections"]
        
        if not deployments:
            self.add_text_to_scene("No deployments found", 10, 10, QColor(AppColors.TEXT_SECONDARY))
            return
        
        # Position elements
        y_offset = 20
        deployment_positions = {}
        service_positions = {}
        
        # Draw deployments
        for i, deployment in enumerate(deployments):
            x = 50 + (i * 250)
            y = y_offset
            
            # Draw deployment box
            self.draw_deployment_box(deployment, x, y)
            deployment_positions[deployment["name"]] = (x + 100, y + 50)  # Center of box
        
        # Draw services
        service_y = y_offset + 150
        for i, service in enumerate(services):
            x = 50 + (i * 200)
            y = service_y
            
            # Draw service box
            self.draw_service_box(service, x, y)
            service_positions[service["name"]] = (x + 75, y + 25)  # Center of box
        
        # Draw connections
        for connection in connections:
            if connection["from"] in deployment_positions and connection["to"] in service_positions:
                from_pos = deployment_positions[connection["from"]]
                to_pos = service_positions[connection["to"]]
                self.draw_connection(from_pos, to_pos)
    
    def draw_deployment_box(self, deployment, x, y):
        """Draw a deployment box"""
        # Main box
        rect = self.diagram_scene.addRect(x, y, 200, 100, 
                                        QPen(QColor("#007acc")), 
                                        QBrush(QColor("#1e3a5f")))
        
        # Deployment name
        name_text = self.diagram_scene.addText(deployment["name"], QFont("Arial", 10, QFont.Weight.Bold))
        name_text.setDefaultTextColor(QColor("white"))
        name_text.setPos(x + 10, y + 5)
        
        # Replica info
        replica_info = f"Replicas: {deployment['ready_replicas']}/{deployment['replicas']}"
        replica_text = self.diagram_scene.addText(replica_info, QFont("Arial", 8))
        replica_text.setDefaultTextColor(QColor("#cccccc"))
        replica_text.setPos(x + 10, y + 25)
        
        # Container info
        containers = deployment.get("containers", [])
        if containers:
            container_text = f"Containers: {len(containers)}"
            cont_text = self.diagram_scene.addText(container_text, QFont("Arial", 8))
            cont_text.setDefaultTextColor(QColor("#cccccc"))
            cont_text.setPos(x + 10, y + 45)
            
            # Show first container image
            if containers[0].get("image"):
                image_name = containers[0]["image"].split("/")[-1][:20] + "..."
                img_text = self.diagram_scene.addText(f"Image: {image_name}", QFont("Arial", 7))
                img_text.setDefaultTextColor(QColor("#aaaaaa"))
                img_text.setPos(x + 10, y + 65)
    
    def draw_service_box(self, service, x, y):
        """Draw a service box"""
        # Main box
        rect = self.diagram_scene.addRect(x, y, 150, 50, 
                                        QPen(QColor("#28a745")), 
                                        QBrush(QColor("#1e4d2b")))
        
        # Service name
        name_text = self.diagram_scene.addText(service["name"], QFont("Arial", 9, QFont.Weight.Bold))
        name_text.setDefaultTextColor(QColor("white"))
        name_text.setPos(x + 10, y + 5)
        
        # Service type and ports
        type_info = f"Type: {service['type']}"
        type_text = self.diagram_scene.addText(type_info, QFont("Arial", 7))
        type_text.setDefaultTextColor(QColor("#cccccc"))
        type_text.setPos(x + 10, y + 25)
    
    def draw_connection(self, from_pos, to_pos):
        """Draw connection line between components"""
        line = self.diagram_scene.addLine(from_pos[0], from_pos[1], 
                                        to_pos[0], to_pos[1], 
                                        QPen(QColor("#666666"), 2))
    
    def add_text_to_scene(self, text, x, y, color):
        """Add text to the scene"""
        text_item = self.diagram_scene.addText(text, QFont("Arial", 12))
        text_item.setDefaultTextColor(color)
        text_item.setPos(x, y)