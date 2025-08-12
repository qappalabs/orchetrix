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
from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from utils.cluster_connector import get_cluster_connector
from UI.Icons import resource_path
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
# StatusLabel - Same implementation as in PodsPage
#------------------------------------------------------------------
class StatusLabel(QWidget):
    """Widget that displays a status with consistent styling and background handling."""
    clicked = pyqtSignal()
    
    def __init__(self, status_text, color=None, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.label = QLabel(status_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if color:
            self.label.setStyleSheet(f"color: {QColor(color).name()}; background-color: transparent;")
        
        layout.addWidget(self.label)
        self.setStyleSheet("background-color: transparent;")
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

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

        # Much longer timer interval for better performance
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(30000)  # 30 seconds for better performance

    def generate_utilization_data(self, nodes_data):
        """Generate utilization data for nodes"""
        if not nodes_data or self._is_updating:
            return
            
        current_time = time.time()
        if current_time - self._last_update_time < 15.0:  # Throttle to 15 seconds
            return
        
        self._is_updating = True
        self._last_update_time = current_time
        
        try:
            # Keep existing data and update gradually
            old_data = self.utilization_data.copy()
            
            for node in nodes_data:
                node_name = node.get("name", "unknown")
                
                if self.title == "CPU Usage":
                    cpu_usage = node.get("cpu_usage")
                    if cpu_usage is not None:
                        utilization = float(cpu_usage)
                    else:
                        # No real data available, skip this node
                        continue
                elif self.title == "Memory Usage":
                    memory_usage = node.get("memory_usage")
                    if memory_usage is not None:
                        utilization = float(memory_usage)
                    else:
                        # No real data available, skip this node
                        continue
                else:  # Disk Usage
                    disk_usage = node.get("disk_usage")
                    if disk_usage is not None:
                        utilization = float(disk_usage)
                    else:
                        # No real data available, skip this node
                        continue
                
                self.utilization_data[node_name] = utilization
        finally:
            self._is_updating = False

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
        """Update the chart data - only use real cluster data"""
        if not self.selected_node or self.node_name not in self.utilization_data:
            return
            
        # Use the actual utilization value from real cluster data
        current_utilization = self.utilization_data[self.node_name]
        
        # Only update if we have valid real data
        if current_utilization is not None and current_utilization >= 0:
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

# No Data Available Widget - removed, now using base class implementation

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
        self.selected_row = -1
        self.has_loaded_data = False
        self.is_loading = False
        
        # Get the cluster connector
        self.cluster_connector = get_cluster_connector()
        
        # Connect to node data signal with error handling
        if self.cluster_connector:
            try:
                self.cluster_connector.node_data_loaded.connect(self.update_nodes)
            except Exception as e:
                logging.error(f"Error connecting to cluster connector signals: {e}")
                self.cluster_connector = None
        
        # Initialize data structure
        self.nodes_data = []
        
        # Set up UI
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Nodes page"""
        headers = ["", "Name", "CPU", "Memory", "Disk", "Taints", "Roles", "Version", "Age", "Conditions", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8, 9}
        
        layout = super().setup_ui("Nodes", headers, sortable_columns)
        
        # Keep select all checkbox but hide the checkbox column for nodes
        if self.table:
            self.table.hideColumn(0)
            # Keep select_all_checkbox but ensure it's disabled for nodes
            if hasattr(self, 'select_all_checkbox') and self.select_all_checkbox:
                self.select_all_checkbox.hide()
            
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
        
        # No need for custom no-data widget - use base class implementation

    def configure_columns(self):
        """Configure column widths for full screen utilization"""
        if not self.table:
            return
            
        self.table.hideColumn(0)
        header = self.table.horizontalHeader()
        
        column_specs = [
            (0, 40, "fixed"),        # Hidden checkbox
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
        """Show no data message using base class implementation"""
        self._show_empty_message()
        
    def show_table(self):
        """Show the table using base class implementation"""
        if hasattr(self, '_table_stack') and self._table_stack:
            self._table_stack.setCurrentWidget(self.table)

    def update_nodes(self, nodes_data):
        """Update with real node data from the cluster"""
        logging.info(f"NodesPage: update_nodes() called with {len(nodes_data) if nodes_data else 0} nodes")
        
        self.is_loading = False
        self.is_showing_skeleton = False
        
        if hasattr(self, 'skeleton_timer') and self.skeleton_timer.isActive():
            self.skeleton_timer.stop()
        
        if not nodes_data:
            logging.warning("NodesPage: No nodes data received")
            self.nodes_data = []
            self.resources = []
            self.show_no_data_message()
            self.items_count.setText("0 items")
            return
        
        logging.info(f"NodesPage: Processing {len(nodes_data)} nodes")
        if nodes_data:
            logging.info(f"NodesPage: First node data keys: {list(nodes_data[0].keys()) if nodes_data[0] else 'No keys'}")
        
        # Store the data
        self.nodes_data = nodes_data
        self.resources = nodes_data
        self.has_loaded_data = True
        
        self.show_table()
        
        # Generate utilization data for graphs
        self.cpu_graph.generate_utilization_data(nodes_data)
        self.mem_graph.generate_utilization_data(nodes_data)
        self.disk_graph.generate_utilization_data(nodes_data)
        
        # Clear and populate table
        self.table.setRowCount(0)
        self.populate_table(nodes_data)
        self.table.setSortingEnabled(True)
        
        self.items_count.setText(f"{len(nodes_data)} items")

    def populate_table(self, resources_to_populate):
        """Populate table with resource data - optimized for nodes"""
        if not self.table or not resources_to_populate: 
            return
            
        logging.info(f"NodesPage: populate_table() called with {len(resources_to_populate)} resources")
        
        # Disable sorting during population for better performance
        self.table.setSortingEnabled(False)
        
        # Clear and resize table efficiently
        self.table.setRowCount(len(resources_to_populate))
        
        # Populate rows in larger batches for better performance
        batch_size = 25  # Larger batches for better performance
        for i in range(0, len(resources_to_populate), batch_size):
            batch = resources_to_populate[i:i + batch_size]
            for j, resource in enumerate(batch):
                self.populate_resource_row(i + j, resource)
            
            # Process events less frequently to reduce overhead
            if i % (batch_size * 4) == 0:
                QApplication.processEvents()
        
        # Re-enable sorting
        self.table.setSortingEnabled(True)

    def populate_resource_row(self, row, resource):
        """Populate a single row with Node data"""
        self.table.setRowHeight(row, 40)
        
        node_name = resource.get("name", "unknown")
        
        # Create checkbox container (hidden)
        checkbox_container = self._create_checkbox_container(row, node_name)
        checkbox_container.setStyleSheet("background-color: transparent;")
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Get real utilization data (no dummy data)
        cpu_usage = resource.get("cpu_usage")
        cpu_capacity = resource.get("cpu_capacity", "")
        if cpu_usage is not None and cpu_capacity:
            display_cpu = f"{cpu_capacity} ({cpu_usage:.1f}%)"
            cpu_util = cpu_usage
        elif cpu_capacity:
            display_cpu = f"{cpu_capacity}"
            cpu_util = 0
        else:
            display_cpu = "N/A"
            cpu_util = 0
        
        memory_usage = resource.get("memory_usage") 
        mem_capacity = resource.get("memory_capacity", "")
        if memory_usage is not None and mem_capacity:
            display_mem = f"{mem_capacity} ({memory_usage:.1f}%)"
            mem_util = memory_usage
        elif mem_capacity:
            display_mem = f"{mem_capacity}"
            mem_util = 0
        else:
            display_mem = "N/A"
            mem_util = 0
        
        disk_usage = resource.get("disk_usage")
        disk_capacity = resource.get("disk_capacity", "")
        if disk_usage is not None:
            # Show cluster-wide disk usage percentage
            display_disk = f"Cluster ({disk_usage:.1f}%)"
            disk_util = disk_usage
        elif disk_capacity:
            display_disk = f"{disk_capacity}"
            disk_util = 0
        else:
            display_disk = "N/A"
            disk_util = 0
        
        taints = resource.get("taints", "0")
        
        roles = resource.get("roles", [])
        if isinstance(roles, list):
            roles_text = ", ".join(roles)
        else:
            roles_text = str(roles)
            
        version = resource.get("version", "Unknown")
        age = resource.get("age", "Unknown")
        status = resource.get("status", "Unknown")
        
        # Store raw data for potential use
        if "raw_data" not in resource:
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
            str(taints),
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
                except ValueError:
                    sort_value = 0
                item = SortableTableWidgetItem(value, sort_value)
            elif col == 7:  # Age column
                try:
                    if 'd' in value:
                        age_value = int(value.replace('d', '')) * 1440
                    elif 'h' in value:
                        age_value = int(value.replace('h', '')) * 60
                    elif 'm' in value:
                        age_value = int(value.replace('m', ''))
                    else:
                        age_value = 0
                except ValueError:
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
        
        # Use base class action button implementation
        action_button = self._create_action_button(row, node_name)
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
    
    def _highlight_active_row(self, row, is_active):
        """Highlight the row when its menu is active"""
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                if is_active:
                    item.setBackground(QColor(AppColors.ACCENT_BLUE + "22"))  # 13% opacity
                else:
                    item.setBackground(QColor("transparent"))

    # Removed _create_node_action_button - now uses base class _create_action_button
    
    # Removed custom _handle_action - now uses base class implementation with nodes support
    
    # Removed _handle_node_action - now uses base class _handle_action
    
    def select_node_for_graphs(self, row):
        """Select a node to show in the graphs"""
        if row < 0 or row >= len(self.nodes_data):
            return
            
        self.selected_row = row
        node_name = self.table.item(row, 1).text()
        node_data = None
        
        # Find the node data
        for node in self.nodes_data:
            if node.get("name") == node_name:
                node_data = node
                break
                
        if not node_data:
            return
            
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
                    
                    parent.detail_manager.show_detail(resource_type, resource_name, None)
            
    def load_data(self, load_more=False):
        """Override to fetch node data from cluster connector"""
        logging.info(f"NodesPage: load_data() called, is_loading={self.is_loading}")
        
        if self.is_loading:
            return
            
        self.is_loading = True
        
        if hasattr(self, 'cluster_connector') and self.cluster_connector:
            logging.info("NodesPage: Calling cluster_connector.load_nodes()")
            self.cluster_connector.load_nodes()
        else:
            logging.warning("NodesPage: No cluster_connector available")
            self.is_loading = False
            self.show_no_data_message()
    
    def force_load_data(self):
        """Override base class force_load_data to use cluster connector"""
        logging.info("NodesPage: force_load_data() called")
        self.load_data()
    
    def _add_controls_to_header(self, header_layout):
        """Override to add custom controls for nodes page without delete button"""
        self._add_filter_controls(header_layout)
        header_layout.addStretch(1)

        # Only add refresh button, no delete button for nodes
        refresh_btn = QPushButton("Refresh")
        refresh_style = getattr(AppStyles, "SECONDARY_BUTTON_STYLE",
                                """QPushButton { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3d3d3d;
                                               border-radius: 4px; padding: 5px 10px; }
                                   QPushButton:hover { background-color: #3d3d3d; }
                                   QPushButton:pressed { background-color: #1e1e1e; }"""
                                )
        refresh_btn.setStyleSheet(refresh_style)
        refresh_btn.clicked.connect(lambda: self.force_load_data())
        header_layout.addWidget(refresh_btn)
        
    def _add_filter_controls(self, header_layout):
        """Override to remove namespace dropdown for nodes (cluster-scoped resources)"""
        from PyQt6.QtWidgets import QLineEdit, QLabel
        from UI.Styles import AppStyles
        
        # Create a separate layout for filters with proper spacing
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(12)  # Add space between elements
        
        # Search bar with label - only search, no namespace dropdown for nodes
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: normal;")
        search_label.setMinimumWidth(50)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search nodes...")
        self.search_bar.textChanged.connect(self._on_search_text_changed)
        self.search_bar.setFixedWidth(200)
        self.search_bar.setFixedHeight(32)
        
        # Apply consistent styling
        search_style = getattr(AppStyles, 'SEARCH_INPUT', 
            """QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                background-color: #353535;
            }""")
        self.search_bar.setStyleSheet(search_style)
        
        # Add widgets to layout - no namespace dropdown
        filters_layout.addWidget(search_label)
        filters_layout.addWidget(self.search_bar)
        
        # Add the filters layout directly to header layout
        header_layout.addLayout(filters_layout)
        
        # Set namespace_combo to None since nodes don't use namespaces
        self.namespace_combo = None
        
    # Disable inherited methods that aren't needed for nodes
    def _handle_checkbox_change(self, state, item_name):
        pass
        
    def _handle_select_all(self, state):
        pass