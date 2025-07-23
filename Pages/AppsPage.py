"""
Simple Apps page with namespace dropdown and basic key-value inputs.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, 
    QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont

from UI.Styles import AppStyles, AppColors
from utils.kubernetes_client import get_kubernetes_client
from kubernetes.client.rest import ApiException
import logging


class NamespaceLoader(QThread):
    """Thread for loading namespaces asynchronously"""
    namespaces_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.kube_client = get_kubernetes_client()
    
    def run(self):
        try:
            if not self.kube_client or not self.kube_client.v1:
                self.error_occurred.emit("Kubernetes client not initialized")
                return
            
            # Load all namespaces
            namespaces_list = self.kube_client.v1.list_namespace()
            namespace_names = []
            
            for ns in namespaces_list.items:
                if ns.metadata and ns.metadata.name:
                    namespace_names.append(ns.metadata.name)
            
            # Sort namespaces alphabetically
            namespace_names.sort()
            self.namespaces_loaded.emit(namespace_names)
            
        except ApiException as e:
            self.error_occurred.emit(f"API error: {e.reason}")
        except Exception as e:
            self.error_occurred.emit(f"Failed to load namespaces: {str(e)}")


class AppsPage(QWidget):
    """Simple Apps page with proper header layout matching other pages"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()
        
        # Load namespaces after UI is set up
        QTimer.singleShot(100, self.load_namespaces)
    
    def setup_ui(self):
        """Setup the UI mimicking BaseResourcePage header layout"""
        # Main layout with standard margins and spacing (like BaseResourcePage)
        page_main_layout = QVBoxLayout(self)
        page_main_layout.setContentsMargins(16, 16, 16, 16)
        page_main_layout.setSpacing(16)
        
        # Create header layout (single line) exactly like BaseResourcePage
        header_controls_layout = QHBoxLayout()
        
        # Title and count (left side)
        self._create_title_and_count(header_controls_layout)
        
        # Filter controls (middle)
        self._add_filter_controls(header_controls_layout)
        
        # Stretch to push buttons to right
        header_controls_layout.addStretch(1)
        
        # Labels controls (right side, before refresh)
        self._add_labels_controls(header_controls_layout)
        
        # Refresh button (far right) - optional, matching other pages
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton { 
                background-color: #2d2d2d; 
                color: #ffffff; 
                border: 1px solid #3d3d3d;
                border-radius: 4px; 
                padding: 5px 10px; 
            }
            QPushButton:hover { 
                background-color: #3d3d3d; 
            }
            QPushButton:pressed { 
                background-color: #1e1e1e; 
            }
        """)
        header_controls_layout.addWidget(refresh_btn)
        
        # Add header to main layout
        page_main_layout.addLayout(header_controls_layout)
        
        # Add stretch to fill remaining space (no content area needed)
        page_main_layout.addStretch(1)
    
    def _create_title_and_count(self, layout):
        """Create title label only"""
        title_label = QLabel("Apps")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        
        layout.addWidget(title_label)
    
    def _add_filter_controls(self, header_layout):
        """Add namespace control in header"""
        filters_widget = QWidget()
        filters_layout = QHBoxLayout(filters_widget)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(10)
        
        # Add spacing to shift namespace right
        filters_layout.addSpacing(20)
        
        # Namespace control
        namespace_label = QLabel("Namespace:")
        namespace_label.setStyleSheet("color: #ffffff; font-size: 13px; margin-right: 5px;")
        filters_layout.addWidget(namespace_label)
        
        self.namespace_combo = QComboBox()
        self.namespace_combo.setFixedHeight(30)
        self.namespace_combo.setMinimumWidth(150)
        # Configure dropdown behavior to prevent upward opening
        self._configure_dropdown_behavior(self.namespace_combo)
        
        # Use the exact same style as other pages from AppStyles
        self.namespace_combo.setStyleSheet(AppStyles.COMBO_BOX_STYLE)
        self.namespace_combo.addItem("Loading...")
        self.namespace_combo.setEnabled(False)
        filters_layout.addWidget(self.namespace_combo)
        
        header_layout.addWidget(filters_widget)
    
    def _add_labels_controls(self, header_layout):
        """Add Labels controls with input fields to header"""
        # Labels label
        labels_label = QLabel("Labels:")
        labels_label.setStyleSheet("color: #ffffff; font-size: 13px; margin-right: 8px;")
        header_layout.addWidget(labels_label)
        
        # Key input (right side of Labels text)
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("key")
        self.key_input.setFixedHeight(30)
        self.key_input.setFixedWidth(100)  # Smaller width
        self.key_input.setStyleSheet("""
            QLineEdit { 
                padding: 3px 5px; 
                border: 1px solid #555; 
                border-radius: 4px; 
                background-color: #333; 
                color: white; 
                font-size: 12px;
            }
        """)
        header_layout.addWidget(self.key_input)
        
        # Add spacing between key and value inputs
        header_layout.addSpacing(5)
        
        # Value input (right side of key input)
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("value")
        self.value_input.setFixedHeight(30)
        self.value_input.setFixedWidth(100)  # Smaller width
        self.value_input.setStyleSheet("""
            QLineEdit { 
                padding: 3px 5px; 
                border: 1px solid #555; 
                border-radius: 4px; 
                background-color: #333; 
                color: white; 
                font-size: 12px;
            }
        """)
        header_layout.addWidget(self.value_input)
        
        # Plus button (right side of input fields)
        self.add_labels_btn = QPushButton("+")
        self.add_labels_btn.setFixedSize(30, 30)
        self.add_labels_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 15px;
                font-weight: bold;
                font-size: 18px;
                text-align: center;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        # Add some spacing before the button
        header_layout.addSpacing(8)
        header_layout.addWidget(self.add_labels_btn)
    
    def _configure_dropdown_behavior(self, combo_box):
        """Configure dropdown behavior to prevent upward opening (like other pages)"""
        try:
            # Set view to list view for consistency
            combo_box.view().setMinimumWidth(combo_box.minimumWidth())
            # Set maximum visible items
            combo_box.setMaxVisibleItems(10)
        except Exception as e:
            logging.debug(f"Could not configure dropdown behavior: {e}")
    
    # Content area methods removed since inputs are now in header
    
    def load_namespaces(self):
        """Load namespaces asynchronously"""
        self.namespace_loader = NamespaceLoader(self)
        self.namespace_loader.namespaces_loaded.connect(self.on_namespaces_loaded)
        self.namespace_loader.error_occurred.connect(self.on_namespace_error)
        self.namespace_loader.start()
    
    def on_namespaces_loaded(self, namespaces):
        """Handle loaded namespaces"""
        self.namespace_combo.blockSignals(True)
        self.namespace_combo.clear()
        self.namespace_combo.addItem("All Namespaces")
        self.namespace_combo.addItems(namespaces)
        
        # Set default namespace if available
        if "default" in namespaces:
            self.namespace_combo.setCurrentText("default")
        elif namespaces:
            self.namespace_combo.setCurrentIndex(1)
        else:
            self.namespace_combo.setCurrentText("All Namespaces")
        
        self.namespace_combo.blockSignals(False)
        self.namespace_combo.setEnabled(True)
        logging.info(f"Loaded {len(namespaces)} namespaces for Apps page")
    
    def on_namespace_error(self, error_message):
        """Handle namespace loading error"""
        self.namespace_combo.blockSignals(True)
        self.namespace_combo.clear()
        self.namespace_combo.addItem("All Namespaces")
        self.namespace_combo.addItem("default")
        self.namespace_combo.setCurrentText("default")
        self.namespace_combo.blockSignals(False)
        self.namespace_combo.setEnabled(True)
        logging.error(f"Failed to load namespaces for Apps page: {error_message}")