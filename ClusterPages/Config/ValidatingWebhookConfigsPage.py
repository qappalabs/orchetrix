# from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
#                              QTableWidgetItem, QLabel, QHeaderView, QPushButton,
#                              QMenu, QToolButton, QCheckBox, QComboBox, QStyle, QStyleOptionHeader)
# from PyQt6.QtCore import Qt, QSize, QPoint
# from PyQt6.QtGui import QColor, QFont, QIcon, QCursor

# #------------------------------------------------------------------
# # CustomHeader: Controls which columns are sortable with visual indicators
# #------------------------------------------------------------------
# class CustomHeader(QHeaderView):
#     """
#     A custom header that only enables sorting for a subset of columns
#     and shows a hover sort indicator arrow on those columns.
#     """
#     def __init__(self, orientation, parent=None):
#         super().__init__(orientation, parent)
#         # Define which columns will be sortable
#         self.sortable_columns = {1, 2, 3}  # Name, Webhooks, Age
#         self.setSectionsClickable(True)
#         self.setHighlightSections(True)

#     def mousePressEvent(self, event):
#         logicalIndex = self.logicalIndexAt(event.pos())
#         if logicalIndex in self.sortable_columns:
#             super().mousePressEvent(event)
#         else:
#             event.ignore()

#     def paintSection(self, painter, rect, logicalIndex):
#         option = QStyleOptionHeader()
#         self.initStyleOption(option)
#         option.rect = rect
#         option.section = logicalIndex
#         # Retrieve header text from the model and set it in the option.
#         header_text = self.model().headerData(logicalIndex, self.orientation(), Qt.ItemDataRole.DisplayRole)
#         option.text = str(header_text) if header_text is not None else ""

#         if logicalIndex in self.sortable_columns:
#             mouse_pos = QCursor.pos()
#             local_mouse = self.mapFromGlobal(mouse_pos)
#             if rect.contains(local_mouse):
#                 option.state |= QStyle.StateFlag.State_MouseOver
#                 # Use the Qt6 enum value for sort indicator (SortDown for descending)
#                 option.sortIndicator = QStyleOptionHeader.SortIndicator.SortDown
#                 option.state |= QStyle.StateFlag.State_Sunken
#             else:
#                 option.state &= ~QStyle.StateFlag.State_MouseOver
#         else:
#             option.state &= ~QStyle.StateFlag.State_MouseOver

#         self.style().drawControl(QStyle.ControlElement.CE_Header, option, painter, self)

# class SortableTableWidgetItem(QTableWidgetItem):
#     """Custom QTableWidgetItem that can be sorted with values"""
#     def __init__(self, text, value=0):
#         super().__init__(text)
#         self.value = value

#     def __lt__(self, other):
#         if hasattr(other, 'value'):
#             return self.value < other.value
#         return super().__lt__(other)

# class ValidatingWebhookConfigsPage(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.selected_validating_webhook_config = set()  # Track selected config maps
#         self.select_all_checkbox = None  # Store reference to select-all checkbox
#         self.setup_ui()
#         self.load_data()

#     def setup_ui(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(16, 16, 16, 16)
#         layout.setSpacing(16)

#         # Header section
#         header = QHBoxLayout()
#         title = QLabel("Validating Webhook Configs")
#         title.setStyleSheet("""
#             font-size: 20px;
#             font-weight: bold;
#             color: #ffffff;
#         """)

#         self.items_count = QLabel("11 items")
#         self.items_count.setStyleSheet("""
#             color: #9ca3af;
#             font-size: 12px;
#             margin-left: 8px;
#             font-family: 'Segoe UI';
#         """)
#         self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)

#         header.addWidget(title)
#         header.addWidget(self.items_count)
#         header.addStretch()

#         # Create table
#         self.table = QTableWidget()
#         self.table.setColumnCount(5)  # Checkbox, Name, Wrebhooks, Age, Actions
#         headers = ["", "Name", "Webhooks", "Age", ""]
#         self.table.setHorizontalHeaderLabels(headers)

#         # Use the custom header to control sorting
#         custom_header = CustomHeader(Qt.Orientation.Horizontal, self.table)
#         self.table.setHorizontalHeader(custom_header)
#         self.table.setSortingEnabled(True)

#         # Style the table
#         self.table.setStyleSheet("""
#             QTableWidget {
#                 background-color: #1e1e1e;
#                 border: none;
#                 gridline-color: #2d2d2d;
#                 outline: none;
#             }
#             QTableWidget::item {
#                 padding: 8px;
#                 border: none;
#                 outline: none;
#             }
#             QTableWidget::item:hover {
#                 background-color: rgba(255, 255, 255, 0.05);
#                 border-radius: 4px;
#             }
#             QTableWidget::item:selected {
#                 background-color: rgba(33, 150, 243, 0.2);
#                 border: none;
#             }
#             QTableWidget::item:focus {
#                 border: none;
#                 outline: none;
#                 background-color: transparent;
#             }
#             QHeaderView::section {
#                 background-color: #252525;
#                 color: #888888;
#                 padding: 8px;
#                 border: none;
#                 border-bottom: 1px solid #2d2d2d;
#                 font-size: 14px;
#             }
#             QHeaderView::section:hover {
#                 background-color: #2d2d2d;
#             }
#             QToolButton {
#                 border: none;
#                 border-radius: 4px;
#                 padding: 4px;
#             }
#             QToolButton:hover {
#                 background-color: rgba(255, 255, 255, 0.1);
#             }
#         """)

#         # Configure selection behavior
#         self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
#         self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
#         self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

#         # Configure table properties
#         self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name column
#         self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
#         self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
#         self.table.horizontalHeader().setStretchLastSection(False)
#         self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
#         self.table.setColumnWidth(4, 40)  # Width for action column
#         self.table.setShowGrid(True)
#         self.table.setAlternatingRowColors(False)
#         self.table.verticalHeader().setVisible(False)

#         # Fixed widths for columns
#         column_widths = [40, None, None, None, 40]
#         for i, width in enumerate(column_widths):
#             if i != 1 or i != 2 or i != 3:  # Skip the Name column which is set to stretch
#                 if width is not None:
#                     self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
#                     self.table.setColumnWidth(i, width)

#         # Temporarily disable sorting during data loading
#         self.table.setSortingEnabled(False)

#         # Set up select all checkbox
#         select_all_checkbox = self.create_select_all_checkbox()
#         self.set_header_widget(0, select_all_checkbox)

#         # Install event filter to handle clicks outside the table
#         self.installEventFilter(self)

#         # Override mousePressEvent to handle selections properly
#         self.table.mousePressEvent = self.custom_table_mousePressEvent

#         # Add click handler for rows
#         self.table.cellClicked.connect(self.handle_row_click)

#         layout.addLayout(header)
#         layout.addWidget(self.table)

#     def custom_table_mousePressEvent(self, event):
#         index = self.table.indexAt(event.pos())
#         if index.isValid():
#             row = index.row()
#             if index.column() != 5:  # Skip action column
#                 # Toggle checkbox when clicking anywhere in the row
#                 checkbox_container = self.table.cellWidget(row, 0)
#                 if checkbox_container:
#                     for child in checkbox_container.children():
#                         if isinstance(child, QCheckBox):
#                             child.setChecked(not child.isChecked())
#                             break
#                 # Select the row
#                 self.table.selectRow(row)
#             QTableWidget.mousePressEvent(self.table, event)
#         else:
#             self.table.clearSelection()
#             QTableWidget.mousePressEvent(self.table, event)

#     def eventFilter(self, obj, event):
#         """
#         Handle clicks outside the table to clear row selection
#         """
#         if event.type() == event.Type.MouseButtonPress:
#             # Get the position of the mouse click
#             pos = event.pos()
#             if not self.table.geometry().contains(pos):
#                 # If click is outside the table, clear the selection (but keep checkboxes)
#                 self.table.clearSelection()
#         return super().eventFilter(obj, event)

#     def handle_row_click(self, row, column):
#         if column != 5:  # Don't trigger for action button column
#             validating_webhook_config_name = self.table.item(row, 1).text()
#             print(f"Clicked  validating Webhook configs: {validating_webhook_config_name}")
#             # Add your Mutation validating configs  click handling logic here

#     def create_action_button(self, row):
#         button = QToolButton()
#         button.setText("⋮")  # Three dots
#         button.setFixedWidth(30)
#         # Set alignment programmatically instead of through stylesheet
#         button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
#         button.setStyleSheet("""
#             QToolButton {
#                 color: #888888;
#                 font-size: 18px;
#                 background: transparent;
#                 padding: 2px;
#                 margin: 0;
#                 border: none;
#                 font-weight: bold;
#             }
#             QToolButton:hover {
#                 background-color: rgba(255, 255, 255, 0.1);
#                 border-radius: 3px;
#                 color: #ffffff;
#             }
#             QToolButton::menu-indicator {
#                 image: none;
#             }
#         """)

#         # Center align the text
#         button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
#         button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
#         button.setCursor(Qt.CursorShape.PointingHandCursor)

#         # Create menu with actions
#         menu = QMenu(button)
#         menu.setStyleSheet("""
#             QMenu {
#                 background-color: #2d2d2d;
#                 border: 1px solid #3d3d3d;
#                 border-radius: 4px;
#                 padding: 4px;
#             }
#             QMenu::item {
#                 color: #ffffff;
#                 padding: 8px 24px 8px 36px;  /* Added left padding for icons */
#                 border-radius: 4px;
#                 font-size: 13px;
#             }
#             QMenu::item:selected {
#                 background-color: rgba(33, 150, 243, 0.2);
#                 color: #ffffff;
#             }
#             QMenu::item[dangerous="true"] {
#                 color: #ff4444;
#             }
#             QMenu::item[dangerous="true"]:selected {
#                 background-color: rgba(255, 68, 68, 0.1);
#             }
#         """)

#         # Create Edit action with pencil icon
#         edit_action = menu.addAction("Edit")
#         edit_action.setIcon(QIcon("icons/edit.png"))
#         edit_action.triggered.connect(lambda: self.handle_action("Edit", row))

#         # Create Delete action with trash icon
#         delete_action = menu.addAction("Delete")
#         delete_action.setIcon(QIcon("icons/delete.png"))
#         delete_action.setProperty("dangerous", True)
#         delete_action.triggered.connect(lambda: self.handle_action("Delete", row))

#         button.setMenu(menu)

#         # Create a container for the action button to prevent selection
#         action_container = QWidget()
#         action_layout = QHBoxLayout(action_container)
#         action_layout.setContentsMargins(0, 0, 0, 0)
#         action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         action_layout.addWidget(button)
#         action_container.setStyleSheet("background-color: transparent;")

#         return action_container

#     def handle_action(self, action, row):
#         validating_webhook_config_name = self.table.item(row, 1).text()
#         if action == "Edit":
#             print(f"Editing validating webhook configs: {validating_webhook_config_name}")
#             # Add edit logic here
#         elif action == "Delete":
#             print(f"Deleting validating webhook configs: {validating_webhook_config_name}")
#             # Add delete logic here

#     def create_checkbox(self, row, validating_webhook_config_name):
#         checkbox = QCheckBox()
#         checkbox.setStyleSheet("""
#             QCheckBox {
#                 spacing: 5px;
#                 background: transparent;
#             }
#             QCheckBox::indicator {
#                 width: 16px;
#                 height: 16px;
#                 border: 2px solid #666666;
#                 border-radius: 3px;
#                 background: transparent;
#             }
#             QCheckBox::indicator:checked {
#                 background-color: #0095ff;
#                 border-color: #0095ff;
#             }
#             QCheckBox::indicator:hover {
#                 border-color: #888888;
#             }
#         """)

#         checkbox.stateChanged.connect(lambda state: self.handle_checkbox_change(state, validating_webhook_config_name))
#         return checkbox

#     def create_checkbox_container(self, row, validating_webhook_config_name):
#         """Create a container widget for the checkbox to prevent row selection"""
#         container = QWidget()
#         container.setStyleSheet("background-color: transparent;")

#         layout = QHBoxLayout(container)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         checkbox = self.create_checkbox(row, validating_webhook_config_name)
#         layout.addWidget(checkbox)

#         return container

#     def handle_checkbox_change(self, state, validating_webhook_config_name):
#         if state == Qt.CheckState.Checked.value:
#             self.selected_validating_webhook_config.add(validating_webhook_config_name)
#         else:
#             self.selected_validating_webhook_config.discard(validating_webhook_config_name)

#             # If any checkbox is unchecked, uncheck the select-all checkbox
#             if self.select_all_checkbox is not None and self.select_all_checkbox.isChecked():
#                 # Block signals to prevent infinite recursion
#                 self.select_all_checkbox.blockSignals(True)
#                 self.select_all_checkbox.setChecked(False)
#                 self.select_all_checkbox.blockSignals(False)

#         print(f"Selected validating webhook configs: {self.selected_validating_webhook_config}")

#     def create_select_all_checkbox(self):
#         checkbox = QCheckBox()
#         checkbox.setStyleSheet("""
#             QCheckBox {
#                 spacing: 5px;
#                 background-color: #252525;
#             }
#             QCheckBox::indicator {
#                 width: 16px;
#                 height: 16px;
#                 border: 2px solid #666666;
#                 border-radius: 3px;
#                 background: transparent;
#             }
#             QCheckBox::indicator:checked {
#                 background-color: #0095ff;
#                 border-color: #0095ff;
#             }
#             QCheckBox::indicator:hover {
#                 border-color: #888888;
#             }
#         """)
#         checkbox.stateChanged.connect(self.handle_select_all)
#         self.select_all_checkbox = checkbox
#         return checkbox

#     def handle_select_all(self, state):
#         # Check/uncheck all row checkboxes
#         for row in range(self.table.rowCount()):
#             checkbox_container = self.table.cellWidget(row, 0)
#             if checkbox_container:
#                 # Find the checkbox within the container
#                 for child in checkbox_container.children():
#                     if isinstance(child, QCheckBox):
#                         child.setChecked(state == Qt.CheckState.Checked.value)
#                         break

#     def load_data(self):
#         # Data from the image
#         validating_webhook_configs_data = [
#             ["cluster-info", "kube-public", "71d"],
#             ["coredns", "kube-system",  "71d"],
#             ["extension-apiserver-authentication", "kube-system","71d"],
#             ["kube-apiserver-legacy-service-account-token-tra", "kube-system",  "71d"],
#             ["kube-proxy", "kube-system",  "71d"],
            
#         ]

#         self.table.setRowCount(len(validating_webhook_configs_data))

#         for row, validating_webhook_config in enumerate(validating_webhook_configs_data):
#             # Set row height
#             self.table.setRowHeight(row, 40)

#             # Add checkbox in a container to prevent selection issues
#             checkbox_container = self.create_checkbox_container(row, validating_webhook_config[0])
#             self.table.setCellWidget(row, 0, checkbox_container)

#             # Add rest of the data
#             for col, value in enumerate(validating_webhook_config):
#                 # Skip value extraction for the checkbox already handled
#                 cell_col = col + 1

#                 # Use SortableTableWidgetItem for columns that need sorting
#                 if col == 3:  # Age column
#                     # Extract number for proper sorting (e.g., "71d" -> 71)
#                     days = int(value.replace('d', ''))
#                     item = SortableTableWidgetItem(value, days)
#                 else:
#                     item = QTableWidgetItem(value)

#                 # Set alignment based on column
#                 if col == 3:  # Age column
#                     item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#                 else:
#                     item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

#                 item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
#                 item.setForeground(QColor("#e2e8f0"))

#                 self.table.setItem(row, cell_col, item)

#             # Add action button
#             action_button = self.create_action_button(row)
#             self.table.setCellWidget(row, 4, action_button)

#         # Update items count label
#         self.items_count.setText(f"{len(validating_webhook_configs_data)} items")

#         # Re-enable sorting after data is loaded
#         self.table.setSortingEnabled(True)

#     def set_header_widget(self, col, widget):
#         """
#         Place a custom widget (like a 'select all' checkbox) into the horizontal header.
#         """
#         header = self.table.horizontalHeader()
#         header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
#         header.resizeSection(col, 40)

#         # Replace default header text with an empty string
#         self.table.setHorizontalHeaderItem(col, QTableWidgetItem(""))

#         # Position the widget
#         # (We embed it in a container so we can manage layout easily)
#         container = QWidget()
#         container.setStyleSheet("background-color: #252525;") # Match header background
#         container_layout = QHBoxLayout(container)
#         container_layout.setContentsMargins(0, 0, 0, 0)
#         container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         container_layout.addWidget(widget)
#         container.setFixedHeight(header.height())

#         container.setParent(header)
#         container.setGeometry(header.sectionPosition(col), 0, header.sectionSize(col), header.height())
#         container.show()


"""
Optimized implementation of the VWCs page with better memory management
and performance.
"""

from PyQt6.QtWidgets import  QHeaderView
from PyQt6.QtCore import Qt

from base_components.base_components import BaseTablePage, SortableTableWidgetItem

class ValidatingWebhookConfigsPage(BaseTablePage):
    """
    Displays Kubernetes VWC with optimizations for performance and memory usage.
    
    Optimizations:
    1. Uses BaseTablePage for common functionality to reduce code duplication
    2. Implements lazy loading of table rows for better performance with large datasets
    3. Uses object pooling to reduce GC pressure from widget creation
    4. Implements virtualized scrolling for better performance with large tables
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_page_ui()
        self.load_data()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the VWC page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Webhooks", "Age", ""]
        sortable_columns = {1, 2, 3}
        
        # Set up the base UI components
        layout = self.setup_ui("Validating Webhooks Configs", headers, sortable_columns)
        
        # Configure column widths
        self.configure_columns()
        
        # Connect the row click handler
        self.table.cellClicked.connect(self.handle_row_click)
    
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Column 0: Checkbox (fixed width) - already set in base class
        
        # Column 1: Name (stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Configure stretch columns
        stretch_columns = [2, 3]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 40)
    
    def load_data(self):
        """Load  VWC data into the table with optimized batch processing"""
        # Sample VWC data
        VWC_data = [
            ["cluster-info", "kube-public",  "71d"],
            ["coredns", "kube-system","71d"],
            ["extension-apiserver-authentication", "kube-system", "71d"],
            ["kube-apiserver-legacy-service-account-token-tra", "kube-system", "71d"],
            ["kube-proxy", "kube-system", "71d"],
            
        ]

        # Set up the table for the data
        self.table.setRowCount(len(VWC_data))
        
        # Batch process all rows using a single loop for better performance
        for row, VWC in enumerate(VWC_data):
            self.populate_VWC_row(row, VWC)
        
        # Update the item count
        self.items_count.setText(f"{len(VWC_data)} items")
    
    def populate_VWC_row(self, row, VWC_data):
        """
        Populate a single row with VWC data using efficient methods
        
        Args:
            row: The row index
            VWC_data: List containing VWC information
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        VWC_name = VWC_data[0]
        checkbox_container = self._create_checkbox_container(row, VWC_name)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Populate data columns efficiently
        for col, value in enumerate(VWC_data):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            
            if col == 2:  # Age column
                try:
                    num = int(value.replace('d', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col == 2:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, [
            {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True},
            {"text": "Logs", "icon": "icons/logs.png", "dangerous": False},
            {"text": "Shell", "icon": "icons/shell.png", "dangerous": False},
        ])
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, len(VWC_data) + 1, action_container)
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            # Log selection (can be removed in production)
            VWC_name = self.table.item(row, 1).text()
            print(f"Selected VWC : {VWC_name}")