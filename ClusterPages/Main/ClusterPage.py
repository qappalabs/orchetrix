# import sys
# from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
#                            QPushButton, QLabel, QFrame, QTabWidget, QGridLayout, QSizePolicy,
#                            QGraphicsDropShadowEffect, QMenu, QToolButton, QToolTip, QLineEdit, 
#                            QStackedWidget)
# from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QEvent, QTimer, QPoint, QRect
# from PyQt6.QtGui import (QIcon, QFont, QColor, QPalette, QPixmap, QPainter, QLinearGradient, 
#                        QGradient, QShortcut, QAction, QGuiApplication, QActionGroup)

# from WorkFlow.PodsPage import PodsPage
# from NodesPage import NodesPage
# from WorkFlow.OverviewPage import OverviewPage
# from WorkFlow.DeploymentsPage import DeploymentsPage

# class NavMenuDropdown(QMenu):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
#         self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
#         self.setStyleSheet("""
#             QMenu {
#                 background-color: #2d2d2d;
#                 border: 1px solid #444444;
#                 border-radius: 6px;
#                 padding: 5px;
#             }
#             QMenu::item {
#                 padding: 1px 16px;
#                 border-radius: 4px;
#                 margin: 2px 5px;
#                 color: #e0e0e0;
#                 font-size: 14px;
#             }
#             QMenu::item:selected {
#                 background-color: rgba(33, 150, 243, 0.15);
#                 color: #ffffff;
#             }
#             QMenu::item[selected="true"] {
#                 background-color: rgba(33, 150, 243, 0.3);
#                 color: #ffffff;
#             }
#             QMenu::item:selected[selected="true"] {
#                 background-color: rgba(33, 150, 243, 0.4);
#                 color: #ffffff;
#             }
#             QMenu::separator {
#                 height: 1px;
#                 background-color: #444444;
#                 margin: 5px 10px;
#             }
#         """)
        
#         shadow = QGraphicsDropShadowEffect(self)
#         shadow.setColor(QColor(0, 0, 0, 100))
#         shadow.setBlurRadius(15)
#         shadow.setOffset(0, 5)
#         self.setGraphicsEffect(shadow)

# class NavIconButton(QToolButton):
#     def __init__(self, icon, text, active=False, has_dropdown=False, parent=None):
#         super().__init__(parent)
#         self.parent_window = parent
#         self.icon_text = icon
#         self.item_text = text
#         self.is_active = active
#         self.has_dropdown = has_dropdown
#         self.dropdown_open = False
#         self.dropdown_menu = None
#         self.selected_item = None
#         self.active_by_child = False  # Add this new property
        
#         # Colors
#         self.bg_dark = "#1a1a1a"
#         self.accent_blue = "#2196F3"
#         self.accent_light_blue = "#64B5F6"
#         self.text_light = "#f0f0f0"
#         self.text_secondary = "#888888"
        
#         self.setup_ui()
#         if self.has_dropdown:
#             self.setup_dropdown()
            
#     def setup_ui(self):
#         self.setFixedSize(40, 40)
#         self.setText(self.icon_text)
#         self.setToolTip(self.item_text)
#         self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
#         self.setCursor(Qt.CursorShape.PointingHandCursor)
#         self.setFont(QFont("Segoe UI", 16))
#         self.setAutoRaise(True)
#         self.update_style()
#         self.clicked.connect(self.activate)
#         if self.has_dropdown:
#             self.clicked.connect(self.show_dropdown)
#         self.installEventFilter(self)
            
#     def setup_dropdown(self):
#         self.dropdown_menu = NavMenuDropdown(self.parent_window)
#         title_action = QAction(f"{self.icon_text} {self.item_text}", self)
#         title_action.setEnabled(False)
#         self.dropdown_menu.addAction(title_action)
#         self.dropdown_menu.addSeparator()
        
#         menu_items = []
#         if self.item_text == "Workloads":
#             menu_items = ["Overview", "Pods", "Deployments", "Daemon Sets", 
#                         "Stateful Sets", "Replica Sets", "Replication Controllers",
#                         "Jobs", "Cron Jobs"]
#         elif self.item_text == "Config":
#             menu_items = ["Config Maps", "Secrets", "Resource Quotas", "Limit Ranges",
#                         "Horizontal Pod Autoscalers", "Pod Disruption Budgets",
#                         "Priority Classes", "Runtime Classes", "Leases"]
#         elif self.item_text == "Network":
#             menu_items = ["Services", "Endpoints", "Ingresses", "Ingress Classes",
#                         "Network Policies"]
#         elif self.item_text == "Storage":
#             menu_items = ["Persistent Volume Claims", "Persistent Volumes", 
#                         "Storage Classes"]
#         elif self.item_text == "Helm":
#             menu_items = ["Charts", "Releases"]
#         elif self.item_text == "Access Control":
#             menu_items = ["Service Accounts", "Cluster Roles", "Roles",
#                         "Cluster Role Bindings", "Role Bindings"]
#         elif self.item_text == "Custom Resources":
#             menu_items = ["Definitions"]

#         # Add actions for all menu items
#         for item in menu_items:
#             action = QAction(item, self.dropdown_menu)
#             action.setData(item)
#             self.dropdown_menu.addAction(action)
#             action.triggered.connect(lambda checked, i=item: self.handle_menu_action(i))
    
#     def handle_menu_action(self, item):
#         # Reset all buttons and their dropdowns first
#         if hasattr(self.parent_window, "reset_all_buttons_and_dropdowns"):
#             self.parent_window.reset_all_buttons_and_dropdowns()
        
#         # Update selected item
#         self.selected_item = item
#         self.active_by_child = True
#         self.is_active = True
        
#         # Update menu item states
#         for action in self.dropdown_menu.actions():
#             if isinstance(action, QAction) and action.data() is not None:
#                 action.setProperty("selected", "true" if action.data() == item else "false")
        
#         # Force style update
#         self.dropdown_menu.style().unpolish(self.dropdown_menu)
#         self.dropdown_menu.style().polish(self.dropdown_menu)
#         self.update_style()
        
#         # Handle specific actions
#         if item == "Pods":
#             self.parent_window.show_pods_page()
#         elif item == "Overview":  # Add handling for Overview
#             self.parent_window.show_workloads_overview_page()
#         elif item == "Deployments":
#             self.parent_window.show_deployments_page()
#             # self.parent_window.content_stack.setCurrentWidget(self.parent_window.deployments_page)
    
#     def show_dropdown(self):
#         if self.has_dropdown:
#             self.dropdown_open = True
#             self.update_style()
#             pos = self.mapToGlobal(QPoint(self.width(), 0))
#             self.dropdown_menu.popup(pos)
#             self.dropdown_menu.aboutToHide.connect(self.dropdown_closed)
#             QTimer.singleShot(50, lambda: self.setDown(False))
    
#     def dropdown_closed(self):
#         self.dropdown_open = False
#         self.update_style()
    
#     def activate(self):
#         if hasattr(self.parent_window, "set_active_nav_button"):
#             self.parent_window.set_active_nav_button(self)
    
#     def update_style(self):
#         if self.is_active or self.active_by_child:
#             self.setStyleSheet(f"""
#                 QToolButton {{
#                     background-color: rgba(255, 255, 255, 0.1);
#                     color: {self.text_light};
#                     border: none;
#                     border-radius: 0;
#                 }}
#                 QToolButton:hover {{
#                     background-color: rgba(255, 255, 255, 0.15);
#                 }}
#             """)
#         else:
#             self.setStyleSheet(f"""
#                 QToolButton {{
#                     background-color: transparent;
#                     color: {self.text_secondary};
#                     border: none;
#                     border-radius: 0;
#                 }}
#                 QToolButton:hover {{
#                     background-color: rgba(255, 255, 255, 0.1);
#                     color: {self.text_light};
#                 }}
#             """)
    
#     def eventFilter(self, obj, event):
#         if event.type() == QEvent.Type.Enter:
#             QToolTip.showText(
#                 self.mapToGlobal(QPoint(self.width() + 5, self.height() // 2)),
#                 self.item_text,
#                 self,
#                 QRect(),
#                 2000
#             )
#         return super().eventFilter(obj, event)

# class SearchBar(QLineEdit):
#     def __init__(self, placeholder_text, parent=None):
#         super().__init__(parent)
#         self.setPlaceholderText(placeholder_text)
#         self.setFixedHeight(28)  # Reduced from 30 to 28
#         self.setMinimumWidth(300)  # Slightly reduced width
#         self.setStyleSheet("""
#             QLineEdit {
#                 background-color: #333333;
#                 border: none;
#                 border-radius: 3px;  /* Reduced radius */
#                 color: #ffffff;
#                 padding: 4px 10px;  /* Reduced padding */
#                 font-size: 12px;  /* Reduced font size */
#             }
#             QLineEdit:focus {
#                 background-color: #404040;
#             }
#         """)

# class DockerDesktopUI(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("Docker Desktop")
#         self.setMinimumSize(1000, 700)
        
#         # Set up custom tooltip style for the entire application
#         app = QApplication.instance()
#         if app:
#             app.setStyleSheet("""
#                 QToolTip {
#                     background-color: #333333;
#                     color: #ffffff;
#                     border: 1px solid #444444;
#                     padding: 4px 8px;
#                     border-radius: 4px;
#                     font-size: 12px;
#                 }
#             """)
        
#         # Colors
#         self.bg_dark = "#1a1a1a"
#         self.bg_sidebar = "#1e1e1e"
#         self.bg_header = "#1e1e1e"
#         self.text_light = "#ffffff"
#         self.text_secondary = "#888888"
#         self.accent_blue = "#0095ff"
#         self.accent_green = "#4CAF50"
#         self.border_color = "#2d2d2d"
#         self.tab_inactive = "#2d2d2d"
#         self.card_bg = "#1e1e1e"
        
#         self.current_page = None
#         self.content_stack = QStackedWidget()

#         self.setup_ui()
        
#     def setup_ui(self):
#         self.setStyleSheet(f"""
#             QMainWindow, QWidget {{
#                 background-color: {self.bg_dark};
#                 color: {self.text_light};
#                 font-family: 'Segoe UI', sans-serif;
#             }}
#             QTabWidget::pane {{
#                 border: none;
#             }}
#             QTabBar::tab {{
#                 background-color: transparent;
#                 color: {self.text_secondary};
#                 padding: 8px 24px;
#                 border: none;
#                 margin-right: 2px;
#                 font-size: 13px;
#             }}
#             QTabBar::tab:selected {{
#                 color: {self.text_light};
#                 border-bottom: 2px solid {self.accent_blue};
#             }}
#             QTabBar::tab:hover:!selected {{
#                 color: {self.text_light};
#             }}
#         """)
        
#         main_widget = QWidget()
#         main_layout = QHBoxLayout(main_widget)
#         main_layout.setContentsMargins(0, 0, 0, 0)
#         main_layout.setSpacing(0)
        
#         sidebar = self.create_sidebar()
#         main_layout.addWidget(sidebar)
        
#         right_container = QWidget()
#         right_layout = QVBoxLayout(right_container)
#         right_layout.setContentsMargins(0, 0, 0, 0)
#         right_layout.setSpacing(0)
        
#         header = self.create_header()
#         right_layout.addWidget(header)
        
#         content_area = self.create_content_area()
#         right_layout.addWidget(content_area, 1)
        
#         main_layout.addWidget(right_container, 1)
#         self.setCentralWidget(main_widget)
    
#     def create_sidebar(self):
#         sidebar = QWidget()
#         sidebar.setFixedWidth(40)
#         sidebar.setStyleSheet(f"""
#             background-color: {self.bg_sidebar};
#             border-right: 1px solid {self.border_color};
#         """)
        
#         layout = QVBoxLayout(sidebar)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setSpacing(0)
        
#         # Create nav buttons
#         self.nav_buttons = []
#         nav_items = [
#             ("⚙️", "Cluster", True),
#             ("💻", "Nodes", False),
#             ("📦", "Workloads", False, True),
#             ("📝", "Config", False, True),
#             ("🌐", "Network", False, True),
#             ("📂", "Storage", False, True),
#             ("🔖", "Namespaces", False),
#             ("🕒", "Events", False),
#             ("⎈", "Helm", False, True),
#             ("🔐", "Access Control", False, True),
#             ("🧩", "Custom Resources", False, True)
#         ]
        
#         for item in nav_items:
#             nav_btn = NavIconButton(item[0], item[1], item[2], item[3] if len(item) > 3 else False, self)
#             self.nav_buttons.append(nav_btn)
#             layout.addWidget(nav_btn)
        
#         layout.addStretch(1)

#         compare_btn = NavIconButton("🖱️", "Compare", False, False, self)
#         terminal_btn = NavIconButton("⌨️", "Terminal", False, False, self)
#         download_btn = NavIconButton("🛠️", "Download", False, False, self)
        
#         self.nav_buttons.append(compare_btn)
#         self.nav_buttons.append(terminal_btn)
#         self.nav_buttons.append(download_btn)
        
#         layout.addWidget(compare_btn)
#         layout.addWidget(terminal_btn)
#         layout.addWidget(download_btn)
#         return sidebar
    
#     def create_header(self):
#         header = QWidget()
#         header.setFixedHeight(40)
#         header.setStyleSheet(f"""
#             background-color: {self.bg_header};
#             border-bottom: 1px solid {self.border_color};
#         """)
        
#         layout = QHBoxLayout(header)
#         layout.setContentsMargins(16, 0, 16, 0)
#         layout.setSpacing(16)
        
#         # Create cluster dropdown menu first
#         cluster_menu = QMenu()
#         cluster_menu.setStyleSheet(f"""
#             QMenu {{
#                 background-color: {self.bg_sidebar};
#                 color: {self.text_light};
#                 border: 1px solid {self.border_color};
#                 border-radius: 4px;
#                 padding: 8px 0px;
#             }}
#             QMenu::item {{
#                 padding: 8px 24px;
#                 font-size: 13px;
#             }}
#             QMenu::item:selected {{
#                 background-color: rgba(255, 255, 255, 0.1);
#             }}
#         """)
        
#         # Add menu items
#         cluster_menu.addAction("docker-desktop")
#         cluster_menu.addSeparator()
#         cluster_menu.addAction("dev-cluster")
#         cluster_menu.addAction("staging-cluster")
#         cluster_menu.addAction("production-cluster")
        
#         # Updated cluster dropdown button
#         cluster_dropdown = QToolButton()
#         cluster_dropdown.setFixedSize(160, 28)
#         cluster_dropdown.setMinimumWidth(200)
        
#         # Create horizontal layout for text and arrow
#         button_layout = QHBoxLayout(cluster_dropdown)
#         button_layout.setContentsMargins(12, 0, 32, 0)
#         button_layout.setSpacing(8)
        
#         # Text label
#         text_label = QLabel("docker-desktop")
#         text_label.setStyleSheet(f"color: #55c732; background: transparent;")
        
#         # Arrow label
#         arrow_label = QLabel("▼")
#         arrow_label.setFixedWidth(20)  # Fixed width for arrow
#         arrow_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
#         arrow_label.setStyleSheet(f"color: {self.text_secondary}; background: transparent; padding-right: 8px;")
        
#         button_layout.addWidget(text_label)
#         button_layout.addStretch()
#         button_layout.addWidget(arrow_label)
        
#         cluster_dropdown.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
#         cluster_dropdown.setMenu(cluster_menu)
#         cluster_dropdown.setStyleSheet(f"""
#             QToolButton {{
#                 background-color: transparent;
#                 border: none;
#                 background-color: rgba(255, 255, 255, 0.1);
#                 font-size: 13px;
#                 text-align: left;
#                 padding-left: 12px;
#                 padding-right: 32px;
#                 position: relative;
#             }}
#             QToolButton::menu-indicator {{
#                 image: none;
#             }}
#             QToolButton:hover {{
#                 background-color: rgba(255, 255, 255, 0.1);
#                 border-radius: 4px;
#             }}
#         """)
        
#         search_bar = SearchBar("Search...", self)
#         search_bar.setFixedHeight(28)
#         namespace_search = SearchBar("Search namespace...", self)
#         namespace_search.setFixedHeight(28)
        
#         layout.addWidget(cluster_dropdown)
#         layout.addStretch(1)
#         layout.addWidget(search_bar)
#         layout.addWidget(namespace_search)
        
#         return header

#     def create_content_area(self):
#         content_widget = QWidget()
#         content_layout = QGridLayout(content_widget)
#         content_layout.setContentsMargins(0, 0, 0, 0)
#         content_layout.setSpacing(0)

#         # Add stacked widget for different pages
#         content_layout.addWidget(self.content_stack)

#         # Create pages
#         self.cluster_page = self.create_cluster_page()
#         self.nodes_page = NodesPage()
#         self.pods_page = PodsPage()
#         self.workloads_overview_page = OverviewPage()  # Add the new OverviewPage
#         self.deployments_page = DeploymentsPage()  # Add the new Deploymentpage

#         # Add pages to stack
#         self.content_stack.addWidget(self.cluster_page)
#         self.content_stack.addWidget(self.nodes_page)
#         self.content_stack.addWidget(self.pods_page)
#         self.content_stack.addWidget(self.workloads_overview_page)  # Add to stack for overview
#         self.content_stack.addWidget(self.deployments_page) # Add to stack for deployments
        
#         return content_widget
    
#     def create_cluster_page(self):
#         page = QWidget()
#         layout = QVBoxLayout(page)  # Changed from QGridLayout to QVBoxLayout
#         layout.setContentsMargins(16, 16, 16, 16)
#         layout.setSpacing(16)
        
#         # Add tab widget only for cluster page
#         tab_widget = QTabWidget()
#         tab_widget.setStyleSheet("""
#             QTabWidget::pane {
#                 border: none;
#             }
#             QTabBar::tab {
#                 background-color: transparent;
#                 color: #888888;
#                 padding: 8px 24px;
#                 border: none;
#                 margin-right: 2px;
#                 font-size: 13px;
#             }
#             QTabBar::tab:selected {
#                 color: #ffffff;
#                 border-bottom: 2px solid #0095ff;
#             }
#             QTabBar::tab:hover:!selected {
#                 color: #ffffff;
#             }
#         """)
        
#         # Create master tab content
#         master_tab = QWidget()
#         master_layout = QGridLayout(master_tab)
#         master_layout.setContentsMargins(0, 16, 0, 0)
#         master_layout.setSpacing(16)
        
#         metric_panel1 = self.create_metric_panel()
#         metric_panel2 = self.create_metric_panel()
#         status_panel = self.create_status_panel()
        
#         master_layout.addWidget(metric_panel1, 0, 0)
#         master_layout.addWidget(metric_panel2, 0, 1)
#         master_layout.addWidget(status_panel, 1, 0, 1, 2)
        
#         # Create worker tab (empty for now)
#         worker_tab = QWidget()
        
#         # Add tabs
#         tab_widget.addTab(master_tab, "Master")
#         tab_widget.addTab(worker_tab, "Worker")
        
#         layout.addWidget(tab_widget)
#         return page
    
#     def create_metric_panel(self):
#         panel = QWidget()
#         panel.setStyleSheet(f"""
#             QWidget {{
#                 background-color: {self.card_bg};
#                 border-radius: 4px;
#             }}
#         """)
        
#         layout = QVBoxLayout(panel)
#         layout.setContentsMargins(16, 16, 16, 16)
#         layout.setSpacing(16)
        
#         # Tab-like buttons
#         tabs = QWidget()
#         tabs_layout = QHBoxLayout(tabs)
#         tabs_layout.setContentsMargins(0, 0, 0, 0)
#         tabs_layout.setSpacing(4)
        
#         cpu_btn = QPushButton("CPU")
#         cpu_btn.setStyleSheet("""
#             QPushButton {
#                 background-color: #333333;
#                 color: #ffffff;
#                 border: none;
#                 padding: 6px 16px;
#                 font-size: 13px;
#                 border-radius: 4px;
#             }
#         """)
        
#         memory_btn = QPushButton("Memory")
#         memory_btn.setStyleSheet("""
#             QPushButton {
#                 background-color: transparent;
#                 color: #888888;
#                 border: none;
#                 padding: 6px 16px;
#                 font-size: 13px;
#             }
#             QPushButton:hover {
#                 color: #ffffff;
#             }
#         """)
        
#         tabs_layout.addWidget(cpu_btn)
#         tabs_layout.addWidget(memory_btn)
#         tabs_layout.addStretch()
        
#         # Info message
#         info_container = QWidget()
#         info_layout = QVBoxLayout(info_container)
#         info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
#         info_msg = QLabel("Metrics are not available due to missing or invalid Prometheus")
#         info_msg.setStyleSheet("color: #888888; font-size: 13px;")
#         info_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
#         settings_link = QLabel("Open cluster settings")
#         settings_link.setStyleSheet("""
#             color: #0095ff;
#             font-size: 13px;
#             margin-top: 8px;
#         """)
#         settings_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         settings_link.setCursor(Qt.CursorShape.PointingHandCursor)
        
#         info_layout.addWidget(info_msg)
#         info_layout.addWidget(settings_link)
        
#         layout.addWidget(tabs)
#         layout.addWidget(info_container, 1, Qt.AlignmentFlag.AlignCenter)
        
#         return panel
    
#     def create_status_panel(self):
#         panel = QWidget()
#         panel.setStyleSheet(f"""
#             background-color: {self.card_bg};
#             border-radius: 4px;
#         """)
        
#         layout = QVBoxLayout(panel)
#         layout.setContentsMargins(32, 48, 32, 48)
#         layout.setSpacing(8)
#         layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
#         # Success icon
#         success_icon = QLabel("✓")
#         success_icon.setFixedSize(80, 80)
#         success_icon.setStyleSheet("""
#             background-color: #4CAF50;
#             color: white;
#             font-size: 40px;
#             border-radius: 40px;
#             qproperty-alignment: AlignCenter;
#         """)
        
#         # Status text
#         status_title = QLabel("No issues found")
#         status_title.setStyleSheet("""
#             color: white;
#             font-size: 20px;
#             font-weight: 500;
#             margin-top: 16px;
#         """)
#         status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
#         status_subtitle = QLabel("Everything is fine in the Cluster")
#         status_subtitle.setStyleSheet("""
#             color: #888888;
#             font-size: 14px;
#             margin-top: 4px;
#         """)
#         status_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
#         layout.addWidget(success_icon, 0, Qt.AlignmentFlag.AlignCenter)
#         layout.addWidget(status_title)
#         layout.addWidget(status_subtitle)
        
#         return panel
    
#     def reset_all_buttons_and_dropdowns(self):
#         """Reset all navigation buttons and their dropdowns to default state"""
#         for btn in self.nav_buttons:
#             btn.is_active = False
#             btn.active_by_child = False
#             btn.selected_item = None
            
#             # Reset dropdown menu items if exists
#             if btn.dropdown_menu:
#                 for action in btn.dropdown_menu.actions():
#                     if isinstance(action, QAction):
#                         action.setProperty("selected", "false")
            
#             btn.update_style()

#     def set_active_nav_button(self, active_button):
#         """Set the active navigation button and handle page switching"""
#         # Reset all buttons and their dropdowns
#         self.reset_all_buttons_and_dropdowns()
        
#         # Set the clicked button as active
#         active_button.is_active = True
#         active_button.update_style()

#         # Switch pages based on button
#         if active_button.item_text == "Nodes":
#             self.content_stack.setCurrentWidget(self.nodes_page)
#         elif active_button.item_text == "Cluster":
#             self.content_stack.setCurrentWidget(self.cluster_page)
#         # Other cases will be handled by dropdown menu items

#     def show_pods_page(self):
#         """Show the pods page and update navigation state"""
#         # Find workload button
#         workload_button = None
#         for btn in self.nav_buttons:
#             if btn.item_text == "Workloads":
#                 workload_button = btn
#                 break
        
#         if workload_button:
#             # Update workload button state
#             workload_button.is_active = True
#             workload_button.active_by_child = True
#             workload_button.update_style()
            
#             # Update other buttons
#             for btn in self.nav_buttons:
#                 if btn != workload_button:
#                     btn.is_active = False
#                     btn.active_by_child = False
#                     btn.update_style()
        
#         # Switch to pods page
#         self.content_stack.setCurrentWidget(self.pods_page)

#     # Add this method to DockerDesktopUI class
#     def show_workloads_overview_page(self):
#         """Show the workloads overview page and update navigation state"""
#         # Find workload button
#         workload_button = None
#         for btn in self.nav_buttons:
#             if btn.item_text == "Workloads":
#                 workload_button = btn
#                 break
        
#         if workload_button:
#             # Update workload button state
#             workload_button.is_active = True
#             workload_button.active_by_child = True
#             workload_button.selected_item = "Overview"  # Set the selected item to Overview
#             workload_button.update_style()
            
#             # Update menu item states
#             for action in workload_button.dropdown_menu.actions():
#                 if isinstance(action, QAction) and action.data() is not None:
#                     action.setProperty("selected", "true" if action.data() == "Overview" else "false")
            
#             # Force style update
#             workload_button.dropdown_menu.style().unpolish(workload_button.dropdown_menu)
#             workload_button.dropdown_menu.style().polish(workload_button.dropdown_menu)
            
#             # Update other buttons
#             for btn in self.nav_buttons:
#                 if btn != workload_button:
#                     btn.is_active = False
#                     btn.active_by_child = False
#                     btn.update_style()
        
#         # Switch to workloads overview page
#         self.content_stack.setCurrentWidget(self.workloads_overview_page) 
        
#     def show_deployments_page(self):
#         """Show the deployments page and update the Workloads nav state."""
#         # 1) Mark the "Workloads" button active (similar logic as show_pods_page).
#         workload_button = None
#         for btn in self.nav_buttons:
#             if btn.item_text == "Workloads":
#                 workload_button = btn
#                 break

#         if workload_button:
#             workload_button.is_active = True
#             workload_button.active_by_child = True
#             workload_button.selected_item = "Deployments"
#             workload_button.update_style()
            
#             # Update menu item states in the Workloads dropdown
#             for action in workload_button.dropdown_menu.actions():
#                 if action.data() is not None:
#                     # Mark "Deployments" as selected
#                     action.setProperty("selected", "true" if action.data() == "Deployments" else "false")

#             workload_button.dropdown_menu.style().unpolish(workload_button.dropdown_menu)
#             workload_button.dropdown_menu.style().polish(workload_button.dropdown_menu)

#             # Reset other buttons
#             for btn in self.nav_buttons:
#                 if btn != workload_button:
#                     btn.is_active = False
#                     btn.active_by_child = False
#                     btn.update_style()

#         # 2) Switch the main content to the Deployments page
#         self.content_stack.setCurrentWidget(self.deployments_page)


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = DockerDesktopUI()
#     window.show()
#     sys.exit(app.exec())








    
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QTabWidget, QGridLayout, QFrame)
from PyQt6.QtCore import Qt, QSize

class ClusterPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add tab container
        tab_container = self.create_tab_container()
        layout.addWidget(tab_container)

        # Add content area
        content_area = self.create_content_area()
        layout.addWidget(content_area)

    def create_tab_container(self):
        tab_widget = QTabWidget()
        tab_widget.setFixedHeight(44)
        tab_widget.addTab(QWidget(), "Master")
        tab_widget.addTab(QWidget(), "Worker")
        tab_widget.setCurrentIndex(0)
        return tab_widget

    def create_content_area(self):
        content_widget = QWidget()
        content_layout = QGridLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)

        metric_panel1 = self.create_metric_panel()
        metric_panel2 = self.create_metric_panel()
        status_panel = self.create_status_panel()

        content_layout.addWidget(metric_panel1, 0, 0)
        content_layout.addWidget(metric_panel2, 0, 1)
        content_layout.addWidget(status_panel, 1, 0, 1, 2)

        return content_widget

    def create_metric_panel(self):
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-radius: 4px;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Tab-like buttons
        tabs = QWidget()
        tabs_layout = QHBoxLayout(tabs)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(4)

        cpu_btn = QPushButton("CPU")
        cpu_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border: none;
                padding: 6px 16px;
                font-size: 13px;
                border-radius: 4px;
            }
        """)

        memory_btn = QPushButton("Memory")
        memory_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: none;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)

        tabs_layout.addWidget(cpu_btn)
        tabs_layout.addWidget(memory_btn)
        tabs_layout.addStretch()

        # Info message
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        info_msg = QLabel("Metrics are not available due to missing or invalid Prometheus")
        info_msg.setStyleSheet("color: #888888; font-size: 13px;")
        info_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        settings_link = QLabel("Open cluster settings")
        settings_link.setStyleSheet("""
            color: #0095ff;
            font-size: 13px;
            margin-top: 8px;
        """)
        settings_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        settings_link.setCursor(Qt.CursorShape.PointingHandCursor)

        info_layout.addWidget(info_msg)
        info_layout.addWidget(settings_link)

        layout.addWidget(tabs)
        layout.addWidget(info_container, 1, Qt.AlignmentFlag.AlignCenter)

        return panel

    def create_status_panel(self):
        panel = QWidget()
        panel.setStyleSheet("""
            background-color: #1e1e1e;
            border-radius: 4px;
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 48, 32, 48)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Success icon
        success_icon = QLabel("✓")
        success_icon.setFixedSize(80, 80)
        success_icon.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            font-size: 40px;
            border-radius: 40px;
            qproperty-alignment: AlignCenter;
        """)

        # Status text
        status_title = QLabel("No issues found")
        status_title.setStyleSheet("""
            color: white;
            font-size: 20px;
            font-weight: 500;
            margin-top: 16px;
        """)
        status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status_subtitle = QLabel("Everything is fine in the Cluster")
        status_subtitle.setStyleSheet("""
            color: #888888;
            font-size: 14px;
            margin-top: 4px;
        """)
        status_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(success_icon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_title)
        layout.addWidget(status_subtitle)

        return panel
