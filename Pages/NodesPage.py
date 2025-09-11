"""
NodesPage - Production Kubernetes Nodes Management Interface

A clean, efficient implementation for managing Kubernetes cluster nodes.
Features:
- Real-time node metrics (CPU, Memory, Disk usage)
- Colored status indicators and usage percentages
- Interactive detail page integration
- Node management actions (drain, cordon)
- Comprehensive search and filtering
"""

import logging
from datetime import datetime, timezone

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QFrame, QTableWidgetItem, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush

from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles
from UI.Icons import Icons, resource_path
from Utils.data_formatters import format_age


class NodesPage(BaseResourcePage):
    """Production-ready Nodes page for Kubernetes cluster management"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "nodes"
        self.namespace_filter = "All Namespaces"  # Nodes are cluster-scoped
        self.show_namespace_dropdown = False
        
        self.metrics_widget = None
        
        self._setup_ui()
        self._setup_table_styling()
        self._setup_table_interactions()
        
        logging.info("NodesPage: Initialized successfully")
    
    def _setup_ui(self):
        """Initialize the main UI components"""
        try:
            headers = self.get_headers()
            # Enable sorting for all columns except Name (column 0) and Actions (column 8)
            sortable_columns = {1, 2, 3, 4, 5, 6, 7}  # CPU, Memory, Disk, Roles, Version, Age, Status
            super().setup_ui("Nodes", headers, sortable_columns)
            
            # Disable node-specific functionality not applicable for nodes
            self.show_select_all = False
            self.show_delete_button = False
            
            # Hide elements with multiple delays to ensure they exist
            QTimer.singleShot(100, self._hide_node_specific_elements)
            QTimer.singleShot(300, self._hide_node_specific_elements)  # Second attempt
            QTimer.singleShot(500, self._hide_node_specific_elements)  # Third attempt
            
            # Create metrics summary
            self._create_metrics_summary()
            
            # Hide namespace dropdown (nodes are cluster-scoped)
            if hasattr(self, 'namespace_combo') and self.namespace_combo:
                self.namespace_combo.hide()
                
        except Exception as e:
            logging.error(f"NodesPage: Failed to setup UI: {e}")
    
    def _hide_node_specific_elements(self):
        """Hide UI elements not applicable for nodes"""
        try:
            # Find and hide delete button more thoroughly
            self._find_and_hide_delete_elements()
            
            # Hide select-all checkbox  
            if hasattr(self, 'select_all_checkbox') and self.select_all_checkbox:
                self.select_all_checkbox.hide()
                self.select_all_checkbox.setVisible(False)
                
            logging.debug("NodesPage: Hidden node-specific UI elements")
        except Exception as e:
            logging.error(f"NodesPage: Error hiding UI elements: {e}")
    
    def _find_and_hide_delete_elements(self):
        """Comprehensively find and hide all delete-related elements"""
        try:
            # Hide direct delete button reference
            if hasattr(self, 'delete_button') and self.delete_button:
                self.delete_button.hide()
                self.delete_button.setVisible(False)
                self.delete_button.setEnabled(False)
                logging.info("NodesPage: Hidden direct delete button")
            
            # Search for delete buttons in the widget hierarchy
            def hide_delete_widgets(widget):
                try:
                    if hasattr(widget, 'children'):
                        for child in widget.children():
                            # Check button text
                            if hasattr(child, 'text') and child.text():
                                text = child.text().lower()
                                if any(keyword in text for keyword in ['delete', 'remove', 'selected']):
                                    child.hide()
                                    child.setVisible(False)
                                    child.setEnabled(False)
                                    logging.info(f"NodesPage: Hidden button with text: {child.text()}")
                            
                            # Check tooltip
                            if hasattr(child, 'toolTip') and child.toolTip():
                                tooltip = child.toolTip().lower()
                                if any(keyword in tooltip for keyword in ['delete', 'remove', 'selected']):
                                    child.hide()
                                    child.setVisible(False)
                                    child.setEnabled(False)
                                    logging.info(f"NodesPage: Hidden button with tooltip: {child.toolTip()}")
                            
                            # Check object name
                            if hasattr(child, 'objectName') and child.objectName():
                                name = child.objectName().lower()
                                if any(keyword in name for keyword in ['delete', 'remove']):
                                    child.hide()
                                    child.setVisible(False)
                                    child.setEnabled(False)
                                    logging.info(f"NodesPage: Hidden button with name: {child.objectName()}")
                            
                            # Recursively check children
                            hide_delete_widgets(child)
                except Exception:
                    pass
            
            # Apply to the entire page
            hide_delete_widgets(self)
            
        except Exception as e:
            logging.error(f"NodesPage: Error finding and hiding delete elements: {e}")
    
    def _setup_table_styling(self):
        """Setup custom table styling to support colored cells"""
        QTimer.singleShot(200, self._apply_table_styles)
    
    def _apply_table_styles(self):
        """Apply custom styles that allow individual cell colors"""
        try:
            if hasattr(self, 'table') and self.table:
                custom_style = f"""
                    QTableWidget {{
                        background-color: {AppColors.CARD_BG};
                        border: none;
                        gridline-color: transparent;
                        outline: none;
                        selection-background-color: rgba(53, 132, 228, 0.15);
                        alternate-background-color: transparent;
                    }}
                    QTableWidget::item {{
                        border: none;
                        padding: 8px;
                    }}
                """
                self.table.setStyleSheet(custom_style)
                logging.info("NodesPage: Applied custom table styling")
        except Exception as e:
            logging.error(f"NodesPage: Failed to apply table styling: {e}")
    
    def _setup_table_interactions(self):
        """Setup table click handlers for node interaction"""
        QTimer.singleShot(300, self._connect_table_events)
    
    def _connect_table_events(self):
        """Connect table interaction events"""
        try:
            if hasattr(self, 'table') and self.table:
                self.table.itemDoubleClicked.connect(self._on_row_double_click)
                self.table.itemClicked.connect(self._on_row_single_click)
                logging.info("NodesPage: Connected table interaction events")
        except Exception as e:
            logging.error(f"NodesPage: Failed to connect table events: {e}")
    
    def _on_row_double_click(self, item):
        """Handle double-click to open node detail page"""
        try:
            if item and item.row() >= 0:
                node_name = self._get_node_name_from_row(item.row())
                if node_name:
                    logging.info(f"NodesPage: Opening detail page for node '{node_name}'")
                    self._open_node_details(node_name)
        except Exception as e:
            logging.error(f"NodesPage: Error handling row double-click: {e}")
    
    def _on_row_single_click(self, item):
        """Handle single-click for selection feedback"""
        try:
            if item and item.row() >= 0:
                node_name = self._get_node_name_from_row(item.row())
                if node_name:
                    logging.debug(f"NodesPage: Selected node '{node_name}'")
        except Exception as e:
            logging.error(f"NodesPage: Error handling row single-click: {e}")
    
    def _get_node_name_from_row(self, row):
        """Get node name from table row"""
        try:
            name_item = self.table.item(row, 0)  # Name is in column 0
            return name_item.text() if name_item else None
        except Exception:
            return None
    
    def _create_metrics_summary(self):
        """Create metrics summary widget showing cluster node stats"""
        QTimer.singleShot(100, self._create_metrics_widget)
    
    def _create_metrics_widget(self):
        """Create the actual metrics widget"""
        try:
            self.metrics_widget = QFrame()
            self.metrics_widget.setStyleSheet(f"""
                QFrame {{
                    background-color: {AppColors.BG_MEDIUM};
                    border: 1px solid {AppColors.BORDER_COLOR};
                    border-radius: 6px;
                    margin: 5px;
                    padding: 10px;
                }}
            """)
            
            layout = QHBoxLayout(self.metrics_widget)
            
            # Metrics labels
            self.total_nodes_label = QLabel("Nodes: 0")
            self.total_nodes_label.setStyleSheet(f"color: {AppColors.TEXT_LIGHT}; font-weight: bold;")
            
            self.ready_nodes_label = QLabel("Ready: 0")
            self.ready_nodes_label.setStyleSheet(f"color: {AppColors.STATUS_ACTIVE}; font-weight: bold;")
            
            self.not_ready_nodes_label = QLabel("Not Ready: 0")
            self.not_ready_nodes_label.setStyleSheet(f"color: {AppColors.STATUS_DISCONNECTED}; font-weight: bold;")
            
            # Layout metrics
            layout.addWidget(self.total_nodes_label)
            layout.addWidget(QLabel("|"))
            layout.addWidget(self.ready_nodes_label)
            layout.addWidget(QLabel("|"))
            layout.addWidget(self.not_ready_nodes_label)
            layout.addStretch()
            
            # Add to main layout
            if hasattr(self, 'main_layout') and self.main_layout:
                self.main_layout.insertWidget(1, self.metrics_widget)
                self.metrics_widget.show()
                logging.info("NodesPage: Created metrics summary widget")
                
        except Exception as e:
            logging.error(f"NodesPage: Failed to create metrics widget: {e}")
    
    def get_headers(self):
        """Return table column headers"""
        return [
            "Name", "CPU", "Memory", "Disk", 
            "Roles", "Version", "Age", "Status", "Actions"
        ]
    
    def populate_table_row(self, row, node):
        """Populate a single table row with node data"""
        try:
            # Column 0: Name
            name_item = QTableWidgetItem(node.get("name", ""))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 0, name_item)
            
            # Column 1: CPU Usage
            self._populate_usage_column(row, 1, node.get("cpu_usage"), "CPU")
            
            # Column 2: Memory Usage  
            self._populate_usage_column(row, 2, node.get("memory_usage"), "Memory")
            
            # Column 3: Disk Usage
            self._populate_usage_column(row, 3, node.get("disk_usage"), "Disk")
            
            # Column 4: Roles
            roles = node.get("roles", [])
            roles_text = ", ".join(roles) if isinstance(roles, list) else str(roles) or "Worker"
            roles_item = QTableWidgetItem(roles_text)
            roles_item.setFlags(roles_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            roles_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, roles_item)
            
            # Column 5: Version
            version = node.get("kubelet_version", node.get("version", "Unknown"))
            version_item = QTableWidgetItem(version)
            version_item.setFlags(version_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            version_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 5, version_item)
            
            # Column 6: Age
            age_text = self._format_node_age(node)
            age_item = QTableWidgetItem(age_text)
            age_item.setFlags(age_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            age_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 6, age_item)
            
            # Column 7: Status
            self._populate_status_column(row, 7, node.get("status", "Unknown"))
            
            # Column 8: Actions (handled by _create_action_button_for_row)
            
        except Exception as e:
            logging.error(f"NodesPage: Error populating row {row}: {e}")
    
    def _populate_usage_column(self, row, col, usage_value, metric_type):
        """Populate a usage column (CPU/Memory/Disk) with colored percentage"""
        try:
            if usage_value is not None:
                try:
                    usage_num = float(usage_value)
                    text = f"{usage_num:.1f}%"
                    color = self._get_usage_color(usage_num)
                except (ValueError, TypeError):
                    text = "N/A"
                    color = AppColors.TEXT_SUBTLE
            else:
                text = "N/A"
                color = AppColors.TEXT_SUBTLE
            
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            
            # Apply color with multiple methods for compatibility
            brush = QBrush(QColor(color))
            item.setForeground(brush)
            item.setData(Qt.ItemDataRole.ForegroundRole, QColor(color))
            
            self.table.setItem(row, col, item)
            
        except Exception as e:
            logging.error(f"NodesPage: Error populating {metric_type} column: {e}")
    
    def _populate_status_column(self, row, col, status):
        """Populate status column with colored status text"""
        try:
            item = QTableWidgetItem(status)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            
            # Color code based on status
            if status.lower() == "ready":
                color = AppColors.STATUS_ACTIVE
            elif status.lower() == "notready":
                color = AppColors.STATUS_DISCONNECTED
            else:
                color = AppColors.STATUS_WARNING
            
            # Apply color
            brush = QBrush(QColor(color))
            item.setForeground(brush)
            item.setData(Qt.ItemDataRole.ForegroundRole, QColor(color))
            
            self.table.setItem(row, col, item)
            
        except Exception as e:
            logging.error(f"NodesPage: Error populating status column: {e}")
    
    def _get_usage_color(self, usage_percentage):
        """Get color based on resource usage percentage"""
        if usage_percentage >= 90:
            return AppColors.STATUS_DISCONNECTED  # Red - Critical
        elif usage_percentage >= 70:
            return AppColors.STATUS_WARNING       # Orange - High
        elif usage_percentage >= 50:
            return AppColors.TEXT_LIGHT          # White - Medium
        else:
            return AppColors.STATUS_ACTIVE       # Green - Low
    
    def _format_node_age(self, node):
        """Format node age with detailed time units"""
        try:
            # Try multiple timestamp fields
            timestamp_fields = ["creation_timestamp", "creationTimestamp", "created", "created_at", "startup_time"]
            
            for field in timestamp_fields:
                timestamp = node.get(field)
                if timestamp and timestamp != "Unknown":
                    return self._format_detailed_age(timestamp)
            
            return "Unknown"
            
        except Exception as e:
            logging.error(f"NodesPage: Error formatting age for node {node.get('name', '')}: {e}")
            return "Unknown"
    
    def _format_detailed_age(self, timestamp):
        """Format timestamp into detailed age string (e.g., '2d 5h', '1h 30m')"""
        try:
            # Parse timestamp
            if isinstance(timestamp, str):
                if any(timestamp.endswith(suffix) for suffix in ['s', 'm', 'h', 'd', 'mo', 'y']):
                    return timestamp  # Already formatted
                
                if 'T' in timestamp:
                    created = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    created = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
            else:
                created = timestamp
            
            # Ensure timezone aware
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            
            # Calculate age components
            now = datetime.now(timezone.utc)
            age_delta = now - created
            
            days = age_delta.days
            hours = age_delta.seconds // 3600
            minutes = (age_delta.seconds % 3600) // 60
            seconds = age_delta.seconds % 60
            
            # Format with two most significant units
            if days > 365:
                years = days // 365
                remaining_days = days % 365
                return f"{years}y {remaining_days // 30}mo" if remaining_days > 30 else f"{years}y {remaining_days}d"
            elif days > 30:
                months = days // 30
                remaining_days = days % 30
                return f"{months}mo {remaining_days}d"
            elif days > 0:
                return f"{days}d {hours}h" if hours > 0 else f"{days}d"
            elif hours > 0:
                return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
            elif minutes > 0:
                return f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"
            else:
                return f"{seconds}s"
                
        except Exception as e:
            logging.debug(f"Error formatting detailed age: {e}")
            return "Unknown"
    
    def populate_table(self, resources_data):
        """Populate the table with nodes data and update metrics"""
        try:
            if not hasattr(self, 'table') or not self.table:
                logging.error("NodesPage: Table not available")
                return
            
            self._clear_table_widgets()
            
            if not resources_data:
                self._show_empty_state()
                return
            
            # Store resources for search
            self.resources = resources_data
            
            # Setup table
            self.table.setRowCount(len(resources_data))
            
            # Populate rows
            for row, node in enumerate(resources_data):
                try:
                    self.table.setRowHeight(row, 32)
                    self.populate_table_row(row, node)
                    self._create_action_button_for_row(row, node)
                except Exception as e:
                    logging.error(f"NodesPage: Error processing row {row}: {e}")
            
            # Update metrics and configure columns
            self._update_metrics_summary(resources_data)
            self.configure_columns()
            self._update_items_count()
            
            logging.info(f"NodesPage: Populated table with {len(resources_data)} nodes")
            
        except Exception as e:
            logging.error(f"NodesPage: Error populating table: {e}")
    
    def _show_empty_state(self):
        """Show empty state when no nodes are available"""
        self.table.setRowCount(1)
        item = QTableWidgetItem("No nodes available")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(0, 0, item)
        
        # Clear other cells and span across columns
        for col in range(1, self.table.columnCount()):
            empty_item = QTableWidgetItem("")
            empty_item.setFlags(empty_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(0, col, empty_item)
        
        self.table.setSpan(0, 0, 1, len(self.get_headers()))
        
        # Update count for empty state
        self._update_items_count()
    
    def _update_metrics_summary(self, nodes_data):
        """Update metrics summary with current node statistics"""
        try:
            if not nodes_data or not hasattr(self, 'total_nodes_label'):
                return
            
            total_nodes = len(nodes_data)
            ready_nodes = sum(1 for node in nodes_data if node.get("status", "").lower() == "ready")
            not_ready_nodes = total_nodes - ready_nodes
            
            self.total_nodes_label.setText(f"Nodes: {total_nodes}")
            self.ready_nodes_label.setText(f"Ready: {ready_nodes}")
            self.not_ready_nodes_label.setText(f"Not Ready: {not_ready_nodes}")
            
        except Exception as e:
            logging.error(f"NodesPage: Error updating metrics: {e}")
    
    def _update_items_count(self):
        """Update the items count label with correct node count"""
        try:
            # Count actual visible rows in table, not total resources
            if hasattr(self, 'table') and self.table:
                count = self.table.rowCount()
                # Don't count if it's an empty state row
                if count == 1:
                    first_item = self.table.item(0, 0)
                    if first_item and first_item.text() == "No nodes available":
                        count = 0
            else:
                count = 0
            
            if hasattr(self, 'items_count') and self.items_count:
                # Use "nodes" instead of generic "items"
                self.items_count.setText(f"{count} nodes")
                logging.debug(f"NodesPage: Updated items count to {count} nodes")
        except Exception as e:
            logging.error(f"NodesPage: Error updating items count: {e}")
    
    def _create_action_button_for_row(self, row, node):
        """Create action button for node row"""
        try:
            node_name = node.get("name", "")
            if not node_name:
                return
            
            action_btn = self._create_action_button(node_name)
            action_btn.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
            
            # Create container for positioning
            from PyQt6.QtWidgets import QWidget
            container = QWidget()
            container.setStyleSheet("QWidget { background-color: transparent; border: none; }")
            container.setFixedSize(40, 32)
            
            # Position button in container
            action_btn.setParent(container)
            action_btn.move(8, -6)
            
            self.table.setCellWidget(row, 8, container)
            
        except Exception as e:
            logging.error(f"NodesPage: Error creating action button for row {row}: {e}")
    
    def _create_action_button(self, resource_name):
        """Create action dropdown button for node"""
        try:
            from PyQt6.QtWidgets import QToolButton, QMenu
            from PyQt6.QtCore import QSize
            from PyQt6.QtGui import QIcon
            import os
            
            button = QToolButton()
            button.setFixedSize(24, 24)
            
            # Load icon or use text fallback
            icon_path = resource_path("Icons/Moreaction_Button.svg")
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                if not icon.isNull():
                    button.setIcon(icon)
                    button.setIconSize(QSize(16, 16))
                else:
                    button.setText("⋮")
            else:
                button.setText("⋮")
            
            # Create menu
            menu = QMenu(button)
            menu.setStyleSheet(f"""
                QMenu {{
                    background-color: {AppColors.BG_MEDIUM};
                    color: {AppColors.TEXT_LIGHT};
                    border: 1px solid {AppColors.BORDER_COLOR};
                    border-radius: 4px;
                    padding: 2px;
                }}
                QMenu::item {{
                    padding: 6px 12px;
                    border-radius: 2px;
                }}
                QMenu::item:selected {{
                    background-color: {AppColors.HOVER_BG};
                }}
            """)
            
            # Add menu actions
            view_action = menu.addAction("View Details")
            view_action.triggered.connect(lambda: self._handle_menu_action("View Details", resource_name))
            
            edit_action = menu.addAction("Edit")
            edit_action.triggered.connect(lambda: self._handle_menu_action("Edit", resource_name))
            
            drain_action = menu.addAction("Drain Node")
            drain_action.triggered.connect(lambda: self._handle_menu_action("Drain Node", resource_name))
            
            cordon_action = menu.addAction("Cordon Node")
            cordon_action.triggered.connect(lambda: self._handle_menu_action("Cordon Node", resource_name))
            
            button.setMenu(menu)
            button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            button.clicked.connect(lambda: button.showMenu())
            
            return button
            
        except Exception as e:
            logging.error(f"NodesPage: Error creating action button: {e}")
            # Fallback button
            from PyQt6.QtWidgets import QToolButton
            button = QToolButton()
            button.setText("⋮")
            button.setFixedSize(24, 24)
            return button
    
    def _handle_menu_action(self, action, resource_name):
        """Handle menu action selection"""
        try:
            logging.info(f"NodesPage: Menu action '{action}' for node '{resource_name}'")
            
            if action == "View Details":
                self._open_node_details(resource_name)
            elif action == "Edit":
                self._open_node_edit(resource_name)
            elif action == "Drain Node":
                self._handle_drain_node(resource_name)
            elif action == "Cordon Node":
                self._handle_cordon_node(resource_name)
            else:
                logging.warning(f"NodesPage: Unknown action '{action}'")
                
        except Exception as e:
            logging.error(f"NodesPage: Error handling menu action '{action}': {e}")
    
    def _open_node_details(self, node_name):
        """Open node detail page"""
        try:
            logging.info(f"NodesPage: Opening details for node '{node_name}'")
            
            cluster_view = self._find_cluster_view()
            if cluster_view and hasattr(cluster_view, 'detail_manager'):
                cluster_view.detail_manager.show_detail('node', node_name, None)
                logging.info(f"NodesPage: Opened detail page for node '{node_name}'")
            else:
                self._show_detail_unavailable_message(node_name)
                
        except Exception as e:
            logging.error(f"NodesPage: Error opening details for node '{node_name}': {e}")
    
    def _open_node_edit(self, node_name):
        """Open node in edit mode"""
        try:
            logging.info(f"NodesPage: Opening edit mode for node '{node_name}'")
            
            cluster_view = self._find_cluster_view()
            if cluster_view and hasattr(cluster_view, 'detail_manager'):
                cluster_view.detail_manager.show_detail('node', node_name, None)
                # Trigger edit mode after a delay
                QTimer.singleShot(500, lambda: self._trigger_edit_mode(cluster_view))
                logging.info(f"NodesPage: Opened edit mode for node '{node_name}'")
            else:
                self._show_detail_unavailable_message(node_name)
                
        except Exception as e:
            logging.error(f"NodesPage: Error opening edit mode for node '{node_name}': {e}")
    
    def _find_cluster_view(self):
        """Find the parent ClusterView containing the detail manager"""
        try:
            parent = self.parent()
            while parent:
                parent_name = parent.__class__.__name__
                if parent_name == 'ClusterView' or hasattr(parent, 'detail_manager'):
                    logging.debug(f"NodesPage: Found ClusterView in '{parent_name}'")
                    return parent
                parent = parent.parent()
            
            logging.warning("NodesPage: Could not find ClusterView")
            return None
            
        except Exception as e:
            logging.error(f"NodesPage: Error finding ClusterView: {e}")
            return None
    
    def _trigger_edit_mode(self, cluster_view):
        """Trigger edit mode in the detail page YAML section"""
        try:
            if (hasattr(cluster_view, 'detail_manager') and 
                cluster_view.detail_manager._detail_page):
                
                detail_page = cluster_view.detail_manager._detail_page
                
                if hasattr(detail_page, 'yaml_section'):
                    yaml_section = detail_page.yaml_section
                    if (hasattr(yaml_section, 'toggle_yaml_edit_mode') and 
                        yaml_section.yaml_editor.isReadOnly()):
                        yaml_section.toggle_yaml_edit_mode()
                        logging.info("NodesPage: Triggered edit mode")
                        
        except Exception as e:
            logging.error(f"NodesPage: Error triggering edit mode: {e}")
    
    def _show_detail_unavailable_message(self, node_name):
        """Show message when detail panel is not available"""
        QMessageBox.information(
            self, "Node Details",
            f"Node: {node_name}\n\nDetail panel not available. "
            f"Please check the main view configuration."
        )
    
    def _handle_drain_node(self, node_name):
        """Handle node drain operation"""
        try:
            reply = QMessageBox.question(
                self, 'Drain Node',
                f'Are you sure you want to drain node "{node_name}"?\n\n'
                'This will safely evict all pods from the node.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # TODO: Implement actual drain operation
                QMessageBox.information(
                    self, "Drain Node",
                    f'Node "{node_name}" drain operation would be initiated.\n'
                    '(Implementation pending)'
                )
                
        except Exception as e:
            logging.error(f"NodesPage: Error draining node '{node_name}': {e}")
    
    def _handle_cordon_node(self, node_name):
        """Handle node cordon operation"""
        try:
            reply = QMessageBox.question(
                self, 'Cordon Node',
                f'Are you sure you want to cordon node "{node_name}"?\n\n'
                'This will mark the node as unschedulable.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # TODO: Implement actual cordon operation
                QMessageBox.information(
                    self, "Cordon Node",
                    f'Node "{node_name}" cordon operation would be initiated.\n'
                    '(Implementation pending)'
                )
                
        except Exception as e:
            logging.error(f"NodesPage: Error cordoning node '{node_name}': {e}")
    
    def _clear_table_widgets(self):
        """Clear all cell widgets from the table"""
        try:
            if not hasattr(self, 'table') or not self.table:
                return
            
            for row in range(self.table.rowCount()):
                for col in range(self.table.columnCount()):
                    widget = self.table.cellWidget(row, col)
                    if widget:
                        self.table.removeCellWidget(row, col)
                        widget.deleteLater()
            
            self.table.clearSpans()
            
        except Exception as e:
            logging.error(f"NodesPage: Error clearing table widgets: {e}")
    
    def configure_columns(self):
        """Configure table column widths and alignment for NodesPage"""
        try:
            if not hasattr(self, 'table') or not self.table:
                return
            
            header = self.table.horizontalHeader()
            
            # Configure proper resizing behavior for NodesPage
            from PyQt6.QtWidgets import QHeaderView
            
            # Override base class column configuration
            header.setStretchLastSection(False)
            header.setSectionsMovable(False)
            header.setSectionsClickable(True)
            header.setMinimumSectionSize(50)  # Allow reasonable minimum
            header.setDefaultSectionSize(120)
            
            # Configure each column specifically for NodesPage
            headers = self.get_headers()
            for i in range(len(headers)):
                if i == 0:  # Name column - resizable, larger minimum
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                    header.resizeSection(i, 200)
                elif i == len(headers) - 1:  # Actions column - fixed width
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                    header.resizeSection(i, 80)
                else:  # Other columns - interactive resizing
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            
            # Set specific column widths
            header.resizeSection(1, 80)   # CPU
            header.resizeSection(2, 80)   # Memory
            header.resizeSection(3, 80)   # Disk
            header.resizeSection(4, 120)  # Roles
            header.resizeSection(5, 120)  # Version
            header.resizeSection(6, 80)   # Age
            header.resizeSection(7, 100)  # Status
            
            # Set Status column to stretch to fill remaining space
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
            
            # Set header alignment
            for col in range(self.table.columnCount()):
                header_item = self.table.horizontalHeaderItem(col)
                if header_item:
                    if col == 0:  # Name column - left align
                        header_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    else:  # Other columns - center align
                        header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            
            logging.debug("NodesPage: Configured columns with proper resizing")
            
        except Exception as e:
            logging.error(f"NodesPage: Error configuring columns: {e}")
    
    
    def refresh_data(self):
        """Refresh nodes data from the cluster"""
        try:
            from Utils.unified_resource_loader import get_unified_resource_loader
            loader = get_unified_resource_loader()
            if loader:
                loader.load_resource_async(
                    resource_type=self.resource_type,
                    namespace="all",
                    force_refresh=True
                )
                logging.info("NodesPage: Requested fresh data")
            else:
                logging.error("NodesPage: Could not get resource loader")
                
        except Exception as e:
            logging.error(f"NodesPage: Error refreshing data: {e}")
    
    def get_resource_display_name(self):
        """Return display name for this resource type"""
        return "Nodes"
    
    def get_resource_icon(self):
        """Return icon for nodes"""
        try:
            return Icons.get_icon("nodes", use_local=True)
        except Exception as e:
            logging.error(f"NodesPage: Error getting nodes icon: {e}")
            return Icons.create_text_icon("📟")
    
    def _on_unified_resources_loaded(self, resource_type, result):
        """Override to handle unified resource loading properly"""
        try:
            if resource_type != self.resource_type:
                return
                
            if result.success:
                logging.info(f"NodesPage: Successfully loaded {len(result.items)} {resource_type}")
                
                # Store the resources for search functionality
                self.resources = result.items
                
                # Only show results if we're not in search mode or this is search results
                if not getattr(self, '_is_searching', False):
                    # Normal load - show all results
                    self.populate_table(result.items)
                    logging.info(f"NodesPage: Displayed {len(result.items)} nodes normally")
                else:
                    # We're in search mode - let search handler deal with it
                    logging.info(f"NodesPage: Received {len(result.items)} nodes during search mode")
            else:
                logging.error(f"NodesPage: Failed to load {resource_type}: {result.error_message}")
                # Show empty message using populate_table to ensure proper cleanup
                self.populate_table([])
                
        except Exception as e:
            logging.error(f"NodesPage: Error processing unified resources: {e}")
    
    def _on_search_text_changed(self, text):
        """Override base class search to use local filtering for nodes"""
        try:
            text = text.strip()
            logging.info(f"NodesPage: Search text changed to: '{text}'")
            
            if not text:
                # Search cleared - restore original data
                self._on_search_cleared()
            else:
                # Perform local search to avoid duplicates
                if hasattr(self, 'resources') and self.resources:
                    filtered_results = self._filter_resources(text)
                    
                    if filtered_results:
                        self.populate_table(filtered_results)
                        logging.info(f"NodesPage: Local search '{text}' showing {len(filtered_results)} results")
                    else:
                        # No results found - show empty message
                        self.populate_table([])
                        logging.info(f"NodesPage: Local search '{text}' found no matching results")
                else:
                    logging.warning("NodesPage: No cached resources for search")
                    # Show empty message when no cached resources
                    self.populate_table([])
        except Exception as e:
            logging.error(f"NodesPage: Error handling search text change: {e}")
    
    def _on_search_cleared(self):
        """Handle when search is cleared - ensure data is restored"""
        try:
            logging.info("NodesPage: Search cleared, restoring original data")
            # Reset search mode flags
            if hasattr(self, '_is_searching'):
                self._is_searching = False
            if hasattr(self, '_current_search_query'):
                self._current_search_query = None
                
            # First try to restore from existing resources
            if hasattr(self, 'resources') and self.resources:
                self.populate_table(self.resources)
                logging.info(f"NodesPage: Restored {len(self.resources)} nodes from cache")
            else:
                # If no cached resources, refresh from server
                logging.info("NodesPage: No cached resources, refreshing from server")
                self.refresh_data()
        except Exception as e:
            logging.error(f"NodesPage: Error handling search clear: {e}")
            # Fallback to refresh if restore fails
            try:
                self.refresh_data()
            except Exception as refresh_error:
                logging.error(f"NodesPage: Fallback refresh also failed: {refresh_error}")
    
    def _on_search_results_loaded(self, resource_type, result):
        """Override to prevent base class search results from interfering"""
        # For nodes, we handle search locally, so ignore global search results
        logging.debug(f"NodesPage: Ignoring global search results for {resource_type} with {len(result.items) if result.success else 0} items - using local search")
        pass
    
    def _filter_resources(self, search_query):
        """Override to prevent duplicate results and handle search properly"""
        try:
            if not search_query or not hasattr(self, 'resources') or not self.resources:
                # If no search query, show all resources
                return self.resources if hasattr(self, 'resources') else []
            
            search_query = search_query.lower().strip()
            if not search_query:  # Empty after strip
                return self.resources
            
            filtered = []
            seen_names = set()  # Prevent duplicates by tracking seen node names
            
            for resource in self.resources:
                if isinstance(resource, dict):
                    node_name = resource.get('name', '')
                    
                    # Skip if we've already seen this node (prevent duplicates)
                    if node_name in seen_names:
                        logging.debug(f"NodesPage: Skipping duplicate node: {node_name}")
                        continue
                    
                    # Search in node name, status, roles
                    searchable_fields = [
                        node_name,
                        resource.get('status', ''),
                        ', '.join(resource.get('roles', [])) if isinstance(resource.get('roles'), list) else str(resource.get('roles', '')),
                        resource.get('kubelet_version', ''),
                        resource.get('version', '')
                    ]
                    
                    # Check if search query matches any field
                    match_found = False
                    for field in searchable_fields:
                        if field and search_query in str(field).lower():
                            match_found = True
                            break
                    
                    if match_found:
                        filtered.append(resource)
                        seen_names.add(node_name)
                        logging.debug(f"NodesPage: Added matching node: {node_name}")
            
            logging.info(f"NodesPage: Local search '{search_query}' found {len(filtered)} unique results")
            return filtered
            
        except Exception as e:
            logging.error(f"NodesPage: Error filtering resources: {e}")
            return self.resources if hasattr(self, 'resources') else []
    
    def _perform_search(self):
        """Override base class search to use local filtering instead of global search"""
        try:
            search_text = self.search_bar.text().strip() if hasattr(self, 'search_bar') and self.search_bar else ""
            
            if not search_text:
                # No search query, clear search
                self._on_search_cleared()
            else:
                # Use local search instead of global search
                logging.info(f"NodesPage: Performing local search for '{search_text}'")
                if hasattr(self, 'resources') and self.resources:
                    filtered_results = self._filter_resources(search_text)
                    self.populate_table(filtered_results)
                    
                    # Set search mode to prevent interference
                    self._is_searching = True
                    self._current_search_query = search_text
                    
                    if filtered_results:
                        logging.info(f"NodesPage: Local search completed - {len(filtered_results)} results")
                    else:
                        logging.info(f"NodesPage: Local search completed - no matching results for '{search_text}'")
                else:
                    logging.warning("NodesPage: No resources available for search")
                    # Show empty message when no cached resources
                    self.populate_table([])
        except Exception as e:
            logging.error(f"NodesPage: Error in _perform_search: {e}")

    # Override parent methods that are not applicable for nodes
    def _create_checkbox_container(self, row, resource_name):
        """Override to prevent checkbox creation for nodes"""
        # Parameters unused as checkboxes are not applicable for nodes
        return None
    
    def _add_select_all_to_header(self):
        """Override to prevent select-all checkbox for nodes"""
        pass
    
    def _create_select_all_checkbox(self):
        """Override to prevent select-all checkbox creation"""
        return None
    
    def _create_delete_button(self):
        """Override to prevent delete button creation"""
        return None
    
    def _setup_delete_functionality(self):
        """Override to prevent delete functionality setup"""
        pass
    
    def delete_selected_resources(self):
        """Override to prevent delete operations on nodes"""
        logging.warning("NodesPage: Delete operation not allowed on nodes")
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "Operation Not Allowed",
            "Nodes cannot be deleted from this interface.\n"
            "Node management should be done through cluster administration tools."
        )
    
    def _handle_delete_selected(self):
        """Override to prevent delete operations"""
        self.delete_selected_resources()
    
    def _on_delete_button_clicked(self):
        """Override to prevent delete button clicks"""
        self.delete_selected_resources()