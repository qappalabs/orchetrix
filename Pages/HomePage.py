from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QLineEdit, QTreeWidget, 
                             QTreeWidgetItem, QFrame, QMenu, QHeaderView,
                             QMessageBox)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QPoint, QSize, QTimer
from PyQt6.QtGui import QColor, QPainter, QIcon, QMouseEvent

from UI.Styles import AppColors, AppStyles, AppConstants
from utils.kubernetes_client import get_kubernetes_client
from utils.cluster_connector import get_cluster_connector

from math import sin, cos

class HomePageSignals(QObject):
    """Centralized signals for navigation between pages"""
    open_cluster_signal = pyqtSignal(str)
    open_preferences_signal = pyqtSignal()

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
            
            x = center.x() + radius * 0.8 * 0.8 * 0.9 * 0.99 * 0.95 * 0.8 * 0.75 * 0.5 * 0.6 * 0.93 * 1 * 0.8 * 0.95 * 1.0 * 0.8 * 0.80 * 0.8 * 0.9 * 0.95 * 0.8 * 0.85 * 0.6 * 0.7 * 0.9 * 0.8 * 0.7 * 0.8 * 0.9 * 0.8 * 0.75 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * cos(angle * 3.14159 / 180)
            y = center.y() + radius * 0.8 * 0.8 * 0.9 * 0.99 * 0.95 * 0.8 * 0.75 * 0.5 * 0.6 * 0.93 * 1 * 0.8 * 0.95 * 1.0 * 0.8 * 0.80 * 0.8 * 0.9 * 0.95 * 0.8 * 0.85 * 0.6 * 0.7 * 0.9 * 0.8 * 0.7 * 0.8 * 0.9 * 0.8 * 0.75 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * 0.8 * 0.85 * 0.8 * 0.9 * 0.8 * 0.8 * sin(angle * 3.14159 / 180)
            
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
            self.setIcon(QIcon(icon_path))
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

        self.kube_client = get_kubernetes_client()
        self.cluster_connector = get_cluster_connector()
        
        # Connect to client signals
        self.kube_client.clusters_loaded.connect(self.on_clusters_loaded)
        self.kube_client.error_occurred.connect(self.show_error_message)
        
        # Connect to connector signals
        self.cluster_connector.connection_started.connect(self.on_cluster_connection_started)
        self.cluster_connector.connection_complete.connect(self.on_cluster_connection_complete)
        self.cluster_connector.error_occurred.connect(self.show_error_message)
        self.cluster_connector.metrics_data_loaded.connect(self.check_cluster_data_loaded)
        self.cluster_connector.issues_data_loaded.connect(self.check_cluster_data_loaded)

        self.drag_position = None
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
        
        # Keep track of clusters in connection process
        self.connecting_clusters = set()
        # Add flag to track if we're waiting for data to load
        self.waiting_for_cluster_load = None

        self.init_data_model()
        self.setup_ui()
        self.update_content_view("Browse All")
        QTimer.singleShot(100, self.load_kubernetes_clusters)



    def load_kubernetes_clusters(self):
        self.kube_client.load_clusters_async()

    def on_clusters_loaded(self, clusters):
        for cluster in clusters:
            exists = False
            for item in self.all_data["Browse All"]:
                if item.get("name") == cluster.name:

                    # Ensure status starts as "available" rather than using the existing status
                    status = "available"
                    if cluster.status == "active":
                        status = "available"  # Even active clusters show as available initially
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

                # Start new clusters with "available" status
                status = "available"
                if cluster.status == "disconnect":
                    status = "disconnect"  # Only keep disconnect status

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

    def check_cluster_data_loaded(self, data):
        """Check if all data is loaded for the cluster we're waiting on"""
        if self.waiting_for_cluster_load:
            cluster_name = self.waiting_for_cluster_load
            
            # Check if data is fully loaded
            if hasattr(self.cluster_connector, 'is_data_loaded') and self.cluster_connector.is_data_loaded(cluster_name):
                # Clear waiting flag
                self.waiting_for_cluster_load = None
                
                # Data is fully loaded, update status to connected
                print(f"All data loaded for {cluster_name}, navigating to cluster view")
                
                # Update the status to "connected" instead of "available"
                for view_type in self.all_data:
                    for item in self.all_data[view_type]:
                        if item.get("name") == cluster_name:
                            item["status"] = "connected"  # New status to show "Connected"
                
                # Refresh the view first to show "Connected" status
                self.update_content_view(self.current_view)
                
                # Then navigate to the cluster view
                QTimer.singleShot(100, lambda: self.open_cluster_signal.emit(cluster_name))
    def on_cluster_connection_started(self, cluster_name):
        """Handle when a cluster connection process starts"""
        self.connecting_clusters.add(cluster_name)
        
        # Update the UI to show connecting status
        for view_type in self.all_data:
            for item in self.all_data[view_type]:
                if item.get("name") == cluster_name:
                    item["status"] = "connecting"
                    
        # Refresh the view to show the connecting status
        self.update_content_view(self.current_view)
    
    def on_cluster_connection_complete(self, cluster_name, success):
        """Handle when a cluster connection completes"""
        # Remove from connecting clusters set
        self.connecting_clusters.discard(cluster_name)
        
        # Update the status in the data model
        for view_type in self.all_data:
            for item in self.all_data[view_type]:
                if item.get("name") == cluster_name:
                    if success:
                        # Change to "loading" instead of "available"
                        item["status"] = "loading"
                        # Set waiting flag for this cluster
                        self.waiting_for_cluster_load = cluster_name
                        print(f"Connection to {cluster_name} successful, loading data...")
                    else:
                        item["status"] = "disconnect"
                        print(f"Connection to {cluster_name} failed")
        
        # Refresh the view to update status
        self.update_content_view(self.current_view)

    def show_error_message(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= AppConstants.SIZES["TOPBAR_HEIGHT"]:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = None
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

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
            self.add_table_item(**{k: item[k] for k in ["name", "kind", "source", "label", "status", "badge_color"]})

    def add_table_item(self, name, kind, source, label, status, badge_color=None):
        item = QTreeWidgetItem(self.tree_widget)
        item.setSizeHint(0, QSize(0, AppConstants.SIZES["ROW_HEIGHT"]))
        item.setData(0, Qt.ItemDataRole.UserRole, name)

        if badge_color:
            parts = name.split(' ', 1)
            item_text = parts[1] if len(parts) > 1 else name
            item.setText(0, item_text)
        else:
            item.setText(0, name)

        item.setText(1, kind)
        item.setText(2, source)
        item.setText(3, label)

        # Define status colors
        status_colors = {
            "available": AppColors.STATUS_AVAILABLE,
            "active": AppColors.STATUS_ACTIVE,
            "connected": AppColors.STATUS_AVAILABLE,  # Add "connected" status with same color as available
            "disconnect": AppColors.STATUS_DISCONNECTED,
            "connecting": AppColors.STATUS_WARNING,
            "loading": AppColors.STATUS_WARNING
        }
        
        # Check if this is a cluster item
        is_cluster = "Cluster" in kind
        
        # Create column cell for status
        status_widget = QWidget()
        status_widget.setObjectName("statusCell")
        status_widget.setStyleSheet("QWidget#statusCell { background: transparent; }")
        
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(5, 0, 0, 0)
        status_layout.setSpacing(5)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Create status indicator based on type and state
        if is_cluster:
            # Handle cluster-specific statuses
            if status in ["connecting", "loading"]:
                # Show loading indicator
                loading_indicator = SmallLoadingIndicator()
                status_layout.addWidget(loading_indicator)
                
                # Add status text
                status_text = "Connecting..." if status == "connecting" else "Loading data..."
                status_label = QLabel(status_text)
                status_label.setStyleSheet(f"color: {status_colors.get(status, AppColors.STATUS_DISCONNECTED)}; background: transparent;")
                status_layout.addWidget(status_label)
            else:
                # Set appropriate status text for clusters
                if status == "available":
                    status_text = "Available"  # Initial state shows "Available"
                elif status == "active" or status == "connected":
                    status_text = "Connected"  # After connection, shows "Connected"
                elif status == "disconnect":
                    status_text = "Disconnected"
                else:
                    status_text = status.capitalize()
                    
                # Just show status text without loading indicator
                status_label = QLabel(status_text)
                status_label.setStyleSheet(f"color: {status_colors.get(status, AppColors.STATUS_DISCONNECTED)}; background: transparent;")
                status_layout.addWidget(status_label)
        else:
            # For non-cluster items, show the exact status text
            status_text = status
            status_label = QLabel(status_text)
            status_label.setStyleSheet(f"color: {status_colors.get(status, AppColors.STATUS_DISCONNECTED)}; background: transparent;")
            status_layout.addWidget(status_label)
        
        # Set the custom widget for status column
        self.tree_widget.setItemWidget(item, 4, status_widget)

        # Create action column
        action_widget = QWidget()
        action_widget.setFixedWidth(AppConstants.SIZES["ACTION_WIDTH"])
        action_widget.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # For active operations (connecting/loading), just show a spinner with no menu
        if status in ["connecting", "loading"] and (name in self.connecting_clusters or self.waiting_for_cluster_load == name):
            # For connecting/loading states, no menu needed - already showing spinner in status column
            pass
        else:
            # Create menu button for actions
            menu_btn = QPushButton("⋮")
            menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            menu_btn.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE)
            menu_btn.setFixedWidth(AppConstants.SIZES["ACTION_WIDTH"])
            menu_btn.setFixedHeight(30)
            menu_btn.setFlat(True)

            menu = QMenu(action_widget)
            menu.setStyleSheet(AppStyles.MENU_STYLE)
            
            # Different menu actions based on status
            if status in ["available", "active", "connected"]:
                open_action = menu.addAction("Open")
                if is_cluster:
                    disconnect_action = menu.addAction("Disconnect")
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
                if action is None:
                    return
                    
                if status in ["available", "active", "connected"]:
                    if action == open_action:
                        self.handle_open_item(item)
                    elif is_cluster and 'disconnect_action' in locals() and action == disconnect_action:
                        self.handle_disconnect_item(item)
                    elif action == delete_action:
                        self.handle_delete_item(item)
                elif status == "disconnect" and is_cluster:
                    if action == connect_action:
                        self.handle_connect_item(item)
                    elif action == delete_action:
                        self.handle_delete_item(item)
                else:
                    if action == open_action:
                        self.handle_open_item(item)
                    elif action == delete_action:
                        self.handle_delete_item(item)

            menu_btn.clicked.connect(show_menu)
            action_layout.addWidget(menu_btn)
            
        self.tree_widget.setItemWidget(item, 5, action_widget)
        item.setSizeHint(5, QSize(AppConstants.SIZES["ACTION_WIDTH"], AppConstants.SIZES["ROW_HEIGHT"]))
    def init_data_model(self):
        self.all_data = {
            "Browse All": [
                {"name": "Welcome Page", "kind": "General", "source": "app", "label": "", 
                 "status": "active", "badge_color": None, "action": self.navigate_to_welcome},
                {"name": "Preference", "kind": "General", "source": "app", "label": "", 
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
            "All Clusters": lambda item: "Cluster" in item["kind"],
            "Web Links": lambda item: item["kind"] == "Weblinks"
        }
        for view_name, filter_func in view_types.items():
            self.all_data[view_name] = [item for item in self.all_data["Browse All"] if filter_func(item)]


    # Add this new method to handle single-click on items
    def handle_item_single_click(self, item, column):
        """Handle single click on item to navigate to cluster or other content"""
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        data_item = self._find_data_item(self.current_view, original_name)
        
        if not data_item:
            return
        
        # Handle both clusters and other items
        if "Cluster" in data_item.get("kind", ""):
            self.navigate_to_cluster(data_item)
        else:
            # For non-cluster items, execute their action directly
            if data_item.get("action"):
                data_item["action"](data_item)

    # 2. Update the create_table_widget method to add single-click handling
    def create_table_widget(self):
        tree_widget = QTreeWidget()
        tree_widget.setColumnCount(6)
        tree_widget.setHeaderLabels(["Name", "Kind", "Source", "Label", "Status", ""])
        tree_widget.setHeaderHidden(False)

        column_widths = [300, 180, 150, 120, 120, AppConstants.SIZES["ACTION_WIDTH"]]
        for i, width in enumerate(column_widths):
            tree_widget.setColumnWidth(i, width)

        header = tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, len(column_widths)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, AppConstants.SIZES["ACTION_WIDTH"])

        tree_widget.setStyleSheet(AppStyles.TREE_WIDGET_STYLE)
        tree_widget.setIconSize(QSize(20, 20))
        tree_widget.setIndentation(0)
        tree_widget.setAlternatingRowColors(False)
        tree_widget.setRootIsDecorated(False)
        tree_widget.setItemsExpandable(False)
        tree_widget.setHorizontalScrollMode(QTreeWidget.ScrollMode.ScrollPerPixel)
        
        tree_widget.itemClicked.connect(self.handle_item_single_click)
        
        return tree_widget

    def _find_data_item(self, view, original_name):
        for data_item in self.all_data[view]:
            if data_item["name"] == original_name:
                return data_item
        return None


    def handle_open_item(self, item):
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        data_item = self._find_data_item(self.current_view, original_name)
        if data_item and data_item["action"]:
            data_item["action"](data_item)
  
    def handle_connect_item(self, item):
        """Handle connecting to a cluster"""
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        data_item = self._find_data_item(self.current_view, original_name)
        
        if data_item and "Cluster" in data_item["kind"]:
            # Update the status to connecting
            for view_type in self.all_data:
                for item in self.all_data[view_type]:
                    if item["name"] == original_name:
                        item["status"] = "connecting"
                        
            # Add to connecting clusters set
            self.connecting_clusters.add(original_name)
            
            # Update the view to show connecting status
            self.update_content_view(self.current_view)
            
            # Start the connection process
            print(f"Connecting to cluster: {original_name}")
            QTimer.singleShot(100, lambda: self.cluster_connector.connect_to_cluster(original_name))


    def handle_disconnect_item(self, item):
        """Handle disconnecting from a cluster"""
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Update status to disconnected
        for view_type in self.all_data:
            for data_item in self.all_data[view_type]:
                if data_item["name"] == original_name:
                    data_item["status"] = "disconnect"
        
        # If there's cache for this cluster, clear it
        if hasattr(self.cluster_connector, 'data_cache'):
            if original_name in self.cluster_connector.data_cache:
                del self.cluster_connector.data_cache[original_name]
            
        # Also clear from loading_complete tracking
        if hasattr(self.cluster_connector, 'loading_complete'):
            if original_name in self.cluster_connector.loading_complete:
                del self.cluster_connector.loading_complete[original_name]
        
        # Stop any polling for this cluster if it's the current one
        if hasattr(self.cluster_connector, 'kube_client') and \
        self.cluster_connector.kube_client.current_cluster == original_name:
            self.cluster_connector.stop_polling()
        
        # Call the disconnect_cluster method if it exists
        if hasattr(self.cluster_connector, 'disconnect_cluster'):
            self.cluster_connector.disconnect_cluster(original_name)
        
        # Refresh the view to show updated status
        self.update_content_view(self.current_view)
        
        print(f"Cluster {original_name} disconnected")

    def handle_delete_item(self, item):
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        index = self.tree_widget.indexOfTopLevelItem(item)
        self.tree_widget.takeTopLevelItem(index)
        for view_type in self.all_data:
            self.all_data[view_type] = [
                item for item in self.all_data[view_type]
                if item["name"] != original_name
            ]
        current_count = len(self.all_data[self.current_view])
        self.items_label.setText(f"{current_count} item{'s' if current_count != 1 else ''}")

    def navigate_to_welcome(self, item):
        print("Navigating to Welcome Page")

    def navigate_to_preferences(self, item):
        print("Navigating to Preferences")
        self.open_preferences_signal.emit()

    def navigate_to_cluster(self, item):
        """Navigate to cluster view, connecting first if necessary"""
        cluster_name = item["name"]
        cluster_status = item["status"]
        
        # If already connecting or loading, do nothing
        if cluster_status in ["connecting", "loading"]:
            print(f"Already working with cluster: {cluster_name}")
            return
        
        # Check if data is already fully loaded
        if hasattr(self.cluster_connector, 'is_data_loaded') and self.cluster_connector.is_data_loaded(cluster_name):
            # Data is ready, navigate immediately
            print(f"Cluster {cluster_name} data already loaded, navigating directly")
            self.open_cluster_signal.emit(cluster_name)
            return
        
        # Data not loaded, start the connection process
        for view_type in self.all_data:
            for data_item in self.all_data[view_type]:
                if data_item["name"] == cluster_name:
                    data_item["status"] = "connecting"
        
        # Update the UI to show connecting status
        self.update_content_view(self.current_view)
        
        # Start the connection process
        print(f"Connecting to Cluster: {cluster_name}")
        QTimer.singleShot(100, lambda: self.cluster_connector.connect_to_cluster(cluster_name))

    def open_web_link(self, item):
        print(f"Opening web link: {item['name']}")

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
        self.sidebar_layout.setContentsMargins(0, 15, 0, 0)
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
        if not hasattr(self, 'tree_widget') or self.tree_widget is None:
            return
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
                for child in action_widget.children():
                    if isinstance(child, QPushButton):
                        child.setFixedWidth(action_column_width)
                        child.setContentsMargins(0, 0, 0, 0)