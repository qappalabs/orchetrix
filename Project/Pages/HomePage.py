from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QLineEdit, QTreeWidget, 
                             QTreeWidgetItem, QFrame, QMenu, QHeaderView)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QPoint, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QPainter

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
    def __init__(self, text, icon, parent=None):
        super().__init__(f"{icon} {text}", parent)
        self.setCheckable(True)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 0px;
                color: #cccccc;
                text-align: left;
                padding: 12px 15px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
                color: white;
            }
            QPushButton:pressed, QPushButton:checked {
                background-color: #3a3a3a;
                color: white;
            }
        """)

class OrchestrixGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # Create signals object for navigation
        self.signals = HomePageSignals()
        self.open_cluster_signal = self.signals.open_cluster_signal
        self.open_preferences_signal = self.signals.open_preferences_signal

        # Configure window properties
        self.setWindowTitle("Kubernetes Manager")
        self.setGeometry(100, 100, 1300, 700)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Default view and search state
        self.current_view = "Browse All"
        self.search_filter = ""
        
        # Data model - structured for easy filtering and updates
        self.init_data_model()
        
        # Apply theme styling
        self.apply_theme()
        
        # Initialize UI components
        self.setup_ui()

    def update_content_view(self, view_type):
        """Update the view to show items from the selected category"""
        # Update current view
        self.current_view = view_type

        # Update top bar title
        self.browser_label.setText(view_type)

        # Uncheck all sidebar buttons
        for button in self.sidebar_buttons:
            button.setChecked(False)

        # Check the selected button
        for button in self.sidebar_buttons:
            if view_type in button.text():
                button.setChecked(True)

        # Apply current search filter to the new view
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
            filtered_data = []
            for item in view_data:
                # Search in name, kind, source, label, and status
                if (self.search_filter.lower() in item["name"].lower() or
                        self.search_filter.lower() in item["kind"].lower() or
                        self.search_filter.lower() in item["source"].lower() or
                        self.search_filter.lower() in item["label"].lower() or
                        self.search_filter.lower() in item["status"].lower()):
                    filtered_data.append(item)
        else:
            # No search filter, use all data for the current view
            filtered_data = view_data

        # Update items count
        self.items_label.setText(f"{len(filtered_data)} item{'s' if len(filtered_data) != 1 else ''}")

        # Clear current table items
        self.tree_widget.clear()

        # Populate with filtered data
        for item in filtered_data:
            self.add_table_item(
                item["name"],
                item["kind"],
                item["source"],
                item["label"],
                item["status"],
                item["badge_color"]
            )
            
    def add_table_item(self, name, kind, source, label, status, badge_color=None):
        """Add a single item to the tree widget"""
        item = QTreeWidgetItem(self.tree_widget)

        # Set consistent row height
        item.setSizeHint(0, QSize(0, 32))

        # Store original name in item data for reference
        item.setData(0, Qt.ItemDataRole.UserRole, name)

        # Format name based on whether it has a badge
        if badge_color:
            # Split the name into badge and text parts
            parts = name.split(' ', 1)
            # Use the main text part, ignoring the badge
            item_text = parts[1] if len(parts) > 1 else name
            item.setText(0, item_text)
        else:
            item.setText(0, name)

        # Set remaining columns
        item.setText(1, kind)
        item.setText(2, source)
        item.setText(3, label)

        # Set status column with appropriate color
        status_color = "#66bb6a" if status == "available" else "#42a5f5" if status == "active" else "#ef5350"
        item.setText(4, status)
        item.setForeground(4, QColor(status_color))

        # Create action widget with menu button
        action_widget = QWidget()
        action_widget.setStyleSheet("background-color: transparent; border: none;")

        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Menu button with kebab icon
        menu_btn = QPushButton("⋮")
        menu_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 0;
                color: #888888;
                font-size: 24px;
                font-weight: bold;
                margin: 0;
                padding: 0;
            }
            QPushButton:hover {
                color: white;
                background-color: transparent;
            }
            QPushButton:pressed, QPushButton:focus {
                border: none;
                outline: none;
                background-color: transparent;
            }
        """)
        menu_btn.setFixedSize(32, 32)
        menu_btn.setFlat(True)

        # Create context menu
        menu = QMenu(action_widget)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3a3a3a;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 15px;
            }
            QMenu::item:selected {
                background-color: #3584e4;
            }
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
        
    def init_data_model(self):
        """Initialize the data model with categorized items"""
        # Main data store - single source of truth
        self.all_data = {
            "Browse All": [
                {"name": "🏠 Welcome Page", "kind": "General", "source": "app", "label": "", 
                 "status": "active", "badge_color": None, "action": self.navigate_to_welcome},
                
                {"name": "⚙️ Preference", "kind": "General", "source": "app", "label": "", 
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
                 "status": "available", "badge_color": "#5cb85c", "action": self.open_web_link},
                
                {"name": "DD docker-desktop", "kind": "Kubernet Cluster", "source": "local", "label": "General", 
                 "status": "disconnect", "badge_color": None, "action": self.navigate_to_cluster}
            ]
        }

        # Create filtered views for faster access
        self.all_data["General"] = [item for item in self.all_data["Browse All"] 
                                    if item["kind"] == "General"]
        
        self.all_data["All Clusters"] = [item for item in self.all_data["Browse All"] 
                                        if "Cluster" in item["kind"]]
        
        self.all_data["Web Links"] = [item for item in self.all_data["Browse All"] 
                                     if item["kind"] == "Weblinks"]

    def create_table_widget(self):
        """Create and configure the tree widget used to display items"""
        # Create the tree widget
        tree_widget = QTreeWidget()
        tree_widget.setColumnCount(6)  # Name, Kind, Source, Label, Status, Actions
        tree_widget.setHeaderLabels(["Name", "Kind", "Source", "Label", "Status", ""])
        tree_widget.setHeaderHidden(False)

        # Set stretch factors for columns
        header = tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name column expands
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # Kind column fixed width
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Source column fixed width
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # Label column fixed width
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)    # Status column fixed width
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)    # Actions column fixed width

        # Apply styling to create a modern, clean look
        tree_widget.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                border: none;
                outline: none;
                font-size: 13px;
                gridline-color: transparent;
            }
            QTreeWidget::item {
                padding: 6px 4px;
                border: none;
                background-color: transparent;
            }
            QTreeWidget::item:hover {
                background-color: #3584e4;
            }
            QHeaderView::section {
                background-color: #323232;
                color: white;
                padding: 8px 8px;
                border: none;
                border-bottom: 1px solid #454545;
                text-align: left;
                font-weight: bold;
            }
            QTreeWidget::item:selected {
                background-color: #3584e4;
            }
            QFrame, QTreeWidget::branch, QTreeWidget::item:hover {
                border: none;
                border-image: none;
                outline: none;
            }
            QHeaderView::section:last {
                padding-right: 20px;
            }
        """)

        # Configure row display
        tree_widget.setIconSize(QSize(20, 20))
        tree_widget.setIndentation(0)  # Remove indentation for flat look
        tree_widget.setAlternatingRowColors(False)  # Consistent row colors

        # Set column widths
        tree_widget.setColumnWidth(0, 250)  # Name
        tree_widget.setColumnWidth(1, 150)  # Kind
        tree_widget.setColumnWidth(2, 100)  # Source
        tree_widget.setColumnWidth(3, 100)  # Label
        tree_widget.setColumnWidth(4, 100)  # Status
        tree_widget.setColumnWidth(5, 40)   # Actions

        # Configure tree behavior
        tree_widget.setRootIsDecorated(False)  # No expand/collapse indicators
        tree_widget.setItemsExpandable(False)  # Items cannot be expanded
        tree_widget.setHorizontalScrollMode(QTreeWidget.ScrollMode.ScrollPerPixel)
        
        # Connect double-click event for navigation
        tree_widget.itemDoubleClicked.connect(self.handle_item_double_click)

        return tree_widget
        
    def apply_theme(self):
        """Apply dark theme styling to the application"""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTreeWidget, QLineEdit, QTabWidget::pane {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #1e1e1e;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected {
                border-bottom: 2px solid #3584e4;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #454545;
            }
            QLineEdit, QComboBox {
                padding: 5px;
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left-width: 1px;
                border-left-color: #3a3a3a;
                border-left-style: solid;
            }
            QMenu {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3a3a3a;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 15px;
            }
            QMenu::item:selected {
                background-color: #3584e4;
            }
        """)

    def handle_item_double_click(self, item, column):
        """Handle double-click on tree widget item"""
        # Get the original name from user data
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Find the corresponding item in data model
        for data_item in self.all_data[self.current_view]:
            if data_item["name"] == original_name:
                # Execute the item's action
                if data_item["action"]:
                    data_item["action"](data_item)
                break
                
    def handle_open_item(self, item):
        """Handle opening the selected item via menu"""
        # Get the original name stored in user role
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Find the corresponding item in data model
        for data_item in self.all_data[self.current_view]:
            if data_item["name"] == original_name:
                # Execute the item's action
                if data_item["action"]:
                    data_item["action"](data_item)
                break

    def handle_delete_item(self, item):
        """Handle deleting the selected item"""
        # Get the original name stored in user role
        original_name = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Remove from tree widget
        index = self.tree_widget.indexOfTopLevelItem(item)
        self.tree_widget.takeTopLevelItem(index)
        
        # Remove from data model for all views
        for view_type, items in self.all_data.items():
            for i, data_item in enumerate(items):
                if data_item["name"] == original_name:
                    # Remove the item
                    self.all_data[view_type].pop(i)
                    break
        
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
        # Emit signal for navigation
        self.open_preferences_signal.emit()
        
    def navigate_to_cluster(self, item):
        """Navigate to cluster page"""
        print(f"Navigating to Cluster: {item['name']}")
        # Emit signal for navigation with cluster name
        cluster_name = item['name']
        self.open_cluster_signal.emit(cluster_name)
        
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
        
        # Initialize with default view
        self.update_content_view("Browse All")

    def create_sidebar(self):
        """Create and configure the sidebar navigation"""
        # Sidebar container
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.setStyleSheet("""
            background-color: #1e1e1e; 
            border-right: 1px solid #3a3a3a;
        """)
        
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 15, 0, 0)
        self.sidebar_layout.setSpacing(1)
        
        # Define sidebar navigation options
        sidebar_options = [
            {"text": "Browse All", "icon": "🔍", "action": lambda: self.update_content_view("Browse All")},
            {"text": "General", "icon": "⚙️", "action": lambda: self.update_content_view("General")},
            {"text": "All Clusters", "icon": "🔄", "action": lambda: self.update_content_view("All Clusters")},
            {"text": "Web Links", "icon": "🔗", "action": lambda: self.update_content_view("Web Links")}
        ]
        
        # Create buttons for each option
        self.sidebar_buttons = []
        for option in sidebar_options:
            button = SidebarButton(option["text"], option["icon"])
            button.clicked.connect(option["action"])
            self.sidebar_layout.addWidget(button)
            self.sidebar_buttons.append(button)
        
        # Set initial selection
        if self.sidebar_buttons:
            self.sidebar_buttons[0].setChecked(True)
        
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
        self.top_bar.setFixedHeight(40)
        self.top_bar.setStyleSheet("""
            background-color: #1e1e1e; 
            border-bottom: 1px solid #3a3a3a;
        """)
        
        self.top_bar_layout = QHBoxLayout(self.top_bar)
        self.top_bar_layout.setContentsMargins(10, 0, 10, 0)
        
        # View title and count
        self.browser_label = QLabel("Browser All")
        self.browser_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        
        self.items_label = QLabel("9 items")
        self.items_label.setStyleSheet("color: #888888; margin-left: 10px; font-size: 14px;")
        
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
        
        # Table container with border
        self.table_container = QFrame()
        self.table_container.setFrameShape(QFrame.Shape.StyledPanel)
        self.table_container.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: 1px solid #3a3a3a;
            }
        """)
        
        self.table_container_layout = QVBoxLayout(self.table_container)
        self.table_container_layout.setContentsMargins(10, 10, 10, 10)
        self.table_container_layout.setSpacing(0)
        
        # Create and configure tree widget for data display
        self.tree_widget = self.create_table_widget()
        self.table_container_layout.addWidget(self.tree_widget)
        
        # Add container to main content
        self.main_content_layout.addWidget(self.table_container)
        
        # Add to content layout
        self.content_layout.addWidget(self.main_content)