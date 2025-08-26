"""
Base class for all detail page sections with common functionality
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from abc import ABCMeta, abstractmethod
from typing import Optional, Dict, Any
import logging

from UI.Styles import AppStyles, AppColors


class QWidgetMeta(type(QWidget), ABCMeta):
    """Metaclass that combines QWidget's metaclass with ABCMeta"""
    pass


class BaseDetailSection(QWidget, metaclass=QWidgetMeta):
    """Base class for all detail page sections"""

    # Signals for communication with main DetailPage
    loading_started = pyqtSignal(str)  # section_name
    loading_finished = pyqtSignal(str)  # section_name
    error_occurred = pyqtSignal(str, str)  # section_name, error_message
    data_loaded = pyqtSignal(str, dict)  # section_name, data

    def __init__(self, section_name: str, kubernetes_client, parent=None):
        super().__init__(parent)
        self.section_name = section_name
        self.kubernetes_client = kubernetes_client
        self.resource_type = None
        self.resource_name = None
        self.resource_namespace = None
        self.current_data = None
        self.is_loading = False
        self._signals_connected = False

        self.setup_ui()

    def setup_ui(self):
        """Setup basic UI structure"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)

        # Error display
        self.error_widget = QLabel()
        self.error_widget.setStyleSheet(f"""
            QLabel {{
                color: #ff4444;
                background-color: rgba(255, 68, 68, 0.1);
                padding: 10px;
                border-radius: 4px;
                border: 1px solid rgba(255, 68, 68, 0.3);
            }}
        """)
        self.error_widget.setWordWrap(True)
        self.error_widget.hide()

        self.main_layout.addWidget(self.error_widget)
        self.main_layout.addWidget(self.content_widget)

    def show_loading(self):
        """Show loading state"""
        if not self.is_loading:
            self.is_loading = True
            self.error_widget.hide()
            self.loading_started.emit(self.section_name)

    def hide_loading(self):
        """Hide loading state"""
        if self.is_loading:
            self.is_loading = False
            self.loading_finished.emit(self.section_name)

    def show_error(self, error_message: str):
        """Show error message only for real errors, not missing resources"""
        self.hide_loading()
        
        # Don't show error for resources that don't exist in cluster
        if ("not found" in error_message.lower() or 
            "404" in error_message or
            "not available in this cluster" in error_message.lower()):
            # Just show that resource is not available
            self.error_widget.setText(f"This {self.section_name.lower()} information is not available for this resource")
            self.error_widget.setStyleSheet(f"""
                QLabel {{
                    color: #888888;
                    background-color: rgba(136, 136, 136, 0.1);
                    padding: 10px;
                    border-radius: 4px;
                    border: 1px solid rgba(136, 136, 136, 0.3);
                }}
            """)
        else:
            # Show actual errors in red
            self.error_widget.setText(f"Unable to load {self.section_name.lower()}: {error_message}")
            self.error_widget.setStyleSheet(f"""
                QLabel {{
                    color: #ff4444;
                    background-color: rgba(255, 68, 68, 0.1);
                    padding: 10px;
                    border-radius: 4px;
                    border: 1px solid rgba(255, 68, 68, 0.3);
                }}
            """)
        
        self.error_widget.show()
        self.error_occurred.emit(self.section_name, error_message)

    def clear_error(self):
        """Clear error message"""
        self.error_widget.hide()

    def set_resource(self, resource_type: str, resource_name: str, namespace: Optional[str] = None):
        """Set the resource information"""
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.resource_namespace = namespace
        self.current_data = None
        self.clear_error()

    def load_data(self):
        """Load data for this section - called when tab becomes active"""
        if not self.resource_type or not self.resource_name:
            return

        self.show_loading()

        # Start async data loading
        QTimer.singleShot(0, self._load_data_async)

    @abstractmethod
    def _load_data_async(self):
        """Abstract method for async data loading - implement in subclasses"""
        pass

    @abstractmethod
    def update_ui_with_data(self, data: Dict[str, Any]):
        """Abstract method for updating UI with loaded data - implement in subclasses"""
        pass

    @abstractmethod
    def clear_content(self):
        """Abstract method for clearing section content - implement in subclasses"""
        pass

    def handle_data_loaded(self, data: Dict[str, Any]):
        """Handle successful data loading"""
        self.current_data = data
        self.hide_loading()
        self.update_ui_with_data(data)
        self.data_loaded.emit(self.section_name, data)

    def handle_error(self, error_message: str):
        """Handle data loading error"""
        self.show_error(error_message)
        logging.error(f"{self.section_name} error: {error_message}")

    def connect_api_signals(self):
        """Safely connect to API signals"""
        if not self._signals_connected:
            self.kubernetes_client.resource_detail_loaded.connect(self.handle_api_data_loaded)
            self.kubernetes_client.error_occurred.connect(self.handle_api_error)
            self._signals_connected = True

    def disconnect_api_signals(self):
        """Safely disconnect from API signals - FIXED VERSION"""
        if not self._signals_connected:
            return

        try:
            if hasattr(self.kubernetes_client, 'resource_detail_loaded'):
                self.kubernetes_client.resource_detail_loaded.disconnect(self.handle_api_data_loaded)
            if hasattr(self.kubernetes_client, 'error_occurred'):
                self.kubernetes_client.error_occurred.disconnect(self.handle_api_error)
        except Exception as e:
            # ← IMPROVED ERROR HANDLING
            logging.debug(f"Signal disconnect error (non-critical): {e}")
        finally:
            # ← ALWAYS reset the flag
            self._signals_connected = False