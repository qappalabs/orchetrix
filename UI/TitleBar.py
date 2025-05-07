import sys
import os

# Add the project root directory to sys.path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.append(project_root)

from PyQt6.QtCore import Qt, QPoint, QEvent, QSize
from PyQt6.QtGui import QFont, QLinearGradient, QPainter, QColor, QPixmap, QIcon, QPainterPath, QCursor, QAction
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QToolButton, QPushButton, QFrame, QLineEdit, QMenu, QSpacerItem, QWidgetAction

from UI.Styles import AppColors, AppStyles
from UI.Icons import Icons

class TitleBar(QWidget):
    def __init__(self, parent=None, update_pinned_items_signal=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)

        # Define consistent icon sizes
        self.normal_icon_size = QSize(18, 18)      # Standard size for most icons
        self.logo_icon_size = QSize(24, 24)        # Size for the app logo
        self.window_ctrl_size = QSize(18, 18)      # MODIFIED: Increased to match normal icon size
        self.maximized_icon_size = QSize(18, 18)   # MODIFIED: Made consistent with other icons

        # Store the signal for pinned items updates
        self.update_pinned_items_signal = update_pinned_items_signal
        # Store the signal for opening clusters
        self.open_cluster_signal = getattr(parent.home_page, 'open_cluster_signal', None) if hasattr(parent, 'home_page') else None

        # Store the pinned items list to preserve it during filtering
        self.pinned_items = []

        self.setup_ui()
        self.old_pos = None
        self.dropdown_menu = None
        self.search_input = None  # Instance variable for the search input
        self.search_action = None  # Instance variable for the search action

    def setup_ui(self):
        # Apply title bar style from Styles.py
        self.setStyleSheet(AppStyles.TITLE_BAR_STYLE)

        # Create a container widget with vertical layout
        container = QWidget(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Create the main content widget
        content = QWidget()
        layout = QHBoxLayout(content)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(14)

        # Orchetrix logo on the left
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(self.logo_icon_size)

        # Try to load app logo from file first
        try:
            logo_path = Icons.resource_path("icons/logoIcon.png")
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                self.logo_label.setPixmap(pixmap.scaled(self.logo_icon_size, Qt.AspectRatioMode.KeepAspectRatio,
                                                        Qt.TransformationMode.SmoothTransformation))
            else:
                # Create a fallback logo
                self.create_fallback_logo()
        except Exception as e:
            print(f"Error loading logo: {e}")
            self.create_fallback_logo()

        # Home icon button
        self.home_btn = self.create_icon_button("home", "Home")
        self.home_btn.clicked.connect(self.navigate_to_home)

        # Pinned Clusters button with dropdown (using QWidget for better control)
        self.pinned_clusters_container = QWidget()
        self.pinned_clusters_container.setFixedSize(300, 30)
        pinned_layout = QHBoxLayout(self.pinned_clusters_container)
        pinned_layout.setContentsMargins(0, 0, 0, 0)
        pinned_layout.setSpacing(0)

        # Label for "Pinned Clusters" text
        self.pinned_clusters_label = QLabel("Pinned Clusters")
        self.pinned_clusters_label.setStyleSheet("""
            QLabel {
                background-color: #2A2A2A;
                color: #FFFFFF;
                padding: 0px 10px;
                font-size: 14px;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        self.pinned_clusters_label.setFixedHeight(30)

        # Button for the ▼ arrow
        self.pinned_clusters_arrow_btn = QToolButton()
        self.pinned_clusters_arrow_btn.setFixedSize(30, 30)
        self.pinned_clusters_arrow_btn.setIcon(self.create_down_arrow_icon())
        self.pinned_clusters_arrow_btn.setIconSize(QSize(10, 10))
        self.pinned_clusters_arrow_btn.setStyleSheet("""
            QToolButton {
                background-color: #2A2A2A;
                border: none;
                border-left: 1px solid #4A4A4A;
                border-radius: 0 4px 4px 0;
            }
            QToolButton:hover {
                background-color: #3e3e3e;
            }
        """)
        self.pinned_clusters_arrow_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pinned_clusters_arrow_btn.clicked.connect(self.toggle_pinned_clusters_dropdown)

        # Container widget to hold the label and arrow button
        self.pinned_clusters_container.setStyleSheet("""
            QWidget {
                background-color: #2A2A2A;
            }
        """)
        pinned_layout.addWidget(self.pinned_clusters_label)
        pinned_layout.addStretch()
        pinned_layout.addWidget(self.pinned_clusters_arrow_btn)

        # Settings and other icons on the right
        self.troubleshoot_btn = self.create_icon_button("help", "Help & Troubleshoot")
        self.notifications_btn = self.create_icon_button("notifications", "Notifications")
        self.profile_btn = self.create_icon_button("profile", "Profile")
        self.profile_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.settings_btn = self.create_icon_button("preferences", "Settings")

        # Window control buttons
        self.minimize_btn = self.create_window_control_button("minimize", "Minimize")
        self.minimize_btn.clicked.connect(self.parent.showMinimized)

        self.maximize_btn = self.create_window_control_button("maximize", "Maximize")
        self.maximize_btn.clicked.connect(self.toggle_maximize)

        self.close_btn = self.create_window_control_button("close", "Close")
        self.close_btn.clicked.connect(self.parent.close)
        self.close_btn.setStyleSheet(AppStyles.TITLE_BAR_CLOSE_BUTTON_STYLE)

        # Add widgets to layout
        layout.addWidget(self.logo_label)
        layout.addWidget(self.home_btn)
        layout.addSpacerItem(QSpacerItem(90, 0))
        layout.addWidget(self.pinned_clusters_container)
        layout.addStretch(1)
        layout.addWidget(self.troubleshoot_btn)
        layout.addWidget(self.notifications_btn)
        layout.addWidget(self.profile_btn)
        layout.addWidget(self.settings_btn)
        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.maximize_btn)
        layout.addWidget(self.close_btn)

        # Add the content to the container
        container_layout.addWidget(content)

        # Create a frame for the bottom border
        bottom_frame = QFrame()
        bottom_frame.setFixedHeight(2)
        bottom_frame.setStyleSheet(f"background-color: {AppColors.BORDER_COLOR};")
        container_layout.addWidget(bottom_frame)

        # Set up the main layout for this widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(container)

        # Install event filter for double-click
        self.installEventFilter(self)

        # Connect the pinned items signal if provided
        if self.update_pinned_items_signal:
            try:
                self.update_pinned_items_signal.disconnect()
            except Exception:
                pass
            self.update_pinned_items_signal.connect(self.update_pinned_dropdown)
            print("Connected update_pinned_items_signal to update_pinned_dropdown")

    def create_down_arrow_icon(self):
        """Create a downward arrow icon for the dropdown"""
        size = QSize(10, 10)  # Smaller size for the arrow
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))

        path = QPainterPath()
        path.moveTo(size.width() * 0.5, size.height() * 0.85)  # Bottom point
        path.lineTo(size.width() * 0.15, size.height() * 0.35)  # Top-left point
        path.lineTo(size.width() * 0.85, size.height() * 0.35)  # Top-right point
        path.closeSubpath()

        painter.drawPath(path)
        painter.end()

        return QIcon(pixmap)

    def toggle_pinned_clusters_dropdown(self):
        """Toggle the visibility of the pinned clusters dropdown"""
        if self.dropdown_menu and self.dropdown_menu.isVisible():
            print("Dropdown is visible, hiding it")
            self.dropdown_menu.hide()
        else:
            print("Dropdown is hidden, showing it")
            self.create_or_update_dropdown()
            if self.search_input:
                self.search_input.setFocus()  # Set focus to the search input when opening

    def create_or_update_dropdown(self):
        """Create or update the dropdown menu with search input and pinned items"""
        if not self.dropdown_menu:
            self.dropdown_menu = QMenu(self)
            self.dropdown_menu.setStyleSheet("""
                QMenu {
                    background-color: #2A2A2A;
                    color: #FFFFFF;
                    border: 1px solid #4A4A4A;
                    padding: 5px;
                }
                QMenu::item {
                    padding: 5px 20px;
                }
                QMenu::item:selected {
                    background-color: #4A9EFF;
                }
            """)

        # Initialize or reuse the search input and action
        if not self.search_input:
            self.search_input = QLineEdit(self)  # Set parent to self to prevent deletion
            self.search_input.setPlaceholderText("Search...")
            self.search_input.setFixedWidth(287)  # Match the width of pinned_clusters_container
            self.search_input.setStyleSheet("""
                QLineEdit {
                    background-color: #2A2A2A;
                    color: #FFFFFF;
                    border: 1px solid #4A4A4A;
                    border-radius: 4px;
                    padding: 5px;
                    margin-bottom: 5px;
                }
                QLineEdit[placeholderText="Search..."] {
                    color: #999999;
                }
            """)
            self.search_input.textChanged.connect(self.filter_pinned_items)
            self.search_action = QWidgetAction(self)  # Set parent to self to prevent deletion
            self.search_action.setDefaultWidget(self.search_input)
            self.dropdown_menu.addAction(self.search_action)

        # Clear and update the pinned items
        self.dropdown_menu.clear()
        self.dropdown_menu.addAction(self.search_action)  # Re-add the search action

        # Add pinned items as actions
        if self.pinned_items:
            for item in self.pinned_items:
                action = QAction(item, self.dropdown_menu)
                action.triggered.connect(lambda checked, i=item: self.handle_item_selection(i))
                self.dropdown_menu.addAction(action)
        else:
            action = QAction("No pinned clusters", self.dropdown_menu)
            action.setEnabled(False)
            self.dropdown_menu.addAction(action)

        # Show the dropdown below the container
        button_pos = self.pinned_clusters_container.mapToGlobal(QPoint(0, self.pinned_clusters_container.height()))
        self.dropdown_menu.move(button_pos)
        self.dropdown_menu.show()

    def filter_pinned_items(self, text):
        """Filter the dropdown items based on the search input with Elasticsearch-like matching"""
        print(f"Filtering pinned items with text: '{text}'")
        if not self.pinned_items or not self.dropdown_menu:
            return

        search_text = text.lower()
        self.dropdown_menu.clear()
        self.dropdown_menu.addAction(self.search_action)  # Re-add the search action

        # Filter items using substring matching (Elasticsearch-like)
        filtered_items = [item for item in self.pinned_items if search_text in item.lower()]
        if filtered_items:
            for item in filtered_items:
                action = QAction(item, self.dropdown_menu)
                action.triggered.connect(lambda checked, i=item: self.handle_item_selection(i))
                self.dropdown_menu.addAction(action)
        else:
            action = QAction("No matching pinned clusters", self.dropdown_menu)
            action.setEnabled(False)
            self.dropdown_menu.addAction(action)

        # Update the dropdown position and restore focus
        button_pos = self.pinned_clusters_container.mapToGlobal(QPoint(0, self.pinned_clusters_container.height()))
        self.dropdown_menu.move(button_pos)
        if self.search_input:
            self.search_input.setFocus()  # Restore focus to ensure continuous typing

    def handle_item_selection(self, item):
        """Handle the selection of a pinned item"""
        print(f"Selected: {item}")
        # Do not update the button text, keep it as "Pinned Clusters"
        if self.open_cluster_signal and hasattr(self.parent.home_page, 'all_data'):
            for view_type in self.parent.home_page.all_data:
                for data_item in self.parent.home_page.all_data[view_type]:
                    if data_item.get("name") == item and "Cluster" in data_item.get("kind", ""):
                        print(f"Navigating to cluster: {item}")
                        self.open_cluster_signal.emit(item)
                        break
        self.dropdown_menu.hide()

    def create_icon_button(self, icon_id, tooltip, fallback_icon=None):
        """Create a tool button with the specified icon and tooltip"""
        btn = QToolButton()
        btn.setFixedSize(30, 30)
        btn.setToolTip(tooltip)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        icon = Icons.get_icon(icon_id)

        if not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(self.normal_icon_size)
            btn.setText("")
        elif fallback_icon is not None:
            btn.setIcon(fallback_icon)
            btn.setIconSize(self.normal_icon_size)
            btn.setText("")
        else:
            fallback_text = getattr(Icons, icon_id.upper(), "⚙️") if isinstance(icon_id, str) else "⚙️"
            btn.setText(fallback_text)

        btn.setStyleSheet(AppStyles.TITLE_BAR_ICON_BUTTON_STYLE)
        return btn

    def create_window_control_button(self, icon_id, tooltip):
        """Create a window control button with minimal style"""
        btn = QToolButton()
        btn.setFixedSize(46, 30)
        btn.setToolTip(tooltip)

        icon = Icons.get_icon(icon_id)

        if not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(QSize(10, 10))
            btn.setText("")
        else:
            fallback_text = ""
            font_size = 9

            if icon_id == "minimize":
                fallback_text = "—"
            elif icon_id == "maximize":
                fallback_text = "□" if not self.parent or not self.parent.isMaximized() else "❐"
            elif icon_id == "close":
                fallback_text = "✕"
            else:
                fallback_text = getattr(Icons, icon_id.upper(), "⚙️") if isinstance(icon_id, str) else "⚙️"

            btn.setText(fallback_text)
            btn.setFont(QFont("Segoe UI", font_size))

        if icon_id == "close":
            btn.setStyleSheet(AppStyles.TITLE_BAR_CLOSE_BUTTON_STYLE)
        else:
            btn.setStyleSheet(AppStyles.TITLE_BAR_WINDOW_BUTTON_STYLE)

        return btn

    def create_window_button(self, icon_id, tooltip, size=14, icon_size=None):
        """Create a small window control button with light color"""
        btn = QPushButton()
        btn.setFixedSize(size, size)
        btn.setToolTip(tooltip)

        if icon_size is None:
            icon_size = self.window_ctrl_size

        icon = Icons.get_icon(icon_id)

        if not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(icon_size)
            btn.setText("")
        else:
            fallback_text = ""
            font_size = 9

            if icon_id == "minimize":
                fallback_text = "─"
            elif icon_id == "maximize":
                fallback_text = "□" if not self.parent or not self.parent.isMaximized() else "❐"
            elif icon_id == "close":
                fallback_text = "✕"
            else:
                fallback_text = getattr(Icons, icon_id.upper(), "⚙️") if isinstance(icon_id, str) else "⚙️"

            btn.setText(fallback_text)
            btn.setFont(QFont("Segoe UI", font_size))

        btn.setStyleSheet(AppStyles.TITLE_BAR_WINDOW_BUTTON_STYLE)
        return btn

    def create_back_icon(self):
        """Create a back arrow icon"""
        size = self.normal_icon_size
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))

        path = QPainterPath()
        path.moveTo(size.width() * 0.65, size.height() * 0.15)
        path.lineTo(size.width() * 0.35, size.height() * 0.5)
        path.lineTo(size.width() * 0.65, size.height() * 0.85)
        path.lineTo(size.width() * 0.55, size.height() * 0.5)
        path.closeSubpath()

        painter.drawPath(path)
        painter.end()

        return QIcon(pixmap)

    def create_forward_icon(self):
        """Create a forward arrow icon"""
        size = self.normal_icon_size
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))

        path = QPainterPath()
        path.moveTo(size.width() * 0.35, size.height() * 0.15)
        path.lineTo(size.width() * 0.65, size.height() * 0.5)
        path.lineTo(size.width() * 0.35, size.height() * 0.85)
        path.lineTo(size.width() * 0.45, size.height() * 0.5)
        path.closeSubpath()

        painter.drawPath(path)
        painter.end()

        return QIcon(pixmap)

    def create_fallback_logo(self):
        """Create a simple colored logo as fallback"""
        pixmap = QPixmap(self.logo_icon_size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gradient = QLinearGradient(0, 0, self.logo_icon_size.width(), self.logo_icon_size.height())
        gradient.setColorAt(0, QColor("#4A9EFF"))
        gradient.setColorAt(1, QColor("#0066CC"))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.logo_icon_size.width(), self.logo_icon_size.height(), 6, 6)

        painter.setPen(QColor("white"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Ox")
        painter.end()

        self.logo_label.setPixmap(pixmap)

    def navigate_to_home(self):
        """Navigate to the home page"""
        if hasattr(self.parent, 'switch_to_home'):
            self.parent.switch_to_home()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self.toggle_maximize()
            return True
        return super().eventFilter(obj, event)

    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            icon = Icons.get_icon("maximize")
            if not icon.isNull():
                self.maximize_btn.setIcon(icon)
                self.maximize_btn.setIconSize(QSize(10, 10))
                self.maximize_btn.setText("")
            else:
                self.maximize_btn.setText("□")
                self.maximize_btn.setFont(QFont("Segoe UI", 9))
            self.maximize_btn.setStyleSheet(AppStyles.TITLE_BAR_WINDOW_BUTTON_STYLE)
        else:
            self.parent.showMaximized()
            icon = Icons.get_icon("maximize_active")
            if not icon.isNull():
                self.maximize_btn.setIcon(icon)
                self.maximize_btn.setIconSize(self.window_ctrl_size)
                self.maximize_btn.setText("")
            else:
                self.maximize_btn.setText("⧉")
                self.maximize_btn.setFont(QFont("Segoe UI", 9))
            self.maximize_btn.setStyleSheet(AppStyles.TITLE_BAR_WINDOW_BUTTON_STYLE)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.parent:
            self.double_click_in_progress = True
            if self.parent.isMaximized():
                self.parent.showNormal()
                self.update_maximize_button_icon(False)
                cursor_pos = event.globalPosition().toPoint()
                window_pos = self.parent.pos()
                local_pos = event.position().toPoint()
                new_window_pos = cursor_pos - local_pos
                self.parent.move(new_window_pos)
                self.drag_position = cursor_pos
            else:
                self.parent.showMaximized()
                self.update_maximize_button_icon(True)
                self.drag_position = None
            event.accept()

    def mouseMoveEvent(self, event):
        if (self.drag_position is not None and
                event.buttons() == Qt.MouseButton.LeftButton and
                self.parent and
                not self.parent.isMaximized()):
            delta = event.globalPosition().toPoint() - self.drag_position
            self.parent.move(self.parent.pos() + delta)
            self.drag_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = None
            self.double_click_in_progress = False

    def update_maximize_button_icon(self, is_maximized):
        icon_id = "maximize_active" if is_maximized else "maximize"
        icon = Icons.get_icon(icon_id)
        if not icon.isNull():
            self.maximize_btn.setIcon(icon)
            self.maximize_btn.setIconSize(QSize(10, 10))
            self.maximize_btn.setText("")
        else:
            self.maximize_btn.setText("⧉" if is_maximized else "□")
            self.maximize_btn.setFont(QFont("Segoe UI", 9))
        self.maximize_btn.setStyleSheet(AppStyles.TITLE_BAR_WINDOW_BUTTON_STYLE)

    def update_pinned_dropdown(self, pinned_items):
        """Update the pinned items list from HomePage"""
        print(f"Received pinned items in TitleBar: {pinned_items}")
        if not isinstance(pinned_items, list):
            print(f"Invalid pinned_items type: {type(pinned_items)}. Expected list.")
            pinned_items = []
        
        self.pinned_items = pinned_items
        if self.dropdown_menu and self.dropdown_menu.isVisible():
            self.create_or_update_dropdown()