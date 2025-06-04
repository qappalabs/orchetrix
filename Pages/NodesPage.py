"""
Dynamic implementation of the Nodes page with live Kubernetes data and resource operations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QToolButton, QMenu, QCheckBox, QFrame, 
    QGraphicsDropShadowEffect, QSizePolicy, QStyleOptionButton, QStyle, QStyleOptionHeader,
    QApplication, QPushButton, QProxyStyle
)
from PyQt6.QtCore import Qt, QTimer, QRect, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QLinearGradient, QPainterPath, QBrush, QCursor

from UI.Styles import AppStyles, AppColors
from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from utils.cluster_connector import get_cluster_connector
import random
import datetime
import re

#------------------------------------------------------------------
# Custom Style to hide checkbox in header
#------------------------------------------------------------------
class CustomHeaderStyle(QProxyStyle):
    """A proxy style that hides checkbox in header"""
    def __init__(self, style=None):
        super().__init__(style)
        
    def drawControl(self, element, option, painter, widget=None):
        # Don't draw checkbox in header
        if element == QStyle.ControlElement.CE_Header:
            # Create a copy of the option to modify
            opt = QStyleOptionHeader(option)
            # Check if it's the first section (checkbox column)
            if widget and widget.orientation() == Qt.Orientation.Horizontal and opt.section == 0:
                # Leave the background but hide text
                opt.text = ""
                super().drawControl(element, opt, painter, widget)
                return
        # For all other elements, use the default drawing
        super().drawControl(element, option, painter, widget)

#------------------------------------------------------------------
# StatusLabel - Same implementation as in PodsPage
#------------------------------------------------------------------
class StatusLabel(QWidget):
    """Widget that displays a status with consistent styling and background handling."""
    clicked = pyqtSignal()
    
    def __init__(self, status_text, color=None, parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create label
        self.label = QLabel(status_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set color if provided, otherwise use default color
        if color:
            self.label.setStyleSheet(f"color: {QColor(color).name()}; background-color: transparent;")
        
        # Add label to layout
        layout.addWidget(self.label)
        
        # Make sure this widget has a transparent background
        self.setStyleSheet("background-color: transparent;")
    
    def mousePressEvent(self, event):
        """Emit clicked signal when widget is clicked"""
        self.clicked.emit()
        super().mousePressEvent(event)

#------------------------------------------------------------------
# GraphWidget
#------------------------------------------------------------------
class GraphWidget(QFrame):
    """Custom widget for displaying resource utilization graphs"""
    def __init__(self, title, unit, color, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.color = color
        self.data = [0] * 24  # Initialize with zeros
        self.current_value = 0
        self.selected_node = None  # Will store the selected node data
        self.node_name = "None"
        self.utilization_data = {}  # Store utilization data for all nodes

        self.setMinimumHeight(120)
        self.setMaximumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Apply styles from Styles.py
        self.setStyleSheet(AppStyles.GRAPH_FRAME_STYLE)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
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

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(3000)

    def generate_utilization_data(self, nodes_data):
        """Generate or update utilization data for nodes"""
        self.utilization_data = {}
        if not nodes_data:
            return
            
        for node in nodes_data:
            node_name = node.get("name", "unknown")
            
            # Extract utilization data from node info if available
            if self.title == "CPU Usage":
                if "cpu_usage" in node:
                    utilization = float(node.get("cpu_usage", 0))
                else:
                    utilization = random.uniform(10, 70)  # Fallback to random for demo
                self.utilization_data[node_name] = utilization
                    
            elif self.title == "Memory Usage":
                if "memory_usage" in node:
                    utilization = float(node.get("memory_usage", 0))
                else:
                    utilization = random.uniform(30, 80)  # Fallback to random for demo
                self.utilization_data[node_name] = utilization
                
            else:  # Disk Usage
                if "disk_usage" in node:
                    utilization = float(node.get("disk_usage", 0))
                else:
                    utilization = random.uniform(40, 90)  # Fallback to random for demo
                self.utilization_data[node_name] = utilization

    def get_node_utilization(self, node_name):
        return self.utilization_data.get(node_name, 0)

    def set_selected_node(self, node_data, node_name):
        """Set the selected node for this graph"""
        self.selected_node = node_data
        self.node_name = node_name
        self.title_label.setText(f"{self.title} ({node_name})")
        if node_name in self.utilization_data:
            self.current_value = round(self.utilization_data[node_name], 1)
            self.value_label.setText(f"{self.current_value}{self.unit}")
        self.update_data()

    def update_data(self):
        """Update the chart data"""
        if not self.selected_node or self.node_name not in self.utilization_data:
            return
            
        current_utilization = self.utilization_data[self.node_name]
        
        # Add a small variation to simulate real-time changes
        variation = random.uniform(-2, 2)
        new_value = current_utilization + variation
        
        # Keep values within reasonable limits
        if self.title == "CPU Usage":
            new_value = max(min(new_value, 95), 5)
        elif self.title == "Memory Usage":
            new_value = max(min(new_value, 95), 10)
        else:
            new_value = max(min(new_value, 98), 20)
            
        self.utilization_data[self.node_name] = new_value
        self.data.append(new_value)
        self.data.pop(0)
        self.current_value = round(new_value, 1)
        self.value_label.setText(f"{self.current_value}{self.unit}")
        self.update()
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width() - 32
        height = 55  # Slightly reduced height to allow for spacing
        
        # Increase the space between graph and x-axis by setting bottom higher
        bottom = self.height() - 25  # More space at bottom for labels (increased from 15 to 25)
        top = bottom - height
        
        gradient = QLinearGradient(0, top, 0, bottom)
        base_color = QColor(self.color)
        gradient.setColorAt(0, QColor(base_color.red(), base_color.green(), base_color.blue(), 100))
        gradient.setColorAt(1, QColor(base_color.red(), base_color.green(), base_color.blue(), 5))
        min_value = min(self.data)
        max_value = max(self.data)
        value_range = max(max_value - min_value, 10)
        path = QPainterPath()
        line_path = QPainterPath()
        x_step = width / (len(self.data) - 1)
        x = 16
        y = bottom - ((self.data[0] - min_value) / value_range) * height
        path.moveTo(x, y)
        line_path.moveTo(x, y)
        for i in range(1, len(self.data)):
            x = 16 + i * x_step
            y = bottom - ((self.data[i] - min_value) / value_range) * height
            path.lineTo(x, y)
            line_path.lineTo(x, y)
        path.lineTo(x, bottom)
        path.lineTo(16, bottom)
        path.closeSubpath()
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(self.color), 2))
        painter.drawPath(line_path)
        
        # Draw a subtle x-axis line to visually separate the graph from labels
        painter.setPen(QPen(QColor(AppColors.BORDER_COLOR), 1, Qt.PenStyle.DotLine))
        painter.drawLine(16, bottom + 1, 16 + width, bottom + 1)
        
        # Draw time labels with simpler approach for better visibility
        # Use a bright, contrasting color for the time labels
        painter.setPen(QPen(QColor("#FFFFFF"), 1))  # Bright white for maximum contrast
        
        # Use a larger, bold font for time labels
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        
        # Improved time label formatting for x-axis
        now = datetime.datetime.now()
        times = [
            now - datetime.timedelta(minutes=20),
            now - datetime.timedelta(minutes=10),
            now
        ]
        x_positions = [16, 16 + width/2, 16 + width]
        
        # Position time labels below the graph with adequate spacing
        label_y_position = self.height() - 4  # Keep close to bottom but not cut off
        
        for i, t in enumerate(times):
            time_str = t.strftime("%H:%M")
            x = x_positions[i]
            
            # Draw text directly without background
            painter.drawText(
                QRectF(x - 25, label_y_position - 12, 50, 16),
                Qt.AlignmentFlag.AlignCenter, 
                time_str
            )
        
        # If no node is selected, show the placeholder text
        if not self.selected_node:
            painter.setPen(QPen(QColor(AppColors.TEXT_SUBTLE)))
            # Draw text but avoid overlapping with the time labels
            text_rect = QRectF(
                0, 
                self.rect().top(), 
                self.rect().width(), 
                self.rect().height() - 20  # Stay above time labels
            )
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "Select a node to view metrics")
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
    
    Features:
    1. Dynamic loading of Nodes from the cluster
    2. Resource utilization graphs
    3. Editing Nodes with editor
    4. Deleting Nodes (individual)
    5. Resource details viewer
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "nodes"
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
        # Define headers with empty first column for checkbox (it will be hidden)
        # The empty string in first position will be hidden but we need it for structure
        headers = ["", "Name", "CPU", "Memory", "Disk", "Taints", "Roles", "Version", "Age", "Conditions", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8, 9}  # Adjusted for checkbox column
        
        # Set up the base UI components with styles
        layout = super().setup_ui("Nodes", headers, sortable_columns)
        
        # Remove default checkbox header and show column name instead
        header_widget = self._item_widgets.get("header_widget")
        if header_widget:
            header_widget.hide()
        # Clear select-all functionality
        self.select_all_checkbox = None
        
        # Manually hide the checkbox column
        if self.table:
            self.table.hideColumn(0)
            
        # Now that we have a layout, set margins and spacing
        self.layout().setContentsMargins(16, 16, 16, 16)
        self.layout().setSpacing(16)
        
        # Add graphs (CPU, Memory, Disk) at the top - insert at the beginning of the layout
        graphs_layout = QHBoxLayout()
        self.cpu_graph = GraphWidget("CPU Usage", "%", AppColors.ACCENT_ORANGE)
        self.mem_graph = GraphWidget("Memory Usage", "%", AppColors.ACCENT_BLUE)
        self.disk_graph = GraphWidget("Disk Usage", "%", AppColors.ACCENT_PURPLE)
        graphs_layout.addWidget(self.cpu_graph)
        graphs_layout.addWidget(self.mem_graph)
        graphs_layout.addWidget(self.disk_graph)
        
        # Insert the graphs layout at the beginning of the main layout
        if self.layout().count() > 0:
            # Create a widget to hold the graphs
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
        
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Set checkbox column width (will be hidden but still needs configuration)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 30)
        
        # Configure stretch columns (adjusted for checkbox column)
        stretch_columns = [1, 2, 3, 4, 5, 6, 7, 8, 9]  # All columns except action and checkbox
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width column for action
        self.table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(10, 40)
        
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
        # Stop skeleton animation and reset loading state
        self.is_loading = False
        self.is_showing_skeleton = False
        
        # Stop skeleton animation if running
        if hasattr(self, 'skeleton_timer') and self.skeleton_timer.isActive():
            self.skeleton_timer.stop()
        
        if not nodes_data:
            self.nodes_data = []
            self.resources = []
            self.show_no_data_message()
            self.items_count.setText("0 items")
            return
        
        # Store the node data
        self.nodes_data = nodes_data
        self.resources = nodes_data  # Also store in the base class variable
        self.has_loaded_data = True
        
        # Make sure we show the table
        self.show_table()
        
        # Generate utilization data for graphs
        self.cpu_graph.generate_utilization_data(nodes_data)
        self.mem_graph.generate_utilization_data(nodes_data)
        self.disk_graph.generate_utilization_data(nodes_data)
        
        # Update the table - clear first
        self.table.setRowCount(0)  # Clear first
        self.populate_table(nodes_data)
        self.table.setSortingEnabled(True)
        
        # Update items count
        self.items_count.setText(f"{len(nodes_data)} items")
        
        # Apply any existing filters
        if hasattr(self, '_apply_filters'):
            self._apply_filters()
            
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with Node data
        """
        # Set row height
        self.table.setRowHeight(row, 40)
        
        # Get the node name
        node_name = resource.get("name", "unknown")
        
        # We'll still need to create checkbox widget as it's part of BaseResourcePage structure
        # but we'll hide the column at the UI level and make the checkbox transparent
        checkbox_container = self._create_checkbox_container(row, node_name)
        checkbox_container.setStyleSheet("background-color: transparent;")
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Prepare node data for display
        cpu_util = self.cpu_graph.get_node_utilization(node_name)
        cpu_capacity = resource.get("cpu_capacity", "")
        display_cpu = f"{cpu_capacity} ({cpu_util:.1f}%)" if cpu_capacity else f"{cpu_util:.1f}%"
        
        mem_util = self.mem_graph.get_node_utilization(node_name)
        mem_capacity = resource.get("memory_capacity", "")
        display_mem = f"{mem_capacity} ({mem_util:.1f}%)" if mem_capacity else f"{mem_util:.1f}%"
        
        disk_util = self.disk_graph.get_node_utilization(node_name)
        disk_capacity = resource.get("disk_capacity", "")
        display_disk = f"{disk_capacity} ({disk_util:.1f}%)" if disk_capacity else f"{disk_util:.1f}%"
        
        taints = resource.get("taints", "0")
        
        roles = resource.get("roles", [])
        if isinstance(roles, list):
            roles_text = ", ".join(roles)
        else:
            roles_text = str(roles)
            
        version = resource.get("version", "Unknown")
        age = resource.get("age", "Unknown")
        status = resource.get("status", "Unknown")
        
        # Store raw data for editing
        if "raw_data" not in resource:
            resource["raw_data"] = {
                "metadata": {
                    "name": node_name
                },
                "status": {
                    "conditions": [
                        {"type": status, "status": "True"}
                    ]
                }
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
            # Adjust for checkbox column which is still there but hidden
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
            elif col == 4:  # Taints column (numeric)
                try:
                    sort_value = int(taints)
                except ValueError:
                    sort_value = 0
                item = SortableTableWidgetItem(value, sort_value)
            elif col == 7:  # Age column
                try:
                    # Convert age string (like "5d" or "2h") to minutes for sorting
                    if 'd' in value:
                        age_value = int(value.replace('d', '')) * 1440  # days to minutes
                    elif 'h' in value:
                        age_value = int(value.replace('h', '')) * 60  # hours to minutes
                    elif 'm' in value:
                        age_value = int(value.replace('m', ''))  # minutes
                    else:
                        age_value = 0
                except ValueError:
                    age_value = 0
                item = SortableTableWidgetItem(value, age_value)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in [1, 2, 3, 4, 6, 7]:  # CPU, Memory, Disk, Taints, Version, Age
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Add the item to the table
            self.table.setItem(row, cell_col, item)
        
        # Add Status column as a widget (like in PodsPage)
        status_col = len(columns) + 1  # Status column index (adjusted for checkbox column)
        
        # Determine status color
        if status.lower() == "ready":
            color = AppColors.STATUS_ACTIVE  # Green for Ready
        else:
            color = AppColors.STATUS_DISCONNECTED  # Red for other statuses
            
        # Create StatusLabel widget with color
        status_widget = StatusLabel(status, color)
        status_widget.clicked.connect(lambda: self.table.selectRow(row))
        self.table.setCellWidget(row, status_col, status_widget)
        
        # Create and add action button with Edit, Delete, and View Metrics options
        action_button = self._create_node_action_button(row, node_name)
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, status_col + 1, action_container)
    
    def _create_node_action_button(self, row, node_name):
        """Create an action button with node-specific options"""
        button = QToolButton()
        button.setText("⋮")
        button.setFixedWidth(30)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Create menu
        menu = QMenu(button)
        menu.setStyleSheet(AppStyles.MENU_STYLE)
        
        # Add actions to menu
        edit_action = menu.addAction("Edit")
        edit_action.setIcon(QIcon("icons/edit.png"))
        edit_action.triggered.connect(lambda: self._handle_node_action("Edit", row, node_name))
        
        delete_action = menu.addAction("Delete")
        delete_action.setIcon(QIcon("icons/delete.png"))
        delete_action.setProperty("dangerous", True)
        delete_action.triggered.connect(lambda: self._handle_node_action("Delete", row, node_name))
        
        view_metrics = menu.addAction("View Metrics")
        view_metrics.setIcon(QIcon("icons/chart.png"))
        view_metrics.triggered.connect(lambda: self._handle_node_action("View Metrics", row, node_name))
        
        button.setMenu(menu)
        return button
    
    def _handle_node_action(self, action, row, node_name):
        """Handle node-specific actions"""
        if row >= len(self.nodes_data):
            return
        
        resource = self.nodes_data[row]
        
        if action == "Edit":
            # Make sure raw_data exists for editing
            if "raw_data" not in resource or not resource["raw_data"]:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Edit Not Available",
                    f"Node {node_name} cannot be edited in this view."
                )
                return
                
            # Use the BaseResourcePage's edit functionality
            self.edit_resource(resource)
        elif action == "Delete":
            # Use the BaseResourcePage's delete functionality
            self.delete_resource(node_name, "")
        elif action == "View Metrics":
            # Select the node for metrics display
            self.select_node_for_graphs(row)
    
    def select_node_for_graphs(self, row):
        """Select a node to show in the graphs"""
        if row < 0 or row >= len(self.nodes_data):
            return
            
        self.selected_row = row
        node_name = self.table.item(row, 1).text()  # Name is at column 1 (after checkbox column)
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
            # Select the row
            self.table.selectRow(row)
            self.select_node_for_graphs(row)
            # Get resource details
            resource_name = None
            namespace = None
            
            # Get the resource name
            if self.table.item(row, 1) is not None:
                resource_name = self.table.item(row, 1).text()
            
            # Get namespace if applicable
            if self.table.item(row, 2) is not None:
                namespace = self.table.item(row, 2).text()
            
            # Show detail view
            if resource_name:
                # Find the ClusterView instance
                parent = self.parent()
                while parent and not hasattr(parent, 'detail_manager'):
                    parent = parent.parent()
                
                if parent and hasattr(parent, 'detail_manager'):
                    # Get singular resource type
                    resource_type = self.resource_type
                    if resource_type.endswith('s'):
                        resource_type = resource_type[:-1]
                    
                    parent.detail_manager.show_detail(resource_type, resource_name, namespace)
            
    def load_data(self, load_more=False):
        """Override to fetch node data from cluster connector"""
        # Skip if already loading
        if self.is_loading:
            return
            
        self.is_loading = True
        
        # If we have a cluster connector, ask it to load node data
        if hasattr(self, 'cluster_connector') and self.cluster_connector:
            self.cluster_connector.load_nodes()
        else:
            # If no connector, hide loading and show error
            self.is_loading = False
            self.is_showing_skeleton = False
            if hasattr(self, 'skeleton_timer') and self.skeleton_timer.isActive():
                self.skeleton_timer.stop()
            self.show_no_data_message()
        
    def _add_delete_selected_button(self):
        """Override to not add the delete selected button for nodes"""
        # Since we're hiding the checkboxes, we don't need the delete selected button
        pass
        
    def _handle_checkbox_change(self, state, item_name):
        """Override to disable checkbox functionality for nodes"""
        # We're disabling checkbox functionality by hiding the column
        pass
        
    def _handle_select_all(self, state):
        """Override to disable select all functionality for nodes"""
        # We're disabling select all functionality by hiding the checkbox column
        pass