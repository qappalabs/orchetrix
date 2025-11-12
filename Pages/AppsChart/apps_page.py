"""
AppsPage - Main UI class for the Apps Chart page.

This module contains the AppsPage widget that provides the main interface
for viewing and interacting with Kubernetes application flow diagrams.
"""

import os
import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, 
    QPushButton, QFrame, QSizePolicy, QTextEdit, QScrollArea, QGraphicsView,
    QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
    QMessageBox, QProgressDialog, QGraphicsPixmapItem, QFileDialog, QMenu, QToolButton,
    QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QRectF, QPointF
from PyQt6.QtGui import QFont, QPen, QBrush, QColor, QPainter, QPixmap, QIcon, QAction

from UI.Styles import AppStyles, AppColors
from UI.Icons import resource_path
from Business_Logic.app_flow_business import (
    AppFlowBusinessLogic, ResourceType, GraphLayout, ResourceInfo, ConnectionInfo
)

# Import modular components from the same package
from .deployment_analyzer import DeploymentAnalyzer
from Utils.unified_resource_loader import get_unified_resource_loader
from Utils.data_formatters import format_age, truncate_string
from .app_flow_analyzer import AppFlowAnalyzer


class AppsPage(QWidget):
    """Simple Apps page with proper header layout matching other pages"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.business_logic = AppFlowBusinessLogic()
        self.current_app_flow_data = None
        self.current_resource_positions = {}  # Store current positions for live updates
        self.live_monitoring_enabled = False
        self.setup_ui()
        
        # Set horizontal layout by default
        self.business_logic.set_graph_layout(GraphLayout.HORIZONTAL)
        
        # Setup live monitoring timer
        self.live_monitor_timer = QTimer()
        self.live_monitor_timer.timeout.connect(self.update_live_monitoring)
        self.live_monitor_timer.setInterval(5000)  # Update every 5 seconds
        
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
        
        # Add sufficient spacing between filters and buttons to ensure resource dropdown is fully visible
        header_controls_layout.addSpacing(30)
        
        # Live monitoring button
        self.live_monitor_btn = QPushButton("▶ Start Live")
        self.live_monitor_btn.setStyleSheet("""
            QPushButton { 
                background-color: #28a745; 
                color: #ffffff; 
                border: 1px solid #34ce57;
                border-radius: 4px; 
                padding: 3px 8px; 
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { 
                background-color: #34ce57; 
            }
            QPushButton:pressed { 
                background-color: #1e7e34; 
            }
            QPushButton:disabled {
                background-color: #6c757d;
                border-color: #6c757d;
                color: #adb5bd;
            }
        """)
        self.live_monitor_btn.clicked.connect(self.toggle_live_monitoring)
        header_controls_layout.addWidget(self.live_monitor_btn)
        
        # Add some spacing
        header_controls_layout.addSpacing(5)
        
        # Refresh button (far right) - optional, matching other pages
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton { 
                background-color: #2d2d2d; 
                color: #ffffff; 
                border: 1px solid #3d3d3d;
                border-radius: 4px; 
                padding: 3px 8px; 
                font-size: 12px;
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
        title_label = QLabel("AppsChart")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        
        layout.addWidget(title_label)
    
    def _add_filter_controls(self, header_layout):
        """Add namespace control in header"""
        filters_widget = QWidget()
        filters_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        filters_layout = QHBoxLayout(filters_widget)
        filters_layout.setContentsMargins(0, 0, 15, 0)  # Add 15px right margin for resource dropdown
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
        
        # Use the centralized dropdown style utility from AppStyles class
        self.namespace_combo.setStyleSheet(AppStyles.get_dropdown_style_with_icon())
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
        
        # Use the centralized dropdown style utility from AppStyles class
        self.workload_combo.setStyleSheet(AppStyles.get_dropdown_style_with_icon())
        
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
        self.resource_combo.setFixedWidth(150)  # Further reduced width for better visibility
        # Configure dropdown behavior to prevent upward opening
        self._configure_dropdown_behavior(self.resource_combo)
        
        # Use the centralized dropdown style utility from AppStyles class
        self.resource_combo.setStyleSheet(AppStyles.get_dropdown_style_with_icon())
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
        """Load namespaces using unified loader"""
        unified_loader = get_unified_resource_loader()
        
        # Connect signals if not already connected
        if not hasattr(self, '_namespace_signals_connected'):
            unified_loader.loading_completed.connect(self._on_namespaces_loaded_unified)
            unified_loader.loading_error.connect(self._on_namespace_error_unified)
            self._namespace_signals_connected = True
        
        # Load namespaces
        self._namespace_operation_id = unified_loader.load_resources_async('namespaces')
    
    def _on_namespaces_loaded_unified(self, resource_type: str, result):
        """Handle namespaces loaded from unified loader"""
        if resource_type != 'namespaces':
            return
        
        if result.success:
            # Extract namespace names from the processed results
            namespaces = [item.get('name', '') for item in result.items if item.get('name')]
            self.on_namespaces_loaded(namespaces)
        else:
            self.on_namespace_error(result.error_message or "Failed to load namespaces")
    
    def _on_namespace_error_unified(self, resource_type: str, error_message: str):
        """Handle namespace loading errors from unified loader"""
        if resource_type == 'namespaces':
            self.on_namespace_error(error_message)
    
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
        
        # Stop live monitoring if active when selection changes
        if self.live_monitoring_enabled:
            self.toggle_live_monitoring()
        
        # Clear the diagram when selection changes
        self.diagram_scene.clear()
        
        # Reset diagram title
        self.diagram_title.setText("App Diagram")
        
        # Reset status text
        self.status_text.setPlainText("Loading resources...")
        
        # Disable live monitoring button
        self.live_monitor_btn.setEnabled(False)
        
        # Stop any running analyzer
        if hasattr(self, 'app_flow_analyzer') and self.app_flow_analyzer.isRunning():
            self.app_flow_analyzer.terminate()
            self.app_flow_analyzer.wait()
        
        if hasattr(self, 'live_app_flow_analyzer') and self.live_app_flow_analyzer.isRunning():
            self.live_app_flow_analyzer.terminate()
            self.live_app_flow_analyzer.wait()
        
        # Reset resource dropdown
        self.resource_combo.blockSignals(True)
        self.resource_combo.clear()
        self.resource_combo.addItem("Loading...")
        self.resource_combo.setEnabled(False)
        self.resource_combo.blockSignals(False)
        
        # Start loading resources
        self.load_resources(namespace, workload_type)
    
    def load_resources(self, namespace, workload_type):
        """Load resources based on namespace and workload type using unified loader"""
        try:
            unified_loader = get_unified_resource_loader()
            
            # Connect signals if not already connected
            if not hasattr(self, '_resource_signals_connected'):
                unified_loader.loading_completed.connect(self._on_resources_loaded_unified)
                unified_loader.loading_error.connect(self._on_resource_error_unified)
                self._resource_signals_connected = True
            
            # Determine namespace for loading
            load_namespace = namespace if namespace != "All Namespaces" else None
            
            # Load the appropriate workload type
            self._current_workload_type = workload_type
            self._resource_operation_id = unified_loader.load_resources_async(
                resource_type=workload_type.lower(),
                namespace=load_namespace
            )
            
            logging.debug(f"Started loading {workload_type} in namespace {namespace}")
            
        except Exception as e:
            logging.error(f"Error starting unified resource loader: {e}")
            self.on_resource_error(f"Error loading resources: {str(e)}")
    
    def _on_resources_loaded_unified(self, resource_type: str, result):
        """Handle resources loaded from unified loader"""
        # Check if this matches our current workload type
        if resource_type != getattr(self, '_current_workload_type', '').lower():
            return
        
        if result.success:
            # Process the unified format resources
            resources = result.items
            self.on_resources_loaded(resources)
        else:
            self.on_resource_error(result.error_message or "Failed to load resources")
    
    def _on_resource_error_unified(self, resource_type: str, error_message: str):
        """Handle resource loading errors from unified loader"""
        if resource_type == getattr(self, '_current_workload_type', '').lower():
            self.on_resource_error(error_message)
    
    def on_resources_loaded(self, resources):
        """Handle loaded resources"""
        self.resource_combo.blockSignals(True)
        self.resource_combo.clear()
        
        if resources:
            # Extract resource names from the processed dictionaries
            # The unified resource loader now returns dictionaries with 'name' field
            resource_names = []
            for resource in resources:
                if isinstance(resource, dict) and 'name' in resource:
                    resource_names.append(resource['name'])
                elif isinstance(resource, str):
                    # Handle case where it might still be strings (backward compatibility)
                    resource_names.append(resource)
                else:
                    # Fallback for unexpected format
                    logging.warning(f"Unexpected resource format: {type(resource)}")
                    resource_names.append(str(resource))
            
            # Store the full resource data for later use if needed
            self._current_resources = resources
            
            self.resource_combo.addItems(resource_names)
            logging.info(f"Loaded {len(resource_names)} resources for Apps page")
            
            # Auto-select and generate graph if there's only one resource
            if len(resource_names) == 1:
                self.resource_combo.setCurrentIndex(0)
                self.resource_combo.blockSignals(False)
                self.resource_combo.setEnabled(False)  # Disable dropdown since there's only one option
                
                # Auto-trigger graph generation
                QTimer.singleShot(100, self.on_resource_selected)
                logging.info(f"Auto-selected single resource: {resource_names[0]}")
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
        
        # Stop live monitoring if active
        if self.live_monitoring_enabled:
            self.toggle_live_monitoring()
        
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
        
        # Disable live monitoring button
        self.live_monitor_btn.setEnabled(False)
        
        # Stop any running analyzers
        if hasattr(self, 'app_flow_analyzer') and self.app_flow_analyzer.isRunning():
            self.app_flow_analyzer.terminate()
            self.app_flow_analyzer.wait()
        
        if hasattr(self, 'live_app_flow_analyzer') and self.live_app_flow_analyzer.isRunning():
            self.live_app_flow_analyzer.terminate()
            self.live_app_flow_analyzer.wait()
        
        # The unified loader handles cancellation internally - no manual termination needed
        
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
    
    def toggle_live_monitoring(self):
        """Toggle live monitoring on/off"""
        if self.live_monitoring_enabled:
            # Stop live monitoring
            self.live_monitor_timer.stop()
            self.live_monitoring_enabled = False
            self.live_monitor_btn.setText("▶ Start Live")
            self.live_monitor_btn.setStyleSheet("""
                QPushButton { 
                    background-color: #28a745; 
                    color: #ffffff; 
                    border: 1px solid #34ce57;
                    border-radius: 4px; 
                    padding: 5px 10px; 
                    font-weight: bold;
                }
                QPushButton:hover { 
                    background-color: #34ce57; 
                }
                QPushButton:pressed { 
                    background-color: #1e7e34; 
                }
            """)
            # Remove live indicator from diagram title
            current_title = self.diagram_title.text()
            if "🔴 LIVE - " in current_title:
                self.diagram_title.setText(current_title.replace("🔴 LIVE - ", ""))
            self.status_text.append("Live monitoring stopped")
        else:
            # Start live monitoring
            if hasattr(self, 'current_resources') and self.current_resources:
                self.live_monitor_timer.start()
                self.live_monitoring_enabled = True
                self.live_monitor_btn.setText("⏸ Stop Live")
                self.live_monitor_btn.setStyleSheet("""
                    QPushButton { 
                        background-color: #dc3545; 
                        color: #ffffff; 
                        border: 1px solid #dc3545;
                        border-radius: 4px; 
                        padding: 5px 10px; 
                        font-weight: bold;
                    }
                    QPushButton:hover { 
                        background-color: #c82333; 
                    }
                    QPushButton:pressed { 
                        background-color: #bd2130; 
                    }
                """)
                # Update diagram title to show live monitoring status
                current_title = self.diagram_title.text()
                if "🔴 LIVE" not in current_title:
                    self.diagram_title.setText(f"🔴 LIVE - {current_title}")
                self.status_text.append("Live monitoring started - updating every 5 seconds")
    
    def update_live_monitoring(self):
        """Update the graph with live data"""
        if not self.live_monitoring_enabled or not hasattr(self, 'current_resources'):
            return
            
        try:
            # Get current namespace, workload type, and resource name
            namespace = self.namespace_combo.currentText()
            workload_type = self.workload_combo.currentText()
            resource_name = self.resource_combo.currentText()
            
            if not all([namespace, workload_type, resource_name]) or resource_name in ["Loading...", "Select namespace and workload first", "No resources found", "Error loading resources"]:
                return
            
            # Start background analysis for live update
            self.start_live_app_flow_analysis(namespace, workload_type, resource_name)
            
        except Exception as e:
            logging.error(f"Live monitoring update failed: {e}")
            self.status_text.append(f"Live monitoring error: {str(e)}")
    
    def start_live_app_flow_analysis(self, namespace, workload_type, resource_name):
        """Start app flow analysis for live monitoring (non-blocking)"""
        try:
            # Stop any existing live analyzer
            if hasattr(self, 'live_app_flow_analyzer') and self.live_app_flow_analyzer.isRunning():
                self.live_app_flow_analyzer.terminate()
                self.live_app_flow_analyzer.wait()
            
            # Start new live analyzer
            self.live_app_flow_analyzer = AppFlowAnalyzer(namespace, workload_type, resource_name, self)
            self.live_app_flow_analyzer.analysis_completed.connect(self.on_live_app_flow_completed)
            self.live_app_flow_analyzer.error_occurred.connect(self.on_live_app_flow_error)
            self.live_app_flow_analyzer.start()
            
        except Exception as e:
            logging.error(f"Error starting live app flow analyzer: {e}")
    
    def on_live_app_flow_completed(self, app_flow):
        """Handle completed live app flow analysis - update existing elements"""
        if not self.live_monitoring_enabled:
            return
            
        try:
            # Store updated app flow data
            self.current_app_flow_data = app_flow
            
            # Process app flow data through business logic
            processed_data = self.business_logic.process_app_flow_data(app_flow)
            
            # Update existing graph elements instead of full redraw
            self.update_existing_graph_elements(processed_data)
            
            # Add timestamp to status
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.status_text.append(f"[{timestamp}] Live update completed")
            
        except Exception as e:
            logging.error(f"Live app flow update failed: {e}")
            self.status_text.append(f"Live update error: {str(e)}")
    
    def on_live_app_flow_error(self, error_message):
        """Handle live app flow analysis error"""
        if self.live_monitoring_enabled:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.status_text.append(f"[{timestamp}] Live update error: {error_message}")
    
    def update_existing_graph_elements(self, processed_data):
        """Update existing graph elements with comprehensive live changes"""
        if not hasattr(self, 'current_resource_positions'):
            # No previous graph exists, create fresh diagram
            self.create_horizontal_app_flow_diagram(processed_data)
            return
            
        current_resources = processed_data.get("resources", [])
        
        # Check if significant changes require full redraw
        if self.requires_full_redraw(current_resources):
            self.create_horizontal_app_flow_diagram(processed_data)
            return
        
        # Perform incremental updates for minor changes
        self.perform_incremental_updates(current_resources)
    
    def requires_full_redraw(self, current_resources):
        """Check if changes require full diagram redraw"""
        if not hasattr(self, 'current_resources') or not self.current_resources:
            return True
            
        # Get previous resource identifiers
        previous_resource_ids = {
            (r.resource_type.value, r.name, r.namespace) for r in self.current_resources
        }
        
        # Get current resource identifiers  
        current_resource_ids = {
            (r.resource_type.value, r.name, r.namespace) for r in current_resources
        }
        
        # Check for added or removed resources
        added_resources = current_resource_ids - previous_resource_ids
        removed_resources = previous_resource_ids - current_resource_ids
        
        # Redraw if resources were added or removed
        if added_resources or removed_resources:
            return True
            
        # Check for significant status changes that affect layout
        # (e.g., deployment replica count changes)
        for current_resource in current_resources:
            # Find matching previous resource
            for prev_resource in self.current_resources:
                if (current_resource.resource_type == prev_resource.resource_type and
                    current_resource.name == prev_resource.name and
                    current_resource.namespace == prev_resource.namespace):
                    
                    # Check for replica count changes in deployments/statefulsets
                    if current_resource.resource_type.value.lower() in ['deployment', 'statefulset', 'daemonset']:
                        if getattr(current_resource, 'replicas', 0) != getattr(prev_resource, 'replicas', 0):
                            return True
                    break
        
        return False
    
    def perform_incremental_updates(self, current_resources):
        """Perform incremental updates to existing graph elements"""
        # Update existing resources with status/color changes
        for item in self.diagram_scene.items():
            if hasattr(item, 'data') and item.data(0):
                item_data = item.data(0)
                if isinstance(item_data, dict) and 'resource' in item_data:
                    stored_resource = item_data['resource']
                    
                    # Find matching resource in new data
                    for new_resource in current_resources:
                        if (new_resource.name == stored_resource.name and 
                            new_resource.resource_type == stored_resource.resource_type and
                            new_resource.namespace == stored_resource.namespace):
                            
                            # Update pod colors if status changed
                            if (new_resource.resource_type.value.lower() == 'pod' and 
                                new_resource.status != stored_resource.status):
                                self.update_pod_color(item, new_resource.status)
                                
                            # Update all resource tooltips with latest information
                            if hasattr(item, 'setToolTip'):
                                tooltip_text = self.create_detailed_tooltip(new_resource)
                                item.setToolTip(tooltip_text)
                                
                            # Update stored resource data
                            item_data['resource'] = new_resource
                            item.setData(0, item_data)
                            break
        
        # Update stored current resources for next comparison
        self.current_resources = current_resources
    
    def update_pod_color(self, pod_item, new_status):
        """Update pod icon based on new status"""
        try:
            # Get appropriate icon path for the new status
            new_icon_path = self.get_pod_icon_path(new_status)
            
            # Update the pod icon if it's a pixmap item
            if hasattr(pod_item, 'setPixmap') and os.path.exists(new_icon_path):
                pixmap = QPixmap(new_icon_path)
                if not pixmap.isNull():
                    # Scale to standard icon size
                    scaled_pixmap = pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    pod_item.setPixmap(scaled_pixmap)
            elif hasattr(pod_item, 'setBrush') and hasattr(pod_item, 'setPen'):
                # Fallback: update circle color if it's still a circle (for compatibility)
                new_color = self.get_pod_status_color(new_status)
                pod_item.setBrush(QBrush(QColor(new_color)))
                pod_item.setPen(QPen(QColor(new_color).darker(150), 2))
                
            # Update tooltip with new status
            if hasattr(pod_item, 'data') and pod_item.data(0):
                item_data = pod_item.data(0)
                if 'resource' in item_data:
                    resource = item_data['resource']
                    resource.status = new_status  # Update status
                    tooltip_text = self.create_detailed_tooltip(resource)
                    pod_item.setToolTip(tooltip_text)
                        
        except Exception as e:
            logging.warning(f"Failed to update pod color: {e}")
    
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
        export_icon_path = resource_path("Icons/terminal_download.svg")
        if os.path.exists(export_icon_path):
            self.export_btn.setIcon(QIcon(export_icon_path))
        else:
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
        export_image_action = QAction("Export as Image", self)
        image_icon_path = resource_path("Icons/export_to_image.svg")
        if os.path.exists(image_icon_path):
            export_image_action.setIcon(QIcon(image_icon_path))
        export_image_action.triggered.connect(self.export_as_image_dialog)
        export_menu.addAction(export_image_action)
        
        export_pdf_action = QAction("Export as PDF", self)
        pdf_icon_path = resource_path("Icons/export_to_pdf.svg")
        if os.path.exists(pdf_icon_path):
            export_pdf_action.setIcon(QIcon(pdf_icon_path))
        export_pdf_action.triggered.connect(self.export_as_pdf_dialog)
        export_menu.addAction(export_pdf_action)
        
        self.export_btn.setMenu(export_menu)
        self.export_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        header_layout.addWidget(self.export_btn)
        
        diagram_layout.addLayout(header_layout)
        
        # Create enhanced graphics view for diagram
        self.diagram_view = QGraphicsView()
        self.diagram_scene = QGraphicsScene()
        self.diagram_view.setScene(self.diagram_scene)
        
        # Enhanced view settings for better interaction
        self.diagram_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.diagram_view.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.diagram_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.diagram_view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.diagram_view.setInteractive(True)
        
        # Enable mouse wheel zooming
        self.diagram_view.wheelEvent = self.enhanced_wheel_event
        
        self.diagram_view.setStyleSheet(f"""
            QGraphicsView {{
                background-color: {AppColors.BG_DARK};
                border: 1px solid {AppColors.BORDER_LIGHT};
                border-radius: 4px;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        """)
        self.diagram_view.setMinimumHeight(350)
        # Create splitter for diagram and status text
        diagram_splitter = QSplitter(Qt.Orientation.Vertical)
        diagram_splitter.setStyleSheet(f"""
            QSplitter {{
                background-color: {AppColors.BG_MEDIUM};
            }}
            QSplitter::handle {{
                background-color: {AppColors.BORDER_LIGHT};
                height: 3px;
                border-radius: 1px;
                margin: 2px 0px;
            }}
            QSplitter::handle:hover {{
                background-color: {AppColors.ACCENT_BLUE};
            }}
            QSplitter::handle:pressed {{
                background-color: {AppColors.ACCENT_BLUE};
            }}
        """)
        
        # Add diagram view to splitter
        diagram_splitter.addWidget(self.diagram_view)
        
        # Create status text area with resizable container
        status_container = QFrame()
        status_container.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.BG_MEDIUM};
                border: none;
                margin: 0px;
            }}
        """)
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 5, 0, 0)
        status_layout.setSpacing(2)
        
        # Status area header
        status_header = QLabel("Analysis Log")
        status_header.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.TEXT_LIGHT};
                font-size: 10px;
                font-weight: bold;
                margin: 2px 8px;
                padding: 0px;
            }}
        """)
        status_layout.addWidget(status_header)
        
        # Status text area (resizable)
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {AppColors.BG_DARK};
                border: 1px solid {AppColors.BORDER_LIGHT};
                border-radius: 4px;
                color: {AppColors.TEXT_SECONDARY};
                font-size: 12px;
                padding: 8px;
                margin: 0px 2px 2px 2px;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        """)
        self.status_text.setPlainText("Select a namespace and click Refresh to view apps")
        status_layout.addWidget(self.status_text)
        
        # Add status container to splitter
        diagram_splitter.addWidget(status_container)
        
        # Set splitter properties and constraints
        diagram_splitter.setCollapsible(0, False)  # Diagram view cannot be collapsed
        diagram_splitter.setCollapsible(1, False)  # Status text cannot be collapsed
        
        # Set initial sizes: diagram view takes most space, status text gets smaller portion
        diagram_splitter.setSizes([300, 80])  # Initial sizes
        
        # Set size constraints for the status area
        status_container.setMinimumHeight(50)   # Minimum height
        status_container.setMaximumHeight(200)  # Maximum height
        
        # Add splitter to main layout
        diagram_layout.addWidget(diagram_splitter)
        
        main_layout.addWidget(diagram_frame)
    
    
    
    def create_app_flow_diagram(self, app_flow):
        """Create visual representation of the app flow diagram (deprecated - use horizontal layout)"""
        # Redirect to horizontal layout method
        processed_data = self.business_logic.process_app_flow_data(app_flow)
        self.create_horizontal_app_flow_diagram(processed_data)
    
    
    def create_horizontal_app_flow_diagram(self, processed_data):
        """Create user-friendly horizontal app flow diagram with enhanced readability"""
        self.diagram_scene.clear()
        
        resources = processed_data.get("resources", [])
        if not resources:
            self.add_text_to_scene("No resources found in app flow", 10, 10, QColor(AppColors.TEXT_SECONDARY))
            return
        
        # Add resource summary at the top for better understanding
        self.add_resource_summary(resources)
        
        # Calculate positions using business logic
        positions = self.business_logic.calculate_horizontal_layout(resources)
        
        # Store positions and resources for live monitoring
        self.current_resource_positions = positions
        self.current_resources = resources
        
        # Draw simple box around pods first
        pod_resources = [r for r in resources if r.resource_type.value.lower() == 'pod']
        if pod_resources:
            self.draw_simple_pod_box(pod_resources, positions)
        
        # Add layer headers for better organization
        self.add_layer_headers(positions, resources)
        
        # Draw resources with K8s icons
        for resource in resources:
            key = f"{resource.resource_type.value}:{resource.name}"
            if key in positions:
                x, y = positions[key]
                self.draw_resource_with_icon(resource, x, y)
        
        # Draw connections with smart routing
        connections = processed_data.get("connections", [])
        logging.info(f"Drawing {len(connections)} connections for enhanced readability")
        logging.info(f"Available positions: {list(positions.keys())}")
        
        if not connections:
            logging.warning("No connections found in processed_data!")
        
        for connection in connections:
            # Handle both dict format and ConnectionInfo object format
            if hasattr(connection, 'from_resource'):
                from_key = connection.from_resource
                to_key = connection.to_resource
                connection_type = connection.connection_type
            else:
                from_key = connection.get("from")
                to_key = connection.get("to") 
                connection_type = connection.get("type")
            
            logging.info(f"Processing connection: {from_key} -> {to_key}")
            if from_key in positions and to_key in positions:
                from_pos = positions[from_key]
                to_pos = positions[to_key]
                logging.info(f"Drawing connection from {from_pos} to {to_pos}")
                self.draw_horizontal_connection(from_pos, to_pos, connection_type)
            else:
                logging.warning(f"Missing positions for connection: {from_key} -> {to_key}")
        
        # Enable live monitoring button if we have a valid graph
        if resources:
            self.live_monitor_btn.setEnabled(True)
    
    def add_resource_summary(self, resources):
        """Add a helpful resource summary at the top of the diagram"""
        # Count resources by type
        resource_counts = {}
        for resource in resources:
            resource_type = resource.resource_type.value
            resource_counts[resource_type] = resource_counts.get(resource_type, 0) + 1
        
        # Create summary text
        summary_parts = []
        for resource_type, count in resource_counts.items():
            summary_parts.append(f"{count} {resource_type.title()}{'s' if count > 1 else ''}")
        
        summary_text = f"Showing: {', '.join(summary_parts)} ({len(resources)} total resources)"
        
        # Add to diagram
        summary_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        summary_item = self.diagram_scene.addText(summary_text, summary_font)
        summary_item.setDefaultTextColor(QColor("#ffffff"))
        summary_item.setPos(60, 10)
    
    def add_layer_headers(self, positions, resources):
        """Add layer headers to show resource type organization"""
        # Determine layer X positions
        layer_positions = {}
        for resource in resources:
            key = f"{resource.resource_type.value}:{resource.name}"
            if key in positions:
                x, y = positions[key]
                resource_type = resource.resource_type.value
                if resource_type not in layer_positions:
                    layer_positions[resource_type] = x
        
        # Add headers
        header_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        for resource_type, x_pos in layer_positions.items():
            header_text = resource_type.title() + "s"
            header_item = self.diagram_scene.addText(header_text, header_font)
            header_item.setDefaultTextColor(QColor("#cccccc"))
            header_item.setPos(x_pos, 35)  # Above the resources
    
    def draw_simple_pod_box(self, pod_resources, positions):
        """Draw a simple box around all pods, aligned with deployment center"""
        if not pod_resources:
            self.pod_container_bounds = None
            return
        
        # Find deployment center Y to align pod box with it
        deployment_center_y = None
        for key, (x, y) in positions.items():
            if key.startswith("deployment:"):
                icon_height = 40
                deployment_center_y = y + icon_height // 2
                break
        
        # Calculate bounding box for all pods in their original positions
        pod_positions = []
        for pod in pod_resources:
            key = f"{pod.resource_type.value}:{pod.name}"
            if key in positions:
                x, y = positions[key]
                # Account for icon (40x40) and text on right side
                pod_positions.extend([(x, y), (x + 40, y + 40)])
        
        if not pod_positions:
            self.pod_container_bounds = None
            return
        
        # Calculate the current bounding box
        min_x = min(pos[0] for pos in pod_positions) - 15   # Small padding on left
        max_x = max(pos[0] for pos in pod_positions) + 120  # Extra space for text on right
        original_min_y = min(pos[1] for pos in pod_positions)
        original_max_y = max(pos[1] for pos in pod_positions)
        
        # Calculate the offset needed to align with deployment
        if deployment_center_y is not None:
            # Calculate current pod center and desired center
            current_pod_center_y = (original_min_y + original_max_y) / 2
            y_offset = deployment_center_y - current_pod_center_y
            
            # Apply the offset to pod positions
            for pod in pod_resources:
                key = f"{pod.resource_type.value}:{pod.name}"
                if key in positions:
                    x, y = positions[key]
                    positions[key] = (x, y + y_offset)  # Adjust pod position
            
            # Recalculate bounding box with adjusted positions
            pod_positions = []
            for pod in pod_resources:
                key = f"{pod.resource_type.value}:{pod.name}"
                if key in positions:
                    x, y = positions[key]
                    pod_positions.extend([(x, y), (x + 40, y + 40)])
            
            min_y = min(pos[1] for pos in pod_positions)
            max_y = max(pos[1] for pos in pod_positions)
            
            # Add padding around the adjusted pod positions
            centered_min_y = min_y - 30  # 30px padding
            centered_max_y = max_y + 30  # 30px padding
        else:
            # Fallback: use the original centering method
            pods_center_y = (original_min_y + original_max_y) / 2
            fixed_box_height = 120
            centered_min_y = pods_center_y - fixed_box_height / 2
            centered_max_y = pods_center_y + fixed_box_height / 2
            
            # If pods extend beyond the fixed height, expand the box symmetrically
            if original_min_y < centered_min_y:
                extra_space = centered_min_y - original_min_y + 15
                centered_min_y -= extra_space
                centered_max_y += extra_space
            
            if original_max_y > centered_max_y:
                extra_space = original_max_y - centered_max_y + 15
                centered_min_y -= extra_space
                centered_max_y += extra_space
        
        box_width = max_x - min_x
        box_height = centered_max_y - centered_min_y
        
        # Store pod container bounds for connection drawing
        self.pod_container_bounds = {
            'min_x': min_x,
            'max_x': max_x,
            'min_y': centered_min_y,
            'max_y': centered_max_y,
            'width': box_width,
            'height': box_height
        }
        
        # Draw simple box border only
        container_box = self.diagram_scene.addRect(
            min_x, centered_min_y, box_width, box_height,
            QPen(QColor("#666666"), 1),  # Simple gray border
            QBrush(Qt.BrushStyle.NoBrush)  # No fill
        )
        container_box.setZValue(-1)  # Put behind everything
    
    def draw_resource_with_icon(self, resource: ResourceInfo, x: float, y: float):
        """Draw resource with icon only (no boxes)"""
        # Standard icon size for all resources
        icon_width = 40
        icon_height = 40
        
        # Get appropriate icon path (with dynamic pod icons based on status)
        icon_path = self.get_resource_icon_path(resource.resource_type, resource.status)
        icon_item = None
        
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                # Scale icon consistently
                scaled_pixmap = pixmap.scaled(icon_width, icon_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon_item = self.diagram_scene.addPixmap(scaled_pixmap)
                icon_item.setPos(x, y)
                
                # Enable hover events and tooltip on the icon
                icon_item.setAcceptHoverEvents(True)
                tooltip_text = self.create_detailed_tooltip(resource)
                icon_item.setToolTip(tooltip_text)
        else:
            # Fallback: create a simple colored circle if icon not found
            fallback_color = self.get_pod_status_color(resource.status) if resource.resource_type.value.lower() == 'pod' else "#2196F3"
            icon_item = self.diagram_scene.addEllipse(
                x, y, icon_width, icon_height,
                QPen(QColor(fallback_color).darker(150), 2), 
                QBrush(QColor(fallback_color))
            )
            icon_item.setAcceptHoverEvents(True)
            tooltip_text = self.create_detailed_tooltip(resource)
            icon_item.setToolTip(tooltip_text)
        
        # Resource name positioning - right side for pods, below for others
        name_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        display_name = resource.name[:12] + "..." if len(resource.name) > 12 else resource.name
        name_text = self.diagram_scene.addText(display_name, name_font)
        name_text.setDefaultTextColor(QColor("#ffffff"))
        
        # Position text based on resource type
        is_pod = resource.resource_type.value.lower() == 'pod'
        if is_pod:
            # For pods: position text on the right side of the icon
            name_text.setPos(x + icon_width + 8, y + (icon_height - name_text.boundingRect().height()) // 2)
        else:
            # For other resources: center text below icon
            text_width = name_text.boundingRect().width()
            name_text.setPos(x + (icon_width - text_width) // 2, y + icon_height + 5)
        
        # Show status information for all resources
        status_color = self.get_status_color(resource.status)
        status_font = QFont("Segoe UI", 6, QFont.Weight.Bold)
        status_text = self.diagram_scene.addText(f"● {resource.status}", status_font)
        status_text.setDefaultTextColor(QColor(status_color))
        
        # Position status based on resource type
        if is_pod:
            # For pods: position status below the name on the right side
            status_text.setPos(x + icon_width + 8, y + (icon_height - name_text.boundingRect().height()) // 2 + 15)
        else:
            # For other resources: center status text below the name
            status_text_width = status_text.boundingRect().width()
            status_text.setPos(x + (icon_width - status_text_width) // 2, y + icon_height + 25)
        
        # Store full resource info for export purposes
        if icon_item:
            icon_item.setData(0, {
                'resource': resource,
                'full_name': resource.name,
                'export_data': self.create_export_resource_data(resource)
            })
    
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
    
    def get_pod_status_color(self, status: str) -> str:
        """Get color for pod circles - green for running, red for problems"""
        # Green for running/healthy pods
        healthy_statuses = ["Running", "Succeeded", "Ready"]
        
        # Red for problematic pods
        problem_statuses = ["Failed", "Error", "CrashLoopBackOff", "ImagePullBackOff", 
                           "ErrImagePull", "InvalidImageName", "CreateContainerConfigError",
                           "CreateContainerError", "RunContainerError", "KillContainerError",
                           "VerifyNonRootError", "RunInitContainerError", "CreatePodSandboxError",
                           "ConfigPodSandboxError", "KillPodSandboxError", "SetupNetworkError",
                           "TeardownNetworkError"]
        
        # Check if status indicates healthy pod
        if status in healthy_statuses:
            return "#4CAF50"  # Green
        
        # Check if status indicates problematic pod
        if status in problem_statuses:
            return "#F44336"  # Red
        
        # For other statuses like "Pending", "ContainerCreating", etc. use yellow/orange
        return "#FF9800"  # Orange/Yellow for unknown or transitional states
    
    def create_interactive_resource_group(self, main_rect, icon_item, resource: ResourceInfo, x: float, y: float, width: float, height: float):
        """Create interactive group with hover tooltips"""
        from PyQt6.QtWidgets import QGraphicsItemGroup, QGraphicsProxyWidget, QLabel
        
        # Enable hover events on the main rectangle
        main_rect.setAcceptHoverEvents(True)
        
        # Create detailed tooltip content
        tooltip_text = self.create_detailed_tooltip(resource)
        main_rect.setToolTip(tooltip_text)
        
        return main_rect
    
    def create_detailed_tooltip(self, resource: ResourceInfo) -> str:
        """Create detailed tooltip with all resource information"""
        tooltip_lines = [
            f"<b>{resource.name}</b>",
            f"<b>Type:</b> {resource.resource_type.value.title()}",
            f"<b>Namespace:</b> {resource.namespace}",
            f"<b>Status:</b> {resource.status}"
        ]
        
        # Add metadata information if available
        if hasattr(resource, 'metadata') and resource.metadata:
            metadata = resource.metadata
            
            # Add specific information based on resource type
            if resource.resource_type.value == 'deployment':
                if 'replicas' in metadata:
                    tooltip_lines.append(f"<b>Replicas:</b> {metadata.get('ready_replicas', 0)}/{metadata.get('replicas', 1)}")
                if 'containers' in metadata:
                    container_names = [c.get('name', 'unknown') for c in metadata['containers']]
                    tooltip_lines.append(f"<b>Containers:</b> {', '.join(container_names)}")
            
            elif resource.resource_type.value == 'service':
                if 'type' in metadata:
                    tooltip_lines.append(f"<b>Service Type:</b> {metadata['type']}")
                if 'ports' in metadata:
                    ports = [str(p.get('port', '?')) for p in metadata['ports']]
                    tooltip_lines.append(f"<b>Ports:</b> {', '.join(ports)}")
            
            elif resource.resource_type.value == 'pod':
                if 'phase' in metadata:
                    tooltip_lines.append(f"<b>Phase:</b> {metadata['phase']}")
                if 'containers' in metadata:
                    container_names = [c.get('name', 'unknown') for c in metadata['containers']]
                    tooltip_lines.append(f"<b>Containers:</b> {', '.join(container_names)}")
            
            elif resource.resource_type.value == 'ingress':
                if 'host' in metadata:
                    tooltip_lines.append(f"<b>Host:</b> {metadata['host']}")
                if 'path' in metadata:
                    tooltip_lines.append(f"<b>Path:</b> {metadata['path']}")
            
            # Add labels if available
            if 'labels' in metadata and metadata['labels']:
                labels_str = ', '.join([f"{k}={v}" for k, v in list(metadata['labels'].items())[:3]])
                if len(metadata['labels']) > 3:
                    labels_str += "..."
                tooltip_lines.append(f"<b>Labels:</b> {labels_str}")
        
        return "<br>".join(tooltip_lines)
    
    def create_export_resource_data(self, resource: ResourceInfo) -> dict:
        """Create comprehensive resource data for export"""
        export_data = {
            'name': resource.name,  # Full name, not truncated
            'type': resource.resource_type.value,
            'namespace': resource.namespace,
            'status': resource.status
        }
        
        # Add detailed metadata for export
        if hasattr(resource, 'metadata') and resource.metadata:
            export_data['metadata'] = resource.metadata
        
        return export_data
    
    def get_resource_icon_path(self, resource_type: ResourceType, status: str = None) -> str:
        """Get icon path for resource type, with dynamic pod icons based on status - fixed for build"""
        if resource_type == ResourceType.POD and status:
            # Dynamic pod icon selection based on status
            return self.get_pod_icon_path(status)
        
        icon_mapping = {
            ResourceType.INGRESS: "network.png",
            ResourceType.SERVICE: os.path.join("k8s_chart_icon", "svc.svg"), 
            ResourceType.DEPLOYMENT: os.path.join("k8s_chart_icon", "deploy.svg"),
            ResourceType.POD: os.path.join("k8s_chart_icon", "pod_running.svg"),
            ResourceType.CONFIGMAP: os.path.join("k8s_chart_icon", "cm.svg"),
            ResourceType.SECRET: "config.png",
            ResourceType.PVC: "storage.png"
        }
        
        icon_name = icon_mapping.get(resource_type, "workloads.png")
        # Use resource_path to properly resolve icon paths for packaged app
        return resource_path(os.path.join("Icons", icon_name))
    
    def get_pod_icon_path(self, status: str) -> str:
        """Get appropriate pod icon based on status - fixed for build"""
        # Running/healthy pods
        healthy_statuses = ["Running", "Succeeded", "Ready"]
        
        # Failed/problematic pods
        problem_statuses = ["Failed", "Error", "CrashLoopBackOff", "ImagePullBackOff", 
                           "ErrImagePull", "InvalidImageName", "CreateContainerConfigError",
                           "CreateContainerError", "RunContainerError", "KillContainerError",
                           "VerifyNonRootError", "RunInitContainerError", "CreatePodSandboxError",
                           "ConfigPodSandboxError", "KillPodSandboxError", "SetupNetworkError",
                           "TeardownNetworkError"]
        
        if status in healthy_statuses:
            icon_name = os.path.join("k8s_chart_icon", "pod_running.svg")
        elif status in problem_statuses:
            icon_name = os.path.join("k8s_chart_icon", "pod_failed.svg")
        else:
            # Pending, ContainerCreating, etc.
            icon_name = os.path.join("k8s_chart_icon", "pod_pending.svg")
        
        # Use resource_path to properly resolve icon paths for packaged app
        return resource_path(os.path.join("Icons", icon_name))
    
    def draw_horizontal_connection(self, from_pos: tuple, to_pos: tuple, connection_type: str):
        """Draw enhanced horizontal connection with smart routing to reduce overlaps"""
        from_x, from_y = from_pos
        to_x, to_y = to_pos
        
        # All resources now use 40x40 pixel icons
        icon_width = 40
        icon_height = 40
        
        # Calculate center points for icon-based connections
        from_center_x = from_x + icon_width // 2
        from_center_y = from_y + icon_height // 2
        to_center_x = to_x + icon_width // 2
        to_center_y = to_y + icon_height // 2
        
        # Smart connection routing to reduce overlaps
        if connection_type == "deployment_to_pod":
            # From deployment center to pod box with curved routing
            from_point_x = from_x + icon_width
            from_point_y = from_center_y
            
            if hasattr(self, 'pod_container_bounds') and self.pod_container_bounds:
                to_point_x = self.pod_container_bounds['min_x']
                to_point_y = from_point_y  # Keep horizontal alignment
            else:
                to_point_x = to_x
                to_point_y = from_point_y
                
        elif connection_type in ["pod_to_config", "pod_to_secret", "pod_to_pvc"]:
            # From pod box RIGHT EDGE to config resource center for proper visual flow
            if hasattr(self, 'pod_container_bounds') and self.pod_container_bounds:
                # Use pod container boundary for more accurate connection point
                from_point_x = self.pod_container_bounds['max_x']
                from_point_y = from_center_y
            else:
                # Fallback to pod icon right edge
                from_point_x = from_x + icon_width
                from_point_y = from_center_y
            
            # To config resource center
            to_point_x = to_center_x  
            to_point_y = to_center_y
            
            # Add vertical offset based on connection type to prevent overlaps
            type_offset = {
                "pod_to_config": -15,    # Slightly above center
                "pod_to_secret": 0,      # At center 
                "pod_to_pvc": 15         # Slightly below center
            }.get(connection_type, 0)
            
            from_point_y += type_offset
            to_point_y += type_offset
            
        else:
            # Default center-to-center routing for service-to-deployment connections
            from_point_x = from_center_x
            from_point_y = from_center_y
            to_point_x = to_center_x
            to_point_y = to_center_y
        
        # Enhanced color mapping with better visibility
        color_map = {
            "ingress_to_service": "#E91E63",    # Pink
            "service_to_deployment": "#28a745",  # Green
            "deployment_to_pod": "#007acc",     # Blue
            "pod_to_config": "#4CAF50",         # Light Green
            "pod_to_secret": "#FF9800",         # Orange
            "pod_to_pvc": "#9C27B0"             # Purple
        }
        
        color = color_map.get(connection_type, "#666666")
        
        # Draw smarter connection lines with reduced visual noise
        if abs(from_point_y - to_point_y) < 5:
            # Straight horizontal line for aligned connections
            main_line = self.diagram_scene.addLine(
                from_point_x, from_point_y,
                to_point_x, to_point_y,
                QPen(QColor(color), 2)  # Slightly thinner lines
            )
        else:
            # Curved path for non-aligned connections to reduce crossing
            self.draw_curved_connection(from_point_x, from_point_y, to_point_x, to_point_y, color)
        
        # Draw enhanced arrow head
        self.draw_enhanced_arrow_head(to_point_x, to_point_y, from_point_x, from_point_y, color)
        
        # Simplified connection labels - only show on hover or for important connections
        if connection_type in ["ingress_to_service", "service_to_deployment"]:
            self.add_connection_label(from_point_x, from_point_y, to_point_x, to_point_y, connection_type)
    
    def draw_curved_connection(self, from_x: float, from_y: float, to_x: float, to_y: float, color: str):
        """Draw a curved connection to avoid overlapping straight lines"""
        from PyQt6.QtGui import QPainterPath
        from PyQt6.QtWidgets import QGraphicsPathItem
        
        # Create curved path
        path = QPainterPath()
        path.moveTo(from_x, from_y)
        
        # Calculate control points for smooth curve
        mid_x = (from_x + to_x) / 2
        control1_x = from_x + (to_x - from_x) * 0.3
        control2_x = from_x + (to_x - from_x) * 0.7
        
        # Add slight curve to avoid overlaps
        if from_y != to_y:
            curve_offset = (to_y - from_y) * 0.3
            path.cubicTo(
                control1_x, from_y + curve_offset,
                control2_x, to_y - curve_offset,
                to_x, to_y
            )
        else:
            # Gentle arc for same-level connections
            path.quadTo(mid_x, from_y - 20, to_x, to_y)
        
        # Add curved path to scene
        path_item = QGraphicsPathItem(path)
        path_item.setPen(QPen(QColor(color), 2))
        self.diagram_scene.addItem(path_item)
    
    def add_connection_label(self, from_x: float, from_y: float, to_x: float, to_y: float, connection_type: str):
        """Add simplified connection label for key connections only"""
        mid_x = from_x + (to_x - from_x) / 2
        mid_y = from_y + (to_y - from_y) / 2 - 15
        
        # Simplified labels
        label_map = {
            "ingress_to_service": "↳",
            "service_to_deployment": "→",
            "deployment_to_pod": "⬇",
            "pod_to_config": "⚙",
            "pod_to_secret": "🔐",
            "pod_to_pvc": "💾"
        }
        
        label = label_map.get(connection_type, "→")
        label_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        label_text = self.diagram_scene.addText(label, label_font)
        label_text.setDefaultTextColor(QColor("#ffffff"))
        
        # Position label
        text_width = label_text.boundingRect().width()
        text_height = label_text.boundingRect().height()
        label_text.setPos(mid_x - text_width / 2, mid_y - text_height / 2)
    
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
        """Export enhanced graph as image with full details (PNG/JPEG)"""
        try:
            # Export the current display directly without modification
            scene_rect = self.diagram_scene.itemsBoundingRect()
            
            # Ensure scene has content
            if scene_rect.isEmpty():
                raise Exception("No content to export")
            
            # Create high-quality pixmap with extra margins
            margin = 60
            pixmap = QPixmap(int(scene_rect.width() + margin*2), int(scene_rect.height() + margin*2))
            pixmap.fill(QColor("#1e1e1e"))  # Use dark background matching app display
            
            # Render scene to pixmap with enhanced quality
            painter = QPainter()
            if painter.begin(pixmap):
                try:
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                    
                    # Create target rect with margins
                    target_rect = QRectF(margin, margin, scene_rect.width(), scene_rect.height())
                    self.diagram_scene.render(painter, target_rect, scene_rect)
                    
                    # Add export metadata
                    self.add_export_metadata_to_image(painter, pixmap.width(), pixmap.height())
                    
                finally:
                    painter.end()
            else:
                raise Exception("Failed to initialize painter")
            
            # Save high-quality pixmap
            if not pixmap.save(file_path, format_type, 95):  # High quality
                raise Exception(f"Failed to save image as {format_type}")
                
        except Exception as e:
            raise Exception(f"Export failed: {str(e)}")
    
    def export_as_pdf(self, file_path: str):
        """Export graph as PDF"""
        try:
            from PyQt6.QtPrintSupport import QPrinter
            from PyQt6.QtGui import QPageSize, QPageLayout
            
            # Export the current display directly without modification
            
            # Get scene bounding rect with padding to prevent clipping
            scene_rect = self.diagram_scene.itemsBoundingRect()
            
            # Add padding to ensure all content is visible (especially right side)
            padding = 50
            scene_rect = scene_rect.adjusted(-padding, -padding, padding, padding)
            
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
                    
                    # Fill page with white background for PDF
                    painter.fillRect(page_rect, QColor("#ffffff"))
                    
                    # Add title heading to PDF
                    painter.setPen(QColor("#000000"))
                    painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
                    deployment_name = self.resource_combo.currentText() if self.resource_combo.currentText() != "Select namespace and workload first" else "Unknown"
                    title = f"Kubernetes App Flow - {deployment_name}"
                    painter.drawText(20, 40, title)
                    
                    # Adjust page rect to account for title space
                    adjusted_page_rect = QRectF(page_rect.x(), page_rect.y() + 60, page_rect.width(), page_rect.height() - 60)
                    
                    # Temporarily adjust text colors for PDF visibility
                    self.adjust_text_colors_for_pdf(True)
                    
                    # Render the diagram
                    self.diagram_scene.render(painter, adjusted_page_rect, scene_rect)
                    
                    # Restore original text colors
                    self.adjust_text_colors_for_pdf(False)
                    
                    # Add timestamp at bottom
                    painter.setFont(QFont("Segoe UI", 10))
                    timestamp = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    painter.drawText(20, int(page_rect.height() - 20), timestamp)
                    
                finally:
                    painter.end()
            else:
                raise Exception("Failed to initialize PDF painter")
                
        except Exception as e:
            raise Exception(f"PDF export failed: {str(e)}")
    
    def adjust_text_colors_for_pdf(self, for_pdf: bool):
        """Temporarily adjust text colors for better PDF visibility"""
        try:
            for item in self.diagram_scene.items():
                if hasattr(item, 'setDefaultTextColor'):
                    if for_pdf:
                        # Set to black for PDF visibility
                        item.setDefaultTextColor(QColor("#000000"))
                    else:
                        # Restore to white for app display
                        item.setDefaultTextColor(QColor("#ffffff"))
        except Exception as e:
            logging.warning(f"Error adjusting text colors: {e}")
    
    def create_export_version_of_graph(self):
        """No longer needed - we export the current display directly"""
        pass
    
    def create_export_horizontal_diagram(self, processed_data):
        """Create horizontal diagram optimized for export with full names"""
        self.diagram_scene.clear()
        
        resources = processed_data.get("resources", [])
        if not resources:
            return
        
        # Calculate positions using business logic
        positions = self.business_logic.calculate_horizontal_layout(resources)
        
        # Draw simple box around pods first (same as normal diagram)
        pod_resources = [r for r in resources if r.resource_type.value.lower() == 'pod']
        if pod_resources:
            self.draw_export_pod_box(pod_resources, positions)
        
        # Draw resources with full names for export
        for resource in resources:
            key = f"{resource.resource_type.value}:{resource.name}"
            if key in positions:
                x, y = positions[key]
                self.draw_export_resource_with_icon(resource, x, y)
        
        # Draw connections
        for connection in processed_data.get("connections", []):
            # Handle both dict format and ConnectionInfo object format
            if hasattr(connection, 'from_resource'):
                from_key = connection.from_resource
                to_key = connection.to_resource
                connection_type = connection.connection_type
            else:
                from_key = connection.get("from")
                to_key = connection.get("to") 
                connection_type = connection.get("type")
                
            if from_key in positions and to_key in positions:
                from_pos = positions[from_key]
                to_pos = positions[to_key]
                self.draw_horizontal_connection(from_pos, to_pos, connection_type)
    
    def draw_export_pod_box(self, pod_resources, positions):
        """Draw pod container box optimized for export with darker border, aligned with deployment center"""
        if not pod_resources:
            return
        
        # Find deployment center Y to align pod box with it
        deployment_center_y = None
        for key, (x, y) in positions.items():
            if key.startswith("deployment:"):
                icon_height = 45  # Export icon size
                deployment_center_y = y + icon_height // 2
                break
        
        # Calculate bounding box for all pods in their original positions
        pod_positions = []
        for pod in pod_resources:
            key = f"{pod.resource_type.value}:{pod.name}"
            if key in positions:
                x, y = positions[key]
                # Account for icon (45x45) and text on right side for export
                pod_positions.extend([(x, y), (x + 45, y + 45)])
        
        if not pod_positions:
            return
        
        # Calculate the current bounding box
        min_x = min(pos[0] for pos in pod_positions) - 20   # More padding for export
        max_x = max(pos[0] for pos in pod_positions) + 120  # Extra space for text on right
        original_min_y = min(pos[1] for pos in pod_positions)
        original_max_y = max(pos[1] for pos in pod_positions)
        
        # Calculate the offset needed to align with deployment
        if deployment_center_y is not None:
            # Calculate current pod center and desired center
            current_pod_center_y = (original_min_y + original_max_y) / 2
            y_offset = deployment_center_y - current_pod_center_y
            
            # Apply the offset to pod positions
            for pod in pod_resources:
                key = f"{pod.resource_type.value}:{pod.name}"
                if key in positions:
                    x, y = positions[key]
                    positions[key] = (x, y + y_offset)  # Adjust pod position
            
            # Recalculate bounding box with adjusted positions
            pod_positions = []
            for pod in pod_resources:
                key = f"{pod.resource_type.value}:{pod.name}"
                if key in positions:
                    x, y = positions[key]
                    pod_positions.extend([(x, y), (x + 45, y + 45)])
            
            min_y = min(pos[1] for pos in pod_positions)
            max_y = max(pos[1] for pos in pod_positions)
            
            # Add padding around the adjusted pod positions
            centered_min_y = min_y - 35  # 35px padding for export
            centered_max_y = max_y + 35  # 35px padding for export
        else:
            # Fallback: use the original centering method
            pods_center_y = (original_min_y + original_max_y) / 2
            fixed_box_height = 140
            centered_min_y = pods_center_y - fixed_box_height / 2
            centered_max_y = pods_center_y + fixed_box_height / 2
            
            # If pods extend beyond the fixed height, expand the box symmetrically
            if original_min_y < centered_min_y:
                extra_space = centered_min_y - original_min_y + 20
                centered_min_y -= extra_space
                centered_max_y += extra_space
            
            if original_max_y > centered_max_y:
                extra_space = original_max_y - centered_max_y + 20
                centered_min_y -= extra_space
                centered_max_y += extra_space
        
        box_width = max_x - min_x
        box_height = centered_max_y - centered_min_y
        
        # Draw container box with darker border for export visibility
        container_box = self.diagram_scene.addRect(
            min_x, centered_min_y, box_width, box_height,
            QPen(QColor("#333333"), 2),  # Darker, thicker border for export visibility
            QBrush(Qt.BrushStyle.NoBrush)  # No fill
        )
        container_box.setZValue(-1)  # Put behind everything
    
    def draw_export_resource_with_icon(self, resource: ResourceInfo, x: float, y: float):
        """Draw resource for export with icon only (no boxes)"""
        # Standard icon size for export
        icon_width = 45
        icon_height = 45
        
        # Get appropriate icon path (with dynamic pod icons based on status)
        icon_path = self.get_resource_icon_path(resource.resource_type, resource.status)
        icon_item = None
        
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                # Scale icon for export
                scaled_pixmap = pixmap.scaled(icon_width, icon_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon_item = self.diagram_scene.addPixmap(scaled_pixmap)
                icon_item.setPos(x, y)
        else:
            # Fallback: create a simple colored circle if icon not found
            fallback_color = self.get_pod_status_color(resource.status) if resource.resource_type.value.lower() == 'pod' else "#2196F3"
            icon_item = self.diagram_scene.addEllipse(
                x, y, icon_width, icon_height,
                QPen(QColor(fallback_color).darker(150), 2), 
                QBrush(QColor(fallback_color))
            )
        
        # Resource name positioned below the icon
        name_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        display_name = resource.name[:12] + "..." if len(resource.name) > 12 else resource.name
        name_text = self.diagram_scene.addText(display_name, name_font)
        name_text.setDefaultTextColor(QColor("#000000"))  # Dark color for PDF visibility
        text_width = name_text.boundingRect().width()
        name_text.setPos(x + (icon_width - text_width) // 2, y + icon_height + 5)
        
        # Status information below name
        status_color = self.get_status_color(resource.status)
        status_font = QFont("Segoe UI", 7, QFont.Weight.Bold)
        status_text = self.diagram_scene.addText(f"● {resource.status}", status_font)
        status_text.setDefaultTextColor(QColor(status_color))
        status_text_width = status_text.boundingRect().width()
        status_text.setPos(x + (icon_width - status_text_width) // 2, y + icon_height + 25)
    
    def add_export_metadata_to_image(self, painter: QPainter, width: int, height: int):
        """Add metadata information to exported image"""
        # Add title and timestamp - Use white color for dark background visibility
        painter.setPen(QColor("#ffffff"))  # White text for dark background
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        
        # Use deployment name instead of namespace in title
        deployment_name = self.resource_combo.currentText() if self.resource_combo.currentText() != "Select namespace and workload first" else "Unknown"
        title = f"Kubernetes App Flow - {deployment_name}"
        painter.drawText(20, 30, title)
        
        # Add timestamp
        painter.setFont(QFont("Segoe UI", 8))
        timestamp = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        painter.drawText(20, height - 20, timestamp)
        
        # Add resource count
        if self.current_app_flow_data:
            total_resources = (len(self.current_app_flow_data.get("ingresses", [])) + 
                             len(self.current_app_flow_data.get("services", [])) + 
                             len(self.current_app_flow_data.get("deployments", [])) + 
                             len(self.current_app_flow_data.get("pods", [])) + 
                             len(self.current_app_flow_data.get("configmaps", [])) + 
                             len(self.current_app_flow_data.get("secrets", [])) + 
                             len(self.current_app_flow_data.get("pvcs", [])))
            
            resource_info = f"Total Resources: {total_resources}"
            painter.drawText(width - 200, height - 20, resource_info)
    
    def restore_original_graph(self):
        """No longer needed - we export the current display directly"""
        pass

    def enhanced_wheel_event(self, event):
        """Enhanced wheel event for smooth zooming"""
        try:
            # Enable zooming with or without Ctrl for better usability
            enable_zoom = True
            
            if enable_zoom:
                # Zoom in/out
                zoom_in_factor = 1.15  # Slightly smoother zoom
                zoom_out_factor = 1 / zoom_in_factor
                
                # Save the scene pos
                old_pos = self.diagram_view.mapToScene(event.position().toPoint())
                
                # Zoom
                if event.angleDelta().y() > 0:
                    zoom_factor = zoom_in_factor
                else:
                    zoom_factor = zoom_out_factor
                
                self.diagram_view.scale(zoom_factor, zoom_factor)
                
                # Get the new position
                new_pos = self.diagram_view.mapToScene(event.position().toPoint())
                
                # Move scene to old position
                delta = new_pos - old_pos
                self.diagram_view.translate(delta.x(), delta.y())
                
                event.accept()
            else:
                # Default scroll behavior
                super(QGraphicsView, self.diagram_view).wheelEvent(event)
        except Exception as e:
            logging.warning(f"Wheel event error: {e}")
            super(QGraphicsView, self.diagram_view).wheelEvent(event)
    
    def add_text_to_scene(self, text, x, y, color):
        """Add text to the scene"""
        text_item = self.diagram_scene.addText(text, QFont("Arial", 12))
        text_item.setDefaultTextColor(color)
        text_item.setPos(x, y)
    
    def clear_for_cluster_change(self):
        """Clear namespace state when cluster changes to prevent stale namespace data"""
        logging.debug("Clearing AppsPage state for cluster change")
        
        # Clear namespace dropdown to prevent showing stale namespaces
        if hasattr(self, 'namespace_combo') and self.namespace_combo:
            self.namespace_combo.blockSignals(True)
            self.namespace_combo.clear()
            self.namespace_combo.addItem("Loading namespaces...")
            self.namespace_combo.setEnabled(False)
            self.namespace_combo.blockSignals(False)
            
        # Clear workload-dependent dropdowns
        if hasattr(self, 'resource_combo') and self.resource_combo:
            self.resource_combo.clear()
            self.resource_combo.addItem("Select namespace and workload first")
            self.resource_combo.setEnabled(False)
            
        # Clear any cached namespace signal connections
        if hasattr(self, '_namespace_signals_connected'):
            delattr(self, '_namespace_signals_connected')
            
        # Clear current app flow data
        self.current_app_flow_data = None
        self.current_resource_positions = {}
        
        # Stop live monitoring if active
        if self.live_monitoring_enabled:
            self.live_monitor_timer.stop()
            self.live_monitoring_enabled = False
            self.live_monitor_btn.setText("▶ Start Live")
            self.live_monitor_btn.setStyleSheet("""
                QPushButton { 
                    background-color: #28a745; 
                    color: #ffffff; 
                    border: 1px solid #34ce57;
                    border-radius: 4px; 
                    padding: 3px 8px; 
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover { 
                    background-color: #34ce57; 
                }
                QPushButton:pressed { 
                    background-color: #1e7e34; 
                }
                QPushButton:disabled {
                    background-color: #6c757d;
                    border-color: #6c757d;
                    color: #dee2e6;
                }
            """)
            
        # Clear diagram
        if hasattr(self, 'diagram_scene') and self.diagram_scene:
            self.diagram_scene.clear()
            
        # Reset diagram title
        if hasattr(self, 'diagram_title') and self.diagram_title:
            self.diagram_title.setText("App Diagram")
            
        # Reload namespaces for the new cluster
        QTimer.singleShot(200, self.load_namespaces)