"""
Dynamic implementation of the Namespaces page with live Kubernetes data.
"""

from PyQt6.QtWidgets import (
    QHeaderView, QWidget, QLabel, QHBoxLayout, QPushButton, QInputDialog, QMessageBox, QLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppStyles, AppColors
import subprocess
import json

import subprocess
import json

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


class NamespacesPage(BaseResourcePage):
    """
    Displays Kubernetes namespaces with live data and resource operations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "namespaces"
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

    def configure_columns(self):
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 80)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 100)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 40)

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
                    num = int(value.replace('d', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)

            if col in (0, 1):
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

        action_button = self._create_action_button(row, resource["name"], "")
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(columns) + 2, action_container)

    def refresh_table(self):
        try:
            cmd = ["kubectl", "get", "namespaces", "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            namespaces_data = json.loads(result.stdout)
            items = namespaces_data.get("items", [])

            self.table.setRowCount(0)
            for row, item in enumerate(items):
                self.table.insertRow(row)
                resource = {
                    "name": item["metadata"]["name"],
                    "age": self._calculate_age(item["metadata"]["creationTimestamp"]),
                    "raw_data": item
                }
                self.populate_resource_row(row, resource)

        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh namespaces: {e.stderr.strip()}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unexpected error while refreshing: {str(e)}")

    def _calculate_age(self, creation_timestamp):
        return "1d"  # Placeholder

    def add_new_namespace(self):
        namespace_name, ok = QInputDialog.getText(self, "Add New Namespace", "Enter namespace name:")

        if ok and namespace_name:
            try:
                cmd = ["kubectl", "create", "namespace", namespace_name]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)

                if result.returncode == 0:
                    self.refresh_table()
                else:
                    QMessageBox.critical(self, "Error", f"Failed to create namespace: {result.stderr.strip()}")

            except subprocess.CalledProcessError as e:
                QMessageBox.critical(self, "Error", f"Error creating namespace: {e.stderr.strip()}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Unexpected error: {str(e)}")

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
