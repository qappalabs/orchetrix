from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QPointF
from PyQt6.QtGui import QColor, QPainter, QBrush
from typing import Dict, Optional, Tuple, Any
import math
import logging

from .DetailManager import DetailManager
from UI.Sidebar import Sidebar
from UI.Styles import AppColors
from UI.TerminalPanel import TerminalPanel
from utils.cluster_connector import get_cluster_connector

# Import all page classes (required for PyInstaller compatibility)
from Pages.ClusterPage import ClusterPage
from Pages.NodesPage import NodesPage
from Pages.EventsPage import EventsPage
from Pages.NamespacesPage import NamespacesPage

# Workload pages
from Pages.WorkLoad.OverviewPage import OverviewPage
from Pages.WorkLoad.PodsPage import PodsPage
from Pages.WorkLoad.DeploymentsPage import DeploymentsPage
from Pages.WorkLoad.StatefulSetsPage import StatefulSetsPage
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

# Access Control pages
from Pages.AccessControl.ServiceAccountsPage import ServiceAccountsPage
from Pages.AccessControl.ClusterRolesPage import ClusterRolesPage
from Pages.AccessControl.RolesPage import RolesPage
from Pages.AccessControl.ClusterRoleBindingsPage import ClusterRoleBindingsPage
from Pages.AccessControl.RoleBinidingsPage import RoleBindingsPage

# Helm pages
from Pages.Helm.ChartsPage import ChartsPage
from Pages.Helm.ReleasesPage import ReleasesPage

# Custom Resource pages
from Pages.CustomResources.DefinitionsPage import DefinitionsPage

# Page configuration with direct class references (PyInstaller compatible)
PAGE_CONFIG = {
    # Core pages
    'Cluster': ClusterPage,
    'Nodes': NodesPage,
    'Events': EventsPage,
    'Namespaces': NamespacesPage,
    
    # Workload pages
    'Overview': OverviewPage,
    'Pods': PodsPage,
    'Deployments': DeploymentsPage,
    'Stateful Sets': StatefulSetsPage,
    'Daemon Sets': DaemonSetsPage,
    'Replica Sets': ReplicaSetsPage,
    'Replication Controllers': ReplicaControllersPage,
    'Jobs': JobsPage,
    'Cron Jobs': CronJobsPage,
    
    # Config pages
    'Config Maps': ConfigMapsPage,
    'Secrets': SecretsPage,
    'Resource Quotas': ResourceQuotasPage,
    'Limit Ranges': LimitRangesPage,
    'Horizontal Pod Autoscalers': HorizontalPodAutoscalersPage,
    'Pod Disruption Budgets': PodDisruptionBudgetsPage,
    'Priority Classes': PriorityClassesPage,
    'Runtime Classes': RuntimeClassesPage,
    'Leases': LeasesPage,
    'Mutating Webhook Configs': MutatingWebhookConfigsPage,
    'Validating Webhook Configs': ValidatingWebhookConfigsPage,
    
    # Network pages
    'Services': ServicesPage,
    'Endpoints': EndpointsPage,
    'Ingresses': IngressesPage,
    'Ingress Classes': IngressClassesPage,
    'Network Policies': NetworkPoliciesPage,
    'Port Forwarding': PortForwardingPage,
    
    # Storage pages
    'Persistent Volume Claims': PersistentVolumeClaimsPage,
    'Persistent Volumes': PersistentVolumesPage,
    'Storage Classes': StorageClassesPage,
    
    # Access Control pages
    'Service Accounts': ServiceAccountsPage,
    'Cluster Roles': ClusterRolesPage,
    'Roles': RolesPage,
    'Cluster Role Bindings': ClusterRoleBindingsPage,
    'Role Bindings': RoleBindingsPage,
    
    # Helm pages
    'Charts': ChartsPage,
    'Releases': ReleasesPage,
    
    # Custom Resource pages
    'Definitions': DefinitionsPage,
}

# Dropdown menu configuration
DROPDOWN_MENUS = {
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

# Cluster-scoped resources that don't have namespaces
CLUSTER_SCOPED_RESOURCES = {
    'node', 'persistentvolume', 'clusterrole', 
    'clusterrolebinding', 'chart'
}


class LoadingOverlay(QWidget):
    """Optimized loading overlay with animation"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_animation()
        
    def _setup_ui(self) -> None:
        """Setup the UI components"""
        self.setObjectName("loadingOverlay")
        self.setStyleSheet(f"""
            #loadingOverlay {{
                background-color: rgba(20, 20, 20, 0.8);
            }}
            QLabel {{
                color: white;
                font-size: 18px;
                font-weight: bold;
            }}
        """)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.spinner_label = QLabel()
        self.spinner_label.setMinimumSize(64, 64)
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.message = QLabel("Connecting to cluster...")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.spinner_label)
        layout.addWidget(self.message)
        
        self.hide()
    
    def _setup_animation(self) -> None:
        """Setup the spinner animation"""
        self.spinner_angle = 0
        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self._update_spinner)
    
    def _update_spinner(self) -> None:
        """Update the spinner animation"""
        self.spinner_angle = (self.spinner_angle + 10) % 360
        self.update()
    
    def paintEvent(self, event) -> None:
        """Paint the loading spinner"""
        super().paintEvent(event)
        
        if not self.isVisible():
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.spinner_label.geometry()
        center = QPoint(rect.center().x(), rect.center().y())
        radius = min(rect.width(), rect.height()) / 2 - 5
        
        # Draw 12 dots with varying opacity
        for i in range(12):
            angle = (self.spinner_angle - i * 30) % 360
            angle_rad = angle * 3.14159 / 180.0
            
            opacity = 0.2 + 0.8 * ((12 - i) % 12) / 12
            
            x = center.x() + radius * 0.8 * math.cos(angle_rad)
            y = center.y() + radius * 0.8 * math.sin(angle_rad)
            
            color = QColor(AppColors.ACCENT_GREEN)
            color.setAlphaF(opacity)
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, y), 5, 5)
    
    def show_loading(self, message: str = "Connecting to cluster...") -> None:
        """Show loading overlay with custom message"""
        self.message.setText(message)
        self.spinner_timer.start(50)
        self.show()
        self.raise_()
    
    def hide_loading(self) -> None:
        """Hide loading overlay"""
        self.spinner_timer.stop()
        self.hide()


class ClusterView(QWidget):
    """
    Optimized ClusterView with lazy loading and improved performance.
    The ClusterView contains the cluster-specific sidebar and pages.
    """
    
    switch_to_home_signal = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.parent_window = parent
        
        # Initialize core attributes
        self.pages: Dict[str, QWidget] = {}
        self._loaded_pages: Dict[str, bool] = {}
        self.active_cluster: Optional[str] = None
        
        # Initialize detail manager first (doesn't depend on UI)
        self._initialize_detail_manager()
        
        # Setup cluster connector
        self._setup_cluster_connector()
        
        # Setup UI (creates sidebar and other components)
        self._setup_ui()
        self._setup_loading_overlay()
        
        # Initialize terminal after UI is ready (needs sidebar)
        self._initialize_terminal()
        
        # Install event filter
        self.installEventFilter(self)
    
    def _setup_cluster_connector(self) -> None:
        """Setup cluster connector and signals"""
        self.cluster_connector = get_cluster_connector()
        
        # Connect signals
        signal_mappings = [
            (self.cluster_connector.connection_started, self._on_connection_started),
            (self.cluster_connector.connection_complete, self._on_connection_complete),
            (self.cluster_connector.cluster_data_loaded, self._on_cluster_data_loaded),
            (self.cluster_connector.error_occurred, self._on_error)
        ]
        
        for signal, slot in signal_mappings:
            signal.connect(slot)
    
    def _setup_ui(self) -> None:
        """Setup the main UI components"""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {AppColors.BG_DARK};
                color: {AppColors.TEXT_LIGHT};
            }}
        """)
        
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create sidebar
        self.sidebar = Sidebar(self)
        main_layout.addWidget(self.sidebar)
        
        # Create right container
        right_container = self._create_right_container()
        main_layout.addWidget(right_container)
        
        # Set initial page
        self._ensure_page_loaded('Cluster')
        self.stacked_widget.setCurrentWidget(self.pages["Cluster"])
    
    def _create_right_container(self) -> QWidget:
        """Create the right side container with stacked widget"""
        right_container = QWidget()
        right_container.setStyleSheet(f"background-color: {AppColors.BG_DARK};")
        
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Create stacked widget
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet(f"background-color: {AppColors.BG_DARK};")
        self.stacked_widget.currentChanged.connect(
            lambda index: self.handle_page_change(self.stacked_widget.widget(index))
        )
        
        right_layout.addWidget(self.stacked_widget)
        return right_container
    
    def _setup_loading_overlay(self) -> None:
        """Setup loading overlay"""
        self.loading_overlay = LoadingOverlay(self)
    
    def _initialize_detail_manager(self) -> None:
        """Initialize the detail page manager"""
        self.detail_manager = DetailManager(self.parent_window)
        self.detail_manager.resource_updated.connect(self._handle_resource_updated)
    
    def _initialize_terminal(self) -> None:
        """Initialize the terminal panel"""
        self.terminal_panel = TerminalPanel(self.parent_window)
        
        # Connect terminal button (sidebar should exist by now)
        self._connect_terminal_button()
        
        # Connect sidebar toggle (sidebar should exist by now)
        if hasattr(self, 'sidebar') and hasattr(self.sidebar, 'toggle_btn'):
            self.sidebar.toggle_btn.clicked.connect(self._update_terminal_on_sidebar_toggle)
    
    def _connect_terminal_button(self) -> None:
        """Connect terminal button in sidebar"""
        # Safety check - ensure sidebar exists
        if not hasattr(self, 'sidebar') or not hasattr(self.sidebar, 'nav_buttons'):
            return
            
        for btn in self.sidebar.nav_buttons:
            if btn.item_text == "Terminal":
                try:
                    btn.clicked.disconnect()
                except TypeError:
                    pass
                btn.clicked.connect(self.toggle_terminal)
                break
    
    def _lazy_load_page(self, page_name: str) -> QWidget:
        """Lazy load a page when first accessed (PyInstaller compatible)"""
        if page_name in self.pages:
            return self.pages[page_name]
        
        if page_name not in PAGE_CONFIG:
            raise ValueError(f"Unknown page: {page_name}")
        
        try:
            # Get the page class directly (no dynamic import needed)
            page_class = PAGE_CONFIG[page_name]
            
            # Create page instance
            page = page_class()
            
            # Add to stacked widget and store reference
            self.stacked_widget.addWidget(page)
            self.pages[page_name] = page
            self._loaded_pages[page_name] = True
            
            return page
            
        except Exception as e:
            logging.error(f"Failed to load page {page_name}: {e}")
            # Return a placeholder or raise
            raise
    
    def _ensure_page_loaded(self, page_name: str) -> QWidget:
        """Ensure a page is loaded and return it"""
        if page_name not in self._loaded_pages:
            return self._lazy_load_page(page_name)
        return self.pages[page_name]
    
    def _get_resource_info_from_table(self, page, row: int) -> Tuple[Optional[str], Optional[str]]:
        """Extract resource name and namespace from table row"""
        resource_name = None
        namespace = None
        
        # Try to get resource name (usually column 1)
        if hasattr(page.table, 'item') and page.table.item(row, 1):
            resource_name = page.table.item(row, 1).text()
        elif hasattr(page.table, 'cellWidget') and page.table.cellWidget(row, 1):
            widget = page.table.cellWidget(row, 1)
            for label in widget.findChildren(QLabel):
                if label.text() and not label.text().isspace():
                    resource_name = label.text()
                    break
        elif hasattr(page.table, 'item') and page.table.item(row, 0):
            resource_name = page.table.item(row, 0).text()
        
        # Try to get namespace (usually column 2)
        if hasattr(page.table, 'item') and page.table.item(row, 2):
            namespace = page.table.item(row, 2).text()
        elif hasattr(page.table, 'cellWidget') and page.table.cellWidget(row, 2):
            widget = page.table.cellWidget(row, 2)
            for label in widget.findChildren(QLabel):
                if label.text() and not label.text().isspace():
                    namespace = label.text()
                    break
        
        return resource_name, namespace
    
    def _handle_special_event_detail(self, page, row: int) -> bool:
        """Handle special case for Events page detail view"""
        if not (hasattr(page, 'resources') and row < len(page.resources)):
            return False
        
        event = page.resources[row]
        raw_data = event.get("raw_data", {})
        
        # Get event identifier
        resource_name = raw_data.get("metadata", {}).get("name", "")
        if not resource_name:
            involved_obj = raw_data.get("involvedObject", {})
            kind = involved_obj.get("kind", "")
            name = involved_obj.get("name", "")
            reason = raw_data.get("reason", "event")
            resource_name = f"{kind}-{name}-{reason}"
        
        namespace = event.get("namespace", "")
        
        if resource_name:
            self.detail_manager.show_detail("event", resource_name, namespace, raw_data)
            return True
        
        return False
    
    def _get_parent_menu(self, page_name: str) -> Optional[str]:
        """Get the parent dropdown menu for a page"""
        for menu, items in DROPDOWN_MENUS.items():
            if page_name in items:
                return menu
        return None
    
    def _reset_navigation_states(self) -> None:
        """Reset all navigation button states"""
        for btn in self.sidebar.nav_buttons:
            dropdown_state = getattr(btn, 'dropdown_open', False)
            btn.is_active = False
            if hasattr(btn, 'dropdown_open'):
                btn.dropdown_open = dropdown_state
    
    def _set_active_navigation(self, page_name: str) -> None:
        """Set the correct navigation button as active"""
        parent_menu = self._get_parent_menu(page_name)
        target_name = parent_menu if parent_menu else page_name
        
        for btn in self.sidebar.nav_buttons:
            if btn.item_text == target_name:
                btn.is_active = True
                break
        
        # Update button styles
        for btn in self.sidebar.nav_buttons:
            btn.update_style()
    
    def _load_page_data(self, page_widget: QWidget) -> None:
        """Load data for a page widget"""
        if hasattr(page_widget, '_show_skeleton_loader') and hasattr(page_widget, 'force_load_data'):
            page_widget.force_load_data()
        elif hasattr(page_widget, 'force_load_data'):
            page_widget.force_load_data()
        elif hasattr(page_widget, 'load_data'):
            page_widget.load_data()
    
    def _update_cached_cluster_data(self, cluster_name: str) -> bool:
        """Update UI with cached cluster data if available"""
        if not (hasattr(self.cluster_connector, 'is_data_loaded') and 
                self.cluster_connector.is_data_loaded(cluster_name)):
            return False
        
        cached_data = self.cluster_connector.get_cached_data(cluster_name)
        
        # Update cluster info
        if 'cluster_info' in cached_data:
            self._on_cluster_data_loaded(cached_data['cluster_info'])
        
        # Update cluster page if loaded
        if 'Cluster' in self.pages:
            cluster_page = self.pages['Cluster']
            if 'metrics' in cached_data:
                cluster_page.update_metrics(cached_data['metrics'])
            if 'issues' in cached_data:
                cluster_page.update_issues(cached_data['issues'])
        
        self.loading_overlay.hide_loading()
        return True
    
    # Public API methods
    def set_active_cluster(self, cluster_name: str) -> None:
        """Set the active cluster and update the UI accordingly"""
        if self.active_cluster == cluster_name:
            return
        
        self.active_cluster = cluster_name
        
        # Try to use cached data first
        if self._update_cached_cluster_data(cluster_name):
            return
        
        # Show loading and connect to cluster
        self.loading_overlay.show_loading(f"Loading cluster: {cluster_name}")
        self.loading_overlay.resize(self.size())
        
        if self.cluster_connector:
            self.cluster_connector.connect_to_cluster(cluster_name)
        else:
            self._on_error("Cluster connector not initialized")
    
    def show_detail_for_table_item(self, row: int, col: int, page, page_name: str) -> None:
        """Show detail page for clicked table item"""
        # Safety check
        if not hasattr(self, 'detail_manager'):
            return
            
        # Handle special cases first
        if page_name == "Events" and self._handle_special_event_detail(page, row):
            return
        
        if page_name == "Charts" and hasattr(page, '_handle_view_details'):
            page._handle_view_details(row)
            return
        
        # Standard resource handling
        resource_type = "chart" if page_name == "Charts" else page_name.rstrip('s')
        if page_name == "Releases":
            resource_type = "helmrelease"
        
        resource_name, namespace = self._get_resource_info_from_table(page, row)
        
        if not resource_name:
            resource_name = f"{resource_type}-{row}"
        
        # Handle cluster-scoped resources
        if resource_type in CLUSTER_SCOPED_RESOURCES:
            namespace = None
        
        if resource_name:
            self.detail_manager.show_detail(resource_type, resource_name, namespace)
    
    def handle_page_change(self, page_widget: QWidget) -> None:
        """Handle page changes with optimized performance"""
        # Close detail page (with safety check)
        if hasattr(self, 'detail_manager') and self.detail_manager.is_detail_visible():
            self.detail_manager.hide_detail()
        
        # Find page name
        page_name = None
        for name, widget in self.pages.items():
            if widget == page_widget:
                page_name = name
                break
        
        if not page_name:
            return
        
        # Update navigation
        self._reset_navigation_states()
        self._set_active_navigation(page_name)
        
        # Load data with delay to allow UI update
        QTimer.singleShot(50, lambda: self._load_page_data(page_widget))
    
    def set_active_nav_button(self, active_button) -> None:
        """Handle sidebar navigation button clicks"""
        if active_button.item_text == "Terminal":
            return
        
        if hasattr(self, 'detail_manager') and self.detail_manager.is_detail_visible():
            self.detail_manager.hide_detail()
        
        button_text = active_button.item_text
        
        if not active_button.has_dropdown and button_text in PAGE_CONFIG:
            page_widget = self._ensure_page_loaded(button_text)
            self.stacked_widget.setCurrentWidget(page_widget)
            QTimer.singleShot(50, lambda: self._load_page_data(page_widget))
        else:
            # Handle dropdown state
            for btn in self.sidebar.nav_buttons:
                if btn != active_button and btn.has_dropdown and hasattr(btn, 'dropdown_open'):
                    btn.dropdown_open = False
            
            for btn in self.sidebar.nav_buttons:
                btn.update_style()
    
    def handle_dropdown_selection(self, item_name: str) -> None:
        """Handle dropdown menu selections"""
        if hasattr(self, 'detail_manager') and self.detail_manager.is_detail_visible():
            self.detail_manager.hide_detail()
        
        if item_name in PAGE_CONFIG:
            page_widget = self._ensure_page_loaded(item_name)
            self.stacked_widget.setCurrentWidget(page_widget)
            self._load_page_data(page_widget)
            
            # Close dropdown
            for btn in self.sidebar.nav_buttons:
                if hasattr(btn, 'dropdown_open') and btn.dropdown_open:
                    btn.dropdown_open = False
                    btn.update_style()
    
    def toggle_terminal(self) -> None:
        """Toggle terminal visibility"""
        self.terminal_panel.toggle_terminal()
        if self.terminal_panel.is_visible:
            self._adjust_terminal_position()
    
    # Event handlers
    def _on_connection_started(self, cluster_name: str) -> None:
        """Handle connection start"""
        if cluster_name == self.active_cluster:
            self.loading_overlay.show_loading(f"Connecting to cluster: {cluster_name}")
            self.loading_overlay.resize(self.size())
    
    def _on_connection_complete(self, cluster_name: str, success: bool) -> None:
        """Handle connection completion"""
        if cluster_name == self.active_cluster:
            if success:
                self.loading_overlay.show_loading(f"Loading data from: {cluster_name}")
            else:
                self.loading_overlay.hide_loading()
                if hasattr(self.parent_window, 'show_error_message'):
                    self.parent_window.show_error_message(f"Failed to connect to cluster: {cluster_name}")
    
    def _on_cluster_data_loaded(self, cluster_info: Dict[str, Any]) -> None:
        """Handle cluster data loaded"""
        self.loading_overlay.hide_loading()
    
    def _on_error(self, error_message: str) -> None:
        """Handle error messages"""
        self.loading_overlay.hide_loading()
        logging.warning(f"ClusterView received error: {error_message}")
    
    def _handle_resource_updated(self, resource_type: str, resource_name: str, namespace: Optional[str]) -> None:
        """Handle resource updates"""
        page_name = resource_type + "s"
        
        if page_name in self.pages:
            page = self.pages[page_name]
            if hasattr(page, 'force_load_data'):
                page.force_load_data()
            elif hasattr(page, 'load_data'):
                page.load_data()
        
        # Always refresh Events page
        if "Events" in self.pages:
            events_page = self.pages["Events"]
            if hasattr(events_page, 'force_load_data'):
                events_page.force_load_data()
            elif hasattr(events_page, 'load_data'):
                events_page.load_data()
    
    def _update_terminal_on_sidebar_toggle(self) -> None:
        """Update terminal position when sidebar toggles"""
        QTimer.singleShot(250, self._adjust_terminal_position)
        if hasattr(self, 'terminal_panel'):
            self.terminal_panel.sidebar_width = self.sidebar.width()
    
    def _adjust_terminal_position(self) -> None:
        """Adjust terminal position and size"""
        if not (hasattr(self, 'terminal_panel') and self.terminal_panel.is_visible):
            return
        
        parent_width = self.parent_window.width()
        parent_height = self.parent_window.height()
        sidebar_width = self.sidebar.width()
        
        terminal_width = parent_width - sidebar_width
        self.terminal_panel.setFixedWidth(terminal_width)
        self.terminal_panel.move(sidebar_width, parent_height - self.terminal_panel.height())
        self.terminal_panel.raise_()
    
    # Qt event handlers
    def resizeEvent(self, event) -> None:
        """Handle resize events"""
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(self.size())
    
    def eventFilter(self, obj, event) -> bool:
        """Handle window events"""
        if obj == self and event.type() == event.Type.Resize:
            if hasattr(self, 'terminal_panel') and self.terminal_panel.is_visible:
                self._adjust_terminal_position()
            
            if hasattr(self, 'detail_manager') and self.detail_manager.is_detail_visible():
                self.detail_manager.update_detail_position()
        
        return super().eventFilter(obj, event)
    
    def showEvent(self, event) -> None:
        """Handle show events"""
        super().showEvent(event)
        
        if hasattr(self, 'terminal_panel') and self.terminal_panel.is_visible:
            self._adjust_terminal_position()
        
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(self.size())
        
        # Sync sidebar selection with current page
        if hasattr(self, 'stacked_widget') and hasattr(self, 'sidebar'):
            current_widget = self.stacked_widget.currentWidget()
            if current_widget:
                self.handle_page_change(current_widget)
    
    def closeEvent(self, event) -> None:
        """Handle close events"""
        if hasattr(self, 'detail_manager') and self.detail_manager.is_detail_visible():
            self.detail_manager.hide_detail()
        
        if hasattr(self, 'terminal_panel') and self.terminal_panel.is_visible:
            self.terminal_panel.hide_terminal()
        
        super().closeEvent(event)