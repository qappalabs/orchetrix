# from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
#                              QLabel, QPushButton, QLineEdit, QTreeWidget, 
#                              QTreeWidgetItem, QFrame, QMenu, QHeaderView)
# from PyQt6.QtCore import Qt, QObject, pyqtSignal, QPoint, QSize
# from PyQt6.QtGui import QColor, QPainter, QIcon, QMouseEvent

# # Constants for reuse throughout the application
# STYLE = {
#     "COLORS": {
#         "BG_DARK": "#1e1e1e",
#         "BG_MEDIUM": "#2d2d2d",
#         "BG_LIGHT": "#3a3a3a",
#         "BORDER": "#3a3a3a",
#         "BORDER_LIGHT": "#454545",
#         "BORDER_DARK": "#2a2a2a",
#         "TABLE_HEADER": "#323232",
#         "TEXT": "#ffffff",
#         "TEXT_MUTED": "#888888",
#         "ACCENT": "#3584e4",
#         "STATUS_AVAILABLE": "#66bb6a",
#         "STATUS_ACTIVE": "#42a5f5",
#         "STATUS_DISCONNECT": "#ef5350"
#     },
#     "SIZES": {
#         "SIDEBAR_WIDTH": 180,
#         "TOPBAR_HEIGHT": 40,
#         "ROW_HEIGHT": 32,
#         "ICON_SIZE": 16,
#         "ACTION_WIDTH": 40  # Exactly 40px for action column
#     }
# }

# class HomePageSignals(QObject):
#     """Centralized signals for navigation between pages"""
#     open_cluster_signal = pyqtSignal(str)
#     open_preferences_signal = pyqtSignal()

# class CircularCheckmark(QLabel):
#     """Visual indicator for active/successful status"""
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setFixedSize(80, 80)
#         self.setAlignment(Qt.AlignmentFlag.AlignCenter)

#     def paintEvent(self, event):
#         painter = QPainter(self)
#         painter.setRenderHint(QPainter.RenderHint.Antialiasing)

#         # Draw green circle
#         painter.setPen(Qt.PenStyle.NoPen)
#         painter.setBrush(QColor("#4CAF50"))
#         painter.drawEllipse(10, 10, 60, 60)

#         # Draw checkmark
#         painter.setPen(QColor("#FFFFFF"))
#         painter.setPen(Qt.PenStyle.SolidLine)
#         painter.drawLine(25, 40, 35, 50)
#         painter.drawLine(35, 50, 55, 30)
#         painter.end()

# class SidebarButton(QPushButton):
#     """Customized button for sidebar navigation"""
#     def __init__(self, text, icon_text, icon_path=None, parent=None):
#         super().__init__(text, parent)
        
#         if icon_path:
#             # Use QIcon if icon path is provided
#             self.setIcon(QIcon(icon_path))
#             self.setIconSize(QSize(STYLE["SIZES"]["ICON_SIZE"], STYLE["SIZES"]["ICON_SIZE"]))
#             # Add text padding to create space between icon and text
#             self.setText(f" {text}")
#         else:
#             # Use text icon as fallback
#             self.setText(f"{icon_text}  {text}")
            
#         self.setCheckable(True)
#         self.setFlat(True)
#         self.setCursor(Qt.CursorShape.PointingHandCursor)
#         self.setStyleSheet(f"""
#             QPushButton {{
#                 background-color: transparent;
#                 border: none;
#                 border-radius: 0px;
#                 color: {STYLE["COLORS"]["TEXT_MUTED"]};
#                 text-align: left;
#                 padding: 12px 15px;
#                 font-size: 15px;
#             }}
#             QPushButton:hover {{
#                 background-color: {STYLE["COLORS"]["BG_MEDIUM"]};
#                 color: {STYLE["COLORS"]["TEXT"]};
#             }}
#             QPushButton:pressed, QPushButton:checked {{
#                 background-color: {STYLE["COLORS"]["BG_LIGHT"]};
#                 color: {STYLE["COLORS"]["TEXT"]};
#             }}
#         """)

# class OrchestrixGUI(QMainWindow):
#     def __init__(self):
#         super().__init__()

#         # Create signals object for navigation
#         self.signals = HomePageSignals()
#         self.open_cluster_signal = self.signals.open_cluster_signal
#         self.open_preferences_signal = self.signals.open_preferences_signal

#         # Mouse tracking for window dragging
#         self.drag_position = None

#         # Configure window properties
#         self.setWindowTitle("Kubernetes Manager")
#         self.setGeometry(100, 100, 1300, 700)
#         self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
#         # Default view and search state
#         self.current_view = "Browse All"
#         self.search_filter = ""
#         self.sidebar_buttons = []
#         self.tree_widget = None
#         self.browser_label = None
#         self.items_label = None
        
#         # Initialize and setup
#         self.init_data_model()
#         self.apply_theme()
#         self.setup_ui()
#         self.update_content_view("Browse All")

#     def mousePressEvent(self, event: QMouseEvent):
#         """Handle mouse press events for window dragging"""
#         if event.button() == Qt.MouseButton.LeftButton:
#             # Only start drag if within top bar height
#             if event.position().y() <= STYLE["SIZES"]["TOPBAR_HEIGHT"]:
#                 self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
#                 event.accept()

#     def mouseReleaseEvent(self, event: QMouseEvent):
#         """Reset drag position on mouse release"""
#         if event.button() == Qt.MouseButton.LeftButton:
#             self.drag_position = None
#             event.accept()

#     def mouseMoveEvent(self, event: QMouseEvent):
#         """Handle window movement when dragging"""
#         if event.buttons() & Qt.MouseButton.LeftButton and self.drag_position is not None:
#             self.move(event.globalPosition().toPoint() - self.drag_position)
#             event.accept()

#     def update_content_view(self, view_type):
#         """Update the view to show items from the selected category"""
#         self.current_view = view_type
#         self.browser_label.setText(view_type)

#         # Reset all buttons and highlight the selected one
#         for button in self.sidebar_buttons:
#             button.setChecked(view_type in button.text())

#         # Apply current filter
#         self.filter_content(self.search_filter)
        
#     def filter_content(self, search_text=None):
#         """Filter displayed items based on search text"""
#         # Update search filter if provided
#         if search_text is not None:
#             self.search_filter = search_text

#         # Get data for current view
#         view_data = self.all_data[self.current_view]

#         # Filter data based on search text
#         if self.search_filter:
#             search_term = self.search_filter.lower()
#             filtered_data = [
#                 item for item in view_data if any(
#                     search_term in str(item.get(field, "")).lower() 
#                     for field in ["name", "kind", "source", "label", "status"]
#                 )
#             ]
#         else:
#             filtered_data = view_data

#         # Update UI
#         self.items_label.setText(f"{len(filtered_data)} item{'s' if len(filtered_data) != 1 else ''}")
#         self.tree_widget.clear()

#         # Populate with filtered data
#         for item in filtered_data:
#             self.add_table_item(**{k: item[k] for k in 
#                 ["name", "kind", "source", "label", "status", "badge_color"]})
            
#     def add_table_item(self, name, kind, source, label, status, badge_color=None):
#         """Add a single item to the tree widget"""
#         item = QTreeWidgetItem(self.tree_widget)
#         item.setSizeHint(0, QSize(0, STYLE["SIZES"]["ROW_HEIGHT"]))
#         item.setData(0, Qt.ItemDataRole.UserRole, name)

#         # Format name based on whether it has a badge
#         if badge_color:
#             parts = name.split(' ', 1)
#             item_text = parts[1] if len(parts) > 1 else name
#             item.setText(0, item_text)
#         else:
#             item.setText(0, name)

#         # Set remaining columns
#         item.setText(1, kind)
#         item.setText(2, source)
#         item.setText(3, label)

#         # Set status column with appropriate color
#         status_colors = {
#             "available": STYLE["COLORS"]["STATUS_AVAILABLE"],
#             "active": STYLE["COLORS"]["STATUS_ACTIVE"],
#             "disconnect": STYLE["COLORS"]["STATUS_DISCONNECT"]
#         }
#         status_color = status_colors.get(status, STYLE["COLORS"]["STATUS_DISCONNECT"])
#         item.setText(4, status)
#         item.setForeground(4, QColor(status_color))

#         # Create action widget with menu button - optimized for exact width
#         action_widget = QWidget()
#         action_widget.setFixedWidth(STYLE["SIZES"]["ACTION_WIDTH"])  # Exact width with no margin
#         action_widget.setContentsMargins(0, 0, 0, 0)
#         action_widget.setStyleSheet("""
#             background-color: transparent;
#             border: none;
#             margin: 0;
#             padding: 0;
#         """)

#         action_layout = QHBoxLayout(action_widget)
#         action_layout.setContentsMargins(0, 0, 0, 0)  # Remove all margins
#         action_layout.setSpacing(0)
#         action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center align for better appearance

#         # Menu button with kebab icon
#         menu_btn = QPushButton("⋮")
#         menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
#         menu_btn.setStyleSheet(f"""
#             QPushButton {{
#                 background-color: transparent;
#                 border: none;
#                 border-radius: 0;
#                 color: {STYLE["COLORS"]["TEXT_MUTED"]};
#                 font-size: 20px;
#                 font-weight: bold;
#                 margin: 0;
#                 padding: 0;
#                 width: {STYLE["SIZES"]["ACTION_WIDTH"]}px;
#             }}
#             QPushButton:hover {{
#                 color: {STYLE["COLORS"]["TEXT"]};
#             }}
#             QPushButton:pressed, QPushButton:focus {{
#                 border: none;
#                 outline: none;
#                 background-color: transparent;
#             }}
#         """)
#         menu_btn.setFixedWidth(STYLE["SIZES"]["ACTION_WIDTH"])  # Ensure button fills the column width
#         menu_btn.setFixedHeight(30)
#         menu_btn.setFlat(True)

#         # Create context menu
#         menu = QMenu(action_widget)
#         menu.setStyleSheet(f"""
#             QMenu {{
#                 background-color: {STYLE["COLORS"]["BG_MEDIUM"]};
#                 color: {STYLE["COLORS"]["TEXT"]};
#                 border: 1px solid {STYLE["COLORS"]["BORDER"]};
#                 padding: 5px;
#             }}
#             QMenu::item {{
#                 padding: 5px 15px;
#             }}
#             QMenu::item:selected {{
#                 background-color: {STYLE["COLORS"]["ACCENT"]};
#             }}
#         """)

#         # Add menu actions
#         open_action = menu.addAction("Open")
#         delete_action = menu.addAction("Delete")

#         # Configure menu popup
#         def show_menu():
#             pos = menu_btn.mapToGlobal(QPoint(0, menu_btn.height()))
#             action = menu.exec(pos)

#             if action == open_action:
#                 self.handle_open_item(item)
#             elif action == delete_action:
#                 self.handle_delete_item(item)

#         menu_btn.clicked.connect(show_menu)

#         action_layout.addWidget(menu_btn)
#         self.tree_widget.setItemWidget(item, 5, action_widget)
        
#         # Force size hint for action column
#         item.setSizeHint(5, QSize(STYLE["SIZES"]["ACTION_WIDTH"], STYLE["SIZES"]["ROW_HEIGHT"]))
        
#     def init_data_model(self):
#         """Initialize the data model with categorized items"""
#         # Main data store - single source of truth
#         self.all_data = {
#             "Browse All": [
#                 {"name": "Welcome Page", "kind": "General", "source": "app", "label": "", 
#                  "status": "active", "badge_color": None, "action": self.navigate_to_welcome},
                
#                 {"name": "Preference", "kind": "General", "source": "app", "label": "", 
#                  "status": "active", "badge_color": None, "action": self.navigate_to_preferences},
                
#                 {"name": "OxW Orchetrix Website", "kind": "Weblinks", "source": "local", "label": "", 
#                  "status": "available", "badge_color": "#f0ad4e", "action": self.open_web_link},
                
#                 {"name": "OxD Orchetrix Documentation", "kind": "Weblinks", "source": "local", "label": "", 
#                  "status": "available", "badge_color": "#ecd06f", "action": self.open_web_link},
                
#                 {"name": "OxF Orchetrix Forum", "kind": "Weblinks", "source": "local", "label": "", 
#                  "status": "available", "badge_color": "#9966cc", "action": self.open_web_link},
                
#                 {"name": "OxT Orchetrix on X", "kind": "Weblinks", "source": "local", "label": "", 
#                  "status": "available", "badge_color": "#5bc0de", "action": self.open_web_link},
                
#                 {"name": "OxOB Orchetrix Official blog", "kind": "Weblinks", "source": "local", "label": "", 
#                  "status": "available", "badge_color": "#d9534f", "action": self.open_web_link},
                
#                 {"name": "KD Kubernetes Document", "kind": "Weblinks", "source": "local", "label": "", 
#                  "status": "available", "badge_color": "#5cb85c", "action": self.open_web_link},
                
#                 {"name": "DD docker-desktop", "kind": "Kubernet Cluster", "source": "local", "label": "General", 
#                  "status": "disconnect", "badge_color": None, "action": self.navigate_to_cluster}
#             ]
#         }

#         # Create filtered views based on kind
#         view_types = {
#             "General": lambda item: item["kind"] == "General",
#             "All Clusters": lambda item: "Cluster" in item["kind"],
#             "Web Links": lambda item: item["kind"] == "Weblinks"
#         }
        
#         # Generate filtered views
#         for view_name, filter_func in view_types.items():
#             self.all_data[view_name] = [item for item in self.all_data["Browse All"] if filter_func(item)]

#     def create_table_widget(self):
#         """Create and configure the tree widget used to display items"""
#         tree_widget = QTreeWidget()
#         tree_widget.setColumnCount(6)  # Name, Kind, Source, Label, Status, Actions
#         tree_widget.setHeaderLabels(["Name", "Kind", "Source", "Label", "Status", ""])
#         tree_widget.setHeaderHidden(False)
        
#         # Critical fix: Disable stretch last section
#         tree_widget.header().setStretchLastSection(False)

#         # Define column widths
#         column_widths = [300, 180, 150, 120, 120, STYLE["SIZES"]["ACTION_WIDTH"]]
        
#         # Set column widths
#         for i, width in enumerate(column_widths):
#             tree_widget.setColumnWidth(i, width)

#         # Configure header sections
#         header = tree_widget.header()
#         header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name column expands
        
#         # Set all other columns to fixed width
#         for i in range(1, len(column_widths)):
#             header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            
#         # Force action column to exact width
#         header.resizeSection(5, STYLE["SIZES"]["ACTION_WIDTH"])

#         # Apply styling to create a modern, clean look with borders (no outer border)
#         tree_widget.setStyleSheet(f"""
#             QTreeWidget {{
#                 background-color: {STYLE["COLORS"]["BG_DARK"]};
#                 border: none;  /* Removed outer border */
#                 outline: none;
#                 font-size: 13px;
#                 gridline-color: {STYLE["COLORS"]["BORDER_DARK"]};
#                 margin: 0;
#                 padding: 0;
#             }}
#             QTreeWidget::item {{
#                 padding: 6px 4px;
#                 border-bottom: 1px solid {STYLE["COLORS"]["BORDER_DARK"]};
#                 border-right: 1px solid {STYLE["COLORS"]["BORDER_DARK"]};
#                 background-color: transparent;
#             }}
#                 QTreeWidget::item:hover {{
#                     background-color: rgba(53, 132, 228, 0.15);
#                 }}
#             QHeaderView::section {{
#                 background-color: {STYLE["COLORS"]["TABLE_HEADER"]};
#                 color: {STYLE["COLORS"]["TEXT"]};
#                 padding: 8px 8px;
#                 border-right: 1px solid {STYLE["COLORS"]["BORDER_DARK"]};
#                 border-bottom: 1px solid {STYLE["COLORS"]["BORDER_DARK"]};
#                 border-top: none;
#                 border-left: none;
#                 text-align: left;
#                 font-weight: bold;
#             }}
#             QHeaderView::section:first {{
#                 border-left: none;  /* Removed left border on first column */
#             }}
#             QHeaderView::section:last {{
#                 padding: 0;  /* No padding for last column */
#                 text-align: center;
#                 width: {STYLE["SIZES"]["ACTION_WIDTH"]}px;
#                 max-width: {STYLE["SIZES"]["ACTION_WIDTH"]}px;
#                 min-width: {STYLE["SIZES"]["ACTION_WIDTH"]}px;
#             }}
#             QTreeWidget::item:selected {{
#                 background-color: rgba(53, 132, 228, 0.15); ;
#             }}
#             QTreeWidget::branch {{
#                 border: none;
#                 border-image: none;
#                 outline: none;
#             }}



from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QLineEdit, QTreeWidget, 
                             QTreeWidgetItem, QFrame, QMenu, QHeaderView,
                             QSplashScreen, QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QPoint, QSize, QTimer
from PyQt6.QtGui import QColor, QPainter, QIcon, QMouseEvent, QPixmap

# Import our Kubernetes client
from utils.kubernetes_client import get_kubernetes_client

# Constants for reuse throughout the application
STYLE = {
    "COLORS": {
        "BG_DARK": "#1e1e1e",
        "BG_MEDIUM": "#2d2d2d",
        "BG_LIGHT": "#3a3a3a",
        "BORDER": "#3a3a3a",
        "BORDER_LIGHT": "#454545",
        "BORDER_DARK": "#2a2a2a",
        "TABLE_HEADER": "#323232",
        "TEXT": "#ffffff",
        "TEXT_MUTED": "#888888",
        "ACCENT": "#3584e4",
        "STATUS_AVAILABLE": "#66bb6a",
        "STATUS_ACTIVE": "#42a5f5",
        "STATUS_DISCONNECT": "#ef5350"
    },
    "SIZES": {
        "SIDEBAR_WIDTH": 180,
        "TOPBAR_HEIGHT": 40,
        "ROW_HEIGHT": 32,
        "ICON_SIZE": 16,
        "ACTION_WIDTH": 40  # Exactly 40px for action column
    }
}

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

        # Draw green circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#4CAF50"))
        painter.drawEllipse(10, 10, 60, 60)

        # Draw checkmark
        painter.setPen(QColor("#FFFFFF"))
        painter.setPen(Qt.PenStyle.SolidLine)
        painter.drawLine(25, 40, 35, 50)
        painter.drawLine(35, 50, 55, 30)
        painter.end()

class SidebarButton(QPushButton):
    """Customized button for sidebar navigation"""
    def __init__(self, text, icon_text, icon_path=None, parent=None):
        super().__init__(text, parent)
        
        if icon_path:
            # Use QIcon if icon path is provided
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(STYLE["SIZES"]["ICON_SIZE"], STYLE["SIZES"]["ICON_SIZE"]))
            # Add text padding to create space between icon and text
            self.setText(f" {text}")
        else:
            # Use text icon as fallback
            self.setText(f"{icon_text}  {text}")
            
        self.setCheckable(True)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 0px;
                color: {STYLE["COLORS"]["TEXT_MUTED"]};
                text-align: left;
                padding: 12px 15px;
                font-size: 15px;
            }}
            QPushButton:hover {{
                background-color: {STYLE["COLORS"]["BG_MEDIUM"]};
                color: {STYLE["COLORS"]["TEXT"]};
            }}
            QPushButton:pressed, QPushButton:checked {{
                background-color: {STYLE["COLORS"]["BG_LIGHT"]};
                color: {STYLE["COLORS"]["TEXT"]};
            }}
        """)

class OrchestrixGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # Create signals object for navigation
        self.signals = HomePageSignals()
        self.open_cluster_signal = self.signals.open_cluster_signal
        self.open_preferences_signal = self.signals.open_preferences_signal

        # Initialize Kubernetes client
        self.kube_client = get_kubernetes_client()
        self.kube_client.clusters_loaded.connect(self.on_clusters_loaded)
        self.kube_client.error_occurred.connect(self.show_error_message)

        # Mouse tracking for window dragging
        self.drag_position = None

        # Configure window properties
        self.setWindowTitle("Kubernetes Manager")
        self.setGeometry(100, 100, 1300, 700)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Default view and search state
        self.current_view = "Browse All"
        self.search_filter = ""
        self.sidebar_buttons = []
        self.tree_widget = None
        self.browser_label = None
        self.items_label = None
        
        # Initialize and setup
        self.init_data_model()
        self.apply_theme()
        self.setup_ui()
        self.update_content_view("Browse All")
        
        # Load Kubernetes configuration asynchronously
        QTimer.singleShot(100, self.load_kubernetes_clusters)

    def load_kubernetes_clusters(self):
        """Load Kubernetes clusters asynchronously"""
        self.kube_client.load_clusters_async()

    def on_clusters_loaded(self, clusters):
        """Handle loaded Kubernetes clusters"""
        # Convert cluster objects to dictionary format for our data model
        for cluster in clusters:
            print(clusters)
            # Check if cluster already exists in our data model
            exists = False
            for item in self.all_data["Browse All"]:
                if item.get("name") == cluster.name:
                    # Update existing item
                    item.update({
                        "name": cluster.name,
                        "kind": cluster.kind,
                        "source": cluster.source,
                        "label": cluster.label,
                        "status": cluster.status,
                        "badge_color": None,
                        "action": self.navigate_to_cluster,
                        "cluster_data": cluster
                    })
                    exists = True
                    break
            
            # Add new cluster if it doesn't exist
            if not exists:
                self.all_data["Browse All"].append({
                    "name": cluster.name,
                    "kind": cluster.kind,
                    "source": cluster.source,
                    "label": cluster.label,
                    "status": cluster.status,
                    "badge_color": None,
                    "action": self.navigate_to_cluster,
                    "cluster_data": cluster
                })
        
        # Update filtered views
        self.update_filtered_views()
        
        # Refresh current view to show new clusters
        self.update_content_view(self.current_view)

    def show_error_message(self, error_message):
        """Display error message to user"""
        QMessageBox.critical(self, "Error", error_message)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events for window dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Only start drag if within top bar height
            if event.position().y() <= STYLE["SIZES"]["TOPBAR_HEIGHT"]:
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Reset drag position on mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = None
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle window movement when dragging"""
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def update_content_view(self, view_type):
        """Update the view to show items from the selected category"""
        self.current_view = view_type
        self.browser_label.setText(view_type)

        # Reset all buttons and highlight the selected one
        for button in self.sidebar_buttons:
            button.setChecked(view_type in button.text())

        # Apply current filter
        self.filter_content(self.search_filter)
        
    def filter_content(self, search_text=None):
        """Filter displayed items based on search text"""
        # Update search filter if provided
        if search_text is not None:
            self.search_filter = search_text

        # Get data for current view
        view_data = self.all_data[self.current_view]

        # Filter data based on search text
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

        # Update UI
        self.items_label.setText(f"{len(filtered_data)} item{'s' if len(filtered_data) != 1 else ''}")
        self.tree_widget.clear()

        # Populate with filtered data
        for item in filtered_data:
            self.add_table_item(**{k: item[k] for k in 
                ["name", "kind", "source", "label", "status", "badge_color"]})
            
    def add_table_item(self, name, kind, source, label, status, badge_color=None):
        """Add a single item to the tree widget"""
        item = QTreeWidgetItem(self.tree_widget)
        item.setSizeHint(0, QSize(0, STYLE["SIZES"]["ROW_HEIGHT"]))
        item.setData(0, Qt.ItemDataRole.UserRole, name)

        # Format name based on whether it has a badge
        if badge_color:
            parts = name.split(' ', 1)
            item_text = parts[1] if len(parts) > 1 else name
            item.setText(0, item_text)
        else:
            item.setText(0, name)

        # Set remaining columns
        item.setText(1, kind)
        item.setText(2, source)
        item.setText(3, label)

        # Set status column with appropriate color
        status_colors = {
            "available": STYLE["COLORS"]["STATUS_AVAILABLE"],
            "active": STYLE["COLORS"]["STATUS_ACTIVE"],
            "disconnect": STYLE["COLORS"]["STATUS_DISCONNECT"]
        }
        status_color = status_colors.get(status, STYLE["COLORS"]["STATUS_DISCONNECT"])
        item.setText(4, status)
        item.setForeground(4, QColor(status_color))

        # Create action widget with menu button - optimized for exact width
        action_widget = QWidget()
        action_widget.setFixedWidth(STYLE["SIZES"]["ACTION_WIDTH"])  # Exact width with no margin
        action_widget.setContentsMargins(0, 0, 0, 0)
        action_widget.setStyleSheet("""
            background-color: transparent;
            border: none;
            margin: 0;
            padding: 0;
        """)

        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)  # Remove all margins
        action_layout.setSpacing(0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center align for better appearance

        # Menu button with kebab icon
        menu_btn = QPushButton("⋮")
        menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        menu_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 0;
                color: {STYLE["COLORS"]["TEXT_MUTED"]};
                font-size: 20px;
                font-weight: bold;
                margin: 0;
                padding: 0;
                width: {STYLE["SIZES"]["ACTION_WIDTH"]}px;
            }}
            QPushButton:hover {{
                color: {STYLE["COLORS"]["TEXT"]};
            }}
            QPushButton:pressed, QPushButton:focus {{
                border: none;
                outline: none;
                background-color: transparent;
            }}
        """)
        menu_btn.setFixedWidth(STYLE["SIZES"]["ACTION_WIDTH"])  # Ensure button fills the column width
        menu_btn.setFixedHeight(30)
        menu_btn.setFlat(True)

        # Create context menu
        menu = QMenu(action_widget)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {STYLE["COLORS"]["BG_MEDIUM"]};
                color: {STYLE["COLORS"]["TEXT"]};
                border: 1px solid {STYLE["COLORS"]["BORDER"]};
                padding: 5px;
            }}
            QMenu::item {{
                padding: 5px 15px;
            }}
            QMenu::item:selected {{
                background-color: {STYLE["COLORS"]["ACCENT"]};
            }}
        """)

        # Add menu actions
        open_action = menu.addAction("Open")
        delete_action = menu.addAction("Delete")

        # Configure menu popup
        def show_menu():
            pos = menu_btn.mapToGlobal(QPoint(0, menu_btn.height()))
            action = menu.exec(pos)

            if action == open_action:
                self.handle_open_item(item)
            elif action == delete_action:
                self.handle_delete_item(item)

        menu_btn.clicked.connect(show_menu)

        action_layout.addWidget(menu_btn)
        self.tree_widget.setItemWidget(item, 5, action_widget)
        
        # Force size hint for action column
        item.setSizeHint(5, QSize(STYLE["SIZES"]["ACTION_WIDTH"], STYLE["SIZES"]["ROW_HEIGHT"]))
        
    def init_data_model(self):
        """Initialize the data model with categorized items"""
        # Main data store - single source of truth
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
                
                {"name": "OxF Orchetrix Forum", "kind": "Weblinks", "source": "local", "label": "", 
                 "status": "available", "badge_color": "#9966cc", "action": self.open_web_link},
                
                {"name": "OxT Orchetrix on X", "kind": "Weblinks", "source": "local", "label": "", 
                 "status": "available", "badge_color": "#5bc0de", "action": self.open_web_link},
                
                {"name": "OxOB Orchetrix Official blog", "kind": "Weblinks", "source": "local", "label": "", 
                 "status": "available", "badge_color": "#d9534f", "action": self.open_web_link},
                
                {"name": "KD Kubernetes Document", "kind": "Weblinks", "source": "local", "label": "", 
                 "status": "available", "badge_color": "#5cb85c", "action": self.open_web_link}
            ]
        }

        # Update filtered views
        self.update_filtered_views()

    def update_filtered_views(self):
        """Update filtered views based on the current data"""
        # Create filtered views based on kind
        view_types = {
            "General": lambda item: item["kind"] == "General",
            "All Clusters": lambda item: "Cluster" in item["kind"],
            "Web Links": lambda item: item["kind"] == "Weblinks"
        }
        
        # Generate filtered views
        for view_name, filter_func in view_types.items():
            self.all_data[view_name] = [item for item in self.all_data["Browse All"] if filter_func(item)]

    def create_table_widget(self):
        """Create and configure the tree widget used to display items"""
        tree_widget = QTreeWidget()
        tree_widget.setColumnCount(6)  # Name, Kind, Source, Label, Status, Actions
        tree_widget.setHeaderLabels(["Name", "Kind", "Source", "Label", "Status", ""])
        tree_widget.setHeaderHidden(False)
        
        # Critical fix: Disable stretch last section
        tree_widget.header().setStretchLastSection(False)

        # Define column widths
        column_widths = [300, 180, 150, 120, 120, STYLE["SIZES"]["ACTION_WIDTH"]]
        
        # Set column widths
        for i, width in enumerate(column_widths):
            tree_widget.setColumnWidth(i, width)

        # Configure header sections
        header = tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name column expands
        
        # Set all other columns to fixed width
        for i in range(1, len(column_widths)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            
        # Force action column to exact width
        header.resizeSection(5, STYLE["SIZES"]["ACTION_WIDTH"])

        # Apply styling to create a modern, clean look with borders (no outer border)
        tree_widget.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {STYLE["COLORS"]["BG_DARK"]};
                border: none;  /* Removed outer border */
                outline: none;
                font-size: 13px;
                gridline-color: {STYLE["COLORS"]["BORDER_DARK"]};
                margin: 0;
                padding: 0;
            }}
            QTreeWidget::item {{
                padding: 6px 4px;
                border-bottom: 1px solid {STYLE["COLORS"]["BORDER_DARK"]};
                border-right: 1px solid {STYLE["COLORS"]["BORDER_DARK"]};
                background-color: transparent;
            }}
                QTreeWidget::item:hover {{
                    background-color: rgba(53, 132, 228, 0.15);
                }}
            QHeaderView::section {{
                background-color: {STYLE["COLORS"]["TABLE_HEADER"]};
                color: {STYLE["COLORS"]["TEXT"]};
                padding: 8px 8px;
                border-right: 1px solid {STYLE["COLORS"]["BORDER_DARK"]};
                border-bottom: 1px solid {STYLE["COLORS"]["BORDER_DARK"]};
                border-top: none;
                border-left: none;
                text-align: left;
                font-weight: bold;
            }}
            QHeaderView::section:first {{
                border-left: none;  /* Removed left border on first column */
            }}
            QHeaderView::section:last {{
                padding: 0;  /* No padding for last column */
                text-align: center;
                width: {STYLE["SIZES"]["ACTION_WIDTH"]}px;
                max-width: {STYLE["SIZES"]["ACTION_WIDTH"]}px;
                min-width: {STYLE["SIZES"]["ACTION_WIDTH"]}px;
            }}
            QTreeWidget::item:selected {{
                background-color: rgba(53, 132, 228, 0.15); ;
            }}
            QTreeWidget::branch {{
                border: none;
                border-image: none;
                outline: none;
            }}
        """)

        # Configure row display
        tree_widget.setIconSize(QSize(20, 20))
        tree_widget.setIndentation(0)  # Remove indentation for flat look
        tree_widget.setAlternatingRowColors(False)  # Consistent row colors

        # Configure tree behavior
        tree_widget.setRootIsDecorated(False)  # No expand/collapse indicators
        tree_widget.setItemsExpandable(False)  # Items cannot be expanded
        tree_widget.setHorizontalScrollMode(QTreeWidget.ScrollMode.ScrollPerPixel)
        
        # Connect double-click event for navigation
        tree_widget.itemDoubleClicked.connect(self.handle_item_double_click)

        return tree_widget
        
    def apply_theme(self):
        """Apply dark theme styling to the application"""
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {STYLE["COLORS"]["BG_DARK"]};
                color: {STYLE["COLORS"]["TEXT"]};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QTreeWidget, QLineEdit, QTabWidget::pane {{
                background-color: {STYLE["COLORS"]["BG_DARK"]};
                color: {STYLE["COLORS"]["TEXT"]};
                border: 1px solid {STYLE["COLORS"]["BORDER"]};
                border-radius: 2px;
            }}
            QTabWidget::tab-bar {{
                alignment: left;
            }}
            QTabBar::tab {{
                background-color: {STYLE["COLORS"]["BG_DARK"]};
                color: {STYLE["COLORS"]["TEXT"]};
                padding: 8px 16px;
                margin-right: 2px;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                border-bottom: 2px solid {STYLE["COLORS"]["ACCENT"]};
            }}
            QPushButton {{
                background-color: {STYLE["COLORS"]["BG_MEDIUM"]};
                color: {STYLE["COLORS"]["TEXT"]};
                border: 1px solid {STYLE["COLORS"]["BORDER"]};
                border-radius: 2px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: {STYLE["COLORS"]["BG_LIGHT"]};
            }}
            QPushButton:pressed {{
                background-color: #454545;
            }}
            QLineEdit, QComboBox {{
                padding: 5px;
                background-color: {STYLE["COLORS"]["BG_MEDIUM"]};
                border: 1px solid {STYLE["COLORS"]["BORDER"]};
                border-radius: 2px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left-width: 1px;
                border-left-color: {STYLE["COLORS"]["BORDER"]};
                border-left-style: solid;
            }}
            QMenu {{
                background-color: {STYLE["COLORS"]["BG_MEDIUM"]};
                color: {STYLE["COLORS"]["TEXT"]};
                border: 1px solid {STYLE["COLORS"]["BORDER"]};
                padding: 5px;
            }}
            QMenu::item {{
                padding: 5px 15px;
            }}
            QMenu::item:selected {{
                background-color: {STYLE["COLORS"]["ACCENT"]};
            }}
        """)

    def _find_data_item(self, view, original_name):
        """Helper method to find a data item by name in a view"""
        for data_item in self.all_data[view]:
            if data_item["name"] == original_name:
                return data_item
        return None

    def handle_item_double_click(self, item, column):
        """Handle double-click on tree widget item"""
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        data_item = self._find_data_item(self.current_view, original_name)
        
        if data_item and data_item["action"]:
            data_item["action"](data_item)
                
    def handle_open_item(self, item):
        """Handle opening the selected item via menu"""
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        data_item = self._find_data_item(self.current_view, original_name)
        
        if data_item and data_item["action"]:
            data_item["action"](data_item)

    def handle_delete_item(self, item):
        """Handle deleting the selected item"""
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Remove from tree widget
        index = self.tree_widget.indexOfTopLevelItem(item)
        self.tree_widget.takeTopLevelItem(index)
        
        # Remove from data model for all views
        for view_type in self.all_data:
            self.all_data[view_type] = [
                item for item in self.all_data[view_type] 
                if item["name"] != original_name
            ]
        
        # Update item count
        current_count = len(self.all_data[self.current_view])
        self.items_label.setText(f"{current_count} item{'s' if current_count != 1 else ''}")
        
    def navigate_to_welcome(self, item):
        """Navigate to welcome page"""
        print(f"Navigating to Welcome Page")
        # Implementation would go here
        
    def navigate_to_preferences(self, item):
        """Navigate to preferences page"""
        print(f"Navigating to Preferences")
        self.open_preferences_signal.emit()
        
    def navigate_to_cluster(self, item):
        """Navigate to cluster page"""
        print(f"Navigating to Cluster: {item['name']}")
        self.open_cluster_signal.emit(item['name'])
        
    def open_web_link(self, item):
        """Open web link in browser"""
        print(f"Opening web link: {item['name']}")
        # Implementation would go here
        
    def setup_ui(self):
        """Initialize and configure UI components"""
        # Main container setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout structure
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Container for sidebar and content
        self.content_container = QWidget()
        self.horizontal_layout = QHBoxLayout(self.content_container)
        self.horizontal_layout.setContentsMargins(0, 0, 0, 0)
        self.horizontal_layout.setSpacing(0)
        
        # Add to main layout
        self.main_layout.addWidget(self.content_container)
        
        # Create UI components
        self.create_sidebar()
        self.create_main_content()
        
        # Fix action column width after UI is created
        self.fix_action_column_width()

    def create_sidebar(self):
        """Create and configure the sidebar navigation"""
        # Sidebar container
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(STYLE["SIZES"]["SIDEBAR_WIDTH"])
        self.sidebar.setStyleSheet(f"""
            background-color: {STYLE["COLORS"]["BG_DARK"]}; 
            border-right: 1px solid {STYLE["COLORS"]["BORDER"]};
        """)
        
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 15, 0, 0)
        self.sidebar_layout.setSpacing(2)  # Increased spacing between buttons
        
        # Define sidebar navigation options with icons
        sidebar_options = [
            {
                "text": "Browse All", 
                "icon": "🔍", 
                "icon_path": "icons/browse.svg",
                "action": lambda: self.update_content_view("Browse All")
            },
            {
                "text": "General", 
                "icon": "⚙️", 
                "icon_path": "icons/settings.svg",
                "action": lambda: self.update_content_view("General")
            },
            {
                "text": "All Clusters", 
                "icon": "🔄", 
                "icon_path": "icons/clusters.svg",
                "action": lambda: self.update_content_view("All Clusters")
            },
            {
                "text": "Web Links", 
                "icon": "🔗", 
                "icon_path": "icons/links.svg",
                "action": lambda: self.update_content_view("Web Links")
            }
        ]
        
        # Create buttons for each option
        self.sidebar_buttons = []
        for option in sidebar_options:
            button = SidebarButton(
                option["text"], 
                option["icon"], 
                option.get("icon_path")
            )
            button.clicked.connect(option["action"])
            self.sidebar_layout.addWidget(button)
            self.sidebar_buttons.append(button)
        
        # Add stretcher to push everything to the top
        self.sidebar_layout.addStretch()
        
        # Add sidebar to horizontal layout
        self.horizontal_layout.addWidget(self.sidebar)

    def create_main_content(self):
        """Create and configure the main content area"""
        # Main content container
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # Top navigation bar
        self.create_top_bar()
        
        # Main content area with table
        self.create_content_area()
        
        # Add content widget to horizontal layout
        self.horizontal_layout.addWidget(self.content)

    def create_top_bar(self):
        """Create the top navigation bar with search"""
        # Top bar container
        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(STYLE["SIZES"]["TOPBAR_HEIGHT"])
        self.top_bar.setStyleSheet(f"""
            background-color: {STYLE["COLORS"]["BG_DARK"]}; 
            border-bottom: 1px solid {STYLE["COLORS"]["BORDER"]};
        """)
        
        self.top_bar_layout = QHBoxLayout(self.top_bar)
        self.top_bar_layout.setContentsMargins(10, 0, 10, 0)
        
        # View title and count
        self.browser_label = QLabel("Browse All")
        self.browser_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        
        self.items_label = QLabel("9 items")
        self.items_label.setStyleSheet(f"color: {STYLE['COLORS']['TEXT_MUTED']}; margin-left: 10px; font-size: 14px;")
        
        # Search box
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search...")
        self.search.setFixedWidth(300)
        self.search.textChanged.connect(self.filter_content)
        
        # Add widgets to top bar
        self.top_bar_layout.addWidget(self.browser_label)
        self.top_bar_layout.addWidget(self.items_label)
        self.top_bar_layout.addStretch()
        self.top_bar_layout.addWidget(self.search)
        
        # Add top bar to content layout
        self.content_layout.addWidget(self.top_bar)

    def create_content_area(self):
        """Create the main content area with the item table"""
        # Main content container with padding
        self.main_content = QWidget()
        self.main_content_layout = QVBoxLayout(self.main_content)
        self.main_content_layout.setContentsMargins(20, 20, 20, 20)
        self.main_content_layout.setSpacing(0)
        
        # Table container with no border and zero padding
        self.table_container = QFrame()
        self.table_container.setFrameShape(QFrame.Shape.NoFrame)  # No frame
        self.table_container.setStyleSheet(f"""
            QFrame {{
                background-color: {STYLE["COLORS"]["BG_DARK"]};
                border: none;
                padding: 0;
                margin: 0;
            }}
        """)
        
        # Zero margins in container layout
        self.table_container_layout = QVBoxLayout(self.table_container)
        self.table_container_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        self.table_container_layout.setSpacing(0)
        
        # Create and configure tree widget for data display
        self.tree_widget = self.create_table_widget()
        self.table_container_layout.addWidget(self.tree_widget)
        
        # Add container to main content
        self.main_content_layout.addWidget(self.table_container)
        
        # Add to content layout
        self.content_layout.addWidget(self.main_content)
        
    def fix_action_column_width(self):
        """Post-initialization fix for action column width"""
        if not hasattr(self, 'tree_widget') or self.tree_widget is None:
            return
            
        # Force action column width on tree widget
        header = self.tree_widget.header()
        header.setStretchLastSection(False)  # Crucial: don't stretch last section
        
        # Set exact width for action column
        action_column_width = STYLE["SIZES"]["ACTION_WIDTH"]
        self.tree_widget.setColumnWidth(5, action_column_width)
        header.resizeSection(5, action_column_width)
        
        # Apply specific style to the action column header
        header.setStyleSheet(f"""
            QHeaderView::section:last {{
                padding: 0;
                margin: 0;
                width: {action_column_width}px;
                max-width: {action_column_width}px;
                min-width: {action_column_width}px;
            }}
        """)
        
        # Update all action widgets to have exact width
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            action_widget = self.tree_widget.itemWidget(item, 5)
            
            if action_widget:
                # Reset widget properties
                action_widget.setFixedWidth(action_column_width)
                action_widget.setContentsMargins(0, 0, 0, 0)
                
                # Find and adjust the button if it exists
                for child in action_widget.children():
                    if isinstance(child, QPushButton):
                        child.setFixedWidth(action_column_width)
                        child.setContentsMargins(0, 0, 0, 0)
                        child.setStyleSheet(child.styleSheet() + f"""
                            padding: 0;
                            margin: 0;
                            width: {action_column_width}px;
                        """)