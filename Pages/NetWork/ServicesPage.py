"""
Enhanced ServicesPage with integrated port forwarding functionality
"""

import logging
from PyQt6.QtWidgets import (QHeaderView, QPushButton, QLabel, QVBoxLayout, 
                            QWidget, QHBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem, StatusLabel
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles
from Utils.port_forward_manager import get_port_forward_manager, PortForwardConfig
from Utils.port_forward_dialog import PortForwardDialog, ActivePortForwardsDialog
from kubernetes import client
from kubernetes.client.rest import ApiException
from UI.Icons import resource_path


class ServicesPage(BaseResourcePage):
    """
    Enhanced Services page with integrated port forwarding functionality
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "services"
        self.port_manager = get_port_forward_manager()
        # Use managed kubernetes client instead of direct client instantiation
        from Utils.kubernetes_client import get_kubernetes_client
        managed_client = get_kubernetes_client()
        self.kube_client = managed_client.v1 if managed_client else None
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
        self._add_port_forward_management_button()

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
            (1, 160, "interactive"), # Name
            (2, 100, "interactive"),  # Namespace
            (3, 80, "interactive"),  # Type
            (4, 90, "interactive"),  # Cluster IP   
            (5, 100, "interactive"),  # Port
            (6, 100, "interactive"),  # External IP
            (7, 100, "interactive"),  # Selector
            (8, 60, "interactive"),  # Age
            (9, 60, "stretch"),      # Status - stretch to fill remaining space
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
        
        # Use processed data from unified resource loader when available
        service_type = resource.get("type", "")
        cluster_ip = resource.get("cluster_ip", "")
        
        # Parse port information dynamically from raw data
        spec = resource.get("raw_data", {}).get("spec", {})
        ports = spec.get("ports", [])
        port_strs = []
        
        for port in ports:
            # Only show actual port data, no hardcoded defaults
            port_num = port.get('port')
            protocol = port.get('protocol')  # Don't default to TCP
            target_port = port.get('targetPort')
            node_port = port.get('nodePort')
            
            if port_num is not None:
                # Build port string with only available data
                port_str = str(port_num)
                
                # Add protocol only if specified
                if protocol:
                    port_str += f"/{protocol}"
                
                # Add target port only if different from port and specified
                if target_port is not None and str(target_port) != str(port_num):
                    port_str += f"→{target_port}"
                
                # Add NodePort only if service type is NodePort and nodePort is specified
                if node_port is not None and service_type == "NodePort":
                    port_str += f":{node_port}"
                
                port_strs.append(port_str)
        
        port_text = ", ".join(port_strs) if port_strs else ""
        
        # Use the pre-processed external IP from unified resource loader
        external_ip_text = resource.get("external_ip", "")
        
        selector = spec.get("selector", {})
        selector_text = ", ".join([f"{k}={v}" for k, v in selector.items()]) if selector else ""
        
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

    # Removed duplicate _create_action_button - now uses base class implementation

    def _get_service_ports(self, service_resource):
        """Extract ports from service resource"""
        if not service_resource or not service_resource.get("raw_data"):
            return []
        
        service_ports = []
        raw_data = service_resource["raw_data"]
        
        # Get ports from service spec - only actual data, no defaults
        ports = raw_data.get("spec", {}).get("ports", [])
        for port in ports:
            if port.get("port"):
                port_info = {
                    'port': port["port"]
                }
                
                # Only add fields that actually exist
                if "targetPort" in port:
                    port_info['target_port'] = port["targetPort"]
                if "protocol" in port:
                    port_info['protocol'] = port["protocol"]
                if "name" in port:
                    port_info['name'] = port["name"]
                
                service_ports.append(port_info)
        
        return service_ports
    
    def determine_service_status(self, resource):
        """Determine the status of a service based on its configuration and state"""
        try:
            raw_data = resource.get("raw_data", {})
            spec = raw_data.get("spec", {})
            status = raw_data.get("status", {})
            service_type = spec.get("type", "")
            namespace = resource.get("namespace", "")
            service_name = resource.get("name", "")
            
            # Determine endpoint status without blocking API calls
            # Use basic service configuration to determine likely status
            has_endpoints = True  # Assume endpoints exist to avoid blocking API calls
            # In a real implementation, this would be cached or loaded asynchronously
            
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

    # Removed duplicate _handle_action_with_data - now uses base class _handle_action

    # Removed duplicate _handle_action method - now using base class implementation

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