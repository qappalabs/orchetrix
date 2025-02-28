from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QToolButton, QMenu, QLineEdit
from PyQt6.QtCore import Qt

class SearchBar(QLineEdit):
    def __init__(self, placeholder_text, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        self.setFixedHeight(28)
        self.setMinimumWidth(300)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #333333;
                border: none;
                border-radius: 3px;
                color: #ffffff;
                padding: 4px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                background-color: #404040;
            }
        """)

class Header(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)

        self.bg_dark = "#1a1a1a"
        self.bg_sidebar = "#1e1e1e"
        self.bg_header = "#1e1e1e"
        self.text_light = "#ffffff"
        self.text_secondary = "#888888"
        self.accent_blue = "#0095ff"
        self.accent_green = "#4CAF50"
        self.border_color = "#2d2d2d"
        self.tab_inactive = "#2d2d2d"
        self.card_bg = "#1e1e1e"
        
        self.setup_ui()

    def setup_ui(self):
        # Set the header background and bottom border
        self.setStyleSheet(f"""
            background-color: {self.bg_header};
            border-bottom: 2px solid {self.border_color};
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        # Create cluster dropdown menu
        cluster_menu = QMenu()
        cluster_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.bg_sidebar};
                color: {self.text_light};
                border: 1px solid {self.border_color};
                border-radius: 4px;
                padding: 8px 0px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                font-size: 13px;
            }}
            QMenu::item:selected {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """)
        cluster_menu.addAction("docker-desktop")
        cluster_menu.addSeparator()
        cluster_menu.addAction("dev-cluster")
        cluster_menu.addAction("staging-cluster")
        cluster_menu.addAction("production-cluster")
        cluster_menu.setFixedWidth(200)
        
        # Create cluster dropdown button
        cluster_dropdown = QToolButton()
        cluster_dropdown.setFixedSize(200, 28)
        cluster_dropdown.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        cluster_dropdown.setMenu(cluster_menu)
        # Clear the tool button's text to avoid duplication
        cluster_dropdown.setText("")
        cluster_dropdown.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                background-color: rgba(255, 255, 255, 0.1);
                font-size: 13px;
                text-align: left;
                padding-left: 12px;
                padding-right: 32px;
                position: relative;
            }}
            QToolButton::menu-indicator {{
                image: none;
            }}
            QToolButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }}
        """)

        # Create horizontal layout for text and arrow inside the button
        button_layout = QHBoxLayout(cluster_dropdown)
        button_layout.setContentsMargins(12, 0, 40, 0)  # Increased right margin pushes the arrow further right
        button_layout.setSpacing(8)
        # Text label for cluster name
        text_label = QLabel("docker-desktop")
        text_label.setStyleSheet("color: #55c732; background: transparent;")
        # Arrow label
        arrow_label = QLabel("▼")
        arrow_label.setFixedWidth(20)
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        arrow_label.setStyleSheet(f"color: {self.text_secondary}; background: transparent; padding-right: 8px;")
        button_layout.addWidget(text_label)
        button_layout.addStretch()
        button_layout.addWidget(arrow_label)

        # Create search bars
        search_bar = SearchBar("Search...", self)
        namespace_search = SearchBar("Search namespace...", self)

        # Add widgets to header layout
        layout.addWidget(cluster_dropdown)
        layout.addStretch(1)
        layout.addWidget(search_bar)
        layout.addWidget(namespace_search)
