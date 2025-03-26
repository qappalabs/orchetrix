class AppColors:
    """
    Application color palette for consistent theming
    """
    # Base colors
    BG_DARK = "#1A1A1A"
    BG_DARKER = "#0D1117"
    BG_SIDEBAR = "#1e1e1e"
    BG_HEADER = "#1e1e1e"
    
    # Text colors
    TEXT_LIGHT = "#ffffff"
    TEXT_SECONDARY = "#888888"
    
    # Accent colors
    ACCENT_BLUE = "#0095ff"
    ACCENT_GREEN = "#4CAF50"
    ACCENT_ORANGE = "#FFA500"
    ACCENT_RED = "#E81123"
    
    # Border colors
    BORDER_COLOR = "#2d2d2d"
    
    # UI element colors
    CARD_BG = "#1e1e1e"
    TAB_INACTIVE = "#2d2d2d"
    
    # Hover states
    HOVER_BG = "rgba(255, 255, 255, 0.1)"
    HOVER_BG_DARKER = "rgba(255, 255, 255, 0.05)"
    
    # Status colors
    STATUS_ACTIVE = "#4CAF50"
    STATUS_AVAILABLE = "#00FF00"
    STATUS_DISCONNECTED = "#FF0000"
    STATUS_PENDING = "#FFA500"
    STATUS_WARNING = "#FFC107"


class AppStyles:
    """
    Application styles for different UI components
    """
    
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
    
    # Tooltip style
    TOOLTIP_STYLE = """
        QToolTip {
            background-color: #333333;
            color: #ffffff;
            border: 1px solid #444444;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
    """
    
    # Search bar styles
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
    
    # Button styles
    BUTTON_PRIMARY_STYLE = f"""
        QPushButton {{
            background-color: {AppColors.ACCENT_BLUE};
            color: white;
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
            background-color: #252a2e;
            color: {AppColors.TEXT_SECONDARY};
            border: 1px solid {AppColors.ACCENT_BLUE};
            padding: 8px 15px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {AppColors.HOVER_BG};
        }}
    """
    
    # Table styles
    TABLE_STYLE = f"""
        QTableWidget {{
            background-color: {AppColors.BG_DARK};
            border: none;
            gridline-color: transparent;
        }}
        QHeaderView::section {{
            background-color: {AppColors.BG_DARK};
            border: none;
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
            padding: 8px;
            color: white;
            text-align: left;
        }}
        QTableWidget::item {{
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
            padding: 4px;
        }}
    """
    
    # Dropdown/Combobox styles
    DROPDOWN_STYLE = f"""
        QComboBox {{
            background-color: #252a2e;
            border: 1px solid #333639;
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
    
    # Menu styles
    MENU_STYLE = f"""
        QMenu {{
            background-color: {AppColors.BG_SIDEBAR};
            color: {AppColors.TEXT_LIGHT};
            border: 1px solid {AppColors.BORDER_COLOR};
            border-radius: 4px;
            padding: 8px 0px;
        }}
        QMenu::item {{
            padding: 8px 24px;
            font-size: 13px;
        }}
        QMenu::item:selected {{
            background-color: {AppColors.HOVER_BG};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {AppColors.BORDER_COLOR};
            margin: 5px 0px;
        }}
    """
    
    # Header styles
    HEADER_STYLE = f"""
        #header {{
            background-color: {AppColors.BG_HEADER};
            border-top: 1px solid {AppColors.BORDER_COLOR};
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
        }}
    """
    
    # Sidebar styles
    SIDEBAR_STYLE = f"""
        #sidebar_content {{
            background-color: {AppColors.BG_SIDEBAR};
            border-top: 1px solid {AppColors.BORDER_COLOR};
        }}
    """
    
    # Titlebar styles
    TITLE_BAR_STYLE = f"""
        QWidget {{
            background-color: {AppColors.BG_DARKER};
            color: {AppColors.TEXT_LIGHT};
        }}
    """