from PyQt6.QtWidgets import (QHeaderView, QPushButton, QLabel, QVBoxLayout, 
                            QWidget, QHBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles
from kubernetes import client
from kubernetes.client.rest import ApiException

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
    Displays Kubernetes Services with live data and resource operations.
    
    Features:
    1. Dynamic loading of Services from the cluster
    2. Editing Services with terminal editor
    3. Deleting Services (individual and batch)
    4. Status column showing service availability
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "services"
        self.kube_client = client.CoreV1Api()  # Initialize Kubernetes API client
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Services page"""
        headers = ["", "Name", "Namespace", "Type", "Cluster IP", "Port", "External IP", "Selector", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8, 9}
        
        layout = super().setup_ui("Services", headers, sortable_columns)
        
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        self.configure_columns()
        self._add_delete_selected_button()
        
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
    
    def configure_columns(self):
        """Configure column widths and behaviors"""
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        stretch_columns = [2, 3, 4, 5, 6, 7, 8, 9]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        self.table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(10, 40)
    
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
            
            if col in [2, 3, 4, 5, 7]:
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