"""
Virtual Scroll Table - Efficient handling of large datasets with virtual scrolling
Uses QTableView with VirtualizedResourceModel for optimal performance
"""

import logging
from PyQt6.QtWidgets import (
    QTableView, QVBoxLayout, QWidget, QHeaderView, QAbstractItemView,
    QStyledItemDelegate, QApplication, QStyle
)
from PyQt6.QtCore import Qt, pyqtSignal, QModelIndex, QTimer
from PyQt6.QtGui import QColor, QPainter, QFont
from typing import List, Dict, Any, Optional, Callable

from .virtualized_table_model import VirtualizedResourceModel


class HighPerformanceDelegate(QStyledItemDelegate):
    """Custom delegate for optimized cell rendering"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_cache = {}
    
    def paint(self, painter: QPainter, option, index: QModelIndex):
        """Optimized paint method"""
        if option.state & QStyle.StateFlag.State_Selected:
            # Custom selection color
            painter.fillRect(option.rect, QColor(227, 242, 253))
        
        # Use default painting for text
        super().paint(painter, option, index)


class VirtualScrollTable(QTableView):
    """
    High-performance virtual scrolling table using QTableView + VirtualizedResourceModel.
    Replaces the old custom widget approach for much better performance.
    """
    
    # Signals - maintaining backward compatibility
    item_selected = pyqtSignal(int)  # Emitted when an item is selected
    item_double_clicked = pyqtSignal(int)  # Emitted when an item is double-clicked
    data_changed = pyqtSignal()  # Emitted when data changes
    selection_changed = pyqtSignal(list)  # Emitted when selection changes
    
    def __init__(self, headers: List[str], parent=None):
        """Initialize virtual scroll table with headers"""
        super().__init__(parent)
        self.headers = headers or []
        self._model = None
        self._formatters = {}
        self._last_selected_rows = []
        
        # Performance settings
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        # Enable virtual scrolling
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        # Set custom delegate for optimized rendering
        self.delegate = HighPerformanceDelegate(self)
        self.setItemDelegate(self.delegate)
        
        # Configure header for responsive layout
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(32)  # Slightly larger rows for better readability
        
        # Enable responsive column resizing
        self._setup_responsive_columns()
        
        # Performance optimizations
        self.setShowGrid(True)
        self.setGridStyle(Qt.PenStyle.DotLine)
        
        # Initialize with empty model first
        self.set_resource_data([], self.headers)
        
        # Connect selection changes after model is set
        if self.selectionModel():
            self.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.doubleClicked.connect(self._on_double_clicked)
        
        logging.info(f"VirtualScrollTable initialized with {len(headers)} columns: {headers}")
    
    def _setup_responsive_columns(self):
        """Setup responsive column sizing"""
        self._responsive_timer = QTimer(self)
        self._responsive_timer.setSingleShot(True)
        self._responsive_timer.timeout.connect(self._adjust_columns_to_screen)
        
        # Connect to parent widget resize events
        self.parent_resize_timer = QTimer(self)
        self.parent_resize_timer.setSingleShot(True) 
        self.parent_resize_timer.timeout.connect(self._adjust_columns_to_screen)
    
    def _adjust_columns_to_screen(self):
        """Adjust column widths to fit screen size optimally"""
        if not self._model or not self.headers:
            return
            
        try:
            available_width = self.viewport().width() - 20  # Account for scrollbar
            if available_width <= 0:
                return
            
            header = self.horizontalHeader()
            column_count = len(self.headers)
            
            if column_count == 0:
                return
            
            # Define column priorities (some columns should be wider than others)
            priority_columns = ['name', 'namespace', 'status', 'age']
            
            # Calculate base width per column
            base_width = max(80, available_width // column_count)
            
            # Adjust individual columns based on content and priority
            for i, column_name in enumerate(self.headers):
                if column_name.lower() in priority_columns:
                    # Priority columns get more space
                    width = min(int(base_width * 1.2), 200)
                else:
                    # Regular columns get standard space
                    width = min(base_width, 150)
                
                # Ensure minimum width for readability
                width = max(width, 80)
                header.resizeSection(i, width)
                
            # Set last column to stretch to fill remaining space
            header.setSectionResizeMode(column_count - 1, QHeaderView.ResizeMode.Stretch)
            
        except Exception as e:
            logging.warning(f"Error adjusting columns to screen: {e}")
    
    def resizeEvent(self, event):
        """Handle resize events to trigger responsive column adjustment"""
        super().resizeEvent(event)
        # Delay adjustment to avoid excessive updates during resize
        if hasattr(self, '_responsive_timer'):
            self._responsive_timer.start(150)  # 150ms delay
    
    def set_resource_data(self, data: List[Dict], columns: Optional[List[str]] = None):
        """Set data using virtualized model for optimal performance"""
        try:
            if columns:
                self.headers = columns
            
            # Create new model
            self._model = VirtualizedResourceModel(data, self.headers, self._formatters)
            self.setModel(self._model)
            
            # Connect model signals
            self._model.data_changed_custom.connect(self.data_changed.emit)
            
            # Connect selection model signals after setting model
            if self.selectionModel() and not hasattr(self, '_selection_connected'):
                self.selectionModel().selectionChanged.connect(self._on_selection_changed)
                self._selection_connected = True
            
            # Apply responsive column sizing
            QTimer.singleShot(100, self._adjust_columns_to_screen)  # Delay to ensure proper widget size
            
            logging.info(f"Set resource data: {len(data)} items, {len(self.headers)} columns")
            
        except Exception as e:
            logging.error(f"Error setting resource data: {e}")
    
    def append_data(self, additional_data: List[Dict]):
        """Append new data efficiently"""
        if self._model:
            self._model.append_data(additional_data)
            self.data_changed.emit()
    
    def update_data(self, new_data: List[Dict], incremental: bool = False):
        """Update data efficiently"""
        if self._model:
            self._model.update_data(new_data, incremental)
            self.data_changed.emit()
    
    def refresh_data(self, new_data: List[Dict]):
        """Refresh all data"""
        if self._model:
            self._model.refresh_data(new_data)
            self.data_changed.emit()
    
    def set_formatters(self, formatters: Dict[str, Callable]):
        """Set custom formatters for columns"""
        self._formatters = formatters
        if self._model:
            self._model.set_formatters(formatters)
    
    def _on_selection_changed(self, selected, deselected):
        """Handle selection changes"""
        selected_rows = []
        for index in self.selectionModel().selectedRows():
            row = index.row()
            selected_rows.append(row)
            if row not in self._last_selected_rows:
                self.item_selected.emit(row)
        
        self._last_selected_rows = selected_rows
        self.selection_changed.emit(selected_rows)
    
    def _on_double_clicked(self, index: QModelIndex):
        """Handle double-click events"""
        if index.isValid():
            self.item_double_clicked.emit(index.row())
    
    # Backward compatibility methods for old VirtualScrollTable interface
    def set_data(self, data):
        """Backward compatibility - redirect to set_resource_data"""
        if isinstance(data, list) and data and isinstance(data[0], dict):
            self.set_resource_data(data, self.headers)
        else:
            # Convert list data to dict format
            dict_data = []
            for item in data:
                if isinstance(item, (list, tuple)):
                    item_dict = {}
                    for i, header in enumerate(self.headers):
                        if i < len(item):
                            item_dict[header] = item[i]
                        else:
                            item_dict[header] = ""
                    dict_data.append(item_dict)
                else:
                    dict_data.append({self.headers[0] if self.headers else "value": str(item)})
            
            self.set_resource_data(dict_data, self.headers)
    
    def get_selected_indices(self):
        """Get currently selected item indices"""
        selected_rows = []
        if self.selectionModel():
            for index in self.selectionModel().selectedRows():
                selected_rows.append(index.row())
        return selected_rows
    
    def get_selected_data(self):
        """Get data for currently selected items"""
        selected_rows = self.get_selected_indices()
        if self._model:
            return self._model.get_selected_data(selected_rows)
        return []
    
    def clear_selection(self):
        """Clear all selections"""
        if self.selectionModel():
            self.selectionModel().clear()
    
    def select_all(self):
        """Select all items"""
        if self.selectionModel():
            self.selectAll()
    
    def scroll_to_item(self, index):
        """Scroll to make the specified item visible"""
        if self._model and 0 <= index < self._model.rowCount():
            model_index = self._model.index(index, 0)
            self.scrollTo(model_index, QAbstractItemView.ScrollHint.PositionAtCenter)
    
    def search_and_filter(self, search_terms: List[str], search_columns: Optional[List[str]] = None) -> List[int]:
        """Search through data and return matching row indices"""
        if self._model:
            return self._model.search_and_filter(search_terms, search_columns)
        return []
    
    def enable_caching(self, enabled: bool = True):
        """Enable or disable model caching"""
        if self._model:
            self._model.enable_cache(enabled)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        if self._model:
            return self._model.get_cache_stats()
        return {}
    
    # Backward compatibility methods for QTableWidget interface
    def rowCount(self):
        """Return number of rows - backward compatibility method"""
        return self._model.rowCount() if self._model else 0
    
    def insertRow(self, row):
        """Insert a row - backward compatibility method (no-op for virtual table)"""
        # Virtual table doesn't need to insert rows, data is managed via set_resource_data
        pass
    
    def setRowCount(self, count):
        """Set row count - backward compatibility method"""
        if count == 0:
            self.set_resource_data([])
        # For non-zero counts, this is a no-op since data is managed via set_resource_data
    
    def clear(self):
        """Clear all data - backward compatibility method"""
        self.set_resource_data([])
    
    def get_visible_range(self):
        """Get the current visible range (rows visible in viewport)"""
        if not self._model:
            return (0, 0)
        
        # Calculate visible range from viewport
        viewport_rect = self.viewport().rect()
        top_index = self.indexAt(viewport_rect.topLeft())
        bottom_index = self.indexAt(viewport_rect.bottomLeft())
        
        if top_index.isValid() and bottom_index.isValid():
            return (top_index.row(), bottom_index.row() + 1)
        elif top_index.isValid():
            return (top_index.row(), top_index.row() + 1)
        else:
            return (0, min(self._model.rowCount(), 100))  # Default range
    
    def get_total_items(self):
        """Get total number of items"""
        return self._model.rowCount() if self._model else 0
    
    def refresh(self):
        """Refresh the virtual table display"""
        if self._model:
            self._model.layoutChanged.emit()
        self.viewport().update()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {
            'total_items': self.get_total_items(),
            'visible_range': self.get_visible_range(),
            'selected_items': len(self.get_selected_indices()),
            'headers': len(self.headers)
        }
        
        if self._model:
            stats.update(self._model.get_cache_stats())
        
        return stats
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            # Check if the widget still exists before cleanup
            if hasattr(self, '_model') and self._model:
                self._model.clear_cache()
            
            # Safely clear selection
            if hasattr(self, 'clearSelection'):
                self.clearSelection()
                
            logging.debug("VirtualScrollTable cleanup completed")
        except RuntimeError:
            # Widget was already deleted - this is expected during shutdown
            logging.debug("VirtualScrollTable already deleted during cleanup")
        except Exception as e:
            logging.error(f"Error in VirtualScrollTable cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except RuntimeError:
            # Widget already deleted - normal during shutdown
            pass
        except Exception as e:
            logging.debug(f"Error in VirtualScrollTable destructor: {e}")