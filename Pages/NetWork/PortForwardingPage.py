"""
Updated PortForwardingPage with real port forwarding data integration
Replaces the mock implementation with actual port forward management
"""

from PyQt6.QtWidgets import (QHeaderView, QPushButton, QLabel, QVBoxLayout, 
                            QWidget, QHBoxLayout, QMessageBox, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtCore import QSize

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles
from utils.port_forward_manager import get_port_forward_manager, PortForwardConfig
from utils.port_forward_dialog import PortForwardDialog, ActivePortForwardsDialog
from functools import partial
import time
from UI.Icons import resource_path


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

class PortForwardingPage(BaseResourcePage):
    """
    Enhanced Port Forwarding page showing real active port forwards
    with comprehensive management capabilities
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "portforwarding"
        self.port_manager = get_port_forward_manager()
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
        layout = super().setup_ui("Port Forwarding", headers, sortable_columns)
        
        # Apply table style
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        # Configure column widths
        self.configure_columns()
        self._add_management_buttons()
        
    def _add_management_buttons(self):
        """Add port forwarding management buttons"""
        
        # Create Port Forward button
        create_btn = QPushButton("Create Port Forward")
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        create_btn.clicked.connect(self.show_create_port_forward_dialog)
        
        # Stop All button
        stop_all_btn = QPushButton("Stop All")
        stop_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c82333;
            }
        """)
        stop_all_btn.clicked.connect(self.stop_all_port_forwards)
        
        # Find header layout and add buttons
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if isinstance(widget, QPushButton) and widget.text() == "Refresh":
                        # Insert buttons before refresh
                        item.layout().insertWidget(item.layout().count() - 1, create_btn)
                        item.layout().insertWidget(item.layout().count() - 1, stop_all_btn)
                        break
    
    def configure_columns(self):
        """Configure column widths for full screen utilization"""
        if not self.table:
            return
        
        header = self.table.horizontalHeader()
        
        # Column specifications optimized for port forwarding data
        column_specs = [
            (0, 40, "fixed"),        # Checkbox
            (1, 160, "interactive"), # Resource
            (2, 100, "interactive"), # Namespace
            (3, 80, "interactive"),  # Type
            (4, 80, "interactive"),  # Local Port
            (5, 80, "interactive"),  # Target Port
            (6, 80, "interactive"),  # Protocol
            (7, 100, "interactive"), # Uptime
            (8, 100, "stretch"),     # Status - stretch to fill remaining space
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

    def load_data(self, load_more=False):
        """Load port forwarding data - override to use real data"""
        if hasattr(self, 'is_loading') and self.is_loading:
            return
            
        self.is_loading = True
        self.selected_items.clear()
        
        # Get real port forwards from manager
        port_forwards = self.port_manager.get_port_forwards()
        
        # Convert to resource format expected by base class
        self.resources = []
        for config in port_forwards:
            resource = {
                'name': f"{config.resource_name}",
                'resource_name': config.resource_name,
                'namespace': config.namespace,
                'resource_type': config.resource_type,
                'local_port': config.local_port,
                'target_port': config.target_port,
                'protocol': config.protocol,
                'status': config.status,
                'created_at': config.created_at,
                'error_message': config.error_message,
                'key': config.key
            }
            self.resources.append(resource)
        
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
        
        self.is_loading = False

    def populate_resource_row(self, row, resource):
        """Populate a single row with port forward data"""
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
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
        
        # Action button
        action_button = self._create_action_button(row, resource["resource_name"], resource["namespace"])
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, 9, action_container)

    def _create_action_button(self, row, resource_name=None, resource_namespace=None):
        """Create action button with port forward specific actions"""
        from PyQt6.QtWidgets import QToolButton
        
        button = QToolButton()
        icon = resource_path("icons/Moreaction_Button.svg")
        button.setIcon(QIcon(icon))
        button.setIconSize(QSize(16, 16))
        button.setText("")
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setFixedWidth(30)
        button.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Create menu
        menu = QMenu(button)
        menu.setStyleSheet(AppStyles.MENU_STYLE)

        # Get port forward config
        resource = self.resources[row] if row < len(self.resources) else None
        
        actions = []
        
        if resource:
            if resource['status'] == 'active':
                actions.append({"text": "Open in Browser", "icon": "icons/web.png", "dangerous": False})
                actions.append({"text": "Copy URL", "icon": "icons/copy.png", "dangerous": False})
                actions.append({"text": "Restart", "icon": "icons/refresh.png", "dangerous": False})
            elif resource['status'] in ['inactive', 'error']:
                actions.append({"text": "Restart", "icon": "icons/refresh.png", "dangerous": False})
            
            actions.append({"text": "Stop", "icon": "icons/stop.png", "dangerous": True})
            actions.append({"text": "Delete", "icon": "icons/delete.png", "dangerous": True})

        # Add actions to menu
        for action_info in actions:
            action = menu.addAction(action_info["text"])
            if "icon" in action_info:
                action.setIcon(QIcon(action_info["icon"]))
            if action_info.get("dangerous", False):
                action.setProperty("dangerous", True)
            action.triggered.connect(
                partial(self._handle_action, action_info["text"], row)
            )

        button.setMenu(menu)
        return button

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
            import webbrowser
            url = f"http://localhost:{resource['local_port']}"
            webbrowser.open(url)
        except Exception as e:
            QMessageBox.warning(self, "Browser Error", f"Could not open browser: {str(e)}")

    def _copy_url_to_clipboard(self, resource):
        """Copy port forward URL to clipboard"""
        try:
            from PyQt6.QtWidgets import QApplication
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

    def show_create_port_forward_dialog(self):
        """Show dialog to create new port forward"""
        # This could be enhanced to show a resource selector
        QMessageBox.information(
            self, "Create Port Forward",
            "To create port forwards, navigate to the Pods or Services page "
            "and use the 'Port Forward' action on specific resources."
        )

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
        self.refresh_port_forwards()

    def on_port_forward_stopped(self, key: str):
        """Handle port forward stopped"""
        self.refresh_port_forwards()

    def on_port_forward_error(self, key: str, error_message: str):
        """Handle port forward error"""
        self.refresh_port_forwards()

    def on_port_forwards_updated(self, configs):
        """Handle port forwards updated"""
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
            # Find and stop selected port forwards
            for selected_name, _ in self.selected_items:
                for resource in self.resources:
                    if resource['name'] == selected_name:
                        self.port_manager.stop_port_forward(resource['key'])
                        break
            
            self.selected_items.clear()
            self.refresh_port_forwards()

    def cleanup_on_destroy(self):
        """Cleanup when page is destroyed"""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()