"""
Non-blocking implementation of the Overview page with async data loading.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSizePolicy, QScrollArea, QFrame, QPushButton, QApplication
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QObject

from UI.Styles import AppStyles, AppColors
from utils.kubernetes_client import get_kubernetes_client
from utils.enhanced_worker import EnhancedBaseWorker
from utils.thread_manager import get_thread_manager
from kubernetes.client.rest import ApiException
import logging

class OverviewResourceWorker(EnhancedBaseWorker):
    """Async worker for loading overview resource data"""
    
    def __init__(self, resource_type, kube_client):
        super().__init__(f"overview_{resource_type}")
        self.resource_type = resource_type
        self.kube_client = kube_client
        
        # Store callbacks for results
        self._data_callback = None
        self._error_callback = None
    
    def connect_callbacks(self, data_callback, error_callback):
        """Connect callbacks for handling results"""
        self._data_callback = data_callback
        self._error_callback = error_callback
        
        # Connect signals AFTER callbacks are set
        self.signals.finished.connect(self._on_finished)
        self.signals.error.connect(self._on_error)
    
    def _on_finished(self, result):
        """Handle finished signal"""
        logging.info(f"OverviewResourceWorker: Finished signal received for {self.resource_type} with result: {result}")
        if self._data_callback and result is not None:
            logging.info(f"OverviewResourceWorker: Calling data callback for {self.resource_type}")
            try:
                self._data_callback(result)
                logging.info(f"OverviewResourceWorker: Data callback completed for {self.resource_type}")
            except Exception as e:
                logging.error(f"OverviewResourceWorker: Error in data callback for {self.resource_type}: {e}")
        else:
            logging.warning(f"OverviewResourceWorker: No callback or result for {self.resource_type}")
    
    def _on_error(self, error):
        """Handle error signal"""
        logging.error(f"OverviewResourceWorker: Error signal received for {self.resource_type}: {error}")
        if self._error_callback:
            self._error_callback(error)
        
    def execute(self):
        if self.is_cancelled():
            logging.info(f"OverviewResourceWorker: Worker cancelled for {self.resource_type}")
            return None
            
        logging.info(f"OverviewResourceWorker: Executing worker for {self.resource_type}")
        
        try:
            # Add safety check for kube_client
            if not self.kube_client:
                raise Exception("Kubernetes client not available")
            
            # Fetch data based on resource type with proper error handling
            items = None
            logging.info(f"OverviewResourceWorker: Fetching {self.resource_type} data")
            
            if self.resource_type == "pods":
                if hasattr(self.kube_client, 'v1') and self.kube_client.v1:
                    logging.info(f"OverviewResourceWorker: Calling list_pod_for_all_namespaces")
                    items = self.kube_client.v1.list_pod_for_all_namespaces()
                    logging.info(f"OverviewResourceWorker: Got {len(items.items) if items and hasattr(items, 'items') else 0} pods")
                else:
                    raise Exception("Kubernetes v1 API not available")
            elif self.resource_type == "deployments":
                if hasattr(self.kube_client, 'apps_v1') and self.kube_client.apps_v1:
                    items = self.kube_client.apps_v1.list_deployment_for_all_namespaces()
                else:
                    raise Exception("Kubernetes apps_v1 API not available")
            elif self.resource_type == "daemonsets":
                if hasattr(self.kube_client, 'apps_v1') and self.kube_client.apps_v1:
                    items = self.kube_client.apps_v1.list_daemon_set_for_all_namespaces()
                else:
                    raise Exception("Kubernetes apps_v1 API not available")
            elif self.resource_type == "statefulsets":
                if hasattr(self.kube_client, 'apps_v1') and self.kube_client.apps_v1:
                    items = self.kube_client.apps_v1.list_stateful_set_for_all_namespaces()
                else:
                    raise Exception("Kubernetes apps_v1 API not available")
            elif self.resource_type == "replicasets":
                if hasattr(self.kube_client, 'apps_v1') and self.kube_client.apps_v1:
                    items = self.kube_client.apps_v1.list_replica_set_for_all_namespaces()
                else:
                    raise Exception("Kubernetes apps_v1 API not available")
            elif self.resource_type == "jobs":
                if hasattr(self.kube_client, 'batch_v1') and self.kube_client.batch_v1:
                    items = self.kube_client.batch_v1.list_job_for_all_namespaces()
                else:
                    raise Exception("Kubernetes batch_v1 API not available")
            elif self.resource_type == "cronjobs":
                if hasattr(self.kube_client, 'batch_v1') and self.kube_client.batch_v1:
                    try:
                        items = self.kube_client.batch_v1.list_cron_job_for_all_namespaces()
                    except (AttributeError, ApiException):
                        if hasattr(self.kube_client, 'batch_v1beta1') and self.kube_client.batch_v1beta1:
                            items = self.kube_client.batch_v1beta1.list_cron_job_for_all_namespaces()
                        else:
                            raise Exception("CronJob API not available")
                else:
                    raise Exception("Kubernetes batch API not available")
            else:
                raise Exception(f"Unknown resource type: {self.resource_type}")
            
            if not items or not hasattr(items, 'items'):
                logging.warning(f"OverviewResourceWorker: No items returned for {self.resource_type}")
                result = (0, 0)  # Return empty results instead of crashing
                logging.info(f"OverviewResourceWorker: Returning result {result} for {self.resource_type}")
                return result
                
            # Calculate status
            logging.info(f"OverviewResourceWorker: Calculating status for {len(items.items)} {self.resource_type} items")
            running, total = self.calculate_status(items.items)
            result = (running, total)
            logging.info(f"OverviewResourceWorker: Calculated status for {self.resource_type}: {running}/{total}")
            logging.info(f"OverviewResourceWorker: Returning result {result} for {self.resource_type}")
            return result
            
        except Exception as e:
            logging.error(f"OverviewResourceWorker error for {self.resource_type}: {e}")
            raise e  # Let the base worker handle the error
            
    def calculate_status(self, items):
        """Calculate running/total status for resource type"""
        if not items:
            return 0, 0

        running = 0
        total = len(items)

        for item in items:
            status = item.status if hasattr(item, 'status') and item.status else None

            if self.resource_type == "pods":
                if status and hasattr(status, 'phase'):
                    if status.phase == "Running":
                        running += 1

            elif self.resource_type in ["deployments", "statefulsets", "daemonsets"]:
                if status:
                    available = getattr(status, 'available_replicas', 0) or 0
                    desired = getattr(status, 'replicas', 0) or 0
                    if available == desired and desired > 0:
                        running += 1

            elif self.resource_type == "replicasets":
                if status:
                    ready = getattr(status, 'ready_replicas', 0) or 0
                    desired = getattr(status, 'replicas', 0) or 0
                    if desired > 0 and ready == desired:
                        running += 1
                    elif desired == 0:
                        total -= 1  # Don't count scaled-down replicasets

            elif self.resource_type == "jobs":
                if status:
                    succeeded = getattr(status, 'succeeded', 0) or 0
                    if succeeded > 0:
                        running += 1

            elif self.resource_type == "cronjobs":
                # CronJobs are considered "running" if they exist and are not suspended
                if hasattr(item, 'spec') and item.spec:
                    if not getattr(item.spec, 'suspend', False):
                        running += 1

        return running, total


class MetricCard(QWidget):
    """Simplified metric card without progress bar and view button."""
    def __init__(self, title, resource_type):
        super().__init__()
        self.resource_type = resource_type
        self.running = 0
        self.total = 0

        # Define colors with fallbacks
        self.colors = {
            'text_primary': getattr(AppColors, 'TEXT_LIGHT', '#ffffff'),
            'text_secondary': getattr(AppColors, 'TEXT_SECONDARY', '#8b8b8b'),
            'bg_secondary': getattr(AppColors, 'BG_SIDEBAR', '#2a2a2a'),
            'border_color': getattr(AppColors, 'BORDER_COLOR', '#404040'),
            'accent_color': '#FF5733',
        }

        self.setup_ui(title)

    def setup_ui(self, title):
        """Set up the simplified metric card UI."""
        # Main container
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Card frame
        self.card = QFrame()
        self.card.setObjectName("metricCard")
        self.card.setStyleSheet(f"""
            QFrame#metricCard {{
                background-color: {self.colors['bg_secondary']};
                border: 1px solid {self.colors['border_color']};
                border-radius: 8px;
                padding: 0px;
            }}
            QFrame#metricCard:hover {{
                border-color: {self.colors['accent_color']};
            }}
        """)

        # Card content layout
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        # Title
        self.title_label = QLabel(title)
        title_font = QFont()
        title_font.setFamily("Segoe UI")
        title_font.setPointSize(14)
        title_font.setWeight(QFont.Weight.Medium)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['text_primary']};
                background-color: transparent;
                border: none;
                margin: 0px;
            }}
        """)
        card_layout.addWidget(self.title_label)

        # Main metric display
        self.metric_label = QLabel("0 / 0")
        metric_font = QFont()
        metric_font.setFamily("Segoe UI")
        metric_font.setPointSize(32)
        metric_font.setWeight(QFont.Weight.Bold)
        self.metric_label.setFont(metric_font)
        self.metric_label.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['text_primary']};
                background-color: transparent;
                border: none;
                margin: 8px 0px;
            }}
        """)
        self.metric_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        card_layout.addWidget(self.metric_label)

        # Subtitle
        self.subtitle_label = QLabel(f"Running / Total {title}")
        subtitle_font = QFont()
        subtitle_font.setFamily("Segoe UI")
        subtitle_font.setPointSize(10)
        self.subtitle_label.setFont(subtitle_font)
        self.subtitle_label.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['text_secondary']};
                background-color: transparent;
                border: none;
                margin: 0px;
            }}
        """)
        card_layout.addWidget(self.subtitle_label)

        main_layout.addWidget(self.card)

    def update_data(self, running, total):
        """Update the card with new data."""
        logging.info(f"MetricCard: Updating {self.resource_type} card with data: {running}/{total}")
        self.running = running
        self.total = total
        self.metric_label.setText(f"{running} / {total}")
        
        # Force a repaint to ensure the update is visible
        self.metric_label.update()
        
        self.card.setStyleSheet(f"""
            QFrame#metricCard {{
                background-color: {self.colors['bg_secondary']};
                border: 1px solid {self.colors['border_color']};
                border-radius: 8px;
                padding: 0px;
            }}
            QFrame#metricCard:hover {{
                border-color: {self.colors['accent_color']};
            }}
        """)
        
        logging.info(f"MetricCard: Successfully updated {self.resource_type} card display")

    def show_error_state(self, show_error, error_message=""):
        """Show error state on the card."""
        if show_error:
            self.metric_label.setText("Error")
            self.subtitle_label.setText(error_message)
            self.card.setStyleSheet(f"""
                QFrame#metricCard {{
                    background-color: {self.colors['bg_secondary']};
                    border: 1px solid #ff4444;
                    border-radius: 8px;
                    padding: 0px;
                }}
            """)
        else:
            # Clear error state and show data
            self.metric_label.setText(f"{self.running} / {self.total}")
            self.subtitle_label.setText(f"Running / Total {self.resource_type.title()}")
            self.card.setStyleSheet(f"""
                QFrame#metricCard {{
                    background-color: {self.colors['bg_secondary']};
                    border: 1px solid {self.colors['border_color']};
                    border-radius: 8px;
                    padding: 0px;
                }}
                QFrame#metricCard:hover {{
                    border-color: {self.colors['accent_color']};
                }}
            """)


class OverviewPage(QWidget):
    """Overview page showing workload metrics with async data loading."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.metric_cards = {}
        self.kube_client = None
        self.refresh_timer = None
        self._initialization_complete = False
        
        try:
            self.setup_ui()
            
            # Initialize kubernetes client
            if self.initialize_kube_client():
                # Set up auto-refresh with much longer interval to reduce load
                self.setup_refresh_timer()
                
                # Initial data load - ensure it's called from main thread with optimized delay
                if self.thread() == QApplication.instance().thread():
                    QTimer.singleShot(1000, self._safe_initial_load)  # Optimized delay for faster loading
                else:
                    # Use metaObject to invoke on main thread
                    from PyQt6.QtCore import QMetaObject
                    QMetaObject.invokeMethod(self, "_safe_initial_load", Qt.ConnectionType.QueuedConnection)
            else:
                # Show error state if client initialization failed
                QTimer.singleShot(500, lambda: self.show_connection_error("Failed to initialize Kubernetes client"))
                
            self._initialization_complete = True
            
        except Exception as e:
            logging.error(f"OverviewPage initialization error: {e}")
            self.show_connection_error(f"Initialization failed: {str(e)}")
    
    def _safe_initial_load(self):
        """Safely perform initial data load"""
        try:
            if self._initialization_complete and self.kube_client:
                logging.info("OverviewPage: Starting initial data load")
                self.fetch_kubernetes_data()
            else:
                logging.warning("OverviewPage: Skipping initial load - not properly initialized")
                # Try to reinitialize the client
                if self.initialize_kube_client():
                    logging.info("OverviewPage: Reinitialized client, trying data load")
                    self.fetch_kubernetes_data()
        except Exception as e:
            logging.error(f"OverviewPage: Error in initial data load: {e}")
            self.show_connection_error(f"Initial load failed: {str(e)}")
        
    def setup_refresh_timer(self):
        """Set up the refresh timer for periodic updates."""
        # Ensure timer is created on main thread
        if self.thread() == QApplication.instance().thread():
            self.refresh_timer = QTimer(self)  # Set parent to ensure proper cleanup
            self.refresh_timer.timeout.connect(self.refresh_data)
            # Refresh every 30 seconds for better data freshness
            self.refresh_timer.start(30000)
        else:
            logging.warning("OverviewPage: Timer setup called from non-main thread")

    def setup_ui(self):
        """Set up the main UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Page title
        title_label = QLabel("Workload Overview")
        title_font = QFont()
        title_font.setFamily("Segoe UI")
        title_font.setPointSize(28)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {getattr(AppColors, 'TEXT_LIGHT', '#ffffff')};
                background-color: transparent;
                border: none;
                margin: 24px 0px 32px 0px;
                padding: 0px 24px;
            }}
        """)
        main_layout.addWidget(title_label)

        # Cards container
        cards_container = QWidget()
        cards_layout = QVBoxLayout(cards_container)
        cards_layout.setContentsMargins(24, 0, 24, 24)
        cards_layout.setSpacing(24)

        # First row (4 cards)
        first_row = QWidget()
        first_row_layout = QHBoxLayout(first_row)
        first_row_layout.setSpacing(20)
        first_row_layout.setContentsMargins(0, 0, 0, 0)

        card_configs = [
            ("Pods", "pods"),
            ("Deployments", "deployments"),
            ("Daemon Sets", "daemonsets"),
            ("Stateful Sets", "statefulsets")
        ]

        for title, resource_type in card_configs:
            card = MetricCard(title, resource_type)
            # Set fixed size policy and size
            card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            card.setFixedSize(280, 180)
            first_row_layout.addWidget(card)
            self.metric_cards[resource_type] = card

        # Add stretch to center the cards
        first_row_layout.addStretch()

        # Second row (3 cards)
        second_row = QWidget()
        second_row_layout = QHBoxLayout(second_row)
        second_row_layout.setSpacing(20)
        second_row_layout.setContentsMargins(0, 0, 0, 0)

        remaining_configs = [
            ("Replica Sets", "replicasets"),
            ("Jobs", "jobs"),
            ("Cron Jobs", "cronjobs")
        ]

        for title, resource_type in remaining_configs:
            card = MetricCard(title, resource_type)
            # Set fixed size policy and size
            card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            card.setFixedSize(280, 180)
            second_row_layout.addWidget(card)
            self.metric_cards[resource_type] = card

        # Add stretch to balance second row
        second_row_layout.addStretch()

        # Add rows to cards layout
        cards_layout.addWidget(first_row)
        cards_layout.addWidget(second_row)
        cards_layout.addStretch()

        # Scroll area with proper styling
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(cards_container)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        """)

        main_layout.addWidget(scroll_area)

    def refresh_data(self):
        """Refresh all resource data (called by timer)."""
        self.fetch_kubernetes_data()

    def force_load_data(self):
        """Force reload data when refresh button is clicked."""
        logging.info("OverviewPage: Force loading data requested")
        
        # Clear any error states first
        for card in self.metric_cards.values():
            card.show_error_state(False)
        
        # Reinitialize client and fetch data
        if self.initialize_kube_client():
            self.fetch_kubernetes_data()
        else:
            self.show_connection_error("Failed to initialize Kubernetes client")

    def fetch_kubernetes_data(self):
        """Fetch actual Kubernetes data using async workers."""
        try:
            logging.info("OverviewPage: fetch_kubernetes_data called")
            
            if not self.kube_client:
                logging.warning("OverviewPage: Kubernetes client not initialized, trying to reinitialize")
                if not self.initialize_kube_client():
                    self.show_connection_error("Kubernetes client not initialized")
                    return

            if not hasattr(self.kube_client, 'current_cluster') or not self.kube_client.current_cluster:
                logging.warning("OverviewPage: No active cluster context")
                self.show_connection_error("No active cluster context")
                return

            # Check if basic API clients are available
            if not hasattr(self.kube_client, 'v1') or not self.kube_client.v1:
                logging.warning("OverviewPage: Kubernetes API client not available")
                self.show_connection_error("Kubernetes API client not available")
                return

            logging.info(f"OverviewPage: Loading data for {len(self.metric_cards)} resource types")
            
            # Load data asynchronously for each resource type
            for resource_type in self.metric_cards.keys():
                try:
                    logging.info(f"OverviewPage: Loading {resource_type}")
                    self.load_resource_async(resource_type)
                except Exception as e:
                    logging.error(f"Error loading {resource_type}: {e}")
                    self.handle_resource_error(resource_type, str(e))
                    
        except Exception as e:
            logging.error(f"Error in fetch_kubernetes_data: {e}")
            self.show_connection_error(f"Error loading data: {str(e)}")

    def load_resource_async(self, resource_type):
        """Load a specific resource type asynchronously"""
        try:
            logging.info(f"OverviewPage: Creating worker for {resource_type}")
            worker = OverviewResourceWorker(resource_type, self.kube_client)
            
            # Set up callbacks
            worker.connect_callbacks(
                lambda data, rtype=resource_type: self.update_card_data(rtype, data),
                lambda error, rtype=resource_type: self.handle_resource_error(rtype, error)
            )
            
            # Submit to thread manager with proper worker_id
            thread_manager = get_thread_manager()
            worker_id = f"overview_{resource_type}_{id(self)}"
            logging.info(f"OverviewPage: Submitting worker {worker_id} for {resource_type}")
            success = thread_manager.submit_worker(worker_id, worker)
            
            if not success:
                logging.error(f"Failed to submit worker for {resource_type}, trying direct load")
                # Fallback: try direct synchronous loading
                self._load_resource_direct(resource_type)
            else:
                logging.info(f"OverviewPage: Successfully submitted worker for {resource_type}")
                
        except Exception as e:
            logging.error(f"Error creating worker for {resource_type}: {e}, trying direct load")
            # Fallback: try direct synchronous loading
            self._load_resource_direct(resource_type)
    
    def _load_resource_direct(self, resource_type):
        """Direct synchronous loading as fallback"""
        try:
            logging.info(f"OverviewPage: Direct loading {resource_type}")
            worker = OverviewResourceWorker(resource_type, self.kube_client)
            result = worker.execute()
            if result is not None:
                logging.info(f"OverviewPage: Direct load successful for {resource_type}: {result}")
                self.update_card_data(resource_type, result)
            else:
                logging.warning(f"OverviewPage: Direct load returned None for {resource_type}")
                self.handle_resource_error(resource_type, "No data returned")
        except Exception as e:
            logging.error(f"OverviewPage: Direct load failed for {resource_type}: {e}")
            self.handle_resource_error(resource_type, str(e))
        
    def update_card_data(self, resource_type, data):
        """Update card with loaded data"""
        if resource_type in self.metric_cards:
            running_count, total_count = data
            logging.info(f"OverviewPage: Updating {resource_type} with data: {running_count}/{total_count}")
            self.metric_cards[resource_type].update_data(running_count, total_count)
            # Clear any error state when we get real data
            self.metric_cards[resource_type].show_error_state(False)
            logging.info(f"OverviewPage: Successfully updated {resource_type}: {running_count}/{total_count}")
        else:
            logging.warning(f"OverviewPage: No metric card found for {resource_type}")
            
    def handle_resource_error(self, resource_type, error):
        """Handle error loading resource data"""
        if resource_type in self.metric_cards:
            self.metric_cards[resource_type].show_error_state(True, f"Error: {error}")
            logging.error(f"Error loading {resource_type}: {error}")

    def show_connection_error(self, error_message):
        """Show connection error on all cards."""
        for card in self.metric_cards.values():
            card.show_error_state(True, error_message)

    def initialize_kube_client(self):
        """Initialize or update the Kubernetes client."""
        try:
            from utils.kubernetes_client import get_kubernetes_client
            self.kube_client = get_kubernetes_client()
            if self.kube_client and hasattr(self.kube_client, 'current_cluster'):
                logging.info(f"OverviewPage: Kubernetes client initialized for cluster: {self.kube_client.current_cluster}")
                return True
            else:
                logging.warning("OverviewPage: Kubernetes client not properly initialized")
                self.kube_client = None
                return False
        except Exception as e:
            logging.error(f"OverviewPage: Failed to initialize Kubernetes client: {e}")
            self.kube_client = None
            return False

    def showEvent(self, event):
        """Handle show event - trigger immediate data load if needed"""
        super().showEvent(event)
        
        # If we don't have data yet and it's been a while since initialization, try loading
        if (self._initialization_complete and 
            not any(card.running > 0 or card.total > 0 for card in self.metric_cards.values())):
            logging.info("OverviewPage: No data visible on show, triggering immediate load")
            QTimer.singleShot(100, self._force_load_all_data)
    
    def _force_load_all_data(self):
        """Force load all data types directly"""
        logging.info("OverviewPage: Force loading all data types")
        for resource_type in self.metric_cards.keys():
            self._load_resource_direct(resource_type)

    def cleanup(self):
        """Cleanup when page is being destroyed."""
        if self.refresh_timer:
            self.refresh_timer.stop()