import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QStackedWidget, QTableWidget, QLabel,QFrame, QPushButton,QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QEvent,QSize
from PyQt6.QtGui import QFont,QIcon

# Import splash screen
from UI.SplashScreen import SplashScreen

# Import the original Home Page
from Pages.HomePage import OrchestrixGUI
from Pages.Preferences import PreferencesWidget  # Changed to use widget instead of window
from UI.TitleBar import TitleBar
from UI.ClusterView import ClusterView

# Import terminal and detail page components
from detail_page_component import ResourceDetailPage

# Import style definitions
from UI.Styles import AppColors, AppStyles

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialize but don't show main window yet
        self.setup_window()
        self.init_ui()
        
        # Install event filter to track window state changes
        self.installEventFilter(self)
    
    def setup_window(self):
        """Set up the basic window properties but don't create UI yet"""
        self.setWindowTitle("Orchestrix")
        self.setMinimumSize(1200, 700)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Apply the application's dark theme
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {AppColors.BG_DARK};
                color: {AppColors.TEXT_LIGHT};
            }}
        """)
    
    def init_ui(self):
        """Initialize all UI components"""
        # Create main widget and layout
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Add title bar
        self.title_bar = TitleBar(self)
        self.main_layout.addWidget(self.title_bar)
        
        # Create stacked widget to switch between home, preferences, and cluster views
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.currentChanged.connect(self.handle_page_change)
        self.main_layout.addWidget(self.stacked_widget)
        
        # Create home page (with its own sidebar)
        self.home_page = OrchestrixGUI()
        
        # Create cluster view (with its own sidebar)
        self.cluster_view = ClusterView(self)
        
        # Create preferences page (now as a widget, not a window)
        self.preferences_page = PreferencesWidget()
        
        # Add all views to the stacked widget
        self.stacked_widget.addWidget(self.home_page)
        self.stacked_widget.addWidget(self.cluster_view)
        self.stacked_widget.addWidget(self.preferences_page)
        
        # Register pages in dictionary for easy access
        self.pages = {
            "Home": self.home_page,
            "Cluster": self.cluster_view,
            "Preferences": self.preferences_page
        }
        
        
        # Set the central widget
        self.setCentralWidget(self.main_widget)
        
        # Initialize with home page
        self.stacked_widget.setCurrentWidget(self.home_page)
        
        # Setup connections
        self.setup_connections()
        
        # For window dragging
        self.drag_position = None
        
        # Keep track of previous page for back button
        self.previous_page = None
        

        # Initlize the detail page
        self.setup_detail_page()
        
        # Connect table click events
        self.connect_table_click_events()

        
    def setup_detail_page(self):
        """Set up the detail panel"""
        self.detail_page = ResourceDetailPage(self)
    

    

    def connect_table_click_events(self):
        """Connect double-click events on tables to show detail panel"""
        if hasattr(self.cluster_view, 'pages'):
            # Connect all table widgets in cluster view
            for page_name, page in self.cluster_view.pages.items():
                if hasattr(page, 'table') and isinstance(page.table, QTableWidget):
                    # Set selection behavior
                    page.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
                    page.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
                    
                    # Store the table, page, and name in variables for lambda closure
                    table = page.table
                    
                    # Disconnect any existing connections
                    try:
                        table.cellDoubleClicked.disconnect()
                    except:
                        pass  # Ignore if no connections exist
                    
                    # Connect double-click to show detail
                    # We pass page and page_name to avoid lambda capture issues
                    table.cellDoubleClicked.connect(
                        lambda row, col, p=page, n=page_name: 
                        self.show_detail_for_table_item(row, col, p, n)
                    )
    
    def show_detail_for_table_item(self, row, col, page, page_name):
        """Show detail page for clicked table item"""
        # Get resource type from page name (remove trailing 's' if present)
        resource_type = page_name.rstrip('s')  # Convert "Pods" to "Pod", etc.
        
        # Get resource name from table (usually column 1)
        resource_name = None
        
        # Try to get directly from table item
        if hasattr(page.table, 'item') and page.table.item(row, 1) is not None:
            resource_name = page.table.item(row, 1).text()
        # Try to get from cell widget if using custom cell widgets
        elif hasattr(page.table, 'cellWidget') and page.table.cellWidget(row, 1) is not None:
            widget = page.table.cellWidget(row, 1)
            # Look for labels in the cell widget
            for label in widget.findChildren(QLabel):
                if label.text() and not label.text().isspace():
                    resource_name = label.text()
                    break
        # Fallback to first column
        elif hasattr(page.table, 'item') and page.table.item(row, 0) is not None:
            resource_name = page.table.item(row, 0).text()
        # Use a default if nothing found
        else:
            resource_name = f"{resource_type}-{row}"
        
        # Show detail panel
        if resource_name:
            self.detail_page.show_detail(resource_type, resource_name)
            print(f"Showing details for {resource_type}: {resource_name}")
    
    def setup_connections(self):
        # Connect home page signals
        self.home_page.open_cluster_signal.connect(self.switch_to_cluster_view)
        self.home_page.open_preferences_signal.connect(self.switch_to_preferences)
        
        # Connect title bar signals
        self.title_bar.home_btn.clicked.connect(self.switch_to_home)
        self.title_bar.settings_btn.clicked.connect(self.switch_to_preferences)
        
        # Connect preferences back signal
        self.preferences_page.back_signal.connect(self.handle_preferences_back)
        
    
    def switch_to_home(self):
        """Switch to the home page view"""
        if self.stacked_widget.currentWidget() != self.home_page:
            self.previous_page = self.stacked_widget.currentWidget()
            self.stacked_widget.setCurrentWidget(self.home_page)
    
    def switch_to_cluster_view(self, cluster_name="docker-desktop"):
        """Switch to the cluster view and set the active cluster"""
        if self.stacked_widget.currentWidget() != self.cluster_view:
            self.previous_page = self.stacked_widget.currentWidget()
        self.cluster_view.set_active_cluster(cluster_name)
        self.stacked_widget.setCurrentWidget(self.cluster_view)
        
        # If terminal is visible, update its position after switching to cluster view
        if hasattr(self.cluster_view, 'terminal_panel') and self.cluster_view.terminal_panel.is_visible:
            QTimer.singleShot(100, self.cluster_view.adjust_terminal_position)
    
    def switch_to_preferences(self):
        """Switch to the preferences page"""
        if self.stacked_widget.currentWidget() != self.preferences_page:
            self.previous_page = self.stacked_widget.currentWidget()
            self.stacked_widget.setCurrentWidget(self.preferences_page)
        
    def handle_preferences_back(self):
        """Handle back button from preferences - return to previous view"""
        if self.previous_page:
            self.stacked_widget.setCurrentWidget(self.previous_page)
        else:
            # Default to home page if there's no previous page
            self.switch_to_home()
    def handle_page_change(self, index):
#         """Handle page changes in the stacked widget"""
        # Get the current widget
        current_widget = self.stacked_widget.widget(index)
    
    # In MainWindow.py, update the resizeEvent method to properly handle terminal positioning:

    def resizeEvent(self, event):
        """Handle resize event to properly position detail panels and terminal"""
        super().resizeEvent(event)
        
        # Update detail page if visible
        if hasattr(self, 'detail_page') and self.detail_page.is_visible:
            # Update height
            self.detail_page.setFixedHeight(self.height())
            
            # Update position (right side)
            self.detail_page.move(self.width() - self.detail_page.width(), 0)
        
        # Update terminal position if visible, using a cleaner approach
        if hasattr(self, 'cluster_view'):
            # If cluster view is visible and has a terminal panel
            if self.stacked_widget.currentWidget() == self.cluster_view and hasattr(self.cluster_view, 'terminal_panel'):
                if self.cluster_view.terminal_panel.is_visible:
                    # Delay the adjustment slightly to ensure sidebar size is settled
                    QTimer.singleShot(10, self.cluster_view.adjust_terminal_position)
            # Even if we're not on the cluster view, update terminal if it's visible
            elif hasattr(self.cluster_view, 'terminal_panel') and self.cluster_view.terminal_panel.is_visible:
                QTimer.singleShot(10, self.cluster_view.adjust_terminal_position)
    # Mouse events to make the window draggable from the title bar
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, 'drag_position'):
            # Move the main window
            self.move(event.globalPosition().toPoint() - self.drag_position)
            
            
                
            # Update detail page position if visible
            if hasattr(self, 'detail_page') and self.detail_page.is_visible:
                self.detail_page.move(self.geometry().right() - self.detail_page.width(), self.geometry().top())
                
            event.accept()
    
    def moveEvent(self, event):
        """Handle move event to keep detail panels and terminal in position"""
        super().moveEvent(event)
        
        # Update detail page position when window moves
        if hasattr(self, 'detail_page') and self.detail_page.is_visible:
            self.detail_page.move(self.geometry().right() - self.detail_page.width(), self.geometry().top())
        
        # Update terminal position when window moves
        if hasattr(self, 'cluster_view') and hasattr(self.cluster_view, 'terminal_panel'):
            if self.cluster_view.terminal_panel.is_visible:
                # Trigger adjustment after a short delay to ensure sidebar is settled
                QTimer.singleShot(10, self.cluster_view.adjust_terminal_position) 
    def closeEvent(self, event):
        """Clean up any resources before closing"""
        # Hide terminal and detail page if visible
        if hasattr(self, 'cluster_view') and hasattr(self.cluster_view, 'terminal_panel'):
            if self.cluster_view.terminal_panel.is_visible:
                self.cluster_view.terminal_panel.hide_terminal()
                
        if hasattr(self, 'detail_page') and self.detail_page.is_visible:
            self.detail_page.hide_detail()
            
        super().closeEvent(event)

if __name__ == "__main__":
    # Initialize application
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    
    # Create and show splash screen
    splash = SplashScreen()
    splash.show()
    
    # Create main window but don't show it yet
    window = MainWindow()
    
    # When splash screen finishes, show main window
    def show_main_window():
        window.show()
        splash.close()
    
    # Connect splash screen finish signal
    splash.finished.connect(show_main_window)
    
    sys.exit(app.exec())
