"""
Enhanced ServicesPage with integrated port forwarding functionality
"""

from PyQt6.QtWidgets import (QHeaderView, QPushButton, QLabel, QVBoxLayout, 
                            QWidget, QHBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles
from kubernetes import client
from kubernetes.client.rest import ApiException
from utils.port_forward_manager import get_port_forward_manager, PortForwardConfig
from utils.port_forward_dialog import PortForwardDialog, ActivePortForwardsDialog
from UI.Icons import resource_path

class StatusLabel(QWidget):
    """Widget that displays a status with consistent styling and background handling."""
    clicked = pyqtSignal()
    
    def __init__(self, status_text, color=None, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.label = QLabel(status_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if color:
            self.label.setStyleSheet(f"color: {QColor(color).name()}; background-color: transparent;")
        
        layout.addWidget(self.label)
        self.setStyleSheet("background-color: transparent;")
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

class ServicesPage(BaseResourcePage):
    """
    Enhanced Services page with integrated port forwarding functionality
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "services"
        self.kube_client = client.CoreV1Api()
        self.port_manager = get_port_forward_manager()
        self.setup_page_ui()
        
        # Connect to port forward manager signals
        self.port_manager.port_forward_started.connect(self.on_port_forward_started)
        self.port_manager.port_forward_stopped.connect(self.on_port_forward_stopped)
        self.port_manager.port_forward_error.connect(self.on_port_forward_error)
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Services page"""
        headers = ["", "Name", "Namespace", "Type", "Cluster IP", "Port", "External IP", "Selector", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8, 9}
        
        layout = super().setup_ui("Services", headers, sortable_columns)
        
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        self.configure_columns()
        self._add_delete_selected_button()
        self._add_port_forward_management_button()
        
    def _add_delete_selected_button(self):
        """Add a button to delete selected resources."""
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected_resources)
        
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if isinstance(widget, QPushButton) and widget.text() == "Refresh":
                        item.layout().insertWidget(item.layout().count() - 1, delete_btn)
                        break

    def _add_port_forward_management_button(self):
        """Add port forward management button"""
        pf_btn = QPushButton("Port Forwards")
        pf_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        pf_btn.clicked.connect(self.show_port_forward_management)
        
        # Find the header layout and add button
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if isinstance(widget, QPushButton) and widget.text() == "Refresh":
                        item.layout().insertWidget(item.layout().count() - 1, pf_btn)
                        break
    
    def configure_columns(self):
        """Configure column widths for full screen utilization"""
        if not self.table:
            return
        
        header = self.table.horizontalHeader()
        
        # Column specifications with optimized default widths
        column_specs = [
            (0, 40, "fixed"),        # Checkbox
            (1, 140, "interactive"), # Name
            (2, 90, "interactive"),  # Namespace
            (3, 80, "interactive"),  # Type
            (4, 60, "interactive"),  # Cluster IP   
            (5, 60, "interactive"),  # Port
            (6, 60, "interactive"),  # External IP
            (7, 60, "interactive"),  # Selector
            (8, 60, "interactive"),  # Age
            (9, 80, "stretch"),      # Status - stretch to fill remaining space
            (10, 40, "fixed")        # Actions
        ]
        
        # Apply column configuration
        for col_index, default_width, resize_type in column_specs:
            if col_index < self.table.columnCount():
                if resize_type == "fixed":
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Fixed)
                    self.table.setColumnWidth(col_index, default_width)
                elif resize_type == "interactive":
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Interactive)
                    self.table.setColumnWidth(col_index, default_width)
                elif resize_type == "stretch":
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Stretch)
                    self.table.setColumnWidth(col_index, default_width)
        # Ensure full width utilization after configuration
        QTimer.singleShot(100, self._ensure_full_width_utilization)
    
    def populate_resource_row(self, row, resource):
        """Populate a single row with Service data including status"""
        self.table.setRowHeight(row, 40)
        
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        spec = resource.get("raw_data", {}).get("spec", {})
        service_type = spec.get("type", "ClusterIP")
        cluster_ip = spec.get("clusterIP", "<none>")
        
        ports = spec.get("ports", [])
        port_strs = []
        for port in ports:
            port_str = f"{port.get('port')}/{port.get('protocol', 'TCP')}"
            if 'targetPort' in port:
                port_str += f"→{port.get('targetPort')}"
            port_strs.append(port_str)
        port_text = ", ".join(port_strs) if port_strs else "<none>"
        
        external_ips = spec.get("externalIPs", [])
        lb_status = resource.get("raw_data", {}).get("status", {}).get("loadBalancer", {}).get("ingress", [])
        for lb in lb_status:
            if "ip" in lb:
                external_ips.append(lb["ip"])
            elif "hostname" in lb:
                external_ips.append(lb["hostname"])
        external_ip_text = ", ".join(external_ips) if external_ips else "<none>"
        
        selector = spec.get("selector", {})
        selector_text = ", ".join([f"{k}={v}" for k, v in selector.items()]) if selector else "<none>"
        
        status = self.determine_service_status(resource)
        
        columns = [
            resource["name"],
            resource["namespace"],
            service_type,
            cluster_ip,
            port_text,
            external_ip_text,
            selector_text,
            resource["age"]
        ]
        
        for col, value in enumerate(columns):
            cell_col = col + 1
            if col == 7:
                try:
                    num = int(value.replace('d', '').replace('h', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            if col in [1, 2, 3, 4, 5, 6, 7]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setForeground(QColor(AppColors.TEXT_TABLE))
            self.table.setItem(row, cell_col, item)
        
        status_col = 9
        status_text = status
        
        if status_text == "Active":
            color = AppColors.STATUS_ACTIVE
        elif status_text == "Warning":
            color = AppColors.STATUS_WARNING
        elif status_text == "Error":
            color = AppColors.STATUS_ERROR
        elif status_text == "Pending":
            color = AppColors.STATUS_PENDING
        else:
            color = AppColors.TEXT_TABLE
        
        status_widget = StatusLabel(status_text, color)
        status_widget.clicked.connect(lambda: self.table.selectRow(row))
        self.table.setCellWidget(row, status_col, status_widget)
        
        action_button = self._create_action_button(row, resource["name"], resource["namespace"])
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(columns) + 2, action_container)

    def _create_action_button(self, row, resource_name=None, resource_namespace=None):
        """Create an action button with menu - Enhanced with port forwarding"""
        from PyQt6.QtWidgets import QToolButton, QMenu
        from PyQt6.QtGui import QIcon
        from PyQt6.QtCore import QSize
        from functools import partial
        
        button = QToolButton()

        # Use custom SVG icon instead of text
        icon = resource_path("icons/Moreaction_Button.svg")
        button.setIcon(QIcon(icon))
        button.setIconSize(QSize(16, 16))

        button.setText("")
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        button.setFixedWidth(30)
        button.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Create menu
        menu = QMenu(button)
        menu.setStyleSheet(AppStyles.MENU_STYLE)

        # Connect signals to change row appearance when menu opens/closes
        menu.aboutToShow.connect(lambda: self._highlight_active_row(row, True))
        menu.aboutToHide.connect(lambda: self._highlight_active_row(row, False))

        # Get service details for port detection
        service_resource = self.resources[row] if row < len(self.resources) else None
        service_ports = self._get_service_ports(service_resource)

        actions = []
        
        # Port forwarding actions - only show if service has ports
        if service_ports:
            actions.append({"text": "Port Forward", "icon": "icons/network.png", "dangerous": False})
        
        # Standard actions
        actions.extend([
            {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True}
        ])

        # Add actions to menu
        for action_info in actions:
            action = menu.addAction(action_info["text"])
            if "icon" in action_info:
                action.setIcon(QIcon(action_info["icon"]))
            if action_info.get("dangerous", False):
                action.setProperty("dangerous", True)
            action.triggered.connect(
                partial(self._handle_action, action_info["text"], row)
            )

        button.setMenu(menu)
        return button

    def _get_service_ports(self, service_resource):
        """Extract ports from service resource"""
        if not service_resource or not service_resource.get("raw_data"):
            return []
        
        service_ports = []
        raw_data = service_resource["raw_data"]
        
        # Get ports from service spec
        ports = raw_data.get("spec", {}).get("ports", [])
        for port in ports:
            if port.get("port"):
                service_ports.append({
                    'port': port["port"],
                    'target_port': port.get("targetPort", port["port"]),
                    'protocol': port.get("protocol", "TCP"),
                    'name': port.get("name", f"port-{port['port']}")
                })
        
        return service_ports
    
    def determine_service_status(self, resource):
        """Determine the status of a service based on its configuration and state"""
        try:
            raw_data = resource.get("raw_data", {})
            spec = raw_data.get("spec", {})
            status = raw_data.get("status", {})
            service_type = spec.get("type", "ClusterIP")
            namespace = resource.get("namespace", "default")
            service_name = resource.get("name", "")
            
            has_endpoints = False
            if service_name and namespace:
                try:
                    endpoints = self.kube_client.read_namespaced_endpoints(name=service_name, namespace=namespace)
                    subsets = endpoints.subsets or []
                    for subset in subsets:
                        if subset.addresses:
                            has_endpoints = True
                            break
                except ApiException as e:
                    if e.status != 404:
                        has_endpoints = True  # Assume endpoints exist if we can't check
            
            if service_type == "ExternalName":
                return "Active" if spec.get("externalName") else "Warning"
            elif service_type == "LoadBalancer":
                lb_ingress = status.get("loadBalancer", {}).get("ingress", [])
                if lb_ingress:
                    return "Active" if has_endpoints else "Warning"
                else:
                    return "Pending"
            elif service_type == "NodePort" or service_type == "ClusterIP":
                return "Active" if has_endpoints else "Warning"
            
            return "Unknown"
        except Exception as e:
            return "Unknown"

    def _handle_action(self, action, row):
        """Handle action button clicks with enhanced port forwarding support."""
        if row >= len(self.resources):
            return

        resource = self.resources[row]
        resource_name = resource.get("name", "")
        resource_namespace = resource.get("namespace", "")

        if action == "Port Forward":
            self._handle_port_forward(resource_name, resource_namespace, resource)
        elif action == "Edit":
            self._handle_edit_resource(resource_name, resource_namespace, resource)
        elif action == "Delete":
            self.delete_resource(resource_name, resource_namespace)

    def _handle_port_forward(self, service_name, namespace, resource):
        """Handle port forwarding for a service"""
        try:
            # Get service ports
            service_ports = self._get_service_ports(resource)
            
            if not service_ports:
                QMessageBox.information(
                    self, "No Ports Available",
                    f"Service '{service_name}' does not expose any ports for forwarding."
                )
                return
            
            # Extract port numbers for the dialog
            available_ports = [port_info['port'] for port_info in service_ports]
            
            # Create and show port forward dialog
            dialog = PortForwardDialog(
                resource_name=service_name,
                resource_type='service',
                namespace=namespace,
                available_ports=available_ports,
                parent=self
            )
            
            dialog.port_forward_requested.connect(self._create_port_forward)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Port Forward Error",
                f"Failed to initiate port forward: {str(e)}"
            )

    def _create_port_forward(self, config):
        """Create a port forward from configuration"""
        try:
            port_config = self.port_manager.start_port_forward(
                resource_name=config['resource_name'],
                resource_type=config['resource_type'],
                namespace=config['namespace'],
                target_port=config['target_port'],
                local_port=config.get('local_port'),
                protocol=config.get('protocol', 'TCP')
            )
            
            QMessageBox.information(
                self, "Port Forward Created",
                f"Port forward created successfully!\n\n"
                f"Resource: {config['resource_type']}/{config['resource_name']}\n"
                f"Local: localhost:{port_config.local_port}\n"
                f"Target: {port_config.target_port}\n"
                f"Protocol: {port_config.protocol}\n\n"
                f"Access at: http://localhost:{port_config.local_port}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Port Forward Failed",
                f"Failed to create port forward: {str(e)}"
            )

    def show_port_forward_management(self):
        """Show port forward management dialog"""
        dialog = ActivePortForwardsDialog(self)
        dialog.exec()

    def on_port_forward_started(self, config: PortForwardConfig):
        """Handle port forward started signal"""
        if hasattr(self, 'show_transient_message'):
            self.show_transient_message(
                f"Port forward started: localhost:{config.local_port} -> {config.target_port}"
            )

    def on_port_forward_stopped(self, key: str):
        """Handle port forward stopped signal"""
        if hasattr(self, 'show_transient_message'):
            self.show_transient_message(f"Port forward stopped: {key}")

    def on_port_forward_error(self, key: str, error_message: str):
        """Handle port forward error signal"""
        if hasattr(self, 'show_transient_message'):
            self.show_transient_message(f"Port forward error: {error_message}")
    
    def handle_row_click(self, row, column):
        if column != self.table.columnCount() - 1:
            self.table.selectRow(row)
            resource_name = self.table.item(row, 1).text() if self.table.item(row, 1) else None
            namespace = self.table.item(row, 2).text() if self.table.item(row, 2) else None
            
            if resource_name:
                parent = self.parent()
                while parent and not hasattr(parent, 'detail_manager'):
                    parent = parent.parent()
                
                if parent and hasattr(parent, 'detail_manager'):
                    resource_type = self.resource_type[:-1] if self.resource_type.endswith('s') else self.resource_type
                    parent.detail_manager.show_detail(resource_type, resource_name, namespace)