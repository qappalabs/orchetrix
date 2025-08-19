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
from Utils.debounced_updater import get_debounced_updater
from Utils.performance_config import get_performance_config
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
        self.timer.start(45000)  # 45 seconds to reduce CPU usage

    def generate_utilization_data(self, nodes_data):
        """Generate utilization data for nodes - optimized for performance"""
        if not nodes_data or self._is_updating:
            return
            
        current_time = time.time()
        if current_time - self._last_update_time < 20.0:  # Increased throttle to 20 seconds
            return
        
        self._is_updating = True
        self._last_update_time = current_time
        
        try:
            # Batch process nodes more efficiently
            metric_key = self.title.replace(" Usage", "").lower() + "_usage"
            
            # Use dictionary comprehension for better performance
            new_data = {}
            for node in nodes_data:
                node_name = node.get("name", "unknown")
                metric_value = node.get(metric_key)
                
                if metric_value is not None:
                    try:
                        new_data[node_name] = float(metric_value)
                    except (ValueError, TypeError):
                        continue  # Skip invalid data
            
            # Update utilization_data in one operation
            if new_data:
                self.utilization_data.update(new_data)
                
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
        """Ultra-simplified paint event for maximum performance"""
        super().paintEvent(event)
        
        # Skip drawing if not visible or data is empty
        if not self.isVisible() or not self.data:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)  # Disabled for performance
        
        width = self.width() - 32
        height = 40
        bottom = self.height() - 25
        
        # Use cached color to avoid object creation
        if not hasattr(self, '_cached_color'):
            self._cached_color = QColor(self.color)
        
        # Simplified line drawing - no gradient for performance
        if len(self.data) > 1 and width > 0:
            # Pre-calculate min/max once
            if not hasattr(self, '_data_range') or len(self.data) != getattr(self, '_last_data_length', 0):
                self._min_value = min(self.data)
                self._max_value = max(self.data) 
                self._value_range = max(self._max_value - self._min_value, 10)
                self._data_range = True
                self._last_data_length = len(self.data)
            
            # Draw simple line without path objects for better performance
            painter.setPen(QPen(self._cached_color, 2))
            x_step = width / (len(self.data) - 1)
            
            prev_x = 16
            prev_y = bottom - ((self.data[0] - self._min_value) / self._value_range) * height
            
            for i in range(1, len(self.data)):
                x = 16 + i * x_step
                y = bottom - ((self.data[i] - self._min_value) / self._value_range) * height
                painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))
                prev_x, prev_y = x, y
        
        # Only draw labels if there's significant space
        if width > 200:
            painter.setPen(QPen(QColor("#FFFFFF"), 1))
            font = painter.font()
            font.setPointSize(9)
            painter.setFont(font)
            
            # Cache time strings to avoid repeated formatting
            if not hasattr(self, '_cached_times') or time.time() - getattr(self, '_last_time_update', 0) > 60:
                now = datetime.datetime.now()
                start_time = now - datetime.timedelta(minutes=10)
                self._cached_times = (start_time.strftime("%H:%M"), now.strftime("%H:%M"))
                self._last_time_update = time.time()
            
            painter.drawText(QRectF(1, self.height() - 16, 30, 12), Qt.AlignmentFlag.AlignCenter, self._cached_times[0])
            painter.drawText(QRectF(width - 15, self.height() - 16, 30, 12), Qt.AlignmentFlag.AlignCenter, self._cached_times[1])
        
        # Only show placeholder if no node selected and space is available
        if not self.selected_node and width > 150:
            painter.setPen(QPen(QColor(AppColors.TEXT_SUBTLE)))
            text_rect = QRectF(0, self.rect().top() + 20, self.rect().width(), 30)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "Select a node")

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
        
        # Get performance configuration and debounced updater
        self.perf_config = get_performance_config()
        self.debounced_updater = get_debounced_updater()
        
        # Get the cluster connector
        self.cluster_connector = get_cluster_connector()
        
        # Connect to node data signal with error handling
        if self.cluster_connector:
            try:
                self.cluster_connector.node_data_loaded.connect(self._debounced_update_nodes)
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
        
        # Completely remove checkbox functionality for nodes
        if self.table:
            self.table.hideColumn(0)
            # Remove select all checkbox completely
            if hasattr(self, 'select_all_checkbox') and self.select_all_checkbox:
                self.select_all_checkbox.hide()
                self.select_all_checkbox.deleteLater()
                self.select_all_checkbox = None
            
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
        """Configure column widths for responsive screen utilization"""
        if not self.table:
            return
            
        self.table.hideColumn(0)
        header = self.table.horizontalHeader()
        
        # Use responsive column sizing
        QTimer.singleShot(100, self._setup_responsive_columns)
    
    def _setup_responsive_columns(self):
        """Setup responsive column sizing for nodes table"""
        if not self.table:
            return
            
        header = self.table.horizontalHeader()
        available_width = self.table.viewport().width() - 20  # Account for scrollbar
        
        if available_width <= 0:
            return
        
        # Column priorities and minimum widths
        column_config = [
            (0, 40, 40, "fixed"),      # Hidden checkbox
            (1, 140, 100, "priority"), # Name (priority)
            (2, 110, 80, "normal"),    # CPU
            (3, 110, 80, "normal"),    # Memory
            (4, 110, 80, "normal"),    # Disk
            (5, 60, 50, "compact"),    # Taints
            (6, 120, 80, "normal"),    # Roles
            (7, 90, 60, "compact"),    # Version
            (8, 60, 50, "compact"),    # Age
            (9, 90, 70, "stretch"),    # Conditions (stretch)
            (10, 40, 40, "fixed")      # Actions
        ]
        
        # Calculate total reserved space for fixed and minimum widths
        reserved_space = sum(min_width for _, _, min_width, _ in column_config)
        remaining_space = max(0, available_width - reserved_space)
        
        # Distribute remaining space based on priorities
        priority_columns = sum(1 for _, _, _, col_type in column_config if col_type == "priority")
        normal_columns = sum(1 for _, _, _, col_type in column_config if col_type == "normal")
        
        if priority_columns > 0:
            priority_extra = remaining_space * 0.4 / priority_columns  # 40% to priority columns
            normal_extra = remaining_space * 0.6 / normal_columns if normal_columns > 0 else 0
        else:
            priority_extra = 0
            normal_extra = remaining_space / normal_columns if normal_columns > 0 else 0
        
        for col_index, default_width, min_width, col_type in column_config:
            if col_index >= self.table.columnCount():
                continue
                
            if col_type == "fixed":
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col_index, min_width)
            elif col_type == "stretch":
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Interactive)
                if col_type == "priority":
                    width = int(min_width + priority_extra)
                elif col_type == "normal":
                    width = int(min_width + normal_extra)
                else:  # compact
                    width = min_width
                
                self.table.setColumnWidth(col_index, max(width, min_width))
        
        QTimer.singleShot(50, self._ensure_full_width_utilization)

    def show_no_data_message(self):
        """Show no data message using base class implementation"""
        self._show_empty_message()
        
    def show_table(self):
        """Show the table using base class implementation"""
        if hasattr(self, '_table_stack') and self._table_stack:
            self._table_stack.setCurrentWidget(self.table)

    def _debounced_update_nodes(self, nodes_data):
        """Debounced wrapper for update_nodes to prevent excessive updates"""
        self.debounced_updater.schedule_update(
            "nodes_update", 
            self.update_nodes, 
            300,  # 300ms delay
            nodes_data
        )

    def update_nodes(self, nodes_data):
        """Update with real node data from the cluster - optimized for speed"""
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
        
        # Store the data
        self.nodes_data = nodes_data
        self.resources = nodes_data
        self.has_loaded_data = True
        
        self.show_table()
        
        # Update graphs asynchronously to avoid blocking UI
        QTimer.singleShot(10, lambda: self._update_graphs_async(nodes_data))
        
        # Populate table with optimized method
        self.populate_table(nodes_data)
        
        self.items_count.setText(f"{len(nodes_data)} items")
    
    def _update_graphs_async(self, nodes_data):
        """Update graphs asynchronously to avoid blocking UI"""
        try:
            self.cpu_graph.generate_utilization_data(nodes_data)
            self.mem_graph.generate_utilization_data(nodes_data) 
            self.disk_graph.generate_utilization_data(nodes_data)
        except Exception as e:
            logging.error(f"Error updating graphs: {e}")
    
    def populate_resource_row(self, row, resource):
        """Fallback method for compatibility - redirects to optimized version"""
        return self.populate_resource_row_optimized(row, resource)

    def populate_table(self, resources_to_populate):
        """Populate table with resource data - heavily optimized for performance"""
        if not self.table or not resources_to_populate: 
            return
            
        logging.info(f"NodesPage: populate_table() called with {len(resources_to_populate)} resources")
        
        # Disable all expensive operations during population
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        
        # Clear and resize table efficiently
        self.table.clearContents()
        self.table.setRowCount(len(resources_to_populate))
        
        # Use batched rendering for better performance with large datasets
        batch_size = self.perf_config.get('table_batch_size', 25)  # Use performance config
        total_items = len(resources_to_populate)
        
        for start_idx in range(0, total_items, batch_size):
            end_idx = min(start_idx + batch_size, total_items)
            batch = resources_to_populate[start_idx:end_idx]
            
            # Populate batch
            for i, resource in enumerate(batch):
                actual_row = start_idx + i
                self.populate_resource_row_optimized(actual_row, resource)
            
            # Process events every batch to keep UI responsive
            QApplication.processEvents()
        
        # Re-enable updates and sorting
        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)
        
        # Force a single repaint
        self.table.update()

    def populate_resource_row_optimized(self, row, resource):
        """Highly optimized row population - minimizes widget creation"""
        self.table.setRowHeight(row, 40)
        
        node_name = resource.get("name", "unknown")
        
        # Skip creating complex widgets during initial population for speed
        # Create simple checkbox container
        checkbox_container = self._create_checkbox_container(row, node_name)
        checkbox_container.setStyleSheet("background-color: transparent;")
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Pre-calculate all display values
        display_values = self._calculate_display_values_fast(resource)
        
        # Create table items in one pass
        for col, (value, sort_value) in enumerate(display_values):
            cell_col = col + 1
            item = SortableTableWidgetItem(value, sort_value) if sort_value is not None else SortableTableWidgetItem(value)
            
            # Set alignment based on column type
            if col in [1, 2, 3, 4, 5, 6, 7]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, cell_col, item)
        
        # Create status and action widgets - defer complex styling
        self._create_status_and_action_widgets_fast(row, resource, len(display_values))
    
    def _calculate_display_values_fast(self, resource):
        """Pre-calculate all display values for faster rendering"""
        # CPU data
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
        
        # Memory data
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
        
        # Disk data
        disk_usage = resource.get("disk_usage")
        if disk_usage is not None:
            display_disk = f"Cluster ({disk_usage:.1f}%)"
            disk_util = disk_usage
        else:
            display_disk = "N/A"
            disk_util = 0
        
        # Other data
        taints = resource.get("taints", "0")
        try:
            taint_sort = int(taints)
        except ValueError:
            taint_sort = 0
        
        roles = resource.get("roles", [])
        roles_text = ", ".join(roles) if isinstance(roles, list) else str(roles)
        
        version = resource.get("version", "Unknown")
        age = resource.get("age", "Unknown")
        
        # Age sorting value
        try:
            if 'd' in age:
                age_sort = int(age.replace('d', '')) * 1440
            elif 'h' in age:
                age_sort = int(age.replace('h', '')) * 60
            elif 'm' in age:
                age_sort = int(age.replace('m', ''))
            else:
                age_sort = 0
        except ValueError:
            age_sort = 0
        
        return [
            (resource.get("name", "unknown"), None),
            (display_cpu, cpu_util),
            (display_mem, mem_util),
            (display_disk, disk_util),
            (str(taints), taint_sort),
            (roles_text, None),
            (version, None),
            (age, age_sort)
        ]
    
    def _create_status_and_action_widgets_fast(self, row, resource, column_offset):
        """Create status and action widgets with minimal styling"""
        status = resource.get("status", "Unknown")
        status_col = column_offset + 1
        
        # Simple status widget
        color = AppColors.STATUS_ACTIVE if status.lower() == "ready" else AppColors.STATUS_DISCONNECTED
        status_widget = StatusLabel(status, color)
        status_widget.clicked.connect(lambda: self.table.selectRow(row))
        self.table.setCellWidget(row, status_col, status_widget)
        
        # Use base class action button implementation with proper styling
        node_name = resource.get("name", "unknown")
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
        
        # Store raw data for potential use
        if "raw_data" not in resource:
            resource["raw_data"] = {
                "metadata": {"name": node_name},
                "status": {"conditions": [{"type": status, "status": "True"}]}
            }
    
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
        """Override to disable checkbox functionality"""
        pass
        
    def _handle_select_all(self, state):
        """Override to disable select all functionality"""
        pass
    
    def _create_checkbox_container(self, row, item_name):
        """Override to create empty container for nodes (no checkbox needed)"""
        from PyQt6.QtWidgets import QWidget
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        return container