from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QLineEdit, QTreeWidget, 
                             QTreeWidgetItem, QFrame, QMenu, QHeaderView,
                             QMessageBox)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QPoint, QSize, QTimer
from PyQt6.QtGui import QColor, QPainter, QIcon, QMouseEvent, QFont
import logging

from UI.Styles import AppColors, AppStyles, AppConstants
from utils.kubernetes_client import get_kubernetes_client
from utils.cluster_connector import get_cluster_connector

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
        
        # Connect to client signals
        self.kube_client.clusters_loaded.connect(self.on_clusters_loaded)
        self.kube_client.error_occurred.connect(self.handle_kubernetes_error)
        
        # Connect to connector signals with improved error handling
        self.cluster_connector.connection_started.connect(self.on_cluster_connection_started)
        self.cluster_connector.connection_progress.connect(self.on_cluster_connection_progress)
        self.cluster_connector.connection_complete.connect(self.on_cluster_connection_complete)
        self.cluster_connector.error_occurred.connect(self.handle_cluster_connector_error)
        self.cluster_connector.metrics_data_loaded.connect(self.check_cluster_data_loaded)
        self.cluster_connector.issues_data_loaded.connect(self.check_cluster_data_loaded)
        self.cluster_connector.cluster_data_loaded.connect(self.on_cluster_info_loaded)  # Add this

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
        
        # Track clusters in connection process with timeout
        self.connecting_clusters = set()
        self.waiting_for_cluster_load = None
        self.connection_timeouts = {}  # Track connection timeouts

        self.init_data_model()
        self.setup_ui()
        self.update_content_view("Browse All")
        QTimer.singleShot(100, self.load_kubernetes_clusters)

    def load_kubernetes_clusters(self):
        """Load Kubernetes clusters with error handling"""
        try:
            self.kube_client.load_clusters_async()
        except Exception as e:
            logging.error(f"Failed to load Kubernetes clusters: {e}")
            self.show_error_message(f"Failed to load clusters: {str(e)}")

    def on_clusters_loaded(self, clusters):
        """Handle loaded clusters with improved error handling"""
        try:
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
            
        except Exception as e:
            logging.error(f"Error processing loaded clusters: {e}")
            self.show_error_message(f"Error processing clusters: {str(e)}")

    def check_cluster_data_loaded(self, data):
        """Check if cluster data is fully loaded"""
        try:
            if self.waiting_for_cluster_load:
                cluster_name = self.waiting_for_cluster_load
                
                # Check if we have sufficient data to proceed
                has_complete_data = (hasattr(self.cluster_connector, 'is_data_loaded') and 
                                   self.cluster_connector.is_data_loaded(cluster_name))
                
                has_partial_data = (hasattr(self.cluster_connector, 'get_cached_data') and 
                                  bool(self.cluster_connector.get_cached_data(cluster_name)))
                
                if has_complete_data or has_partial_data:
                    logging.info(f"Data loaded for cluster {cluster_name} (complete: {has_complete_data}, partial: {has_partial_data})")
                    
                    self.waiting_for_cluster_load = None
                    self.connecting_clusters.discard(cluster_name)
                    
                    # Clear any timeout for this cluster since we have data
                    if cluster_name in self.connection_timeouts:
                        self.connection_timeouts[cluster_name].stop()
                        del self.connection_timeouts[cluster_name]
                    
                    # Update status to connected
                    for view_type in self.all_data:
                        for item in self.all_data[view_type]:
                            if item.get("name") == cluster_name:
                                item["status"] = "connected"
                    
                    self.update_content_view(self.current_view)
                    QTimer.singleShot(100, lambda: self.open_cluster_signal.emit(cluster_name))
                    
        except Exception as e:
            logging.error(f"Error checking cluster data loaded: {e}")
            if hasattr(self, 'waiting_for_cluster_load') and self.waiting_for_cluster_load:
                # Only reset on actual errors, not on data loading delays
                cluster_name = self.waiting_for_cluster_load
                if "connection" in str(e).lower() or "authentication" in str(e).lower():
                    self.reset_cluster_connection_state(cluster_name)

    def on_cluster_connection_started(self, cluster_name):
        """Handle cluster connection start with timeout"""
        try:
            logging.info(f"Starting connection to cluster: {cluster_name}")
            self.connecting_clusters.add(cluster_name)
            
            # Set up connection timeout (20 seconds) - shorter, focused on connection only
            timeout_timer = QTimer()
            timeout_timer.setSingleShot(True)
            timeout_timer.timeout.connect(lambda: self.handle_connection_timeout(cluster_name))
            timeout_timer.start(20000)  # 20 seconds timeout for connection
            self.connection_timeouts[cluster_name] = timeout_timer
            
            # Update UI status
            for view_type in self.all_data:
                for item in self.all_data[view_type]:
                    if item.get("name") == cluster_name:
                        item["status"] = "connecting"
            
            self.update_content_view(self.current_view)
            
        except Exception as e:
            logging.error(f"Error handling connection start for {cluster_name}: {e}")
            self.reset_cluster_connection_state(cluster_name)

    def on_cluster_info_loaded(self, cluster_info):
        """Handle when cluster info is loaded - this means we have basic connectivity"""
        try:
            if self.waiting_for_cluster_load:
                cluster_name = self.waiting_for_cluster_load
                logging.info(f"Cluster info loaded for {cluster_name}, proceeding with connection")
                
                # If we have cluster info, that's enough to proceed
                # Metrics and issues can load in the background
                self.waiting_for_cluster_load = None
                self.connecting_clusters.discard(cluster_name)
                
                # Clear any timeout since we have basic data
                if cluster_name in self.connection_timeouts:
                    self.connection_timeouts[cluster_name].stop()
                    del self.connection_timeouts[cluster_name]
                
                # Update status to connected
                for view_type in self.all_data:
                    for item in self.all_data[view_type]:
                        if item.get("name") == cluster_name:
                            item["status"] = "connected"
                
                self.update_content_view(self.current_view)
                QTimer.singleShot(100, lambda: self.open_cluster_signal.emit(cluster_name))
                
        except Exception as e:
            logging.error(f"Error handling cluster info loaded: {e}")

    def on_cluster_connection_progress(self, cluster_name, progress_message):
        """Handle connection progress updates"""
        try:
            logging.info(f"Connection progress for {cluster_name}: {progress_message}")
            # You can add progress indicators here if needed
        except Exception as e:
            logging.error(f"Error handling connection progress for {cluster_name}: {e}")

    def on_cluster_connection_complete(self, cluster_name, success, message):
        """Handle cluster connection completion with improved error handling"""
        try:
            logging.info(f"Connection complete for {cluster_name}: success={success}, message={message}")
            
            # Clear connection timeout (not data loading timeout)
            if cluster_name in self.connection_timeouts:
                self.connection_timeouts[cluster_name].stop()
                del self.connection_timeouts[cluster_name]
            
            if success:
                # Connection successful - update status to loading data
                for view_type in self.all_data:
                    for item in self.all_data[view_type]:
                        if item.get("name") == cluster_name:
                            item["status"] = "loading"
                
                self.waiting_for_cluster_load = cluster_name
                self.update_content_view(self.current_view)
                
                # For successful connections, use a longer timeout for data loading
                # and only timeout if there's a real issue
                data_timeout = QTimer()
                data_timeout.setSingleShot(True)
                data_timeout.timeout.connect(lambda: self.handle_data_loading_timeout(cluster_name))
                data_timeout.start(60000)  # 60 seconds for data loading (much longer)
                self.connection_timeouts[cluster_name] = data_timeout
                
            else:
                # Connection failed - reset to disconnected state
                self.reset_cluster_connection_state(cluster_name)
                self.show_cluster_error(cluster_name, f"Connection failed: {message}")
                
        except Exception as e:
            logging.error(f"Error handling connection complete for {cluster_name}: {e}")
            self.reset_cluster_connection_state(cluster_name)

    def handle_connection_timeout(self, cluster_name):
        """Handle connection timeout"""
        logging.warning(f"Connection timeout for cluster: {cluster_name}")
        self.reset_cluster_connection_state(cluster_name)
        self.show_cluster_error(cluster_name, "Connection timeout. Please check if the cluster is running and accessible.")

    def handle_data_loading_timeout(self, cluster_name):
        """Handle data loading timeout - only if there are actual issues"""
        try:
            logging.warning(f"Data loading timeout check for cluster: {cluster_name}")
            
            # Check if the cluster connector has any actual errors
            if hasattr(self.cluster_connector, 'get_connection_state'):
                connection_state = self.cluster_connector.get_connection_state(cluster_name)
                if connection_state == "failed":
                    # There was an actual error, so timeout is justified
                    self.reset_cluster_connection_state(cluster_name)
                    self.show_cluster_error(cluster_name, "Data loading failed due to cluster errors.")
                    return
            
            # Check if we have any data loaded (partial success)
            if (hasattr(self.cluster_connector, 'get_cached_data') and 
                self.cluster_connector.get_cached_data(cluster_name)):
                # We have some data, so the connection is working, just slow
                # Don't timeout, but stop waiting and proceed anyway
                logging.info(f"Cluster {cluster_name} data loading is slow but working, proceeding anyway")
                
                if self.waiting_for_cluster_load == cluster_name:
                    self.waiting_for_cluster_load = None
                    self.connecting_clusters.discard(cluster_name)
                    
                    # Update status to connected since we have some data
                    for view_type in self.all_data:
                        for item in self.all_data[view_type]:
                            if item.get("name") == cluster_name:
                                item["status"] = "connected"
                    
                    self.update_content_view(self.current_view)
                    QTimer.singleShot(100, lambda: self.open_cluster_signal.emit(cluster_name))
                return
            
            # Only timeout if we truly have no data and the connection seems stuck
            # But be very lenient - give it more time
            logging.info(f"Extending data loading time for cluster: {cluster_name}")
            
            # Extend timeout by another 30 seconds instead of failing immediately
            if cluster_name in self.connection_timeouts:
                extended_timeout = QTimer()
                extended_timeout.setSingleShot(True)
                extended_timeout.timeout.connect(lambda: self.handle_final_data_timeout(cluster_name))
                extended_timeout.start(30000)  # Additional 30 seconds
                
                # Replace the old timeout
                self.connection_timeouts[cluster_name].stop()
                self.connection_timeouts[cluster_name] = extended_timeout
            
        except Exception as e:
            logging.error(f"Error in data loading timeout handler for {cluster_name}: {e}")

    def handle_final_data_timeout(self, cluster_name):
        """Handle final data loading timeout after extension"""
        try:
            logging.warning(f"Final data loading timeout for cluster: {cluster_name}")
            
            # Check one more time if we have any data
            if (hasattr(self.cluster_connector, 'get_cached_data') and 
                self.cluster_connector.get_cached_data(cluster_name)):
                # We have data, proceed anyway
                logging.info(f"Proceeding with partial data for cluster: {cluster_name}")
                
                if self.waiting_for_cluster_load == cluster_name:
                    self.waiting_for_cluster_load = None
                    self.connecting_clusters.discard(cluster_name)
                    
                    for view_type in self.all_data:
                        for item in self.all_data[view_type]:
                            if item.get("name") == cluster_name:
                                item["status"] = "connected"
                    
                    self.update_content_view(self.current_view)
                    QTimer.singleShot(100, lambda: self.open_cluster_signal.emit(cluster_name))
                return
            
            # Truly no data after extended time - now we can timeout
            self.reset_cluster_connection_state(cluster_name)
            self.show_cluster_error(cluster_name, "Cluster data loading took too long. The cluster may be slow to respond.")
            
        except Exception as e:
            logging.error(f"Error in final data timeout handler for {cluster_name}: {e}")
            self.reset_cluster_connection_state(cluster_name)

    def reset_cluster_connection_state(self, cluster_name):
        """Reset cluster connection state to disconnected"""
        try:
            if not cluster_name:
                return
                
            logging.info(f"Resetting connection state for cluster: {cluster_name}")
            
            # Clear from connecting sets
            self.connecting_clusters.discard(cluster_name)
            if self.waiting_for_cluster_load == cluster_name:
                self.waiting_for_cluster_load = None
            
            # Clear timeout
            if cluster_name in self.connection_timeouts:
                self.connection_timeouts[cluster_name].stop()
                del self.connection_timeouts[cluster_name]
            
            # Update status to disconnected
            for view_type in self.all_data:
                for item in self.all_data[view_type]:
                    if item.get("name") == cluster_name:
                        item["status"] = "disconnect"
            
            self.update_content_view(self.current_view)
            
        except Exception as e:
            logging.error(f"Error resetting cluster connection state for {cluster_name}: {e}")

    def show_cluster_error(self, cluster_name, error_message):
        """Show cluster-specific error message"""
        try:
            formatted_message = f"Cluster '{cluster_name}': {error_message}"
            logging.error(formatted_message)
            
            # Show a non-blocking notification instead of a blocking dialog
            QTimer.singleShot(100, lambda: self.show_error_message(formatted_message))
            
        except Exception as e:
            logging.error(f"Error showing cluster error for {cluster_name}: {e}")

    def show_cluster_warning(self, cluster_name, warning_message):
        """Show cluster-specific warning message (less intrusive)"""
        try:
            formatted_message = f"Cluster '{cluster_name}' warning: {warning_message}"
            logging.warning(formatted_message)
            
            # For warnings, just log them - don't show dialogs unless it's critical
            # You could add a notification system here instead of dialogs
            
        except Exception as e:
            logging.error(f"Error showing cluster warning for {cluster_name}: {e}")

    def handle_kubernetes_error(self, error_message):
        """Handle Kubernetes client errors"""
        try:
            logging.error(f"Kubernetes client error: {error_message}")
            # Don't show all kubernetes errors to avoid spamming the user
            # Only show critical errors
            if any(keyword in error_message.lower() for keyword in ['critical', 'fatal', 'config']):
                self.show_error_message(f"Kubernetes Error: {error_message}")
        except Exception as e:
            logging.error(f"Error handling Kubernetes error: {e}")

    def handle_cluster_connector_error(self, error_type, error_message):
        """Handle cluster connector errors with improved categorization"""
        try:
            full_message = f"{error_type}: {error_message}"
            logging.error(f"Cluster connector error: {full_message}")
            
            # Only reset clusters for critical connection errors, not for data loading issues
            critical_errors = ['connection', 'authentication', 'authorization', 'config']
            
            if error_type in critical_errors:
                # Find and reset any connecting clusters only for critical errors
                for cluster_name in list(self.connecting_clusters):
                    self.reset_cluster_connection_state(cluster_name)
                
                # Show user-friendly error message for critical errors
                user_message = self.get_user_friendly_error_message(error_type, error_message)
                self.show_error_message(user_message)
            else:
                # For non-critical errors (like data loading issues), just log them
                # Don't reset connection state or show error dialogs
                logging.warning(f"Non-critical cluster error: {full_message}")
                
                # If it's a data loading error and we're waiting for a cluster, 
                # check if we have partial data and can proceed
                if error_type in ['data_loading', 'metrics', 'issues'] and self.waiting_for_cluster_load:
                    cluster_name = self.waiting_for_cluster_load
                    if (hasattr(self.cluster_connector, 'get_cached_data') and 
                        self.cluster_connector.get_cached_data(cluster_name)):
                        # We have some data, proceed anyway
                        logging.info(f"Proceeding with partial data for {cluster_name} despite {error_type} error")
                        self.check_cluster_data_loaded(None)  # Force check with current data
                    else:
                        # Show as warning, not error
                        self.show_cluster_warning(cluster_name, f"Some data could not be loaded: {error_message}")
                elif error_type in ['kubernetes'] and 'metrics' not in error_message.lower() and 'issues' not in error_message.lower():
                    # Only show kubernetes errors if they're not about metrics/issues
                    user_message = self.get_user_friendly_error_message(error_type, error_message)
                    self.show_cluster_warning("cluster", user_message)
            
        except Exception as e:
            logging.error(f"Error handling cluster connector error: {e}")

    def get_user_friendly_error_message(self, error_type, error_message):
        """Convert technical error messages to user-friendly ones"""
        try:
            if error_type == 'connection':
                if 'refused' in error_message.lower():
                    return "Unable to connect to cluster. Please check if the cluster is running."
                elif 'timeout' in error_message.lower():
                    return "Connection timeout. Please check your network connection."
                elif 'certificate' in error_message.lower():
                    return "Certificate error. Please check cluster certificates."
                else:
                    return f"Connection failed: {error_message}"
            elif error_type == 'authentication':
                return "Authentication failed. Please check your cluster credentials."
            elif error_type == 'authorization':
                return "Access denied. Please check your cluster permissions."
            else:
                return f"Cluster error: {error_message}"
        except Exception:
            return f"An error occurred: {error_message}"

    def show_error_message(self, error_message):
        """Show error message with improved handling"""
        try:
            # Truncate very long error messages
            if len(error_message) > 500:
                error_message = error_message[:500] + "..."
            
            QMessageBox.critical(self, "Error", error_message)
        except Exception as e:
            logging.error(f"Error showing error message: {e}")

    def navigate_to_cluster(self, item):
        """Navigate to cluster with improved error handling and timeout protection"""
        try:
            cluster_name = item["name"]
            cluster_status = item["status"]
            
            logging.info(f"Navigating to cluster: {cluster_name}, status: {cluster_status}")
            
            # Prevent multiple simultaneous connections to the same cluster
            if cluster_status in ["connecting", "loading"]:
                logging.warning(f"Cluster {cluster_name} is already in connecting/loading state")
                return
            
            # If cluster is already connected and data is loaded, navigate directly
            if (hasattr(self.cluster_connector, 'is_data_loaded') and 
                self.cluster_connector.is_data_loaded(cluster_name)):
                logging.info(f"Cluster {cluster_name} data already loaded, navigating directly")
                self.open_cluster_signal.emit(cluster_name)
                return
            
            # Start connection process
            self.start_cluster_connection(cluster_name)
            
        except Exception as e:
            logging.error(f"Error navigating to cluster {item.get('name', 'unknown')}: {e}")
            cluster_name = item.get("name")
            if cluster_name:
                self.reset_cluster_connection_state(cluster_name)
                self.show_cluster_error(cluster_name, f"Navigation error: {str(e)}")

    def start_cluster_connection(self, cluster_name):
        """Start cluster connection with proper state management"""
        try:
            # Update UI to show connecting state
            for view_type in self.all_data:
                for data_item in self.all_data[view_type]:
                    if data_item["name"] == cluster_name:
                        data_item["status"] = "connecting"
            
            self.update_content_view(self.current_view)
            
            # Start connection with a small delay to allow UI update
            QTimer.singleShot(100, lambda: self.initiate_cluster_connection(cluster_name))
            
        except Exception as e:
            logging.error(f"Error starting cluster connection for {cluster_name}: {e}")
            self.reset_cluster_connection_state(cluster_name)

    def initiate_cluster_connection(self, cluster_name):
        """Initiate the actual cluster connection"""
        try:
            self.cluster_connector.connect_to_cluster(cluster_name)
        except Exception as e:
            logging.error(f"Error initiating cluster connection for {cluster_name}: {e}")
            self.reset_cluster_connection_state(cluster_name)
            self.show_cluster_error(cluster_name, f"Failed to initiate connection: {str(e)}")

    def handle_item_single_click(self, item, column):
        """Handle item single click with error handling"""
        try:
            original_name = item.data(0, Qt.ItemDataRole.UserRole)
            original_data = item.data(0, Qt.ItemDataRole.UserRole + 1)
            
            if not original_data:
                return
            
            if "Cluster" in original_data.get("kind", ""):
                self.navigate_to_cluster(original_data)
            else:
                if original_data.get("action"):
                    original_data["action"](original_data)
                    
        except Exception as e:
            logging.error(f"Error handling item click: {e}")

    def handle_connect_item(self, item):
        """Handle connect item action with improved error handling"""
        try:
            original_name = item.data(0, Qt.ItemDataRole.UserRole)
            original_data = item.data(0, Qt.ItemDataRole.UserRole + 1)
            
            if original_data and "Cluster" in original_data["kind"]:
                # Check if already connecting
                if original_name in self.connecting_clusters:
                    logging.warning(f"Cluster {original_name} is already connecting")
                    return
                
                self.start_cluster_connection(original_name)
                
        except Exception as e:
            logging.error(f"Error handling connect item: {e}")
            original_name = item.data(0, Qt.ItemDataRole.UserRole) if item else "unknown"
            self.reset_cluster_connection_state(original_name)

    def handle_disconnect_item(self, item):
        """Handle disconnect item action with improved cleanup"""
        try:
            original_name = item.data(0, Qt.ItemDataRole.UserRole)
            
            # Reset connection state first
            self.reset_cluster_connection_state(original_name)
            
            # Clean up cluster connector data
            if hasattr(self.cluster_connector, 'data_cache') and original_name in self.cluster_connector.data_cache:
                del self.cluster_connector.data_cache[original_name]
            
            if hasattr(self.cluster_connector, 'loading_complete') and original_name in self.cluster_connector.loading_complete:
                del self.cluster_connector.loading_complete[original_name]
            
            # Stop polling if this was the current cluster
            if (hasattr(self.cluster_connector, 'kube_client') and 
                hasattr(self.cluster_connector.kube_client, 'current_cluster') and
                self.cluster_connector.kube_client.current_cluster == original_name):
                self.cluster_connector.stop_polling()
            
            # Call disconnect method if available
            if hasattr(self.cluster_connector, 'disconnect_cluster'):
                self.cluster_connector.disconnect_cluster(original_name)
            
            logging.info(f"Successfully disconnected from cluster: {original_name}")
            
        except Exception as e:
            logging.error(f"Error handling disconnect item: {e}")

    def handle_delete_item(self, item):
        """Handle delete item action with error handling"""
        try:
            original_name = item.data(0, Qt.ItemDataRole.UserRole)
            
            # First disconnect if connected
            self.handle_disconnect_item(item)
            
            # Remove from UI
            index = self.tree_widget.indexOfTopLevelItem(item)
            self.tree_widget.takeTopLevelItem(index)
            
            # Remove from data
            for view_type in self.all_data:
                self.all_data[view_type] = [
                    item for item in self.all_data[view_type]
                    if item["name"] != original_name
                ]
            
            # Update item count
            current_count = len(self.all_data[self.current_view])
            self.items_label.setText(f"{current_count} item{'s' if current_count != 1 else ''}")
            
            logging.info(f"Successfully deleted item: {original_name}")
            
        except Exception as e:
            logging.error(f"Error handling delete item: {e}")

    # Rest of the methods remain the same...
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

        item.setText(1, kind)
        item.setText(2, source)
        item.setText(3, label)

        # Define status colors
        status_colors = {
            "available": AppColors.STATUS_AVAILABLE,
            "active": AppColors.STATUS_ACTIVE,
            "connected": AppColors.STATUS_AVAILABLE,
            "disconnect": AppColors.STATUS_DISCONNECTED,
            "connecting": AppColors.STATUS_WARNING,
            "loading": AppColors.STATUS_WARNING
        }
        
        is_cluster = "Cluster" in kind
        
        # Create column cell for status
        status_widget = QWidget()
        status_widget.setObjectName("statusCell")
        status_widget.setStyleSheet("QWidget#statusCell { background: transparent; }")
        
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
                if status == "available":
                    status_text = "Available"
                elif status == "active" or status == "connected":
                    status_text = "Connected"
                elif status == "disconnect":
                    status_text = "Disconnected"
                else:
                    status_text = status.capitalize()
                status_label = QLabel(status_text)
                status_label.setStyleSheet(f"color: {status_colors.get(status, AppColors.STATUS_DISCONNECTED)}; background: transparent;")
                status_layout.addWidget(status_label)
        else:
            status_text = status
            status_label = QLabel(status_text)
            status_label.setStyleSheet(f"color: {status_colors.get(status, AppColors.STATUS_DISCONNECTED)}; background: transparent;")
            status_layout.addWidget(status_label)
        
        self.tree_widget.setItemWidget(item, 4, status_widget)

        # Create action column
        action_widget = QWidget()
        action_widget.setFixedWidth(AppConstants.SIZES["ACTION_WIDTH"])
        action_widget.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if status in ["connecting", "loading"] and (name in self.connecting_clusters or self.waiting_for_cluster_load == name):
            pass
        else:
            menu_btn = QPushButton("⋮")
            menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            menu_btn.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE)
            menu_btn.setFixedWidth(AppConstants.SIZES["ACTION_WIDTH"])
            menu_btn.setFixedHeight(30)
            menu_btn.setFlat(True)

            menu = QMenu(action_widget)
            menu.setStyleSheet(AppStyles.MENU_STYLE)
            
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
                try:
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
                except Exception as e:
                    logging.error(f"Error in menu action: {e}")

            menu_btn.clicked.connect(show_menu)
            action_layout.addWidget(menu_btn)
        
        self.tree_widget.setItemWidget(item, 5, action_widget)
        item.setSizeHint(5, QSize(AppConstants.SIZES["ACTION_WIDTH"], AppConstants.SIZES["ROW_HEIGHT"]))

        # Add pin/unpin buttons to the "Name" column only for Kubernetes client data
        name_widget = QWidget()
        name_widget.setStyleSheet("background: transparent; padding: 0px; margin: 0px;")
        name_layout = QHBoxLayout(name_widget)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(0)
        name_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        name_label = QLabel(name if not badge_color else item_text)
        font = QFont("Segoe UI", 10)
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        name_label.setFont(font)
        name_label.setStyleSheet("color: #FFFFFF; background: transparent; padding: 0px; margin: 0px;")
        name_layout.addWidget(name_label)

        # Only add pin button if original_data has cluster_data (from kubernetes_client.py)
        if original_data and 'cluster_data' in original_data:
            name_layout.addSpacing(10)
            pin_btn = QPushButton()
            pin_btn.setFixedSize(20, 20)
            pin_icon_path = resource_path("icons/pin.png") if name not in self.pinned_items else resource_path("icons/unpin.png")
            pin_btn.setIcon(QIcon(pin_icon_path))
            pin_btn.setIconSize(QSize(16, 16))
            pin_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background: #3e3e3e;
                }
            """)
            pin_btn.clicked.connect(lambda: self.toggle_pin_item(name))
            name_layout.addWidget(pin_btn)

        self.tree_widget.setItemWidget(item, 0, name_widget)
        item.setSizeHint(0, QSize(0, AppConstants.SIZES["ROW_HEIGHT"]))

    # Initialize remaining methods...
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
            if data_item["name"] == original_name:
                return data_item
        return None

    def handle_open_item(self, item):
        try:
            original_name = item.data(0, Qt.ItemDataRole.UserRole)
            original_data = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if original_data and original_data["action"]:
                original_data["action"](original_data)
        except Exception as e:
            logging.error(f"Error handling open item: {e}")

    def navigate_to_welcome(self, item):
        pass

    def navigate_to_preferences(self, item):
        self.open_preferences_signal.emit()

    def open_web_link(self, item):
        pass

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

    def toggle_pin_item(self, name):
        """Toggle pin/unpin status for an item and update the dropdown"""
        try:
            data_item = self._find_data_item(self.current_view, name)
            if not data_item or 'cluster_data' not in data_item:
                return
            
            if name in self.pinned_items:
                self.pinned_items.remove(name)
                pin_icon = QIcon(resource_path("icons/pin.png"))
            else:
                self.pinned_items.add(name)
                pin_icon = QIcon(resource_path("icons/unpin.png"))

            # Update the UI for all items with this name
            for i in range(self.tree_widget.topLevelItemCount()):
                item = self.tree_widget.topLevelItem(i)
                if item.data(0, Qt.ItemDataRole.UserRole) == name:
                    name_widget = self.tree_widget.itemWidget(item, 0)
                    for child in name_widget.children():
                        if isinstance(child, QPushButton):
                            child.setIcon(pin_icon)
            
            pinned_list = list(self.pinned_items)
            self.update_pinned_items_signal.emit(pinned_list)
            self.update_content_view(self.current_view)
        except Exception as e:
            logging.error(f"Error toggling pin for item {name}: {e}")
            
    def __del__(self):
        """Destructor - ensure cleanup when object is destroyed"""
        try:
            self.cleanup_on_destroy()
        except Exception as e:
            logging.error(f"Error in HomePage destructor: {e}")

    def cleanup_on_destroy(self):
        """Clean up all resources safely"""
        try:
            # Stop all timers
            for cluster_name in list(self.connection_timeouts.keys()):
                try:
                    self.connection_timeouts[cluster_name].stop()
                    del self.connection_timeouts[cluster_name]
                except:
                    pass
            
            # Clear all sets and data
            self.connecting_clusters.clear()
            self.waiting_for_cluster_load = None
            
            # Disconnect signals to prevent issues during destruction
            try:
                if hasattr(self, 'cluster_connector') and self.cluster_connector:
                    self.cluster_connector.connection_started.disconnect()
                    self.cluster_connector.connection_progress.disconnect() 
                    self.cluster_connector.connection_complete.disconnect()
                    self.cluster_connector.error_occurred.disconnect()
                    self.cluster_connector.metrics_data_loaded.disconnect()
                    self.cluster_connector.issues_data_loaded.disconnect()
                    if hasattr(self.cluster_connector, 'cluster_data_loaded'):
                        self.cluster_connector.cluster_data_loaded.disconnect()
            except (TypeError, RuntimeError):
                pass
                
            try:
                if hasattr(self, 'kube_client') and self.kube_client:
                    self.kube_client.clusters_loaded.disconnect()
                    self.kube_client.error_occurred.disconnect()
            except (TypeError, RuntimeError):
                pass
                
            logging.info("HomePage cleanup completed successfully")
            
        except Exception as e:
            logging.error(f"Error in HomePage cleanup: {e}")

    def closeEvent(self, event):
        """Handle close event"""
        try:
            self.cleanup_on_destroy()
            super().closeEvent(event)
        except Exception as e:
            logging.error(f"Error in HomePage closeEvent: {e}")

    def hideEvent(self, event):
        """Handle hide event"""
        try:
            # Stop timers when page is hidden to prevent unnecessary work
            for cluster_name in list(self.connection_timeouts.keys()):
                try:
                    if self.connection_timeouts[cluster_name].isActive():
                        self.connection_timeouts[cluster_name].stop()
                except:
                    pass
            super().hideEvent(event)
        except Exception as e:
            logging.error(f"Error in HomePage hideEvent: {e}")
            
