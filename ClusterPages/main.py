import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget
from PyQt6.QtCore import Qt

from Main.TitleBar import TitleBar
from Main.Sidebar import Sidebar
from Main.Header import Header


from Main.ClusterPage import ClusterPage
from Main.NodesPage import NodesPage


from WorkLoad.OverviewPage import OverviewPage
from WorkLoad.PodsPage import PodsPage
from WorkLoad.DeploymentsPage import DeploymentsPage
from WorkLoad.StatfulSetsPage import StatefulSetsPage
from WorkLoad.DaemonSetsPage import DaemonSetsPage
from WorkLoad.ReplicaSetsPage import ReplicaSetsPage
from WorkLoad.ReplicationControllersPage import ReplicaControllersPage
from WorkLoad.JobsPage import JobsPage
from WorkLoad.CronJobsPage import CronJobsPage


from Config.ConfigMapsPage import ConfigMapsPage


from NetWork.ServicesPage import ServicesPage
from NetWork.EndpointesPage import EndpointsPage
from NetWork.IngressesPage import IngressesPage
from NetWork.IngressClassesPage import IngressClassesPage
from NetWork.NetworkPoliciesPage import NetworkPoliciesPage
from NetWork.PortForwardingPage import PortForwardingPage




class DockerDesktopUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Docker Desktop")
        self.setMinimumSize(1000, 700)

        # Remove default window frame
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # Create stacked widget for managing pages
        self.stacked_widget = QStackedWidget()

        # Dictionary to store pages for easy navigation
        self.pages = {}

        # Set up custom tooltip style for the entire application
        app = QApplication.instance()
        if app:
            app.setStyleSheet("""
                QToolTip {
                    background-color: #333333;
                    color: #ffffff;
                    border: 1px solid #444444;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                }
            """)

        # Colors
        self.bg_dark = "#1a1a1a"
        self.bg_sidebar = "#1e1e1e"
        self.bg_header = "#1e1e1e"
        self.text_light = "#ffffff"
        self.text_secondary = "#888888"
        self.accent_blue = "#0095ff"
        self.accent_green = "#4CAF50"
        self.border_color = "#2d2d2d"
        self.tab_inactive = "#2d2d2d"
        self.card_bg = "#1e1e1e"

        self.setup_ui()
        self.drag_position = None

    def setup_ui(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {self.bg_dark};
                color: {self.text_light};
                font-family: 'Segoe UI', sans-serif;
            }}
            QTabWidget::pane {{
                border: none;
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {self.text_secondary};
                padding: 8px 24px;
                border: none;
                margin-right: 2px;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                color: {self.text_light};
                border-bottom: 2px solid {self.accent_blue};
            }}
            QTabBar::tab:hover:!selected {{
                color: {self.text_light};
            }}
        """)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add title bar
        self.title_bar = TitleBar(self)
        main_layout.addWidget(self.title_bar)

        # Container for sidebar and content
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Create sidebar
        self.sidebar = Sidebar(self)
        container_layout.addWidget(self.sidebar)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Create header
        self.header = Header(self)
        right_layout.addWidget(self.header)

        # Create pages
        self.cluster_page = ClusterPage()
        self.nodes_page = NodesPage()
        self.overview_page = OverviewPage()
        self.pods_page = PodsPage()
        self.deployments_page = DeploymentsPage()  # Add the new Deploymentpage
        self.daemonsets_page = DaemonSetsPage()
        self.statfulsets_page = StatefulSetsPage()
        self.replicasets_page = ReplicaSetsPage()
        self.replicationcontrollers_page = ReplicaControllersPage()
        self.jobs_page = JobsPage()
        self.cronjobs_page = CronJobsPage()
        self.configmaps_page = ConfigMapsPage()
        self.services_page = ServicesPage()
        self.endpoints_page = EndpointsPage()
        self.ingresses_page = IngressesPage()
        self.ingressclasses_page = IngressClassesPage()
        self.networkpolicies_page = NetworkPoliciesPage()
        self.portforwarding_page = PortForwardingPage()


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
        self.stacked_widget.addWidget(self.services_page)
        self.stacked_widget.addWidget(self.endpoints_page)
        self.stacked_widget.addWidget(self.ingresses_page)
        self.stacked_widget.addWidget(self.ingressclasses_page)
        self.stacked_widget.addWidget(self.networkpolicies_page)
        self.stacked_widget.addWidget(self.portforwarding_page)

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
        self.pages["Services"] = self.services_page
        self.pages["Endpoints"] = self.endpoints_page
        self.pages["Ingresses"] = self.ingresses_page
        self.pages["Ingress Classes"] = self.ingressclasses_page
        self.pages["Network Policies"] = self.networkpolicies_page
        self.pages["Port Forwarding"] = self.portforwarding_page

        
        right_layout.addWidget(self.stacked_widget)
        container_layout.addWidget(right_container, 1)

        main_layout.addWidget(container, 1)

        self.setCentralWidget(main_widget)

        # Set initial page
        self.stacked_widget.setCurrentWidget(self.cluster_page)

    def set_active_nav_button(self, active_button):
        for btn in self.sidebar.nav_buttons:
            btn.is_active = False
            btn.update_style()
        active_button.is_active = True
        active_button.update_style()

        # Switch pages based on button clicked
        if active_button.item_text == "Nodes":
            self.stacked_widget.setCurrentWidget(self.nodes_page)
        elif active_button.item_text == "Cluster":
            self.stacked_widget.setCurrentWidget(self.cluster_page)

    def handle_dropdown_selection(self, item_name):
        """Handle dropdown menu selections"""
        print(f"Selected dropdown item: {item_name}")
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
        elif item_name in ["Config Maps", "Secrets", "Resource Quotas", "Limit Ranges",
                           "Horizontal Pod Autoscalers", "Pod Disruption Budgets",
                           "Priority Classes", "Runtime Classes", "Leases"]:
            # Set Config nav button as active
            for btn in self.sidebar.nav_buttons:
                if btn.item_text == "Config":
                    btn.is_active = True
                    btn.update_style()
                else:
                    btn.is_active = False
                    btn.update_style()

    # Mouse events to make the window draggable from the title bar
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, 'drag_position'):
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DockerDesktopUI()
    window.show()
    sys.exit(app.exec())
