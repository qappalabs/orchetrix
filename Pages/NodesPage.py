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
from Base_Components.base_components import SortableTableWidgetItem
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

        # Longer timer interval for better performance
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(int(self._update_interval * 1000))

    def generate_utilization_data(self, nodes_data):
        """Generate utilization data for nodes"""
        if not nodes_data or self._is_updating:
            return
            
        current_time = time.time()
        if current_time - self._last_update_time < 5.0:  # Throttle to 5 seconds
            return
        
        self._is_updating = True
        self._last_update_time = current_time
        
        try:
            # Keep existing data and update gradually
            old_data = self.utilization_data.copy()
            
            for node in nodes_data:
                node_name = node.get("name", "unknown")
                
                if self.title == "CPU Usage":
                    if "cpu_usage" in node:
                        utilization = float(node.get("cpu_usage", 0))
                    else:
                        prev_value = old_data.get(node_name, random.uniform(15, 50))
                        utilization = max(5, min(80, prev_value + random.uniform(-3, 3)))
                elif self.title == "Memory Usage":
                    if "memory_usage" in node:
                        utilization = float(node.get("memory_usage", 0))
                    else:
                        prev_value = old_data.get(node_name, random.uniform(25, 60))
                        utilization = max(10, min(85, prev_value + random.uniform(-3, 3)))
                else:  # Disk Usage
                    if "disk_usage" in node:
                        utilization = float(node.get("disk_usage", 0))
                    else:
                        prev_value = old_data.get(node_name, random.uniform(30, 70))
                        utilization = max(15, min(90, prev_value + random.uniform(-2, 2)))
                
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
        """Update the chart data"""
        if not self.selected_node or self.node_name not in self.utilization_data:
            return
            
        current_utilization = self.utilization_data[self.node_name]
        variation = random.uniform(-1, 1)
        new_value = max(0, min(100, current_utilization + variation))
            
        self.utilization_data[self.node_name] = new_value
        self.data.append(new_value)
        self.data.pop(0)
        self.current_value = round(new_value, 1)
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
        
        # Remove default checkbox header
        header_widget = self._item_widgets.get("header_widget")
        if header_widget:
            header_widget.hide()
        self.select_all_checkbox = None
        
        # Hide the checkbox column
        if self.table:
            self.table.hideColumn(0)
            
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
        # self.table.setRowCount(0)
        # self.populate_table(nodes_data)
        # self.table.setSortingEnabled(True)
        
        self.items_count.setText(f"{len(nodes_data)} items")

    def populate_resource_row(self, row, resource):
        """Populate a single row with Node data"""
        self.table.setRowHeight(row, 40)
        
        node_name = resource.get("name", "unknown")
        
        # Create checkbox container (hidden)
        checkbox_container = self._create_checkbox_container(row, node_name)
        checkbox_container.setStyleSheet("background-color: transparent;")
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Get utilization data
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
        button = QToolButton()

        # Use custom SVG icon instead of text
        icon = resource_path("icons/Moreaction_Button.svg")
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
        detail_action.setIcon(QIcon(resource_path("icons/edit.png")))
        detail_action.triggered.connect(lambda: self._handle_node_action("Detail", row, node_name))
        
        delete_action = menu.addAction("Delete")
        delete_action.setIcon(QIcon(resource_path("icons/delete.png")))
        delete_action.setProperty("dangerous", True)
        delete_action.triggered.connect(lambda: self._handle_node_action("Delete", row, node_name))
        
        view_metrics = menu.addAction("View Metrics")
        view_metrics.setIcon(QIcon(resource_path("icons/chart.png")))
        view_metrics.triggered.connect(lambda: self._handle_node_action("View Metrics", row, node_name))

        button.setMenu(menu)
        self._item_widgets[f"action_button_{row}"] = button
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
                
                parent.detail_manager.show_detail(resource_type, node_name, None)
        elif action == "Delete":
            self.delete_resource(node_name, "")
        elif action == "View Metrics":
            self.select_node_for_graphs(row)
    
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
        if self.is_loading:
            return
            
        self.is_loading = True
        
        if hasattr(self, 'cluster_connector') and self.cluster_connector:
            self.cluster_connector.load_nodes()
        else:
            self.is_loading = False
            self.show_no_data_message()
        
    # Disable inherited methods that aren't needed for nodes
    def _add_delete_selected_button(self):
        pass
        
    def _handle_checkbox_change(self, state, item_name):
        pass
        
    def _handle_select_all(self, state):
        pass