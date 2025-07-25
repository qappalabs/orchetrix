import sys
import os
import traceback
import logging
import time
import webbrowser
import requests
import json
import gc
from datetime import datetime
from PyQt6.QtCore import QPoint

# Set up logging first
try:
    from log_handler import setup_logging, log_exception
    log_file = setup_logging()
except ImportError as e:
    # Fallback logging setup
    error_file = "orchestrix_critical_error.log"
    with open(error_file, "w") as f:
        f.write(f"CRITICAL IMPORT ERROR: {str(e)}\n")
        f.write(traceback.format_exc())
    log_file = error_file

    # Setup basic logging
    logging.basicConfig(
        filename=error_file,
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# Initialize PyQt imports
try:
    logging.info("Initializing application...")
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout,
        QStackedWidget, QMessageBox
    )
    from PyQt6.QtCore import Qt, QTimer, qVersion, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QIcon

    # Import application components
    from UI.SplashScreen import SplashScreen
    from Pages.HomePage import OrchestrixGUI
    from Pages.Preferences import PreferencesWidget
    from UI.TitleBar import TitleBar
    from UI.ClusterView import ClusterView, LoadingOverlay
    from UI.Styles import AppColors, AppStyles
    from utils.cluster_connector import get_cluster_connector
    from UI.DetailPageComponent import DetailPageComponent
    from UI.detail_sections.detailpage_yamlsection import DetailPageYAMLSection

    from utils.cluster_state_manager import get_cluster_state_manager, ClusterState
    from utils.thread_manager import get_thread_manager, shutdown_thread_manager


    logging.info("All modules imported successfully")
    
except ImportError as e:
    logging.critical(f"Failed to import application modules: {e}")
    raise

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            full_path = os.path.join(base_path, relative_path)
            logging.debug(f"Resource path: {full_path}")
            return full_path
        else:
            base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)
    except Exception as e:
        logging.error(f"Error in resource_path for {relative_path}: {e}")
        return relative_path

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Global handler for uncaught exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    try:
        if QApplication.instance():
            if not getattr(QApplication.instance(), '_showing_error', False):
                QApplication.instance()._showing_error = True
                QMessageBox.critical(None, "Error",
                                     f"An unexpected error occurred:\n{str(exc_value)}\n\nDetails have been logged to: {log_file}")
    except Exception:
        pass

def initialize_resources():
    """Initialize resource paths and verify critical resources exist"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        logging.info(f"Running as PyInstaller bundle from: {base_path}")

        resource_dirs = ['icons', 'images', 'logos']
        for dir_name in resource_dirs:
            dir_path = os.path.join(base_path, dir_name)
            if os.path.exists(dir_path):
                files = os.listdir(dir_path)[:10]
                logging.info(f"✓ Directory {dir_name} found with items: {files}")

                if dir_name == 'icons':
                    critical_icons = ['logoIcon.png', 'home.svg', 'browse.svg']
                    for icon in critical_icons:
                        if os.path.exists(os.path.join(dir_path, icon)):
                            logging.info(f"  ✓ Critical file found: {icon}")
                        else:
                            logging.warning(f"  ✗ Critical file missing: {icon}")
            else:
                logging.error(f"✗ Directory {dir_name} NOT FOUND")
    else:
        logging.info("Running in normal Python environment")


class MainWindow(QMainWindow):
    """Optimized main window with improved resource management and performance"""
    
    def __init__(self):
        super().__init__()
        self.previous_page = None
        self.drag_position = None
        self.app_timezone = None
        self._error_shown = False
        self._shutting_down = False
        self._is_switching_to_cluster = False
        self._target_cluster_for_switch = None
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._periodic_cleanup)
        self._cleanup_timer.start(30000)  # Cleanup every 30 seconds

        # Set application icon
        icon_path = resource_path("icons/logoIcon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            png_path = resource_path("icons/logoIcon.png")
            if os.path.exists(png_path):
                self.setWindowIcon(QIcon(png_path))

        # Setup window properties first
        self.setWindowTitle("Orchestrix")
        self.setMinimumSize(1300, 700)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(AppStyles.MAIN_STYLE)

        try:
            self._setup_cluster_state_manager()
        except Exception as e:
            logging.error(f"Failed to initialize cluster state manager: {e}")
            self.cluster_state_manager = None

        # Initialize UI components
        self.init_ui()

        # Central loading overlay
        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.hide()

        self.installEventFilter(self)

        # Initialize cluster connector for home page
        if hasattr(self.home_page, 'initialize_cluster_connector'):
            self.home_page.initialize_cluster_connector()

    def _periodic_cleanup(self):
        """Periodic cleanup to prevent memory leaks"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Cleanup chart page caches if needed
            if hasattr(self, 'cluster_view') and hasattr(self.cluster_view, 'pages'):
                charts_page = self.cluster_view.pages.get('Charts')
                if charts_page and hasattr(charts_page, 'cleanup_cache'):
                    charts_page.cleanup_cache()
                    
        except Exception as e:
            logging.error(f"Error during periodic cleanup: {e}")

    def _setup_cluster_state_manager(self):
        """Setup cluster state manager"""
        try:
            self.cluster_state_manager = get_cluster_state_manager()
            self.cluster_state_manager.state_changed.connect(self._on_cluster_state_changed)
            self.cluster_state_manager.switch_completed.connect(self._on_cluster_switch_completed)
        except Exception as e:
            logging.error(f"Failed to setup cluster state manager: {e}")
            self.cluster_state_manager = None

    def resizeEvent(self, event):
        """Handle resize event"""
        super().resizeEvent(event)
        self.update_panel_positions()
        if hasattr(self, 'loading_overlay') and self.loading_overlay.isVisible():
            self.loading_overlay.resize(self.size())

    def init_ui(self):
        """Initialize all UI components"""
        # Main widget and layout
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Initialize pages
        self.home_page = OrchestrixGUI()
        self.title_bar = TitleBar(self, update_pinned_items_signal=self.home_page.update_pinned_items_signal)
        self.main_layout.addWidget(self.title_bar)

        # Setup stacked widget for page navigation
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.currentChanged.connect(self.handle_page_change)
        self.main_layout.addWidget(self.stacked_widget)

        # Create pages
        self.cluster_view = ClusterView(self)
        self.preferences_page = PreferencesWidget()

        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.home_page)
        self.stacked_widget.addWidget(self.cluster_view)
        self.stacked_widget.addWidget(self.preferences_page)

        # Page registry
        self.pages = {
            "Home": self.home_page,
            "Cluster": self.cluster_view,
            "Preferences": self.preferences_page
        }

        # Set main widget and default page
        self.setCentralWidget(self.main_widget)
        self.stacked_widget.setCurrentWidget(self.home_page)

        # Setup connections
        self.setup_connections()

    def setup_connections(self):
        """Set up signal connections between components"""
        self.home_page.open_cluster_signal.connect(self.switch_to_cluster_view)
        self.home_page.open_preferences_signal.connect(self.switch_to_preferences)
        self.title_bar.home_btn.clicked.connect(self.switch_to_home)
        self.title_bar.settings_btn.clicked.connect(self.switch_to_preferences)
        self.preferences_page.back_signal.connect(self.handle_preferences_back)

        # Connect preferences signals
        self.preferences_page.font_size_changed.connect(self.update_yaml_editor_font_size)
        self.preferences_page.font_changed.connect(self.update_yaml_editor_font_family)
        self.preferences_page.line_numbers_changed.connect(self.update_yaml_editor_line_numbers)
        self.preferences_page.tab_size_changed.connect(self.update_yaml_editor_tab_size)
        self.preferences_page.timezone_changed.connect(self.apply_timezone_change)

    def show_simple_notification(self, title, message):
        """Show a simple notification"""
        try:
            msg = QMessageBox(self)
            msg.setWindowTitle(title)
            msg.setText(message)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
            msg.setWindowOpacity(0.9)

            # Position notification
            if hasattr(self, 'main_widget'):
                parent_geom = self.main_widget.geometry()
                parent_global_pos = self.main_widget.mapToGlobal(QPoint(0,0))
                pos_x = parent_global_pos.x() + parent_geom.width() - 310
                pos_y = parent_global_pos.y() + parent_geom.height() - 110
                msg.move(pos_x, pos_y)

            QTimer.singleShot(3000, msg.close)
            msg.show()

        except Exception as e:
            logging.error(f"Error showing notification: {e}")

    def apply_timezone_change(self, timezone):
        """Apply timezone changes throughout the application"""
        try:
            self.app_timezone = timezone
            logging.info(f"Setting application timezone to: {timezone}")

            os.environ["TZ"] = timezone
            try:
                if hasattr(time, 'tzset'):
                    time.tzset()
            except Exception as e:
                logging.warning(f"Failed to apply timezone with tzset: {e}")

            if hasattr(self.title_bar, 'update_timezone'):
                self.title_bar.update_timezone(timezone)

            if hasattr(self.cluster_view, 'update_timezone_dependent_displays'):
                self.cluster_view.update_timezone_dependent_displays(timezone)

            self.save_timezone_preference(timezone)

        except Exception as e:
            logging.error(f"Error applying timezone change: {e}")
            self.show_error_message(f"Failed to change timezone: {str(e)}")

    def save_timezone_preference(self, timezone):
        """Save timezone preference to settings"""
        try:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))

            settings_dir = os.path.join(base_dir, "settings")
            os.makedirs(settings_dir, exist_ok=True)
            settings_file = os.path.join(settings_dir, "app_settings.json")

            settings = {}
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r') as f:
                        settings = json.load(f)
                except json.JSONDecodeError:
                    logging.warning(f"Could not decode settings file: {settings_file}")

            settings['timezone'] = timezone

            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)

            logging.info(f"Saved timezone preference to {settings_file}")

        except Exception as e:
            logging.error(f"Failed to save timezone preference: {e}")

    def load_app_settings(self):
        """Load application settings"""
        try:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))

            settings_file = os.path.join(base_dir, "settings", "app_settings.json")

            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    try:
                        settings = json.load(f)
                    except json.JSONDecodeError:
                        logging.error(f"Failed to parse settings file: {settings_file}")
                        settings = {}

                loaded_timezone = settings.get('timezone')
                if loaded_timezone:
                    self.app_timezone = loaded_timezone
                    os.environ["TZ"] = loaded_timezone
                    try:
                        if hasattr(time, 'tzset'):
                            time.tzset()
                    except Exception as e:
                        logging.warning(f"Failed to apply saved timezone: {e}")
                    
                    if hasattr(self.preferences_page, 'set_initial_timezone'):
                        self.preferences_page.set_initial_timezone(loaded_timezone)

        except Exception as e:
            logging.error(f"Error loading application settings: {e}")

    def update_yaml_editor_font_size(self, font_size):
        """Update font size for all YAML editors"""
        logging.debug(f"Updating YAML editor font size to {font_size}")

        if hasattr(self, 'cluster_view') and self.cluster_view:
            if hasattr(self.cluster_view, 'update_yaml_editor_font_size'):
                self.cluster_view.update_yaml_editor_font_size(font_size)

        for widget in QApplication.allWidgets():
            if isinstance(widget, DetailPageComponent) and hasattr(widget, 'update_yaml_font_size'):
                widget.update_yaml_font_size(font_size)
            elif isinstance(widget, DetailPageYAMLSection) and hasattr(widget, 'update_yaml_font_size'):
                widget.update_yaml_font_size(font_size)

    def update_yaml_editor_font_family(self, font_family):
        """Update font family for all YAML editors"""
        logging.debug(f"Updating YAML editor font family to {font_family}")

        if hasattr(self, '_updating_font_family') and self._updating_font_family == font_family:
            return
        self._updating_font_family = font_family

        try:
            if hasattr(self, 'cluster_view') and self.cluster_view:
                if hasattr(self.cluster_view, 'update_yaml_editor_font_family'):
                    self.cluster_view.update_yaml_editor_font_family(font_family)

            for widget in QApplication.allWidgets():
                if isinstance(widget, DetailPageComponent):
                    if hasattr(widget, 'update_yaml_font_family'):
                        widget.update_yaml_font_family(font_family)
                elif isinstance(widget, DetailPageYAMLSection):
                    if hasattr(widget, 'update_yaml_font_family'):
                        widget.update_yaml_font_family(font_family)

        finally:
            delattr(self, '_updating_font_family')

    def update_yaml_editor_line_numbers(self, show_line_numbers):
        """Update line numbers for all YAML editors"""
        logging.debug(f"Updating YAML editor line numbers to {show_line_numbers}")

        if hasattr(self, 'cluster_view') and self.cluster_view:
            if hasattr(self.cluster_view, 'update_yaml_editor_line_numbers'):
                self.cluster_view.update_yaml_editor_line_numbers(show_line_numbers)

        for widget in QApplication.allWidgets():
            if isinstance(widget, DetailPageComponent) and hasattr(widget, 'update_yaml_line_numbers'):
                widget.update_yaml_line_numbers(show_line_numbers)
            elif isinstance(widget, DetailPageYAMLSection) and hasattr(widget, 'update_yaml_line_numbers'):
                widget.update_yaml_line_numbers(show_line_numbers)

    def update_yaml_editor_tab_size(self, tab_size):
        """Update tab size for all YAML editors"""
        logging.debug(f"Updating YAML editor tab size to {tab_size}")

        if hasattr(self, 'cluster_view') and self.cluster_view:
            if hasattr(self.cluster_view, 'update_yaml_editor_tab_size'):
                self.cluster_view.update_yaml_editor_tab_size(tab_size)

        for widget in QApplication.allWidgets():
            if isinstance(widget, DetailPageComponent) and hasattr(widget, 'update_yaml_tab_size'):
                widget.update_yaml_tab_size(tab_size)
            elif isinstance(widget, DetailPageYAMLSection) and hasattr(widget, 'update_yaml_tab_size'):
                widget.update_yaml_tab_size(tab_size)

    def hide_terminal_if_visible(self):
        """Helper method to hide terminal if visible"""
        if (hasattr(self, 'cluster_view') and
                hasattr(self.cluster_view, 'terminal_panel') and
                self.cluster_view.terminal_panel.is_visible):
            self.cluster_view.terminal_panel.hide_terminal()

    def switch_to_home(self):
        """Switch to home page"""
        logging.debug("Switching to home page...")

        if hasattr(self, 'cluster_view') and hasattr(self.cluster_view, 'close_any_open_detail_panels'):
            self.cluster_view.close_any_open_detail_panels()

        self.hide_terminal_if_visible()

        if self.stacked_widget.currentWidget() != self.home_page:
            self.previous_page = self.stacked_widget.currentWidget()
            self.stacked_widget.setCurrentWidget(self.home_page)

    def switch_to_preferences(self):
        """Switch to preferences page"""
        logging.debug("Switching to preferences page...")

        if hasattr(self, 'cluster_view') and hasattr(self.cluster_view, 'close_any_open_detail_panels'):
            self.cluster_view.close_any_open_detail_panels()

        self.hide_terminal_if_visible()

        if self.stacked_widget.currentWidget() != self.preferences_page:
            self.previous_page = self.stacked_widget.currentWidget()
            self.stacked_widget.setCurrentWidget(self.preferences_page)

    def handle_preferences_back(self):
        """Handle back button from preferences"""
        if self.previous_page and self.previous_page in [self.home_page, self.cluster_view]:
            self.stacked_widget.setCurrentWidget(self.previous_page)
        else:
            self.switch_to_home()
        self.previous_page = None

    def _on_cluster_state_changed(self, cluster_name: str, state: ClusterState):
        """Handle cluster state changes with better error handling"""
        try:
            if state == ClusterState.CONNECTING:
                # Don't show loading overlay during connection
                pass
                
            elif state == ClusterState.CONNECTED:
                # Don't show loading message, connect silently
                logging.info(f"Successfully connected to cluster: {cluster_name}")
                
            elif state == ClusterState.ERROR:
                # Hide any existing loading overlay on error
                self.loading_overlay.hide_loading()
                logging.error(f"Failed to connect to cluster: {cluster_name}")
                
        except Exception as e:
            logging.error(f"Error handling cluster state change: {e}")

    def _on_cluster_switch_completed(self, cluster_name: str, success: bool):
        """Handle cluster switch completion with better error handling"""
        try:
            self.loading_overlay.hide_loading()
            
            if success:
                # Always switch to cluster view when switch is completed successfully
                current_widget = self.stacked_widget.currentWidget()
                if current_widget != self.cluster_view:
                    logging.info(f"Switching to cluster view for {cluster_name}")
                    self.stacked_widget.setCurrentWidget(self.cluster_view)
                
                # FIXED: Set active cluster without triggering another connection
                self.cluster_view.set_active_cluster(cluster_name)
                
                # FIXED: Post-switch operations with error handling
                QTimer.singleShot(50, lambda: self._post_switch_operations(cluster_name))
                
            else:
                # FIXED: Better error handling - don't switch to cluster view on failure
                error_msg = f"Failed to connect to cluster: {cluster_name}"
                logging.error(error_msg)
                self.show_error_message(error_msg)
                
                # FIXED: Stay on home page when connection fails
                if self.stacked_widget.currentWidget() != self.home_page:
                    logging.info(f"Connection failed for {cluster_name}, staying on home page")
                    self.stacked_widget.setCurrentWidget(self.home_page)
                    
        except Exception as e:
            logging.error(f"Error handling cluster switch completion: {e}")
            self.loading_overlay.hide_loading()

    def _post_switch_operations(self, cluster_name):
        """Post-switch operations with better error handling"""
        try:
            # FIXED: Don't call set_active_cluster again, it was already called
            
            # Update terminal panel position if visible
            if (hasattr(self.cluster_view, 'terminal_panel') and
                    self.cluster_view.terminal_panel.is_visible and
                    hasattr(self.cluster_view.terminal_panel, 'reposition')):
                self.cluster_view.terminal_panel.reposition()
                
            # Handle page change for current cluster view page
            if hasattr(self.cluster_view, 'handle_page_change'):
                current_page = self.cluster_view.stacked_widget.currentWidget()
                if current_page:
                    self.cluster_view.handle_page_change(current_page)
                    
            logging.info(f"Post-switch operations completed for {cluster_name}")
            
        except Exception as e:
            logging.error(f"Error in post-switch operations for {cluster_name}: {e}")

    def switch_to_cluster_view(self, cluster_name="docker-desktop"):
        """Improved cluster switching with better error handling"""
        try:
            if not self.cluster_state_manager:
                self.show_error_message("Cluster state manager not initialized.")
                return

            self.previous_page = self.stacked_widget.currentWidget()
            
            # FIXED: Check actual connection state first
            cluster_state = self.cluster_state_manager.get_cluster_state(cluster_name)
            
            # If already connected, switch to cluster view immediately
            if cluster_state == ClusterState.CONNECTED:
                logging.info(f"Cluster {cluster_name} already connected, switching to cluster view")
                if self.stacked_widget.currentWidget() != self.cluster_view:
                    self.stacked_widget.setCurrentWidget(self.cluster_view)
                self.cluster_view.set_active_cluster(cluster_name)
                return
            
            # FIXED: Only show loading overlay if we need to connect
            if cluster_state in [ClusterState.DISCONNECTED, ClusterState.ERROR, ClusterState.MANUALLY_DISCONNECTED]:
                logging.info(f"Requesting cluster switch to: {cluster_name}")
                
                if not self.cluster_state_manager.request_cluster_switch(cluster_name):
                    error_msg = f"Could not initiate switch to {cluster_name}"
                    logging.warning(error_msg)
                    self.show_error_message(error_msg)
                    return
            else:
                # Already connecting, just wait
                logging.info(f"Cluster {cluster_name} already connecting, waiting...")
                
        except Exception as e:
            logging.error(f"Error in switch_to_cluster_view for {cluster_name}: {e}")
            self.show_error_message(f"Error switching to cluster: {str(e)}")

    def show_error_message(self, error_message):
        """Display error messages with improved handling"""
        if self._shutting_down:
            return

        try:
            # FIXED: Prevent error dialog spam
            if not hasattr(self, '_error_shown'):
                self._error_shown = False

            if self._error_shown:
                logging.error(f"Suppressed duplicate error dialog: {error_message}")
                return

            self._error_shown = True
            
            # FIXED: Hide loading overlay when showing error
            if hasattr(self, 'loading_overlay'):
                self.loading_overlay.hide_loading()
            
            # Create and show error message
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Error")
            msg.setText(str(error_message))
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # FIXED: Add timeout to prevent hanging dialogs
            QTimer.singleShot(10000, msg.close)  # Auto-close after 10 seconds
            
            msg.exec()
            
            # Reset error flag after showing
            QTimer.singleShot(2000, self._reset_error_flag)
            
        except Exception as e:
            logging.error(f"Error showing error message: {e}")

    def _reset_error_flag(self):
        """Reset the error dialog flag"""
        try:
            self._error_shown = False
        except:
            pass
  

    def handle_page_change(self, index):
        """Handle page changes in the stacked widget"""
        current_widget = self.stacked_widget.widget(index)
        logging.debug(f"Page changed to: {current_widget.objectName() if hasattr(current_widget, 'objectName') else type(current_widget).__name__}")

        if hasattr(self, 'cluster_view'):
            if current_widget != self.cluster_view:
                logging.debug("Switched away from cluster view, ensuring detail panels are closed.")
                if hasattr(self.cluster_view, 'close_any_open_detail_panels'):
                    self.cluster_view.close_any_open_detail_panels()

        self.hide_terminal_if_visible()

        if current_widget == self.cluster_view and hasattr(self.cluster_view, 'stacked_widget'):
            active_cluster_subpage = self.cluster_view.stacked_widget.currentWidget()

            if active_cluster_subpage:
                if hasattr(active_cluster_subpage, 'force_load_data'):
                    active_cluster_subpage.force_load_data()
                elif hasattr(active_cluster_subpage, 'load_data'):
                    active_cluster_subpage.load_data()

        if hasattr(self.title_bar, 'update_context'):
            page_name = "Unknown"
            for name, widget_instance in self.pages.items():
                if widget_instance == current_widget:
                    page_name = name
                    break
            self.title_bar.update_context(page_name)

    def update_panel_positions(self):
        """Update positions of panels"""
        if hasattr(self, 'profile_screen') and self.profile_screen.is_visible:
            self.profile_screen.setFixedHeight(self.height())
            self.profile_screen.move(self.width() - self.profile_screen.width(), 0)

        if hasattr(self, 'notification_screen') and self.notification_screen.is_visible:
            if hasattr(self.notification_screen, 'update_position'):
                self.notification_screen.update_position()

    def moveEvent(self, event):
        """Handle move event"""
        super().moveEvent(event)
        self.update_panel_positions()

    def closeEvent(self, event):
        if self._shutting_down:
            super().closeEvent(event)
            return

        logging.info("Starting application shutdown sequence...")
        self._shutting_down = True

        try:
            # Stop cleanup timer
            if hasattr(self, '_cleanup_timer'):
                self._cleanup_timer.stop()

            # Shutdown thread manager
            shutdown_thread_manager()
            
            # Shutdown cluster operations
            self.shutdown_cluster_operations()

            # Clean up UI components
            self.cleanup_ui_components()

            # Clean up timers and threads
            self.cleanup_timers_and_threads()

            super().closeEvent(event)
            logging.info("Application shutdown completed successfully.")

        except Exception as e:
            logging.error(f"Error during application shutdown: {e}")
            super().closeEvent(event)


    def shutdown_cluster_operations(self):
        """Stop all cluster-related operations"""
        try:
            if hasattr(self, 'cluster_connector') and self.cluster_connector:
                logging.debug("Stopping cluster connector operations.")
                if hasattr(self.cluster_connector, 'stop_polling'):
                    self.cluster_connector.stop_polling()
                if hasattr(self.cluster_connector, '_shutting_down'):
                    self.cluster_connector._shutting_down = True
                self._disconnect_cluster_signals()

            if hasattr(self, 'home_page') and hasattr(self.home_page, 'kube_client'):
                kube_client = self.home_page.kube_client
                if kube_client:
                    logging.debug("Stopping Kubernetes client operations.")
                    if hasattr(kube_client, '_shutting_down'):
                        kube_client._shutting_down = True
                    if hasattr(kube_client, 'stop_metrics_polling'):
                        kube_client.stop_metrics_polling()
                    if hasattr(kube_client, 'stop_issues_polling'):
                        kube_client.stop_issues_polling()

        except Exception as e:
            logging.error(f"Error in shutdown_cluster_operations: {e}")

    def cleanup_ui_components(self):
        """Clean up UI components safely"""
        try:
            if (hasattr(self, 'cluster_view') and
                    hasattr(self.cluster_view, 'terminal_panel')):
                if self.cluster_view.terminal_panel.is_visible:
                    try:
                        self.cluster_view.terminal_panel.hide_terminal()
                    except Exception as e:
                        logging.error(f"Error hiding terminal: {e}")
                
                if hasattr(self.cluster_view.terminal_panel, 'cleanup'):
                    self.cluster_view.terminal_panel.cleanup()

            # Clean up main pages
            pages_to_cleanup = [self.home_page, self.cluster_view, self.preferences_page]
            for page in pages_to_cleanup:
                if page and hasattr(page, 'cleanup_on_destroy'):
                    try:
                        page.cleanup_on_destroy()
                    except Exception as e:
                        logging.error(f"Error cleaning up page {type(page).__name__}: {e}")

        except Exception as e:
            logging.error(f"Error in cleanup_ui_components: {e}")

    def cleanup_timers_and_threads(self):
        """Clean up all QTimer objects and threads"""
        logging.debug("Stopping active QTimers and threads.")

        potential_timer_parents = [self, self.main_widget, self.title_bar, self.stacked_widget,
                                   self.home_page, self.cluster_view, self.preferences_page,
                                   self.loading_overlay]
        
        if hasattr(self, 'cluster_view') and hasattr(self.cluster_view, 'terminal_panel'):
            potential_timer_parents.append(self.cluster_view.terminal_panel)

        timers_stopped = 0
        for parent_obj in potential_timer_parents:
            if parent_obj is None:
                continue

            try:
                child_timers = parent_obj.findChildren(QTimer)
                for timer in child_timers:
                    if timer.isActive():
                        timer.stop()
                        timers_stopped += 1
            except RuntimeError:
                logging.warning(f"RuntimeError while finding timers for {type(parent_obj).__name__}")
            except Exception as e:
                logging.error(f"Error finding/stopping timers for {type(parent_obj).__name__}: {e}")

        logging.info(f"Stopped {timers_stopped} active QTimers.")
        QThread.msleep(100)

def main():
    """Application entry point with platform-consistent styling"""
    sys.excepthook = global_exception_handler
    initialize_resources()

    logging.info(f"Python version: {sys.version}")
    logging.info(f"PyQt version: {qVersion()}")
    logging.info(f"Working directory: {os.getcwd()}")
    logging.info(f"Process ID: {os.getpid()}")

    logging.info("Creating QApplication with consistent styling")
    app = QApplication(sys.argv)
    
    # Force consistent Qt style across platforms
    app.setStyle('Fusion')  # Use Fusion style for consistency
 
    # Force consistent font rendering
    app.setFont(QFont("Segoe UI", 9))
    
    # Apply global stylesheet with platform overrides
    app.setStyleSheet(AppStyles.GLOBAL_PLATFORM_OVERRIDE_STYLE)
    
    # Set application icon
    icon_path_ico = resource_path("icons/logoIcon.ico")
    icon_path_png = resource_path("icons/logoIcon.png")
    if os.path.exists(icon_path_ico):
        app.setWindowIcon(QIcon(icon_path_ico))
        logging.info(f"Application icon set from: {icon_path_ico}")
    elif os.path.exists(icon_path_png):
        app.setWindowIcon(QIcon(icon_path_png))
        logging.info(f"Application icon set from PNG: {icon_path_png}")

    # Windows taskbar configuration
    if sys.platform == 'win32':
        try:
            import ctypes
            app_id = u'Orchestrix.KubernetesManager.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            logging.info(f"Windows AppUserModelID set to: {app_id}")
        except Exception as e:
            logging.warning(f"Failed to set Windows taskbar AppUserModelID: {e}")

    app.setQuitOnLastWindowClosed(True)

    # Create and show splash screen
    splash = None
    try:
        logging.info("Creating splash screen")
        splash = SplashScreen()
        splash.show()
        app.processEvents()
    except Exception as e:
        logging.error(f"Error creating splash screen: {e}")
        if splash:
            splash.close()
        splash = None

    # Create main window
    window = None
    try:
        logging.info("Creating main window...")
        window = MainWindow()

        logging.info("Loading application settings...")
        window.load_app_settings()

        # Handle splash screen
        if splash:
            def show_main_window_after_splash():
                if window:
                    logging.info("Showing main window...")
                    window.show()
                    window.activateWindow()

                logging.info("Closing splash screen...")
                if window:
                    if hasattr(splash, 'finish'):
                        splash.finish(window)
                    else:
                        splash.close()
                else:
                    splash.close()

                logging.info("Main window shown successfully.")

            if hasattr(splash, 'start_loading_simulation'):
                splash.loading_finished.connect(show_main_window_after_splash)
                splash.start_loading_simulation(3000)
            else:
                QTimer.singleShot(2000, show_main_window_after_splash)

        else:
            if window:
                window.show()
                window.activateWindow()
                logging.info("Main window shown directly.")

        logging.info("Starting application main event loop.")
        exit_code = app.exec()
        logging.info(f"Application event loop finished. Exit code: {exit_code}")
        return exit_code

    except Exception as e:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_details = f"[{current_time}] CRITICAL ERROR: {str(e)}\n{traceback.format_exc()}"
        logging.critical(error_details)

        try:
            if QApplication.instance():
                if not getattr(QApplication.instance(), '_showing_error', False):
                    QApplication.instance()._showing_error = True
                    QMessageBox.critical(None, "Fatal Application Error",
                                         f"A critical error occurred:\n{str(e)}\n\n"
                                         f"Details logged to: {log_file}")
        except Exception:
            pass

        return 1
    
if __name__ == "__main__":
    exit_status = 1
    try:
        exit_status = main()
    except SystemExit as se:
        exit_status = se.code if se.code is not None else 0
        logging.info(f"Application exited via SystemExit with code: {exit_status}")
    except Exception as e:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fatal_error_msg = f"[{current_time}] FATAL EXCEPTION: {str(e)}\n{traceback.format_exc()}"
        logging.critical(fatal_error_msg)

        try:
            fatal_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orchestrix_FATAL_ERROR.log")
            with open(fatal_log_path, "a") as f:
                f.write(fatal_error_msg + "\n")
        except Exception:
            pass

    finally:
        logging.info(f"Exiting application with status code: {exit_status}")
        sys.exit(exit_status)
