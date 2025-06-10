"""
Base components to reduce code duplication across the application.
This module contains reusable classes and functions for efficient UI creation.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QLabel, QHeaderView, QToolButton, QMenu, QCheckBox, QFrame, QApplication, 
    QStyle, QStyleOptionHeader, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QPoint, QEvent, QPropertyAnimation, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QCursor, QFont, QLinearGradient, QPainter, QPen, QBrush
from functools import partial
import weakref

# Centralized styles to maintain consistency and reduce duplication
STYLES = {
    "table": """
        QTableWidget {
            background-color: #1e1e1e;
            border: none;
            gridline-color: #2d2d2d;
            outline: none;
        }
        QTableWidget::item {
            padding: 8px;
            border: none;
            outline: none;
        }
        QTableWidget::item:hover {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
        }
        QTableWidget::item:selected {
            background-color: rgba(33, 150, 243, 0.2);
            border: none;
        }
        QHeaderView::section {
            background-color: #252525;
            color: #888888;
            padding: 8px;
            border: none;
            border-bottom: 1px solid #2d2d2d;
            font-size: 12px;
            text-align: center;
        }
    """,
    "title": """
        font-size: 20px;
        font-weight: bold;
        color: #ffffff;
    """,
    "count": """
        color: #9ca3af;
        font-size: 12px;
        margin-left: 8px;
        font-family: 'Segoe UI';
    """,
    "checkbox": """
        QCheckBox {
            spacing: 5px;
            background: transparent;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid #666666;
            border-radius: 3px;
            background: transparent;
        }
        QCheckBox::indicator:checked {
            background-color: #0095ff;
            border-color: #0095ff;
        }
        QCheckBox::indicator:hover {
            border-color: #888888;
        }
    """,
    "header_checkbox": """
        QCheckBox {
            spacing: 5px;
            background-color: #252525;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid #666666;
            border-radius: 3px;
            background: transparent;
        }
        QCheckBox::indicator:checked {
            background-color: #0095ff;
            border-color: #0095ff;
        }
        QCheckBox::indicator:hover {
            border-color: #888888;
        }
    """,
    "action_button": """
        QToolButton {
            color: #888888;
            font-size: 18px;
            background: transparent;
            padding: 2px;
            margin: 0;
            border: none;
            font-weight: bold;
        }
        QToolButton:hover {
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            color: #ffffff;
        }
        QToolButton::menu-indicator {
            image: none;
        }
    """,
    "menu": """
        QMenu {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            padding: 4px;
        }
        QMenu::item {
            color: #ffffff;
            padding: 8px 24px 8px 36px;
            border-radius: 4px;
            font-size: 13px;
        }
        QMenu::item:selected {
            background-color: rgba(33, 150, 243, 0.2);
            color: #ffffff;
        }
        QMenu::item[dangerous="true"] {
            color: #ff4444;
        }
        QMenu::item[dangerous="true"]:selected {
            background-color: rgba(255, 68, 68, 0.1);
        }
    """,
    "empty_state": """
        background-color: #1e1e1e;
        color: #aaaaaa;
        border-radius: 8px;
        border: 1px solid #333333;
    """
}

class SortableTableWidgetItem(QTableWidgetItem):
    """
    Customized QTableWidgetItem that enables sorting based on a numeric value.
    
    Attributes:
        value: The numeric value used for sorting (allows proper sorting of data)
    """
    def __init__(self, text, value=None):
        super().__init__(str(text))
        self.value = value
        
    def __lt__(self, other):
        if isinstance(other, SortableTableWidgetItem) and self.value is not None and other.value is not None:
            return self.value < other.value
        return super().__lt__(other)

class CustomHeader(QHeaderView):
    """
    Custom table header that enables sorting only for specific columns
    and shows a hover sort indicator.
    
    Attributes:
        sortable_columns: A set containing column indices that can be sorted
    """
    def __init__(self, orientation, sortable_columns=None, parent=None):
        super().__init__(orientation, parent)
        self.sortable_columns = sortable_columns or set()
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        
        # Set default alignment to center for all sections
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        logicalIndex = self.logicalIndexAt(event.pos())
        if logicalIndex in self.sortable_columns:
            super().mousePressEvent(event)
        else:
            event.ignore()
    
    def paintSection(self, painter, rect, logicalIndex):
        option = QStyleOptionHeader()
        self.initStyleOption(option)
        option.rect = rect
        option.section = logicalIndex
        
        # Retrieve header text from the model and set it
        header_text = self.model().headerData(logicalIndex, self.orientation(), Qt.ItemDataRole.DisplayRole)
        option.text = str(header_text) if header_text is not None else ""
        
        # Set text alignment to center
        option.textAlignment = Qt.AlignmentFlag.AlignCenter

        if logicalIndex in self.sortable_columns:
            mouse_pos = QCursor.pos()
            local_mouse = self.mapFromGlobal(mouse_pos)
            if rect.contains(local_mouse):
                option.state |= QStyle.StateFlag.State_MouseOver
                option.sortIndicator = QStyleOptionHeader.SortIndicator.SortDown
                option.state |= QStyle.StateFlag.State_Sunken
            else:
                option.state &= ~QStyle.StateFlag.State_MouseOver
        else:
            option.state &= ~QStyle.StateFlag.State_MouseOver
        
        self.style().drawControl(QStyle.ControlElement.CE_Header, option, painter, self)

class BaseTablePage(QWidget):
    """
    Base class for table-based pages with common functionality.
    Implements table creation, checkbox management, and action menu creation.
    
    Attributes:
        selected_items: A set tracking selected item names
        select_all_checkbox: Reference to the select-all checkbox
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_items = set()
        self.select_all_checkbox = None
        self._setup_refs()
        
    def _setup_refs(self):
        """Set up weak references to avoid memory leaks"""
        self._item_widgets = weakref.WeakValueDictionary()
    
    def setup_ui(self, title, headers, sortable_columns=None):
        """Set up the basic UI structure with title, table, and headers"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header section with title and count
        header_layout = self._create_header(title)
        layout.addLayout(header_layout)
        
        # Create table
        self.table = self._create_table(headers, sortable_columns)
        layout.addWidget(self.table)
        
        # Create and set the select-all checkbox in header
        select_all_checkbox = self._create_select_all_checkbox()
        self._set_header_widget(0, select_all_checkbox)
        
        # Install event filter and override mouse events
        self.installEventFilter(self)
        
        return layout
    
    def _create_header(self, title):
        """Create header with title and item count"""
        header_layout = QHBoxLayout()
        
        title_label = QLabel(title)
        title_label.setStyleSheet(STYLES["title"])
        
        self.items_count = QLabel("0 items")
        self.items_count.setStyleSheet(STYLES["count"])
        self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(self.items_count)
        header_layout.addStretch()
        
        return header_layout
    
    def _create_table(self, headers, sortable_columns=None):
        """Create and configure the table with headers and sorting"""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        # Use custom header for selective header-based sorting
        custom_header = CustomHeader(Qt.Orientation.Horizontal, sortable_columns, table)
        table.setHorizontalHeader(custom_header)
        table.setSortingEnabled(True)
        
        # Apply styling
        table.setStyleSheet(STYLES["table"])
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Configure appearance
        table.setShowGrid(True)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setVisible(False)
        
        # Set first column (checkbox) as fixed width
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, 40)
        
        # Connect cell click signal
        table.cellClicked.connect(self.handle_row_click)
        
        return table
    
    def eventFilter(self, obj, event):
        """Handle events like clicks outside the table"""
        if event.type() == event.Type.MouseButtonPress:
            pos = event.pos()
            if hasattr(self, 'table') and not self.table.geometry().contains(pos):
                self.table.clearSelection()
        return super().eventFilter(obj, event)
    
    def _create_checkbox(self, row, item_name):
        """Create a checkbox for row selection"""
        checkbox = QCheckBox()
        checkbox.setStyleSheet(STYLES["checkbox"])
        checkbox.stateChanged.connect(partial(self._handle_checkbox_change, item_name=item_name))
        return checkbox

    def _create_checkbox_container(self, row, item_name):
        """Create a container for the checkbox"""
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox = self._create_checkbox(row, item_name)
        layout.addWidget(checkbox)
        self._item_widgets[f"checkbox_{row}_{item_name}"] = container
        return container

    def _handle_checkbox_change(self, state, item_name):
        """Handle checkbox state changes"""
        if state == Qt.CheckState.Checked.value:
            self.selected_items.add(item_name)
        else:
            self.selected_items.discard(item_name)

            # If any checkbox is unchecked, uncheck the select-all checkbox
            if self.select_all_checkbox is not None and self.select_all_checkbox.isChecked():
                # Block signals to prevent infinite recursion
                self.select_all_checkbox.blockSignals(True)
                self.select_all_checkbox.setChecked(False)
                self.select_all_checkbox.blockSignals(False)

    def _create_select_all_checkbox(self):
        """Create the select-all checkbox for the header"""
        checkbox = QCheckBox()
        checkbox.setStyleSheet(STYLES["header_checkbox"])
        checkbox.stateChanged.connect(self._handle_select_all)
        self.select_all_checkbox = checkbox
        return checkbox

    def _handle_select_all(self, state):
        """Handle select-all checkbox state changes"""
        for row in range(self.table.rowCount()):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                for child in checkbox_container.children():
                    if isinstance(child, QCheckBox):
                        child.setChecked(state == Qt.CheckState.Checked.value)
                        break

    def _set_header_widget(self, col, widget):
        """Place a widget in a table header cell"""
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(col, 40)
        self.table.setHorizontalHeaderItem(col, QTableWidgetItem(""))
        
        container = QWidget()
        container.setStyleSheet("background-color: #252525;")
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(widget)
        container.setFixedHeight(header.height())
        container.setParent(header)
        container.setGeometry(header.sectionPosition(col), 0, header.sectionSize(col), header.height())
        container.show()
        self._item_widgets["header_widget"] = container
    
    def _create_action_button(self, row, resource_name=None, resource_namespace=None):
        """Create an action button with menu"""
        button = QToolButton()
        button.setText("⋮")
        button.setFixedWidth(30)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setStyleSheet(STYLES["action_button"])
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Create menu
        menu = QMenu(button)
        menu.setStyleSheet(STYLES["menu"])
        
        actions  = []
        # Only show "View Logs" for pods
        if self.resource_type == "pods":
            actions.append({"text": "View Logs", "icon": "icons/logs.png", "dangerous": False})
            actions.append({"text": "SSH", "icon": "icons/terminal.png", "dangerous": False})
        
        # Add default actions
        actions.extend([
            {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True}
        ])
        
        
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
        self._item_widgets[f"action_button_{row}"] = button
        return button
    
    def _handle_action(self, action, row):
        """Base implementation for handling action button clicks"""
        item_name = self.table.item(row, 1).text() if self.table.item(row, 1) else f"Item {row}"
        
    
    def _create_action_container(self, row, button):
        """Create a container for an action button"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(button)
        container.setStyleSheet("background-color: transparent;")
        return container
        
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            
    def create_empty_state(self, message, description=None):
        """Create a standardized empty state widget"""
        # Create a container for the empty state
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the content container with proper sizing
        content_widget = QWidget()
        content_widget.setStyleSheet(STYLES["empty_state"])
        content_widget.setFixedWidth(500)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.setContentsMargins(30, 40, 30, 40)
        
        # Main message
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        content_layout.addWidget(message_label)
        
        # Description (optional)
        if description:
            desc_label = QLabel(description)
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_label.setStyleSheet("font-size: 14px; margin-top: 5px; color: #888888;")
            desc_label.setWordWrap(True)
            content_layout.addWidget(desc_label)
        
        # Add content to the main empty layout
        empty_layout.addWidget(content_widget, 0, Qt.AlignmentFlag.AlignCenter)
        
        return empty_widget