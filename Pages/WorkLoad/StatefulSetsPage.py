"""
Dynamic implementation of the StatefulSets page with live Kubernetes data and resource operations.
"""

import concurrent.futures
import logging

from PyQt6.QtWidgets import QHeaderView, QInputDialog, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors
from UI.toast_notification import get_toast_manager
from Utils.data_formatters import parse_age_to_seconds
from Utils.kubernetes_client import get_kubernetes_client
from Utils.qt_utils import is_valid

class StatefulSetsPage(BaseResourcePage):
    """
    Displays Kubernetes StatefulSets with live data and resource operations.

    Features:
    1. Dynamic loading of StatefulSets from the cluster
    2. Editing StatefulSets with editor
    3. Deleting StatefulSets (individual and batch)
    4. Resource details viewer
    5. Scale (with HPA pre-scan) and Restart Rollout (with OnDelete warning),
       both guarded against duplicate concurrent operations and surfacing
       async completion feedback.
    """

    # Upper bound (seconds) on the HPA pre-scan before the Scale dialog opens.
    # A healthy cluster answers well within this; past it we open the dialog
    # without the HPA warning rather than freeze the UI on a slow API server.
    _HPA_SCAN_TIMEOUT = 1.5
    _MAX_SCALE_LIMIT = 100000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "statefulsets"
        # Concurrency guardrail keyed by (name, namespace) — matches the
        # completion-signal payload shape for O(1) lookup. Added on confirmed
        # Scale/Restart, dropped in the completion handler's finally block.
        self._in_flight_ops: set = set()
        # Connect once at construction, then filter by payload in the slot —
        # see DeploymentsPage for why per-click connections misfire under
        # concurrent operations.
        kc = get_kubernetes_client()
        try:
            kc.statefulset_scale_completed.connect(self._on_scale_completed)
            kc.statefulset_restart_completed.connect(self._on_restart_completed)
        except Exception as e:
            logging.warning(f"StatefulSetsPage: signal wiring failed: {e}")
        self.setup_page_ui()

    def setup_page_ui(self):
        """Set up the main UI elements for the StatefulSets page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Pods", "Replicas", "Age", ""]
        sortable_columns = {1, 2, 3, 4, 5}

        # Set up the base UI components
        super().setup_ui("Stateful Sets", headers, sortable_columns)

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
            (2, 90, "interactive"),  # Namespace
            (3, 80, "interactive"),  # POds
            (4, 70, "interactive"),  # Replicas
            (5, 80, "interactive"),  # Age
            (6, 40, "fixed")         # Actions
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
            4: 90,   # Replicas
            5: 60,   # Age
            6: 40,   # Actions
        }
        
        if min_col_widths:
            explicit_mins.update(min_col_widths)
            
        explicit_maxes = {
            2: 150,  # Namespace
            3: 110,  # Pods
            4: 110,  # Replicas
            5: 80,   # Age
        }
        
        if max_col_widths:
            explicit_maxes.update(max_col_widths)
            
        super()._auto_resize_columns(max_col_widths=explicit_maxes, min_col_widths=explicit_mins)

    def populate_resource_row(self, row, resource):
        """
        Populate a single row with StatefulSet data
        """
        # Set row height
        self.table.setRowHeight(row, 42)

        # Create checkbox for row selection - styling handled by BaseResourcePage
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)

        # Get pre-parsed pods and replicas count from resource dict
        pods_str = resource.get("pods", "0/0")
        replicas_str = str(resource.get("replicas", "0"))

        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            pods_str,
            replicas_str,
            resource["age"]
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
            elif col == 3:  # Replicas column
                try:
                    replicas_value = float(value)
                except ValueError:
                    replicas_value = 0
                item = SortableTableWidgetItem(value, replicas_value)
            elif col == 4:  # Age column
                age_value = parse_age_to_seconds(value)
                item = SortableTableWidgetItem(value, age_value)
            else:
                item = SortableTableWidgetItem(value)

            # Set text alignment
            if col in [1, 2, 3, 4]:  # Pods, Replicas, Age
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

    # ── Action dispatch: Scale + Restart Rollout with safeguards ─────────

    def _handle_action(self, action, target):
        """Intercept Scale / Restart Rollout to add StatefulSet-specific
        safeguards; everything else defers to the base dispatcher."""
        if action == "Scale":
            self._handle_scale_action(target)
        elif action == "Restart Rollout":
            self._handle_restart_rollout_action(target)
        else:
            super()._handle_action(action, target)

    def _handle_scale_action(self, target):
        resolved = self._get_action_resource(target)
        if resolved is None:
            return
        resource, name, namespace = resolved
        key = (name, namespace)

        if key in self._in_flight_ops:
            self._notify_in_flight(name)
            return

        # HPA pre-scan, bounded so a slow or unreachable API server can't
        # freeze the UI. QInputDialog can't be mutated after show(), so we need
        # the result up front to build the message — but instead of blocking on
        # it we run the autoscaling/v{2,1} lookup on a worker thread and wait
        # only briefly. If it overruns the budget we open the dialog without the
        # warning rather than stall on it.
        hpa_warning = ""
        hpa_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = hpa_executor.submit(
                get_kubernetes_client().find_hpas_for_workload,
                "StatefulSet", name, namespace,
            )
            scan = future.result(timeout=self._HPA_SCAN_TIMEOUT)
            if scan.get("success") and scan.get("hpas"):
                hpa_names = ", ".join(scan["hpas"])
                hpa_warning = (
                    f"\n\nWarning: this StatefulSet is managed by HorizontalPodAutoscaler"
                    f" ({hpa_names}). A manual scale will be reverted by the HPA's "
                    f"next reconciliation pass."
                )
        except concurrent.futures.TimeoutError:
            logging.debug(
                f"HPA pre-scan for {name}/{namespace} exceeded "
                f"{self._HPA_SCAN_TIMEOUT}s; opening scale dialog without warning"
            )
        except Exception as e:
            logging.debug(f"HPA pre-scan failed for {name}/{namespace}: {e}")
        finally:
            # Don't join the worker; on the timeout path it exits on its own
            # once the bounded API call returns.
            hpa_executor.shutdown(wait=False)

        current = self._current_replicas(resource)
        # Surface the PVC-retention default at the decision point: scaling a
        # StatefulSet down does NOT delete the terminated pods' PVCs by
        # default (persistentVolumeClaimRetentionPolicy.whenScaled = Retain),
        # so storage lingers unless reclaimed by hand.
        prompt = (
            f"Set replica count for '{name}'."
            f"\nCurrent: {current}."
            f"\n\nPersistent volume claims for terminated pods are retained "
            f"by default. Delete manually if you need to reclaim storage."
            f"{hpa_warning}"
        )
        new_replicas, ok = QInputDialog.getInt(
            self, "Scale StatefulSet", prompt,
            value=current, min=0, max=max(current, self._MAX_SCALE_LIMIT), step=1,
        )
        if not ok:
            return
        if new_replicas == current:
            # No-op edit; skip the API round trip.
            return

        self._in_flight_ops.add(key)
        try:
            get_kubernetes_client().scale_statefulset_async(name, namespace, new_replicas)
        except Exception as e:
            self._in_flight_ops.discard(key)
            QMessageBox.critical(
                self, "Scale Failed", f"Could not start scale operation: {e}"
            )

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
        # successfully, but no pods rotate until each is deleted manually.
        # StatefulSet deletion is ordered (highest ordinal first), so the
        # rollout is stuck per-pod rather than cluster-wide (cf. DaemonSet).
        update_strategy = (spec.get("updateStrategy") or {}).get("type")
        if update_strategy == "OnDelete":
            choice = QMessageBox.warning(
                self,
                "OnDelete Strategy — Stuck Rollout",
                f"'{name}' uses the OnDelete update strategy. The restart "
                f"annotation will be applied successfully, but no pods will "
                f"rotate until you delete each one manually (in reverse "
                f"ordinal order). Until then every replica keeps running the "
                f"current pod template.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                return
        else:
            # Standard confirmation for RollingUpdate (the default). Pods
            # cycle one ordinal at a time, gated by the partition cursor.
            choice = QMessageBox.question(
                self,
                "Restart Rollout",
                f"Restart all pods of StatefulSet '{name}' in "
                f"'{namespace or 'cluster'}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                return

        self._in_flight_ops.add(key)
        try:
            get_kubernetes_client().restart_statefulset_rollout_async(name, namespace)
        except Exception as e:
            self._in_flight_ops.discard(key)
            QMessageBox.critical(
                self, "Restart Failed", f"Could not start restart operation: {e}"
            )

    # ── Completion handlers (filter by payload, drop from in-flight set) ──

    def _on_scale_completed(self, result):
        if not is_valid(self):
            return
        try:
            name = result.get("statefulset", "")
            namespace = result.get("namespace", "")
            key = (name, namespace)
            if key not in self._in_flight_ops:
                # Not ours — another StatefulSetsPage instance, a stale
                # connection, or a completion after teardown. Ignore.
                return
            try:
                if result.get("success"):
                    replicas = result.get("replicas", "?")
                    self._show_success_toast(
                        "Scale succeeded",
                        f"{name} scaled to {replicas} replicas.",
                    )
                else:
                    self._show_error_modal("Scale Failed", result)
            finally:
                self._in_flight_ops.discard(key)
        except Exception as e:
            logging.error(f"StatefulSetsPage._on_scale_completed: {e}")

    def _on_restart_completed(self, result):
        if not is_valid(self):
            return
        try:
            name = result.get("statefulset", "")
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
            logging.error(f"StatefulSetsPage._on_restart_completed: {e}")

    # ── Small helpers ────────────────────────────────────────────────────

    @staticmethod
    def _current_replicas(resource) -> int:
        """Pull current replica count from the resource's raw payload.

        Prefers spec.replicas (desired); falls back to status.replicas
        (actual); defaults to 0 on a brand-new or malformed StatefulSet.
        """
        raw = resource.get("raw_data") or {}
        spec_replicas = (raw.get("spec") or {}).get("replicas")
        if spec_replicas is not None:
            try:
                return int(spec_replicas)
            except (TypeError, ValueError):
                pass
        status_replicas = (raw.get("status") or {}).get("replicas")
        if status_replicas is not None:
            try:
                return int(status_replicas)
            except (TypeError, ValueError):
                pass
        return 0

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
        """Errors get a modal (blocking) so the operator can't miss them;
        the toast manager is reserved for success."""
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
