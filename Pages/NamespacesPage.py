"""
Dynamic implementation of the Namespaces page with live Kubernetes data using API.
"""

from PyQt6.QtWidgets import (
    QHeaderView, QWidget, QLabel, QHBoxLayout, QPushButton, QInputDialog, QMessageBox, QLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem, StatusLabel
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppStyles, AppColors
from Utils.kubernetes_client import get_kubernetes_client
from kubernetes.client.rest import ApiException
from kubernetes import client
import datetime
import logging


class NamespaceOperationThread(QThread):
    """Thread for performing namespace operations asynchronously"""
    operation_completed = pyqtSignal(bool, str)  # success, message

    def __init__(self, operation, namespace_name=None, parent=None):
        super().__init__(parent)
        self.operation = operation
        self.namespace_name = namespace_name
        self.kube_client = get_kubernetes_client()

    def run(self):
        try:
            if self.operation == "create":
                self._create_namespace()
            elif self.operation == "delete":
                self._delete_namespace()
            elif self.operation == "refresh":
                self._refresh_namespaces()
        except Exception as e:
            self.operation_completed.emit(False, str(e))

    def _create_namespace(self):
        """Create a new namespace"""
        try:
            if not self.kube_client.v1:
                self.operation_completed.emit(False, "Kubernetes client not initialized")
                return

            # Create namespace object
            namespace_body = client.V1Namespace(
                metadata=client.V1ObjectMeta(name=self.namespace_name)
            )

            # Create the namespace
            self.kube_client.v1.create_namespace(body=namespace_body)
            self.operation_completed.emit(True, f"Namespace '{self.namespace_name}' created successfully")

        except ApiException as e:
            if e.status == 409:
                self.operation_completed.emit(False, f"Namespace '{self.namespace_name}' already exists")
            else:
                self.operation_completed.emit(False, f"API error: {e.reason}")
        except Exception as e:
            self.operation_completed.emit(False, f"Failed to create namespace: {str(e)}")

    def _delete_namespace(self):
        """Delete a namespace"""
        try:
            if not self.kube_client.v1:
                self.operation_completed.emit(False, "Kubernetes client not initialized")
                return

            # Delete the namespace
            self.kube_client.v1.delete_namespace(name=self.namespace_name)
            self.operation_completed.emit(True, f"Namespace '{self.namespace_name}' deletion initiated")

        except ApiException as e:
            if e.status == 404:
                self.operation_completed.emit(False, f"Namespace '{self.namespace_name}' not found")
            else:
                self.operation_completed.emit(False, f"API error: {e.reason}")
        except Exception as e:
            self.operation_completed.emit(False, f"Failed to delete namespace: {str(e)}")

class NamespacesPage(BaseResourcePage):
    """
    Displays Kubernetes namespaces with live data and resource operations using API.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "namespaces"
        self.show_namespace_dropdown = False  # Namespaces are cluster-scoped
        self.kube_client = get_kubernetes_client()
        self.operation_thread = None
        self.setup_page_ui()

    def setup_page_ui(self):
        headers = ["", "Name", "Labels", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4}

        layout = super().setup_ui("Namespaces", headers, sortable_columns)

        # Search for the button layout (QHBoxLayout) to insert our button before Refresh
        button_layout = None
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if isinstance(item, QHBoxLayout):
                button_layout = item
                break
            elif isinstance(item, QWidget):
                widget_layout = item.layout()
                if isinstance(widget_layout, QHBoxLayout):
                    button_layout = widget_layout
                    break

        if button_layout:
            # Create the Add NewNameSpace button
            self.add_namespace_button = QPushButton("Add Namespaces")
            try:
                self.add_namespace_button.setStyleSheet(AppStyles.BUTTON_STYLE)
            except AttributeError:
                self.add_namespace_button.setStyleSheet("""
                    QPushButton {
                        background-color: #3d3d3d;
                        color: white;
                        padding: 5px 15px;
                        border-radius: 2px;
                    }
                    QPushButton:hover {
                        background-color: #333333;
                    }
                    QPushButton:pressed {
                        background-color: #388E3C;
                    }
                """)
            self.add_namespace_button.clicked.connect(self.add_new_namespace)

            # Insert before Refresh button
            refresh_index = -1
            for i in range(button_layout.count()):
                widget = button_layout.itemAt(i).widget()
                if isinstance(widget, QPushButton) and "Refresh" in widget.text():
                    refresh_index = i
                    break

            if refresh_index != -1:
                button_layout.insertWidget(refresh_index, self.add_namespace_button)
            else:
                button_layout.addWidget(self.add_namespace_button)

        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        self.configure_columns()
        
        # Add delete selected button

    def configure_columns(self):
        """Configure column widths for full screen utilization"""
        if not self.table:
            return
        
        header = self.table.horizontalHeader()
        
        # Column specifications with optimized default widths
        column_specs = [
            (0, 40, "fixed"),        # Checkbox
            (1, 180, "interactive"), # Name
            (2, 260, "interactive"),  # Labels
            (3, 60, "interactive"),  # Age
            (4, 80, "stretch"),      # Status - stretch to fill remaining space
            (5, 40, "fixed")        # Actions
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
        self.table.setRowHeight(row, 40)
        resource_name = resource["name"]

        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)

        raw_data = resource.get("raw_data", {})
        labels = raw_data.get("metadata", {}).get("labels", {})
        labels_str = ", ".join([f"{k}={v}" for k, v in labels.items()]) if labels else "<none>"
        status = raw_data.get("status", {}).get("phase", "Unknown")

        columns = [resource["name"], labels_str, resource["age"]]

        for col, value in enumerate(columns):
            cell_col = col + 1

            if col == 2:
                try:
                    num = int(value.replace('d', '').replace('h', '').replace('m', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)

            if col == 0:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setForeground(QColor(AppColors.TEXT_TABLE))
            self.table.setItem(row, cell_col, item)

        status_col = 4
        if status == "Active":
            color = AppColors.STATUS_ACTIVE
        elif status == "Terminating":
            color = AppColors.STATUS_WARNING
        else:
            color = AppColors.STATUS_ERROR

        status_widget = StatusLabel(status, color)
        status_widget.clicked.connect(lambda: self.table.selectRow(row))
        self.table.setCellWidget(row, status_col, status_widget)

        # Replace the action button creation section with this:
        action_button = self._create_action_button(row, resource["name"], "")
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)

        # Connect the action button to handle the click properly
        action_button.clicked.connect(lambda checked, name=resource_name: self._handle_action_button_click(name))

        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(columns) + 2, action_container)

    def refresh_table(self):
        """Refresh the namespaces table using async resource loading"""
        try:
            # Clear table before loading
            self.clear_table()
            
            # Use base class async loading method
            self.load_data()
            
        except Exception as e:
            logging.error(f"Error refreshing namespace table: {e}")
            QMessageBox.critical(self, "Error", f"Unexpected error while refreshing: {str(e)}")

    def _calculate_age(self, creation_timestamp):
        """Calculate age from creation timestamp"""
        if not creation_timestamp:
            return "Unknown"

        try:
            # Convert to datetime if it's a string
            if isinstance(creation_timestamp, str):
                created_time = datetime.datetime.fromisoformat(creation_timestamp.replace('Z', '+00:00'))
            else:
                # Assume it's already a datetime object
                created_time = creation_timestamp.replace(tzinfo=datetime.timezone.utc)

            now = datetime.datetime.now(datetime.timezone.utc)
            diff = now - created_time

            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60

            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
        except Exception as e:
            logging.warning(f"Error calculating age: {e}")
            return "Unknown"

    def add_new_namespace(self):
        """Add a new namespace using Kubernetes API"""
        namespace_name, ok = QInputDialog.getText(self, "Add New Namespace", "Enter namespace name:")

        if ok and namespace_name:
            # Validate namespace name
            if not namespace_name.strip():
                QMessageBox.warning(self, "Invalid Name", "Namespace name cannot be empty")
                return

            # Check for valid namespace name (basic validation)
            if not namespace_name.replace('-', '').replace('.', '').isalnum():
                QMessageBox.warning(self, "Invalid Name", "Namespace name can only contain alphanumeric characters, hyphens, and periods")
                return

            # Start the operation in a separate thread
            self.operation_thread = NamespaceOperationThread("create", namespace_name, self)
            self.operation_thread.operation_completed.connect(self._on_operation_completed)
            self.operation_thread.start()

            # Disable the button while operation is in progress
            self.add_namespace_button.setEnabled(False)
            self.add_namespace_button.setText("Creating...")

    def handle_row_click(self, row, column):
        if column != self.table.columnCount() - 1:
            self.table.selectRow(row)
            resource_name = None
            namespace = None

            if self.table.item(row, 1) is not None:
                resource_name = self.table.item(row, 1).text()
            if self.table.item(row, 2) is not None:
                namespace = self.table.item(row, 2).text()

            if resource_name:
                parent = self.parent()
                while parent and not hasattr(parent, 'detail_manager'):
                    parent = parent.parent()

                if parent and hasattr(parent, 'detail_manager'):
                    resource_type = self.resource_type
                    if resource_type.endswith('s'):
                        resource_type = resource_type[:-1]
                    parent.detail_manager.show_detail(resource_type, resource_name, namespace)

    def _handle_action_button_click(self, resource_name):
        """Handle action button click to show context menu with edit and delete options"""
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)

        # Add edit action
        edit_action = menu.addAction("Edit")
        edit_action.triggered.connect(lambda: self._edit_namespace_yaml(resource_name))

        # Add separator
        menu.addSeparator()

        # Add delete action
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self._delete_namespace(resource_name))

        # Show menu at cursor position
        menu.exec(self.cursor().pos())

    def _delete_namespace(self, namespace_name):
        """Delete a specific namespace using Kubernetes API"""
        # Check if it's a system namespace and warn user
        system_namespaces = ["default", "kube-system", "kube-public", "kube-node-lease"]
        if namespace_name in system_namespaces:
            reply = QMessageBox.warning(
                self,
                "Delete System Namespace",
                f"'{namespace_name}' is a system namespace. Deleting it may cause cluster issues.\n\nAre you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Confirm deletion
        result = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete namespace '{namespace_name}'?\n\nThis will also delete all resources within this namespace.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        # Start the deletion operation in a separate thread
        self.operation_thread = NamespaceOperationThread("delete", namespace_name, self)
        self.operation_thread.operation_completed.connect(self._on_operation_completed)
        self.operation_thread.start()

    def _edit_namespace_yaml(self, namespace_name):
        """Edit namespace by opening YAML section in detail panel"""
        try:
            # Find the parent window that has detail_manager
            parent = self.parent()
            while parent and not hasattr(parent, 'detail_manager'):
                parent = parent.parent()

            if parent and hasattr(parent, 'detail_manager'):
                # Show detail panel for the namespace
                parent.detail_manager.show_detail("namespace", namespace_name, "")

                # Switch to YAML tab and enable edit mode after a short delay
                QTimer.singleShot(100, lambda: self._enable_yaml_edit_mode(parent.detail_manager))
            else:
                QMessageBox.warning(self, "Error", "Could not access detail panel for editing.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open YAML editor: {str(e)}")

    def _enable_yaml_edit_mode(self, detail_manager):
        """Enable YAML edit mode in the detail panel"""
        try:
            if detail_manager._detail_page and detail_manager._detail_page.isVisible():
                detail_page = detail_manager._detail_page

                # Switch to YAML tab (index 2: Overview=0, Details=1, YAML=2, Events=3)
                detail_page.tab_widget.setCurrentIndex(2)

                # Enable edit mode in YAML section after tab loads
                QTimer.singleShot(200, lambda: self._activate_yaml_editor(detail_page))
        except Exception as e:
            logging.error(f"Error enabling YAML edit mode: {e}")

    def _activate_yaml_editor(self, detail_page):
        """Activate the YAML editor for editing"""
        try:
            # Get the YAML section (index 2)
            yaml_section = detail_page.tab_widget.widget(2)

            if yaml_section and hasattr(yaml_section, 'toggle_yaml_edit_mode'):
                # Check if already in edit mode
                if yaml_section.yaml_editor.isReadOnly():
                    # Enable edit mode
                    yaml_section.toggle_yaml_edit_mode()

                    # Optional: Show a message that edit mode is enabled
                    logging.info("YAML edit mode enabled for namespace")
        except Exception as e:
            logging.error(f"Error activating YAML editor: {e}")

    def _on_operation_completed(self, success, message):
        """Handle completion of namespace operation"""
        # Re-enable the add button if it was disabled
        if hasattr(self, 'add_namespace_button'):
            self.add_namespace_button.setEnabled(True)
            self.add_namespace_button.setText("Add Namespaces")

        if success:
            QMessageBox.information(self, "Success", message)
            # Refresh the table to show changes
            self.refresh_table()
        else:
            QMessageBox.critical(self, "Error", message)

        # Clean up thread
        if hasattr(self, 'operation_thread') and self.operation_thread:
            try:
                self.operation_thread.deleteLater()
            except Exception as e:
                logging.error(f"Error deleting operation thread: {e}")
            finally:
                self.operation_thread = None

    def delete_resource(self, resource_name, resource_namespace):
        """Override to handle namespace deletion specifics - called by base class"""
        self._delete_namespace(resource_name)

    def closeEvent(self, event):
        """Clean up when the widget is closed"""
        # Stop any running operations
        if hasattr(self, 'operation_thread') and self.operation_thread and self.operation_thread.isRunning():
            try:
                self.operation_thread.quit()
                self.operation_thread.wait(1000)
            except Exception as e:
                logging.error(f"Error stopping operation thread: {e}")

        super().closeEvent(event)
    
    def load_data(self):
        """Load namespace data using async resource loader"""
        try:
            # Use base class async loading with proper resource type
            super().load_data()
        except Exception as e:
            logging.error(f"Error in load_data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load namespaces: {str(e)}")
    
    def force_load_data(self):
        """Force load namespace data using async resource loader"""
        try:
            # Use base class async loading with proper resource type
            super().force_load_data()
        except Exception as e:
            logging.error(f"Error in force_load_data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load namespaces: {str(e)}")