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

class OverviewResourceWorker(QObject, EnhancedBaseWorker):
    """Async worker for loading overview resource data"""
    data_loaded = pyqtSignal(tuple)  # (running_count, total_count)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, resource_type, kube_client):
        QObject.__init__(self)
        EnhancedBaseWorker.__init__(self, f"overview_{resource_type}")
        self.resource_type = resource_type
        self.kube_client = kube_client
        
    def execute(self):
        try:
            # Fetch data based on resource type
            if self.resource_type == "pods":
                items = self.kube_client.v1.list_pod_for_all_namespaces()
            elif self.resource_type == "deployments":
                items = self.kube_client.apps_v1.list_deployment_for_all_namespaces()
            elif self.resource_type == "daemonsets":
                items = self.kube_client.apps_v1.list_daemon_set_for_all_namespaces()
            elif self.resource_type == "statefulsets":
                items = self.kube_client.apps_v1.list_stateful_set_for_all_namespaces()
            elif self.resource_type == "replicasets":
                items = self.kube_client.apps_v1.list_replica_set_for_all_namespaces()
            elif self.resource_type == "jobs":
                items = self.kube_client.batch_v1.list_job_for_all_namespaces()
            elif self.resource_type == "cronjobs":
                try:
                    items = self.kube_client.batch_v1.list_cron_job_for_all_namespaces()
                except (AttributeError, ApiException):
                    if hasattr(self.kube_client, 'batch_v1beta1') and self.kube_client.batch_v1beta1:
                        items = self.kube_client.batch_v1beta1.list_cron_job_for_all_namespaces()
                    else:
                        raise Exception("CronJob API not available")
            else:
                raise Exception(f"Unknown resource type: {self.resource_type}")
            
            # Calculate status
            running, total = self.calculate_status(items.items)
            self.data_loaded.emit((running, total))
            
        except Exception as e:
            self.error_occurred.emit(str(e))
            
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
        self.running = running
        self.total = total
        self.metric_label.setText(f"{running} / {total}")
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
            self.update_data(self.running, self.total)


class OverviewPage(QWidget):
    """Overview page showing workload metrics with async data loading."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.metric_cards = {}
        self.kube_client = None
        self.refresh_timer = None
        
        self.setup_ui()
        self.initialize_kube_client()
        
        # Set up auto-refresh with longer interval to reduce load
        self.setup_refresh_timer()
        
        # Initial data load - ensure it's called from main thread
        if self.thread() == QApplication.instance().thread():
            QTimer.singleShot(1000, self.fetch_kubernetes_data)
        else:
            # Use metaObject to invoke on main thread
            from PyQt6.QtCore import QMetaObject, Q_ARG
            QMetaObject.invokeMethod(self, "fetch_kubernetes_data", Qt.ConnectionType.QueuedConnection)
        
    def setup_refresh_timer(self):
        """Set up the refresh timer for periodic updates."""
        # Ensure timer is created on main thread
        if self.thread() == QApplication.instance().thread():
            self.refresh_timer = QTimer(self)  # Set parent to ensure proper cleanup
            self.refresh_timer.timeout.connect(self.refresh_data)
            # Refresh every 30 seconds instead of 5 to reduce load
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
        self.initialize_kube_client()
        self.fetch_kubernetes_data()

    def fetch_kubernetes_data(self):
        """Fetch actual Kubernetes data using async workers."""
        if not self.kube_client:
            self.show_connection_error("Kubernetes client not initialized")
            return

        if not self.kube_client.current_cluster:
            self.show_connection_error("No active cluster context")
            return

        # Check if API clients are available
        if not hasattr(self.kube_client, 'v1') or not self.kube_client.v1:
            self.show_connection_error("Kubernetes API client not available")
            return

        # Load data asynchronously for each resource type
        for resource_type in self.metric_cards.keys():
            self.load_resource_async(resource_type)

    def load_resource_async(self, resource_type):
        """Load a specific resource type asynchronously"""
        worker = OverviewResourceWorker(resource_type, self.kube_client)
        worker.data_loaded.connect(lambda data, rtype=resource_type: self.update_card_data(rtype, data))
        worker.error_occurred.connect(lambda error, rtype=resource_type: self.handle_resource_error(rtype, error))
        
        # Submit to thread manager
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(worker)
        
    def update_card_data(self, resource_type, data):
        """Update card with loaded data"""
        if resource_type in self.metric_cards:
            running_count, total_count = data
            self.metric_cards[resource_type].update_data(running_count, total_count)
            logging.info(f"Updated {resource_type}: {running_count}/{total_count}")
            
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
            self.kube_client = get_kubernetes_client()
            if self.kube_client and hasattr(self.kube_client, 'current_cluster'):
                logging.info(f"OverviewPage: Kubernetes client initialized for cluster: {self.kube_client.current_cluster}")
            else:
                logging.warning("OverviewPage: Kubernetes client not properly initialized")
        except Exception as e:
            logging.error(f"OverviewPage: Failed to initialize Kubernetes client: {e}")
            self.kube_client = None

    def cleanup(self):
        """Cleanup when page is being destroyed."""
        if self.refresh_timer:
            self.refresh_timer.stop()