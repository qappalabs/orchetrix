from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QLineEdit, QTreeWidget,
                             QTreeWidgetItem, QFrame, QMenu, QHeaderView,
                             QMessageBox, QToolButton)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QPoint, QSize, QTimer
from PyQt6.QtGui import QColor, QPainter, QIcon, QMouseEvent, QFont, QPixmap # Added QPixmap

from UI.Styles import AppColors, AppStyles, AppConstants
from utils.kubernetes_client import get_kubernetes_client
from utils.cluster_connector import get_cluster_connector
import logging

from math import sin, cos
from UI.Icons import resource_path  # Add this import at the top of the file

class HomePageSignals(QObject):
    """Centralized signals for navigation between pages"""
    open_cluster_signal = pyqtSignal(str)
    open_preferences_signal = pyqtSignal()
    update_pinned_items_signal = pyqtSignal(list)  # Signal for pinned items

class CircularCheckmark(QLabel):
    """Visual indicator for active/successful status"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 80)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#4CAF50"))
        painter.drawEllipse(10, 10, 60, 60)
        painter.setPen(QColor("#FFFFFF"))
        painter.setPen(Qt.PenStyle.SolidLine)
        painter.drawLine(25, 40, 35, 50)
        painter.drawLine(35, 50, 55, 30)
        painter.end()

class LoadingIndicator(QWidget):
    """Loading spinner for async operations"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_angle)
        self.timer.start(50)
        self.setFixedSize(40, 40)

    def update_angle(self):
        self.angle = (self.angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.rect().center()
        radius = min(self.width(), self.height()) / 2 - 5

        painter.setPen(Qt.PenStyle.NoPen)

        # Draw 12 dots with varying opacity
        for i in range(12):
            angle = (self.angle - i * 30) % 360
            opacity = 0.2 + 0.8 * ((12 - i) % 12) / 12

            x = center.x() + radius * cos(angle * 3.14159 / 180)
            y = center.y() + radius * sin(angle * 3.14159 / 180)

            color = QColor(AppColors.ACCENT_GREEN)
            color.setAlphaF(opacity)
            painter.setBrush(color)

            painter.drawEllipse(int(x), int(y), 5, 5)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        self.timer.start(50)
        super().showEvent(event)

class SmallLoadingIndicator(QWidget):
    """Smaller loading spinner for inline use in tables"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_angle)
        self.timer.start(50)
        self.setFixedSize(16, 16)

    def update_angle(self):
        self.angle = (self.angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.rect().center()
        radius = min(self.width(), self.height()) / 2 - 2

        painter.setPen(Qt.PenStyle.NoPen)

        # Draw 8 dots with varying opacity for a more compact spinner
        for i in range(8):
            angle = (self.angle - i * 45) % 360
            angle_rad = angle * 3.14159 / 180
            opacity = 0.2 + 0.8 * ((8 - i) % 8) / 8

            x = center.x() + radius * cos(angle_rad)
            y = center.y() + radius * sin(angle_rad)

            color = QColor(AppColors.ACCENT_GREEN)
            color.setAlphaF(opacity)
            painter.setBrush(color)

            painter.drawEllipse(int(x - 1.5), int(y - 1.5), 3, 3)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        self.timer.start(50)
        super().showEvent(event)

class SidebarButton(QPushButton):
    """Customized button for sidebar navigation"""
    def __init__(self, text, icon_text, icon_path=None, parent=None):
        super().__init__(text, parent)
        if icon_path:
            resolved_path = resource_path(icon_path)
            self.setIcon(QIcon(resolved_path))
            self.setIconSize(QSize(AppConstants.SIZES["ICON_SIZE"], AppConstants.SIZES["ICON_SIZE"]))
            self.setText(f" {text}")
        else:
            self.setText(f"{icon_text}  {text}")
        self.setCheckable(True)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(AppStyles.SIDEBAR_BUTTON_STYLE)

class OrchestrixGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.signals = HomePageSignals()
        self.open_cluster_signal = self.signals.open_cluster_signal
        self.open_preferences_signal = self.signals.open_preferences_signal
        self.update_pinned_items_signal = self.signals.update_pinned_items_signal

        self.kube_client = get_kubernetes_client()
        self.cluster_connector = get_cluster_connector()

        try:
            from utils.cluster_state_manager import get_cluster_state_manager
            self.cluster_state_manager = get_cluster_state_manager()
            logging.info("Cluster state manager initialized in HomePage")
        except Exception as e:
            logging.error(f"Failed to initialize cluster state manager in HomePage: {e}")
            self.cluster_state_manager = None


        self.kube_client.clusters_loaded.connect(self.on_clusters_loaded)
        self.kube_client.error_occurred.connect(self.show_error_message)

        self.cluster_connector.connection_started.connect(self.on_cluster_connection_started)
        self.cluster_connector.connection_complete.connect(self.on_cluster_connection_complete)
        self.cluster_connector.error_occurred.connect(
            lambda error_type, error_msg: self.show_error_message(error_msg)
        )
        # self.cluster_connector.error_occurred.connect(self.show_error_message)
        self.cluster_connector.metrics_data_loaded.connect(self.check_cluster_data_loaded)
        self.cluster_connector.issues_data_loaded.connect(self.check_cluster_data_loaded)

        self.setWindowTitle("Kubernetes Manager")
        self.setGeometry(100, 100, 1300, 700)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(AppStyles.MAIN_STYLE)

        self.current_view = "Browse All"
        self.search_filter = ""
        self.sidebar_buttons = []
        self.tree_widget = None
        self.browser_label = None
        self.items_label = None
        self.pinned_items = set()

        self.connecting_clusters = set()
        self.waiting_for_cluster_load = None

        # --- New properties for cluster icon colors ---
        self.cluster_colors_cache = {}  # Cache for assigned colors
        self.vibrant_cluster_colors = [
            QColor("#1ABC9C"), QColor("#2ECC71"), QColor("#3498DB"),
            QColor("#9B59B6"), QColor("#F1C40F"), QColor("#E67E22"),
            QColor("#E74C3C"), QColor("#34495E"), QColor("#16A085"),
            QColor("#27AE60"), QColor("#2980B9"), QColor("#8E44AD"),
            QColor("#F39C12"), QColor("#D35400"), QColor("#C0392B")
        ]
        self.next_color_index = 0
        # --- End of new properties ---

        self.init_data_model()
        self.setup_ui()
        self.update_content_view("Browse All")
        QTimer.singleShot(100, self.load_kubernetes_clusters)

    # --- New method to get cluster color ---
    def get_cluster_color(self, cluster_name: str) -> QColor:
        """Assigns a unique vibrant color to a cluster name."""
        if cluster_name not in self.cluster_colors_cache:
            color = self.vibrant_cluster_colors[self.next_color_index % len(self.vibrant_cluster_colors)]
            self.cluster_colors_cache[cluster_name] = color
            self.next_color_index += 1
        return self.cluster_colors_cache[cluster_name]
    # --- End of new method ---

    def load_kubernetes_clusters(self):
        self.kube_client.load_clusters_async()

    def on_clusters_loaded(self, clusters):
        for cluster in clusters:
            exists = False
            for item in self.all_data["Browse All"]:
                if item.get("name") == cluster.name:
                    status = "available"
                    if cluster.status == "active":
                        status = "available"
                    elif cluster.status == "disconnect":
                        status = "disconnect"

                    item.update({
                        "name": cluster.name,
                        "kind": cluster.kind,
                        "source": cluster.source,
                        "label": cluster.label,
                        "status": status,
                        "badge_color": None,
                        "action": self.navigate_to_cluster,
                        "cluster_data": cluster
                    })
                    exists = True
                    break
            if not exists:
                status = "available"
                if cluster.status == "disconnect":
                    status = "disconnect"

                self.all_data["Browse All"].append({
                    "name": cluster.name,
                    "kind": cluster.kind,
                    "source": cluster.source,
                    "label": cluster.label,
                    "status": status,
                    "badge_color": None,
                    "action": self.navigate_to_cluster,
                    "cluster_data": cluster
                })
        self.update_filtered_views()
        self.update_content_view(self.current_view)
        self.update_pinned_items_signal.emit(list(self.pinned_items))

    def check_cluster_data_loaded(self, data):
        if self.waiting_for_cluster_load:
            cluster_name = self.waiting_for_cluster_load

            if hasattr(self.cluster_connector, 'is_data_loaded') and self.cluster_connector.is_data_loaded(cluster_name):
                self.waiting_for_cluster_load = None
                for view_type in self.all_data:
                    for item in self.all_data[view_type]:
                        if item.get("name") == cluster_name:
                            item["status"] = "connected"
                self.update_content_view(self.current_view)
                QTimer.singleShot(100, lambda: self.open_cluster_signal.emit(cluster_name))

    def on_cluster_connection_started(self, cluster_name):
        self.connecting_clusters.add(cluster_name)
        for view_type in self.all_data:
            for item in self.all_data[view_type]:
                if item.get("name") == cluster_name:
                    item["status"] = "connecting"
        self.update_content_view(self.current_view)

    def on_cluster_connection_complete(self, cluster_name, success):
        self.connecting_clusters.discard(cluster_name)
        for view_type in self.all_data:
            for item in self.all_data[view_type]:
                if item.get("name") == cluster_name:
                    if success:
                        item["status"] = "loading"
                        self.waiting_for_cluster_load = cluster_name
                    else:
                        item["status"] = "disconnect"
        self.update_content_view(self.current_view)

    def show_error_message(self, error_message):
        """Display error messages with better formatting"""
        try:
            # Clean up the message
            if not error_message:
                error_message = "An unknown error occurred."
            
            error_message = str(error_message).strip()
            
            # Log for debugging
            logging.error(f"Showing error dialog: {error_message}")
            
            # Create message box
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Connection Error")
            msg_box.setText(error_message)
            
            # Add helpful suggestions for Docker Desktop issues
            if "docker-desktop" in error_message.lower() and "refused" in error_message.lower():
                msg_box.setInformativeText(
                    "💡 Try these solutions:\n"
                    "• Start Docker Desktop\n"
                    "• Enable Kubernetes in Docker Desktop settings\n"
                    "• Wait for Kubernetes to initialize completely"
                )
            
            # Style the dialog
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    font-size: 12px;
                    min-width: 400px;
                }
                QMessageBox QLabel {
                    color: #ffffff;
                    padding: 10px;
                }
                QMessageBox QPushButton {
                    background-color: #404040;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 8px 15px;
                    border-radius: 3px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #505050;
                }
            """)
            
            msg_box.exec()
            
        except Exception as e:
            logging.error(f"Error showing dialog: {e}")
            # Fallback
            QMessageBox.critical(self, "Error", str(error_message))


    def update_content_view(self, view_type):
        self.current_view = view_type
        self.browser_label.setText(view_type)
        for button in self.sidebar_buttons:
            button.setChecked(view_type in button.text())
        self.filter_content(self.search_filter)

    def filter_content(self, search_text=None):
        if search_text is not None:
            self.search_filter = search_text
        view_data = self.all_data[self.current_view]
        if self.search_filter:
            search_term = self.search_filter.lower()
            filtered_data = [
                item for item in view_data if any(
                    search_term in str(item.get(field, "")).lower()
                    for field in ["name", "kind", "source", "label", "status"]
                )
            ]
        else:
            filtered_data = view_data
        self.items_label.setText(f"{len(filtered_data)} item{'s' if len(filtered_data) != 1 else ''}")
        self.tree_widget.clear()
        for item in filtered_data:
            self.add_table_item(**{k: item[k] for k in ["name", "kind", "source", "label", "status", "badge_color"]}, original_data=item)

    def add_table_item(self, name, kind, source, label, status, badge_color=None, original_data=None):
        item = QTreeWidgetItem(self.tree_widget)
        item.setSizeHint(0, QSize(0, AppConstants.SIZES["ROW_HEIGHT"]))
        item.setData(0, Qt.ItemDataRole.UserRole, name)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, original_data)

        if badge_color:
            parts = name.split(' ', 1)
            item_text = parts[1] if len(parts) > 1 else name
        else:
            item_text = name

        # --- Modified Name column widget to include cluster icon ---
        name_widget = QWidget()
        name_widget.setStyleSheet("background: transparent; padding: 0px; margin: 0px;")
        name_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        name_layout = QHBoxLayout(name_widget)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(6)  # Spacing between icon, text, and pin button
        name_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        is_cluster = "Cluster" in kind

        # Add colored cluster icon if it's a cluster
        if is_cluster:
            cluster_icon_label = QLabel()
            icon_size = AppConstants.SIZES.get("ICON_SIZE_SMALL", 16)

            # Load and color the cluster icon
            try:
                cluster_color = self.get_cluster_color(name)
                colored_pixmap = self.create_colored_icon("icons/Cluster_Logo.svg", cluster_color, icon_size)

                if not colored_pixmap.isNull():
                    cluster_icon_label.setPixmap(colored_pixmap)
                    cluster_icon_label.setFixedSize(icon_size, icon_size)
                    name_layout.addWidget(cluster_icon_label)
                else:
                    print(f"Warning: Could not create colored icon for {name}")
            except Exception as e:
                print(f"Error processing cluster icon for {name}: {e}")

        name_label = QLabel(name if not badge_color else item_text)
        font = QFont("Segoe UI", 10)
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        name_label.setFont(font)
        name_label.setStyleSheet("color: #FFFFFF; background: transparent; padding: 0px; margin: 0px;")
        name_layout.addWidget(name_label)

        if original_data and 'cluster_data' in original_data:
            pin_btn = QPushButton()
            pin_btn.setFixedSize(20, 20)
            pin_icon_path = resource_path("icons/pin.png") if name not in self.pinned_items else resource_path("icons/unpin.png")
            pin_btn.setIcon(QIcon(pin_icon_path))
            pin_btn.setIconSize(QSize(16, 16))
            pin_btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; padding: 0px; margin: 0px; }
                QPushButton:hover { background: #3e3e3e; }
            """)
            pin_btn.clicked.connect(lambda checked=False, n=name: self.toggle_pin_item(n))
            name_layout.addWidget(pin_btn)

        self.tree_widget.setItemWidget(item, 0, name_widget)

        # --- NEW: Create custom widgets for Kind, Source, and Label columns with hand cursor ---

        # Kind column (column 1)
        kind_widget = QWidget()
        kind_widget.setStyleSheet("background: transparent; padding: 0px; margin: 0px;")
        kind_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        kind_layout = QHBoxLayout(kind_widget)
        kind_layout.setContentsMargins(8, 0, 8, 0)  # Add some padding
        kind_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        kind_label = QLabel(kind)
        font = QFont("Segoe UI", 10)
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        kind_label.setFont(font)
        kind_label.setStyleSheet("color: #FFFFFF; background: transparent; padding: 0px; margin: 0px;")
        kind_layout.addWidget(kind_label)
        self.tree_widget.setItemWidget(item, 1, kind_widget)

        # Source column (column 2)
        source_widget = QWidget()
        source_widget.setStyleSheet("background: transparent; padding: 0px; margin: 0px;")
        source_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        source_layout = QHBoxLayout(source_widget)
        source_layout.setContentsMargins(8, 0, 8, 0)  # Add some padding
        source_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        source_label = QLabel(source)
        font = QFont("Segoe UI", 10)
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        source_label.setFont(font)
        source_label.setStyleSheet("color: #FFFFFF; background: transparent; padding: 0px; margin: 0px;")
        source_layout.addWidget(source_label)
        self.tree_widget.setItemWidget(item, 2, source_widget)

        # Label column (column 3)
        label_widget = QWidget()
        label_widget.setStyleSheet("background: transparent; padding: 0px; margin: 0px;")
        label_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        label_layout = QHBoxLayout(label_widget)
        label_layout.setContentsMargins(8, 0, 8, 0)  # Add some padding
        label_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        label_label = QLabel(label)
        font = QFont("Segoe UI", 10)
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        label_label.setFont(font)
        label_label.setStyleSheet("color: #FFFFFF; background: transparent; padding: 0px; margin: 0px;")
        label_layout.addWidget(label_label)
        self.tree_widget.setItemWidget(item, 3, label_widget)

        # --- END of new custom widgets for Kind, Source, and Label ---

        status_colors = {
            "available": AppColors.STATUS_AVAILABLE,
            "active": AppColors.STATUS_ACTIVE,
            "connected": AppColors.STATUS_AVAILABLE,
            "disconnect": AppColors.STATUS_DISCONNECTED,
            "connecting": AppColors.STATUS_WARNING,
            "loading": AppColors.STATUS_WARNING
        }

        status_widget = QWidget()
        status_widget.setObjectName("statusCell")
        status_widget.setStyleSheet("QWidget#statusCell { background: transparent; }")
        status_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(5, 0, 0, 0)
        status_layout.setSpacing(5)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        if is_cluster:
            if status in ["connecting", "loading"]:
                loading_indicator = SmallLoadingIndicator()
                status_layout.addWidget(loading_indicator)
                status_text = "Connecting..." if status == "connecting" else "Loading data..."
                status_label = QLabel(status_text)
                status_label.setStyleSheet(f"color: {status_colors.get(status, AppColors.STATUS_DISCONNECTED)}; background: transparent;")
                status_layout.addWidget(status_label)
            else:
                if status == "available": status_text = "Available"
                elif status in ["active", "connected"]: status_text = "Connected"
                elif status == "disconnect": status_text = "Disconnected"
                else: status_text = status.capitalize()
                status_label = QLabel(status_text)
                status_label.setStyleSheet(f"color: {status_colors.get(status, AppColors.STATUS_DISCONNECTED)}; background: transparent;")
                status_layout.addWidget(status_label)
        else:
            status_text = status
            status_label = QLabel(status_text)
            status_label.setStyleSheet(f"color: {status_colors.get(status, AppColors.STATUS_DISCONNECTED)}; background: transparent;")
            status_layout.addWidget(status_label)
        self.tree_widget.setItemWidget(item, 4, status_widget)

        action_widget = QWidget()
        action_widget.setFixedWidth(AppConstants.SIZES["ACTION_WIDTH"])
        action_widget.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        menu_btn = QToolButton()
        icon = QIcon("icons/Moreaction_Button.svg")
        menu_btn.setIcon(icon)
        menu_btn.setIconSize(QSize(AppConstants.SIZES["ICON_SIZE"], AppConstants.SIZES["ICON_SIZE"]))
        menu_btn.setText("")
        menu_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        menu_btn.setFixedWidth(AppConstants.SIZES["ACTION_WIDTH"])
        menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        menu_btn.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE)
        menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        if status in ["connecting", "loading"] and (name in self.connecting_clusters or self.waiting_for_cluster_load == name):
            menu_btn.setEnabled(False)
            menu_btn.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE + " QToolButton:disabled { opacity: 0.5; background-color: transparent; }")
        else:
            menu = QMenu(action_widget)
            menu.setStyleSheet(AppStyles.MENU_STYLE)
            if status == "available" and is_cluster:
                open_action = menu.addAction("Open")
                connect_action = menu.addAction("Connect")
                delete_action = menu.addAction("Delete")
            elif status in ["active", "connected"]:
                open_action = menu.addAction("Open")
                if is_cluster: disconnect_action = menu.addAction("Disconnect")
                delete_action = menu.addAction("Delete")
            elif status == "disconnect" and is_cluster:
                connect_action = menu.addAction("Connect")
                delete_action = menu.addAction("Delete")
            else:
                open_action = menu.addAction("Open")
                delete_action = menu.addAction("Delete")

            def show_menu():
                pos = menu_btn.mapToGlobal(QPoint(0, menu_btn.height()))
                action = menu.exec(pos)
                if action is None: return
                if status == "available" and is_cluster:
                    if action == open_action: self.handle_open_item(item)
                    elif action == connect_action: self.handle_connect_item(item)
                    elif action == delete_action: self.handle_delete_item(item)
                elif status in ["active", "connected"]:
                    if action == open_action: self.handle_open_item(item)
                    elif is_cluster and 'disconnect_action' in locals() and action == disconnect_action: self.handle_disconnect_item(item)
                    elif action == delete_action: self.handle_delete_item(item)
                elif status == "disconnect" and is_cluster:
                    if action == connect_action: self.handle_connect_item(item)
                    elif action == delete_action: self.handle_delete_item(item)
                else:
                    if action == open_action: self.handle_open_item(item)
                    elif action == delete_action: self.handle_delete_item(item)
            menu_btn.clicked.connect(show_menu)
        action_layout.addWidget(menu_btn)
        self.tree_widget.setItemWidget(item, 5, action_widget)
        item.setSizeHint(5, QSize(AppConstants.SIZES["ACTION_WIDTH"], AppConstants.SIZES["ROW_HEIGHT"]))

        # Set size hints for all columns
        item.setSizeHint(0, QSize(0, AppConstants.SIZES["ROW_HEIGHT"]))
        item.setSizeHint(1, QSize(0, AppConstants.SIZES["ROW_HEIGHT"]))
        item.setSizeHint(2, QSize(0, AppConstants.SIZES["ROW_HEIGHT"]))
        item.setSizeHint(3, QSize(0, AppConstants.SIZES["ROW_HEIGHT"]))
        item.setSizeHint(4, QSize(0, AppConstants.SIZES["ROW_HEIGHT"]))

    def create_colored_icon(self, icon_path: str, color: QColor, size: int) -> QPixmap:
        """
        Creates a colored version of an icon while preserving its shape and details.
        """
        # Load the original icon
        original_pixmap = QPixmap(resource_path(icon_path))
        if original_pixmap.isNull():
            return QPixmap()  # Return empty pixmap if loading fails

        # Scale the icon to the desired size
        scaled_pixmap = original_pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Create a new pixmap with the same size and transparency
        colored_pixmap = QPixmap(scaled_pixmap.size())
        colored_pixmap.fill(Qt.GlobalColor.transparent)

        # Use QPainter to draw the colored version
        painter = QPainter(colored_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Draw the original icon
        painter.drawPixmap(0, 0, scaled_pixmap)

        # Apply color overlay using composition mode
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(colored_pixmap.rect(), color)

        painter.end()
        return colored_pixmap

    def create_colored_icon_alternative(self, icon_path: str, color: QColor, size: int) -> QPixmap:
        """
        Alternative method using QIcon for better SVG handling.
        """
        # Create QIcon from the SVG file
        icon = QIcon(resource_path(icon_path))
        if icon.isNull():
            return QPixmap()

        # Get pixmap from icon
        original_pixmap = icon.pixmap(QSize(size, size))

        # Create colored version
        colored_pixmap = QPixmap(original_pixmap.size())
        colored_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(colored_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the icon
        painter.drawPixmap(0, 0, original_pixmap)

        # Apply color tint
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(colored_pixmap.rect(), color)

        painter.end()
        return colored_pixmap

    def init_data_model(self):
        self.all_data = {
            "Browse All": [
                {"name": "Welcome Page", "kind": "General", "source": "app", "label": "",
                 "status": "active", "badge_color": None, "action": self.navigate_to_welcome},
                {"name": "Settings", "kind": "General", "source": "app", "label": "",
                 "status": "active", "badge_color": None, "action": self.navigate_to_preferences},
                {"name": "OxW Orchetrix Website", "kind": "Weblinks", "source": "local", "label": "",
                 "status": "available", "badge_color": "#f0ad4e", "action": self.open_web_link},
                {"name": "OxD Orchetrix Documentation", "kind": "Weblinks", "source": "local", "label": "",
                 "status": "available", "badge_color": "#ecd06f", "action": self.open_web_link},
                {"name": "OxOB Orchetrix Official blog", "kind": "Weblinks", "source": "local", "label": "",
                 "status": "available", "badge_color": "#d9534f", "action": self.open_web_link},
                {"name": "KD Kubernetes Document", "kind": "Weblinks", "source": "local", "label": "",
                 "status": "available", "badge_color": "#5cb85c", "action": self.open_web_link}
            ]
        }
        self.update_filtered_views()

    def update_filtered_views(self):
        view_types = {
            "General": lambda item: item["kind"] == "General",
            "All Clusters": lambda item: "Cluster" in item["kind"], #
            "Web Links": lambda item: item["kind"] == "Weblinks"
        }
        for view_name, filter_func in view_types.items():
            self.all_data[view_name] = [item for item in self.all_data["Browse All"] if filter_func(item)]

    def handle_item_single_click(self, item, column):
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        original_data = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if not original_data: return
        if "Cluster" in original_data.get("kind", ""): self.navigate_to_cluster(original_data)
        else:
            if original_data.get("action"): original_data["action"](original_data)

    def create_table_widget(self):
        tree_widget = QTreeWidget()
        tree_widget.setColumnCount(6)
        tree_widget.setHeaderLabels(["Name", "Kind", "Source", "Label", "Status", ""])
        tree_widget.setHeaderHidden(False)
        column_widths = [300, 180, 150, 120, 120, AppConstants.SIZES["ACTION_WIDTH"]]
        for i, width in enumerate(column_widths): tree_widget.setColumnWidth(i, width)
        header = tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, len(column_widths)): header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, AppConstants.SIZES["ACTION_WIDTH"])
        font = QFont("Segoe UI", 13)
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        tree_widget.setFont(font)
        tree_widget.setStyleSheet(AppStyles.TREE_WIDGET_STYLE)
        tree_widget.setIconSize(QSize(20, 20))
        tree_widget.setIndentation(0)
        tree_widget.setAlternatingRowColors(False)
        tree_widget.setRootIsDecorated(False)
        tree_widget.setItemsExpandable(False)
        tree_widget.setHorizontalScrollMode(QTreeWidget.ScrollMode.ScrollPerPixel)
        tree_widget.setContentsMargins(0, 0, 0, 0)
        tree_widget.itemClicked.connect(self.handle_item_single_click)
        return tree_widget

    def _find_data_item(self, view, original_name):
        for data_item in self.all_data[view]:
            if data_item["name"] == original_name: return data_item
        return None

    def handle_open_item(self, item):
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        original_data = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if original_data and original_data["action"]: original_data["action"](original_data)

    def handle_connect_item(self, item):
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        original_data = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if original_data and "Cluster" in original_data["kind"]:
            for view_type in self.all_data:
                for d_item in self.all_data[view_type]: # renamed item to d_item to avoid conflict
                    if d_item["name"] == original_name: d_item["status"] = "connecting"
            self.connecting_clusters.add(original_name)
            self.update_content_view(self.current_view)
            QTimer.singleShot(100, lambda: self.cluster_connector.connect_to_cluster(original_name))

    def handle_disconnect_item(self, item):
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        
        logging.info(f"Disconnecting cluster: {original_name}")
        
        # Update UI status first
        for view_type in self.all_data:
            for data_item in self.all_data[view_type]:
                if data_item["name"] == original_name: 
                    data_item["status"] = "disconnect"
                    logging.info(f"Updated UI status for {original_name} to disconnect")
        
        # Clean up cluster connector data
        try:
            if hasattr(self.cluster_connector, 'data_cache') and original_name in self.cluster_connector.data_cache:
                del self.cluster_connector.data_cache[original_name]
                logging.info(f"Cleared data cache for {original_name}")
                
            if hasattr(self.cluster_connector, 'loading_complete') and original_name in self.cluster_connector.loading_complete:
                del self.cluster_connector.loading_complete[original_name]
                logging.info(f"Cleared loading complete flag for {original_name}")
                
            if (hasattr(self.cluster_connector, 'kube_client') and 
                hasattr(self.cluster_connector.kube_client, 'current_cluster') and
                self.cluster_connector.kube_client.current_cluster == original_name):
                self.cluster_connector.stop_polling()
                # Also reset the current cluster in kube_client
                self.cluster_connector.kube_client.current_cluster = None
                logging.info(f"Stopped polling and reset current cluster for {original_name}")
                
            if hasattr(self.cluster_connector, 'disconnect_cluster'):
                self.cluster_connector.disconnect_cluster(original_name)
                logging.info(f"Called cluster_connector.disconnect_cluster for {original_name}")
        except Exception as e:
            logging.error(f"Error during cluster connector cleanup for {original_name}: {e}")
        
        # IMPORTANT: Notify the cluster state manager about the disconnection
        try:
            if self.cluster_state_manager:
                self.cluster_state_manager.disconnect_cluster(original_name)
                logging.info(f"Notified cluster state manager about disconnect: {original_name}")
            else:
                logging.warning("Cluster state manager not available for disconnect notification")
        except Exception as e:
            logging.error(f"Error notifying cluster state manager about disconnect: {e}")
        
        # Remove from connecting clusters set if present
        self.connecting_clusters.discard(original_name)
        
        # Reset waiting for cluster load if it matches
        if self.waiting_for_cluster_load == original_name:
            self.waiting_for_cluster_load = None
            logging.info(f"Reset waiting_for_cluster_load for {original_name}")
        
        # Update the view
        self.update_content_view(self.current_view)
        logging.info(f"Cluster disconnect completed for: {original_name}")

    def disconnect_cluster(self, cluster_name):
        """Disconnect from a specific cluster"""
        try:
            logging.info(f"Disconnecting from cluster: {cluster_name}")
            
            # Stop any workers for this cluster
            self._stop_workers_for_cluster(cluster_name)
            
            # Update connection state
            self.connection_states[cluster_name] = "disconnected"
            
            # Clean up cached data
            if cluster_name in self.data_cache:
                del self.data_cache[cluster_name]
                logging.info(f"Cleared data cache for {cluster_name}")
            
            if cluster_name in self.loading_complete:
                del self.loading_complete[cluster_name]
                logging.info(f"Cleared loading complete flag for {cluster_name}")
            
            # Stop polling and reset current cluster if this is the current cluster
            if (hasattr(self.kube_client, 'current_cluster') and 
                self.kube_client.current_cluster == cluster_name):
                self.stop_polling()
                self.kube_client.current_cluster = None
                logging.info(f"Stopped polling and reset current cluster for {cluster_name}")
                
            # Reset current cluster in the connector itself
            if hasattr(self, 'current_cluster') and self.current_cluster == cluster_name:
                self.current_cluster = None
                logging.info(f"Reset cluster connector current_cluster for {cluster_name}")
                
        except Exception as e:
            logging.error(f"Error disconnecting from cluster {cluster_name}: {e}")

    def handle_delete_item(self, item):
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        index = self.tree_widget.indexOfTopLevelItem(item)
        self.tree_widget.takeTopLevelItem(index)
        for view_type in self.all_data:
            self.all_data[view_type] = [
                d_item for d_item in self.all_data[view_type] # renamed item to d_item
                if d_item["name"] != original_name
            ]
        current_count = len(self.all_data[self.current_view])
        self.items_label.setText(f"{current_count} item{'s' if current_count != 1 else ''}")

    def navigate_to_welcome(self, item): pass
    def navigate_to_preferences(self, item): self.open_preferences_signal.emit()

    def navigate_to_cluster(self, item):
        cluster_name = item["name"]
        cluster_status = item["status"]
        if cluster_status in ["connecting", "loading"]: return
        if hasattr(self.cluster_connector, 'is_data_loaded') and self.cluster_connector.is_data_loaded(cluster_name):
            self.open_cluster_signal.emit(cluster_name)
            return
        for view_type in self.all_data:
            for data_item in self.all_data[view_type]:
                if data_item["name"] == cluster_name: data_item["status"] = "connecting"
        self.update_content_view(self.current_view)
        QTimer.singleShot(100, lambda: self.cluster_connector.connect_to_cluster(cluster_name))

    def open_web_link(self, item): pass

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.content_container = QWidget()
        self.horizontal_layout = QHBoxLayout(self.content_container)
        self.horizontal_layout.setContentsMargins(0, 0, 0, 0)
        self.horizontal_layout.setSpacing(0)
        self.main_layout.addWidget(self.content_container)
        self.create_sidebar()
        self.create_main_content()
        self.fix_action_column_width()

    def create_sidebar(self):
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(AppConstants.SIZES["SIDEBAR_WIDTH"])
        self.sidebar.setStyleSheet(AppStyles.SIDEBAR_CONTAINER_STYLE)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(2)
        sidebar_options = [
            {"text": "Browse All", "icon": "🔍", "icon_path": "icons/browse.svg", "action": lambda: self.update_content_view("Browse All")},
            {"text": "General", "icon": "⚙️", "icon_path": "icons/settings.svg", "action": lambda: self.update_content_view("General")},
            {"text": "All Clusters", "icon": "🔄", "icon_path": "icons/clusters.svg", "action": lambda: self.update_content_view("All Clusters")},
            {"text": "Web Links", "icon": "🔗", "icon_path": "icons/links.svg", "action": lambda: self.update_content_view("Web Links")}
        ]
        self.sidebar_buttons = []
        for option in sidebar_options:
            button = SidebarButton(option["text"], option["icon"], option.get("icon_path"))
            button.clicked.connect(option["action"])
            self.sidebar_layout.addWidget(button)
            self.sidebar_buttons.append(button)
        self.sidebar_layout.addStretch()
        self.horizontal_layout.addWidget(self.sidebar)

    def create_main_content(self):
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.create_top_bar()
        self.create_content_area()
        self.horizontal_layout.addWidget(self.content)

    def create_top_bar(self):
        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(AppConstants.SIZES["TOPBAR_HEIGHT"])
        self.top_bar.setStyleSheet(AppStyles.TOP_BAR_STYLE)
        self.top_bar_layout = QHBoxLayout(self.top_bar)
        self.top_bar_layout.setContentsMargins(10, 0, 10, 0)
        self.browser_label = QLabel("Browse All")
        self.browser_label.setStyleSheet(AppStyles.BROWSER_LABEL_STYLE)
        self.items_label = QLabel("9 items")
        self.items_label.setStyleSheet(AppStyles.ITEMS_LABEL_STYLE)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search...")
        self.search.setFixedWidth(300)
        self.search.setStyleSheet(AppStyles.SEARCH_STYLE)
        self.search.textChanged.connect(self.filter_content)
        self.top_bar_layout.addWidget(self.browser_label)
        self.top_bar_layout.addWidget(self.items_label)
        self.top_bar_layout.addStretch()
        self.top_bar_layout.addWidget(self.search)
        self.content_layout.addWidget(self.top_bar)

    def create_content_area(self):
        self.main_content = QWidget()
        self.main_content_layout = QVBoxLayout(self.main_content)
        self.main_content_layout.setContentsMargins(20, 20, 20, 20)
        self.main_content_layout.setSpacing(0)
        self.table_container = QFrame()
        self.table_container.setFrameShape(QFrame.Shape.NoFrame)
        self.table_container.setStyleSheet(AppStyles.CONTENT_AREA_STYLE)
        self.table_container_layout = QVBoxLayout(self.table_container)
        self.table_container_layout.setContentsMargins(0, 0, 0, 0)
        self.table_container_layout.setSpacing(0)
        self.tree_widget = self.create_table_widget()
        self.table_container_layout.addWidget(self.tree_widget)
        self.main_content_layout.addWidget(self.table_container)
        self.content_layout.addWidget(self.main_content)

    def fix_action_column_width(self):
        if not hasattr(self, 'tree_widget') or self.tree_widget is None: return
        header = self.tree_widget.header()
        header.setStretchLastSection(False)
        action_column_width = AppConstants.SIZES["ACTION_WIDTH"]
        self.tree_widget.setColumnWidth(5, action_column_width)
        header.resizeSection(5, action_column_width)
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            action_widget = self.tree_widget.itemWidget(item, 5)
            if action_widget:
                action_widget.setFixedWidth(action_column_width)
                action_widget.setContentsMargins(0, 0, 0, 0)
                # Check if action_widget has children before iterating
                if hasattr(action_widget, 'children'):
                    for child in action_widget.children():
                        if isinstance(child, QPushButton): # Should be QToolButton based on your code
                            child.setFixedWidth(action_column_width)
                            child.setContentsMargins(0,0,0,0)
                        elif isinstance(child, QToolButton):
                            child.setFixedWidth(action_column_width)
                            # QToolButton might not directly have setContentsMargins,
                            # its layout or padding would handle spacing.

    def toggle_pin_item(self, name):
        data_item = None
        # Iterate through all_data to find the item, as current_view might not always be "Browse All"
        # and cluster_data is part of the items in "Browse All" initially
        for item_in_all_data in self.all_data.get("Browse All", []):
            if item_in_all_data.get("name") == name and 'cluster_data' in item_in_all_data:
                data_item = item_in_all_data
                break

        if not data_item:
            # Fallback or safety check if not found in "Browse All" (though it should be for pinnable items)
            # This part of the logic might need adjustment if items can be pinned from other views
            # without being in "Browse All" with 'cluster_data'.
            # For now, we rely on the 'cluster_data' check which implies it's from kube_client.
            # print(f"Debug: Item {name} not found with cluster_data for pinning.")
            return


        if name in self.pinned_items:
            self.pinned_items.remove(name)
        else:
            self.pinned_items.add(name)

        self.update_pinned_items_signal.emit(list(self.pinned_items))
        # No need to call update_content_view here, as only the icon of the pin button changes.
        # The pin button icon is updated directly below.

        # Update the pin button icon in the tree_widget
        for i in range(self.tree_widget.topLevelItemCount()):
            tree_item = self.tree_widget.topLevelItem(i)
            if tree_item.data(0, Qt.ItemDataRole.UserRole) == name:
                name_widget = self.tree_widget.itemWidget(tree_item, 0)
                if name_widget: # Ensure name_widget exists
                    for child_widget in name_widget.children():
                        if isinstance(child_widget, QPushButton) and hasattr(child_widget, 'setIcon'): # Check if it's the pin button
                            # Check the actual name again to be super sure it's a pin button for this item
                            # This logic assumes the pin button is a direct child and identifiable
                            current_pin_icon_path = resource_path("icons/pin.png") if name not in self.pinned_items else resource_path("icons/unpin.png")
                            child_widget.setIcon(QIcon(current_pin_icon_path))
                            break # Found and updated the pin button