"""
Corrected implementation of the Nodes page with performance improvements and proper data display.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QToolButton, QMenu, QFrame, 
    QGraphicsDropShadowEffect, QSizePolicy, QStyleOptionButton, QStyle, QStyleOptionHeader,
    QApplication, QPushButton, QProxyStyle, QTableView, QAbstractItemView, QStyledItemDelegate
)
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal, QSize, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QCursor, QFont

from UI.Styles import AppStyles, AppColors, AppConstants
from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from Utils.cluster_connector import get_cluster_connector
from Utils.debounced_updater import get_debounced_updater
from Utils.performance_config import get_performance_config
from UI.Icons import resource_path
import datetime
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
# Conditions Color Delegate - Forces colors to be visible
#------------------------------------------------------------------
class ConditionColorDelegate(QStyledItemDelegate):
    """Custom delegate that forces condition colors to be visible, bypassing stylesheet issues"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def paint(self, painter, option, index):
        """Custom paint method to force condition colors"""
        if index.column() == 8:  # Conditions column
            text = index.data(Qt.ItemDataRole.DisplayRole)
            if text:
                # Prepare painter
                painter.save()
                
                # Set background (if selected)
                if option.state & QStyle.StateFlag.State_Selected:
                    painter.fillRect(option.rect, QColor(53, 132, 228, 40))  # Selection background
                elif option.state & QStyle.StateFlag.State_MouseOver:
                    painter.fillRect(option.rect, QColor(53, 132, 228, 25))  # Hover background
                
                # Set text color based on status - FORCED colors
                status = text.lower().strip()
                if status == 'ready':
                    text_color = QColor("#4CAF50")  # Bright green
                elif status == 'notready':
                    text_color = QColor("#FF0000")  # Bright red  
                elif status == 'unknown':
                    text_color = QColor("#FFA500")  # Bright orange
                else:
                    text_color = QColor("#FFFFFF")  # White fallback
                
                # Set font and pen
                font = painter.font()
                font.setWeight(QFont.Weight.Medium)  # Make it slightly bolder
                painter.setFont(font)
                painter.setPen(text_color)
                
                # Draw text centered
                painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, text)
                
                painter.restore()
                return
        
        # Use default painting for other columns
        super().paint(painter, option, index)
        
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

        # Timer for regular updates - but allow immediate updates on selection
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(5000)  # 5 seconds for responsive updates

    def generate_utilization_data(self, nodes_data, force_update=False):
        """Generate utilization data for nodes - optimized for performance"""
        logging.debug(f"GraphWidget ({self.title}): generate_utilization_data called - nodes: {len(nodes_data) if nodes_data else 0}, force_update: {force_update}")
        
        if not nodes_data or self._is_updating:
            if not nodes_data:
                logging.debug(f"GraphWidget ({self.title}): No nodes data provided")
            if self._is_updating:
                logging.debug(f"GraphWidget ({self.title}): Already updating, skipping")
            return
            
        current_time = time.time()
        # Only throttle if we have data, enough time hasn't passed, and not forced
        if (not force_update and self.utilization_data and 
            self._last_update_time > 0 and 
            current_time - self._last_update_time < self._update_interval):
            logging.debug(f"GraphWidget ({self.title}): Throttling update - last update {current_time - self._last_update_time:.1f}s ago")
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
                logging.debug(f"GraphWidget ({self.title}): Updated utilization data for {len(new_data)} nodes: {new_data}")
                logging.info(f"GraphWidget ({self.title}): Successfully processed utilization data from {len(nodes_data)} nodes")
            else:
                logging.warning(f"GraphWidget ({self.title}): No utilization data found in nodes for metric_key: {metric_key}")
                
        finally:
            self._is_updating = False

    def get_node_utilization(self, node_name):
        return self.utilization_data.get(node_name, 0)

    def set_selected_node(self, node_data, node_name):
        """Set the selected node for this graph"""
        logging.info(f"GraphWidget ({self.title}): Setting selected node to '{node_name}'")
        
        if not node_data or not node_name:
            logging.warning(f"GraphWidget ({self.title}): Cannot set selected node - node_data: {node_data is not None}, node_name: {node_name}")
            return
            
        self.selected_node = node_data
        self.node_name = node_name
        self.title_label.setText(f"{self.title} ({node_name})")
        
        logging.debug(f"GraphWidget ({self.title}): Set selected node {node_name}")
        logging.debug(f"GraphWidget ({self.title}): Available utilization data nodes: {list(self.utilization_data.keys())}")
        
        if node_name in self.utilization_data:
            self.current_value = round(self.utilization_data[node_name], 1)
            self.value_label.setText(f"{self.current_value}{self.unit}")
            logging.info(f"GraphWidget ({self.title}): Set value for {node_name}: {self.current_value}{self.unit}")
        else:
            logging.warning(f"GraphWidget ({self.title}): No utilization data found for {node_name} - available nodes: {list(self.utilization_data.keys())}")
            
        # Force immediate data update and display
        logging.debug(f"GraphWidget ({self.title}): Forcing immediate update and repaint for {node_name}")
        self.update_data()
        self.update()
        self.repaint()
        logging.debug(f"GraphWidget ({self.title}): Completed immediate update for {node_name}")

    def update_data(self):
        """Update the chart data - only use real cluster data"""
        if not self.selected_node or self.node_name not in self.utilization_data:
            if not self.selected_node:
                logging.debug(f"GraphWidget ({self.title}): No node selected for data update")
            if self.node_name not in self.utilization_data:
                logging.debug(f"GraphWidget ({self.title}): Node {self.node_name} not in utilization data")
            return
            
        # Use the actual utilization value from real cluster data
        current_utilization = self.utilization_data[self.node_name]
        
        # Only update if we have valid real data
        if current_utilization is not None and current_utilization >= 0:
            self.data.append(current_utilization)
            self.data.pop(0)
            self.current_value = round(current_utilization, 1)
            self.value_label.setText(f"{self.current_value}{self.unit}")
            logging.debug(f"GraphWidget ({self.title}): Updated data point for {self.node_name}: {current_utilization}")
            
            if self.isVisible():
                self.update()
                logging.debug(f"GraphWidget ({self.title}): Triggered visual update for {self.node_name}")

    def paintEvent(self, event):
        """Ultra-simplified paint event for maximum performance with proper bounds checking"""
        super().paintEvent(event)
        
        # Skip drawing if not visible or data is empty
        if not self.isVisible() or not self.data:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)  # Disabled for performance
        
        # Ensure proper bounds for drawing area
        widget_width = self.width()
        widget_height = self.height()
        
        if widget_width <= 32 or widget_height <= 50:
            return  # Widget too small to draw properly
        
        width = widget_width - 32
        # Reserve space for header (40px) and footer (25px)
        top_margin = 45  # Increased top margin for header
        bottom_margin = 30
        height = max(60, widget_height - top_margin - bottom_margin)
        bottom = widget_height - bottom_margin
        
        # Ensure proper drawing area
        if bottom <= top_margin:
            bottom = top_margin + height
        
        # Use cached color to avoid object creation
        if not hasattr(self, '_cached_color'):
            self._cached_color = QColor(self.color)
        
        # Simplified line drawing - no gradient for performance
        if len(self.data) > 1 and width > 0:
            # Use fixed 0-100% scale for proper percentage visualization
            self._min_value = 0
            self._max_value = 100 
            self._value_range = 100
            
            # Draw simple line without path objects for better performance
            painter.setPen(QPen(self._cached_color, 2))
            x_step = width / (len(self.data) - 1) if len(self.data) > 1 else 0
            
            prev_x = 16
            # Ensure y coordinates stay within the drawing area
            data_y = bottom - ((self.data[0] - self._min_value) / self._value_range) * height
            prev_y = max(top_margin + 5, min(bottom - 5, data_y))  # 5px padding from edges
            
            for i in range(1, len(self.data)):
                x = 16 + i * x_step
                data_y = bottom - ((self.data[i] - self._min_value) / self._value_range) * height
                y = max(top_margin + 5, min(bottom - 5, data_y))  # 5px padding from edges
                
                # Draw line ensuring it stays within visible area
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
            
            # Ensure text drawing is within bounds
            text_y = max(widget_height - 16, 10)
            painter.drawText(QRectF(1, text_y, 30, 12), Qt.AlignmentFlag.AlignCenter, self._cached_times[0])
            painter.drawText(QRectF(width - 15, text_y, 30, 12), Qt.AlignmentFlag.AlignCenter, self._cached_times[1])
            
            # Add percentage scale indicators and grid lines
            painter.setPen(QPen(QColor("#333333"), 1))  # Subtle dark gray for grid
            
            # Draw horizontal grid lines for 25%, 50%, 75%
            y_25 = top_margin + (height * 0.25)
            y_50 = top_margin + (height * 0.5) 
            y_75 = top_margin + (height * 0.75)
            
            painter.drawLine(16, int(y_25), width + 16, int(y_25))  # 75% line
            painter.drawLine(16, int(y_50), width + 16, int(y_50))  # 50% line  
            painter.drawLine(16, int(y_75), width + 16, int(y_75))  # 25% line
            
            # Scale text indicators
            painter.setPen(QPen(QColor("#666666"), 1))
            font.setPointSize(8)
            painter.setFont(font)
            
            # Only show key percentages to avoid clutter
            painter.drawText(QRectF(width + 20, top_margin - 1, 25, 12), Qt.AlignmentFlag.AlignLeft, "100%")
            painter.drawText(QRectF(width + 20, y_50 - 6, 25, 12), Qt.AlignmentFlag.AlignLeft, "50%") 
            painter.drawText(QRectF(width + 20, bottom - 11, 25, 12), Qt.AlignmentFlag.AlignLeft, "0%")
        
        # Only show placeholder if no node selected and space is available
        if not self.selected_node and width > 150:
            painter.setPen(QPen(QColor(AppColors.TEXT_SUBTLE)))
            placeholder_y = max(top_margin, min(widget_height - 50, 20))
            text_rect = QRectF(0, placeholder_y, widget_width, min(30, widget_height - placeholder_y - 20))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "Select a node")

    def cleanup(self):
        """Cleanup method"""
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()

# No Data Available Widget - removed, now using base class implementation

#------------------------------------------------------------------
# High-Performance Nodes Table Model for Heavy Data
#------------------------------------------------------------------
class NodesTableModel(QAbstractTableModel):
    """High-performance table model specifically optimized for node data"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._nodes_data = []
        self._headers = ["Name", "CPU", "Memory", "Disk", "Taints", "Roles", "Version", "Age", "Conditions", "Actions"]
        self._performance_cache = {}
        
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._nodes_data)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if section < len(self._headers):
                return self._headers[section]
        return None
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._nodes_data):
            return None
            
        node = self._nodes_data[index.row()]
        col = index.column()
        
        if role == Qt.ItemDataRole.DisplayRole:
            return self._get_node_display_data(node, col)
        elif role == Qt.ItemDataRole.BackgroundRole:
            return self._get_node_background_color(node, col)
        elif role == Qt.ItemDataRole.ForegroundRole:
            return self._get_node_text_color(node, col)
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [1, 2, 3, 4, 7, 9]:  # CPU, Memory, Disk, Taints, Age, Action columns
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            
        return None
    
    def _get_node_display_data(self, node: dict, col: int) -> str:
        """Get display data for node efficiently"""
        if col == 0:  # Name column
            return node.get("name", "Unknown")
        elif col == 1:  # CPU
            cpu_usage = node.get("cpu_usage")
            cpu_capacity = node.get("cpu_capacity", "")
            if cpu_usage is not None and cpu_capacity:
                return f"{cpu_capacity} ({cpu_usage:.1f}%)"
            return cpu_capacity or "N/A"
        elif col == 2:  # Memory (was col 3)
            memory_usage = node.get("memory_usage")
            memory_capacity = node.get("memory_capacity", "")
            if memory_usage is not None and memory_capacity:
                return f"{memory_capacity} ({memory_usage:.1f}%)"
            return memory_capacity or "N/A"
        elif col == 3:  # Disk (was col 4)
            disk_usage = node.get("disk_usage")
            disk_capacity = node.get("disk_capacity", "")
            if disk_usage is not None and disk_capacity:
                return f"{disk_capacity} ({disk_usage:.1f}%)"
            return disk_capacity or "N/A"
        elif col == 4:  # Taints (was col 5)
            return str(node.get("taints", "0"))
        elif col == 5:  # Roles (was col 6)
            roles = node.get("roles", [])
            return ", ".join(roles) if isinstance(roles, list) else str(roles)
        elif col == 6:  # Version (was col 7)
            return node.get("version", "Unknown")
        elif col == 7:  # Age (was col 8)
            return node.get("age", "Unknown")
        elif col == 8:  # Conditions (was col 9)
            return node.get("status", "Unknown")
        elif col == 9:  # Actions (was col 10)
            return ""  # Empty for action column - handled by widget
        return ""
    
    def _get_node_background_color(self, node: dict, col: int):
        """Get background color for node status - removed for conditions column"""
        # No background colors for conditions column anymore
        return None
    
    def _get_node_text_color(self, node: dict, col: int):
        """Get text color for node status - used for conditions column with strong colors"""
        if col == 8:  # Conditions/Status column (correct index)
            status = node.get("status", "Unknown").lower()
            if status == "ready":
                # Use bright green that stands out
                color = QColor(AppColors.STATUS_ACTIVE)
                color.setAlpha(255)  # Full opacity
                return color
            elif status == "notready":
                # Use bright red that stands out  
                color = QColor(AppColors.STATUS_DISCONNECTED)
                color.setAlpha(255)  # Full opacity
                return color
            else:
                # Use bright orange for unknown status
                color = QColor("#FFA500")
                color.setAlpha(255)  # Full opacity
                return color
        elif col == 9:  # Action column
            return QColor("#666666")  # Gray text for action menu
        return None
    
    def update_nodes_data(self, nodes_data):
        """Update the model with new node data efficiently"""
        self.beginResetModel()
        self._nodes_data = nodes_data or []
        self._performance_cache.clear()  # Clear cache on data update
        self.endResetModel()
        logging.info(f"NodesTableModel: Updated with {len(self._nodes_data)} nodes")
    
    def get_node_at_row(self, row: int):
        """Get node data at specific row"""
        if 0 <= row < len(self._nodes_data):
            return self._nodes_data[row]
        return None

#------------------------------------------------------------------
# NodesPage - Now extending BaseResourcePage for consistency with Virtual Scrolling
#------------------------------------------------------------------
class NodesPage(BaseResourcePage):
    """
    Displays Kubernetes Nodes with live data and resource operations.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "nodes"
        self.show_namespace_dropdown = False  # Nodes are cluster-scoped
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
        
        # Initialize search state
        self._is_searching = False
        self._current_search_query = None
        
        # Set up UI
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Nodes page with virtual scrolling"""
        headers = ["Name", "CPU", "Memory", "Disk", "Taints", "Roles", "Version", "Age", "Conditions", "Actions"]
        sortable_columns = {0, 1, 2, 3, 4, 5, 6, 7, 8}  # Adjusted column indices after removing checkbox column
        
        # Check if we should use virtual scrolling for heavy data
        # Detect PyQt6 compatibility issues
        virtual_scrolling_supported = True
        try:
            # Test PyQt6 enum access
            _ = QAbstractItemView.SelectionBehavior.SelectRows
        except AttributeError:
            try:
                # Try older enum style
                _ = QAbstractItemView.SelectRows
            except AttributeError:
                virtual_scrolling_supported = False
                logging.warning("NodesPage: PyQt6 virtual scrolling enums not available - disabling virtual scrolling")
        
        self.use_virtual_scrolling = (self.perf_config.get('enable_virtual_scrolling', True) and 
                                     virtual_scrolling_supported)
        
        if self.use_virtual_scrolling:
            # Use virtual scrolling with custom layout (title and controls above table)
            logging.info("NodesPage: Setting up virtual scrolling mode")
            
            try:
                # Set up base UI with minimal header (title and controls will be above table)
                self._setup_base_ui_with_search("Nodes")
                
                # Setup virtual table and graphs
                self._setup_virtual_table()
                self._setup_graphs()
                
                # Setup the complete layout with graphs above table and controls above table
                self._setup_virtual_layout()
                
                # Load initial data
                QTimer.singleShot(100, self.force_load_data)
                
                logging.info("NodesPage: Virtual table and graphs created successfully")
            except Exception as e:
                logging.error(f"NodesPage: Virtual scrolling setup failed: {e}")
                self.use_virtual_scrolling = False
        
        if not self.use_virtual_scrolling:
            # Use traditional table widget
            layout = super().setup_ui("Nodes", headers, sortable_columns)
            logging.info("NodesPage: Using traditional table widget")
            return  # Early return - base class handles everything
    
    def _add_filter_controls(self, header_layout):
        """Override to add search bar above table instead of in header"""
        # For traditional mode, don't add search to header - we'll add it above table later
        if not self.use_virtual_scrolling:
            # Skip adding search to header for traditional mode
            pass
        else:
            # For virtual scrolling, use the original method but we'll move it later
            super()._add_filter_controls(header_layout)
    
    def _replace_table_with_virtual_and_graphs(self):
        """Replace BaseResourcePage table with virtual table and move search bar above table"""
        try:
            logging.debug("NodesPage: Starting to replace BaseResourcePage table with virtual table and graphs")
            
            # First, setup virtual table and graphs
            self._setup_virtual_table()
            self._setup_graphs()
            
            # Find and remove the BaseResourcePage search bar from header
            self._remove_base_resource_page_search_bar()
            
            # Now setup the new layout with repositioned search bar
            self._setup_virtual_layout()
            
            logging.debug("NodesPage: Successfully replaced table and repositioned search bar")
            
        except Exception as e:
            logging.error(f"NodesPage: Failed to replace table with virtual layout: {e}")
            logging.debug("NodesPage: Replace table error details", exc_info=True)
            raise e
    
    def _remove_base_resource_page_search_bar(self):
        """Remove the search bar created by BaseResourcePage from the header"""
        try:
            # Find and remove the search bar from BaseResourcePage layout
            if hasattr(self, 'search_bar') and self.search_bar:
                # Remove from parent layout
                parent_widget = self.search_bar.parent()
                if parent_widget:
                    parent_layout = parent_widget.layout()
                    if parent_layout:
                        # Find the search bar's container in the layout
                        for i in range(parent_layout.count()):
                            item = parent_layout.itemAt(i)
                            if item and item.widget() and item.widget() == self.search_bar:
                                parent_layout.removeItem(item)
                                break
                            elif item and item.layout():
                                # Check if search bar is in a sublayout
                                sublayout = item.layout()
                                for j in range(sublayout.count()):
                                    subitem = sublayout.itemAt(j)
                                    if subitem and subitem.widget() and subitem.widget() == self.search_bar:
                                        sublayout.removeItem(subitem)
                                        break
                
                # Keep reference to search bar but remove from old position
                old_search_bar = self.search_bar
                old_search_bar.setParent(None)
                self.search_bar = None  # Clear reference temporarily
                
                logging.debug("NodesPage: Removed BaseResourcePage search bar from header")
            
        except Exception as e:
            logging.warning(f"NodesPage: Failed to remove BaseResourcePage search bar: {e}")
    
    def _setup_virtual_table(self):
        """Setup virtual table for heavy data scenarios"""
        from PyQt6.QtWidgets import QVBoxLayout
        
        try:
            # Create the virtual table model
            self.virtual_model = NodesTableModel(self)
            
            # Create QTableView for virtual scrolling
            self.table = QTableView(self)
            self.table.setModel(self.virtual_model)
        
            # Configure virtual table properties with PyQt6 compatibility
            self.table.setAlternatingRowColors(True)
            
            # Handle PyQt6 enum compatibility
            try:
                self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
                self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
                self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
                self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
            except AttributeError:
                # Fallback for older PyQt6 versions
                self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
                self.table.setSelectionMode(QAbstractItemView.SingleSelection)
                self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
                self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
            
            self.table.setSortingEnabled(True)
            self.table.setShowGrid(False)
            
            # Apply proper styling for virtual table (QTableView)
            self._apply_virtual_table_styling()
        
            # Set row height for consistency and action button visibility
            self.table.verticalHeader().setDefaultSectionSize(40)
            self.table.verticalHeader().setMinimumSectionSize(40)
            self.table.verticalHeader().hide()
            
            # Ensure viewport updates properly for action buttons
            self.table.setAlternatingRowColors(True)
            self.table.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            
            # Connect signals
            self.table.clicked.connect(self._handle_virtual_table_click)
            self.table.doubleClicked.connect(self._on_table_double_click)
            self.table.selectionModel().currentRowChanged.connect(self._handle_virtual_row_selection)
            
            # Apply condition color delegate to force colors to be visible
            condition_delegate = ConditionColorDelegate(self)
            self.table.setItemDelegateForColumn(8, condition_delegate)  # Column 8 is Conditions
            logging.debug("NodesPage: Applied condition color delegate to force color visibility")
            
            # Create items count label for virtual scrolling
            from PyQt6.QtWidgets import QLabel
            self.items_count = QLabel("0 items")
            self.items_count.setStyleSheet("color: #666; font-size: 12px;")
            
            logging.debug("NodesPage: Virtual table created and ready for layout integration")
            
            logging.info("NodesPage: Virtual table setup completed")
            
        except Exception as e:
            logging.error(f"NodesPage: Virtual table setup failed: {e}")
            logging.debug(f"NodesPage: Virtual table error details", exc_info=True)
            # Clean up partial state
            if hasattr(self, 'virtual_model'):
                delattr(self, 'virtual_model')
            if hasattr(self, 'table'):
                delattr(self, 'table')
            # Fallback to traditional table will be handled by setup_page_ui
            self.use_virtual_scrolling = False
            raise e  # Re-raise to trigger fallback in setup_page_ui
    
    def _setup_graphs(self):
        """Setup graphs for virtual scrolling mode"""
        try:
            # Create the graph widgets (same as in traditional setup)
            self.cpu_graph = GraphWidget("CPU Usage", "%", AppColors.ACCENT_ORANGE)
            self.mem_graph = GraphWidget("Memory Usage", "%", AppColors.ACCENT_GREEN)
            self.disk_graph = GraphWidget("Disk Usage", "%", AppColors.ACCENT_BLUE)
            
            # Configure graphs for full width utilization
            for graph in [self.cpu_graph, self.mem_graph, self.disk_graph]:
                # Remove fixed size to allow full width utilization
                graph.setMinimumSize(200, 160)  # Minimum size for readability
                graph.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            
            logging.debug("NodesPage: Graphs created for virtual scrolling mode")
            
        except Exception as e:
            logging.error(f"NodesPage: Failed to create graphs: {e}")
            # Create dummy graphs to prevent attribute errors
            self.cpu_graph = None
            self.mem_graph = None 
            self.disk_graph = None
    
    def _replace_table_with_virtual_and_graphs(self):
        """Replace the BaseResourcePage table with virtual table and graphs while preserving proper header structure"""
        try:
            logging.debug("NodesPage: Starting table replacement with virtual table and graphs")
            
            # First setup virtual table and graphs
            self._setup_virtual_table()
            self._setup_graphs()
            
            # Create a new container widget that will hold graphs above the virtual table
            container_widget = QWidget()
            container_layout = QVBoxLayout(container_widget)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(16)
            
            # Create graphs layout (horizontal, full width)
            if self.cpu_graph and self.mem_graph and self.disk_graph:
                graphs_container = QWidget()
                graphs_layout = QHBoxLayout(graphs_container)
                graphs_layout.setContentsMargins(0, 0, 0, 0)
                graphs_layout.setSpacing(16)
                
                # Add graphs with equal width distribution (no addStretch)
                graphs_layout.addWidget(self.cpu_graph, 1)  # Equal stretch factor
                graphs_layout.addWidget(self.mem_graph, 1)   # Equal stretch factor
                graphs_layout.addWidget(self.disk_graph, 1)  # Equal stretch factor
                
                container_layout.addWidget(graphs_container)
                logging.debug("NodesPage: Added graphs to container with full width layout")
            
            # Add the virtual table to the container
            if hasattr(self, 'table') and self.table:
                container_layout.addWidget(self.table)
                logging.debug("NodesPage: Added virtual table to container")
                
                # Apply styling for virtual table  
                self._apply_virtual_table_styling()
                
                # Ensure clean header without checkboxes
                self._ensure_clean_table_header()
                
                # Connect double-click to detail page (EXACT same as BaseResourcePage)
                self.table.doubleClicked.connect(self._on_table_double_click)
                
                # Connect search bar from BaseResourcePage to our search functionality
                if hasattr(self, 'search_bar') and self.search_bar:
                    # Disconnect any existing connections first
                    try:
                        self.search_bar.textChanged.disconnect()
                    except:
                        pass
                    # Connect to our search functionality
                    self.search_bar.textChanged.connect(self._on_search_text_changed)
                    logging.debug("NodesPage: Connected inherited search bar to virtual table search")
            
            # Replace the table in the _table_stack (created by BaseResourcePage.setup_ui)
            if hasattr(self, '_table_stack'):
                # Clear the stack by removing all widgets (PyQt6 compatible)
                while self._table_stack.count() > 0:
                    widget = self._table_stack.widget(0)
                    self._table_stack.removeWidget(widget)
                    if widget:
                        widget.setParent(None)
                        
                # Add our new container
                self._table_stack.addWidget(container_widget)
                self._table_stack.setCurrentWidget(container_widget)
                logging.debug("NodesPage: Replaced BaseResourcePage table with virtual table + graphs container")
                
                # Remove the select all checkbox created by BaseResourcePage
                self._remove_base_resource_page_checkbox()
                
            else:
                logging.error("NodesPage: _table_stack not found - BaseResourcePage setup may have failed")
                
                # Update the table reference to point to our virtual table
                # This ensures BaseResourcePage methods can still work with our virtual table
                if hasattr(self, 'table') and self.table:
                    # Keep the virtual table as self.table so BaseResourcePage methods work
                    logging.debug("NodesPage: Virtual table properly referenced for BaseResourcePage compatibility")
                
            logging.info("NodesPage: Successfully replaced table with virtual table and graphs")
            
        except Exception as e:
            logging.error(f"NodesPage: Failed to replace table with virtual table and graphs: {e}")
            logging.debug("NodesPage: Table replacement error details", exc_info=True)
            raise e
    
    def _on_table_double_click(self, index):
        """Handle double-click on virtual table to open detail page using standard pattern"""
        try:
            if not index.isValid():
                return
                
            # Get the node name from the clicked row
            name_index = self.virtual_model.index(index.row(), 0)  # Name is in column 0 (no more checkbox column)
            node_name = self.virtual_model.data(name_index, Qt.ItemDataRole.DisplayRole)
            
            if node_name:
                # Use standard pattern to find parent with detail_manager
                parent = self.parent()
                while parent and not hasattr(parent, 'detail_manager'):
                    parent = parent.parent()
                
                if parent and hasattr(parent, 'detail_manager'):
                    # Nodes are cluster-scoped, so no namespace
                    parent.detail_manager.show_detail('node', node_name, None)
                    logging.debug(f"NodesPage: Opened detail page for node '{node_name}' via double-click")
                else:
                    logging.warning("NodesPage: Could not find detail_manager to open detail page")
            else:
                logging.warning("NodesPage: Could not get node name for detail page")
                
        except Exception as e:
            logging.error(f"NodesPage: Error handling double-click for detail page: {e}")
    
    def _add_virtual_action_buttons(self, resources_data):
        """Add actual action button widgets to virtual table like other pages"""
        try:
            if not hasattr(self, 'table') or not self.table or not resources_data:
                logging.debug("NodesPage: Cannot add action buttons - missing table or data")
                return
            
            from UI.Styles import AppStyles
            
            logging.debug(f"NodesPage: Adding {len(resources_data)} real action button widgets to virtual table")
            
            for row in range(len(resources_data)):
                try:
                    node_data = resources_data[row]
                    node_name = node_data.get('name', f'node-{row}')
                    
                    # Create action button using nodes-specific method
                    action_btn = self._create_nodes_action_button(row, node_name, None)
                    
                    # Apply the same styling as other pages
                    try:
                        action_btn.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
                    except (ImportError, AttributeError):
                        action_btn.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE)
                    
                    # Create action container exactly like other pages
                    container = self._create_action_container(row, action_btn)
                    try:
                        container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
                    except (ImportError, AttributeError):
                        pass
                    
                    # Set the widget in the table
                    index = self.virtual_model.index(row, 9)  # Column 9 is Actions
                    self.table.setIndexWidget(index, container)
                    
                    logging.debug(f"NodesPage: Created real action button widget for row {row}, node '{node_name}'")
                    
                except Exception as e:
                    logging.error(f"NodesPage: Error creating action button widget for row {row}: {e}")
                    
            logging.debug(f"NodesPage: Successfully added {len(resources_data)} real action button widgets")
            
        except Exception as e:
            logging.error(f"NodesPage: Error adding virtual action button widgets: {e}")
    
    def _handle_view_details_action(self, node_name):
        """Handle View Details action"""
        try:
            parent = self.parent()
            while parent and not hasattr(parent, 'detail_manager'):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'detail_manager'):
                parent.detail_manager.show_detail('node', node_name, None)
                logging.info(f"NodesPage: Opened detail page for node '{node_name}'")
            else:
                logging.warning("NodesPage: Could not find detail_manager")
        except Exception as e:
            logging.error(f"NodesPage: Error opening detail page for node '{node_name}': {e}")
    
    def _handle_edit_action(self, node_name):
        """Handle Edit action - opens detail page in edit mode"""
        logging.info(f"NodesPage: Edit action for node '{node_name}'")
        try:
            # Find the ClusterView that contains the detail manager
            parent = self.parent()
            cluster_view = None
            
            # Walk up the parent tree to find ClusterView
            while parent:
                if parent.__class__.__name__ == 'ClusterView' or hasattr(parent, 'detail_manager'):
                    cluster_view = parent
                    break
                parent = parent.parent()
            
            if cluster_view and hasattr(cluster_view, 'detail_manager'):
                # Show the detail page first  
                cluster_view.detail_manager.show_detail('node', node_name, None)
                
                # After showing detail page, trigger edit mode
                # We need to wait a bit for the detail page to load completely
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, lambda: self._trigger_edit_mode(cluster_view))
                
                logging.info(f"Opening node/{node_name} in edit mode")
            else:
                # Fallback: show error if detail manager not found
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "Edit Resource",
                    f"Cannot edit node/{node_name}: Detail panel not available"
                )
                logging.warning(f"Detail manager not found for editing {node_name}")
                
        except Exception as e:
            logging.error(f"Failed to open {node_name} for editing: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "Error", 
                f"Failed to open {node_name} for editing: {str(e)}"
            )
    
    def _handle_delete_action(self, node_name):
        """Handle Delete action - shows confirmation and deletes node"""
        logging.info(f"NodesPage: Delete action for node '{node_name}'")
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            # Show confirmation dialog
            reply = QMessageBox.question(
                self, 
                'Confirm Deletion',
                f'Are you sure you want to delete node "{node_name}"?\n\nThis action cannot be undone.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                logging.info(f"NodesPage: User confirmed deletion of node '{node_name}'")
                # TODO: Implement actual node deletion via Kubernetes API
                # For now, just show a message
                QMessageBox.information(
                    self,
                    'Node Deletion',
                    f'Node "{node_name}" deletion would be executed.\n(Feature not yet implemented)'
                )
            else:
                logging.info(f"NodesPage: User cancelled deletion of node '{node_name}'")
                
        except Exception as e:
            logging.error(f"NodesPage: Error in delete action for node '{node_name}': {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, 'Error', f'Error deleting node: {str(e)}')
    
    def _create_nodes_action_button(self, row, node_name, node_namespace):
        """Create action button with nodes-specific menu - matches BaseResourcePage style exactly"""
        from PyQt6.QtWidgets import QToolButton, QMenu
        from PyQt6.QtGui import QIcon
        from PyQt6.QtCore import QSize, Qt
        from functools import partial
        from UI.Icons import resource_path
        import os
        
        button = QToolButton()
        # Use custom SVG icon (EXACT same code as BaseResourcePage)
        try:
            icon_path = resource_path("Icons/Moreaction_Button.svg")
            if os.path.exists(icon_path):
                button.setIcon(QIcon(icon_path))
                button.setIconSize(QSize(16, 16))
        except Exception as e:
            logging.warning(f"Could not load action button icon: {e}")
        
        # Remove text and change to icon-only style (EXACT same code as BaseResourcePage)
        button.setText("")
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setFixedWidth(30)
        
        # Apply BaseResourcePage styling
        try:
            from UI.Styles import AppStyles
            button.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE)
        except (ImportError, AttributeError) as e:
            logging.debug(f"Could not load AppStyles for button: {e}")
            # Fallback styling (EXACT same as BaseResourcePage)
            button.setStyleSheet("""
                QToolButton {
                    background-color: transparent;
                    border: none;
                    padding: 2px;
                }
                QToolButton:hover {
                    background-color: #3d3d3d;
                    border-radius: 2px;
                }
            """)
        
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Create menu with nodes-specific actions
        menu = QMenu(button)
        try:
            from UI.Styles import AppStyles
            menu.setStyleSheet(AppStyles.MENU_STYLE)
        except (ImportError, AttributeError) as e:
            logging.debug(f"Could not load AppStyles for menu: {e}")
            # Fallback menu styling (EXACT same as BaseResourcePage)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    color: white;
                }
                QMenu::item {
                    padding: 5px 20px;
                }
                QMenu::item:selected {
                    background-color: #0078d4;
                }
            """)
        
        # Add nodes-specific actions
        menu.addAction("View Details", partial(self._handle_view_details_action, node_name))
        menu.addAction("Edit", partial(self._handle_edit_action, node_name))
        menu.addAction("Delete", partial(self._handle_delete_action, node_name))
        menu.addAction("View Metrics", partial(self._select_node_for_graphs_virtual, row))
        
        button.setMenu(menu)
        return button
    
    def _apply_virtual_table_styling(self):
        """Apply proper styling to virtual table (QTableView) matching other pages"""
        try:
            from UI.Styles import AppColors
            
            # Create QTableView-specific styling (adapted from TABLE_STYLE in UI/Styles.py)
            virtual_table_style = f"""
                QTableView {{
                    background-color: {AppColors.CARD_BG};
                    border: none;
                    gridline-color: transparent;
                    outline: none;
                    color: {AppColors.TEXT_TABLE};
                    selection-background-color: rgba(53, 132, 228, 0.15);
                    alternate-background-color: transparent;
                    font-size: 11px;
                }}
                
                QTableView::item {{
                    padding: 10px 8px;
                    border: none;
                    outline: none;
                    background-color: transparent;
                    min-height: 24px;
                }}
                
                QTableView::item:hover {{
                    background-color: rgba(53, 132, 228, 0.10);
                    border: none;
                }}
                
                QTableView::item:selected {{
                    background-color: rgba(53, 132, 228, 0.15);
                }}
                
                /* Allow model colors to override stylesheet colors */
                QTableView::item[role="condition"] {{
                    color: inherit;
                }}
                
                QTableView::item:selected:hover {{
                    background-color: rgba(53, 132, 228, 0.20);
                }}
                
                /* Header styling */
                QHeaderView::section {{
                    background-color: {AppColors.HEADER_BG};
                    color: {AppColors.TEXT_SECONDARY};
                    padding: 10px 8px;
                    border: none;
                    border-bottom: 1px solid {AppColors.BORDER_COLOR};
                    font-size: 12px;
                    font-weight: 600;
                }}
                
                QHeaderView::section:hover {{
                    background-color: {AppColors.BG_MEDIUM};
                }}
                
                /* Ensure selection stays visible when focus is lost */
                QTableView::item:selected:!focus {{
                    background-color: rgba(53, 132, 228, 0.12);
                    color: {AppColors.TEXT_LIGHT};
                }}
                
                /* Remove focus rectangle */
                QTableView:focus {{
                    outline: none;
                    border: none;
                }}
            """
            
            self.table.setStyleSheet(virtual_table_style)
            
            # Ensure proper row height
            self.table.verticalHeader().setMinimumSectionSize(40)
            self.table.verticalHeader().setDefaultSectionSize(40)
            
            logging.debug("NodesPage: Applied virtual table styling")
            
        except Exception as e:
            logging.error(f"NodesPage: Failed to apply virtual table styling: {e}")
    
    def _ensure_clean_table_header(self):
        """Ensure the virtual table header is clean without any checkboxes"""
        try:
            if hasattr(self, 'table') and self.table:
                # Create a clean header view without any custom widgets
                from PyQt6.QtWidgets import QHeaderView
                
                header = self.table.horizontalHeader()
                if header:
                    # Ensure no widgets are set in the header
                    for section in range(header.count()):
                        # Remove any widgets that might have been set (like checkboxes)
                        if hasattr(header, 'setSectionWidget') and hasattr(header, 'sectionWidget'):
                            widget = header.sectionWidget(section) 
                            if widget:
                                header.setSectionWidget(section, None)
                                widget.setParent(None)
                                widget.deleteLater()
                        
                        # Ensure clean section text
                        if section < self.virtual_model.columnCount():
                            header_text = self.virtual_model.headerData(section, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
                            if header_text:
                                # Make sure it's just the text, no HTML or special formatting
                                clean_text = str(header_text).replace('<', '').replace('>', '').strip()
                                self.virtual_model._headers[section] = clean_text
                    
                    # Force header to refresh
                    header.viewport().update()
                    
                    logging.debug("NodesPage: Ensured clean table header without checkboxes")
                
        except Exception as e:
            logging.error(f"NodesPage: Failed to ensure clean table header: {e}")
    
    def _remove_base_resource_page_checkbox(self):
        """Remove the select all checkbox created by BaseResourcePage"""
        try:
            # Remove the select_all_checkbox if it exists
            if hasattr(self, 'select_all_checkbox') and self.select_all_checkbox:
                logging.debug("NodesPage: Removing BaseResourcePage select_all_checkbox")
                
                # Hide and remove the checkbox
                self.select_all_checkbox.hide()
                self.select_all_checkbox.setParent(None)
                self.select_all_checkbox.deleteLater()
                self.select_all_checkbox = None
                
                logging.debug("NodesPage: Successfully removed BaseResourcePage checkbox")
                
        except Exception as e:
            logging.error(f"NodesPage: Failed to remove BaseResourcePage checkbox: {e}")
    
    def _create_select_all_checkbox(self):
        """Override BaseResourcePage method - NodesPage doesn't need select all checkbox"""
        # Return None to prevent checkbox creation
        logging.debug("NodesPage: Overriding _create_select_all_checkbox - returning None")
        return None
    
    def _add_select_all_to_header(self):
        """Override BaseResourcePage method - NodesPage doesn't need select all checkbox"""
        # Do nothing to prevent checkbox being added to header
        logging.debug("NodesPage: Overriding _add_select_all_to_header - doing nothing")
        pass
    
    def _setup_base_ui_with_search(self, title):
        """Setup base UI structure with minimal header (title and controls moved to above table)"""
        try:
            from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox
            from UI.Styles import AppStyles
            
            # Create main page layout
            page_main_layout = QVBoxLayout(self)
            page_main_layout.setContentsMargins(16, 16, 16, 16)
            page_main_layout.setSpacing(16)
            
            # Store the main layout for later use (no header controls here - they'll be above the table)
            self._main_page_layout = page_main_layout
            
            logging.debug("NodesPage: Base UI setup completed (title, count, refresh, and search bar will be added above table)")
            
        except Exception as e:
            logging.error(f"NodesPage: Failed to setup base UI: {e}")
    
    def _on_search_text_changed(self, text):
        """Handle search text changes with debouncing"""
        # Use base class search functionality
        if hasattr(super(), '_on_search_text_changed'):
            super()._on_search_text_changed(text)
        else:
            # Fallback implementation
            if hasattr(self, '_debounced_updater'):
                self._debounced_updater.schedule_update(
                    'search_nodes',
                    self._perform_search,
                    delay_ms=300
                )
    
    def _perform_search(self):
        """Perform search on node data"""
        if not hasattr(self, 'search_bar') or not self.search_bar:
            return
            
        search_text = self.search_bar.text().strip()
        
        if not search_text:
            # No search query, reload normal resources
            self._clear_search_and_reload()
            return
        
        # Mark that we're searching
        self._is_searching = True
        self._current_search_query = search_text.lower()
        
        # Filter current node data
        self._filter_nodes_by_search(search_text.lower())
    
    def _filter_nodes_by_search(self, search_query):
        """Filter nodes based on search query"""
        if not hasattr(self, 'nodes_data') or not self.nodes_data:
            return
            
        try:
            filtered_nodes = []
            for node in self.nodes_data:
                # Search in node name, status, roles, etc.
                searchable_text = ' '.join([
                    str(node.get('name', '')),
                    str(node.get('status', '')),
                    str(node.get('version', '')),
                    ' '.join(node.get('roles', [])),
                    str(node.get('conditions', ''))
                ]).lower()
                
                if search_query in searchable_text:
                    filtered_nodes.append(node)
            
            # Update table with filtered data
            logging.info(f"NodesPage: Search '{search_query}' found {len(filtered_nodes)} matches")
            self.populate_table(filtered_nodes)
            self.items_count.setText(f"{len(filtered_nodes)} items (filtered)")
            
        except Exception as e:
            logging.error(f"NodesPage: Error filtering nodes: {e}")
    
    def _clear_search_and_reload(self):
        """Clear search and reload normal resources"""
        self._is_searching = False
        self._current_search_query = None
        
        if hasattr(self, 'nodes_data') and self.nodes_data:
            # Reload full data
            self.populate_table(self.nodes_data)
            self.items_count.setText(f"{len(self.nodes_data)} items")
    
    
    def _handle_action(self, action, row):
        """Override base class _handle_action to work with both virtual and traditional tables"""
        logging.info(f"NodesPage: Action '{action}' clicked on row {row}")
        
        # Handle virtual table differently
        if hasattr(self, 'virtual_model') and self.virtual_model and hasattr(self, 'use_virtual_scrolling') and self.use_virtual_scrolling:
            return self._handle_virtual_table_action(action, row)
        else:
            # Use base class implementation for traditional table
            return super()._handle_action(action, row)
    
    def _handle_virtual_table_action(self, action, row):
        """Handle action button clicks in virtual table using standard BaseResourcePage pattern"""
        try:
            node = self.virtual_model.get_node_at_row(row)
            if not node:
                logging.warning(f"NodesPage: No node found at row {row}")
                return
                
            node_name = node.get('name', 'Unknown')
            logging.info(f"NodesPage: Virtual action '{action}' for node '{node_name}' (row {row})")
            
            if action == "View Details":
                # Show detail page using standard pattern
                parent = self.parent()
                while parent and not hasattr(parent, 'detail_manager'):
                    parent = parent.parent()
                
                if parent and hasattr(parent, 'detail_manager'):
                    parent.detail_manager.show_detail('node', node_name, None)
            elif action == "Edit":
                # Use the standard edit resource method from base class
                self._handle_edit_resource(node_name, None, node)
            elif action == "Delete":
                # Use the standard delete resource method from base class
                self.delete_resource(node_name, None)
            elif action == "View Metrics":
                # Select node for graphs display
                self._select_node_for_graphs_virtual(row)
                    
        except Exception as e:
            logging.error(f"NodesPage: Error handling virtual action '{action}' at row {row}: {e}")
    
    def _setup_virtual_layout(self):
        """Setup the complete layout structure for virtual scrolling mode with graphs above table"""
        try:
            from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QPushButton
            from UI.Styles import AppStyles
            
            # Use the existing main page layout from _setup_base_ui_with_search
            if not hasattr(self, '_main_page_layout'):
                logging.error("NodesPage: Main page layout not found")
                return
            
            main_layout = self._main_page_layout
            
            # Create graphs section at the top if they exist (full width, no centering)
            has_graphs = any(hasattr(self, attr) and getattr(self, attr) 
                           for attr in ['cpu_graph', 'mem_graph', 'disk_graph'])
            
            if has_graphs:
                # Create horizontal layout for graphs that uses FULL width without side spaces
                graphs_widget = QWidget()
                graphs_layout = QHBoxLayout(graphs_widget)
                graphs_layout.setContentsMargins(0, 0, 0, 0)  # Remove all margins
                graphs_layout.setSpacing(15)  # Spacing between graphs only
                
                # NO stretch before graphs - start from left edge
                
                # Add existing graphs horizontally with equal spacing
                graphs_added = 0
                for graph_attr in ['cpu_graph', 'mem_graph', 'disk_graph']:
                    if hasattr(self, graph_attr):
                        graph = getattr(self, graph_attr)
                        if graph:
                            # Make graphs larger to utilize full available width
                            graph.setFixedSize(300, 180)  # Increased to 300 width
                            graphs_layout.addWidget(graph)
                            graphs_added += 1
                            logging.debug(f"NodesPage: Added {graph_attr} to full-width layout")
                            
                            # Add flexible spacing between graphs (except after the last one)
                            if graphs_added < 3:  # Don't add stretch after the last graph
                                graphs_layout.addStretch(1)
                
                # NO stretch after graphs - end at right edge
                
                if graphs_added > 0:
                    # Add graphs section to main layout
                    main_layout.addWidget(graphs_widget)
                    logging.debug("NodesPage: Added graphs section with FULL width utilization")
            
            # Create header controls DIRECTLY in main layout to ensure visibility
            table_header_layout = QHBoxLayout()
            
            # Create Node title
            from PyQt6.QtWidgets import QLabel, QLineEdit
            node_title_label = QLabel("Nodes")
            title_label_style = getattr(AppStyles, "TITLE_STYLE", "font-size: 20px; font-weight: bold; color: #ffffff;")
            node_title_label.setStyleSheet(title_label_style)
            table_header_layout.addWidget(node_title_label)
            
            # Add items count
            if hasattr(self, 'items_count') and self.items_count:
                table_header_layout.addWidget(self.items_count)
            
            # Add search bar
            search_label = QLabel("Search:")
            search_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: normal; margin-left: 16px;")
            search_label.setMinimumWidth(50)
            table_header_layout.addWidget(search_label)
            
            self.search_bar = QLineEdit()
            self.search_bar.setPlaceholderText("Search nodes...")
            self.search_bar.textChanged.connect(self._on_search_text_changed)
            self.search_bar.setFixedWidth(180)
            self.search_bar.setFixedHeight(24)
            
            # Apply search bar styling
            search_style = getattr(AppStyles, 'SEARCH_INPUT', 
                """QLineEdit {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 12px;
                }
                QLineEdit:focus {
                    border-color: #0078d4;
                    background-color: #353535;
                }""")
            self.search_bar.setStyleSheet(search_style)
            table_header_layout.addWidget(self.search_bar)
            
            # Add stretch to push refresh button to the right
            table_header_layout.addStretch(1)
            
            # Create refresh button
            refresh_btn = QPushButton("Refresh")
            refresh_btn.setMinimumHeight(24)
            refresh_btn.setFixedHeight(24)
            refresh_style = getattr(AppStyles, "SECONDARY_BUTTON_STYLE",
                                    """QPushButton { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3d3d3d;
                                                   border-radius: 4px; padding: 4px 8px; font-weight: bold; }
                                       QPushButton:hover { background-color: #3d3d3d; }
                                       QPushButton:pressed { background-color: #1e1e1e; }"""
                                    )
            refresh_btn.setStyleSheet(refresh_style)
            refresh_btn.clicked.connect(self.force_load_data)
            table_header_layout.addWidget(refresh_btn)
            
            # Create header container
            table_header_container = QWidget()
            table_header_container.setLayout(table_header_layout)
            table_header_container.setFixedHeight(40)  # Increased height for better visibility
            table_header_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            
            # Add header DIRECTLY to main layout (not inside table widget)
            main_layout.addWidget(table_header_container)
            
            # Create table section ONLY for the actual table (no header inside)
            table_widget = QWidget()
            table_layout = QVBoxLayout(table_widget)
            table_layout.setContentsMargins(10, 0, 10, 10)  # No top margin needed since header is separate
            table_layout.setSpacing(0)
            
            # Add the virtual table to the table layout
            if hasattr(self, 'table') and self.table:
                # Ensure table doesn't have overlapping geometry
                self.table.setContentsMargins(0, 0, 0, 0)
                # Ensure table respects layout constraints
                self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                # Add spacing before table to ensure header is visible
                table_layout.addSpacing(5)
                table_layout.addWidget(self.table)
                logging.debug("NodesPage: Added virtual table to layout")
            
            # Add table section to main layout (below graphs)
            main_layout.addWidget(table_widget)
            
            # Set proper stretch factors - header is fixed, table is expandable
            if has_graphs:
                # Set stretch factors for all components
                for i in range(main_layout.count()):
                    item = main_layout.itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        if widget == graphs_widget:
                            main_layout.setStretchFactor(widget, 0)  # Graphs: fixed size
                        elif widget == table_header_container:
                            main_layout.setStretchFactor(widget, 0)  # Header: fixed size
                        elif widget == table_widget:
                            main_layout.setStretchFactor(widget, 1)  # Table: expandable
            else:
                # No graphs case - just header and table
                main_layout.setStretchFactor(table_header_container, 0)  # Header: fixed size
                main_layout.setStretchFactor(table_widget, 1)  # Table: expandable
            
            # Configure initial column setup
            if hasattr(self, 'table') and self.table:
                QTimer.singleShot(100, self.configure_columns)
            
            logging.info("NodesPage: Virtual layout setup completed successfully with Node title, count, refresh button and search bar above table")
            
        except Exception as e:
            logging.error(f"NodesPage: Failed to setup virtual layout: {e}")
            logging.debug("NodesPage: Virtual layout setup error details", exc_info=True)
            raise e
    
    def _handle_virtual_table_click(self, index: QModelIndex):
        """Handle clicks on virtual table"""
        if index.isValid():
            row = index.row()
            column = index.column()
            logging.debug(f"NodesPage: Virtual table click - row: {row}, column: {column}")
            
            if column == 9:  # Action column clicked - buttons handle this
                # Action buttons are already in place, no need for context menu
                pass
            else:
                self._select_node_for_graphs_virtual(row)
    
    def _handle_virtual_table_double_click(self, index: QModelIndex):
        """Handle double-clicks on virtual table"""
        if index.isValid():
            node = self.virtual_model.get_node_at_row(index.row())
            if node:
                node_name = node.get('name')
                if node_name:
                    # Show detail page
                    parent = self.parent()
                    while parent and not hasattr(parent, 'detail_manager'):
                        parent = parent.parent()
                    
                    if parent and hasattr(parent, 'detail_manager'):
                        parent.detail_manager.show_detail('node', node_name, None)
    
    def _handle_virtual_row_selection(self, current: QModelIndex, previous: QModelIndex):
        """Handle row selection changes in virtual table"""
        if current.isValid():
            self._select_node_for_graphs_virtual(current.row())
    
    def _select_node_for_graphs_virtual(self, row: int):
        """Select node for graphs using virtual table model"""
        node = self.virtual_model.get_node_at_row(row)
        if node:
            node_name = node.get('name')
            if node_name:
                logging.info(f"NodesPage: Selecting virtual node '{node_name}' for graph display (row {row})")
                
                # Update graphs with node data (if they exist)
                graphs = []
                if hasattr(self, 'cpu_graph') and self.cpu_graph:
                    graphs.append(self.cpu_graph)
                if hasattr(self, 'mem_graph') and self.mem_graph:
                    graphs.append(self.mem_graph)
                if hasattr(self, 'disk_graph') and self.disk_graph:
                    graphs.append(self.disk_graph)
                
                if graphs:
                    # Show graphs
                    for graph in graphs:
                        if not graph.isVisible():
                            graph.show()
                        graph.raise_()
                    
                    # Force immediate update of graph data
                    for graph in graphs:
                        graph._last_update_time = 0
                        graph._is_updating = False
                        graph.generate_utilization_data([node], force_update=True)
                    
                    # Set the selected node
                    if hasattr(self, 'cpu_graph') and self.cpu_graph:
                        self.cpu_graph.set_selected_node(node, node_name)
                    if hasattr(self, 'mem_graph') and self.mem_graph:
                        self.mem_graph.set_selected_node(node, node_name)
                    if hasattr(self, 'disk_graph') and self.disk_graph:
                        self.disk_graph.set_selected_node(node, node_name)
                    
                    # Force immediate repaint
                    for graph in graphs:
                        graph.update()
                        graph.repaint()
                    
                    logging.debug(f"NodesPage: Updated {len(graphs)} graphs for selected node {node_name}")
                else:
                    logging.debug(f"NodesPage: No graphs to update for selected node {node_name}")

    def configure_columns(self):
        """Configure column widths for responsive screen utilization"""
        if not self.table:
            return
            
        # No longer need to hide checkbox column since it's removed
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
            # Use the model's columnCount method instead of table's
            if hasattr(self, 'virtual_model') and self.virtual_model:
                if col_index >= self.virtual_model.columnCount():
                    continue
            else:
                # Fallback for traditional table
                if hasattr(self.table, 'columnCount') and col_index >= self.table.columnCount():
                    continue
                elif not hasattr(self.table, 'columnCount') and col_index >= 11:  # Default column count
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
        """Show no data message - override for virtual table compatibility"""
        if hasattr(self, 'virtual_model') and self.virtual_model:
            # Clear virtual model data 
            self.virtual_model.update_nodes_data([])
            # Show a proper empty message for virtual table
            self._show_virtual_empty_message()
        else:
            # Use base class implementation for traditional table
            self._show_empty_message()
        
    def _show_virtual_empty_message(self):
        """Show empty message for virtual table mode"""
        try:
            from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout
            from PyQt6.QtCore import Qt
            
            # Create or get the empty message widget
            if not hasattr(self, '_empty_message_widget'):
                self._empty_message_widget = QWidget()
                empty_layout = QVBoxLayout(self._empty_message_widget)
                empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_layout.setContentsMargins(20, 20, 20, 20)
                
                # Create title and subtitle like base class
                empty_title = QLabel("No items found")
                empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_title.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold; background-color: transparent; margin: 8px;")
                
                empty_subtitle = QLabel("No results match your search criteria")
                empty_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_subtitle.setStyleSheet("color: #9ca3af; font-size: 14px; background-color: transparent; margin: 4px;")
                
                empty_layout.addWidget(empty_title)
                empty_layout.addWidget(empty_subtitle)
                
                # Style the container
                self._empty_message_widget.setStyleSheet("background-color: transparent;")
            
            # Hide the table and show empty message
            if hasattr(self, 'table') and self.table:
                self.table.hide()
            
            # Add empty message to the table's parent layout
            if hasattr(self, 'table') and self.table and self.table.parent():
                table_parent = self.table.parent()
                table_layout = table_parent.layout()
                if table_layout:
                    # Insert the empty message at the same position as the table
                    table_index = table_layout.indexOf(self.table)
                    if table_index >= 0:
                        table_layout.insertWidget(table_index + 1, self._empty_message_widget)
                        self._empty_message_widget.show()
                        logging.debug("NodesPage: Showing virtual empty message")
        
        except Exception as e:
            logging.error(f"NodesPage: Error showing virtual empty message: {e}")
    
    def show_table(self):
        """Show the table using base class implementation"""
        # Hide empty message if it exists
        if hasattr(self, '_empty_message_widget') and self._empty_message_widget:
            self._empty_message_widget.hide()
            # Remove from layout to prevent duplicate widgets
            if self._empty_message_widget.parent():
                parent_layout = self._empty_message_widget.parent().layout()
                if parent_layout:
                    parent_layout.removeWidget(self._empty_message_widget)
        
        # Show the table
        if hasattr(self, 'table') and self.table:
            self.table.show()
            
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
        logging.debug(f"NodesPage: Received nodes data type: {type(nodes_data)}")
        
        self.is_loading = False
        self.is_showing_skeleton = False
        
        if hasattr(self, 'skeleton_timer') and self.skeleton_timer.isActive():
            self.skeleton_timer.stop()
        
        if not nodes_data:
            logging.warning("NodesPage: No nodes data received - will display empty state")
            self.nodes_data = []
            self.resources = []
            # Clear search state when no data is available
            self._is_searching = False
            self._current_search_query = None
            self.show_no_data_message()
            self.items_count.setText("0 items")
            return
        
        logging.info(f"NodesPage: Processing {len(nodes_data)} nodes for UI display")
        logging.debug(f"NodesPage: Sample node data: {nodes_data[0] if nodes_data else 'No data'}")
        
        # Store the data
        self.nodes_data = nodes_data
        self.resources = nodes_data
        self.has_loaded_data = True
        logging.debug(f"NodesPage: Stored node data - has_loaded_data: {self.has_loaded_data}")
        
        # Update graphs asynchronously to avoid blocking UI
        QTimer.singleShot(10, lambda: self._update_graphs_async(nodes_data))
        
        # Also update graphs immediately if this is the first load
        if not hasattr(self, '_graphs_initialized'):
            self._update_graphs_async(nodes_data)
            self._graphs_initialized = True
        
        # Check if we're in search mode and apply search filter
        if self._is_searching and self._current_search_query:
            logging.debug(f"NodesPage: Applying search filter for query: {self._current_search_query}")
            self._filter_nodes_by_search(self._current_search_query)
        else:
            logging.debug("NodesPage: No search active - showing all nodes")
            self.show_table()
            # Populate table with optimized method
            logging.debug(f"NodesPage: Starting to populate table with {len(nodes_data)} nodes")
            self.populate_table(nodes_data)
            self.items_count.setText(f"{len(nodes_data)} items")
            logging.info(f"NodesPage: Successfully populated table with {len(nodes_data)} nodes and updated items count")
    
    def _update_graphs_async(self, nodes_data):
        """Update graphs asynchronously to avoid blocking UI"""
        logging.debug(f"NodesPage: Updating graphs asynchronously with {len(nodes_data) if nodes_data else 0} nodes")
        try:
            # Only update graphs if they exist
            if hasattr(self, 'cpu_graph') and self.cpu_graph:
                self.cpu_graph.generate_utilization_data(nodes_data)
            if hasattr(self, 'mem_graph') and self.mem_graph:
                self.mem_graph.generate_utilization_data(nodes_data) 
            if hasattr(self, 'disk_graph') and self.disk_graph:
                self.disk_graph.generate_utilization_data(nodes_data)
            
            # Check if any graphs were updated
            graphs_exist = any(hasattr(self, attr) and getattr(self, attr) 
                             for attr in ['cpu_graph', 'mem_graph', 'disk_graph'])
            
            if graphs_exist:
                logging.debug("NodesPage: Successfully updated available graphs with node data")
            else:
                logging.debug("NodesPage: No graphs available to update")
                
        except Exception as e:
            logging.error(f"NodesPage: Error updating graphs: {e}")
            logging.debug(f"NodesPage: Graph update error details", exc_info=True)
    
    def _display_resources(self, resources):
        """Override to use nodes-specific table population"""
        # Always populate the table/model, even with empty resources
        # This ensures the virtual model is properly updated
        if not resources:
            # Update the model with empty data to clear previous results
            self.populate_table([])
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
            # This is less common but we need to handle it (only for QTableWidget)
            if hasattr(self.table, 'rowCount') and hasattr(self.table, 'setRowCount'):
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
            
        except Exception as e:
            logging.error(f"Error in node search filtering: {e}")
            # Fallback to showing all nodes
            self._display_resources(self.nodes_data)
    
    def _clear_search_and_reload(self):
        """Override to clear search and show all nodes"""
        self._is_searching = False
        self._current_search_query = None
        
        # Show all nodes data
        self._display_resources(self.nodes_data)
    
    def _on_search_text_changed(self, text):
        """Override to handle search text changes for nodes"""
        # If search is cleared, show all nodes immediately
        if not text.strip():
            self._clear_search_and_reload()
            return
        
        # Use the parent class debounced search
        super()._on_search_text_changed(text)
    
    # Removed duplicate populate_resource_row methods - using optimized version directly

    def clear_table(self):
        """Override base class clear_table to ensure proper widget cleanup"""
        if not self.table:
            return
            
        # Clear all cell widgets first
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                widget = self.table.cellWidget(row, col)
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
        
        # Clear virtual model data
        if hasattr(self, 'virtual_model') and self.virtual_model:
            self.virtual_model.update_nodes_data([])  # Clear data
        else:
            # Only use QTableWidget methods if we have a QTableWidget
            if hasattr(self.table, 'clearContents'):
                self.table.clearContents()
            if hasattr(self.table, 'setRowCount'):
                self.table.setRowCount(0)

    def populate_table(self, resources_to_populate):
        """Populate table with resource data - supports both traditional and virtual tables"""
        logging.debug(f"NodesPage: populate_table() called with table: {self.table is not None}, resources: {len(resources_to_populate) if resources_to_populate else 0}")
        if not self.table: 
            logging.warning(f"NodesPage: Cannot populate table - table not found")
            return
        
        # Handle empty resources - still need to update the model
        resources_to_use = resources_to_populate or []
        logging.info(f"NodesPage: Starting table population with {len(resources_to_use)} resources")
        
        # Check if using virtual scrolling
        if hasattr(self, 'virtual_model') and self.virtual_model:
            # Use virtual model for heavy data (including empty data)
            logging.info(f"NodesPage: Using virtual model for {len(resources_to_use)} nodes")
            self.virtual_model.update_nodes_data(resources_to_use)
            self._configure_virtual_table_columns()
            # Only add action buttons if there are resources
            if resources_to_use:
                self._add_virtual_action_buttons(resources_to_use)
            return
        
        # Use traditional table widget approach for smaller datasets
        self._populate_traditional_table(resources_to_populate)
    
    def _populate_traditional_table(self, resources_to_populate):
        """Populate traditional QTableWidget - for backward compatibility"""
        logging.debug(f"NodesPage: Using traditional table population for {len(resources_to_populate)} resources")
        
        # Disable all expensive operations during population
        if hasattr(self.table, 'setSortingEnabled'):  # QTableWidget
            self.table.setSortingEnabled(False)
            self.table.setUpdatesEnabled(False)
        
        # Clear and resize table efficiently - also clear all cell widgets
        # First clear all cell widgets explicitly to prevent orphaned widgets
        old_row_count = self.table.rowCount()
        for row in range(old_row_count):
            for col in range(self.table.columnCount()):
                widget = self.table.cellWidget(row, col)
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
        
        # Clear table contents and reset row count (only for QTableWidget)
        if hasattr(self.table, 'clearContents'):
            self.table.clearContents()
        if hasattr(self.table, 'setRowCount'):
            self.table.setRowCount(0)  # Reset to 0 first
            self.table.setRowCount(len(resources_to_populate))  # Then set to new count
        
        # Use batched rendering for better performance with large datasets
        batch_size = self.perf_config.get('table_batch_size', 25)  # Use performance config
        total_items = len(resources_to_populate)
        logging.debug(f"NodesPage: Using batch size {batch_size} for {total_items} total items")
        
        for start_idx in range(0, total_items, batch_size):
            end_idx = min(start_idx + batch_size, total_items)
            batch = resources_to_populate[start_idx:end_idx]
            
            logging.debug(f"NodesPage: Processing batch {start_idx}-{end_idx} ({len(batch)} nodes)")
            # Populate batch
            for i, resource in enumerate(batch):
                actual_row = start_idx + i
                self.populate_resource_row_optimized(actual_row, resource)
            
            # Process events every batch to keep UI responsive
            QApplication.processEvents()
            
        logging.debug(f"NodesPage: Completed all batches for table population")
        
        # Re-enable updates and sorting
        if hasattr(self.table, 'setUpdatesEnabled'):  # QTableWidget
            self.table.setUpdatesEnabled(True)
            self.table.setSortingEnabled(True)
            logging.debug("NodesPage: Re-enabled table updates and sorting")
        
        # Force a proper repaint and update
        self.table.viewport().update()
        self.table.update()
        logging.debug("NodesPage: Triggered table repaint and update")
        
        # Process any pending events to ensure widgets are properly displayed
        QApplication.processEvents()
        logging.info(f"NodesPage: Traditional table population completed successfully - {len(resources_to_populate)} nodes displayed")
    
    def _configure_virtual_table_columns(self):
        """Configure columns for virtual table"""
        if not hasattr(self, 'table') or not self.table:
            return
            
        header = self.table.horizontalHeader()
        available_width = self.table.viewport().width() - 20
        
        if available_width <= 0:
            # Defer column setup until table is properly sized
            QTimer.singleShot(100, self._configure_virtual_table_columns)
            return
        
        # Column configuration (same as traditional table)
        column_config = [
            (0, 140, 100, "priority"), # Name (no more checkbox column)
            (1, 110, 80, "normal"),    # CPU
            (2, 110, 80, "normal"),    # Memory
            (3, 110, 80, "normal"),    # Disk
            (4, 60, 50, "compact"),    # Taints
            (5, 120, 80, "normal"),    # Roles
            (6, 90, 60, "compact"),    # Version
            (7, 60, 50, "compact"),    # Age
            (8, 90, 70, "stretch"),    # Conditions
            (9, 60, 60, "fixed")       # Actions
        ]
        
        # No columns need to be hidden - checkbox column removed, action column is visible
        
        # Apply column configuration
        for col_index, default_width, min_width, col_type in column_config:
            if col_index >= self.table.model().columnCount():
                continue
                
            if col_type == "fixed":
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col_index, min_width)
            elif col_type == "stretch":
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Interactive)
                self.table.setColumnWidth(col_index, max(default_width, min_width))
        
        logging.debug("NodesPage: Virtual table columns configured")

    def populate_resource_row_optimized(self, row, resource):
        """Highly optimized row population - minimizes widget creation"""
        self.table.setRowHeight(row, 40)
        
        node_name = resource.get("name", "unknown")
        logging.debug(f"NodesPage: Populating row {row} with node: {node_name}")
        
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
        logging.debug(f"NodesPage: Completed populating row {row} for node {node_name}")
    
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
        disk_capacity = resource.get("disk_capacity", "")
        if disk_usage is not None and disk_capacity:
            display_disk = f"{disk_capacity} ({disk_usage:.1f}%)"
            disk_util = disk_usage
        elif disk_capacity:
            display_disk = f"{disk_capacity}"
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
        
        # Action button goes in column 9 (last column)
        action_col = 9
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
        """Highlight the row when its menu is active (virtual table compatible)"""
        try:
            # For QTableView (virtual table), we use selection to highlight the row
            if hasattr(self, 'table') and self.table and hasattr(self, 'virtual_model'):
                if is_active:
                    # Select the row to highlight it
                    self.table.selectRow(row)
                    logging.debug(f"NodesPage: Highlighted virtual table row {row}")
                else:
                    # Clear selection when menu closes
                    self.table.clearSelection()
                    logging.debug(f"NodesPage: Cleared virtual table row {row} highlight")
            else:
                # Fallback for traditional table (QTableWidget)
                if hasattr(self, 'table') and hasattr(self.table, 'columnCount'):
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        if item:
                            if is_active:
                                item.setBackground(QColor(AppColors.ACCENT_BLUE + "22"))  # 13% opacity
                            else:
                                item.setBackground(QColor("transparent"))
        except Exception as e:
            logging.error(f"NodesPage: Error highlighting row {row}: {e}")

    # Removed _create_node_action_button - now uses base class _create_action_button
    
    # Removed custom _handle_action - now uses base class implementation with nodes support
    
    # Removed _handle_node_action - now uses base class _handle_action
    
    def select_node_for_graphs(self, row):
        """Select a node to show in the graphs"""
        logging.debug(f"NodesPage: select_node_for_graphs() called with row: {row}")
        
        if row < 0 or not hasattr(self, 'nodes_data') or row >= len(self.nodes_data):
            logging.warning(f"NodesPage: Invalid row selection - row: {row}, nodes_data available: {hasattr(self, 'nodes_data')}, nodes count: {len(self.nodes_data) if hasattr(self, 'nodes_data') else 0}")
            return
            
        self.selected_row = row
        node_name = self.table.item(row, 1).text() if self.table.item(row, 1) else None
        if not node_name:
            logging.warning(f"NodesPage: No node name found in table row {row}")
            return
            
        logging.info(f"NodesPage: Selecting node '{node_name}' for graph display (row {row})")
        node_data = None
        
        # Find the node data
        for node in self.nodes_data:
            if node.get("name") == node_name:
                node_data = node
                break
                
        if not node_data:
            logging.warning(f"NodesPage: Node data not found for {node_name} in nodes_data array")
            return
        
        logging.debug(f"NodesPage: Found node data for {node_name}: {node_data}")
            
        self.table.selectRow(row)
        
        # Ensure graphs are properly initialized and visible
        for graph in [self.cpu_graph, self.mem_graph, self.disk_graph]:
            if not graph.isVisible():
                graph.show()
            graph.raise_()  # Bring graph to front
        
        # Force immediate update of graph data with no throttling
        for graph in [self.cpu_graph, self.mem_graph, self.disk_graph]:
            # Bypass all throttling for immediate display
            graph._last_update_time = 0
            graph._is_updating = False
            # Force utilization data update
            graph.generate_utilization_data(self.nodes_data, force_update=True)
        
        # Set the selected node with immediate updates
        self.cpu_graph.set_selected_node(node_data, node_name)
        self.mem_graph.set_selected_node(node_data, node_name)  
        self.disk_graph.set_selected_node(node_data, node_name)
        
        # Force immediate repaint of all graphs
        for graph in [self.cpu_graph, self.mem_graph, self.disk_graph]:
            graph.update()
            graph.repaint()
        
        # Log for debugging
        logging.info(f"NodesPage: Successfully selected node '{node_name}' for graphs")
        logging.debug(f"NodesPage: CPU utilization data for {node_name}: {self.cpu_graph.utilization_data.get(node_name, 'Not found')}")
        logging.debug(f"NodesPage: Memory utilization data for {node_name}: {self.mem_graph.utilization_data.get(node_name, 'Not found')}")
        logging.debug(f"NodesPage: Disk utilization data for {node_name}: {self.disk_graph.utilization_data.get(node_name, 'Not found')}")
    
    def handle_row_click(self, row, column):
        logging.debug(f"NodesPage: Row click - row: {row}, column: {column}")
        if column != self.table.columnCount() - 1:  # Skip action column
            self.table.selectRow(row)
            logging.debug(f"NodesPage: Selected table row {row}, triggering graph update")
            # Use QTimer.singleShot to ensure immediate graph display
            QTimer.singleShot(0, lambda: self.select_node_for_graphs(row))
    
    def handle_row_double_click(self, row, column):
        """Handle double-click to show node detail page"""
        if column != self.table.columnCount() - 1:  # Skip action column
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
            logging.debug("NodesPage: Already loading data, skipping duplicate request")
            return
            
        self.is_loading = True
        logging.debug("NodesPage: Set is_loading=True, starting data fetch process")
        
        if hasattr(self, 'cluster_connector') and self.cluster_connector:
            logging.info("NodesPage: Using cluster_connector to load nodes data")
            self.cluster_connector.load_nodes()
            logging.debug("NodesPage: load_nodes() call completed, waiting for data")
        else:
            logging.warning("NodesPage: No cluster_connector available - cannot load nodes")
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
        refresh_btn.setMinimumHeight(24)  # Height adjusted for proper visibility
        refresh_btn.setFixedHeight(24)
        refresh_style = getattr(AppStyles, "SECONDARY_BUTTON_STYLE",
                                """QPushButton { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3d3d3d;
                                               border-radius: 4px; padding: 4px 8px; font-weight: bold; }
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