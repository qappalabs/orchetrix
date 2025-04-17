from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QScrollArea, QFrame, QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, QPoint, pyqtSignal, QEventLoop, QEvent
from PyQt6.QtGui import QCursor

from UI.Styles import AppColors, AppStyles

class NotificationScreen(QWidget):
    """
    A dropdown notification screen that appears when the user clicks on the notification button.
    Shows a simple list of notifications without icons or categories.
    """
    closed = pyqtSignal()  # Signal emitted when notification screen is closed

    def __init__(self, parent=None, button=None):
        super().__init__(parent)
        self.parent = parent
        self.button = button  # The button that triggers this notification panel
        self.is_visible = False
        self.is_animating = False  # Track if animation is in progress
        self.setFixedWidth(350)  # Width of the notification panel

        # Set window flags to be a popup
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Install event filter on parent to detect clicks outside
        if parent:
            parent.installEventFilter(self)

        self.setup_ui()
        self.hide()

    def setup_ui(self):
        """Initialize the UI components"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Main container with border and shadow
        container = QFrame()
        container.setObjectName("notification_container")
        container.setStyleSheet(f"""
            QFrame#notification_container {{
                background-color: {AppColors.BG_SIDEBAR};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
            }}
        """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(50)
        header.setStyleSheet(f"background-color: {AppColors.BG_HEADER}; border-top-left-radius: 6px; border-top-right-radius: 6px;")

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(15, 0, 15, 0)

        title_label = QLabel("Notifications")
        title_label.setStyleSheet("font-weight: bold; font-size: 14pt; color: white;")

        clear_btn = QPushButton("Clear All")
        clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {AppColors.TEXT_SECONDARY};
                border: none;
                padding: 5px 10px;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                color: {AppColors.TEXT_LIGHT};
                text-decoration: underline;
            }}
        """)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(clear_btn)

        container_layout.addWidget(header)

        # Add a thin divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {AppColors.BORDER_COLOR};")
        container_layout.addWidget(divider)

        # Scroll area for notification content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {AppColors.BG_MEDIUM};
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {AppColors.BG_LIGHT};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(0)

        # Create all notification items
        notifications = [
            # System Alerts
            {"text": "Node `node-1` is unreachable", "time": "2 min ago"},
            {"text": "Cluster `prod-cluster` has high memory usage", "time": "10 min ago"},
            {"text": "PersistentVolume `pv-01` failed to mount", "time": "15 min ago"},

            # User Activity
            {"text": "`admin@qappa.com` added a new cluster", "time": "30 min ago"},
            {"text": "API token was regenerated by `devops_user`", "time": "45 min ago"},
            {"text": "Profile settings updated successfully", "time": "1 hour ago"},

            # Critical Events
            {"text": "Pod crash loop detected in namespace `kube-system`", "time": "2 hours ago"},
            {"text": "Kubelet service not running on `node-2`", "time": "3 hours ago"},
            {"text": "Unauthorized login attempt detected", "time": "4 hours ago"},

            # Informational
            {"text": "New update available: `v2.0.1`", "time": "Yesterday"},
            {"text": "Backup completed successfully", "time": "Yesterday"},
            {"text": "Maintenance mode activated for `test-cluster`", "time": "2 days ago"}
        ]

        for i, notification in enumerate(notifications):
            notification_item = self.create_notification_item(
                notification["text"],
                notification["time"]
            )
            content_layout.addWidget(notification_item)

            # Add divider between items (except after the last one)
            if i < len(notifications) - 1:
                item_divider = QFrame()
                item_divider.setFrameShape(QFrame.Shape.HLine)
                item_divider.setFixedHeight(1)
                item_divider.setStyleSheet(f"background-color: {AppColors.BORDER_COLOR}; margin: 0px 5px;")
                content_layout.addWidget(item_divider)

        scroll_area.setWidget(content_widget)
        container_layout.addWidget(scroll_area)

        # Footer with "View All" button
        footer = QWidget()
        footer.setFixedHeight(50)
        footer.setStyleSheet(f"background-color: {AppColors.BG_MEDIUM}; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px;")

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        view_all_btn = QPushButton("View All Notifications")
        view_all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        view_all_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        view_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {AppColors.TEXT_LIGHT};
                border: none;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: {AppColors.HOVER_BG};
            }}
        """)

        footer_layout.addWidget(view_all_btn)
        container_layout.addWidget(footer)

        main_layout.addWidget(container)

        # Set default size
        self.setFixedHeight(500)

    def create_notification_item(self, text, time):
        """Create a simple notification item with text and time"""
        item = QWidget()
        item.setFixedHeight(60)  # Slightly reduced height for simpler layout
        item.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        item.setStyleSheet(f"""
            QWidget:hover {{
                background-color: {AppColors.HOVER_BG};
            }}
        """)

        layout = QVBoxLayout(item)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)

        # Message text
        message = QLabel(text)
        message.setWordWrap(True)
        message.setStyleSheet("""
            color: white;
            font-size: 10pt;
        """)

        # Time text
        time_label = QLabel(time)
        time_label.setStyleSheet(f"""
            color: {AppColors.TEXT_SECONDARY};
            font-size: 9pt;
        """)

        layout.addWidget(message)
        layout.addWidget(time_label)

        return item

    def show_notifications(self):
        """Show the notification panel as a dropdown from the button"""
        if self.is_visible or self.is_animating:
            return

        self.is_animating = True
        self.is_visible = True

        # Calculate position relative to the button
        if self.button and self.parent:
            global_pos = self.button.mapToGlobal(QPoint(0, self.button.height()))
            local_pos = self.parent.mapFromGlobal(global_pos)

            # Adjust position to align with the button
            pos_x = local_pos.x() - self.width() + self.button.width()
            # Ensure it doesn't go off-screen to the left
            if pos_x < 0:
                pos_x = 0

            target_y = local_pos.y()

            # Set initial collapsed size (starting from button)
            start_rect = QRect(pos_x, local_pos.y(), self.width(), 0)
            # Set final expanded size
            end_rect = QRect(pos_x, local_pos.y(), self.width(), self.height())

            # Show before animation, but with 0 height
            self.setGeometry(start_rect)
            self.show()
            self.raise_()  # Ensure it's on top

            # Create animation
            self.anim = QPropertyAnimation(self, b"geometry")
            self.anim.setDuration(200)
            self.anim.setStartValue(start_rect)
            self.anim.setEndValue(end_rect)
            self.anim.finished.connect(self._on_show_finished)
            self.anim.start()

    def _on_show_finished(self):
        """Called when the show animation finishes"""
        self.is_animating = False

    def hide_notifications(self):
        """Hide the notification panel with animation"""
        if not self.is_visible or self.is_animating:
            return

        self.is_animating = True
        self.is_visible = False

        # Create collapse animation
        start_rect = self.geometry()
        end_rect = QRect(start_rect.x(), start_rect.y(), start_rect.width(), 0)

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(200)
        self.anim.setStartValue(start_rect)
        self.anim.setEndValue(end_rect)
        self.anim.finished.connect(self._on_hide_finished)
        self.anim.start()

    def _on_hide_finished(self):
        """Called when the hide animation finishes"""
        self.hide()
        self.is_animating = False
        self.closed.emit()

    def toggle_notifications(self):
        """Toggle the visibility of the notification panel"""
        if self.is_animating:
            return

        if self.is_visible:
            self.hide_notifications()
        else:
            self.show_notifications()

    def eventFilter(self, obj, event):
        """Filter events to detect clicks outside the notification panel"""
        if obj == self.parent and event.type() == QEvent.Type.MouseButtonPress:
            if self.is_visible and not self.geometry().contains(event.pos()):
                # Only process clicks outside if we're not in the middle of animating
                if not self.is_animating and not self.button.geometry().contains(event.pos()):
                    self.hide_notifications()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        """Handle mouse press events to prevent closing when clicking inside the panel"""
        super().mousePressEvent(event)
        # Prevent event propagation to parent
        event.accept()