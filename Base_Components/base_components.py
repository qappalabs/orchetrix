"""
Base components to reduce code duplication across the application.
This module contains reusable classes and functions for efficient UI creation.
"""


from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QFrame,
    QSizePolicy, QCheckBox, QToolButton, QMenu,
    QGraphicsDropShadowEffect, QAbstractScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QPoint, QEvent
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QBrush, QPen
from PyQt6 import sip
import logging
from functools import partial
import weakref

from UI.Styles import AppColors, AppConstants
from UI.Icons import Icons
from UI.ThemeAwarePage import ThemeAwareMixin
from UI.ThemeManager import get_theme_manager
import Styles.BaseTablePageStyles as BaseTablePageStyles
import Styles.BaseComponentsStyles as BaseComponentsStyles
import Styles.BaseDetailSectionStyles as BaseDetailSectionStyles

__all__ = [
    'SortableTableWidgetItem',
    'StatusLabel',
    'CustomHeader',
    'BaseTablePage'
]


class SortableTableWidgetItem(QTableWidgetItem):
    """
    Customized QTableWidgetItem that enables sorting based on a numeric value.

    Attributes:
        value: The numeric value used for sorting (allows proper sorting of data)
    """

    def __init__(self, text, value=None):

        super().__init__(text)
        self.value = value

    def __lt__(self, other):

        if self.value is not None and other.value is not None:
            return self.value < other.value
        return super().__lt__(other)


class StatusLabel(QWidget):
    """Status label widget with colored badge."""

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

        # Set style: either explicit color or mapped status type.
        # Remember the explicit color so theme refresh can reapply it instead of
        # remapping from status text (which would discard custom badge colors).
        self._custom_color = color
        if color:
            self.label.setStyleSheet(
                BaseDetailSectionStyles.get_custom_badge_style(color, is_small=True))
        else:
            status_type = self._map_status_to_type(status_text)
            self.label.setStyleSheet(
                BaseDetailSectionStyles.get_status_badge_style(status_type, is_small=True))

        # Add label to layout
        layout.addWidget(self.label)

        # Make sure this widget has a transparent background
        self.setStyleSheet("background: transparent; border: none;")

    def _map_status_to_type(self, status):
        """Map Kubernetes status strings to theme status types."""
        if not status:
            return 'default'

        status = str(status).lower()

        # Error patterns (checked first so values like 'notready' / 'unhealthy'
        # are not swallowed by the 'ready' / 'healthy' success substrings)
        if any(s in status for s in ['failed', 'error', 'crash', 'notready', 'unhealthy', 'evicted', 'backoff', 'imagepullbackoff', 'errimagepull']):
            return 'error'

        # Warning patterns
        if any(s in status for s in ['pending', 'waiting', 'terminating', 'creating', 'starting', 'unknown', 'containercreating']):
            return 'warning'

        # Success patterns
        if any(s in status for s in ['running', 'ready', 'active', 'succeeded', 'completed', 'healthy', 'bound']):
            return 'success'

        return 'default'

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        """Ensure the parent table knows we're being hovered to trigger row highlight."""
        if sip.isdeleted(self):
            return
            
        super().enterEvent(event)
        
        # Guard against deleted parent or no parent
        parent_widget = self.parent()
        if not parent_widget or sip.isdeleted(parent_widget):
            return

        # QTableWidget's viewport is the actual parent of cell widgets
        table = None
        current = parent_widget
        while current and not sip.isdeleted(current):
            if isinstance(current, QTableWidget):
                table = current
                break
            current = current.parent()
        
        if table and not sip.isdeleted(table):
            # Trigger the table's highlight logic via the page if accessible
            page = table.parent()
            while page and not sip.isdeleted(page) and not hasattr(page, '_highlight_row'):
                page = page.parent()
            
            if page and not sip.isdeleted(page) and hasattr(page, '_highlight_row'):
                # Map our center to table coordinates to find the row
                try:
                    # Map position relative to the table's viewport
                    pos = table.viewport().mapFromGlobal(self.mapToGlobal(self.rect().center()))
                    row = table.rowAt(pos.y())
                    if row != -1:
                        page._highlight_row(row)
                except (RuntimeError, AttributeError):
                    pass


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

        # Set default alignment to left/center for all sections
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        # Force consistent styling
        self.setStyleSheet(self._get_header_style())

        # Disable default sort indicators
        self.setSortIndicatorShown(False)

        # Enable mouse tracking for hover detection
        self.setMouseTracking(True)

    def _get_header_style(self):
        """Get theme - aware header stylesheet."""
        # Use centralized styling from BaseTablePageStyles if available
        # But CustomHeader has specific requirements for rounding etc.
        return BaseTablePageStyles.get_table_header_style()

    def mousePressEvent(self, event):
        """Handle mouse press events for sortable columns only.

        Column resize drags (initiated near a section boundary) are always
        forwarded to the base class so that Interactive-mode columns can be
        resized regardless of whether they are sortable.
        """
        # Check whether the click lands inside a section-edge resize zone.
        # QHeaderView uses a ±4 px zone around each section boundary for resize.
        RESIZE_ZONE = 4
        pos_x = event.pos().x()
        in_resize_zone = False
        for i in range(self.count()):
            if self.isSectionHidden(i):
                continue
            # Left edge of the section in viewport coordinates
            sec_pos = self.sectionViewportPosition(i)
            sec_end = sec_pos + self.sectionSize(i)
            # Check if click is within the resize handle at the RIGHT edge of this section
            # (or the LEFT edge of the next visible section)
            if abs(pos_x - sec_end) <= RESIZE_ZONE:
                in_resize_zone = True
                break

        logicalIndex = self.logicalIndexAt(event.pos())
        if in_resize_zone or logicalIndex in self.sortable_columns:
            super().mousePressEvent(event)
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        """Handle mouse move events for hover effects."""
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
        """Handle mouse leave events."""
        super().leaveEvent(event)
        if self.hovered_section != -1:
            self.hovered_section = -1
            self.update()  # Trigger repaint

    def enterEvent(self, event):
        """Handle mouse enter events."""
        super().enterEvent(event)

    def set_custom_widget(self, section, widget):
        if not hasattr(self, '_custom_widgets'):
            self._custom_widgets = {}
        widget.setParent(self.viewport())
        self._custom_widgets[section] = widget
        widget.show()

    def paintEvent(self, event):
        """Custom paint event for sort indicators and custom widgets."""
        super().paintEvent(event)
        
        # Synchronize custom widgets to scroll precisely frame-by-frame
        if hasattr(self, '_custom_widgets'):
            for section, widget in self._custom_widgets.items():
                if not sip.isdeleted(widget):
                    if self.isSectionHidden(section):
                        widget.hide()
                    else:
                        x = self.sectionViewportPosition(section)
                        if x + self.sectionSize(section) > 0 and x < self.viewport().width():
                            widget.setGeometry(x, 0, self.sectionSize(section), self.height())
                            widget.show()
                        else:
                            widget.hide()

        # Force repaint with our custom style
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw custom sort indicators for active sort and hover
        for i in range(self.count()):
            if i in self.sortable_columns:
                self._draw_custom_sort_indicator(painter, i)

        painter.end()

    def _draw_custom_sort_indicator(self, painter, section):
        """Draw custom sort indicator for a section."""
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

        # For header row indicators, use the theme-defined light text color
        theme = get_theme_manager().get_current_theme()
        text_color = QColor(theme.colors.TEXT_LIGHT)

        # Use different opacity for hover vs active sort
        if is_sorted_section:
            # Full opacity for active sort
            painter.setPen(QPen(text_color, 2))
        else:
            # Reduced opacity for hover
            hover_color = QColor(text_color)
            hover_color.setAlpha(128)  # 50% opacity
            painter.setPen(QPen(hover_color, 2))

        if is_sorted_section:
            # Draw actual sort direction for sorted columns
            if self.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder:
                # Draw up arrow
                painter.drawLine(arrow_x, arrow_y + 3,
                                 arrow_x + 4, arrow_y - 3)
                painter.drawLine(arrow_x + 4, arrow_y - 3,
                                 arrow_x + 8, arrow_y + 3)
            else:
                # Draw down arrow
                painter.drawLine(arrow_x, arrow_y - 3,
                                 arrow_x + 4, arrow_y + 3)
                painter.drawLine(arrow_x + 4, arrow_y + 3,
                                 arrow_x + 8, arrow_y - 3)
        else:
            # Draw neutral / default up arrow for hover (indicating sortable)
            painter.drawLine(arrow_x, arrow_y + 3, arrow_x + 4, arrow_y - 3)
            painter.drawLine(arrow_x + 4, arrow_y - 3,
                             arrow_x + 8, arrow_y + 3)


class BaseTablePage(ThemeAwareMixin, QWidget):
    """
    Base class for table - based pages with common functionality.
    Implements table creation, checkbox management, and action menu creation.

    Attributes:
        selected_items: A set tracking selected item names
        select_all_checkbox: Reference to the select - all checkbox
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.selected_items = set()
        self.select_all_checkbox = None
        self._setup_refs()
        self._load_action_button_icon()  # Load theme - aware icon once for performance

    def _setup_refs(self):
        """Setup weak references for widgets."""
        self._item_widgets = weakref.WeakValueDictionary()

    def _load_action_button_icon(self):
        """Load theme - aware action button icon."""
        theme_name = get_theme_manager().get_current_theme_name() or "Dark"
        self.action_button_icon = Icons.get_theme_icon(
            "Moreaction_Button.svg", theme_name)

    def setup_ui(self, title, headers, sortable_columns=None):
        """Setup the UI with table and headers."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header section with title and count
        header_layout = self._create_header(title)
        layout.addLayout(header_layout)

        # Create table container (The Card)
        self.table_container = QFrame()
        self.table_container.setObjectName("table_container")
        self.table_container.setStyleSheet(
            BaseTablePageStyles.get_table_container_style())

        # Add Shadow Effect (matching info card style)
        shadow = QGraphicsDropShadowEffect(self.table_container)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.table_container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.table_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Create table
        self.table = self._create_table(headers, sortable_columns)
        container_layout.addWidget(self.table)

        layout.addWidget(self.table_container)
        layout.addStretch(1)  # Push the table card to the top

        # Create and set the select - all checkbox in header
        select_all_checkbox = self._create_select_all_checkbox()
        self._set_header_widget(0, select_all_checkbox)

        # Install event filter and override mouse events
        self.installEventFilter(self)

        return layout

    def _update_table_height(self):
        """Update table height - deferring to native QSizePolicy for flex layouts."""
        pass

    def _create_header(self, title):
        """Create header layout with title and count."""
        header_layout = QHBoxLayout()

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(BaseTablePageStyles.get_title_style())

        self.items_count = QLabel("0 items")
        self.items_count.setStyleSheet(BaseTablePageStyles.get_count_style())
        self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.items_count)
        header_layout.addStretch()

        return header_layout

    def _create_table(self, headers, sortable_columns=None):
        """Create and configure the table widget."""
        table = QTableWidget()
        # Ensure the table only takes as much space as it needs for its content
        table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        # Use custom header for selective header - based sorting
        custom_header = CustomHeader(
            Qt.Orientation.Horizontal, sortable_columns, table)
        table.setHorizontalHeader(custom_header)
        table.setSortingEnabled(True)

        # Apply enhanced styling with platform overrides
        table.setStyleSheet(BaseTablePageStyles.get_table_style())
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setMouseTracking(True)  # Enable tracking for full-row hover
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Configure appearance with explicit settings
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(42)  # Enough height for badge descenders


        # Force consistent selection behavior
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)

        # Configure resizable columns
        self._configure_table_resizing(table, headers)

        # Connect signals
        table.cellClicked.connect(self.handle_row_click)
        table.itemEntered.connect(self._handle_item_entered)
        # Also track mouse moves on the viewport for cells with widgets
        table.viewport().installEventFilter(self)

        return table

    def _configure_table_resizing(self, table, headers):
        """Configure table column resizing behavior."""
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
                header.setSectionResizeMode(
                    i, QHeaderView.ResizeMode.Interactive)

        if len(headers) > 2:
            stretch_column = len(headers) - 2
            header.setSectionResizeMode(
                stretch_column, QHeaderView.ResizeMode.Stretch)

    def eventFilter(self, obj, event):
        """Filter events to handle clicks outside table and robust row hover."""
        if event.type() == QEvent.Type.MouseButtonPress:
            if hasattr(self, 'table') and self.table and not sip.isdeleted(self.table):
                # event.pos() is relative to the filtered object (the page or the
                # viewport), while the table lives inside table_container, so a
                # geometry() comparison would mix coordinate spaces. Map through
                # global coordinates into the table's own space instead.
                local_pos = self.table.mapFromGlobal(event.globalPosition().toPoint())
                if not self.table.rect().contains(local_pos):
                    self.table.clearSelection()
        
        # Robust row hover detection for cells with widgets
        elif hasattr(self, 'table') and obj == self.table.viewport():
            if event.type() == QEvent.Type.MouseMove:
                row = self.table.rowAt(event.pos().y())
                if row != -1:
                    self._highlight_row(row)
                    self.table.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    self._clear_hover_highlight()
            elif event.type() == QEvent.Type.Leave:
                self._clear_hover_highlight()
                
        return super().eventFilter(obj, event)

    def _clear_hover_highlight(self):
        """Clear the current hover highlight."""
        if hasattr(self, '_hovered_row') and self._hovered_row != -1:
            self._set_row_highlight(self._hovered_row, False)
            self._hovered_row = -1
            if hasattr(self, 'table') and self.table:
                self.table.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def _create_checkbox_container(self, row, item_name):
        """Create container widget for checkbox."""
        container = QWidget()
        container.setStyleSheet(
            BaseComponentsStyles.CONTAINER_TRANSPARENT_STYLE)
        container.setContentsMargins(0, 0, 0, 0)
        container.setAttribute(
            Qt.WidgetAttribute.WA_LayoutUsesWidgetRect, True)
        container.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True)
        container.setStyleSheet("background: transparent; border: none;")

        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        checkbox = self._create_checkbox(row, item_name)
        layout.addWidget(checkbox)

        # Use a slightly larger container to ensure the 14x14 indicator + border is never clipped
        container.setFixedSize(22, 22)

        self._item_widgets[f"checkbox_{row}_{item_name}"] = container
        return container

    def _create_checkbox(self, row, item_name):
        """Create checkbox widget."""
        checkbox = QCheckBox()

        # Apply theme-aware checkbox styling
        checkbox.setStyleSheet(BaseTablePageStyles.get_checkbox_style())
        checkbox.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        checkbox.stateChanged.connect(
            partial(self._handle_checkbox_change, item_name=item_name))
        return checkbox

    def _handle_checkbox_change(self, state, item_name):
        """Handle checkbox state changes."""
        if state == Qt.CheckState.Checked.value:
            self.selected_items.add(item_name)
        else:
            self.selected_items.discard(item_name)

            # If any checkbox is unchecked, uncheck the select - all checkbox
            if self.select_all_checkbox is not None and self.select_all_checkbox.isChecked():
                # Block signals to prevent infinite recursion
                self.select_all_checkbox.blockSignals(True)
                self.select_all_checkbox.setChecked(False)
                self.select_all_checkbox.blockSignals(False)

    def _create_select_all_checkbox(self):
        """Create select - all checkbox for header."""
        checkbox = QCheckBox()

        # Apply theme - aware checkbox styling
        checkbox.setStyleSheet(BaseTablePageStyles.get_checkbox_style())
        checkbox.stateChanged.connect(self._handle_select_all)
        self.select_all_checkbox = checkbox
        return checkbox

    def _handle_select_all(self, state):
        """Handle select - all checkbox state changes."""
        if not hasattr(self, 'table') or self.table is None or sip.isdeleted(self.table):
            return

        for row in range(self.table.rowCount()):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container and not sip.isdeleted(checkbox_container):
                for child in checkbox_container.children():
                    if not sip.isdeleted(child) and isinstance(child, QCheckBox):
                        child.setChecked(state == Qt.CheckState.Checked.value)
                        break

    def _set_header_widget(self, col, widget):
        """Set widget in table header."""
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(col, 40)
        self.table.setHorizontalHeaderItem(col, QTableWidgetItem(""))

        container = QWidget()
        container.setStyleSheet(BaseTablePageStyles.get_header_widget_style())
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(widget)
        container.setFixedHeight(header.height())
        container.setParent(header)
        container.setGeometry(header.sectionPosition(
            col), 0, header.sectionSize(col), header.height())
        container.show()
        self._item_widgets["header_widget"] = container

    def _create_action_button(self, row, resource_name=None, resource_namespace=None):
        """Create action button for table row."""
        button = QToolButton()

        # Use pre - loaded theme - aware icon (loaded once, reused for all rows)
        button.setIcon(self.action_button_icon)
        button.setIconSize(
            QSize(AppConstants.SIZES["ICON_SIZE"], AppConstants.SIZES["ICON_SIZE"]))

        # Remove text and change to icon - only style
        button.setText("")
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        button.setFixedWidth(30)
        button.setStyleSheet(BaseTablePageStyles.get_action_button_style())
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Create menu using virtual method (allows child classes to override)
        # This follows PyQt6 best practices for extensibility
        self._create_action_menu(button, row)
        self._item_widgets[f"action_button_{row}"] = button
        return button

    def _create_action_menu(self, button, row):
        """
        Create and attach menu to action button.
        Virtual method - child classes can override to customize menus.
        """
        if sip.isdeleted(button):
            return None

        # Create menu with button as parent for proper Qt ownership
        menu = QMenu(button)
        menu.setStyleSheet(BaseTablePageStyles.get_menu_style())

        # Connect signals using functools.partial (better than lambda for PyQt6)
        menu.aboutToShow.connect(partial(self._highlight_active_row, row, True))
        menu.aboutToHide.connect(partial(self._highlight_active_row, row, False))

        # Build actions list
        actions = self._get_resource_actions()

        # Add actions to menu
        for action_info in actions:
            action = menu.addAction(action_info["text"])
            if "icon" in action_info:
                try:
                    theme_name = get_theme_manager().get_current_theme_name() or "Dark"
                    action.setIcon(Icons.get_theme_icon_by_id(action_info["icon"], theme_name))
                except Exception:
                    pass  # Icon loading failure is not critical
            
            if action_info.get("dangerous", False):
                action.setProperty("dangerous", True)
            
            # Use functools.partial for proper signal handling
            action.triggered.connect(partial(self._handle_action, action_info["text"], row))

        # Attach menu to button
        button.setMenu(menu)
        return menu

    def _get_resource_actions(self):
        """
        Get list of actions for the current resource type.
        Can be overridden by child classes for resource-specific actions.
        """
        actions = []

        # Default resource-specific actions (e.g., pods get View Logs and SSH)
        # Note: Ideally this mapping should move to a central registry or child classes,
        # but kept here for backward compatibility with the existing BaseResourcePage structure.
        resource_type = getattr(self, 'resource_type', None)
        
        if resource_type == "pods":
            actions.extend([
                {"text": "View Logs", "icon": "logs", "dangerous": False},
                {"text": "SSH", "icon": "terminal", "dangerous": False}
            ])

        # Default actions for all resources
        actions.extend([
            {"text": "Edit", "icon": "edit", "dangerous": False},
            {"text": "Delete", "icon": "delete", "dangerous": True}
        ])
        
        return actions

    def _highlight_active_row(self, row, is_active):
        """Highlight or unhighlight a table row."""
        if not hasattr(self, 'table') or self.table is None or sip.isdeleted(self.table):
            return

        for col in range(self.table.columnCount()):
            try:
                item = self.table.item(row, col)
                if item:
                    if is_active:
                        accent_color = getattr(get_theme_manager().get_current_theme().colors, 'ACCENT_BLUE', AppColors.ACCENT_BLUE)
                        bg_color = QColor(accent_color)
                        bg_color.setAlpha(0x22)  # 13% opacity
                        item.setBackground(bg_color)
                    else:
                        item.setBackground(QColor("transparent"))
            except (RuntimeError, AttributeError):
                continue

    def _handle_action(self, action, row):
        """Handle action menu item selection."""
        pass

    def _create_action_container(self, row, button):
        """Create container widget for action button."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(button)
        container.setStyleSheet(
            BaseComponentsStyles.CONTAINER_TRANSPARENT_STYLE)
        return container

    def _handle_item_entered(self, item):
        """Handle mouse entering a table item for full-row hover."""
        if not item:
            return
        row = item.row()
        self._highlight_row(row)

    def _highlight_row(self, row):
        """Highlight a specific row and unhighlight others."""
        # Unhighlight previous row
        if hasattr(self, '_hovered_row') and self._hovered_row != row:
            self._set_row_highlight(self._hovered_row, False)

        self._hovered_row = row
        self._set_row_highlight(row, True)

    def _set_row_highlight(self, row, highlight):
        """Set or clear background highlight for an entire row."""
        if not hasattr(self, 'table') or self.table is None or sip.isdeleted(self.table):
            return

        if row < 0 or row >= self.table.rowCount():
            return

        try:
            theme = get_theme_manager().get_current_theme()
            hover_bg = getattr(theme.colors, 'HOVER_HIGHLIGHT', 'rgba(255, 87, 51, 20)')
            bg_color = QColor(hover_bg) if highlight else QColor("transparent")

            for col in range(self.table.columnCount()):
                it = self.table.item(row, col)
                if it:
                    it.setBackground(bg_color)
        except (RuntimeError, AttributeError):
            pass

    def leaveEvent(self, event):
        """Handle mouse leaving the page to clear row highlight."""
        self._clear_hover_highlight()
        super().leaveEvent(event)

    def style_table_item(self, item, is_name=False):
        """Apply consistent styling to table items."""
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if is_name:
            theme = get_theme_manager().get_current_theme()
            orange_color = getattr(theme.colors, 'ACCENT_ORANGE', '#FF5733')
            item.setForeground(QColor(orange_color))
            font = item.font()
            # Set to SemiBold (600) instead of standard Bold (700) for a cleaner look
            font.setWeight(650) if hasattr(QFont, 'DemiBold') else font.setWeight(600)
            font.setPointSize(10) # Roughly 14px depending on DPI, maybe 11 for clearer look
            item.setFont(font)
        return item

    def handle_row_click(self, row, column):
        """Handle table row click events."""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)

    def create_empty_state(self, message, description=None):
        """Create empty state widget for when table has no data."""
        # Create a container for the empty state
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setContentsMargins(0, 0, 0, 0)

        # Create the content container with proper sizing
        content_widget = QWidget()
        content_widget.setStyleSheet(
            BaseTablePageStyles.get_empty_state_style())
        content_widget.setFixedWidth(500)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.setContentsMargins(30, 40, 30, 40)

        # Main message
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet(
            BaseComponentsStyles.EMPTY_STATE_MESSAGE_LABEL_STYLE)
        content_layout.addWidget(message_label)

        # Description (optional)
        if description:
            desc_label = QLabel(description)
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_label.setStyleSheet(
                BaseTablePageStyles.get_empty_message_style())
            desc_label.setWordWrap(True)
            content_layout.addWidget(desc_label)

        # Add content to the main empty layout
        empty_layout.addWidget(content_widget, 0, Qt.AlignmentFlag.AlignCenter)

        return empty_widget

    def _on_theme_changed(self, theme_name):
        """Handle theme change events."""
        logging.debug(f"BaseTablePage: Refreshing theme to {theme_name}")

        # Reload action button icon for new theme
        self._load_action_button_icon()

        # Refresh static UI elements
        self._refresh_static_ui_styles()

        # Refresh table and its contents
        if hasattr(self, 'table') and self.table and not sip.isdeleted(self.table):
            self._refresh_table_theme_styles()
            
            # The per-row iteration below uses QTableWidgetItem / cellWidget APIs
            # that only exist on QTableWidget. Pages migrated to QTableView (the
            # model-view migration) handle theme via delegate paint() reading the
            # current theme, plus a viewport().update() in their _on_theme_changed.
            if isinstance(self.table, QTableWidget):
                self._refresh_all_row_widgets()

        logging.debug(f"BaseTablePage: Theme refresh complete for {theme_name}")

    def _refresh_static_ui_styles(self):
        """Refresh styles of top-level UI components."""
        if hasattr(self, 'title_label') and self.title_label and not sip.isdeleted(self.title_label):
            self.title_label.setStyleSheet(BaseTablePageStyles.get_title_style())
        if hasattr(self, 'items_count') and self.items_count and not sip.isdeleted(self.items_count):
            self.items_count.setStyleSheet(BaseTablePageStyles.get_count_style())
        if hasattr(self, 'select_all_checkbox') and self.select_all_checkbox and not sip.isdeleted(self.select_all_checkbox):
            self.select_all_checkbox.setStyleSheet(BaseTablePageStyles.get_checkbox_style())

    def _refresh_table_theme_styles(self):
        """Refresh theme-aware styles for the table and its container."""
        if hasattr(self, 'table_container') and self.table_container and not sip.isdeleted(self.table_container):
            self.table_container.setStyleSheet(BaseTablePageStyles.get_table_container_style())
        
        self.table.setStyleSheet(BaseTablePageStyles.get_table_style())
        
        header = self.table.horizontalHeader()
        if header and not sip.isdeleted(header):
            header.setStyleSheet(BaseTablePageStyles.get_table_header_style())
            
        if hasattr(self, '_item_widgets') and 'header_widget' in self._item_widgets:
            header_widget = self._item_widgets['header_widget']
            if header_widget and not sip.isdeleted(header_widget):
                header_widget.setStyleSheet(BaseTablePageStyles.get_header_widget_style())

    def _refresh_all_row_widgets(self):
        """Refresh all widgets rendered inside table cells (checkboxes, badges, buttons)."""
        action_col = self.table.columnCount() - 1
        for row in range(self.table.rowCount()):
            # Clear programmatic backgrounds to let stylesheet defaults take over
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor("transparent"))
            
            # Refresh cell widgets
            for col in range(self.table.columnCount()):
                widget = self.table.cellWidget(row, col)
                if not widget or sip.isdeleted(widget):
                    continue
                
                self._refresh_cell_widget(widget, col == 0, col == action_col)

    def _refresh_cell_widget(self, widget, is_checkbox_col, is_action_col):
        """Refresh a specific widget within a table cell."""
        if is_checkbox_col:
            for child in widget.children():
                if isinstance(child, QCheckBox) and not sip.isdeleted(child):
                    child.setStyleSheet("")
                    child.setStyleSheet(BaseTablePageStyles.get_checkbox_style())
                    break
        elif is_action_col:
            for child in widget.children():
                if isinstance(child, QToolButton) and not sip.isdeleted(child):
                    child.setStyleSheet(BaseTablePageStyles.get_action_button_style())
                    child.setIcon(self.action_button_icon)
                    # Refresh menu styling with new theme
                    menu = child.menu()
                    if menu and not sip.isdeleted(menu):
                        menu.setStyleSheet(BaseTablePageStyles.get_menu_style())
                    break
        elif isinstance(widget, StatusLabel):
            self._refresh_status_label(widget)
        elif widget.__class__.__name__ == "MultiColorStatusLabel" and hasattr(widget, 'refresh_theme_style'):
            try:
                widget.refresh_theme_style()
            except (RuntimeError, AttributeError):
                pass

    def _refresh_status_label(self, widget):
        """Update StatusLabel appearance for current theme."""
        try:
            if hasattr(widget, "label") and widget.label and not sip.isdeleted(widget.label):
                custom_color = getattr(widget, "_custom_color", None)
                if custom_color:
                    # Preserve explicitly supplied badge color across theme refresh
                    widget.label.setStyleSheet(
                        BaseDetailSectionStyles.get_custom_badge_style(custom_color, is_small=True)
                    )
                else:
                    status_type = widget._map_status_to_type(widget.label.text())
                    widget.label.setStyleSheet(
                        BaseDetailSectionStyles.get_status_badge_style(status_type, is_small=True)
                    )
                widget.update()
        except (RuntimeError, AttributeError):
            pass

