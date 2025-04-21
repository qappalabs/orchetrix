"""
Dynamic implementation of the Overview page with live Kubernetes data.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QSizePolicy, QTableWidget, QScrollArea, QFrame, 
    QTableWidgetItem, QHeaderView, QPushButton
)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt6.QtCore import Qt, QSize, QTimer

from UI.Styles import AppStyles, AppColors
from utils.cluster_connector import get_cluster_connector

class CircularProgressIndicator(QWidget):
    """Widget that displays a circular progress indicator with three rings."""
    def __init__(self, running=0, in_progress=0, failed=0, total=20):
        super().__init__()
        self.running = running
        self.in_progress = in_progress
        self.failed = failed
        self.total = total
        self.setMinimumSize(120, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get dimensions for the circle
        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2

        # Ring sizes - make them proportional to widget size
        size_factor = min(width, height) / 150  # Scale factor based on widget size

        outer_radius = min(width, height) / 2 - (15 * size_factor)
        middle_radius = outer_radius - (10 * size_factor)
        inner_radius = middle_radius - (10 * size_factor)

        # Scale pen width based on widget size but make it thicker for visibility
        pen_width = 6 * size_factor

        # Set up pen properties
        pen = QPen()
        pen.setWidth(max(3, int(pen_width)))  # Increased minimum width from 2 to 3
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        # Draw the background circles
        pen.setColor(QColor(AppColors.BG_DARKER))  # Darker background color
        painter.setPen(pen)

        # Draw outer ring background (for running)
        painter.drawEllipse(int(center_x - outer_radius), int(center_y - outer_radius),
                            int(outer_radius * 2), int(outer_radius * 2))

        # Draw middle ring background (for in progress)
        painter.drawEllipse(int(center_x - middle_radius), int(center_y - middle_radius),
                            int(middle_radius * 2), int(middle_radius * 2))

        # Draw inner ring background (for failed)
        painter.drawEllipse(int(center_x - inner_radius), int(center_y - inner_radius),
                            int(inner_radius * 2), int(inner_radius * 2))

        # Start angle for all segments (same starting point)
        start_angle = -90 * 16  # Start at top (negative numbers go clockwise in Qt)

        # Draw the running segment (green) on outer ring
        if self.running > 0:
            pen.setColor(QColor(AppColors.STATUS_ACTIVE))  # Green
            painter.setPen(pen)
            segment_angle = int(self.running / self.total * 360 * 16)
            painter.drawArc(int(center_x - outer_radius), int(center_y - outer_radius),
                            int(outer_radius * 2), int(outer_radius * 2),
                            start_angle, segment_angle)

        # Draw the in progress segment (yellow/orange) on middle ring
        if self.in_progress > 0:
            pen.setColor(QColor(AppColors.STATUS_PENDING))  # Orange
            painter.setPen(pen)
            segment_angle = int(self.in_progress / self.total * 360 * 16)
            painter.drawArc(int(center_x - middle_radius), int(center_y - middle_radius),
                            int(middle_radius * 2), int(middle_radius * 2),
                            start_angle, segment_angle)

        # Draw the failed segment (red) on inner ring
        if self.failed > 0:
            pen.setColor(QColor(AppColors.STATUS_DISCONNECTED))  # Red
            painter.setPen(pen)
            segment_angle = int(self.failed / self.total * 360 * 16)
            painter.drawArc(int(center_x - inner_radius), int(center_y - inner_radius),
                            int(inner_radius * 2), int(inner_radius * 2),
                            start_angle, segment_angle)

    def sizeHint(self):
        return QSize(150, 150)


class StatusWidget(QWidget):
    """Widget that displays a resource status with a circular indicator."""
    def __init__(self, title, resource_type, running=0, in_progress=0, failed=0):
        super().__init__()
        self.resource_type = resource_type

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # Create a frame for the box background
        self.box = QFrame()
        self.box.setObjectName("statusBox")
        self.box.setStyleSheet(AppStyles.STATUS_BOX_STYLE)

        # Box layout
        box_layout = QVBoxLayout(self.box)
        box_layout.setContentsMargins(10, 10, 10, 10)

        # Add title
        title_label = QLabel(title)
        title_label.setStyleSheet(AppStyles.STATUS_TITLE_STYLE)
        font = QFont()
        font.setBold(True)
        title_label.setFont(font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(title_label)

        # Add circular progress indicator
        self.progress = CircularProgressIndicator(running, in_progress, failed)
        self.progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        box_layout.addWidget(self.progress)

        # Add status labels
        self.running_label = QLabel(f"● Running: {running}")
        self.running_label.setStyleSheet(AppStyles.RESOURCE_LABEL_USAGE_STYLE)  # Green
        self.running_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.running_label)

        self.in_progress_label = QLabel(f"● In Progress: {in_progress}")
        self.in_progress_label.setStyleSheet(AppStyles.RESOURCE_LABEL_REQUESTS_STYLE)  # Orange-like
        self.in_progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.in_progress_label)

        self.failed_label = QLabel(f"● Failed: {failed}")
        self.failed_label.setStyleSheet(AppStyles.MESSAGE_WARNING_STYLE)  # Red
        self.failed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.failed_label)

        # Add the box to the main layout
        main_layout.addWidget(self.box)

        # Set widget to be transparent (the box inside has the background)
        self.setStyleSheet("background-color: transparent;")
        
    def update_status(self, running, in_progress, failed):
        """Update the status widget with new values."""
        self.progress.running = running
        self.progress.in_progress = in_progress
        self.progress.failed = failed
        self.progress.repaint()
        
        # Update labels
        self.running_label.setText(f"● Running: {running}")
        self.in_progress_label.setText(f"● In Progress: {in_progress}")
        self.failed_label.setText(f"● Failed: {failed}")

    def sizeHint(self):
        return QSize(170, 270)

    def minimumSizeHint(self):
        return QSize(150, 240)


class EventsTable(QTableWidget):
    """Table widget that displays cluster events."""
    def __init__(self):
        super().__init__()
        # Configure table
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(["Type", "Message", "Namespace", "Involved Object", "Source", "Count", "Age"])

        # Make table resize correctly
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # Disable alternating row colors
        self.setAlternatingRowColors(False)

        # Make table non-editable
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Keep selection mode but make it more subtle
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Make vertical header fixed size
        self.verticalHeader().setDefaultSectionSize(36)
        self.verticalHeader().setVisible(False)

        # Apply styles
        self.setStyleSheet(AppStyles.EVENTS_TABLE_STYLE)
    
    def update_events(self, events_data):
        """Update the table with new events data."""
        self.setRowCount(0)  # Clear existing rows
        
        # Add the events to the table
        for row_index, event in enumerate(events_data):
            self.insertRow(row_index)
            event_type = event.get("type", "Normal")
            message = event.get("message", "")
            namespace = event.get("namespace", "default")
            involved_object = event.get("object", "")
            source = "Unknown"
            if "reason" in event:
                source = event["reason"]
            count = "1"
            age = event.get("age", "")
            
            # Create data for row
            event_columns = [event_type, message, namespace, involved_object, source, count, age]
            
            for col_index, value in enumerate(event_columns):
                item = QTableWidgetItem(value)
                
                # Style based on event type
                if col_index == 0:  # Type column
                    if value == "Warning":
                        item.setForeground(QColor(AppColors.STATUS_WARNING))
                    elif value == "Normal":
                        item.setForeground(QColor(AppColors.STATUS_ACTIVE))
                    else:
                        item.setForeground(QColor(AppColors.TEXT_LIGHT))
                
                # Center align count and age columns
                if col_index >= 5:  # Count and Age columns
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                
                self.setItem(row_index, col_index, item)


class OverviewPage(QWidget):
    """
    Overview page shows a summary of workload resources and recent events.
    
    Features:
    1. Dynamic loading of resource status from the cluster
    2. Real-time updates of workload statistics
    3. Event monitoring with live updates
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status_widgets = {}
        self.setup_ui()
        
        # Connect to the cluster connector for live updates
        self.cluster_connector = get_cluster_connector()
        self.cluster_connector.issues_data_loaded.connect(self.update_events)
        
        # Start a timer to periodically refresh resource status
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_resources)
        self.refresh_timer.start(10000)  # Refresh every 10 seconds
        
        # Initial resource fetch
        QTimer.singleShot(500, self.refresh_resources)

    def setup_ui(self):
        """Set up the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Top bar - just the Overview title
        top_bar = QWidget()
        top_bar.setStyleSheet(AppStyles.TOP_BAR_STYLE)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 10)

        overview_label = QLabel("Overview")
        overview_label.setStyleSheet(AppStyles.TITLE_STYLE)

        # Add refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_resources)

        top_bar_layout.addWidget(overview_label)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(refresh_btn)

        main_layout.addWidget(top_bar)

        # Status widgets
        status_row = QWidget()
        self.status_layout = QHBoxLayout(status_row)
        self.status_layout.setSpacing(15)  # Spacing between widgets

        # Make scroll area for status widgets to handle window resizing
        status_scroll = QScrollArea()
        status_scroll.setWidgetResizable(True)
        status_scroll.setWidget(status_row)
        status_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        status_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        status_scroll.setStyleSheet(AppStyles.STATUS_SCROLL_STYLE)

        # Create status widgets for each resource type
        resource_types = [
            ("Pods", "pods"),
            ("Deployments", "deployments"),
            ("Daemon Sets", "daemonsets"),
            ("Stateful Sets", "statefulsets"),
            ("Replica Sets", "replicasets"),
            ("Jobs", "jobs"),
            ("Cron Jobs", "cronjobs")
        ]

        for title, resource_type in resource_types:
            widget = StatusWidget(title, resource_type)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            widget.setMinimumWidth(150)
            self.status_layout.addWidget(widget)
            self.status_widgets[resource_type] = widget

        # Add status section to main content
        main_layout.addWidget(status_scroll)

        # Events section header
        events_header = QWidget()
        events_header_layout = QHBoxLayout(events_header)
        events_header_layout.setContentsMargins(0, 20, 0, 5)

        # Add Events title
        events_title = QLabel("Events")
        events_title.setStyleSheet(AppStyles.TITLE_STYLE)
        self.events_count = QLabel("0 of 0")
        self.events_count.setStyleSheet(AppStyles.ITEMS_COUNT_STYLE)
        self.events_count.setAlignment(Qt.AlignmentFlag.AlignRight)

        events_header_layout.addWidget(events_title)
        events_header_layout.addStretch()
        events_header_layout.addWidget(self.events_count)

        main_layout.addWidget(events_header)

        # Events table
        self.events_table = EventsTable()
        main_layout.addWidget(self.events_table)

        # Set stretch factor to ensure table takes available space
        main_layout.setStretchFactor(self.events_table, 1)

        # Install event filter to clear table selection when clicking elsewhere
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Clear table selection when clicking elsewhere."""
        # Check if the event is a mouse press
        if event.type() == event.Type.MouseButtonPress:
            # Check if the click is outside the table
            if obj != self.events_table and not self.events_table.underMouse():
                # Clear the selection
                self.events_table.clearSelection()

        # Always return False to let the event continue to the target
        return False

    def refresh_resources(self):
        """Refresh all resource status from the Kubernetes cluster."""
        # Use kubectl to get resource status for each type
        self.fetch_resource_status()
        
    def fetch_resource_status(self):
        """Fetch resource status from kubectl for all resource types."""
        import subprocess
        import json
        
        # Process each resource type
        for resource_type, widget in self.status_widgets.items():
            try:
                # Get all resources of this type across all namespaces
                cmd = ["kubectl", "get", resource_type, "--all-namespaces", "-o", "json"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    items = data.get("items", [])
                    
                    # Initialize counters
                    running = 0
                    in_progress = 0
                    failed = 0
                    
                    for item in items:
                        status = item.get("status", {})
                        
                        # Different logic based on resource type
                        if resource_type == "pods":
                            phase = status.get("phase", "")
                            if phase == "Running":
                                running += 1
                            elif phase == "Failed" or phase == "Error":
                                failed += 1
                            else:
                                in_progress += 1
                                
                        elif resource_type in ["deployments", "statefulsets", "daemonsets"]:
                            # For workload controllers, check replica status
                            available = status.get("availableReplicas", 0)
                            desired = status.get("replicas", 0)
                            ready = status.get("readyReplicas", 0)
                            updated = status.get("updatedReplicas", 0)
                            
                            if available == desired and ready == desired:
                                running += 1
                            elif ready == 0:
                                failed += 1
                            else:
                                in_progress += 1
                                
                        elif resource_type == "replicasets":
                            ready = status.get("readyReplicas", 0)
                            desired = status.get("replicas", 0)
                            
                            if desired == 0:  # Ignore scaled-down replicasets
                                continue
                                
                            if ready == desired:
                                running += 1
                            elif ready == 0:
                                failed += 1
                            else:
                                in_progress += 1
                                
                        elif resource_type == "jobs":
                            succeeded = status.get("succeeded", 0)
                            active = status.get("active", 0)
                            failed_count = status.get("failed", 0)
                            
                            if succeeded > 0:
                                running += 1
                            elif failed_count > 0:
                                failed += 1
                            elif active > 0:
                                in_progress += 1
                            else:
                                in_progress += 1
                                
                        elif resource_type == "cronjobs":
                            # For CronJobs, get the active jobs
                            if status.get("active", []):
                                in_progress += 1
                            else:
                                running += 1  # Treat as "ready for scheduling"
                    
                    # Update the status widget
                    widget.update_status(running, in_progress, failed)
                    
            except (subprocess.SubprocessError, json.JSONDecodeError, Exception) as e:
                print(f"Error fetching {resource_type}: {str(e)}")
                # Reset to zeros in case of error
                widget.update_status(0, 0, 0)
    
    def update_events(self, events_data):
        """Update the events table with new data."""
        # Sort events by age (newest first)
        sorted_events = sorted(events_data, 
                               key=lambda x: self._age_to_minutes(x.get("age", "0m")), 
                               reverse=False)
        
        # Update events count
        self.events_count.setText(f"{len(sorted_events)} events")
        
        # Limit to the 20 most recent events
        recent_events = sorted_events[:20] if len(sorted_events) > 20 else sorted_events
        
        # Update the events table
        self.events_table.update_events(recent_events)
    
    def _age_to_minutes(self, age_str):
        """Convert age string to minutes for sorting."""
        try:
            if 'd' in age_str:
                return int(age_str.replace('d', '')) * 1440  # days to minutes
            elif 'h' in age_str:
                return int(age_str.replace('h', '')) * 60   # hours to minutes
            elif 'm' in age_str:
                return int(age_str.replace('m', ''))        # already minutes
            else:
                return 0
        except ValueError:
            return 0
    
    def showEvent(self, event):
        """Refresh resources when the page is shown."""
        super().showEvent(event)
        QTimer.singleShot(100, self.refresh_resources)
        
    def hideEvent(self, event):
        """Stop the refresh timer when the page is hidden."""
        super().hideEvent(event)
        self.refresh_timer.stop()
        
    def showEvent(self, event):
        """Start the refresh timer when the page is shown."""
        super().showEvent(event)
        self.refresh_resources()  # Immediate refresh
        self.refresh_timer.start(10000)  # Resume timer