import sys
import os
import traceback
import logging
import time
import webbrowser
import requests
import json
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

# Note: subprocess_patch import moved to after PyQt imports to avoid conflicts
# with kubernetes library that also uses subprocess

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
    from UI.ProfileScreen import ProfileScreen
    from UI.NotificationScreen import NotificationScreen
    from UI.DetailPageComponent import DetailPage

    logging.info("All modules imported successfully")

    # Apply subprocess patch after other imports to avoid conflicts
    try:
        # Only import subprocess patch if we're not in a problematic environment
        import sys
        if not hasattr(sys, '_subprocess_patched'):
            from subprocess_patch import *
            sys._subprocess_patched = True
            logging.info("Subprocess patch applied successfully")
    except ImportError as e:
        logging.warning(f"Subprocess patch not available: {e}")
    except Exception as e:
        logging.warning(f"Failed to apply subprocess patch: {e}")

except ImportError as e:
    logging.critical(f"Failed to import application modules: {e}")
    raise

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            full_path = os.path.join(base_path, relative_path)
            logging.debug(f"Resource path: {full_path}")
            return full_path
        else:
            # Running in normal Python environment
            base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)
    except Exception as e:
        logging.error(f"Error in resource_path for {relative_path}: {e}")
        return relative_path

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Global handler for uncaught exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't catch KeyboardInterrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Log the exception
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    # Show user-friendly message if possible, but only once
    try:
        if QApplication.instance():
            # Only show dialog if not already shutting down
            if not getattr(QApplication.instance(), '_showing_error', False):
                QApplication.instance()._showing_error = True
                QMessageBox.critical(None, "Error",
                                     f"An unexpected error occurred:\n{str(exc_value)}\n\nDetails have been logged to: {log_file}")
    except Exception:
        pass

def initialize_resources():
    """Initialize resource paths and verify critical resources exist in PyInstaller environment"""
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        base_path = sys._MEIPASS
        logging.info(f"Running as PyInstaller bundle from: {base_path}")

        # Check critical resource directories
        resource_dirs = ['icons', 'images', 'logos']
        for dir_name in resource_dirs:
            dir_path = os.path.join(base_path, dir_name)
            if os.path.exists(dir_path):
                # List first 10 files as a sample
                files = os.listdir(dir_path)[:10]
                logging.info(f"✓ Directory {dir_name} found with items: {files}")

                # Verify some critical files if they should exist
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

# Define Update Checker thread
class UpdateCheckerThread(QThread):
    """Thread for checking updates in the background"""
    update_available = pyqtSignal(str, str, str)  # version, channel, notes
    update_not_found = pyqtSignal()
    update_error = pyqtSignal(str)

    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    def run(self):
        try:
            # Simulate a network request
            time.sleep(2)

            # Simulate different results based on channel
            if self.channel == "Alpha":
                # Alpha has frequent updates
                version = "2.1.0-alpha.3"
                notes = "New experimental features added:\n- Cloud synchronization\n- Advanced terminal capabilities\n- Extended API support\n\nWarning: This is an alpha build with known issues."
                self.update_available.emit(version, self.channel, notes)
            elif self.channel == "Beta":
                # Beta has occasional updates
                version = "2.0.5-beta"
                notes = "Beta features ready for testing:\n- Performance improvements\n- Bug fixes for recent issues\n- UI enhancements\n\nThis version has been tested but may have minor issues."
                self.update_available.emit(version, self.channel, notes)
            else:  # Stable
                # Stable has rare updates
                version = "2.0.0"
                notes = "You are running the latest stable version."
                self.update_not_found.emit()
        except Exception as e:
            self.update_error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.previous_page = None
        self.drag_position = None
        self.app_timezone = None
        self.update_channel = "Stable"  # Default to Stable channel
        self.update_checker = None
        self.pending_update_info = None
        self._current_update_dialog = None  # Track update dialogs
        self._error_shown = False
        self._shutting_down = False  # Add shutdown flag
        self._is_switching_to_cluster = False # Flag for managing cluster switch state
        self._target_cluster_for_switch = None # Stores the name of the cluster we are trying to switch to

        # Set application icon for this window too
        icon_path = resource_path("icons/logoIcon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            # Fallback to PNG
            png_path = resource_path("icons/logoIcon.png")
            if os.path.exists(png_path):
                self.setWindowIcon(QIcon(png_path))

        # Setup window properties first
        self.setWindowTitle("Orchestrix")
        self.setMinimumSize(1300, 700)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(AppStyles.MAIN_STYLE)

        # Initialize cluster connector before UI setup
        self.cluster_connector = get_cluster_connector()

        # Make sure we are the only component showing error messages
        if hasattr(self, 'home_page') and hasattr(self.home_page, 'show_error_message'):
            try:
                self.cluster_connector.error_occurred.disconnect(self.home_page.show_error_message)
            except (TypeError, RuntimeError):
                pass

        # Initialize UI components
        self.init_ui()

        # Central loading overlay for MainWindow
        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.hide()

        self.installEventFilter(self)

        # Pass cluster connector to home page if needed
        if hasattr(self.home_page, 'initialize_cluster_connector'):
            self.home_page.initialize_cluster_connector()

        # Connect signals for cluster switching logic
        if hasattr(self.cluster_connector, 'connection_complete'):
            try:
                self.cluster_connector.connection_complete.disconnect(self._on_cluster_connection_complete_for_switch)
            except TypeError: pass
            self.cluster_connector.connection_complete.connect(self._on_cluster_connection_complete_for_switch)

        if hasattr(self.cluster_connector, 'cluster_data_loaded'):
            try:
                self.cluster_connector.cluster_data_loaded.disconnect(self._on_initial_cluster_data_ready_for_switch)
            except TypeError: pass
            self.cluster_connector.cluster_data_loaded.connect(self._on_initial_cluster_data_ready_for_switch)

        # Ensure the error_occurred signal is connected for switch logic too
        if hasattr(self.cluster_connector, 'error_occurred'):
            try:
                self.cluster_connector.error_occurred.disconnect(self._on_cluster_connection_error_for_switch)
            except TypeError: pass
            self.cluster_connector.error_occurred.connect(self._on_cluster_connection_error_for_switch)

    def _on_cluster_connection_complete_for_switch(self, cluster_name, success, message):
        if self._is_switching_to_cluster and cluster_name == self._target_cluster_for_switch:
            if success:
                logging.info(f"Connection to {cluster_name} successful. Waiting for initial data...")
                # Loading indicator remains, waiting for cluster_data_loaded
            else:
                logging.error(f"Connection to {cluster_name} failed: {message}")
                self._is_switching_to_cluster = False
                self._target_cluster_for_switch = None
                if self.loading_overlay.isVisible():
                    self.loading_overlay.hide_loading()
                self.show_error_message(f"Failed to connect to {cluster_name}: {message}")

    def _on_initial_cluster_data_ready_for_switch(self, data):
        # data here is the cluster_info dict
        if not self._is_switching_to_cluster or not data or 'name' not in data:
            return

        loaded_cluster_name = data['name']

        if loaded_cluster_name == self._target_cluster_for_switch:
            logging.info(f"Initial data ready for {loaded_cluster_name}, proceeding to switch view.")

            self._is_switching_to_cluster = False
            self._target_cluster_for_switch = None

            if self.loading_overlay.isVisible():
                self.loading_overlay.hide_loading()

            self.stacked_widget.setCurrentWidget(self.cluster_view)

            cached_data = self.cluster_connector.get_cached_data(loaded_cluster_name)
            cluster_page = self.cluster_view.pages.get('Cluster')

            if cluster_page and cached_data:
                if hasattr(cluster_page, 'preload_with_cached_data'):
                    cluster_page.preload_with_cached_data(
                        cached_data.get('cluster_info'),
                        cached_data.get('metrics'),
                        cached_data.get('issues')
                    )
                elif hasattr(cluster_page, 'update_cluster_info'):
                    cluster_page.update_cluster_info(cached_data.get('cluster_info'))

            def post_switch_operations():
                self.cluster_view.set_active_cluster(loaded_cluster_name)
                if hasattr(self.cluster_view, 'terminal_panel') and self.cluster_view.terminal_panel.is_visible:
                    self.cluster_view.adjust_terminal_position()
                if hasattr(self.cluster_view, 'handle_page_change'):
                    self.cluster_view.handle_page_change(self.cluster_view.stacked_widget.currentWidget())

            QTimer.singleShot(50, post_switch_operations)

    def _on_cluster_connection_error_for_switch(self, error_type, error_message):
        if self._is_switching_to_cluster:
            target_cluster = self._target_cluster_for_switch
            logging.error(f"Error connecting to {target_cluster} (type: {error_type}): {error_message}")

            self._is_switching_to_cluster = False
            self._target_cluster_for_switch = None

            if self.loading_overlay.isVisible():
                self.loading_overlay.hide_loading()

            self.show_error_message(f"Failed to connect to {target_cluster}: {error_message}")

    def switch_to_cluster_view(self, cluster_name="docker-desktop"):
        if self._is_switching_to_cluster and self._target_cluster_for_switch == cluster_name:
            logging.info(f"Already attempting to switch to cluster: {cluster_name}")
            return

        if self.stacked_widget.currentWidget() == self.cluster_view and \
                hasattr(self.cluster_view, 'active_cluster') and self.cluster_view.active_cluster == cluster_name:
            logging.info(f"Already viewing cluster: {cluster_name}")
            return

        if not hasattr(self, 'cluster_connector') or not self.cluster_connector:
            self.show_error_message("Cluster connector not initialized.")
            return

        self.previous_page = self.stacked_widget.currentWidget()

        # Check cache first
        cached_cluster_info = None
        if hasattr(self.cluster_connector, 'get_cached_data'):
            cached_data_full = self.cluster_connector.get_cached_data(cluster_name)
            if cached_data_full and 'cluster_info' in cached_data_full:
                cached_cluster_info = cached_data_full['cluster_info']

        if cached_cluster_info: # If basic info is cached
            logging.info(f"Using cached data for {cluster_name} for initial switch.")
            self.stacked_widget.setCurrentWidget(self.cluster_view)

            cluster_page = self.cluster_view.pages.get('Cluster')
            if cluster_page:
                if hasattr(cluster_page, 'preload_with_cached_data'):
                    cluster_page.preload_with_cached_data(
                        cached_data_full.get('cluster_info'),
                        cached_data_full.get('metrics'),
                        cached_data_full.get('issues')
                    )
                elif hasattr(cluster_page, 'update_cluster_info'):
                    cluster_page.update_cluster_info(cached_data_full.get('cluster_info'))

            def post_switch_ops_cached():
                self.cluster_view.set_active_cluster(cluster_name)
                if hasattr(self.cluster_view, 'terminal_panel') and self.cluster_view.terminal_panel.is_visible:
                    self.cluster_view.adjust_terminal_position()
                if hasattr(self.cluster_view, 'handle_page_change'):
                    self.cluster_view.handle_page_change(self.cluster_view.stacked_widget.currentWidget())
            QTimer.singleShot(50, post_switch_ops_cached)
            return

        # If not cached, initiate loading then switch
        logging.info(f"No sufficient cache for {cluster_name}. Initiating load before switching.")
        self._is_switching_to_cluster = True
        self._target_cluster_for_switch = cluster_name

        self.loading_overlay.show_loading(f"Connecting to {cluster_name}...")
        self.loading_overlay.resize(self.size())
        self.loading_overlay.raise_()

        self.cluster_connector.connect_to_cluster(cluster_name)

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

        # Central Loading Overlay (instantiate after main_widget is created)
        self.loading_overlay = LoadingOverlay(self.main_widget)
        self.loading_overlay.setGeometry(self.main_widget.rect())
        self.loading_overlay.hide()

        # Setup connections and auxiliary panels
        self.setup_connections()
        self.setup_profile_screen()
        self.setup_notification_screen()

    def setup_profile_screen(self):
        """Set up the profile panel"""
        self.profile_screen = ProfileScreen(self)
        if hasattr(self.title_bar, 'profile_btn'):
            self.title_bar.profile_btn.clicked.connect(self.toggle_profile_screen)

    def toggle_profile_screen(self):
        """Toggle the profile screen visibility"""
        if not hasattr(self, 'profile_screen'):
            return

        if self.profile_screen.is_visible:
            self.profile_screen.hide_profile()
        else:
            # Set user information before showing
            self.profile_screen.set_user_info(
                name="John Doe",
                username="johndoe",
                email="john.doe@example.com",
                organization="Acme Corp",
                team="DevOps",
                role="Administrator"
            )
            self.profile_screen.show_profile()
            self.profile_screen.raise_()

    def setup_notification_screen(self):
        """Set up the notification panel"""
        self.notification_screen = NotificationScreen(self, self.title_bar.notifications_btn)
        if hasattr(self.title_bar, 'notifications_btn'):
            self.title_bar.notifications_btn.clicked.connect(self.toggle_notification_screen)

    def toggle_notification_screen(self):
        """Toggle the notification screen visibility"""
        if hasattr(self, 'notification_screen'):
            self.notification_screen.toggle_notifications()

    def setup_connections(self):
        """Set up signal connections between components"""
        self.home_page.open_cluster_signal.connect(self.switch_to_cluster_view)
        self.home_page.open_preferences_signal.connect(self.switch_to_preferences)
        self.title_bar.home_btn.clicked.connect(self.switch_to_home)
        self.title_bar.settings_btn.clicked.connect(self.switch_to_preferences)
        self.preferences_page.back_signal.connect(self.handle_preferences_back)

        # Connect preferences font signals to update YAML editor
        self.preferences_page.font_size_changed.connect(self.update_yaml_editor_font_size)
        self.preferences_page.font_changed.connect(self.update_yaml_editor_font_family)

        # Connect preferences line numbers signals to update YAML editor
        self.preferences_page.line_numbers_changed.connect(self.update_yaml_editor_line_numbers)

        # Connect preferences tab size signal to update YAML editor
        self.preferences_page.tab_size_changed.connect(self.update_yaml_editor_tab_size)

        # Connect new timezone changed signal
        self.preferences_page.timezone_changed.connect(self.apply_timezone_change)

        # Connect new update channel changed signal
        self.preferences_page.update_channel_changed.connect(self.apply_update_channel_change)

    def apply_update_channel_change(self, channel):
        """Apply update channel changes throughout the application"""
        try:
            old_channel = self.update_channel
            self.update_channel = channel
            logging.info(f"Setting application update channel from {old_channel} to: {channel}")

            # Apply channel-specific behavior
            if channel == "Alpha":
                self.apply_alpha_channel_behavior()
            elif channel == "Beta":
                self.apply_beta_channel_behavior()
            else:  # Stable
                self.apply_stable_channel_behavior()

            # Save the update channel preference to a settings file
            self.save_update_channel_preference(channel)

            # Check for updates on channel change
            self.check_for_updates_background()

        except Exception as e:
            logging.error(f"Error applying update channel change: {e}")
            self.show_error_message(f"Failed to change update channel: {str(e)}")

    def apply_alpha_channel_behavior(self):
        """Apply alpha channel specific behavior"""
        logging.info("Applying Alpha channel behavior")

        # Customize app appearance for alpha channel
        alpha_style = f"{AppStyles.MAIN_STYLE} QMainWindow {{ border: 2px solid #FF5733; }}"
        self.setStyleSheet(alpha_style)

        # Update title to indicate alpha channel
        self.setWindowTitle("Orchestrix (Alpha)")

        # Enable experimental features
        self.enable_experimental_features(True)

        # Show simple notification instead of using notification screen
        self.show_simple_notification("Alpha Channel Activated",
                                      "You are now using the Alpha channel with experimental features.")

    def apply_beta_channel_behavior(self):
        """Apply beta channel specific behavior"""
        logging.info("Applying Beta channel behavior")

        # Customize app appearance for beta channel
        beta_style = f"{AppStyles.MAIN_STYLE} QMainWindow {{ border: 2px solid #FFC300; }}"
        self.setStyleSheet(beta_style)

        # Update title to indicate beta channel
        self.setWindowTitle("Orchestrix (Beta)")

        # Enable some experimental features
        self.enable_experimental_features(False) # Or True for some beta features

        # Show simple notification instead of using notification screen
        self.show_simple_notification("Beta Channel Activated",
                                      "You are now using the Beta channel with new features.")

    def apply_stable_channel_behavior(self):
        """Apply stable channel specific behavior"""
        logging.info("Applying Stable channel behavior")

        # Reset app appearance to standard style
        self.setStyleSheet(AppStyles.MAIN_STYLE)

        # Reset title
        self.setWindowTitle("Orchestrix")

        # Disable experimental features
        self.enable_experimental_features(False)

        # Show simple notification instead of using notification screen
        self.show_simple_notification("Stable Channel Activated",
                                      "You are now using the Stable channel.")

    def show_simple_notification(self, title, message):
        """Show a simple notification without using the notification screen"""
        try:
            # Create a small, non-modal message box
            msg = QMessageBox(self)
            msg.setWindowTitle(title)
            msg.setText(message)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint) # Tooltip makes it non-modal
            msg.setWindowOpacity(0.9)


            # Position it in the bottom right corner
            geom = self.geometry()
            # Ensure width and height are reasonable for positioning
            msg_width = 300
            msg_height = 100

            # Calculate global position for bottom-right corner
            # Use main_widget for positioning relative to application content area
            if hasattr(self, 'main_widget'):
                parent_geom = self.main_widget.geometry()
                parent_global_pos = self.main_widget.mapToGlobal(QPoint(0,0))
                pos_x = parent_global_pos.x() + parent_geom.width() - msg_width - 10 # 10px margin
                pos_y = parent_global_pos.y() + parent_geom.height() - msg_height -10 # 10px margin
                msg.move(pos_x, pos_y)

            else: # Fallback if main_widget not available yet
                pos = self.mapToGlobal(QPoint(geom.width() - msg_width -10 , geom.height() - msg_height -10))
                msg.move(pos)


            # Automatically close after 3 seconds
            QTimer.singleShot(3000, msg.close)

            # Show the notification
            msg.show()

            # Update notification count on title bar if available
            if hasattr(self.title_bar, 'update_notification_count'):
                try:
                    # This logic should be in NotificationScreen or a shared manager
                    # For now, just simulate an increase.
                    # A more robust solution: self.notification_screen.add_notification_item(...)
                    # and then self.title_bar.update_notification_count(self.notification_screen.get_unread_count())
                    current_count = 0 # Placeholder, get actual count
                    if hasattr(self.notification_screen, 'get_unread_count'):
                        current_count = self.notification_screen.get_unread_count() +1 # Simulate adding one
                    self.title_bar.update_notification_count(current_count if current_count >0 else 1)

                except Exception as e:
                    logging.warning(f"Failed to update notification count: {e}")

        except Exception as e:
            logging.error(f"Error showing notification: {e}")


    def enable_experimental_features(self, enable=False):
        """Enable or disable experimental features"""
        logging.info(f"{'Enabling' if enable else 'Disabling'} experimental features")

        # Example: Enable/disable experimental features in cluster view
        if hasattr(self.cluster_view, 'enable_experimental_features'):
            self.cluster_view.enable_experimental_features(enable)

        # Example: Enable/disable experimental features in home page
        if hasattr(self.home_page, 'enable_experimental_features'):
            self.home_page.enable_experimental_features(enable)

    def check_for_updates_background(self):
        """Check for updates in the background based on current channel"""
        try:
            # Cancel any existing update checker thread
            if self.update_checker and self.update_checker.isRunning():
                self.update_checker.terminate() # Request termination
                self.update_checker.wait(2000) # Wait for up to 2 seconds

            # Create new update checker thread
            self.update_checker = UpdateCheckerThread(self.update_channel)

            # Connect signals
            self.update_checker.update_available.connect(self.handle_update_available)
            self.update_checker.update_not_found.connect(self.handle_update_not_found)
            self.update_checker.update_error.connect(self.handle_update_error)

            # Start the thread
            self.update_checker.start()

            logging.info(f"Started background update check for {self.update_channel} channel")

        except Exception as e:
            logging.error(f"Error starting update check: {e}")

    def handle_update_available(self, version, channel, notes):
        """Handle update available notification from background check"""
        logging.info(f"Update available: {version} on {channel} channel")

        # Store update info for later
        self.pending_update_info = {
            'version': version,
            'channel': channel,
            'notes': notes
        }

        # Show a simple notification about the available update
        self.show_simple_notification(
            f"Update Available: {version}",
            f"A new {channel} update is available.\nClick settings or the notification icon to view details and install."
        )
        # Also add it to the notification screen
        if hasattr(self, 'notification_screen'):
            self.notification_screen.add_notification(
                title=f"Update: {version} ({channel})",
                message="A new software update is available. Click to view details.",
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                on_click=self.show_update_details_from_notification_screen # Pass a callable
            )


    def show_update_details_from_notification_screen(self):
        """Callback for notification screen to show update details"""
        self.show_update_details()


    def handle_update_not_found(self):
        """Handle no update available notification from background check"""
        logging.info(f"No updates available for {self.update_channel} channel")

        # Clear any pending update info
        self.pending_update_info = None
        # Optionally, notify user or update preferences page status
        if hasattr(self.preferences_page, 'update_update_status_label'):
            self.preferences_page.update_update_status_label("You are up to date.", "success")


    def handle_update_error(self, error_message):
        """Handle error in update check"""
        logging.error(f"Error checking for updates: {error_message}")

        # Show a simple error notification
        self.show_simple_notification(
            "Update Check Failed",
            f"Failed to check for updates: {error_message}"
        )
        # Optionally, update preferences page status
        if hasattr(self.preferences_page, 'update_update_status_label'):
            self.preferences_page.update_update_status_label(f"Error: {error_message}", "error")


    def show_update_details(self):
        """Show details about pending update"""
        if not self.pending_update_info:
            QMessageBox.information(self, "No Update", "No pending update information available.")
            return

        update_info = self.pending_update_info

        # Prevent multiple dialogs
        if self._current_update_dialog and self._current_update_dialog.isVisible():
            self._current_update_dialog.raise_()
            self._current_update_dialog.activateWindow()
            return

        # Show update details dialog
        update_msg = QMessageBox(self)
        update_msg.setWindowTitle("Update Available")
        update_msg.setText(f"A new {update_info['channel']} update is available!")
        update_msg.setInformativeText(
            f"Version: {update_info['version']}\n\n"
            f"Release notes:\n{update_info['notes']}"
        )
        update_msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        update_msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        update_msg.button(QMessageBox.StandardButton.Yes).setText("Download and Install")
        update_msg.button(QMessageBox.StandardButton.No).setText("Not Now")
        update_msg.setModal(True) # Ensure it's modal

        # Store reference to current dialog
        self._current_update_dialog = update_msg

        result = update_msg.exec()

        # Clear the reference after dialog is closed
        self._current_update_dialog = None

        if result == QMessageBox.StandardButton.Yes:
            # User chose to download and install
            self.download_and_install_update(
                update_info['version'],
                update_info['channel']
            )

    def download_and_install_update(self, version, channel):
        """Download and install the update"""
        try:
            # Prevent multiple dialogs
            if self._current_update_dialog and self._current_update_dialog.isVisible():
                return

            # Show download progress
            progress_msg = QMessageBox(self)
            progress_msg.setWindowTitle("Downloading Update")
            progress_msg.setText(f"Downloading {channel} version {version}...")
            # progress_msg.setStandardButtons(QMessageBox.StandardButton.Cancel) # Can be problematic with auto-close
            progress_msg.setStandardButtons(QMessageBox.StandardButton.NoButton) # No buttons, auto-close
            progress_msg.setModal(True)

            # Connect cancel button (if using one)
            # progress_msg.button(QMessageBox.StandardButton.Cancel).clicked.connect(self._handle_update_cancel)

            # Store reference to current dialog
            self._current_update_dialog = progress_msg

            # Show the message
            # progress_msg.show() # exec() is better for modality

            # Simulate download and installation process
            # For a real download, use QNetworkAccessManager or requests in a thread
            # Here, we use a timer to simulate progress
            self._download_progress_timer = QTimer(self)
            self._download_progress_value = 0

            def update_progress():
                self._download_progress_value += 20
                if self._current_update_dialog and self._current_update_dialog.isVisible():
                    if self._download_progress_value <= 100:
                        self._current_update_dialog.setText(f"Downloading {channel} version {version}... {self._download_progress_value}%")
                    else:
                        self._download_progress_timer.stop()
                        self._current_update_dialog.setText("Download complete. Installing...")
                        QTimer.singleShot(1500, lambda: self.finish_update_installation(self._current_update_dialog, version, channel))

            self._download_progress_timer.timeout.connect(update_progress)
            self._download_progress_timer.start(500) # Update every 0.5 seconds

            progress_msg.exec() # Use exec() to make it truly modal and block until closed

        except Exception as e:
            logging.error(f"Error downloading update: {e}")
            self.show_error_message(f"Failed to download and install update: {str(e)}")

            # Clean up dialog reference if an error occurs
            if hasattr(self, '_current_update_dialog') and self._current_update_dialog:
                try:
                    self._current_update_dialog.close()
                except: pass # Might already be closed
            self._current_update_dialog = None
            if hasattr(self, '_download_progress_timer') and self._download_progress_timer.isActive():
                self._download_progress_timer.stop()


    def _handle_update_cancel(self):
        logging.info("Update download cancelled by user.")
        if hasattr(self, '_download_progress_timer') and self._download_progress_timer.isActive():
            self._download_progress_timer.stop()
        if self._current_update_dialog and self._current_update_dialog.isVisible():
            self._current_update_dialog.close()
        self._current_update_dialog = None
        self.show_simple_notification("Update Cancelled", "The update download was cancelled.")


    def finish_update_installation(self, progress_msg_ref, version, channel):
        """Finish the update installation process"""
        # Close the progress message
        try:
            if progress_msg_ref and progress_msg_ref.isVisible(): # Use the reference passed
                progress_msg_ref.accept() # Or close() if it was opened with show()
        except RuntimeError:
            # Widget might have been deleted
            pass

        # Clear the dialog reference
        self._current_update_dialog = None

        # Show completion message
        completion_msg = QMessageBox(self)
        completion_msg.setWindowTitle("Update Complete")
        completion_msg.setText(f"Successfully updated to {channel} version {version}!\n\nThe application will restart to apply changes.")
        completion_msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        completion_msg.setModal(True)

        # Ensure it's cleaned up if the app closes before this dialog
        self._current_update_dialog = completion_msg
        completion_msg.exec()
        self._current_update_dialog = None


        # Clear pending update info
        self.pending_update_info = None

        # In a real implementation, you would restart the application here
        logging.info(f"Application would restart now to apply {channel} version {version}")

        # Simulate restart by closing and reopening
        # QApplication.instance().quit() # This will exit the app
        # For a true restart, need to launch a new process.
        # For now, let's just log and maybe close the window.
        QTimer.singleShot(100, self.restart_application)


    def restart_application(self):
        """Restart the application"""
        try:
            logging.info("Preparing to restart application...")
            # This is a simplified restart. A robust restart involves
            # launching a new instance of the application and exiting the current one.

            # Ensure all cleanup is done
            # self.close() # This might be too soon if exec is running

            q_app = QApplication.instance()
            if q_app:
                # Store restart command if needed (e.g., for a launcher script)
                # For now, we just quit and rely on the OS or user to restart,
                # or a more sophisticated mechanism if implemented.
                logging.info("Application will quit. Please restart manually or implement a launcher.")
                q_app.quit()

                # Attempt to relaunch (this is OS-dependent and can be complex)
                # This is a basic example and might not work perfectly in all environments
                if getattr(sys, 'frozen', False): # PyInstaller
                    executable = sys.executable
                    os.execl(executable, executable, *sys.argv)
                else: # Development
                    python = sys.executable
                    os.execl(python, python, *sys.argv)

        except Exception as e:
            logging.error(f"Error attempting to restart application: {e}")
            self.show_error_message(f"Failed to restart application automatically: {str(e)}. Please restart manually.")
            QApplication.instance().quit() # Ensure exit even if restart fails


    def save_update_channel_preference(self, channel):
        """Save the update channel preference to a settings file"""
        try:
            # Determine settings file path
            if getattr(sys, 'frozen', False):
                # Running in PyInstaller bundle
                base_dir = os.path.dirname(sys.executable)
            else:
                # Running in normal Python environment
                base_dir = os.path.dirname(os.path.abspath(__file__))

            settings_dir = os.path.join(base_dir, "settings")
            os.makedirs(settings_dir, exist_ok=True)

            settings_file = os.path.join(settings_dir, "app_settings.json") # Use JSON for settings

            # Read existing settings
            settings = {}
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r') as f:
                        settings = json.load(f)
                except json.JSONDecodeError:
                    logging.warning(f"Could not decode existing settings file: {settings_file}. Starting fresh.")


            # Update update channel
            settings['update_channel'] = channel

            # Write back all settings
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)


            logging.info(f"Saved update channel preference to {settings_file}")

        except Exception as e:
            logging.error(f"Failed to save update channel preference: {e}")

    def apply_timezone_change(self, timezone):
        """Apply timezone changes throughout the application"""
        try:
            self.app_timezone = timezone
            logging.info(f"Setting application timezone to: {timezone}")

            # Set timezone in environment variable (effects new datetime objects)
            os.environ["TZ"] = timezone
            try:
                # This only works on Unix-like systems, tells C library to re-read TZ
                if hasattr(time, 'tzset'):
                    time.tzset()
            except Exception as e:
                logging.warning(f"Failed to apply timezone with tzset: {e}")

            # Update any time displays in the application
            if hasattr(self.title_bar, 'update_timezone'): # Assuming TitleBar might show time
                self.title_bar.update_timezone(timezone)

            # Update any time displays in cluster view (e.g., event timestamps)
            if hasattr(self.cluster_view, 'update_timezone_dependent_displays'):
                self.cluster_view.update_timezone_dependent_displays(timezone)

            # Update notification screen timestamps
            if hasattr(self.notification_screen, 'refresh_timestamps'):
                self.notification_screen.refresh_timestamps()


            logging.info(f"Applied timezone change to: {timezone}")

            # Save the timezone preference to a settings file
            self.save_timezone_preference(timezone)

        except Exception as e:
            logging.error(f"Error applying timezone change: {e}")
            self.show_error_message(f"Failed to change timezone: {str(e)}")

    def save_timezone_preference(self, timezone):
        """Save the timezone preference to a settings file"""
        try:
            # Determine settings file path
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))

            settings_dir = os.path.join(base_dir, "settings")
            os.makedirs(settings_dir, exist_ok=True)
            settings_file = os.path.join(settings_dir, "app_settings.json") # Use JSON

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
        """Load application settings including timezone and update channel"""
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
                        logging.error(f"Failed to parse settings file: {settings_file}. Using defaults.")
                        settings = {} # Fallback to empty settings

                # Handle timezone setting
                loaded_timezone = settings.get('timezone')
                if loaded_timezone:
                    self.app_timezone = loaded_timezone
                    os.environ["TZ"] = loaded_timezone # Set for current process
                    try:
                        if hasattr(time, 'tzset'): # For Unix-like
                            time.tzset()
                    except Exception as e:
                        logging.warning(f"Failed to apply saved timezone with tzset during load: {e}")
                    logging.info(f"Loaded timezone from settings: {loaded_timezone}")

                    if hasattr(self.preferences_page, 'set_initial_timezone'):
                        self.preferences_page.set_initial_timezone(loaded_timezone)


                # Handle update channel setting
                loaded_channel = settings.get('update_channel', 'Stable') # Default to Stable
                self.update_channel = loaded_channel
                logging.info(f"Loaded update channel from settings: {loaded_channel}")

                if hasattr(self.preferences_page, 'set_initial_update_channel'):
                    self.preferences_page.set_initial_update_channel(loaded_channel)

                # Apply channel-specific behavior post-load
                if loaded_channel == "Alpha":
                    self.apply_alpha_channel_behavior()
                elif loaded_channel == "Beta":
                    self.apply_beta_channel_behavior()
                else:  # Stable
                    self.apply_stable_channel_behavior()
            else:
                logging.info("No settings file found, using default settings (Timezone: System, Channel: Stable)")
                # Set defaults explicitly if file not found
                self.update_channel = "Stable"
                if hasattr(self.preferences_page, 'set_initial_update_channel'):
                    self.preferences_page.set_initial_update_channel("Stable")
                self.apply_stable_channel_behavior()

                # For timezone, could try to get system default or leave as None
                # For now, we don't set os.environ['TZ'] if not in settings to use system default.
                # self.app_timezone = # get system default if desired.

        except Exception as e:
            logging.error(f"Error loading application settings: {e}")


    def update_yaml_editor_font_size(self, font_size):
        """Update font size for all YAML editors"""
        logging.debug(f"MainWindow: Updating YAML editor font size to {font_size}")

        # Update in ClusterView if available
        if hasattr(self, 'cluster_view') and self.cluster_view:
            if hasattr(self.cluster_view, 'update_yaml_editor_font_size'):
                self.cluster_view.update_yaml_editor_font_size(font_size)

        # Find and update all DetailPage instances in the application
        # This is a bit broad, consider a more targeted approach if performance is an issue
        # e.g., maintain a list of active DetailPage instances.
        for widget in QApplication.allWidgets():
            if isinstance(widget, DetailPage) and hasattr(widget, 'update_yaml_font_size'):
                logging.debug(f"Found DetailPage {widget.objectName()}, updating font size to {font_size}")
                widget.update_yaml_font_size(font_size)


    def update_yaml_editor_font_family(self, font_family):
        """Update font family for all YAML editors"""
        logging.debug(f"MainWindow: Updating YAML editor font family to {font_family}")

        if hasattr(self, '_updating_font_family') and self._updating_font_family == font_family:
            return
        self._updating_font_family = font_family

        try:
            if hasattr(self, 'cluster_view') and self.cluster_view:
                if hasattr(self.cluster_view, 'update_yaml_editor_font_family'):
                    self.cluster_view.update_yaml_editor_font_family(font_family)

            for widget in QApplication.allWidgets():
                if isinstance(widget, DetailPage):
                    if hasattr(widget, 'update_yaml_font_family'):
                        logging.debug(f"Found DetailPage {widget.objectName()}, updating font family to {font_family}")
                        widget.update_yaml_font_family(font_family)
                    elif hasattr(widget, 'update_yaml_editor_font_family'): # Fallback for older name
                        widget.update_yaml_editor_font_family(font_family)
        finally:
            delattr(self, '_updating_font_family')


    def update_yaml_editor_line_numbers(self, show_line_numbers):
        """Update line numbers for all YAML editors"""
        logging.debug(f"MainWindow: Updating YAML editor line numbers to {show_line_numbers}")

        if hasattr(self, 'cluster_view') and self.cluster_view:
            if hasattr(self.cluster_view, 'update_yaml_editor_line_numbers'):
                self.cluster_view.update_yaml_editor_line_numbers(show_line_numbers)

        for widget in QApplication.allWidgets():
            if isinstance(widget, DetailPage) and hasattr(widget, 'update_yaml_line_numbers'):
                logging.debug(f"Found DetailPage {widget.objectName()}, updating line numbers to {show_line_numbers}")
                widget.update_yaml_line_numbers(show_line_numbers)


    def update_yaml_editor_tab_size(self, tab_size):
        """Update tab size for all YAML editors"""
        logging.debug(f"MainWindow: Updating YAML editor tab size to {tab_size}")

        if hasattr(self, 'cluster_view') and self.cluster_view:
            if hasattr(self.cluster_view, 'update_yaml_editor_tab_size'):
                self.cluster_view.update_yaml_editor_tab_size(tab_size)

        for widget in QApplication.allWidgets():
            if isinstance(widget, DetailPage) and hasattr(widget, 'update_yaml_tab_size'):
                logging.debug(f"Found DetailPage {widget.objectName()}, updating tab size to {tab_size}")
                widget.update_yaml_tab_size(tab_size)


    def hide_terminal_if_visible(self):
        """Helper method to hide terminal if visible"""
        if (hasattr(self, 'cluster_view') and
                hasattr(self.cluster_view, 'terminal_panel') and
                self.cluster_view.terminal_panel.is_visible):
            self.cluster_view.terminal_panel.hide_terminal()

    def switch_to_home(self):
        """Enhanced switch to home page with detail panel auto-close"""
        logging.debug("Switching to home page...")

        # Close detail panels first
        if hasattr(self, 'cluster_view') and hasattr(self.cluster_view, 'close_any_open_detail_panels'):
            self.cluster_view.close_any_open_detail_panels()

        self.hide_terminal_if_visible()

        if self.stacked_widget.currentWidget() != self.home_page:
            self.previous_page = self.stacked_widget.currentWidget()
            self.stacked_widget.setCurrentWidget(self.home_page)

    def switch_to_preferences(self):
        """Enhanced switch to preferences page with detail panel auto-close"""
        logging.debug("Switching to preferences page...")

        # Close detail panels first
        if hasattr(self, 'cluster_view') and hasattr(self.cluster_view, 'close_any_open_detail_panels'):
            self.cluster_view.close_any_open_detail_panels()

        self.hide_terminal_if_visible()

        if self.stacked_widget.currentWidget() != self.preferences_page:
            self.previous_page = self.stacked_widget.currentWidget()
            self.stacked_widget.setCurrentWidget(self.preferences_page)

    def handle_preferences_back(self):
        """Handle back button from preferences"""
        if self.previous_page and self.previous_page in [self.home_page, self.cluster_view]: # Ensure it's a valid page
            self.stacked_widget.setCurrentWidget(self.previous_page)
        else:
            self.switch_to_home() # Default to home
        self.previous_page = None # Clear after use


    def show_error_message(self, error_message):
        """Display error messages from various components"""
        if self._shutting_down: return # Don't show errors during shutdown

        if not hasattr(self, '_error_shown'):
            self._error_shown = False

        # Prevent multiple error dialogs in rapid succession, unless it's a cluster switch error
        if self._error_shown and not self._is_switching_to_cluster:
            logging.error(f"Suppressed duplicate error dialog: {error_message}")
            return

        self._error_shown = True

        # Use a non-modal QMessageBox if preferred for some errors, but critical usually modal
        QMessageBox.critical(self, "Error", error_message)

        QTimer.singleShot(1000, self._reset_error_flag) # Reset flag after a delay

    def _reset_error_flag(self):
        """Reset the error dialog flag safely"""
        self._error_shown = False

    def handle_page_change(self, index):
        """Enhanced handle page changes in the stacked widget with detail panel auto-close"""
        current_widget = self.stacked_widget.widget(index)
        logging.debug(f"Page changed to: {current_widget.objectName() if hasattr(current_widget, 'objectName') else type(current_widget).__name__}")


        # Close any open detail panels when switching away from cluster view OR to a different main page
        if hasattr(self, 'cluster_view'):
            if current_widget != self.cluster_view: # If new page is NOT cluster view
                logging.debug("Switched away from cluster view, ensuring detail panels are closed.")
                if hasattr(self.cluster_view, 'close_any_open_detail_panels'):
                    self.cluster_view.close_any_open_detail_panels()

            # Also, iterate through all potential DetailPage instances that might be parented to MainWindow directly
            # This is a fallback but ideally DetailPages are managed by their respective views.
            # for child_widget in self.findChildren(DetailPage):
            #    if child_widget.isVisible() and current_widget != self.cluster_view: # or some other condition
            #        logging.debug(f"Closing a top-level DetailPage: {child_widget.objectName()}")
            #        child_widget.close_detail_panel()


        self.hide_terminal_if_visible() # Always hide terminal if not on cluster view (or specific sub-page of it)

        # If we're switching to cluster view, and it has its own stacked widget for sub-pages
        if current_widget == self.cluster_view and hasattr(self.cluster_view, 'stacked_widget'):
            active_cluster_subpage = self.cluster_view.stacked_widget.currentWidget()

            if active_cluster_subpage:
                logging.debug(f"Cluster view active, current sub-page: {active_cluster_subpage.objectName() if hasattr(active_cluster_subpage, 'objectName') else type(active_cluster_subpage).__name__}")
                if hasattr(active_cluster_subpage, 'force_load_data'):
                    active_cluster_subpage.force_load_data()
                elif hasattr(active_cluster_subpage, 'load_data'): # Fallback
                    active_cluster_subpage.load_data()

        # Update title bar context if needed
        if hasattr(self.title_bar, 'update_context'):
            page_name = "Unknown"
            for name, widget_instance in self.pages.items():
                if widget_instance == current_widget:
                    page_name = name
                    break
            self.title_bar.update_context(page_name)


    def update_panel_positions(self):
        """Update positions of panels - called from resize and move events"""
        # Update profile screen position if visible
        if hasattr(self, 'profile_screen') and self.profile_screen.is_visible:
            self.profile_screen.setFixedHeight(self.height()) # Cover full height
            # Position from right edge: self.width() - self.profile_screen.width()
            # Position from top: 0 (assuming title bar handles its own space)
            self.profile_screen.move(self.width() - self.profile_screen.width(), 0)


        # Update terminal position if visible (terminal is part of ClusterView)
        if (hasattr(self, 'cluster_view') and
                hasattr(self.cluster_view, 'terminal_panel') and
                self.cluster_view.terminal_panel.is_visible):
            self.cluster_view.adjust_terminal_position() # ClusterView handles its own terminal positioning

        # Update notification screen position
        if hasattr(self, 'notification_screen') and self.notification_screen.is_visible:
            # Notification screen might have its own logic via update_position or similar
            if hasattr(self.notification_screen, 'update_position'):
                self.notification_screen.update_position()


    def moveEvent(self, event):
        """Handle move event"""
        super().moveEvent(event)
        self.update_panel_positions() # Panels might need repositioning if they are independent windows/widgets

    def closeEvent(self, event):
        """Enhanced close event handling with proper cleanup order"""
        if self._shutting_down: # Already in shutdown sequence
            super().closeEvent(event)
            return

        logging.info("Starting application shutdown sequence...")
        self._shutting_down = True # Set flag

        try:
            # Close any open modal dialogs first (like update dialogs)
            if hasattr(self, '_current_update_dialog') and self._current_update_dialog and self._current_update_dialog.isVisible():
                logging.debug("Closing active update dialog.")
                try:
                    self._current_update_dialog.reject() # Or accept() or close() depending on type
                except Exception as e_diag:
                    logging.warning(f"Error closing update dialog: {e_diag}")
                self._current_update_dialog = None


            # Terminate update checker thread if running
            if hasattr(self, 'update_checker') and self.update_checker and self.update_checker.isRunning():
                logging.debug("Terminating update checker thread.")
                self.update_checker.terminate()
                if not self.update_checker.wait(1000): # Wait max 1 sec
                    logging.warning("Update checker thread did not terminate gracefully.")

            # Step 1: Stop all cluster operations immediately
            logging.debug("Shutting down cluster operations.")
            self.shutdown_cluster_operations()

            # Step 2: Clean up UI components
            logging.debug("Cleaning up UI components.")
            self.cleanup_ui_components()

            # Step 3: Stop all timers and other threads (application-wide)
            logging.debug("Cleaning up timers and threads.")
            self.cleanup_timers_and_threads() # This is a general QTimer sweep

            # Step 4: Call parent close event
            super().closeEvent(event)
            logging.info("Application shutdown completed successfully.")

        except Exception as e:
            logging.error(f"Error during application shutdown: {e}\n{traceback.format_exc()}")
            # Force close even if there are errors, but call parent's method
            super().closeEvent(event) # Ensure Qt part of shutdown happens


    def shutdown_cluster_operations(self):
        """Stop all cluster-related operations immediately"""
        try:
            # Stop cluster connector operations
            if hasattr(self, 'cluster_connector') and self.cluster_connector:
                logging.debug("Stopping cluster connector polling and disconnecting signals.")
                if hasattr(self.cluster_connector, 'stop_polling'):
                    self.cluster_connector.stop_polling()
                if hasattr(self.cluster_connector, '_shutting_down'): # If connector has its own flag
                    self.cluster_connector._shutting_down = True
                self.disconnect_cluster_signals() # Disconnect all signals

            # Stop kubernetes client operations (if home_page.kube_client is the main one)
            if hasattr(self, 'home_page') and hasattr(self.home_page, 'kube_client'):
                kube_client = self.home_page.kube_client
                if kube_client: # Ensure it exists
                    logging.debug("Stopping home page Kubernetes client operations.")
                    if hasattr(kube_client, '_shutting_down'):
                        kube_client._shutting_down = True
                    if hasattr(kube_client, 'stop_metrics_polling'):
                        kube_client.stop_metrics_polling()
                    if hasattr(kube_client, 'stop_issues_polling'):
                        kube_client.stop_issues_polling()
                    # Any other specific cleanup for kube_client

        except Exception as e:
            logging.error(f"Error in shutdown_cluster_operations: {e}")

    def disconnect_cluster_signals(self):
        """Safely disconnect all cluster-related signals from the main connector"""
        if not (hasattr(self, 'cluster_connector') and self.cluster_connector):
            return

        signals_to_disconnect = [
            'connection_started', 'connection_progress', 'connection_complete',
            'cluster_data_loaded', 'node_data_loaded', 'issues_data_loaded',
            'metrics_data_loaded', 'error_occurred'
            # Add any other signals the cluster_connector might have
        ]

        for signal_name in signals_to_disconnect:
            try:
                signal_instance = getattr(self.cluster_connector, signal_name, None)
                if signal_instance and hasattr(signal_instance, 'disconnect'):
                    signal_instance.disconnect()
                    logging.debug(f"Disconnected signal: cluster_connector.{signal_name}")
            except (TypeError, RuntimeError, AttributeError) as e:
                # TypeError if no slots were connected, RuntimeError if object is deleted
                logging.warning(f"Could not disconnect cluster_connector.{signal_name}: {e}")


    def cleanup_ui_components(self):
        """Clean up UI components safely"""
        try:
            # Hide and cleanup cluster view terminal if visible
            if (hasattr(self, 'cluster_view') and
                    hasattr(self.cluster_view, 'terminal_panel')): # Check existence before visibility
                if self.cluster_view.terminal_panel.is_visible: # Now check visibility
                    try:
                        logging.debug("Hiding terminal panel.")
                        self.cluster_view.terminal_panel.hide_terminal() # This should also handle its cleanup
                    except Exception as e_term:
                        logging.error(f"Error hiding terminal: {e_term}")
                # Explicitly call cleanup if terminal has one
                if hasattr(self.cluster_view.terminal_panel, 'cleanup'):
                    self.cluster_view.terminal_panel.cleanup()


            # Hide profile screen if visible
            if hasattr(self, 'profile_screen') and self.profile_screen.is_visible:
                try:
                    logging.debug("Hiding profile screen.")
                    self.profile_screen.hide_profile()
                except Exception as e_prof:
                    logging.error(f"Error hiding profile screen: {e_prof}")

            # Hide notification screen if visible
            if hasattr(self, 'notification_screen') and self.notification_screen.is_visible:
                try:
                    logging.debug("Hiding notification screen.")
                    self.notification_screen.hide_notifications() # Assuming method name
                except Exception as e_notif:
                    logging.error(f"Error hiding notification screen: {e_notif}")


            # Clean up main pages if they have specific cleanup methods
            pages_to_cleanup = [self.home_page, self.cluster_view, self.preferences_page]
            for page in pages_to_cleanup:
                if page and hasattr(page, 'cleanup_on_destroy'): # Standardized name
                    try:
                        logging.debug(f"Cleaning up page: {type(page).__name__}")
                        page.cleanup_on_destroy()
                    except Exception as e_page:
                        logging.error(f"Error cleaning up page {type(page).__name__}: {e_page}")
                # Or specific methods like for preferences_page
                elif page == self.preferences_page and hasattr(page, 'cleanup_timers_and_threads'):
                    try:
                        logging.debug(f"Cleaning up preferences page timers/threads.")
                        page.cleanup_timers_and_threads()
                    except Exception as e_pref_cleanup:
                        logging.error(f"Error cleaning up preferences page specific: {e_pref_cleanup}")


        except Exception as e:
            logging.error(f"Error in cleanup_ui_components: {e}")

    def cleanup_timers_and_threads(self):
        """Clean up all QTimer objects associated with this MainWindow and its direct children."""
        # This is a more targeted approach than gc.get_objects()
        logging.debug("Stopping active QTimers associated with MainWindow and its children.")

        # Find QTimer objects that are children of this MainWindow instance or its main components
        # This avoids stopping timers from unrelated parts of Qt or other libraries.
        # Check self, main_widget, title_bar, stacked_widget, and pages

        potential_timer_parents = [self, self.main_widget, self.title_bar, self.stacked_widget,
                                   self.home_page, self.cluster_view, self.preferences_page,
                                   self.loading_overlay, self.profile_screen, self.notification_screen]
        if hasattr(self, 'cluster_view') and hasattr(self.cluster_view, 'terminal_panel'):
            potential_timer_parents.append(self.cluster_view.terminal_panel)

        timers_stopped = 0
        for parent_obj in potential_timer_parents:
            if parent_obj is None: continue # Skip if a component wasn't initialized

            try:
                child_timers = parent_obj.findChildren(QTimer)
                for timer in child_timers:
                    if timer.isActive():
                        timer.stop()
                        timers_stopped += 1
                        logging.debug(f"Stopped QTimer: {timer.objectName() if timer.objectName() else 'Unnamed Timer'} parented to {type(parent_obj).__name__}")
            except RuntimeError:
                # Parent object might have been deleted if shutdown order is tricky
                logging.warning(f"RuntimeError while finding timers for {type(parent_obj).__name__}, possibly already deleted.")
            except Exception as e_timer_find:
                logging.error(f"Error finding/stopping timers for {type(parent_obj).__name__}: {e_timer_find}")

        logging.info(f"Stopped {timers_stopped} active QTimers.")

        # Regarding QThreads: Proper QThread management involves moving workers to the thread,
        # and then quitting the thread and waiting for it to finish.
        # The update_checker thread is explicitly handled in closeEvent.
        # Other threads should ideally be managed by their creating components.
        # A general QThread.msleep(100) can give some time but isn't a robust solution for all threads.
        logging.debug("Allowing a brief moment for threads to finish if any were missed...")
        QThread.msleep(100) # Brief pause for any other threads to wind down.

def main():
    """Application entry point"""
    # Install the global exception handler
    sys.excepthook = global_exception_handler

    # Initialize resources (e.g., check PyInstaller paths)
    initialize_resources()

    # Log system info
    logging.info(f"Python version: {sys.version}")
    logging.info(f"PyQt version: {qVersion() if hasattr(Qt, 'qVersion') else 'Unknown Qt version'}")
    logging.info(f"Working directory: {os.getcwd()}")
    logging.info(f"Process ID: {os.getpid()}")


    # Initialize application
    logging.info("Creating QApplication")
    app = QApplication(sys.argv)
    # Set global font (can be overridden by specific widgets/styles)
    app.setFont(QFont("Segoe UI", 9)) # Consistent font size
    # Apply global tooltip style (can also be part of AppStyles.MAIN_STYLE if desired)
    app.setStyleSheet(AppStyles.TOOLTIP_STYLE)


    # Set application icon (for window decorations, taskbar in some OS)
    icon_path_ico = resource_path("icons/logoIcon.ico")
    icon_path_png = resource_path("icons/logoIcon.png")
    app_icon_set = False
    if os.path.exists(icon_path_ico):
        app.setWindowIcon(QIcon(icon_path_ico))
        logging.info(f"Application icon set from: {icon_path_ico}")
        app_icon_set = True
    elif os.path.exists(icon_path_png): # Fallback to PNG
        app.setWindowIcon(QIcon(icon_path_png))
        logging.info(f"Application icon set from PNG: {icon_path_png}")
        app_icon_set = True
    else:
        logging.warning(f"Application icon file not found at: {icon_path_ico} or {icon_path_png}")

    # For Windows taskbar icon grouping and appearance
    if sys.platform == 'win32':
        try:
            import ctypes
            app_id = u'Orchestrix.KubernetesManager.1.0'  # Unicode string, arbitrary but unique
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            logging.info(f"Windows AppUserModelID set to: {app_id}")
        except Exception as e_win_appid:
            logging.warning(f"Failed to set Windows taskbar AppUserModelID: {e_win_appid}")

    if hasattr(app, 'setQuitOnLastWindowClosed'):
        app.setQuitOnLastWindowClosed(True) # Default, but good to be explicit

    # Create and show splash screen if available
    splash = None
    try:
        logging.info("Creating splash screen")
        splash = SplashScreen() # Assuming SplashScreen is lightweight
        # Optional: Set window flags for splash if needed (e.g., Qt.WindowStaysOnTopHint)
        splash.show()
        app.processEvents() # Ensure splash is drawn
    except Exception as e_splash:
        logging.error(f"Error creating or showing splash screen: {e_splash}")
        if splash: splash.close() # Clean up if show failed
        splash = None # Ensure it's None if failed


    # Create main window
    window = None # Initialize to None
    try:
        logging.info("Creating main window...")
        window = MainWindow() # This now initializes UI, connects signals etc.

        # Load application settings (timezone, update channel, etc.) AFTER window and its sub-components are created
        logging.info("Loading application settings...")
        window.load_app_settings() # This might affect UI elements, so call before show if possible, or refresh after.

        # Handle splash screen or show window directly
        if splash:
            def show_main_window_after_splash_tasks():
                if window: # Ensure window was created
                    logging.info("Showing main window...")
                    window.show()
                    window.activateWindow() # Bring to front
                    # Optionally, do some quick final checks/updates on window here
                else:
                    logging.critical("Main window is None, cannot show.")

                logging.info("Closing splash screen...")
                if window:
                    # Fix: Check if splash has finish method, otherwise use close
                    if hasattr(splash, 'finish'):
                        splash.finish(window)
                    else:
                        splash.close()
                else:
                    splash.close()

                logging.info("Main window shown successfully (after splash).")

                # Start background update check a bit after window is shown and responsive
                if window:
                    QTimer.singleShot(2500, window.check_for_updates_background)


            # Simulate some loading tasks for the splash screen
            # In a real app, this timer would be replaced by actual initialization steps
            # or splash.start_loading_simulation() could be called
            if hasattr(splash, 'start_loading_simulation'):
                splash.loading_finished.connect(show_main_window_after_splash_tasks)
                splash.start_loading_simulation(3000) # Simulate 3 seconds of loading
            else: # Fallback if splash doesn't have this
                QTimer.singleShot(2000, show_main_window_after_splash_tasks) # Show after 2s if no simulation

        else: # No splash screen
            if window:
                window.show()
                window.activateWindow()
                logging.info("Main window shown directly (no splash).")
                # Start background update check
                QTimer.singleShot(2000, window.check_for_updates_background)
            else:
                logging.critical("Main window is None and no splash, application cannot start UI.")
                return 1 # Exit if window creation failed catastrophically

        # Run the application event loop
        logging.info("Starting application main event loop.")
        exit_code = app.exec()
        logging.info(f"Application event loop finished. Exited with code: {exit_code}")
        return exit_code

    except Exception as e_main_app:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_details = f"[{current_time}] CRITICAL ERROR IN MAIN APPLICATION SETUP:\n{str(e_main_app)}\n{traceback.format_exc()}"
        logging.critical(error_details)

        # Try to show a user-friendly message if GUI components are available
        try:
            if not QApplication.instance(): # If app object wasn't created or died
                critical_app = QApplication(sys.argv) # Minimal app for dialog
                QMessageBox.critical(None, "Fatal Application Error",
                                     f"A critical error occurred during application startup:\n{str(e_main_app)}\n\n"
                                     f"Details have been logged to: {log_file if 'log_file' in locals() else 'application log'}.\n"
                                     "The application will now exit.")
                # critical_app.exec() # Not needed, just show dialog
            else: # App instance exists
                QMessageBox.critical(None, "Fatal Application Error",
                                     f"A critical error prevented the application from starting correctly:\n{str(e_main_app)}\n\n"
                                     f"Details have been logged to: {log_file if 'log_file' in locals() else 'application log'}.\n"
                                     "The application will now exit.")
        except Exception as e_dialog:
            # Fallback if even showing a dialog fails
            fallback_error_file = "orchestrix_ULTRA_CRITICAL_error.log"
            with open(fallback_error_file, "a") as f:
                f.write(f"Failed to show critical error dialog: {str(e_dialog)}\n")
                f.write(error_details + "\n") # Log original error too
            print(f"FATAL: {error_details}\nDialog display failed: {e_dialog}", file=sys.stderr)

        return 1 # Indicate an error exit status
    finally:
        # Ensure any remaining Qt resources are cleaned if app.exec() was not reached or exited early
        # This is tricky; usually app.quit() or exit from exec() handles this.
        # If window was created and shown, its closeEvent should have run if app.exec() was started.
        logging.info("Main function's try-finally block reached.")
        if window and not window.isHidden(): # If window is still around and was shown
            pass # closeEvent should handle cleanup
        # QApplication.quit() # Not always safe here, could be called too early or too late.
        # Rely on Python's exit handling for final cleanup.


if __name__ == "__main__":
    # Ensure the application exits cleanly even if main() itself raises an unhandled exception
    # (though global_exception_handler and main's try/except should catch most)
    exit_status = 1 # Default to error if something goes very wrong
    try:
        exit_status = main()
    except SystemExit as se: # To allow sys.exit() to work as intended
        exit_status = se.code if se.code is not None else 0
        logging.info(f"Application exited via SystemExit with code: {exit_status}")
    except Exception as e_top_level:
        # This is the absolute last resort if something went wrong outside main's try/except
        # or if global_exception_handler somehow failed or was bypassed.
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fatal_error_msg = f"[{current_time}] UNHANDLED FATAL EXCEPTION AT TOP LEVEL:\n{str(e_top_level)}\n{traceback.format_exc()}"
        logging.critical(fatal_error_msg)

        # Try to write to a dedicated fatal error log if logging itself might be compromised
        try:
            if getattr(sys, 'frozen', False): base_dir = os.path.dirname(sys.executable)
            else: base_dir = os.path.dirname(os.path.abspath(__file__))
            fatal_log_path = os.path.join(base_dir, "orchestrix_FATAL_EXECUTION_ERROR.log")
            with open(fatal_log_path, "a") as f:
                f.write(fatal_error_msg + "\n")
            print(f"A fatal unhandled error occurred. Details logged to {fatal_log_path} and standard logs.", file=sys.stderr)
        except Exception as e_log_fatal:
            print(f"FATAL ERROR: {fatal_error_msg}\nALSO FAILED TO WRITE TO FATAL LOG: {e_log_fatal}", file=sys.stderr)

        # Attempt to show a message box as a last effort if Qt can be imported
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if not QApplication.instance():
                app = QApplication(sys.argv) # Create a minimal instance for the dialog
            QMessageBox.critical(None, "Critical Unrecoverable Error",
                                 f"A critical unrecoverable error occurred:\n{str(e_top_level)}\n\n"
                                 "The application must exit. Please check log files for details.")
        except Exception:
            pass # If GUI can't even show this, nothing more can be done visually.

    finally:
        logging.info(f"Exiting application with status code: {exit_status}")
        sys.exit(exit_status)