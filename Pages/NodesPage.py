"""
Corrected implementation of the Nodes page with performance improvements and proper data display.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QHeaderView, QToolButton, QMenu, QCheckBox, QFrame, 
    QGraphicsDropShadowEffect, QSizePolicy, QStyleOptionButton, QStyle, QStyleOptionHeader,
    QApplication, QPushButton, QProxyStyle
)
from PyQt6.QtCore import Qt, QTimer, QRect, QRectF, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QLinearGradient, QPainterPath, QBrush, QCursor

from UI.Styles import AppStyles, AppColors, AppConstants
from Base_Components.base_components import SortableTableWidgetItem, StatusLabel
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
        self._update_interval = 5.0  # 5 seconds for real-time updates
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

        # Real-time timer interval for better user experience  
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(5000)  # 5 seconds for real-time updates

    def generate_utilization_data(self, nodes_data):
        """Generate utilization data for nodes - optimized for performance"""
        if not nodes_data or self._is_updating:
            return
            
        current_time = time.time()
        # Only throttle if we have data and enough time hasn't passed
        if (self.utilization_data and 
            self._last_update_time > 0 and 
            current_time - self._last_update_time < self._update_interval):
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
                logging.debug(f"{self.title}: Updated utilization data for {len(new_data)} nodes: {new_data}")
            else:
                logging.debug(f"{self.title}: No utilization data found in nodes for metric_key: {metric_key}")
                
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
        
        logging.debug(f"Setting selected node {node_name} for {self.title}")
        logging.debug(f"Available utilization data: {list(self.utilization_data.keys())}")
        
        if node_name in self.utilization_data:
            self.current_value = round(self.utilization_data[node_name], 1)
            self.value_label.setText(f"{self.current_value}{self.unit}")
            logging.debug(f"Set {self.title} value: {self.current_value}{self.unit}")
            
            # Force immediate graph update with current data
            self.update_data()
            
            # Start/restart the timer for real-time updates
            self.timer.start(5000)
        else:
            logging.debug(f"No utilization data found for {node_name} in {self.title}")
            # Reset to show no selection
            self.current_value = 0
            self.value_label.setText(f"0{self.unit}")
            self.timer.stop()

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
        # Define columns for nodes table to match original layout
        node_columns = ["", "Name", "CPU", "Memory", "Disk", "Taints", "Roles", "Version", "Age", "Conditions", ""]
        
        # Initialize parent class
        super().__init__(parent)
        
        self.resource_type = "nodes"
        self.columns = node_columns
        self.has_namespace_column = False  # Nodes are cluster-level resources
        
        self.selected_row = -1
        self._selected_node_name = None
        self._is_double_clicking = False
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
        
        # Initialize search state
        self._is_searching = False
        self._current_search_query = None
        
        # Set up UI
        self.setup_page_ui()
    
    def cleanup_on_destroy(self):
        """Override base cleanup to handle NodesPage-specific resources"""
        try:
            # Stop NodesPage-specific timers
            if hasattr(self, '_graph_update_timer'):
                self._graph_update_timer.stop()
                self._graph_update_timer.deleteLater()
            
            # Disconnect cluster connector signals
            if hasattr(self, 'cluster_connector') and self.cluster_connector:
                try:
                    self.cluster_connector.node_data_loaded.disconnect(self._debounced_update_nodes)
                except (TypeError, RuntimeError):
                    pass  # Signal was not connected or object deleted
            
            # Call parent cleanup
            super().cleanup_on_destroy()
            
        except RuntimeError:
            # Widget already deleted - this is expected during shutdown
            logging.debug("NodesPage already deleted during cleanup")
        except Exception as e:
            logging.error(f"Error disconnecting signals in NodesPage: {e}")
            # Still call parent cleanup even if our cleanup fails
            try:
                super().cleanup_on_destroy()
            except RuntimeError:
                # Parent also deleted
                pass
        
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
        
        # Connect double-click to show detail page
        self.table.cellDoubleClicked.connect(self.handle_row_double_click)
        
        # Connect single-click to update graphs
        self.table.cellClicked.connect(self.handle_row_click)
        
        # Configure column widths
        self.configure_columns()

    def configure_columns(self):
        """Configure column widths for responsive screen utilization"""
        if not self.table:
            return
        
        # Use QTimer to delay column configuration until table is ready
        QTimer.singleShot(100, self._apply_column_configuration)
    
    def _apply_column_configuration(self):
        """Apply column configuration after table is ready"""
        try:
            if not hasattr(self.table, 'horizontalHeader'):
                return
            
            header = self.table.horizontalHeader()
            if not header:
                return
            
            # Hide only checkbox column, keep actions column visible
            self.table.setColumnHidden(0, True)   # Checkbox column
            # Actions column (column 10) should remain visible
            
            # Set up responsive sizing for the remaining columns
            self._setup_responsive_columns()
            
        except Exception as e:
            logging.error(f"Error applying column configuration: {e}")
    
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
            if col_index >= len(self.columns):
                continue
                
            if col_type == "fixed":
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Fixed)
                header.resizeSection(col_index, min_width)
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
                
                header.resizeSection(col_index, max(width, min_width))
        
        # Ensure full width utilization immediately after column setup
        self._ensure_full_width_utilization()

    def show_no_data_message(self):
        """Show no data message using base class implementation"""
        self._show_empty_message()
        
    def show_table(self):
        """Show the table using base class implementation"""
        if hasattr(self, '_table_stack') and self._table_stack:
            self._table_stack.setCurrentWidget(self.table)
        
        # Hide the empty overlay if it exists and is visible
        if hasattr(self, '_empty_overlay') and self._empty_overlay:
            self._empty_overlay.hide()

    def _debounced_update_nodes(self, nodes_data):
        """Debounced wrapper for update_nodes to prevent excessive updates"""
        if not self.has_loaded_data:
            self.debounced_updater.schedule_update(
                "nodes_update", 
                self.update_nodes, 
                300,  # 300ms delay
                nodes_data
            )
        else:
            self.update_nodes(nodes_data)

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
            if not getattr(self, '_is_searching', False):
                self._is_searching = False
                self._current_search_query = None
            self.show_no_data_message()
            self.items_count.setText("0 items")
            return
        
        # Store the data and cache timestamp for performance
        self.nodes_data = nodes_data
        self.resources = nodes_data
        import time
        self._last_load_time = time.time()
        self.has_loaded_data = True
        
        # Optimized graph updates - only update when data changes significantly
        if not hasattr(self, '_graphs_initialized') or self._should_update_graphs(nodes_data):
            self._update_graphs_async(nodes_data)
            self._graphs_initialized = True
        
        # Check if we're in search mode and apply search filter
        if self._is_searching and self._current_search_query:
            self._filter_nodes_by_search(self._current_search_query)
        else:
            self.show_table()
            # Populate table with optimized method
            self.populate_table(nodes_data)
            self.items_count.setText(f"{len(nodes_data)} items")
    
    def _should_update_graphs(self, new_nodes_data):
        """Determine if graphs should be updated based on data changes"""
        if not hasattr(self, '_last_nodes_hash'):
            return True
        
        # Simple hash of node count and first few node names for change detection
        try:
            new_hash = hash(str(len(new_nodes_data)) + str([n.get('name', '') for n in new_nodes_data[:3]]))
            if new_hash != self._last_nodes_hash:
                self._last_nodes_hash = new_hash
                return True
        except Exception:
            pass
        return False
    
    def _format_cpu_display(self, node):
        """Format CPU information for display"""
        try:
            cpu_capacity = node.get("cpu_capacity", "")
            cpu_usage = node.get("cpu_usage")
            
            if cpu_usage is not None and cpu_capacity:
                return f"{cpu_capacity} ({cpu_usage:.1f}%)"
            elif cpu_capacity:
                return cpu_capacity
            else:
                return "N/A"
        except Exception as e:
            logging.debug(f"Error formatting CPU display: {e}")
            return "N/A"
    
    def _format_memory_display(self, node):
        """Format memory information for display"""
        try:
            memory_capacity = node.get("memory_capacity", "")
            memory_usage = node.get("memory_usage")
            
            if memory_usage is not None and memory_capacity:
                return f"{memory_capacity} ({memory_usage:.1f}%)"
            elif memory_capacity:
                return memory_capacity
            else:
                return "N/A"
        except Exception as e:
            logging.debug(f"Error formatting memory display: {e}")
            return "N/A"
    
    def _format_disk_display(self, node):
        """Format disk information for display"""
        try:
            disk_capacity = node.get("disk_capacity", "")
            disk_usage = node.get("disk_usage")
            
            if disk_usage is not None and disk_capacity:
                return f"{disk_capacity} ({disk_usage:.1f}%)"
            elif disk_capacity:
                return disk_capacity
            else:
                return "N/A"
        except Exception as e:
            logging.debug(f"Error formatting disk display: {e}")
            return "N/A"
    
    def _format_taints_display(self, node):
        """Format taints information for display"""
        try:
            taints = node.get("taints", [])
            if isinstance(taints, list) and taints:
                return str(len(taints))
            else:
                return "0"
        except Exception as e:
            logging.debug(f"Error formatting taints display: {e}")
            return "0"
    
    def _format_conditions_display(self, node):
        """Format conditions information for display"""
        try:
            conditions = node.get("conditions", [])
            if isinstance(conditions, list) and conditions:
                # Find Ready condition status
                for condition in conditions:
                    if condition.get("type") == "Ready":
                        return condition.get("status", "Unknown")
                # If no Ready condition, show general status
                return node.get("status", "Unknown")
            else:
                return node.get("status", "Unknown")
        except Exception as e:
            logging.debug(f"Error formatting conditions display: {e}")
            return "Unknown"
    
    def _enable_graphs_lazy(self):
        """Enable graph updates with lazy loading - only when user interacts"""
        if not hasattr(self, '_graphs_enabled'):
            # Enable graphs but don't populate until selection
            self.cpu_graph.setEnabled(True)
            self.mem_graph.setEnabled(True)
            self.disk_graph.setEnabled(True)
            self._graphs_enabled = True
            logging.debug("Graphs enabled with lazy loading")
    
    def _batch_update_graphs(self, nodes_data):
        """Batch update all graphs to avoid timer cascades"""
        try:
            # Update main graphs
            self._update_graphs_async(nodes_data)
            
            # Update selected node graphs if applicable
            if hasattr(self, 'selected_row') and self.selected_row >= 0:
                self._update_selected_node_graphs()
                
        except Exception as e:
            logging.error(f"Error in batch graph update: {e}")
    
    def _update_graphs_async(self, nodes_data):
        """Update graphs asynchronously to avoid blocking UI"""
        try:
            self.cpu_graph.generate_utilization_data(nodes_data)
            self.mem_graph.generate_utilization_data(nodes_data) 
            self.disk_graph.generate_utilization_data(nodes_data)
        except Exception as e:
            logging.error(f"Error updating graphs: {e}")
    
    def _update_selected_node_graphs(self):
        """Update graphs for the currently selected node with latest data"""
        try:
            if (hasattr(self, 'selected_row') and self.selected_row >= 0 and 
                self.selected_row < self.table.rowCount()):
                
                node_name_item = self.table.item(self.selected_row, 1)
                if node_name_item:
                    node_name = node_name_item.text()
                    
                    # Find the node data
                    for node in self.nodes_data:
                        if node.get("name") == node_name:
                            # Force update graphs with new data - bypass throttling
                            for graph in [self.cpu_graph, self.mem_graph, self.disk_graph]:
                                graph._last_update_time = 0  # Reset throttling
                                graph._is_updating = False
                                graph.generate_utilization_data(self.nodes_data)
                                graph.set_selected_node(node, node_name)
                            break
        except Exception as e:
            logging.error(f"Error updating selected node graphs: {e}")
    
    def _display_resources(self, resources):
        """Override to use nodes-specific table population"""
        if not resources:
            self.show_no_data_message()
            return
        
        self.show_table()
        
        # Clear previous selections when displaying new data
        if hasattr(self, 'selected_items'):
            self.selected_items.clear()
        
        # Store current selection before repopulating
        selected_node_name = None
        if (hasattr(self, 'selected_row') and self.selected_row >= 0 and 
            self.table.item(self.selected_row, 1)):
            selected_node_name = self.table.item(self.selected_row, 1).text()
        
        # Use the nodes-specific populate_table method
        self.populate_table(resources)
        
        # Restore selection if possible
        if selected_node_name:
            for row in range(self.table.rowCount()):
                if (self.table.item(row, 1) and 
                    self.table.item(row, 1).text() == selected_node_name):
                    self.selected_row = row
                    self.table.selectRow(row)
                    # Don't call select_node_for_graphs here to avoid recursion
                    break
        
        # Update items count
        if hasattr(self, 'items_count') and self.items_count:
            self.items_count.setText(f"{len(resources)} items")
    
    def _render_resources_batch(self, resources, append=False):
        """Override base class to use our custom populate_table method"""
        if not resources:
            return
            
        if not append:
            # Use our custom populate_table method instead of the base class method
            self.populate_table(resources)
        else:
            # For append operations, still use our method but preserve existing rows
            # This is less common but we need to handle it
            existing_count = self.table.rowCount()
            new_total = existing_count + len(resources)
            self.table.setRowCount(new_total)
            
            # Populate only the new rows
            for i, resource in enumerate(resources):
                row = existing_count + i
                self.populate_resource_row_optimized(row, resource)
                
        # Update items count
        if hasattr(self, 'items_count') and self.items_count:
            total_count = len(resources) if not append else self.table.rowCount()
            self.items_count.setText(f"{total_count} items")
    
    def _perform_global_search(self, search_text):
        """Override to perform node-specific search"""
        try:
            # Mark that we're in search mode
            self._is_searching = True
            self._current_search_query = search_text
            
            # For nodes, we'll do a local search since they are cluster-scoped
            self._filter_nodes_by_search(search_text)
            
        except Exception as e:
            logging.error(f"Error performing nodes search: {e}")
            # Fall back to base class implementation
            super()._perform_global_search(search_text)
    
    def _filter_nodes_by_search(self, search_text):
        """Filter nodes based on search text"""
        try:
            if not search_text or not self.nodes_data:
                self._display_resources(self.nodes_data)
                return
            
            search_lower = search_text.lower().strip()
            filtered_nodes = []
            
            for node in self.nodes_data:
                try:
                    # Search in multiple node fields with safe string conversion
                    node_name = str(node.get("name", "")).lower()
                    node_roles = str(node.get("roles", [])).lower()
                    node_version = str(node.get("version", "")).lower()
                    node_status = str(node.get("status", "")).lower()
                    
                    # Also search in capacity and usage information
                    cpu_capacity = str(node.get("cpu_capacity", "")).lower()
                    memory_capacity = str(node.get("memory_capacity", "")).lower()
                    
                    # Convert age to searchable text
                    age = str(node.get("age", "")).lower()
                    
                    # Check if search term matches any searchable field
                    if (search_lower in node_name or 
                        search_lower in node_roles or 
                        search_lower in node_version or 
                        search_lower in node_status or
                        search_lower in cpu_capacity or
                        search_lower in memory_capacity or
                        search_lower in age):
                        filtered_nodes.append(node)
                        
                except Exception as e:
                    logging.debug(f"Error processing node during search: {e}")
                    continue
            
            logging.info(f"Node search for '{search_text}' found {len(filtered_nodes)} results out of {len(self.nodes_data)} total nodes")
            self._display_resources(filtered_nodes)
            
            # Update items count for search results
            self.items_count.setText(f"{len(filtered_nodes)} items")
            
        except Exception as e:
            logging.error(f"Error in node search filtering: {e}")
            # Fallback to showing all nodes
            self._display_resources(self.nodes_data)
    
    def _clear_search_and_reload(self):
        """Override to clear search and show all nodes"""
        self._is_searching = False
        self._current_search_query = None
        
        # Show all nodes data and update items count
        if self.nodes_data:
            self._display_resources(self.nodes_data)
            self.items_count.setText(f"{len(self.nodes_data)} items")
        else:
            # If no data available, show empty message
            self.show_no_data_message()
            self.items_count.setText("0 items")
    
    def _on_search_text_changed(self, text):
        """Override to handle search text changes for nodes"""
        # If search is cleared, show all nodes immediately
        if not text.strip():
            self._clear_search_and_reload()
            return
        
        # Use the parent class debounced search
        super()._on_search_text_changed(text)
    
    def populate_resource_row(self, row, resource):
        """Fallback method for compatibility - redirects to optimized version"""
        return self.populate_resource_row_optimized(row, resource)
    
    def _populate_resource_row(self, row, resource):
        """Base class method override - redirects to optimized version"""
        return self.populate_resource_row_optimized(row, resource)

    def clear_table(self):
        """Override base class clear_table to ensure proper widget cleanup"""
        if not self.table:
            return
            
        # Clear all cell widgets first
        for row in range(self.table.rowCount()):
            for col in range(len(self.columns)):
                widget = self.table.cellWidget(row, col)
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
        
        # Clear contents and reset row count
        self.table.clearContents()
        self.table.setRowCount(0)

    def populate_table(self, resources_to_populate):
        """Populate table with resource data - heavily optimized for performance"""
        if not self.table or not resources_to_populate: 
            return
            
        logging.info(f"NodesPage: populate_table() called with {len(resources_to_populate)} resources")
        
        # Disable all expensive operations during population
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        
        # Clear and resize table efficiently - also clear all cell widgets
        # First clear all cell widgets explicitly to prevent orphaned widgets
        old_row_count = self.table.rowCount()
        for row in range(old_row_count):
            for col in range(len(self.columns)):
                widget = self.table.cellWidget(row, col)
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
        
        # Clear table contents and reset row count
        self.table.clearContents()
        self.table.setRowCount(0)  # Reset to 0 first
        self.table.setRowCount(len(resources_to_populate))  # Then set to new count
        
        # Use larger batches for better performance
        batch_size = 50  # Increased batch size
        total_items = len(resources_to_populate)
        
        # Process all items in larger batches with minimal event processing
        for start_idx in range(0, total_items, batch_size):
            end_idx = min(start_idx + batch_size, total_items)
            
            # Populate batch without individual processing
            for i in range(start_idx, end_idx):
                self.populate_resource_row_optimized(i, resources_to_populate[i])
            
            # Process events only between larger batches
            if end_idx < total_items:
                QApplication.processEvents()
        
        # Re-enable updates and sorting
        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)
        
        # Force a proper repaint and update
        self.table.viewport().update()
        self.table.update()
        
        # Process any pending events to ensure widgets are properly displayed
        QApplication.processEvents()

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
        if disk_usage is not None and disk_usage >= 0:
            display_disk = f"Node ({disk_usage:.1f}%)"
            disk_util = disk_usage
        else:
            # Try to get disk capacity info as fallback
            disk_capacity = resource.get("disk_capacity", "")
            if disk_capacity and disk_capacity != "":
                display_disk = f"{disk_capacity} (0%)"
                disk_util = 0
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
        node_name = resource.get("name", "unknown")
        status = resource.get("status", "Unknown")
        
        # Status goes in column 9 (Conditions column)
        status_col = 9
        
        # Simple status widget
        color = AppColors.STATUS_ACTIVE if status.lower() == "ready" else AppColors.STATUS_DISCONNECTED
        status_widget = StatusLabel(status, color)
        status_widget.clicked.connect(lambda r=row: self.table.selectRow(r))
        
        # Ensure the widget is properly initialized before setting
        status_widget.show()
        self.table.setCellWidget(row, status_col, status_widget)
        # Use base class action button implementation with proper styling
        action_button = self._create_action_button(row, node_name)
        action_button.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE +
    """
    QToolButton::menu-indicator { image: none; width: 0px; }
    """)
        
        # Create action container with proper styling
        action_container = QWidget()
        action_container.setFixedSize(40, 30)  # Fixed size instead of just width
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(5, 0, 5, 0)
        action_layout.setSpacing(0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(action_button)
        
        # Ensure the container is properly initialized before setting
        action_container.show()
        
        # Action button goes in column 10 (last column)
        action_col = 10
        self.table.setCellWidget(row, action_col, action_container)
        # Ensure the table cell is properly updated
        self.table.viewport().update(self.table.visualRect(self.table.model().index(row, status_col)))
        self.table.viewport().update(self.table.visualRect(self.table.model().index(row, action_col)))
        
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
        """Select a node to show in the graphs - optimized to avoid unnecessary reloads"""
        if row < 0 or row >= len(self.nodes_data):
            return
        
        node_name = self.table.item(row, 1).text()
        
        # Check if this is the same node already selected - avoid unnecessary reload
        if (hasattr(self, 'selected_row') and self.selected_row == row and 
            hasattr(self, '_selected_node_name') and self._selected_node_name == node_name):
            logging.debug(f"Node {node_name} already selected, skipping graph reload")
            return
            
        self.selected_row = row
        self._selected_node_name = node_name
        node_data = None
        
        # Find the node data
        for node in self.nodes_data:
            if node.get("name") == node_name:
                node_data = node
                break
                
        if not node_data:
            return
            
        self.table.selectRow(row)
        
        # Optimized graph updates - only update if data has changed significantly
        if self._should_update_graphs_for_node(node_data):
            # Force update graphs with current data first - bypass throttling
            for graph in [self.cpu_graph, self.mem_graph, self.disk_graph]:
                # Temporarily reset throttling to force immediate update
                old_time = getattr(graph, '_last_update_time', 0)
                if hasattr(graph, '_last_update_time'):
                    graph._last_update_time = 0
                if hasattr(graph, '_is_updating'):
                    graph._is_updating = False
                graph.generate_utilization_data(self.nodes_data)
                if hasattr(graph, '_last_update_time'):
                    graph._last_update_time = old_time
            
            # Then set the selected node
            self.cpu_graph.set_selected_node(node_data, node_name)
            self.mem_graph.set_selected_node(node_data, node_name)
            self.disk_graph.set_selected_node(node_data, node_name)
        
        # Log for debugging
        logging.info(f"Selected node: {node_name}")
        logging.debug(f"CPU utilization data: {self.cpu_graph.utilization_data.get(node_name, 'Not found')}")
        logging.debug(f"Memory utilization data: {self.mem_graph.utilization_data.get(node_name, 'Not found')}")
        logging.debug(f"Disk utilization data: {self.disk_graph.utilization_data.get(node_name, 'Not found')}")
    
    def _should_update_graphs_for_node(self, node_data):
        """Determine if graphs should be updated for node selection"""
        # Only update if significant time has passed or node data changed
        import time
        current_time = time.time()
        last_update = getattr(self, '_last_graph_update_time', 0)
        
        # Update graphs at most every 5 seconds for performance
        if current_time - last_update > 5.0:
            self._last_graph_update_time = current_time
            return True
        return False
    
    def handle_row_click(self, row, column):
        if column != self.table.columnCount() - 1:  # Skip action column
            # Check if this is part of a double-click sequence
            if not getattr(self, '_is_double_clicking', False):
                self.table.selectRow(row)
                self.select_node_for_graphs(row)

    def handle_row_double_click(self, row, column):
        """Handle double-click to show node detail page"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Set flag to prevent single-click graph updates during double-click
            self._is_double_clicking = True
            
            # Use QTimer to reset the flag after a short delay
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(300, lambda: setattr(self, '_is_double_clicking', False))
            
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
        """Override to fetch node data from cluster connector with performance optimization"""
        logging.info(f"NodesPage: load_data() called, is_loading={self.is_loading}")
        
        if self.is_loading:
            logging.debug("NodesPage: Already loading, skipping")
            return
        
        # Check if we have cached data and it's recent (for performance)
        if hasattr(self, '_last_load_time') and hasattr(self, 'resources'):
            import time
            if self.resources and (time.time() - self._last_load_time) < 10:  # Reduced to 10 second cache
                logging.info("NodesPage: Using cached node data for performance")
                self._display_resources(self.resources)
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