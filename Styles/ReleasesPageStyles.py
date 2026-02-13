"""
ReleasesPage-specific styles
Contains styles that are unique to ReleasesPage and defined inline in the page.
"""

from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


def get_upgrade_dialog_style():
    """Background style for upgrade dialog"""
    theme = _get_theme()
    return f"""
        background-color: {theme.colors.BG_DARK};
        color: {theme.colors.TEXT_LIGHT};
    """


def get_line_edit_style():
    """Shared style for QLineEdit input fields"""
    theme = _get_theme()
    return f"""
        QLineEdit {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 4px;
            padding: 8px;
            font-size: 13px;
        }}
        QLineEdit:focus {{
            border: 1px solid {theme.colors.ACCENT_BLUE};
        }}
    """


def get_chart_input_style():
    """Style for chart input field"""
    return get_line_edit_style()


def get_version_input_style():
    """Style for version input field"""
    return get_line_edit_style()


def get_values_editor_style():
    """Style for values editor text area"""
    theme = _get_theme()
    return f"""
        QTextEdit {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 4px;
            padding: 8px;
            font-size: 13px;
            font-family: Consolas, 'Courier New', monospace;
        }}
        QTextEdit:focus {{
            border: 1px solid {theme.colors.ACCENT_BLUE};
        }}
    """


def get_atomic_checkbox_style():
    """Style for atomic checkbox"""
    theme = _get_theme()
    return f"""
        QCheckBox {{
            color: {theme.colors.TEXT_LIGHT};
            font-size: 13px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
        }}
    """


def get_cancel_button_style():
    """Style for cancel button"""
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: {theme.colors.BG_LIGHT};
            color: {theme.colors.TEXT_LIGHT};
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.HOVER_BG};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.BG_MEDIUM};
        }}
    """


def get_upgrade_button_style():
    """Style for upgrade button (primary action)"""
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: {theme.colors.ACCENT_BLUE};
            color: {theme.colors.TEXT_LIGHT};
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.ACCENT_BLUE_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.ACCENT_BLUE_PRESSED};
        }}
    """


def get_loading_bar_style():
    """Style for loading progress bar"""
    theme = _get_theme()
    return f"""
        QProgressBar {{
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 3px;
            background-color: {theme.colors.BG_DARKER};
            height: 20px;
        }}
        QProgressBar::chunk {{
            background-color: {theme.colors.ACCENT_BLUE};
        }}
    """


def get_loading_text_style():
    """Style for loading text"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_LIGHT}; font-size: 14px;"


def get_empty_overlay_style():
    """Style for empty state overlay"""
    theme = _get_theme()
    return f"""
        color: {theme.colors.TEXT_SUBTLE};
        font-size: 16px;
        font-weight: bold;
        background-color: transparent;
        padding: 20px;
        margin: 20px;
    """


def get_action_container_style():
    """Style for action container"""
    return "background-color: transparent;"


def get_menu_style():
    """Style for context menu"""
    theme = _get_theme()
    return f"""
        QMenu {{
            background-color: {theme.colors.BG_MEDIUM};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 4px;
            padding: 4px;
        }}
        QMenu::item {{
            color: {theme.colors.TEXT_LIGHT};
            padding: 8px 24px 8px 36px;
            border-radius: 4px;
            font-size: 13px;
        }}
        QMenu::item:selected {{
            background-color: {theme.colors.SELECTED_BG};
            color: {theme.colors.TEXT_LIGHT};
        }}
        QMenu::item[dangerous="true"] {{
            color: {theme.colors.TEXT_DANGER};
        }}
        QMenu::item[dangerous="true"]:selected {{
            background-color: {theme.colors.DANGER_HOVER_BG};
        }}
    """


def get_form_label_style():
    """Style for form labels"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_LIGHT}; font-size: 14px;"


def get_dialog_title_style():
    """Style for dialog title"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_LIGHT}; font-size: 16px; font-weight: bold;"
