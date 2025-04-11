import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QStackedWidget, QTableWidget, QLabel, QFrame, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QEvent, QSize
from PyQt6.QtGui import QFont, QIcon

try:
    # Import splash screen
    from UI.SplashScreen import SplashScreen

    # Import the original Home Page
    from Pages.HomePage import OrchestrixGUI
    from Pages.Preferences import PreferencesWidget
    from UI.TitleBar import TitleBar
    from UI.ClusterView import ClusterView

    # Import terminal and detail page components
    from detail_page_component import ResourceDetailPage

    # Import style definitions
    from UI.Styles import AppColors, AppStyles
    
    # Import cluster connector
    from utils.cluster_connector import get_cluster_connector

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            # Setup window properties first
            self.setup_window()
            
            # Initialize cluster connector before UI setup
            self.cluster_connector = get_cluster_connector()
            
            # Now initialize UI components
            self.init_ui()
            self.installEventFilter(self)

        def setup_window(self):
            """Set up the basic window properties"""
            self.setWindowTitle("Orchestrix")
            self.setMinimumSize(1300, 700)
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setStyleSheet(AppStyles.MAIN_STYLE)

        def init_ui(self):
            """Initialize all UI components"""
            self.main_widget = QWidget()
            self.main_layout = QVBoxLayout(self.main_widget)
            self.main_layout.setContentsMargins(0, 0, 0, 0)
            self.main_layout.setSpacing(0)

            self.title_bar = TitleBar(self)
            self.main_layout.addWidget(self.title_bar)

            self.stacked_widget = QStackedWidget()
            self.stacked_widget.currentChanged.connect(self.handle_page_change)
            self.main_layout.addWidget(self.stacked_widget)

            self.home_page = OrchestrixGUI()
            self.cluster_view = ClusterView(self)
            self.preferences_page = PreferencesWidget()

            self.stacked_widget.addWidget(self.home_page)
            self.stacked_widget.addWidget(self.cluster_view)
            self.stacked_widget.addWidget(self.preferences_page)

            self.pages = {
                "Home": self.home_page,
                "Cluster": self.cluster_view,
                "Preferences": self.preferences_page
            }

            self.setCentralWidget(self.main_widget)
            self.stacked_widget.setCurrentWidget(self.home_page)

            self.setup_connections()
            self.drag_position = None
            self.previous_page = None

            self.setup_detail_page()
            self.connect_table_click_events()

        def setup_detail_page(self):
            """Set up the detail panel"""
            self.detail_page = ResourceDetailPage(self)

        def connect_table_click_events(self):
            """Connect double-click events on tables to show detail panel"""
            if hasattr(self.cluster_view, 'pages'):
                for page_name, page in self.cluster_view.pages.items():
                    if hasattr(page, 'table') and isinstance(page.table, QTableWidget):
                        page.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
                        page.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
                        try:
                            page.table.cellDoubleClicked.disconnect()
                        except:
                            pass
                        table = page.table
                        table.cellDoubleClicked.connect(
                            lambda row, col, p=page, n=page_name: 
                            self.show_detail_for_table_item(row, col, p, n)
                        )

        def show_detail_for_table_item(self, row, col, page, page_name):
            """Show detail page for clicked table item"""
            resource_type = page_name.rstrip('s')
            resource_name = None

            if hasattr(page.table, 'item') and page.table.item(row, 1) is not None:
                resource_name = page.table.item(row, 1).text()
            elif hasattr(page.table, 'cellWidget') and page.table.cellWidget(row, 1) is not None:
                widget = page.table.cellWidget(row, 1)
                for label in widget.findChildren(QLabel):
                    if label.text() and not label.text().isspace():
                        resource_name = label.text()
                        break
            elif hasattr(page.table, 'item') and page.table.item(row, 0) is not None:
                resource_name = page.table.item(row, 0).text()
            else:
                resource_name = f"{resource_type}-{row}"

            if resource_name:
                self.detail_page.show_detail(resource_type, resource_name)

        def setup_connections(self):
            self.home_page.open_cluster_signal.connect(self.switch_to_cluster_view)
            self.home_page.open_preferences_signal.connect(self.switch_to_preferences)
            self.title_bar.home_btn.clicked.connect(self.switch_to_home)
            self.title_bar.settings_btn.clicked.connect(self.switch_to_preferences)
            self.preferences_page.back_signal.connect(self.handle_preferences_back)
            
            # Connect error signals from cluster connector
            if hasattr(self, 'cluster_connector'):
                self.cluster_connector.error_occurred.connect(self.show_error_message)

        def switch_to_home(self):
            """Switch to the home page view"""
            if self.stacked_widget.currentWidget() != self.home_page:
                self.previous_page = self.stacked_widget.currentWidget()
                self.stacked_widget.setCurrentWidget(self.home_page)

        def switch_to_cluster_view(self, cluster_name="docker-desktop"):
            """Switch to the cluster view and set the active cluster"""
            if self.stacked_widget.currentWidget() != self.cluster_view:
                self.previous_page = self.stacked_widget.currentWidget()
            
            # Check if cluster connector is ready
            if not hasattr(self, 'cluster_connector') or not self.cluster_connector:
                self.show_error_message("Cluster connector not initialized.")
                return
                
            # Switch to cluster view first, then set active cluster to show loading state
            self.stacked_widget.setCurrentWidget(self.cluster_view)
            
            # Set active cluster after switching to the view
            QTimer.singleShot(100, lambda: self.cluster_view.set_active_cluster(cluster_name))
            
            # Adjust terminal panel if visible
            if hasattr(self.cluster_view, 'terminal_panel') and self.cluster_view.terminal_panel.is_visible:
                QTimer.singleShot(200, self.cluster_view.adjust_terminal_position)
        def switch_to_preferences(self):
            """Switch to the preferences page"""
            if self.stacked_widget.currentWidget() != self.preferences_page:
                self.previous_page = self.stacked_widget.currentWidget()
                self.stacked_widget.setCurrentWidget(self.preferences_page)

        def handle_preferences_back(self):
            """Handle back button from preferences"""
            if self.previous_page:
                self.stacked_widget.setCurrentWidget(self.previous_page)
            else:
                self.switch_to_home()
        
        def show_error_message(self, error_message):
            """Display error messages from various components"""
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", error_message)

        def handle_page_change(self, index):
            """Handle page changes in the stacked widget"""
            current_widget = self.stacked_widget.widget(index)

        def resizeEvent(self, event):
            """Handle resize event to position detail panels and terminal"""
            super().resizeEvent(event)
            if hasattr(self, 'detail_page') and self.detail_page.is_visible:
                self.detail_page.setFixedHeight(self.height())
                self.detail_page.move(self.width() - self.detail_page.width(), 0)
            if hasattr(self, 'cluster_view'):
                if self.stacked_widget.currentWidget() == self.cluster_view and hasattr(self.cluster_view, 'terminal_panel'):
                    if self.cluster_view.terminal_panel.is_visible:
                        QTimer.singleShot(10, self.cluster_view.adjust_terminal_position)
                elif hasattr(self.cluster_view, 'terminal_panel') and self.cluster_view.terminal_panel.is_visible:
                    QTimer.singleShot(10, self.cluster_view.adjust_terminal_position)

        def mousePressEvent(self, event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

        def mouseMoveEvent(self, event):
            if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, 'drag_position'):
                self.move(event.globalPosition().toPoint() - self.drag_position)
                if hasattr(self, 'detail_page') and self.detail_page.is_visible:
                    self.detail_page.move(self.geometry().right() - self.detail_page.width(), self.geometry().top())
                event.accept()

        def moveEvent(self, event):
            """Handle move event to keep detail panels and terminal in position"""
            super().moveEvent(event)
            if hasattr(self, 'detail_page') and self.detail_page.is_visible:
                self.detail_page.move(self.geometry().right() - self.detail_page.width(), self.geometry().top())
            if hasattr(self, 'cluster_view') and hasattr(self.cluster_view, 'terminal_panel'):
                if self.cluster_view.terminal_panel.is_visible:
                    QTimer.singleShot(10, self.cluster_view.adjust_terminal_position)

        def closeEvent(self, event):
            """Clean up resources before closing"""
            if hasattr(self, 'cluster_view') and hasattr(self.cluster_view, 'terminal_panel'):
                if self.cluster_view.terminal_panel.is_visible:
                    self.cluster_view.terminal_panel.hide_terminal()
            if hasattr(self, 'detail_page') and self.detail_page.is_visible:
                self.detail_page.hide_detail()
            super().closeEvent(event)

    if __name__ == "__main__":
        app = QApplication(sys.argv)
        app.setFont(QFont("Segoe UI", 10))
        
        splash = SplashScreen()
        splash.show()
        
        window = MainWindow()
        
        def show_main_window():
            window.show()
            splash.close()
        
        splash.finished.connect(show_main_window)
        sys.exit(app.exec())

except Exception as e:
    import traceback
    print(f"Error during execution: {e}")
    traceback.print_exc()
    sys.exit(1)