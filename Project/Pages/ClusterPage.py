from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QTabWidget, QGridLayout, QSizePolicy, QFrame, QToolTip,
                             QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea)
from PyQt6.QtCore import Qt, QSize, QPoint, QRect, QEvent, pyqtSlot
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QBrush, QFont, QCursor
import math

from UI.Styles import AppStyles, AppColors
from utils.cluster_connector import get_cluster_connector

class BarChart(QWidget):
    def __init__(self, color="#ff0000", title="", unit=""):
        super().__init__()
        self.color = QColor(color)
        self.data = [0] * 24  # Initialize with zeros
        self.current_value = 0
        self.setMinimumHeight(300)
        self.setStyleSheet(AppStyles.BAR_CHART_TOOLTIP_STYLE)

        if color == "#ff0000":  # Red for CPU
            self.chart_title = "CPU Usage"
        else:  # Cyan for Memory
            self.chart_title = "Memory Usage"
            
        self.times = ["00:00", "01:00", "02:00", "03:00", "04:00", "05:00", 
                      "06:00", "07:00", "08:00", "09:00", "10:00", "11:00"]
        
        self.bar_positions = []
        self.hovered_bar = -1

    def mouseMoveEvent(self, event):
        for i, rect in enumerate(self.bar_positions):
            if rect.contains(event.pos()):
                if self.hovered_bar != i:
                    self.hovered_bar = i
                    self.update()
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
            self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        chart_height = height - 120
        
        self.bar_positions = []
        
        y_labels = ["0%", "20%", "40%", "60%", "80%", "100%"]
        for i, label in enumerate(y_labels):
            y = height - 120 - (i * chart_height / 5)
            painter.setPen(QPen(QColor("#333333"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(40, int(y), width, int(y))
            painter.setPen(QColor("#aaaaaa"))
            painter.drawText(0, int(y) - 5, 30, 20, int(Qt.AlignmentFlag.AlignRight), label)
            
        bar_count = len(self.data)
        available_width = width - 50
        bar_width = available_width / bar_count * 0.7
        bar_spacing = available_width / bar_count * 0.3
        
        painter.setPen(QPen(QColor("#333333"), 1, Qt.PenStyle.SolidLine))
        painter.drawLine(40, height - 120, width, height - 120)
        
        for i, value in enumerate(self.data):
            bar_height = (value / 100) * chart_height
            x = 40 + i * (bar_width + bar_spacing)
            y = height - 120 - bar_height
            
            bar_rect = QRect(int(x), int(y), int(bar_width), int(bar_height))
            self.bar_positions.append(bar_rect)
            
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
            
            painter.setPen(QColor("#ffffff"))
            label_font = painter.font()
            label_font.setPointSize(10)
            painter.setFont(label_font)
            x_center = x + (bar_width / 2)
            
            # Only display a subset of labels if many bars
            if len(self.times) <= 12 or i % max(1, len(self.times) // 12) == 0:
                painter.drawText(
                    int(x_center - 25),
                    height - 105,
                    50,
                    20,
                    int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop),
                    self.times[i] if i < len(self.times) else ""
                )

class ResourceCircularIndicator(QWidget):
    def __init__(self, usage=0, requests=0, limits=0, allocated=0, capacity=100):
        super().__init__()
        self.usage = usage
        self.requests = requests
        self.limits = limits
        self.allocated = allocated
        self.capacity = capacity
        self.hovered_segment = None
        self.setMinimumSize(120, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.title = ""
        self.setStyleSheet(AppStyles.CIRCULAR_INDICATOR_TOOLTIP_STYLE)
        
    def set_title(self, title):
        self.title = title

    def get_segment_at_position(self, x, y):
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
        inner_radius = ring2_radius - (8 * size_factor)
        
        if distance > outer_radius or distance < inner_radius - 5:
            return None
            
        usage_angle = self.usage / self.capacity * 360
        requests_angle = self.requests / self.capacity * 360
        limits_angle = self.limits / self.capacity * 360
        allocated_angle = self.allocated / self.capacity * 360
        
        if distance >= ring4_radius + 5:
            return "usage" if angle <= usage_angle else None
        elif distance >= ring3_radius + 5:
            return "requests" if angle <= requests_angle else None
        elif distance >= ring2_radius + 5:
            return "limits" if angle <= limits_angle else None
        else:
            return "allocated" if angle <= allocated_angle else None

    def mouseMoveEvent(self, event):
        segment = self.get_segment_at_position(event.pos().x(), event.pos().y())
        
        if segment != self.hovered_segment:
            self.hovered_segment = segment
            self.update()
            
            if segment == "usage":
                tooltip_text = f"{self.title}\nUsage: {self.usage} ({self.usage/self.capacity*100:.1f}%)"
                QToolTip.showText(QCursor.pos(), tooltip_text, self)
            elif segment == "requests":
                tooltip_text = f"{self.title}\nRequests: {self.requests} ({self.requests/self.capacity*100:.1f}%)"
                QToolTip.showText(QCursor.pos(), tooltip_text, self)
            elif segment == "limits":
                tooltip_text = f"{self.title}\nLimits: {self.limits} ({self.limits/self.capacity*100:.1f}%)"
                QToolTip.showText(QCursor.pos(), tooltip_text, self)
            elif segment == "allocated":
                tooltip_text = f"{self.title}\nAllocated: {self.allocated} ({self.allocated/self.capacity*100:.1f}%)"
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

        size_factor = min(width, height) / 150
        outer_radius = min(width, height) / 2 - (10 * size_factor)
        ring4_radius = outer_radius - (8 * size_factor)
        ring3_radius = ring4_radius - (8 * size_factor)
        ring2_radius = ring3_radius - (8 * size_factor)
        inner_radius = ring2_radius - (8 * size_factor)

        pen_width = 6 * size_factor
        pen = QPen()
        pen.setWidth(max(3, int(pen_width)))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        pen.setColor(QColor(30, 30, 30))
        painter.setPen(pen)

        painter.drawEllipse(int(center_x - outer_radius), int(center_y - outer_radius),
                            int(outer_radius * 2), int(outer_radius * 2))
        painter.drawEllipse(int(center_x - ring4_radius), int(center_y - ring4_radius),
                            int(ring4_radius * 2), int(ring4_radius * 2))
        painter.drawEllipse(int(center_x - ring3_radius), int(center_y - ring3_radius),
                            int(ring3_radius * 2), int(ring3_radius * 2))
        painter.drawEllipse(int(center_x - ring2_radius), int(center_y - ring2_radius),
                            int(ring2_radius * 2), int(ring2_radius * 2))
        painter.drawEllipse(int(center_x - inner_radius), int(center_y - inner_radius),
                            int(inner_radius * 2), int(inner_radius * 2))

        start_angle = -90 * 16

        if self.usage > 0:
            color = QColor(80, 255, 80) if self.hovered_segment == "usage" else QColor(50, 220, 50)
            pen.setColor(color)
            painter.setPen(pen)
            segment_angle = int(self.usage / self.capacity * 360 * 16)
            painter.drawArc(int(center_x - outer_radius), int(center_y - outer_radius),
                            int(outer_radius * 2), int(outer_radius * 2),
                            start_angle, segment_angle)

        if self.requests > 0:
            color = QColor(80, 180, 255) if self.hovered_segment == "requests" else QColor(50, 150, 220)
            pen.setColor(color)
            painter.setPen(pen)
            segment_angle = int(self.requests / self.capacity * 360 * 16)
            painter.drawArc(int(center_x - ring4_radius), int(center_y - ring4_radius),
                            int(ring4_radius * 2), int(ring4_radius * 2),
                            start_angle, segment_angle)

        if self.limits > 0:
            color = QColor(200, 100, 255) if self.hovered_segment == "limits" else QColor(170, 70, 220)
            pen.setColor(color)
            painter.setPen(pen)
            segment_angle = int(self.limits / self.capacity * 360 * 16)
            painter.drawArc(int(center_x - ring3_radius), int(center_y - ring3_radius),
                            int(ring3_radius * 2), int(ring3_radius * 2),
                            start_angle, segment_angle)

        if self.allocated > 0:
            color = QColor(255, 160, 80) if self.hovered_segment == "allocated" else QColor(255, 140, 40)
            pen.setColor(color)
            painter.setPen(pen)
            segment_angle = int(self.allocated / self.capacity * 360 * 16)
            painter.drawArc(int(center_x - ring2_radius), int(center_y - ring2_radius),
                            int(ring2_radius * 2), int(ring2_radius * 2),
                            start_angle, segment_angle)

    def sizeHint(self):
        return QSize(150, 150)

class ResourceStatusWidget(QWidget):
    def __init__(self, title, usage=0, requests=0, limits=0, allocated=0, capacity=0):
        super().__init__()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        self.box = QFrame()
        self.box.setObjectName("statusBox")
        self.box.setStyleSheet(AppStyles.CLUSTER_STATUS_BOX_STYLE)

        box_layout = QVBoxLayout(self.box)
        box_layout.setContentsMargins(10, 10, 10, 10)

        self.title = title
        self.title_label = QLabel(title)
        font = QFont()
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_TITLE_STYLE)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.title_label)

        self.progress = ResourceCircularIndicator(usage, requests, limits, allocated, capacity)
        self.progress.set_title(title)
        self.progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        box_layout.addWidget(self.progress)


        self.usage_label = QLabel(f"● Usage: {usage}")
        self.usage_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_USAGE_STYLE)
        self.usage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.usage_label)

        self.requests_label = QLabel(f"● Requests: {requests}")
        self.requests_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_REQUESTS_STYLE)
        self.requests_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.requests_label)

        self.limits_label = QLabel(f"● Limits: {limits}")
        self.limits_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_LIMITS_STYLE)
        self.limits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.limits_label)

        self.allocated_label = QLabel(f"● Allocated: {allocated}")
        self.allocated_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_ALLOCATED_STYLE)
        self.allocated_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.allocated_label)

        self.capacity_label = QLabel(f"● Capacity: {capacity}")
        self.capacity_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_CAPACITY_STYLE)
        self.capacity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.capacity_label)

        main_layout.addWidget(self.box)
        self.setStyleSheet("background-color: transparent;")
        
    def update_metrics(self, usage, requests, limits, allocated, capacity=None):
        self.progress.usage = usage
        self.progress.requests = requests
        self.progress.limits = limits
        self.progress.allocated = allocated
        if capacity is not None:
            self.progress.capacity = capacity
        self.progress.update()
        
    def sizeHint(self):
        return QSize(170, 300)

    def minimumSizeHint(self):
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
        content_layout = QGridLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)

        # Create the chart panel
        chart_panel = self.create_chart_panel()
        
        # Create a container widget for resource metrics with fixed width
        metrics_container = QWidget()
        metrics_container.setStyleSheet(AppStyles.CLUSTER_METRICS_PANEL_STYLE)
        metrics_container.setMinimumWidth(600)  # Set minimum width to prevent squeezing
        
        # Use a grid layout for more precise control of widget placement
        metrics_grid = QGridLayout(metrics_container)
        metrics_grid.setContentsMargins(16, 16, 16, 16)
        metrics_grid.setSpacing(15)
        
        # Create resource widgets with fixed widths
        self.cpu_status = ResourceStatusWidget("CPU Resources", 0, 0, 0, 0, 100)
        self.memory_status = ResourceStatusWidget("Memory Resources", 0, 0, 0, 0, 100)
        self.disk_status = ResourceStatusWidget("Storage Resources", 0, 0, 0, 0, 100)
        
        # Set a fixed width for each resource widget to prevent overlap
        self.cpu_status.setFixedWidth(180)
        self.memory_status.setFixedWidth(180)
        self.disk_status.setFixedWidth(180)
        
        # Add widgets to the grid layout
        metrics_grid.addWidget(self.cpu_status, 0, 0)
        metrics_grid.addWidget(self.memory_status, 0, 1)
        metrics_grid.addWidget(self.disk_status, 0, 2)
        
        # Status panel for issues
        self.status_panel = self.create_status_panel()

        # Add widgets to the main layout
        content_layout.addWidget(chart_panel, 0, 0)
        content_layout.addWidget(metrics_container, 0, 1)
        content_layout.addWidget(self.status_panel, 1, 0, 1, 2)  # Span two columns

        return content_widget
    def create_chart_panel(self):
        panel = QWidget()
        panel.setStyleSheet(AppStyles.CLUSTER_CHART_PANEL_STYLE)

        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
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
        
        charts = QWidget()
        charts.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        charts_layout = QVBoxLayout(charts)
        charts_layout.setContentsMargins(0, 16, 0, 0)
        
        # Initialize with empty chart data - Fixed to include title and unit
        self.cpu_chart = BarChart(color="#ff0000", title="CPU Usage", unit="%")
        self.memory_chart = BarChart(color="#00ffff", title="Memory Usage", unit="%")
        
        self.cpu_chart.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.memory_chart.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.memory_chart.hide()
        
        charts_layout.addWidget(self.cpu_chart)
        charts_layout.addWidget(self.memory_chart)

        main_layout.addWidget(charts)

        return panel
    
    def show_master_data(self):
        self.master_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        self.worker_btn.setStyleSheet(AppStyles.CLUSTER_INACTIVE_BTN_STYLE)
        
    def show_worker_data(self):
        self.worker_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        self.master_btn.setStyleSheet(AppStyles.CLUSTER_INACTIVE_BTN_STYLE)

    def show_cpu_chart(self):
        self.cpu_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        self.memory_btn.setStyleSheet(AppStyles.CLUSTER_INACTIVE_BTN_STYLE)
        self.cpu_chart.show()
        self.memory_chart.hide()
        
    def show_memory_chart(self):
        self.memory_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        self.cpu_btn.setStyleSheet(AppStyles.CLUSTER_INACTIVE_BTN_STYLE)
        self.memory_chart.show()
        self.cpu_chart.hide()

    def create_status_panel(self):
        # Create a container widget
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Create the panel for no issues
        self.no_issues_panel = QWidget()
        self.no_issues_panel.setStyleSheet(AppStyles.CLUSTER_STATUS_PANEL_STYLE)
        
        no_issues_layout = QVBoxLayout(self.no_issues_panel)
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
        
        # Create the panel for issues
        self.issues_panel = QWidget()
        self.issues_panel.setStyleSheet(AppStyles.CLUSTER_STATUS_PANEL_STYLE)
        
        issues_layout = QVBoxLayout(self.issues_panel)
        issues_layout.setContentsMargins(16, 16, 16, 16)
        issues_layout.setSpacing(16)
        
        issues_header = QLabel("Cluster Issues")
        issues_header.setStyleSheet(AppStyles.CLUSTER_STATUS_TITLE_STYLE)
        issues_header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.issues_table = IssuesTable()
        self.issues_table.setMinimumHeight(200)
        
        issues_layout.addWidget(issues_header)
        issues_layout.addWidget(self.issues_table)
        
        # Initially add the no issues panel
        container_layout.addWidget(self.no_issues_panel)
        container_layout.addWidget(self.issues_panel)
        self.issues_panel.hide()
        
        return container
    
    def update_cluster_info(self, info):
        """Update cluster information from real data"""
        self.cluster_info = info
        # We don't immediately update UI here because we wait for metrics
    
    def update_metrics(self, metrics):
        """Update metrics with real data and proper formatting"""
        self.metrics_data = metrics
        
        if not metrics:
            return
            
        # CPU metrics
        if "cpu" in metrics:
            cpu = metrics["cpu"]
            usage = cpu.get("usage", 0)
            requests = cpu.get("requests", 0)
            limits = cpu.get("limits", 0)
            allocated = cpu.get("allocatable", 0)
            capacity = cpu.get("capacity", 100)
            
            # Update the CPU status widget
            self.cpu_status.update_metrics(
                usage,
                requests,
                limits,
                allocated,
                capacity
            )
            
            # Format the labels with proper units (cores)
            self.cpu_status.usage_label.setText(f"● Usage: {usage:.1f}% ({requests:.2f} cores)")
            self.cpu_status.requests_label.setText(f"● Requests: {requests:.2f} cores")
            self.cpu_status.limits_label.setText(f"● Limits: {limits:.2f} cores")
            self.cpu_status.allocated_label.setText(f"● Allocated: {allocated:.2f} cores")
            self.cpu_status.capacity_label.setText(f"● Capacity: {capacity:.2f} cores")
            
            # Update CPU chart with history data
            cpu_history = cpu.get("history", [0] * 12)
            # Generate some time points for the chart
            times = self.generate_time_points(len(cpu_history))
            self.cpu_chart.update_data(cpu_history, times)
            
        # Memory metrics
        if "memory" in metrics:
            memory = metrics["memory"]
            usage = memory.get("usage", 0)
            requests = memory.get("requests", 0)
            limits = memory.get("limits", 0)
            allocated = memory.get("allocatable", 0)
            capacity = memory.get("capacity", 100)
            
            # Update the memory status widget
            self.memory_status.update_metrics(
                usage,
                requests,
                limits,
                allocated,
                capacity
            )
            
            # Format the labels with proper units (convert to GB for readability)
            self.memory_status.usage_label.setText(f"● Usage: {usage:.1f}% ({self.format_memory(requests)})")
            self.memory_status.requests_label.setText(f"● Requests: {self.format_memory(requests)}")
            self.memory_status.limits_label.setText(f"● Limits: {self.format_memory(limits)}")
            self.memory_status.allocated_label.setText(f"● Allocated: {self.format_memory(allocated)}")
            self.memory_status.capacity_label.setText(f"● Capacity: {self.format_memory(capacity)}")
            
            # Update memory chart with history data
            memory_history = memory.get("history", [0] * 12)
            # Generate some time points for the chart
            times = self.generate_time_points(len(memory_history))
            self.memory_chart.update_data(memory_history, times)
            
        # Storage metrics - use dedicated storage metrics if available, otherwise show pods
        if "storage" in metrics:
            storage = metrics["storage"]
            usage = storage.get("usage", 0)
            requests = storage.get("requests", 0)
            limits = storage.get("limits", 0)
            allocated = storage.get("allocatable", 0)
            capacity = storage.get("capacity", 100)
            
            # Update the storage status widget
            self.disk_status.update_metrics(
                usage,
                requests,
                limits,
                allocated,
                capacity
            )
            
            # Format the labels with proper units (GB)
            self.disk_status.usage_label.setText(f"● Usage: {usage:.1f}% ({self.format_memory(requests)})")
            self.disk_status.requests_label.setText(f"● Requests: {self.format_memory(requests)}")
            self.disk_status.limits_label.setText(f"● Limits: {self.format_memory(limits)}")
            self.disk_status.allocated_label.setText(f"● Allocated: {self.format_memory(allocated)}")
            self.disk_status.capacity_label.setText(f"● Capacity: {self.format_memory(capacity)}")
            
        elif "pods" in metrics:
            # Use pods metrics if storage not available
            pods = metrics["pods"]
            usage = pods.get("usage", 0)
            count = pods.get("count", 0)
            capacity = pods.get("capacity", 100)
            
            # Update the widget title to indicate it's showing pods
            self.disk_status.title_label.setText("Pod Resources")
            
            # Update the storage status widget with pod data
            self.disk_status.update_metrics(
                usage,
                count,
                0,
                0,
                capacity
            )
            
            # Format the labels for pods
            self.disk_status.usage_label.setText(f"● Usage: {usage:.1f}% ({count} pods)")
            self.disk_status.requests_label.setText(f"● Count: {count} pods")
            self.disk_status.limits_label.setText(f"● Limits: N/A")
            self.disk_status.allocated_label.setText(f"● Allocated: N/A")
            self.disk_status.capacity_label.setText(f"● Capacity: {capacity} pods")
        else:
            # If neither storage nor pods info is available, show empty but valid data
            self.disk_status.title_label.setText("Storage Resources")
            self.disk_status.update_metrics(0, 0, 0, 0, 100)
            self.disk_status.usage_label.setText("● Usage: 0% (No data)")
            self.disk_status.requests_label.setText("● Requests: No data")
            self.disk_status.limits_label.setText("● Limits: No data")
            self.disk_status.allocated_label.setText("● Allocated: No data")
            self.disk_status.capacity_label.setText("● Capacity: No data")
    
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
        self.issues_data = issues
        
        if issues and len(issues) > 0:
            # We have issues to display
            self.no_issues_panel.hide()
            self.issues_panel.show()
            self.issues_table.update_issues(issues)
        else:
            # No issues, show the success panel
            self.issues_panel.hide()
            self.no_issues_panel.show()
    
    def generate_time_points(self, count):
        """Generate time points for charts"""
        import datetime
        
        now = datetime.datetime.now()
        # Generate time points backwards from now
        times = []
        for i in range(count, 0, -1):
            time_point = now - datetime.timedelta(minutes=i*5)
            times.append(time_point.strftime("%H:%M"))
        
        return times