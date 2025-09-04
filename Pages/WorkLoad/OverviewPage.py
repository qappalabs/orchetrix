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
from Utils.kubernetes_client import get_kubernetes_client
from Utils.enhanced_worker import EnhancedBaseWorker
from Utils.thread_manager import get_thread_manager
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
                    logging.info(f"OverviewResourceWorker: Calling list_pod_for_all_namespaces with limit")
                    items = self.kube_client.v1.list_pod_for_all_namespaces(limit=1000)
                    logging.info(f"OverviewResourceWorker: Got {len(items.items) if items and hasattr(items, 'items') else 0} pods")
                else:
                    raise Exception("Kubernetes v1 API not available")
            elif self.resource_type == "deployments":
                if hasattr(self.kube_client, 'apps_v1') and self.kube_client.apps_v1:
                    items = self.kube_client.apps_v1.list_deployment_for_all_namespaces(limit=1000)
                else:
                    raise Exception("Kubernetes apps_v1 API not available")
            elif self.resource_type == "daemonsets":
                if hasattr(self.kube_client, 'apps_v1') and self.kube_client.apps_v1:
                    items = self.kube_client.apps_v1.list_daemon_set_for_all_namespaces(limit=1000)
                else:
                    raise Exception("Kubernetes apps_v1 API not available")
            elif self.resource_type == "statefulsets":
                if hasattr(self.kube_client, 'apps_v1') and self.kube_client.apps_v1:
                    items = self.kube_client.apps_v1.list_stateful_set_for_all_namespaces(limit=1000)
                else:
                    raise Exception("Kubernetes apps_v1 API not available")
            elif self.resource_type == "replicasets":
                if hasattr(self.kube_client, 'apps_v1') and self.kube_client.apps_v1:
                    items = self.kube_client.apps_v1.list_replica_set_for_all_namespaces(limit=1000)
                else:
                    raise Exception("Kubernetes apps_v1 API not available")
            elif self.resource_type == "jobs":
                if hasattr(self.kube_client, 'batch_v1') and self.kube_client.batch_v1:
                    items = self.kube_client.batch_v1.list_job_for_all_namespaces(limit=1000)
                else:
                    raise Exception("Kubernetes batch_v1 API not available")
            elif self.resource_type == "cronjobs":
                if hasattr(self.kube_client, 'batch_v1') and self.kube_client.batch_v1:
                    try:
                        items = self.kube_client.batch_v1.list_cron_job_for_all_namespaces(limit=1000)
                    except (AttributeError, ApiException):
                        if hasattr(self.kube_client, 'batch_v1beta1') and self.kube_client.batch_v1beta1:
                            items = self.kube_client.batch_v1beta1.list_cron_job_for_all_namespaces(limit=1000)
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
        self.running = running if isinstance(running, int) else 0
        
        # Handle progressive display for large datasets
        if isinstance(total, str) and "+" in str(total):
            # Progressive count display (e.g., "1500+")
            self.total = 0  # We don't know the exact total yet
            self.metric_label.setText(f"{running} / {total}")
        else:
            # Final accurate count
            self.total = total if isinstance(total, int) else 0
            self.metric_label.setText(f"{running} / {total}")
        
        # Force a repaint to ensure the update is visible
        self.metric_label.update()
        
        # Use different styling for progressive vs final display
        border_color = self.colors['accent_color'] if "+" in str(total) else self.colors['border_color']
        
        self.card.setStyleSheet(f"""
            QFrame#metricCard {{
                background-color: {self.colors['bg_secondary']};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 0px;
            }}
            QFrame#metricCard:hover {{
                border-color: {self.colors['accent_color']};
            }}
        """)
        
        logging.info(f"MetricCard: Successfully updated {self.resource_type} card display")

    def show_loading(self):
        """Show loading state with spinner indicator."""
        self.metric_label.setText("⏳")
        self.subtitle_label.setText("Loading...")
        self.card.setStyleSheet(f"""
            QFrame#metricCard {{
                background-color: {self.colors['bg_secondary']};
                border: 1px solid {self.colors['accent_color']};
                border-radius: 8px;
                padding: 0px;
            }}
        """)
        self.metric_label.update()
        self.subtitle_label.update()

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
        self._is_loading = False  # Prevent duplicate loading
        self._loading_resources = set()  # Track which resources are being loaded
        
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
            # Refresh every 2 minutes to reduce load on slow Docker Desktop
            self.refresh_timer.start(120000)
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
        
        # Stop any current loading to prevent conflicts
        self._is_loading = False
        self._loading_resources.clear()
        
        # Clear any error states first
        for card in self.metric_cards.values():
            card.show_error_state(False)
        
        # Reinitialize client and fetch data
        if self.initialize_kube_client():
            self.fetch_kubernetes_data()
        else:
            self.show_connection_error("Failed to initialize Kubernetes client")

    def fetch_kubernetes_data(self):
        """Fetch Kubernetes data with progressive async loading to prevent UI freezing."""
        try:
            logging.info("OverviewPage: fetch_kubernetes_data called")
            
            # Simple check to prevent duplicate loading
            if self._is_loading:
                logging.info("OverviewPage: Already loading, skipping duplicate call")
                return
            
            self._is_loading = True
            self._loading_resources.clear()  # Clear any previous loading state
            
            if not self.kube_client:
                if not self.initialize_kube_client():
                    self.show_connection_error("Kubernetes client not initialized")
                    self._is_loading = False
                    return

            if not hasattr(self.kube_client, 'current_cluster') or not self.kube_client.current_cluster:
                self.show_connection_error("No active cluster context")
                self._is_loading = False
                return

            if not hasattr(self.kube_client, 'v1') or not self.kube_client.v1:
                self.show_connection_error("Kubernetes API client not available")
                self._is_loading = False
                return

            logging.info(f"OverviewPage: Starting progressive loading for {len(self.metric_cards)} resource types")
            
            # Show loading indicators on all cards immediately
            for card in self.metric_cards.values():
                card.show_loading()
            
            # Load all resource types immediately without staggering for faster response
            resource_types = list(self.metric_cards.keys())
            for resource_type in resource_types:
                self.load_resource_async(resource_type)
                    
        except Exception as e:
            logging.error(f"Error in fetch_kubernetes_data: {e}")
            self.show_connection_error(f"Error loading data: {str(e)}")
            self._is_loading = False

    def load_resource_async(self, resource_type):
        """Load a specific resource type asynchronously"""
        try:
            # Check if this resource is already being loaded
            if resource_type in self._loading_resources:
                logging.info(f"OverviewPage: {resource_type} already being loaded, skipping")
                return
                
            self._loading_resources.add(resource_type)
            logging.info(f"OverviewPage: Starting load for {resource_type}")
            
            # Use direct optimized loading for faster response and fewer thread issues
            self._load_resource_direct_optimized(resource_type)
                
        except Exception as e:
            logging.error(f"Critical error for {resource_type}: {e}")
            self._loading_resources.discard(resource_type)
            self.handle_resource_error(resource_type, str(e))
    
    def _load_resource_with_timer(self, resource_type):
        """Load resource using QTimer for main-thread async loading"""
        try:
            logging.info(f"OverviewPage: Loading {resource_type} with timer fallback")
            self._load_resource_direct_optimized(resource_type)
        except Exception as e:
            logging.error(f"Timer load failed for {resource_type}: {e}")
            self._loading_resources.discard(resource_type)
            self.handle_resource_error(resource_type, str(e))
    
    def _load_resource_direct_optimized(self, resource_type):
        """Scalable loading optimized for large datasets (1000+ resources)"""
        try:
            if not self.kube_client:
                self.handle_resource_error(resource_type, "No Kubernetes client")
                return
                
            logging.info(f"OverviewPage: Scalable loading {resource_type}")
            
            # For overview page, we only need counts, not full resource details
            # Use efficient pagination to handle 1000+ resources
            batch_size = 500  # Larger batches for efficiency
            all_items = []
            continue_token = None
            total_fetched = 0
            max_total_items = 5000  # Safety limit to prevent memory issues
            
            while total_fetched < max_total_items:
                try:
                    # Fetch batch with continuation token for pagination
                    batch_items = None
                    if resource_type == "pods":
                        batch_items = self.kube_client.v1.list_pod_for_all_namespaces(
                            limit=batch_size, _continue=continue_token)
                    elif resource_type == "deployments":
                        batch_items = self.kube_client.apps_v1.list_deployment_for_all_namespaces(
                            limit=batch_size, _continue=continue_token)
                    elif resource_type == "daemonsets":
                        batch_items = self.kube_client.apps_v1.list_daemon_set_for_all_namespaces(
                            limit=batch_size, _continue=continue_token)
                    elif resource_type == "statefulsets":
                        batch_items = self.kube_client.apps_v1.list_stateful_set_for_all_namespaces(
                            limit=batch_size, _continue=continue_token)
                    elif resource_type == "replicasets":
                        batch_items = self.kube_client.apps_v1.list_replica_set_for_all_namespaces(
                            limit=batch_size, _continue=continue_token)
                    elif resource_type == "jobs":
                        batch_items = self.kube_client.batch_v1.list_job_for_all_namespaces(
                            limit=batch_size, _continue=continue_token)
                    elif resource_type == "cronjobs":
                        try:
                            batch_items = self.kube_client.batch_v1.list_cron_job_for_all_namespaces(
                                limit=batch_size, _continue=continue_token)
                        except (AttributeError, Exception):
                            if hasattr(self.kube_client, 'batch_v1beta1'):
                                batch_items = self.kube_client.batch_v1beta1.list_cron_job_for_all_namespaces(
                                    limit=batch_size, _continue=continue_token)
                    
                    if not batch_items or not hasattr(batch_items, 'items'):
                        break
                    
                    # Add items from this batch
                    if batch_items.items:
                        all_items.extend(batch_items.items)
                        total_fetched += len(batch_items.items)
                        
                        # Update with progressive count for very large datasets
                        if total_fetched > 1000 and total_fetched % 500 == 0:
                            # Show progressive update for large datasets
                            partial_running = self._calculate_running_count(resource_type, all_items)
                            self.update_card_data(resource_type, (partial_running, f"{total_fetched}+"))
                    
                    # Check for continuation token
                    continue_token = getattr(batch_items.metadata, 'continue', None) if hasattr(batch_items, 'metadata') else None
                    if not continue_token:
                        break
                        
                except Exception as e:
                    logging.warning(f"OverviewPage: Batch fetch error for {resource_type}: {e}")
                    break
            
            # Calculate final counts
            total_count = len(all_items)
            running_count = self._calculate_running_count(resource_type, all_items)
            
            # Update card with final accurate data
            self.update_card_data(resource_type, (running_count, total_count))
            self._loading_resources.discard(resource_type)
            
            if total_count >= max_total_items:
                logging.warning(f"OverviewPage: {resource_type} count may be incomplete due to safety limit ({max_total_items})")
            
            logging.info(f"OverviewPage: Completed {resource_type} scalable load: {running_count}/{total_count}")
                
        except Exception as e:
            logging.error(f"OverviewPage: Scalable load failed for {resource_type}: {e}")
            self._loading_resources.discard(resource_type)
            self.handle_resource_error(resource_type, str(e))
    
    def _process_remaining_chunks(self, resource_type, remaining_items, chunk_size, initial_running, total_count):
        """Process remaining items in chunks with timers to prevent UI blocking"""
        if not remaining_items:
            self._loading_resources.discard(resource_type)
            return
            
        # Process next chunk
        chunk = remaining_items[:chunk_size]
        remaining = remaining_items[chunk_size:]
        
        chunk_running = self._calculate_running_count(resource_type, chunk)
        final_running = initial_running + chunk_running
        
        # Update card with more accurate data
        self.update_card_data(resource_type, (final_running, total_count))
        
        # Continue processing remaining chunks
        if remaining:
            QTimer.singleShot(50, lambda: self._process_remaining_chunks(
                resource_type, remaining, chunk_size, final_running, total_count))
        else:
            self._loading_resources.discard(resource_type)
    
    def _calculate_running_count(self, resource_type, items):
        """Calculate running count for a chunk of items"""
        running = 0
        for item in items:
            if not item or not hasattr(item, 'status'):
                continue
                
            status = item.status
            if resource_type == "pods":
                if status and hasattr(status, 'phase') and status.phase == "Running":
                    running += 1
            elif resource_type in ["deployments", "statefulsets", "daemonsets"]:
                if status:
                    available = getattr(status, 'available_replicas', 0) or 0
                    desired = getattr(status, 'replicas', 0) or 0
                    if available == desired and desired > 0:
                        running += 1
            elif resource_type == "replicasets":
                if status:
                    ready = getattr(status, 'ready_replicas', 0) or 0
                    desired = getattr(status, 'replicas', 0) or 0
                    if desired > 0 and ready == desired:
                        running += 1
            elif resource_type == "jobs":
                if status:
                    succeeded = getattr(status, 'succeeded', 0) or 0
                    if succeeded > 0:
                        running += 1
            elif resource_type == "cronjobs":
                if hasattr(item, 'spec') and item.spec:
                    if not getattr(item.spec, 'suspend', False):
                        running += 1
        return running
    
    def _load_resource_direct(self, resource_type):
        """Legacy direct synchronous loading - kept for compatibility"""
        # Redirect to optimized version
        self._load_resource_direct_optimized(resource_type)
        
    def _handle_resource_completed(self, resource_type, data_or_error, is_error):
        """Handle resource loading completion and cleanup loading state"""
        # Remove from loading set
        self._loading_resources.discard(resource_type)
        
        # Check if all resources are done loading
        if not self._loading_resources:
            self._is_loading = False
        
        if is_error:
            self.handle_resource_error(resource_type, data_or_error)
        else:
            self.update_card_data(resource_type, data_or_error)
    
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
            from Utils.kubernetes_client import get_kubernetes_client
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
        
        # Only trigger load if not already loading and no data is visible
        if (self._initialization_complete and not self._is_loading and
            not any(card.running > 0 or card.total > 0 for card in self.metric_cards.values())):
            logging.info("OverviewPage: No data visible on show, triggering immediate load")
            QTimer.singleShot(100, self._force_load_all_data)
    
    def _force_load_all_data(self):
        """Force load all data types directly"""
        logging.info("OverviewPage: Force loading all data types")
        
        # Reset loading state first
        self._is_loading = False
        
        # Load data directly for immediate response
        self.fetch_kubernetes_data()

    def cleanup(self):
        """Cleanup when page is being destroyed."""
        try:
            # Stop the timer first
            if self.refresh_timer:
                self.refresh_timer.stop()
                self.refresh_timer.deleteLater()
                self.refresh_timer = None
            
            # Cancel any ongoing loading
            self._is_loading = False
            self._loading_resources.clear()
            
            # Cancel any pending workers
            try:
                thread_manager = get_thread_manager()
                for resource_type in self.metric_cards.keys():
                    worker_id = f"overview_{resource_type}_{id(self)}"
                    thread_manager.cancel_worker(worker_id)
            except Exception as e:
                logging.error(f"Error canceling workers: {e}")
            
            # Clear references
            self.kube_client = None
            if hasattr(self, 'metric_cards'):
                self.metric_cards.clear()
            
            # Force garbage collection
            import gc
            gc.collect()
            
            logging.info("OverviewPage: Cleanup completed")
            
        except Exception as e:
            logging.error(f"OverviewPage: Error during cleanup: {e}")
    
    def closeEvent(self, event):
        """Handle close event"""
        try:
            self.cleanup()
        except Exception as e:
            logging.error(f"Error in closeEvent: {e}")
        finally:
            if hasattr(super(), 'closeEvent'):
                super().closeEvent(event)
            else:
                event.accept()
    
    def __del__(self):
        """Destructor for additional safety"""
        try:
            self.cleanup()
        except Exception as e:
            logging.error(f"OverviewPage: Error in destructor: {e}")
