"""
Dynamic implementation of the Overview page with simplified metric cards using Kubernetes API.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSizePolicy, QScrollArea, QFrame, QPushButton
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QSize, QTimer

from UI.Styles import AppStyles, AppColors
from utils.kubernetes_client import get_kubernetes_client
from kubernetes.client.rest import ApiException
import logging

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
        subtitle_font.setPointSize(12)
        subtitle_font.setWeight(QFont.Weight.Normal)
        self.subtitle_label.setFont(subtitle_font)
        self.subtitle_label.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['text_secondary']};
                background-color: transparent;
                border: none;
                margin: 0px;
            }}
        """)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        card_layout.addWidget(self.subtitle_label)

        # Add stretch to push content to top
        card_layout.addStretch()

        # Add the card to main layout
        main_layout.addWidget(self.card)

    def update_data(self, running, total):
        """Update the card with new data."""
        self.running = running
        self.total = total
        self.metric_label.setText(f"{running} / {total}")

        # Reset error state when we have valid data
        self.show_error_state(False)

    def show_error_state(self, is_error, error_message="Unable to fetch data"):
        """Show or hide error state for this card."""
        if is_error:
            self.metric_label.setText("--")
            self.subtitle_label.setText(error_message)
            self.subtitle_label.setStyleSheet(f"""
                QLabel {{
                    color: {self.colors['text_secondary']};
                    background-color: transparent;
                    border: none;
                    margin: 0px;
                    font-style: italic;
                }}
            """)
        else:
            # Reset to normal subtitle
            self.subtitle_label.setText(f"Running / Total {self.title_label.text()}")
            self.subtitle_label.setStyleSheet(f"""
                QLabel {{
                    color: {self.colors['text_secondary']};
                    background-color: transparent;
                    border: none;
                    margin: 0px;
                }}
            """)

    def sizeHint(self):
        """Return fixed size for all cards."""
        return QSize(280, 180)

    def minimumSizeHint(self):
        """Return minimum size for all cards."""
        return QSize(280, 180)

    def maximumSize(self):
        """Return maximum size for all cards."""
        return QSize(280, 180)


class OverviewPage(QWidget):
    """
    Overview page with simplified design and real-time data using Kubernetes API.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.metric_cards = {}
        self.kube_client = None
        self.setup_ui()

        # Timer for auto-refresh
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

        # Initial data load with slight delay to allow UI to render
        QTimer.singleShot(500, self.initial_refresh)

    def initial_refresh(self):
        """Perform initial data refresh."""
        self.initialize_kube_client()
        self.refresh_data()

    def initialize_kube_client(self):
        """Initialize Kubernetes client connection."""
        try:
            self.kube_client = get_kubernetes_client()
            if not self.kube_client.current_cluster:
                # Load kubeconfig asynchronously to avoid blocking UI
                self._load_kubeconfig_async()
        except Exception as e:
            logging.error(f"Error initializing Kubernetes client: {e}")

    def _load_kubeconfig_async(self):
        """Load kubeconfig asynchronously in background thread"""
        try:
            from utils.kubernetes_client import KubeConfigWorker
            from utils.thread_manager import get_thread_manager
            
            thread_manager = get_thread_manager()
            worker = KubeConfigWorker(self.kube_client)
            
            def on_config_loaded(clusters):
                if clusters:
                    # Find active cluster or use first available
                    active_cluster = next((c for c in clusters if c.status == "active"), None)
                    if not active_cluster and clusters:
                        active_cluster = clusters[0]

                    if active_cluster:
                        self.kube_client.switch_context(active_cluster.name)
            
            def on_error(error):
                logging.error(f"Error loading kubeconfig async: {error}")
            
            worker.signals.finished.connect(on_config_loaded)
            worker.signals.error.connect(on_error)
            thread_manager.submit_worker(f"kubeconfig_load_{id(self)}", worker)
            
        except Exception as e:
            logging.error(f"Error starting async kubeconfig load: {e}")
            self.show_connection_error(f"Failed to initialize: {str(e)}")

    def setup_ui(self):
        """Set up the main UI."""
        # Define colors
        colors = {
            'text_primary': getattr(AppColors, 'TEXT_LIGHT', '#ffffff'),
            'accent_color': getattr(AppColors, 'ACCENT_BLUE', '#0ea5e9'),
            'accent_hover': getattr(AppColors, 'ACCENT_BLUE', '#0284c7'),
        }

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title_label = QLabel("Overview")
        title_font = QFont()
        title_font.setFamily("Segoe UI")
        title_font.setPointSize(28)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['text_primary']};
                background-color: transparent;
                border: none;
                margin: 0px;
            }}
        """)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_style = getattr(AppStyles, "SECONDARY_BUTTON_STYLE",
                                """QPushButton { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3d3d3d;
                                               border-radius: 4px; padding: 5px 10px; }
                                   QPushButton:hover { background-color: #3d3d3d; }
                                   QPushButton:pressed { background-color: #1e1e1e; }"""
                                )
        refresh_btn.setStyleSheet(refresh_style)
        refresh_btn.clicked.connect(lambda: self.force_load_data())

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)

        # Create header widget
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        main_layout.addWidget(header_widget)

        # Cards container
        cards_container = QWidget()
        cards_layout = QVBoxLayout(cards_container)
        cards_layout.setSpacing(20)
        cards_layout.setContentsMargins(0, 0, 0, 0)

        # First row (4 cards)
        first_row = QWidget()
        first_row_layout = QHBoxLayout(first_row)
        first_row_layout.setSpacing(20)
        first_row_layout.setContentsMargins(0, 0, 0, 0)

        # Create cards for first row
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
        """Fetch actual Kubernetes data using the API client."""
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

        success_count = 0
        total_resources = len(self.metric_cards)

        for resource_type, card in self.metric_cards.items():
            try:
                # Get resource data using API calls
                if resource_type == "pods":
                    items = self.kube_client.v1.list_pod_for_all_namespaces()
                elif resource_type == "deployments":
                    items = self.kube_client.apps_v1.list_deployment_for_all_namespaces()
                elif resource_type == "daemonsets":
                    items = self.kube_client.apps_v1.list_daemon_set_for_all_namespaces()
                elif resource_type == "statefulsets":
                    items = self.kube_client.apps_v1.list_stateful_set_for_all_namespaces()
                elif resource_type == "replicasets":
                    items = self.kube_client.apps_v1.list_replica_set_for_all_namespaces()
                elif resource_type == "jobs":
                    items = self.kube_client.batch_v1.list_job_for_all_namespaces()
                elif resource_type == "cronjobs":
                    # Try batch/v1 first (Kubernetes 1.21+), fallback to batch/v1beta1
                    try:
                        items = self.kube_client.batch_v1.list_cron_job_for_all_namespaces()
                    except (AttributeError, ApiException):
                        # Fallback to batch/v1beta1 for older clusters
                        if hasattr(self.kube_client, 'batch_v1beta1') and self.kube_client.batch_v1beta1:
                            items = self.kube_client.batch_v1beta1.list_cron_job_for_all_namespaces()
                        else:
                            raise Exception("CronJob API not available")
                else:
                    card.show_error_state(True, f"Unknown resource type: {resource_type}")
                    continue

                # Calculate running/total status
                running, total = self.calculate_status(resource_type, items.items)
                card.update_data(running, total)
                success_count += 1

            except ApiException as e:
                if e.status == 403:
                    card.show_error_state(True, f"Permission denied")
                elif e.status == 404:
                    card.show_error_state(True, f"Resource not found")
                else:
                    card.show_error_state(True, f"API error: {e.reason}")
                logging.error(f"API error fetching {resource_type}: {e}")

            except Exception as e:
                card.show_error_state(True, "Connection error")
                logging.error(f"Error fetching {resource_type}: {e}")

        # Log overall status
        if success_count == 0:
            logging.warning("Failed to fetch data for all resource types")
        elif success_count < total_resources:
            logging.warning(f"Successfully fetched {success_count}/{total_resources} resource types")
        else:
            logging.info(f"Successfully fetched all {total_resources} resource types")

    def show_connection_error(self, error_message):
        """Show connection error on all cards."""
        for card in self.metric_cards.values():
            card.show_error_state(True, error_message)

    def calculate_status(self, resource_type, items):
        """Calculate running/total status for resource type using API objects."""
        if not items:
            return 0, 0

        running = 0
        total = len(items)

        for item in items:
            status = item.status if hasattr(item, 'status') and item.status else None

            if resource_type == "pods":
                if status and hasattr(status, 'phase'):
                    if status.phase == "Running":
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
                    elif desired == 0:
                        total -= 1  # Don't count scaled-down replicasets

            elif resource_type == "jobs":
                if status:
                    succeeded = getattr(status, 'succeeded', 0) or 0
                    if succeeded > 0:
                        running += 1

            elif resource_type == "cronjobs":
                # CronJobs are considered "running" if they exist and are not suspended
                if hasattr(item, 'spec') and item.spec:
                    suspended = getattr(item.spec, 'suspend', False)
                    if not suspended:
                        running += 1

        return running, max(total, 0)

    def showEvent(self, event):
        """Start refresh timer when page is shown."""
        super().showEvent(event)
        self.refresh_timer.start(5000)
        if not self.kube_client:
            self.initialize_kube_client()
        self.refresh_data()

    def hideEvent(self, event):
        """Stop refresh timer when page is hidden."""
        super().hideEvent(event)
        self.refresh_timer.stop()

    def closeEvent(self, event):
        """Clean up when the widget is closed."""
        try:
            if hasattr(self, 'refresh_timer') and self.refresh_timer:
                self.refresh_timer.stop()
        except Exception as e:
            logging.error(f"Error cleaning up overview page: {e}")
        super().closeEvent(event)