"""
Dynamic implementation of the DaemonSets page with live Kubernetes data and resource operations.
"""
import logging

from PyQt6.QtWidgets import QHeaderView, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors
from UI.toast_notification import get_toast_manager
from Utils.data_formatters import parse_age_to_seconds
from Utils.kubernetes_client import get_kubernetes_client
from Utils.qt_utils import is_valid

class DaemonSetsPage(BaseResourcePage):
    """
    Displays Kubernetes DaemonSets with live data and resource operations.

    Features:
    1. Dynamic loading of DaemonSets from the cluster
    2. Editing DaemonSets with editor
    3. Deleting DaemonSets (individual and batch)
    4. Resource details viewer
    5. Restart Rollout with OnDelete-strategy warning, in-flight de-duplication,
       and async completion feedback (toast on success, modal on failure).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "daemonsets"
        # Restart-only in-flight guard. DaemonSets have no replicas concept,
        # so there's no Scale operation to track here.
        self._in_flight_ops: set = set()
        try:
            get_kubernetes_client().daemonset_restart_completed.connect(
                self._on_restart_completed
            )
        except Exception as e:
            logging.warning(f"DaemonSetsPage: restart signal wiring failed: {e}")
        self.setup_page_ui()

    def setup_page_ui(self):
        """Set up the main UI elements for the DaemonSets page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Pods", "Node Selector", "Age", ""]
        sortable_columns = {1, 2, 3, 5}

        # Set up the base UI components
        super().setup_ui("Daemon Sets", headers, sortable_columns)

        # Configure column widths
        self.configure_columns()

    def configure_columns(self):
        """Configure column widths for full screen utilization"""
        if not self.table:
            return

        header = self.table.horizontalHeader()

        # Column specifications with optimized default widths
        column_specs = [
            (0, 40, "fixed"),        # Checkbox
            (1, 140, "stretch"),     # Name
            (2, 100, "interactive"),  # Namespace
            (3, 90, "interactive"),  # Pods
            (4, 180, "interactive"),  # Node Selector
            (5, 80, "interactive"),  # Age
            (6, 40, "fixed"),        # Actions
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

    def _auto_resize_columns(self, max_col_widths=None, min_col_widths=None):
        """Override to provide explicit widths for columns to let Name stretch."""
        explicit_mins = {
            1: 140,  # Name
            2: 100,  # Namespace
            3: 90,   # Pods
            4: 150,  # Node Selector
            5: 60,   # Age
            6: 40,   # Actions
        }
        
        if min_col_widths:
            explicit_mins.update(min_col_widths)
            
        explicit_maxes = {
            2: 150,  # Namespace
            3: 110,  # Pods
            4: 250,  # Node Selector
            5: 80,   # Age
        }
        
        if max_col_widths:
            explicit_maxes.update(max_col_widths)
            
        super()._auto_resize_columns(max_col_widths=explicit_maxes, min_col_widths=explicit_mins)

    def populate_resource_row(self, row, resource):
        """
        Populate a single row with DaemonSet data
        """
        # Set row height
        self.table.setRowHeight(row, 42)

        # Create checkbox for row selection - styling handled by BaseResourcePage
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)

        # Get pre-parsed pods and node selector from resource dict
        pods_str = resource.get("pods", "0/0")
        node_selector = resource.get("node_selector", "<none>")

        age_str = resource["age"]

        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            pods_str,
            node_selector,
            age_str
        ]

        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column

            # Handle numeric columns for sorting
            if col == 2:  # Pods column
                try:
                    current, desired = value.split("/")
                    pods_value = float(current) / float(desired) if float(desired) > 0 else 0
                except (ValueError, ZeroDivisionError):
                    pods_value = 0
                item = SortableTableWidgetItem(value, pods_value)
            elif col == 4:  # Age column
                item = SortableTableWidgetItem(value, parse_age_to_seconds(value))
            else:
                item = SortableTableWidgetItem(value)

            # Set text alignment
            if col in [1, 2, 3, 4]:  # Namespace, Pods, Node Selector, Age
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Set text color
            item.setForeground(QColor(AppColors.TEXT_TABLE))

            # Add the item to the table
            self.table.setItem(row, cell_col, item)

        # Create and add action button - styling handled by BaseResourcePage
        action_button = self._create_action_button(row, resource_name, resource["namespace"])
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, len(columns) + 1, action_container)

    # ── Restart Rollout: OnDelete warning + in-flight guard + feedback ──

    def _handle_action(self, action, target):
        """Intercept Restart Rollout to add DaemonSet-specific safeguards.

        Everything else defers to the base dispatcher unchanged.
        """
        if action == "Restart Rollout":
            self._handle_restart_rollout_action(target)
        else:
            super()._handle_action(action, target)

    def _handle_restart_rollout_action(self, target):
        resolved = self._get_action_resource(target)
        if resolved is None:
            return
        resource, name, namespace = resolved
        key = (name, namespace)

        if key in self._in_flight_ops:
            self._notify_in_flight(name)
            return

        spec = (resource.get("raw_data") or {}).get("spec") or {}

        # Pre-flight — OnDelete update strategy. The restart annotation lands
        # successfully, but no DaemonSet pods rotate anywhere in the cluster
        # until each is deleted manually. Warn with copy that conveys the
        # cluster-wide (not ordered-per-pod) impact.
        update_strategy = (spec.get("updateStrategy") or {}).get("type")
        if update_strategy == "OnDelete":
            choice = QMessageBox.warning(
                self,
                "OnDelete Strategy — Cluster-Wide Stuck Rollout",
                f"'{name}' uses the OnDelete update strategy. The restart "
                f"annotation will be applied successfully, but no DaemonSet "
                f"pods will rotate anywhere in the cluster until you delete "
                f"each one manually. Every node will continue running the "
                f"current pod template until then.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                return
        else:
            # Standard confirmation for RollingUpdate (the default). Pods
            # cycle one node at a time, gated by maxUnavailable.
            choice = QMessageBox.question(
                self,
                "Restart Rollout",
                f"Restart DaemonSet pods of '{name}' in "
                f"'{namespace or 'cluster'}' across all eligible nodes?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                return

        self._in_flight_ops.add(key)
        try:
            get_kubernetes_client().restart_daemonset_rollout_async(name, namespace)
        except Exception as e:
            self._in_flight_ops.discard(key)
            QMessageBox.critical(
                self, "Restart Failed", f"Could not start restart operation: {e}"
            )

    def _on_restart_completed(self, result):
        """Filter the shared signal by payload, surface feedback, clear guard."""
        if not is_valid(self):
            return
        try:
            name = result.get("daemonset", "")
            namespace = result.get("namespace", "")
            key = (name, namespace)
            if key not in self._in_flight_ops:
                return
            try:
                if result.get("success"):
                    self._show_success_toast(
                        "Restart triggered",
                        f"Rollout restart triggered for {name}.",
                    )
                else:
                    self._show_error_modal("Restart Failed", result)
            finally:
                self._in_flight_ops.discard(key)
        except Exception as e:
            logging.error(f"DaemonSetsPage._on_restart_completed: {e}")

    def _notify_in_flight(self, name: str):
        try:
            tm = get_toast_manager()
            if tm is not None:
                tm.show_info(
                    "Operation in progress",
                    f"An operation on {name} is still running.",
                    duration=2000,
                )
        except Exception as e:
            logging.debug(f"in-flight toast failed: {e}")

    def _show_success_toast(self, title: str, message: str):
        try:
            tm = get_toast_manager()
            if tm is not None:
                tm.show_success(title, message)
        except Exception as e:
            logging.debug(f"success toast failed: {e}")

    def _show_error_modal(self, title: str, result: dict):
        try:
            QMessageBox.critical(
                self, title, result.get("message", "Unknown error")
            )
        except Exception as e:
            logging.debug(f"error modal failed: {e}")

    def handle_row_click(self, row, column):
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
                    # Get singular resource type
                    resource_type = self.resource_type
                    if resource_type.endswith('s'):
                        resource_type = resource_type[:-1]

                    parent.detail_manager.show_detail(resource_type, resource_name, namespace)
