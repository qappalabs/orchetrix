from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from UI.Sidebar import Sidebar
from UI.Header import Header
from UI.Styles import AppColors, AppStyles
from UI.TerminalPanel import TerminalPanel

# Import cluster pages
from Pages.ClusterPage import ClusterPage
from Pages.NodesPage import NodesPage
from Pages.EventsPage import EventPage
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
from Pages.Helm.ReleasesPage import ReleasesPage

# Custome Resource Pages
from Pages.CustomResources.DefinitionsPage import DefinitionsPage




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
        self.active_cluster = "docker-desktop"
        
        self.setup_ui()
        
        # Initialize the terminal panel
        self.initialize_terminal()
        
        # Install event filter to detect window resize events
        self.installEventFilter(self)
    
    def setup_ui(self):
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
        
        # Create header
        self.header = Header(self)
        right_layout.addWidget(self.header)
        
        # Create stacked widget for pages
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet(f"background-color: {AppColors.BG_DARK};")
        
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
    def eventFilter(self, obj, event):
        """Handle events for window resize"""
        if obj == self and event.type() == event.Type.Resize:
            # When window is resized, adjust terminal position
            if hasattr(self, 'terminal_panel') and self.terminal_panel.is_visible:
                self.adjust_terminal_position()
        
        return super().eventFilter(obj, event)
    
    def create_pages(self):
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

        self.releases_page = ReleasesPage()

        self.definitions_page = DefinitionsPage()

        self.events_page = EventPage()

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

        self.pages["Releases"] = self.releases_page

        self.pages["Definitions"] = self.definitions_page


        self.pages["Events"] = self.events_page
        self.pages["Namespaces"] = self.namespace_page
    
    def set_active_nav_button(self, active_button):
        """Handle sidebar navigation button clicks"""
        # Special handling for Terminal button - don't change active state
        if active_button.item_text == "Terminal":
            return
            
        for btn in self.sidebar.nav_buttons:
            btn.is_active = False
            btn.update_style()
        active_button.is_active = True
        active_button.update_style()
            
        # Switch to the corresponding page
        if active_button.item_text in self.pages:
            self.stacked_widget.setCurrentWidget(self.pages[active_button.item_text])
    
    def handle_dropdown_selection(self, item_name):
        """Handle dropdown menu selections"""
        if item_name in self.pages:
            self.stacked_widget.setCurrentWidget(self.pages[item_name])
            
            # Find and set the correct nav button as active
            if item_name == "Overview" or item_name in ["Pods", "Deployments", "Daemon Sets",
                                                    "Stateful Sets", "Replica Sets",
                                                    "Replication Controllers", "Jobs", "Cron Jobs"]:
                # Set Workloads nav button as active
                for btn in self.sidebar.nav_buttons:
                    if btn.item_text == "Workloads":
                        btn.is_active = True
                        btn.update_style()
                    else:
                        btn.is_active = False
                        btn.update_style()
    
    def set_active_cluster(self, cluster_name):
        """Set the active cluster and update the UI accordingly"""
        self.active_cluster = cluster_name
        
        # Update header cluster name
        if hasattr(self.header, 'cluster_dropdown'):
            # Find the text label within the cluster dropdown layout
            found = False
            for child in self.header.cluster_dropdown.findChildren(QLabel):
                if not child.text().startswith("▼"):  # Skip the arrow label
                    child.setText(cluster_name)
                    child.setStyleSheet(f"color: {AppColors.ACCENT_GREEN}; background: transparent;")
                    found = True
                    break
            
            if not found:
                print("Could not find cluster name label in header")
                
    def showEvent(self, event):
        """Handle show event - update terminal position if needed"""
        super().showEvent(event)
        if hasattr(self, 'terminal_panel') and self.terminal_panel.is_visible:
            self.adjust_terminal_position()