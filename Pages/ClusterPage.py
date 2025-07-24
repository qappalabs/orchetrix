from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QGridLayout, QSizePolicy, QFrame, QToolTip,
                             QTableWidget, QTableWidgetItem, QHeaderView, QStackedLayout)
from PyQt6.QtCore import Qt, QSize, QRect, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QCursor
import math
import datetime
import logging

from UI.Styles import AppStyles, AppColors
from utils.cluster_connector import get_cluster_connector

class BarChart(QWidget):
    def __init__(self, color="#ff0000", title="", unit=""):
        super().__init__()
        self.color = QColor(color)
        self.data = []
        self.current_value = 0
        self.setMinimumHeight(300)
        self.setStyleSheet(AppStyles.BAR_CHART_TOOLTIP_STYLE)

        if color == "#ff0000":  # Red for CPU
            self.chart_title = "CPU Usage"
        else:  # Cyan for Memory
            self.chart_title = "Memory Usage"
            
        self.times = []
        self.bar_positions = []
        self.hovered_bar = -1
        self.has_data = False
        
        # Enable mouse tracking
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        if not self.has_data or not self.data:
            return super().mouseMoveEvent(event)
            
        for i, rect in enumerate(self.bar_positions):
            if rect.contains(event.pos()):
                if self.hovered_bar != i:
                    self.hovered_bar = i
                    self.update()
                    if i < len(self.data) and i < len(self.times):
                        tooltip_text = f"{self.chart_title}\nTime: {self.times[i]}\nValue: {self.data[i]:.1f}%"
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
            QToolTip.hideText()
        super().leaveEvent(event)
    
    def update_data(self, data, times=None):
        """Update chart with real data and proper cleanup"""
        try:
            if data and isinstance(data, list) and len(data) > 0:
                # Clear previous data first to prevent memory buildup
                self.data.clear()
                self.times.clear()
                self.bar_positions.clear()
                
                # Validate and limit data to max 8 points
                validated_data = []
                data_to_use = data[-8:] if len(data) > 8 else data  # Only take last 8 points
                for value in data_to_use:
                    try:
                        val = float(value)
                        validated_data.append(max(0, min(100, val)))  # Clamp between 0-100
                    except (ValueError, TypeError):
                        validated_data.append(0)
                
                self.data = validated_data
                
                # Generate times if not provided
                if times and len(times) >= len(self.data):
                    self.times = times[-len(self.data):]  # Take matching number of times
                else:
                    self.times = self._generate_time_labels(len(self.data))
                
                self.has_data = True
                logging.debug(f"Chart updated with {len(self.data)} data points (max 8): {self.data}")
                self.update()
            else:
                logging.warning(f"Invalid data provided to chart: {data}")
                self._clear_chart_data()
        except Exception as e:
            logging.error(f"Error updating chart data: {e}")
            self._clear_chart_data()
    
    def _clear_chart_data(self):
        """Clear all chart data and reset state"""
        self.has_data = False
        self.data.clear()
        self.times.clear()
        self.bar_positions.clear()
        self.hovered_bar = -1
        self.update()
    
    def _generate_time_labels(self, count):
        """Generate time labels for the chart"""
        try:
            now = datetime.datetime.now()
            times = []
            
            # Calculate interval based on count
            if count <= 12:
                interval_minutes = 5
            elif count <= 24:
                interval_minutes = 2
            else:
                interval_minutes = 1
            
            for i in range(count):
                time_point = now - datetime.timedelta(minutes=(count - i) * interval_minutes)
                times.append(time_point.strftime("%H:%M"))
            
            return times
        except Exception as e:
            logging.error(f"Error generating time labels: {e}")
            return [f"T{i}" for i in range(count)]
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Don't draw chart if we don't have data
        if not self.has_data or not self.data:
            painter.setPen(QColor("#aaaaaa"))
            font = painter.font()
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(
                0, 0, width, height, 
                int(Qt.AlignmentFlag.AlignCenter), 
                "Loading real-time data..."
            )
            return
            
        # Calculate chart area
        chart_height = height - 140
        bottom_y = height - 50
        
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
        available_width = width - 60
        bar_width = min(30, available_width / bar_count * 0.6)
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
            
            # Draw x-axis labels (time)
            painter.setPen(QColor("#aaaaaa"))
            label_font = painter.font()
            label_font.setPointSize(9)
            painter.setFont(label_font)
            
            # Show every nth label to avoid overcrowding
            label_interval = max(1, bar_count // 8)
            if i % label_interval == 0 or i == bar_count - 1:
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
        self.resource_type = resource_type
        self.hovered_segment = None
        self.setMinimumSize(120, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.title = ""
        self.setStyleSheet(AppStyles.CIRCULAR_INDICATOR_TOOLTIP_STYLE)
        self.has_data = False
        
    def set_title(self, title):
        self.title = title

    def update_metrics(self, usage, requests, limits, allocated, capacity):
        """Update the metrics and mark as having data"""
        try:
            self.usage = float(usage) if usage is not None else 0
            self.requests = float(requests) if requests is not None else 0
            self.limits = float(limits) if limits is not None else 0
            self.allocated = float(allocated) if allocated is not None else 0
            self.capacity = float(capacity) if capacity is not None else 100
            self.has_data = True
            self.update()
            logging.debug(f"Updated metrics for {self.resource_type}: usage={self.usage}, capacity={self.capacity}")
        except Exception as e:
            logging.error(f"Error updating metrics for {self.resource_type}: {e}")
            self.has_data = False

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
            
        usage_angle = self.usage / 100 * 360 if self.usage <= 100 else 360
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
            painter.setPen(QColor("#aaaaaa"))
            font = painter.font()
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(
                0, 0, width, height, 
                int(Qt.AlignmentFlag.AlignCenter), 
                "Loading..."
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

        # Draw background circles
        pen.setColor(QColor(30, 30, 30))
        painter.setPen(pen)

        # Always draw the outer ring for usage
        painter.drawEllipse(int(center_x - outer_radius), int(center_y - outer_radius),
                            int(outer_radius * 2), int(outer_radius * 2))
        
        # Only draw other rings if we have data
        if self.requests > 0 or self.resource_type == "pods":
            painter.drawEllipse(int(center_x - ring4_radius), int(center_y - ring4_radius),
                            int(ring4_radius * 2), int(ring4_radius * 2))
        
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
            segment_angle = int(min(self.usage, 100) / 100 * 360 * 16)
            painter.drawArc(int(center_x - outer_radius), int(center_y - outer_radius),
                            int(outer_radius * 2), int(outer_radius * 2),
                            start_angle, segment_angle)

        # Draw requests arc if requests > 0
        if self.requests > 0 and self.capacity > 0:
            color = QColor(80, 180, 255) if self.hovered_segment == "requests" else QColor(50, 150, 220)
            pen.setColor(color)
            painter.setPen(pen)
            segment_angle = int(min(self.requests / self.capacity, 1.0) * 360 * 16)
            painter.drawArc(int(center_x - ring4_radius), int(center_y - ring4_radius),
                            int(ring4_radius * 2), int(ring4_radius * 2),
                            start_angle, segment_angle)

        # Only draw limits and allocated arcs for non-pod resources
        if self.resource_type != "pods":
            if self.limits > 0 and self.capacity > 0:
                color = QColor(200, 100, 255) if self.hovered_segment == "limits" else QColor(170, 70, 220)
                pen.setColor(color)
                painter.setPen(pen)
                segment_angle = int(min(self.limits / self.capacity, 1.0) * 360 * 16)
                painter.drawArc(int(center_x - ring3_radius), int(center_y - ring3_radius),
                                int(ring3_radius * 2), int(ring3_radius * 2),
                                start_angle, segment_angle)

            if self.allocated > 0 and self.capacity > 0:
                color = QColor(255, 160, 80) if self.hovered_segment == "allocated" else QColor(255, 140, 40)
                pen.setColor(color)
                painter.setPen(pen)
                segment_angle = int(min(self.allocated / self.capacity, 1.0) * 360 * 16)
                painter.drawArc(int(center_x - ring2_radius), int(center_y - ring2_radius),
                                int(ring2_radius * 2), int(ring2_radius * 2),
                                start_angle, segment_angle)

    def sizeHint(self):
        return QSize(150, 150)


class ResourceStatusWidget(QWidget):
    def __init__(self, title, usage=0, requests=0, limits=0, allocated=0, capacity=0, resource_type=""):
        super().__init__()
        self.resource_type = resource_type

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.box = QFrame()
        self.box.setObjectName("statusBox")
        self.box.setStyleSheet(AppStyles.CLUSTER_STATUS_BOX_STYLE)

        box_layout = QVBoxLayout(self.box)
        box_layout.setContentsMargins(10, 10, 10, 10)
        box_layout.setSpacing(0)

        self.title = title
        self.title_label = QLabel(title)
        font = QFont()
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_TITLE_STYLE)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.title_label)

        # Create the progress indicator
        self.progress = ResourceCircularIndicator(usage, requests, limits, allocated, capacity, resource_type)
        self.progress.set_title(title)
        self.progress.setFixedSize(130, 130)
        
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(0)
        progress_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.progress)
        box_layout.addWidget(progress_container)

        # Create labels container
        self.labels_container = QWidget()
        labels_layout = QVBoxLayout(self.labels_container)
        labels_layout.setContentsMargins(10, 0, 0, 0)
        labels_layout.setSpacing(1)

        self.usage_label = QLabel("● Usage: Loading...")
        self.usage_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_USAGE_STYLE)
        self.usage_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        labels_layout.addWidget(self.usage_label)

        self.requests_label = QLabel("● Requests: Loading...")
        self.requests_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_REQUESTS_STYLE)
        self.requests_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        labels_layout.addWidget(self.requests_label)

        # For CPU and Memory, add limits and allocated labels
        if resource_type != "pods":
            self.limits_label = QLabel("● Limits: Loading...")
            self.limits_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_LIMITS_STYLE)
            self.limits_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            labels_layout.addWidget(self.limits_label)

            self.allocated_label = QLabel("● Allocated: Loading...")
            self.allocated_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_ALLOCATED_STYLE)
            self.allocated_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            labels_layout.addWidget(self.allocated_label)

        self.capacity_label = QLabel("● Capacity: Loading...")
        self.capacity_label.setStyleSheet(AppStyles.CLUSTER_RESOURCE_LABEL_CAPACITY_STYLE)
        self.capacity_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        labels_layout.addWidget(self.capacity_label)

        box_layout.addWidget(self.labels_container)
        self.labels_container.show()  # Always show labels

        box_layout.addStretch(1)
        main_layout.addWidget(self.box)
        self.setStyleSheet("background-color: transparent;")
        
    def update_metrics(self, usage, requests, limits, allocated, capacity=None):
        """Update the resource metrics with real data"""
        try:
            # Update the progress indicator
            if capacity is not None:
                self.progress.capacity = capacity
            
            self.progress.update_metrics(usage, requests, limits, allocated, self.progress.capacity)
            
            # Update labels based on resource type
            if self.resource_type == "cpu":
                usage_cores = (usage / 100) * self.progress.capacity if self.progress.capacity > 0 else 0
                self.usage_label.setText(f"● Usage: {usage:.1f}% ({usage_cores:.2f} cores)")
                self.requests_label.setText(f"● Requests: {requests:.2f} cores")
                if hasattr(self, 'limits_label') and limits > 0:
                    self.limits_label.setText(f"● Limits: {limits:.2f} cores")
                else:
                    if hasattr(self, 'limits_label'):
                        self.limits_label.setText("● Limits: Not set")
                if hasattr(self, 'allocated_label') and allocated > 0:
                    self.allocated_label.setText(f"● Allocated: {allocated:.2f} cores")
                else:
                    if hasattr(self, 'allocated_label'):
                        self.allocated_label.setText("● Allocated: Not set")
                self.capacity_label.setText(f"● Capacity: {self.progress.capacity:.2f} cores")
                
            elif self.resource_type == "memory":
                usage_memory = (usage / 100) * self.progress.capacity if self.progress.capacity > 0 else 0
                self.usage_label.setText(f"● Usage: {usage:.1f}% ({self.format_memory(usage_memory)})")
                self.requests_label.setText(f"● Requests: {self.format_memory(requests)}")
                if hasattr(self, 'limits_label') and limits > 0:
                    self.limits_label.setText(f"● Limits: {self.format_memory(limits)}")
                else:
                    if hasattr(self, 'limits_label'):
                        self.limits_label.setText("● Limits: Not set")
                if hasattr(self, 'allocated_label') and allocated > 0:
                    self.allocated_label.setText(f"● Allocated: {self.format_memory(allocated)}")
                else:
                    if hasattr(self, 'allocated_label'):
                        self.allocated_label.setText("● Allocated: Not set")
                self.capacity_label.setText(f"● Capacity: {self.format_memory(self.progress.capacity)}")
                
            elif self.resource_type == "pods":
                count = int(requests)  # For pods, requests represents count
                self.usage_label.setText(f"● Usage: {usage:.1f}% ({count} pods)")
                self.requests_label.setText(f"● Count: {count} pods")
                self.capacity_label.setText(f"● Capacity: {int(self.progress.capacity)} pods")
                
            logging.debug(f"Updated {self.resource_type} metrics: usage={usage:.1f}%")
            
        except Exception as e:
            logging.error(f"Error updating {self.resource_type} metrics: {e}")
    
    def format_memory(self, memory_value):
        """Format memory values to human-readable format"""
        try:
            if memory_value < 1024:
                return f"{memory_value:.2f} MB"
            elif memory_value < 1024 * 1024:
                return f"{memory_value/1024:.2f} GB"
            else:
                return f"{memory_value/(1024*1024):.2f} TB"
        except:
            return f"{memory_value:.2f} MB"
        
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
        self.setRowCount(0)
        
        if not issues:
            return
            
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
        
        # Initialize data
        self.cluster_info = None
        self.metrics_data = None
        self.issues_data = []
        
        # FIXED: Connect signals with better error handling and logging
        self._connect_cluster_signals()
        
        # Data refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        
        # Store historical data for charts
        self.cpu_history = []
        self.memory_history = []
        self.max_history_points = 8
        self.last_metrics_hash = None
        
        # UI setup
        self.setup_ui()
        
        # Ensure worker is selected by default and master remains disabled
        QTimer.singleShot(100, self.show_worker_data)

    def _connect_cluster_signals(self):
        """Connect cluster connector signals with improved error handling"""
        try:
            # Disconnect any existing connections first
            try:
                self.cluster_connector.cluster_data_loaded.disconnect()
                self.cluster_connector.metrics_data_loaded.disconnect()
                self.cluster_connector.issues_data_loaded.disconnect()
            except (TypeError, RuntimeError):
                pass  # No existing connections
            
            # Connect signals
            self.cluster_connector.cluster_data_loaded.connect(self.update_cluster_info)
            self.cluster_connector.metrics_data_loaded.connect(self.update_metrics)
            self.cluster_connector.issues_data_loaded.connect(self.update_issues)
            
            logging.info("ClusterPage: Successfully connected cluster connector signals")
            
        except Exception as e:
            logging.error(f"ClusterPage: Error connecting cluster signals: {e}")


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
        
        # Create metrics container
        metrics_container = QWidget()
        metrics_container.setStyleSheet(AppStyles.CLUSTER_METRICS_PANEL_STYLE)
        metrics_container.setMinimumWidth(600)
        
        metrics_grid = QGridLayout(metrics_container)
        metrics_grid.setContentsMargins(16, 16, 16, 16)
        metrics_grid.setSpacing(15)
        
        # Create resource widgets
        self.cpu_status = ResourceStatusWidget("CPU Resources", 0, 0, 0, 0, 100, "cpu")
        self.memory_status = ResourceStatusWidget("Memory Resources", 0, 0, 0, 0, 100, "memory")
        self.disk_status = ResourceStatusWidget("Pod Resources", 0, 0, 0, 0, 100, "pods")
        
        # Set fixed width for alignment
        fixed_width = 180
        self.cpu_status.setFixedWidth(fixed_width)
        self.memory_status.setFixedWidth(fixed_width)
        self.disk_status.setFixedWidth(fixed_width)
        
        # Add widgets to grid
        metrics_grid.addWidget(self.cpu_status, 0, 0)
        metrics_grid.addWidget(self.memory_status, 0, 1)
        metrics_grid.addWidget(self.disk_status, 0, 2)
        
        # Set equal column stretches
        metrics_grid.setColumnStretch(0, 1)
        metrics_grid.setColumnStretch(1, 1)
        metrics_grid.setColumnStretch(2, 1)
        
        # Add to top section
        top_layout.addWidget(chart_panel, 1)
        top_layout.addWidget(metrics_container, 0)
        
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
        # Custom disabled style that clearly shows it's inactive and disabled
        disabled_style = """
            QPushButton {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: normal;
                opacity: 0.6;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #555555;
                border: 1px solid #333333;
                opacity: 0.5;
            }
        """
        self.master_btn.setStyleSheet(disabled_style)
        self.master_btn.setEnabled(False)  # Disable the Master button
        # self.master_btn.clicked.connect(self.show_master_data)  # Removed click handler
        
        self.worker_btn = QPushButton("Worker")
        self.worker_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
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
        
        # Create charts container
        self.charts_container = QWidget()
        self.charts_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.charts_layout = QStackedLayout(self.charts_container)
        self.charts_layout.setContentsMargins(0, 16, 0, 0)
        
        # Initialize charts
        self.cpu_chart = BarChart(color="#ff0000", title="CPU Usage", unit="%")
        self.memory_chart = BarChart(color="#00ffff", title="Memory Usage", unit="%")
        
        # Add charts to stacked layout
        self.charts_layout.addWidget(self.cpu_chart)
        self.charts_layout.addWidget(self.memory_chart)
        
        # Set CPU chart as current
        self.charts_layout.setCurrentWidget(self.cpu_chart)
        
        main_layout.addWidget(self.charts_container)

        return panel

    def show_master_data(self):
        self.master_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        self.worker_btn.setStyleSheet(AppStyles.CLUSTER_INACTIVE_BTN_STYLE)
        
    def show_worker_data(self):
        self.worker_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        # Keep Master button disabled style
        disabled_style = """
            QPushButton {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: normal;
                opacity: 0.6;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #555555;
                border: 1px solid #333333;
                opacity: 0.5;
            }
        """
        self.master_btn.setStyleSheet(disabled_style)

    def show_cpu_chart(self):
        self.cpu_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        self.memory_btn.setStyleSheet(AppStyles.CLUSTER_INACTIVE_BTN_STYLE)
        
        if hasattr(self, 'charts_layout') and self.charts_layout:
            self.charts_layout.setCurrentWidget(self.cpu_chart)

    def show_memory_chart(self):
        self.memory_btn.setStyleSheet(AppStyles.CLUSTER_ACTIVE_BTN_STYLE)
        self.cpu_btn.setStyleSheet(AppStyles.CLUSTER_INACTIVE_BTN_STYLE)
        
        if hasattr(self, 'charts_layout') and self.charts_layout:
            self.charts_layout.setCurrentWidget(self.memory_chart)
    
    def create_status_panel(self):
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        self.status_widget = QWidget()
        self.status_widget.setStyleSheet(AppStyles.CLUSTER_STATUS_PANEL_STYLE)
        
        self.stacked_layout = QStackedLayout(self.status_widget)
        self.stacked_layout.setContentsMargins(0, 0, 0, 0)
        
        # No issues content
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
        
        # Issues content
        issues_widget = QWidget()
        issues_layout = QVBoxLayout(issues_widget)
        issues_layout.setContentsMargins(16, 2, 16, 16)
        issues_layout.setSpacing(8)
        
        issues_header = QLabel("Cluster Issues")
        issues_header.setStyleSheet(AppStyles.CLUSTER_STATUS_TITLE_STYLE)
        issues_header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.issues_table = IssuesTable()
        
        issues_layout.addWidget(issues_header)
        issues_layout.addWidget(self.issues_table)
        
        # Add both widgets to stacked layout
        self.stacked_layout.addWidget(no_issues_widget)  # index 0
        self.stacked_layout.addWidget(issues_widget)     # index 1
        
        container_layout.addWidget(self.status_widget)
        return container
    
    def preload_with_cached_data(self, cluster_info, metrics, issues):
        """Preload the page with cached data"""
        logging.info(f"ClusterPage: Preloading with data for cluster: {cluster_info.get('name') if cluster_info else 'Unknown'}")
        try:
            if cluster_info:
                self.update_cluster_info(cluster_info)
            
            if metrics:
                self.update_metrics(metrics)
            else:
                # Show loading state for metrics-dependent UI elements
                logging.info("No cached metrics available, will wait for real data")

            if issues is not None: # Allow empty list of issues
                self.update_issues(issues)
            else:
                if hasattr(self, 'issues_table'): 
                    self.update_issues([])

            logging.info("Preloaded cluster page with cached data")
        except Exception as e:
            logging.error(f"Error preloading cached data: {e}")

    def update_metrics(self, metrics):
        """Update metrics with real data and maintain history"""
        logging.info(f"ClusterPage: update_metrics called with data: {metrics}")
        
        self.metrics_data = metrics
        if not metrics:
            logging.warning("ClusterPage: No metrics data to update.")
            return

        # Create hash to prevent excessive duplicate updates (allow some updates for chart progression)
        metrics_hash = hash(str(sorted(metrics.items()))) if metrics else None
        if hasattr(self, 'duplicate_count'):
            if self.last_metrics_hash == metrics_hash:
                self.duplicate_count += 1
                if self.duplicate_count < 3:  # Allow first 3 updates even if duplicate
                    logging.debug(f"ClusterPage: Allowing duplicate metrics update #{self.duplicate_count}")
                else:
                    logging.debug("ClusterPage: Skipping excessive duplicate metrics update")
                    return
            else:
                self.duplicate_count = 0
        else:
            self.duplicate_count = 0
        self.last_metrics_hash = metrics_hash

        logging.info(f"ClusterPage: Processing metrics with keys: {list(metrics.keys())}")
        
        try:
            # Update CPU metrics
            if "cpu" in metrics:
                cpu = metrics["cpu"]
                usage = float(cpu.get("usage", 0))
                requests = float(cpu.get("requests", 0))
                limits = float(cpu.get("limits", 0))
                allocatable = float(cpu.get("allocatable", 0))
                capacity = float(cpu.get("capacity", 100))
                
                logging.info(f"ClusterPage: Updating CPU - usage={usage}%, capacity={capacity}")
                
                if hasattr(self, 'cpu_status'):
                    self.cpu_status.update_metrics(usage, requests, limits, allocatable, capacity)
                    logging.info(f"ClusterPage: CPU status widget updated successfully")
                else:
                    logging.error("ClusterPage: cpu_status widget not found")
                
                # Update CPU chart with proper cleanup
                if hasattr(self, 'cpu_chart'):
                    # Add usage data (allow duplicate values to build up chart)
                    self.cpu_history.append(usage)
                    # Limit to max 8 points
                    if len(self.cpu_history) > self.max_history_points:
                        self.cpu_history = self.cpu_history[-self.max_history_points:]
                    
                    timestamps = cpu.get("timestamps", self._generate_time_points(len(self.cpu_history)))
                    self.cpu_chart.update_data(self.cpu_history.copy(), timestamps)
                    logging.info(f"ClusterPage: CPU chart updated successfully with {len(self.cpu_history)} points")
                else:
                    logging.error("ClusterPage: cpu_chart widget not found")
            
            # Update Memory metrics
            if "memory" in metrics:
                memory = metrics["memory"]
                usage = float(memory.get("usage", 0))
                requests = float(memory.get("requests", 0))
                limits = float(memory.get("limits", 0))
                allocatable = float(memory.get("allocatable", 0))
                capacity = float(memory.get("capacity", 100))
                
                logging.info(f"ClusterPage: Updating Memory - usage={usage}%, capacity={capacity}")
                
                if hasattr(self, 'memory_status'):
                    self.memory_status.update_metrics(usage, requests, limits, allocatable, capacity)
                    logging.info(f"ClusterPage: Memory status widget updated successfully")
                else:
                    logging.error("ClusterPage: memory_status widget not found")
                    
                # Update Memory chart with proper cleanup
                if hasattr(self, 'memory_chart'):
                    # Add usage data (allow duplicate values to build up chart)
                    self.memory_history.append(usage)
                    # Limit to max 8 points
                    if len(self.memory_history) > self.max_history_points:
                        self.memory_history = self.memory_history[-self.max_history_points:]
                    
                    timestamps = memory.get("timestamps", self._generate_time_points(len(self.memory_history)))
                    self.memory_chart.update_data(self.memory_history.copy(), timestamps)
                    logging.info(f"ClusterPage: Memory chart updated successfully with {len(self.memory_history)} points")
                else:
                    logging.error("ClusterPage: memory_chart widget not found")

            # Update Pod metrics
            if "pods" in metrics:
                pods = metrics["pods"]
                usage = float(pods.get("usage", 0))
                count = int(pods.get("count", 0))
                capacity = int(pods.get("capacity", 100))
                
                logging.info(f"ClusterPage: Updating Pods - usage={usage}%, count={count}, capacity={capacity}")
                
                if hasattr(self, 'disk_status'):
                    # For pods, we use count as requests and don't have limits/allocated
                    self.disk_status.update_metrics(usage, count, 0, 0, capacity)
                    logging.info(f"ClusterPage: Pod status widget updated successfully")
                else:
                    logging.error("ClusterPage: disk_status widget not found")
                    
            logging.info("ClusterPage: All metrics widgets updated successfully")
            
        except Exception as e:
            logging.error(f"ClusterPage: Error updating metrics UI: {e}")
            import traceback
            logging.error(f"ClusterPage: Full traceback: {traceback.format_exc()}")

    def update_issues(self, issues):
        """Update issues display with real data"""
        logging.info(f"ClusterPage: update_issues called with {len(issues) if issues else 0} issues")
        
        self.issues_data = issues if issues is not None else []
        
        try:
            if hasattr(self, 'stacked_layout') and hasattr(self, 'issues_table'):
                if self.issues_data:
                    logging.info(f"ClusterPage: Displaying {len(self.issues_data)} issues")
                    self.stacked_layout.setCurrentIndex(1)  # Show issues view
                    self.issues_table.update_issues(self.issues_data)
                else:
                    logging.info("ClusterPage: No issues found, showing success view")
                    self.stacked_layout.setCurrentIndex(0)  # Show no issues view
            else:
                logging.error("ClusterPage: Issues display widgets not found")
                
        except Exception as e:
            logging.error(f"ClusterPage: Error updating issues UI: {e}")

    def update_cluster_info(self, info):
        """Update cluster information from real data"""
        logging.info(f"ClusterPage: update_cluster_info called with: {info.get('name', 'Unknown') if info else 'None'}")
        self.cluster_info = info

    # Add this method to force an immediate UI update:
    def force_load_data(self):
        """Request fresh data for the current cluster if one is active."""
        if hasattr(self, '_loading') and self._loading:
            logging.debug("ClusterPage: force_load_data skipped - already loading")
            return
            
        logging.info("ClusterPage: force_load_data called - requesting fresh metrics and issues")
        self._loading = True
        try:
            # Reset duplicate counter and clear excessive historical data
            self.duplicate_count = 0
            self.last_metrics_hash = None
            # Don't clear all history, just limit it
            if len(self.cpu_history) > 2:
                self.cpu_history = self.cpu_history[-2:]
            if len(self.memory_history) > 2:
                self.memory_history = self.memory_history[-2:]
            
            # Clear chart data
            if hasattr(self, 'cpu_chart'):
                self.cpu_chart._clear_chart_data()
            if hasattr(self, 'memory_chart'):
                self.memory_chart._clear_chart_data()
                
            # Ensure signals are connected
            self._connect_cluster_signals()
            
            # Request fresh data
            self.refresh_data()
            
            # Also try to get any cached data immediately
            if hasattr(self, 'cluster_connector') and self.cluster_connector.current_cluster:
                cached_data = self.cluster_connector.get_cached_data(self.cluster_connector.current_cluster)
                if cached_data:
                    logging.info(f"ClusterPage: Found cached data: {list(cached_data.keys())}")
                    if 'metrics' in cached_data:
                        self.update_metrics(cached_data['metrics'])
                    if 'issues' in cached_data:
                        self.update_issues(cached_data['issues'])
                    if 'cluster_info' in cached_data:
                        self.update_cluster_info(cached_data['cluster_info'])
        finally:
            self._loading = False


    def _generate_time_points(self, count):
        """Generate time points for charts"""
        try:
            now = datetime.datetime.now()
            times = []
            
            # Calculate interval based on count
            if count <= 12:
                interval_minutes = 5
            elif count <= 24:
                interval_minutes = 2
            else:
                interval_minutes = 1
            
            for i in range(count):
                time_point = now - datetime.timedelta(minutes=(count - i) * interval_minutes)
                times.append(time_point.strftime("%H:%M"))
            
            return times
        except Exception as e:
            logging.error(f"Error generating time points: {e}")
            return [f"T{i}" for i in range(count)]

    def refresh_data(self):
        """Refresh cluster data"""
        try:
            logging.info("ClusterPage: Refreshing metrics and issues data")
            if self.cluster_connector and hasattr(self.cluster_connector, 'load_metrics'):
                self.cluster_connector.load_metrics()
            if self.cluster_connector and hasattr(self.cluster_connector, 'load_issues'):
                self.cluster_connector.load_issues()
        except Exception as e:
            logging.error(f"Error refreshing data: {e}")

    def showEvent(self, event):
        """Start refresh timer when page becomes visible"""
        super().showEvent(event)
        if not self.refresh_timer.isActive():
            self.refresh_timer.start(60000)  # Refresh every 60 seconds (reduced frequency)
            # Also refresh immediately when shown
            QTimer.singleShot(2000, self.refresh_data)  # Slight delay to prevent immediate overload

    def hideEvent(self, event):
        """Stop refresh timer when page is hidden and cleanup data"""
        super().hideEvent(event)
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        
        # Clear historical data when page is hidden to save memory
        if len(self.cpu_history) > 4:
            self.cpu_history = self.cpu_history[-4:]  # Keep only last 4 points
        if len(self.memory_history) > 4:
            self.memory_history = self.memory_history[-4:]  # Keep only last 4 points