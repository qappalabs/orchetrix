"""
Non-blocking implementation of the Overview page with async data loading.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSizePolicy, QScrollArea, QFrame
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer, pyqtSignal,QThread

from UI.Styles import AppStyles, AppColors
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
        """Run the background data loading with robust error handling"""
        try:
            if self._should_stop:
                return

            if not self.kube_client:
                self.error_occurred.emit("Kubernetes client not available")
                return

            self.progress_update.emit(10, "Connecting to Kubernetes API...")

            # Test connection with timeout
            try:
                # Simple connection test with short timeout
                if hasattr(self.kube_client, 'version_api'):
                    version = self.kube_client.version_api.get_code(_request_timeout=5)
                    logging.info(f"Connected to Kubernetes cluster version: {version.git_version if version else 'Unknown'}")
                else:
                    logging.warning("Cannot test connection - proceeding with data load")
            except Exception as conn_e:
                logging.warning(f"Connection test failed: {conn_e}, but continuing with data load")

            if self._should_stop:
                return

            self.progress_update.emit(30, "Loading cluster metrics...")

            # Load overview data in background with timeout protection
            import time
            import threading
            
            # Use threading-based timeout instead of signal-based
            overview_data = None
            exception_holder = [None]
            
            def load_with_timeout():
                try:
                    nonlocal overview_data
                    overview_data = self._load_overview_data()
                except Exception as e:
                    exception_holder[0] = e
            
            # Start loading in a separate thread with timeout
            load_thread = threading.Thread(target=load_with_timeout)
            load_thread.daemon = True
            load_thread.start()
            load_thread.join(timeout=60)  # 60 second timeout
            
            if load_thread.is_alive():
                # Timeout occurred
                raise TimeoutError("Data loading timeout")
            
            if exception_holder[0]:
                raise exception_holder[0]
                
            if overview_data is None:
                raise Exception("No data loaded")

            if self._should_stop:
                return

            self.progress_update.emit(100, "Data loaded successfully")
            self.data_loaded.emit(overview_data)

        except TimeoutError:
            logging.error("OverviewDataWorker: Data loading timeout")
            self.error_occurred.emit("Data loading timeout - cluster may be under heavy load")
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
            workloads_data = {}
            start_time = time.time()
            timeout = 60  # Increased timeout for heavy clusters

            # Helper function to check timeout
            def check_timeout():
                if time.time() - start_time > timeout:
                    logging.warning("OverviewPage: Workload loading timeout, returning partial data")
                    return True
                return False

            # Helper function to safely count resources
            def safe_count_resources(resource_type, api_call, progress_pct, progress_msg):
                if check_timeout() or self._should_stop:
                    return 0

                self.progress_update.emit(progress_pct, progress_msg)

                try:
                    resources = api_call()
                    count = len(resources.items) if hasattr(resources, 'items') else 0
                    logging.info(f"OverviewPage: Loaded {count} {resource_type}")
                    return count
                except Exception as e:
                    logging.warning(f"Error loading {resource_type}: {e}")
                    return 0

            # Use direct API calls for better reliability
            api_service = self.kube_client.service.api_service

            # Load deployments
            workloads_data['deployments'] = safe_count_resources(
                'deployments',
                lambda: api_service.apps_v1.list_deployment_for_all_namespaces(limit=5000),
                20, "Loading deployments..."
            )

            # Load daemonsets
            workloads_data['daemonsets'] = safe_count_resources(
                'daemonsets',
                lambda: api_service.apps_v1.list_daemon_set_for_all_namespaces(limit=5000),
                30, "Loading daemon sets..."
            )

            # Load statefulsets
            workloads_data['statefulsets'] = safe_count_resources(
                'statefulsets',
                lambda: api_service.apps_v1.list_stateful_set_for_all_namespaces(limit=5000),
                40, "Loading stateful sets..."
            )

            # Load replicasets
            workloads_data['replicasets'] = safe_count_resources(
                'replicasets',
                lambda: api_service.apps_v1.list_replica_set_for_all_namespaces(limit=5000),
                50, "Loading replica sets..."
            )

            # Load jobs
            workloads_data['jobs'] = safe_count_resources(
                'jobs',
                lambda: api_service.batch_v1.list_job_for_all_namespaces(limit=5000),
                60, "Loading jobs..."
            )

            # Load cronjobs
            try:
                workloads_data['cronjobs'] = safe_count_resources(
                    'cronjobs',
                    lambda: api_service.batch_v1.list_cron_job_for_all_namespaces(limit=5000),
                    70, "Loading cron jobs..."
                )
            except Exception:
                # Fallback to v1beta1 if v1 not available
                try:
                    workloads_data['cronjobs'] = safe_count_resources(
                        'cronjobs',
                        lambda: api_service.batch_v1beta1.list_cron_job_for_all_namespaces(limit=5000),
                        70, "Loading cron jobs..."
                    )
                except Exception as e:
                    logging.warning(f"Error loading cronjobs: {e}")
                    workloads_data['cronjobs'] = 0

            # Load pods last as they're usually the largest dataset
            self.progress_update.emit(80, "Loading pods...")

            try:
                if check_timeout() or self._should_stop:
                    workloads_data['pods_total'] = 0
                    workloads_data['pods_running'] = 0
                else:
                    # Use pagination for pods to handle large datasets
                    pods_total = 0
                    pods_running = 0
                    continue_token = None
                    batch_count = 0
                    max_batches = 20  # Limit to prevent excessive API calls

                    while batch_count < max_batches and not (check_timeout() or self._should_stop):
                        try:
                            # Fetch batch with pagination
                            pods_batch = api_service.v1.list_pod_for_all_namespaces(
                                limit=500, _continue=continue_token
                            )

                            if not pods_batch.items:
                                break

                            # Count pods in this batch
                            batch_total = len(pods_batch.items)
                            batch_running = sum(1 for pod in pods_batch.items
                                              if pod.status and pod.status.phase == "Running")

                            pods_total += batch_total
                            pods_running += batch_running
                            batch_count += 1

                            # Update progress
                            progress = 80 + (batch_count * 15 // max_batches)
                            self.progress_update.emit(progress, f"Loading pods... ({pods_total} found)")

                            # Check for next page
                            continue_token = getattr(pods_batch.metadata, 'continue', None) if hasattr(pods_batch, 'metadata') else None
                            if not continue_token:
                                break

                        except Exception as batch_e:
                            logging.warning(f"Error in pods batch {batch_count}: {batch_e}")
                            break

                    workloads_data['pods_total'] = pods_total
                    workloads_data['pods_running'] = pods_running
                    logging.info(f"OverviewPage: Loaded {pods_total} pods ({pods_running} running) in {batch_count} batches")

            except Exception as e:
                logging.warning(f"Error loading pods: {e}")
                workloads_data['pods_total'] = 0
                workloads_data['pods_running'] = 0

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
        
        # Update subtitle to show proper text instead of "Loading..."
        self.subtitle_label.setText(f"Running / Total {self.title_label.text()}")
        
        # Force a repaint to ensure the update is visible
        self.metric_label.update()
        self.subtitle_label.update()
        
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

            # Show loading indicators immediately on all cards
            self._show_loading_on_all_cards()

            # Initialize kubernetes client
            if self.initialize_kube_client():
                # Set up auto-refresh with much longer interval to reduce load
                self.setup_refresh_timer()

                # Initial data load - immediate start with proper delay
                QTimer.singleShot(100, self._safe_initial_load)  # Reduced delay for faster response
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
            # Always try to load data regardless of initialization state
            if not self.kube_client:
                self.initialize_kube_client()

            if self.kube_client:
                logging.info("OverviewPage: Starting initial data load")
                self.fetch_kubernetes_data()
            else:
                logging.error("OverviewPage: No Kubernetes client available")
                self.show_connection_error("Unable to connect to Kubernetes cluster")
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

    def _show_loading_on_all_cards(self):
        """Show loading indicators on all metric cards"""
        for card in self.metric_cards.values():
            card.show_loading()

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

        # Show loading indicators immediately
        self._show_loading_on_all_cards()

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

            # Show loading indicators on all cards immediately
            self._show_loading_on_all_cards()

            if not self.kube_client:
                if not self.initialize_kube_client():
                    self.show_connection_error("Kubernetes client not initialized")
                    self._loading_in_progress = False
                    return

            # Check connection with timeout
            try:
                if not self.kube_client.is_connected():
                    self.show_connection_error("Not connected to Kubernetes cluster")
                    self._loading_in_progress = False
                    return
            except Exception as conn_e:
                logging.warning(f"Connection check failed: {conn_e}, proceeding anyway")

            # Stop any existing worker
            if self.data_worker and self.data_worker.isRunning():
                self.data_worker.stop()
                self.data_worker.wait(1000)  # Wait up to 1 second

            # Create and configure new worker
            self.data_worker = OverviewDataWorker(self)
            self.data_worker.set_client(self.kube_client)

            # Connect signals properly
            self.data_worker.data_loaded.connect(self._on_background_data_loaded)
            self.data_worker.error_occurred.connect(self._on_background_error)
            self.data_worker.progress_update.connect(self._on_progress_update)
            self.data_worker.finished.connect(self._on_worker_finished)

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
            logging.info(f"OverviewPage: Received overview data from background worker: {overview_data}")

            # Update workloads cards (main focus of Overview page)
            if 'workloads' in overview_data:
                self._update_workloads_cards(overview_data['workloads'])
            else:
                logging.warning("OverviewPage: No workloads data in overview_data")
                # Show empty data instead of error
                empty_data = {
                    'deployments': 0, 'pods_total': 0, 'pods_running': 0,
                    'daemonsets': 0, 'statefulsets': 0, 'replicasets': 0,
                    'jobs': 0, 'cronjobs': 0
                }
                self._update_workloads_cards(empty_data)

            logging.info("OverviewPage: Successfully updated all overview cards")

        except Exception as e:
            logging.error(f"OverviewPage: Error handling background data: {e}")
            self.show_connection_error(f"Error updating overview: {str(e)}")
            
    def _on_background_error(self, error_message):
        """Handle error from background worker"""
        try:
            logging.error(f"OverviewPage: Background worker error: {error_message}")

            # Reset loading state
            self._loading_in_progress = False

            # Show error on all cards
            for card in self.metric_cards.values():
                card.show_error_state(True, f"Loading failed: {error_message}")

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
            logging.info("OverviewPage: Background worker finished")
            self._loading_in_progress = False
            if self.data_worker:
                self.data_worker.deleteLater()
                self.data_worker = None
        except Exception as e:
            logging.error(f"OverviewPage: Error in worker finished handler: {e}")
            
    def _update_workloads_cards(self, workloads_data):
        """Update workloads cards with data"""
        try:
            logging.info(f"OverviewPage: Updating cards with data: {workloads_data}")

            # Update pods card
            if 'pods' in self.metric_cards:
                pods_running = workloads_data.get('pods_running', 0)
                pods_total = workloads_data.get('pods_total', 0)
                self.metric_cards['pods'].update_data(pods_running, pods_total)
                logging.info(f"Updated pods card: {pods_running}/{pods_total}")

            # Update deployments card
            if 'deployments' in self.metric_cards:
                deployments_count = workloads_data.get('deployments', 0)
                # For deployments, we don't track running vs total, so show count for both
                self.metric_cards['deployments'].update_data(deployments_count, deployments_count)
                logging.info(f"Updated deployments card: {deployments_count}")

            # Update daemon sets card
            if 'daemonsets' in self.metric_cards:
                daemonsets_count = workloads_data.get('daemonsets', 0)
                self.metric_cards['daemonsets'].update_data(daemonsets_count, daemonsets_count)
                logging.info(f"Updated daemonsets card: {daemonsets_count}")

            # Update stateful sets card
            if 'statefulsets' in self.metric_cards:
                statefulsets_count = workloads_data.get('statefulsets', 0)
                self.metric_cards['statefulsets'].update_data(statefulsets_count, statefulsets_count)
                logging.info(f"Updated statefulsets card: {statefulsets_count}")

            # Update replica sets card
            if 'replicasets' in self.metric_cards:
                replicasets_count = workloads_data.get('replicasets', 0)
                self.metric_cards['replicasets'].update_data(replicasets_count, replicasets_count)
                logging.info(f"Updated replicasets card: {replicasets_count}")

            # Update jobs card
            if 'jobs' in self.metric_cards:
                jobs_count = workloads_data.get('jobs', 0)
                self.metric_cards['jobs'].update_data(jobs_count, jobs_count)
                logging.info(f"Updated jobs card: {jobs_count}")

            # Update cron jobs card
            if 'cronjobs' in self.metric_cards:
                cronjobs_count = workloads_data.get('cronjobs', 0)
                self.metric_cards['cronjobs'].update_data(cronjobs_count, cronjobs_count)
                logging.info(f"Updated cronjobs card: {cronjobs_count}")

            logging.info("OverviewPage: All cards updated successfully")

        except Exception as e:
            logging.error(f"OverviewPage: Error updating workloads cards: {e}")
            # Clear loading state on error
            for card in self.metric_cards.values():
                card.show_error_state(True, f"Update error: {str(e)}")
            
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


    def show_connection_error(self, error_message):
        """Show connection error on all cards."""
        for card in self.metric_cards.values():
            card.show_error_state(True, error_message)

    def initialize_kube_client(self):
        """Initialize or update the Kubernetes client."""
        try:
            from Utils.kubernetes_client import get_kubernetes_client
            self.kube_client = get_kubernetes_client()

            if self.kube_client:
                # Test the connection by trying to get the API version
                try:
                    if self.kube_client.is_connected():
                        cluster_name = getattr(self.kube_client, 'current_cluster', 'Unknown')
                        logging.info(f"OverviewPage: Kubernetes client initialized and connected to cluster: {cluster_name}")
                        return True
                    else:
                        logging.warning("OverviewPage: Kubernetes client initialized but not connected")
                        return False
                except Exception as conn_e:
                    logging.warning(f"OverviewPage: Kubernetes client connection test failed: {conn_e}")
                    # Still return True if we have a client, connection might work for actual API calls
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
        """Handle show event - trigger data load if not already loaded"""
        super().showEvent(event)

        # Only load if we haven't loaded data yet and not currently loading
        if not self._loading_in_progress:
            # Check if all cards are showing 0/0 (indicating no data loaded)
            all_empty = all(
                card.running == 0 and card.total == 0
                for card in self.metric_cards.values()
            )

            if all_empty:
                logging.info("OverviewPage: Show event detected empty cards, triggering data load")
                QTimer.singleShot(100, self.fetch_kubernetes_data)
    

    def cleanup(self):
        """Cleanup when page is being destroyed."""
        try:
            # Stop any background worker
            if self.data_worker and self.data_worker.isRunning():
                self.data_worker.stop()
                self.data_worker.wait(2000)
                self.data_worker.deleteLater()
                self.data_worker = None

            # Stop any timer
            if self.refresh_timer:
                self.refresh_timer.stop()
                self.refresh_timer.deleteLater()
                self.refresh_timer = None

            # Reset loading state
            self._loading_in_progress = False
            self._loading_resources.clear()

            # Clear references
            self.kube_client = None

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
            super().closeEvent(event)

    def __del__(self):
        """Destructor for additional safety"""
        try:
            if hasattr(self, 'data_worker'):
                self.cleanup()
        except Exception:
            pass  # Ignore errors in destructor
