"""
Dynamic implementation of the Pods page with live Kubernetes data using Python kubernetes library.
Status colors are properly displayed and have consistent background styling.
"""

from PyQt6.QtWidgets import QHeaderView, QPushButton, QLabel, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles

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
    Displays Kubernetes Pods with live data and resource operations using Python kubernetes library.
    
    Features:
    1. Dynamic loading of Pods from the cluster using kubernetes client
    2. Editing Pods with editor
    3. Deleting Pods (individual and batch)
    4. Resource details viewer
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "pods"
        self.setup_page_ui()
        
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
        
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Column 0: Checkbox (fixed width) - already set in base class
        
        # Column 1: Name (stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Configure stretch columns
        stretch_columns = [2, 5, 6, 7, 9]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width columns
        fixed_widths = {3: 100, 4: 80, 8: 80, 10: 40}
        for col, width in fixed_widths.items():
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
            
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
            if idx in (2, 3, 6, 7):  # numeric and age columns
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
