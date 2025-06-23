from PyQt6.QtCore import QSize

class AppColors:
    # Base colors
    BG_DARK = "#1A1A1A"
    BG_DARKER = "#0D1117"
    BG_SIDEBAR = "#1e1e1e"
    BG_HEADER = "#1e1e1e"
    BG_MEDIUM = "#2d2d2d"
    BG_LIGHT = "#3a3a3a"

    # Text colors
    TEXT_LIGHT = "#ffffff"
    TEXT_SECONDARY = "#888888"
    TEXT_SUBTLE = "#8e9ba9"
    TEXT_LINK = "#4FC3F7"
    TEXT_DANGER = "#FF5252"
    TEXT_TABLE = "#e2e8f0"
    TEXT_SUCCESS = "#4CAF50"

    # Accent colors
    ACCENT_BLUE = "#0095ff"
    ACCENT_GREEN = "#4CAF50"
    ACCENT_ORANGE = "#FF5733"
    ACCENT_RED = "#E81123"
    ACCENT_PURPLE = "#8C33FF"

    # Border colors
    BORDER_COLOR = "#2d2d2d"
    BORDER_LIGHT = "#454545"
    BORDER_DARK = "#2a2a2a"

    # UI element colors
    CARD_BG = "#1e1e1e"
    TAB_INACTIVE = "#2d2d2d"
    HEADER_BG = "#252525"
    TABLE_HEADER = "#323232"

    # Hover states
    HOVER_BG = "rgba(255, 255, 255, 0.1)"
    HOVER_BG_DARKER = "rgba(255, 255, 255, 0.05)"
    SELECTED_BG = "rgba(33, 150, 243, 0.2)"
    DANGER_HOVER_BG = "rgba(255, 68, 68, 0.1)"

    # Status colors
    STATUS_ACTIVE = "#4CAF50"    # Green
    STATUS_AVAILABLE = "#00FF00"
    STATUS_DISCONNECTED = "#FF0000"  # Red
    STATUS_PENDING = "#FFA500"    # Orange
    STATUS_WARNING = "#FFC107"
    STATUS_PROGRESS = "#969efa"

    SEARCH_BAR_HEIGHT = 30
    SEARCH_BAR_MIN_WIDTH = 200

    # Search bar styling
    SEARCH_BAR_STYLE = """
        QLineEdit, QComboBox {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            padding: 5px 10px;
            font-size: 13px;
        }
        QLineEdit:hover, QComboBox:hover {
            border: 1px solid #555555;
        }
        QLineEdit:focus, QComboBox:focus {
            border: 1px solid #0078d7;
        }
    """


class AppConstants:
    # Layout size constants
    SIZES = {
        "SIDEBAR_WIDTH": 180,
        "TOPBAR_HEIGHT": 40,
        "ROW_HEIGHT": 32,
        "ICON_SIZE": 16,
        "ACTION_WIDTH": 40
    }

    # Events table column indices
    EVENTS_TABLE_COLUMNS = {
        "TYPE": 0,
        "MESSAGE": 1,
        "NAMESPACE": 2,
        "INVOLVED_OBJECT": 3,
        "SOURCE": 4,
        "COUNT": 5,
        "AGE": 6,
        "LAST_SEEN": 7,
        "ACTIONS": 8
    }

    # Releases table column indices
    RELEASES_TABLE_COLUMNS = {
        "CHECKBOX": 0,
        "NAME": 1,
        "NAMESPACE": 2,
        "CHART": 3,
        "REVISION": 4,
        "VERSION": 5,
        "APP_VERSION": 6,
        "STATUS": 7,
        "UPDATED": 8,
        "ACTIONS": 9
    }

    # Standardized spacing system
    SPACING = {
        "TINY": 4,
        "SMALL": 8,
        "MEDIUM": 16,
        "LARGE": 24,
        "XLARGE": 32
    }


class AppStyles:
    # Main application style
    MAIN_STYLE = f"""
        QMainWindow, QWidget {{
            background-color: {AppColors.BG_DARK};
            color: {AppColors.TEXT_LIGHT};
            font-family: 'Segoe UI', sans-serif;
        }}
        QTabWidget::pane {{
            border: none;
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
            padding: 8px 24px;
            border: none;
            margin-right: 2px;
            font-size: 13px;
        }}
        QTabBar::tab:selected {{
            color: {AppColors.TEXT_LIGHT};
            border-bottom: 2px solid {AppColors.ACCENT_BLUE};
        }}
        QTabBar::tab:hover:!selected {{
            color: {AppColors.TEXT_LIGHT};
        }}
    """

    UNIFIED_SCROLL_BAR_STYLE = """
        QScrollBar:vertical {
            background-color: transparent;
            width: 12px;
            margin: 0px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background-color: #6B7280;
            min-height: 30px;
            border-radius: 4px;
            margin: 2px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #9CA3AF;
        }
        QScrollBar::handle:vertical:pressed {
            background-color: #4B5563;
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
            width: 0px;
            background: none;
        }
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {
            background: none;
        }
        QScrollBar:horizontal {
            background-color: transparent;
            height: 12px;
            margin: 0px;
            border-radius: 4px;
        }
        QScrollBar::handle:horizontal {
            background-color: #6B7280;
            min-width: 30px;
            border-radius: 4px;
            margin: 2px;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: #9CA3AF;
        }
        QScrollBar::handle:horizontal:pressed {
            background-color: #4B5563;
        }
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {
            height: 0px;
            width: 0px;
            background: none;
        }
        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {
            background: none;
        }
    """

    # Preferences-specific styles
    PREFERENCES_MAIN_STYLE = f"""
        QWidget {{
            background-color: {AppColors.BG_SIDEBAR};
            color: {AppColors.TEXT_LIGHT};
            font-family: 'Segoe UI', Arial, sans-serif;
        }}
        QLabel {{
            color: {AppColors.TEXT_SUBTLE};
        }}
    """

    PROGRESS_BAR_STYLE = f"""
        QProgressBar {{
            background-color: {AppColors.BG_DARK};
            border: none;
            border-radius: 3px;
            height: 6px;
        }}
        QProgressBar::chunk {{
            background-color: {AppColors.ACCENT_BLUE};
            border-radius: 3px;
        }}
    """

    PREFERENCES_SIDEBAR_STYLE = f"""
        QWidget {{
            background-color: {AppColors.BG_DARKER};
        }}
    """

    PREFERENCES_HEADER_STYLE = f"""
        QLabel {{
            padding: 20px;
            color: {AppColors.TEXT_SUBTLE};
            font-size: 12px;
            font-weight: bold;
        }}
    """

    SECTION_HEADER_STYLE = f"""
        QLabel#header {{
            color: {AppColors.TEXT_LIGHT};
            font-size: 22px;
            font-weight: bold;
            padding-bottom: 10px;
        }}
    """

    SUBSECTION_HEADER_STYLE = f"""
        QLabel#sectionHeader {{
            color: {AppColors.TEXT_SUBTLE};
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            padding-top: 20px;
            padding-bottom: 10px;
        }}
    """

    BACK_BUTTON_STYLE = f"""
        QPushButton {{
            background-color: transparent;
            color: {AppColors.TEXT_SUBTLE};
            font-size: 20px;
            font-weight: bold;
            border: 1px solid {AppColors.BORDER_LIGHT};
            border-radius: 15px;
        }}
        QPushButton:hover {{
            background-color: {AppColors.BG_LIGHT};
            color: {AppColors.TEXT_LIGHT};
        }}
    """

    BACK_LABEL_STYLE = f"""
        QLabel {{
            color: {AppColors.TEXT_SUBTLE};
            font-size: 10px;
        }}
    """

    TEXT_STYLE = f"""
        QLabel {{
            color: {AppColors.TEXT_LIGHT};
            font-size: 14px;
        }}
    """

    DESCRIPTION_STYLE = f"""
        QLabel {{
            color: {AppColors.TEXT_SUBTLE};
            font-size: 13px;
            padding: 10px 0px;
        }}
    """

    STATUS_TEXT_STYLE = f"""
        QLabel {{
            color: {AppColors.TEXT_SUBTLE};
            font-size: 12px;
            margin-right: 10px;
        }}
    """

    STATUS_TEXT_ENABLED_STYLE = f"""
        QLabel {{
            color: {AppColors.ACCENT_BLUE};
            font-size: 12px;
            margin-right: 10px;
        }}
    """

    INPUT_STYLE = f"""
        QLineEdit {{
            background-color: {AppColors.HEADER_BG};
            border: 1px solid {AppColors.BORDER_DARK};
            border-radius: 4px;
            padding: 8px 12px;
            color: {AppColors.TEXT_LIGHT};
        }}
    """

    DROPDOWN_STYLE = f"""
        QComboBox {{
            background-color: {AppColors.HEADER_BG};
            border: 1px solid {AppColors.BORDER_DARK};
            border-radius: 4px;
            padding: 8px 12px;
            color: {AppColors.TEXT_LIGHT};
            min-width: 200px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        QComboBox:hover {{
            background-color: {AppColors.HOVER_BG};
        }}
    """

    DIVIDER_STYLE = f"""
        QFrame#divider {{
            background-color: {AppColors.BORDER_DARK};
            max-height: 1px;
            margin: 20px 0px;
        }}
    """

    SYNCED_ITEM_STYLE = f"""
        QLabel {{
            color: {AppColors.TEXT_LIGHT};
            font-size: 14px;
            background-color: {AppColors.HEADER_BG};
            padding: 8px;
            border-radius: 4px;
        }}
    """

    DELETE_BUTTON_STYLE = f"""
        QPushButton {{
            background-color: transparent;
            color: {AppColors.TEXT_SUBTLE};
            border: none;
            font-size: 16px;
        }}
        QPushButton:hover {{
            color: {AppColors.TEXT_DANGER};
        }}
    """

    BUTTON_PRIMARY_STYLE = f"""
        QPushButton {{
            background-color: {AppColors.ACCENT_BLUE};
            color: {AppColors.TEXT_LIGHT};
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: #3A8EDF;
        }}
    """

    BUTTON_SECONDARY_STYLE = f"""
        QPushButton {{
            background-color: {AppColors.HEADER_BG};
            color: {AppColors.TEXT_SUBTLE};
            border: 1px solid {AppColors.ACCENT_BLUE};
            padding: 8px 15px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {AppColors.BG_MEDIUM};
        }}
    """

    PLACEHOLDER_STYLE = f"""
        QLabel {{
            color: {AppColors.TEXT_SUBTLE};
            font-size: 14px;
            padding: 40px 0px;
        }}
    """

    # Table and related styles (used in ReplicaSetsPage and others)
    TABLE_STYLE = f"""
        QTableWidget {{
            background-color: {AppColors.CARD_BG};
            border: none;
            gridline-color: transparent;
            outline: none;
            color: {AppColors.TEXT_TABLE};
        }}
        QTableWidget::item {{
            padding: 10px 8px;
            /* Change 2: Remove the bottom border from each cell */
            border: none;
            outline: none;
            color: {AppColors.TEXT_TABLE};
        }}
        
        QTableWidget::item:hover {{
            background-color: rgba(53, 132, 228, 0.15); /* Light Blue with 15% opacity */
            
        }}
        
        QTableWidget::item:selected {{
            background-color: rgba(53, 132, 228, 0.15); /* Light Blue with 40% opacity */
            border: none;
        }}
        QHeaderView::section {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
            padding: 10px 8px;
            border: none;
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
            font-size: 12px;
            text-align: center;
        }}
        {UNIFIED_SCROLL_BAR_STYLE}
    """

    FOCUS_STYLE = f"""
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QPushButton:focus {{
            outline: 1px solid {AppColors.ACCENT_BLUE}99;
            outline-offset: -1px;
        }}
        QLabel, QTabWidget, QTabBar, QTabBar::tab {{
            outline: none !important;
            border: none !important;
        }}
        QTabBar::tab:focus, QTabBar::tab:selected:focus {{
            outline: none !important;
            border: none !important;
        }}
    """

    CUSTOM_HEADER_STYLE = f"""
        QHeaderView::section {{
            background-color: {AppColors.HEADER_BG};
            color: {AppColors.TEXT_SECONDARY};
            padding: 8px;
            border: none;
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
            font-size: 12px;
            text-align: center;
        }}
        QHeaderView::section:hover {{
            background-color: {AppColors.BG_MEDIUM};
        }}
    """

    CHECKBOX_STYLE = f"""
        QCheckBox {{
            spacing: 3px;
            background: transparent;
        }}
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            border: 1px solid {AppColors.TEXT_SECONDARY};
            border-radius: 3px;
            background: transparent;
        }}
        QCheckBox::indicator:checked {{
            background-color: {AppColors.ACCENT_BLUE};
            border-color: {AppColors.ACCENT_BLUE};
        }}
        QCheckBox::indicator:hover {{
            border-color: {AppColors.TEXT_LIGHT};
        }}
    """

    SELECT_ALL_CHECKBOX_STYLE = f"""
        QCheckBox {{
            spacing: 3px;
            background-color: transparent;  # Changed from {AppColors.HEADER_BG}
        }}
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            border: 1px solid {AppColors.TEXT_SECONDARY};
            border-radius: 3px;
            background: transparent;
        }}
        QCheckBox::indicator:checked {{
            background-color: {AppColors.ACCENT_BLUE};
            border-color: {AppColors.ACCENT_BLUE};
        }}
        QCheckBox::indicator:hover {{
            border-color: #888888;
        }}
    """

    ACTION_BUTTON_STYLE = f"""
        QToolButton {{
            background: transparent;
            padding: 2px;
            margin: 0;
            border: none;
        }}
        QToolButton:hover {{
            background-color: {AppColors.HOVER_BG};
            border-radius: 3px;
        }}
        QToolButton:pressed {{
            background-color: {AppColors.HOVER_BG_DARKER};
        }}
        QToolButton::menu-indicator {{
            image: none;
        }}
    """

    MENU_STYLE = f"""
        QMenu {{
            background-color: {AppColors.BG_DARKER};
            border: 1px solid {AppColors.BORDER_COLOR};
            border-radius: 6px;
            padding: 6px;
        }}
        QMenu::item {{
            color: {AppColors.TEXT_LIGHT};
            padding: 10px 24px 10px 36px;
            border-radius: 4px;
            font-size: 13px;
            margin: 2px 0px;
        }}
        QMenu::item:selected {{
            background-color: {AppColors.SELECTED_BG};
            color: {AppColors.TEXT_LIGHT};
        }}
        QMenu::item[dangerous="true"] {{
            color: {AppColors.TEXT_DANGER};
        }}
        QMenu::item[dangerous="true"]:selected {{
            background-color: {AppColors.DANGER_HOVER_BG};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {AppColors.BORDER_COLOR};
            margin: 6px 10px;
        }}
    """

    ACTION_CONTAINER_STYLE = """
        background-color: transparent;
        border: none;
        margin: 0;
        padding: 0;
    """

    ITEMS_COUNT_STYLE = f"""
        QLabel {{
            color: {AppColors.TEXT_SUBTLE};
            font-size: 12px;
            margin-left: 8px;
            font-family: 'Segoe UI';
        }}
    """

    # OverviewPage-specific styles
    EVENTS_TABLE_STYLE = f"""
        QTableWidget {{
            background-color: {AppColors.CARD_BG};
            color: {AppColors.TEXT_LIGHT};
            gridline-color: transparent;
            border: none;
        }}
        QHeaderView::section {{
            background-color: {AppColors.HEADER_BG};
            color: {AppColors.TEXT_LIGHT};
            padding: 8px;
            border: none;
        }}
        QTableWidget::item {{
            padding: 8px;
            border: none;
            background: transparent;
        }}
        QTableWidget::item:hover {{
            background-color: rgba(80, 80, 80, 120);
        }}
        QTableWidget::item:selected {{
            background-color: rgba(60, 60, 60, 150);
            color: {AppColors.TEXT_LIGHT};
        }}
        QTableWidget:focus {{
            outline: none;
        }}
        QHeaderView::section:hover {{
            background-color: {AppColors.BG_MEDIUM};
        }}
        {UNIFIED_SCROLL_BAR_STYLE}
    """

    STATUS_SCROLL_STYLE = f"""
        QScrollArea {{
            background-color: transparent;
            border: none;
        }}
        {UNIFIED_SCROLL_BAR_STYLE}
    """

    # Other existing styles
    TOOLTIP_STYLE = f"""
        QToolTip {{
            background-color: {AppColors.BG_DARKER};
            color: #FFFFFF;
            border: 1px solid {AppColors.BORDER_COLOR};
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }}
    """

    SEARCH_BAR_STYLE = f"""
        QLineEdit {{
            background-color: #333333;
            border: none;
            border-radius: 3px;
            color: {AppColors.TEXT_LIGHT};
            padding: 4px 10px;
            font-size: 12px;
        }}
        QLineEdit:focus {{
            background-color: #404040;
        }}
    """

    SEARCH_STYLE = f"""
        QLineEdit {{
            padding: 5px;
            background-color: {AppColors.BG_MEDIUM};
            border: 1px solid {AppColors.BORDER_COLOR};
            border-radius: 2px;
            color: {AppColors.TEXT_LIGHT};
        }}
    """

    GRAPH_FRAME_STYLE = f"""
        QFrame {{
            background-color: {AppColors.CARD_BG};
            border-radius: 4px;
            border: 1px solid {AppColors.BORDER_COLOR};
        }}
    """

    GRAPH_TITLE_STYLE = f"""
        QLabel {{
            color: {AppColors.TEXT_LIGHT};
            font-size: 14px;
            font-weight: bold;
        }}
    """

    @staticmethod
    def graph_value_style(color):
        return f"""
            QLabel {{
                color: {color};
                font-size: 16px;
                font-weight: bold;
            }}
        """

    HEADER_CONTAINER_STYLE = f"""
        background-color: {AppColors.HEADER_BG};
    """

    TITLE_STYLE = f"""
        QLabel {{
            font-size: 20px;
            font-weight: bold;
            color: {AppColors.TEXT_LIGHT};
        }}
    """

    TREE_WIDGET_STYLE = f"""
        QTreeWidget {{
            background-color: {AppColors.BG_DARK};
            border: none;
            outline: none;
            font-size: 13px;
            gridline-color: {AppColors.BORDER_DARK};
            margin: 0;
            padding: 0;
        }}
        QTreeWidget::item {{
            padding: 6px 4px;
            background-color: transparent;
        }}
        QTreeWidget::item:hover {{
            background-color: rgba(53, 132, 228, 0.15);
        }}
        QHeaderView::section {{
            background-color: {AppColors.TABLE_HEADER};
            color: {AppColors.TEXT_LIGHT};
            padding: 8px 8px;
            border-right: 1px solid {AppColors.BORDER_DARK};
            border-bottom: 1px solid {AppColors.BORDER_DARK};
            border-left: 1px solid {AppColors.BORDER_DARK};
            border-top: none;
            border-left: none;
            text-align: left;
            font-weight: bold;
        }}
        QHeaderView::section:first {{
            border-left: 1px solid {AppColors.BORDER_DARK};  /* Changed from 'border-left: none;' to add left border */
        }}
        QHeaderView::section:last {{
            padding: 0;
            text-align: center;
            width: {AppConstants.SIZES["ACTION_WIDTH"]}px;
            max-width: {AppConstants.SIZES["ACTION_WIDTH"]}px;
            min-width: {AppConstants.SIZES["ACTION_WIDTH"]}px;
        }}
        QTreeWidget::item:selected {{
            background-color: rgba(53, 132, 228, 0.15);
        }}
        QTreeWidget::branch {{
            border: none;
            border-image: none;
            outline: none;
        }}
        {UNIFIED_SCROLL_BAR_STYLE}
    """

    HEADER_STYLE = f"""
        #header {{
            background-color: {AppColors.BG_HEADER};
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
        }}
    """

    SIDEBAR_STYLE = f"""
        #sidebar_content {{
            background-color: {AppColors.BG_SIDEBAR};
            border-top: 1px solid {AppColors.BORDER_COLOR};
        }}
    """

    SIDEBAR_BUTTON_STYLE = f"""
        QPushButton {{
            background-color: transparent;
            color: {AppColors.TEXT_SUBTLE};
            text-align: left;
            padding: 10px 20px;
            border: none;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {AppColors.HOVER_BG};
            color: {AppColors.TEXT_LIGHT};
        }}
        QPushButton:checked {{
            background-color: {AppColors.HOVER_BG};
            color: {AppColors.TEXT_LIGHT};
            padding-left: 17px;
        }}
    """

    SIDEBAR_CONTAINER_STYLE = f"""
        QWidget {{
            background-color: {AppColors.BG_SIDEBAR};
            border-right: 2px solid {AppColors.BORDER_COLOR};
        }}
    """

    TITLE_BAR_STYLE = f"""
        QWidget {{
            background-color: {AppColors.BG_DARK};
            color: {AppColors.TEXT_LIGHT};
        }}
    """

    TITLE_BAR_BOTTOM_FRAME_STYLE = f"""
        QFrame {{
            background-color: {AppColors.BORDER_COLOR};
            min-height: 1px;
            max-height: 1px;
        }}
    """

    PANEL_STYLE = f"""
        QWidget {{
            background-color: {AppColors.CARD_BG};
            border-radius: 4px;
            border: 1px solid {AppColors.BORDER_COLOR};
        }}
    """

    STATUS_BOX_STYLE = f"""
        #statusBox {{
            background-color: {AppColors.CARD_BG};
            border-radius: 5px;
            border: 1px solid {AppColors.BORDER_COLOR};
        }}
        #statusBox:hover {{
            background-color: {AppColors.HOVER_BG_DARKER};
            border: 1px solid {AppColors.BORDER_COLOR};
        }}
    """

    STATUS_ICON_STYLE = f"""
        QLabel {{
            background-color: {AppColors.STATUS_ACTIVE};
            color: {AppColors.TEXT_LIGHT};
            font-size: 40px;
            border-radius: 40px;
            qproperty-alignment: AlignCenter;
        }}
    """

    STATUS_TITLE_STYLE = f"""
        QLabel {{
            color: {AppColors.TEXT_LIGHT};
            font-size: 16px;
            font-weight: 500;
            margin-top: 16px;
        }}
    """

    STATUS_SUBTITLE_STYLE = f"""
        QLabel {{
            color: {AppColors.TEXT_SECONDARY};
            font-size: 14px;
            margin-top: 4px;
        }}
    """

    RESOURCE_LABEL_USAGE_STYLE = f"color: {AppColors.STATUS_ACTIVE};"  # Green
    RESOURCE_LABEL_REQUESTS_STYLE = f"color: {AppColors.STATUS_PENDING};"  # Orange
    RESOURCE_LABEL_LIMITS_STYLE = f"color: {AppColors.ACCENT_PURPLE};"
    RESOURCE_LABEL_ALLOCATED_STYLE = f"color: {AppColors.ACCENT_ORANGE};"
    RESOURCE_LABEL_CAPACITY_STYLE = f"color: {AppColors.TEXT_SECONDARY};"
    RESOURCE_TITLE_STYLE = f"color: {AppColors.TEXT_LIGHT}; font-size: 16px;"

    EMPTY_LABEL_STYLE = f"""
        QLabel {{
            color: {AppColors.TEXT_SUBTLE};
            font-size: 16px;
            background-color: transparent;
        }}
    """

    HOME_ACTION_BUTTON_STYLE = f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            border-radius: 0;
            color: {AppColors.TEXT_SECONDARY};
            font-size: 20px;
            font-weight: bold;
            margin: 0;
            padding: 0;
            width: {AppConstants.SIZES["ACTION_WIDTH"]}px;
        }}
        QPushButton:hover {{
            color: {AppColors.TEXT_LIGHT};
        }}
        QPushButton:pressed, QPushButton:focus {{
            border: none;
            outline: none;
            background-color: transparent;
        }}
    """

    MESSAGE_NORMAL_STYLE = f"color: {AppColors.TEXT_LIGHT};"
    MESSAGE_WARNING_STYLE = f"color: {AppColors.STATUS_DISCONNECTED};"  # Red
    SOURCE_LINK_STYLE = f"color: {AppColors.TEXT_LINK};"

    TOP_BAR_STYLE = f"""
        QWidget {{
            background-color: {AppColors.BG_DARK};
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
        }}
    """

    BROWSER_LABEL_STYLE = f"font-weight: bold; font-size: 16px; color: {AppColors.TEXT_LIGHT};"
    ITEMS_LABEL_STYLE = f"color: {AppColors.TEXT_SUBTLE}; margin-left: 10px; font-size: 14px;"

    CONTENT_AREA_STYLE = f"""
        QFrame {{
            background-color: {AppColors.BG_DARK};
            border: none;
            padding: 0;
            margin: 0;
        }}
    """

    # ClusterPage-specific styles
    BAR_CHART_TOOLTIP_STYLE = f"""
        QToolTip {{
            background-color: #2a2a2a;
            color: {AppColors.TEXT_LIGHT};
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            padding: 5px;
            font-size: 12px;
        }}
    """

    CIRCULAR_INDICATOR_TOOLTIP_STYLE = f"""
        QToolTip {{
            background-color: #2a2a2a;
            color: {AppColors.TEXT_LIGHT};
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            padding: 5px;
            font-size: 12px;
        }}
    """

    CLUSTER_STATUS_BOX_STYLE = f"""
        #statusBox {{
            background-color: #262626;
            border-radius: 5px;
            border: 1px solid transparent;
        }}
        #statusBox:hover {{
            background-color: #333333;
            border: 1px solid #4d4d4d;
        }}
    """

    CLUSTER_RESOURCE_TITLE_STYLE = f"""
        color: {AppColors.TEXT_LIGHT};
        font-size: 16px;
    """

    CLUSTER_RESOURCE_LABEL_USAGE_STYLE = "color: #32dc32;"  # Green
    CLUSTER_RESOURCE_LABEL_REQUESTS_STYLE = "color: #50a0ff;"  # Blue
    CLUSTER_RESOURCE_LABEL_LIMITS_STYLE = "color: #c050ff;"  # Purple
    CLUSTER_RESOURCE_LABEL_ALLOCATED_STYLE = "color: #ff9428;"  # Orange
    CLUSTER_RESOURCE_LABEL_CAPACITY_STYLE = "color: #d0d0d0;"  # Light gray

    CLUSTER_CHART_PANEL_STYLE = f"""
        QWidget {{
            background-color: {AppColors.BG_SIDEBAR};
            border-radius: 4px;
        }}
    """

    CLUSTER_ACTIVE_BTN_STYLE = f"""
        QPushButton {{
            background-color: #333333;
            color: {AppColors.TEXT_LIGHT};
            border: none;
            padding: 6px 16px;
            font-size: 13px;
            border-radius: 4px;
        }}
    """

    CLUSTER_INACTIVE_BTN_STYLE = f"""
        QPushButton {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
            border: none;
            padding: 6px 16px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            color: {AppColors.TEXT_LIGHT};
        }}
    """

    CLUSTER_METRICS_PANEL_STYLE = f"""
        background-color: {AppColors.BG_SIDEBAR};
        border-radius: 4px;
    """

    CLUSTER_STATUS_PANEL_STYLE = f"""
        background-color: {AppColors.BG_SIDEBAR};
        border-radius: 4px;
    """

    CLUSTER_STATUS_ICON_STYLE = f"""
        background-color: {AppColors.STATUS_ACTIVE};
        color: {AppColors.TEXT_LIGHT};
        font-size: 40px;
        border-radius: 40px;
        qproperty-alignment: AlignCenter;
    """

    CLUSTER_STATUS_TITLE_STYLE = f"""
        color: {AppColors.TEXT_LIGHT};
        font-size: 20px;
        font-weight: 500;
        margin-top: 16px;
    """

    CLUSTER_STATUS_SUBTITLE_STYLE = f"""
        color: {AppColors.TEXT_SECONDARY};
        font-size: 14px;
        margin-top: 4px;
    """

    # Releases page specific styles
    RELEASES_TABLE_STYLE = f"""
        QTableWidget {{
            background-color: {AppColors.CARD_BG};
            border: none;
            gridline-color: {AppColors.BORDER_COLOR};
            outline: none;
            color: {AppColors.TEXT_TABLE};
        }}
        QTableWidget::item {{
            padding: 8px;
            border: none;
            outline: none;
        }}
        QTableWidget::item:hover {{
            background-color: {AppColors.HOVER_BG_DARKER};
            border-radius: 4px;
        }}
        QTableWidget::item:selected {{
            background-color: {AppColors.SELECTED_BG};
            border: none;
        }}
        QHeaderView::section {{
            background-color: {AppColors.HEADER_BG};
            color: {AppColors.TEXT_SECONDARY};
            padding: 8px;
            border: none;
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
            font-size: 12px;
            text-align: center;
        }}
        {UNIFIED_SCROLL_BAR_STYLE}
    """

    RELEASES_NAME_STYLE = f"""
        color: {AppColors.TEXT_TABLE};
        text-align: left;
    """

    RELEASES_STATUS_ACTIVE_STYLE = f"""
        color: {AppColors.STATUS_ACTIVE};
        text-align: left;
    """

    RELEASES_STATUS_INACTIVE_STYLE = f"""
        color: {AppColors.ACCENT_RED};
        text-align: left;
    """

    RELEASES_DEFAULT_CELL_STYLE = f"""
        color: {AppColors.TEXT_TABLE};
        text-align: center;
    """

    # TitleBar-specific styles
    TITLE_BAR_ICON_BUTTON_STYLE = f"""
        QToolButton {{
            background-color: transparent;
            color: {AppColors.TEXT_LIGHT};
            border: none;
            font-size: 16px;
        }}
        QToolButton:hover {{
            background-color: {AppColors.HOVER_BG};
            border-radius: 4px;
        }}
    """

    TITLE_BAR_WINDOW_BUTTON_STYLE = f"""
        QToolButton {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
            border: none;
            font-size: 10px;
            min-width: 46px;
            min-height: 30px;
            padding: 0px;
            margin: 0px;
        }}
        QToolButton:hover {{
            background-color: rgba(255, 255, 255, 0.1); /* Subtle hover effect */
            color: {AppColors.TEXT_LIGHT};
            border-radius: 0px; /* No rounded corners */
        }}
    """

    TITLE_BAR_CLOSE_BUTTON_STYLE = f"""
        QToolButton {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
            border: none;
            font-size: 10px;
            min-width: 46px;
            min-height: 30px;
            padding: 0px;
            margin: 0px;
        }}
        QToolButton:hover {{
            background-color: #E81123; /* Bright red on hover for close button */
            color: white;
            border-radius: 0px; /* No rounded corners */
        }}
    """

    # ================================
    # TERMINAL-SPECIFIC STYLES
    # ================================

    # Terminal unified widget style
    TERMINAL_TEXTEDIT = f"""
        QTextEdit {{
            background-color: #1E1E1E;
            color: #E0E0E0;
            border: none;
            selection-background-color: #264F78;
            selection-color: #E0E0E0;
            padding: 8px;
        }}
        {UNIFIED_SCROLL_BAR_STYLE}
    """

    # Terminal wrapper style
    TERMINAL_WRAPPER = f"""
        QWidget#terminal_wrapper {{
            background-color: {AppColors.BG_DARKER};
            border: 1px solid {AppColors.BORDER_COLOR};
            border-bottom: none;
        }}
    """

    # Terminal header content style
    TERMINAL_HEADER_CONTENT = f"""
        background-color: {AppColors.BG_DARKER};
        border-bottom: 1px solid {AppColors.BORDER_COLOR};
    """

    # Terminal tab label style
    TERMINAL_TAB_LABEL = f"""
        color: {AppColors.TEXT_SECONDARY};
        background: transparent;
        font-size: 12px;
        text-decoration: none;
        border: none;
        outline: none;
    """

    # Terminal tab close button style
    TERMINAL_TAB_CLOSE_BUTTON = f"""
        QPushButton {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
            border: none;
            font-size: 10px;
            font-weight: bold;
            padding: 0px;
            margin: 0px;
        }}
        QPushButton:hover {{
            background-color: #FF4D4D;
            color: white;
            border-radius: 8px;
        }}
    """

    # Terminal tab button style
    TERMINAL_TAB_BUTTON = f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            border-right: 1px solid {AppColors.BORDER_COLOR};
            border-left: 1px solid {AppColors.BORDER_COLOR};
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
            border-top: 1px solid {AppColors.BORDER_COLOR};
            padding: 0px 35px;
            margin: 0px;
        }}
        QPushButton:hover {{
            background-color: {AppColors.HOVER_BG};
        }}
        QPushButton:checked {{
            background-color: #1E1E1E;
            border-bottom: 2px solid {AppColors.ACCENT_BLUE};
        }}
    """

    # Terminal header button style
    TERMINAL_HEADER_BUTTON = f"""
        QToolButton {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
            border: none;
            font-size: 12px;
            padding: 4px;
        }}
        QToolButton:hover {{
            background-color: {AppColors.HOVER_BG};
            color: #ffffff;
            border-radius: 4px;
        }}
    """

    # Terminal resize handle style
    TERMINAL_RESIZE_HANDLE = """
        background-color: rgba(80, 80, 80, 0.3);
        border: none;
    """

    # Terminal shell dropdown style
    TERMINAL_SHELL_DROPDOWN = f"""
        QComboBox {{
            background-color: {AppColors.BG_DARKER};
            color: {AppColors.TEXT_SECONDARY};
            border: 1px solid {AppColors.BORDER_COLOR};
            padding: 2px 4px;
            font-size: 12px;
        }}
        QComboBox:hover {{
            background-color: {AppColors.HOVER_BG};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: url(icons/down_btn.svg);
            width: 12px;
            height: 12px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {AppColors.BG_DARKER};
            color: {AppColors.TEXT_SECONDARY};
            selection-background-color: {AppColors.HOVER_BG};
            border: 1px solid {AppColors.BORDER_COLOR};
        }}
        QComboBox QAbstractItemView::item {{
            cursor: pointer;
            padding: 6px 8px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            cursor: pointer;
        }}
    """

    # Deprecated terminal styles - kept for backwards compatibility
    # (These can be removed once all references are updated)
    TERMINAL_OUTPUT_STYLE = TERMINAL_TEXTEDIT  # Alias for backwards compatibility
    TERMINAL_INPUT_STYLE = f"""
        QTextEdit {{
            background-color: #252525;
            color: #E0E0E0;
            border: none;
            border-top: 1px solid #3D3D3D;
            padding: 5px 8px;
            selection-background-color: #264F78;
        }}
    """

    TERMINAL_WRAPPER_STYLE = TERMINAL_WRAPPER  # Alias for backwards compatibility

    TERMINAL_HEADER_STYLE = TERMINAL_HEADER_CONTENT  # Alias for backwards compatibility

    TERMINAL_HEADER_TITLE_STYLE = f"""
        QLabel {{
            color: {AppColors.TEXT_LIGHT};
            font-size: 14px;
            font-weight: bold;
        }}
    """

    TERMINAL_HEADER_BUTTON_STYLE = TERMINAL_HEADER_BUTTON  # Alias for backwards compatibility

    TERMINAL_TABS_CONTAINER_STYLE = f"""
        QWidget {{
            background-color: #252525;
            border-top: 1px solid {AppColors.BORDER_COLOR};
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
        }}
    """

    TERMINAL_NEW_TAB_BUTTON_STYLE = f"""
        QPushButton {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
            border: none;
            font-size: 16px;
            font-weight: bold;
            padding: 2px;
        }}
        QPushButton:hover {{
            background-color: {AppColors.HOVER_BG};
            color: {AppColors.TEXT_LIGHT};
            border-radius: 4px;
        }}
    """

    TERMINAL_TAB_LABEL_STYLE = TERMINAL_TAB_LABEL  # Alias for backwards compatibility

    TERMINAL_TAB_CLOSE_BUTTON_STYLE = TERMINAL_TAB_CLOSE_BUTTON  # Alias for backwards compatibility

    TERMINAL_TAB_BUTTON_STYLE = TERMINAL_TAB_BUTTON  # Alias for backwards compatibility

    # Splash Screen Styles
    SPLASH_CENTER_CONTAINER_STYLE = """
        QWidget#center_container {
            background-color: transparent;
            border-radius: 10px;
        }
    """

    SPLASH_ANIMATION_CONTAINER_STYLE = """
        QLabel#bg_container {
            background-color: transparent;
            border-radius: 10px;
        }
    """

    SPLASH_ANIMATION_FALLBACK_STYLE = """
        background-color: #1E1E2E; 
        border-radius: 10px;
        background-image: linear-gradient(135deg, #1E1E2E 0%, #2D2D44 100%);
    """

    SPLASH_LOGO_BASE_STYLE = """
        background-color: transparent;
    """

    SPLASH_LOGO_TEXT_FALLBACK_STYLE = """
        font-size: 36px;
        font-weight: bold;
        color: #FF6D3F;
    """

    SPLASH_DESCRIPTION_STYLE = """
        QLabel {
            color: #FFFFFF;
            font-size: 16px;
            background-color: transparent;
        }
    """

    SPLASH_LOADING_LABEL_STYLE = """
        QLabel {
            color: #D0D0D0;
            font-size: 14px;
            background-color: transparent;
        }
    """

    SPLASH_PROGRESS_BAR_STYLE = """
        QProgressBar {
            background-color: rgba(30, 30, 46, 150);
            color: #FFFFFF;
            border-radius: 5px;
            text-align: center;
            height: 20px;
        }
        QProgressBar::chunk {
            background-color: qlineargradient(spread:pad, x1:0, y1:0.5, x2:1, y2:0.5, stop:0 #FF6D3F, stop:1 #FF9F5B);
            border-radius: 5px;
        }
    """

    SPLASH_VERSION_LABEL_STYLE = """
        QLabel {
            color: #A0A0A0;
            font-size: 12px;
            margin-top: 10px;
            background-color: transparent;
        }
    """

    # Sidebar-specific styles
    NAV_MENU_DROPDOWN_STYLE = f"""
        QMenu {{
            background-color: #2d2d2d;
            border: 1px solid #444444;
            border-radius: 6px;
            padding: 5px;
        }}
        QMenu::item {{
            padding: 1px 16px;
            border-radius: 4px;
            margin: 2px 5px;
            color: #e0e0e0;
            font-size: 14px;
        }}
        QMenu::item:selected {{
            background-color: rgba(33, 150, 243, 0.15);
        }}
        QMenu::separator {{
            height: 1px;
            background-color: #444444;
            margin: 5px 10px;
        }}
    """

    SIDEBAR_TOGGLE_BUTTON_STYLE = f"""
        QToolButton {{
            background-color: transparent;
            border-top: none;
        }}
        QToolButton:hover {{
            background-color: rgba(255, 255, 255, 0.1);
        }}
    """

    NAV_ICON_BUTTON_EXPANDED_STYLE = """
        QToolButton {{
            background-color: {background_color};
            border: none;
            border-radius: 0;
            text-align: left;
        }}
        QToolButton:hover {{
            background-color: {hover_background_color};
        }}
    """

    NAV_ICON_BUTTON_COLLAPSED_STYLE = """
        QToolButton {{
            background-color: {background_color};
            color: {text_color};
            border: none;
            border-radius: 0;
            padding-left: 10px;
            text-align: left;
        }}
        QToolButton:hover {{
            background-color: {hover_background_color};
        }}
    """

    NAV_ICON_BUTTON_ICON_LABEL_STYLE = f"""
        QLabel {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
        }}
    """

    NAV_ICON_BUTTON_TEXT_LABEL_STYLE = f"""
        QLabel {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
        }}
    """

    NAV_ICON_BUTTON_DROPDOWN_LABEL_STYLE = f"""
        QLabel {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
        }}
    """

    SIDEBAR_BORDER_STYLE = "color: #444444;"

    SIDEBAR_CONTROLS_STYLE = f"""
        QWidget#sidebar_controls {{
        }}
    """

    # Icon-specific styles (from Icons.py)
    TEXT_ICON_SIZE = QSize(24, 24)
    TEXT_ICON_COLOR = AppColors.TEXT_LIGHT  # Previously hardcoded as #ffffff
    TEXT_ICON_FONT_SIZE = 12  # Previously size.width() // 2, now fixed for consistency

    TAG_ICON_SIZE = QSize(28, 16)
    TAG_ICON_RADIUS = 2
    TAG_ICON_TEXT_COLOR = "black"  # Kept as original hardcoded value

    LOGO_ICON_SIZE = QSize(24, 24)
    LOGO_ICON_RADIUS = 6
    LOGO_TEXT_COLOR = "black"  # Kept as original hardcoded value
    LOGO_START_COLOR = "#FF8A00"  # Original default
    LOGO_END_COLOR = "#FF5722"    # Original default

    APP_LOGO_SIZE = QSize(120, 30)

    # Header-specific styles (from Header.py)
    SEARCH_BAR_HEIGHT = 28
    SEARCH_BAR_MIN_WIDTH = 300

    HEADER_HEIGHT = 40
    HEADER_MARGIN_LEFT = 16
    HEADER_MARGIN_RIGHT = 16
    HEADER_SPACING = 16

    CLUSTER_DROPDOWN_WIDTH = 160
    CLUSTER_DROPDOWN_HEIGHT = 28
    CLUSTER_DROPDOWN_MIN_WIDTH = 200
    CLUSTER_DROPDOWN_MARGIN_LEFT = 12
    CLUSTER_DROPDOWN_MARGIN_RIGHT = 32
    CLUSTER_DROPDOWN_SPACING = 8
    CLUSTER_DROPDOWN_ARROW_WIDTH = 20
    CLUSTER_DROPDOWN_STYLE = f"""
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
    """
    CLUSTER_DROPDOWN_TEXT_STYLE = f"color: {AppColors.ACCENT_GREEN}; background: transparent;"
    CLUSTER_DROPDOWN_ARROW_STYLE = f"color: {AppColors.TEXT_SECONDARY}; background: transparent; padding-right: 8px;"

    FILTER_BUTTON_HEIGHT = 28
    FILTER_BUTTON_MARGIN_LEFT = 8
    FILTER_BUTTON_MARGIN_RIGHT = 24
    FILTER_BUTTON_SPACING = 4
    FILTER_BUTTON_ARROW_WIDTH = 10
    FILTER_BUTTON_STYLE = f"""
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
    """
    FILTER_BUTTON_ARROW_STYLE = f"color: {AppColors.TEXT_SECONDARY}; background: transparent;"

    # Detail Page-specific styles (from detail_page_component.py)
    DETAIL_PAGE_WIDTH = 450
    DETAIL_PAGE_MIN_WIDTH = 400
    DETAIL_PAGE_MAX_WIDTH = 800
    DETAIL_PAGE_SHADOW_BLUR_RADIUS = 20
    DETAIL_PAGE_SHADOW_COLOR = (0, 0, 0, 180)  # QColor tuple (r, g, b, a)
    DETAIL_PAGE_SHADOW_OFFSET_X = -5
    DETAIL_PAGE_SHADOW_OFFSET_Y = 0
    DETAIL_PAGE_STYLE = f"""
        background-color: {AppColors.BG_SIDEBAR};
        border-left: 1px solid {AppColors.BORDER_COLOR};
    """

    DETAIL_PAGE_HEADER_HEIGHT = 60
    DETAIL_PAGE_HEADER_MARGIN_LEFT = 15
    DETAIL_PAGE_HEADER_MARGIN_TOP = 10
    DETAIL_PAGE_HEADER_MARGIN_RIGHT = 15
    DETAIL_PAGE_HEADER_MARGIN_BOTTOM = 10
    DETAIL_PAGE_HEADER_STYLE = f"""
        background-color: {AppColors.BG_HEADER};
        border-bottom: 1px solid {AppColors.BORDER_COLOR};
    """

    DETAIL_PAGE_BACK_BUTTON_SIZE = 40
    DETAIL_PAGE_BACK_BUTTON_STYLE = f"""
        QPushButton {{
            background-color: transparent;
            color: {AppColors.TEXT_SUBTLE};
            font-size: 18px;
            font-weight: bold;
            border: 1px solid #3a3e42;
            border-radius: 20px;
        }}
        QPushButton:hover {{
            background-color: #3a3e42;
            color: {AppColors.TEXT_LIGHT};
        }}
    """

    DETAIL_PAGE_TITLE_STYLE = f"""
        color: {AppColors.TEXT_LIGHT};
        font-size: 16px;
        font-weight: bold;
        margin-left: 10px;
    """

    DETAIL_PAGE_LOADING_WIDTH = 100
    DETAIL_PAGE_LOADING_HEIGHT = 5
    DETAIL_PAGE_LOADING_STYLE = f"""
        QProgressBar {{
            background-color: {AppColors.BG_MEDIUM};
            border: none;
            border-radius: 2px;
        }}
        QProgressBar::chunk {{
            background-color: {AppColors.ACCENT_BLUE};
        }}
    """

    DETAIL_PAGE_RESIZE_HANDLE_WIDTH = 5
    DETAIL_PAGE_RESIZE_HANDLE_STYLE = "background-color: transparent;"

    DETAIL_PAGE_CONTENT_MARGIN = 20
    DETAIL_PAGE_CONTENT_SPACING = 10

    DETAIL_PAGE_SUMMARY_MARGIN_BOTTOM = 20
    DETAIL_PAGE_RESOURCE_NAME_STYLE = f"""
        font-size: 20px;
        font-weight: bold;
        color: {AppColors.TEXT_LIGHT};
    """
    DETAIL_PAGE_RESOURCE_INFO_STYLE = f"""
        font-size: 14px;
        color: {AppColors.TEXT_SUBTLE};
        margin-bottom: 10px;
    """
    DETAIL_PAGE_CREATION_TIME_STYLE = f"""
        font-size: 13px;
        color: {AppColors.TEXT_SUBTLE};
    """

    DETAIL_PAGE_DIVIDER_STYLE = f"background-color: {AppColors.BORDER_COLOR};"

    DETAIL_PAGE_SECTION_MARGIN = 20
    DETAIL_PAGE_SECTION_TITLE_STYLE = f"""
        font-size: 12px;
        font-weight: bold;
        color: {AppColors.TEXT_SUBTLE};
        text-transform: uppercase;
    """

    DETAIL_PAGE_STATUS_VALUE_RUNNING_STYLE = f"""
        font-size: 14px;
        font-weight: bold;
        color: {AppColors.STATUS_ACTIVE};
    """
    DETAIL_PAGE_STATUS_VALUE_PENDING_STYLE = f"""
        font-size: 14px;
        font-weight: bold;
        color: {AppColors.STATUS_WARNING};
    """
    DETAIL_PAGE_STATUS_VALUE_SUCCEEDED_STYLE = f"""
        font-size: 14px;
        font-weight: bold;
        color: #2196F3;
    """
    DETAIL_PAGE_STATUS_VALUE_FAILED_STYLE = f"""
        font-size: 14px;
        font-weight: bold;
        color: {AppColors.TEXT_DANGER};
    """
    DETAIL_PAGE_STATUS_TEXT_STYLE = f"""
        font-size: 14px;
        color: {AppColors.TEXT_LIGHT};
        margin-left: 10px;
    """

    DETAIL_PAGE_CONDITION_TYPE_WIDTH = 120
    DETAIL_PAGE_CONDITION_STATUS_WIDTH = 60
    DETAIL_PAGE_CONDITION_TYPE_STYLE = f"""
        font-size: 14px;
        color: {AppColors.TEXT_LIGHT};
    """
    DETAIL_PAGE_CONDITION_STATUS_TRUE_STYLE = f"""
        font-size: 14px;
        color: {AppColors.STATUS_ACTIVE};
    """
    DETAIL_PAGE_CONDITION_STATUS_FALSE_STYLE = f"""
        font-size: 14px;
        color: {AppColors.TEXT_DANGER};
    """
    DETAIL_PAGE_CONDITION_MESSAGE_STYLE = f"""
        font-size: 14px;
        color: {AppColors.TEXT_SUBTLE};
        margin-left: 10px;
    """
    DETAIL_PAGE_CONDITION_NO_DATA_STYLE = f"""
        font-size: 14px;
        color: {AppColors.TEXT_SUBTLE};
    """

    DETAIL_PAGE_LABELS_CONTENT_STYLE = f"""
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 14px;
        color: {AppColors.TEXT_LIGHT};
        margin-top: 10px;
    """

    DETAIL_PAGE_YAML_TEXT_STYLE = f"""
        QTextEdit {{
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13px;
            color: #E0E0E0;
            padding: 20px;
            background-color: {AppColors.BG_SIDEBAR};
            border: none;
        }}
        {UNIFIED_SCROLL_BAR_STYLE}
    """

    DETAIL_PAGE_EVENTS_LIST_STYLE = f"""
        QListWidget {{
            background-color: {AppColors.BG_SIDEBAR};
            border: none;
            padding: 5px;
        }}
        QListWidget::item {{
            border-bottom: 1px solid #333;
            padding: 10px;
        }}
        QListWidget::item:hover {{
            background-color: {AppColors.HOVER_BG_DARKER};
        }}
        {UNIFIED_SCROLL_BAR_STYLE}
    """

    DETAIL_PAGE_EVENT_ITEM_MARGIN = 5
    DETAIL_PAGE_EVENT_TYPE_NORMAL_STYLE = f"""
        color: {AppColors.STATUS_ACTIVE};
        font-weight: bold;
    """
    DETAIL_PAGE_EVENT_TYPE_WARNING_STYLE = f"""
        color: {AppColors.STATUS_WARNING};
        font-weight: bold;
    """
    DETAIL_PAGE_EVENT_REASON_STYLE = f"""
        color: #4A9EFF;
        font-weight: bold;
    """
    DETAIL_PAGE_EVENT_AGE_STYLE = f"""
        color: {AppColors.TEXT_SUBTLE};
    """
    DETAIL_PAGE_EVENT_MESSAGE_STYLE = f"""
        color: #E0E0E0;
    """

    DETAIL_PAGE_ANIMATION_DURATION = 300

    BASE_TITLE_STYLE = f"""
        font-size: 20px;
        font-weight: bold;
        color: {AppColors.TEXT_LIGHT};
    """

    BASE_COUNT_STYLE = f"""
        color: {AppColors.TEXT_SUBTLE};
        font-size: 12px;
        margin-left: 8px;
        font-family: 'Segoe UI';
    """

    BASE_CHECKBOX_STYLE = f"""
        QCheckBox {{
            margin: 0;
            padding: 0;
            background: transparent;
            height: 100%;
            width: 100%;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: none;
            background: transparent;
            subcontrol-position: center;
            subcontrol-origin: content;
        }}
        QCheckBox::indicator:unchecked {{
            image: url(icons/check_box_unchecked.svg);
        }}
        QCheckBox::indicator:checked {{
            image: url(icons/check_box_checked.svg);
            background-color: transparent;
        }}
        QCheckBox::indicator:hover {{
            opacity: 0.8;
        }}
    """

    EMPTY_STATE_STYLE = f"""
        background-color: {AppColors.CARD_BG};
        color: {AppColors.TEXT_SECONDARY};
        border-radius: 8px;
        border: 1px solid {AppColors.BORDER_COLOR};
    """

    # Add these two constants to your AppStyles class

    DETAIL_PAGE_OVERVIEW_STYLE = f"""
        QScrollArea {{
            background-color: {AppColors.BG_SIDEBAR};
            border: none;
            outline: none;
        }}
        {UNIFIED_SCROLL_BAR_STYLE}
    """

    DETAIL_PAGE_DETAILS_STYLE = f"""
        QScrollArea {{
            background-color: {AppColors.BG_SIDEBAR};
            border: none;
            outline: none;
        }}
        {UNIFIED_SCROLL_BAR_STYLE}
    """

class EnhancedStyles:
    # Typography hierarchy
    SECTION_HEADER = {
        'font_size': '16px',
        'font_weight': 'bold',
        'color': '#E8EAED',
        'letter_spacing': '0.5px',
        'text_transform': 'uppercase',
        'margin_bottom': '12px'
    }
    FIELD_LABEL = {
        'font_size': '13px',
        'font_weight': '500',
        'color': '#8AB4F8'
    }
    FIELD_VALUE = {
        'font_size': '13px',
        'font_weight': 'normal',
        'color': '#DADCE0',
        'line_height': '1.5'
    }
    PRIMARY_TEXT = {
        'font_size': '20px',
        'font_weight': 'bold',
        'color': '#FFFFFF'
    }
    SECONDARY_TEXT = {
        'font_size': '14px',
        'font_weight': 'normal',
        'color': '#9AA0A6'
    }
    # Spacing system
    SECTION_GAP = 24
    SUBSECTION_GAP = 16
    FIELD_GAP = 8
    CONTENT_PADDING = 20

    @staticmethod
    def get_section_header_style():
        return f"""
            QLabel {{
                font-size: {EnhancedStyles.SECTION_HEADER['font_size']};
                font-weight: {EnhancedStyles.SECTION_HEADER['font_weight']};
                color: {EnhancedStyles.SECTION_HEADER['color']};
                letter-spacing: {EnhancedStyles.SECTION_HEADER['letter_spacing']};
                margin-bottom: {EnhancedStyles.SECTION_HEADER['margin_bottom']};
            }}
        """

    @staticmethod
    def get_field_label_style():
        return f"""
            QLabel {{
                font-size: {EnhancedStyles.FIELD_LABEL['font_size']};
                font-weight: {EnhancedStyles.FIELD_LABEL['font_weight']};
                color: {EnhancedStyles.FIELD_LABEL['color']};
            }}
        """

    @staticmethod
    def get_field_value_style():
        return f"""
            QLabel {{
                font-size: {EnhancedStyles.FIELD_VALUE['font_size']};
                font-weight: {EnhancedStyles.FIELD_VALUE['font_weight']};
                color: {EnhancedStyles.FIELD_VALUE['color']};
                line-height: {EnhancedStyles.FIELD_VALUE['line_height']};
            }}
        """

    @staticmethod
    def get_primary_text_style():
        return f"""
            QLabel {{
                font-size: {EnhancedStyles.PRIMARY_TEXT['font_size']};
                font-weight: {EnhancedStyles.PRIMARY_TEXT['font_weight']};
                color: {EnhancedStyles.PRIMARY_TEXT['color']};
                padding: 4px 0px;
            }}
        """

    @staticmethod
    def get_secondary_text_style():
        return f"""
            QLabel {{
                font-size: {EnhancedStyles.SECONDARY_TEXT['font_size']};
                font-weight: {EnhancedStyles.SECONDARY_TEXT['font_weight']};
                color: {EnhancedStyles.SECONDARY_TEXT['color']};
                padding: 2px 0px;
            }}
        """