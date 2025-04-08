from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QTabWidget, QGridLayout, QSizePolicy, QFrame, QToolTip)
from PyQt6.QtCore import Qt, QSize, QPoint, QRect, QEvent
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QCursor
import math

class BarChart(QWidget):
    def __init__(self, parent=None, color="#ff0000"):
        super().__init__(parent)
        self.color = QColor(color)
        # Increase minimum height to make the graph taller
        self.setMinimumHeight(300)  # Increased from 200
        self.setMouseTracking(True)  # Enable mouse tracking for hover effects
        self.hovered_bar = -1  # Track which bar is hovered
        
        # Sample data - heights in percentage (0-100)
        if color == "#ff0000":  # Red for CPU
            self.bar_data = [10, 40, 60, 20, 25, 15, 10, 40, 30, 15, 10, 20]
            self.chart_title = "CPU Usage"
        else:  # Cyan for Memory
            self.bar_data = [25, 50, 45, 30, 20, 5, 5, 10, 45, 40, 20, 10]
            self.chart_title = "Memory Usage"
            
        self.times = ["00:00", "01:00", "02:00", "03:00", "04:00", "05:00", 
                     "06:00", "07:00", "08:00", "09:00", "10:00", "11:00"]
        
        # Store bar positions for hover detection
        self.bar_positions = []

        # Style tooltips
        self.setStyleSheet("""
            QToolTip {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px;
                font-size: 12px;
            }
        """)

    def mouseMoveEvent(self, event):
        # Check if mouse is over any bar
        for i, rect in enumerate(self.bar_positions):
            if rect.contains(event.pos()):
                if self.hovered_bar != i:
                    self.hovered_bar = i
                    self.update()  # Redraw with new hover state
                    # Show tooltip with details
                    tooltip_text = f"{self.chart_title}\nTime: {self.times[i]}\nValue: {self.bar_data[i]}%"
                    QToolTip.showText(QCursor.pos(), tooltip_text, self)
                return
        
        # If not hovering any bar
        if self.hovered_bar != -1:
            self.hovered_bar = -1
            self.update()  # Redraw with no hover
            QToolTip.hideText()
        
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        # Reset hover state when mouse leaves the widget
        if self.hovered_bar != -1:
            self.hovered_bar = -1
            self.update()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Increase space for labels at the bottom even more
        chart_height = height - 120  # Increased from 100 to 120 for more space
        
        # Clear the bar positions for this paint cycle
        self.bar_positions = []
        
        # Draw y-axis labels and horizontal guidelines
        y_labels = ["0%", "20%", "40%", "60%", "80%", "100%"]
        for i, label in enumerate(y_labels):
            y = height - 120 - (i * chart_height / 5)  # Adjusted to use new bottom margin
            
            # First set pen for the guidelines (for all lines including 0%)
            painter.setPen(QPen(QColor("#333333"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(40, int(y), width, int(y))
            
            # Then set pen for the text - changed from white to light gray to remove borders
            painter.setPen(QColor("#aaaaaa"))
            painter.drawText(0, int(y) - 5, 30, 20, int(Qt.AlignmentFlag.AlignRight), label)
            
        # Calculate bar width and spacing
        bar_count = len(self.bar_data)
        available_width = width - 50
        bar_width = available_width / bar_count * 0.7
        bar_spacing = available_width / bar_count * 0.3
        
        # X-axis baseline - moved lower to give more space for labels
        painter.setPen(QPen(QColor("#333333"), 1, Qt.PenStyle.SolidLine))
        painter.drawLine(40, height - 120, width, height - 120)  # Adjusted to use new bottom margin
        
        # Draw bars - make sure we use no pen (no borders) for all bars
        for i, value in enumerate(self.bar_data):
            bar_height = (value / 100) * chart_height
            x = 40 + i * (bar_width + bar_spacing)
            y = height - 120 - bar_height  # Adjusted to use new bottom margin
            
            # Define bar rect and store it
            bar_rect = QRect(int(x), int(y), int(bar_width), int(bar_height))
            self.bar_positions.append(bar_rect)
            
            # Important: Set the pen explicitly to NoPen before drawing each bar
            # to ensure no white borders
            if i == self.hovered_bar:
                # Only for hovered bars we use a slight border effect
                if self.color == QColor("#ff0000"):  # Red
                    hover_color = QColor("#ff5555")
                else:  # Cyan
                    hover_color = QColor("#55ffff")
                painter.setBrush(QBrush(hover_color))
                # Thin gray border for hovered bars
                painter.setPen(QPen(QColor("#666666"), 1))
            else:
                # Explicitly no border for non-hovered bars
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(self.color))
                
            painter.drawRect(bar_rect)
            
            # Draw time labels - improved visibility with larger font and better positioning
            painter.setPen(QColor("#ffffff"))  # White for maximum visibility
            
            # Use a larger font for x-axis labels
            label_font = painter.font()
            label_font.setPointSize(10)  # Increased font size
            painter.setFont(label_font)
            
            # Calculate position - center of the bar
            x_center = x + (bar_width / 2)
            
            # Draw the time label with significantly more space below the chart
            # and increase the height of the text rectangle
            painter.drawText(
                int(x_center - 25),  # Keep x position centered
                height - 105,        # Move labels higher up (closer to the bars)
                50,                  # Width of the text area
                20,                  # Significant increase in height to ensure visibility
                int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop),  # Align top center
                self.times[i]
            )

class ResourceCircularIndicator(QWidget):
    def __init__(self, usage=0, requests=0, limits=0, allocated=0, capacity=100):
        super().__init__()
        self.usage = usage          # Current usage
        self.requests = requests    # Requested resources
        self.limits = limits        # Resource limits
        self.allocated = allocated  # Allocated capacity
        self.capacity = capacity    # Total capacity
        self.hovered_segment = None  # Track which segment is hovered
        self.setMinimumSize(120, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)  # Enable mouse tracking for hover
        self.title = ""  # Add a title property

        # Style tooltips
        self.setStyleSheet("""
            QToolTip {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px;
                font-size: 12px;
            }
        """)
        
    def set_title(self, title):
        self.title = title

    def get_segment_at_position(self, x, y):
        """Determine which segment (if any) contains the given point"""
        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2
        
        # Calculate distance from center
        dx = x - center_x
        dy = y - center_y
        distance = (dx**2 + dy**2)**0.5
        
        # Calculate angle (in degrees)
        angle = -1 * math.atan2(-dy, dx) * 180 / math.pi
        if angle < 0:
            angle += 360
            
        # Adjust to match the -90 degree start point in the paint event
        angle = (angle + 90) % 360
        
        # Ring sizes - same as in paint event
        size_factor = min(width, height) / 150
        
        # Define all ring radiuses
        outer_radius = min(width, height) / 2 - (10 * size_factor)
        ring4_radius = outer_radius - (8 * size_factor)
        ring3_radius = ring4_radius - (8 * size_factor)
        ring2_radius = ring3_radius - (8 * size_factor)
        inner_radius = ring2_radius - (8 * size_factor)
        
        # Check if point is within any ring
        if distance > outer_radius or distance < inner_radius - 5:
            return None
            
        # Calculate segment angles
        usage_angle = self.usage / self.capacity * 360
        requests_angle = self.requests / self.capacity * 360
        limits_angle = self.limits / self.capacity * 360
        allocated_angle = self.allocated / self.capacity * 360
        
        # Determine which segment the point is in based on the ring and angle
        if distance >= ring4_radius + 5:
            # In the outer ring (usage)
            return "usage" if angle <= usage_angle else None
        elif distance >= ring3_radius + 5:
            # In the second ring (requests)
            return "requests" if angle <= requests_angle else None
        elif distance >= ring2_radius + 5:
            # In the third ring (limits)
            return "limits" if angle <= limits_angle else None
        else:
            # In the inner ring (allocated)
            return "allocated" if angle <= allocated_angle else None

    def mouseMoveEvent(self, event):
        segment = self.get_segment_at_position(event.pos().x(), event.pos().y())
        
        if segment != self.hovered_segment:
            self.hovered_segment = segment
            self.update()
            
            # Show tooltip with details based on segment
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

        # Get dimensions for the circle
        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2

        # Ring sizes - make them proportional to widget size
        size_factor = min(width, height) / 150

        # Define all ring radiuses with even spacing
        outer_radius = min(width, height) / 2 - (10 * size_factor)
        ring4_radius = outer_radius - (8 * size_factor)
        ring3_radius = ring4_radius - (8 * size_factor)
        ring2_radius = ring3_radius - (8 * size_factor)
        inner_radius = ring2_radius - (8 * size_factor)

        # Scale pen width based on widget size
        pen_width = 6 * size_factor

        # Set up pen properties
        pen = QPen()
        pen.setWidth(max(3, int(pen_width)))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        # Draw the background circles
        pen.setColor(QColor(30, 30, 30))
        painter.setPen(pen)

        # Draw background rings
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

        # Start angle for all segments (same starting point)
        start_angle = -90 * 16  # Start at top (negative numbers go clockwise in Qt)

        # Draw the usage segment (green) on outer ring
        if self.usage > 0:
            # Normal vs hovered color
            color = QColor(80, 255, 80) if self.hovered_segment == "usage" else QColor(50, 220, 50)
            pen.setColor(color)
            painter.setPen(pen)
            segment_angle = int(self.usage / self.capacity * 360 * 16)
            painter.drawArc(int(center_x - outer_radius), int(center_y - outer_radius),
                            int(outer_radius * 2), int(outer_radius * 2),
                            start_angle, segment_angle)

        # Draw the requests segment (blue) on ring4
        if self.requests > 0:
            # Normal vs hovered color
            color = QColor(80, 180, 255) if self.hovered_segment == "requests" else QColor(50, 150, 220)
            pen.setColor(color)
            painter.setPen(pen)
            segment_angle = int(self.requests / self.capacity * 360 * 16)
            painter.drawArc(int(center_x - ring4_radius), int(center_y - ring4_radius),
                            int(ring4_radius * 2), int(ring4_radius * 2),
                            start_angle, segment_angle)

        # Draw the limits segment (purple) on ring3
        if self.limits > 0:
            # Normal vs hovered color
            color = QColor(200, 100, 255) if self.hovered_segment == "limits" else QColor(170, 70, 220)
            pen.setColor(color)
            painter.setPen(pen)
            segment_angle = int(self.limits / self.capacity * 360 * 16)
            painter.drawArc(int(center_x - ring3_radius), int(center_y - ring3_radius),
                            int(ring3_radius * 2), int(ring3_radius * 2),
                            start_angle, segment_angle)

        # Draw the allocated segment (orange) on ring2
        if self.allocated > 0:
            # Normal vs hovered color
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
    def __init__(self, title, usage=0, requests=0, limits=0, allocated=0, capacity=100):
        super().__init__()

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # Create a frame for the box background
        self.box = QFrame()
        self.box.setObjectName("statusBox")
        self.box.setStyleSheet("""
            #statusBox {
                background-color: #262626;
                border-radius: 5px;
                border: 1px solid transparent;
            }
            #statusBox:hover {
                background-color: #333333;
                border: 1px solid #4d4d4d;
            }
        """)

        # Box layout
        box_layout = QVBoxLayout(self.box)
        box_layout.setContentsMargins(10, 10, 10, 10)

        # Add title with bold font
        self.title = title
        title_label = QLabel(title)
        font = QFont()
        font.setBold(True)
        title_label.setFont(font)
        title_label.setStyleSheet("color: white; font-size: 16px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(title_label)

        # Add circular progress indicator
        self.progress = ResourceCircularIndicator(usage, requests, limits, allocated, capacity)
        self.progress.set_title(title)  # Set the title for tooltips
        self.progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        box_layout.addWidget(self.progress)

        # Add status labels - center-aligned with distinct colors
        self.usage_label = QLabel(f"● Usage: {usage}")
        self.usage_label.setStyleSheet("color: #32dc32;")  # Green
        self.usage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.usage_label)

        self.requests_label = QLabel(f"● Requests: {requests}")
        self.requests_label.setStyleSheet("color: #50a0ff;")  # Blue
        self.requests_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.requests_label)

        self.limits_label = QLabel(f"● Limits: {limits}")
        self.limits_label.setStyleSheet("color: #c050ff;")  # Purple
        self.limits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.limits_label)

        self.allocated_label = QLabel(f"● Allocated: {allocated}")
        self.allocated_label.setStyleSheet("color: #ff9428;")  # Orange
        self.allocated_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.allocated_label)

        # Add a capacity label
        self.capacity_label = QLabel(f"● Capacity: {capacity}")
        self.capacity_label.setStyleSheet("color: #d0d0d0;")  # Light gray
        self.capacity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.capacity_label)

        # Add the box to the main layout
        main_layout.addWidget(self.box)

        # Set widget to be transparent (the box inside has the background)
        self.setStyleSheet("background-color: transparent;")
        
    def update_metrics(self, usage, requests, limits, allocated, capacity=None):
        """Update metrics and labels"""
        self.progress.usage = usage
        self.progress.requests = requests
        self.progress.limits = limits
        self.progress.allocated = allocated
        if capacity is not None:
            self.progress.capacity = capacity
        self.progress.update()
        
        self.usage_label.setText(f"● Usage: {usage}")
        self.requests_label.setText(f"● Requests: {requests}")
        self.limits_label.setText(f"● Limits: {limits}")
        self.allocated_label.setText(f"● Allocated: {allocated}")
        
        if capacity is not None:
            self.capacity_label.setText(f"● Capacity: {capacity}")

    def sizeHint(self):
        return QSize(170, 300)

    def minimumSizeHint(self):
        return QSize(150, 270)

class ClusterPage(QWidget):
    # Define reusable button styles as class variables
    ACTIVE_BTN_STYLE = """
        QPushButton {
            background-color: #333333;
            color: #ffffff;
            border: none;
            padding: 6px 16px;
            font-size: 13px;
            border-radius: 4px;
        }
    """
    
    INACTIVE_BTN_STYLE = """
        QPushButton {
            background-color: transparent;
            color: #888888;
            border: none;
            padding: 6px 16px;
            font-size: 13px;
        }
        QPushButton:hover {
            color: #ffffff;
        }
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add content area (no more tab container)
        content_area = self.create_content_area()
        layout.addWidget(content_area)

    def create_content_area(self):
        content_widget = QWidget()
        content_layout = QGridLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)

        # First panel with the charts - now with aligned tabs
        chart_panel = self.create_chart_panel()
        
        # Create a horizontal layout for the circular indicators
        metrics_widget = QWidget()
        metrics_widget.setStyleSheet("background-color: #1e1e1e; border-radius: 4px;")
        metrics_layout = QHBoxLayout(metrics_widget)
        metrics_layout.setContentsMargins(16, 16, 16, 16)
        metrics_layout.setSpacing(15)
        
        # Create individual ResourceStatusWidget instances with sample values
        # Arguments: title, usage, requests, limits, allocated, capacity
        self.cpu_status = ResourceStatusWidget("CPU Resources", 60, 75, 90, 80, 100)
        self.memory_status = ResourceStatusWidget("Memory Resources", 40, 65, 80, 70, 100)
        self.disk_status = ResourceStatusWidget("Storage Resources", 30, 50, 75, 60, 100)
        
        # Add them directly to the horizontal layout
        metrics_layout.addWidget(self.cpu_status)
        metrics_layout.addWidget(self.memory_status)
        metrics_layout.addWidget(self.disk_status)
        
        # Status panel (the one with the green checkmark)
        status_panel = self.create_status_panel()

        # Add all panels to the grid layout
        content_layout.addWidget(chart_panel, 0, 0)
        content_layout.addWidget(metrics_widget, 0, 1)
        content_layout.addWidget(status_panel, 1, 0, 1, 2)

        return content_widget

    def create_chart_panel(self):
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-radius: 4px;
            }
        """)

        # Create a vertical layout for the entire panel
        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Add a single row of tabs with both sets of buttons aligned
        tabs = QWidget()
        tabs_layout = QHBoxLayout(tabs)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(4)
        
        # Add Master/Worker buttons on the left
        self.master_btn = QPushButton("Master")
        self.master_btn.setStyleSheet(self.ACTIVE_BTN_STYLE)
        self.master_btn.clicked.connect(self.show_master_data)
        
        self.worker_btn = QPushButton("Worker")
        self.worker_btn.setStyleSheet(self.INACTIVE_BTN_STYLE)
        self.worker_btn.clicked.connect(self.show_worker_data)
        
        tabs_layout.addWidget(self.master_btn)
        tabs_layout.addWidget(self.worker_btn)
        
        # Add a stretching space to push CPU/Memory buttons to the right
        tabs_layout.addStretch()
        
        # Add CPU/Memory buttons on the right
        self.cpu_btn = QPushButton("CPU")
        self.cpu_btn.setStyleSheet(self.ACTIVE_BTN_STYLE)
        self.cpu_btn.clicked.connect(self.show_cpu_chart)

        self.memory_btn = QPushButton("Memory")
        self.memory_btn.setStyleSheet(self.INACTIVE_BTN_STYLE)
        self.memory_btn.clicked.connect(self.show_memory_chart)

        tabs_layout.addWidget(self.cpu_btn)
        tabs_layout.addWidget(self.memory_btn)
        
        # Add the tabs to the main layout
        main_layout.addWidget(tabs)
        
        # Create charts container
        charts = QWidget()
        charts.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        charts_layout = QVBoxLayout(charts)
        charts_layout.setContentsMargins(0, 16, 0, 0)
        
        # Create the charts with increased height
        self.cpu_chart = BarChart(color="#ff0000")  # Red for CPU
        self.memory_chart = BarChart(color="#00ffff")  # Cyan for Memory
        
        # Set size policies to make charts expand
        self.cpu_chart.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.memory_chart.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Initially show only CPU chart
        self.memory_chart.hide()
        
        charts_layout.addWidget(self.cpu_chart)
        charts_layout.addWidget(self.memory_chart)

        # Add chart container to main layout
        main_layout.addWidget(charts)

        return panel
    
    # Button click handlers for the Master/Worker tabs
    def show_master_data(self):
        self.master_btn.setStyleSheet(self.ACTIVE_BTN_STYLE)
        self.worker_btn.setStyleSheet(self.INACTIVE_BTN_STYLE)
        # Here you would update chart data to show master node data
        # For now, we'll just keep this as a placeholder
        
    def show_worker_data(self):
        self.worker_btn.setStyleSheet(self.ACTIVE_BTN_STYLE)
        self.master_btn.setStyleSheet(self.INACTIVE_BTN_STYLE)
        # Here you would update chart data to show worker node data
        # For now, we'll just keep this as a placeholder

    # Button click handlers for the CPU/Memory tabs
    def show_cpu_chart(self):
        self.cpu_btn.setStyleSheet(self.ACTIVE_BTN_STYLE)
        self.memory_btn.setStyleSheet(self.INACTIVE_BTN_STYLE)
        self.cpu_chart.show()
        self.memory_chart.hide()
        
    def show_memory_chart(self):
        self.memory_btn.setStyleSheet(self.ACTIVE_BTN_STYLE)
        self.cpu_btn.setStyleSheet(self.INACTIVE_BTN_STYLE)
        self.memory_chart.show()
        self.cpu_chart.hide()

    def create_status_panel(self):
        panel = QWidget()
        panel.setStyleSheet("""
            background-color: #1e1e1e;
            border-radius: 4px;
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 48, 32, 48)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Success icon
        success_icon = QLabel("✓")
        success_icon.setFixedSize(80, 80)
        success_icon.setStyleSheet("""
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

        status_subtitle = QLabel("All resources are within acceptable limits")
        status_subtitle.setStyleSheet("""
            color: #888888;
            font-size: 14px;
            margin-top: 4px;
        """)
        status_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(success_icon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_title)
        layout.addWidget(status_subtitle)

        return panel
    
    def update_metrics(self, cpu_metrics=None, memory_metrics=None, disk_metrics=None):
        """Update the metrics displays with new data"""
        if cpu_metrics:
            self.cpu_status.update_metrics(
                cpu_metrics.get("usage", 0),
                cpu_metrics.get("requests", 0),
                cpu_metrics.get("limits", 0),
                cpu_metrics.get("allocated", 0),
                cpu_metrics.get("capacity", 100)
            )
            
        if memory_metrics:
            self.memory_status.update_metrics(
                memory_metrics.get("usage", 0),
                memory_metrics.get("requests", 0),
                memory_metrics.get("limits", 0),
                memory_metrics.get("allocated", 0),
                memory_metrics.get("capacity", 100)
            )
            
        if disk_metrics:
            self.disk_status.update_metrics(
                disk_metrics.get("usage", 0),
                disk_metrics.get("requests", 0),
                disk_metrics.get("limits", 0),
                disk_metrics.get("allocated", 0),
                disk_metrics.get("capacity", 100)
            )