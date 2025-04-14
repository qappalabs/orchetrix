from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QTabWidget, QGridLayout, QSizePolicy, QFrame, QToolTip,
                             QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QStackedLayout)
from PyQt6.QtCore import Qt, QSize, QPoint, QRect, QEvent, pyqtSlot
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QBrush, QFont, QCursor
import math

from UI.Styles import AppStyles, AppColors
from utils.cluster_connector import get_cluster_connector

class BarChart(QWidget):
    def __init__(self, color="#ff0000", title="", unit=""):
        super().__init__()
        self.color = QColor(color)
        self.data = []  # Empty data initially
        self.current_value = 0
        self.setMinimumHeight(300)
        self.setStyleSheet(AppStyles.BAR_CHART_TOOLTIP_STYLE)

        if color == "#ff0000":  # Red for CPU
            self.chart_title = "CPU Usage"
        else:  # Cyan for Memory
            self.chart_title = "Memory Usage"
            
        self.times = []  # Empty times initially
        
        self.bar_positions = []
        self.hovered_bar = -1
        self.has_data = False  # Flag to indicate if we have real data

    def mouseMoveEvent(self, event):
        if not self.has_data or not self.data:
            return super().mouseMoveEvent(event)
            
        for i, rect in enumerate(self.bar_positions):
            if rect.contains(event.pos()):
                if self.hovered_bar != i:
                    self.hovered_bar = i
                    self.update()
                    if i < len(self.data) and i < len(self.times):
                        tooltip_text = f"{self.chart_title}\nTime: {self.times[i]}\nValue: {self.data[i]}%"
                        QToolTip.showText(QCursor.pos(), tooltip_text, self)
                return
        
        if self.hovered_bar != -1:
            self.hovered_bar = -1
            self.update()
            QToolTip.hideText()
        
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.hovered_bar != -1:
            self.hovered_bar = -1
            self.update()
        super().leaveEvent(event)
    
    def update_data(self, data, times):
        """Update chart with real data"""
        if data and times:
            self.data = data
            self.times = times
            self.has_data = True
            self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Don't draw chart if we don't have data
        if not self.has_data or not self.data:
            # Draw "No data available" message
            painter.setPen(QColor("#aaaaaa"))
            font = painter.font()
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(
                0, 0, width, height, 
                int(Qt.AlignmentFlag.AlignCenter), 
                "No data available"
            )
            return
            
        # Calculate chart area - ensure enough space for labels
        chart_height = height - 140  # Height for the actual chart
        bottom_y = height - 50  # Where the x-axis sits
        
        self.bar_positions = []
        
        # Draw y-axis grid and labels
        y_labels = ["0%", "20%", "40%", "60%", "80%", "100%"]
        for i, label in enumerate(y_labels):
            y = bottom_y - 70 - (i * chart_height / 5)
            # Draw grid line
            painter.setPen(QPen(QColor("#333333"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(40, int(y), width - 20, int(y))
            # Draw label
            painter.setPen(QColor("#aaaaaa"))
            painter.drawText(0, int(y) - 10, 30, 20, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), label)
        
        # Calculate bar sizes
        bar_count = len(self.data)
        available_width = width - 60  # Allow space on both sides
        bar_width = min(30, available_width / bar_count * 0.6)  # Cap max width at 30px
        bar_spacing = available_width / bar_count - bar_width
        
        # Draw x-axis
        painter.setPen(QPen(QColor("#333333"), 1, Qt.PenStyle.SolidLine))
        painter.drawLine(40, bottom_y - 70, width - 20, bottom_y - 70)
        
        # Draw bars and x-axis labels
        for i, value in enumerate(self.data):
            # Calculate bar position
            bar_height = (value / 100) * chart_height if value <= 100 else chart_height
            x = 40 + (bar_width + bar_spacing) * i + bar_spacing/2
            y = bottom_y - 70 - bar_height
            
            bar_rect = QRect(int(x), int(y), int(bar_width), int(bar_height))
            self.bar_positions.append(bar_rect)
            
            # Draw the bar with appropriate color
            if i == self.hovered_bar:
                if self.color == QColor("#ff0000"):  # Red
                    hover_color = QColor("#ff5555")
                else:  # Cyan
                    hover_color = QColor("#55ffff")
                painter.setBrush(QBrush(hover_color))
                painter.setPen(QPen(QColor("#666666"), 1))
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(self.color))
                
            painter.drawRect(bar_rect)
            
            # Draw x-axis labels (time) - but avoid overcrowding
            painter.setPen(QColor("#aaaaaa"))
            label_font = painter.font()
            label_font.setPointSize(9)
            painter.setFont(label_font)
            
            # Calculate label display interval to avoid overlap
            label_interval = max(1, bar_count // 8)  # Show at most 8 labels
            if i % label_interval == 0 or i == bar_count - 1:  # Show selected labels plus the last one
                x_center = x + (bar_width / 2)
                time_label = self.times[i] if i < len(self.times) else ""
                painter.drawText(
                    int(x_center - 25),
                    bottom_y - 50,
                    50,
                    30,
                    int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop),
                    time_label
                )


class ResourceCircularIndicator(QWidget):
    def __init__(self, usage=0, requests=0, limits=0, allocated=0, capacity=100, resource_type=""):
        super().__init__()
        self.usage = usage
        self.requests = requests
        self.limits = limits
        self.allocated = allocated
        self.capacity = capacity
        self.resource_type = resource_type  # Store resource type
        self.hovered_segment = None
        self.setMinimumSize(120, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.title = ""
        self.setStyleSheet(AppStyles.CIRCULAR_INDICATOR_TOOLTIP_STYLE)
        self.has_data = False  # Flag to track if we have real data
        
    def set_title(self, title):
        self.title = title

    def get_segment_at_position(self, x, y):
        if not self.has_data:
            return None
            
        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2
        
        dx = x - center_x
        dy = y - center_y
        distance = (dx**2 + dy**2)**0.5
        
        angle = -1 * math.atan2(-dy, dx) * 180 / math.pi
        if angle < 0:
            angle += 360
        angle = (angle + 90) % 360
        
        size_factor = min(width, height) / 150
        
        outer_radius = min(width, height) / 2 - (10 * size_factor)
        ring4_radius = outer_radius - (8 * size_factor)
        ring3_radius = ring4_radius - (8 * size_factor)
        ring2_radius = ring3_radius - (8 * size_factor)
        
        if distance > outer_radius or distance < ring2_radius - 5:
            return None
            
        usage_angle = self.usage / self.capacity * 360 if self.capacity > 0 else 0
        requests_angle = self.requests / self.capacity * 360 if self.capacity > 0 else 0
        limits_angle = self.limits / self.capacity * 360 if self.capacity > 0 else 0
        allocated_angle = self.allocated / self.capacity * 360 if self.capacity > 0 else 0
        
        # Determine which segment was hovered
        if distance >= ring4_radius + 5:
            return "usage" if angle <= usage_angle else None
        elif distance >= ring3_radius + 5 and self.requests > 0:
            return "requests" if angle <= requests_angle else None
        elif distance >= ring2_radius + 5 and self.resource_type != "pods" and self.limits > 0:
            return "limits" if angle <= limits_angle else None
        elif self.resource_type != "pods" and self.allocated > 0:
            return "allocated" if angle <= allocated_angle else None
        else:
            return None

    def mouseMoveEvent(self, event):
        segment = self.get_segment_at_position(event.pos().x(), event.pos().y())
        
        if segment != self.hovered_segment:
            self.hovered_segment = segment
            self.update()
            
            if segment == "usage":
                tooltip_text = f"{self.title}\nUsage: {self.usage:.1f}%"
                QToolTip.showText(QCursor.pos(), tooltip_text, self)
            elif segment == "requests":
                tooltip_text = f"{self.title}\nRequests: {self.requests} ({(self.requests/self.capacity*100):.1f}%)" if self.capacity > 0 else f"{self.title}\nRequests: {self.requests}"
                QToolTip.showText(QCursor.pos(), tooltip_text, self)
            elif segment == "limits" and self.resource_type != "pods":
                tooltip_text = f"{self.title}\nLimits: {self.limits} ({(self.limits/self.capacity*100):.1f}%)" if self.capacity > 0 else f"{self.title}\nLimits: {self.limits}"
                QToolTip.showText(QCursor.pos(), tooltip_text, self)
            elif segment == "allocated" and self.resource_type != "pods":
                tooltip_text = f"{self.title}\nAllocated: {self.allocated} ({(self.allocated/self.capacity*100):.1f}%)" if self.capacity > 0 else f"{self.title}\nAllocated: {self.allocated}"
                QToolTip.showText(QCursor.pos(), tooltip_text, self)
            else:
                QToolTip.hideText()
        
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.hovered_segment = None
        self.update()
        QToolTip.hideText()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2

        if not self.has_data:
            # Draw "No data" message
            painter.setPen(QColor("#aaaaaa"))
            font = painter.font()
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(
                0, 0, width, height, 
                int(Qt.AlignmentFlag.AlignCenter), 
                "No data available"
            )
            return

        size_factor = min(width, height) / 150
        outer_radius = min(width, height) / 2 - (10 * size_factor)
        ring4_radius = outer_radius - (8 * size_factor)
        ring3_radius = ring4_radius - (8 * size_factor)
        ring2_radius = ring3_radius - (8 * size_factor)

        pen_width = 6 * size_factor
        pen = QPen()
        pen.setWidth(max(3, int(pen_width)))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        # Draw background circles - only for rings that have data
        pen.setColor(QColor(30, 30, 30))
        painter.setPen(pen)

        # Always draw the outer ring for usage
        painter.drawEllipse(int(center_x - outer_radius), int(center_y - outer_radius),
                            int(outer_radius * 2), int(outer_radius * 2))
        
        # Only draw the requests ring if we have request data
        if self.requests > 0 or self.resource_type == "pods":
            painter.drawEllipse(int(center_x - ring4_radius), int(center_y - ring4_radius),
                            int(ring4_radius * 2), int(ring4_radius * 2))
        
        # For CPU/Memory, draw the limits and allocated rings if we have data
        if self.resource_type != "pods":
            if self.limits > 0:
                painter.drawEllipse(int(center_x - ring3_radius), int(center_y - ring3_radius),
                                int(ring3_radius * 2), int(ring3_radius * 2))
            
            if self.allocated > 0:
                painter.drawEllipse(int(center_x - ring2_radius), int(center_y - ring2_radius),
                                int(ring2_radius * 2), int(ring2_radius * 2))

        start_angle = -90 * 16

        # Draw usage arc if usage > 0
        if self.usage > 0:
            color = QColor(80, 255, 80) if self.hovered_segment == "usage" else QColor(50, 220, 50)
            pen.setColor(color)
            painter.setPen(pen)
            segment_angle = int(self.usage / 100 * 360 * 16)  # Use fixed scale 0-100%
            painter.drawArc(int(center_x - outer_radius), int(center_y - outer_radius),
                            int(outer_radius * 2), int(outer_radius * 2),
                            start_angle, segment_angle)

        # Draw requests arc if requests > 0
        if self.requests > 0 and self.capacity > 0:
            color = QColor(80, 180, 255) if self.hovered_segment == "requests" else QColor(50, 150, 220)
            pen.setColor(color)
            painter.setPen(pen)
            segment_angle = int(self.requests / self.capacity * 360 * 16)
            painter.drawArc(int(center_x - ring4_radius), int(center_y - ring4_radius),
                            int(ring4_radius * 2), int(ring4_radius * 2),
                            start_angle, segment_angle)

        # Only draw limits and allocated arcs for non-pod resources
        if self.resource_type != "pods":
            # Draw limits arc if limits > 0
            if self.limits > 0 and self.capacity > 0:
                color = QColor(200, 100, 255) if self.hovered_segment == "limits" else QColor(170, 70, 220)
                pen.setColor(color)
                painter.setPen(pen)
                segment_angle = int(self.limits / self.capacity * 360 * 16)
                painter.drawArc(int(center_x - ring3_radius), int(center_y - ring3_radius),
                                int(ring3_radius * 2), int(ring3_radius * 2),
                                start_angle, segment_angle)

            # Draw allocated arc if allocated > 0
            if self.allocated > 0 and self.capacity > 0:
                color = QColor(255, 160, 80) if self.hovered_segment == "allocated" else QColor(255, 140, 40)
                pen.setColor(color)
                painter.setPen(pen)
                segment_angle = int(self.allocated / self.capacity * 360 * 16)
                painter.drawArc(int(center_x - ring2_radius), int(center_y - ring2_radius),
                                int(ring2_radius * 2), int(ring2_radius * 2),
                                start_angle, segment_angle)

    def sizeHint(self):
        # Make all resource indicators the same size
        return QSize(150, 150)


class ResourceStatusWidget(QWidget):
    def __init__(self, title, usage=0, requests=0, limits=0, allocated=0, capacity=0, resource_type=""):
        super().__init__()
        self.resource_type = resource_type

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)  # No spacing between elements to keep them tight

        self.box = QFrame()
        self.box.setObjectName("statusBox")
        self.box.setStyleSheet(AppStyles.CLUSTER_STATUS_BOX_STYLE)

        box_layout = QVBoxLayout(self.box)
        box_layout.setContentsMargins(10, 10, 10, 10)
        box_layout.setSpacing(0)  # No spacing to keep elements tight

        self.title = title
        self.title_label = QLabel(title)
        font = QFont()
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_TITLE_STYLE)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.title_label)

        # Create the progress indicator with resource type
        self.progress = ResourceCircularIndicator(usage, requests, limits, allocated, capacity, resource_type)
        self.progress.set_title(title)
        
        # Use fixed size for indicator to ensure consistent spacing
        self.progress.setFixedSize(130, 130)
        
        # Create a container with no spacing
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        progress_layout.setSpacing(0)  # No spacing
        progress_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        progress_layout.addWidget(self.progress)
        
        box_layout.addWidget(progress_container)

        # Create labels container with minimal spacing
        self.labels_container = QWidget()
        labels_layout = QVBoxLayout(self.labels_container)
        labels_layout.setContentsMargins(10, 0, 0, 0)  # Add left margin for better left alignment
        labels_layout.setSpacing(1)  # Minimal spacing between labels

        # Set labels to be left-aligned instead of center-aligned
        self.usage_label = QLabel("● Usage: No data")
        self.usage_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_USAGE_STYLE)
        self.usage_label.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left-aligned
        labels_layout.addWidget(self.usage_label)

        self.requests_label = QLabel("● Requests: No data")
        self.requests_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_REQUESTS_STYLE)
        self.requests_label.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left-aligned
        labels_layout.addWidget(self.requests_label)

        # For CPU and Memory, add limits and allocated labels (not for Pods)
        if resource_type != "pods":
            self.limits_label = QLabel("● Limits: No data")
            self.limits_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_LIMITS_STYLE)
            self.limits_label.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left-aligned
            labels_layout.addWidget(self.limits_label)

            self.allocated_label = QLabel("● Allocated: No data")
            self.allocated_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_ALLOCATED_STYLE)
            self.allocated_label.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left-aligned
            labels_layout.addWidget(self.allocated_label)

        self.capacity_label = QLabel("● Capacity: No data")
        self.capacity_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_CAPACITY_STYLE)
        self.capacity_label.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left-aligned
        labels_layout.addWidget(self.capacity_label)

        # Add the labels container directly after the progress with no spacing
        box_layout.addWidget(self.labels_container)
        self.labels_container.hide()  # Initially hide until we have data

        # Add a stretch at the end to push everything to the top
        box_layout.addStretch(1)

        main_layout.addWidget(self.box)
        self.setStyleSheet("background-color: transparent;")
        
    def update_metrics(self, usage, requests, limits, allocated, capacity=None):
        """Update the resource metrics with real data"""
        # Update the progress indicator
        self.progress.usage = usage
        self.progress.requests = requests
        
        if self.resource_type != "pods":
            self.progress.limits = limits
            self.progress.allocated = allocated
        else:
            # For pods, don't show limits and allocated
            self.progress.limits = 0
            self.progress.allocated = 0
            
        if capacity is not None:
            self.progress.capacity = capacity
            
        self.progress.has_data = True
        self.progress.update()
        
        # Show the labels container now that we have data
        self.labels_container.show()
        
    def sizeHint(self):
        # Same size for all resource types to ensure alignment
        return QSize(170, 300)

    def minimumSizeHint(self):
        # Same minimum size for all resource types to ensure alignment
        return QSize(150, 270)
class IssuesTable(QTableWidget):
    """Table to display cluster issues"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["Type", "Reason", "Object", "Age", "Message"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(0, 80)
        self.setColumnWidth(1, 120)
        self.setColumnWidth(3, 80)
        self.setStyleSheet(AppStyles.TABLE_STYLE)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
    def update_issues(self, issues):
        """Update the table with a list of issues"""
        self.setRowCount(0)  # Clear existing rows
        
        if not issues:
            return
            
        # Add issues to the table
        for i, issue in enumerate(issues):
            self.insertRow(i)
            
            # Type
            type_item = QTableWidgetItem(issue.get("type", "Unknown"))
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if issue.get("type", "").lower() == "warning":
                type_item.setForeground(QColor(AppColors.STATUS_WARNING))
            elif issue.get("type", "").lower() == "error":
                type_item.setForeground(QColor(AppColors.STATUS_ERROR))
            self.setItem(i, 0, type_item)
            
            # Reason
            reason_item = QTableWidgetItem(issue.get("reason", "Unknown"))
            reason_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(i, 1, reason_item)
            
            # Object
            object_item = QTableWidgetItem(issue.get("object", "Unknown"))
            object_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(i, 2, object_item)
            
            # Age
            age_item = QTableWidgetItem(issue.get("age", "Unknown"))
            age_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(i, 3, age_item)
            
            # Message
            message_item = QTableWidgetItem(issue.get("message", "Unknown"))
            message_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(i, 4, message_item)
        
        # Adjust row heights
        for row in range(self.rowCount()):
            self.setRowHeight(row, 40)


class ClusterPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Get the cluster connector
        self.cluster_connector = get_cluster_connector()
        
        # Connect signals from the connector
        self.cluster_connector.cluster_data_loaded.connect(self.update_cluster_info)
        self.cluster_connector.metrics_data_loaded.connect(self.update_metrics)
        self.cluster_connector.issues_data_loaded.connect(self.update_issues)
        
        # Initialize data
        self.cluster_info = None
        self.metrics_data = None
        self.issues_data = []
        
        # UI setup
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        content_area = self.create_content_area()
        layout.addWidget(content_area)

    def create_content_area(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)

        # Create top section with charts and metrics
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(16)

        # Create the chart panel
        chart_panel = self.create_chart_panel()
        
        # Create a container widget for resource metrics
        metrics_container = QWidget()
        metrics_container.setStyleSheet(AppStyles.CLUSTER_METRICS_PANEL_STYLE)
        metrics_container.setMinimumWidth(600)
        
        # Use a grid layout for resource widgets with equal column widths
        metrics_grid = QGridLayout(metrics_container)
        metrics_grid.setContentsMargins(16, 16, 16, 16)
        metrics_grid.setSpacing(15)
        
        # Create resource widgets with proper resource types
        self.cpu_status = ResourceStatusWidget("CPU Resources", 0, 0, 0, 0, 100, "cpu")
        self.memory_status = ResourceStatusWidget("Memory Resources", 0, 0, 0, 0, 100, "memory")
        self.disk_status = ResourceStatusWidget("Pod Resources", 0, 0, 0, 0, 100, "pods")
        
        # Set fixed width for each resource widget to ensure they're all the same size
        fixed_width = 180
        self.cpu_status.setFixedWidth(fixed_width)
        self.memory_status.setFixedWidth(fixed_width)
        self.disk_status.setFixedWidth(fixed_width)
        
        # Add widgets to the grid layout with equal column sizes
        metrics_grid.addWidget(self.cpu_status, 0, 0)
        metrics_grid.addWidget(self.memory_status, 0, 1)
        metrics_grid.addWidget(self.disk_status, 0, 2)
        
        # Set equal column stretches to ensure proper alignment
        metrics_grid.setColumnStretch(0, 1)
        metrics_grid.setColumnStretch(1, 1)
        metrics_grid.setColumnStretch(2, 1)
        
        # Add chart and metrics to the top section
        top_layout.addWidget(chart_panel, 1)  # Chart gets stretch factor 1
        top_layout.addWidget(metrics_container, 0)  # Metrics don't stretch
        
        # Status panel for issues
        self.status_panel = self.create_status_panel()

        # Add sections to main layout
        content_layout.addWidget(top_section)
        content_layout.addWidget(self.status_panel)
        
        return content_widget

    def create_chart_panel(self):
        panel = QWidget()
        panel.setStyleSheet(AppStyles.CLUSTER_CHART_PANEL_STYLE)
        panel.setMinimumHeight(380)
        
        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Create tabs for switching between chart views
        tabs = QWidget()
        tabs_layout = QHBoxLayout(tabs)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(4)
        
        self.master_btn = QPushButton("Master")
        self.master_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        self.master_btn.clicked.connect(self.show_master_data)
        
        self.worker_btn = QPushButton("Worker")
        self.worker_btn.setStyleSheet(AppStyles.CLUSTER_INACTIVE_BTN_STYLE)
        self.worker_btn.clicked.connect(self.show_worker_data)
        
        tabs_layout.addWidget(self.master_btn)
        tabs_layout.addWidget(self.worker_btn)
        
        tabs_layout.addStretch()
        
        self.cpu_btn = QPushButton("CPU")
        self.cpu_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        self.cpu_btn.clicked.connect(self.show_cpu_chart)

        self.memory_btn = QPushButton("Memory")
        self.memory_btn.setStyleSheet(AppStyles.CLUSTER_INACTIVE_BTN_STYLE)
        self.memory_btn.clicked.connect(self.show_memory_chart)

        tabs_layout.addWidget(self.cpu_btn)
        tabs_layout.addWidget(self.memory_btn)
        
        main_layout.addWidget(tabs)
        
        # Create a container for charts with a stacked layout
        self.charts_container = QWidget()
        self.charts_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Use a stacked layout to prevent chart widgets from being deleted
        self.charts_layout = QStackedLayout(self.charts_container)
        self.charts_layout.setContentsMargins(0, 16, 0, 0)
        
        # Initialize with empty chart data - Fixed to include title and unit
        self.cpu_chart = BarChart(color="#ff0000", title="CPU Usage", unit="%")
        self.memory_chart = BarChart(color="#00ffff", title="Memory Usage", unit="%")
        
        # Add charts to stacked layout
        self.charts_layout.addWidget(self.cpu_chart)
        self.charts_layout.addWidget(self.memory_chart)
        
        # Set the CPU chart as current
        self.charts_layout.setCurrentWidget(self.cpu_chart)
        
        # Add the charts container to the main layout
        main_layout.addWidget(self.charts_container)

        return panel

    def show_master_data(self):
        self.master_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        self.worker_btn.setStyleSheet(AppStyles.CLUSTER_INACTIVE_BTN_STYLE)
        
    def show_worker_data(self):
        self.worker_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        self.master_btn.setStyleSheet(AppStyles.CLUSTER_INACTIVE_BTN_STYLE)

    def show_cpu_chart(self):
        """Switch to CPU chart view"""
        self.cpu_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        self.memory_btn.setStyleSheet(AppStyles.CLUSTER_INACTIVE_BTN_STYLE)
        
        # Use the stacked layout to switch charts instead of show/hide
        if hasattr(self, 'charts_layout') and self.charts_layout:
            self.charts_layout.setCurrentWidget(self.cpu_chart)

    def show_memory_chart(self):
        """Switch to memory chart view"""
        self.memory_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        self.cpu_btn.setStyleSheet(AppStyles.CLUSTER_INACTIVE_BTN_STYLE)
        
        # Use the stacked layout to switch charts instead of show/hide
        if hasattr(self, 'charts_layout') and self.charts_layout:
            self.charts_layout.setCurrentWidget(self.memory_chart)
    
    def create_status_panel(self):
        # Create a container widget
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Create the panel for both states (no issues and issues)
        self.status_widget = QWidget()
        self.status_widget.setStyleSheet(AppStyles.CLUSTER_STATUS_PANEL_STYLE)
        
        # Create stacked layout to toggle between no issues and issues content
        self.stacked_layout = QStackedLayout(self.status_widget)
        self.stacked_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create no issues content - keep this the same
        no_issues_widget = QWidget()
        no_issues_layout = QVBoxLayout(no_issues_widget)
        no_issues_layout.setContentsMargins(32, 48, 32, 48)  
        no_issues_layout.setSpacing(8)
        no_issues_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        success_icon = QLabel("✓")
        success_icon.setFixedSize(80, 80)  
        success_icon.setStyleSheet(AppStyles.CLUSTER_STATUS_ICON_STYLE)

        status_title = QLabel("No issues found")
        status_title.setStyleSheet(AppStyles.CLUSTER_STATUS_TITLE_STYLE)
        status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status_subtitle = QLabel("All resources are within acceptable limits")
        status_subtitle.setStyleSheet(AppStyles.CLUSTER_STATUS_SUBTITLE_STYLE)
        status_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        no_issues_layout.addWidget(success_icon, 0, Qt.AlignmentFlag.AlignCenter)
        no_issues_layout.addWidget(status_title)
        no_issues_layout.addWidget(status_subtitle)
        
        # Create issues content - with reduced top space
        issues_widget = QWidget()
        issues_layout = QVBoxLayout(issues_widget)
        # Significantly reduce the top margin (from 16 to just 2)
        issues_layout.setContentsMargins(16, 2, 16, 16)
        issues_layout.setSpacing(8)  # Also reduce spacing between header and table
        
        issues_header = QLabel("Cluster Issues")
        issues_header.setStyleSheet(AppStyles.CLUSTER_STATUS_TITLE_STYLE)
        issues_header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.issues_table = IssuesTable()
        
        issues_layout.addWidget(issues_header)
        issues_layout.addWidget(self.issues_table)
        
        # Add both widgets to the stacked layout
        self.stacked_layout.addWidget(no_issues_widget)  # index 0
        self.stacked_layout.addWidget(issues_widget)     # index 1
        
        # Add the status widget to the container
        container_layout.addWidget(self.status_widget)
        
        return container
    def update_cluster_info(self, info):
        """Update cluster information from real data"""
        self.cluster_info = info
        # We don't immediately update UI here because we wait for metrics


    def update_metrics(self, metrics):
        """Update metrics with real data and proper formatting"""
        try:
            if not metrics:
                return
                
            self.metrics_data = metrics
            
            # Check if widgets still exist
            if not all(hasattr(self, attr) for attr in ['cpu_status', 'memory_status', 'disk_status', 'cpu_chart', 'memory_chart']):
                return
                    
            # CPU metrics
            if "cpu" in metrics:
                cpu = metrics["cpu"]
                usage_percent = cpu.get("usage", 0)  # Already in percentage
                requests = cpu.get("requests", 0)    # Absolute value
                limits = cpu.get("limits", 0)
                allocated = cpu.get("allocatable", 0)
                capacity = cpu.get("capacity", 100)
                
                # Only update if we have valid data (usage > 0 or requests > 0)
                if usage_percent > 0 or requests > 0:
                    # Update the CPU status widget
                    self.cpu_status.update_metrics(
                        usage_percent,
                        requests,
                        limits,
                        allocated,
                        capacity
                    )
                    
                    # Format the labels with proper units (cores)
                    self.cpu_status.usage_label.setText(f"● Usage: {usage_percent:.1f}% ({requests:.2f} cores)")
                    self.cpu_status.requests_label.setText(f"● Requests: {requests:.2f} cores")
                    
                    if hasattr(self.cpu_status, 'limits_label') and limits > 0:
                        self.cpu_status.limits_label.setText(f"● Limits: {limits:.2f} cores")
                    
                    if hasattr(self.cpu_status, 'allocated_label') and allocated > 0:
                        self.cpu_status.allocated_label.setText(f"● Allocated: {allocated:.2f} cores")
                        
                    self.cpu_status.capacity_label.setText(f"● Capacity: {capacity:.2f} cores")
                    
                    # Update CPU chart with history data
                    cpu_history = cpu.get("history")
                    cpu_timestamps = cpu.get("timestamps", [])  # Get real timestamps if available
                    
                    if cpu_history and len(cpu_history) > 0:
                        # Use real timestamps from the metrics if available
                        if cpu_timestamps and len(cpu_timestamps) == len(cpu_history):
                            times = cpu_timestamps
                        else:
                            # Fall back to generated timestamps if real ones aren't available
                            times = self.generate_time_points(len(cpu_history))
                            
                        try:
                            self.cpu_chart.update_data(cpu_history, times)
                        except RuntimeError:
                            # Handle case where widget was deleted
                            pass
                
                # Memory metrics
                if "memory" in metrics:
                    memory = metrics["memory"]
                    usage_percent = memory.get("usage", 0)
                    requests = memory.get("requests", 0)
                    limits = memory.get("limits", 0)
                    allocated = memory.get("allocatable", 0)
                    capacity = memory.get("capacity", 100)
                    
                    # Only update if we have valid data (usage > 0 or requests > 0)
                    if usage_percent > 0 or requests > 0:
                        # Update the memory status widget
                        self.memory_status.update_metrics(
                            usage_percent,
                            requests,
                            limits,
                            allocated,
                            capacity
                        )
                        
                        # Format the labels with proper units
                        self.memory_status.usage_label.setText(f"● Usage: {usage_percent:.1f}% ({self.format_memory(requests)})")
                        self.memory_status.requests_label.setText(f"● Requests: {self.format_memory(requests)}")
                        
                        if hasattr(self.memory_status, 'limits_label') and limits > 0:
                            self.memory_status.limits_label.setText(f"● Limits: {self.format_memory(limits)}")
                        
                        if hasattr(self.memory_status, 'allocated_label') and allocated > 0:
                            self.memory_status.allocated_label.setText(f"● Allocated: {self.format_memory(allocated)}")
                            
                        self.memory_status.capacity_label.setText(f"● Capacity: {self.format_memory(capacity)}")
                        
                        # Update memory chart with history data
                        memory_history = memory.get("history")
                        memory_timestamps = memory.get("timestamps", [])  # Get real timestamps if available
                        
                        if memory_history and len(memory_history) > 0:
                            # Use real timestamps from the metrics if available
                            if memory_timestamps and len(memory_timestamps) == len(memory_history):
                                times = memory_timestamps
                            else:
                                # Fall back to generated timestamps if real ones aren't available
                                times = self.generate_time_points(len(memory_history))
                                
                            try:
                                self.memory_chart.update_data(memory_history, times)
                            except RuntimeError:
                                # Handle case where widget was deleted
                                pass
                if "pods" in metrics:
    #             # Use pods metrics if storage not available
                    pods = metrics["pods"]
                    usage_percent = pods.get("usage", 0)
                    count = pods.get("count", 0)
                    capacity = pods.get("capacity", 100)
                    
                    # Only update if we have valid data (usage > 0 or count > 0)
                    if usage_percent > 0 or count > 0:
                        # Update the widget title to indicate it's showing pods
                        self.disk_status.title_label.setText("Pod Resources")
                        
                        # Update the pods status widget
                        self.disk_status.update_metrics(
                            usage_percent,
                            count,
                            0,  # No limits for pods
                            0,  # No allocation for pods
                            capacity
                        )
                        
                        # Format the labels for pods
                        self.disk_status.usage_label.setText(f"● Usage: {usage_percent:.1f}% ({count} pods)")
                        self.disk_status.requests_label.setText(f"● Count: {count} pods")
                        self.disk_status.capacity_label.setText(f"● Capacity: {capacity} pods")
            
            # Storage metrics remain the same...
                
        except Exception as e:
            print(f"Error updating metrics: {e}")    
    def format_memory(self, memory_value):
        """Format memory values to human-readable format"""
        if memory_value < 1024:
            return f"{memory_value:.2f} MB"
        elif memory_value < 1024 * 1024:
            return f"{memory_value/1024:.2f} GB"
        else:
            return f"{memory_value/(1024*1024):.2f} TB"
    
    def update_issues(self, issues):
        """Update with real issues data"""
        try:
            self.issues_data = issues
            
            if hasattr(self, 'stacked_layout'):
                if issues and len(issues) > 0:
                    # We have issues to display - switch to issues view
                    self.stacked_layout.setCurrentIndex(1)
                    if hasattr(self, 'issues_table'):
                        self.issues_table.update_issues(issues)
                else:
                    # No issues, show the success panel
                    self.stacked_layout.setCurrentIndex(0)
        except Exception as e:
            print(f"Error updating issues: {e}")
    
    def generate_time_points(self, count):
        """Generate time points for charts with even spacing"""
        import datetime
        
        now = datetime.datetime.now()
        # Generate time points backwards from now with proper spacing
        times = []
        
        # Calculate appropriate time interval based on data point count
        if count <= 12:
            interval_minutes = 5  # 5 minute intervals for small datasets
        elif count <= 24:
            interval_minutes = 2  # 2 minute intervals for medium datasets
        else:
            interval_minutes = 1  # 1 minute intervals for large datasets
        
        for i in range(count, 0, -1):
            time_point = now - datetime.timedelta(minutes=i*interval_minutes)
            times.append(time_point.strftime("%H:%M"))
        
        return times