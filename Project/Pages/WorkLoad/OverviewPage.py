import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QSizePolicy, QTableWidget,
                             QScrollArea, QFrame, QTableWidgetItem, QHeaderView)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt6.QtCore import Qt, QSize


class CircularProgressIndicator(QWidget):
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

        # Draw the background circles - make them darker for better contrast
        pen.setColor(QColor(30, 30, 30))  # Darker background color
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

        # Draw the running segment (green) on outer ring - make colors brighter
        if self.running > 0:
            pen.setColor(QColor(50, 220, 50))  # Brighter green
            painter.setPen(pen)
            segment_angle = int(self.running / self.total * 360 * 16)
            painter.drawArc(int(center_x - outer_radius), int(center_y - outer_radius),
                            int(outer_radius * 2), int(outer_radius * 2),
                            start_angle, segment_angle)

        # Draw the in progress segment (yellow/orange) on middle ring
        if self.in_progress > 0:
            pen.setColor(QColor(255, 180, 0))  # Brighter orange/yellow
            painter.setPen(pen)
            segment_angle = int(self.in_progress / self.total * 360 * 16)
            painter.drawArc(int(center_x - middle_radius), int(center_y - middle_radius),
                            int(middle_radius * 2), int(middle_radius * 2),
                            start_angle, segment_angle)

        # Draw the failed segment (red) on inner ring
        if self.failed > 0:
            pen.setColor(QColor(255, 60, 60))  # Brighter red
            painter.setPen(pen)
            segment_angle = int(self.failed / self.total * 360 * 16)
            painter.drawArc(int(center_x - inner_radius), int(center_y - inner_radius),
                            int(inner_radius * 2), int(inner_radius * 2),
                            start_angle, segment_angle)

    def sizeHint(self):
        return QSize(150, 150)


class StatusWidget(QWidget):
    def __init__(self, title, running=0, in_progress=0, failed=0):
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
            }
        """)

        # Box layout
        box_layout = QVBoxLayout(self.box)
        box_layout.setContentsMargins(10, 10, 10, 10)

        # Add title - now with bold font
        title_label = QLabel(title)
        # Create a bold font for the title
        font = QFont()
        font.setBold(True)
        title_label.setFont(font)
        title_label.setStyleSheet("color: white; font-size: 16px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(title_label)

        # Add circular progress indicator
        self.progress = CircularProgressIndicator(running, in_progress, failed)
        self.progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        box_layout.addWidget(self.progress)

        # Add status labels - center-aligned with brighter colors
        running_label = QLabel(f"● Running: {running}")
        running_label.setStyleSheet("color: #32dc32;")  # Brighter green
        running_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(running_label)

        in_progress_label = QLabel(f"● In Progress: {in_progress}")
        in_progress_label.setStyleSheet("color: #ffb400;")  # Brighter orange
        in_progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(in_progress_label)

        failed_label = QLabel(f"● Failed: {failed}")
        failed_label.setStyleSheet("color: #ff3c3c;")  # Brighter red
        failed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(failed_label)

        # Add the box to the main layout
        main_layout.addWidget(self.box)

        # Set widget to be transparent (the box inside has the background)
        self.setStyleSheet("background-color: transparent;")

    def sizeHint(self):
        return QSize(170, 270)

    def minimumSizeHint(self):
        return QSize(150, 240)


class EventsTable(QTableWidget):
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

        # Style - with hover effect and subtle selection
        self.setStyleSheet("""
            QTableWidget {
                background-color: #262626;
                color: white;
                gridline-color: transparent;
                border: none;
            }
            QHeaderView::section {
                background-color: #212121;
                color: white;
                padding: 8px;
                border: none;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
                background: transparent;
            }
            QTableWidget::item:hover {
                background-color: rgba(80, 80, 80, 120);
            }
            QTableWidget::item:selected {
                background-color: rgba(60, 60, 60, 150);
                color: white;
            }
            QTableWidget:focus {
                outline: none;
            }
            QHeaderView::section:hover {
                background-color: #2a2a2a;
            }
            QScrollBar:vertical {
                background-color: #212121;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(160, 160, 160, 150);
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #212121;
                height: 8px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: rgba(160, 160, 160, 150);
                border-radius: 4px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

        # Sample data based on the image
        events_data = [
            ("Normal", "Node docker desktop event: registration", "default", "Node: docker desktop", "Node Controller", "1", "46m"),
            ("Normal", "Node docker desktop is not responding", "default", "Node: docker desktop", "Kubelet docker...", "7", "46m"),
            ("Normal", "Update node allocation limit across th pods", "default", "Node: docker desktop", "Kubelet docker...", "1", "46m"),
            ("Normal", "Starting Kubelet.", "default", "Node: docker desktop", "Kubelet docker...", "1", "46m"),
            ("Normal", "Node docker desktop event: registration", "default", "Node: docker desktop", "Node Controller", "1", "46m"),
            ("Normal", "Node docker desktop is not responding", "default", "Node: docker desktop", "Kubelet docker...", "7", "46m"),
            ("Normal", "Update node allocation limit across th pods", "default", "Node: docker desktop", "Kubelet docker...", "1", "46m"),
            ("Normal", "Starting Kubelet.", "default", "Node: docker desktop", "Kubelet docker...", "1", "46m")
        ]

        # Add the sample data to the table
        for row_index, event in enumerate(events_data):
            self.insertRow(row_index)
            for col_index, value in enumerate(event):
                item = QTableWidgetItem(value)
                # Center align count and age columns
                if col_index >= 5:  # Count and Age columns
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row_index, col_index, item)


class OverviewPage(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Docker Desktop")
        self.resize(1200, 800)
        self.setStyleSheet("background-color: #1a1a1a; color: white;")

        # Main widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Top bar - just the Overview title
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 10)

        overview_label = QLabel("Overview")
        overview_label.setStyleSheet("font-size: 22px; font-weight: bold;")

        top_bar_layout.addWidget(overview_label)
        top_bar_layout.addStretch()

        main_layout.addWidget(top_bar)

        # Status widgets
        status_row = QWidget()
        status_layout = QHBoxLayout(status_row)
        status_layout.setSpacing(15)  # Spacing between widgets

        # Make scroll area for status widgets to handle window resizing
        status_scroll = QScrollArea()
        status_scroll.setWidgetResizable(True)
        status_scroll.setWidget(status_row)
        status_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        status_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        status_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:horizontal {
                background-color: #212121;
                height: 8px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: rgba(160, 160, 160, 150);
                border-radius: 4px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

        status_widgets = [
            ("Pods", 10, 4, 6),
            ("Deployment", 4, 10, 6),
            ("Daemon Sets", 10, 6, 4),
            ("Stateful Sets", 10, 4, 6),
            ("Replica Sets", 10, 4, 6),
            ("Jobs", 8, 6, 6),
            ("Cron Jobs", 6, 3, 4)
        ]

        for title, running, in_progress, failed in status_widgets:
            widget = StatusWidget(title, running, in_progress, failed)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            widget.setMinimumWidth(150)
            status_layout.addWidget(widget)

        # Add status section to main content
        main_layout.addWidget(status_scroll)

        # Events section header
        events_header = QWidget()
        events_header_layout = QHBoxLayout(events_header)
        events_header_layout.setContentsMargins(0, 20, 0, 5)

        # Add Events title with the same style as Overview
        events_title = QLabel("Events")
        events_title.setStyleSheet("font-size: 22px; font-weight: bold;")
        events_count = QLabel("8 of 28")
        events_count.setAlignment(Qt.AlignmentFlag.AlignRight)

        events_header_layout.addWidget(events_title)
        events_header_layout.addStretch()
        events_header_layout.addWidget(events_count)

        main_layout.addWidget(events_header)

        # Events table
        self.events_table = EventsTable()
        main_layout.addWidget(self.events_table)

        # Set stretch factor to ensure table takes available space
        main_layout.setStretchFactor(self.events_table, 1)

        self.setCentralWidget(central_widget)

        # Install event filter to clear table selection when clicking elsewhere
        central_widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        # Check if the event is a mouse press
        if event.type() == event.Type.MouseButtonPress:
            # Check if the click is outside the table
            if obj != self.events_table and not self.events_table.underMouse():
                # Clear the selection
                self.events_table.clearSelection()

        # Always return False to let the event continue to the target
        return False

    def resizeEvent(self, event):
        # Call parent class resize event
        super().resizeEvent(event)

        # Get current window size
        width = self.width()

        # Could implement additional responsive behavior here based on window size