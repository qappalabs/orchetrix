"""
NodesPage - Kubernetes Nodes Management Interface

This module provides a high-performance nodes page for the OrchestrixGUI Kubernetes management application.
Key features:
- Virtual table scrolling for handling large numbers of nodes
- Progressive loading with real-time metrics calculation 
- Asynchronous CPU, Memory, and Disk metrics computation
- Real-time graph visualization for selected nodes
- No dummy/fallback data - only displays real Kubernetes metrics

Architecture:
- Uses QTableView with custom NodesTableModel for virtual scrolling
- NodeMetricsWorker handles asynchronous metrics calculation per node
- GraphWidget provides real-time usage visualization
- Integrates with cluster_connector for live data updates
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QHeaderView, QFrame, 
    QGraphicsDropShadowEffect, QSizePolicy, QStyle, QStyleOptionHeader,
    QProxyStyle, QTableView, QAbstractItemView, QStyledItemDelegate
)
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal, QAbstractTableModel, QModelIndex, QThreadPool, QRunnable, QObject, pyqtSlot
from PyQt6.QtGui import QColor, QPainter, QPen, QFont

from UI.Styles import AppStyles, AppColors
from Base_Components.base_resource_page import BaseResourcePage
from Utils.cluster_connector import get_cluster_connector
from Utils.debounced_updater import get_debounced_updater
from Utils.performance_config import get_performance_config
import datetime
import logging
import time

# ====================================================================
# ASYNC WORKER CLASSES - Node Metrics Calculation
# ====================================================================
class NodeMetricsWorkerSignals(QObject):
    """Signals for the node metrics worker"""
    finished = pyqtSignal(str, str, dict)  # node_name, metric_type, result
    error = pyqtSignal(str, str, str)  # node_name, metric_type, error_msg

class NodeMetricsWorker(QRunnable):
    """Worker to calculate metrics for a single node asynchronously"""
    
    def __init__(self, node_name: str, node_data: dict, metric_type: str):
        super().__init__()
        self.node_name = node_name
        self.node_data = node_data
        self.metric_type = metric_type
        self.signals = NodeMetricsWorkerSignals()
    
    def run(self):
        """Calculate the metric and emit result"""
        logging.info(f"NodeMetricsWorker: Starting {self.metric_type} calculation for {self.node_name}")
        try:
            if self.metric_type == 'cpu':
                result = self._calculate_cpu_metrics()
            elif self.metric_type == 'memory':
                result = self._calculate_memory_metrics()
            elif self.metric_type == 'disk':
                result = self._calculate_disk_metrics()
            else:
                result = {'usage': None, 'capacity': 'N/A'}
            
            logging.info(f"NodeMetricsWorker: Completed {self.metric_type} calculation for {self.node_name}: {result}")
            self.signals.finished.emit(self.node_name, self.metric_type, result)
            
        except Exception as e:
            error_msg = f"Error calculating {self.metric_type} for {self.node_name}: {str(e)}"
            logging.error(error_msg)
            self.signals.error.emit(self.node_name, self.metric_type, error_msg)
    
    def _calculate_cpu_metrics(self):
        """Calculate CPU metrics for the node"""
        try:
            # Use the already processed node data that has cpu_capacity and cpu_usage
            cpu_capacity = self.node_data.get('cpu_capacity', '')
            cpu_usage = self.node_data.get('cpu_usage', None)
            
            logging.info(f"CPU metrics - capacity: {cpu_capacity}, usage: {cpu_usage}")
            
            # Parse CPU capacity to get readable format
            if cpu_capacity:
                cpu_cores = self._parse_cpu_value(cpu_capacity)
                if cpu_cores > 0:
                    capacity_str = f"{cpu_cores} cores"
                else:
                    capacity_str = str(cpu_capacity)
            else:
                capacity_str = 'N/A'
            
            return {
                'usage': cpu_usage,
                'capacity': capacity_str
            }
                
        except Exception as e:
            logging.error(f"Error calculating CPU metrics: {e}")
            return {'usage': None, 'capacity': ''}
    
    def _calculate_memory_metrics(self):
        """Calculate Memory metrics for the node"""
        try:
            # Use the already processed node data that has memory_capacity and memory_usage
            memory_capacity = self.node_data.get('memory_capacity', '')
            memory_usage = self.node_data.get('memory_usage', None)
            
            logging.info(f"Memory metrics - capacity: {memory_capacity}, usage: {memory_usage}")
            
            # Use the capacity directly (it's already formatted)
            capacity_str = memory_capacity if memory_capacity else ''
            
            return {
                'usage': memory_usage,
                'capacity': capacity_str
            }
                
        except Exception as e:
            logging.error(f"Error calculating memory metrics: {e}")
            return {'usage': None, 'capacity': ''}
    
    def _calculate_disk_metrics(self):
        """Calculate Disk metrics for the node"""
        try:
            # Use the already processed node data that has disk_capacity and disk_usage
            disk_capacity = self.node_data.get('disk_capacity', '')
            disk_usage = self.node_data.get('disk_usage', None)
            
            logging.info(f"Disk metrics - capacity: {disk_capacity}, usage: {disk_usage}")
            
            # Use the capacity directly (it's already formatted)
            capacity_str = disk_capacity if disk_capacity else ''
            
            return {
                'usage': disk_usage,
                'capacity': capacity_str
            }
                
        except Exception as e:
            logging.error(f"Error calculating disk metrics: {e}")
            return {'usage': None, 'capacity': ''}
    
    def _parse_cpu_value(self, cpu_str):
        """Parse CPU string to numeric value"""
        try:
            if not cpu_str:
                return 0
            cpu_str = str(cpu_str).lower()
            if 'm' in cpu_str:
                # Handle millicores (e.g., "2000m" = 2 cores)
                return int(cpu_str.replace('m', '')) / 1000
            else:
                return float(cpu_str)
        except:
            return 0
    
    def _format_memory_value(self, memory_str):
        """Format memory/storage value to readable format"""
        try:
            if not memory_str:
                return 'N/A'
            
            memory_str = str(memory_str).upper()
            
            # Handle different units
            if 'KI' in memory_str:
                value = int(memory_str.replace('KI', ''))
                return f"{value / 1024 / 1024:.1f} GiB" if value > 1024*1024 else f"{value / 1024:.1f} MiB"
            elif 'MI' in memory_str:
                value = int(memory_str.replace('MI', ''))
                return f"{value / 1024:.1f} GiB" if value > 1024 else f"{value} MiB"
            elif 'GI' in memory_str:
                value = int(memory_str.replace('GI', ''))
                return f"{value} GiB"
            elif 'K' in memory_str:
                value = int(memory_str.replace('K', ''))
                return f"{value / 1024 / 1024:.1f} GiB" if value > 1024*1024 else f"{value / 1024:.1f} MiB"
            elif 'M' in memory_str:
                value = int(memory_str.replace('M', ''))
                return f"{value / 1024:.1f} GiB" if value > 1024 else f"{value} MiB"
            elif 'G' in memory_str:
                value = int(memory_str.replace('G', ''))
                return f"{value} GiB"
            else:
                # Assume bytes
                value = int(memory_str)
                if value > 1024*1024*1024:
                    return f"{value / 1024 / 1024 / 1024:.1f} GiB"
                elif value > 1024*1024:
                    return f"{value / 1024 / 1024:.1f} MiB"
                else:
                    return f"{value / 1024:.1f} KiB"
                    
        except:
            return str(memory_str) if memory_str else 'N/A'

# ====================================================================
# BATCH WORKER CLASSES - Optimized batch processing
# ====================================================================

class NodeBatchMetricsWorkerSignals(QObject):
    """Signals for batch node metrics worker"""
    batch_finished = pyqtSignal(str, dict)  # metric_type, {node_name: result}
    batch_error = pyqtSignal(str, str)  # metric_type, error_msg

class NodeBatchMetricsWorker(QRunnable):
    """Worker to calculate metrics for multiple nodes in batch for better performance"""
    
    def __init__(self, batch_nodes: list, metric_type: str):
        super().__init__()
        self.batch_nodes = batch_nodes  # List of (node_name, node_data) tuples
        self.metric_type = metric_type
        self.signals = NodeBatchMetricsWorkerSignals()
    
    def run(self):
        """Calculate the metric for all nodes in the batch"""
        logging.info(f"NodeBatchMetricsWorker: Starting {self.metric_type} calculation for {len(self.batch_nodes)} nodes")
        batch_results = {}
        
        try:
            for node_name, node_data in self.batch_nodes:
                try:
                    if self.metric_type == 'cpu':
                        result = self._calculate_cpu_metrics(node_data)
                    elif self.metric_type == 'memory':
                        result = self._calculate_memory_metrics(node_data)
                    elif self.metric_type == 'disk':
                        result = self._calculate_disk_metrics(node_data)
                    else:
                        result = {'usage': None, 'capacity': 'N/A'}
                    
                    batch_results[node_name] = result
                    
                except Exception as e:
                    logging.error(f"Error calculating {self.metric_type} for {node_name}: {e}")
                    batch_results[node_name] = {'usage': None, 'capacity': 'Error'}
            
            logging.info(f"NodeBatchMetricsWorker: Completed {self.metric_type} calculation for {len(batch_results)} nodes")
            self.signals.batch_finished.emit(self.metric_type, batch_results)
            
        except Exception as e:
            error_msg = f"Batch calculation error for {self.metric_type}: {str(e)}"
            logging.error(error_msg)
            self.signals.batch_error.emit(self.metric_type, error_msg)
    
    def _calculate_cpu_metrics(self, node_data):
        """Calculate CPU metrics for a single node"""
        try:
            cpu_capacity = node_data.get('cpu_capacity', '')
            cpu_usage = node_data.get('cpu_usage', None)
            
            if cpu_capacity:
                cpu_cores = self._parse_cpu_value(cpu_capacity)
                capacity_str = f"{cpu_cores} cores" if cpu_cores > 0 else str(cpu_capacity)
            else:
                capacity_str = 'N/A'
            
            return {'usage': cpu_usage, 'capacity': capacity_str}
        except Exception as e:
            logging.error(f"Error calculating CPU metrics: {e}")
            return {'usage': None, 'capacity': ''}
    
    def _calculate_memory_metrics(self, node_data):
        """Calculate Memory metrics for a single node"""
        try:
            memory_capacity = node_data.get('memory_capacity', '')
            memory_usage = node_data.get('memory_usage', None)
            capacity_str = memory_capacity if memory_capacity else ''
            return {'usage': memory_usage, 'capacity': capacity_str}
        except Exception as e:
            logging.error(f"Error calculating memory metrics: {e}")
            return {'usage': None, 'capacity': ''}
    
    def _calculate_disk_metrics(self, node_data):
        """Calculate Disk metrics for a single node"""
        try:
            disk_capacity = node_data.get('disk_capacity', '')
            disk_usage = node_data.get('disk_usage', None)
            capacity_str = disk_capacity if disk_capacity else ''
            return {'usage': disk_usage, 'capacity': capacity_str}
        except Exception as e:
            logging.error(f"Error calculating disk metrics: {e}")
            return {'usage': None, 'capacity': ''}
    
    def _parse_cpu_value(self, cpu_str):
        """Parse CPU string to numeric value"""
        try:
            if not cpu_str:
                return 0
            cpu_str = str(cpu_str).lower()
            if 'm' in cpu_str:
                return float(cpu_str.replace('m', '')) / 1000.0
            else:
                return float(cpu_str)
        except (ValueError, AttributeError):
            return 0

# ====================================================================
# UI STYLE CLASSES - Custom Header and Cell Styling
# ====================================================================
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
                    text_color = QColor("#FFFFFF")  # Default white for other statuses
                
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
        self._update_interval = 30.0  # 30 seconds to reduce load
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
        self.timer.start(30000)  # 30 seconds to reduce CPU load

    def generate_utilization_data(self, nodes_data, force_update=False):
        """Generate utilization data for nodes - optimized for performance"""
        if not nodes_data or self._is_updating:
            return
            
        current_time = time.time()
        # Only throttle if we have data, enough time hasn't passed, and not forced
        if (not force_update and self.utilization_data and 
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
            else:
                logging.warning(f"GraphWidget ({self.title}): No utilization data found for metric_key: {metric_key}")
                
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
        
        if node_name in self.utilization_data:
            self.current_value = round(self.utilization_data[node_name], 1)
            self.value_label.setText(f"{self.current_value}{self.unit}")
            logging.info(f"GraphWidget ({self.title}): Set value for {node_name}: {self.current_value}{self.unit}")
        else:
            logging.warning(f"GraphWidget ({self.title}): No utilization data found for {node_name} - available nodes: {list(self.utilization_data.keys())}")
            
        # Update data without forcing immediate repaint to reduce load
        self.update_data()

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
            # Only trigger visual update if widget is visible to reduce painting overhead
            if self.isVisible():
                self.update()

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
        
        # No placeholder text - graph only shows data when real node is selected

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
    
    # Signal emitted when data count changes
    data_count_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._nodes_data = []
        self._headers = ["Name", "CPU", "Memory", "Disk", "Taints", "Roles", "Version", "Age", "Conditions", "Actions"]
        self._performance_cache = {}
        self._calculation_status = {}  # Track which nodes have completed calculations
        
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
            name = node.get("name")
            return name if name else None
        elif col == 1:  # CPU
            node_name = node.get("name", "")
            cpu_usage = node.get("cpu_usage")
            cpu_capacity = node.get("cpu_capacity", "")
            
            # Add debug logging to understand data flow
            logging.debug(f"NodesPage: CPU data for {node_name}: usage={cpu_usage}, capacity='{cpu_capacity}'")
            
            # If unified loader provided complete data, use it directly 
            if cpu_usage is not None and cpu_capacity:
                return f"{cpu_capacity} ({cpu_usage:.1f}%)"
            elif cpu_capacity:  # Has capacity but no usage yet
                # Show loading indicator for nodes that have capacity but no usage data yet
                logging.debug(f"NodesPage: Showing loading indicator for {node_name} CPU (has capacity, waiting for usage)")
                return f"{cpu_capacity} (⏳)"
            
            # Check if async calculations are complete
            cpu_complete = self._calculation_status.get(node_name, {}).get('cpu_complete', False)
            if cpu_complete:
                # Calculation completed but no data - show empty
                return ""
            else:
                # Show loading indicator while calculations are pending
                logging.debug(f"NodesPage: Showing loading indicator for {node_name} CPU (waiting for calculations)")
                return "⏳"  # Loading indicator
        elif col == 2:  # Memory 
            node_name = node.get("name", "")
            memory_usage = node.get("memory_usage")
            memory_capacity = node.get("memory_capacity", "")
            
            # If unified loader provided complete data, use it directly
            if memory_usage is not None and memory_capacity:
                return f"{memory_capacity} ({memory_usage:.1f}%)"
            elif memory_capacity:  # Has capacity but no usage yet
                return f"{memory_capacity} (⏳)"
            
            # Check if async calculations are complete
            memory_complete = self._calculation_status.get(node_name, {}).get('memory_complete', False)
            if memory_complete:
                # Calculation completed but no data - show empty
                return ""
            else:
                logging.debug(f"NodesPage: Showing loading indicator for {node_name} Memory")
                return "⏳"  # Loading indicator
        elif col == 3:  # Disk
            node_name = node.get("name", "")
            disk_usage = node.get("disk_usage")
            disk_capacity = node.get("disk_capacity", "")
            
            # If unified loader provided complete data, use it directly
            if disk_usage is not None and disk_capacity:
                return f"{disk_capacity} ({disk_usage:.1f}%)"
            elif disk_capacity:  # Has capacity but no usage yet
                return f"{disk_capacity} (⏳)"
            
            # Check if async calculations are complete
            disk_complete = self._calculation_status.get(node_name, {}).get('disk_complete', False)
            if disk_complete:
                # Calculation completed but no data - show empty
                return ""
            else:
                logging.debug(f"NodesPage: Showing loading indicator for {node_name} Disk")
                return "⏳"  # Loading indicator
        elif col == 4:  # Taints (was col 5)
            return str(node.get("taints", "0"))
        elif col == 5:  # Roles (was col 6)
            roles = node.get("roles", [])
            return ", ".join(roles) if isinstance(roles, list) else str(roles)
        elif col == 6:  # Version (was col 7)
            version = node.get("version")
            return version if version else None
        elif col == 7:  # Age (was col 8)
            age = node.get("age")
            return age if age else None
        elif col == 8:  # Conditions (was col 9)
            status = node.get("status")
            return status if status else None
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
            status_value = node.get("status")
            if not status_value:
                return ""  # Skip nodes without status
            status = status_value.lower()
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
        self.reset_calculation_status()  # Reset calculation status for new data
        self.endResetModel()
        
        # Emit signal to update item count display
        self.data_count_changed.emit(len(self._nodes_data))
        
        # Start async calculations immediately after model reset
        if self._nodes_data:
            logging.info(f"CALLING _start_async_calculations() for {len(self._nodes_data)} nodes")
            # Use immediate timer (0ms) to start calculations right after UI update
            if hasattr(self.parent(), 'safe_timer_call'):
                self.parent().safe_timer_call(0, self._start_async_calculations)
            else:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, self._start_async_calculations)
        else:
            logging.info("No nodes data provided, skipping async calculations")
        
        logging.info(f"NodesTableModel: Updated with {len(self._nodes_data)} nodes")
    
    def _start_async_calculations(self):
        """Start optimized batch async calculations for nodes that need them"""
        # Prevent duplicate calculations
        if hasattr(self, '_calculations_running') and self._calculations_running:
            logging.info("NodesPage: Calculations already running, skipping duplicate request")
            return
        
        if not self._nodes_data:
            logging.info("No nodes data available for calculations")
            return
            
        if not hasattr(self, 'threadpool'):
            self.threadpool = QThreadPool()
            self.threadpool.setMaxThreadCount(3)  # Allow 3 concurrent workers (CPU, Memory, Disk)
        
        self._calculations_running = True
        
        # Filter out nodes that already have complete unified data
        nodes_needing_calculation = []
        for node in self._nodes_data:
            node_name = node.get("name", "")
            has_cpu = node.get("cpu_usage") is not None and node.get("cpu_capacity")
            has_memory = node.get("memory_usage") is not None and node.get("memory_capacity")  
            has_disk = node.get("disk_usage") is not None and node.get("disk_capacity")
            
            if not (has_cpu and has_memory and has_disk):
                nodes_needing_calculation.append(node)
            else:
                # Mark as complete since unified data is available
                if node_name not in self._calculation_status:
                    self._calculation_status[node_name] = {}
                self._calculation_status[node_name]['cpu_complete'] = has_cpu
                self._calculation_status[node_name]['memory_complete'] = has_memory
                self._calculation_status[node_name]['disk_complete'] = has_disk
        
        node_count = len(nodes_needing_calculation)
        total_nodes = len(self._nodes_data)
        
        if node_count == 0:
            logging.info(f"All {total_nodes} nodes have unified data - skipping calculations")
            self._calculations_running = False
            return
            
        # Determine optimal batch size based on node count
        if node_count <= 10:
            batch_size = node_count  # Process all at once for small counts
            delay = 0
        elif node_count <= 50:
            batch_size = 15  # Medium batches
            delay = 25
        else:
            batch_size = 25  # Large batches for heavy loads
            delay = 50
        
        # Process in optimized batches using filtered nodes
        batch_count = 0
        for batch_start in range(0, node_count, batch_size):
            batch_end = min(batch_start + batch_size, node_count)
            batch_nodes = []
            
            # Collect nodes for this batch from filtered list
            for i in range(batch_start, batch_end):
                if i < len(nodes_needing_calculation):
                    node = nodes_needing_calculation[i]
                    node_name = node.get('name')
                    if node_name:
                        batch_nodes.append((node_name, node))
            
            # Schedule batch processing with minimal delay using safe timer
            batch_delay = batch_count * delay
            if hasattr(self.parent(), 'safe_timer_call'):
                self.parent().safe_timer_call(batch_delay, lambda nodes=batch_nodes: self._process_batch_async(nodes))
            else:
                # Fallback to regular QTimer
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(batch_delay, lambda nodes=batch_nodes: self._process_batch_async(nodes))
            batch_count += 1
        
        # Reset calculation flag after estimated completion time
        total_batches = (node_count + batch_size - 1) // batch_size  # Ceiling division
        estimated_completion_time = (total_batches * delay) + 2000  # Add 2 second buffer
        if hasattr(self.parent(), 'safe_timer_call'):
            self.parent().safe_timer_call(estimated_completion_time, lambda: setattr(self, '_calculations_running', False))
        else:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(estimated_completion_time, lambda: setattr(self, '_calculations_running', False))
    
    def _process_batch_async(self, batch_nodes):
        """Process a batch of nodes using optimized batch workers"""
        if not batch_nodes:
            return
            
        logging.info(f"Processing batch of {len(batch_nodes)} nodes with batch workers")
        
        # Create one worker per metric type for the entire batch
        for metric_type in ['cpu', 'memory', 'disk']:
            batch_worker = NodeBatchMetricsWorker(batch_nodes, metric_type)
            batch_worker.signals.batch_finished.connect(self._on_batch_metrics_calculated)
            batch_worker.signals.batch_error.connect(self._on_batch_metrics_error)
            if hasattr(self, 'threadpool'):
                self.threadpool.start(batch_worker)
    
    
    
    def _on_metric_calculated(self, node_name: str, metric_type: str, result: dict):
        """Handle completed metric calculation"""
        logging.info(f"Received {metric_type} calculation result for {node_name}: {result}")
        try:
            # Update the node data with calculated values
            for node in self._nodes_data:
                if node.get('name') == node_name:
                    if metric_type == 'cpu':
                        node.update({
                            'cpu_usage': result.get('usage'),
                            'cpu_capacity': result.get('capacity')
                        })
                    elif metric_type == 'memory':
                        node.update({
                            'memory_usage': result.get('usage'),
                            'memory_capacity': result.get('capacity')
                        })
                    elif metric_type == 'disk':
                        node.update({
                            'disk_usage': result.get('usage'),
                            'disk_capacity': result.get('capacity')
                        })
                    break
            
            # Mark calculation as complete and trigger UI update
            self.mark_calculation_complete(node_name, metric_type)
            logging.info(f"Marked {metric_type} calculation complete for {node_name} and updated UI")
            
        except Exception as e:
            logging.error(f"Error processing calculated metric {metric_type} for {node_name}: {e}")
    
    def get_node_at_row(self, row: int):
        """Get node data at specific row"""
        if 0 <= row < len(self._nodes_data):
            return self._nodes_data[row]
        return None
    
    def _on_batch_metrics_calculated(self, metric_type: str, batch_results: dict):
        """Handle batch metric calculation completion - optimized bulk updates"""
        logging.info(f"Received batch {metric_type} results for {len(batch_results)} nodes")
        
        # Update affected rows in bulk for better performance
        updated_rows = set()
        
        try:
            for node_name, result in batch_results.items():
                # Update node data
                for node in self._nodes_data:
                    if node.get('name') == node_name:
                        if metric_type == 'cpu':
                            node.update({
                                'cpu_usage': result.get('usage'),
                                'cpu_capacity': result.get('capacity')
                            })
                        elif metric_type == 'memory':
                            node.update({
                                'memory_usage': result.get('usage'),
                                'memory_capacity': result.get('capacity')
                            })
                        elif metric_type == 'disk':
                            node.update({
                                'disk_usage': result.get('usage'),
                                'disk_capacity': result.get('capacity')
                            })
                        
                        # Mark calculation as complete
                        if node_name not in self._calculation_status:
                            self._calculation_status[node_name] = {}
                        self._calculation_status[node_name][f'{metric_type}_complete'] = True
                        
                        # Track updated row
                        for row, n in enumerate(self._nodes_data):
                            if n.get('name') == node_name:
                                updated_rows.add(row)
                                break
                        break
            
            # Emit optimized bulk dataChanged signals
            if updated_rows:
                col = 1 if metric_type == 'cpu' else 2 if metric_type == 'memory' else 3
                sorted_rows = sorted(updated_rows)
                
                # Group consecutive rows for efficient updates
                if len(sorted_rows) > 1:
                    # Emit range signals for consecutive rows
                    start_row = sorted_rows[0]
                    end_row = sorted_rows[0]
                    
                    for row in sorted_rows[1:]:
                        if row == end_row + 1:
                            end_row = row
                        else:
                            # Emit for previous range
                            top_left = self.createIndex(start_row, col)
                            bottom_right = self.createIndex(end_row, col)
                            self.dataChanged.emit(top_left, bottom_right)
                            start_row = end_row = row
                    
                    # Emit for final range
                    top_left = self.createIndex(start_row, col)
                    bottom_right = self.createIndex(end_row, col)
                    self.dataChanged.emit(top_left, bottom_right)
                else:
                    # Single row update
                    row = sorted_rows[0]
                    index = self.createIndex(row, col)
                    self.dataChanged.emit(index, index)
                
                logging.info(f"Updated {len(updated_rows)} rows for {metric_type} metrics")
            
        except Exception as e:
            logging.error(f"Error processing batch {metric_type} results: {e}")
    
    def _on_batch_metrics_error(self, metric_type: str, error_msg: str):
        """Handle batch metric calculation error"""
        logging.error(f"Batch metrics error for {metric_type}: {error_msg}")
    
    def mark_calculation_complete(self, node_name: str, metric_type: str):
        """Mark a metric calculation as complete for a node (legacy method)"""
        if node_name not in self._calculation_status:
            self._calculation_status[node_name] = {}
        self._calculation_status[node_name][f'{metric_type}_complete'] = True
        
        # Find row index and emit dataChanged for the specific cell
        for row, node in enumerate(self._nodes_data):
            if node.get('name') == node_name:
                # Determine column based on metric type
                col = 1 if metric_type == 'cpu' else 2 if metric_type == 'memory' else 3
                index = self.createIndex(row, col)
                self.dataChanged.emit(index, index)
                break
    
    def reset_calculation_status(self):
        """Reset all calculation statuses when new data is loaded"""
        self._calculation_status.clear()
        
        # Don't clear unified loader data - we want to use it when available
        # Loading indicators will show for nodes without unified data
    
    def cleanup_calculations(self):
        """Cleanup calculation resources"""
        try:
            if hasattr(self, 'threadpool'):
                self.threadpool.waitForDone(1000)  # Wait max 1 second for completion
                self.threadpool.clear()
        except Exception as e:
            logging.error(f"Error during calculation cleanup: {e}")

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
        
        # Pagination properties
        self.page_size = 25  # Load 25 nodes at a time for better performance
        self.current_page = 0
        self.total_nodes = 0
        self.has_more_data = True
        
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
                
                # Load initial data with delay to ensure UI is properly set up
                QTimer.singleShot(300, self._initial_load_data)
                
                logging.info("NodesPage: Virtual table and graphs created successfully")
            except Exception as e:
                logging.error(f"NodesPage: Virtual scrolling setup failed: {e}")
                self.use_virtual_scrolling = False
        
        if not self.use_virtual_scrolling:
            # Virtual scrolling failed - NodesPage only supports virtual tables
            raise Exception("NodesPage requires virtual scrolling - traditional table fallback removed")
    
    def _add_filter_controls(self, header_layout):
        """Override to add search bar above table instead of in header"""
        # Virtual scrolling only - no traditional mode
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
            
            # Connect model signals to update item count
            self.virtual_model.data_count_changed.connect(self._update_item_count_display)
            
            # Create QTableView for virtual scrolling
            self.table = QTableView(self)
            self.table.setModel(self.virtual_model)
            
            # Connect scroll bar to load more data automatically
            scroll_bar = self.table.verticalScrollBar()
            scroll_bar.valueChanged.connect(self._on_scroll)
        
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
            # Clean up partial state and fail - no fallback
            if hasattr(self, 'virtual_model'):
                delattr(self, 'virtual_model')
            if hasattr(self, 'table'):
                delattr(self, 'table')
            # No fallback - virtual table is required
            self.use_virtual_scrolling = False
            raise Exception(f"NodesPage virtual table setup failed: {e}")
    
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
            # Graphs will only be created if real node data with metrics is available
    
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
            from UI.Styles import AppColors, AppStyles
            
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
                
                {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
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
            
        except Exception as e:
            logging.error(f"NodesPage: Error filtering nodes: {e}")
    
    def _clear_search_and_reload(self):
        """Clear search and reload normal resources"""
        self._is_searching = False
        self._current_search_query = None
        
        if hasattr(self, 'nodes_data') and self.nodes_data:
            # Reload full data
            self.populate_table(self.nodes_data)
    
    
    def _handle_action(self, action, row):
        """Handle actions for virtual table only"""
        logging.info(f"NodesPage: Action '{action}' clicked on row {row}")
        
        # NodesPage only supports virtual table
        if hasattr(self, 'virtual_model') and self.virtual_model:
            return self._handle_virtual_table_action(action, row)
        else:
            raise Exception("NodesPage action handling requires virtual table")
    
    def _handle_virtual_table_action(self, action, row):
        """Handle action button clicks in virtual table using standard BaseResourcePage pattern"""
        try:
            node = self.virtual_model.get_node_at_row(row)
            if not node:
                logging.warning(f"NodesPage: No node found at row {row}")
                return
                
            node_name = node.get('name')
            if not node_name:
                return  # Skip nodes without names
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
                # Configure columns immediately for proper initial visibility
                self.configure_columns()
                # Also schedule a delayed reconfigure for final adjustments
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
                    
                    # Request updates without forcing immediate repaint
                    for graph in graphs:
                        if graph.isVisible():
                            graph.update()
                    
                    logging.debug(f"NodesPage: Updated {len(graphs)} graphs for selected node {node_name}")
                else:
                    logging.debug(f"NodesPage: No graphs to update for selected node {node_name}")

    def configure_columns(self):
        """Configure column widths for responsive screen utilization"""
        if not self.table:
            return
            
        # No longer need to hide checkbox column since it's removed
        header = self.table.horizontalHeader()
        
        # Use responsive column sizing with reduced frequency
        QTimer.singleShot(300, self._setup_responsive_columns)
    
    def _setup_responsive_columns(self):
        """Setup responsive column sizing for nodes table"""
        if not self.table:
            return
            
        header = self.table.horizontalHeader()
        available_width = self.table.viewport().width() - 20  # Account for scrollbar
        
        if available_width <= 0:
            available_width = 1200  # Use default width if viewport not ready
        
        # Ensure first column (Name) is immediately visible
        if hasattr(self, 'virtual_model') and self.virtual_model and self.virtual_model.columnCount() > 0:
            self.table.setColumnWidth(0, 150)  # Force Name column width
        
        # Column priorities and minimum widths (no checkbox column)
        column_config = [
            (0, 160, 120, "priority"), # Name (priority - first column)
            (1, 110, 80, "normal"),    # CPU
            (2, 110, 80, "normal"),    # Memory
            (3, 110, 80, "normal"),    # Disk
            (4, 60, 50, "compact"),    # Taints
            (5, 120, 80, "normal"),    # Roles
            (6, 90, 60, "compact"),    # Version
            (7, 60, 50, "compact"),    # Age
            (8, 90, 70, "stretch"),    # Conditions (stretch)
            (9, 60, 60, "fixed")       # Actions
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
            # Virtual table only - check model column count
            if hasattr(self, 'virtual_model') and self.virtual_model:
                if col_index >= self.virtual_model.columnCount():
                    continue
            else:
                # No virtual model available
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
            # No virtual table available
            logging.warning("NodesPage: Cannot show empty message - virtual table not available")
        
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
        
        # Debounce rapid update calls
        current_time = time.time()
        if (hasattr(self, '_last_update_time') and 
            current_time - self._last_update_time < 0.5):  # 500ms debounce
            logging.debug("NodesPage: Debouncing rapid update call")
            return
        self._last_update_time = current_time
        
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
            return
        
        logging.info(f"NodesPage: Processing {len(nodes_data)} nodes for UI display")
        
        # Update total count for pagination
        self.total_nodes = len(nodes_data)
        
        # For progressive loading, show only a page of data initially
        if not hasattr(self, '_showing_all_data') or not self._showing_all_data:
            displayed_data = nodes_data[:self.page_size]
            self.has_more_data = len(nodes_data) > self.page_size
            logging.info(f"NodesPage: Showing {len(displayed_data)} of {len(nodes_data)} nodes initially")
        else:
            displayed_data = nodes_data
            self.has_more_data = False
            logging.info(f"NodesPage: Showing all {len(displayed_data)} nodes")
        
        # Check if this is the same data to prevent redundant updates
        if (hasattr(self, 'nodes_data') and self.nodes_data and 
            len(self.nodes_data) == len(nodes_data) and
            hasattr(self, '_last_data_hash')):
            # Compare data hash to avoid unnecessary updates
            import hashlib
            current_hash = hashlib.md5(str(nodes_data).encode()).hexdigest()
            if current_hash == self._last_data_hash:
                logging.debug("NodesPage: Identical data received, skipping update")
                return
            self._last_data_hash = current_hash
        else:
            # Store hash for future comparisons
            import hashlib
            self._last_data_hash = hashlib.md5(str(nodes_data).encode()).hexdigest()
        
        # Store the data
        self.nodes_data = nodes_data  # Keep full dataset for searches and graphs
        self.resources = displayed_data  # Use paginated data for table display
        self.has_loaded_data = True
        logging.debug(f"NodesPage: Stored node data - has_loaded_data: {self.has_loaded_data}")
        
        # Update graphs only once to reduce load
        if not hasattr(self, '_graphs_initialized') or not self._graphs_initialized:
            self.safe_timer_call(100, lambda: self._update_graphs_async(nodes_data))
            self._graphs_initialized = True
        
        # Check if we're in search mode and apply search filter
        if self._is_searching and self._current_search_query:
            logging.debug(f"NodesPage: Applying search filter for query: {self._current_search_query}")
            self._filter_nodes_by_search(self._current_search_query)
        else:
            logging.debug("NodesPage: No search active - showing paginated nodes")
            self.show_table()
            # Populate table with paginated data
            logging.debug(f"NodesPage: Starting to populate table with {len(displayed_data)} of {len(nodes_data)} nodes")
            self.populate_table(displayed_data)
            logging.info(f"NodesPage: Successfully populated table with {len(displayed_data)} of {len(nodes_data)} nodes")
    
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
        
        # Item count will be updated automatically via model signal
    
    def _render_resources_batch(self, resources, append=False):
        """Override base class to use virtual table populate_table method"""
        if not resources:
            return
        # Virtual table mode only - no traditional table support
        self.populate_table(resources)
    
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
            # Show all nodes data
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

    def _show_startup_loading_message(self):
        """Override to prevent clearing table if data is already loaded"""
        # Check if we already have data loaded - don't clear it
        if (hasattr(self, 'virtual_model') and 
            self.virtual_model and 
            hasattr(self.virtual_model, '_nodes_data') and 
            self.virtual_model._nodes_data):
            logging.info(f"NodesPage: Skipping startup loading message - {len(self.virtual_model._nodes_data)} nodes already loaded")
            return
        
        # Check if we have loaded data flag
        if hasattr(self, 'has_loaded_data') and self.has_loaded_data:
            logging.info("NodesPage: Skipping startup loading message - data already loaded")
            return
            
        # If no data loaded yet, use parent implementation
        logging.info("NodesPage: No data loaded yet, showing startup loading message")
        super()._show_startup_loading_message()

    def clear_table(self):
        """Override base class clear_table to ensure proper widget cleanup"""
        if not self.table:
            return
            
        # Clear all cell widgets first (only for QTableWidget, skip for QTableView)
        if hasattr(self.table, 'columnCount'):  # QTableWidget
            for row in range(self.table.rowCount()):
                for col in range(self.table.columnCount()):
                    widget = self.table.cellWidget(row, col)
                    if widget:
                        widget.setParent(None)
                        widget.deleteLater()
        
        # Clear virtual model data - but don't trigger calculations for empty data
        if hasattr(self, 'virtual_model') and self.virtual_model:
            # Clear data directly without triggering calculations
            self.virtual_model.beginResetModel()
            self.virtual_model._nodes_data = []
            self.virtual_model._performance_cache.clear()
            self.virtual_model.reset_calculation_status()
            self.virtual_model.endResetModel()
            self.virtual_model.data_count_changed.emit(0)
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
            self._setup_responsive_columns()
            # Only add action buttons if there are resources
            if resources_to_use:
                self._add_virtual_action_buttons(resources_to_use)
            # Schedule async metrics updates for virtual model
            self._schedule_virtual_metrics_updates(resources_to_use)
            return
        
        # NodesPage only supports virtual tables - no traditional table fallback
        raise Exception("NodesPage populate_table called but virtual table not available")
    
    

    def _update_selected_node_metrics(self, resource, node_name):
        """Update graph metrics for the currently selected node"""
        try:
            graphs = []
            if hasattr(self, 'cpu_graph') and self.cpu_graph:
                graphs.append(self.cpu_graph)
            if hasattr(self, 'mem_graph') and self.mem_graph:
                graphs.append(self.mem_graph)
            if hasattr(self, 'disk_graph') and self.disk_graph:
                graphs.append(self.disk_graph)
                
            if graphs:
                for graph in graphs:
                    graph.generate_utilization_data([resource], force_update=True)
                    graph.set_selected_node(resource, node_name)
                    
        except Exception as e:
            logging.error(f"Error updating selected node metrics: {e}")
    
    def _schedule_virtual_metrics_updates(self, resources):
        """Schedule async metrics updates for virtual table model"""
        if not resources:
            return
            
        # Update virtual model progressively
        for i, resource in enumerate(resources):
            delay = 100 + (i * 20)  # Staggered updates every 20ms
            self.safe_timer_call(delay, lambda res=resource, idx=i: self._update_virtual_metrics(idx, res))
    
    
    def _update_virtual_metrics(self, index, resource):
        """Update metrics for a virtual table row"""
        try:
            if hasattr(self, 'virtual_model') and self.virtual_model:
                # Calculate metrics  
                node_name = resource.get("name")
                if not node_name:
                    return  # Skip nodes without names
                
                # Calculate the same metrics as traditional table - only if data exists
                cpu_usage = resource.get("cpu_usage")
                cpu_capacity = resource.get("cpu_capacity", "")
                if cpu_usage is not None and cpu_capacity:
                    display_cpu = f"{cpu_capacity} ({cpu_usage:.1f}%)"
                elif cpu_capacity:
                    display_cpu = f"{cpu_capacity}"
                else:
                    # Skip virtual rows without real CPU data
                    return
                
                memory_usage = resource.get("memory_usage")
                mem_capacity = resource.get("memory_capacity", "")
                if memory_usage is not None and mem_capacity:
                    display_mem = f"{mem_capacity} ({memory_usage:.1f}%)"
                elif mem_capacity:
                    display_mem = f"{mem_capacity}"
                else:
                    # Skip virtual rows without real memory data
                    return
                
                disk_usage = resource.get("disk_usage")
                disk_capacity = resource.get("disk_capacity", "")
                if disk_usage is not None and disk_capacity:
                    display_disk = f"{disk_capacity} ({disk_usage:.1f}%)"
                elif disk_capacity:
                    display_disk = f"{disk_capacity}"
                else:
                    # Skip virtual rows without real disk data
                    return
                
                # Update the resource data with calculated values
                resource.update({
                    'calculated_cpu': display_cpu,
                    'calculated_memory': display_mem,
                    'calculated_disk': display_disk
                })
                
                # Trigger model update for this specific row
                if hasattr(self.virtual_model, 'update_row_metrics'):
                    self.virtual_model.update_row_metrics(index, resource)
                else:
                    # Alternative: trigger data changed signal for the metric columns
                    model_index = self.virtual_model.index(index, 1)  # CPU column
                    self.virtual_model.dataChanged.emit(model_index, self.virtual_model.index(index, 3))
                    
        except Exception as e:
            logging.error(f"Error updating virtual metrics for index {index}: {e}")
    
    
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
                # No virtual table available for highlighting
                logging.warning("NodesPage: Cannot highlight row - virtual table not available")
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
        # Skip action column (last column)
        model_col_count = self.virtual_model.columnCount() if hasattr(self, 'virtual_model') and self.virtual_model else 10
        if column != model_col_count - 1:
            self.table.selectRow(row)
            logging.debug(f"NodesPage: Selected table row {row}, triggering graph update")
            # Use safe timer to ensure immediate graph display
            self.safe_timer_call(0, lambda: self.select_node_for_graphs(row))
    
    def handle_row_double_click(self, row, column):
        """Handle double-click to show node detail page"""
        # Skip action column (last column)  
        model_col_count = self.virtual_model.columnCount() if hasattr(self, 'virtual_model') and self.virtual_model else 10
        if column != model_col_count - 1:
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
            
        # Check if we have recent data to avoid redundant loads
        if (hasattr(self, 'nodes_data') and self.nodes_data and 
            hasattr(self, '_last_load_time') and self._last_load_time and
            time.time() - self._last_load_time < 3.0):  # 3 second throttle
            logging.info("NodesPage: Recent data available, skipping load due to throttling")
            return
            
        self.is_loading = True
        self._last_load_time = time.time()
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
        
        # Prevent multiple concurrent force loads
        if self.is_loading:
            logging.debug("NodesPage: Already loading data, skipping force load request")
            return
            
        # Reset pagination state for fresh load
        self.current_page = 0
        self._showing_all_data = False
        
        # Reset throttling for forced refresh
        self._last_load_time = 0
        self.load_data()
    
    def _initial_load_data(self):
        """Initial data load with proper state management"""
        logging.info("NodesPage: _initial_load_data() called")
        if not hasattr(self, 'has_loaded_data') or not self.has_loaded_data:
            self._last_load_time = 0  # Bypass throttling for initial load
            self.load_data()
    
    def safe_timer_call(self, delay: int, callback):
        """Thread-safe timer call - schedule callback to run in main thread"""
        try:
            from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
            # Store callback in a way that can be accessed by method name
            callback_id = str(id(callback))
            setattr(self, f'_timer_callback_{callback_id}', callback)
            
            # Use QMetaObject to invoke a method in the main thread
            QMetaObject.invokeMethod(
                self, 
                "_execute_stored_timer_callback", 
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, delay),
                Q_ARG(str, callback_id)
            )
        except Exception as e:
            logging.warning(f"NodesPage: Error with safe timer call: {e}")
            # Fallback: try direct timer call (may fail in worker thread)
            try:
                QTimer.singleShot(delay, callback)
            except Exception as e2:
                logging.error(f"NodesPage: Timer fallback also failed: {e2}")
    
    @pyqtSlot(int, str)
    def _execute_stored_timer_callback(self, delay: int, callback_id: str):
        """Execute stored timer callback in main thread"""
        try:
            callback_attr = f'_timer_callback_{callback_id}'
            if hasattr(self, callback_attr):
                callback = getattr(self, callback_attr)
                QTimer.singleShot(delay, callback)
                # Clean up stored callback
                delattr(self, callback_attr)
            else:
                logging.warning(f"NodesPage: Stored callback {callback_id} not found")
        except Exception as e:
            logging.warning(f"NodesPage: Error executing stored timer callback: {e}")
    
    def _update_item_count_display(self, count: int):
        """Update the item count display when model data changes"""
        if hasattr(self, 'items_count') and self.items_count:
            if self._is_searching and hasattr(self, '_current_search_query') and self._current_search_query:
                self.items_count.setText(f"{count} items (filtered)")
            else:
                if hasattr(self, 'total_nodes') and self.total_nodes > count:
                    self.items_count.setText(f"{count} of {self.total_nodes} items")
                else:
                    self.items_count.setText(f"{count} items")
            logging.debug(f"NodesPage: Updated item count display to {count} items")
    
    def _on_scroll(self, value):
        """Handle scroll events to load more data automatically"""
        if not hasattr(self, 'nodes_data') or not self.nodes_data:
            return
        
        # Don't load more if we're already showing all data
        if hasattr(self, '_showing_all_data') and self._showing_all_data:
            return
        
        # Prevent immediate triggering when table is first loaded
        if not hasattr(self, '_scroll_initialized'):
            self._scroll_initialized = True
            return
        
        # Get the scroll bar
        scroll_bar = self.table.verticalScrollBar()
        
        # Only trigger if scrollbar exists and has meaningful range
        if scroll_bar.maximum() <= 10:  # Need minimum range to prevent immediate triggering
            return
        
        # Add minimum delay between scroll triggers
        import time
        current_time = time.time()
        if hasattr(self, '_last_scroll_trigger'):
            if current_time - self._last_scroll_trigger < 1.0:  # 1 second cooldown
                return
        
        # Check if we're near the bottom (98% threshold for better control)
        scroll_percentage = value / scroll_bar.maximum() if scroll_bar.maximum() > 0 else 0
        
        if scroll_percentage >= 0.98:  # 98% threshold for more precise control
            current_display_count = len(self.resources) if self.resources else 0
            new_display_count = min(current_display_count + self.page_size, len(self.nodes_data))
            
            # Only load if there's actually more data to show
            if new_display_count > current_display_count:
                # Record this scroll trigger
                self._last_scroll_trigger = current_time
                
                # Show more data
                displayed_data = self.nodes_data[:new_display_count]
                self.resources = displayed_data
                self.populate_table(displayed_data)
                
                # Check if we've shown all data
                if new_display_count >= len(self.nodes_data):
                    self._showing_all_data = True
                
                logging.info(f"NodesPage: Auto-loaded more nodes on scroll - now showing {new_display_count} of {len(self.nodes_data)} nodes")
    
    def _add_controls_to_header(self, header_layout):
        """Override to add custom controls for nodes page without delete button"""
        # NodesPage uses virtual layout with its own refresh button - no duplicate needed
        pass
        
        
    
    # Disable inherited methods that aren't needed for nodes
    def _handle_checkbox_change(self, state, item_name):
        """Override to disable checkbox functionality"""
        _ = state, item_name  # Unused parameters
        pass
        
    def _handle_select_all(self, state):
        """Override to disable select all functionality"""
        _ = state  # Unused parameter
        pass
    
    def _create_checkbox_container(self, row, item_name):
        """Override to create empty container for nodes (no checkbox needed)"""
        _ = row, item_name  # Unused parameters
        from PyQt6.QtWidgets import QWidget
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        return container