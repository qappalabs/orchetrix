"""
Virtual Scroll Table - Efficient handling of large datasets with virtual scrolling
Split from base_resource_page.py for better architecture
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QScrollBar, 
    QLabel, QFrame, QHeaderView, QSizePolicy
)
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QPaintEvent


class VirtualScrollTable(QWidget):
    """Virtual scrolling table for handling large datasets efficiently"""
    
    # Signals
    item_selected = pyqtSignal(int)  # Emitted when an item is selected
    item_double_clicked = pyqtSignal(int)  # Emitted when an item is double-clicked
    
    def __init__(self, headers, parent=None):
        super().__init__(parent)
        self.headers = headers
        self.all_data = []
        self.visible_range = (0, 0)
        self.row_height = 40
        self.viewport_rows = 20
        self.header_height = 35
        self.selected_indices = set()
        
        # Performance settings
        self.buffer_size = 5  # Extra rows to render above/below viewport
        self.scroll_debounce_timer = QTimer()
        self.scroll_debounce_timer.setSingleShot(True)
        self.scroll_debounce_timer.timeout.connect(self._update_visible_items)
        
        # Setup UI
        self._setup_ui()
        
        logging.debug(f"VirtualScrollTable initialized with {len(headers)} headers")
        
    def _setup_ui(self):
        """Setup the virtual scroll table UI"""
        self.setMinimumHeight(400)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create header
        self.header = self._create_header()
        layout.addWidget(self.header)
        
        # Create scroll area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        # Create content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)
        
        # Connect scroll events
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        # Item containers for visible items
        self.visible_items = []
        
    def _create_header(self):
        """Create the table header"""
        header_widget = QFrame()
        header_widget.setFixedHeight(self.header_height)
        header_widget.setFrameStyle(QFrame.Shape.Box)
        header_widget.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-bottom: 2px solid #a0a0a0;
            }
        """)
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(5, 0, 5, 0)
        
        # Add header labels
        for header in self.headers:
            label = QLabel(header)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            label.setStyleSheet("font-weight: bold; padding: 0 10px;")
            header_layout.addWidget(label)
        
        return header_widget
        
    def set_data(self, data):
        """Set data for virtual scrolling"""
        self.all_data = data
        self.selected_indices.clear()
        
        # Update content widget size based on total data
        total_height = len(data) * self.row_height
        self.content_widget.setMinimumHeight(total_height)
        
        # Update visible range
        self._update_visible_range()
        self._render_visible_items()
        
        logging.debug(f"VirtualScrollTable data set: {len(data)} items, total height: {total_height}px")
        
    def _on_scroll(self, value):
        """Handle scroll events with debouncing"""
        # Debounce scroll events for better performance
        self.scroll_debounce_timer.stop()
        self.scroll_debounce_timer.start(16)  # ~60fps
        
    def _update_visible_items(self):
        """Update visible items after scroll debounce"""
        self._update_visible_range()
        self._render_visible_items()
        
    def _update_visible_range(self):
        """Update visible range based on scroll position"""
        if not self.all_data:
            self.visible_range = (0, 0)
            return
            
        # Get current scroll position
        scroll_value = self.scroll_area.verticalScrollBar().value()
        viewport_height = self.scroll_area.viewport().height()
        
        # Calculate visible row indices
        first_visible_row = max(0, scroll_value // self.row_height - self.buffer_size)
        last_visible_row = min(
            len(self.all_data) - 1,
            (scroll_value + viewport_height) // self.row_height + self.buffer_size
        )
        
        self.visible_range = (first_visible_row, last_visible_row + 1)
        
    def _render_visible_items(self):
        """Render only the visible items for performance"""
        start_idx, end_idx = self.visible_range
        
        # Clear existing visible items
        for item_widget in self.visible_items:
            item_widget.setParent(None)
            item_widget.deleteLater()
        self.visible_items.clear()
        
        # Create spacer for items above visible range
        if start_idx > 0:
            spacer_height = start_idx * self.row_height
            top_spacer = QWidget()
            top_spacer.setFixedHeight(spacer_height)
            self.content_layout.addWidget(top_spacer)
        
        # Render visible items
        for i in range(start_idx, min(end_idx, len(self.all_data))):
            item_widget = self._create_item_widget(i, self.all_data[i])
            self.content_layout.addWidget(item_widget)
            self.visible_items.append(item_widget)
        
        # Create spacer for items below visible range
        if end_idx < len(self.all_data):
            remaining_items = len(self.all_data) - end_idx
            spacer_height = remaining_items * self.row_height
            bottom_spacer = QWidget()
            bottom_spacer.setFixedHeight(spacer_height)
            self.content_layout.addWidget(bottom_spacer)
            
    def _create_item_widget(self, index, item_data):
        """Create a widget for a single table item"""
        item_widget = QFrame()
        item_widget.setFixedHeight(self.row_height)
        item_widget.setFrameStyle(QFrame.Shape.Box)
        
        # Set styling based on selection
        if index in self.selected_indices:
            item_widget.setStyleSheet("""
                QFrame {
                    background-color: #e3f2fd;
                    border: 1px solid #2196f3;
                }
            """)
        else:
            item_widget.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                }
                QFrame:hover {
                    background-color: #f5f5f5;
                }
            """)
        
        # Create layout for item content
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(5, 0, 5, 0)
        
        # Add data columns
        if isinstance(item_data, dict):
            # Handle dictionary data
            for header in self.headers:
                value = item_data.get(header.lower(), "")
                label = QLabel(str(value))
                label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item_layout.addWidget(label)
        elif isinstance(item_data, (list, tuple)):
            # Handle list/tuple data
            for i, header in enumerate(self.headers):
                value = item_data[i] if i < len(item_data) else ""
                label = QLabel(str(value))
                label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item_layout.addWidget(label)
        else:
            # Handle single value
            label = QLabel(str(item_data))
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item_layout.addWidget(label)
        
        # Add mouse event handling
        item_widget.mousePressEvent = lambda event, idx=index: self._on_item_clicked(idx, event)
        item_widget.mouseDoubleClickEvent = lambda event, idx=index: self._on_item_double_clicked(idx, event)
        
        return item_widget
    
    def _on_item_clicked(self, index, event):
        """Handle item click events"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Toggle selection
            if index in self.selected_indices:
                self.selected_indices.remove(index)
            else:
                # For single selection, clear others first
                self.selected_indices.clear()
                self.selected_indices.add(index)
            
            # Re-render to update selection styling
            self._render_visible_items()
            
            # Emit selection signal
            self.item_selected.emit(index)
    
    def _on_item_double_clicked(self, index, event):
        """Handle item double-click events"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.item_double_clicked.emit(index)
    
    def get_selected_indices(self):
        """Get currently selected item indices"""
        return list(self.selected_indices)
    
    def get_selected_data(self):
        """Get data for currently selected items"""
        return [self.all_data[i] for i in self.selected_indices if i < len(self.all_data)]
    
    def clear_selection(self):
        """Clear all selections"""
        self.selected_indices.clear()
        self._render_visible_items()
    
    def select_all(self):
        """Select all items"""
        self.selected_indices = set(range(len(self.all_data)))
        self._render_visible_items()
    
    def scroll_to_item(self, index):
        """Scroll to make the specified item visible"""
        if 0 <= index < len(self.all_data):
            target_position = index * self.row_height
            self.scroll_area.verticalScrollBar().setValue(target_position)
    
    # Backward compatibility methods for QTableWidget interface
    def rowCount(self):
        """Return number of rows - backward compatibility method"""
        return len(self.all_data)
    
    def insertRow(self, row):
        """Insert a row - backward compatibility method (no-op for virtual table)"""
        # Virtual table doesn't need to insert rows, data is managed via set_data
        pass
    
    def setRowCount(self, count):
        """Set row count - backward compatibility method"""
        if count == 0:
            self.set_data([])
        # For non-zero counts, this is a no-op since data is managed via set_data
    
    def clear(self):
        """Clear all data - backward compatibility method"""
        self.set_data([])
    
    def verticalScrollBar(self):
        """Return vertical scroll bar - backward compatibility method"""
        return self.scroll_area.verticalScrollBar()
    
    def get_visible_range(self):
        """Get the current visible range"""
        return self.visible_range
    
    def get_total_items(self):
        """Get total number of items"""
        return len(self.all_data)
    
    def refresh(self):
        """Refresh the virtual table display"""
        self._update_visible_range()
        self._render_visible_items()
    
    def cleanup(self):
        """Cleanup resources"""
        self.scroll_debounce_timer.stop()
        for item_widget in self.visible_items:
            item_widget.setParent(None)
            item_widget.deleteLater()
        self.visible_items.clear()
        logging.debug("VirtualScrollTable cleanup completed")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except Exception as e:
            logging.error(f"Error in VirtualScrollTable destructor: {e}")