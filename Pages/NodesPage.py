"""
NodesPage - Kubernetes Nodes Management Interface

Clean, efficient implementation for managing Kubernetes cluster nodes.
Features:
- Real-time node metrics with accurate disk usage from cluster data
- Colored status indicators and usage percentages  
- Interactive graphs and detail pages
- Node management actions (drain, cordon)
- Optimized search and filtering
- No dummy data - all metrics from real Kubernetes APIs
"""

import logging
from datetime import datetime, timezone
import time
from collections import deque

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QFrame, QTableWidgetItem, QMessageBox, QVBoxLayout, QWidget, QSizePolicy, QApplication
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QColor, QBrush, QPainter, QPen, QFont

from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors
from UI.Icons import Icons, resource_path
# Removed unused format_age import



class NodeMetricsGraph(QWidget):
    """Custom line graph widget for displaying node metrics over time"""
    
    def __init__(self, title: str, color: str, max_data_points: int = 20):
        super().__init__()
        self.graph_title = title
        self.graph_color = QColor(color)
        self.max_data_points = max_data_points
        self.data_points = deque(maxlen=max_data_points)
        self.timestamps = deque(maxlen=max_data_points)
        self.current_value = 0.0
        
        self.setMinimumSize(250, 140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {AppColors.CARD_BG};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
            }}
        """)
    
    def add_data_point(self, value: float):
        """Add a new data point to the graph"""
        self.current_value = value
        self.data_points.append(value)
        self.timestamps.append(time.time())
        self.update()  # Trigger repaint
    
    def clear_data(self):
        """Clear all data points"""
        self.data_points.clear()
        self.timestamps.clear()
        self.current_value = 0.0
        self.update()
    
    def paintEvent(self, event):  
        """Custom paint event to draw the line graph"""
        del event  # Required by PyQt6 but not used
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        margin = 15
        left_margin = 40  # Extra space for Y-axis labels
        bottom_margin = 40  # Extra space for time labels
        graph_rect = QRect(left_margin, margin + 20, rect.width() - left_margin - margin, rect.height() - margin - 20 - bottom_margin)
        
        # Draw background
        painter.fillRect(rect, QColor(AppColors.CARD_BG))
        
        # Draw title
        painter.setPen(QPen(QColor(AppColors.TEXT_LIGHT), 1))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(margin, 15, self.graph_title)
        
        # Draw current value
        painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        painter.setPen(QPen(self.graph_color, 1))
        value_text = f"{self.current_value:.1f}%"
        painter.drawText(rect.width() - 60, 15, value_text)
        
        if len(self.data_points) == 0:
            # No data to draw
            painter.setPen(QPen(QColor(AppColors.TEXT_SUBTLE), 1))
            painter.setFont(QFont("Arial", 9))
            painter.drawText(graph_rect.center().x() - 30, graph_rect.center().y(), "Click node to view metrics")
            return
        elif len(self.data_points) == 1:
            # Single data point - draw as a point with label
            painter.setPen(QPen(self.graph_color, 2))
            painter.setBrush(self.graph_color)
            
            x = graph_rect.center().x()
            y = graph_rect.bottom() - int((self.data_points[0] * graph_rect.height()) // 100)
            painter.drawEllipse(int(x) - 4, int(y) - 4, 8, 8)
            
            # Draw connecting line to show trend start
            painter.setPen(QPen(self.color, 1))
            painter.drawLine(graph_rect.left() + 20, int(y), graph_rect.right() - 20, int(y))
            return
        
        # Draw grid lines
        painter.setPen(QPen(QColor(AppColors.BORDER_COLOR), 1))
        for i in range(5):
            y = graph_rect.top() + i * graph_rect.height() // 4
            painter.drawLine(graph_rect.left(), y, graph_rect.right(), y)
        
        # Draw Y-axis labels (0%, 25%, 50%, 75%, 100%)
        painter.setPen(QPen(QColor(AppColors.TEXT_SUBTLE), 1))
        painter.setFont(QFont("Arial", 8))
        for i in range(5):
            y = graph_rect.top() + i * graph_rect.height() // 4
            label = f"{100 - i * 25}%"
            painter.drawText(5, y + 3, label)
        
        # Draw X-axis time labels if we have data points with timestamps
        if len(self.data_points) > 1 and len(self.timestamps) > 1:
            painter.setPen(QPen(QColor(AppColors.TEXT_SUBTLE), 1))
            painter.setFont(QFont("Arial", 7))
            
            import datetime
            
            # Show real time labels for first, middle, and last points
            for i in [0, len(self.data_points) // 2, len(self.data_points) - 1]:
                if i < len(self.timestamps):
                    # Convert timestamp to real time format
                    dt = datetime.datetime.fromtimestamp(self.timestamps[i])
                    time_label = dt.strftime("%H:%M:%S")
                    
                    x = graph_rect.left() + (i * graph_rect.width()) // (len(self.data_points) - 1)
                    painter.drawText(x - 15, graph_rect.bottom() + 15, time_label)
        
        # Draw the line graph
        if len(self.data_points) > 1:
            painter.setPen(QPen(self.graph_color, 2))
            
            points = []
            for i, value in enumerate(self.data_points):
                if len(self.data_points) == 1:
                    x = graph_rect.center().x()
                else:
                    x = graph_rect.left() + (i * graph_rect.width()) // (len(self.data_points) - 1)
                y = graph_rect.bottom() - int((value * graph_rect.height()) // 100)
                points.append((int(x), int(y)))
            
            # Draw the line
            for i in range(len(points) - 1):
                painter.drawLine(int(points[i][0]), int(points[i][1]), int(points[i + 1][0]), int(points[i + 1][1]))
            
            # Draw data points
            painter.setBrush(self.graph_color)
            for x, y in points:
                painter.drawEllipse(int(x) - 2, int(y) - 2, 4, 4)
        
        painter.end()


class NodesPage(BaseResourcePage):
    """
    Kubernetes Nodes Management Page
    
    High-performance implementation with:
    - Lazy-loading disk usage for sub-second table loading
    - Batch metrics caching for 50+ nodes optimization
    - Real-time node metrics graphs
    - Progressive loading with background data fetching
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "nodes"
        self.namespace_filter = "All Namespaces"  # Nodes are cluster-scoped
        self.show_namespace_dropdown = False
        
        self.metrics_widget = None
        self.selected_node_name = None
        
        # Performance optimization - batch metrics caching
        self.metrics_cache = {}
        self.last_cache_update_time = 0
        self.cache_ttl_seconds = 30
        
        # Lazy loading configuration for optimal performance
        self.is_disk_usage_enabled = True
        self.is_lazy_loading_enabled = True
        self.is_disk_loading_in_progress = False
        self.is_table_population_in_progress = False
        
        # Node metrics graphs for real-time monitoring
        self.cpu_metrics_graph = None
        self.memory_metrics_graph = None
        self.disk_metrics_graph = None
        
        # Timer for real-time graph updates
        self.metrics_update_timer = QTimer()
        self.metrics_update_timer.timeout.connect(self._update_node_metrics_graphs)
        
        self._setup_ui()
        self._setup_table_styling()
        
        # Debug wrapper removed - table sorting issue was fixed
        self._setup_table_interactions()
        
        # Ensure unified resource loader connection is active
        self._connect_to_unified_loader()
        
        logging.info("NodesPage: Initialized successfully")
    
    def _setup_ui(self):
        """Initialize the main UI components"""
        try:
            headers = self.get_headers()
            # Enable sorting for all columns except Name (column 0) and Actions (column 8)
            sortable_columns = {1, 2, 3, 4, 5, 6, 7}  # CPU, Memory, Disk, Roles, Version, Age, Status
            super().setup_ui("Nodes", headers, sortable_columns)
            
            # Disable node-specific functionality not applicable for nodes
            self.show_select_all = False
            self.show_delete_button = False
            
            # Initialize UI components with proper timing
            QTimer.singleShot(50, self._verify_table_setup)
            QTimer.singleShot(100, self._hide_node_specific_elements)
            QTimer.singleShot(200, self._create_metrics_graphs)
            QTimer.singleShot(500, self._finalize_ui_setup)
            
            # Hide namespace dropdown (nodes are cluster-scoped)
            if hasattr(self, 'namespace_combo') and self.namespace_combo:
                self.namespace_combo.hide()
                
        except Exception as e:
            logging.error(f"NodesPage: Failed to setup UI: {e}")
    
    def _verify_table_setup(self):
        """Verify table is properly set up"""
        try:
            if not hasattr(self, 'table') or not self.table:
                logging.error("NodesPage: Table not found during verification")
                return
            
            headers = self.get_headers()
            if self.table.columnCount() != len(headers):
                logging.error(f"NodesPage: Column count mismatch - expected {len(headers)}, got {self.table.columnCount()}")
                return
            
            # Verify headers are set correctly
            for i, expected_header in enumerate(headers):
                item = self.table.horizontalHeaderItem(i)
                if not item or item.text() != expected_header:
                    logging.warning(f"NodesPage: Header mismatch at column {i} - expected '{expected_header}', got '{item.text() if item else None}'")
            
            logging.info(f"NodesPage: Table verification complete - {len(headers)} columns configured")
            
        except Exception as e:
            logging.error(f"NodesPage: Error during table verification: {e}")
    
    def _finalize_ui_setup(self):
        """Final UI setup after all components are initialized"""
        try:
            # Ensure all node-specific elements are properly hidden
            self._hide_node_specific_elements()
            logging.info("NodesPage: UI setup finalized")
        except Exception as e:
            logging.error(f"NodesPage: Error in final UI setup: {e}")
    
    def _hide_node_specific_elements(self):
        """Hide UI elements not applicable for nodes"""
        try:
            # Find and hide delete button more thoroughly
            self._find_and_hide_delete_elements()
            
            # Hide select-all checkbox  
            if hasattr(self, 'select_all_checkbox') and self.select_all_checkbox:
                self.select_all_checkbox.hide()
                self.select_all_checkbox.setVisible(False)
                
            logging.debug("NodesPage: Hidden node-specific UI elements")
        except Exception as e:
            logging.error(f"NodesPage: Error hiding UI elements: {e}")
    
    def _find_and_hide_delete_elements(self):
        """Hide delete-related elements"""
        try:
            # Hide direct delete button reference
            if hasattr(self, 'delete_button') and self.delete_button:
                self._hide_element(self.delete_button, "direct delete button")
            
            # Hide delete elements recursively
            self._hide_delete_widgets_recursive(self)
            
        except Exception as e:
            logging.error(f"NodesPage: Error hiding delete elements: {e}")
    
    def _hide_element(self, element, description="element"):
        """Hide and disable a UI element"""
        element.hide()
        element.setVisible(False)
        element.setEnabled(False)
        logging.debug(f"NodesPage: Hidden {description}")
    
    def _hide_delete_widgets_recursive(self, widget):
        """Recursively hide delete-related widgets"""
        try:
            if not hasattr(widget, 'children'):
                return
                
            for child in widget.children():
                # Check for delete-related keywords in various properties
                keywords = ['delete', 'remove', 'selected']
                
                if self._widget_contains_keywords(child, keywords):
                    self._hide_element(child, f"widget with delete keyword")
                
                # Continue recursively
                self._hide_delete_widgets_recursive(child)
                
        except Exception:
            pass  # Ignore errors in recursive traversal
    
    def _widget_contains_keywords(self, widget, keywords):
        """Check if widget contains any of the specified keywords"""
        properties_to_check = [
            (hasattr(widget, 'text') and widget.text(), 'text'),
            (hasattr(widget, 'toolTip') and widget.toolTip(), 'tooltip'),
            (hasattr(widget, 'objectName') and widget.objectName(), 'objectName')
        ]
        
        for prop_value, _ in properties_to_check:
            if prop_value and any(keyword in prop_value.lower() for keyword in keywords):
                return True
        return False
    
    def _setup_table_styling(self):
        """Setup custom table styling and interactions"""
        QTimer.singleShot(200, self._apply_table_configuration)
    
    def _apply_table_configuration(self):
        """Apply table styles and connect events"""
        try:
            if not hasattr(self, 'table') or not self.table:
                return
                
            # Apply custom styling
            custom_style = f"""
                QTableWidget {{
                    background-color: {AppColors.CARD_BG};
                    border: none;
                    gridline-color: transparent;
                    outline: none;
                    selection-background-color: rgba(53, 132, 228, 0.15);
                    alternate-background-color: transparent;
                }}
                QTableWidget::item {{
                    border: none;
                    padding: 8px;
                }}
            """
            self.table.setStyleSheet(custom_style)
            
            # Connect interaction events
            self.table.itemDoubleClicked.connect(self._on_row_double_click)
            self.table.itemClicked.connect(self._on_row_single_click)
            
            logging.info("NodesPage: Applied table configuration")
        except Exception as e:
            logging.error(f"NodesPage: Failed to configure table: {e}")
    
    def _setup_table_interactions(self):
        """Setup table interactions - now handled in _apply_table_configuration"""
        pass  # Merged into _apply_table_configuration
    
    def _on_row_double_click(self, item):
        """Handle double-click to open node detail page"""
        try:
            if item and item.row() >= 0:
                node_name = self._get_node_name_from_row(item.row())
                if node_name:
                    logging.info(f"NodesPage: Opening detail page for node '{node_name}'")
                    self._open_node_details(node_name)
        except Exception as e:
            logging.error(f"NodesPage: Error handling row double-click: {e}")
    
    def _on_row_single_click(self, item):
        """Handle single-click for selection feedback and graph update"""
        try:
            if item and item.row() >= 0:
                node_name = self._get_node_name_from_row(item.row())
                if node_name:
                    logging.debug(f"NodesPage: Selected node '{node_name}'")
                    self._select_node_for_graphs(node_name)
        except Exception as e:
            logging.error(f"NodesPage: Error handling row single-click: {e}")
    
    def _get_node_name_from_row(self, row):
        """Get node name from table row"""
        try:
            name_item = self.table.item(row, 0)  # Name is in column 0
            if name_item:
                node_name = name_item.text().strip()
                logging.debug(f"NodesPage: Extracted node name '{node_name}' from row {row}")
                return node_name
            logging.warning(f"NodesPage: No name item found in row {row}")
            return None
        except Exception as e:
            logging.error(f"NodesPage: Error getting node name from row {row}: {e}")
            return None
    
    def _create_metrics_summary(self):
        """Create metrics summary widget showing cluster node stats"""
        QTimer.singleShot(100, self._create_metrics_widget)
    
    def _create_metrics_graphs(self):
        """Create the metrics graphs for the selected node"""
        try:
            logging.info("NodesPage: _create_metrics_graphs called")
            self._create_node_metrics_graphs_widget()  # Call directly instead of using timer
        except Exception as e:
            logging.error(f"NodesPage: Error in _create_metrics_graphs: {e}")
    
# Removed complex graph visibility method
    
    def _create_metrics_widget(self):
        """Create the actual metrics widget"""
        try:
            self.metrics_widget = QFrame()
            self.metrics_widget.setStyleSheet(f"""
                QFrame {{
                    background-color: {AppColors.BG_MEDIUM};
                    border: 1px solid {AppColors.BORDER_COLOR};
                    border-radius: 6px;
                    margin: 5px;
                    padding: 10px;
                }}
            """)
            
            layout = QHBoxLayout(self.metrics_widget)
            
            # Metrics labels
            self.total_nodes_label = QLabel("Nodes: 0")
            self.total_nodes_label.setStyleSheet(f"color: {AppColors.TEXT_LIGHT}; font-weight: bold;")
            
            self.ready_nodes_label = QLabel("Ready: 0")
            self.ready_nodes_label.setStyleSheet(f"color: {AppColors.STATUS_ACTIVE}; font-weight: bold;")
            
            self.not_ready_nodes_label = QLabel("Not Ready: 0")
            self.not_ready_nodes_label.setStyleSheet(f"color: {AppColors.STATUS_DISCONNECTED}; font-weight: bold;")
            
            # Layout metrics
            layout.addWidget(self.total_nodes_label)
            layout.addWidget(QLabel("|"))
            layout.addWidget(self.ready_nodes_label)
            layout.addWidget(QLabel("|"))
            layout.addWidget(self.not_ready_nodes_label)
            layout.addStretch()
            
            # Add to main layout
            page_layout = self.layout()
            if page_layout:
                page_layout.insertWidget(1, self.metrics_widget)
                self.metrics_widget.show()
                logging.info("NodesPage: Created metrics summary widget")
            else:
                logging.error("NodesPage: Page layout not found for metrics widget")
                
        except Exception as e:
            logging.error(f"NodesPage: Failed to create metrics widget: {e}")
    
    def _create_node_metrics_graphs_widget(self):
        """Create the node metrics graphs widget container"""
        try:
            logging.info("NodesPage: Creating node metrics graphs widget")
            
            # Create container frame for graphs
            self.graphs_container = QFrame()
            self.graphs_container.setStyleSheet(f"""
                QFrame {{
                    background-color: {AppColors.BG_MEDIUM};
                    border: 1px solid {AppColors.BORDER_COLOR};
                    border-radius: 8px;
                    margin: 8px 0px;
                    padding: 15px;
                    min-height: 170px;
                }}
            """)
            
            # Create main vertical layout
            main_layout = QVBoxLayout(self.graphs_container)
            
            # Add title label
            self.graphs_title_label = QLabel("Selected Node Metrics")
            self.graphs_title_label.setStyleSheet(f"""
                color: {AppColors.TEXT_LIGHT}; 
                font-weight: bold; 
                font-size: 16px;
                padding: 0px 0px 5px 0px;
                margin: 0px;
            """)
            self.graphs_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(self.graphs_title_label)
            
            # Create individual metric graphs
            self.cpu_metrics_graph = NodeMetricsGraph("CPU Usage", AppColors.STATUS_WARNING)
            self.memory_metrics_graph = NodeMetricsGraph("Memory Usage", AppColors.ACCENT_BLUE) 
            self.disk_metrics_graph = NodeMetricsGraph("Disk Usage", AppColors.ACCENT_PURPLE)
            
            # Create horizontal layout for metric graphs
            metrics_graphs_layout = QHBoxLayout()
            metrics_graphs_layout.setSpacing(15)
            metrics_graphs_layout.setContentsMargins(0, 5, 0, 5)
            
            # Add metric graphs with equal width distribution
            metrics_graphs_layout.addWidget(self.cpu_metrics_graph, 1)
            metrics_graphs_layout.addWidget(self.memory_metrics_graph, 1)
            metrics_graphs_layout.addWidget(self.disk_metrics_graph, 1)
            
            main_layout.addLayout(metrics_graphs_layout)
            
            # Add to main layout at position 1 (right after header controls)
            page_layout = self.layout()
            if page_layout:
                logging.info(f"NodesPage: Page layout found with {page_layout.count()} items")
                page_layout.insertWidget(1, self.graphs_container)
                
                logging.info("NodesPage: Created metrics graphs widget with 3 graphs")
            else:
                logging.error("NodesPage: Page layout not found, cannot add graphs")
                
        except Exception as e:
            logging.error(f"NodesPage: Failed to create graphs widget: {e}")
            import traceback
            logging.error(f"NodesPage: Stack trace: {traceback.format_exc()}")
    
    def _select_node_for_graphs(self, node_name: str):
        """Select a node and start updating its graphs - optimized to avoid restarts"""
        try:
            # Check if we're already monitoring this node
            if self.selected_node_name == node_name and self.metrics_update_timer.isActive():
                logging.debug(f"NodesPage: Already monitoring node '{node_name}', continuing existing session")
                return
            
            # Update the selection only if different
            logging.info(f"NodesPage: Switching graph monitoring from '{self.selected_node_name}' to '{node_name}'")
            self.selected_node_name = node_name
            
            # Check if graphs exist before using them
            if not (self.cpu_metrics_graph and self.memory_metrics_graph and self.disk_metrics_graph):
                logging.warning("NodesPage: Graphs not initialized yet, skipping selection")
                return
            
            # Clear data and reset graphs for new node selection
            self.cpu_metrics_graph.clear_data()
            self.memory_metrics_graph.clear_data()
            self.disk_metrics_graph.clear_data()
            
            # Add a few baseline data points for smooth graph start
            for _ in range(3):
                self.cpu_metrics_graph.add_data_point(0.0)
                self.memory_metrics_graph.add_data_point(0.0)
                self.disk_metrics_graph.add_data_point(0.0)
            
            # Update title to show selected node
            if hasattr(self, 'graphs_title_label') and self.graphs_title_label:
                self.graphs_title_label.setText(f"Node Metrics: {node_name}")
            
            # Start the update timer (update every 5 seconds)
            self.metrics_update_timer.start(5000)
            
            # Get initial data point
            self._update_node_metrics_graphs()
            
            logging.info(f"NodesPage: Started monitoring metrics for node '{node_name}'")
            
        except Exception as e:
            logging.error(f"NodesPage: Error selecting node for graphs: {e}")
    
    def _update_node_metrics_graphs(self):
        """Update node metrics graphs with current data - uses individual calls for real-time data"""
        try:
            if not self.selected_node_name:
                return
            
            # Check if graphs exist before using them
            if not (self.cpu_metrics_graph and self.memory_metrics_graph and self.disk_metrics_graph):
                logging.warning("NodesPage: Graphs not available for update")
                return
            
            # For graphs, we want real-time data so use individual calls
            from Services.kubernetes.kubernetes_service import get_kubernetes_service
            kube_service = get_kubernetes_service()
            
            if kube_service and kube_service.metrics_service:
                logging.debug(f"NodesPage: Fetching real-time metrics for selected node '{self.selected_node_name}'")
                node_metrics = kube_service.metrics_service.get_node_metrics(self.selected_node_name)
                if node_metrics:
                    # Add data points to graphs
                    cpu_usage = node_metrics['cpu']['usage']
                    memory_usage = node_metrics['memory']['usage']
                    disk_usage = node_metrics.get('disk', {}).get('usage', 0.0)
                    
                    self.cpu_metrics_graph.add_data_point(cpu_usage)
                    self.memory_metrics_graph.add_data_point(memory_usage)
                    self.disk_metrics_graph.add_data_point(disk_usage)
                    
                    logging.info(f"NodesPage: Updated graphs for node '{self.selected_node_name}': CPU {cpu_usage:.1f}%, Memory {memory_usage:.1f}%, Disk {disk_usage:.1f}%")
                else:
                    logging.warning(f"NodesPage: No metrics available for node '{self.selected_node_name}'")
            else:
                logging.warning("NodesPage: Metrics service not available")
                
        except Exception as e:
            logging.error(f"NodesPage: Error updating graphs: {e}")
    
    def get_headers(self):
        """Return table column headers"""
        return [
            "Name", "CPU", "Memory", "Disk", 
            "Roles", "Version", "Age", "Status", "Actions"
        ]
    
    def populate_table_row(self, row, node):
        """Populate a single table row with node data"""
        try:
            # Column 0: Name
            name_item = QTableWidgetItem(node.get("name", ""))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 0, name_item)
            
            # Column 1: CPU Usage - use cached metrics for performance
            cpu_usage = self._get_cached_metric_value(node.get("name"), "cpu", "usage")
            if cpu_usage is None:
                cpu_usage = node.get("cpu_usage")
            self._populate_usage_column(row, 1, cpu_usage, "CPU")
            
            # Column 2: Memory Usage - use cached metrics for performance
            memory_usage = self._get_cached_metric_value(node.get("name"), "memory", "usage")
            if memory_usage is None:
                memory_usage = node.get("memory_usage")
            self._populate_usage_column(row, 2, memory_usage, "Memory")
            
            # Column 3: Disk Usage - get fresh metrics if needed
            self._populate_disk_usage_column(row, 3, node)
            
            # Column 4: Roles
            roles = node.get("roles", [])
            roles_text = ", ".join(roles) if isinstance(roles, list) else str(roles) or "Worker"
            roles_item = QTableWidgetItem(roles_text)
            roles_item.setFlags(roles_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            roles_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, roles_item)
            
            # Column 5: Version
            version = node.get("kubelet_version", node.get("version", "Unknown"))
            version_item = QTableWidgetItem(version)
            version_item.setFlags(version_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            version_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 5, version_item)
            
            # Column 6: Age
            age_text = self._format_node_age(node)
            age_item = QTableWidgetItem(age_text)
            age_item.setFlags(age_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            age_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 6, age_item)
            
            # Column 7: Status
            self._populate_status_column(row, 7, node.get("status", "Unknown"))
            
            # Column 8: Actions (handled by _create_action_button_for_row)
            
        except Exception as e:
            logging.error(f"NodesPage: Error populating row {row}: {e}")
    
    def _populate_usage_column(self, row, col, usage_value, metric_type):
        """Populate a usage column (CPU/Memory/Disk) with colored percentage - IMPROVED"""
        try:
            if usage_value is not None:
                try:
                    usage_num = float(usage_value)
                    text = f"{usage_num:.1f}%"
                    color = self._get_usage_color(usage_num)
                    tooltip = f"{metric_type} usage: {usage_num:.1f}%"
                except (ValueError, TypeError):
                    text = "⚠️"  # Warning symbol for invalid data
                    color = AppColors.STATUS_WARNING
                    tooltip = f"Invalid {metric_type} data"
            else:
                text = "⏳"  # Loading symbol for missing data
                color = AppColors.TEXT_SUBTLE
                tooltip = f"Loading {metric_type} metrics..."
            
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            item.setToolTip(tooltip)
            
            # Apply color with multiple methods for compatibility
            brush = QBrush(QColor(color))
            item.setForeground(brush)
            item.setData(Qt.ItemDataRole.ForegroundRole, QColor(color))
            
            self.table.setItem(row, col, item)
            
        except Exception as e:
            logging.error(f"NodesPage: Error populating {metric_type} column: {e}")
    
    def _populate_disk_usage_column(self, row, col, node):
        """Populate disk usage column with batch-cached metrics for performance"""
        try:
            node_name = node.get("name") if node else None
            if not node_name:
                self._populate_usage_column(row, col, None, "Disk")
                return
            
            # Use batch metrics cache for performance
            disk_usage = self._get_cached_metric_value(node_name, "disk", "usage")
            
            # Fallback to node data if no cached metrics
            if disk_usage is None:
                disk_usage = node.get("disk_usage")
            
            self._populate_usage_column(row, col, disk_usage, "Disk")
            
        except Exception as e:
            logging.error(f"NodesPage: Error populating disk usage column: {e}")
    
    def _get_cached_metric_value(self, node_name, metric_type, metric_field):
        """Get a specific metric value from metrics cache"""
        try:
            if node_name in self.metrics_cache:
                node_metrics = self.metrics_cache[node_name]
                if metric_type in node_metrics and metric_field in node_metrics[metric_type]:
                    value = node_metrics[metric_type][metric_field]
                    return value
            return None
        except Exception as e:
            logging.debug(f"NodesPage: Error getting cached metric: {e}")
            return None
    
    def _populate_status_column(self, row, col, status):
        """Populate status column with colored status text"""
        try:
            item = QTableWidgetItem(status)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            
            # Color code based on status
            if status.lower() == "ready":
                color = AppColors.STATUS_ACTIVE
            elif status.lower() == "notready":
                color = AppColors.STATUS_DISCONNECTED
            else:
                color = AppColors.STATUS_WARNING
            
            # Apply color
            brush = QBrush(QColor(color))
            item.setForeground(brush)
            item.setData(Qt.ItemDataRole.ForegroundRole, QColor(color))
            
            self.table.setItem(row, col, item)
            
        except Exception as e:
            logging.error(f"NodesPage: Error populating status column: {e}")
    
    def _get_usage_color(self, usage_percentage):
        """Get color based on resource usage percentage"""
        if usage_percentage >= 90:
            return AppColors.STATUS_DISCONNECTED  # Red - Critical
        elif usage_percentage >= 70:
            return AppColors.STATUS_WARNING       # Orange - High
        elif usage_percentage >= 50:
            return AppColors.TEXT_LIGHT          # White - Medium
        else:
            return AppColors.STATUS_ACTIVE       # Green - Low
    
    def _format_node_age(self, node):
        """Format node age with detailed time units"""
        try:
            # Try multiple timestamp fields
            timestamp_fields = ["creation_timestamp", "creationTimestamp", "created", "created_at", "startup_time"]
            
            for field in timestamp_fields:
                timestamp = node.get(field)
                if timestamp and timestamp != "Unknown":
                    return self._format_detailed_age(timestamp)
            
            return "Unknown"
            
        except Exception as e:
            logging.error(f"NodesPage: Error formatting age for node {node.get('name', '')}: {e}")
            return "Unknown"
    
    def _format_detailed_age(self, timestamp):
        """Format timestamp into detailed age string (e.g., '2d 5h', '1h 30m')"""
        try:
            # Parse timestamp
            if isinstance(timestamp, str):
                if any(timestamp.endswith(suffix) for suffix in ['s', 'm', 'h', 'd', 'mo', 'y']):
                    return timestamp  # Already formatted
                
                if 'T' in timestamp:
                    created = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    created = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
            else:
                created = timestamp
            
            # Ensure timezone aware
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            
            # Calculate age components
            now = datetime.now(timezone.utc)
            age_delta = now - created
            
            days = age_delta.days
            hours = age_delta.seconds // 3600
            minutes = (age_delta.seconds % 3600) // 60
            seconds = age_delta.seconds % 60
            
            # Format with two most significant units
            if days > 365:
                years = days // 365
                remaining_days = days % 365
                return f"{years}y {remaining_days // 30}mo" if remaining_days > 30 else f"{years}y {remaining_days}d"
            elif days > 30:
                months = days // 30
                remaining_days = days % 30
                return f"{months}mo {remaining_days}d"
            elif days > 0:
                return f"{days}d {hours}h" if hours > 0 else f"{days}d"
            elif hours > 0:
                return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
            elif minutes > 0:
                return f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"
            else:
                return f"{seconds}s"
                
        except Exception as e:
            logging.debug(f"Error formatting detailed age: {e}")
            return "Unknown"
    
    def _load_metrics_batch(self, node_names, include_disk_usage=None):
        """Load all node metrics in batch for performance optimization"""
        try:
            current_time = time.time()
            
            # Determine if we should include disk usage
            if include_disk_usage is None:
                include_disk_usage = self.is_disk_usage_enabled and not self.is_lazy_loading_enabled
            
            # Check if metrics cache is still valid
            if (current_time - self.last_cache_update_time) < self.cache_ttl_seconds and self.metrics_cache:
                logging.debug(f"NodesPage: Using cached metrics for {len(self.metrics_cache)} nodes")
                return
            
            from Services.kubernetes.kubernetes_service import get_kubernetes_service
            kubernetes_service = get_kubernetes_service()
            
            if kubernetes_service and kubernetes_service.metrics_service:
                metrics_type = "with disk usage" if include_disk_usage else "fast (no disk)"
                logging.info(f"🚀 [BATCH METRICS] Loading {metrics_type} metrics for {len(node_names)} nodes...")
                start_time = time.time()
                
                # Use the optimized batch method with disk usage control
                if hasattr(kubernetes_service.metrics_service, 'get_all_node_metrics_fast'):
                    node_metrics = kubernetes_service.metrics_service.get_all_node_metrics_fast(node_names, include_disk_usage)
                else:
                    # Fallback to existing method
                    node_metrics = kubernetes_service.metrics_service.get_all_node_metrics(node_names)
                
                if node_metrics:
                    self.metrics_cache = node_metrics
                    self.last_cache_update_time = current_time
                    
                    processing_time = (time.time() - start_time) * 1000
                    logging.info(f"✅ [BATCH METRICS] Loaded {metrics_type} metrics for {len(node_metrics)} nodes in {processing_time:.1f}ms")
                else:
                    logging.warning("NodesPage: No node metrics returned")
            else:
                logging.warning("NodesPage: Kubernetes service not available for metrics loading")
                
        except Exception as e:
            logging.error(f"NodesPage: Error loading batch metrics: {e}")

    def _load_disk_usage_in_background(self, node_names):
        """Load disk usage in background and update table progressively"""
        try:
            if self.is_disk_loading_in_progress:
                logging.debug("NodesPage: Disk loading already in progress, skipping")
                return
            
            self.is_disk_loading_in_progress = True
            logging.info(f"🔄 [BACKGROUND] Loading disk usage for {len(node_names)} nodes...")
            
            from Services.kubernetes.kubernetes_service import get_kubernetes_service
            kube_service = get_kubernetes_service()
            
            if kube_service and kube_service.metrics_service:
                start_time = time.time()
                
                # Load disk usage in background
                disk_metrics = kube_service.metrics_service.get_all_node_metrics_fast(node_names, include_disk_usage=True)
                
                if disk_metrics:
                    # Update the existing cache with disk data
                    for node_name, metrics in disk_metrics.items():
                        if node_name in self.metrics_cache and 'disk' in metrics:
                            self.metrics_cache[node_name]['disk'] = metrics['disk']
                    
                    # Update the disk column in the table
                    self._update_disk_columns_from_cache()
                    
                    processing_time = (time.time() - start_time) * 1000
                    logging.info(f"✅ [BACKGROUND] Loaded disk usage for {len(disk_metrics)} nodes in {processing_time:.1f}ms")
                else:
                    logging.warning("NodesPage: No disk metrics returned from background loading")
            else:
                logging.warning("NodesPage: Kubernetes service not available for background disk loading")
                
        except Exception as e:
            logging.error(f"NodesPage: Error loading disk usage in background: {e}")
        finally:
            self.is_disk_loading_in_progress = False

    def _update_disk_columns_from_cache(self):
        """Update disk usage columns in the table from cached data"""
        try:
            if not hasattr(self, 'table') or not self.table:
                return
            
            row_count = self.table.rowCount()
            updated_count = 0
            
            for row in range(row_count):
                try:
                    # Get node name from first column
                    name_item = self.table.item(row, 0)
                    if name_item:
                        node_name = name_item.text()
                        
                        # Get disk usage from cache
                        disk_usage = self._get_cached_metric_value(node_name, "disk", "usage")
                        if disk_usage is not None:
                            self._populate_usage_column(row, 3, disk_usage, "Disk")
                            updated_count += 1
                            
                except Exception as e:
                    logging.debug(f"NodesPage: Error updating disk for row {row}: {e}")
            
            if updated_count > 0:
                logging.info(f"🔄 [DISK UPDATE] Updated disk usage for {updated_count} nodes in table")
            
        except Exception as e:
            logging.error(f"NodesPage: Error updating disk columns from cache: {e}")

    def clear_metrics_cache(self):
        """Clear the node metrics cache to force fresh data loading"""
        self.metrics_cache.clear()
        self.last_cache_update_time = 0
        logging.debug("NodesPage: Node metrics cache cleared")

    def populate_table(self, resources_data):
        """Populate the table with nodes data - BATCH OPTIMIZED FOR 50+ NODES"""
        try:
            if not hasattr(self, 'table') or not self.table:
                logging.error("NodesPage: Table not available")
                return
            
            logging.debug(f"NodesPage: populate_table called with {len(resources_data) if resources_data else 0} nodes")
            
            # Prevent duplicate population calls
            if self.is_table_population_in_progress:
                logging.debug("NodesPage: Table population already in progress, skipping duplicate call")
                return
            
            self.is_table_population_in_progress = True
            
            self._clear_table_widgets()
            
            if not resources_data:
                self._show_empty_state()
                self.is_table_population_in_progress = False
                return
            
            # Remove duplicate nodes by name
            unique_nodes = {}
            for node in resources_data:
                node_name = node.get("name")
                if node_name and node_name not in unique_nodes:
                    unique_nodes[node_name] = node
            
            resources_data = list(unique_nodes.values())
            logging.info(f"NodesPage: Filtered to {len(resources_data)} unique nodes")
            
            # Store resources for search
            self.resources = resources_data
            
            # Extract node names and load batch metrics BEFORE table population
            node_names = [node.get("name") for node in resources_data if node.get("name")]
            if node_names:
                # Initial fast load without disk usage for performance
                logging.info(f"NodesPage: Loading fast metrics for nodes: {node_names}")
                self._load_metrics_batch(node_names, include_disk_usage=False)
                logging.info(f"NodesPage: Metrics cache now has {len(self.metrics_cache)} nodes")
            
            # Setup table
            self.table.setRowCount(len(resources_data))
            
            # CRITICAL FIX: Disable sorting during population to prevent row shuffling
            sorting_was_enabled = self.table.isSortingEnabled()
            self.table.setSortingEnabled(False)
            logging.debug(f"NodesPage: Disabled sorting during table population (was {sorting_was_enabled})")
            
            logging.debug(f"NodesPage: Table setup - Row count: {self.table.rowCount()}, Column count: {self.table.columnCount()}")
            
            # PROGRESSIVE LOADING: Show basic data first, then metrics
            start_time = time.time()
            logging.info(f"🚀 [PROGRESSIVE] Starting progressive loading for {len(resources_data)} nodes")
            
            # Phase 1: Populate basic node info (fast)
            for row, node in enumerate(resources_data):
                try:
                    self.table.setRowHeight(row, 32)
                    self.populate_table_row_basic(row, node)  # Basic info only
                    self._create_action_button_for_row(row, node)
                except Exception as e:
                    logging.error(f"NodesPage: Error processing row {row} for node {node.get('name', 'unknown')}: {e}")
                    import traceback
                    logging.error(f"NodesPage: Traceback: {traceback.format_exc()}")
            
            basic_time = (time.time() - start_time) * 1000
            logging.info(f"✅ [BASIC DATA] Loaded basic info for {len(resources_data)} nodes in {basic_time:.1f}ms")
            
            # Update metrics and configure columns
            self._update_metrics_summary(resources_data)
            self.configure_columns()
            self._update_items_count()
            
            # Phase 2: Load metrics progressively (if available)
            if self._has_metrics_in_data(resources_data):
                self._update_metrics_progressively(resources_data)
            else:
                logging.info("⏳ [METRICS] No metrics available in data - showing placeholders")
            
            total_time = (time.time() - start_time) * 1000
            logging.info(f"✅ [COMPLETE] Progressive loading completed in {total_time:.1f}ms")
            
            # CRITICAL FIX: Re-enable sorting after population is complete (delayed to prevent immediate sorting)
            if sorting_was_enabled:
                def re_enable_sorting():
                    self.table.setSortingEnabled(True)
                    logging.debug("NodesPage: Re-enabled table sorting after population (delayed)")
                
                # Delay sorting re-enable to prevent immediate sorting of populated data
                QTimer.singleShot(100, re_enable_sorting)
            
            # Start background disk usage loading if enabled and not already in progress
            if self.is_disk_usage_enabled and self.is_lazy_loading_enabled and node_names and not self.is_disk_loading_in_progress:
                QTimer.singleShot(500, lambda: self._load_disk_usage_in_background(node_names))
            
        except Exception as e:
            logging.error(f"NodesPage: Error populating table: {e}")
            # CRITICAL FIX: Ensure sorting is re-enabled even on error (delayed)
            if 'sorting_was_enabled' in locals() and sorting_was_enabled:
                def re_enable_sorting_on_error():
                    self.table.setSortingEnabled(True)
                    logging.debug("NodesPage: Re-enabled table sorting after error (delayed)")
                QTimer.singleShot(100, re_enable_sorting_on_error)
        finally:
            self.is_table_population_in_progress = False
    
    def populate_table_row_basic(self, row, node):
        """Populate a single table row with basic node data (no metrics) - FAST"""
        try:
            # Column 0: Name
            node_name = node.get("name", "")
            name_item = QTableWidgetItem(node_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 0, name_item)
            
            # Column 1-2: CPU, Memory Usage - Use cached metrics for performance
            node_name = node.get("name")
            
            # CPU Usage
            cpu_usage = self._get_cached_metric_value(node_name, "cpu", "usage")
            if cpu_usage is None:
                cpu_usage = node.get("cpu_usage")
            self._populate_usage_column(row, 1, cpu_usage, "CPU")
            
            # Memory Usage  
            memory_usage = self._get_cached_metric_value(node_name, "memory", "usage")
            if memory_usage is None:
                memory_usage = node.get("memory_usage")
            self._populate_usage_column(row, 2, memory_usage, "Memory")
            
            # Column 3: Disk Usage - handle specially with fresh metrics
            self._populate_disk_usage_column(row, 3, node)
            
            # Column 4: Roles
            roles = node.get("roles", [])
            roles_text = ", ".join(roles) if isinstance(roles, list) else str(roles) or "Worker"
            roles_item = QTableWidgetItem(roles_text)
            roles_item.setFlags(roles_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            roles_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, roles_item)
            
            # Column 5: Version
            version = node.get("kubelet_version", node.get("version", "Unknown"))
            version_item = QTableWidgetItem(version)
            version_item.setFlags(version_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            version_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 5, version_item)
            
            # Column 6: Age
            age_text = self._format_node_age(node)
            age_item = QTableWidgetItem(age_text)
            age_item.setFlags(age_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            age_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 6, age_item)
            
            # Column 7: Status
            self._populate_status_column(row, 7, node.get("status", "Unknown"))
            
        except Exception as e:
            logging.error(f"NodesPage: Error populating basic row {row}: {e}")
    
    def _populate_loading_column(self, row, col, metric_type):
        """Populate a column with loading indicator"""
        try:
            item = QTableWidgetItem("⏳")  # Loading indicator
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            
            # Use subtle color for loading indicator
            brush = QBrush(QColor(AppColors.TEXT_SUBTLE))
            item.setForeground(brush)
            item.setData(Qt.ItemDataRole.ForegroundRole, QColor(AppColors.TEXT_SUBTLE))
            
            # Set tooltip
            item.setToolTip(f"Loading {metric_type} metrics...")
            
            self.table.setItem(row, col, item)
            
        except Exception as e:
            logging.error(f"NodesPage: Error populating loading {metric_type} column: {e}")
    
    def _has_metrics_in_data(self, resources_data):
        """Check if any node in the data has metrics"""
        try:
            for node in resources_data:
                if (node.get("cpu_usage") is not None or 
                    node.get("memory_usage") is not None or 
                    node.get("disk_usage") is not None):
                    return True
            return False
        except Exception:
            return False
    
    def _update_metrics_progressively(self, resources_data):
        """Update metrics columns progressively"""
        try:
            metrics_start = time.time()
            updated_count = 0
            
            
            for row, node in enumerate(resources_data):
                try:
                    node_name = node.get("name")
                    
                    # Update CPU column with cached metrics
                    cpu_usage = self._get_cached_metric_value(node_name, "cpu", "usage")
                    if cpu_usage is None:
                        cpu_usage = node.get("cpu_usage")
                    if cpu_usage is not None:
                        self._populate_usage_column(row, 1, cpu_usage, "CPU")
                    
                    # Update Memory column with cached metrics
                    memory_usage = self._get_cached_metric_value(node_name, "memory", "usage")
                    if memory_usage is None:
                        memory_usage = node.get("memory_usage")
                    if memory_usage is not None:
                        self._populate_usage_column(row, 2, memory_usage, "Memory")
                    
                    # Update Disk column with cached metrics
                    disk_usage = self._get_cached_metric_value(node_name, "disk", "usage")
                    if disk_usage is None:
                        disk_usage = node.get("disk_usage")
                    if disk_usage is not None:
                        self._populate_usage_column(row, 3, disk_usage, "Disk")
                    
                    updated_count += 1
                    
                    # Process UI events every 10 rows to keep UI responsive
                    if updated_count % 10 == 0:
                        QApplication.processEvents()
                        
                except Exception as e:
                    logging.error(f"NodesPage: Error updating metrics for row {row}: {e}")
            
            
            metrics_time = (time.time() - metrics_start) * 1000
            logging.info(f"✅ [METRICS UPDATE] Updated metrics for {updated_count} nodes in {metrics_time:.1f}ms")
            
        except Exception as e:
            logging.error(f"NodesPage: Error in progressive metrics update: {e}")

# Removed complex background metrics loading methods
    
    def _show_empty_state(self):
        """Show empty state when no nodes are available"""
        self.table.setRowCount(1)
        item = QTableWidgetItem("No nodes available")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(0, 0, item)
        
        # Clear other cells and span across columns
        for col in range(1, self.table.columnCount()):
            empty_item = QTableWidgetItem("")
            empty_item.setFlags(empty_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(0, col, empty_item)
        
        self.table.setSpan(0, 0, 1, len(self.get_headers()))
        
        # Update count for empty state
        self._update_items_count()
    
    def _update_metrics_summary(self, nodes_data):
        """Update metrics summary with current node statistics"""
        try:
            if not nodes_data or not hasattr(self, 'total_nodes_label'):
                return
            
            total_nodes = len(nodes_data)
            ready_nodes = sum(1 for node in nodes_data if node.get("status", "").lower() == "ready")
            not_ready_nodes = total_nodes - ready_nodes
            
            self.total_nodes_label.setText(f"Nodes: {total_nodes}")
            self.ready_nodes_label.setText(f"Ready: {ready_nodes}")
            self.not_ready_nodes_label.setText(f"Not Ready: {not_ready_nodes}")
            
        except Exception as e:
            logging.error(f"NodesPage: Error updating metrics: {e}")
    
    def _update_items_count(self):
        """Update the items count label with correct node count"""
        try:
            # Count actual visible rows in table, not total resources
            if hasattr(self, 'table') and self.table:
                count = self.table.rowCount()
                # Don't count if it's an empty state row
                if count == 1:
                    first_item = self.table.item(0, 0)
                    if first_item and first_item.text() == "No nodes available":
                        count = 0
            else:
                count = 0
            
            if hasattr(self, 'items_count') and self.items_count:
                # Use "nodes" instead of generic "items"
                self.items_count.setText(f"{count} nodes")
                logging.debug(f"NodesPage: Updated items count to {count} nodes")
        except Exception as e:
            logging.error(f"NodesPage: Error updating items count: {e}")
    
    def _create_action_button_for_row(self, row, node):
        """Create action button for node row"""
        try:
            node_name = node.get("name", "")
            if not node_name:
                return
            
            action_btn = self._create_action_button(node_name)
            if not action_btn:
                return
            
            # Create container for positioning
            container = QWidget()
            container.setStyleSheet("QWidget { background-color: transparent; border: none; }")
            container.setFixedSize(40, 32)
            
            # Position button in container
            action_btn.setParent(container)
            action_btn.move(8, -6)
            
            self.table.setCellWidget(row, 8, container)
            
        except Exception as e:
            logging.error(f"NodesPage: Error creating action button for row {row}: {e}")
    
    def _create_action_button(self, resource_name):
        """Create action dropdown button for node"""
        try:
            from PyQt6.QtWidgets import QToolButton, QMenu
            from PyQt6.QtCore import QSize
            from PyQt6.QtGui import QIcon
            import os
            
            button = QToolButton()
            button.setFixedSize(24, 24)
            
            # Load icon or use text fallback
            icon_path = resource_path("Icons/Moreaction_Button.svg")
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                if not icon.isNull():
                    button.setIcon(icon)
                    button.setIconSize(QSize(16, 16))
                else:
                    button.setText("⋮")
            else:
                button.setText("⋮")
            
            # Create menu
            menu = QMenu(button)
            menu.setStyleSheet(f"""
                QMenu {{
                    background-color: {AppColors.BG_MEDIUM};
                    color: {AppColors.TEXT_LIGHT};
                    border: 1px solid {AppColors.BORDER_COLOR};
                    border-radius: 4px;
                    padding: 2px;
                }}
                QMenu::item {{
                    padding: 6px 12px;
                    border-radius: 2px;
                }}
                QMenu::item:selected {{
                    background-color: {AppColors.HOVER_BG};
                }}
            """)
            
            # Add menu actions
            view_action = menu.addAction("View Details")
            view_action.triggered.connect(lambda: self._handle_menu_action("View Details", resource_name))
            
            edit_action = menu.addAction("Edit")
            edit_action.triggered.connect(lambda: self._handle_menu_action("Edit", resource_name))
            
            drain_action = menu.addAction("Drain Node")
            drain_action.triggered.connect(lambda: self._handle_menu_action("Drain Node", resource_name))
            
            cordon_action = menu.addAction("Cordon Node")
            cordon_action.triggered.connect(lambda: self._handle_menu_action("Cordon Node", resource_name))
            
            # Don't set menu directly to avoid automatic arrow
            # button.setMenu(menu)  # This causes the arrow to appear
            
            # Store menu reference and show manually
            button._menu = menu
            button.clicked.connect(lambda: self._show_button_menu(button, menu))
            
            return button
            
        except Exception as e:
            logging.error(f"NodesPage: Error creating action button: {e}")
            # Fallback button
            from PyQt6.QtWidgets import QToolButton
            button = QToolButton()
            button.setText("⋮")
            button.setFixedSize(24, 24)
            return button
    
    def _show_button_menu(self, button, menu):
        """Show menu at button position without arrow"""
        try:
            # Calculate position to show menu below the button
            global_pos = button.mapToGlobal(button.rect().bottomLeft())
            menu.exec(global_pos)
        except Exception as e:
            logging.error(f"NodesPage: Error showing button menu: {e}")
    
    def _handle_menu_action(self, action, resource_name):
        """Handle menu action selection"""
        try:
            logging.info(f"NodesPage: Menu action '{action}' for node '{resource_name}'")
            
            if action == "View Details":
                self._open_node_details(resource_name)
            elif action == "Edit":
                self._open_node_edit(resource_name)
            elif action == "Drain Node":
                self._handle_drain_node(resource_name)
            elif action == "Cordon Node":
                self._handle_cordon_node(resource_name)
            else:
                logging.warning(f"NodesPage: Unknown action '{action}'")
                
        except Exception as e:
            logging.error(f"NodesPage: Error handling menu action '{action}': {e}")
    
    def _open_node_details(self, node_name):
        """Open node detail page"""
        try:
            logging.info(f"NodesPage: Opening details for node '{node_name}'")
            
            cluster_view = self._find_cluster_view()
            if cluster_view and hasattr(cluster_view, 'detail_manager'):
                cluster_view.detail_manager.show_detail('node', node_name, None)
                logging.info(f"NodesPage: Opened detail page for node '{node_name}'")
            else:
                self._show_detail_unavailable_message(node_name)
                
        except Exception as e:
            logging.error(f"NodesPage: Error opening details for node '{node_name}': {e}")
    
    def _open_node_edit(self, node_name):
        """Open node in edit mode"""
        try:
            logging.info(f"NodesPage: Opening edit mode for node '{node_name}'")
            
            cluster_view = self._find_cluster_view()
            if cluster_view and hasattr(cluster_view, 'detail_manager'):
                cluster_view.detail_manager.show_detail('node', node_name, None)
                # Trigger edit mode after a delay
                QTimer.singleShot(500, lambda: self._trigger_edit_mode(cluster_view))
                logging.info(f"NodesPage: Opened edit mode for node '{node_name}'")
            else:
                self._show_detail_unavailable_message(node_name)
                
        except Exception as e:
            logging.error(f"NodesPage: Error opening edit mode for node '{node_name}': {e}")
    
    def _find_cluster_view(self):
        """Find the parent ClusterView containing the detail manager"""
        try:
            parent = self.parent()
            while parent:
                parent_name = parent.__class__.__name__
                if parent_name == 'ClusterView' or hasattr(parent, 'detail_manager'):
                    logging.debug(f"NodesPage: Found ClusterView in '{parent_name}'")
                    return parent
                parent = parent.parent()
            
            logging.warning("NodesPage: Could not find ClusterView")
            return None
            
        except Exception as e:
            logging.error(f"NodesPage: Error finding ClusterView: {e}")
            return None
    
    def _trigger_edit_mode(self, cluster_view):
        """Trigger edit mode in the detail page YAML section"""
        try:
            if (hasattr(cluster_view, 'detail_manager') and 
                cluster_view.detail_manager._detail_page):
                
                detail_page = cluster_view.detail_manager._detail_page
                
                if hasattr(detail_page, 'yaml_section'):
                    yaml_section = detail_page.yaml_section
                    if (hasattr(yaml_section, 'toggle_yaml_edit_mode') and 
                        yaml_section.yaml_editor.isReadOnly()):
                        yaml_section.toggle_yaml_edit_mode()
                        logging.info("NodesPage: Triggered edit mode")
                        
        except Exception as e:
            logging.error(f"NodesPage: Error triggering edit mode: {e}")
    
    def _show_detail_unavailable_message(self, node_name):
        """Show message when detail panel is not available"""
        QMessageBox.information(
            self, "Node Details",
            f"Node: {node_name}\n\nDetail panel not available. "
            f"Please check the main view configuration."
        )
    
    def _handle_drain_node(self, node_name):
        """Handle node drain operation"""
        try:
            reply = QMessageBox.question(
                self, 'Drain Node',
                f'Are you sure you want to drain node "{node_name}"?\n\n'
                'This will safely evict all pods from the node.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # TODO: Implement actual drain operation
                QMessageBox.information(
                    self, "Drain Node",
                    f'Node "{node_name}" drain operation would be initiated.\n'
                    '(Implementation pending)'
                )
                
        except Exception as e:
            logging.error(f"NodesPage: Error draining node '{node_name}': {e}")
    
    def _handle_cordon_node(self, node_name):
        """Handle node cordon operation"""
        try:
            reply = QMessageBox.question(
                self, 'Cordon Node',
                f'Are you sure you want to cordon node "{node_name}"?\n\n'
                'This will mark the node as unschedulable.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # TODO: Implement actual cordon operation
                QMessageBox.information(
                    self, "Cordon Node",
                    f'Node "{node_name}" cordon operation would be initiated.\n'
                    '(Implementation pending)'
                )
                
        except Exception as e:
            logging.error(f"NodesPage: Error cordoning node '{node_name}': {e}")
    
    def _clear_table_widgets(self):
        """Clear all cell widgets from the table"""
        try:
            if not hasattr(self, 'table') or not self.table:
                return
            
            for row in range(self.table.rowCount()):
                for col in range(self.table.columnCount()):
                    widget = self.table.cellWidget(row, col)
                    if widget:
                        self.table.removeCellWidget(row, col)
                        widget.deleteLater()
            
            self.table.clearSpans()
            
        except Exception as e:
            logging.error(f"NodesPage: Error clearing table widgets: {e}")
    
    def configure_columns(self):
        """Configure table column widths and alignment for NodesPage"""
        try:
            if not hasattr(self, 'table') or not self.table:
                return
            
            header = self.table.horizontalHeader()
            
            # Configure proper resizing behavior for NodesPage
            from PyQt6.QtWidgets import QHeaderView
            
            # Override base class column configuration
            header.setStretchLastSection(False)
            header.setSectionsMovable(False)
            header.setSectionsClickable(True)
            header.setMinimumSectionSize(50)  # Allow reasonable minimum
            header.setDefaultSectionSize(120)
            
            # Configure each column specifically for NodesPage
            headers = self.get_headers()
            for i in range(len(headers)):
                if i == 0:  # Name column - resizable, larger minimum
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                    header.resizeSection(i, 200)
                elif i == len(headers) - 1:  # Actions column - fixed width
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                    header.resizeSection(i, 80)
                else:  # Other columns - interactive resizing
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            
            # Set specific column widths
            header.resizeSection(1, 80)   # CPU
            header.resizeSection(2, 80)   # Memory
            header.resizeSection(3, 80)   # Disk
            header.resizeSection(4, 120)  # Roles
            header.resizeSection(5, 120)  # Version
            header.resizeSection(6, 80)   # Age
            header.resizeSection(7, 100)  # Status
            
            # Set Status column to stretch to fill remaining space
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
            
            # Set header alignment
            for col in range(self.table.columnCount()):
                header_item = self.table.horizontalHeaderItem(col)
                if header_item:
                    if col == 0:  # Name column - left align
                        header_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    else:  # Other columns - center align
                        header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            
            logging.debug("NodesPage: Configured columns with proper resizing")
            
        except Exception as e:
            logging.error(f"NodesPage: Error configuring columns: {e}")
    
    
    def refresh_data(self):
        """Refresh nodes data from the cluster"""
        try:
            from Utils.unified_resource_loader import get_unified_resource_loader
            loader = get_unified_resource_loader()
            if loader:
                loader.load_resources_async(
                    resource_type=self.resource_type,
                    namespace="all"
                )
                logging.info("NodesPage: Requested fresh data")
            else:
                logging.error("NodesPage: Could not get resource loader")
                
        except Exception as e:
            logging.error(f"NodesPage: Error refreshing data: {e}")
    
    def get_resource_display_name(self):
        """Return display name for this resource type"""
        return "Nodes"
    
    def get_resource_icon(self):
        """Return icon for nodes"""
        try:
            return Icons.get_icon("nodes", use_local=True)
        except Exception as e:
            logging.error(f"NodesPage: Error getting nodes icon: {e}")
            return Icons.create_text_icon("📟")
    
    def _on_unified_resources_loaded(self, resource_type, result):
        """Override to handle unified resource loading properly - WITH PERFORMANCE MONITORING"""
        try:
            if resource_type != self.resource_type:
                return
            
            load_start_time = time.time()
            
            if result.success:
                # PERFORMANCE MONITORING
                data_load_time = result.load_time_ms if hasattr(result, 'load_time_ms') else 0
                total_nodes = len(result.items)
                from_cache = result.from_cache if hasattr(result, 'from_cache') else False
                
                logging.info(f"📊 [PERFORMANCE] NodesPage: Loaded {total_nodes} nodes in {data_load_time:.1f}ms ({'from cache' if from_cache else 'from API'})")
                
                # Store the resources for search functionality
                self.resources = result.items
                
                # Only show results if we're not in search mode or this is search results
                if not getattr(self, '_is_searching', False):
                    # Normal load - show all results
                    ui_start_time = time.time()
                    self.populate_table(result.items)
                    ui_time = (time.time() - ui_start_time) * 1000
                    
                    total_time = (time.time() - load_start_time) * 1000
                    
                    # PERFORMANCE SUMMARY
                    logging.info(f"🎯 [PERFORMANCE SUMMARY] NodesPage: "
                               f"Data: {data_load_time:.1f}ms, "
                               f"UI: {ui_time:.1f}ms, "
                               f"Total: {total_time:.1f}ms, "
                               f"Nodes: {total_nodes}, "
                               f"Speed: {(total_nodes/total_time*1000):.1f} nodes/sec")
                else:
                    # We're in search mode - let search handler deal with it
                    logging.info(f"NodesPage: Received {len(result.items)} nodes during search mode")
            else:
                logging.error(f"❌ [ERROR] NodesPage: Failed to load {resource_type}: {result.error_message}")
                # Show empty message using populate_table to ensure proper cleanup
                self.populate_table([])
                
        except Exception as e:
            error_time = (time.time() - load_start_time) * 1000 if 'load_start_time' in locals() else 0
            logging.error(f"❌ [EXCEPTION] NodesPage: Error processing unified resources after {error_time:.1f}ms: {e}")
            import traceback
            logging.debug(f"NodesPage: Full error traceback: {traceback.format_exc()}")
    
    def _on_search_text_changed(self, text):
        """Override base class search to use local filtering for nodes - WITH PERFORMANCE MONITORING"""
        try:
            search_start_time = time.time()
            text = text.strip()
            logging.info(f"🔍 [SEARCH] NodesPage: Search text changed to: '{text}'")
            
            if not text:
                # Search cleared - restore original data
                self._on_search_cleared()
            else:
                # Perform local search to avoid duplicates
                if hasattr(self, 'resources') and self.resources:
                    filter_start_time = time.time()
                    filtered_results = self._filter_resources(text)
                    filter_time = (time.time() - filter_start_time) * 1000
                    
                    ui_start_time = time.time()
                    if filtered_results:
                        self.populate_table(filtered_results)
                        ui_time = (time.time() - ui_start_time) * 1000
                        total_time = (time.time() - search_start_time) * 1000
                        
                        logging.info(f"✅ [SEARCH] NodesPage: Found {len(filtered_results)} results for '{text}' "
                                   f"(Filter: {filter_time:.1f}ms, UI: {ui_time:.1f}ms, Total: {total_time:.1f}ms)")
                    else:
                        # No results found - show empty message
                        self.populate_table([])
                        total_time = (time.time() - search_start_time) * 1000
                        logging.info(f"🔍 [SEARCH] NodesPage: No matches for '{text}' in {total_time:.1f}ms")
                else:
                    logging.warning("⚠️ [SEARCH] NodesPage: No cached resources for search")
                    # Show empty message when no cached resources
                    self.populate_table([])
        except Exception as e:
            search_time = (time.time() - search_start_time) * 1000 if 'search_start_time' in locals() else 0
            logging.error(f"❌ [SEARCH ERROR] NodesPage: Error handling search after {search_time:.1f}ms: {e}")
    
    def _on_search_cleared(self):
        """Handle when search is cleared - ensure data is restored"""
        try:
            logging.info("NodesPage: Search cleared, restoring original data")
            # Reset search mode flags
            if hasattr(self, '_is_searching'):
                self._is_searching = False
            if hasattr(self, '_current_search_query'):
                self._current_search_query = None
                
            # First try to restore from existing resources
            if hasattr(self, 'resources') and self.resources:
                self.populate_table(self.resources)
                logging.info(f"NodesPage: Restored {len(self.resources)} nodes from cache")
            else:
                # If no cached resources, refresh from server
                logging.info("NodesPage: No cached resources, refreshing from server")
                self.refresh_data()
        except Exception as e:
            logging.error(f"NodesPage: Error handling search clear: {e}")
            # Fallback to refresh if restore fails
            try:
                self.refresh_data()
            except Exception as refresh_error:
                logging.error(f"NodesPage: Fallback refresh also failed: {refresh_error}")
    
    def _on_search_results_loaded(self, resource_type, result):
        """Override to prevent base class search results from interfering"""
        # For nodes, we handle search locally, so ignore global search results
        logging.debug(f"NodesPage: Ignoring global search results for {resource_type} with {len(result.items) if result.success else 0} items - using local search")
        pass
    
    def _filter_resources(self, search_query):
        """Override to prevent duplicate results and handle search properly"""
        try:
            if not search_query or not hasattr(self, 'resources') or not self.resources:
                # If no search query, show all resources
                return self.resources if hasattr(self, 'resources') else []
            
            search_query = search_query.lower().strip()
            if not search_query:  # Empty after strip
                return self.resources
            
            filtered = []
            seen_names = set()  # Prevent duplicates by tracking seen node names
            
            for resource in self.resources:
                if isinstance(resource, dict):
                    node_name = resource.get('name', '')
                    
                    # Skip if we've already seen this node (prevent duplicates)
                    if node_name in seen_names:
                        logging.debug(f"NodesPage: Skipping duplicate node: {node_name}")
                        continue
                    
                    # Search in node name, status, roles
                    searchable_fields = [
                        node_name,
                        resource.get('status', ''),
                        ', '.join(resource.get('roles', [])) if isinstance(resource.get('roles'), list) else str(resource.get('roles', '')),
                        resource.get('kubelet_version', ''),
                        resource.get('version', '')
                    ]
                    
                    # Check if search query matches any field
                    match_found = False
                    for field in searchable_fields:
                        if field and search_query in str(field).lower():
                            match_found = True
                            break
                    
                    if match_found:
                        filtered.append(resource)
                        seen_names.add(node_name)
                        logging.debug(f"NodesPage: Added matching node: {node_name}")
            
            logging.info(f"NodesPage: Local search '{search_query}' found {len(filtered)} unique results")
            return filtered
            
        except Exception as e:
            logging.error(f"NodesPage: Error filtering resources: {e}")
            return self.resources if hasattr(self, 'resources') else []
    
    def _perform_search(self):
        """Override base class search to use local filtering instead of global search"""
        try:
            search_text = self.search_bar.text().strip() if hasattr(self, 'search_bar') and self.search_bar else ""
            
            if not search_text:
                # No search query, clear search
                self._on_search_cleared()
            else:
                # Use local search instead of global search
                logging.info(f"NodesPage: Performing local search for '{search_text}'")
                if hasattr(self, 'resources') and self.resources:
                    filtered_results = self._filter_resources(search_text)
                    self.populate_table(filtered_results)
                    
                    # Set search mode to prevent interference
                    self._is_searching = True
                    self._current_search_query = search_text
                    
                    if filtered_results:
                        logging.info(f"NodesPage: Local search completed - {len(filtered_results)} results")
                    else:
                        logging.info(f"NodesPage: Local search completed - no matching results for '{search_text}'")
                else:
                    logging.warning("NodesPage: No resources available for search")
                    # Show empty message when no cached resources
                    self.populate_table([])
        except Exception as e:
            logging.error(f"NodesPage: Error in _perform_search: {e}")

    # Override parent methods that are not applicable for nodes
    def _create_checkbox_container(self, row, resource_name):
        """Override to prevent checkbox creation for nodes"""
        del row, resource_name  # Mark as unused
        return None
    
    def delete_selected_resources(self):
        """Override to prevent delete operations on nodes"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "Operation Not Allowed",
            "Nodes cannot be deleted from this interface.\n"
            "Node management should be done through cluster administration tools."
        )
    
    # Additional overrides to prevent node deletion - simplified
    def _add_select_all_to_header(self): pass
    def _create_select_all_checkbox(self): return None
    def _create_delete_button(self): return None
    def _setup_delete_functionality(self): pass
    def _handle_delete_selected(self): self.delete_selected_resources()
    def _on_delete_button_clicked(self): self.delete_selected_resources()
    
    def _connect_to_unified_loader(self):
        """Ensure connection to unified resource loader for data loading"""
        try:
            from Utils.unified_resource_loader import get_unified_resource_loader
            loader = get_unified_resource_loader()
            if loader:
                # Ensure signals are connected (base class might not have connected them yet)
                try:
                    loader.loading_completed.disconnect(self._on_unified_resources_loaded)
                except:
                    pass  # Connection doesn't exist, which is fine
                
                try:
                    loader.loading_error.disconnect(self._on_unified_loading_error)
                except:
                    pass  # Connection doesn't exist, which is fine
                
                # Connect the signals
                loader.loading_completed.connect(self._on_unified_resources_loaded)
                loader.loading_error.connect(self._on_unified_loading_error)
                
                logging.info("NodesPage: Connected to unified resource loader")
                
                # Trigger initial load if not done already
                if not getattr(self, '_initial_load_triggered', False):
                    QTimer.singleShot(100, self._trigger_initial_load)
                    self._initial_load_triggered = True
            else:
                logging.error("NodesPage: Could not get unified resource loader")
        except Exception as e:
            logging.error(f"NodesPage: Error connecting to unified loader: {e}")
    
    def _trigger_initial_load(self):
        """Trigger initial data load"""
        try:
            self.refresh_data()
            logging.info("NodesPage: Triggered initial data load")
        except Exception as e:
            logging.error(f"NodesPage: Error triggering initial load: {e}")
    
    def _on_unified_loading_error(self, resource_type, error_message):
        """Handle unified loading errors"""
        if resource_type == self.resource_type:
            logging.error(f"NodesPage: Failed to load {resource_type}: {error_message}")
            # Show empty state with error message
            self.populate_table([])
    
    def cleanup(self):
        """Clean up resources when page is destroyed"""
        try:
            if hasattr(self, 'graph_update_timer') and self.metrics_update_timer:
                self.metrics_update_timer.stop()
                logging.debug("NodesPage: Stopped graph update timer")
        except Exception as e:
            logging.error(f"NodesPage: Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except Exception as e:
            logging.error(f"NodesPage: Error in destructor: {e}")