# from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
#                              QTabWidget, QGridLayout, QFrame)
# from PyQt6.QtCore import Qt, QSize

# class ClusterPage(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setup_ui()

#     def setup_ui(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setSpacing(0)

#         # Add tab container
#         tab_container = self.create_tab_container()
#         layout.addWidget(tab_container)

#         # Add content area
#         content_area = self.create_content_area()
#         layout.addWidget(content_area)

#     def create_tab_container(self):
#         tab_widget = QTabWidget()
#         tab_widget.setFixedHeight(44)
#         tab_widget.addTab(QWidget(), "Master")
#         tab_widget.addTab(QWidget(), "Worker")
#         tab_widget.setCurrentIndex(0)
#         return tab_widget

#     def create_content_area(self):
#         content_widget = QWidget()
#         content_layout = QGridLayout(content_widget)
#         content_layout.setContentsMargins(16, 16, 16, 16)
#         content_layout.setSpacing(16)

#         metric_panel1 = self.create_metric_panel()
#         metric_panel2 = self.create_metric_panel()
#         status_panel = self.create_status_panel()

#         content_layout.addWidget(metric_panel1, 0, 0)
#         content_layout.addWidget(metric_panel2, 0, 1)
#         content_layout.addWidget(status_panel, 1, 0, 1, 2)

#         return content_widget

#     def create_metric_panel(self):
#         panel = QWidget()
#         panel.setStyleSheet("""
#             QWidget {
#                 background-color: #1e1e1e;
#                 border-radius: 4px;
#             }
#         """)

#         layout = QVBoxLayout(panel)
#         layout.setContentsMargins(16, 16, 16, 16)
#         layout.setSpacing(16)

#         # Tab-like buttons
#         tabs = QWidget()
#         tabs_layout = QHBoxLayout(tabs)
#         tabs_layout.setContentsMargins(0, 0, 0, 0)
#         tabs_layout.setSpacing(4)

#         cpu_btn = QPushButton("CPU")
#         cpu_btn.setStyleSheet("""
#             QPushButton {
#                 background-color: #333333;
#                 color: #ffffff;
#                 border: none;
#                 padding: 6px 16px;
#                 font-size: 13px;
#                 border-radius: 4px;
#             }
#         """)

#         memory_btn = QPushButton("Memory")
#         memory_btn.setStyleSheet("""
#             QPushButton {
#                 background-color: transparent;
#                 color: #888888;
#                 border: none;
#                 padding: 6px 16px;
#                 font-size: 13px;
#             }
#             QPushButton:hover {
#                 color: #ffffff;
#             }
#         """)

#         tabs_layout.addWidget(cpu_btn)
#         tabs_layout.addWidget(memory_btn)
#         tabs_layout.addStretch()

#         # Info message
#         info_container = QWidget()
#         info_layout = QVBoxLayout(info_container)
#         info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         info_msg = QLabel("Metrics are not available due to missing or invalid Prometheus")
#         info_msg.setStyleSheet("color: #888888; font-size: 13px;")
#         info_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         settings_link = QLabel("Open cluster settings")
#         settings_link.setStyleSheet("""
#             color: #0095ff;
#             font-size: 13px;
#             margin-top: 8px;
#         """)
#         settings_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         settings_link.setCursor(Qt.CursorShape.PointingHandCursor)

#         info_layout.addWidget(info_msg)
#         info_layout.addWidget(settings_link)

#         layout.addWidget(tabs)
#         layout.addWidget(info_container, 1, Qt.AlignmentFlag.AlignCenter)

#         return panel

#     def create_status_panel(self):
#         panel = QWidget()
#         panel.setStyleSheet("""
#             background-color: #1e1e1e;
#             border-radius: 4px;
#         """)

#         layout = QVBoxLayout(panel)
#         layout.setContentsMargins(32, 48, 32, 48)
#         layout.setSpacing(8)
#         layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         # Success icon
#         success_icon = QLabel("✓")
#         success_icon.setFixedSize(80, 80)
#         success_icon.setStyleSheet("""
#             background-color: #4CAF50;
#             color: white;
#             font-size: 40px;
#             border-radius: 40px;
#             qproperty-alignment: AlignCenter;
#         """)

#         # Status text
#         status_title = QLabel("No issues found")
#         status_title.setStyleSheet("""
#             color: white;
#             font-size: 20px;
#             font-weight: 500;
#             margin-top: 16px;
#         """)
#         status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         status_subtitle = QLabel("Everything is fine in the Cluster")
#         status_subtitle.setStyleSheet("""
#             color: #888888;
#             font-size: 14px;
#             margin-top: 4px;
#         """)
#         status_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         layout.addWidget(success_icon, 0, Qt.AlignmentFlag.AlignCenter)
#         layout.addWidget(status_title)
#         layout.addWidget(status_subtitle)

#         return panel




from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QTabWidget, QGridLayout, QFrame, QTableWidget, QTableWidgetItem,
                             QHeaderView, QGraphicsDropShadowEffect, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient

from utils.kubernetes_client import get_kubernetes_client

class MetricGauge(QFrame):
    """Custom widget for displaying circular gauge with utilization metrics"""
    def __init__(self, title, color, parent=None):
        super().__init__(parent)
        self.title = title
        self.color = color
        self.value = 0
        self.history = []
        self.capacity = 0
        self.requests = 0
        self.limits = 0
        self.allocate_capacity = 0
        
        self.setMinimumHeight(120)
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Setup UI
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: white; font-size: 16px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Value labels
        self.value_layout = QVBoxLayout()
        self.value_layout.setSpacing(2)
        
        # Usage value
        self.usage_label = QLabel(f"Usage: 0.00")
        self.usage_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        
        # Requests value
        self.requests_label = QLabel(f"Requests: 0.00")
        self.requests_label.setStyleSheet("color: #4CAF50; font-size: 12px;")
        
        # Limits value
        self.limits_label = QLabel(f"Limits: 0.00")
        self.limits_label.setStyleSheet("color: #2196F3; font-size: 12px;")
        
        # Allocate capacity value
        self.allocate_label = QLabel(f"Allocate Capacity: 0.00")
        self.allocate_label.setStyleSheet("color: #FFC107; font-size: 12px;")
        
        # Capacity value
        self.capacity_label = QLabel(f"Capacity: 0.00")
        self.capacity_label.setStyleSheet("color: white; font-size: 12px;")
        
        # Add labels to value layout
        self.value_layout.addWidget(self.usage_label)
        self.value_layout.addWidget(self.requests_label)
        self.value_layout.addWidget(self.limits_label)
        self.value_layout.addWidget(self.allocate_label)
        self.value_layout.addWidget(self.capacity_label)
        
        # Add widgets to main layout
        layout.addWidget(self.title_label)
        layout.addLayout(self.value_layout)
        
        self.setStyleSheet("""
            background-color: #1E1E1E;
            border-radius: 8px;
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
    
    def update_values(self, value, capacity=None, requests=None, limits=None, allocate_capacity=None, history=None):
        """Update the gauge values"""
        self.value = value
        
        if capacity is not None:
            self.capacity = capacity
        
        if requests is not None:
            self.requests = requests
        
        if limits is not None:
            self.limits = limits
        
        if allocate_capacity is not None:
            self.allocate_capacity = allocate_capacity
        
        if history is not None:
            self.history = history
        
        # Update labels with formatted values
        self.usage_label.setText(f"Usage: {value:.2f}%")
        self.requests_label.setText(f"Requests: {self.requests:.2f}")
        self.limits_label.setText(f"Limits: {self.limits:.2f}")
        self.allocate_label.setText(f"Allocate Capacity: {self.allocate_capacity:.2f}")
        self.capacity_label.setText(f"Capacity: {self.capacity:.2f}")
        
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate center and radius
        width = self.width()
        height = self.height()
        center_x = width * 0.5
        center_y = height * 0.4  # Position gauge in upper portion
        outer_radius = min(center_x, center_y) * 0.8
        inner_radius = outer_radius * 0.75
        
        # Draw background circle
        painter.setPen(Qt.PenStyle.NoPen)
        bg_gradient = QRadialGradient(center_x, center_y, outer_radius)
        bg_gradient.setColorAt(0, QColor(40, 40, 40))
        bg_gradient.setColorAt(1, QColor(30, 30, 30))
        painter.setBrush(QBrush(bg_gradient))
        painter.drawEllipse(center_x - outer_radius, center_y - outer_radius,
                           outer_radius * 2, outer_radius * 2)
        
        # Draw track (gray circle)
        painter.setPen(QPen(QColor(60, 60, 60), 5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center_x - inner_radius, center_y - inner_radius,
                           inner_radius * 2, inner_radius * 2)
        
        # Calculate angle for current value
        angle = self.value / 100 * 360
        
        # Draw progress arc (colored)
        painter.setPen(QPen(QColor(self.color), 5))
        painter.drawArc(center_x - inner_radius, center_y - inner_radius,
                       inner_radius * 2, inner_radius * 2,
                       90 * 16, -angle * 16)  # Start at 90 degrees, move counterclockwise

class IssuesTable(QTableWidget):
    """Custom table widget for displaying cluster issues"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        # Set table properties
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Message", "Object", "Type", "Age"])
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setVisible(False)
        
        # Set styles
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                border: none;
                gridline-color: #2d2d2d;
                outline: none;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
                outline: none;
                color: #e2e8f0;
            }
            QTableWidget::item:selected {
                background-color: rgba(33, 150, 243, 0.2);
                border: none;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #888888;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #2d2d2d;
                font-size: 12px;
                text-align: left;
            }
        """)
    
    def update_issues(self, issues):
        """Update table with cluster issues"""
        self.setRowCount(0)
        
        if not issues:
            return
        
        self.setRowCount(len(issues))
        
        for row, issue in enumerate(issues):
            # Message column
            message_item = QTableWidgetItem(issue.get("message", ""))
            message_item.setToolTip(issue.get("message", ""))
            self.setItem(row, 0, message_item)
            
            # Object column
            object_item = QTableWidgetItem(issue.get("object", ""))
            self.setItem(row, 1, object_item)
            
            # Type column
            type_item = QTableWidgetItem(issue.get("type", ""))
            if issue.get("type") == "Warning":
                type_item.setForeground(QColor("#FFC107"))
            elif issue.get("type") == "Error":
                type_item.setForeground(QColor("#FF5252"))
            self.setItem(row, 2, type_item)
            
            # Age column
            age_item = QTableWidgetItem(issue.get("age", ""))
            self.setItem(row, 3, age_item)

class MetricsChart(QFrame):
    """Custom widget for displaying bar charts for metrics history"""
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.data = []
        self.setMinimumHeight(150)
        self.setStyleSheet(f"""
            background-color: transparent;
            border: none;
        """)
    
    def update_data(self, data):
        """Update the chart data"""
        self.data = data
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.data:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw background grid lines
        painter.setPen(QPen(QColor(60, 60, 60), 1, Qt.PenStyle.DotLine))
        for i in range(1, 5):
            y = height - (height * i / 5)
            painter.drawLine(0, y, width, y)
        
        # Get min/max values for scaling
        max_value = max(self.data) if self.data else 100
        min_value = 0  # Start from 0 for better visualization
        
        # Ensure min/max difference to avoid division by zero
        value_range = max(max_value - min_value, 1)
        
        # Calculate bar width and spacing
        bar_count = len(self.data)
        if bar_count == 0:
            return
        
        total_spacing = width * 0.2  # 20% of width for spacing
        spacing = total_spacing / (bar_count + 1)
        bar_width = (width - total_spacing) / bar_count
        
        # Draw bars
        for i, value in enumerate(self.data):
            # Calculate bar dimensions
            bar_height = ((value - min_value) / value_range) * (height * 0.9)
            x = spacing + i * (bar_width + spacing)
            y = height - bar_height
            
            # Create gradient for bar
            gradient = QLinearGradient(x, y, x, height)
            base_color = QColor(self.color)
            gradient.setColorAt(0, base_color)
            gradient.setColorAt(1, QColor(base_color.red(), base_color.green(), base_color.blue(), 100))
            
            # Draw bar
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(x, y, bar_width, bar_height, 2, 2)
        
        # Draw time labels along x-axis
        painter.setPen(QColor(120, 120, 120))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        
        # Draw hour labels (simplified for this example)
        for i in range(0, bar_count, max(1, bar_count // 6)):  # Show ~6 labels
            x = spacing + i * (bar_width + spacing) + bar_width / 2
            label = f"{i:02d}:00"
            painter.drawText(x - 15, height - 5, 30, 20, Qt.AlignmentFlag.AlignCenter, label)

class ClusterPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.kubernetes_client = get_kubernetes_client()
        
        # Connect signals
        self.kubernetes_client.cluster_metrics_updated.connect(self.update_metrics)
        self.kubernetes_client.cluster_issues_updated.connect(self.update_issues)
        
        self.setup_ui()
        
        # Start a timer to request metrics updates
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self.request_metrics_update)
        self.metrics_timer.start(5000)  # Update every 5 seconds
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add tab container
        tab_container = self.create_tab_container()
        layout.addWidget(tab_container)

        # Add content area
        content_area = self.create_content_area()
        layout.addWidget(content_area)
    
    def create_tab_container(self):
        tab_widget = QTabWidget()
        tab_widget.setFixedHeight(44)
        tab_widget.addTab(QWidget(), "Master")
        tab_widget.addTab(QWidget(), "Worker")
        tab_widget.setCurrentIndex(0)
        return tab_widget

    def create_content_area(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        # Top section with metrics
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(16)
        
        # CPU Metric
        self.cpu_gauge = MetricGauge("CPU", "#FF5733")
        metrics_layout.addWidget(self.cpu_gauge)
        
        # Memory Metric
        self.memory_gauge = MetricGauge("Memory", "#33A8FF")
        metrics_layout.addWidget(self.memory_gauge)
        
        # Pods Metric
        self.pods_gauge = MetricGauge("Pods", "#4CAF50")
        metrics_layout.addWidget(self.pods_gauge)
        
        content_layout.addLayout(metrics_layout)
        
        # Middle section with charts
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(16)
        
        # CPU History Chart
        cpu_chart_container = QFrame()
        cpu_chart_container.setStyleSheet("""
            background-color: #1e1e1e;
            border-radius: 4px;
        """)
        cpu_chart_layout = QVBoxLayout(cpu_chart_container)
        
        cpu_chart_title = QLabel("CPU Usage History")
        cpu_chart_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        
        self.cpu_chart = MetricsChart("#FF5733")
        
        cpu_chart_layout.addWidget(cpu_chart_title)
        cpu_chart_layout.addWidget(self.cpu_chart)
        
        # Memory History Chart
        memory_chart_container = QFrame()
        memory_chart_container.setStyleSheet("""
            background-color: #1e1e1e;
            border-radius: 4px;
        """)
        memory_chart_layout = QVBoxLayout(memory_chart_container)
        
        memory_chart_title = QLabel("Memory Usage History")
        memory_chart_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        
        self.memory_chart = MetricsChart("#33A8FF")
        
        memory_chart_layout.addWidget(memory_chart_title)
        memory_chart_layout.addWidget(self.memory_chart)
        
        charts_layout.addWidget(cpu_chart_container)
        charts_layout.addWidget(memory_chart_container)
        
        content_layout.addLayout(charts_layout)
        
        # Bottom section with issues or status
        issues_container = QFrame()
        issues_container.setStyleSheet("""
            background-color: #1e1e1e;
            border-radius: 4px;
        """)
        issues_layout = QVBoxLayout(issues_container)
        
        issues_header = QHBoxLayout()
        issues_title = QLabel("Cluster Issues")
        issues_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        
        self.issues_count = QLabel("0 issues found")
        self.issues_count.setStyleSheet("color: #888888; font-size: 12px; margin-left: 8px;")
        
        issues_header.addWidget(issues_title)
        issues_header.addWidget(self.issues_count)
        issues_header.addStretch()
        
        issues_layout.addLayout(issues_header)
        
        # Issues table or status indicator based on issues
        self.issues_table = IssuesTable()
        self.issues_table.setVisible(False)
        issues_layout.addWidget(self.issues_table)
        
        # No issues widget
        self.no_issues_widget = QWidget()
        no_issues_layout = QVBoxLayout(self.no_issues_widget)
        no_issues_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Success icon
        success_icon_label = QLabel("✓")
        success_icon_label.setFixedSize(80, 80)
        success_icon_label.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            font-size: 40px;
            border-radius: 40px;
            qproperty-alignment: AlignCenter;
        """)
        
        # Status text
        status_title = QLabel("No issues found")
        status_title.setStyleSheet("""
            color: white;
            font-size: 20px;
            font-weight: 500;
            margin-top: 16px;
        """)
        status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_subtitle = QLabel("Everything is fine in the Cluster")
        status_subtitle.setStyleSheet("""
            color: #888888;
            font-size: 14px;
            margin-top: 4px;
        """)
        status_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        no_issues_layout.addWidget(success_icon_label, 0, Qt.AlignmentFlag.AlignCenter)
        no_issues_layout.addWidget(status_title)
        no_issues_layout.addWidget(status_subtitle)
        
        issues_layout.addWidget(self.no_issues_widget)
        
        content_layout.addWidget(issues_container)
        
        return content_widget
    
    def request_metrics_update(self):
        """Request metrics update from client"""
        self.kubernetes_client.get_cluster_metrics_async()
        self.kubernetes_client.get_cluster_issues_async()
    
    @pyqtSlot(dict)
    def update_metrics(self, metrics):
        """Update UI with new metrics data"""
        if not metrics:
            return
        
        # Update CPU gauge
        cpu_data = metrics.get("cpu", {})
        if cpu_data:
            self.cpu_gauge.update_values(
                cpu_data.get("usage", 0),
                cpu_data.get("capacity", 0),
                cpu_data.get("requests", 0),
                cpu_data.get("limits", 0),
                cpu_data.get("allocatable", 0)
            )
            self.cpu_chart.update_data(cpu_data.get("history", []))
        
        # Update Memory gauge
        memory_data = metrics.get("memory", {})
        if memory_data:
            self.memory_gauge.update_values(
                memory_data.get("usage", 0),
                memory_data.get("capacity", 0),
                memory_data.get("requests", 0),
                memory_data.get("limits", 0),
                memory_data.get("allocatable", 0)
            )
            self.memory_chart.update_data(memory_data.get("history", []))
        
        # Update Pods gauge
        pods_data = metrics.get("pods", {})
        if pods_data:
            self.pods_gauge.update_values(
                pods_data.get("usage", 0),
                pods_data.get("capacity", 0),
                pods_data.get("count", 0)
            )
    
    @pyqtSlot(list)
    def update_issues(self, issues):
        """Update UI with cluster issues"""
        if not issues:
            self.issues_count.setText("0 issues found")
            self.issues_table.setVisible(False)
            self.no_issues_widget.setVisible(True)
            return
        
        # Update issues count
        self.issues_count.setText(f"{len(issues)} issues found")
        
        # Update issues table
        self.issues_table.update_issues(issues)
        
        # Show table if issues exist, otherwise show "No issues" widget
        self.issues_table.setVisible(len(issues) > 0)
        self.no_issues_widget.setVisible(len(issues) == 0)