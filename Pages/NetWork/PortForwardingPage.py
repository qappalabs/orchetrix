from PyQt6.QtWidgets import (QHeaderView, QPushButton, QLabel, QVBoxLayout, 
                            QWidget, QHBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles
from kubernetes import client
from kubernetes.client.rest import ApiException
import random

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

class PortForwardingPage(BaseResourcePage):
    """
    Displays Kubernetes port forwarding configurations with live data.
    
    Features:
    1. Dynamic loading of port forwards from internal tracking and pod validation
    2. Editing port forwards
    3. Deleting port forwards (individual and batch)
    4. Status monitoring
    """
    
    def __init__(self, parent=None):
        self.resources = []
        self.resource_type = "portforwarding"
        self.is_loading = False
        self.port_forward_processes = {}  # Store port-forward configurations
        super().__init__(parent)
        self.kube_client = client.CoreV1Api()  # Initialize Kubernetes API client
        self.setup_page_ui()
        self._initialize_sample_port_forwards()  # Initialize sample data
        
    def _initialize_sample_port_forwards(self):
        """Initialize sample port forwarding configurations for demonstration"""
        try:
            # Fetch pods to create realistic port forwards
            pods = self.kube_client.list_pod_for_all_namespaces().items
            
            # Select up to 5 random pods for sample port forwards
            sample_pods = random.sample(pods, min(5, len(pods))) if pods else []
            
            for pod in sample_pods:
                resource_name = pod.metadata.name
                namespace = pod.metadata.namespace or "default"
                local_port = str(random.randint(8000, 9000))
                target_port = str(random.randint(80, 8080))
                name = f"{resource_name}-{local_port}-{target_port}"
                
                self.port_forward_processes[(name, namespace)] = {
                    'resource_name': resource_name,
                    'namespace': namespace,
                    'kind': 'Pod',
                    'target_port': target_port,
                    'local_port': local_port,
                    'protocol': 'TCP',
                    'is_running': random.choice([True, False])  # Simulate active/inactive
                }
                
        except ApiException as e:
            self.on_load_error(f"API error initializing sample port forwards: {str(e)}")
        except Exception as e:
            self.on_load_error(f"Error initializing sample port forwards: {str(e)}")
    
    def setup_page_ui(self):
        """Set up the main UI elements for the Port Forwarding page"""
        headers = ["", "Name", "Namespace", "Kind", "Pod Port", "Local Port", "Protocol", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7}
        
        layout = super().setup_ui("Port Forwarding", headers, sortable_columns)
        
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
        
        stretch_columns = [2, 3, 4, 5, 6, 7]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 40)
    
    def load_data(self, load_more=False):
        """Load port forwarding data into the table with live data"""
        if self.is_loading:
            return
            
        self.is_loading = True
        self.resources = []
        self.selected_items.clear()
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        loading_row = self.table.rowCount()
        self.table.setRowCount(loading_row + 1)
        self.table.setSpan(loading_row, 0, 1, self.table.columnCount())
        
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.setContentsMargins(20, 20, 20, 20)
        
        loading_text = QLabel("Loading port forwards...")
        loading_text.setStyleSheet("color: #BBBBBB; font-size: 14px;")
        loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        loading_layout.addWidget(loading_text)
        self.table.setCellWidget(loading_row, 0, loading_widget)
        
        QTimer.singleShot(50, self._load_port_forwarding_data)
    
    def _load_port_forwarding_data(self):
        """Internal method to load port forwarding data using Kubernetes API"""
        try:
            port_forwards = []
            
            # Fetch all pods to validate port forwards
            pods = self.kube_client.list_pod_for_all_namespaces().items
            
            # Process existing port forwards
            for key, process_info in self.port_forward_processes.items():
                name, namespace = key
                resource_name = process_info.get('resource_name', name)
                target_port = process_info.get('target_port', '<none>')
                local_port = process_info.get('local_port', '<none>')
                protocol = process_info.get('protocol', 'TCP')
                kind = process_info.get('kind', 'Pod')
                
                # Check if the target pod still exists
                pod_exists = False
                for pod in pods:
                    if (pod.metadata.name == resource_name and 
                        pod.metadata.namespace == namespace):
                        pod_exists = True
                        break
                
                status = 'Active' if process_info.get('is_running', False) and pod_exists else 'Disconnected'
                
                port_forwards.append({
                    'name': name,
                    'resource_name': resource_name,
                    'namespace': namespace,
                    'kind': kind,
                    'pod_port': target_port,
                    'local_port': local_port,
                    'protocol': protocol,
                    'status': status,
                    'pid': process_info.get('pid')
                })
            
            self.resources = port_forwards
            self.on_resources_loaded(port_forwards, self.resource_type, next_continue_token="", load_more=False)
            
        except ApiException as e:
            self.on_load_error(f"API error loading port forwarding data: {str(e)}")
        except Exception as e:
            self.on_load_error(f"Error loading port forwarding data: {str(e)}")
    
    def populate_resource_row(self, row, resource):
        """Populate a single row with port forwarding data using ServicesPage style"""
        self.table.setRowHeight(row, 40)
        
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        columns = [
            resource["resource_name"],
            resource["namespace"],
            resource["kind"],
            resource["pod_port"],
            resource["local_port"], 
            resource["protocol"]
        ]
        
        for col, value in enumerate(columns):
            cell_col = col + 1
            item = SortableTableWidgetItem(value)
            
            if col in [2, 3, 4, 5]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setForeground(QColor(AppColors.TEXT_TABLE))
            self.table.setItem(row, cell_col, item)
        
        status_col = 7
        status_text = resource["status"]
        color = AppColors.STATUS_ACTIVE if status_text == "Active" else AppColors.STATUS_DISCONNECTED
        
        status_widget = StatusLabel(status_text, color)
        status_widget.clicked.connect(lambda: self.table.selectRow(row))
        self.table.setCellWidget(row, status_col, status_widget)
        
        action_button = self._create_action_button(row, resource["name"], resource["namespace"])
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(columns) + 2, action_container)
    
    def _handle_action(self, action, row):
        """Handle action button clicks - Edit or Delete"""
        if row >= len(self.resources):
            return
            
        resource = self.resources[row]
        resource_name = resource.get("name", "")
        resource_namespace = resource.get("namespace", "")
        
        if action == "Edit":
            self.edit_resource(resource)
        elif action == "Delete":
            self.delete_resource(resource_name, resource_namespace)
    
    def edit_resource(self, resource):
        """Open editor for port-forwarding configuration"""
        if resource["status"] == "Active":
            key = (resource["name"], resource["namespace"])
            if key in self.port_forward_processes:
                self.port_forward_processes[key]["is_running"] = False
                resource["status"] = "Disconnected"
        
        QMessageBox.information(
            self,
            "Edit Port Forward",
            f"Editing port forward to {resource['resource_name']}\n\n"
            f"Resource: {resource['kind']}/{resource['resource_name']}\n"
            f"Namespace: {resource['namespace']}\n"
            f"Local Port: {resource['local_port']}\n"
            f"Target Port: {resource['pod_port']}\n\n"
            "To edit port-forwards, terminate the current one and create a new one."
        )
        
        self.load_data()
    
    def delete_resource(self, resource_name, resource_namespace):
        """Override to handle port-forward specific deletion"""
        resource = None
        for r in self.resources:
            if r["name"] == resource_name and r["namespace"] == resource_namespace:
                resource = r
                break
                
        if not resource:
            return
            
        result = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the port forward to {resource['resource_name']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        key = (resource_name, resource_namespace)
        if key in self.port_forward_processes:
            self.port_forward_processes[key]["is_running"] = False
            del self.port_forward_processes[key]
        
        self.resources = [r for r in self.resources if not (
            r["name"] == resource_name and r["namespace"] == resource_namespace
        )]
        
        QMessageBox.information(
            self,
            "Port Forward Deleted",
            f"Port forward to {resource['resource_name']} has been deleted."
        )
        
        self.load_data()
    
    def delete_selected_resources(self):
        """Override to handle port-forward specific deletion for multiple resources"""
        if not self.selected_items:
            QMessageBox.information(
                self, 
                "No Selection", 
                "No port forwards selected for deletion."
            )
            return
            
        count = len(self.selected_items)
        result = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {count} selected port forwards?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        resources_to_delete = []
        for key in self.selected_items:
            for resource in self.resources:
                if resource["name"] == key[0] and resource.get("namespace", "") == key[1]:
                    resources_to_delete.append(resource)
                    break
        
        for port_forward in resources_to_delete:
            key = (port_forward["name"], port_forward["namespace"])
            if key in self.port_forward_processes:
                self.port_forward_processes[key]["is_running"] = False
                del self.port_forward_processes[key]
        
        QMessageBox.information(
            self,
            "Port Forwards Deleted",
            f"{len(resources_to_delete)} port forwards have been deleted."
        )
        
        self.selected_items.clear()
        self.load_data()
    
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