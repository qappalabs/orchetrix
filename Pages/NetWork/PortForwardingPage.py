"""
Updated PortForwardingPage with real port forwarding data integration
Replaces the mock implementation with actual port forward management
"""

from PyQt6.QtWidgets import (QHeaderView, QPushButton, QMessageBox, QApplication)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QIcon

from Base_Components.base_components import SortableTableWidgetItem, StatusLabel
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors
from Utils.port_forward_manager import get_port_forward_manager, PortForwardConfig
from Styles.PortForwardingPageStyles import STOP_ALL_BUTTON_STYLE
from functools import partial
import time
import logging
import webbrowser
from UI.Icons import Icons
from UI.ThemeManager import get_theme_manager



class PortForwardingPage(BaseResourcePage):
    """
    Enhanced Port Forwarding page showing real active port forwards
    with comprehensive management capabilities
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "portforwarding"
        self.port_manager = get_port_forward_manager()
        self._is_deleting = False  # Flag to prevent refresh during deletion
        self.setup_page_ui()

        # Connect to port forward manager signals for real-time updates
        self.port_manager.port_forward_started.connect(self.on_port_forward_started)
        self.port_manager.port_forward_stopped.connect(self.on_port_forward_stopped)
        self.port_manager.port_forward_error.connect(self.on_port_forward_error)
        self.port_manager.port_forwards_updated.connect(self.on_port_forwards_updated)

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_port_forwards)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

    def setup_page_ui(self):
        """Set up the main UI elements for the Port Forwarding page"""
        headers = ["", "Resource", "Namespace", "Type", "Local Port", "Target Port", "Protocol", "Uptime", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8}

        # Set up the base UI components
        super().setup_ui("Port Forwarding", headers, sortable_columns)

        # Configure column widths
        self.configure_columns()
        self._add_management_buttons()

    def _add_management_buttons(self):
        """Add port forwarding management buttons"""

        # Stop All button
        self.stop_all_btn = QPushButton("Stop All")
        self.stop_all_btn.setStyleSheet(STOP_ALL_BUTTON_STYLE)
        self.stop_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_all_btn.clicked.connect(self.stop_all_port_forwards)

        # Find header layout and add buttons
        button_added = False
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if isinstance(widget, QPushButton) and widget.text() == "Refresh":
                        # Insert stop all button before refresh
                        item.layout().insertWidget(item.layout().count() - 1, self.stop_all_btn)
                        button_added = True
                        break
                if button_added:
                    break

        # Fallback: if Refresh button wasn't found, add to the first available layout
        if not button_added:
            logging.warning("Refresh button not found in layout, adding Stop All button to fallback location")
            for i in range(self.layout().count()):
                item = self.layout().itemAt(i)
                if item.layout():
                    item.layout().addWidget(self.stop_all_btn)
                    button_added = True
                    break

            # Last resort: add directly to main layout if no sub-layout found
            if not button_added:
                logging.warning("No suitable layout found, adding Stop All button to main layout")
                self.layout().addWidget(self.stop_all_btn)

    def _update_stop_all_button(self):
        """Update the Stop All button state and cursor based on available port forwards"""
        if hasattr(self, 'stop_all_btn'):
            has_forwards = len(self.resources) > 0
            self.stop_all_btn.setEnabled(has_forwards)
            if has_forwards:
                self.stop_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.stop_all_btn.setCursor(Qt.CursorShape.ArrowCursor)

    def configure_columns(self):
        """Configure column widths for full screen utilization"""
        if not self.table:
            return

        header = self.table.horizontalHeader()

        # Column specifications optimized for port forwarding data
        column_specs = [
            (0, 40, "fixed"),        # Checkbox
            (1, 160, "stretch"),     # Resource - stretch to fill remaining space
            (2, 100, "interactive"), # Namespace
            (3, 80, "interactive"),  # Type
            (4, 80, "interactive"),  # Local Port
            (5, 80, "interactive"),  # Target Port
            (6, 80, "interactive"),  # Protocol
            (7, 100, "interactive"), # Uptime
            (8, 100, "interactive"), # Status
            (9, 40, "fixed")         # Actions
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
        """Override to provide explicit widths for columns to let Resource stretch and avoid clipping."""
        explicit_mins = {
            1: 120,  # Resource
            2: 100,  # Namespace
            3: 80,   # Type
            4: 80,   # Local Port
            5: 80,   # Target Port
            6: 80,   # Protocol
            7: 100,  # Uptime
            8: 100,  # Status
            9: 40,   # Actions
        }
        if min_col_widths:
            explicit_mins.update(min_col_widths)
        explicit_maxes = {
            2: 150,  # Namespace
            3: 120,  # Type
            4: 100,  # Local Port
            5: 100,  # Target Port
            6: 100,  # Protocol
            7: 120,  # Uptime
            8: 120,  # Status
        }
        if max_col_widths:
            explicit_maxes.update(max_col_widths)
        super()._auto_resize_columns(max_col_widths=explicit_maxes, min_col_widths=explicit_mins)

    def force_load_data(self):
        """Override to prevent calling unified resource loader for port forwarding"""
        self.load_data()

    def _start_loading_thread(self, continue_token=None):
        """Override to prevent starting resource loading thread for port forwarding"""
        self.load_data()

    def load_data(self, load_more=False):
        """Load port forwarding data - override to use real data"""
        if hasattr(self, 'is_loading') and self.is_loading:
            return

        self.is_loading = True
        
        # Preserve current selections to restore after refresh
        preserved_selections = set(self.selected_items)

        # Get real port forwards from manager
        port_forwards = self.port_manager.get_port_forwards()

        # Convert to resource format expected by base class
        self.resources = []
        for config in port_forwards:
            try:
                resource = {
                    'name': getattr(config, 'resource_name', 'Unknown'),
                    'resource_name': getattr(config, 'resource_name', 'Unknown'),
                    'namespace': getattr(config, 'namespace', 'default'),
                    'resource_type': getattr(config, 'resource_type', 'service'),
                    'local_port': getattr(config, 'local_port', 0),
                    'target_port': getattr(config, 'target_port', 0),
                    'protocol': getattr(config, 'protocol', 'TCP'),
                    'status': getattr(config, 'status', 'unknown'),
                    'created_at': getattr(config, 'created_at', 0),
                    'error_message': getattr(config, 'error_message', ''),
                    'key': getattr(config, 'key', f"{config.resource_name}:{config.local_port}" if hasattr(config, 'resource_name') and hasattr(config, 'local_port') else 'unknown'),
                    'age': 'N/A'  # Port forwards don't have age like Kubernetes resources
                }
                self.resources.append(resource)
            except Exception as e:
                logging.error(f"Error processing port forward config: {e}")
                continue

        # Apply search filter if any
        search_text = self.search_bar.text().lower() if self.search_bar and self.search_bar.text() else ""
        if search_text:
            filtered_resources = []
            for resource in self.resources:
                if (search_text in resource['resource_name'].lower() or
                    search_text in resource['namespace'].lower() or
                    search_text in resource['resource_type'].lower()):
                    filtered_resources.append(resource)
            self.resources = filtered_resources

        # Update table
        self._display_resources(self.resources)
        self.items_count.setText(f"{len(self.resources)} items")

        # Update stop all button state
        self._update_stop_all_button()

        # Restore selections for items that still exist
        self._restore_selections(preserved_selections)

        self.is_loading = False

    def _restore_selections(self, preserved_selections):
        """Restore checkbox selections for items that still exist after refresh."""
        if not preserved_selections:
            return

        # Get names of current resources
        current_resource_names = {r['name'] for r in self.resources}

        # Restore selections for items that still exist
        for name, namespace in preserved_selections:
            if name in current_resource_names:
                self.selected_items.add((name, namespace))

        # Update checkbox states in the table
        for row in range(self.table.rowCount()):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                checkbox = checkbox_container.findChild(type(checkbox_container.layout().itemAt(0).widget()))
                if checkbox and row < len(self.resources):
                    resource_name = self.resources[row]['name']
                    # Check if this resource is in selected_items
                    is_selected = any(name == resource_name for name, _ in self.selected_items)
                    checkbox.setChecked(is_selected)

    def populate_resource_row(self, row, resource):
        """Populate a single row with port forward data"""
        self.table.setRowHeight(row, 42)

        # Create checkbox for row selection - styling handled by BaseResourcePage
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)

        # Calculate uptime
        uptime_text = "Unknown"
        if resource.get('created_at') and resource.get('status') == 'active':
            uptime_seconds = time.time() - resource['created_at']
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            uptime_text = f"{hours}h {minutes}m"
        elif resource.get('status') != 'active':
            uptime_text = "N/A"

        columns = [
            resource["resource_name"],
            resource["namespace"],
            resource["resource_type"].upper(),
            str(resource["local_port"]),
            str(resource["target_port"]),
            resource["protocol"]
            # Status is now handled separately using StatusLabel widget
        ]

        # Add columns to table - similar to ServicesPage style
        for col, value in enumerate(columns):
            cell_col = col + 1

            # Create sortable items for numeric columns
            if col in [3, 4]:  # Local port, target port
                try:
                    num_value = int(value)
                    item = SortableTableWidgetItem(value, num_value)
                except ValueError:
                    item = SortableTableWidgetItem(value)
            else:
                item = SortableTableWidgetItem(value)

            # Set alignment
            if col in [2, 3, 4, 5]:  # Type, ports, protocol
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Set default text color for all non-status columns
            item.setForeground(QColor(AppColors.TEXT_TABLE))

            # Add the item to the table
            self.table.setItem(row, cell_col, item)

        # Uptime column
        uptime_item = SortableTableWidgetItem(uptime_text)
        uptime_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        uptime_item.setFlags(uptime_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        uptime_item.setForeground(QColor(AppColors.TEXT_TABLE))
        self.table.setItem(row, 7, uptime_item)

        # Status column with color coding
        status_col = 8
        status_text = resource["status"].title()

        # Map status to colors
        status_colors = {
            'Active': AppColors.STATUS_ACTIVE,
            'Inactive': AppColors.STATUS_DISCONNECTED,
            'Starting': AppColors.STATUS_WARNING,
            'Error': AppColors.STATUS_ERROR
        }
        color = status_colors.get(status_text, AppColors.TEXT_TABLE)

        # Create status widget with proper color
        status_widget = StatusLabel(status_text, color)
        # Connect click event to select the row
        status_widget.clicked.connect(lambda: self.table.selectRow(row))
        self.table.setCellWidget(row, status_col, status_widget)

        # Action button - styling handled by BaseResourcePage
        action_button = self._create_action_button(row, resource["resource_name"], resource["namespace"])
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, 9, action_container)

    def _create_action_menu(self, button, row):
        """
        Create and attach menu to action button with port forward specific actions.
        Overrides base class to add port forwarding functionality.
        """
        # Call parent to get base menu functionality (Edit, Delete)
        menu = super()._create_action_menu(button, row)
        
        # Get port forward config
        resource = self.resources[row] if row < len(self.resources) else None

        if resource:
            # Clear existing actions to rebuild with port forward specific actions
            menu.clear()
            theme_name = get_theme_manager().get_current_theme_name() or "Dark"

            # Add port forward specific actions based on status
            if resource['status'] == 'active':
                # Active port forward actions
                open_browser_action = menu.addAction("Open in Browser")
                try:
                    open_browser_action.setIcon(Icons.get_theme_icon_by_id("web", theme_name))
                except Exception:
                    pass
                open_browser_action.triggered.connect(
                    partial(self._handle_action, "Open in Browser", row)
                )
                
                copy_url_action = menu.addAction("Copy URL")
                try:
                    copy_url_action.setIcon(Icons.get_theme_icon_by_id("copy", theme_name))
                except Exception:
                    pass
                copy_url_action.triggered.connect(
                    partial(self._handle_action, "Copy URL", row)
                )
                
                restart_action = menu.addAction("Restart")
                try:
                    restart_action.setIcon(Icons.get_theme_icon_by_id("refresh", theme_name))
                except Exception:
                    pass
                restart_action.triggered.connect(
                    partial(self._handle_action, "Restart", row)
                )
            elif resource['status'] in ['inactive', 'error']:
                # Inactive/error port forward actions
                restart_action = menu.addAction("Restart")
                try:
                    restart_action.setIcon(Icons.get_theme_icon_by_id("refresh", theme_name))
                except Exception:
                    pass
                restart_action.triggered.connect(
                    partial(self._handle_action, "Restart", row)
                )

            # Add common actions
            stop_action = menu.addAction("Stop")
            try:
                stop_action.setIcon(Icons.get_theme_icon_by_id("stop", theme_name))
            except Exception:
                pass
            stop_action.setProperty("dangerous", True)
            stop_action.triggered.connect(
                partial(self._handle_action, "Stop", row)
            )
            
            delete_action = menu.addAction("Delete")
            try:
                delete_action.setIcon(Icons.get_theme_icon_by_id("delete", theme_name))
            except Exception:
                pass
            delete_action.setProperty("dangerous", True)
            delete_action.triggered.connect(
                partial(self._handle_action, "Delete", row)
            )

        return menu

    def _handle_action(self, action, row):
        """Handle action button clicks for port forwards"""
        if row >= len(self.resources):
            return

        resource = self.resources[row]
        port_forward_key = resource.get("key", "")

        if action == "Open in Browser":
            self._open_in_browser(resource)
        elif action == "Copy URL":
            self._copy_url_to_clipboard(resource)
        elif action == "Restart":
            self._restart_port_forward(resource)
        elif action == "Stop":
            self._stop_port_forward(port_forward_key)
        elif action == "Delete":
            self._delete_port_forward(port_forward_key)

    def _open_in_browser(self, resource):
        """Open port forward URL in browser"""
        try:
            url = f"http://localhost:{resource['local_port']}"
            webbrowser.open(url)
        except Exception as e:
            QMessageBox.warning(self, "Browser Error", f"Could not open browser: {str(e)}")

    def _copy_url_to_clipboard(self, resource):
        """Copy port forward URL to clipboard"""
        try:
            url = f"http://localhost:{resource['local_port']}"
            clipboard = QApplication.clipboard()
            clipboard.setText(url)

            # Show confirmation
            if hasattr(self, 'show_transient_message'):
                self.show_transient_message(f"URL copied to clipboard: {url}")
            else:
                QMessageBox.information(self, "Copied", f"URL copied to clipboard:\n{url}")
        except Exception as e:
            QMessageBox.warning(self, "Copy Error", f"Could not copy to clipboard: {str(e)}")

    def _restart_port_forward(self, resource):
        """Restart a port forward"""
        try:
            # Stop existing forward
            self.port_manager.stop_port_forward(resource['key'])

            # Wait a moment
            QTimer.singleShot(1000, lambda: self._recreate_port_forward(resource))

        except Exception as e:
            QMessageBox.critical(self, "Restart Error", f"Failed to restart port forward: {str(e)}")

    def _recreate_port_forward(self, resource):
        """Recreate port forward after restart"""
        try:
            self.port_manager.start_port_forward(
                resource_name=resource['resource_name'],
                resource_type=resource['resource_type'],
                namespace=resource['namespace'],
                target_port=resource['target_port'],
                local_port=resource['local_port'],
                protocol=resource['protocol']
            )
        except Exception as e:
            QMessageBox.critical(self, "Restart Error", f"Failed to recreate port forward: {str(e)}")

    def _stop_port_forward(self, key):
        """Stop a specific port forward"""
        try:
            self.port_manager.stop_port_forward(key)
        except Exception as e:
            QMessageBox.critical(self, "Stop Error", f"Failed to stop port forward: {str(e)}")

    def _delete_port_forward(self, key):
        """Delete a port forward with confirmation"""
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete this port forward?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._stop_port_forward(key)


    def stop_all_port_forwards(self):
        """Stop all active port forwards"""
        if not self.resources:
            QMessageBox.information(self, "No Port Forwards", "No active port forwards to stop.")
            return

        reply = QMessageBox.question(
            self, "Confirm Stop All",
            f"Are you sure you want to stop all {len(self.resources)} port forwards?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.port_manager.stop_all_port_forwards()

    def refresh_port_forwards(self):
        """Refresh port forwards data"""
        self.load_data()

    # Signal handlers for real-time updates
    def on_port_forward_started(self, config: PortForwardConfig):
        """Handle port forward started"""
        if not self._is_deleting:
            self.refresh_port_forwards()

    def on_port_forward_stopped(self, key: str):
        """Handle port forward stopped"""
        if not self._is_deleting:
            self.refresh_port_forwards()

    def on_port_forward_error(self, key: str, error_message: str):
        """Handle port forward error"""
        if not self._is_deleting:
            self.refresh_port_forwards()

    def on_port_forwards_updated(self, configs):
        """Handle port forwards updated"""
        if not self._is_deleting:
            self.refresh_port_forwards()

    def handle_row_click(self, row, column):
        """Handle row selection"""
        if column != self.table.columnCount() - 1:
            self.table.selectRow(row)

    def delete_selected_resources(self):
        """Override to handle port forward deletion"""
        if not self.selected_items:
            QMessageBox.information(
                self, "No Selection",
                "No port forwards selected for deletion."
            )
            return

        count = len(self.selected_items)
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to stop {count} selected port forwards?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._perform_deletion_without_confirmation()

    def _perform_deletion_without_confirmation(self):
        """Perform port forward deletion without confirmation dialog.
        
        Called by ResourceDeletionManager after confirmation has already been shown.
        """
        if not self.selected_items:
            return

        # Prevent signal-triggered refreshes during deletion
        self._is_deleting = True

        try:
            # Copy to list to avoid 'Set changed size during iteration' error
            items_to_delete = list(self.selected_items)

            # Find and stop selected port forwards
            for selected_name, _ in items_to_delete:
                for resource in self.resources:
                    if resource['name'] == selected_name:
                        self.port_manager.stop_port_forward(resource['key'])
                        break

            self.selected_items.clear()
        finally:
            self._is_deleting = False
            # Refresh once after all deletions are complete
            self.refresh_port_forwards()

    def cleanup(self):
        """Cleanup when page is destroyed"""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()

        super().cleanup()
