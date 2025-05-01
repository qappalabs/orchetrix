"""
Detail Manager for ClusterView that handles showing and managing resource detail pages.
Improved version with better performance and animation handling.
"""

from PyQt6.QtCore import QObject, pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import QApplication

from .DetailPageComponent import DetailPage

class DetailManager(QObject):
    """
    Manages the detail page component for ClusterView.
    Handles showing and hiding resource details with improved performance.
    """
    # Signals
    resource_updated = pyqtSignal(str, str, str)  # Resource type, name, namespace
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # Create the detail page but don't show it yet
        self.detail_page = DetailPage(self.parent_window)
        
        # Connect signals
        self.detail_page.resource_updated_signal.connect(self.handle_resource_updated)
        
        # Track current resource
        self.current_resource_type = None
        self.current_resource_name = None
        self.current_resource_namespace = None
        
        # Pre-calculate sizes to avoid layout recalculation during animation
        self.init_sizing()
    
    def init_sizing(self):
        """Pre-calculate sizes to improve animation performance"""
        if self.parent_window:
            # Set the detail page height to match parent window
            self.detail_page.setFixedHeight(self.parent_window.height())
    def show_detail(self, resource_type, resource_name, namespace=None):
        """Show detail view for the specified resource with improved click handling"""
        # Store current resource info
        self.current_resource_type = resource_type
        self.current_resource_name = resource_name
        self.current_resource_namespace = namespace
        
        # Check if we're viewing the same resource
        if (self.detail_page.resource_type == resource_type and 
            self.detail_page.resource_name == resource_name and
            self.detail_page.resource_namespace == namespace and
            self.detail_page.isVisible()):
            # Just make sure it's positioned correctly and visible
            self.update_detail_position()
            return
        
        # Update the detail page height before showing
        if self.parent_window:
            self.detail_page.setFixedHeight(self.parent_window.height())
        
        # Show the detail page with new resource info
        self.detail_page.show_detail(resource_type, resource_name, namespace)
        
        # Ensure it's positioned correctly
        QTimer.singleShot(50, self.update_detail_position)
        
    def hide_detail(self):
        """Hide the detail view with cleanup"""
        # If the parent window has our event filter, remove it
        if self.parent_window and self.detail_page:
            self.parent_window.removeEventFilter(self.detail_page)
        
        self.detail_page.close_detail()
        
        # Clear current resource info
        self.current_resource_type = None
        self.current_resource_name = None
        self.current_resource_namespace = None
    def is_detail_visible(self):
        """Check if the detail view is currently visible"""
        return self.detail_page.isVisible()
    
    def handle_resource_updated(self, resource_type, resource_name, namespace):
        """Handle when a resource is updated in the detail view"""
        # Emit signal to notify listeners
        self.resource_updated.emit(resource_type, resource_name, namespace)
    
    def update_detail_position(self):
        """Update the position of the detail page when parent geometry changes"""
        if self.is_detail_visible() and self.parent_window:
            # Update height to match parent
            self.detail_page.setFixedHeight(self.parent_window.height())
            
            # Position at the right edge of the parent
            if self.detail_page.is_minimized:
                target_x = self.parent_window.width() - self.detail_page.minimized_width
                self.detail_page.move(target_x, 0)
            else:
                target_x = self.parent_window.width() - self.detail_page.width()
                self.detail_page.move(target_x, 0)