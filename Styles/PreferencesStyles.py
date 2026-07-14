"""
Preferences-specific styles with theme-aware support.
Contains styles for the Preferences/Settings page including cards, inputs,
toggle switches, dropdowns, radio groups, sidebar nav, and scroll areas.
"""
from PyQt6.QtGui import QColor
from UI.ThemeManager import get_theme_manager

def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()

def get_main_style():
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: {theme.colors.BG_SIDEBAR};
            color: {theme.colors.TEXT_LIGHT};
            font-family: 'Segoe UI', Arial, sans-serif;
        }}
        QLabel {{
            color: {theme.colors.TEXT_SUBTLE};
        }}
    """

def get_sidebar_style():
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: {theme.colors.BG_DARKER};
        }}
    """

def get_header_style():
    theme = _get_theme()
    return f"""
        QLabel {{
            padding: 20px;
            color: {theme.colors.TEXT_SUBTLE};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
        }}
    """

def get_section_header_style():
    theme = _get_theme()
    return f"""
        QLabel#header {{
            color: {theme.colors.TEXT_LIGHT};
            font-size: 32px;
            font-weight: bold;
            letter-spacing: -0.5px;
            padding-bottom: 20px;
        }}
    """

def get_subsection_header_style():
    """Card title bar - small grey uppercase label (used inside cards)"""
    theme = _get_theme()
    return f"""
        QLabel#sectionHeader {{
            color: {theme.colors.TEXT_SUBTLE};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 0.8px;
            padding: 16px 24px 14px 24px;
            background-color: {theme.colors.BG_DARK};
            border-bottom: 1px solid {theme.colors.BORDER_LIGHT};
            border-top-left-radius: 11px;
            border-top-right-radius: 11px;
        }}
    """

def get_card_outer_style():
    """Outer QFrame for a settings card with rounded corners and border"""
    theme = _get_theme()
    return f"""
        QFrame#SettingsCard {{
            background-color: {theme.colors.BG_MEDIUM};
            border: 1px solid {theme.colors.BORDER_LIGHT};
            border-radius: 12px;
        }}
    """

def get_card_content_style():
    """Content widget inside a card - transparent so card bg shows through"""
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: transparent;
        }}
    """

def get_text_style():
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_LIGHT};
            font-size: 14px;
        }}
    """

def get_description_style():
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_SUBTLE};
            font-size: 13px;
            padding: 8px 0px 0px 0px;
        }}
    """

def get_status_text_style(enabled=False):
    theme = _get_theme()
    accent = getattr(theme.colors, 'ACCENT_ORANGE', '#FF5733')
    color = accent if enabled else theme.colors.TEXT_SUBTLE
    return f"""
        QLabel {{
            color: {color};
            font-size: 12px;
            margin-right: 10px;
        }}
    """

def get_input_style():
    theme = _get_theme()
    accent = getattr(theme.colors, 'ACCENT_ORANGE', '#FF5733')
    return f"""
        QLineEdit {{
            background-color: {theme.colors.BG_DARK};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 8px;
            padding: 10px 14px;
            color: {theme.colors.TEXT_LIGHT};
            font-size: 14px;
        }}
        QLineEdit:focus {{
            border: 1px solid {accent};
        }}
        QLineEdit:hover {{
            border-color: {accent};
        }}
    """

def get_dropdown_style():
    theme = _get_theme()
    accent = getattr(theme.colors, 'ACCENT_ORANGE', '#FF5733')
    _qc = QColor(accent)
    accent_light = f"rgba({_qc.red()}, {_qc.green()}, {_qc.blue()}, 31)"
    accent_selected = f"rgba({_qc.red()}, {_qc.green()}, {_qc.blue()}, 46)"
    return f"""
        QComboBox {{
            background-color: {theme.colors.BG_DARK};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 8px;
            padding: 10px 14px;
            color: {theme.colors.TEXT_LIGHT};
            font-size: 14px;
            min-width: 200px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        QComboBox:hover {{
            border-color: {accent};
        }}
        QComboBox:focus {{
            border-color: {accent};
        }}
        QComboBox:on {{
            border-color: {accent};
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {theme.colors.BG_MEDIUM};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 8px;
            outline: none;
            padding: 4px;
            color: {theme.colors.TEXT_LIGHT};
        }}
        QComboBox QAbstractItemView::item {{
            padding: 10px 16px;
            border-radius: 6px;
            margin: 2px 4px;
            color: {theme.colors.TEXT_LIGHT};
            min-height: 24px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {accent_light};
            color: {accent};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {accent_selected};
            color: {accent};
            font-weight: 600;
        }}
    """

def style_combo(combo):
    """Apply reliable styling for QComboBox popups in PyQt6.
    No-op for CustomComboBox (which styles itself)."""
    # CustomComboBox is self-styling — skip entirely
    try:
        from UI.CustomComboBox import CustomComboBox as _CCB
        if isinstance(combo, _CCB):
            return combo
    except ImportError:
        pass

    from PyQt6.QtWidgets import QStyledItemDelegate, QListView, QFrame

    combo.setStyleSheet(get_dropdown_style())
    combo.setItemDelegate(QStyledItemDelegate(combo))
    view = QListView()
    view.setFrameShape(QFrame.Shape.NoFrame)
    combo.setView(view)

    return combo


def get_divider_style():
    """Kept for compatibility but no longer used in the card layout"""
    theme = _get_theme()
    return f"""
        QFrame#divider {{
            background-color: {theme.colors.BORDER_LIGHT};
            max-height: 1px;
            margin: 8px 0px;
        }}
    """

def get_synced_item_style():
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_LIGHT};
            font-size: 14px;
            background-color: {theme.colors.HEADER_BG};
            padding: 8px;
            border-radius: 4px;
        }}
    """

def get_delete_button_style():
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {theme.colors.TEXT_SUBTLE};
            border: none;
            font-size: 16px;
        }}
        QPushButton:hover {{
            color: {theme.colors.TEXT_DANGER};
        }}
    """

def get_button_primary_style():
    """Primary button uses ACCENT_ORANGE per the design reference"""
    theme = _get_theme()
    accent = getattr(theme.colors, 'ACCENT_ORANGE', '#FF5733')
    _qc = QColor(accent)
    return f"""
        QPushButton {{
            background-color: {accent};
            color: #ffffff;
            border: none;
            padding: 10px 22px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {_qc.lighter(130).name()};
        }}
        QPushButton:pressed {{
            background-color: {_qc.darker(115).name()};
        }}
    """

def get_button_secondary_style():
    theme = _get_theme()
    accent = getattr(theme.colors, 'ACCENT_ORANGE', '#FF5733')
    return f"""
        QPushButton {{
            background-color: {theme.colors.HEADER_BG};
            color: {theme.colors.TEXT_SUBTLE};
            border: 1px solid {accent};
            padding: 8px 15px;
            border-radius: 8px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.BG_MEDIUM};
        }}
    """

def get_placeholder_style():
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_SUBTLE};
            font-size: 14px;
            padding: 40px 0px;
        }}
    """

def get_sidebar_button_style():
    """Sidebar nav buttons — active state uses ACCENT_ORANGE (SIDEBAR_ACTIVE_TEXT) with orange accent left border"""
    theme = _get_theme()
    accent = getattr(theme.colors, 'SIDEBAR_ACTIVE_TEXT', getattr(theme.colors, 'ACCENT_ORANGE', '#FF5733'))
    hover_bg = getattr(theme.colors, 'SIDEBAR_HOVER_BG', theme.colors.HOVER_BG)
    active_bg = getattr(theme.colors, 'SIDEBAR_HOVER_BG', theme.colors.HOVER_BG)
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {theme.colors.TEXT_SUBTLE};
            text-align: left;
            padding: 10px 16px;
            border: none;
            border-left: 3px solid transparent;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            margin: 2px 8px;
        }}
        QPushButton:hover {{
            background-color: {hover_bg};
            color: {theme.colors.TEXT_LIGHT};
        }}
        QPushButton:checked {{
            background-color: {active_bg};
            color: {accent};
            font-weight: 600;
            border-left: 3px solid {accent};
            border-radius: 0px 8px 8px 0px;
            margin-left: 0px;
            padding-left: 19px;
        }}
    """

def get_scroll_style():
    theme = _get_theme()
    scroll_area_style = f"""
        QScrollArea {{
            background-color: {theme.colors.BG_DARK};
            border: none;
            outline: none;
        }}
        QScrollArea > QWidget > QWidget {{
            background-color: {theme.colors.BG_DARK};
        }}
    """
    return scroll_area_style + theme.get_scrollbar_style()

def get_toggle_switch_colors():
    """Toggle switch uses ACCENT_ORANGE when checked"""
    theme = _get_theme()
    accent = getattr(theme.colors, 'ACCENT_ORANGE', '#FF5733')
    unchecked = getattr(theme.colors, 'TEXT_SECONDARY', '#888888')
    return {
        'checked_bg': accent,
        'unchecked_bg': unchecked,
        'circle': '#ffffff'
    }

def get_back_button_style():
    """Get theme-aware back button style"""
    return "QPushButton { background-color: transparent; border: none; }"

def get_radio_group_style():
    """Radio button group container"""
    theme = _get_theme()
    accent = getattr(theme.colors, 'ACCENT_ORANGE', '#FF5733')
    return f"""
        QWidget#RadioGroup {{
            background-color: {theme.colors.BG_DARK};
            border-radius: 8px;
            padding: 12px;
        }}
        QRadioButton {{
            color: {theme.colors.TEXT_LIGHT};
            font-size: 14px;
            font-weight: 500;
            spacing: 8px;
            background-color: transparent;
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 9px;
            border: 2px solid {theme.colors.BORDER_COLOR};
            background-color: {theme.colors.BG_DARK};
        }}
        QRadioButton::indicator:hover {{
            border-color: {accent};
        }}
        QRadioButton::indicator:checked {{
            background-color: {accent};
            border-color: {accent};
        }}
    """
