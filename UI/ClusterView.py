from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QPointF
from PyQt6.QtGui import QColor, QPainter, QBrush
import math

from .DetailManager import DetailManager
import logging
from UI.Sidebar import Sidebar

from UI.Styles import AppColors

from UI.TerminalPanel import TerminalPanel

# Import cluster connector
from utils.cluster_connector import get_cluster_connector

# Import cluster pages
from Pages.ClusterPage import ClusterPage
from Pages.NodesPage import NodesPage
from Pages.EventsPage import EventsPage
from Pages.NamespacesPage import NamespacesPage

# Workload pages
from Pages.WorkLoad.OverviewPage import OverviewPage
from Pages.WorkLoad.PodsPage import PodsPage
from Pages.WorkLoad.DeploymentsPage import DeploymentsPage
from Pages.WorkLoad.StatfulSetsPage import StatefulSetsPage
from Pages.WorkLoad.DaemonSetsPage import DaemonSetsPage
from Pages.WorkLoad.ReplicaSetsPage import ReplicaSetsPage
from Pages.WorkLoad.ReplicationControllersPage import ReplicaControllersPage
from Pages.WorkLoad.JobsPage import JobsPage
from Pages.WorkLoad.CronJobsPage import CronJobsPage

# Config pages
from Pages.Config.ConfigMapsPage import ConfigMapsPage
from Pages.Config.SecretsPage import SecretsPage
from Pages.Config.ResourceQuotasPage import ResourceQuotasPage
from Pages.Config.LimitRangesPage import LimitRangesPage
from Pages.Config.HorizontalPodAutoscalersPage import HorizontalPodAutoscalersPage
from Pages.Config.PodDisruptionBudgetsPage import PodDisruptionBudgetsPage
from Pages.Config.PriorityClassesPage import PriorityClassesPage
from Pages.Config.RuntimeClassesPage import RuntimeClassesPage
from Pages.Config.LeasesPage import LeasesPage
from Pages.Config.MutatingWebhookConfigsPage import MutatingWebhookConfigsPage
from Pages.Config.ValidatingWebhookConfigsPage import ValidatingWebhookConfigsPage

# Network pages
from Pages.NetWork.ServicesPage import ServicesPage
from Pages.NetWork.EndpointesPage import EndpointsPage
from Pages.NetWork.IngressesPage import IngressesPage
from Pages.NetWork.IngressClassesPage import IngressClassesPage
from Pages.NetWork.NetworkPoliciesPage import NetworkPoliciesPage
from Pages.NetWork.PortForwardingPage import PortForwardingPage

# Storage pages
from Pages.Storage.PersistentVolumeClaimsPage import PersistentVolumeClaimsPage
from Pages.Storage.PersistentVolumesPage import PersistentVolumesPage
from Pages.Storage.StorageClassesPage import StorageClassesPage

# Access Control Pages
from Pages.AccessControl.ServiceAccountsPage import ServiceAccountsPage
from Pages.AccessControl.ClusterRolesPage import ClusterRolesPage
from Pages.AccessControl.RolesPage import RolesPage
from Pages.AccessControl.ClusterRoleBindingsPage import ClusterRoleBindingsPage
from Pages.AccessControl.RoleBinidingsPage import RoleBindingsPage

# Helm Pages
from Pages.Helm.ChartsPage import ChartsPage
from Pages.Helm.ReleasesPage import ReleasesPage

# Custome Resource Pages
from Pages.CustomResources.DefinitionsPage import DefinitionsPage

class LoadingOverlay(QWidget):
    """Overlay to show loading state with animation"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        self.setStyleSheet("""
            #loadingOverlay {
                background-color: rgba(20, 20, 20, 0.8);
            }
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add a loading spinner
        self.spinner_label = QLabel()
        self.spinner_label.setMinimumSize(64, 64)
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create spinner animation
        self.spinner_angle = 0
        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self.update_spinner)
        
        # Message label
        self.message = QLabel("Connecting to cluster...")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.spinner_label)
        layout.addWidget(self.message)
        
        self.hide()
    
    def update_spinner(self):
        """Update the spinner animation"""
        self.spinner_angle = (self.spinner_angle + 10) % 360
        self.update()
    
    def paintEvent(self, event):
        """Paint the loading spinner"""
        super().paintEvent(event)
        
        if self.isVisible():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw spinner in the spinner_label
            rect = self.spinner_label.geometry()
            center = QPoint(rect.center().x(), rect.center().y())
            radius = min(rect.width(), rect.height()) / 2 - 5
            
            # Draw 12 dots with varying opacity
            for i in range(12):
                angle = (self.spinner_angle - i * 30) % 360
                angle_rad = angle * 3.14159 / 180.0
                
                # Calculate opacity based on position
                opacity = 0.2 + 0.8 * ((12 - i) % 12) / 12
                
                # Calculate position
                x = center.x() + radius * 0.8 * math.cos(angle_rad)
                y = center.y() + radius * 0.8 * math.sin(angle_rad)
                
                # Set color with appropriate opacity
                color = QColor(AppColors.ACCENT_GREEN)
                color.setAlphaF(opacity)
                
                # Draw the dot
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(x, y), 5, 5)
    
    def show_loading(self, message="Connecting to cluster..."):
        """Show loading overlay with custom message"""
        self.message.setText(message)
        self.spinner_timer.start(50)  # Update every 50ms
        self.show()
        self.raise_()
    
    def hide_loading(self):
        """Hide loading overlay"""
        self.spinner_timer.stop()
        self.hide()

class ClusterView(QWidget):
    """
    The ClusterView contains the cluster-specific sidebar and pages.
    It's used when viewing cluster-related content.
    """
    # Signal when a user wants to switch back to home
    switch_to_home_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # Set the background color for the entire view
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {AppColors.BG_DARK};
                color: {AppColors.TEXT_LIGHT};
            }}
        """)
        
        # Dictionary to store pages for easy navigation
        self.pages = {}
        
        # Current active cluster
        self.active_cluster = None
        
        # Get the cluster connector
        self.cluster_connector = get_cluster_connector()
        
        # Connect to signals
        self.cluster_connector.connection_started.connect(self.on_connection_started)
        self.cluster_connector.connection_complete.connect(self.on_connection_complete)
        self.cluster_connector.cluster_data_loaded.connect(self.on_cluster_data_loaded)
        self.cluster_connector.error_occurred.connect(self.on_error)
        
        self.setup_ui()
        
        # Initialize the terminal panel
        self.initialize_terminal()

        self.initialize_detail_page()
        # Create loading overlay
        self.loading_overlay = LoadingOverlay(self)
        
        # Install event filter to detect window resize events
        self.installEventFilter(self)

    def initialize_detail_page(self):
        """Initialize the detail page manager"""
        self.detail_manager = DetailManager(self.parent_window)
        
        # Connect signals
        self.detail_manager.resource_updated.connect(self.handle_resource_updated)
    
   
    def show_detail_for_table_item(self, row, col, page, page_name):
        """Show detail page for clicked table item with improved chart handling"""
        # Determine resource type based on page name
        if page_name == "Charts":
            resource_type = "chart"  # Use chart type for Helm charts
        elif page_name == "Releases":
            resource_type = "helmrelease"  # Use helmrelease instead of Release
        else:
            resource_type = page_name.rstrip('s')  # Remove trailing 's' for regular resources
        
        # Special handling for Events
        if page_name == "Events" and hasattr(page, 'resources') and row < len(page.resources):
            event = page.resources[row]
            raw_data = event.get("raw_data", {})
            
            # Get a proper name identifier for the event
            resource_name = raw_data.get("metadata", {}).get("name", "")
            if not resource_name:
                # Fallback: combine involved object and reason
                involved_obj = raw_data.get("involvedObject", {})
                kind = involved_obj.get("kind", "")
                name = involved_obj.get("name", "")
                reason = raw_data.get("reason", "event")
                resource_name = f"{kind}-{name}-{reason}"
            
            # Get namespace
            namespace = event.get("namespace", "")
            
            # Show the detail using all available information
            if resource_name:
                # Pass the raw data to help with event lookup
                self.detail_manager.show_detail(resource_type, resource_name, namespace, raw_data)
            return
        resource_name = None
        namespace = None

        # Try to get the resource name from the table
        if hasattr(page.table, 'item') and page.table.item(row, 1) is not None:
            resource_name = page.table.item(row, 1).text()
        elif hasattr(page.table, 'cellWidget') and page.table.cellWidget(row, 1) is not None:
            widget = page.table.cellWidget(row, 1)
            for label in widget.findChildren(QLabel):
                if label.text() and not label.text().isspace():
                    resource_name = label.text()
                    break
        elif hasattr(page.table, 'item') and page.table.item(row, 0) is not None:
            resource_name = page.table.item(row, 0).text()
        else:
            resource_name = f"{resource_type}-{row}"
        
        # Try to get namespace (usually in column 2)
        if hasattr(page.table, 'item') and page.table.item(row, 2) is not None:
            namespace = page.table.item(row, 2).text()
        elif hasattr(page.table, 'cellWidget') and page.table.cellWidget(row, 2) is not None:
            widget = page.table.cellWidget(row, 2)
            for label in widget.findChildren(QLabel):
                if label.text() and not label.text().isspace():
                    namespace = label.text()
                    break
        
        # Handle special case for cluster-scoped resources and charts
        if resource_type in ['node', 'persistentvolume', 'clusterrole', 'clusterrolebinding', 'chart']:
            namespace = None
        
        # If this is a Charts page, call its specific view_details method instead
        if page_name == "Charts" and hasattr(page, '_handle_view_details'):
            page._handle_view_details(row)
            return
        
        # Show the detail page for non-chart resources
        if resource_name:
            self.detail_manager.show_detail(resource_type, resource_name, namespace)
    # Add to ClusterView.handle_resource_updated method
    def handle_resource_updated(self, resource_type, resource_name, namespace):
        """Handle when a resource is updated in the detail view"""
        # Find the corresponding page and reload its data
        page_name = resource_type + "s"  # Add 's' to get plural form
        
        if page_name in self.pages:
            page = self.pages[page_name]
            if hasattr(page, 'force_load_data'):
                page.force_load_data()
            elif hasattr(page, 'load_data'):
                page.load_data()
        
        # Special handling for Events page - always refresh
        if "Events" in self.pages:
            events_page = self.pages["Events"]
            if hasattr(events_page, 'force_load_data'):
                events_page.force_load_data()
            elif hasattr(events_page, 'load_data'):
                events_page.load_data()
    def update_detail_on_resize(self, event):
        """Update detail page position when window is resized"""
        super().resizeEvent(event)
        
        # Update detail page position if it's visible
        if hasattr(self, 'detail_manager'):
            self.detail_manager.update_detail_position()
        
        # Also update terminal position
        if hasattr(self, 'terminal_panel') and self.terminal_panel.is_visible:
            QTimer.singleShot(10, self.adjust_terminal_position)
    def update_detail_on_move(self, event):
        """Update detail page position when window is moved"""
        super().moveEvent(event)
        
        # Update detail page position if it's visible
        if hasattr(self, 'detail_manager'):
            self.detail_manager.update_detail_position()
        
        # Also update terminal position
        if hasattr(self, 'terminal_panel') and self.terminal_panel.is_visible:
            QTimer.singleShot(10, self.adjust_terminal_position)

    # Add to ClusterView.handle_page_change method
    def update_detail_on_page_change(self, page_widget):
        """Handle page changes to update detail page if needed"""
        # (existing code)
        
        # Hide detail view if different resource type
        if hasattr(self, 'detail_manager') and self.detail_manager.is_detail_visible():
            # Find the page name from our pages dictionary
            page_name = None
            for name, widget in self.pages.items():
                if widget == page_widget:
                    page_name = name
                    break
            
            if page_name:
                # Get current resource type being viewed
                resource_type = page_name.rstrip('s')  # Remove trailing 's' to get singular form
                
                # If resource type doesn't match current detail view, hide it
                if resource_type != self.detail_manager.current_resource_type:
                    self.detail_manager.hide_detail()
    

    # Add to ClusterView.closeEvent
    def update_close_event(self, event):
        """Clean up resources before closing"""
        if hasattr(self, 'detail_manager') and self.detail_manager.is_detail_visible():
            self.detail_manager.hide_detail()
        
        # (Existing code)
        if hasattr(self, 'terminal_panel') and self.terminal_panel.is_visible:
            self.terminal_panel.hide_terminal()
        super().closeEvent(event)
        
    def set_active_cluster(self, cluster_name):
        """Set the active cluster and update the UI accordingly"""
        # Avoid unnecessary reconnection to the same cluster
        if self.active_cluster == cluster_name:
            # Even if it's the same cluster, ensure UI is updated correctly
            return
            
        self.active_cluster = cluster_name
        
        # Check if there's cached data for this cluster
        if (hasattr(self, 'cluster_connector') and self.cluster_connector and 
            hasattr(self.cluster_connector, 'is_data_loaded') and
            self.cluster_connector.is_data_loaded(cluster_name)):
            
            # Get cached data
            cached_data = self.cluster_connector.get_cached_data(cluster_name)
            
            # Use cached data to update UI immediately
            if 'cluster_info' in cached_data:
                self.on_cluster_data_loaded(cached_data['cluster_info'])
            
            if 'metrics' in cached_data and hasattr(self, 'pages') and 'Cluster' in self.pages:
                # If we have the cluster_page, update its metrics directly
                self.pages["Cluster"].update_metrics(cached_data['metrics'])
            
            if 'issues' in cached_data and hasattr(self, 'pages') and 'Cluster' in self.pages:
                # If we have the cluster_page, update its issues directly
                self.pages["Cluster"].update_issues(cached_data['issues'])
            
            # Hide loading overlay since we already have the data
            if hasattr(self, 'loading_overlay'):
                self.loading_overlay.hide_loading()
            
            return
        
        # If we don't have cached data, show loading overlay and connect
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.show_loading(f"Loading cluster: {cluster_name}")
            self.loading_overlay.resize(self.size())
        
        # Connect to the cluster
        if hasattr(self, 'cluster_connector') and self.cluster_connector:
            self.cluster_connector.connect_to_cluster(cluster_name)
        else:
            self.on_error("Cluster connector not initialized")
            
    def on_connection_started(self, cluster_name):
        """Handle when a cluster connection starts"""
        if cluster_name == self.active_cluster:
            self.loading_overlay.show_loading(f"Connecting to cluster: {cluster_name}")
            self.loading_overlay.resize(self.size())
    
    def on_connection_complete(self, cluster_name, success):
        """Handle when a cluster connection completes"""
        if cluster_name == self.active_cluster:
            if success:
                self.loading_overlay.show_loading(f"Loading data from: {cluster_name}")
            else:
                self.loading_overlay.hide_loading()
                # Show error message
                if hasattr(self.parent_window, 'show_error_message'):
                    self.parent_window.show_error_message(f"Failed to connect to cluster: {cluster_name}")
    
    def on_cluster_data_loaded(self, cluster_info):
        """Handle when cluster data is loaded"""
        # Hide loading overlay
        self.loading_overlay.hide_loading()
    
    def on_error(self, error_message):
        """Handle error messages"""
        # Hide loading overlay
        self.loading_overlay.hide_loading()
        
        # Do NOT forward the error to parent_window
        # Just log it instead to avoid duplicate dialogs
        logging.warning(f"ClusterView received error: {error_message}")
    
    def setup_ui(self):
        """Set up the main UI components"""
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create sidebar
        self.sidebar = Sidebar(self)
        main_layout.addWidget(self.sidebar)
        
        # Create right side container (header + content)
        right_container = QWidget()
        right_container.setStyleSheet(f"background-color: {AppColors.BG_DARK};")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Create stacked widget for pages
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet(f"background-color: {AppColors.BG_DARK};")
        
        # Connect signal to handle page changes
        self.stacked_widget.currentChanged.connect(
            lambda index: self.handle_page_change(self.stacked_widget.widget(index))
        )
        
        # Create and add pages
        self.create_pages()
        
        right_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(right_container)
        
        # Set initial page
        self.stacked_widget.setCurrentWidget(self.pages["Cluster"])
    
    def initialize_terminal(self):
        """Initialize the terminal panel as a child of the main window"""
        # Create terminal but don't make it a child of any widget
        # This allows it to float independently
        self.terminal_panel = TerminalPanel(self.parent_window)
        
        # Connect terminal button in sidebar to toggle terminal
        for btn in self.sidebar.nav_buttons:
            if btn.item_text == "Terminal":
                # Disconnect any existing connections
                try:
                    btn.clicked.disconnect()
                except TypeError:
                    pass  # No connections to disconnect
                
                # Connect to our toggle function
                btn.clicked.connect(self.toggle_terminal)
                break
        
        # Connect sidebar toggle to update terminal position
        self.sidebar.toggle_btn.clicked.connect(self.update_terminal_on_sidebar_toggle)
    
    def update_terminal_on_sidebar_toggle(self):
        """Update terminal position and size when sidebar is toggled"""
        # Add a short delay to allow sidebar animation to complete
        QTimer.singleShot(250, self.adjust_terminal_position)
        
        # Notify terminal panel about the sidebar state change
        if hasattr(self, 'terminal_panel'):
            self.terminal_panel.sidebar_width = self.sidebar.width()
        
    def toggle_terminal(self):
        """Toggle the terminal visibility and update its position/size"""
        self.terminal_panel.toggle_terminal()
        
        # If terminal became visible, adjust its position and size
        if self.terminal_panel.is_visible:
            self.adjust_terminal_position()
    
    def adjust_terminal_position(self):
        """Adjust terminal position and size based on sidebar state"""
        if hasattr(self, 'terminal_panel') and self.terminal_panel.is_visible:
            # Get main window width and height
            parent_width = self.parent_window.width()
            parent_height = self.parent_window.height()
            
            # Get sidebar width based on its expanded state
            sidebar_width = self.sidebar.width()
            
            # Calculate terminal width (only cover area to the right of sidebar)
            terminal_width = parent_width - sidebar_width
            
            # Set terminal width
            self.terminal_panel.setFixedWidth(terminal_width)
            
            # Position terminal at bottom-right, ensuring it's placed next to sidebar
            self.terminal_panel.move(sidebar_width, 
                                    parent_height - self.terminal_panel.height())
            
            # Bring terminal to front
            self.terminal_panel.raise_()
    
    def resizeEvent(self, event):
        """Handle resize event to update loading overlay size"""
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(self.size())
    
    def eventFilter(self, obj, event):
        """Handle events for window resize and detail page interaction"""
        if obj == self and event.type() == event.Type.Resize:
            # When window is resized, adjust terminal position
            if hasattr(self, 'terminal_panel') and self.terminal_panel.is_visible:
                self.adjust_terminal_position()
            
            # Also update detail page position if visible
            if hasattr(self, 'detail_manager') and self.detail_manager.is_detail_visible():
                self.detail_manager.update_detail_position()
        
        return super().eventFilter(obj, event)
    def create_pages(self):
        """Create all page components and add them to the stacked widget"""
        # Create pages
        self.cluster_page = ClusterPage()
        self.nodes_page = NodesPage()
        self.overview_page = OverviewPage()
        self.pods_page = PodsPage()
        self.deployments_page = DeploymentsPage()
        self.daemonsets_page = DaemonSetsPage()
        self.statfulsets_page = StatefulSetsPage()
        self.replicasets_page = ReplicaSetsPage()
        self.replicationcontrollers_page = ReplicaControllersPage()
        self.jobs_page = JobsPage()
        self.cronjobs_page = CronJobsPage()

        self.configmaps_page = ConfigMapsPage()
        self.secrets_page = SecretsPage()
        self.resourcequotas_page = ResourceQuotasPage()
        self.limitranges_page = LimitRangesPage()
        self.horizontalpodautoscalers_page = HorizontalPodAutoscalersPage()
        self.poddisruptionbudgets_page = PodDisruptionBudgetsPage()
        self.priorityclasses_page = PriorityClassesPage()
        self.runtimeclasses_page = RuntimeClassesPage()
        self.leases_page = LeasesPage()
        self.mutatingwebhookconfigs_page = MutatingWebhookConfigsPage()
        self.validatingwebhookconfigs_page = ValidatingWebhookConfigsPage()

        self.services_page = ServicesPage()
        self.endpoints_page = EndpointsPage()
        self.ingresses_page = IngressesPage()
        self.ingressclasses_page = IngressClassesPage()
        self.networkpolicies_page = NetworkPoliciesPage()
        self.portforwarding_page = PortForwardingPage()

        self.persistentvolumeclaims_page = PersistentVolumeClaimsPage()
        self.persistentvolumes_page = PersistentVolumesPage()
        self.storageclasses_page = StorageClassesPage()

        self.serviceaccounts_page = ServiceAccountsPage()
        self.clusterroles_page = ClusterRolesPage()
        self.roles_page = RolesPage()
        self.clusterrolebindings_page = ClusterRoleBindingsPage()
        self.rolebindings_page = RoleBindingsPage()

        self.charts_page = ChartsPage()
        self.releases_page = ReleasesPage()

        self.definitions_page = DefinitionsPage()

        self.events_page = EventsPage()

        self.namespace_page = NamespacesPage()

        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.cluster_page)
        self.stacked_widget.addWidget(self.nodes_page)
        self.stacked_widget.addWidget(self.overview_page)
        self.stacked_widget.addWidget(self.pods_page)
        self.stacked_widget.addWidget(self.deployments_page)
        self.stacked_widget.addWidget(self.daemonsets_page)
        self.stacked_widget.addWidget(self.statfulsets_page)
        self.stacked_widget.addWidget(self.replicasets_page)
        self.stacked_widget.addWidget(self.replicationcontrollers_page)
        self.stacked_widget.addWidget(self.jobs_page)
        self.stacked_widget.addWidget(self.cronjobs_page)

        self.stacked_widget.addWidget(self.configmaps_page)
        self.stacked_widget.addWidget(self.secrets_page)
        self.stacked_widget.addWidget(self.resourcequotas_page)
        self.stacked_widget.addWidget(self.limitranges_page)
        self.stacked_widget.addWidget(self.horizontalpodautoscalers_page)
        self.stacked_widget.addWidget(self.poddisruptionbudgets_page)
        self.stacked_widget.addWidget(self.priorityclasses_page)
        self.stacked_widget.addWidget(self.runtimeclasses_page)
        self.stacked_widget.addWidget(self.leases_page)
        self.stacked_widget.addWidget(self.mutatingwebhookconfigs_page)
        self.stacked_widget.addWidget(self.validatingwebhookconfigs_page)

        self.stacked_widget.addWidget(self.services_page)
        self.stacked_widget.addWidget(self.endpoints_page)
        self.stacked_widget.addWidget(self.ingresses_page)
        self.stacked_widget.addWidget(self.ingressclasses_page)
        self.stacked_widget.addWidget(self.networkpolicies_page)
        self.stacked_widget.addWidget(self.portforwarding_page)

        self.stacked_widget.addWidget(self.persistentvolumeclaims_page)
        self.stacked_widget.addWidget(self.persistentvolumes_page)
        self.stacked_widget.addWidget(self.storageclasses_page)

        self.stacked_widget.addWidget(self.serviceaccounts_page)
        self.stacked_widget.addWidget(self.clusterroles_page)
        self.stacked_widget.addWidget(self.roles_page)
        self.stacked_widget.addWidget(self.clusterrolebindings_page)
        self.stacked_widget.addWidget(self.rolebindings_page)

        self.stacked_widget.addWidget(self.charts_page)
        self.stacked_widget.addWidget(self.releases_page)

        self.stacked_widget.addWidget(self.definitions_page)

        self.stacked_widget.addWidget(self.events_page)
        
        self.stacked_widget.addWidget(self.namespace_page)

        # Register pages in dictionary for easy access
        self.pages["Cluster"] = self.cluster_page
        self.pages["Nodes"] = self.nodes_page
        self.pages["Overview"] = self.overview_page
        self.pages["Pods"] = self.pods_page
        self.pages["Deployments"] = self.deployments_page
        self.pages["Daemon Sets"] = self.daemonsets_page
        self.pages["Stateful Sets"] = self.statfulsets_page
        self.pages["Replica Sets"] = self.replicasets_page
        self.pages["Replication Controllers"] = self.replicationcontrollers_page
        self.pages["Jobs"] = self.jobs_page
        self.pages["Cron Jobs"] = self.cronjobs_page

        self.pages["Config Maps"] = self.configmaps_page
        self.pages["Secrets"] = self.secrets_page
        self.pages["Resource Quotas"] = self.resourcequotas_page
        self.pages["Limit Ranges"] = self.limitranges_page
        self.pages["Horizontal Pod Autoscalers"] = self.horizontalpodautoscalers_page
        self.pages["Pod Disruption Budgets"] = self.poddisruptionbudgets_page
        self.pages["Priority Classes"] = self.priorityclasses_page
        self.pages["Runtime Classes"] = self.runtimeclasses_page
        self.pages["Leases"] = self.leases_page
        self.pages["Mutating Webhook Configs"] = self.mutatingwebhookconfigs_page
        self.pages["Validating Webhook Configs"] = self.validatingwebhookconfigs_page

        self.pages["Services"] = self.services_page
        self.pages["Endpoints"] = self.endpoints_page
        self.pages["Ingresses"] = self.ingresses_page
        self.pages["Ingress Classes"] = self.ingressclasses_page
        self.pages["Network Policies"] = self.networkpolicies_page
        self.pages["Port Forwarding"] = self.portforwarding_page

        self.pages["Persistent Volume Claims"] = self.persistentvolumeclaims_page
        self.pages["Persistent Volumes"] = self.persistentvolumes_page
        self.pages["Storage Classes"] = self.storageclasses_page

        self.pages["Service Accounts"] = self.serviceaccounts_page
        self.pages["Cluster Roles"] = self.clusterroles_page
        self.pages["Roles"] = self.roles_page
        self.pages["Cluster Role Bindings"] = self.clusterrolebindings_page
        self.pages["Role Bindings"] = self.rolebindings_page

        self.pages["Charts"] = self.charts_page
        self.pages["Releases"] = self.releases_page

        self.pages["Definitions"] = self.definitions_page

        self.pages["Events"] = self.events_page
        self.pages["Namespaces"] = self.namespace_page
    
    def handle_page_change(self, page_widget):
        """
        Update the sidebar selection based on the current page and trigger data loading.
        Called whenever a page change happens from any source.
        """
        # Close detail page when changing pages 
       
        if hasattr(self, 'detail_manager') and self.detail_manager.is_detail_visible():
            self.detail_manager.hide_detail()
        
        # Find the page name from our pages dictionary
        page_name = None
        for name, widget in self.pages.items():
            if widget == page_widget:
                page_name = name
                break
        
        if not page_name:
            return  # Page not found in our dictionary
        
        # Determine if this is a child of a dropdown menu
        parent_menu = None
        dropdown_menus = {
            "Workloads": ["Overview", "Pods", "Deployments", "Daemon Sets", 
                        "Stateful Sets", "Replica Sets", "Replication Controllers", 
                        "Jobs", "Cron Jobs"],
            "Config": ["Config Maps", "Secrets", "Resource Quotas", "Limit Ranges",
                    "Horizontal Pod Autoscalers", "Pod Disruption Budgets",
                    "Priority Classes", "Runtime Classes", "Leases", 
                    "Mutating Webhook Configs", "Validating Webhook Configs"],
            "Network": ["Services", "Endpoints", "Ingresses", "Ingress Classes",
                    "Network Policies", "Port Forwarding"],
            "Storage": ["Persistent Volume Claims", "Persistent Volumes", "Storage Classes"],
            "Access Control": ["Service Accounts", "Cluster Roles", "Roles",
                            "Cluster Role Bindings", "Role Bindings"],
            "Custom Resources": ["Definitions"],
            "Helm": ["Releases", "Charts"]
        }
        
        # Find which dropdown menu this page belongs to
        for menu, items in dropdown_menus.items():
            if page_name in items:
                parent_menu = menu
                break
        
        # Reset all navigation button states first
        for btn in self.sidebar.nav_buttons:
            # Reset active state but preserve dropdown open state
            dropdown_state = getattr(btn, 'dropdown_open', False)
            btn.is_active = False
            # Ensure the dropdown_open attribute exists before setting it
            if hasattr(btn, 'dropdown_open'):
                btn.dropdown_open = dropdown_state  # Keep dropdown open state unchanged
        
        # Now set the correct button as active based on the current page
        if parent_menu:
            # For pages that are part of a dropdown menu, set the parent as active
            for btn in self.sidebar.nav_buttons:
                if btn.item_text == parent_menu:
                    btn.is_active = True
                    break
        else:
            # For direct pages, set that specific button as active
            for btn in self.sidebar.nav_buttons:
                if btn.item_text == page_name:
                    btn.is_active = True
                    break
        
        # Update the visual appearance of all buttons
        for btn in self.sidebar.nav_buttons:
            btn.update_style()

        QTimer.singleShot(50, lambda: self._delayed_load_data(page_widget))
        

    def _delayed_load_data(self, page_widget, active_button=None):
        """Helper method to delay data loading to allow UI to update first"""
        # Check if this is a resource page with skeleton loading capability
        if hasattr(page_widget, '_show_skeleton_loader') and hasattr(page_widget, 'force_load_data'):
            page_widget.force_load_data()
        # For other page types with force_load_data
        elif hasattr(page_widget, 'force_load_data'):
            page_widget.force_load_data()
        # For page types with regular load_data
        elif hasattr(page_widget, 'load_data'):
            page_widget.load_data()
            
        # Hide loading indicator after a delay
        if active_button and hasattr(active_button, 'hide_loading_state'):
            QTimer.singleShot(1000, active_button.hide_loading_state)

    def set_active_nav_button(self, active_button):
        """Handle sidebar navigation button clicks with loading indication"""
        # Special handling for Terminal button - don't change active state
        if active_button.item_text == "Terminal":
            return
        
        # Close detail page when navigating to a different section
        if hasattr(self, 'detail_manager') and self.detail_manager.is_detail_visible():
            self.detail_manager.hide_detail()
        
        # Important: Don't modify active_button.item_text! Keep it as the original key
        button_text = active_button.item_text  # Get clean text without loading symbols
        
        # For non-dropdown buttons, switch to the page
        if not active_button.has_dropdown and button_text in self.pages:
            # Show loading state in the button
            # if hasattr(active_button, 'show_loading_state'):
            #     active_button.show_loading_state()
            
            # Switch to the page - use original text as key
            self.stacked_widget.setCurrentWidget(self.pages[button_text])
            
            # Force data loading with skeleton for resource pages
            page_widget = self.pages[button_text]
            QTimer.singleShot(50, lambda: self._delayed_load_data(page_widget, active_button))
        else:
            # For dropdown buttons, just update their visual state
            # but don't consider them "active" in terms of navigation
            for btn in self.sidebar.nav_buttons:
                # Only reset dropdown open state for other dropdown buttons
                if btn != active_button and btn.has_dropdown and hasattr(btn, 'dropdown_open'):
                    btn.dropdown_open = False
            
            # Make sure all buttons have updated styles
            for btn in self.sidebar.nav_buttons:
                btn.update_style()
    def handle_dropdown_selection(self, item_name):
        """Handle dropdown menu selections with detail page management"""
        # Close detail page when navigating to a different section via dropdown
        if hasattr(self, 'detail_manager') and self.detail_manager.is_detail_visible():
            self.detail_manager.hide_detail()
        
        if item_name in self.pages:
            # When a dropdown item is selected, switch to that page
            self.stacked_widget.setCurrentWidget(self.pages[item_name])
            
            # Explicitly load data for the page that was just selected
            if hasattr(self.pages[item_name], 'force_load_data'):
                self.pages[item_name].force_load_data()
            elif hasattr(self.pages[item_name], 'load_data'):
                self.pages[item_name].load_data()
            
            # The page change will trigger currentChanged signal
            # which will call handle_page_change to update sidebar selection
            
            # Find the dropdown button that was open and close its visual state
            for btn in self.sidebar.nav_buttons:
                # Check if the button has the dropdown_open attribute and it's True
                if hasattr(btn, 'dropdown_open') and btn.dropdown_open:
                    btn.dropdown_open = False
                    btn.update_style()
    def showEvent(self, event):
        """Handle show event - update terminal position if needed and sync sidebar state"""
        super().showEvent(event)
        if hasattr(self, 'terminal_panel') and self.terminal_panel.is_visible:
            self.adjust_terminal_position()
                
        # If we have an active cluster, make sure loading overlay is sized correctly
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(self.size())
        
        # Sync the sidebar selection with the current page
        if hasattr(self, 'stacked_widget') and hasattr(self, 'sidebar'):
            current_widget = self.stacked_widget.currentWidget()
            if current_widget:
                self.handle_page_change(current_widget)