from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QFrame, QGraphicsDropShadowEffect, QSizePolicy, QListWidget, 
                           QListWidgetItem, QToolTip)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPoint, QEvent
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

import math

class WorkloadItem:
    def __init__(self, name, count, color):
        self.name = name
        self.count = count
        self.color = color
        self.angle = 0  # Will be calculated based on percentage
        self.percentage = 0  # Will be calculated based on total
        self.start_angle = 0  # Starting angle in degrees
        self.end_angle = 0  # Ending angle in degrees

class ConsolidatedPieChart(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.total_count = 0
        self.animation_step = 0
        self.max_animation_steps = 60  # Animation will take 60 frames
        self.selected_item = None
        self.hovered_item = None
        
        # Visual properties
        self.setMinimumSize(350, 350)
        self.setMaximumSize(450, 450)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # Styling
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 6px;
                border: 1px solid #2d2d2d;
            }
        """)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        
        # Create animation for pie chart
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate_chart)
        
    def add_item(self, name, count, color):
        item = WorkloadItem(name, count, color)
        self.items.append(item)
        self.total_count += count
        self.calculate_percentages()
        
    def calculate_percentages(self):
        current_angle = 0
        for item in self.items:
            if self.total_count > 0:
                item.percentage = (item.count / self.total_count * 100)
                item.angle = item.percentage * 3.6  # Convert percentage to degrees (360 / 100)
            else:
                item.percentage = 0
                item.angle = 0
                
            item.start_angle = current_angle
            current_angle += item.angle
            item.end_angle = current_angle
            
    def start_animation(self):
        self.animation_step = 0
        self.animation_timer.start(16)  # ~60fps
        
    def animate_chart(self):
        self.animation_step += 1
        if self.animation_step >= self.max_animation_steps:
            self.animation_timer.stop()
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if not self.items:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set up drawing area
        width = self.width() - 60  # Account for margins
        height = width  # Make it a square
        radius = min(width, height) / 2
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # Calculate animation progress (0 to 1)
        progress = min(self.animation_step / self.max_animation_steps, 1.0)
        
        # Draw pie slices
        current_angle = 0
        for item in self.items:
            if item.count == 0:
                continue
                
            # Calculate slice angles with animation
            animated_angle = item.angle * progress
            start_angle = current_angle
            
            if animated_angle > 0:
                # Add arc to path
                x = int(center_x - radius)
                y = int(center_y - radius)
                w = int(radius * 2)
                h = int(radius * 2)
                
                # Adjust color brightness for hovered/selected items
                color = QColor(item.color)
                if item == self.hovered_item:
                    # Make brighter
                    color = color.lighter(120)
                elif item == self.selected_item:
                    # Make slightly brighter
                    color = color.lighter(110)
                
                # Draw slice
                painter.setBrush(color)
                
                # Define pen based on selection
                if item == self.selected_item:
                    pen_width = 2
                    pen_color = QColor("#ffffff")
                else:
                    pen_width = 1
                    pen_color = QColor("#2d2d2d")
                
                painter.setPen(QPen(pen_color, pen_width))
                
                # Calculate points for slice
                path = QPainterPath()
                path.moveTo(center_x, center_y)
                path.arcTo(x, y, w, h, start_angle, animated_angle)
                path.closeSubpath()
                
                # Draw the slice
                painter.drawPath(path)
                
            current_angle += animated_angle
        
        # Draw inner circle (hole) with shadow effect
        inner_radius = radius * 0.6
        
        # Draw shadow for inner circle
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            int(center_x - inner_radius + 2),
            int(center_y - inner_radius + 2),
            int(inner_radius * 2),
            int(inner_radius * 2)
        )
        
        # Draw inner circle
        painter.setBrush(QColor("#1e1e1e"))
        painter.setPen(QPen(QColor("#2d2d2d"), 1))
        painter.drawEllipse(
            int(center_x - inner_radius),
            int(center_y - inner_radius),
            int(inner_radius * 2),
            int(inner_radius * 2)
        )
        
        # Draw total count in the center
        painter.setPen(QPen(QColor("#999999")))
        painter.setFont(QFont("Segoe UI", 14, QFont.Weight.Normal))
        painter.drawText(QRectF(center_x - inner_radius, center_y - inner_radius / 2 - 10, 
                        inner_radius * 2, inner_radius), 
                        Qt.AlignmentFlag.AlignCenter, "Total")
        
        painter.setPen(QPen(QColor("#ffffff")))
        painter.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        painter.drawText(QRectF(center_x - inner_radius, center_y - inner_radius / 2 + 10, 
                        inner_radius * 2, inner_radius), 
                        Qt.AlignmentFlag.AlignCenter, str(self.total_count))
                        
        # If item is hovered, draw a tooltip directly on the chart
        if self.hovered_item and self.hovered_item.count > 0:
            # Calculate position for the tooltip (middle of the pie slice)
            mid_angle = self.hovered_item.start_angle + (self.hovered_item.angle / 2)
            mid_angle_rad = mid_angle * (math.pi / 180)
            
            # Position the tooltip
            tooltip_distance = radius * 0.8
            tooltip_x = center_x + tooltip_distance * math.cos(mid_angle_rad)
            tooltip_y = center_y + tooltip_distance * math.sin(mid_angle_rad)
            
            # Adjust the tooltip position to keep it inside the view
            tooltip_width = 180
            tooltip_height = 36
            
            # Ensure tooltip stays within widget bounds
            if tooltip_x - tooltip_width/2 < 10:
                tooltip_x = 10 + tooltip_width/2
            elif tooltip_x + tooltip_width/2 > self.width() - 10:
                tooltip_x = self.width() - 10 - tooltip_width/2
                
            if tooltip_y - tooltip_height/2 < 10:
                tooltip_y = 10 + tooltip_height/2
            elif tooltip_y + tooltip_height/2 > self.height() - 10:
                tooltip_y = self.height() - 10 - tooltip_height/2
            
            # Prepare tooltip text
            tooltip_text = f"{self.hovered_item.name}: {self.hovered_item.count} ({self.hovered_item.percentage:.1f}%)"
            
            # Draw tooltip background
            tooltip_rect = QRectF(tooltip_x - tooltip_width/2, tooltip_y - tooltip_height/2, 
                                 tooltip_width, tooltip_height)
            
            # Draw tooltip with rounded corners and shadow
            # First draw shadow
            shadow_rect = QRectF(tooltip_rect.x() + 2, tooltip_rect.y() + 2, 
                               tooltip_rect.width(), tooltip_rect.height())
            painter.setBrush(QColor(0, 0, 0, 50))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(shadow_rect, 5, 5)
            
            # Then draw tooltip
            painter.setBrush(QColor(60, 60, 60, 240))
            painter.setPen(QPen(QColor("#555555"), 1))
            painter.drawRoundedRect(tooltip_rect, 5, 5)
            
            # Draw color indicator
            indicator_rect = QRectF(tooltip_rect.x() + 5, tooltip_rect.y() + tooltip_rect.height() - 7, 
                                  24, 4)
            painter.setBrush(QColor(self.hovered_item.color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(indicator_rect, 2, 2)
            
            # Draw tooltip text
            painter.setPen(QPen(QColor("#ffffff")))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(tooltip_rect, Qt.AlignmentFlag.AlignCenter, tooltip_text)
    
    def mouseMoveEvent(self, event):
        # Find which section is under the cursor and update hover state
        pos = event.position()
        hovered_item = self.get_item_at_position(pos)
        
        if hovered_item != self.hovered_item:
            self.hovered_item = hovered_item
            self.update()
            
            # Notify parent about the hover (for info panel update)
            if hasattr(self.parent(), "hover_workload") and hovered_item and hovered_item.count > 0:
                self.parent().hover_workload(hovered_item)
    
    def leaveEvent(self, event):
        # Clear hover state when mouse leaves
        if self.hovered_item:
            self.hovered_item = None
            self.update()
            
            # Reset info panel if a workload was selected
            if hasattr(self.parent(), "reset_hover") and self.selected_item:
                self.parent().reset_hover()
    
    def mouseReleaseEvent(self, event):
        # Find which section was clicked
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            clicked_item = self.get_item_at_position(pos)
            
            if clicked_item and clicked_item.count > 0:
                self.selected_item = clicked_item
                self.update()
                
                # Notify parent about the selection
                if hasattr(self.parent(), "select_workload"):
                    self.parent().select_workload(clicked_item)
    
    def get_item_at_position(self, pos):
        # Convert to widget coordinates
        x = pos.x() - self.width() / 2
        y = pos.y() - self.height() / 2
        
        # Calculate distance from center
        distance = math.sqrt(x*x + y*y)
        
        # Check if click is inside the outer ring of the pie chart
        radius = min(self.width(), self.height()) / 2 - 30
        inner_radius = radius * 0.6
        
        if distance < inner_radius or distance > radius:
            return None
            
        # Calculate angle of click in degrees
        angle = math.degrees(math.atan2(y, x))
        if angle < 0:
            angle += 360
            
        # Find which slice contains this angle
        for item in self.items:
            if item.count == 0:
                continue
                
            # Check if angle is between start and end angles
            if item.start_angle <= angle <= item.end_angle:
                return item
                
        return None

class InfoPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 4px;
                border: 1px solid #2d2d2d;
            }
        """)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)
        
        # Title section
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 8)
        title_layout.setSpacing(8)
        
        # Color dot 
        self.color_dot = QFrame()
        self.color_dot.setFixedSize(12, 12)
        self.color_dot.setStyleSheet("background-color: #2196F3; border-radius: 6px;")
        
        # Title
        self.title = QLabel("Resource Details")
        self.title.setStyleSheet("""
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
        """)
        
        title_layout.addWidget(self.color_dot)
        title_layout.addWidget(self.title)
        title_layout.addStretch()
        
        self.layout.addLayout(title_layout)
        
        # Add color indicator
        self.color_indicator = QFrame()
        self.color_indicator.setFixedHeight(4)
        self.color_indicator.setStyleSheet("background-color: #2196F3; border-radius: 2px;")
        self.layout.addWidget(self.color_indicator)
        
        # Add divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #2d2d2d;")
        divider.setFixedHeight(1)
        self.layout.addWidget(divider)
        
        # Add info sections with placeholder data
        self.type_value = self.add_info_section("Type", "No resource selected")
        self.count_value = self.add_info_section("Count", "0")
        self.status_value = self.add_info_section("Status", "N/A")
        self.usage_value = self.add_info_section("Resource Usage", "N/A")
        
        # Add second divider
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet("background-color: #2d2d2d;")
        divider2.setFixedHeight(1)
        self.layout.addWidget(divider2)
        
        # Description section
        description_label = QLabel("Description")
        description_label.setStyleSheet("""
            color: #9ca3af;
            font-size: 12px;
            margin-top: 8px;
        """)
        
        self.description_value = QLabel("Information about the selected workload type")
        self.description_value.setStyleSheet("""
            color: #e2e8f0;
            font-size: 14px;
            line-height: 1.5;
            margin-top: 4px;
        """)
        self.description_value.setWordWrap(True)
        
        self.layout.addWidget(description_label)
        self.layout.addWidget(self.description_value)
        
        self.layout.addStretch()
        
        # Is in hover mode flag
        self.in_hover_mode = False
        self.previous_data = None
    
    def add_info_section(self, label_text, value_text):
        section = QWidget()
        section_layout = QHBoxLayout(section)
        section_layout.setContentsMargins(0, 8, 0, 8)
        section_layout.setSpacing(8)
        
        label = QLabel(label_text)
        label.setStyleSheet("""
            color: #9ca3af;
            font-size: 13px;
        """)
        label.setFixedWidth(120)
        
        value = QLabel(value_text)
        value.setStyleSheet("""
            color: #ffffff;
            font-size: 15px;
            font-weight: bold;
        """)
        
        section_layout.addWidget(label)
        section_layout.addWidget(value)
        
        self.layout.addWidget(section)
        return value  # Return value label for later updates
    
    def update_info(self, workload_item, total, is_hover=False):
        if not workload_item:
            return
        
        if is_hover:
            if not self.in_hover_mode:
                # Save current data for restoring later
                self.previous_data = (self.title.text(), self.color_indicator.styleSheet())
                self.in_hover_mode = True
        else:
            # Permanently update for selection
            self.in_hover_mode = False
            self.previous_data = None
        
        # Update info panel with selected workload data
        self.title.setText(f"{workload_item.name}")
        
        # Update color indicator and dot
        self.color_indicator.setStyleSheet(f"background-color: {workload_item.color}; border-radius: 2px;")
        self.color_dot.setStyleSheet(f"background-color: {workload_item.color}; border-radius: 6px;")
        
        # Update values
        self.type_value.setText(workload_item.name)
        self.count_value.setText(f"{workload_item.count} / {total}")
        
        if workload_item.count > 0:
            self.status_value.setText("Running")
            self.status_value.setStyleSheet("""
                color: #4CAF50;
                font-size: 15px;
                font-weight: bold;
            """)
        else:
            self.status_value.setText("None")
            self.status_value.setStyleSheet("""
                color: #ffffff;
                font-size: 15px;
                font-weight: bold;
            """)
            
        self.usage_value.setText(f"{workload_item.percentage:.1f}% of workloads")
        
        # Update description based on workload type
        descriptions = {
            "Pods": "The smallest deployable units of computing that you can create and manage in Kubernetes.",
            "Deployments": "Provides declarative updates for Pods and ReplicaSets.",
            "Daemon Sets": "Ensures that all (or some) Nodes run a copy of a Pod.",
            "Stateful Sets": "Manages the deployment and scaling of a set of Pods with persistent storage.",
            "Replica Sets": "Ensures that a specified number of pod replicas are running at any given time.",
            "Jobs": "Creates one or more Pods and ensures that a specified number of them successfully terminate.",
            "Cron Jobs": "Creates Jobs on a repeating schedule."
        }
        
        self.description_value.setText(descriptions.get(workload_item.name, 
                                                     "Information about this workload type"))
    
    def reset_hover(self):
        if self.in_hover_mode and self.previous_data:
            self.title.setText(self.previous_data[0])
            self.color_indicator.setStyleSheet(self.previous_data[1])
            self.color_dot.setStyleSheet(self.previous_data[1])
            self.in_hover_mode = False

class LegendWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 4px;
                border: 1px solid #2d2d2d;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
                font-size: 14px;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 8px 4px;
                border: none;
            }
            QListWidget::item:selected {
                background-color: rgba(33, 150, 243, 0.2);
                border-radius: 4px;
            }
        """)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(8)
        
        # Title
        title = QLabel("Workload Types")
        title.setStyleSheet("""
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
        """)
        
        self.layout.addWidget(title)
        
        # Legend list
        self.list_widget = QListWidget()
        self.list_widget.setFixedHeight(250)
        self.layout.addWidget(self.list_widget)
        
        # Connect item clicked signal
        self.list_widget.itemClicked.connect(self.item_clicked)
        
        # Store legend items for selection
        self.legend_items = []
    
    def add_legend_item(self, workload_item):
        item = QListWidgetItem()
        
        # Create custom widget for the item
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Color indicator
        color_indicator = QFrame()
        color_indicator.setFixedSize(12, 12)
        color_indicator.setStyleSheet(f"background-color: {workload_item.color}; border-radius: 6px;")
        
        # Name label
        name_label = QLabel(workload_item.name)
        name_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        # Count label
        count_label = QLabel(str(workload_item.count))
        count_label.setStyleSheet("color: #9ca3af; font-size: 14px;")
        count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        layout.addWidget(color_indicator)
        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(count_label)
        
        # Set item properties
        item.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)
        
        # Store workload item reference for selection
        item.setData(Qt.ItemDataRole.UserRole, workload_item)
        self.legend_items.append(item)
        
        return item
    
    def item_clicked(self, item):
        # Get associated workload item
        workload_item = item.data(Qt.ItemDataRole.UserRole)
        
        # Notify parent about the selection
        if workload_item and hasattr(self.parent(), "select_workload"):
            self.parent().select_workload(workload_item)
    
    def select_item(self, workload_item):
        # Find and select the corresponding legend item
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == workload_item:
                self.list_widget.setCurrentItem(item)
                break

class WorkloadsOverviewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Left side with chart and legend
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        
        # Title for charts section
        charts_title = QLabel("Workloads Overview")
        charts_title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 8px;
        """)
        left_layout.addWidget(charts_title)
        
        # Chart and legend container
        chart_legend_container = QHBoxLayout()
        
        # Chart container
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(0)
        chart_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create consolidated pie chart
        self.pie_chart = ConsolidatedPieChart()
        chart_layout.addWidget(self.pie_chart, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Legend container
        self.legend = LegendWidget()
        
        chart_legend_container.addWidget(chart_container, 1)
        chart_legend_container.addWidget(self.legend)
        
        left_layout.addLayout(chart_legend_container)
        left_layout.addStretch()
        
        # Right side with info panel
        self.info_panel = InfoPanel()
        self.info_panel.setMinimumWidth(300)
        self.info_panel.setMaximumWidth(300)
        
        layout.addWidget(left_container, 1)
        layout.addWidget(self.info_panel)
    
    def load_data(self):
        # Define workload data
        workload_data = [
            ("Pods", 9, "#00C853"),
            ("Deployments", 1, "#2196F3"),
            ("Daemon Sets", 1, "#FFC107"),
            ("Stateful Sets", 0, "#9C27B0"),
            ("Replica Sets", 1, "#FF5722"),
            ("Jobs", 0, "#795548"),
            ("Cron Jobs", 0, "#607D8B")
        ]
        
        # Create workload items and add to pie chart and legend
        self.workload_items = []
        for name, count, color in workload_data:
            # Create workload item
            item = WorkloadItem(name, count, color)
            self.workload_items.append(item)
            
            # Add to pie chart
            self.pie_chart.add_item(name, count, color)
            
            # Add to legend
            self.legend.add_legend_item(item)
        
        # Start animation
        QTimer.singleShot(100, self.pie_chart.start_animation)
        
        # Select first item with non-zero count
        for item in self.pie_chart.items:
            if item.count > 0:
                self.select_workload(item)
                break
    
    def select_workload(self, workload_item):
        # Update pie chart
        self.pie_chart.selected_item = workload_item
        self.pie_chart.update()
        
        # Update info panel (not hover mode)
        self.info_panel.update_info(workload_item, self.pie_chart.total_count, is_hover=False)
        
        # Update legend selection
        self.legend.select_item(workload_item)
    
    def hover_workload(self, workload_item):
        # Update info panel in hover mode
        self.info_panel.update_info(workload_item, self.pie_chart.total_count, is_hover=True)
    
    def reset_hover(self):
        # Reset hover info in panel
        self.info_panel.reset_hover()