"""
Paginated Resource Page - Implements proper pagination for large datasets
Extends BaseResourcePage with pagination capabilities
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QProgressBar, QFrame, QSpacerItem, QSizePolicy, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from typing import List, Dict, Any, Optional

from .base_resource_page import BaseResourcePage
from .virtualized_table_model import VirtualizedResourceModel
from .virtual_scroll_table import VirtualScrollTable
from Utils.unified_resource_loader import get_unified_resource_loader
from .resource_processing_worker import create_processing_worker
from Utils.thread_manager import get_thread_manager


class PaginationControls(QFrame):
    """Pagination controls widget"""
    
    # Signals
    load_more_requested = pyqtSignal()
    page_size_changed = pyqtSignal(int)
    refresh_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_loaded = 0
        self.has_more_data = True
        self.is_loading = False
        self.page_size = 100
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup pagination controls UI"""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(16)
        
        # Items info
        self.items_info_label = QLabel("No items loaded")
        self.items_info_label.setFont(QFont("", 9))
        layout.addWidget(self.items_info_label)
        
        # Spacer
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout.addItem(spacer)
        
        # Page size selector
        page_size_label = QLabel("Items per page:")
        page_size_label.setFont(QFont("", 9))
        layout.addWidget(page_size_label)
        
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["50", "100", "200", "500"])
        self.page_size_combo.setCurrentText("100")
        self.page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        layout.addWidget(self.page_size_combo)
        
        # Load more button
        self.load_more_button = QPushButton("Load More Items")
        self.load_more_button.clicked.connect(self.load_more_requested.emit)
        self.load_more_button.setMinimumWidth(120)
        layout.addWidget(self.load_more_button)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.refresh_button.setMinimumWidth(80)
        layout.addWidget(self.refresh_button)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        layout.addWidget(self.progress_bar)
    
    def _on_page_size_changed(self, text):
        """Handle page size change"""
        try:
            new_page_size = int(text)
            if new_page_size != self.page_size:
                self.page_size = new_page_size
                self.page_size_changed.emit(new_page_size)
        except ValueError:
            pass
    
    def update_status(self, total_loaded: int, has_more_data: bool, is_loading: bool = False):
        """Update pagination status"""
        self.total_loaded = total_loaded
        self.has_more_data = has_more_data
        self.is_loading = is_loading
        
        # Update items info
        if total_loaded == 0:
            self.items_info_label.setText("No items loaded")
        elif has_more_data:
            self.items_info_label.setText(f"{total_loaded} items loaded (more available)")
        else:
            self.items_info_label.setText(f"{total_loaded} items loaded (all)")
        
        # Update button states
        self.load_more_button.setEnabled(has_more_data and not is_loading)
        self.load_more_button.setText("Loading..." if is_loading else "Load More Items")
        self.refresh_button.setEnabled(not is_loading)
        
        # Show/hide progress bar
        self.progress_bar.setVisible(is_loading)
    
    def show_progress(self, progress: int, message: str = ""):
        """Show loading progress"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(progress)
        if message:
            self.progress_bar.setFormat(f"{message} - %p%")
        else:
            self.progress_bar.setFormat("%p%")
    
    def hide_progress(self):
        """Hide loading progress"""
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)


class PaginatedResourcePage(BaseResourcePage):
    """
    Resource page with pagination support for handling large datasets efficiently.
    Loads data in chunks to prevent UI freezing and memory exhaustion.
    """
    
    def __init__(self, resource_type: str, columns: List[str], namespace_scoped: bool = True):
        # Initialize with pagination settings
        super().__init__()
        
        # Set resource properties
        self.resource_type = resource_type
        self.columns = columns
        self.namespace_scoped = namespace_scoped
        
        # Pagination state
        self.continue_token = None
        self.total_loaded = 0
        self.has_more_data = True
        self.page_size = 100
        self.is_loading = False
        
        # Workers
        self.data_worker = None
        self.processing_worker = None
        
        # Resource storage
        self.filtered_resources = []
        
        # Note: setup_pagination_ui() should be called after base UI is set up by child class
        
        logging.info(f"PaginatedResourcePage initialized for {resource_type} with {len(columns)} columns")
    
    def setup_pagination_ui(self):
        """Setup pagination-specific UI elements"""
        # Add pagination controls to the bottom
        self.pagination_controls = PaginationControls(self)
        
        # Add to the widget's layout (which was set up by BaseResourcePage.setup_ui)
        if self.layout():
            self.layout().addWidget(self.pagination_controls)
        
        # Connect pagination signals
        self.pagination_controls.load_more_requested.connect(self.load_more_data)
        self.pagination_controls.page_size_changed.connect(self._on_page_size_changed)
        self.pagination_controls.refresh_requested.connect(self.refresh_data)
        
        # Update initial status
        self.pagination_controls.update_status(0, False, False)
    
    def load_data(self, load_more: bool = False):
        """Load data with pagination support"""
        if self.is_loading:
            logging.debug(f"Already loading {self.resource_type}, ignoring request")
            return
        
        if not load_more:
            # Full refresh - reset pagination state
            self.continue_token = None
            self.total_loaded = 0
            self.has_more_data = True
            
            # Clear resource arrays safely
            if hasattr(self, 'resources'):
                self.resources.clear()
            else:
                self.resources = []
                
            if hasattr(self, 'filtered_resources'):
                self.filtered_resources.clear()
            else:
                self.filtered_resources = []
                
            # Clear table contents but preserve headers
            if hasattr(self, 'table') and self.table:
                if hasattr(self.table, 'clearContents'):
                    self.table.clearContents()
                elif hasattr(self.table, 'setRowCount'):
                    self.table.setRowCount(0)
                else:
                    self.table.clear()
        
        self._start_data_loading(load_more)
    
    def load_more_data(self):
        """Load more data (next page)"""
        if self.has_more_data and not self.is_loading:
            self.load_data(load_more=True)
    
    def refresh_data(self):
        """Refresh all data from beginning"""
        self.load_data(load_more=False)
    
    def _on_page_size_changed(self, new_page_size: int):
        """Handle page size change"""
        self.page_size = new_page_size
        # Optionally refresh data with new page size
        # self.refresh_data()  # Uncomment if you want automatic refresh
    
    def _start_data_loading(self, load_more: bool):
        """Start loading data in background"""
        self.is_loading = True
        self.pagination_controls.update_status(self.total_loaded, self.has_more_data, True)
        
        # Show loading indicator
        if hasattr(self, 'show_loading_indicator'):
            if not load_more:
                self.show_loading_indicator("Loading resources...")
        
        # Create and start data loader using unified resource loader
        unified_loader = get_unified_resource_loader()
        
        # Connect signals for unified loader
        unified_loader.loading_completed.connect(self._on_unified_data_loaded)
        unified_loader.loading_error.connect(self._on_unified_data_error)
        
        # Start loading
        operation_id = unified_loader.load_resources_async(
            resource_type=self.resource_type,
            namespace=self.namespace_filter if self.namespace_filter != "All Namespaces" else None
        )
        
        logging.info(f"Started loading {self.resource_type}, page_size={self.page_size}, load_more={load_more}")
    
    def _on_unified_data_loaded(self, resource_type, load_result):
        """Handle data loaded from unified resource loader"""
        try:
            if load_result.success:
                resources = load_result.items
                self._on_data_loaded((resources, resource_type, None))
            else:
                self._on_unified_data_error(resource_type, load_result.error_message)
        except Exception as e:
            logging.error(f"Error handling unified data load: {e}")
            self._on_unified_data_error(resource_type, str(e))
    
    def _on_unified_data_error(self, resource_type, error_message):
        """Handle error from unified resource loader"""
        logging.error(f"Failed to load {resource_type}: {error_message}")
        self._on_data_load_error(error_message)

    def _on_data_loaded(self, result):
        """Handle raw data loaded from API"""
        try:
            resources, resource_type, next_token = result
            
            # Update pagination state
            self.continue_token = next_token if next_token else None
            self.has_more_data = bool(self.continue_token)
            
            if not resources:
                # No data received
                self._finish_loading(load_more=bool(self.total_loaded > 0))
                return
            
            # Process data in background
            self._start_data_processing(resources, load_more=bool(self.total_loaded > 0))
            
        except Exception as e:
            logging.error(f"Error handling data loaded for {self.resource_type}: {e}")
            self._on_data_load_error(str(e))
    
    def _start_data_processing(self, raw_resources: List[Dict], load_more: bool):
        """Start processing raw data in background"""
        # Create appropriate processing worker
        self.processing_worker = create_processing_worker(self.resource_type, raw_resources)
        
        # Connect signals
        self.processing_worker.data_processed.connect(lambda data: self._on_data_processed(data, load_more))
        self.processing_worker.progress_updated.connect(self._on_processing_progress)
        self.processing_worker.error_occurred.connect(self._on_processing_error)
        
        # Start processing
        self.processing_worker.start()
        
        logging.info(f"Started processing {len(raw_resources)} {self.resource_type} items")
    
    def _on_processing_progress(self, progress: int, message: str):
        """Handle processing progress updates"""
        self.pagination_controls.show_progress(progress, message)
    
    def _on_data_processed(self, processed_resources: List[Dict], load_more: bool):
        """Handle processed data"""
        try:
            if load_more:
                # Append to existing data
                self.resources.extend(processed_resources)
                self.table.append_data(processed_resources)
            else:
                # Replace existing data
                self.resources = processed_resources
                self.table.set_resource_data(processed_resources, self.columns)
            
            # Update counters
            self.total_loaded = len(self.resources)
            
            # Apply current search filter if any
            if hasattr(self, 'search_input') and self.search_input.text().strip():
                self.perform_search()
            
            self._finish_loading(load_more)
            
            logging.info(f"Processed {len(processed_resources)} items, total: {self.total_loaded}")
            
        except Exception as e:
            logging.error(f"Error handling processed data: {e}")
            self._on_processing_error(str(e))
    
    def _finish_loading(self, load_more: bool):
        """Finish loading process"""
        self.is_loading = False
        
        # Update pagination controls
        self.pagination_controls.update_status(self.total_loaded, self.has_more_data, False)
        self.pagination_controls.hide_progress()
        
        # Hide loading indicator
        if hasattr(self, 'hide_loading_indicator'):
            self.hide_loading_indicator()
        
        # Update status
        status_message = f"{self.total_loaded} {self.resource_type} loaded"
        if self.has_more_data:
            status_message += " (more available)"
        
        if hasattr(self, 'update_status_message'):
            self.update_status_message(status_message)
        
        logging.info(f"Finished loading {self.resource_type}: {status_message}")
    
    def _on_data_load_error(self, error_message: str):
        """Handle data loading error"""
        logging.error(f"Data loading error for {self.resource_type}: {error_message}")
        self._handle_loading_error(f"Failed to load {self.resource_type}: {error_message}")
    
    def _on_processing_error(self, error_message: str):
        """Handle data processing error"""
        logging.error(f"Data processing error for {self.resource_type}: {error_message}")
        self._handle_loading_error(f"Failed to process {self.resource_type}: {error_message}")
    
    def _handle_loading_error(self, error_message: str):
        """Handle loading errors"""
        self.is_loading = False
        self.pagination_controls.update_status(self.total_loaded, self.has_more_data, False)
        self.pagination_controls.hide_progress()
        
        if hasattr(self, 'hide_loading_indicator'):
            self.hide_loading_indicator()
        
        if hasattr(self, 'show_error_message'):
            self.show_error_message(error_message)
        
        if hasattr(self, 'update_status_message'):
            self.update_status_message(f"Error: {error_message}")
    
    def perform_search(self):
        """Perform search on loaded data (override to work with pagination)"""
        if not hasattr(self, 'search_input'):
            return
        
        search_text = self.search_input.text().strip().lower()
        
        if not search_text:
            # No search - show all loaded data
            self.filtered_resources = self.resources.copy()
            self.table.set_resource_data(self.filtered_resources, self.columns)
            self.update_status_message(f"Showing all {len(self.filtered_resources)} {self.resource_type}")
            return
        
        # Perform search on loaded data
        search_terms = search_text.split()
        matching_indices = self.table.search_and_filter(search_terms)
        
        # Filter resources based on matching indices
        self.filtered_resources = [self.resources[i] for i in matching_indices if i < len(self.resources)]
        
        # Update table
        self.table.set_resource_data(self.filtered_resources, self.columns)
        
        # Update status
        total_loaded = len(self.resources)
        filtered_count = len(self.filtered_resources)
        
        status_msg = f"Found {filtered_count} of {total_loaded} {self.resource_type}"
        if self.has_more_data:
            status_msg += " (search limited to loaded items - load more to expand search)"
        
        self.update_status_message(status_msg)
        
        logging.info(f"Search '{search_text}' found {filtered_count} items")
    
    def cleanup_on_destroy(self):
        """Enhanced cleanup for pagination"""
        # Cancel any running workers
        if self.data_worker and hasattr(self.data_worker, 'cancel'):
            self.data_worker.cancel()
        
        if self.processing_worker and hasattr(self.processing_worker, 'cancel'):
            self.processing_worker.cancel()
        
        # Call parent cleanup
        super().cleanup_on_destroy()
        
        logging.debug(f"PaginatedResourcePage cleanup completed for {self.resource_type}")
    
    def get_pagination_stats(self) -> Dict[str, Any]:
        """Get pagination statistics"""
        return {
            'resource_type': self.resource_type,
            'total_loaded': self.total_loaded,
            'page_size': self.page_size,
            'has_more_data': self.has_more_data,
            'is_loading': self.is_loading,
            'continue_token': bool(self.continue_token),
            'filtered_count': len(getattr(self, 'filtered_resources', [])),
            'performance_stats': self.table.get_performance_stats() if hasattr(self.table, 'get_performance_stats') else {}
        }