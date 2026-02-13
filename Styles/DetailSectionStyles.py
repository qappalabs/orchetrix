"""
Styles for DetailPageDetailsSection component.
Contains only page-specific unique styles.
Shared styles should be imported directly from UI.Styles.EnhancedStyles.
"""
from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


def get_scroll_area_style():
    """Scroll area style - uses unified AppStyles scrollbar for consistency"""
    from UI.Styles import AppStyles
    theme = _get_theme()
    return f"""
        QScrollArea {{
            background-color: {theme.colors.BG_SIDEBAR};
            border: none;
        }}
        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
    """


def get_content_style():
    """Details content widget style"""
    theme = _get_theme()
    return f"background-color: {theme.colors.BG_SIDEBAR}; border: none;"


def get_truncated_label_style():
    """Truncated data label style"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_SUBTLE}; font-style: italic;"


def get_nested_field_title_style(depth):
    """Nested field title style with dynamic margin"""
    theme = _get_theme()
    return f"""
        font-weight: bold;
        color: {theme.colors.TEXT_SECONDARY};
        margin-left: {depth * 10}px;
        margin-top: 10px;
    """


def get_item_title_style(depth):
    """Item title style for list items with dynamic margin"""
    theme = _get_theme()
    return f"""
        font-weight: normal;
        color: {theme.colors.TEXT_SUBTLE};
        margin-left: {(depth + 1) * 10}px;
    """


def get_more_items_label_style(depth):
    """More items label style with dynamic margin"""
    theme = _get_theme()
    return f"""
        color: {theme.colors.TEXT_SUBTLE};
        margin-left: {(depth + 1) * 10}px;
    """
