"""
Updated EventsPage using clean architecture - no more KubernetesResourceLoader import
"""

import logging
from PyQt6.QtWidgets import QHeaderView, QTableWidgetItem, QPushButton, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors

class EventsPage(BaseResourcePage):
    """
    Updated Events page using clean architecture
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "events"
        self.setup_page_ui()

    def setup_page_ui(self):
        """Set up the main UI elements for the Events page"""
        # Define headers and sortable columns
        headers = ["", "Type", "Reason", "Object", "Message", "Age", "Count", "Source", ""]
        sortable_columns = {1, 2, 3, 5, 6, 7}  # Type, Reason, Object, Age, Count, Source
        
        # Set up the base UI components
        layout = super().setup_ui("Events", headers, sortable_columns)
        
        # Configure column widths
        self.configure_columns()
        
        # Add delete selected button
        self._add_delete_selected_button()

    def configure_columns(self):
        """Configure column widths for events table"""
        if not self.table:
            return
        
        header = self.table.horizontalHeader()
        
        # Column specifications [index, width, resize_mode]
        column_specs = [
            (0, 40, "fixed"),        # Checkbox
            (1, 80, "interactive"),  # Type
            (2, 120, "interactive"), # Reason
            (3, 150, "interactive"), # Object
            (4, 300, "stretch"),     # Message (main content)
            (5, 80, "interactive"),  # Age
            (6, 60, "interactive"),  # Count
            (7, 120, "interactive"), # Source
            (8, 80, "fixed")         # Actions
        ]
        
        for col_index, width, resize_mode in column_specs:
            if col_index < self.table.columnCount():
                if resize_mode == "fixed":
                    header.resizeSection(col_index, width)
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Fixed)
                elif resize_mode == "stretch":
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Stretch)
                elif resize_mode == "interactive":
                    header.resizeSection(col_index, width)
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Interactive)

    def _add_delete_selected_button(self):
        """Add a button to delete selected events."""
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected_resources)
        
        # Find the header layout and add the button
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if isinstance(widget, QPushButton) and widget.text() == "Refresh":
                        # Insert before the refresh button
                        item.layout().insertWidget(item.layout().count() - 1, delete_btn)
                        break

    def delete_selected_resources(self):
        """Delete selected event resources - Note: Events are typically read-only"""
        try:
            # Show info message that events cannot be deleted
            QMessageBox.information(
                self, 
                "Events Cannot Be Deleted",
                "Events are read-only system-generated objects that cannot be deleted directly.\n\n"
                "Events will be automatically cleaned up by Kubernetes based on the cluster's "
                "event retention policy."
            )
        except Exception as e:
            logging.error(f"Error in delete_selected_resources: {e}")

    def handle_row_click(self, row, column):
        """Handle row clicks to show event details"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            
            # Get event details
            event_type = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            reason = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
            object_name = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
            message = self.table.item(row, 4).text() if self.table.item(row, 4) else ""
            
            # Show event details in a message box
            details = f"Type: {event_type}\nReason: {reason}\nObject: {object_name}\n\nMessage:\n{message}"
            QMessageBox.information(self, "Event Details", details)

    def update_table_data(self, events):
        """Update the table with events data"""
        if not events:
            self.show_no_data_message()
            return
        
        # Clear existing rows
        self.table.setRowCount(0)
        
        # Add events to table
        for event in events:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Add checkbox
            self.table.setItem(row, 0, QTableWidgetItem(""))
            
            # Add event data
            self.table.setItem(row, 1, SortableTableWidgetItem(event.get('type', '')))
            self.table.setItem(row, 2, SortableTableWidgetItem(event.get('reason', '')))
            self.table.setItem(row, 3, SortableTableWidgetItem(event.get('object', '')))
            self.table.setItem(row, 4, SortableTableWidgetItem(event.get('message', '')))
            self.table.setItem(row, 5, SortableTableWidgetItem(event.get('age', '')))
            self.table.setItem(row, 6, SortableTableWidgetItem(str(event.get('count', ''))))
            self.table.setItem(row, 7, SortableTableWidgetItem(event.get('source', '')))
            
            # Add actions column
            self.table.setItem(row, 8, QTableWidgetItem(""))
            
            # Color code by event type
            if event.get('type') == 'Warning':
                color = QColor(AppColors.TEXT_WARNING)
            elif event.get('type') == 'Normal':
                color = QColor(AppColors.TEXT_SUCCESS)
            else:
                color = QColor(AppColors.TEXT_LIGHT)
            
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setForeground(color)
        
        # Update items count
        self.update_item_count(len(events))

    def show_no_data_message(self):
        """Show a message when no events are available"""
        self._show_message_in_table_area(
            "No events available",
            "No events found in the selected namespace."
        )

    def update_item_count(self, count):
        """Update the item count display"""
        if hasattr(self, 'items_count'):
            self.items_count.setText(f"{count} events")