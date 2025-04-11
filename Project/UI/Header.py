import sys
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                             QToolButton, QMenu, QLineEdit)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QAction

from UI.Styles import AppColors, AppStyles
from UI.Icons import Icons

class SearchBar(QLineEdit):
    def __init__(self, placeholder_text, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        self.setFixedHeight(AppStyles.SEARCH_BAR_HEIGHT)
        self.setMinimumWidth(AppStyles.SEARCH_BAR_MIN_WIDTH)
        self.setStyleSheet(AppStyles.SEARCH_BAR_STYLE)

class Header(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # Main layout for the entire header (top + bottom)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create top section
        self.top_header = self.create_top_header()
        
        main_layout.addWidget(self.top_header)
    
    def create_top_header(self):
        top_header = QWidget()
        top_header.setObjectName("header")
        top_header.setFixedHeight(AppStyles.HEADER_HEIGHT)
        top_header.setStyleSheet(AppStyles.HEADER_STYLE)

        layout = QHBoxLayout(top_header)
        layout.setContentsMargins(AppStyles.HEADER_MARGIN_LEFT, 0, AppStyles.HEADER_MARGIN_RIGHT, 0)
        layout.setSpacing(AppStyles.HEADER_SPACING)

        # Create cluster dropdown menu
        cluster_menu = QMenu()
        cluster_menu.setStyleSheet(AppStyles.MENU_STYLE)

        # Add menu items
        cluster_menu.addAction("docker-desktop")
        cluster_menu.addSeparator()
        cluster_menu.addAction("dev-cluster")
        cluster_menu.addAction("staging-cluster")
        cluster_menu.addAction("production-cluster")

        # Cluster dropdown button
        self.cluster_dropdown = QToolButton()
        self.cluster_dropdown.setFixedSize(AppStyles.CLUSTER_DROPDOWN_WIDTH, AppStyles.CLUSTER_DROPDOWN_HEIGHT)
        self.cluster_dropdown.setMinimumWidth(AppStyles.CLUSTER_DROPDOWN_MIN_WIDTH)

        # Create horizontal layout for text and arrow
        button_layout = QHBoxLayout(self.cluster_dropdown)
        button_layout.setContentsMargins(AppStyles.CLUSTER_DROPDOWN_MARGIN_LEFT, 0, AppStyles.CLUSTER_DROPDOWN_MARGIN_RIGHT, 0)
        button_layout.setSpacing(AppStyles.CLUSTER_DROPDOWN_SPACING)

        # Text label
        text_label = QLabel("docker-desktop")
        text_label.setStyleSheet(AppStyles.CLUSTER_DROPDOWN_TEXT_STYLE)

        # Arrow label
        arrow_label = QLabel(Icons.DROPDOWN_ARROW)
        arrow_label.setFixedWidth(AppStyles.CLUSTER_DROPDOWN_ARROW_WIDTH)
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        arrow_label.setStyleSheet(AppStyles.CLUSTER_DROPDOWN_ARROW_STYLE)

        button_layout.addWidget(text_label)
        button_layout.addStretch()
        button_layout.addWidget(arrow_label)

        self.cluster_dropdown.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.cluster_dropdown.setMenu(cluster_menu)
        self.cluster_dropdown.setStyleSheet(AppStyles.CLUSTER_DROPDOWN_STYLE)

        # Create search bars
        search_bar = SearchBar("Search...", self)
        search_bar.setFixedHeight(AppStyles.SEARCH_BAR_HEIGHT)
        namespace_search = SearchBar("Search namespace...", self)
        namespace_search.setFixedHeight(AppStyles.SEARCH_BAR_HEIGHT)

        # Add all widgets to layout
        layout.addWidget(self.cluster_dropdown)
        layout.addStretch(1)
        layout.addWidget(search_bar)
        layout.addWidget(namespace_search)

        return top_header
      
    def create_filter_button(self, text):
        """Create filter dropdown buttons for the bottom header"""
        button = QToolButton()
        button.setText(text)
        button.setFixedHeight(AppStyles.FILTER_BUTTON_HEIGHT)
        
        # Create dropdown menu
        menu = QMenu()
        menu.setStyleSheet(AppStyles.MENU_STYLE)
        
        # Add generic menu items (would be customized based on the filter type)
        if "Status" in text:
            menu.addAction("All")
            menu.addAction("Available")
            menu.addAction("Running")
            menu.addAction("Pending")
            menu.addAction("Failed")
        elif "Type" in text:
            menu.addAction("All")
            menu.addAction("Pod")
            menu.addAction("Deployment")
            menu.addAction("Service")
        elif "Age" in text:
            menu.addAction("Any time")
            menu.addAction("Last hour")
            menu.addAction("Last day")
            menu.addAction("Last week")
            menu.addAction("Last month")
        elif "view" in text:
            menu.addAction("List view")
            menu.addAction("Card view")
            menu.addAction("Compact view")
        
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setMenu(menu)
        
        # Create a horizontal layout with button text and arrow
        layout = QHBoxLayout(button)
        layout.setContentsMargins(AppStyles.FILTER_BUTTON_MARGIN_LEFT, 0, AppStyles.FILTER_BUTTON_MARGIN_RIGHT, 0)
        layout.setSpacing(AppStyles.FILTER_BUTTON_SPACING)
        
        # Add arrow indicator
        arrow_label = QLabel(Icons.DROPDOWN_ARROW)
        arrow_label.setFixedWidth(AppStyles.FILTER_BUTTON_ARROW_WIDTH)
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        arrow_label.setStyleSheet(AppStyles.FILTER_BUTTON_ARROW_STYLE)
        
        layout.addStretch()
        layout.addWidget(arrow_label)
        
        button.setStyleSheet(AppStyles.FILTER_BUTTON_STYLE)
        
        return button
