"""
Non-blocking implementation of the Overview page with async data loading.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSizePolicy, QScrollArea, QFrame, QPushButton, QApplication
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QObject, QThread

from UI.Styles import AppStyles, AppColors
from Utils.kubernetes_client import get_kubernetes_client
from Utils.enhanced_worker import EnhancedBaseWorker
from Utils.thread_manager import get_thread_manager
from kubernetes.client.rest import ApiException
import logging


class OverviewDataWorker(QThread):
    """Background worker for loading overview data to prevent UI freezing"""
    
    data_loaded = pyqtSignal(dict)  # Emit loaded overview data
    error_occurred = pyqtSignal(str)  # Emit error message
    progress_update = pyqtSignal(int, str)  # Emit progress percentage and status
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.kube_client = None
        self._should_stop = False
        
    def set_client(self, kube_client):
        """Set the Kubernetes client"""
        self.kube_client = kube_client
        
    def stop(self):
        """Stop the worker thread"""
        self._should_stop = True
        
    def run(self):
        """Run the background data loading"""
        try:
            if not self.kube_client:
                self.error_occurred.emit("Kubernetes client not available")
                return
                
            if self._should_stop:
                return
                
            self.progress_update.emit(10, "Connecting to Kubernetes API...")
            
            # Check if client is connected
            if not self.kube_client.is_connected():
                self.error_occurred.emit("Not connected to Kubernetes cluster")
                return
                
            if self._should_stop:
                return
                
            self.progress_update.emit(30, "Loading cluster metrics...")
            
            # Load overview data in background
            overview_data = self._load_overview_data()
            
            if self._should_stop:
                return
                
            self.progress_update.emit(100, "Data loaded successfully")
            self.data_loaded.emit(overview_data)
            
        except Exception as e:
            logging.error(f"Error in OverviewDataWorker: {e}")
            self.error_occurred.emit(f"Failed to load overview data: {str(e)}")
            
    def _load_overview_data(self):
        """Load overview data with progress updates - focused on workloads only"""
        try:
            overview_data = {}
            
            # Load workloads summary only (Overview page focus)
            self.progress_update.emit(50, "Loading workloads summary...")
            workloads_data = self._load_workloads_summary()
            overview_data['workloads'] = workloads_data
            
            return overview_data
            
        except Exception as e:
            logging.error(f"Error loading overview data: {e}")
            raise
            
            
    def _load_workloads_summary(self):
        """Load workloads summary data with optimizations for heavy loads"""
        import time
        try:
            from PyQt6.QtCore import QCoreApplication
            
            workloads_data = {}
            start_time = time.time()
            timeout = 30  # 30 second timeout for heavy clusters
            
            # Helper function to check timeout
            def check_timeout():
                if time.time() - start_time > timeout:
                    logging.warning("OverviewPage: Workload loading timeout, returning partial data")
                    return True
                return False
            
            # Load deployments with timeout protection
            self.progress_update.emit(72, "Loading deployments...")
            try:
                if check_timeout() or self._should_stop:
                    workloads_data['deployments'] = 0
                else:
                    deployments = self.kube_client.service.api_service.apps_v1.list_deployment_for_all_namespaces()
                    workloads_data['deployments'] = len(deployments.items)
            except Exception as e:
                logging.warning(f"Error loading deployments: {e}")
                workloads_data['deployments'] = 0
                
            # Load pods with chunked processing for large datasets
            self.progress_update.emit(74, "Loading pods...")
            try:
                if check_timeout() or self._should_stop:
                    workloads_data['pods_total'] = 0
                    workloads_data['pods_running'] = 0
                else:
                    pods = self.kube_client.service.api_service.v1.list_pod_for_all_namespaces()
                    workloads_data['pods_total'] = len(pods.items)
                    
                    # Process pods in chunks to avoid blocking
                    running_count = 0
                    chunk_size = 100  # Process 100 pods at a time
                    for i in range(0, len(pods.items), chunk_size):
                        if check_timeout() or self._should_stop:
                            break
                        chunk = pods.items[i:i + chunk_size]
                        running_count += sum(1 for pod in chunk 
                                           if pod.status and pod.status.phase == "Running")
                        # Allow UI to process events during heavy operations
                        QCoreApplication.processEvents()
                        time.sleep(0.001)  # 1ms pause to prevent UI freezing
                    workloads_data['pods_running'] = running_count
            except Exception as e:
                logging.warning(f"Error loading pods: {e}")
                workloads_data['pods_total'] = 0
                workloads_data['pods_running'] = 0
                
            # Load other resources with timeout checks
            resource_types = [
                ('daemonsets', 76, 'apps_v1', 'list_daemon_set_for_all_namespaces'),
                ('statefulsets', 78, 'apps_v1', 'list_stateful_set_for_all_namespaces'),  
                ('replicasets', 80, 'apps_v1', 'list_replica_set_for_all_namespaces'),
                ('jobs', 82, 'batch_v1', 'list_job_for_all_namespaces'),
                ('cronjobs', 84, 'batch_v1', 'list_cron_job_for_all_namespaces')
            ]
            
            for resource_name, progress, api_version, method_name in resource_types:
                if check_timeout() or self._should_stop:
                    workloads_data[resource_name] = 0
                    continue
                    
                self.progress_update.emit(progress, f"Loading {resource_name}...")
                # Allow UI to process events between resource loads
                QCoreApplication.processEvents()
                
                try:
                    api = getattr(self.kube_client.service.api_service, api_version)
                    method = getattr(api, method_name)
                    resources = method()
                    workloads_data[resource_name] = len(resources.items)
                except Exception as e:
                    logging.warning(f"Error loading {resource_name}: {e}")
                    workloads_data[resource_name] = 0
            
            load_time = (time.time() - start_time) * 1000
            logging.info(f"OverviewPage: Loaded workloads summary in {load_time:.1f}ms")
            return workloads_data
            
        except Exception as e:
            logging.error(f"Error loading workloads summary: {e}")
            return {
                'deployments': 0, 'pods_total': 0, 'pods_running': 0, 
                'daemonsets': 0, 'statefulsets': 0, 'replicasets': 0, 
                'jobs': 0, 'cronjobs': 0
            }
            

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

        from PyQt6.QtCore import QCoreApplication
        import time
        
        running = 0
        total = len(items)
        
        # Process in chunks for large datasets
        chunk_size = 50
        for idx, item in enumerate(items):
            # Allow UI processing every chunk_size items
            if idx > 0 and idx % chunk_size == 0:
                QCoreApplication.processEvents()
                time.sleep(0.001)  # 1ms pause to prevent UI freezing
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
        
        # Background worker for performance
        self.data_worker = None
        self._loading_in_progress = False
        
        try:
            self.setup_ui()
            
            # Initialize kubernetes client
            if self.initialize_kube_client():
                # Set up auto-refresh with much longer interval to reduce load
                self.setup_refresh_timer()
                
                # Initial data load - single call only
                if self.thread() == QApplication.instance().thread():
                    QTimer.singleShot(500, self._safe_initial_load)  # Single optimized call
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
        """Set up the refresh timer for periodic updates - DISABLED for now"""
        # Disable automatic refresh to prevent excessive API calls
        # User can manually refresh using the refresh button
        self.refresh_timer = None
        logging.info("OverviewPage: Auto-refresh disabled - manual refresh only")

    def setup_ui(self):
        """Set up the main UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Page title
        title_label = QLabel("Overview")
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
        # Check if already loading to prevent duplicate calls
        if self._loading_in_progress:
            logging.info("OverviewPage: Force loading data requested - already in progress, skipping")
            return
            
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
        """Fetch Kubernetes data using background worker to prevent UI freezing."""
        try:
            logging.info("OverviewPage: fetch_kubernetes_data called")
            
            if self._loading_in_progress:
                logging.info("OverviewPage: Background loading already in progress, skipping")
                return
                
            self._loading_in_progress = True
            
            if not self.kube_client:
                if not self.initialize_kube_client():
                    self.show_connection_error("Kubernetes client not initialized")
                    self._loading_in_progress = False
                    return

            if not hasattr(self.kube_client, 'current_cluster') or not self.kube_client.current_cluster:
                self.show_connection_error("No active cluster context")
                self._loading_in_progress = False
                return

            if not hasattr(self.kube_client, 'v1') or not self.kube_client.v1:
                self.show_connection_error("Kubernetes API client not available")
                self._loading_in_progress = False
                return

            # Stop any existing worker
            if self.data_worker and self.data_worker.isRunning():
                self.data_worker.stop()
                self.data_worker.wait(1000)  # Wait up to 1 second
                
            # Create and configure new worker
            self.data_worker = OverviewDataWorker(self)
            self.data_worker.set_client(self.kube_client)
            
            # Connect signals
            self.data_worker.data_loaded.connect(self._on_background_data_loaded)
            self.data_worker.error_occurred.connect(self._on_background_error)
            self.data_worker.progress_update.connect(self._on_progress_update)
            self.data_worker.finished.connect(self._on_worker_finished)
            
            # Don't show loading indicators - keep cards clean
            # Loading happens in background, no need to show spinners
            
            # Start background loading
            self.data_worker.start()
            logging.info("OverviewPage: Started background data loading")
            
        except Exception as e:
            logging.error(f"OverviewPage: Error starting background data fetch: {e}")
            self._loading_in_progress = False
            self.show_connection_error(f"Failed to start data loading: {str(e)}")
            
    def _on_background_data_loaded(self, overview_data):
        """Handle data loaded from background worker"""
        try:
            logging.info("OverviewPage: Received overview data from background worker")
            
            # Update workloads cards (main focus of Overview page)
            if 'workloads' in overview_data:
                self._update_workloads_cards(overview_data['workloads'])
                
            logging.info("OverviewPage: Successfully updated all overview cards")
            
        except Exception as e:
            logging.error(f"OverviewPage: Error handling background data: {e}")
            self.show_connection_error(f"Error updating overview: {str(e)}")
            
    def _on_background_error(self, error_message):
        """Handle error from background worker"""
        try:
            logging.error(f"OverviewPage: Background worker error: {error_message}")
            self.show_connection_error(error_message)
            
            # No loading indicators to hide
                    
        except Exception as e:
            logging.error(f"OverviewPage: Error handling background error: {e}")
            
    def _on_progress_update(self, percentage, status):
        """Handle progress update from background worker"""
        try:
            logging.debug(f"OverviewPage: Progress {percentage}% - {status}")
            # You could update a progress indicator here if you have one
        except Exception as e:
            logging.error(f"OverviewPage: Error handling progress update: {e}")
            
    def _on_worker_finished(self):
        """Handle worker finished signal"""
        try:
            self._loading_in_progress = False
            if self.data_worker:
                self.data_worker.deleteLater()
                self.data_worker = None
        except Exception as e:
            logging.error(f"OverviewPage: Error in worker finished handler: {e}")
            
    def _update_workloads_cards(self, workloads_data):
        """Update workloads cards with data"""
        try:
            # Update pods card
            if 'pods' in self.metric_cards:
                pods_running = workloads_data.get('pods_running', 0)
                pods_total = workloads_data.get('pods_total', 0)
                self.metric_cards['pods'].update_data(pods_running, pods_total)
                
            # Update deployments card  
            if 'deployments' in self.metric_cards:
                deployments_count = workloads_data.get('deployments', 0)
                self.metric_cards['deployments'].update_data(deployments_count, deployments_count)
                
            # Update daemon sets card
            if 'daemonsets' in self.metric_cards:
                daemonsets_count = workloads_data.get('daemonsets', 0)
                self.metric_cards['daemonsets'].update_data(daemonsets_count, daemonsets_count)
                
            # Update stateful sets card
            if 'statefulsets' in self.metric_cards:
                statefulsets_count = workloads_data.get('statefulsets', 0)
                self.metric_cards['statefulsets'].update_data(statefulsets_count, statefulsets_count)
                
            # Update replica sets card
            if 'replicasets' in self.metric_cards:
                replicasets_count = workloads_data.get('replicasets', 0)
                self.metric_cards['replicasets'].update_data(replicasets_count, replicasets_count)
                
            # Update jobs card
            if 'jobs' in self.metric_cards:
                jobs_count = workloads_data.get('jobs', 0)
                self.metric_cards['jobs'].update_data(jobs_count, jobs_count)
                
            # Update cron jobs card
            if 'cronjobs' in self.metric_cards:
                cronjobs_count = workloads_data.get('cronjobs', 0)
                self.metric_cards['cronjobs'].update_data(cronjobs_count, cronjobs_count)
                
        except Exception as e:
            logging.error(f"OverviewPage: Error updating workloads cards: {e}")
            
    def cleanup_on_destroy(self):
        """Clean up resources when page is destroyed"""
        try:
            # Stop background worker
            if self.data_worker and self.data_worker.isRunning():
                self.data_worker.stop()
                self.data_worker.wait(1000)
                
            # Stop refresh timer
            if self.refresh_timer:
                self.refresh_timer.stop()
                
            logging.info("OverviewPage: Cleanup completed")
            
        except Exception as e:
            logging.error(f"OverviewPage: Error during cleanup: {e}")

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
                
            logging.info(f"OverviewPage: Optimized scalable loading {resource_type}")
            
            # For overview page, we only need counts, not full resource details
            # Use larger batches and parallel processing for heavy loads
            batch_size = 500  # Reduced batch size to prevent UI freezing
            all_items = []
            continue_token = None
            total_fetched = 0
            max_total_items = 5000  # Reduced safety limit to prevent crashes
            max_batches = 10  # Limit number of API calls to prevent hanging
            batch_count = 0
            
            while total_fetched < max_total_items and batch_count < max_batches:
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
                        batch_count += 1
                        
                        # Update with progressive count for large datasets - less frequent updates
                        if total_fetched > 1000 and batch_count % 3 == 0:
                            # Show progressive update every 3 batches to reduce UI load
                            partial_running = self._calculate_running_count(resource_type, all_items)
                            self.update_card_data(resource_type, (partial_running, f"{total_fetched}+"))
                            
                            # Process pending events to prevent UI freeze
                            QApplication.processEvents()
                    
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
            # Don't crash the entire page - show partial data if available
            if all_items:
                partial_running = self._calculate_running_count(resource_type, all_items)
                self.update_card_data(resource_type, (partial_running, f"{len(all_items)}+"))
                logging.info(f"OverviewPage: Showing partial data for {resource_type}: {partial_running}/{len(all_items)}+")
            else:
                self.handle_resource_error(resource_type, str(e))
            self._loading_resources.discard(resource_type)
    
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
        """Handle show event - no automatic loading (handled by initial load)"""
        super().showEvent(event)
        
        # No automatic loading on show - initial load handles everything
        # This prevents duplicate loading calls
        pass
    

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
