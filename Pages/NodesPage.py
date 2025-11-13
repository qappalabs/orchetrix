"""
Corrected implementation of the Nodes page with performance improvements and proper data display.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QToolButton, QMenu, QCheckBox, QFrame, 
    QGraphicsDropShadowEffect, QSizePolicy, QStyleOptionButton, QStyle, QStyleOptionHeader,
    QApplication, QPushButton, QProxyStyle
)
from PyQt6.QtCore import Qt, QTimer, QRect, QRectF, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QLinearGradient, QPainterPath, QBrush, QCursor

from UI.Styles import AppStyles, AppColors, AppConstants
from Base_Components.base_components import SortableTableWidgetItem, StatusLabel
from Base_Components.base_resource_page import BaseResourcePage
from Utils.cluster_connector import get_cluster_connector
from UI.Icons import resource_path
import random
import datetime
import re
import logging
import time

#------------------------------------------------------------------
# Custom Style to hide checkbox in header
#------------------------------------------------------------------
class CustomHeaderStyle(QProxyStyle):
    """A proxy style that hides checkbox in header"""
    def __init__(self, style=None):
        super().__init__(style)
        
    def drawControl(self, element, option, painter, widget=None):
        if element == QStyle.ControlElement.CE_Header:
            opt = QStyleOptionHeader(option)
            if widget and widget.orientation() == Qt.Orientation.Horizontal and opt.section == 0:
                opt.text = ""
                super().drawControl(element, opt, painter, widget)
                return
        super().drawControl(element, option, painter, widget)


#------------------------------------------------------------------
# Optimized GraphWidget
#------------------------------------------------------------------
class GraphWidget(QFrame):
    """Optimized widget for displaying resource utilization graphs"""
    def __init__(self, title, unit, color, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.color = color
        self.data = [0] * 12
        self.current_value = 0
        self.selected_node = None
        self.node_name = "None"
        self.utilization_data = {}
        self._last_update_time = 0
        self._update_interval = 10.0  # 10 seconds
        self._is_updating = False

        self.setMinimumHeight(120)
        self.setMaximumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.setStyleSheet(AppStyles.GRAPH_FRAME_STYLE)

        # Reduced shadow effect for performance
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"{title} (No node selected)")
        self.title_label.setStyleSheet(AppStyles.GRAPH_TITLE_STYLE)
        self.value_label = QLabel(f"0{unit}")
        self.value_label.setStyleSheet(AppStyles.graph_value_style(self.color))
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.value_label)
        layout.addLayout(header_layout)
        layout.addStretch()

        # Longer timer interval for better performance
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(int(self._update_interval * 1000))

    def generate_utilization_data(self, nodes_data):
        """Generate utilization data for nodes from real metrics - NON-BLOCKING"""
        if not nodes_data or self._is_updating:
            return
            
        current_time = time.time()
        if current_time - self._last_update_time < 5.0:  # Throttle to 5 seconds
            return
        
        self._is_updating = True
        self._last_update_time = current_time
        
        # Extract node names with proper validation
        node_names = []
        for node in nodes_data:
            if isinstance(node, dict):
                name = node.get("name")
                if name:
                    node_names.append(name)
            else:
                logging.warning(f"Graph: Invalid node data format: {type(node)}")
        
        if not node_names:
            logging.warning("Graph: No valid node names found for metrics")
            self._is_updating = False
            return
        
        # IMPORTANT: Do metrics fetching in a separate thread to prevent UI freezing
        from PyQt6.QtCore import QThread, QObject, pyqtSignal
        
        class MetricsWorker(QObject):
            metrics_ready = pyqtSignal(dict)
            
            def __init__(self, node_names, graph_title):
                super().__init__()
                self.node_names = node_names
                self.graph_title = graph_title
            
            def fetch_metrics(self):
                try:
                    from Utils.kubernetes_client import get_kubernetes_client
                    kube_client = get_kubernetes_client()
                    
                    metrics_data = {}
                    
                    if hasattr(kube_client, 'metrics_service'):
                        # Get all node metrics in batch for efficiency
                        all_node_metrics = kube_client.metrics_service.get_all_node_metrics_fast(
                            node_names=self.node_names,
                            include_disk_usage=(self.graph_title == "Disk Usage")
                        )
                        
                        for node_name in self.node_names:
                            node_metrics = all_node_metrics.get(node_name)
                            
                            if node_metrics:
                                if self.graph_title == "CPU Usage":
                                    utilization = node_metrics.get("cpu", {}).get("usage", 0)
                                elif self.graph_title == "Memory Usage":
                                    utilization = node_metrics.get("memory", {}).get("usage", 0)
                                else:  # Disk Usage
                                    disk_usage = node_metrics.get("disk", {}).get("usage")
                                    utilization = disk_usage if disk_usage is not None else 0
                                
                                # Ensure utilization is within reasonable bounds
                                utilization = max(0, min(100, utilization))
                                metrics_data[node_name] = utilization
                                
                                logging.debug(f"Real {self.graph_title} for {node_name}: {utilization:.1f}%")
                            else:
                                # If we can't get real metrics, show 0 instead of random data
                                metrics_data[node_name] = 0
                                logging.debug(f"No real metrics available for {node_name}, showing 0%")
                    else:
                        # No metrics service available, show 0 for all nodes
                        for node_name in self.node_names:
                            metrics_data[node_name] = 0
                            
                except Exception as e:
                    logging.error(f"Error getting real node metrics for graphs: {e}")
                    # On error, show 0 instead of random data
                    for node_name in self.node_names:
                        metrics_data[node_name] = 0
                
                self.metrics_ready.emit(metrics_data)
        
        # Create worker and thread
        self.metrics_worker = MetricsWorker(node_names, self.title)
        self.metrics_thread = QThread()
        
        # Connect signals
        self.metrics_worker.metrics_ready.connect(self._on_metrics_ready)
        self.metrics_worker.moveToThread(self.metrics_thread)
        self.metrics_thread.started.connect(self.metrics_worker.fetch_metrics)
        
        # Start the thread
        self.metrics_thread.start()
    
    def _on_metrics_ready(self, metrics_data):
        """Handle metrics data received from background thread"""
        try:
            self.utilization_data.update(metrics_data)
            logging.info(f"Updated {self.title} metrics for {len(metrics_data)} nodes")
        except Exception as e:
            logging.error(f"Error updating metrics data: {e}")
        finally:
            self._is_updating = False
            # Clean up thread
            if hasattr(self, 'metrics_thread') and self.metrics_thread:
                self.metrics_thread.quit()
                self.metrics_thread.wait()
                self.metrics_thread.deleteLater()
                self.metrics_worker.deleteLater()

    def get_node_utilization(self, node_name):
        return self.utilization_data.get(node_name, 0)

    def set_selected_node(self, node_data, node_name):
        """Set the selected node for this graph"""
        if not node_data or not node_name:
            return
            
        self.selected_node = node_data
        self.node_name = node_name
        self.title_label.setText(f"{self.title} ({node_name})")
        
        if node_name in self.utilization_data:
            self.current_value = round(self.utilization_data[node_name], 1)
            self.value_label.setText(f"{self.current_value}{self.unit}")

    def update_data(self):
        """Update the chart data with real metrics"""
        if not self.selected_node or self.node_name not in self.utilization_data:
            return
            
        # Get the latest real utilization data (no random variation)
        current_utilization = self.utilization_data[self.node_name]
        
        # Update the data series for the graph
        self.data.append(current_utilization)
        self.data.pop(0)
        self.current_value = round(current_utilization, 1)
        self.value_label.setText(f"{self.current_value}{self.unit}")
        
        if self.isVisible():
            self.update()

    def paintEvent(self, event):
        """Simplified paint event for better performance"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)  # Disabled for performance
        
        width = self.width() - 32
        height = 40
        bottom = self.height() - 25
        top = bottom - height
        
        # Simple gradient
        base_color = QColor(self.color)
        gradient = QLinearGradient(0, top, 0, bottom)
        gradient.setColorAt(0, QColor(base_color.red(), base_color.green(), base_color.blue(), 60))
        gradient.setColorAt(1, QColor(base_color.red(), base_color.green(), base_color.blue(), 10))
        
        min_value = min(self.data) if self.data else 0
        max_value = max(self.data) if self.data else 100
        value_range = max(max_value - min_value, 10)
        
        # Draw simple line chart
        if len(self.data) > 1:
            path = QPainterPath()
            x_step = width / (len(self.data) - 1)
            
            for i, data_point in enumerate(self.data):
                x = 16 + i * x_step
                y = bottom - ((data_point - min_value) / value_range) * height
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            
            painter.setPen(QPen(base_color, 2))
            painter.drawPath(path)
        
        # Simple time labels
        painter.setPen(QPen(QColor("#FFFFFF"), 1))
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        
        now = datetime.datetime.now()
        start_time = now - datetime.timedelta(minutes=10)
        
        painter.drawText(QRectF(16 - 15, self.height() - 16, 30, 12), Qt.AlignmentFlag.AlignCenter, start_time.strftime("%H:%M"))
        painter.drawText(QRectF(16 + width - 15, self.height() - 16, 30, 12), Qt.AlignmentFlag.AlignCenter, now.strftime("%H:%M"))
        
        if not self.selected_node:
            painter.setPen(QPen(QColor(AppColors.TEXT_SUBTLE)))
            text_rect = QRectF(0, self.rect().top(), self.rect().width(), self.rect().height() - 20)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "Select a node to view metrics")

    def cleanup(self):
        """Cleanup method"""
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()

# No Data Available Widget
class NoDataWidget(QWidget):
    """Widget shown when no data is available"""
    def __init__(self, message="No data available", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel("📊")
        icon_label.setStyleSheet("font-size: 48px; color: #666;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        message_label = QLabel(message)
        message_label.setStyleSheet("font-size: 18px; color: #666;")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(icon_label)
        layout.addWidget(message_label)

#------------------------------------------------------------------
# NodesPage - Now extending BaseResourcePage for consistency
#------------------------------------------------------------------
class NodesPage(BaseResourcePage):
    """
    Displays Kubernetes Nodes with live data and resource operations.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "nodes"
        self.show_namespace_dropdown = False  # Hide namespace dropdown for Nodes page
        self.selected_row = -1
        self.has_loaded_data = False
        self.is_loading = False
        
        # Get the cluster connector
        self.cluster_connector = get_cluster_connector()
        
        # Connect to node data signal
        self.cluster_connector.node_data_loaded.connect(self.update_nodes)
        
        # Initialize data structure
        self.nodes_data = []
        
        # Set up UI
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Nodes page"""
        headers = ["", "Name", "CPU", "Memory", "Disk", "Taints", "Roles", "Version", "Age", "Conditions", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8, 9}
        
        layout = super().setup_ui("Nodes", headers, sortable_columns)
        
        # Keep checkbox functionality enabled for Nodes page
            
        self.layout().setContentsMargins(16, 16, 16, 16)
        self.layout().setSpacing(16)
        
        # Add graphs at the top
        graphs_layout = QHBoxLayout()
        self.cpu_graph = GraphWidget("CPU Usage", "%", AppColors.ACCENT_ORANGE)
        self.mem_graph = GraphWidget("Memory Usage", "%", AppColors.ACCENT_BLUE)
        self.disk_graph = GraphWidget("Disk Usage", "%", AppColors.ACCENT_PURPLE)
        graphs_layout.addWidget(self.cpu_graph)
        graphs_layout.addWidget(self.mem_graph)
        graphs_layout.addWidget(self.disk_graph)
        
        if self.layout().count() > 0:
            graphs_widget = QWidget()
            graphs_widget.setLayout(graphs_layout)
            self.layout().insertWidget(0, graphs_widget)
        
        # Apply table style
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)

        # Configure column widths
        self.configure_columns()

        # Create no-data widget
        self.no_data_widget = NoDataWidget("No node data available. Please connect to a cluster.")
        self.no_data_widget.hide()
        self.layout().addWidget(self.no_data_widget)

        # Use default blue spinner to match other pages
        self._spinner_type = "circular"

    def configure_columns(self):
        """Configure column widths for full screen utilization"""
        if not self.table:
            return
            
        # Show checkbox column (column 0)
        header = self.table.horizontalHeader()
        
        column_specs = [
            (0, 40, "fixed"),        # Checkbox
            (1, 140, "interactive"), # Name
            (2, 110, "interactive"), # CPU
            (3, 110, "interactive"), # Memory
            (4, 110, "interactive"), # Disk
            (5, 60, "interactive"),  # Taints
            (6, 90, "interactive"),  # Roles
            (7, 90, "interactive"),  # Version
            (8, 60, "interactive"),  # Age
            (9, 110, "stretch"),     # Conditions
            (10, 40, "fixed")        # Actions
        ]
        
        for col_index, default_width, resize_type in column_specs:
            if col_index < self.table.columnCount():
                if resize_type == "fixed":
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Fixed)
                    self.table.setColumnWidth(col_index, default_width)
                elif resize_type == "interactive":
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Interactive)
                    self.table.setColumnWidth(col_index, default_width)
                elif resize_type == "stretch":
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Stretch)
        
        QTimer.singleShot(100, self._ensure_full_width_utilization)

    def show_no_data_message(self):
        """Show no data message instead of table"""
        self.table.hide()
        self.no_data_widget.show()
        
    def show_table(self):
        """Show the table and hide no data message"""
        self.no_data_widget.hide()
        self.table.show()

    def update_nodes(self, nodes_data):
        """Update with real node data from the cluster"""
        self.is_loading = False
        self.is_showing_skeleton = False
        
        if hasattr(self, 'skeleton_timer') and self.skeleton_timer.isActive():
            self.skeleton_timer.stop()
        
        if not nodes_data:
            self.nodes_data = []
            self.resources = []
            self.show_no_data_message()
            self.items_count.setText("0 items")
            return
        
        # Validate and normalize data format
        logging.info(f"Received {len(nodes_data)} nodes, validating data format...")
        
        # Run validation check
        if not self.validate_data_format(nodes_data):
            logging.warning("Data format validation failed, proceeding with normalization...")
        
        normalized_nodes = []
        for i, node_data in enumerate(nodes_data):
            try:
                if isinstance(node_data, dict):
                    # Data is already in correct format - preserve all fields including raw_data
                    normalized_nodes.append(node_data)
                else:
                    # Handle NodeInfo objects or other formats
                    logging.warning(f"Node {i} has unexpected format: {type(node_data)}")
                    if hasattr(node_data, '__dict__'):
                        # Convert object to dictionary, preserving raw_data
                        node_dict = {
                            "name": getattr(node_data, 'name', 'Unknown'),
                            "status": getattr(node_data, 'status', 'Unknown'),
                            "roles": getattr(node_data, 'roles', ['<none>']),
                            "cpu_capacity": getattr(node_data, 'cpu_capacity', ''),
                            "memory_capacity": getattr(node_data, 'memory_capacity', ''),
                            "disk_capacity": getattr(node_data, 'disk_capacity', ''),
                            "taints": str(getattr(node_data, 'taints', '0')),
                            "version": getattr(node_data, 'version', 'Unknown'),
                            "age": getattr(node_data, 'age', 'Unknown'),
                            "raw_data": getattr(node_data, 'raw_data', {})
                        }
                        # Log if raw_data is missing to help debug
                        if not node_dict["raw_data"]:
                            logging.warning(f"Node {node_dict['name']}: No raw_data found during object conversion")
                        normalized_nodes.append(node_dict)
                    else:
                        logging.error(f"Cannot process node data at index {i}: {node_data}")
            except Exception as e:
                logging.error(f"Error normalizing node {i}: {e}")
                continue
        
        if not normalized_nodes:
            logging.error("No valid node data after normalization")
            self.show_no_data_message()
            self.items_count.setText("0 items")
            return
        
        # Store the normalized data
        self.nodes_data = normalized_nodes
        self.resources = normalized_nodes
        self.has_loaded_data = True
        
        self.show_table()
        
        # Generate utilization data for graphs in background
        try:
            self.cpu_graph.generate_utilization_data(normalized_nodes)
            self.mem_graph.generate_utilization_data(normalized_nodes)
            self.disk_graph.generate_utilization_data(normalized_nodes)
        except Exception as e:
            logging.warning(f"Error generating graph data: {e}")
        
        # Populate table with normalized data
        logging.info(f"Populating node table with {len(normalized_nodes)} normalized nodes")
        try:
            self.table.setRowCount(0)  # Clear existing rows
            self._populate_nodes_table_optimized(normalized_nodes)
            self.table.setSortingEnabled(True)
            logging.info("Node table population completed successfully")
        except Exception as e:
            logging.error(f"Error populating node table: {e}")
            logging.debug("Table population error details", exc_info=True)
            # Fallback to showing error message
            self.show_no_data_message()
        
        self.items_count.setText(f"{len(normalized_nodes)} items")

    def _populate_nodes_table_optimized(self, nodes_data):
        """Optimized method to populate nodes table without blocking the UI thread"""
        if not nodes_data:
            return
            
        # Set row count
        self.table.setRowCount(len(nodes_data))
        
        # Disable sorting during population for performance
        self.table.setSortingEnabled(False)
        
        # Process nodes in batches to keep UI responsive
        batch_size = 25  # Process 25 nodes at a time
        for i in range(0, len(nodes_data), batch_size):
            batch_end = min(i + batch_size, len(nodes_data))
            batch = nodes_data[i:batch_end]
            
            # Populate this batch
            for j, node_data in enumerate(batch):
                row = i + j
                try:
                    self._populate_node_row_fast(row, node_data)
                except Exception as e:
                    logging.warning(f"Error populating node row {row}: {e}")
                    # Continue with next row instead of crashing
                    continue
            
            # Process UI events every batch to keep responsive
            QApplication.processEvents()
        
        # Re-enable sorting after all rows are populated
        self.table.setSortingEnabled(True)
        logging.info(f"Successfully populated {len(nodes_data)} node rows")

    def _populate_node_row_fast(self, row, resource):
        """Fast node row population without blocking API calls"""
        try:
            self.table.setRowHeight(row, 40)
            
            # Validate resource is a dictionary
            if not isinstance(resource, dict):
                logging.error(f"Row {row}: Expected dict, got {type(resource)}")
                return
            
            node_name = resource.get("name", "unknown")
            if not node_name or node_name == "unknown":
                logging.warning(f"Row {row}: Node has no valid name")
                return
            
            # Create checkbox container (visible)
            checkbox_container = self._create_checkbox_container(row, node_name)
            checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
            self.table.setCellWidget(row, 0, checkbox_container)
            
            # Get utilization data from graphs (already loaded in background)
            # This avoids the synchronous API calls that were causing freezing
            cpu_util = self.cpu_graph.get_node_utilization(node_name)
            mem_util = self.mem_graph.get_node_utilization(node_name) 
            disk_util = self.disk_graph.get_node_utilization(node_name)
            
            # Format display strings with capacity and utilization
            cpu_capacity = resource.get("cpu_capacity", "")
            if cpu_capacity:
                display_cpu = f"{cpu_capacity} ({cpu_util:.1f}%)"
            else:
                display_cpu = f"{cpu_util:.1f}%" if cpu_util > 0 else "N/A"
            
            mem_capacity = resource.get("memory_capacity", "")
            if mem_capacity:
                display_mem = f"{mem_capacity} ({mem_util:.1f}%)"
            else:
                display_mem = f"{mem_util:.1f}%" if mem_util > 0 else "N/A"
            
            disk_capacity = resource.get("disk_capacity", "")
            if disk_capacity:
                display_disk = f"{disk_capacity} ({disk_util:.1f}%)"
            else:
                display_disk = f"{disk_util:.1f}%" if disk_util > 0 else "N/A"
            
            taints = str(resource.get("taints", "0"))
            
            # Handle roles properly
            roles = resource.get("roles", [])
            if isinstance(roles, list):
                roles_text = ", ".join(roles) if roles else "<none>"
            else:
                roles_text = str(roles) if roles else "<none>"
                
            version = resource.get("version", "Unknown")
            age = resource.get("age", "Unknown")
            status = resource.get("status", "Unknown")
            
            # Ensure raw_data exists for detail view
            if "raw_data" not in resource or not resource["raw_data"]:
                resource["raw_data"] = {
                    "metadata": {"name": node_name},
                    "status": {"conditions": [{"type": status, "status": "True"}]}
                }
            
            # Prepare data columns
            columns = [
                node_name,
                display_cpu,
                display_mem,
                display_disk,
                taints,
                roles_text,
                version,
                age
            ]
            
            # Add columns to table
            for col, value in enumerate(columns):
                cell_col = col + 1
                
                # Handle numeric columns for sorting
                if col == 1:  # CPU column
                    sort_value = cpu_util
                    item = SortableTableWidgetItem(value, sort_value)
                elif col == 2:  # Memory column
                    sort_value = mem_util
                    item = SortableTableWidgetItem(value, sort_value)
                elif col == 3:  # Disk column
                    sort_value = disk_util
                    item = SortableTableWidgetItem(value, sort_value)
                elif col == 4:  # Taints column
                    try:
                        sort_value = int(taints)
                    except (ValueError, TypeError):
                        sort_value = 0
                    item = SortableTableWidgetItem(value, sort_value)
                elif col == 7:  # Age column
                    try:
                        if isinstance(value, str):
                            if 'd' in value:
                                age_value = int(value.replace('d', '')) * 1440
                            elif 'h' in value:
                                age_value = int(value.replace('h', '')) * 60
                            elif 'm' in value:
                                age_value = int(value.replace('m', ''))
                            else:
                                age_value = 0
                        else:
                            age_value = 0
                    except (ValueError, TypeError):
                        age_value = 0
                    item = SortableTableWidgetItem(value, age_value)
                else:
                    item = SortableTableWidgetItem(value)
                
                # Set text alignment
                if col in [1, 2, 3, 4, 5, 6, 7]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, cell_col, item)
            
            # Add Status column as a widget
            status_col = len(columns) + 1
            
            if status.lower() == "ready":
                color = AppColors.STATUS_ACTIVE
            else:
                color = AppColors.STATUS_DISCONNECTED
                
            status_widget = StatusLabel(status, color)
            status_widget.clicked.connect(lambda: self.table.selectRow(row))
            self.table.setCellWidget(row, status_col, status_widget)
            
            # Create and add action button with proper styling
            action_button = self._create_node_action_button(row, node_name)
            action_button.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE +
        """
        QToolButton::menu-indicator { image: none; width: 0px; }
        """)
            
            # Create action container with proper styling
            action_container = QWidget()
            action_container.setFixedWidth(AppConstants.SIZES["ACTION_WIDTH"])
            action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
            action_layout = QHBoxLayout(action_container)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(0)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            action_layout.addWidget(action_button)
            
            self.table.setCellWidget(row, status_col + 1, action_container)
            
            logging.debug(f"Successfully populated row {row} for node {node_name}")
            
        except Exception as e:
            logging.error(f"Error populating row {row}: {e}")
            logging.debug(f"Row population error details for row {row}", exc_info=True)
            # Continue with next row instead of crashing
            pass

    def populate_resource_row(self, row, resource):
        """Populate a single row with Node data - FIXED to avoid blocking API calls"""
        # IMPORTANT: Delegate to optimized method to prevent UI freezing
        # The old implementation made synchronous API calls for every row which
        # caused the application to freeze and crash with large node counts
        self._populate_node_row_fast(row, resource)
    
    def _highlight_active_row(self, row, is_active):
        """Highlight the row when its menu is active"""
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                if is_active:
                    item.setBackground(QColor(AppColors.ACCENT_BLUE + "22"))  # 13% opacity
                else:
                    item.setBackground(QColor("transparent"))

    def _create_node_action_button(self, row, node_name):
        """Create an action button with node-specific options"""
        try:
            button = QToolButton()

            # Use custom SVG icon instead of text
            icon = resource_path("Icons/Moreaction_Button.svg")
            button.setIcon(QIcon(icon))
            button.setIconSize(QSize(AppConstants.SIZES["ICON_SIZE"], AppConstants.SIZES["ICON_SIZE"]))

            # Remove text and change to icon-only style
            button.setText("")
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

            button.setFixedWidth(30)
            button.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE)
            button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            # Create menu
            menu = QMenu(button)
            menu.setStyleSheet(AppStyles.MENU_STYLE)

            # Connect signals to change row appearance when menu opens/closes
            menu.aboutToShow.connect(lambda: self._highlight_active_row(row, True))
            menu.aboutToHide.connect(lambda: self._highlight_active_row(row, False))

            # Add actions to menu
            detail_action = menu.addAction("Detail")
            try:
                detail_action.setIcon(QIcon(resource_path("icons/edit.png")))
            except:
                pass  # Icon not critical
            detail_action.triggered.connect(lambda: self._handle_node_action("Detail", row, node_name))
            
            delete_action = menu.addAction("Delete")
            try:
                delete_action.setIcon(QIcon(resource_path("icons/delete.png")))
            except:
                pass  # Icon not critical
            delete_action.setProperty("dangerous", True)
            delete_action.triggered.connect(lambda: self._handle_node_action("Delete", row, node_name))
            
            view_metrics = menu.addAction("View Metrics")
            try:
                view_metrics.setIcon(QIcon(resource_path("icons/chart.png")))
            except:
                pass  # Icon not critical
            view_metrics.triggered.connect(lambda: self._handle_node_action("View Metrics", row, node_name))

            button.setMenu(menu)
            
            # Store reference safely
            if not hasattr(self, '_item_widgets'):
                self._item_widgets = {}
            self._item_widgets[f"action_button_{row}"] = button
            
            return button
        except Exception as e:
            logging.warning(f"Error creating action button for row {row}: {e}")
            # Return a simple button as fallback
            button = QToolButton()
            button.setText("...")
            button.setFixedWidth(30)
            return button
    
    def _handle_node_action(self, action, row, node_name):
        """Handle node-specific actions"""
        if row >= len(self.nodes_data):
            return
        
        resource = self.nodes_data[row]
        
        if action == "Detail":
            # Show the detail view for the selected node
            parent = self.parent()
            while parent and not hasattr(parent, 'detail_manager'):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'detail_manager'):
                resource_type = self.resource_type
                if resource_type.endswith('s'):
                    resource_type = resource_type[:-1]
                
                # Get the raw_data for this node
                raw_data = resource.get("raw_data", {}) if resource else {}
                if not raw_data:
                    logging.warning(f"No raw_data found for node {node_name} in action handler")
                
                parent.detail_manager.show_detail(resource_type, node_name, None, raw_data)
        elif action == "Delete":
            self.delete_resource(node_name, "")
        elif action == "View Metrics":
            self.select_node_for_graphs(row)
    
    def select_node_for_graphs(self, row):
        """Select a node to show in the graphs"""
        if row < 0 or row >= len(self.nodes_data):
            logging.warning(f"Invalid row selection: {row}, available rows: {len(self.nodes_data)}")
            return
            
        self.selected_row = row
        
        # Get node name from table or data
        node_name = None
        if self.table.item(row, 1):
            node_name = self.table.item(row, 1).text()
        
        if not node_name:
            logging.warning(f"No node name found for row {row}")
            return
            
        node_data = None
        
        # Find the node data - handle both dict and object formats
        for node in self.nodes_data:
            if isinstance(node, dict):
                if node.get("name") == node_name:
                    node_data = node
                    break
            else:
                # Handle object format (fallback)
                if hasattr(node, 'name') and node.name == node_name:
                    node_data = {
                        "name": node.name,
                        "status": getattr(node, 'status', 'Unknown'),
                        "cpu_capacity": getattr(node, 'cpu_capacity', ''),
                        "memory_capacity": getattr(node, 'memory_capacity', ''),
                        "disk_capacity": getattr(node, 'disk_capacity', '')
                    }
                    break
                
        if not node_data:
            logging.warning(f"Node data not found for {node_name}")
            return
            
        logging.debug(f"Selected node {node_name} for graphs")
        self.table.selectRow(row)
        self.cpu_graph.set_selected_node(node_data, node_name)
        self.mem_graph.set_selected_node(node_data, node_name)
        self.disk_graph.set_selected_node(node_data, node_name)
    
    def handle_row_click(self, row, column):
        if column != self.table.columnCount() - 1:  # Skip action column
            self.table.selectRow(row)
            self.select_node_for_graphs(row)
            
            resource_name = None
            if self.table.item(row, 1) is not None:
                resource_name = self.table.item(row, 1).text()
            
            if resource_name:
                parent = self.parent()
                while parent and not hasattr(parent, 'detail_manager'):
                    parent = parent.parent()
                
                if parent and hasattr(parent, 'detail_manager'):
                    resource_type = self.resource_type
                    if resource_type.endswith('s'):
                        resource_type = resource_type[:-1]
                    
                    # Get the raw_data for this node from row data
                    raw_data = {}
                    if 0 <= row < len(self.nodes_data):
                        node_data = self.nodes_data[row]
                        raw_data = node_data.get("raw_data", {}) if isinstance(node_data, dict) else {}
                        if not raw_data:
                            logging.warning(f"No raw_data found for node {resource_name} in row click handler")
                    
                    parent.detail_manager.show_detail(resource_type, resource_name, None, raw_data)
            
    def load_data(self, load_more=False):
        """Override to fetch node data from cluster connector with proper error handling"""
        if self.is_loading:
            logging.debug("Node data loading already in progress, skipping")
            return
            
        self.is_loading = True
        logging.info("Starting node data loading process")
        
        try:
            if hasattr(self, 'cluster_connector') and self.cluster_connector:
                # Show loading indicator
                self.show_loading_indicator("Loading nodes...")
                
                # Check if cluster is connected
                current_cluster = self.cluster_connector.current_cluster
                if current_cluster:
                    state = self.cluster_connector.get_connection_state(current_cluster)
                    logging.info(f"Cluster {current_cluster} connection state: {state}")
                    
                    if state == "connected":
                        self.cluster_connector.load_nodes()
                        logging.info("Node data loading request sent to cluster connector")
                    else:
                        logging.warning(f"Cluster not connected (state: {state}), cannot load nodes")
                        self.is_loading = False
                        self.show_no_data_message()
                        self.hide_loading_indicator()
                else:
                    logging.warning("No current cluster selected")
                    self.is_loading = False
                    self.show_no_data_message()
                    self.hide_loading_indicator()
            else:
                logging.error("No cluster connector available")
                self.is_loading = False
                self.show_no_data_message()
                self.hide_loading_indicator()
        except Exception as e:
            logging.error(f"Error loading node data: {e}")
            logging.debug("Node data loading error details", exc_info=True)
            self.is_loading = False
            self.show_no_data_message()
            self.hide_loading_indicator()
    
    def validate_data_format(self, nodes_data):
        """Validate that node data is in the expected format for debugging"""
        if not nodes_data:
            logging.warning("NodesPage: No nodes data provided for validation")
            return False
        
        valid_count = 0
        for i, node in enumerate(nodes_data):
            if isinstance(node, dict):
                required_fields = ["name", "status", "roles", "cpu_capacity", "memory_capacity", "disk_capacity"]
                has_all_fields = all(field in node for field in required_fields)
                
                # Check if raw_data exists and log if missing
                if "raw_data" not in node or not node["raw_data"]:
                    node_name = node.get("name", f"node_{i}")
                    logging.warning(f"NodesPage: Node {node_name} missing raw_data - detail view may not work properly")
                
                if has_all_fields:
                    valid_count += 1
                else:
                    missing_fields = [field for field in required_fields if field not in node]
                    logging.warning(f"NodesPage: Node {i} missing fields: {missing_fields}")
            else:
                logging.warning(f"NodesPage: Node {i} is not a dictionary: {type(node)}")
        
        success_rate = valid_count / len(nodes_data) * 100
        logging.info(f"NodesPage: Data validation - {valid_count}/{len(nodes_data)} nodes valid ({success_rate:.1f}%)")
        return success_rate >= 80  # Consider valid if at least 80% of nodes are properly formatted
