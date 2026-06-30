"""
Dynamic CustomResource Instance Page - Shows instances of a specific CRD
Similar to how OpenLens displays custom resource instances when clicking on a CRD from sidebar
"""

import logging
from PyQt6.QtWidgets import (
    QHeaderView, QApplication, QMessageBox, QProgressDialog, QLabel
)
from PyQt6.QtCore import Qt, QTimer, QEventLoop
from PyQt6.QtGui import QColor, QFont

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors
from Utils.data_formatters import parse_age_to_seconds
from Utils.kubernetes_client import get_kubernetes_client
from datetime import datetime
import dateutil.parser
import Styles.CustomResourceInstancePageStyles as CustomResourceInstancePageStyles


class CustomResourceInstancePage(BaseResourcePage):
    """
    Dynamic page that displays instances of a specific CustomResourceDefinition.
    Each CRD gets its own page instance accessible from the sidebar.
    """

    def __init__(self, crd_name, crd_spec, parent=None):
        super().__init__(parent)
        
        self.crd_name = crd_name
        self.crd_spec = crd_spec

        # Extract and store CRD configuration
        self._extract_crd_config(crd_spec)

        # Disable unified loader search for CRD instances
        self.resource_type = None

        self.setup_page_ui()

    def _extract_crd_config(self, crd_spec):

        self.api_group = crd_spec.get("group", "")
        versions = crd_spec.get("versions", [])
        # Find the served version (preferably the storage version)
        # CRDs can have multiple versions where some are only for migration
        self.api_version = self._get_served_version(versions)
        self.plural = crd_spec.get("names", {}).get("plural", "")
        self.scope = crd_spec.get("scope", "Namespaced")

        # Log version selection for debugging multi-version CRDs
        version_names = [v.get("name", "?") for v in versions]
        if len(versions) > 1:
            logging.info(f"CRD {self.plural}: selected version '{self.api_version}' from {version_names}")

    def _get_served_version(self, versions: list) -> str:
        """Find the API version that is actually served by the cluster.

        CRDs can have multiple versions where:
        - served: true = available via API
        - storage: true = the canonical stored version

        Prefer: storage version > any served version > first version
        """
        if not versions:
            return ""

        # First, try to find the storage version (which is always served)
        for v in versions:
            if v.get("storage", False) and v.get("served", True):
                return v.get("name", "")

        # Fall back to any served version
        for v in versions:
            if v.get("served", True):  # Default to True if not specified
                return v.get("name", "")

        # Last resort: first version
        return versions[0].get("name", "") if versions else ""

    def _get_column_config(self) -> dict:

        if self.scope == "Cluster":
            return {
                'headers': ["", "Name", "Status", "Age", ""],
                'sortable_columns': {1, 2, 3},
                'column_specs': [
                    (0, 40, "fixed"),        # Checkbox
                    (1, 200, "interactive"),  # Name
                    (2, 120, "interactive"),  # Status
                    (3, 100, "stretch"),     # Age
                    (4, 40, "fixed")         # Actions
                ]
            }
        else:
            return {
                'headers': ["", "Name", "Namespace", "Status", "Age", ""],
                'sortable_columns': {1, 2, 3, 4},
                'column_specs': [
                    (0, 40, "fixed"),        # Checkbox
                    (1, 180, "interactive"),  # Name
                    (2, 120, "interactive"),  # Namespace
                    (3, 120, "interactive"),  # Status
                    (4, 100, "stretch"),     # Age
                    (5, 40, "fixed")         # Actions
                ]
            }

    def setup_page_ui(self):
        config = self._get_column_config()

        # CRITICAL: Set namespace dropdown visibility based on CRD scope
        # This was accidentally removed during refactoring
        if self.scope == "Cluster":
            self.show_namespace_dropdown = False
        else:
            self.show_namespace_dropdown = True

        # Set up the base UI components with dynamic title
        crd_display_name = self.crd_spec.get(
            "names", {}).get("kind", self.crd_name)
        page_title = f"{crd_display_name} Instances"
        super().setup_ui(page_title,
                         config['headers'], config['sortable_columns'])

        # Apply styling and configure columns
        self._apply_table_styling()
        self.configure_columns()

    def _apply_table_styling(self):
        """Table styling is handled by BaseResourcePage."""
        pass

    def configure_columns(self):
        if not self.table:
            return

        config = self._get_column_config()
        self._apply_column_configuration(config['column_specs'])

        # Ensure full width utilization after configuration
        QTimer.singleShot(100, self._ensure_full_width_utilization)

    def _apply_column_configuration(self, column_specs):

        header = self.table.horizontalHeader()

        for col_index, default_width, resize_type in column_specs:
            if col_index < self.table.columnCount():
                # .title() converts "fixed"/"interactive"/"stretch" to "Fixed"/"Interactive"/"Stretch"
                resize_mode = getattr(QHeaderView.ResizeMode, resize_type.title())
                header.setSectionResizeMode(col_index, resize_mode)
                self.table.setColumnWidth(col_index, default_width)

    def populate_resource_row(self, row, resource):
        """
        Populate a single row with custom resource instance data
        """
        # Set row height once
        self.table.setRowHeight(row, 42)

        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(
            row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)

        # Extract custom resource details from raw data
        raw_data = resource.get("raw_data", {})
        metadata = raw_data.get("metadata", {})
        status = raw_data.get("status", {})

        # Get basic information
        name = metadata.get("name", resource_name)
        namespace = metadata.get("namespace", "<none>")

        # Try to extract status information
        status_value = "Unknown"
        if status:
            # Common status fields to check
            status_fields = ["phase", "state", "status", "condition"]
            for field in status_fields:
                if field in status:
                    status_value = str(status[field])
                    break

            # If no direct status, check conditions array
            if status_value == "Unknown" and "conditions" in status:
                conditions = status.get("conditions", [])
                if conditions and isinstance(conditions, list):
                    # Get the latest condition
                    latest_condition = conditions[-1]
                    if isinstance(latest_condition, dict):
                        condition_type = latest_condition.get("type", "")
                        condition_status = latest_condition.get("status", "")
                        if condition_type and condition_status:
                            status_value = f"{condition_type}: {condition_status}"

        # Prepare data columns based on scope
        if self.scope == "Cluster":
            columns = [name, status_value, resource["age"]]
        else:
            columns = [name, namespace, status_value, resource["age"]]

        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column

            # Handle numeric columns for sorting (age)
            if (self.scope == "Cluster" and col == 2) or (self.scope == "Namespaced" and col == 3):
                num = parse_age_to_seconds(value)
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)

            # Set text alignment
            if col == 0:  # Name column
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Set text color based on status
            if (self.scope == "Cluster" and col == 1) or (self.scope == "Namespaced" and col == 2):
                # Status column - color coding
                if "running" in value.lower() or "ready" in value.lower() or "true" in value.lower():
                    item.setForeground(QColor("#4CAF50"))  # Green for healthy
                elif "pending" in value.lower() or "false" in value.lower():
                    item.setForeground(QColor("#FF9800"))  # Orange for pending
                elif "failed" in value.lower() or "error" in value.lower():
                    item.setForeground(QColor("#F44336"))  # Red for errors
                else:
                    item.setForeground(QColor(AppColors.TEXT_TABLE))
            else:
                item.setForeground(QColor(AppColors.TEXT_TABLE))

            # Add the item to the table
            self.table.setItem(row, cell_col, item)

        # Create and add action button
        action_button = self._create_action_button(
            row, resource["name"], namespace if self.scope == "Namespaced" else "")
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, len(columns) + 1, action_container)

    def handle_row_click(self, row, column):
        # Select the row
        self.table.selectRow(row)

        # Get resource details
        resource_name = None
        namespace = None

        # Get the resource name from the Name column (column 1)
        if self.table.item(row, 1) is not None:
            resource_name = self.table.item(row, 1).text()

        # Get namespace if resource is namespaced
        if self.scope == "Namespaced" and self.table.item(row, 2) is not None:
            namespace = self.table.item(row, 2).text()
            if namespace == "<none>":
                namespace = None

        # Show detail view
        if resource_name:
            # Find the ClusterView instance
            parent = self.parent()
            while parent and not hasattr(parent, 'detail_manager'):
                parent = parent.parent()

            if parent and hasattr(parent, 'detail_manager'):
                # FIXED: Get raw_data from resources list and pass it to detail view
                # This fixes the issue where detail sections couldn't load data
                # because get_resource_detail doesn't handle custom resource instances
                raw_data = self.get_raw_data_for_row(row)

                # Use the plural name as resource type for detail view
                parent.detail_manager.show_detail(
                    self.plural, resource_name, namespace, raw_data)

    def get_raw_data_for_row(self, row):
        """
        This method is used to pass raw_data to the detail view, which is necessary
        because get_resource_detail doesn't have handlers for custom resource instances.
        Uses resource name and namespace lookup (not row index) to handle sorted / filtered tables correctly.
        """
        try:
            # Get resource name from the table cell (column 1 is Name)
            name_item = self.table.item(row, 1)
            if not name_item:
                return {}
            resource_name = name_item.text()

            # Get namespace from table if resource is namespaced (column 2)
            table_namespace = None
            if self.scope == "Namespaced":
                namespace_item = self.table.item(row, 2)
                if namespace_item:
                    table_namespace = namespace_item.text()
                    if table_namespace == "<none>":
                        table_namespace = None

            # Find matching resource by name and namespace to handle sorting / filtering correctly
            for resource in self.resources:
                if resource.get("name") != resource_name:
                    continue

                # Get resource namespace from raw_data.metadata (correct path for resource structure)
                resource_namespace = resource.get("raw_data", {}).get("metadata", {}).get("namespace")

                # Explicit three-way namespace matching to prevent cross-namespace errors
                if resource_namespace and table_namespace:
                    # Both have namespaces - must match exactly
                    if resource_namespace == table_namespace:
                        return resource.get("raw_data", {})
                elif not resource_namespace and not table_namespace:
                    # Both are None/missing - cluster-scoped resource, match by name only
                    return resource.get("raw_data", {})
                # else: One has namespace, other doesn't - inconsistent, skip to next resource

        except Exception as e:
            logging.error(f"Error getting raw data for row {row}: {e}")
        return {}

    def _handle_edit_resource(self, resource_name, resource_namespace, resource):
        """Override to handle edit for custom resource instances.

        CustomResourceInstancePage sets resource_type=None to disable unified loader,
        but the base class _handle_edit_resource expects a valid resource_type.
        We use self.plural instead.
        """
        try:
            from PyQt6.QtCore import QTimer

            # Find the ClusterView that contains the detail manager
            parent = self.parent()
            cluster_view = None

            # Walk up the parent tree to find ClusterView
            while parent:
                if parent.__class__.__name__ == 'ClusterView' or hasattr(parent, 'detail_manager'):
                    cluster_view = parent
                    break
                parent = parent.parent()

            if cluster_view and hasattr(cluster_view, 'detail_manager'):
                resource_type = self.plural
                raw_data = resource.get("raw_data", {}) if resource else {}
                cluster_view.detail_manager.show_detail(
                    resource_type, resource_name, resource_namespace, raw_data)
                QTimer.singleShot(500, lambda: self._trigger_edit_mode(cluster_view))
                logging.info(f"Opening {self.plural}/{resource_name} in edit mode")
            else:
                QMessageBox.information(
                    self, "Edit Resource",
                    f"Cannot edit {self.plural}/{resource_name}: Detail panel not available"
                )
                logging.warning(f"Detail manager not found for editing {resource_name}")

        except Exception as e:
            logging.error(f"Failed to open {resource_name} for editing: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to open {resource_name} for editing: {str(e)}"
            )

    def _perform_deletion_without_confirmation(self):
        """Delete selected custom resource instances.

        Called by ResourceDeletionManager after confirmation has already been shown.
        Uses the Custom Objects API since resource_type=None for CRD instances.
        """
        if not self.selected_items:
            return

        items_to_delete = list(self.selected_items)
        success_count = 0
        error_list = []
        total = len(items_to_delete)

        progress = QProgressDialog(f"Deleting {total} {self.plural}...", "Cancel", 0, total, self)
        progress.setWindowTitle("Deleting Resources")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()

        try:
            kubernetes_client = get_kubernetes_client()
            if not kubernetes_client:
                QMessageBox.critical(self, "Error", "Kubernetes client not available")
                progress.close()
                return

            for i, (resource_name, namespace) in enumerate(items_to_delete):
                if progress.wasCanceled():
                    break

                progress.setValue(i)
                progress.setLabelText(f"Deleting {resource_name}...")
                QApplication.processEvents()

                try:
                    # Use Custom Objects API for CRD deletion
                    if self.scope == "Namespaced" and namespace:
                        kubernetes_client.custom_objects_api.delete_namespaced_custom_object(
                            group=self.api_group,
                            version=self.api_version,
                            namespace=namespace,
                            plural=self.plural,
                            name=resource_name
                        )
                    else:
                        kubernetes_client.custom_objects_api.delete_cluster_custom_object(
                            group=self.api_group,
                            version=self.api_version,
                            plural=self.plural,
                            name=resource_name
                        )
                    success_count += 1
                    logging.info(f"Deleted {self.plural}/{resource_name}")
                except Exception as e:
                    error_msg = str(e)
                    error_list.append((resource_name, error_msg))
                    logging.error(f"Failed to delete {self.plural}/{resource_name}: {e}")

            progress.setValue(total)

        except Exception as e:
            logging.error(f"Error during batch delete of {self.plural}: {e}")
            error_list.append(("batch", str(e)))
        finally:
            progress.close()

        # Show results
        crd_name = self.crd_spec.get("names", {}).get("kind", self.plural)
        if error_list:
            error_details = "\n".join([f"- {name}: {err}" for name, err in error_list])
            QMessageBox.warning(
                self, "Deletion Results",
                f"Deleted {success_count} of {total} {crd_name}.\n\n"
                f"Failed to delete {len(error_list)} resources:\n{error_details}"
            )
        elif success_count > 0:
            QMessageBox.information(
                self, "Deletion Complete",
                f"Successfully deleted {success_count} {crd_name}."
            )

        # Clear selections and refresh
        self.selected_items.clear()
        self.force_load_data()

    def _perform_global_search(self, search_text):

        try:
            # Mark that we're in search mode
            self._is_searching = True
            self._current_search_query = search_text

            # Use custom CRD search instead of generic linear search
            self._filter_crd_resources(search_text)

        except Exception as e:
            logging.error(f"Error in CRD local search: {e}")
            # Show error and reset
            self._clear_search_and_reload()

    def _filter_crd_resources(self, search_text):

        if not search_text:
            self._display_all_resources()
            return

        filtered_resources = self._search_resources(search_text)
        self._display_filtered_resources(filtered_resources, search_text)

    def _display_all_resources(self):

        self._hide_empty_state()
        self._populate_table_with_resources(self.resources)
        if not self.resources:
            self._show_empty_state()

    def _search_resources(self, search_text):

        search_lower = search_text.lower()
        filtered = []

        for resource in self.resources:
            if self._resource_matches_search(resource, search_lower):
                filtered.append(resource)

        return filtered

    def _resource_matches_search(self, resource, search_lower):

        # Search in basic fields
        if search_lower in resource.get("name", "").lower():
            return True

        # Search in raw_data for comprehensive search
        raw_data = resource.get("raw_data", {})
        metadata = raw_data.get("metadata", {})

        # Search in namespace
        if search_lower in metadata.get("namespace", "").lower():
            return True

        # Search in status fields
        status = raw_data.get("status", {})
        if isinstance(status, dict) and search_lower in str(status).lower():
            return True

        return False

    def _display_filtered_resources(self, filtered_resources, search_text):

        self._hide_empty_state()

        if filtered_resources:
            self._populate_table_with_resources(filtered_resources)
        else:
            self.clear_table()
            self._show_search_empty_state(search_text)

    def _populate_table_with_resources(self, resources):
        """Populate table with resources using batched processing (like NodesPage)"""
        self.clear_table()
        
        if not resources:
            return
        
        total = len(resources)
        self.table.setRowCount(total)
        self.table.setSortingEnabled(False)
        
        # Process resources in batches to keep UI responsive (like NodesPage)
        batch_size = 25  # Process 25 resources at a time
        for i in range(0, total, batch_size):
            batch_end = min(i + batch_size, total)
            
            # Populate this batch
            for row in range(i, batch_end):
                try:
                    self.populate_resource_row(row, resources[row])
                except Exception as e:
                    logging.warning(f"Failed to populate row {row}: {e}")
                    continue
            
            # Process UI events every batch to keep responsive (like NodesPage)
            QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
        
        # Re-enable sorting after all rows are populated
        self.table.setSortingEnabled(True)
        logging.info(f"Successfully populated {total} CRD instance rows")

    def _clear_search_and_reload(self):

        # Mark that we're no longer in search mode
        self._is_searching = False
        self._current_search_query = None

        # Hide any existing empty state overlay first
        self._hide_empty_state()

        # Reload normal CRD resources
        self.force_load_data()

    def _show_search_empty_state(self, search_query):

        search_message = f"No results found for '{search_query}'"
        self._create_empty_overlay(search_message, "search_empty_state_label")

    def _on_namespace_changed(self, namespace):
        """Override to ensure namespace changes are properly handled for CRD instances"""

        if namespace == "Loading namespaces...":
            return  # Ignore the loading placeholder

        old_namespace = getattr(self, 'namespace_filter', 'default')

        # Only proceed if namespace actually changed
        if old_namespace == namespace:
            logging.debug(f"Namespace unchanged ({namespace}), skipping reload")
            return

        logging.info(f"CRD instance page: Namespace changed from '{old_namespace}' to '{namespace}'")

        # Update namespace filter BEFORE loading data
        self.namespace_filter = namespace

        # Reset any search state
        self._is_searching = False
        self._current_search_query = None

        # Reload data with new namespace
        self.force_load_data()

    def force_load_data(self):

        # Show loading indicator
        self.show_loading_indicator("Loading custom resource instances...")

        # Backup existing resources before loading - will restore if load returns empty
        self._backup_resources = list(self.resources) if self.resources else []

        # Load custom resource instances directly
        self._load_custom_resource_instances()

    def _load_custom_resource_instances(self):
        """Load CRD instances directly from the Kubernetes API."""
        try:
            kubernetes_client = get_kubernetes_client()
            if not kubernetes_client:
                self.hide_loading_indicator()
                return

            # Load instances using Kubernetes API
            result = self._fetch_crd_instances(kubernetes_client)
            instances = result.get('items', []) if result else []

            logging.info(f"Found {len(instances)} {self.plural} instances")
            self._process_custom_resource_instances(instances)

        except Exception as e:
            logging.error(
                f"Error loading custom resource instances for {self.crd_name}: {e}")
            # Restore backup on error (like BaseResourcePage pattern)
            if hasattr(self, '_backup_resources') and self._backup_resources:
                logging.warning(
                    f"Restoring {len(self._backup_resources)} backed up {self.plural} items after error")
                self.resources = self._backup_resources
                self._backup_resources = []
                self._hide_empty_state()
                self._populate_table_with_resources(self.resources)
            else:
                # No backup available - show empty state
                self._process_custom_resource_instances([])
        finally:
            self.hide_loading_indicator()

    def _fetch_crd_instances(self, kubernetes_client):

        try:
            current_namespace_filter = getattr(self, 'namespace_filter', None)

            # Check if we need to filter by namespace
            # For namespaced resources with a specific namespace selected, use namespaced API
            use_namespaced_api = (
                self.scope == "Namespaced" and
                current_namespace_filter is not None and
                current_namespace_filter and
                current_namespace_filter != "All Namespaces"
            )

            if use_namespaced_api:
                logging.info(f"Loading namespaced {self.plural} instances in namespace: {current_namespace_filter}")
                return kubernetes_client.custom_objects_api.list_namespaced_custom_object(
                    group=self.api_group,
                    version=self.api_version,
                    namespace=current_namespace_filter,
                    plural=self.plural
                )
            else:
                scope_text = "namespaced (all)" if self.scope == "Namespaced" else "cluster-scoped"
                logging.info(f"Loading {scope_text} {self.plural} instances...")
                return kubernetes_client.custom_objects_api.list_cluster_custom_object(
                    group=self.api_group,
                    version=self.api_version,
                    plural=self.plural
                )
        except Exception as api_error:
            logging.warning(
                f"Failed to load {self.plural} instances: {api_error}")
            return None

    def _process_custom_resource_instances(self, instances):

        formatted_resources = [self._format_resource_instance(
            instance) for instance in instances]

        # Clear backup on successful load (even if empty - that's a legitimate empty state)
        # Backup restoration happens only on ERRORS in _load_custom_resource_instances()
        if hasattr(self, '_backup_resources'):
            self._backup_resources = []

        # Store resources and update display
        self.resources = formatted_resources
        self._hide_empty_state()

        if formatted_resources:
            self._populate_table_with_resources(formatted_resources)
            logging.info(
                f"Loaded {len(formatted_resources)} {self.plural} instances")
        else:
            self.clear_table()
            self._show_empty_state()
            logging.info(
                f"Displaying empty state for {self.plural} - no instances found")

        # Update items count in header
        if hasattr(self, 'items_count') and self.items_count:
            self.items_count.setText(f"{len(formatted_resources)} items")

        # Update status bar if available
        if hasattr(self, '_update_status_bar'):
            self._update_status_bar(
                f"Loaded {len(formatted_resources)} {self.plural}")

    def _format_resource_instance(self, instance):

        metadata = instance.get("metadata", {})
        name = metadata.get("name", "Unknown")
        namespace = metadata.get("namespace", "")  # Extract namespace for selection
        age = self._calculate_age(metadata.get("creationTimestamp", ""))

        return {
            "name": name,
            "namespace": namespace,  # Add namespace for checkbox selection
            "age": age,
            "raw_data": instance
        }

    def _calculate_age(self, creation_timestamp):
        """Calculate human-readable age from a Kubernetes creation timestamp."""
        if not creation_timestamp:
            return "Unknown"

        try:
            created = dateutil.parser.parse(creation_timestamp)
            now = datetime.now(created.tzinfo)
            delta = now - created

            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60

            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
        except Exception as e:
            logging.debug(f"Failed to parse timestamp '{creation_timestamp}': {e}")
            return "Unknown"

    def _show_empty_state(self):

        crd_display_name = self.crd_spec.get(
            "names", {}).get("kind", self.crd_name)
        empty_message = f"No {crd_display_name.lower()} found"
        self._create_empty_overlay(empty_message, "empty_state_label")

    def _create_empty_overlay(self, message, object_name):
        """Create a centered overlay label for empty/search states."""
        try:
            logging.info(f"Creating empty overlay: '{message}'")

            container = self.table.parent() or self
            self.empty_state_overlay = QLabel(message, container)
            self.empty_state_overlay.setObjectName(object_name)

            font = QFont()
            font.setBold(True)
            font.setPointSize(14)
            self.empty_state_overlay.setFont(font)
            self.empty_state_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_state_overlay.setStyleSheet(
                CustomResourceInstancePageStyles.get_empty_state_overlay_style(object_name))

            # Position and show
            self._position_empty_overlay()
            self.empty_state_overlay.show()
            self.empty_state_overlay.raise_()

            logging.info(f"Empty overlay created: '{message}'")

        except Exception as e:
            logging.error(f"Error creating empty overlay: {e}")

    def _position_empty_overlay(self):

        try:
            if hasattr(self, 'empty_state_overlay') and self.empty_state_overlay:
                container = self.empty_state_overlay.parent()
                if container:
                    # Center the label in the container
                    container_rect = container.rect()
                    label_size = self.empty_state_overlay.sizeHint()

                    x = (container_rect.width() - label_size.width()) // 2
                    y = (container_rect.height() - label_size.height()) // 2

                    self.empty_state_overlay.move(x, y)
                    self.empty_state_overlay.resize(label_size)

        except Exception as e:
            logging.error(f"Error positioning empty overlay: {e}")

    def _hide_empty_state(self):

        try:
            if hasattr(self, 'empty_state_overlay') and self.empty_state_overlay:
                self.empty_state_overlay.hide()
                self.empty_state_overlay.deleteLater()
                self.empty_state_overlay = None
                logging.info("Empty state overlay hidden")
        except Exception as e:
            logging.error(f"Error hiding empty state: {e}")

    def resizeEvent(self, event):
        """Re-center the empty state overlay when the widget is resized."""
        super().resizeEvent(event)
        self._position_empty_overlay()
