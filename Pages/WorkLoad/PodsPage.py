"""
Enhanced PodsPage with integrated port forwarding functionality
"""

from PyQt6.QtWidgets import QHeaderView, QPushButton, QLabel, QWidget, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles
from UI.Icons import resource_path
from utils.port_forward_manager import get_port_forward_manager, PortForwardConfig
from utils.port_forward_dialog import PortForwardDialog, ActivePortForwardsDialog

class StatusLabel(QWidget):
    """Widget that displays a status with consistent styling and background handling."""
    clicked = pyqtSignal()
    
    def __init__(self, status_text, color=None, parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create label
        self.label = QLabel(status_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set color if provided, otherwise use default color
        if color:
            self.label.setStyleSheet(f"color: {QColor(color).name()}; background-color: transparent;")
        
        # Add label to layout
        layout.addWidget(self.label)
        
        # Make sure this widget has a transparent background
        self.setStyleSheet("background-color: transparent;")
    
    def mousePressEvent(self, event):
        """Emit clicked signal when widget is clicked"""
        self.clicked.emit()
        super().mousePressEvent(event)

class PodsPage(BaseResourcePage):
    """
    Enhanced Pods page with integrated port forwarding functionality
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "pods"
        self.port_manager = get_port_forward_manager()
        self.setup_page_ui()
        
        # Connect to port forward manager signals
        self.port_manager.port_forward_started.connect(self.on_port_forward_started)
        self.port_manager.port_forward_stopped.connect(self.on_port_forward_stopped)
        self.port_manager.port_forward_error.connect(self.on_port_forward_error)
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Pods page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Containers", "Restarts", "Controlled By", "Node", "QoS", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8, 9}
        
        # Set up the base UI components with styles
        layout = super().setup_ui("Pods", headers, sortable_columns)
        
        # Apply table style
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        # Configure column widths
        self.configure_columns()
        
        # Add delete selected button
        self._add_delete_selected_button()
        
        # Add port forwarding management button
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
        
        # Find the header layout
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if isinstance(widget, QPushButton) and widget.text() == "Refresh":
                        # Insert before the refresh button
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
                        # Insert before the refresh button
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
            (3, 80, "interactive"),  # Containers
            (4, 70, "interactive"),  # Restarts
            (5, 130, "interactive"), # Controlled By
            (6, 110, "interactive"), # Node
            (7, 60, "interactive"),  # QoS
            (8, 60, "stretch"),  # Age
            (9, 80, "fixed"),      # Status - stretch to fill remaining space
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
        """
        Populate a single row with Pod data from kubernetes client response,
        using a StatusLabel for the Status column so per-status colors aren't overridden.
        """
        self.table.setRowHeight(row, 40)
        name = resource["name"]
        
        # 1) Checkbox
        cb = self._create_checkbox_container(row, name)
        cb.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, cb)

        # Get data from the kubernetes client response
        raw = resource.get("raw_data", {}) or {}
        
        # Get container count from kubernetes API response
        containers_count = "0"
        if raw and raw.get("spec", {}).get("containers"):
            containers = raw["spec"]["containers"]
            init_containers = raw["spec"].get("initContainers", [])
            containers_count = str(len(containers) + len(init_containers))
        
        # Get restart count from kubernetes API response
        restart_count = "0"
        if raw and raw.get("status", {}).get("containerStatuses"):
            container_statuses = raw["status"]["containerStatuses"]
            total_restarts = sum(container.get("restartCount", 0) for container in container_statuses)
            restart_count = str(total_restarts)
        
        # Get controller reference from kubernetes API response
        controller_by = ""
        if raw and raw.get("metadata", {}).get("ownerReferences"):
            owner_references = raw["metadata"]["ownerReferences"]
            if owner_references:
                controller_by = owner_references[0].get("kind", "")
        
        # Get QoS class from kubernetes API response
        qos_class = ""
        if raw and raw.get("status", {}).get("qosClass"):
            qos_class = raw["status"]["qosClass"]
        
        # Get node name from kubernetes API response
        node_name = ""
        if raw and raw.get("spec", {}).get("nodeName"):
            node_name = raw["spec"]["nodeName"]
        
        # Use age from resource (already formatted by the loader)
        age_str = resource.get("age", "Unknown")
        
        # Determine pod status from kubernetes API response
        pod_status = "Unknown"
        if raw and raw.get("status"):
            status = raw["status"]
            pod_phase = status.get("phase", "Unknown")
            pod_status = pod_phase
            
            # Check for more specific states from container statuses
            for cs in status.get("containerStatuses", []):
                state = cs.get("state", {})
                if "waiting" in state:
                    reason = state["waiting"].get("reason", "")
                    if reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                        pod_status = reason
                        break
                elif "terminated" in state:
                    if state["terminated"].get("exitCode", 0) != 0:
                        pod_status = "Error"
                        break

        # 2) All columns *except* Status and Actions
        cols = [
            name,
            resource.get("namespace", ""),
            containers_count,
            restart_count,
            controller_by,
            node_name,
            qos_class,
            age_str
        ]
        
        for idx, val in enumerate(cols):
            col = idx + 1  # shift right for checkbox at col 0
            if idx in (2, 3):  # numeric columns (containers, restarts)
                num = int(val) if val.isdigit() else 0
                item = SortableTableWidgetItem(val, num)
            elif idx == 7:  # age column
                if val and val != "Unknown":
                    unit = val[-1]
                    time_value = val[:-1]
                    if time_value.isdigit():
                        # Convert to minutes for sorting
                        num = int(time_value) * {'d': 1440, 'h': 60, 'm': 1}.get(unit, 1)
                        item = SortableTableWidgetItem(val, num)
                    else:
                        item = SortableTableWidgetItem(val)
                else:
                    item = SortableTableWidgetItem(val)
            else:
                item = SortableTableWidgetItem(val)
            
            # Set alignment
            if idx in (1, 2, 3,4,5, 6, 7):  # numeric and age columns
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
            
            # Make non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set default text color
            item.setForeground(QColor(AppColors.TEXT_TABLE))
            self.table.setItem(row, col, item)

        # 3) Status column as StatusLabel widget (col index 9)
        status_col = 1 + len(cols)  # equals 9
        
        # Pick the right color based on pod status
        if pod_status == "Running":
            color = AppColors.STATUS_ACTIVE
        elif pod_status == "Pending":
            color = AppColors.STATUS_PENDING
        elif pod_status in ("Failed", "Error", "CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
            color = AppColors.STATUS_DISCONNECTED
        elif pod_status == "Succeeded":
            color = AppColors.STATUS_AVAILABLE
        else:
            color = AppColors.TEXT_TABLE

        # Create status widget with proper color
        status_widget = StatusLabel(pod_status, color)
        # Connect click event to select the row
        status_widget.clicked.connect(lambda: self.table.selectRow(row))
        self.table.setCellWidget(row, status_col, status_widget)

        # 4) Action menu (last column index 10)
        action_btn = self._create_action_button(row, name, resource.get("namespace", ""))
        action_btn.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_btn)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, status_col + 1, action_container)

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

        # Remove text and change to icon-only style
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

        # Get pod details for port detection
        pod_resource = self.resources[row] if row < len(self.resources) else None
        exposed_ports = self._get_pod_exposed_ports(pod_resource)

        actions = []
        
        # Pod-specific actions
        actions.append({"text": "View Logs", "icon": "icons/logs.png", "dangerous": False})
        actions.append({"text": "SSH", "icon": "icons/terminal.png", "dangerous": False})
        
        # Port forwarding actions - only show if pod has exposed ports
        if exposed_ports:
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

    def _get_pod_exposed_ports(self, pod_resource):
        """Extract exposed ports from pod resource"""
        if not pod_resource or not pod_resource.get("raw_data"):
            return []
        
        exposed_ports = []
        raw_data = pod_resource["raw_data"]
        
        # Get ports from container specs
        containers = raw_data.get("spec", {}).get("containers", [])
        for container in containers:
            ports = container.get("ports", [])
            for port in ports:
                if port.get("containerPort"):
                    exposed_ports.append({
                        'port': port["containerPort"],
                        'protocol': port.get("protocol", "TCP"),
                        'name': port.get("name", f"port-{port['containerPort']}")
                    })
        
        return exposed_ports

    def _handle_action(self, action, row):
        """Handle action button clicks with enhanced port forwarding support."""
        if row >= len(self.resources):
            return

        resource = self.resources[row]
        resource_name = resource.get("name", "")
        resource_namespace = resource.get("namespace", "")

        if action == "Port Forward":
            self._handle_port_forward(resource_name, resource_namespace, resource)
        elif action == "View Logs":
            if self.resource_type == "pods":
                self._handle_view_logs(resource_name, resource_namespace, resource)
            else:
                self._show_logs_error("Logs are only available for pod resources.")
        elif action == "SSH":
            if self.resource_type == "pods":
                self._handle_ssh_into_pod(resource_name, resource_namespace, resource)
            else:
                self._show_ssh_error("SSH is only available for pod resources.")
        elif action == "Edit":
            self._handle_edit_resource(resource_name, resource_namespace, resource)
        elif action == "Delete":
            self.delete_resource(resource_name, resource_namespace)

    def _handle_port_forward(self, pod_name, namespace, resource):
        """Handle port forwarding for a pod"""
        try:
            # Get exposed ports
            exposed_ports = self._get_pod_exposed_ports(resource)
            
            if not exposed_ports:
                QMessageBox.information(
                    self, "No Ports Available",
                    f"Pod '{pod_name}' does not expose any ports for forwarding."
                )
                return
            
            # Extract port numbers for the dialog
            available_ports = [port_info['port'] for port_info in exposed_ports]
            
            # Create and show port forward dialog
            dialog = PortForwardDialog(
                resource_name=pod_name,
                resource_type='pod',
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
        """Handle row clicks to show pod details"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            
            # Get resource details
            resource_name = None
            namespace = None
            
            # Get the resource name
            if self.table.item(row, 1) is not None:
                resource_name = self.table.item(row, 1).text()
            
            # Get namespace if applicable
            if self.table.item(row, 2) is not None:
                namespace = self.table.item(row, 2).text()
            
            # Show detail view
            if resource_name:
                # Find the ClusterView instance
                parent = self.parent()
                while parent and not hasattr(parent, 'detail_manager'):
                    parent = parent.parent()
                
                if parent and hasattr(parent, 'detail_manager'):
                    # Show pod details using the detail manager
                    parent.detail_manager.show_detail("pod", resource_name, namespace)