"""
Dynamic implementation of the Persistent Volume Claims page with live Kubernetes data.
"""

from PyQt6.QtWidgets import (QHeaderView)
from PyQt6.QtCore import Qt, QTimer, QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6 import sip

from Base_Components.base_components import SortableTableWidgetItem, StatusLabel
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors
from Utils.data_formatters import parse_age_to_seconds, parse_memory_value
from Utils.kubernetes_client import get_kubernetes_client


def _memory_to_bytes(value):
    """Parse a memory string (e.g. '10Gi', '100Mi') into float bytes for numeric sorting."""
    try:
        return parse_memory_value(value).value
    except Exception:
        return 0


class _PodLookupSignals(QObject):
    result_ready = pyqtSignal(dict)  # {(namespace, claim_name): [pod_name, ...]}


class _PodLookupWorker(QRunnable):
    def __init__(self, kube_client, namespace_filter):
        super().__init__()
        self.kube_client = kube_client
        self.namespace_filter = namespace_filter
        self.signals = _PodLookupSignals()

    def run(self):
        result = {}
        try:
            if not self.kube_client:
                self.signals.result_ready.emit(result)
                return

            ns = self.namespace_filter
            if not ns or ns == "All Namespaces" or ns == "all":
                pod_list = self.kube_client.list_pod_for_all_namespaces()
            else:
                pod_list = self.kube_client.list_namespaced_pod(namespace=ns)

            for pod in getattr(pod_list, "items", []) or []:
                pod_ns = pod.metadata.namespace if pod.metadata else None
                pod_name = pod.metadata.name if pod.metadata else None
                if not pod_ns or not pod_name:
                    continue
                volumes = getattr(pod.spec, "volumes", None) or []
                for vol in volumes:
                    pvc = getattr(vol, "persistent_volume_claim", None)
                    if not pvc:
                        continue
                    claim_name = getattr(pvc, "claim_name", None)
                    if not claim_name:
                        continue
                    result.setdefault((pod_ns, claim_name), []).append(pod_name)
        except Exception as e:
            import logging
            logging.debug(f"PodLookupWorker failed: {e}")
        finally:
            self.signals.result_ready.emit(result)


class PersistentVolumeClaimsPage(BaseResourcePage):
    """
    Displays Kubernetes persistent volume claims with live data and resource operations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "persistentvolumeclaims"  # Set resource type for kubectl
        self._thread_pool = QThreadPool.globalInstance()
        self._pvc_pods_map = {}
        self.setup_page_ui()

    def setup_page_ui(self):
        """Set up the main UI elements for the Persistent Volume Claims page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Storage Class", "Size", "Pods", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7}

        # Set up the base UI components
        super().setup_ui("Persistent Volume Claims", headers, sortable_columns)

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
            (1, 140, "stretch"),     # Name - stretch to fill remaining space
            (2, 90, "interactive"),  # Namespace
            (3, 80, "interactive"),  # Storage Class
            (4, 70, "interactive"),  # Size
            (5, 130, "interactive"), # Pods
            (6, 110, "interactive"), # Age
            (7, 80, "interactive"),  # Status
            (8, 40, "fixed")         # Actions
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
        """Override to provide explicit widths for columns to let Name stretch and avoid clipping."""
        explicit_mins = {
            1: 120,  # Name
            2: 100,  # Namespace
            3: 120,  # Storage Class
            4: 80,   # Size
            5: 100,  # Pods
            6: 60,   # Age
            7: 80,   # Status
            8: 40,   # Actions
        }
        if min_col_widths:
            explicit_mins.update(min_col_widths)
        explicit_maxes = {
            2: 150,  # Namespace
            3: 180,  # Storage Class
            4: 100,  # Size
            5: 150,  # Pods
            6: 80,   # Age
            7: 100,  # Status
        }
        if max_col_widths:
            explicit_maxes.update(max_col_widths)
        super()._auto_resize_columns(max_col_widths=explicit_maxes, min_col_widths=explicit_mins)

    def populate_resource_row(self, row, resource):
        """
        Populate a single row with persistent volume claim data from live Kubernetes resources
        """
        # Set row height once
        self.table.setRowHeight(row, 42)

        # Create checkbox for row selection
        resource_name = resource["name"]
        # Checkbox styling handled by BaseResourcePage
        checkbox_container = self._create_checkbox_container(row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)

        # Extract data from raw_data
        raw_data = resource.get("raw_data", {})
        spec = raw_data.get("spec", {})
        status = raw_data.get("status", {})

        # Get storage class
        storage_class = spec.get("storageClassName", "<none>")
        if not storage_class:
            storage_class = "<none>"

        # Get size
        size = "<none>"
        if status.get("capacity") and status["capacity"].get("storage"):
            size = status["capacity"]["storage"]
        elif spec.get("resources") and spec["resources"].get("requests") and spec["resources"]["requests"].get("storage"):
            size = spec["resources"]["requests"]["storage"]

        # Get pods using this PVC from the cached map
        key = (resource.get("namespace", "default"), resource["name"])
        pods_list = self._pvc_pods_map.get(key, [])
        pods = ", ".join(pods_list) if pods_list else "<none>"

        # Get status
        pvc_status = status.get("phase", "Unknown")

        # Prepare data columns
        columns = [
            resource["name"],        # Name
            resource["namespace"],   # Namespace
            storage_class,          # Storage Class
            size,                   # Size
            pods,                   # Pods
            resource["age"]         # Age
            # Status is handled separately as StatusLabel widget
        ]

        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column

            # Handle numeric columns for sorting
            if col == 5:  # Age column
                item = SortableTableWidgetItem(value, parse_age_to_seconds(value))
            elif col == 4:  # Pods column - sort by number of pods
                try:
                    if value == "<none>":
                        num = 0
                    elif "+" in value and "more" in value:
                        # Extract number from "pod1, pod2 +3 more" format
                        parts = value.split("+")
                        if len(parts) > 1:
                            num = int(parts[1].split()[0]) + 2  # +2 for the two shown pods
                        else:
                            num = 1
                    else:
                        # Count commas to get number of pods
                        num = len(value.split(","))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 3:  # Size column
                item = SortableTableWidgetItem(value, _memory_to_bytes(value))
            else:
                item = SortableTableWidgetItem(value)

            # Set text alignment
            if col == 0:  # Name column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Set default text color for all non-status columns
            item.setForeground(QColor(AppColors.TEXT_TABLE))

            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Add the item to the table
            self.table.setItem(row, cell_col, item)

        # Create status widget with proper color for PVCs (column 7 - Status)
        status_col = 7  # Status column index
        status_text = pvc_status

        # Pick the right color
        if status_text == "Bound":
            color = AppColors.STATUS_ACTIVE
        else:
            color = AppColors.STATUS_WARNING

        # Create status widget with proper color
        status_widget = StatusLabel(status_text, color)
        # Connect click event to select the row
        status_widget.clicked.connect(lambda: self.table.selectRow(row))
        self.table.setCellWidget(row, status_col, status_widget)

        # Create and add action button
        # Action button styling handled by BaseResourcePage
        action_button = self._create_action_button(row, resource["name"], resource["namespace"])
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, len(columns) + 2, action_container)  # +2 for checkbox and status

    def _display_resources(self, resources):
        super()._display_resources(resources)
        self._dispatch_pod_lookup()

    def _dispatch_pod_lookup(self):
        kube_client = get_kubernetes_client()
        if not kube_client:
            return
        v1_client = getattr(kube_client, "v1", None)
        namespace_filter = getattr(self, "namespace_filter", "All Namespaces")
        worker = _PodLookupWorker(v1_client, namespace_filter)
        worker.signals.result_ready.connect(self._on_pod_lookup_ready)
        self._thread_pool.start(worker)

    def _on_pod_lookup_ready(self, pvc_to_pods):
        # Guard against the page/table being torn down while the lookup was
        # in flight (worker runs on the thread pool and can finish late).
        if sip.isdeleted(self) or not getattr(self, "table", None) or sip.isdeleted(self.table):
            return
        if not pvc_to_pods:
            return
        self._pvc_pods_map.update(pvc_to_pods)

        pods_col_index = 5
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 1)
            ns_item = self.table.item(row, 2)
            if not name_item or not ns_item:
                continue
            name = name_item.text()
            namespace = ns_item.text()
            key = (namespace, name)
            if key in pvc_to_pods:
                pods_list = pvc_to_pods[key]
                new_text = ", ".join(pods_list) if pods_list else "<none>"
                num = len(pods_list)

                item = self.table.item(row, pods_col_index)
                if item:
                    item.setText(new_text)
                    item.value = num

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
                    parent.detail_manager.show_detail("persistentvolumeclaim", resource_name, namespace)
