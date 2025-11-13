"""
Dynamic CustomResource Instance Page - Shows instances of a specific CRD
Similar to how OpenLens displays custom resource instances when clicking on a CRD from sidebar
"""

import logging
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppStyles, AppColors


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
        
        # IMPORTANT: Disable unified loader search for CRD instances
        self.resource_type = None
        
        self.setup_page_ui()
    
    def _extract_crd_config(self, crd_spec):
        """Extract and store CRD configuration from spec"""
        self.api_group = crd_spec.get("group", "")
        versions = crd_spec.get("versions", [])
        self.api_version = versions[0].get("name", "") if versions else ""
        self.plural = crd_spec.get("names", {}).get("plural", "")
        self.scope = crd_spec.get("scope", "Namespaced")
        
    def _get_column_config(self):
        """Get column configuration based on scope"""
        if self.scope == "Cluster":
            return {
                'headers': ["", "Name", "Status", "Age", ""],
                'sortable_columns': {1, 2, 3},
                'column_specs': [
                    (0, 40, "fixed"),        # Checkbox
                    (1, 200, "interactive"), # Name
                    (2, 120, "interactive"), # Status
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
                    (1, 180, "interactive"), # Name
                    (2, 120, "interactive"), # Namespace
                    (3, 120, "interactive"), # Status
                    (4, 100, "stretch"),     # Age
                    (5, 40, "fixed")         # Actions
                ]
            }

    def setup_page_ui(self):
        """Set up the main UI elements for the Custom Resource Instance page"""
        config = self._get_column_config()
        
        # Set up the base UI components with dynamic title
        crd_display_name = self.crd_spec.get("names", {}).get("kind", self.crd_name)
        page_title = f"{crd_display_name} Instances"
        super().setup_ui(page_title, config['headers'], config['sortable_columns'])
        
        # Apply styling and configure columns
        self._apply_table_styling()
        self.configure_columns()
    
    def _apply_table_styling(self):
        """Apply consistent table styling"""
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
    def configure_columns(self):
        """Configure column widths for custom resource instances"""
        if not self.table:
            return
        
        config = self._get_column_config()
        self._apply_column_configuration(config['column_specs'])
        
        # Ensure full width utilization after configuration
        QTimer.singleShot(100, self._ensure_full_width_utilization)
    
    def _apply_column_configuration(self, column_specs):
        """Apply column configuration from specs"""
        header = self.table.horizontalHeader()
        
        for col_index, default_width, resize_type in column_specs:
            if col_index < self.table.columnCount():
                resize_mode = getattr(QHeaderView.ResizeMode, resize_type.title())
                if resize_type == "stretch":
                    resize_mode = QHeaderView.ResizeMode.Stretch
                
                header.setSectionResizeMode(col_index, resize_mode)
                self.table.setColumnWidth(col_index, default_width)
    
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with custom resource instance data
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
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
                # Age column
                try:
                    num = int(value.replace('d', '').replace('h', '').replace('m', '').replace('s', ''))
                except (ValueError, AttributeError):
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col == 0:  # Name column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
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
        action_button = self._create_action_button(row, resource["name"], namespace if self.scope == "Namespaced" else "")
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(columns) + 1, action_container)
    
    def handle_row_click(self, row, column):
        if column != self.table.columnCount() - 1:  # Skip action column
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
                    # Use the plural name as resource type for detail view
                    parent.detail_manager.show_detail(self.plural, resource_name, namespace)
    
    def _perform_global_search(self, search_text):
        """Override to use local search only for CRD instances"""
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
        """Filter CRD resources by searching through name, namespace, and status"""
        if not search_text:
            self._display_all_resources()
            return
        
        filtered_resources = self._search_resources(search_text)
        self._display_filtered_resources(filtered_resources, search_text)
    
    def _display_all_resources(self):
        """Display all resources when clearing search"""
        self._hide_empty_state()
        self._populate_table_with_resources(self.resources)
        if not self.resources:
            self._show_empty_state()
    
    def _search_resources(self, search_text):
        """Search through resources and return filtered list"""
        search_lower = search_text.lower()
        filtered = []
        
        for resource in self.resources:
            if self._resource_matches_search(resource, search_lower):
                filtered.append(resource)
        
        return filtered
    
    def _resource_matches_search(self, resource, search_lower):
        """Check if a resource matches the search criteria"""
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
        """Display filtered resources or show no results message"""
        self._hide_empty_state()
        
        if filtered_resources:
            self._populate_table_with_resources(filtered_resources)
        else:
            self.clear_table()
            self._show_search_empty_state(search_text)
    
    def _populate_table_with_resources(self, resources):
        """Populate table with the given resources"""
        self.clear_table()
        for row, resource in enumerate(resources):
            self.table.insertRow(row)
            self.populate_resource_row(row, resource)

    def _clear_search_and_reload(self):
        """Override to properly clear search state and reload CRD data"""
        # Mark that we're no longer in search mode
        self._is_searching = False
        self._current_search_query = None
        
        # Hide any existing empty state overlay first
        self._hide_empty_state()
        
        # Reload normal CRD resources  
        self.force_load_data()

    def _show_search_empty_state(self, search_query):
        """Show empty state message for search with no results"""
        search_message = f"No results found for '{search_query}'"
        self._create_empty_overlay(search_message, "search_empty_state_label")

    def force_load_data(self):
        """Override to load custom resource instances using Kubernetes API"""
        # Show loading indicator
        self.show_loading_indicator("Loading custom resource instances...")
        
        # Load custom resource instances directly
        self._load_custom_resource_instances()
    
    def _load_custom_resource_instances(self):
        """Load custom resource instances for this CRD"""
        try:
            from Utils.kubernetes_client import get_kubernetes_client
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
            logging.error(f"Error loading custom resource instances for {self.crd_name}: {e}")
            self._process_custom_resource_instances([])
        finally:
            self.hide_loading_indicator()
    
    def _fetch_crd_instances(self, kubernetes_client):
        """Fetch CRD instances from Kubernetes API"""
        try:
            scope_text = "namespaced" if self.scope == "Namespaced" else "cluster-scoped"
            logging.info(f"Loading {scope_text} {self.plural} instances...")
            
            # Both namespaced and cluster-scoped use the same API call
            return kubernetes_client.custom_objects_api.list_cluster_custom_object(
                group=self.api_group,
                version=self.api_version,
                plural=self.plural
            )
        except Exception as api_error:
            logging.warning(f"Failed to load {self.plural} instances: {api_error}")
            return None
    
    def _process_custom_resource_instances(self, instances):
        """Process and display custom resource instances"""
        formatted_resources = [self._format_resource_instance(instance) for instance in instances]
        
        # Store resources and update display
        self.resources = formatted_resources
        self._hide_empty_state()
        
        if formatted_resources:
            self._populate_table_with_resources(formatted_resources)
            logging.info(f"Loaded {len(formatted_resources)} {self.plural} instances")
        else:
            self.clear_table()
            self._show_empty_state()
            logging.info(f"Displaying empty state for {self.plural} - no instances found")
        
        # Update status bar if available
        if hasattr(self, '_update_status_bar'):
            self._update_status_bar(f"Loaded {len(formatted_resources)} {self.plural}")
    
    def _format_resource_instance(self, instance):
        """Format a single resource instance for display"""
        metadata = instance.get("metadata", {})
        name = metadata.get("name", "Unknown")
        age = self._calculate_age(metadata.get("creationTimestamp", ""))
        
        return {
            "name": name,
            "age": age,
            "raw_data": instance
        }
    
    def _calculate_age(self, creation_timestamp):
        """Calculate age from creation timestamp"""
        if not creation_timestamp:
            return "Unknown"
        
        try:
            from datetime import datetime
            import dateutil.parser
            
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
        except Exception:
            return "Unknown"
    
    def _show_empty_state(self):
        """Show empty state message in center of page like other pages"""
        crd_display_name = self.crd_spec.get("names", {}).get("kind", self.crd_name)
        empty_message = f"No {crd_display_name.lower()} found"
        self._create_empty_overlay(empty_message, "empty_state_label")
    
    def _create_empty_overlay(self, message, object_name):
        """Create and display an empty state overlay with the given message"""
        try:
            logging.info(f"Creating empty overlay: '{message}'")
            
            from PyQt6.QtWidgets import QLabel
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QFont
            
            # Find container and create overlay
            container = self.table.parent() or self
            self.empty_state_overlay = QLabel(message, container)
            self.empty_state_overlay.setObjectName(object_name)
            
            # Apply consistent styling
            font = QFont()
            font.setBold(True)
            font.setPointSize(14)
            self.empty_state_overlay.setFont(font)
            self.empty_state_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_state_overlay.setStyleSheet(f"""
                QLabel#{object_name} {{
                    color: white;
                    background: transparent;
                    border: none;
                }}
            """)
            
            # Position and show
            self._position_empty_overlay()
            self.empty_state_overlay.show()
            self.empty_state_overlay.raise_()
            
            logging.info(f"Empty overlay created: '{message}'")
            
        except Exception as e:
            logging.error(f"Error creating empty overlay: {e}")
    
    def _position_empty_overlay(self):
        """Position the empty state overlay in center of page"""
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
        """Hide empty state overlay"""
        try:
            if hasattr(self, 'empty_state_overlay') and self.empty_state_overlay:
                self.empty_state_overlay.hide()
                self.empty_state_overlay.deleteLater()
                self.empty_state_overlay = None
                logging.info("Empty state overlay hidden")
        except Exception as e:
            logging.error(f"Error hiding empty state: {e}")