from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QFrame, QGraphicsDropShadowEffect, QSizePolicy,
                           QGridLayout, QScrollArea, QToolTip)
from PyQt6.QtCore import Qt, QRectF, QPointF, QEvent
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QPainterPath, QFont, QCursor
import math

class ResourceStatus:
    """Class to represent status of a resource"""
    RUNNING = "Running"
    STOPPED = "Stopped"
    IN_PROCESS = "In Process"


class ResourceDonutChart(QWidget):
    """Widget to display a small donut chart for a specific resource"""
    def __init__(self, resource_name, counts, parent=None):
        """
        Initialize with resource details and counts
        
        Args:
            resource_name (str): Name of the resource
            counts (dict): Dictionary with keys 'running', 'stopped', 'in_process', and 'total'
        """
        super().__init__(parent)
        self.resource_name = resource_name
        self.counts = counts
        
        # Define specific colors for different statuses as requested
        self.status_colors = {
            ResourceStatus.RUNNING: "#ff7808",    # Orange
            ResourceStatus.STOPPED: "#df0f0f",    # Red
            ResourceStatus.IN_PROCESS: "#1bbd02"  # Green
        }
        
        # Set fixed size for the small chart - increased size for larger radius
        self.setMinimumSize(150, 150)  # Increased from 120, 120
        self.setMaximumSize(180, 180)  # Increased from 150, 150
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get chart area geometry
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        # Increased outer radius by reducing the padding
        outer_radius = min(self.width(), self.height()) // 2 - 5  # Changed from 10 to 5
        inner_radius = outer_radius * 0.8  # Large inner radius for thin ring
        
        # Initialize starting angle (start from top, clockwise)
        start_angle = 90
        
        # Draw background circle if total is 0
        if self.counts['total'] == 0:
            # Draw outer circle
            painter.setPen(QPen(QColor("#333333"), 1))
            painter.setBrush(QBrush(QColor("#2d2d2d")))
            painter.drawEllipse(
                int(center_x - outer_radius),
                int(center_y - outer_radius),
                int(outer_radius * 2),
                int(outer_radius * 2)
            )
            
            # Draw inner circle (donut hole)
            painter.setBrush(QBrush(QColor("#1e1e1e")))
            painter.drawEllipse(
                int(center_x - inner_radius),
                int(center_y - inner_radius),
                int(inner_radius * 2),
                int(inner_radius * 2)
            )
            
            font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QPen(QColor("#888888")))
            painter.drawText(
                QRectF(center_x - inner_radius, center_y - inner_radius, inner_radius * 2, inner_radius * 2),
                Qt.AlignmentFlag.AlignCenter,
                "No Data"
            )
            return
        
        # Draw segments for different statuses
        segments = [
            (ResourceStatus.RUNNING, self.counts['running']),
            (ResourceStatus.STOPPED, self.counts['stopped']),
            (ResourceStatus.IN_PROCESS, self.counts['in_process'])
        ]
        
        # Filter out zero counts
        segments = [(status, count) for status, count in segments if count > 0]
        
        for i, (status, count) in enumerate(segments):
            # Skip if count is 0
            if count == 0:
                continue
                
            # Calculate slice angle
            slice_angle = (count / self.counts['total']) * 360
            
            # Get color for this status
            color = self.status_colors.get(status, "#cccccc")  # Default gray if status not found
            
            # Draw outer arc
            path = QPainterPath()
            
            # Start arc - outer edge
            path.arcMoveTo(
                int(center_x - outer_radius),
                int(center_y - outer_radius),
                int(outer_radius * 2),
                int(outer_radius * 2),
                start_angle
            )
            
            # Draw outer arc
            path.arcTo(
                int(center_x - outer_radius),
                int(center_y - outer_radius),
                int(outer_radius * 2),
                int(outer_radius * 2),
                start_angle,
                -slice_angle
            )
            
            # Draw line to inner arc
            end_angle = start_angle - slice_angle
            end_x = center_x + inner_radius * math.cos(math.radians(end_angle))
            end_y = center_y - inner_radius * math.sin(math.radians(end_angle))
            path.lineTo(end_x, end_y)
            
            # Draw inner arc
            path.arcTo(
                int(center_x - inner_radius),
                int(center_y - inner_radius),
                int(inner_radius * 2),
                int(inner_radius * 2),
                end_angle,
                slice_angle
            )
            
            # Close path
            path.closeSubpath()
            
            # Set pen and brush - made slightly thicker for better visibility
            painter.setPen(QPen(QColor(color).darker(110), 1.5))  # Increased from 1 to 1.5
            painter.setBrush(QBrush(QColor(color)))
            painter.drawPath(path)
            
            # Update starting angle for next slice
            start_angle -= slice_angle
        
        # Draw center hole (clean up any artifacts)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#1e1e1e")))
        painter.drawEllipse(
            int(center_x - inner_radius),
            int(center_y - inner_radius),
            int(inner_radius * 2),
            int(inner_radius * 2)
        )
        
        # Choose text color based on primary status
        # If running counts are highest, use running color, otherwise use white
        primary_status = max(segments, key=lambda x: x[1])[0] if segments else None
        text_color = self.status_colors.get(primary_status, "#ffffff") if primary_status else "#ffffff"
        
        # Draw resource name and count in the center
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(text_color)))
        
        # Draw the resource name
        name_rect = QRectF(
            center_x - inner_radius,
            center_y - 12,
            inner_radius * 2,
            15
        )
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, self.resource_name)
        
        # Draw the count below
        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#FFFFFF")))
        
        count_rect = QRectF(
            center_x - inner_radius,
            center_y + 3,
            inner_radius * 2,
            15
        )
        painter.drawText(count_rect, Qt.AlignmentFlag.AlignCenter, f"{self.counts['running']}/{self.counts['total']}")


class ResourcesOverviewWidget(QFrame):
    """Widget to display individual donut charts for each resource type"""
    def __init__(self, resources_data, parent=None):
        """
        Initialize with resource data
        
        Args:
            resources_data: List of tuples (name, total, running, stopped, in_process)
        """
        super().__init__(parent)
        self.resources_data = resources_data
        
        # Styling
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 4px;
                border: 1px solid #2d2d2d;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#scrollContents {
                background-color: transparent;
            }
        """)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Add header
        header = QLabel("Resource Status")
        header.setStyleSheet("""
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
        """)
        layout.addWidget(header)
        
        # Add color legend
        # legend_frame = QFrame()
        legend_layout = QHBoxLayout()
        legend_layout.setContentsMargins(0, 0, 0, 10)
        legend_layout.setSpacing(15)
        
        # Add legend items
        status_colors = {
            ResourceStatus.RUNNING: "#ff7808",
            ResourceStatus.STOPPED: "#df0f0f",
            ResourceStatus.IN_PROCESS: "#1bbd02"
        }
        
        for status, color in status_colors.items():
            legend_item = QHBoxLayout()
            legend_item.setSpacing(5)
            
            # Color indicator
            color_indicator = QFrame()
            color_indicator.setFixedSize(12, 12)
            color_indicator.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
            
            # Status label
            status_label = QLabel(status)
            status_label.setStyleSheet(f"color: #ffffff; font-size: 12px;")
            
            legend_item.addWidget(color_indicator)
            legend_item.addWidget(status_label)
            legend_layout.addLayout(legend_item)
        
        legend_layout.addStretch()
        layout.addLayout(legend_layout)
        
        # Create scroll area for donut charts
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create widget to hold charts
        scroll_contents = QWidget()
        scroll_contents.setObjectName("scrollContents")
        
        # Grid layout for charts - adjusted for larger chart sizes
        grid_layout = QGridLayout(scroll_contents)
        grid_layout.setContentsMargins(10, 10, 10, 10)
        grid_layout.setSpacing(20)
        
        # Add individual charts for each resource
        # Using 2 charts per row since they're larger
        charts_per_row = 4
        
        for i, resource in enumerate(self.resources_data):
            name, total, running, stopped, in_process = resource
            
            # Create counts dictionary
            counts = {
                'total': total,
                'running': running,
                'stopped': stopped,
                'in_process': in_process
            }
            
            # Create chart widget
            chart = ResourceDonutChart(name, counts)
            
            # Add to grid layout - 2 charts per row
            row = i // charts_per_row
            col = i % charts_per_row
            grid_layout.addWidget(chart, row, col, Qt.AlignmentFlag.AlignCenter)
        
        # Add empty widgets to fill any remaining grid cells
        # remaining = (charts_per_row - (len(self.resources_data) % charts_per_row)) % charts_per_row
        # for i in range(remaining):
        #     empty_widget = QWidget()
        #     empty_widget.setMinimumSize(150, 150)  # Match the chart size
        #     grid_layout.addWidget(empty_widget, len(self.resources_data) // charts_per_row, 
        #                         (len(self.resources_data) % charts_per_row) + i)
        
        # Set scroll area widget
        scroll_area.setWidget(scroll_contents)
        layout.addWidget(scroll_area)


class OverviewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Overview")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #ffffff;
        """)
        
        # Add count of total resources
        items_count = QLabel("7 items")
        items_count.setStyleSheet("""
            color: #9ca3af;
            font-size: 12px;
            margin-left: 8px;
            font-family: 'Segoe UI';
        """)
        items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(items_count)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Format: (name, total, running, stopped, in_process)
        resources_data = [
            ("Pods", 9, 7, 1, 1),             
            ("Deployments", 1, 1, 0, 0),      
            ("Daemon Sets", 1, 1, 0, 0),      
            ("Stateful Sets", 2, 2, 0, 0),    
            ("Replica Sets", 1, 1, 0, 0),     
            ("Jobs", 3, 2, 1, 0),             
            ("Cron Jobs", 4, 3, 0, 1)         
        ]
        
        # Create the resources overview widget
        resources_widget = ResourcesOverviewWidget(resources_data)
        
        layout.addWidget(resources_widget)
        layout.addStretch()


# For testing
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = OverviewPage()
    window.setStyleSheet("background-color: #121212;")
    window.resize(800, 600)
    window.show()
    
    sys.exit(app.exec())