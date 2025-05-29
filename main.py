# import sys
# import os
# import traceback
# import logging

# # Set up logging first
# try:
#     from log_handler import setup_logging, log_exception
#     log_file = setup_logging()
# except ImportError as e:
#     # Fallback logging setup
#     error_file = "orchestrix_critical_error.log"
#     with open(error_file, "w") as f:
#         f.write(f"CRITICAL IMPORT ERROR: {str(e)}\n")
#         f.write(traceback.format_exc())
#     log_file = error_file
    
#     # Setup basic logging
#     logging.basicConfig(
#         filename=error_file,
#         level=logging.INFO,
#         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#     )

# # Initialize PyQt imports
# try:
#     logging.info("Initializing application...")
#     from PyQt6.QtWidgets import (
#         QApplication, QMainWindow, QWidget, QVBoxLayout, 
#         QStackedWidget, QMessageBox
#     )
#     from PyQt6.QtCore import Qt, QTimer, qVersion
#     from PyQt6.QtGui import QFont, QIcon
    
#     # Import application components
#     from UI.SplashScreen import SplashScreen
#     from Pages.HomePage import OrchestrixGUI
#     from Pages.Preferences import PreferencesWidget
#     from UI.TitleBar import TitleBar
#     from UI.ClusterView import ClusterView
#     from UI.Styles import AppColors, AppStyles
#     from utils.cluster_connector import get_cluster_connector
#     from UI.ProfileScreen import ProfileScreen
#     from UI.NotificationScreen import NotificationScreen
    
#     logging.info("All modules imported successfully")
# except ImportError as e:
#     logging.critical(f"Failed to import application modules: {e}")
#     raise


# def resource_path(relative_path):
#     """Get absolute path to resource, works for dev and for PyInstaller"""
#     try:
#         # PyInstaller creates a temp folder and stores path in _MEIPASS
#         if getattr(sys, 'frozen', False):
#             base_path = sys._MEIPASS
#             full_path = os.path.join(base_path, relative_path)
#             logging.debug(f"Resource path: {full_path}")
#             return full_path
#         else:
#             # Running in normal Python environment
#             base_path = os.path.abspath(".")
#             return os.path.join(base_path, relative_path)
#     except Exception as e:
#         logging.error(f"Error in resource_path for {relative_path}: {e}")
#         return relative_path

# def global_exception_handler(exc_type, exc_value, exc_traceback):
#     """Global handler for uncaught exceptions"""
#     if issubclass(exc_type, KeyboardInterrupt):
#         # Don't catch KeyboardInterrupt
#         sys.__excepthook__(exc_type, exc_value, exc_traceback)
#         return

#     # Log the exception
#     logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
#     # Show user-friendly message if possible, but only once
#     try:
#         if QApplication.instance():
#             # Only show dialog if not already shutting down
#             if not getattr(QApplication.instance(), '_showing_error', False):
#                 QApplication.instance()._showing_error = True
#                 QMessageBox.critical(None, "Error", 
#                                 f"An unexpected error occurred:\n{str(exc_value)}\n\nDetails have been logged to: {log_file}")
#     except Exception:
#         pass

# def initialize_resources():
#     """Initialize resource paths and verify critical resources exist in PyInstaller environment"""
#     if getattr(sys, 'frozen', False):
#         # Running in PyInstaller bundle
#         base_path = sys._MEIPASS
#         logging.info(f"Running as PyInstaller bundle from: {base_path}")
        
#         # Check critical resource directories
#         resource_dirs = ['icons', 'images', 'logos']
#         for dir_name in resource_dirs:
#             dir_path = os.path.join(base_path, dir_name)
#             if os.path.exists(dir_path):
#                 # List first 10 files as a sample
#                 files = os.listdir(dir_path)[:10] 
#                 logging.info(f"✓ Directory {dir_name} found with items: {files}")
                
#                 # Verify some critical files if they should exist
#                 if dir_name == 'icons':
#                     critical_icons = ['logoIcon.png', 'home.svg', 'browse.svg']
#                     for icon in critical_icons:
#                         if os.path.exists(os.path.join(dir_path, icon)):
#                             logging.info(f"  ✓ Critical file found: {icon}")
#                         else:
#                             logging.warning(f"  ✗ Critical file missing: {icon}")
#             else:
#                 logging.error(f"✗ Directory {dir_name} NOT FOUND")
#     else:
#         logging.info("Running in normal Python environment")

# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.previous_page = None
#         self.drag_position = None
#         self._error_shown = False
#         self._shutting_down = False  # Add shutdown flag
        
#         # Set application icon for this window too
#         icon_path = resource_path("icons/logoIcon.ico")
#         if os.path.exists(icon_path):
#             self.setWindowIcon(QIcon(icon_path))
#         else:
#             # Fallback to PNG
#             png_path = resource_path("icons/logoIcon.png")
#             if os.path.exists(png_path):
#                 self.setWindowIcon(QIcon(png_path))
        
#         # Setup window properties first
#         self.setWindowTitle("Orchestrix")
#         self.setMinimumSize(1300, 700)
#         self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
#         self.setStyleSheet(AppStyles.MAIN_STYLE)
        
#         # Initialize cluster connector before UI setup
#         self.cluster_connector = get_cluster_connector()
        
#         # Make sure we are the only component showing error messages
#         if hasattr(self, 'home_page') and hasattr(self.home_page, 'show_error_message'):
#             try:
#                 self.cluster_connector.error_occurred.disconnect(self.home_page.show_error_message)
#             except (TypeError, RuntimeError):
#                 pass  # 
#         # Initialize UI components
#         self.init_ui()
#         self.installEventFilter(self)
        
#         # Pass cluster connector to home page if needed
#         if hasattr(self.home_page, 'initialize_cluster_connector'):
#             self.home_page.initialize_cluster_connector()

#     def init_ui(self):
#         """Initialize all UI components"""
#         # Main widget and layout
#         self.main_widget = QWidget()
#         self.main_layout = QVBoxLayout(self.main_widget)
#         self.main_layout.setContentsMargins(0, 0, 0, 0)
#         self.main_layout.setSpacing(0)
        
#         # Initialize pages
#         self.home_page = OrchestrixGUI()
#         self.title_bar = TitleBar(self, update_pinned_items_signal=self.home_page.update_pinned_items_signal)
#         self.main_layout.addWidget(self.title_bar)
        
#         # Setup stacked widget for page navigation
#         self.stacked_widget = QStackedWidget()
#         self.stacked_widget.currentChanged.connect(self.handle_page_change)
#         self.main_layout.addWidget(self.stacked_widget)
        
#         # Create pages
#         self.cluster_view = ClusterView(self)
#         self.preferences_page = PreferencesWidget()
        
#         # Add pages to stacked widget
#         self.stacked_widget.addWidget(self.home_page)
#         self.stacked_widget.addWidget(self.cluster_view)
#         self.stacked_widget.addWidget(self.preferences_page)
        
#         # Page registry
#         self.pages = {
#             "Home": self.home_page,
#             "Cluster": self.cluster_view,
#             "Preferences": self.preferences_page
#         }
        
#         # Set main widget and default page
#         self.setCentralWidget(self.main_widget)
#         self.stacked_widget.setCurrentWidget(self.home_page)
        
#         # Setup connections and auxiliary panels
#         self.setup_connections()
#         self.setup_profile_screen()
#         self.setup_notification_screen()
    
#     def setup_profile_screen(self):
#         """Set up the profile panel"""
#         self.profile_screen = ProfileScreen(self)
#         if hasattr(self.title_bar, 'profile_btn'):
#             self.title_bar.profile_btn.clicked.connect(self.toggle_profile_screen)
    
#     def toggle_profile_screen(self):
#         """Toggle the profile screen visibility"""
#         if not hasattr(self, 'profile_screen'):
#             return
            
#         if self.profile_screen.is_visible:
#             self.profile_screen.hide_profile()
#         else:
#             # Set user information before showing
#             self.profile_screen.set_user_info(
#                 name="John Doe",
#                 username="johndoe",
#                 email="john.doe@example.com",
#                 organization="Acme Corp",
#                 team="DevOps",
#                 role="Administrator"
#             )
#             self.profile_screen.show_profile()
#             self.profile_screen.raise_()

#     def setup_notification_screen(self):
#         """Set up the notification panel"""
#         self.notification_screen = NotificationScreen(self, self.title_bar.notifications_btn)
#         if hasattr(self.title_bar, 'notifications_btn'):
#             self.title_bar.notifications_btn.clicked.connect(self.toggle_notification_screen)

#     def toggle_notification_screen(self):
#         """Toggle the notification screen visibility"""
#         if hasattr(self, 'notification_screen'):
#             self.notification_screen.toggle_notifications()

#     def setup_connections(self):
#         """Set up signal connections between components"""
#         self.home_page.open_cluster_signal.connect(self.switch_to_cluster_view)
#         self.home_page.open_preferences_signal.connect(self.switch_to_preferences)
#         self.title_bar.home_btn.clicked.connect(self.switch_to_home)
#         self.title_bar.settings_btn.clicked.connect(self.switch_to_preferences)
#         self.preferences_page.back_signal.connect(self.handle_preferences_back)

#         # Connect error signals from cluster connector if available
#         if hasattr(self.cluster_connector, 'error_occurred'):
#             self.cluster_connector.error_occurred.connect(self.show_error_message)

#     def hide_terminal_if_visible(self):
#         """Helper method to hide terminal if visible"""
#         if (hasattr(self, 'cluster_view') and 
#             hasattr(self.cluster_view, 'terminal_panel') and 
#             self.cluster_view.terminal_panel.is_visible):
#             self.cluster_view.terminal_panel.hide_terminal()

#     def switch_to_home(self):
#         """Switch to the home page view"""
#         self.hide_terminal_if_visible()
        
#         if self.stacked_widget.currentWidget() != self.home_page:
#             self.previous_page = self.stacked_widget.currentWidget()
#             self.stacked_widget.setCurrentWidget(self.home_page)

#     def switch_to_cluster_view(self, cluster_name="docker-desktop"):
#         """Switch to the cluster view and set the active cluster"""
#         if self.stacked_widget.currentWidget() != self.cluster_view:
#             self.previous_page = self.stacked_widget.currentWidget()

#         # Check if cluster connector is ready
#         if not hasattr(self, 'cluster_connector') or not self.cluster_connector:
#             self.show_error_message("Cluster connector not initialized.")
#             return

#         # Get cached data if available
#         if (hasattr(self.cluster_connector, 'is_data_loaded') and 
#             self.cluster_connector.is_data_loaded(cluster_name)):
            
#             cached_data = self.cluster_connector.get_cached_data(cluster_name)
            
#             # Pre-populate cluster page with cached data if available
#             if (hasattr(self.cluster_view, 'pages') and 
#                 'Cluster' in self.cluster_view.pages and cached_data):
                
#                 cluster_page = self.cluster_view.pages['Cluster']
#                 if hasattr(cluster_page, 'preload_with_cached_data'):
#                     cluster_page.preload_with_cached_data(
#                         cached_data.get('cluster_info'),
#                         cached_data.get('metrics'),
#                         cached_data.get('issues')
#                     )

#         # Switch to cluster view
#         self.stacked_widget.setCurrentWidget(self.cluster_view)
        
        
#         # Use a single timer for post-switch operations
#         def post_switch_operations():
#             self.cluster_view.set_active_cluster(cluster_name)
            
#             if (hasattr(self.cluster_view, 'terminal_panel') and 
#                 self.cluster_view.terminal_panel.is_visible):
#                 self.cluster_view.adjust_terminal_position()
                
#             # Force page data refresh
#             if hasattr(self.cluster_view, 'handle_page_change'):
#                 self.cluster_view.handle_page_change(
#                     self.cluster_view.stacked_widget.currentWidget())
                
#         # Schedule post-switch operations
#         QTimer.singleShot(100, post_switch_operations)

#     def switch_to_preferences(self):
#         """Switch to the preferences page"""
#         self.hide_terminal_if_visible()
        
#         if self.stacked_widget.currentWidget() != self.preferences_page:
#             self.previous_page = self.stacked_widget.currentWidget()
#             self.stacked_widget.setCurrentWidget(self.preferences_page)

#     def handle_preferences_back(self):
#         """Handle back button from preferences"""
#         if self.previous_page:
#             self.stacked_widget.setCurrentWidget(self.previous_page)
#         else:
#             self.switch_to_home()
    
#     def show_error_message(self, error_message):
#         """Display error messages from various components"""
#         # Use a class attribute to track error dialog state
#         if not hasattr(self, '_error_shown'):
#             self._error_shown = False
        
#         # Prevent multiple error dialogs in rapid succession
#         if self._error_shown:
#             logging.error(f"Suppressed duplicate error dialog: {error_message}")
#             return
            
#         # Set flag to prevent further dialogs
#         self._error_shown = True
        
#         # Show the dialog
#         QMessageBox.critical(self, "Error", error_message)
        
#         # Reset the flag after a delay
#         QTimer.singleShot(1000, self._reset_error_flag)

#     def _reset_error_flag(self):
#         """Reset the error dialog flag safely"""
#         self._error_shown = False

#     def handle_page_change(self, index):
#         """Handle page changes in the stacked widget"""
#         current_widget = self.stacked_widget.widget(index)

#         # Hide terminal panel when not on cluster page
#         self.hide_terminal_if_visible()
        
#         # If we're switching to cluster view, force a page refresh
#         if current_widget == self.cluster_view and hasattr(self.cluster_view, 'stacked_widget'):
#             active_page = self.cluster_view.stacked_widget.currentWidget()
            
#             # Try to load data, preferring force_load_data if available
#             if active_page:
#                 if hasattr(active_page, 'force_load_data'):
#                     active_page.force_load_data()
#                 elif hasattr(active_page, 'load_data'):
#                     active_page.load_data()

#     def update_panel_positions(self):
#         """Update positions of panels - called from resize and move events"""
#         # Update profile screen position if visible
#         if hasattr(self, 'profile_screen') and self.profile_screen.is_visible:
#             self.profile_screen.setFixedHeight(self.height())
#             self.profile_screen.move(self.width() - self.profile_screen.width(), 0)

#         # Update terminal position if visible
#         if (hasattr(self, 'cluster_view') and 
#             hasattr(self.cluster_view, 'terminal_panel') and 
#             self.cluster_view.terminal_panel.is_visible):
#             self.cluster_view.adjust_terminal_position()

#     def resizeEvent(self, event):
#         """Handle resize event"""
#         super().resizeEvent(event)
#         self.update_panel_positions()

#     def moveEvent(self, event):
#         """Handle move event"""
#         super().moveEvent(event)
#         self.update_panel_positions()

#     def closeEvent(self, event):
#         """Enhanced close event handling with proper cleanup order"""
#         try:
#             logging.info("Starting application shutdown sequence...")
            
#             # Set shutdown flag to prevent new operations
#             self._shutting_down = True
            
#             # Step 1: Stop all cluster operations immediately
#             self.shutdown_cluster_operations()
            
#             # Step 2: Clean up UI components
#             self.cleanup_ui_components()
            
#             # Step 3: Stop all timers and threads
#             self.cleanup_timers_and_threads()
            
#             # Step 4: Call parent close event
#             super().closeEvent(event)
            
#             logging.info("Application shutdown completed successfully")
            
#         except Exception as e:
#             logging.error(f"Error during application shutdown: {e}")
#             # Force close even if there are errors
#             super().closeEvent(event)

#     def shutdown_cluster_operations(self):
#         """Stop all cluster-related operations immediately"""
#         try:
#             # Stop cluster connector operations
#             if hasattr(self, 'cluster_connector') and self.cluster_connector:
#                 try:
#                     # Stop polling
#                     if hasattr(self.cluster_connector, 'stop_polling'):
#                         self.cluster_connector.stop_polling()
                    
#                     # Set shutdown flag
#                     if hasattr(self.cluster_connector, '_shutting_down'):
#                         self.cluster_connector._shutting_down = True
                        
#                     # Disconnect all signals to prevent emission to deleted objects
#                     self.disconnect_cluster_signals()
                    
#                 except Exception as e:
#                     logging.error(f"Error stopping cluster connector: {e}")
            
#             # Stop kubernetes client operations  
#             if hasattr(self, 'home_page') and hasattr(self.home_page, 'kube_client'):
#                 try:
#                     kube_client = self.home_page.kube_client
#                     if hasattr(kube_client, '_shutting_down'):
#                         kube_client._shutting_down = True
                        
#                     # Stop any polling timers
#                     if hasattr(kube_client, 'stop_metrics_polling'):
#                         kube_client.stop_metrics_polling()
#                     if hasattr(kube_client, 'stop_issues_polling'):
#                         kube_client.stop_issues_polling()
                        
#                 except Exception as e:
#                     logging.error(f"Error stopping kubernetes client: {e}")
                    
#         except Exception as e:
#             logging.error(f"Error in shutdown_cluster_operations: {e}")

#     def disconnect_cluster_signals(self):
#         """Safely disconnect all cluster-related signals"""
#         try:
#             if hasattr(self, 'cluster_connector') and self.cluster_connector:
#                 signals_to_disconnect = [
#                     'connection_started', 'connection_progress', 'connection_complete',
#                     'cluster_data_loaded', 'node_data_loaded', 'issues_data_loaded', 
#                     'metrics_data_loaded', 'error_occurred'
#                 ]
                
#                 for signal_name in signals_to_disconnect:
#                     try:
#                         signal = getattr(self.cluster_connector, signal_name, None)
#                         if signal:
#                             signal.disconnect()
#                     except (TypeError, RuntimeError, AttributeError):
#                         pass  # Signal already disconnected or doesn't exist
                        
#         except Exception as e:
#             logging.error(f"Error disconnecting cluster signals: {e}")

#     def cleanup_ui_components(self):
#         """Clean up UI components safely"""
#         try:
#             # Hide and cleanup cluster view terminal if visible
#             if (hasattr(self, 'cluster_view') and 
#                 hasattr(self.cluster_view, 'terminal_panel') and 
#                 self.cluster_view.terminal_panel.is_visible):
#                 try:
#                     self.cluster_view.terminal_panel.hide_terminal()
#                 except Exception as e:
#                     logging.error(f"Error hiding terminal: {e}")
            
#             # Hide profile screen if visible
#             if hasattr(self, 'profile_screen') and self.profile_screen.is_visible:
#                 try:
#                     self.profile_screen.hide_profile()
#                 except Exception as e:
#                     logging.error(f"Error hiding profile screen: {e}")
            
#             # Clean up home page
#             if hasattr(self, 'home_page'):
#                 try:
#                     if hasattr(self.home_page, 'cleanup_on_destroy'):
#                         self.home_page.cleanup_on_destroy()
#                 except Exception as e:
#                     logging.error(f"Error cleaning up home page: {e}")
                    
#             # Clean up preferences page
#             if hasattr(self, 'preferences_page'):
#                 try:
#                     if hasattr(self.preferences_page, 'cleanup_timers_and_threads'):
#                         self.preferences_page.cleanup_timers_and_threads()
#                 except Exception as e:
#                     logging.error(f"Error cleaning up preferences page: {e}")
                    
#         except Exception as e:
#             logging.error(f"Error in cleanup_ui_components: {e}")

#     def cleanup_timers_and_threads(self):
#         """Clean up all remaining timers and threads"""
#         try:
#             # Find and stop all QTimer objects
#             import gc
#             from PyQt6.QtCore import QTimer
            
#             for obj in gc.get_objects():
#                 try:
#                     if isinstance(obj, QTimer) and obj.isActive():
#                         obj.stop()
#                 except (RuntimeError, TypeError):
#                     pass  # Object may have been deleted
                    
#             # Give threads time to finish
#             from PyQt6.QtCore import QThread
#             QThread.msleep(100)
            
#         except Exception as e:
#             logging.error(f"Error in cleanup_timers_and_threads: {e}")

# def main():
#     """Application entry point"""
#     # Install the global exception handler
#     sys.excepthook = global_exception_handler
    
#     # Initialize resources
#     initialize_resources()
#     # Log system info
#     logging.info(f"Python version: {sys.version}")
#     logging.info(f"PyQt version: {qVersion() if hasattr(Qt, 'qVersion') else 'Unknown'}")
#     logging.info(f"Working directory: {os.getcwd()}")
    
#     # Log resource paths in PyInstaller mode
#     if getattr(sys, 'frozen', False):
#         logging.info("Running as PyInstaller bundle")
#         try:
#             base_path = sys._MEIPASS
#             logging.info(f"PyInstaller base path: {base_path}")
            
#             # Check critical directories
#             resource_dirs = ['icons', 'images', 'logos']
#             for dir_name in resource_dirs:
#                 dir_path = os.path.join(base_path, dir_name)
#                 if os.path.exists(dir_path):
#                     logging.info(f"Directory {dir_name} found with items: {os.listdir(dir_path)[:5]}")
#                 else:
#                     logging.error(f"Directory {dir_name} NOT FOUND")
#         except Exception as e:
#             logging.error(f"Error checking resource paths: {e}")
    
#     # Initialize application
#     logging.info("Creating QApplication")
#     app = QApplication(sys.argv)
#     app.setFont(QFont("Segoe UI", 10))
#     app.setStyleSheet(AppStyles.TOOLTIP_STYLE)

#     # Set application icon
#     icon_path = resource_path("icons/logoIcon.ico")
#     if os.path.exists(icon_path):
#         app_icon = QIcon(icon_path)
#         app.setWindowIcon(app_icon)
#         logging.info(f"Application icon set from: {icon_path}")
#     else:
#         png_path = resource_path("icons/logoIcon.png")
#         if os.path.exists(png_path):
#             app.setWindowIcon(QIcon(png_path))
#         logging.warning(f"Icon file not found at: {icon_path}")
    
#     # For Windows taskbar icon
#     if sys.platform == 'win32':
#         try:
#             import ctypes
#             app_id = 'Orchestrix.KubernetesManager.1.0'  # Arbitrary string
#             ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
#             logging.info("Windows taskbar app ID set")
#         except Exception as e:
#             logging.warning(f"Failed to set Windows taskbar app ID: {e}")
    
#     if hasattr(app, 'setQuitOnLastWindowClosed'):
#         app.setQuitOnLastWindowClosed(True)
    
#     # Create and show splash screen if available
#     splash = None
#     try:
#         logging.info("Creating splash screen")
#         splash = SplashScreen()
#         splash.show()
#     except Exception as e:
#         logging.error(f"Error creating splash screen: {e}")
    
#     # Create main window
#     try:
#         logging.info("Creating main window")
#         window = MainWindow()
        
#         # Handle splash screen or show window directly
#         if splash:
#             def show_main_window():
#                 window.show()
#                 splash.close()
#                 logging.info("Main window shown successfully")
            
#             splash.finished.connect(show_main_window)
#         else:
#             window.show()
#             logging.info("Main window shown directly (no splash)")
        
#         # Run the application
#         logging.info("Starting application main loop")
#         exit_code = app.exec()
#         logging.info(f"Application exited with code: {exit_code}")
#         return exit_code
        
#     except Exception as e:
#         logging.error(f"Error in main application: {e}")
#         logging.error(traceback.format_exc())
        
#         # Show error dialog if possible
#         try:
#             if QApplication.instance():
#                 QMessageBox.critical(None, "Application Error", 
#                                     f"A critical error occurred:\n{str(e)}\n\nDetails have been logged to: {log_file}")
#         except Exception:
#             pass
            
#         return 1

# if __name__ == "__main__":
#     try:
#         sys.exit(main())
#     except Exception as e:
#         # Last-resort error handling
#         error_msg = f"CRITICAL STARTUP ERROR: {str(e)}"
        
#         try:
#             logging.critical(error_msg)
#             logging.critical(traceback.format_exc())
#         except Exception:
#             # If logging fails, write directly to a file
#             try:
#                 if getattr(sys, 'frozen', False):
#                     base_dir = os.path.dirname(sys.executable)
#                 else:
#                     base_dir = os.path.dirname(os.path.abspath(__file__))
                    
#                 with open(os.path.join(base_dir, "orchestrix_fatal_error.log"), "w") as f:
#                     f.write(f"{error_msg}\n\n")
#                     f.write(traceback.format_exc())
#             except Exception:
#                 print(error_msg, file=sys.__stderr__)
#                 traceback.print_exc(file=sys.__stderr__)
        
#         # Try to show error dialog
#         try:
#             from PyQt6.QtWidgets import QApplication, QMessageBox
#             if not QApplication.instance():
#                 app = QApplication(sys.argv)
#             QMessageBox.critical(None, "Fatal Error", 
#                                 f"{error_msg}\n\nThe application will now exit.")
#         except Exception:
#             pass
            
#         sys.exit(1)


# main.py
import sys
import os
import traceback
import logging

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
    from PyQt6.QtCore import Qt, QTimer, qVersion
    from PyQt6.QtGui import QFont, QIcon
    
    # Import application components
    from UI.SplashScreen import SplashScreen # Assuming SplashScreen has a simple loading text/animation
    from Pages.HomePage import OrchestrixGUI
    from Pages.Preferences import PreferencesWidget
    from UI.TitleBar import TitleBar
    from UI.ClusterView import ClusterView, LoadingOverlay # Import LoadingOverlay from ClusterView
    from UI.Styles import AppColors, AppStyles
    from utils.cluster_connector import get_cluster_connector
    from UI.ProfileScreen import ProfileScreen
    from UI.NotificationScreen import NotificationScreen
    
    logging.info("All modules imported successfully")
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.previous_page = None
        self.drag_position = None
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
                pass  # 
        # Initialize UI components
        self.init_ui() # This will create self.home_page, self.cluster_view etc.
        
        # Central loading overlay for MainWindow
        self.loading_overlay = LoadingOverlay(self) # Using the one from ClusterView.py for consistency
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
                # Disconnect general handler if it was connected before specific one for switch
                self.cluster_connector.error_occurred.disconnect(self.show_error_message)
            except TypeError: pass
            try:
                self.cluster_connector.error_occurred.disconnect(self._on_cluster_connection_error_for_switch)
            except TypeError: pass # Not connected or already disconnected
            self.cluster_connector.error_occurred.connect(self._on_cluster_connection_error_for_switch)
            # Reconnect general handler if desired, or rely on switch-specific handler to show messages
            # self.cluster_connector.error_occurred.connect(self.show_error_message) # Or manage errors contextually


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
                elif hasattr(cluster_page, 'update_cluster_info'): # Fallback
                     cluster_page.update_cluster_info(cached_data.get('cluster_info'))


            def post_switch_operations():
                self.cluster_view.set_active_cluster(loaded_cluster_name)
                if hasattr(self.cluster_view, 'terminal_panel') and self.cluster_view.terminal_panel.is_visible:
                    self.cluster_view.adjust_terminal_position()
                if hasattr(self.cluster_view, 'handle_page_change'):
                    self.cluster_view.handle_page_change(self.cluster_view.stacked_widget.currentWidget())
            
            QTimer.singleShot(50, post_switch_operations)

    def _on_cluster_connection_error_for_switch(self, error_type, error_message):
        # This handler is now connected in __init__
        # It will catch errors during the connection attempt for a switch
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
        # is_data_loaded checks for 'cluster_info', 'metrics', and 'issues'
        # For pre-loading, we might only need 'cluster_info' initially.
        # Let's adjust to check if at least cluster_info is cached.
        cached_cluster_info = None
        if hasattr(self.cluster_connector, 'get_cached_data'):
            cached_data_full = self.cluster_connector.get_cached_data(cluster_name)
            if cached_data_full and 'cluster_info' in cached_data_full:
                 cached_cluster_info = cached_data_full['cluster_info']


        if cached_cluster_info: # If basic info is cached
            logging.info(f"Using cached data for {cluster_name} for initial switch.")
            self.stacked_widget.setCurrentWidget(self.cluster_view)
            
            cluster_page = self.cluster_view.pages.get('Cluster')
            if cluster_page: # Ensure ClusterPage is loaded
                if hasattr(cluster_page, 'preload_with_cached_data'):
                    cluster_page.preload_with_cached_data(
                        cached_data_full.get('cluster_info'),
                        cached_data_full.get('metrics'), # Pass along if available
                        cached_data_full.get('issues')   # Pass along if available
                    )
                elif hasattr(cluster_page, 'update_cluster_info'): # Fallback
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
        self.loading_overlay.resize(self.size()) # Ensure overlay covers the window
        self.loading_overlay.raise_()

        self.cluster_connector.connect_to_cluster(cluster_name)
        # The rest of the switch will happen via signal handlers _on_cluster_connection_complete_for_switch 
        # and _on_initial_cluster_data_ready_for_switch
    
    def resizeEvent(self, event):
        """Handle resize event"""
        super().resizeEvent(event)
        self.update_panel_positions()
        if hasattr(self, 'loading_overlay') and self.loading_overlay.isVisible():
            self.loading_overlay.resize(self.size())


    # ... (rest of MainWindow methods: init_ui, setup_profile_screen, etc. remain unchanged)
    # Ensure to add LoadingOverlay to MainWindow's layout or make it a top-level widget if it's not already.
    # A simple way is to make it a child of main_widget and raise_() it when shown.

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
        self.loading_overlay = LoadingOverlay(self.main_widget) # Make it child of main_widget
        self.loading_overlay.setGeometry(self.main_widget.rect()) # Cover main_widget
        self.loading_overlay.hide() # Initially hidden
        
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

        # Connect error signals from cluster connector if available
        # This general handler might conflict or be redundant with the switch-specific one.
        # Ensure only one appropriate handler is active or they are coordinated.
        # For now, let's ensure the switch-specific error handler is connected and prioritize it.
        # If a general error message is still desired, connect self.show_error_message as well.
        # if hasattr(self.cluster_connector, 'error_occurred'):
        #    self.cluster_connector.error_occurred.connect(self.show_error_message) # General error display

    def hide_terminal_if_visible(self):
        """Helper method to hide terminal if visible"""
        if (hasattr(self, 'cluster_view') and 
            hasattr(self.cluster_view, 'terminal_panel') and 
            self.cluster_view.terminal_panel.is_visible):
            self.cluster_view.terminal_panel.hide_terminal()

    def switch_to_home(self):
        """Switch to the home page view"""
        self.hide_terminal_if_visible()
        
        if self.stacked_widget.currentWidget() != self.home_page:
            self.previous_page = self.stacked_widget.currentWidget()
            self.stacked_widget.setCurrentWidget(self.home_page)

    def switch_to_preferences(self):
        """Switch to the preferences page"""
        self.hide_terminal_if_visible()
        
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
        # Use a class attribute to track error dialog state
        if not hasattr(self, '_error_shown'):
            self._error_shown = False
        
        # Prevent multiple error dialogs in rapid succession
        if self._error_shown and not self._is_switching_to_cluster: # Allow errors during switching
            logging.error(f"Suppressed duplicate error dialog: {error_message}")
            return
            
        # Set flag to prevent further dialogs
        self._error_shown = True
        
        # Show the dialog
        QMessageBox.critical(self, "Error", error_message)
        
        # Reset the flag after a delay
        QTimer.singleShot(1000, self._reset_error_flag)

    def _reset_error_flag(self):
        """Reset the error dialog flag safely"""
        self._error_shown = False

    def handle_page_change(self, index):
        """Handle page changes in the stacked widget"""
        current_widget = self.stacked_widget.widget(index)

        # Hide terminal panel when not on cluster page
        self.hide_terminal_if_visible()
        
        # If we're switching to cluster view, force a page refresh
        if current_widget == self.cluster_view and hasattr(self.cluster_view, 'stacked_widget'):
            active_page = self.cluster_view.stacked_widget.currentWidget()
            
            # Try to load data, preferring force_load_data if available
            if active_page:
                if hasattr(active_page, 'force_load_data'):
                    active_page.force_load_data()
                elif hasattr(active_page, 'load_data'):
                    active_page.load_data()

    def update_panel_positions(self):
        """Update positions of panels - called from resize and move events"""
        # Update profile screen position if visible
        if hasattr(self, 'profile_screen') and self.profile_screen.is_visible:
            self.profile_screen.setFixedHeight(self.height())
            self.profile_screen.move(self.width() - self.profile_screen.width(), 0)

        # Update terminal position if visible
        if (hasattr(self, 'cluster_view') and 
            hasattr(self.cluster_view, 'terminal_panel') and 
            self.cluster_view.terminal_panel.is_visible):
            self.cluster_view.adjust_terminal_position()
            
    def moveEvent(self, event):
        """Handle move event"""
        super().moveEvent(event)
        self.update_panel_positions()

    def closeEvent(self, event):
        """Enhanced close event handling with proper cleanup order"""
        try:
            logging.info("Starting application shutdown sequence...")
            
            # Set shutdown flag to prevent new operations
            self._shutting_down = True
            
            # Step 1: Stop all cluster operations immediately
            self.shutdown_cluster_operations()
            
            # Step 2: Clean up UI components
            self.cleanup_ui_components()
            
            # Step 3: Stop all timers and threads
            self.cleanup_timers_and_threads()
            
            # Step 4: Call parent close event
            super().closeEvent(event)
            
            logging.info("Application shutdown completed successfully")
            
        except Exception as e:
            logging.error(f"Error during application shutdown: {e}")
            # Force close even if there are errors
            super().closeEvent(event)

    def shutdown_cluster_operations(self):
        """Stop all cluster-related operations immediately"""
        try:
            # Stop cluster connector operations
            if hasattr(self, 'cluster_connector') and self.cluster_connector:
                try:
                    # Stop polling
                    if hasattr(self.cluster_connector, 'stop_polling'):
                        self.cluster_connector.stop_polling()
                    
                    # Set shutdown flag
                    if hasattr(self.cluster_connector, '_shutting_down'):
                        self.cluster_connector._shutting_down = True
                        
                    # Disconnect all signals to prevent emission to deleted objects
                    self.disconnect_cluster_signals()
                    
                except Exception as e:
                    logging.error(f"Error stopping cluster connector: {e}")
            
            # Stop kubernetes client operations  
            if hasattr(self, 'home_page') and hasattr(self.home_page, 'kube_client'):
                try:
                    kube_client = self.home_page.kube_client
                    if hasattr(kube_client, '_shutting_down'):
                        kube_client._shutting_down = True
                        
                    # Stop any polling timers
                    if hasattr(kube_client, 'stop_metrics_polling'):
                        kube_client.stop_metrics_polling()
                    if hasattr(kube_client, 'stop_issues_polling'):
                        kube_client.stop_issues_polling()
                        
                except Exception as e:
                    logging.error(f"Error stopping kubernetes client: {e}")
                    
        except Exception as e:
            logging.error(f"Error in shutdown_cluster_operations: {e}")

    def disconnect_cluster_signals(self):
        """Safely disconnect all cluster-related signals"""
        try:
            if hasattr(self, 'cluster_connector') and self.cluster_connector:
                signals_to_disconnect = [
                    'connection_started', 'connection_progress', 'connection_complete',
                    'cluster_data_loaded', 'node_data_loaded', 'issues_data_loaded', 
                    'metrics_data_loaded', 'error_occurred'
                ]
                
                for signal_name in signals_to_disconnect:
                    try:
                        signal = getattr(self.cluster_connector, signal_name, None)
                        if signal:
                            signal.disconnect()
                    except (TypeError, RuntimeError, AttributeError):
                        pass  # Signal already disconnected or doesn't exist
                        
        except Exception as e:
            logging.error(f"Error disconnecting cluster signals: {e}")

    def cleanup_ui_components(self):
        """Clean up UI components safely"""
        try:
            # Hide and cleanup cluster view terminal if visible
            if (hasattr(self, 'cluster_view') and 
                hasattr(self.cluster_view, 'terminal_panel') and 
                self.cluster_view.terminal_panel.is_visible):
                try:
                    self.cluster_view.terminal_panel.hide_terminal()
                except Exception as e:
                    logging.error(f"Error hiding terminal: {e}")
            
            # Hide profile screen if visible
            if hasattr(self, 'profile_screen') and self.profile_screen.is_visible:
                try:
                    self.profile_screen.hide_profile()
                except Exception as e:
                    logging.error(f"Error hiding profile screen: {e}")
            
            # Clean up home page
            if hasattr(self, 'home_page'):
                try:
                    if hasattr(self.home_page, 'cleanup_on_destroy'):
                        self.home_page.cleanup_on_destroy()
                except Exception as e:
                    logging.error(f"Error cleaning up home page: {e}")
                    
            # Clean up preferences page
            if hasattr(self, 'preferences_page'):
                try:
                    if hasattr(self.preferences_page, 'cleanup_timers_and_threads'):
                        self.preferences_page.cleanup_timers_and_threads()
                except Exception as e:
                    logging.error(f"Error cleaning up preferences page: {e}")
                    
        except Exception as e:
            logging.error(f"Error in cleanup_ui_components: {e}")

    def cleanup_timers_and_threads(self):
        """Clean up all remaining timers and threads"""
        try:
            # Find and stop all QTimer objects
            import gc
            from PyQt6.QtCore import QTimer
            
            for obj in gc.get_objects():
                try:
                    if isinstance(obj, QTimer) and obj.isActive():
                        obj.stop()
                except (RuntimeError, TypeError):
                    pass  # Object may have been deleted
                    
            # Give threads time to finish
            from PyQt6.QtCore import QThread
            QThread.msleep(100)
            
        except Exception as e:
            logging.error(f"Error in cleanup_timers_and_threads: {e}")

def main():
    """Application entry point"""
    # Install the global exception handler
    sys.excepthook = global_exception_handler
    
    # Initialize resources
    initialize_resources()
    # Log system info
    logging.info(f"Python version: {sys.version}")
    logging.info(f"PyQt version: {qVersion() if hasattr(Qt, 'qVersion') else 'Unknown'}")
    logging.info(f"Working directory: {os.getcwd()}")
    
    # Log resource paths in PyInstaller mode
    if getattr(sys, 'frozen', False):
        logging.info("Running as PyInstaller bundle")
        try:
            base_path = sys._MEIPASS
            logging.info(f"PyInstaller base path: {base_path}")
            
            # Check critical directories
            resource_dirs = ['icons', 'images', 'logos']
            for dir_name in resource_dirs:
                dir_path = os.path.join(base_path, dir_name)
                if os.path.exists(dir_path):
                    logging.info(f"Directory {dir_name} found with items: {os.listdir(dir_path)[:5]}")
                else:
                    logging.error(f"Directory {dir_name} NOT FOUND")
        except Exception as e:
            logging.error(f"Error checking resource paths: {e}")
    
    # Initialize application
    logging.info("Creating QApplication")
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(AppStyles.TOOLTIP_STYLE)

    # Set application icon
    icon_path = resource_path("icons/logoIcon.ico")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
        logging.info(f"Application icon set from: {icon_path}")
    else:
        png_path = resource_path("icons/logoIcon.png")
        if os.path.exists(png_path):
            app.setWindowIcon(QIcon(png_path))
        logging.warning(f"Icon file not found at: {icon_path}")
    
    # For Windows taskbar icon
    if sys.platform == 'win32':
        try:
            import ctypes
            app_id = 'Orchestrix.KubernetesManager.1.0'  # Arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            logging.info("Windows taskbar app ID set")
        except Exception as e:
            logging.warning(f"Failed to set Windows taskbar app ID: {e}")
    
    if hasattr(app, 'setQuitOnLastWindowClosed'):
        app.setQuitOnLastWindowClosed(True)
    
    # Create and show splash screen if available
    splash = None
    try:
        logging.info("Creating splash screen")
        splash = SplashScreen()
        splash.show()
    except Exception as e:
        logging.error(f"Error creating splash screen: {e}")
    
    # Create main window
    try:
        logging.info("Creating main window")
        window = MainWindow()
        
        # Handle splash screen or show window directly
        if splash:
            def show_main_window():
                window.show()
                splash.close()
                logging.info("Main window shown successfully")
            
            splash.finished.connect(show_main_window)
        else:
            window.show()
            logging.info("Main window shown directly (no splash)")
        
        # Run the application
        logging.info("Starting application main loop")
        exit_code = app.exec()
        logging.info(f"Application exited with code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logging.error(f"Error in main application: {e}")
        logging.error(traceback.format_exc())
        
        # Show error dialog if possible
        try:
            if QApplication.instance():
                QMessageBox.critical(None, "Application Error", 
                                    f"A critical error occurred:\n{str(e)}\n\nDetails have been logged to: {log_file}")
        except Exception:
            pass
            
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # Last-resort error handling
        error_msg = f"CRITICAL STARTUP ERROR: {str(e)}"
        
        try:
            logging.critical(error_msg)
            logging.critical(traceback.format_exc())
        except Exception:
            # If logging fails, write directly to a file
            try:
                if getattr(sys, 'frozen', False):
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    
                with open(os.path.join(base_dir, "orchestrix_fatal_error.log"), "w") as f:
                    f.write(f"{error_msg}\n\n")
                    f.write(traceback.format_exc())
            except Exception:
                print(error_msg, file=sys.__stderr__)
                traceback.print_exc(file=sys.__stderr__)
        
        # Try to show error dialog
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if not QApplication.instance():
                app = QApplication(sys.argv)
            QMessageBox.critical(None, "Fatal Error", 
                                f"{error_msg}\n\nThe application will now exit.")
        except Exception:
            pass
            
        sys.exit(1)