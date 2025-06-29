"""
Optimized Detail Manager for ClusterView that handles showing and managing resource detail pages.
Improved version with better performance, error handling, and code organization.
"""

from PyQt6.QtCore import QObject, pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import QApplication
from typing import Optional, Dict, Any

from .DetailPageComponent import DetailPageComponent

import logging

class DetailManager(QObject):
    """
    Manages the detail page component for ClusterView with optimized performance.
    Handles showing and hiding resource details with improved caching and state management.
    """

    # Signals
    resource_updated = pyqtSignal(str, str, str)  # Resource type, name, namespace
    refresh_main_page = pyqtSignal(str, str, str)  # resource_type, resource_name, namespace

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.parent_window = parent

        # Initialize core attributes
        self._detail_page: Optional[DetailPageComponent] = None  # Fixed: Changed DetailPage to DetailPageComponent
        self._current_resource: Dict[str, Optional[str]] = {
            'type': None,
            'name': None,
            'namespace': None
        }

        # Performance optimization: Pre-calculate sizes
        self._cached_height: Optional[int] = None

        # Lazy initialization flag
        self._is_initialized = False

    def _ensure_detail_page(self) -> DetailPageComponent:
        """Lazy initialization of detail page for better startup performance"""
        if self._detail_page is None:
            self._detail_page = DetailPageComponent(self.parent_window)
            self._detail_page.resource_updated_signal.connect(self._handle_resource_updated)

            # Connect the new refresh signal
            self._detail_page.refresh_main_page_signal.connect(self._handle_refresh_main_page)

            self._init_sizing()
            self._is_initialized = True

        return self._detail_page

    def _handle_refresh_main_page(self, resource_type: str, resource_name: str, namespace: str):
        """Handle request to refresh main page after YAML update"""
        logging.info(f"DetailManager: Requesting main page refresh for {resource_type}/{resource_name}")
        self.refresh_main_page.emit(resource_type, resource_name, namespace)

    def _init_sizing(self) -> None:
        """Pre-calculate sizes to improve animation performance"""
        if self.parent_window:
            self._cached_height = self.parent_window.height()
            if self._detail_page:
                self._detail_page.setFixedHeight(self._cached_height)

    def _update_cached_height(self) -> None:
        """Update cached height if parent window size changed"""
        if self.parent_window:
            new_height = self.parent_window.height()
            if new_height != self._cached_height:
                self._cached_height = new_height
                if self._detail_page:
                    self._detail_page.setFixedHeight(new_height)

    def show_detail(self, resource_type: str, resource_name: str,
                    namespace: Optional[str] = None, raw_data: Optional[Dict[str, Any]] = None) -> None:
        """Show detail view for the specified resource with optimized performance"""
        # Ensure detail page is created
        detail_page = self._ensure_detail_page()

        # Check if we're already viewing the same resource
        if self._is_same_resource(resource_type, resource_name, namespace) and detail_page.isVisible():
            self.update_detail_position()
            return

        # Update current resource tracking
        self._current_resource.update({
            'type': resource_type,
            'name': resource_name,
            'namespace': namespace
        })

        # Handle special data for events
        if raw_data and resource_type.lower() == "event":
            detail_page.event_raw_data = raw_data

        # Update height before showing
        self._update_cached_height()

        # Show the detail page
        detail_page.show_detail(resource_type, resource_name, namespace)

        # Position correctly with minimal delay
        QTimer.singleShot(25, self.update_detail_position)  # Reduced from 50ms

    def hide_detail(self) -> None:
        """Hide the detail view with proper cleanup"""
        if not self._detail_page:
            return

        # Remove event filter from parent if installed
        if self.parent_window:
            self.parent_window.removeEventFilter(self._detail_page)

        # Close detail page
        self._detail_page.close_detail()

        # Clear current resource tracking
        self._current_resource.update({
            'type': None,
            'name': None,
            'namespace': None
        })

    def is_detail_visible(self) -> bool:
        """Check if the detail view is currently visible"""
        return self._detail_page is not None and self._detail_page.isVisible()

    def update_detail_position(self) -> None:
        """Update the position of the detail page when parent geometry changes"""
        if not self.is_detail_visible() or not self.parent_window:
            return

        detail_page = self._detail_page

        # Update height to match parent
        self._update_cached_height()

        # Calculate position based on minimized state
        parent_width = self.parent_window.width()

        # Note: The new DetailPageComponent might not have isMinimized() method
        # Check if method exists before calling it
        if hasattr(detail_page, 'isMinimized') and detail_page.isMinimized():
            target_x = parent_width - getattr(detail_page, 'minimized_width', detail_page.width())
        else:
            target_x = parent_width - detail_page.width()

        detail_page.move(target_x, 0)

    def get_current_resource_info(self) -> Dict[str, Optional[str]]:
        """Get information about the currently displayed resource"""
        return self._current_resource.copy()

    def refresh_current_detail(self) -> None:
        """Refresh the current detail view if one is open"""
        if self.is_detail_visible() and self._current_resource['type']:
            current = self._current_resource
            self.show_detail(
                current['type'],
                current['name'],
                current['namespace']
            )

    # Private helper methods
    def _is_same_resource(self, resource_type: str, resource_name: str,
                          namespace: Optional[str]) -> bool:
        """Check if the given resource is the same as currently displayed"""
        current = self._current_resource
        return (current['type'] == resource_type and
                current['name'] == resource_name and
                current['namespace'] == namespace)

    def _handle_resource_updated(self, resource_type: str, resource_name: str, namespace: str) -> None:
        """Handle when a resource is updated in the detail view"""
        self.resource_updated.emit(resource_type, resource_name, namespace)

    # Properties for external access
    @property
    def current_resource_type(self) -> Optional[str]:
        """Get the current resource type"""
        return self._current_resource['type']

    @property
    def current_resource_name(self) -> Optional[str]:
        """Get the current resource name"""
        return self._current_resource['name']

    @property
    def current_resource_namespace(self) -> Optional[str]:
        """Get the current resource namespace"""
        return self._current_resource['namespace']

    def cleanup(self) -> None:
        """Clean up resources when manager is being destroyed"""
        if self._detail_page:
            self._detail_page.close()
            self._detail_page.deleteLater()
            self._detail_page = None

        self._current_resource.clear()
        self._cached_height = None