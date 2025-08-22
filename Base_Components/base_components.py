"""
Base components to reduce code duplication across the application.
This module contains reusable classes and functions for efficient UI creation.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QToolButton, QMenu, QCheckBox, QFrame, QApplication,
    QStyle, QStyleOptionHeader, QSizePolicy, QAbstractItemView
)
from PyQt6.QtCore import Qt, QSize, QPoint, QEvent, QPropertyAnimation, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QCursor, QFont, QLinearGradient, QPainter, QPen, QBrush
from functools import partial
import weakref

from UI.Styles import AppStyles, AppColors, AppConstants
from UI.Icons import resource_path
import logging
import os

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
        hovered_section: The currently hovered section index (-1 if none)
    """
    def __init__(self, orientation, sortable_columns=None, parent=None):
        super().__init__(orientation, parent)
        self.sortable_columns = sortable_columns or set()
        self.hovered_section = -1  # Track hovered section
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        
        # Set default alignment to center for all sections
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        # Force consistent styling
        self.setStyleSheet(self._get_header_style())
        
        # Disable default sort indicators
        self.setSortIndicatorShown(False)
        
        # Enable mouse tracking for hover detection
        self.setMouseTracking(True)

    def _get_header_style(self):
        """Get consistent header styling"""
        return f"""
            QHeaderView::section {{
                background-color: {AppColors.HEADER_BG};
                color: {AppColors.TEXT_SECONDARY};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {AppColors.BORDER_COLOR};
                font-size: 12px;
                text-align: center;
                font-weight: bold;
            }}
            
            QHeaderView::section:hover {{
                background-color: {AppColors.BG_MEDIUM};
            }}
            
            /* Completely hide default sort indicators */
            QHeaderView::down-arrow, QHeaderView::up-arrow {{
                image: none;
                width: 0px;
                height: 0px;
                border: none;
                background: none;
                subcontrol-origin: content;
                subcontrol-position: right;
            }}
        """

    def mousePressEvent(self, event):
        logicalIndex = self.logicalIndexAt(event.pos())
        if logicalIndex in self.sortable_columns:
            super().mousePressEvent(event)
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        """Handle mouse move events to track hover state"""
        super().mouseMoveEvent(event)
        logical_index = self.logicalIndexAt(event.pos())
        
        # Only update hover state for sortable columns
        if logical_index in self.sortable_columns:
            if self.hovered_section != logical_index:
                self.hovered_section = logical_index
                self.update()  # Trigger repaint
        else:
            if self.hovered_section != -1:
                self.hovered_section = -1
                self.update()  # Trigger repaint

    def leaveEvent(self, event):
        """Handle mouse leave events"""
        super().leaveEvent(event)
        if self.hovered_section != -1:
            self.hovered_section = -1
            self.update()  # Trigger repaint

    def enterEvent(self, event):
        """Handle mouse enter events"""
        super().enterEvent(event)

    def paintEvent(self, event):
        """Custom paint event to ensure consistent rendering"""
        super().paintEvent(event)
        
        # Force repaint with our custom style
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw custom sort indicators for active sort and hover
        for i in range(self.count()):
            if i in self.sortable_columns:
                self._draw_custom_sort_indicator(painter, i)
        
        painter.end()

    def _draw_custom_sort_indicator(self, painter, section):
        """Draw custom sort indicator for active sort or hover"""
        is_sorted_section = (self.sortIndicatorSection() == section)
        is_hovered_section = (self.hovered_section == section)
        
        # Only draw if this section is sorted or hovered
        if not (is_sorted_section or is_hovered_section):
            return
            
        rect = self.sectionViewportPosition(section)
        section_rect = self.rect()
        section_rect.setLeft(rect)
        section_rect.setWidth(self.sectionSize(section))
        
        # Draw custom arrow
        arrow_size = 8
        arrow_x = section_rect.right() - arrow_size - 5
        arrow_y = section_rect.center().y()
        
        # Use different opacity for hover vs active sort
        if is_sorted_section:
            # Full opacity for active sort
            painter.setPen(QPen(QColor(AppColors.TEXT_SECONDARY), 2))
        else:
            # Reduced opacity for hover
            hover_color = QColor(AppColors.TEXT_SECONDARY)
            hover_color.setAlpha(128)  # 50% opacity
            painter.setPen(QPen(hover_color, 2))
        
        if is_sorted_section:
            # Draw actual sort direction for sorted columns
            if self.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder:
                # Draw up arrow
                painter.drawLine(arrow_x, arrow_y + 3, arrow_x + 4, arrow_y - 3)
                painter.drawLine(arrow_x + 4, arrow_y - 3, arrow_x + 8, arrow_y + 3)
            else:
                # Draw down arrow
                painter.drawLine(arrow_x, arrow_y - 3, arrow_x + 4, arrow_y + 3)
                painter.drawLine(arrow_x + 4, arrow_y + 3, arrow_x + 8, arrow_y - 3)
        else:
            # Draw neutral/default up arrow for hover (indicating sortable)
            painter.drawLine(arrow_x, arrow_y + 3, arrow_x + 4, arrow_y - 3)
            painter.drawLine(arrow_x + 4, arrow_y - 3, arrow_x + 8, arrow_y + 3)
            
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
        title_label.setStyleSheet(AppStyles.BASE_TITLE_STYLE)

        self.items_count = QLabel("0 items")
        self.items_count.setStyleSheet(AppStyles.BASE_COUNT_STYLE)
        self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        header_layout.addWidget(title_label)
        header_layout.addWidget(self.items_count)
        header_layout.addStretch()

        return header_layout
    
    
    def _create_table(self, headers, sortable_columns=None):
        """Create and configure the table with proper column resizing"""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        # Use custom header for selective header-based sorting
        custom_header = CustomHeader(Qt.Orientation.Horizontal, sortable_columns, table)
        table.setHorizontalHeader(custom_header)
        table.setSortingEnabled(True)

        # Apply enhanced styling with platform overrides
        table.setStyleSheet(AppStyles.TABLE_STYLE)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Configure appearance with explicit settings
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setVisible(False)
        
        # Force consistent selection behavior
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Configure resizable columns
        self._configure_table_resizing(table, headers)

        # Connect cell click signal
        table.cellClicked.connect(self.handle_row_click)
        
        return table

    def _configure_table_resizing(self, table, headers):
        """Configure table columns for proper resizing with minimal checkbox width"""
        header = table.horizontalHeader()
        
        header.setStretchLastSection(False)
        header.setSectionsMovable(False)
        header.setSectionsClickable(True)
        header.setMinimumSectionSize(20)  # Reduced minimum
        header.setDefaultSectionSize(120)
        
        for i in range(len(headers)):
            if i == 0:  # Checkbox column
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                table.setColumnWidth(i, 20)  # Minimal width for checkbox
            elif i == len(headers) - 1:  # Action column
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                table.setColumnWidth(i, 40)
            else:  # All content columns
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        if len(headers) > 2:
            stretch_column = len(headers) - 2
            header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)

    def eventFilter(self, obj, event):
        """Handle events like clicks outside the table"""
        if event.type() == event.Type.MouseButtonPress:
            pos = event.pos()
            if hasattr(self, 'table') and not self.table.geometry().contains(pos):
                self.table.clearSelection()
        return super().eventFilter(obj, event)

    def _create_checkbox_container(self, row, item_name):
        """Create a container for the checkbox with zero padding and margins"""
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        container.setContentsMargins(0, 0, 0, 0)
        container.setAttribute(Qt.WidgetAttribute.WA_LayoutUsesWidgetRect, True)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        checkbox = self._create_checkbox(row, item_name)
        layout.addWidget(checkbox)
        
        # Force exact size to eliminate any extra space
        container.setFixedSize(20, 20)
        
        self._item_widgets[f"checkbox_{row}_{item_name}"] = container
        return container
      
    def _create_checkbox(self, row, item_name):
        """Create a checkbox with proper icon loading and zero margins"""
        checkbox = QCheckBox()
        
        # Get resolved icon paths using the resource_path function
        unchecked_icon_path = resource_path("Icons/check_box_unchecked.svg")
        checked_icon_path = resource_path("Icons/check_box_checked.svg")
        
        # Create stylesheet with resolved paths
        checkbox_style = f"""
            QCheckBox {{
                margin: 0px;
                padding: 0px;
                spacing: 0px;
                background: transparent;
                border: none;
                outline: none;
                width: 16px;
                height: 16px;
                max-width: 16px;
                max-height: 16px;
                min-width: 16px;
                min-height: 16px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: none;
                background: transparent;
                margin: 0px;
                padding: 0px;
                spacing: 0px;
                subcontrol-position: center;
                subcontrol-origin: content;
            }}
            QCheckBox::indicator:unchecked {{
                image: url({unchecked_icon_path.replace(os.sep, '/')});
            }}
            QCheckBox::indicator:checked {{
                image: url({checked_icon_path.replace(os.sep, '/')});
            }}
            QCheckBox::indicator:hover {{
                opacity: 0.8;
            }}
        """
        
        checkbox.setStyleSheet(checkbox_style)
        checkbox.setFixedSize(16, 16)
        checkbox.stateChanged.connect(partial(self._handle_checkbox_change, item_name=item_name))
        return checkbox

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

    # def _create_select_all_checkbox(self):
    #     """Create the select-all checkbox for the header using the same SVG icon as row checkboxes"""
    #     checkbox = QCheckBox()
    #     checkbox.setStyleSheet(AppStyles.BASE_CHECKBOX_STYLE)
    #     checkbox.stateChanged.connect(self._handle_select_all)
    #     self.select_all_checkbox = checkbox
    #     return checkbox

    def _create_select_all_checkbox(self):
        """Create the select-all checkbox for the header using resolved icon paths"""
        checkbox = QCheckBox()
        
        # Get resolved icon paths
        unchecked_icon_path = resource_path("Icons/check_box_unchecked.svg")
        checked_icon_path = resource_path("Icons/check_box_checked.svg")
        
        # Apply consistent styling with resolved paths
        select_all_style = f"""
            QCheckBox {{
                margin: 0px;
                padding: 0px;
                spacing: 0px;
                background: transparent;
                border: none;
                outline: none;
                width: 16px;
                height: 16px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: none;
                background: transparent;
                margin: 0px;
                padding: 0px;
                subcontrol-position: center;
                subcontrol-origin: content;
            }}
            QCheckBox::indicator:unchecked {{
                image: url({unchecked_icon_path.replace(os.sep, '/')});
            }}
            QCheckBox::indicator:checked {{
                image: url({checked_icon_path.replace(os.sep, '/')});
            }}
            QCheckBox::indicator:hover {{
                opacity: 0.8;
            }}
        """
        
        checkbox.setStyleSheet(select_all_style)
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

        # Use custom SVG icon instead of text
        icon = resource_path("Icons/Moreaction_Button.svg")
        button.setIcon(QIcon(icon))
        button.setIconSize(QSize(AppConstants.SIZES["ICON_SIZE"], AppConstants.SIZES["ICON_SIZE"]))

        # Remove text and change to icon-only style
        button.setText("")
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        button.setFixedWidth(30)
        button.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Create menu
        menu = QMenu(button)
        menu.setStyleSheet(AppStyles.MENU_STYLE)

        # Connect signals to change row appearance when menu opens/closes
        menu.aboutToShow.connect(lambda: self._highlight_active_row(row, True))
        menu.aboutToHide.connect(lambda: self._highlight_active_row(row, False))

        actions  = []
        # Only show "View Logs" for pods
        if self.resource_type == "pods":
            actions.append({"text": "View Logs", "icon": "Icons/logs.png", "dangerous": False})
            actions.append({"text": "SSH", "icon": "Icons/terminal.png", "dangerous": False})

        # Add default actions
        actions.extend([
            {"text": "Edit", "icon": "Icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "Icons/delete.png", "dangerous": True}
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

    def _highlight_active_row(self, row, is_active):
        """Highlight the row when its menu is active"""
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                if is_active:
                    item.setBackground(QColor(AppColors.ACCENT_BLUE + "22"))  # 13% opacity
                else:
                    item.setBackground(QColor("transparent"))

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
        content_widget.setStyleSheet(AppStyles.EMPTY_STATE_STYLE)
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


class StatusLabel(QWidget):
    """
    Shared widget that displays a status with consistent styling and background handling.
    This component replaces all duplicate StatusLabel classes across resource pages.
    
    Features:
    - Consistent styling across all resource pages
    - Clickable functionality with signal emission
    - Transparent background for table integration
    - Customizable color support
    """
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
        else:
            # Use default styling from AppColors
            self.label.setStyleSheet("background-color: transparent;")
        
        # Add label to layout
        layout.addWidget(self.label)
        
        # Make sure this widget has a transparent background
        self.setStyleSheet("background-color: transparent;")
    
    def setText(self, text):
        """Update the status text"""
        self.label.setText(text)
    
    def setColor(self, color):
        """Update the status color"""
        if color:
            self.label.setStyleSheet(f"color: {QColor(color).name()}; background-color: transparent;")
        else:
            self.label.setStyleSheet("background-color: transparent;")
    
    def mousePressEvent(self, event):
        """Emit clicked signal when widget is clicked"""
        self.clicked.emit()
        super().mousePressEvent(event)
