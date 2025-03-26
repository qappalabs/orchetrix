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
        self.setFixedHeight(28)
        self.setMinimumWidth(300)
        self.setStyleSheet(AppStyles.SEARCH_BAR_STYLE)

class Header(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # Main layout for the entire header (top + bottom)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create top and bottom sections
        self.top_header = self.create_top_header()
        
        main_layout.addWidget(self.top_header)
    
    def create_top_header(self):
        top_header = QWidget()
        top_header.setObjectName("header")
        top_header.setFixedHeight(40)
        
        # Add specific styling with bottom border
        top_header.setStyleSheet(f"""
            #header {{
                background-color: {AppColors.BG_HEADER};
                border-top: 1px solid {AppColors.BORDER_COLOR};
                border-bottom: 1px solid {AppColors.BORDER_COLOR};
            }}
        """)

        layout = QHBoxLayout(top_header)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        # Create cluster dropdown menu
        cluster_menu = QMenu()
        cluster_menu.setStyleSheet(AppStyles.MENU_STYLE)

        # Add menu items
        cluster_menu.addAction("docker-desktop")
        cluster_menu.addSeparator()
        cluster_menu.addAction("dev-cluster")
        cluster_menu.addAction("staging-cluster")
        cluster_menu.addAction("production-cluster")

        # Updated cluster dropdown button
        self.cluster_dropdown = QToolButton()
        self.cluster_dropdown.setFixedSize(160, 28)
        self.cluster_dropdown.setMinimumWidth(200)

        # Create horizontal layout for text and arrow
        button_layout = QHBoxLayout(self.cluster_dropdown)
        button_layout.setContentsMargins(12, 0, 32, 0)
        button_layout.setSpacing(8)

        # Text label
        text_label = QLabel("docker-desktop")
        text_label.setStyleSheet(f"color: {AppColors.ACCENT_GREEN}; background: transparent;")

        # Arrow label
        arrow_label = QLabel(Icons.DROPDOWN_ARROW)
        arrow_label.setFixedWidth(20)  # Fixed width for arrow
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        arrow_label.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; background: transparent; padding-right: 8px;")

        button_layout.addWidget(text_label)
        button_layout.addStretch()
        button_layout.addWidget(arrow_label)

        self.cluster_dropdown.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.cluster_dropdown.setMenu(cluster_menu)
        self.cluster_dropdown.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                background-color: {AppColors.HOVER_BG};
                font-size: 13px;
                text-align: left;
                padding-left: 12px;
                padding-right: 32px;
                position: relative;
                border-radius: 4px;
            }}
            QToolButton::menu-indicator {{
                image: none;
            }}
            QToolButton:hover {{
                background-color: {AppColors.HOVER_BG_DARKER};
            }}
        """)

        # Create search bars
        search_bar = SearchBar("Search...", self)
        search_bar.setFixedHeight(28)
        namespace_search = SearchBar("Search namespace...", self)
        namespace_search.setFixedHeight(28)

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
        button.setFixedHeight(28)
        
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
        layout.setContentsMargins(8, 0, 24, 0)
        layout.setSpacing(4)
        
        # Add arrow indicator
        arrow_label = QLabel(Icons.DROPDOWN_ARROW)
        arrow_label.setFixedWidth(10)  # Fixed width for arrow
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        arrow_label.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; background: transparent;")
        
        layout.addStretch()
        layout.addWidget(arrow_label)
        
        button.setStyleSheet(f"""
            QToolButton {{
                background-color: {AppColors.HOVER_BG};
                color: {AppColors.TEXT_LIGHT};
                border: none;
                border-radius: 3px;
                padding-left: 10px;
                padding-right: 20px;
                font-size: 12px;
                text-align: left;
            }}
            QToolButton:hover {{
                background-color: {AppColors.HOVER_BG_DARKER};
            }}
            QToolButton::menu-indicator {{
                image: none;
            }}
        """)
        
        return button