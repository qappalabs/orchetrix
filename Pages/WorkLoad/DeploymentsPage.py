"""
Dynamic implementation of the Deployments page with live Kubernetes data and resource operations.
Status display shows color-coded status, including multiple status conditions in different colors.
"""
import logging
import concurrent.futures

from PyQt6.QtWidgets import (
    QHeaderView, QLabel, QWidget, QHBoxLayout, QInputDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem, StatusLabel
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors
from UI.toast_notification import get_toast_manager
from Utils.data_formatters import parse_age_to_seconds
from Utils.kubernetes_client import get_kubernetes_client
from Utils.qt_utils import is_valid
import Styles.BaseDetailSectionStyles as BaseDetailSectionStyles

from UI.ThemeManager import get_theme_manager

class MultiColorStatusLabel(QWidget):
    """Widget that displays status conditions with different colors in a single label."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)  # Space between different status text
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Make sure this widget has a transparent background
        self.setStyleSheet("background-color: transparent;")

    def _get_status_color(self, status, theme):
        """Helper to get dynamic theme-aware color for status condition."""
        if status == "Available":
            return theme.colors.STATUS_ACTIVE
        elif status == "Progressing":
            return theme.colors.STATUS_PROGRESS
        elif "Failure" in status or "Failed" in status or status == "ReplicaFailure":
            return theme.colors.STATUS_ERROR
        elif status == "<none>":
            return theme.colors.TEXT_SECONDARY
        else:
            return theme.colors.TEXT_SECONDARY

    def set_status_text(self, status_text):
        """Set status text, parsing multiple statuses if present."""
        # Clear any existing labels
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        theme = get_theme_manager().get_current_theme()

        # If no status text, show an empty label
        if not status_text:
            label = QLabel("<none>")
            label.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY};")
            self.layout.addWidget(label)
            return

        # Parse status text - split by space
        statuses = status_text.split()

        for status in statuses:
            label = QLabel(status)
            color = self._get_status_color(status, theme)
            label.setStyleSheet(
                BaseDetailSectionStyles.get_custom_badge_style(color, is_small=True))
            self.layout.addWidget(label)

    def refresh_theme_style(self):
        """Refresh the style of all labels inside the layout for theme changes."""
        theme = get_theme_manager().get_current_theme()
        for i in range(self.layout.count()):
            item = self.layout.itemAt(i)
            if item and item.widget():
                label = item.widget()
                if isinstance(label, QLabel):
                    status = label.text()
                    color = self._get_status_color(status, theme)
                    label.setStyleSheet(
                        BaseDetailSectionStyles.get_custom_badge_style(color, is_small=True))

class DeploymentsPage(BaseResourcePage):
    """
    Displays Kubernetes Deployments with live data and resource operations.
    
    Features:
    1. Dynamic loading of Deployments from the cluster
    2. Editing Deployments with editor
    3. Deleting Deployments (individual and batch)
    4. Resource details viewer
    """

    _HPA_SCAN_TIMEOUT = 1.5
    _MAX_SCALE_LIMIT = 100000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "deployments"
        # Concurrency guardrail keyed by (name, namespace) — same shape as the
        # completion-signal payload, so the handler looks up in O(1). Keys are
        # added on confirmed Scale/Restart and dropped in the completion
        # handler's finally block, guaranteeing release even on exceptions.
        self._in_flight_ops: set = set()
        # Connect once at construction (NOT per-click): connecting per click
        # would fire the slot N times for N concurrent operations. Connecting
        # once + filtering by payload (deployment, namespace) avoids that, and
        # Qt's parent-child cleanup severs the connection on page destruction.
        kc = get_kubernetes_client()
        try:
            kc.deployment_scale_completed.connect(self._on_scale_completed)
            kc.deployment_restart_completed.connect(self._on_restart_completed)
        except Exception as e:
            logging.warning(f"DeploymentsPage: signal wiring failed: {e}")
        self.setup_page_ui()

    def setup_page_ui(self):
        """Set up the main UI elements for the Deployments page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Pods", "Replicas", "Age", "Conditions", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6}

        # Set up the base UI components
        super().setup_ui("Deployments", headers, sortable_columns)

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
            (1, 220, "interactive"), # Name
            (2, 120, "interactive"),  # Namespace
            (3, 80, "interactive"),  # pod
            (4, 100, "interactive"),  # Replicas
            (5, 90, "interactive"), # Age
            (6, 100, "stretch"), # Conditions
            (7, 40, "fixed"),  # Action
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
        """Override to provide explicit widths for columns where headers are clipping."""
        explicit_mins = {
            # 0 is Checkbox
            1: 120,  # Name - lower floor allows it to shrink more
            2: 120,  # Namespace
            3: 80,   # Pods
            4: 90,   # Replicas
            5: 60,   # Age
            6: 120,  # Conditions
            7: 40,   # Actions
        }
        
        # Merge with any caller overrides
        if min_col_widths:
            explicit_mins.update(min_col_widths)
            
        explicit_maxes = {
            2: 150,  # Namespace - don't let it take up all the extra space
            3: 110,  # Pods
            4: 110,  # Replicas
            5: 80,   # Age
        }
        
        if max_col_widths:
            explicit_maxes.update(max_col_widths)
            
        super()._auto_resize_columns(max_col_widths=explicit_maxes, min_col_widths=explicit_mins)

    def _project_row_data(self, resource):
        """Project a deployment resource into a flat dict for diff comparison.

        Mirrors the semantic columns rendered by populate_resource_row so the
        diff engine can skip rebuilds when nothing visible changed.  Stores
        only display-text values — never colors or styles (the Conditions
        multi-color widget resolves its own colors at render time).
        """
        return {
            "uid": self._build_uid_from_resource(resource),
            "name": resource.get("name", ""),
            "namespace": resource.get("namespace", ""),
            "pods": resource.get("pods", "0/0"),
            "replicas": str(resource.get("replicas", "0")),
            "conditions": resource.get("conditions", ""),
            "age": resource.get("age", ""),
            "_raw": resource,  # internal — excluded from diff comparison
        }

    def populate_resource_row(self, row, resource):
        """
        Populate a single row with Deployment data
        """
        # Set row height
        self.table.setRowHeight(row, 42)

        # Create checkbox for row selection - styling handled by BaseResourcePage
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)

        # Get dynamic stats directly from pre-parsed resource fields
        pods_str = resource.get("pods", "0/0")
        replicas_str = str(resource.get("replicas", "0"))
        conditions_str = resource.get("conditions", "")

        age_str = resource["age"]

        # Prepare data columns - all except Conditions
        columns = [
            resource["name"],
            resource["namespace"],
            pods_str,
            replicas_str,
            age_str
        ]

        # Add normal columns to table (all except Conditions)
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column

            # Handle numeric columns for sorting
            if col == 2:  # Pods column
                try:
                    available, total = value.split("/")
                    # Calculate as percentage for better sorting
                    pods_value = (float(available) / float(total)) * 100 if float(total) > 0 else 0
                except (ValueError, IndexError, ZeroDivisionError):
                    pods_value = 0
                item = SortableTableWidgetItem(value, pods_value)
            elif col == 3:  # Replicas column
                try:
                    replicas_value = float(value)
                except ValueError:
                    replicas_value = 0
                item = SortableTableWidgetItem(value, replicas_value)
            elif col == 4:  # Age column
                item = SortableTableWidgetItem(value, parse_age_to_seconds(value))
            else:
                item = SortableTableWidgetItem(value)

            # Set text alignment
            if col in [2, 3, 4]:  # Pods, Replicas, Age
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # Set item styling and alignment
            self.table.setItem(row, cell_col, self.style_table_item(item, is_name=(col == 0)))

        # Add the Conditions column as a special multi-color widget (cell 6)
        conditions_widget = MultiColorStatusLabel()
        conditions_widget.set_status_text(conditions_str)
        self.table.setCellWidget(row, 6, conditions_widget)

        # Create and add action button - styling handled by BaseResourcePage
        action_button = self._create_action_button(row, resource_name, resource["namespace"])
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, 7, action_container)

    # ── Action dispatch: Scale + Restart Rollout with safeguards ─────────

    def _handle_action(self, action, target):
        """Intercept Scale / Restart Rollout to add deployment-specific
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
                "Deployment", name, namespace,
            )
            scan = future.result(timeout=self._HPA_SCAN_TIMEOUT)
            if scan.get("success") and scan.get("hpas"):
                hpa_names = ", ".join(scan["hpas"])
                hpa_warning = (
                    f"\n\nWarning: this deployment is managed by HorizontalPodAutoscaler"
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
            hpa_executor.shutdown(wait=False)

        current = self._current_replicas(resource)
        prompt = (
            f"Set replica count for '{name}'."
            f"\nCurrent: {current}."
            f"{hpa_warning}"
        )
        new_replicas, ok = QInputDialog.getInt(
            self, "Scale Deployment", prompt,
            value=current, min=0, max=max(current, self._MAX_SCALE_LIMIT), step=1,
        )
        if not ok:
            return
        if new_replicas == current:
            # No-op edit; skip the API round trip.
            return

        self._in_flight_ops.add(key)
        try:
            get_kubernetes_client().scale_deployment_async(name, namespace, new_replicas)
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

        # Pre-flight 1 — paused: the controller accepts the patch and silently
        # queues it, never rotating pods until resumed. Warn before the user
        # waits on what looks like a successful op.
        if spec.get("paused"):
            choice = QMessageBox.warning(
                self,
                "Deployment is Paused",
                f"'{name}' is currently paused. The restart will be queued but no "
                f"pods will rotate until the deployment is resumed.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                return

        # Pre-flight 2 — Recreate strategy: the controller WILL execute the
        # restart, but terminates all pods simultaneously, causing downtime
        # for the duration of image pull + container init. Warn before
        # proceeding.
        strategy_type = (spec.get("strategy") or {}).get("type")
        if strategy_type == "Recreate":
            choice = QMessageBox.warning(
                self,
                "Recreate Strategy — Downtime Warning",
                f"'{name}' uses the Recreate strategy. All pods will be terminated "
                f"simultaneously before new ones start, causing application downtime "
                f"for the duration of image pull + container init.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                return

        # Standard confirmation for RollingUpdate (the common path).
        if not spec.get("paused") and strategy_type != "Recreate":
            choice = QMessageBox.question(
                self,
                "Restart Rollout",
                f"Restart all pods of deployment '{name}' in '{namespace or 'cluster'}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                return

        self._in_flight_ops.add(key)
        try:
            get_kubernetes_client().restart_deployment_rollout_async(name, namespace)
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
            name = result.get("deployment", "")
            namespace = result.get("namespace", "")
            key = (name, namespace)
            if key not in self._in_flight_ops:
                # Not ours — another DeploymentsPage instance, a stale
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
            logging.error(f"DeploymentsPage._on_scale_completed: {e}")

    def _on_restart_completed(self, result):
        if not is_valid(self):
            return
        try:
            name = result.get("deployment", "")
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
            logging.error(f"DeploymentsPage._on_restart_completed: {e}")

    # ── Small helpers ────────────────────────────────────────────────────

    @staticmethod
    def _current_replicas(resource) -> int:
        """Pull current replica count from the resource's raw payload.

        Prefers spec.replicas (desired); falls back to status.replicas
        (actual); defaults to 0 on a brand-new or malformed deployment.
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
