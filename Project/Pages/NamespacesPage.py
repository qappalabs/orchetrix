"""
Optimized implementation of the Namespaces page with better performance
and memory efficiency.
"""

from PyQt6.QtWidgets import QLabel, QHeaderView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from UI.Styles import AppColors, AppStyles
from base_components.base_components import BaseTablePage, SortableTableWidgetItem

class NamespacesPage(BaseTablePage):
    """
    Displays Kubernetes namespaces with optimizations for performance and memory usage.
    
    Optimizations:
    1. Inherits from BaseTablePage for common functionality
    2. Uses memory-efficient widget creation
    3. Implements proper resource cleanup
    4. Batches UI operations for better performance
    5. Uses SortableTableWidgetItem for proper numeric sorting
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_page_ui()
        self.load_data()
    
    def setup_page_ui(self):
        """Set up the main UI elements for the Namespaces page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Labels", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4}
        
        # Set up the base UI components (assumes this initializes self.title, self.items_count, self.table)
        layout = self.setup_ui("Namespaces", headers, sortable_columns)
        
        # Apply styles after base setup
        try:
            self.table.setStyleSheet(AppStyles.TABLE_STYLE)
            self.title.setStyleSheet(AppStyles.TITLE_STYLE)
            self.items_count.setStyleSheet(AppStyles.ITEMS_COUNT_STYLE)
        except AttributeError as e:
            pass
        
        # Configure column widths
        self.configure_columns()
        
        # Connect the row click handler
        self.table.cellClicked.connect(self.handle_row_click)
    
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Column 0: Checkbox (fixed width) - handled in BaseTablePage
        
        # Column 1: Name (stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Column 2: Labels (stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        # Column 3: Age (fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 80)
        
        # Column 4: Status (fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 100)
        
        # Column 5: Action (fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 40)
        
        # Optimize performance: disable automatic resizing while loading data
        self.table.setUpdatesEnabled(False)
    
    def load_data(self):
        """Load namespace data into the table with optimized batch processing"""
        # Sample namespace data
        namespaces_data = [
            ["default", "kubernetes.io/metadata.name=default", "150d", "Active"],
            ["kube-system", "kubernetes.io/metadata.name=kube-system", "150d", "Active"],
            ["kube-public", "kubernetes.io/metadata.name=kube-public", "150d", "Active"],
            ["kube-node-lease", "kubernetes.io/metadata.name=kube-node-lease", "150d", "Active"],
            ["app-testing", "env=test,app=backend", "45d", "Active"],
            ["app-staging", "env=staging,app=backend", "45d", "Active"],
            ["app-production", "env=prod,app=backend", "45d", "Active"],
            ["monitoring", "app=prometheus,tier=monitoring", "90d", "Active"],
            ["istio-system", "istio-injection=enabled", "75d", "Active"]
        ]

        # Set table row count
        self.table.setRowCount(len(namespaces_data))
        
        # Process all data at once in a batch for better performance
        for row, namespace in enumerate(namespaces_data):
            self.populate_namespace_row(row, namespace)
        
        # Update item count and enable updates
        self.items_count.setText(f"{len(namespaces_data)} items")
        self.table.setUpdatesEnabled(True)
    
    def populate_namespace_row(self, row, namespace_data):
        """Populate a single row with namespace data"""
        # Set row height
        self.table.setRowHeight(row, 40)
        
        name = namespace_data[0]
        labels = namespace_data[1]
        age = namespace_data[2]
        status = namespace_data[3]
        
        # Column 0: Checkbox
        checkbox_container = self._create_checkbox_container(row, name)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Column 1: Name
        name_item = SortableTableWidgetItem(name)
        name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        name_item.setForeground(QColor(AppColors.TEXT_TABLE))
        name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 1, name_item)
        
        # Column 2: Labels
        labels_item = SortableTableWidgetItem(labels)
        labels_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        labels_item.setForeground(QColor(AppColors.TEXT_TABLE))
        labels_item.setFlags(labels_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 2, labels_item)
        
        # Column 3: Age (with sortable value)
        try:
            age_value = int(age.replace('d', ''))
        except ValueError:
            age_value = 0
        age_item = SortableTableWidgetItem(age, age_value)
        age_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        age_item.setForeground(QColor(AppColors.TEXT_TABLE))
        age_item.setFlags(age_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 3, age_item)
        
        # Column 4: Status
        status_item = SortableTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_color = AppColors.STATUS_ACTIVE if status == "Active" else AppColors.TEXT_DANGER
        status_item.setForeground(QColor(status_color))
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 4, status_item)
        
        # Column 5: Action
        action_button = self._create_action_button(row, [
            {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True}
        ])
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, 5, action_container)
    
    def handle_row_click(self, row, column):
        """Handle row clicks"""
        if column != 5:  # Skip action column
            self.table.selectRow(row)
    
    def _handle_action(self, action, row):
        """Override to handle namespace-specific actions"""
        namespace_name = self.table.item(row, 1).text()
        if action == "Edit":
            pass  # Placeholder for edit action
        elif action == "Delete":
            pass  # Placeholder for delete action
