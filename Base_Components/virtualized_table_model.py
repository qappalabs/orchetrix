"""
Virtualized Table Model for efficient rendering of large datasets
This replaces QTableWidget with QAbstractTableModel for better performance
"""

from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from typing import List, Dict, Any, Optional, Callable
import logging
import time
import hashlib

class VirtualizedResourceModel(QAbstractTableModel):
    """
    High-performance table model that virtualizes data rendering.
    Only formats data when actually displayed, supports caching and dirty flags.
    """
    
    data_changed_custom = pyqtSignal()
    
    def __init__(self, resource_data: List[Dict], columns: List[str], 
                 formatters: Optional[Dict[str, Callable]] = None):
        super().__init__()
        self._data = resource_data or []
        self._columns = columns or []
        self._formatters = formatters or {}

        # Performance optimizations
        self._dirty_rows = set()  # Track which rows need updates
        
        logging.info(f"VirtualizedResourceModel initialized with {len(self._data)} rows, {len(self._columns)} columns")
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """Return number of rows"""
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        """Return number of columns"""  
        return len(self._columns)
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        """Return header data"""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal and section < len(self._columns):
                return self._columns[section]
            elif orientation == Qt.Orientation.Vertical:
                return str(section + 1)
        return None
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        """Return data for given index and role - optimized with caching"""
        if not index.isValid() or index.row() >= len(self._data):
            return None
            
        row, col = index.row(), index.column()
        
        # Handle different roles
        if role == Qt.ItemDataRole.DisplayRole:
            return self._get_display_data(row, col)
        elif role == Qt.ItemDataRole.BackgroundRole:
            return self._get_background_color(row, col)
        elif role == Qt.ItemDataRole.ForegroundRole:
            return self._get_foreground_color(row, col)
        elif role == Qt.ItemDataRole.FontRole:
            return self._get_font(row, col)
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return self._get_text_alignment(row, col)
            
        return None
    
    def _get_display_data(self, row: int, col: int) -> str:
        """Get display data"""
        if col >= len(self._columns):
            return ""

        # Calculate value
        column_key = self._columns[col]
        item = self._data[row]

        # Use custom formatter if available
        if column_key in self._formatters:
            try:
                value = self._formatters[column_key](item)
            except Exception as e:
                logging.warning(f"Formatter error for column {column_key}: {e}")
                value = str(item.get(column_key, ""))
        else:
            value = self._format_cell_value(item, column_key)

        return value
    
    def _format_cell_value(self, item: Dict, column_key: str) -> str:
        """Format individual cell value"""
        value = item.get(column_key, "")
        
        # Handle different data types
        if isinstance(value, (list, tuple)):
            return ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            return str(value)
        elif value is None:
            return ""
        else:
            return str(value)
    
    def _get_background_color(self, row: int, col: int) -> Optional[QColor]:
        """Get background color for cell"""
        # Calculate row color based on status or other criteria
        item = self._data[row]
        color = self._calculate_row_color(item)
        return color
    
    def _get_foreground_color(self, row: int, col: int) -> Optional[QColor]:
        """Get foreground color for cell"""
        return None  # Default color
    
    def _get_font(self, row: int, col: int) -> Optional[QFont]:
        """Get font for cell"""
        return None  # Default font
    
    def _get_text_alignment(self, row: int, col: int) -> int:
        """Get text alignment for cell"""
        return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    
    def _calculate_row_color(self, item: Dict) -> Optional[QColor]:
        """Calculate background color based on item status"""
        status = item.get("status", "").lower()
        
        # Color coding based on status
        if "error" in status or "failed" in status:
            return QColor(255, 240, 240)  # Light red
        elif "warning" in status or "pending" in status:
            return QColor(255, 250, 205)  # Light yellow
        elif "running" in status or "active" in status:
            return QColor(240, 255, 240)  # Light green
        
        return None  # Default color
    
    def mark_row_dirty(self, row: int):
        """Mark a row as needing update"""
        self._dirty_rows.add(row)
    
    def mark_all_dirty(self):
        """Mark all rows as dirty - forces complete refresh"""
        self._dirty_rows = set(range(len(self._data)))
    
    def update_data(self, new_data: List[Dict], incremental: bool = False):
        """Update model data efficiently"""
        self.beginResetModel()
        
        if incremental and len(new_data) > len(self._data):
            # Appending new data
            old_count = len(self._data)
            self._data.extend(new_data[old_count:])
            logging.info(f"Appended {len(new_data) - old_count} new rows")
        else:
            # Complete refresh
            if len(new_data) == len(self._data):
                # Check for changes and mark dirty rows
                for i, (old, new) in enumerate(zip(self._data, new_data)):
                    if old != new:
                        self.mark_row_dirty(i)

            self._data = new_data
        
        self._dirty_rows.clear()
        self.endResetModel()
        self.data_changed_custom.emit()

        logging.info(f"Model updated: {len(self._data)} rows")
    
    def refresh_data(self, new_data: List[Dict]):
        """Refresh data - alias for update_data"""
        self.update_data(new_data, incremental=False)
    
    def append_data(self, additional_data: List[Dict]):
        """Append new data efficiently"""
        if not additional_data:
            return
            
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data) + len(additional_data) - 1)
        self._data.extend(additional_data)
        self.endInsertRows()
        
        self.data_changed_custom.emit()
        logging.info(f"Appended {len(additional_data)} rows, total: {len(self._data)}")
    
    def get_row_data(self, row: int) -> Optional[Dict]:
        """Get raw data for a specific row"""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None
    
    def get_selected_data(self, selected_rows: List[int]) -> List[Dict]:
        """Get raw data for selected rows"""
        return [self._data[row] for row in selected_rows if 0 <= row < len(self._data)]
    
    def search_and_filter(self, search_terms: List[str], search_columns: List[str] = None) -> List[int]:
        """Search through data and return matching row indices"""
        if not search_terms:
            return list(range(len(self._data)))
        
        search_columns = search_columns or self._columns
        matching_rows = []
        
        for i, item in enumerate(self._data):
            # Check if any search term matches any search column
            item_text = ""
            for col in search_columns:
                value = item.get(col, "")
                item_text += f" {str(value).lower()}"
            
            # Check if all search terms are found
            if all(term.lower() in item_text for term in search_terms):
                matching_rows.append(i)
        
        return matching_rows
    
    def sort_data(self, column: int, order: Qt.SortOrder):
        """Sort data by column"""
        if column >= len(self._columns):
            return

        column_key = self._columns[column]
        reverse = (order == Qt.SortOrder.DescendingOrder)

        try:
            self._data.sort(key=lambda item: str(item.get(column_key, "")), reverse=reverse)
            self.layoutChanged.emit()
            logging.info(f"Sorted by column {column_key}, reverse={reverse}")
        except Exception as e:
            logging.error(f"Error sorting data: {e}")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache performance statistics - caching disabled, returns zeros"""
        return {
            'cache_hits': 0,
            'cache_misses': 0,
            'hit_rate_percent': 0,
            'cache_size': 0,
            'color_cache_size': 0
        }
    
    def set_formatters(self, formatters: Dict[str, Callable]):
        """Set custom formatters for columns"""
        self._formatters = formatters
            
    def __del__(self):
        """Cleanup when model is destroyed"""
        try:
            logging.debug(f"VirtualizedResourceModel destroyed")
        except Exception as e:
            logging.debug(f"Error during VirtualizedResourceModel cleanup: {e}")