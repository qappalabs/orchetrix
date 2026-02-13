import logging
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QComboBox, QLabel, QTableWidgetItem
from PyQt6.QtCore import Qt

# Import Managers via local import or assume injected usage to avoid circulars if possible,
# but ResourceSearchHandler interacts heavily with page UI.
from Base_Components.resource_page_style_manager import ResourcePageStyleManager
from Utils.unified_resource_loader import get_unified_resource_loader

# Constants from BaseResourcePage (could be moved to a shared config)
SEARCH_DEBOUNCE_MS = 500

class ResourceSearchHandler:
    """
    Manages search and filtering UI behaviors for BaseResourcePage.
    """

    def __init__(self, page):
        self.page = page
        self.search_bar = None
        self.search_label = None
        self.namespace_combo = None
        self.namespace_label = None
        self._is_searching = False
        self._current_search_query = None
        self._search_signals_connected = False

    def add_filter_controls(self, header_layout):
        """Creates and adds filter controls (Search, Namespace) to the header."""
        
        # Create a separate layout for filters with proper spacing
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(12) 

        # Search bar with label
        self.search_label = QLabel("Search:")
        self.search_label.setStyleSheet(ResourcePageStyleManager.get_search_label_style())
        self.search_label.setMinimumWidth(50)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search resources...")
        self.search_bar.textChanged.connect(self.on_search_text_changed)
        self.search_bar.setFixedWidth(200)
        self.search_bar.setFixedHeight(32)

        # Apply styling
        ResourcePageStyleManager.apply_search_input_style(self.search_bar)

        # Namespace combo
        if getattr(self.page, 'show_namespace_dropdown', True):
            self.namespace_label = QLabel("Namespace:")
            self.namespace_label.setStyleSheet(ResourcePageStyleManager.get_namespace_label_style())
            self.namespace_label.setMinimumWidth(70)

            self.namespace_combo = QComboBox()
            self.namespace_combo.addItem("Loading namespaces...")
            # We assume the page has _on_namespace_changed or hook it up via handler
            # For now, binding to page's method to maintain existing logic flow
            self.namespace_combo.currentTextChanged.connect(self.page._on_namespace_changed)
            self.namespace_combo.setFixedWidth(150)
            self.namespace_combo.setFixedHeight(32)
        else:
            self.namespace_combo = None

        # Apply styling
        if self.namespace_combo:
            ResourcePageStyleManager.apply_namespace_combo_style(self.namespace_combo)

        # Add widgets to layout
        filters_layout.addWidget(self.search_label)
        filters_layout.addWidget(self.search_bar)

        if self.namespace_combo and self.namespace_label:
            filters_layout.addSpacing(16)
            filters_layout.addWidget(self.namespace_label)
            filters_layout.addWidget(self.namespace_combo)

        header_layout.addLayout(filters_layout)
        
        # Expose widgets to page if needed (BaseResourcePage expects them)
        self.page.search_bar = self.search_bar
        self.page.search_label = self.search_label
        self.page.namespace_combo = self.namespace_combo
        self.page.namespace_label = self.namespace_label

    def on_search_text_changed(self, text):
        """Schedule search via page's debouncer."""
        if hasattr(self.page, '_debounced_updater'):
            self.page._debounced_updater.schedule_update(
                'search_' + self.page.__class__.__name__,
                self.perform_search,
                delay_ms=SEARCH_DEBOUNCE_MS
            )

    def perform_search(self):
        """Execute the search logic."""
        if not self.search_bar:
            return
            
        search_text = self.search_bar.text().strip()

        if not search_text:
            self.clear_search_and_reload()
            return

        self.perform_global_search(search_text.lower())

    def clear_search_and_reload(self):
        """Clear search mode."""
        self._is_searching = False
        self._current_search_query = None
        
        # Update page state
        self.page._is_searching = False
        self.page._current_search_query = None
        
        # Reload normal data
        self.page.force_load_data()

    def perform_global_search(self, search_text):
        """Start global search."""
        try:
            self._is_searching = True
            self._current_search_query = search_text
            
            # Sync to page state
            self.page._is_searching = True
            self.page._current_search_query = search_text

            self.show_search_loading_message(search_text)
            self.start_global_search_thread(search_text)

        except Exception as e:
            logging.error(f"Error starting global search: {e}")
            self.filter_resources_linear(search_text)

    def show_search_loading_message(self, search_query):
        """Show loading message in the table."""
        try:
            if hasattr(self.page, 'table') and self.page.table:
                self.page.clear_table()
                self.page.table.setRowCount(1)

                item = QTableWidgetItem(
                    f"🔍 Searching for '{search_query}' across all resources...")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.page.table.setItem(0, 0, item)

                if self.page.table.columnCount() > 1:
                    self.page.table.setSpan(0, 0, 1, self.page.table.columnCount())

        except Exception as e:
            logging.debug(f"Error showing search loading message: {e}")

    def start_global_search_thread(self, search_text):
        """Initiate async search."""
        try:
            unified_loader = get_unified_resource_loader()

            if not self._search_signals_connected:
                # Disconnect old signals if attached to page directly previously, 
                # or just connect our new handler
                unified_loader.loading_completed.connect(self.on_search_results_loaded)
                unified_loader.loading_error.connect(self.on_search_error)
                self._search_signals_connected = True

            search_namespace = None if self.page.namespace_filter == "All Namespaces" else self.page.namespace_filter

            self.page._current_search_operation_id = unified_loader.load_resources_with_search_async(
                resource_type=self.page.resource_type,
                namespace=search_namespace,
                search_query=search_text
            )

            logging.info(
                f"Started global search for '{search_text}' in {self.page.resource_type}")

        except Exception as e:
            logging.error(f"Failed to start global search thread: {e}")
            self.filter_resources_linear(search_text)

    def on_search_results_loaded(self, resource_type, result):
        """Handle search results.

        NOTE: Unlike other signal handlers, we intentionally do NOT add an isVisible()
        check here. Search is user-initiated, and discarding results when the user
        briefly navigates away would be a UX regression. The _is_searching flag
        already provides sufficient protection against unwanted signal processing.
        """
        try:
            if (resource_type != self.page.resource_type or 
                not self._is_searching):
                return

            if not result.success:
                self.on_search_error(resource_type, result.error_message or "Search failed")
                return

            search_results = result.items or []
            
            # Update page display
            self.page._display_resources(search_results)
            self.page._update_items_count()

            if search_results:
                logging.info(f"Search found {len(search_results)} {resource_type} items.")
            else:
                logging.info(f"Search found no {resource_type} items.")

        except Exception as e:
            logging.error(f"Error processing search results: {e}")

    def on_search_error(self, resource_type, error_message):
        """Handle search error."""
        if resource_type != self.page.resource_type:
            return

        logging.error(f"Search error for {resource_type}: {error_message}")
        
        try:
            if hasattr(self.page, 'table') and self.page.table:
                self.page.clear_table()
                self.page.table.setRowCount(1)

                item = QTableWidgetItem(f"❌ Search failed: {error_message}")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.page.table.setItem(0, 0, item)

                if self.page.table.columnCount() > 1:
                    self.page.table.setSpan(0, 0, 1, self.page.table.columnCount())

        except Exception as e:
            logging.debug(f"Error showing search error message: {e}")

    def filter_resources_linear(self, search_text):
        """Fallback local filter."""
        if not search_text:
            self.page._display_resources(self.page.resources)
            return

        search_lower = search_text.lower()
        filtered = [r for r in self.page.resources
                    if search_lower in r.get("name", "").lower()
                    or search_lower in r.get("namespace", "").lower()]

        self.page._display_resources(filtered)
