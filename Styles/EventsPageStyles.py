"""
EventsPage-specific styles
Contains styles that are unique to EventsPage and defined inline in the page.
"""

from UI.ThemeManager import get_theme_manager


def get_header_style():
    """Enhanced header style with better text visibility using current theme"""
    theme = get_theme_manager().get_current_theme()
    return f"""
            QHeaderView::section {{
                background-color: {theme.colors.HEADER_BG};
                color: #FFFFFF;
                padding: 10px 8px;
                border: none;
                border-bottom: 1px solid {theme.colors.BORDER_COLOR};
                border-right: 1px solid {theme.colors.BORDER_COLOR};
                font-size: 12px;
                font-weight: bold;
                text-align: center;
                margin: 0px;
            }}
            QHeaderView::section:hover {{
                background-color: {theme.colors.BG_MEDIUM};
                color: #FFFFFF;
            }}
            QHeaderView::section:first {{
                border-left: 1px solid {theme.colors.BORDER_COLOR};
                padding-left: 0px;
                margin-left: 0px;
            }}
            QHeaderView::section:pressed {{
                background-color: {theme.colors.BG_DARKER};
                color: #FFFFFF;
            }}
        """


def get_action_button_style():
    """Very compact button styling for action buttons using current theme"""
    theme = get_theme_manager().get_current_theme()
    return f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 3px;
                margin: 0px;
                color: {theme.colors.TEXT_SECONDARY};
            }}
            QToolButton:hover {{
                background-color: {theme.colors.HOVER_BG};
                color: {theme.colors.TEXT_LIGHT};
            }}
            QToolButton:pressed {{
                background-color: {theme.colors.HOVER_BG_DARKER};
            }}
            QToolButton::menu-indicator {{
                image: none;
                width: 0px;
                height: 0px;
            }}
        """


def get_menu_style():
    """Menu style for action button dropdown using current theme"""
    theme = get_theme_manager().get_current_theme()
    return f"""
            QMenu {{
                background-color: {theme.colors.BG_DARKER};
                border: 1px solid {theme.colors.BORDER_COLOR};
                border-radius: 6px;
                padding: 4px;
                color: {theme.colors.TEXT_LIGHT};
            }}
            QMenu::item {{
                color: {theme.colors.TEXT_LIGHT};
                padding: 8px 12px;
                border-radius: 3px;
                font-size: 12px;
                margin: 1px 0px;
                min-width: 80px;
            }}
            QMenu::item:selected {{
                background-color: {theme.colors.SELECTED_BG};
                color: {theme.colors.TEXT_LIGHT};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {theme.colors.BORDER_COLOR};
                margin: 3px 6px;
            }}
        """


ACTION_CONTAINER_STYLE = """
            QWidget {
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """


ACTION_CONTAINER_ACTIVE_STYLE = """
                    QWidget {
                        background-color: rgba(33, 150, 243, 0.08);
                        border-radius: 4px;
                    }
                """


ACTION_CONTAINER_INACTIVE_STYLE = """
                    QWidget {
                        background-color: transparent;
                        border: none;
                    }
                """
