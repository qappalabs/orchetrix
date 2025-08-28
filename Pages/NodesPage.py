"""
Optimized Nodes Page Implementation for Heavy Data Loads

Key Performance Features:
- Progressive table population for 1000+ nodes
- Memory-optimized widget pooling with size limits  
- Smart data caching with adaptive TTL
- Background search threading for large datasets
- Virtual scrolling with viewport optimization
- Segmentation fault protection
- Async population for medium datasets (50-1000 nodes)
- Direct population for small datasets (<50 nodes)

Removed: Unused imports, duplicate methods, loading indicators, fallback stubs
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QLabel, QToolButton, QMenu, QFrame, 
    QGraphicsDropShadowEffect, QSizePolicy, QApplication, QPushButton, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal, QThread, pyqtSignal as Signal
from PyQt6.QtGui import QColor, QPainter, QPen, QLinearGradient, QPainterPath, QBrush

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

        self.setMinimumHeight(140)
        self.setMaximumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.setStyleSheet(AppStyles.GRAPH_FRAME_STYLE)

        # Reduced shadow effect for performance
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

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
        height = 60  # Increased from 40 to 60 for better visibility
        bottom = self.height() - 25
        
        # Use cached color to avoid object creation
        if not hasattr(self, '_cached_color'):
            self._cached_color = QColor(self.color)
        
        # Simplified line drawing - no gradient for performance
        if len(self.data) > 1 and width > 0:
            # Pre-calculate min/max with proper scaling for percentages
            if not hasattr(self, '_data_range') or len(self.data) != getattr(self, '_last_data_length', 0):
                self._min_value = 0  # Always start from 0 for percentages
                self._max_value = max(100, max(self.data))  # Ensure at least 100% scale
                self._value_range = self._max_value - self._min_value
                self._data_range = True
                self._last_data_length = len(self.data)
            
            # Draw simple line without path objects for better performance
            painter.setPen(QPen(self._cached_color, 2))
            x_step = width / (len(self.data) - 1)
            
            prev_x = 16
            # Ensure first point is also properly scaled and clamped
            y_ratio = (self.data[0] - self._min_value) / self._value_range if self._value_range > 0 else 0
            prev_y = bottom - (y_ratio * height)
            prev_y = max(bottom - height, min(bottom, prev_y))  # Clamp to visible area
            
            for i in range(1, len(self.data)):
                x = 16 + i * x_step
                # Ensure y-coordinate stays within bounds and properly scales percentages
                y_ratio = (self.data[i] - self._min_value) / self._value_range if self._value_range > 0 else 0
                y = bottom - (y_ratio * height)
                y = max(bottom - height, min(bottom, y))  # Clamp to visible area
                painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))
                prev_x, prev_y = x, y
        
        # Draw scale labels and time axis if space available
        if width > 200:
            painter.setPen(QPen(QColor("#FFFFFF"), 1))
            font = painter.font()
            font.setPointSize(9)
            painter.setFont(font)
            
            # Draw Y-axis scale indicators
            if hasattr(self, '_max_value'):
                # Show max value at top
                max_text = f"{self._max_value:.0f}%" if self._max_value < 1000 else f"{self._max_value:.0f}"
                painter.drawText(QRectF(2, bottom - height - 15, 40, 12), Qt.AlignmentFlag.AlignLeft, max_text)
                
                # Show 0% at bottom
                painter.drawText(QRectF(2, bottom + 2, 40, 12), Qt.AlignmentFlag.AlignLeft, "0%")
            
            # Cache time strings to avoid repeated formatting
            if not hasattr(self, '_cached_times') or time.time() - getattr(self, '_last_time_update', 0) > 60:
                now = datetime.datetime.now()
                start_time = now - datetime.timedelta(minutes=10)
                self._cached_times = (start_time.strftime("%H:%M"), now.strftime("%H:%M"))
                self._last_time_update = time.time()
            
            painter.drawText(QRectF(16, self.height() - 16, 30, 12), Qt.AlignmentFlag.AlignCenter, self._cached_times[0])
            painter.drawText(QRectF(width - 15, self.height() - 16, 30, 12), Qt.AlignmentFlag.AlignCenter, self._cached_times[1])
        
        # Only show placeholder if no node selected and space is available
        if not self.selected_node and width > 150:
            painter.setPen(QPen(QColor(AppColors.TEXT_SUBTLE)))
            text_rect = QRectF(0, self.rect().top() + 20, self.rect().width(), 30)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "Select a node")
        
        # CRITICAL: Always end the painter to prevent segfaults
        painter.end()

    def cleanup(self):
        """Cleanup method"""
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()

# No Data Available Widget - removed, now using base class implementation

#------------------------------------------------------------------
# NodesPage - Now extending BaseResourcePage for consistency
#------------------------------------------------------------------
class AsyncTablePopulator(QThread):
    """Worker thread for asynchronous table population"""
    rows_ready = Signal(list, bool)  # (rows_data, is_complete)
    population_complete = Signal()
    
    def __init__(self, resources, batch_size=25):
        super().__init__()
        self.resources = resources
        self.batch_size = batch_size
        self._should_stop = False
        
    def stop(self):
        self._should_stop = True
        
    def run(self):
        """Process resources in batches asynchronously"""
        try:
            total_items = len(self.resources)
            
            for start_idx in range(0, total_items, self.batch_size):
                if self._should_stop:
                    return
                    
                end_idx = min(start_idx + self.batch_size, total_items)
                batch = self.resources[start_idx:end_idx]
                is_complete = end_idx >= total_items
                
                # Pre-process row data in background thread
                processed_rows = []
                for i, resource in enumerate(batch):
                    if self._should_stop:
                        return
                    row_data = self._process_resource(resource, start_idx + i)
                    processed_rows.append(row_data)
                
                # Emit batch of processed rows
                self.rows_ready.emit(processed_rows, is_complete)
                
                # Small delay to prevent overwhelming the UI thread
                if not is_complete:
                    self.msleep(10)
                    
            self.population_complete.emit()
            
        except Exception as e:
            logging.error(f"Error in async table population: {e}")
            self.population_complete.emit()
    
    def _process_resource(self, resource, row_index):
        """Pre-process resource data for faster UI updates"""
        return {
            'row': row_index,
            'node_name': resource.get("name", "unknown"),
            'resource': resource
        }


class WidgetPool:
    """Memory-optimized widget pool with size limits and smart reuse"""
    def __init__(self, max_pool_size=200):
        self._status_widgets = []
        self._action_containers = []
        self._checkbox_containers = []
        self.max_pool_size = max_pool_size
        self._creation_count = 0
        
    def get_status_widget(self, status, color):
        """Get or create a status widget with intelligent reuse"""
        # Find reusable widget - check if widget is still valid
        for widget in self._status_widgets[:]:  # Create copy to avoid modification during iteration
            try:
                if not widget.parent():
                    widget.setText(status)
                    if hasattr(widget, 'set_color'):
                        widget.set_color(color)
                    return widget
            except RuntimeError:
                # Widget has been deleted, remove from pool
                self._status_widgets.remove(widget)
        
        # Create new widget if pool not at limit
        if len(self._status_widgets) < self.max_pool_size // 3:
            from Base_Components.base_components import StatusLabel
            widget = StatusLabel(status, color)
            self._status_widgets.append(widget)
            self._creation_count += 1
            return widget
        
        # Pool at limit, force reuse oldest widget
        oldest_widget = self._status_widgets[0]
        oldest_widget.setParent(None)
        oldest_widget.setText(status)
        if hasattr(oldest_widget, 'set_color'):
            oldest_widget.set_color(color)
        return oldest_widget
        
    def get_action_container(self):
        """Get or create an action container with size management"""
        # Find reusable container - check if container is still valid
        for container in self._action_containers[:]:
            try:
                if not container.parent():
                    return container
            except RuntimeError:
                # Container has been deleted, remove from pool
                self._action_containers.remove(container)
                
        # Create new if under limit
        if len(self._action_containers) < self.max_pool_size // 3:
            container = QWidget()
            container.setFixedSize(40, 30)
            container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
            self._action_containers.append(container)
            return container
        
        # Reuse oldest
        oldest = self._action_containers[0]
        oldest.setParent(None)
        return oldest
        
    def get_checkbox_container(self):
        """Get or create a checkbox container with memory limits"""
        # Find reusable container - check if container is still valid
        for container in self._checkbox_containers[:]:
            try:
                if not container.parent():
                    return container
            except RuntimeError:
                # Container has been deleted, remove from pool
                self._checkbox_containers.remove(container)
        
        # Create new if under limit        
        if len(self._checkbox_containers) < self.max_pool_size // 3:
            container = QWidget()
            container.setStyleSheet("background-color: transparent;")
            self._checkbox_containers.append(container)
            return container
        
        # Reuse oldest
        oldest = self._checkbox_containers[0]
        oldest.setParent(None)
        return oldest
    
    def get_pool_stats(self):
        """Get widget pool statistics with validation"""
        try:
            # Count valid widgets only
            valid_status = 0
            valid_actions = 0
            valid_checkboxes = 0
            
            for widget in self._status_widgets:
                try:
                    widget.parent()  # Try to access the widget
                    valid_status += 1
                except RuntimeError:
                    pass
            
            for widget in self._action_containers:
                try:
                    widget.parent()
                    valid_actions += 1
                except RuntimeError:
                    pass
            
            for widget in self._checkbox_containers:
                try:
                    widget.parent()
                    valid_checkboxes += 1
                except RuntimeError:
                    pass
            
            return {
                'status_widgets': valid_status,
                'action_containers': valid_actions,
                'checkbox_containers': valid_checkboxes,
                'total_widgets': valid_status + valid_actions + valid_checkboxes,
                'creation_count': self._creation_count,
                'max_pool_size': self.max_pool_size
            }
        except Exception:
            # Fallback if there's any error
            return {
                'status_widgets': 0,
                'action_containers': 0,
                'checkbox_containers': 0,
                'total_widgets': 0,
                'creation_count': self._creation_count,
                'max_pool_size': self.max_pool_size
            }
    
    def optimize_pool(self):
        """Optimize pool by removing unused widgets"""
        def cleanup_pool(widget_list, max_keep=50):
            # First, remove any deleted widgets from the list
            valid_widgets = []
            for widget in widget_list:
                try:
                    # Try to access widget to check if it's still valid
                    widget.parent()
                    valid_widgets.append(widget)
                except RuntimeError:
                    # Widget has been deleted, don't add to valid list
                    pass
            
            # Replace list with valid widgets
            widget_list[:] = valid_widgets
            
            # Keep only widgets that are not parented and limit count
            orphaned = [w for w in valid_widgets if not w.parent()]
            excess = len(orphaned) - max_keep
            
            if excess > 0:
                # Remove oldest excess widgets
                for widget in orphaned[:excess]:
                    try:
                        widget.deleteLater()
                        widget_list.remove(widget)
                    except (RuntimeError, ValueError):
                        # Widget already deleted or not in list
                        pass
                
                logging.debug(f"Cleaned up {excess} excess widgets from pool")
        
        try:
            cleanup_pool(self._status_widgets)
            cleanup_pool(self._action_containers)  
            cleanup_pool(self._checkbox_containers)
        except Exception as e:
            logging.debug(f"Error in pool optimization: {e}")
        
    def cleanup(self):
        """Clean up all pooled widgets with memory optimization"""
        try:
            # Clean up in batches to avoid UI freezing
            all_widgets = (self._status_widgets + self._action_containers + 
                          self._checkbox_containers)
            
            batch_size = 50
            for i in range(0, len(all_widgets), batch_size):
                batch = all_widgets[i:i + batch_size]
                for widget in batch:
                    widget.setParent(None)
                    widget.deleteLater()
                    
                # Small delay between batches for very large pools
                if len(all_widgets) > 200 and i + batch_size < len(all_widgets):
                    QApplication.processEvents()
            
            self._status_widgets.clear()
            self._action_containers.clear()
            self._checkbox_containers.clear()
            
            logging.info(f"Widget pool cleanup completed. Cleaned {len(all_widgets)} widgets")
            
        except Exception as e:
            logging.error(f"Error in widget pool cleanup: {e}")


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
        
        # Initialize memory-optimized widget pool and async populator
        self.widget_pool = WidgetPool(max_pool_size=300)  # Larger pool for heavy loads
        self.async_populator = None
        
        # Periodic widget pool optimization for heavy loads
        self._pool_optimizer_timer = QTimer()
        self._pool_optimizer_timer.timeout.connect(self._optimize_widget_pool)
        self._pool_optimizer_timer.start(30000)  # Optimize every 30 seconds
        
        # Virtual scrolling optimizations with memory efficiency
        self._viewport_buffer = 3  # Reduced buffer for memory efficiency
        self._visible_range = (0, 0)
        
        # Verify heavy load capabilities are properly initialized
        QTimer.singleShot(1000, self._verify_heavy_load_capability)  # Check after 1 second
        self._widget_cache = {}  # Cache for created widgets
        self._rendered_widgets = set()  # Track which rows have widgets
        self._lazy_widget_creation = True  # Enable lazy widget creation
        
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
            # Stop async populator
            if hasattr(self, 'async_populator') and self.async_populator:
                self.async_populator.stop()
                self.async_populator.wait(1000)  # Wait max 1 second
                self.async_populator.deleteLater()
            
            # Stop pool optimizer timer
            if hasattr(self, '_pool_optimizer_timer'):
                self._pool_optimizer_timer.stop()
                self._pool_optimizer_timer.deleteLater()
                
            # Clean up widget pool
            if hasattr(self, 'widget_pool'):
                self.widget_pool.cleanup()
            
            # Stop NodesPage-specific timers
            if hasattr(self, '_graph_update_timer'):
                self._graph_update_timer.stop()
                self._graph_update_timer.deleteLater()
            
            # Clean up background search worker
            if hasattr(self, '_search_worker'):
                self._search_worker.quit()
                self._search_worker.wait(1000)
                self._search_worker.deleteLater()
                delattr(self, '_search_worker')
            
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
            
        self.layout().setContentsMargins(8, 8, 8, 8)
        self.layout().setSpacing(12)
        
        # Add graphs at the top with optimized spacing
        graphs_layout = QHBoxLayout()
        graphs_layout.setContentsMargins(0, 0, 0, 0)
        graphs_layout.setSpacing(8)  # Reduced spacing between graphs
        
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
        
        # Connect scroll events for optimized virtual scrolling
        if hasattr(self.table, 'verticalScrollBar'):
            self.table.verticalScrollBar().valueChanged.connect(self._handle_optimized_scroll)
        
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
        
        # Optimized column configuration for perfect matrix display
        column_config = [
            (0, 0, 0, "fixed"),        # Hidden checkbox - zero width
            (1, 120, 90, "priority"),   # Name (priority) - slightly reduced
            (2, 95, 70, "normal"),     # CPU - more compact
            (3, 95, 70, "normal"),     # Memory - more compact  
            (4, 95, 70, "normal"),     # Disk - more compact
            (5, 50, 40, "compact"),    # Taints - more compact
            (6, 100, 70, "normal"),    # Roles - reduced
            (7, 75, 55, "compact"),    # Version - more compact
            (8, 50, 40, "compact"),    # Age - more compact
            (9, 85, 65, "stretch"),    # Conditions (stretch) - optimized
            (10, 35, 35, "fixed")      # Actions - minimal but functional
        ]
        
        # Calculate total reserved space for fixed and minimum widths
        reserved_space = sum(min_width for _, _, min_width, _ in column_config)
        remaining_space = max(0, available_width - reserved_space)
        
        # Distribute remaining space based on priorities
        priority_columns = sum(1 for _, _, _, col_type in column_config if col_type == "priority")
        normal_columns = sum(1 for _, _, _, col_type in column_config if col_type == "normal")
        
        if priority_columns > 0:
            priority_extra = remaining_space * 0.35 / priority_columns  # 35% to priority columns
            normal_extra = remaining_space * 0.65 / normal_columns if normal_columns > 0 else 0
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
        """Ultra-optimized node data update with intelligent processing strategies"""
        data_size = len(nodes_data) if nodes_data else 0
        logging.info(f"NodesPage: update_nodes() called with {data_size} nodes")
        
        self.is_loading = False
        self.is_showing_skeleton = False
        
        # Clean up any loading artifacts
        self._cleanup_loading_artifacts()
        
        if not nodes_data:
            self._handle_empty_data()
            return
        
        # Store data and optimize memory usage
        self._store_and_cache_data(nodes_data)
        
        # Smart processing strategy based on data size
        if data_size > 1000:
            logging.info(f"NodesPage: Processing VERY LARGE dataset ({data_size} nodes) with maximum optimization")
            self._process_large_dataset(nodes_data)
        elif data_size > 500:
            logging.info(f"NodesPage: Processing LARGE dataset ({data_size} nodes) with heavy optimization")
            self._process_medium_dataset(nodes_data) 
        elif data_size > 100:
            logging.info(f"NodesPage: Processing MEDIUM dataset ({data_size} nodes) with standard optimization")
            self._process_small_dataset(nodes_data)
        else:
            logging.info(f"NodesPage: Processing SMALL dataset ({data_size} nodes) with direct rendering")
            self._process_tiny_dataset(nodes_data)
    
    def _cleanup_loading_artifacts(self):
        """Clean up loading timers and artifacts"""
        if hasattr(self, 'skeleton_timer'):
            if self.skeleton_timer.isActive():
                self.skeleton_timer.stop()
            self.skeleton_timer.deleteLater()
            delattr(self, 'skeleton_timer')
    
    def _handle_empty_data(self):
        """Handle case when no node data is received"""
        logging.warning("NodesPage: No nodes data received")
        self.nodes_data = []
        self.resources = []
        if not getattr(self, '_is_searching', False):
            self._is_searching = False
            self._current_search_query = None
        self.show_no_data_message()
        self.items_count.setText("0 items")
    
    def _store_and_cache_data(self, nodes_data):
        """Efficiently store and cache node data"""
        # Use memory-optimized storage
        self.nodes_data = nodes_data
        self.resources = nodes_data
        
        import time
        self._last_load_time = time.time()
        self.has_loaded_data = True
        
        # Set total available items for virtual scrolling
        self._total_available_items = len(nodes_data)
        
        # Initialize virtual scrolling if needed
        self._ensure_virtual_scrolling_state()
    
    def _ensure_virtual_scrolling_state(self):
        """Ensure virtual scrolling state is properly initialized"""
        if not hasattr(self, '_virtual_scrolling_enabled'):
            self._virtual_scrolling_enabled = True
            self._rendered_items_count = 0
            # Adaptive thresholds based on system performance
            self.virtual_scroll_threshold = 50
            self.items_per_page = 50
            self.virtual_load_size = 100
    
    def _process_large_dataset(self, nodes_data):
        """Process datasets > 1000 nodes with maximum optimization"""
        data_size = len(nodes_data)
        logging.info(f"Processing large dataset: {data_size} nodes")
        
        # Update graphs with reduced frequency for performance
        if self._should_update_graphs_throttled(nodes_data):
            self._update_graphs_async_throttled(nodes_data)
        
        # Handle search mode
        if self._is_searching and self._current_search_query:
            self._filter_nodes_by_search_optimized(self._current_search_query)
        else:
            self.show_table()
            # Always use progressive rendering for large datasets
            self._display_nodes_progressive_large(nodes_data)
    
    def _process_medium_dataset(self, nodes_data):
        """Process datasets 500-1000 nodes with balanced optimization"""
        data_size = len(nodes_data)
        logging.info(f"Processing medium dataset: {data_size} nodes")
        
        # Update graphs with normal frequency
        if self._should_update_graphs(nodes_data):
            self._update_graphs_async(nodes_data)
        
        # Handle search mode
        if self._is_searching and self._current_search_query:
            self._filter_nodes_by_search(self._current_search_query)
        else:
            self.show_table()
            # Use progressive rendering for medium datasets
            self._display_nodes_progressive(nodes_data)
    
    def _process_small_dataset(self, nodes_data):
        """Process datasets 100-500 nodes with standard optimization"""
        data_size = len(nodes_data)
        logging.info(f"Processing small dataset: {data_size} nodes")
        
        # Update graphs normally
        if self._should_update_graphs(nodes_data):
            self._update_graphs_async(nodes_data)
        
        # Handle search mode
        if self._is_searching and self._current_search_query:
            self._filter_nodes_by_search(self._current_search_query)
        else:
            self.show_table()
            # Use virtual scrolling
            self._display_nodes_virtual(nodes_data)
    
    def _process_tiny_dataset(self, nodes_data):
        """Process datasets < 100 nodes with minimal optimization"""
        data_size = len(nodes_data)
        logging.info(f"Processing tiny dataset: {data_size} nodes")
        
        # Update graphs normally
        if self._should_update_graphs(nodes_data):
            self._update_graphs_async(nodes_data)
        
        # Handle search mode
        if self._is_searching and self._current_search_query:
            self._filter_nodes_by_search(self._current_search_query)
        else:
            self.show_table()
            # Use direct population for small datasets
            self.populate_table(nodes_data)
            self._rendered_items_count = len(nodes_data)
            self.all_data_loaded = True
            self.items_count.setText(f"{len(nodes_data)} items")
    
    def _display_nodes_progressive_large(self, nodes_data):
        """Display nodes with maximum optimization for very large datasets"""
        data_size = len(nodes_data)
        logging.info(f"Progressive large display for {data_size} nodes")
        
        # Use the most optimized progressive rendering
        self._populate_table_progressive(nodes_data)
        
        # Update state
        self._rendered_items_count = data_size
        self.all_data_loaded = True
        
        # Use deferred counter update to avoid blocking
        QTimer.singleShot(100, lambda: self.items_count.setText(f"{data_size} items"))
    
    def _should_update_graphs_throttled(self, nodes_data):
        """Throttled graph update decision for large datasets"""
        if not hasattr(self, '_last_graph_update_time'):
            self._last_graph_update_time = 0
        
        import time
        current_time = time.time()
        
        # Update graphs less frequently for large datasets (every 10 seconds)
        return (current_time - self._last_graph_update_time) > 10
    
    def _update_graphs_async_throttled(self, nodes_data):
        """Throttled graph update for performance with large datasets"""
        try:
            import time
            self._last_graph_update_time = time.time()
            
            # Update graphs with reduced precision for performance
            self.cpu_graph.generate_utilization_data(nodes_data[:500])  # Sample first 500
            self.mem_graph.generate_utilization_data(nodes_data[:500])
            self.disk_graph.generate_utilization_data(nodes_data[:500])
            
        except Exception as e:
            logging.error(f"Error in throttled graph update: {e}")
    
    def _filter_nodes_by_search_optimized(self, search_query):
        """Optimized search filtering for large datasets"""
        if not search_query or not self.nodes_data:
            self._display_resources(self.nodes_data)
            return
        
        # Use background thread for large dataset searches
        if len(self.nodes_data) > 500:
            self._perform_background_search(search_query)
        else:
            self._filter_nodes_by_search(search_query)
    
    def _perform_background_search(self, search_query):
        """Perform search in background thread for large datasets"""
        from PyQt6.QtCore import QThread, pyqtSignal
        
        class BackgroundSearchWorker(QThread):
            search_complete = pyqtSignal(list)
            
            def __init__(self, nodes_data, search_query):
                super().__init__()
                self.nodes_data = nodes_data
                self.search_query = search_query.lower().strip()
                
            def run(self):
                try:
                    filtered_nodes = []
                    for node in self.nodes_data:
                        try:
                            # Optimized search fields
                            node_name = str(node.get("name", "")).lower()
                            if self.search_query in node_name:
                                filtered_nodes.append(node)
                                continue
                                
                            # Additional fields for comprehensive search
                            node_roles = str(node.get("roles", [])).lower()
                            node_version = str(node.get("version", "")).lower()
                            node_status = str(node.get("status", "")).lower()
                            
                            if (self.search_query in node_roles or 
                                self.search_query in node_version or 
                                self.search_query in node_status):
                                filtered_nodes.append(node)
                                
                        except Exception:
                            continue
                    
                    self.search_complete.emit(filtered_nodes)
                    
                except Exception as e:
                    logging.error(f"Background search error: {e}")
                    self.search_complete.emit([])
        
        # Show search indicator
        self.items_count.setText("🔍 Searching...")
        
        # Start background search
        self._search_worker = BackgroundSearchWorker(self.nodes_data, search_query)
        self._search_worker.search_complete.connect(self._handle_background_search_complete)
        self._search_worker.start()
    
    def _handle_background_search_complete(self, filtered_nodes):
        """Handle completion of background search"""
        try:
            logging.info(f"Background search completed: {len(filtered_nodes)} results")
            self._display_resources(filtered_nodes)
            self.items_count.setText(f"{len(filtered_nodes)} items")
            
            # Clean up search worker
            if hasattr(self, '_search_worker'):
                self._search_worker.deleteLater()
                delattr(self, '_search_worker')
                
        except Exception as e:
            logging.error(f"Error handling background search completion: {e}")
    
    def _optimize_widget_pool(self):
        """Periodic widget pool optimization for memory management"""
        try:
            if hasattr(self, 'widget_pool'):
                stats_before = self.widget_pool.get_pool_stats()
                self.widget_pool.optimize_pool()
                stats_after = self.widget_pool.get_pool_stats()
                
                # Log optimization if significant cleanup occurred
                if stats_before['total_widgets'] - stats_after['total_widgets'] > 10:
                    logging.debug(f"Widget pool optimized: {stats_before['total_widgets']} -> {stats_after['total_widgets']} widgets")
                
        except Exception as e:
            logging.debug(f"Error optimizing widget pool: {e}")  # Changed to debug to reduce noise
    
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
    
    def _display_nodes_virtual(self, nodes_data):
        """Memory-efficient virtual display with lazy loading"""
        if not nodes_data:
            self.show_no_data_message()
            return
        
        # Clear previous selections and widget tracking
        if hasattr(self, 'selected_items'):
            self.selected_items.clear()
        self._rendered_widgets.clear()
        
        # Create table structure without widgets initially
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(nodes_data))  # Full row count for scrolling
        
        # Populate text items only (no widgets yet)
        for row, resource in enumerate(nodes_data):
            self._populate_text_items_only(row, resource)
            
        # Create widgets only for initially visible rows
        visible_range = self._get_visible_row_range()
        if visible_range:
            start_row, end_row = visible_range
            for row in range(start_row, min(end_row + 1, len(nodes_data))):
                self._create_row_widgets_lazy(row)
                
        self.table.setSortingEnabled(True)
        self._rendered_items_count = len(nodes_data)
        self.all_data_loaded = True
        
        logging.info(f"NodesPage: Memory-efficient virtual display for {len(nodes_data)} nodes")
        self._update_nodes_items_count()
        
    def _populate_text_items_only(self, row, resource):
        """Populate only text items without expensive widgets"""
        self.table.setRowHeight(row, 40)
        
        # Pre-calculate display values
        display_values = self._calculate_display_values_fast(resource)
        
        # Create table items efficiently (text only)
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
    
    def _populate_nodes_batch(self, nodes_batch, append=False):
        """Populate a batch of nodes efficiently for virtual scrolling"""
        if not append:
            self.clear_table()
        
        if not nodes_batch:
            return
        
        # Get starting row
        start_row = self.table.rowCount() if append else 0
        
        # Remove loading indicator if appending
        if append and hasattr(self, '_load_more_indicator_row'):
            self.table.setRowCount(self._load_more_indicator_row)
            delattr(self, '_load_more_indicator_row')
            start_row = self.table.rowCount()
        
        # Set new row count
        total_rows = start_row + len(nodes_batch)
        self.table.setRowCount(total_rows)
        
        # Disable expensive operations (keep updates enabled to prevent loading indicators)
        self.table.setSortingEnabled(False)
        # self.table.setUpdatesEnabled(False)  # Skip this to prevent loading indicators
        
        try:
            # Populate rows efficiently
            for i, node in enumerate(nodes_batch):
                row = start_row + i
                self.populate_resource_row_optimized(row, node)
        finally:
            # Re-enable operations
            # self.table.setUpdatesEnabled(True)  # Was never disabled
            self.table.setSortingEnabled(True)
    
    def _add_nodes_load_more_indicator(self):
        """Add a load more indicator specific to nodes page"""
        try:
            if not self.table:
                return
            
            current_row_count = self.table.rowCount()
            self.table.setRowCount(current_row_count + 1)
            
            # Create load more indicator
            from PyQt6.QtWidgets import QLabel
            from PyQt6.QtCore import Qt
            
            remaining_nodes = self._total_available_items - self._rendered_items_count
            load_more_label = QLabel(f"🖥️ Scroll down to load {min(remaining_nodes, self.virtual_load_size)} more nodes...")
            load_more_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            load_more_label.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-style: italic;
                    padding: 15px;
                    background-color: #2a2a2a;
                    border-top: 1px solid #444444;
                    font-size: 13px;
                }
            """)
            
            # Set the indicator to span all columns
            self.table.setCellWidget(current_row_count, 0, load_more_label)
            if self.table.columnCount() > 1:
                self.table.setSpan(current_row_count, 0, 1, self.table.columnCount())
            
            # Set row height
            self.table.setRowHeight(current_row_count, 60)
            
            # Store reference to remove it later
            self._load_more_indicator_row = current_row_count
            
        except Exception as e:
            logging.debug(f"Error adding nodes load more indicator: {e}")
    
    def _update_nodes_items_count(self):
        """Update items count for nodes with virtual scrolling info"""
        if hasattr(self, 'items_count') and self.items_count:
            if (hasattr(self, '_virtual_scrolling_enabled') and 
                self._virtual_scrolling_enabled and 
                hasattr(self, '_total_available_items') and
                self._total_available_items > self._rendered_items_count):
                # Show virtual scrolling progress
                self.items_count.setText(f"Showing {self._rendered_items_count} of {self._total_available_items} nodes")
            else:
                # Show normal count
                count = len(getattr(self, 'nodes_data', []))
                self.items_count.setText(f"{count} items")
    
    def _handle_optimized_scroll(self, value):
        """Handle scroll events with viewport optimization"""
        # Update visible range for viewport optimization
        visible_range = self._get_visible_row_range()
        if visible_range != self._visible_range:
            self._visible_range = visible_range
            self._optimize_viewport_rendering()
            
        # Handle virtual scrolling
        if hasattr(self, '_virtual_scrolling_enabled') and self._virtual_scrolling_enabled:
            if (self.table and not getattr(self, 'is_loading_more', False) and 
                not getattr(self, 'all_data_loaded', True)):
                
                scrollbar = self.table.verticalScrollBar()
                if scrollbar.value() >= scrollbar.maximum() - 20:  # Near bottom
                    self._load_more_nodes()
                    
    def _get_visible_row_range(self):
        """Get range of visible rows in viewport"""
        if not self.table or self.table.rowCount() == 0:
            return None
            
        try:
            viewport_rect = self.table.viewport().rect()
            top_row = self.table.rowAt(viewport_rect.top())
            bottom_row = self.table.rowAt(viewport_rect.bottom())
            
            # Handle edge cases
            if top_row == -1:
                top_row = 0
            if bottom_row == -1:
                bottom_row = self.table.rowCount() - 1
                
            # Add buffer for smoother scrolling
            buffer = self._viewport_buffer
            start_row = max(0, top_row - buffer)
            end_row = min(self.table.rowCount() - 1, bottom_row + buffer)
            
            return (start_row, end_row)
        except Exception as e:
            logging.debug(f"Error getting visible row range: {e}")
            return None
            
    def _optimize_viewport_rendering(self):
        """Memory-efficient viewport optimization with lazy widget creation"""
        if not self._visible_range:
            return
            
        start_row, end_row = self._visible_range
        
        # Create widgets only for visible rows
        for row in range(self.table.rowCount()):
            if start_row <= row <= end_row:
                # Ensure widgets exist for visible rows
                if row not in self._rendered_widgets:
                    self._create_row_widgets_lazy(row)
                    
                # Show existing widgets
                for col in [0, 9, 10]:  # checkbox, status, action columns
                    widget = self.table.cellWidget(row, col)
                    if widget and not widget.isVisible():
                        widget.show()
            else:
                # Hide widgets outside visible range and potentially remove them
                for col in [0, 9, 10]:
                    widget = self.table.cellWidget(row, col)
                    if widget:
                        if widget.isVisible():
                            widget.hide()
                        # Remove widgets that are far from viewport for memory efficiency
                        if row < start_row - 20 or row > end_row + 20:
                            self._remove_row_widgets(row)
                            
    def _create_row_widgets_lazy(self, row):
        """Lazily create widgets for a specific row"""
        if row in self._rendered_widgets or row >= self.table.rowCount():
            return
            
        try:
            # Find the corresponding resource data
            resource_data = None
            if hasattr(self, 'nodes_data') and row < len(self.nodes_data):
                resource_data = self.nodes_data[row]
            elif hasattr(self, 'resources') and row < len(self.resources):
                resource_data = self.resources[row]
                
            if resource_data:
                node_name = resource_data.get("name", "unknown")
                
                # Create widgets using pool
                checkbox_container = self.widget_pool.get_checkbox_container()
                checkbox_container.setParent(None)
                self.table.setCellWidget(row, 0, checkbox_container)
                
                # Create status and action widgets
                self._create_status_and_action_widgets_pooled(row, resource_data, node_name)
                
                self._rendered_widgets.add(row)
                
        except Exception as e:
            logging.debug(f"Error creating lazy widgets for row {row}: {e}")
            
    def _remove_row_widgets(self, row):
        """Remove widgets for a row to save memory"""
        if row not in self._rendered_widgets:
            return
            
        try:
            # Return widgets to pool and remove from table
            for col in [0, 9, 10]:
                widget = self.table.cellWidget(row, col)
                if widget:
                    widget.setParent(None)  # Return to pool
                    self.table.setCellWidget(row, col, None)
                    
            self._rendered_widgets.discard(row)
            
        except Exception as e:
            logging.debug(f"Error removing widgets for row {row}: {e}")
                        
    def _update_viewport_region(self, visible_range):
        """Update only the visible viewport region"""
        if not visible_range:
            return
            
        start_row, end_row = visible_range
        
        # Update only visible region
        for row in range(start_row, end_row + 1):
            for col in range(self.table.columnCount()):
                index = self.table.model().index(row, col)
                rect = self.table.visualRect(index)
                if rect.isValid():
                    self.table.viewport().update(rect)

    def _handle_node_scroll(self, value):
        """Legacy method - redirects to optimized version"""
        self._handle_optimized_scroll(value)
    
    def _load_more_nodes(self):
        """Load more nodes for virtual scrolling"""
        if (getattr(self, 'is_loading_more', False) or 
            getattr(self, 'all_data_loaded', True) or 
            not hasattr(self, 'nodes_data')):
            return
        
        try:
            # Check if we have more nodes to render
            if self._rendered_items_count < len(self.nodes_data):
                self.is_loading_more = True
                
                # Calculate next batch
                start_idx = self._rendered_items_count
                end_idx = min(start_idx + self.virtual_load_size, len(self.nodes_data))
                next_batch = self.nodes_data[start_idx:end_idx]
                
                logging.info(f"NodesPage: Loading more nodes {start_idx}-{end_idx-1} of {len(self.nodes_data)}")
                
                # Render next batch
                if next_batch:
                    self._populate_nodes_batch(next_batch, append=True)
                
                # Update state
                self._rendered_items_count = end_idx
                if self._rendered_items_count >= len(self.nodes_data):
                    self.all_data_loaded = True
                    logging.info(f"NodesPage: All {len(self.nodes_data)} nodes rendered")
                else:
                    # Add indicator for remaining nodes
                    self._add_nodes_load_more_indicator()
                
                # Update items count
                self._update_nodes_items_count()
                
                self.is_loading_more = False
            else:
                # No more nodes to render
                self.all_data_loaded = True
                
        except Exception as e:
            logging.error(f"Error loading more nodes: {e}")
            self.is_loading_more = False
            self.all_data_loaded = True
    
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
        """Override base class clear_table with memory-efficient cleanup"""
        if not self.table:
            return
            
        # Return widgets to pool instead of deleting
        for row in range(self.table.rowCount()):
            for col in [0, 9, 10]:  # Only widget columns
                widget = self.table.cellWidget(row, col)
                if widget:
                    widget.setParent(None)  # Return to pool
        
        # Clear tracking sets
        self._rendered_widgets.clear()
        self._widget_cache.clear()
        
        # Clear contents and reset row count
        self.table.clearContents()
        self.table.setRowCount(0)

    def populate_table(self, resources_to_populate):
        """Ultra-optimized table population with segfault protection"""
        if not self.table or not resources_to_populate: 
            return
        
        # Additional safety checks to prevent segfaults
        try:
            # Check if table is still valid
            self.table.rowCount()  # This will raise an exception if table is deleted
        except RuntimeError:
            logging.error("Table widget has been deleted, cannot populate")
            return
            
        total_items = len(resources_to_populate)
        logging.info(f"NodesPage: populate_table() called with {total_items} resources")
        
        # Prevent concurrent population attempts
        if hasattr(self, '_populating_table') and self._populating_table:
            logging.debug("Table population already in progress, skipping")
            return
        
        self._populating_table = True
        
        try:
            # For heavy loads, use progressive population strategy
            if total_items > 100:
                logging.info(f"NodesPage: Using PROGRESSIVE table population for {total_items} nodes (heavy load)")
                self._populate_table_progressive(resources_to_populate)
            elif total_items > 50:
                logging.info(f"NodesPage: Using ASYNC table population for {total_items} nodes (medium load)")
                self._populate_table_async(resources_to_populate)
            else:
                logging.info(f"NodesPage: Using SYNC table population for {total_items} nodes (light load)")
                self._populate_table_sync(resources_to_populate)
        finally:
            self._populating_table = False
    
    def _populate_table_progressive(self, resources_to_populate):
        """Progressive population for very heavy loads (1000+ nodes)"""
        total_items = len(resources_to_populate)
        
        # Disable all expensive operations
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        
        # Optimized clearing
        self._ultra_fast_clear_table()
        
        # Set final row count
        self.table.setRowCount(total_items)
        
        # Progressive rendering in optimized chunks
        chunk_size = min(200, max(50, total_items // 10))  # Adaptive chunk size
        
        def render_chunk(start_idx):
            try:
                end_idx = min(start_idx + chunk_size, total_items)
                
                # Render chunk efficiently
                for i in range(start_idx, end_idx):
                    if i >= total_items:
                        break
                    self._populate_row_ultra_fast(i, resources_to_populate[i])
                
                # Schedule next chunk or finish
                if end_idx < total_items:
                    # Schedule next chunk with minimal delay
                    QTimer.singleShot(1, lambda: render_chunk(end_idx))
                else:
                    # Final setup
                    self._finalize_progressive_rendering()
                    
            except Exception as e:
                logging.error(f"Error in progressive rendering: {e}")
                self._finalize_progressive_rendering()
        
        # Start progressive rendering
        render_chunk(0)
    
    def _populate_table_sync(self, resources_to_populate):
        """Optimized synchronous population for small datasets"""
        self.table.setSortingEnabled(False)
        self._ultra_fast_clear_table()
        self.table.setRowCount(len(resources_to_populate))
        
        for i, resource in enumerate(resources_to_populate):
            self._populate_row_ultra_fast(i, resource)
        
        self.table.setSortingEnabled(True)
        self.table.viewport().update()
    
    def _ultra_fast_clear_table(self):
        """Ultra-fast table clearing with segfault protection"""
        try:
            # Verify table is still valid
            old_count = self.table.rowCount()
        except RuntimeError:
            logging.debug("Table widget deleted during clear operation")
            return
        
        if old_count > 0:
            try:
                # Return widgets to pool instead of deleting - with safety checks
                for row in range(min(old_count, 100)):  # Only process first 100 for speed
                    for col in [0, 9, 10]:  # Only widget columns
                        try:
                            widget = self.table.cellWidget(row, col)
                            if widget:
                                widget.setParent(None)  # Return to pool
                        except RuntimeError:
                            # Widget or table was deleted, skip
                            continue
                
                # Clear everything at once with error handling
                self.table.clearContents()
                self.table.setRowCount(0)
                
            except RuntimeError:
                logging.debug("Table widget deleted during clear operation")
                return
    
    def _populate_row_ultra_fast(self, row, resource):
        """Ultra-fast row population with segfault protection"""
        try:
            # Verify table is still valid and has enough rows
            if row >= self.table.rowCount():
                logging.debug(f"Row {row} exceeds table size, skipping")
                return
                
            self.table.setRowHeight(row, 40)
            
            # Pre-calculate display values once
            display_values = self._calculate_display_values_fast(resource)
            
            # Create text items in batch with error handling
            for col, (value, sort_value) in enumerate(display_values):
                try:
                    cell_col = col + 1
                    item = SortableTableWidgetItem(value, sort_value) if sort_value is not None else SortableTableWidgetItem(value)
                    
                    # Optimized alignment setting
                    if col in {1, 2, 3, 4, 5, 6, 7}:  # Use set for faster lookup
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    else:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, cell_col, item)
                except RuntimeError:
                    # Table was deleted, abort population
                    return
            
            # Create widgets only when needed (lazy) - with error handling
            self._create_minimal_row_widgets(row, resource)
            
        except RuntimeError:
            logging.debug("Table widget deleted during row population")
            return
    
    def _create_minimal_row_widgets(self, row, resource):
        """Create only essential widgets with pooling and segfault protection"""
        try:
            # Verify table is still valid
            if row >= self.table.rowCount():
                return
                
            # Checkbox container (minimal)
            checkbox_container = QWidget()
            checkbox_container.setStyleSheet("background-color: transparent;")
            self.table.setCellWidget(row, 0, checkbox_container)
            
            # Status widget (pooled) - with error handling
            status = resource.get("status", "Unknown")
            color = AppColors.STATUS_ACTIVE if status.lower() == "ready" else AppColors.STATUS_DISCONNECTED
            
            try:
                # Use widget pool for status
                status_widget = self.widget_pool.get_status_widget(status, color)
                if status_widget:  # Check if widget is valid
                    status_widget.setParent(None)
                    self.table.setCellWidget(row, 9, status_widget)
            except (RuntimeError, AttributeError):
                # Widget pool failed, skip status widget
                logging.debug("Failed to create status widget, skipping")
            
            # Action container (pooled) - with error handling
            try:
                action_container = self.widget_pool.get_action_container()
                if action_container:  # Check if container is valid
                    action_container.setParent(None)
                    
                    # Create action button using the original method
                    action_button = self._create_action_button(row, resource.get("name", ""))
                    if action_button:  # Check if button was created successfully
                        layout = action_container.layout()
                        if not layout:
                            layout = QHBoxLayout(action_container)
                            layout.setContentsMargins(5, 0, 5, 0)
                            layout.setSpacing(0)
                            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        else:
                            # Clear existing layout safely
                            while layout.count():
                                child = layout.takeAt(0)
                                if child.widget():
                                    child.widget().setParent(None)
                        
                        layout.addWidget(action_button)
                        self.table.setCellWidget(row, 10, action_container)
            except (RuntimeError, AttributeError):
                # Widget pool failed, skip action container
                logging.debug("Failed to create action container, skipping")
            
            # Store raw data efficiently
            if "raw_data" not in resource:
                resource["raw_data"] = {
                    "metadata": {"name": resource.get("name", "")},
                    "status": {"conditions": [{"type": status, "status": "True"}]}
                }
                
        except RuntimeError:
            logging.debug("Table widget deleted during widget creation")
            return
    
    
    def _finalize_progressive_rendering(self):
        """Finalize progressive rendering setup with segfault protection"""
        try:
            # Verify table is still valid before finalizing
            if not self.table:
                return
                
            row_count = self.table.rowCount()  # This will raise RuntimeError if table is deleted
            
            self.table.setUpdatesEnabled(True)
            self.table.setSortingEnabled(True)
            self.table.viewport().update()
            logging.info(f"Progressive rendering completed for {row_count} nodes")
            
        except RuntimeError:
            logging.debug("Table widget deleted during finalization")
            return
        except Exception as e:
            logging.error(f"Error finalizing progressive rendering: {e}")
    

    def _populate_table_async(self, resources_to_populate):
        """Populate table asynchronously to prevent UI freezing"""
        # Stop any existing async populator
        if self.async_populator:
            self.async_populator.stop()
            self.async_populator.wait(1000)
            self.async_populator.deleteLater()
            
        # Create and start async populator
        batch_size = min(25, max(10, len(resources_to_populate) // 10))
        self.async_populator = AsyncTablePopulator(resources_to_populate, batch_size)
        self.async_populator.rows_ready.connect(self._handle_async_rows)
        self.async_populator.population_complete.connect(self._handle_population_complete)
        self.async_populator.start()
        
    def _handle_async_rows(self, processed_rows, is_complete):
        """Handle rows processed asynchronously"""
        try:
            for row_data in processed_rows:
                row = row_data['row']
                if row < self.table.rowCount():
                    self._populate_row_from_processed_data(row_data)
                    
            # Update viewport only for visible rows
            if self.table.isVisible():
                visible_rows = self._get_visible_row_range()
                if visible_rows:
                    self._update_viewport_region(visible_rows)
                    
        except Exception as e:
            logging.error(f"Error handling async rows: {e}")
            
    def _handle_population_complete(self):
        """Handle completion of async population"""
        try:
            # Re-enable sorting
            self.table.setSortingEnabled(True)
            
            # Final viewport update
            self.table.viewport().update()
            
            logging.info(f"Async table population completed for {self.table.rowCount()} rows")
        except Exception as e:
            logging.error(f"Error in population complete handler: {e}")
            
    def _populate_row_from_processed_data(self, row_data):
        """Populate a single row using pre-processed data"""
        row = row_data['row']
        node_name = row_data['node_name']
        resource = row_data['resource']
        display_values = row_data['display_values']
        
        self.table.setRowHeight(row, 40)
        
        # Create widgets using pool
        checkbox_container = self.widget_pool.get_checkbox_container()
        checkbox_container.setParent(None)  # Clear previous parent
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Create table items efficiently
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
        
        # Create status and action widgets using pool
        self._create_status_and_action_widgets_pooled(row, resource, node_name)

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
    
    def _create_status_and_action_widgets_pooled(self, row, resource, node_name):
        """Create status and action widgets using widget pool"""
        status = resource.get("status", "Unknown")
        
        # Status goes in column 9 (Conditions column)
        status_col = 9
        
        # Get status widget from pool
        color = AppColors.STATUS_ACTIVE if status.lower() == "ready" else AppColors.STATUS_DISCONNECTED
        status_widget = self.widget_pool.get_status_widget(status, color)
        status_widget.clicked.connect(lambda r=row: self.table.selectRow(r))
        status_widget.setParent(None)  # Clear previous parent
        self.table.setCellWidget(row, status_col, status_widget)
        
        # Get action container from pool
        action_container = self.widget_pool.get_action_container()
        action_container.setParent(None)  # Clear previous parent
        
        # Create action button
        action_button = self._create_action_button(row, node_name)
        action_button.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE +
    """
    QToolButton::menu-indicator { image: none; width: 0px; }
    """)
        
        # Set up container layout
        if action_container.layout():
            # Clear existing layout
            layout = action_container.layout()
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().setParent(None)
        else:
            # Create new layout
            layout = QHBoxLayout(action_container)
            layout.setContentsMargins(5, 0, 5, 0)
            layout.setSpacing(0)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
        layout.addWidget(action_button)
        
        # Action button goes in column 10 (last column)
        action_col = 10
        self.table.setCellWidget(row, action_col, action_container)
        
        # Store raw data for potential use
        if "raw_data" not in resource:
            resource["raw_data"] = {
                "metadata": {"name": node_name},
                "status": {"conditions": [{"type": status, "status": "True"}]}
            }
    
    def _create_status_and_action_widgets_fast(self, row, resource, column_offset):
        """Redirect to pooled version"""
        node_name = resource.get("name", "unknown")
        return self._create_status_and_action_widgets_pooled(row, resource, node_name)
    
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
        """Ultra-optimized data loading with intelligent caching and lazy strategies"""
        logging.info(f"NodesPage: load_data() called, is_loading={self.is_loading}")
        
        if self.is_loading:
            logging.debug("NodesPage: Already loading, skipping")
            return
        
        # Intelligent caching strategy
        if self._should_use_cached_data():
            logging.info(f"NodesPage: Using cached node data ({len(self.resources)} nodes)")
            self._display_cached_data()
            return
        
        # Smart loading strategy based on data size
        expected_size = self._estimate_data_size()
        logging.info(f"NodesPage: Expected data size: {expected_size} nodes")
        
        if expected_size > 500:
            logging.info("NodesPage: Detected HEAVY load scenario (500+ nodes) - using progressive rendering")
            self._load_data_heavy()
        elif expected_size > 100:
            logging.info("NodesPage: Detected MEDIUM load scenario (100-500 nodes) - using async rendering")
            self._load_data_medium()
        else:
            logging.info("NodesPage: Detected LIGHT load scenario (<100 nodes) - using direct rendering")
            self._load_data_light()
    
    def _should_use_cached_data(self):
        """Intelligent cache decision based on data freshness and load"""
        if not hasattr(self, '_last_load_time') or not hasattr(self, 'resources'):
            return False
        
        import time
        current_time = time.time()
        time_since_load = current_time - self._last_load_time
        
        # Dynamic cache time based on current load and data size
        if len(getattr(self, 'resources', [])) > 1000:
            cache_time = 120  # 2 minutes for very large datasets
        elif len(getattr(self, 'resources', [])) > 500:
            cache_time = 60   # 1 minute for large datasets  
        elif len(getattr(self, 'resources', [])) > 100:
            cache_time = 30   # 30 seconds for medium datasets
        else:
            cache_time = 15   # 15 seconds for small datasets
        
        return self.resources and time_since_load < cache_time
    
    def _display_cached_data(self):
        """Efficiently display cached data with minimal overhead"""
        try:
            # Use lazy rendering for cached data too
            total_items = len(self.resources)
            if total_items > 200:
                # For large cached datasets, still use progressive rendering
                self._display_resources_progressive(self.resources)
            else:
                # Direct display for smaller cached datasets
                self._display_resources(self.resources)
            
            # Update UI indicators
            self.items_count.setText(f"{total_items} items (cached)")
            
        except Exception as e:
            logging.error(f"Error displaying cached data: {e}")
            self._force_fresh_load()
    
    def _estimate_data_size(self):
        """Estimate expected data size based on cluster characteristics"""
        try:
            # Check if we have previous data to estimate from
            if hasattr(self, 'resources') and self.resources:
                estimated_size = len(self.resources)
                logging.debug(f"NodesPage: Data size estimate based on previous load: {estimated_size}")
                return estimated_size
            
            # Try to get a quick count estimate from cluster connector
            if hasattr(self, 'cluster_connector') and self.cluster_connector:
                # Enhanced estimation based on cluster size
                if hasattr(self.cluster_connector, 'get_estimated_node_count'):
                    estimated = self.cluster_connector.get_estimated_node_count()
                    logging.debug(f"NodesPage: Cluster connector estimates {estimated} nodes")
                    return estimated
                else:
                    # Default estimate for production clusters
                    estimated = 200  # Higher default for production scenarios
                    logging.debug(f"NodesPage: Using default production estimate: {estimated}")
                    return estimated
            
            # Conservative estimate for unknown scenarios
            logging.debug("NodesPage: Using conservative fallback estimate: 50")
            return 50
            
        except Exception as e:
            logging.debug(f"NodesPage: Error in data size estimation: {e}")
            return 50
    
    def _load_data_heavy(self):
        """Optimized loading for heavy datasets (500+ nodes)"""
        logging.info("NodesPage: Using heavy data loading strategy")
        self._setup_progressive_loading()
        self._perform_load()
    
    def _load_data_medium(self):
        """Optimized loading for medium datasets (100-500 nodes)"""
        logging.info("NodesPage: Using medium data loading strategy")
        self._perform_load()
    
    def _load_data_light(self):
        """Optimized loading for light datasets (<100 nodes)"""
        logging.info("NodesPage: Using light data loading strategy")
        self._perform_load()
    
    def _perform_load(self):
        """Common loading logic"""
        self.is_loading = True
        self.is_showing_skeleton = False
        
        if hasattr(self, 'cluster_connector') and self.cluster_connector:
            self.cluster_connector.load_nodes()
        else:
            self._handle_no_connector()
    
    def _setup_progressive_loading(self):
        """Setup for progressive/chunked data loading"""
        self._progressive_loading_active = True
        self._loaded_chunks = 0
        self._total_expected_chunks = 0
    
    
    def _handle_no_connector(self):
        """Handle case when no cluster connector is available"""
        logging.warning("NodesPage: No cluster_connector available")
        self.is_loading = False
        self.show_no_data_message()
    
    def _force_fresh_load(self):
        """Force a fresh load bypassing cache"""
        if hasattr(self, '_last_load_time'):
            self._last_load_time = 0  # Reset cache timestamp
        self.load_data()
    
    def _display_resources_progressive(self, resources):
        """Display resources with progressive rendering for large datasets"""
        total_items = len(resources)
        logging.info(f"Progressive display for {total_items} resources")
        
        # Use the progressive table population
        self.show_table()
        self._populate_table_progressive(resources)
        
        # Update counters
        self.items_count.setText(f"Loading {total_items} items...")
        
        # Final update will be done in _finalize_progressive_rendering
    
    def force_load_data(self):
        """Override base class force_load_data with protection against rapid successive calls"""
        logging.info("NodesPage: force_load_data() called")
        
        # Prevent rapid successive calls that can cause segfaults
        import time
        current_time = time.time()
        if hasattr(self, '_last_force_load_time'):
            if current_time - self._last_force_load_time < 0.5:  # 500ms minimum interval
                logging.debug("NodesPage: Skipping force_load_data - too soon after previous call")
                return
        
        self._last_force_load_time = current_time
        
        # Check if currently loading to prevent conflicts
        if self.is_loading:
            logging.debug("NodesPage: Already loading, skipping force_load_data")
            return
        
        try:
            # Reset cache timestamp to force fresh load
            if hasattr(self, '_last_load_time'):
                self._last_load_time = 0
            
            # Reset virtual scrolling state safely
            if hasattr(self, '_virtual_scrolling_enabled'):
                self._rendered_items_count = 0
                self._total_available_items = 0
                self.all_data_loaded = False
                if hasattr(self, '_load_more_indicator_row'):
                    delattr(self, '_load_more_indicator_row')
            
            # Cancel any existing background operations
            self._cancel_background_operations()
            
            # Load data
            self.load_data()
            
        except Exception as e:
            logging.error(f"Error in force_load_data: {e}")
            self.is_loading = False
    
    def _cancel_background_operations(self):
        """Cancel any running background operations to prevent conflicts"""
        try:
            # Cancel background search worker
            if hasattr(self, '_search_worker') and self._search_worker:
                if self._search_worker.isRunning():
                    self._search_worker.quit()
                    self._search_worker.wait(100)  # Short wait
                    
            # Cancel async populator
            if hasattr(self, 'async_populator') and self.async_populator:
                self.async_populator.stop()
                
        except Exception as e:
            logging.debug(f"Error canceling background operations: {e}")
    
    def _verify_heavy_load_capability(self):
        """Verify that heavy load optimizations are working correctly"""
        capabilities = []
        
        # Check if all heavy load methods exist
        required_methods = [
            '_populate_table_progressive', '_populate_table_async', 
            '_process_large_dataset', '_process_medium_dataset',
            '_load_data_heavy', '_load_data_medium', '_load_data_light'
        ]
        
        for method_name in required_methods:
            if hasattr(self, method_name):
                capabilities.append(f"✓ {method_name}")
            else:
                capabilities.append(f"✗ {method_name} MISSING")
        
        # Check widget pool
        if hasattr(self, 'widget_pool') and self.widget_pool:
            capabilities.append("✓ Widget pool initialized")
            stats = self.widget_pool.get_pool_stats()
            capabilities.append(f"  Pool capacity: {stats.get('max_pool_size', 0)}")
        else:
            capabilities.append("✗ Widget pool MISSING")
        
        # Check cluster connector
        if hasattr(self, 'cluster_connector') and self.cluster_connector:
            capabilities.append("✓ Cluster connector connected")
        else:
            capabilities.append("✗ Cluster connector MISSING")
        
        logging.info("NodesPage Heavy Load Capabilities:")
        for capability in capabilities:
            logging.info(f"  {capability}")
        
        return all('✓' in cap for cap in capabilities)
    
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
    
    def configure_nodes_virtual_scrolling(self, enabled=True, threshold=50, initial_batch=50, load_batch=100):
        """Configure virtual scrolling specifically for nodes"""
        self._virtual_scrolling_enabled = enabled
        self.virtual_scroll_threshold = threshold
        self.items_per_page = initial_batch
        self.virtual_load_size = load_batch
        
        logging.info(f"NodesPage: Virtual scrolling configured - enabled={enabled}, threshold={threshold}, initial={initial_batch}, batch={load_batch}")
    
    def disable_nodes_virtual_scrolling(self):
        """Disable virtual scrolling for nodes page"""
        self.configure_nodes_virtual_scrolling(enabled=False)
        logging.info("NodesPage: Virtual scrolling disabled")
        
    
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