from PyQt6.QtCore import QObject, pyqtSignal


class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._current_theme = "Dark"  # Match preferences dropdown values
        self._themes = {
            "Dark": self._get_dark_theme(),
            "Light": self._get_light_theme()
        }
    
    def get_current_theme(self):
        return self._themes[self._current_theme]
    
    def set_theme(self, theme_name: str):
        if theme_name in self._themes and self._current_theme != theme_name:
            self._current_theme = theme_name
            self.theme_changed.emit(theme_name)
    
    def apply_theme_to_widget(self, widget, component_type="default"):
        theme = self.get_current_theme()
        style = theme.get_component_style(component_type)
        if style:
            widget.setStyleSheet(style)
    
    def _get_dark_theme(self):
        return DarkTheme()
    
    def _get_light_theme(self):
        return LightTheme()
    
    def get_available_themes(self):
        return list(self._themes.keys())


class BaseTheme:
    """Base theme with shared style templates (structure only, no colors)"""
    
    def get_component_style(self, component_type):
        return getattr(self, f"get_{component_type}_style", lambda: "")()
    
    # Shared style templates - only structure, colors injected by themes
    @staticmethod
    def _button_template(bg_color, text_color, hover_color):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """
    
    @staticmethod
    def _table_template(bg_color, text_color, border_color, border_light, header_bg, header_text):
        return f"""
            QTableWidget {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                gridline-color: {border_light};
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {header_text};
                border: 1px solid {border_color};
            }}
        """
    
    @staticmethod
    def _widget_template(bg_color, text_color):
        return f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
            }}
        """
    
    @staticmethod
    def _sidebar_template(bg_color, border_color):
        return f"""
            QWidget {{
                background-color: {bg_color};
                border-right: 2px solid {border_color};
            }}
        """
    
    @staticmethod
    def _menu_template(bg_color, border_color, text_color, selected_bg):
        return f"""
            QMenu {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 6px;
            }}
            QMenu::item {{
                color: {text_color};
                padding: 10px 24px 10px 36px;
                border-radius: 4px;
                font-size: 13px;
                margin: 2px 0px;
            }}
            QMenu::item:selected {{
                background-color: {selected_bg};
                color: {text_color};
            }}
        """
    
    @staticmethod
    def _scrollbar_template(handle_color, handle_hover, handle_pressed):
        return f"""
            QScrollBar:vertical {{
                background-color: transparent;
                width: 12px;
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {handle_color};
                min-height: 30px;
                border-radius: 4px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {handle_hover};
            }}
            QScrollBar::handle:vertical:pressed {{
                background-color: {handle_pressed};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
                width: 0px;
                background: none;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QScrollBar:horizontal {{
                background-color: transparent;
                height: 12px;
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {handle_color};
                min-width: 30px;
                border-radius: 4px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {handle_hover};
            }}
            QScrollBar::handle:horizontal:pressed {{
                background-color: {handle_pressed};
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                height: 0px;
                width: 0px;
                background: none;
            }}
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """
    
    @staticmethod
    def _checkbox_template(border_color, checked_bg, checked_border, hover_border):
        return f"""
            QCheckBox {{
                spacing: 3px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid {border_color};
                border-radius: 3px;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background-color: {checked_bg};
                border-color: {checked_border};
            }}
            QCheckBox::indicator:hover {{
                border-color: {hover_border};
            }}
        """
    
    @staticmethod
    def _input_template(bg_color, border_color, text_color):
        return f"""
            QLineEdit {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 8px 12px;
                color: {text_color};
            }}
        """
    
    @staticmethod
    def _dropdown_template(bg_color, border_color, text_color, hover_bg):
        return f"""
            QComboBox {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 8px 12px;
                color: {text_color};
                min-width: 200px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox:hover {{
                background-color: {hover_bg};
            }}
        """
    
    @staticmethod
    def _button_secondary_template(bg_color, text_color, border_color, hover_bg):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                padding: 8px 15px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
        """
    
    @staticmethod
    def _sidebar_button_template(bg_color, text_color, hover_bg, active_bg):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                text-align: left;
                padding: 10px 20px;
                border: none;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            QPushButton:checked {{
                background-color: {active_bg};
                padding-left: 17px;
            }}
        """
    
    @staticmethod
    def _action_button_template(bg_color, hover_bg, pressed_bg):
        return f"""
            QToolButton {{
                background: {bg_color};
                padding: 2px;
                margin: 0;
                border: none;
            }}
            QToolButton:hover {{
                background-color: {hover_bg};
                border-radius: 3px;
            }}
            QToolButton:pressed {{
                background-color: {pressed_bg};
            }}
            QToolButton::menu-indicator {{
                image: none;
            }}
        """
    
    @staticmethod
    def _panel_template(bg_color, border_color):
        return f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: 4px;
                border: 1px solid {border_color};
            }}
        """
    
    @staticmethod
    def _header_template(bg_color, border_color):
        return f"""
            QWidget {{
                background-color: {bg_color};
                border-bottom: 1px solid {border_color};
            }}
        """
    
    @staticmethod
    def _progress_bar_template(bg_color, chunk_color):
        return f"""
            QProgressBar {{
                background-color: {bg_color};
                border: none;
                border-radius: 3px;
                height: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {chunk_color};
                border-radius: 3px;
            }}
        """
    
    @staticmethod
    def _tooltip_template(bg_color, text_color, border_color):
        return f"""
            QToolTip {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
            }}
        """
    
    @staticmethod
    def _search_bar_template(bg_color, text_color, border_color, focus_border):
        return f"""
            QLineEdit {{
                background-color: {bg_color};
                border: none;
                border-radius: 3px;
                color: {text_color};
                padding: 4px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                background-color: {focus_border};
            }}
        """
    
    @staticmethod
    def _tree_widget_template(bg_color, text_color, border_color, header_bg, hover_bg, selected_bg):
        return f"""
            QTreeWidget {{
                background-color: {bg_color};
                border: none;
                outline: none;
                font-size: 13px;
                color: {text_color};
            }}
            QTreeWidget::item {{
                padding: 6px 4px;
                background-color: transparent;
            }}
            QTreeWidget::item:hover {{
                background-color: {hover_bg};
            }}
            QTreeWidget::item:selected {{
                background-color: {selected_bg};
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {text_color};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {border_color};
            }}
        """
    
    @staticmethod
    def _status_box_template(bg_color, border_color, hover_bg, hover_border):
        return f"""
            #statusBox {{
                background-color: {bg_color};
                border-radius: 5px;
                border: 1px solid {border_color};
            }}
            #statusBox:hover {{
                background-color: {hover_bg};
                border: 1px solid {hover_border};
            }}
        """
    
    @staticmethod
    def _title_style_template(text_color, font_size):
        return f"""
            QLabel {{
                font-size: {font_size};
                font-weight: bold;
                color: {text_color};
            }}
        """
    
    @staticmethod
    def _divider_template(bg_color):
        return f"""
            QFrame#divider {{
                background-color: {bg_color};
                max-height: 1px;
                margin: 20px 0px;
            }}
        """
    
    @staticmethod
    def _delete_button_template(bg_color, text_color, hover_color):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                font-size: 16px;
            }}
            QPushButton:hover {{
                color: {hover_color};
            }}
        """
    
    @staticmethod
    def _empty_label_template(text_color, bg_color):
        return f"""
            QLabel {{
                color: {text_color};
                font-size: 16px;
                background-color: {bg_color};
            }}
        """
    
    @staticmethod
    def _text_style_template(text_color, font_size):
        return f"""
            QLabel {{
                color: {text_color};
                font-size: {font_size};
            }}
        """
    
    @staticmethod
    def _description_style_template(text_color):
        return f"""
            QLabel {{
                color: {text_color};
                font-size: 13px;
                padding: 10px 0px;
            }}
        """
    
    @staticmethod
    def _placeholder_template(text_color):
        return f"""
            QLabel {{
                color: {text_color};
                font-size: 14px;
                padding: 40px 0px;
            }}
        """
    
    @staticmethod
    def _back_button_template(bg_color, text_color, border_color, hover_bg, hover_text):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                font-size: 20px;
                font-weight: bold;
                border: 1px solid {border_color};
                border-radius: 15px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                color: {hover_text};
            }}
        """
    
    @staticmethod
    def _empty_state_template(bg_color, text_color, border_color):
        return f"""
            background-color: {bg_color};
            color: {text_color};
            border-radius: 8px;
            border: 1px solid {border_color};
        """
    
    @staticmethod
    def _terminal_textedit_template(bg_color, text_color, selection_bg):
        return f"""
            QTextEdit {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                selection-background-color: {selection_bg};
                padding: 8px;
            }}
        """
    
    @staticmethod
    def _terminal_wrapper_template(bg_color, border_color):
        return f"""
            QWidget#terminal_wrapper {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-bottom: none;
            }}
        """
    
    @staticmethod
    def _terminal_header_template(bg_color, border_color):
        return f"""
            background-color: {bg_color};
            border-bottom: 1px solid {border_color};
        """
    
    @staticmethod
    def _terminal_tab_button_template(bg_color, border_color, hover_bg, checked_bg, accent_color):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                padding: 0px 35px;
                margin: 0px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            QPushButton:checked {{
                background-color: {checked_bg};
                border-bottom: 2px solid {accent_color};
            }}
        """
    
    @staticmethod
    def _graph_frame_template(bg_color, border_color):
        return f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 4px;
                border: 1px solid {border_color};
            }}
        """
    
    @staticmethod
    def _content_area_template(bg_color):
        return f"""
            QFrame {{
                background-color: {bg_color};
                border: none;
                padding: 0;
                margin: 0;
            }}
        """
    
    @staticmethod
    def _top_bar_template(bg_color, border_color):
        return f"""
            QWidget {{
                background-color: {bg_color};
                border-bottom: 1px solid {border_color};
            }}
        """
    
    @staticmethod
    def _focus_style_template(accent_color):
        return f"""
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QPushButton:focus {{
                outline: 1px solid {accent_color}99;
                outline-offset: -1px;
            }}
            QLabel, QTabWidget, QTabBar, QTabBar::tab {{
                outline: none !important;
                border: none !important;
            }}
        """
    
    @staticmethod
    def _synced_item_template(bg_color, text_color):
        return f"""
            QLabel {{
                color: {text_color};
                font-size: 14px;
                background-color: {bg_color};
                padding: 8px;
                border-radius: 4px;
            }}
        """
    
    @staticmethod
    def _status_text_template(text_color, font_size):
        return f"""
            QLabel {{
                color: {text_color};
                font-size: {font_size};
                margin-right: 10px;
            }}
        """
    
    @staticmethod
    def _detail_page_style_template(bg_color, border_color):
        return f"""
            background-color: {bg_color};
            border-left: 1px solid {border_color};
        """
    
    @staticmethod
    def _detail_page_header_template(bg_color, border_color):
        return f"""
            background-color: {bg_color};
            border-bottom: 1px solid {border_color};
        """
    
    @staticmethod
    def _detail_page_yaml_template(bg_color, text_color):
        return f"""
            QTextEdit {{
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                color: {text_color};
                padding: 20px;
                background-color: {bg_color};
                border: none;
            }}
        """
    
    @staticmethod
    def _nav_menu_dropdown_template(bg_color, border_color, text_color, selected_bg):
        return f"""
            QMenu {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 1px 16px;
                border-radius: 4px;
                margin: 2px 5px;
                color: {text_color};
                font-size: 14px;
            }}
            QMenu::item:selected {{
                background-color: {selected_bg};
            }}
        """
    
    @staticmethod
    def _title_bar_style_template(bg_color, text_color):
        return f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
            }}
        """
    
    @staticmethod
    def _events_table_template(bg_color, text_color, header_bg, hover_bg, selected_bg):
        return f"""
            QTableWidget {{
                background-color: {bg_color};
                color: {text_color};
                gridline-color: transparent;
                border: none;
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {text_color};
                padding: 8px;
                border: none;
            }}
            QTableWidget::item:hover {{
                background-color: {hover_bg};
            }}
            QTableWidget::item:selected {{
                background-color: {selected_bg};
            }}
        """
    
    @staticmethod
    def _releases_table_template(bg_color, text_color, header_bg, hover_bg, selected_bg, border_color):
        return f"""
            QTableWidget {{
                background-color: {bg_color};
                border: none;
                gridline-color: {border_color};
                outline: none;
                color: {text_color};
            }}
            QTableWidget::item:hover {{
                background-color: {hover_bg};
                border-radius: 4px;
            }}
            QTableWidget::item:selected {{
                background-color: {selected_bg};
                border: none;
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {text_color};
                padding: 8px;
                border: none;
                font-size: 12px;
                text-align: center;
            }}
        """
    
    @staticmethod
    def _cluster_status_box_template(bg_color, hover_bg, hover_border):
        return f"""
            #statusBox {{
                background-color: {bg_color};
                border-radius: 5px;
                border: 1px solid transparent;
            }}
            #statusBox:hover {{
                background-color: {hover_bg};
                border: 1px solid {hover_border};
            }}
        """
    
    @staticmethod
    def _cluster_chart_panel_template(bg_color):
        return f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: 4px;
            }}
        """
    
    @staticmethod
    def _items_count_template(text_color):
        return f"""
            QLabel {{
                color: {text_color};
                font-size: 12px;
                margin-left: 8px;
                font-family: 'Segoe UI';
            }}
        """
    
    @staticmethod
    def _section_header_template(text_color):
        return f"""
            QLabel#header {{
                color: {text_color};
                font-size: 22px;
                font-weight: bold;
                padding-bottom: 10px;
            }}
        """
    
    @staticmethod
    def _subsection_header_template(text_color):
        return f"""
            QLabel#sectionHeader {{
                color: {text_color};
                font-size: 12px;
                font-weight: bold;
                text-transform: uppercase;
                padding-top: 20px;
                padding-bottom: 10px;
            }}
        """
    
    @staticmethod
    def _graph_title_template(text_color):
        return f"""
            QLabel {{
                color: {text_color};
                font-size: 14px;
                font-weight: bold;
            }}
        """
    
    @staticmethod
    def _detail_page_back_button_template(bg_color, text_color, border_color, hover_bg, hover_text):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                font-size: 18px;
                font-weight: bold;
                border: 1px solid {border_color};
                border-radius: 20px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                color: {hover_text};
            }}
        """
    
    @staticmethod
    def _status_scroll_template(bg_color):
        return f"""
            QScrollArea {{
                background-color: {bg_color};
                border: none;
            }}
        """


class DarkTheme(BaseTheme):
    def __init__(self):
        from UI.Styles import AppColors, AppStyles
        self.colors = AppColors
        self.styles = AppStyles
    
    def get_button_style(self):
        # Use existing AppStyles (backward compatibility)
        return self.styles.BUTTON_PRIMARY_STYLE
    
    def get_table_style(self):
        return self.styles.TABLE_STYLE
    
    def get_default_style(self):
        return self.styles.MAIN_STYLE
    
    def get_sidebar_style(self):
        return self.styles.SIDEBAR_CONTAINER_STYLE
    
    def get_menu_style(self):
        return self.styles.MENU_STYLE
    
    def get_scrollbar_style(self):
        return self.styles.UNIFIED_SCROLL_BAR_STYLE
    
    def get_checkbox_style(self):
        return self.styles.CHECKBOX_STYLE
    
    def get_input_style(self):
        return self.styles.INPUT_STYLE
    
    def get_dropdown_style(self):
        return self.styles.DROPDOWN_STYLE
    
    def get_button_secondary_style(self):
        return self.styles.BUTTON_SECONDARY_STYLE
    
    def get_sidebar_button_style(self):
        return self.styles.SIDEBAR_BUTTON_STYLE
    
    def get_action_button_style(self):
        return self.styles.ACTION_BUTTON_STYLE
    
    def get_panel_style(self):
        return self.styles.PANEL_STYLE
    
    def get_header_style(self):
        return self.styles.HEADER_STYLE
    
    def get_progress_bar_style(self):
        return self.styles.PROGRESS_BAR_STYLE
    
    def get_tooltip_style(self):
        return self.styles.TOOLTIP_STYLE
    
    def get_search_bar_style(self):
        return self.styles.SEARCH_BAR_STYLE
    
    def get_tree_widget_style(self):
        return self.styles.TREE_WIDGET_STYLE
    
    def get_status_box_style(self):
        return self.styles.STATUS_BOX_STYLE
    
    def get_title_style(self):
        return self.styles.TITLE_STYLE
    
    def get_divider_style(self):
        return self.styles.DIVIDER_STYLE
    
    def get_delete_button_style(self):
        return self.styles.DELETE_BUTTON_STYLE
    
    def get_empty_label_style(self):
        return self.styles.EMPTY_LABEL_STYLE
    
    def get_text_style(self):
        return self.styles.TEXT_STYLE
    
    def get_description_style(self):
        return self.styles.DESCRIPTION_STYLE
    
    def get_placeholder_style(self):
        return self.styles.PLACEHOLDER_STYLE
    
    def get_back_button_style(self):
        return self.styles.BACK_BUTTON_STYLE
    
    def get_empty_state_style(self):
        return self.styles.EMPTY_STATE_STYLE
    
    def get_terminal_textedit_style(self):
        return self.styles.TERMINAL_TEXTEDIT
    
    def get_terminal_wrapper_style(self):
        return self.styles.TERMINAL_WRAPPER
    
    def get_terminal_header_style(self):
        return self.styles.TERMINAL_HEADER_CONTENT
    
    def get_terminal_tab_button_style(self):
        return self.styles.TERMINAL_TAB_BUTTON
    
    def get_graph_frame_style(self):
        return self.styles.GRAPH_FRAME_STYLE
    
    def get_content_area_style(self):
        return self.styles.CONTENT_AREA_STYLE
    
    def get_top_bar_style(self):
        return self.styles.TOP_BAR_STYLE
    
    def get_focus_style(self):
        return self.styles.FOCUS_STYLE
    
    def get_synced_item_style(self):
        return self.styles.SYNCED_ITEM_STYLE
    
    def get_status_text_style(self):
        return self.styles.STATUS_TEXT_STYLE
    
    def get_detail_page_style(self):
        return self.styles.DETAIL_PAGE_STYLE
    
    def get_detail_page_header_style(self):
        return self.styles.DETAIL_PAGE_HEADER_STYLE
    
    def get_detail_page_yaml_style(self):
        return self.styles.DETAIL_PAGE_YAML_TEXT_STYLE
    
    def get_nav_menu_dropdown_style(self):
        return self.styles.NAV_MENU_DROPDOWN_STYLE
    
    def get_title_bar_style(self):
        return self.styles.TITLE_BAR_STYLE
    
    def get_events_table_style(self):
        return self.styles.EVENTS_TABLE_STYLE
    
    def get_releases_table_style(self):
        return self.styles.RELEASES_TABLE_STYLE
    
    def get_cluster_status_box_style(self):
        return self.styles.CLUSTER_STATUS_BOX_STYLE
    
    def get_cluster_chart_panel_style(self):
        return self.styles.CLUSTER_CHART_PANEL_STYLE
    
    def get_items_count_style(self):
        return self.styles.ITEMS_COUNT_STYLE
    
    def get_section_header_style(self):
        return self.styles.SECTION_HEADER_STYLE
    
    def get_subsection_header_style(self):
        return self.styles.SUBSECTION_HEADER_STYLE
    
    def get_graph_title_style(self):
        return self.styles.GRAPH_TITLE_STYLE
    
    def get_detail_page_back_button_style(self):
        return self.styles.DETAIL_PAGE_BACK_BUTTON_STYLE
    
    def get_status_scroll_style(self):
        return self.styles.STATUS_SCROLL_STYLE
    
    def get_placeholder_style(self):
        return self.styles.PLACEHOLDER_STYLE
    
    def get_back_button_style(self):
        return self.styles.BACK_BUTTON_STYLE
    
    def get_empty_state_style(self):
        return self.styles.EMPTY_STATE_STYLE
    
    def get_main_style(self):
        return self.styles.MAIN_STYLE


class LightColors:
    # Multi-platform light theme (semantically correct names)
    
    # Base colors - lightest to darkest (CREAM for verification)
    BG_LIGHTEST = "#FFF8E7"   # Cream white for verification
    BG_LIGHT = "#FFF4D6"      # Light cream
    BG_MEDIUM = "#FFF0C5"     # Medium cream (main background)
    BG_DARK = "#FFE8A3"       # Darker cream
    BG_DARKER = "#FFE082"     # Darkest cream
    
    # Semantic backgrounds
    BG_SIDEBAR = "#F8F8F8"    # Sidebar background
    BG_HEADER = "#F8F8F8"     # Header background
    CARD_BG = "#F8F8F8"       # Card/Panel backgrounds
    HEADER_BG = "#F8F8F8"     # Header background (alias)
    TAB_INACTIVE = "#E8E8E8"  # Inactive tab background
    TABLE_HEADER = "#E8E8E8"  # Table header background
    
    # Text colors - dark on light backgrounds
    TEXT_DARK = "#24292F"     # Primary dark text
    TEXT_LIGHT = "#24292F"    # Alias for compatibility
    TEXT_SECONDARY = "#656D76" # Muted text
    TEXT_SUBTLE = "#8B949E"   # Very muted text
    TEXT_LINK = "#0366D6"     # Link text
    TEXT_DANGER = "#DC3545"   # Danger text
    TEXT_TABLE = "#24292F"    # Table text
    TEXT_SUCCESS = "#28A745"  # Success text
    TEXT_WARNING = "#DC3545"  # Warning text
    
    # Orchetrix accent colors (consistent across themes)
    ACCENT_BLUE = "#0095ff"   # Original Orchetrix blue
    ACCENT_GREEN = "#4CAF50"  # Material Design green (same as dark theme)
    ACCENT_ORANGE = "#FF5733" # Original orange
    ACCENT_RED = "#DC3545"    # Light-friendly red
    ACCENT_PURPLE = "#8C33FF" # Purple accent
    
    # Borders - light to dark
    BORDER_LIGHT = "#E1E4E8"  # Lightest borders
    BORDER_COLOR = "#D1D5DA"  # Standard borders
    BORDER_DARK = "#C6CBD1"   # Darkest borders
    
    # Hover states
    HOVER_BG = "rgba(0, 0, 0, 0.05)"  # Light hover background
    HOVER_BG_DARKER = "rgba(0, 0, 0, 0.1)"  # Darker hover
    SELECTED_BG = "rgba(53, 132, 228, 0.15)"  # Selected background
    DANGER_HOVER_BG = "rgba(220, 53, 69, 0.1)"  # Danger hover
    
    # Status colors
    STATUS_ACTIVE = "#28A745"  # Green
    STATUS_AVAILABLE = "#28A745"  # Green
    STATUS_DISCONNECTED = "#DC3545"  # Red
    STATUS_PENDING = "#FFA500"  # Orange
    STATUS_WARNING = "#FFC107"  # Warning yellow
    STATUS_PROGRESS = "#0095ff"  # Progress blue
    STATUS_ERROR = "#DC3545"  # Error red


class LightTheme(BaseTheme):
    def __init__(self):
        self.colors = LightColors
    
    def get_button_style(self):
        # Use shared template, inject light theme colors
        return self._button_template(
            bg_color=self.colors.ACCENT_BLUE,
            text_color=self.colors.BG_LIGHTEST,
            hover_color="#007ACC"
        )
    
    def get_table_style(self):
        # Use shared template, inject light theme colors
        return self._table_template(
            bg_color=self.colors.CARD_BG,
            text_color=self.colors.TEXT_LIGHT,
            border_color=self.colors.BORDER_COLOR,
            border_light=self.colors.BORDER_LIGHT,
            header_bg=self.colors.BG_MEDIUM,
            header_text=self.colors.TEXT_SECONDARY
        )
    
    def get_default_style(self):
        # Use shared template, inject light theme colors
        return self._widget_template(
            bg_color=self.colors.BG_MEDIUM,
            text_color=self.colors.TEXT_DARK
        )
    
    def get_sidebar_style(self):
        # VS Code Light sidebar
        return self._sidebar_template(
            bg_color=self.colors.BG_SIDEBAR,
            border_color=self.colors.BORDER_COLOR
        )
    
    def get_menu_style(self):
        # GitHub Light + Modern Light UI
        return self._menu_template(
            bg_color=self.colors.BG_LIGHTEST,
            border_color=self.colors.BORDER_COLOR,
            text_color=self.colors.TEXT_DARK,
            selected_bg="rgba(53, 132, 228, 0.15)"
        )
    
    def get_scrollbar_style(self):
        # Light theme scrollbar
        return self._scrollbar_template(
            handle_color="#C1C1C1",
            handle_hover="#A8A8A8",
            handle_pressed="#787878"
        )
    
    def get_checkbox_style(self):
        # Light theme checkbox
        return self._checkbox_template(
            border_color=self.colors.TEXT_SECONDARY,
            checked_bg=self.colors.ACCENT_BLUE,
            checked_border=self.colors.ACCENT_BLUE,
            hover_border=self.colors.TEXT_DARK
        )
    
    def get_input_style(self):
        # Light theme input
        return self._input_template(
            bg_color=self.colors.BG_LIGHTEST,
            border_color=self.colors.BORDER_COLOR,
            text_color=self.colors.TEXT_DARK
        )
    
    def get_dropdown_style(self):
        # Light theme dropdown
        return self._dropdown_template(
            bg_color=self.colors.BG_LIGHTEST,
            border_color=self.colors.BORDER_COLOR,
            text_color=self.colors.TEXT_DARK,
            hover_bg=self.colors.BG_LIGHT
        )
    
    def get_button_secondary_style(self):
        # Light theme secondary button
        return self._button_secondary_template(
            bg_color=self.colors.BG_LIGHTEST,
            text_color=self.colors.TEXT_SECONDARY,
            border_color=self.colors.ACCENT_BLUE,
            hover_bg=self.colors.BG_LIGHT
        )
    
    def get_sidebar_button_style(self):
        # VS Code Light sidebar button
        return self._sidebar_button_template(
            bg_color="transparent",
            text_color=self.colors.TEXT_SECONDARY,
            hover_bg="rgba(0, 0, 0, 0.05)",
            active_bg="rgba(0, 0, 0, 0.05)"
        )
    
    def get_action_button_style(self):
        # Light theme action button
        return self._action_button_template(
            bg_color="transparent",
            hover_bg="rgba(0, 0, 0, 0.05)",
            pressed_bg="rgba(0, 0, 0, 0.1)"
        )
    
    def get_panel_style(self):
        # VS Code Light panel
        return self._panel_template(
            bg_color=self.colors.CARD_BG,
            border_color=self.colors.BORDER_COLOR
        )
    
    def get_header_style(self):
        # VS Code Light header
        return self._header_template(
            bg_color=self.colors.BG_HEADER,
            border_color=self.colors.BORDER_COLOR
        )
    
    def get_progress_bar_style(self):
        # Light theme progress bar
        return self._progress_bar_template(
            bg_color=self.colors.BG_DARK,
            chunk_color=self.colors.ACCENT_BLUE
        )
    
    def get_tooltip_style(self):
        # GitHub Light tooltip
        return self._tooltip_template(
            bg_color=self.colors.BG_LIGHTEST,
            text_color=self.colors.TEXT_DARK,
            border_color=self.colors.BORDER_COLOR
        )
    
    def get_search_bar_style(self):
        # Light theme search bar
        return self._search_bar_template(
            bg_color=self.colors.BG_DARK,
            text_color=self.colors.TEXT_DARK,
            border_color=self.colors.BORDER_COLOR,
            focus_border=self.colors.BG_DARKER
        )
    
    def get_tree_widget_style(self):
        # VS Code Light tree widget
        return self._tree_widget_template(
            bg_color=self.colors.BG_MEDIUM,
            text_color=self.colors.TEXT_DARK,
            border_color=self.colors.BORDER_COLOR,
            header_bg=self.colors.BG_LIGHT,
            hover_bg="rgba(0, 0, 0, 0.05)",
            selected_bg="rgba(53, 132, 228, 0.15)"
        )
    
    def get_status_box_style(self):
        # VS Code Light status box
        return self._status_box_template(
            bg_color=self.colors.CARD_BG,
            border_color=self.colors.BORDER_COLOR,
            hover_bg=self.colors.BG_DARK,
            hover_border=self.colors.BORDER_DARK
        )
    
    def get_title_style(self):
        # Light theme title
        return self._title_style_template(
            text_color=self.colors.TEXT_DARK,
            font_size="20px"
        )
    
    def get_divider_style(self):
        # Light theme divider
        return self._divider_template(
            bg_color=self.colors.BORDER_COLOR
        )
    
    def get_delete_button_style(self):
        # Light theme delete button
        return self._delete_button_template(
            bg_color="transparent",
            text_color=self.colors.TEXT_SECONDARY,
            hover_color=self.colors.ACCENT_RED
        )
    
    def get_empty_label_style(self):
        # Light theme empty label
        return self._empty_label_template(
            text_color=self.colors.TEXT_SUBTLE,
            bg_color="transparent"
        )
    
    def get_text_style(self):
        # Light theme text
        return self._text_style_template(
            text_color=self.colors.TEXT_DARK,
            font_size="14px"
        )
    
    def get_description_style(self):
        # Light theme description
        return self._description_style_template(
            text_color=self.colors.TEXT_SUBTLE
        )
    
    def get_placeholder_style(self):
        # Light theme placeholder
        return self._placeholder_template(
            text_color=self.colors.TEXT_SUBTLE
        )
    
    def get_back_button_style(self):
        # Light theme back button
        return self._back_button_template(
            bg_color="transparent",
            text_color=self.colors.TEXT_SECONDARY,
            border_color=self.colors.BORDER_COLOR,
            hover_bg=self.colors.BG_DARK,
            hover_text=self.colors.TEXT_DARK
        )
    
    def get_empty_state_style(self):
        # VS Code Light empty state
        return self._empty_state_template(
            bg_color=self.colors.CARD_BG,
            text_color=self.colors.TEXT_SECONDARY,
            border_color=self.colors.BORDER_COLOR
        )
    
    def get_terminal_textedit_style(self):
        # Light theme terminal
        return self._terminal_textedit_template(
            bg_color=self.colors.BG_LIGHTEST,
            text_color=self.colors.TEXT_DARK,
            selection_bg="rgba(53, 132, 228, 0.3)"
        )
    
    def get_terminal_wrapper_style(self):
        # GitHub Light terminal wrapper
        return self._terminal_wrapper_template(
            bg_color=self.colors.BG_LIGHTEST,
            border_color=self.colors.BORDER_COLOR
        )
    
    def get_terminal_header_style(self):
        # GitHub Light terminal header
        return self._terminal_header_template(
            bg_color=self.colors.BG_LIGHTEST,
            border_color=self.colors.BORDER_COLOR
        )
    
    def get_terminal_tab_button_style(self):
        # Light theme terminal tab button
        return self._terminal_tab_button_template(
            bg_color="transparent",
            border_color=self.colors.BORDER_COLOR,
            hover_bg="rgba(0, 0, 0, 0.05)",
            checked_bg=self.colors.BG_LIGHTEST,
            accent_color=self.colors.ACCENT_BLUE
        )
    
    def get_graph_frame_style(self):
        # VS Code Light graph frame
        return self._graph_frame_template(
            bg_color=self.colors.CARD_BG,
            border_color=self.colors.BORDER_COLOR
        )
    
    def get_content_area_style(self):
        # VS Code Light content area
        return self._content_area_template(
            bg_color=self.colors.BG_MEDIUM
        )
    
    def get_top_bar_style(self):
        # VS Code Light top bar
        return self._top_bar_template(
            bg_color=self.colors.BG_MEDIUM,
            border_color=self.colors.BORDER_COLOR
        )
    
    def get_focus_style(self):
        # Light theme focus
        return self._focus_style_template(
            accent_color=self.colors.ACCENT_BLUE
        )
    
    def get_synced_item_style(self):
        # Light theme synced item
        return self._synced_item_template(
            bg_color=self.colors.BG_LIGHT,
            text_color=self.colors.TEXT_DARK
        )
    
    def get_status_text_style(self):
        # Light theme status text
        return self._status_text_template(
            text_color=self.colors.TEXT_SUBTLE,
            font_size="12px"
        )
    
    def get_detail_page_style(self):
        # VS Code Light detail page
        return self._detail_page_style_template(
            bg_color=self.colors.BG_SIDEBAR,
            border_color=self.colors.BORDER_COLOR
        )
    
    def get_detail_page_header_style(self):
        # VS Code Light detail page header
        return self._detail_page_header_template(
            bg_color=self.colors.BG_HEADER,
            border_color=self.colors.BORDER_COLOR
        )
    
    def get_detail_page_yaml_style(self):
        # Light theme YAML editor
        return self._detail_page_yaml_template(
            bg_color=self.colors.BG_SIDEBAR,
            text_color=self.colors.TEXT_DARK
        )
    
    def get_nav_menu_dropdown_style(self):
        # Modern Light nav menu
        return self._nav_menu_dropdown_template(
            bg_color=self.colors.BG_LIGHTEST,
            border_color=self.colors.BORDER_DARK,
            text_color=self.colors.TEXT_DARK,
            selected_bg="rgba(53, 132, 228, 0.15)"
        )
    
    def get_title_bar_style(self):
        # VS Code Light title bar
        return self._title_bar_style_template(
            bg_color=self.colors.BG_MEDIUM,
            text_color=self.colors.TEXT_DARK
        )
    
    def get_events_table_style(self):
        # VS Code Light events table
        return self._events_table_template(
            bg_color=self.colors.CARD_BG,
            text_color=self.colors.TEXT_DARK,
            header_bg=self.colors.BG_LIGHT,
            hover_bg="rgba(0, 0, 0, 0.05)",
            selected_bg="rgba(53, 132, 228, 0.15)"
        )
    
    def get_releases_table_style(self):
        # VS Code Light releases table
        return self._releases_table_template(
            bg_color=self.colors.CARD_BG,
            text_color=self.colors.TEXT_DARK,
            header_bg=self.colors.BG_LIGHT,
            hover_bg="rgba(0, 0, 0, 0.05)",
            selected_bg="rgba(53, 132, 228, 0.15)",
            border_color=self.colors.BORDER_COLOR
        )
    
    def get_cluster_status_box_style(self):
        # Light theme cluster status box
        return self._cluster_status_box_template(
            bg_color=self.colors.BG_LIGHT,
            hover_bg=self.colors.BG_DARK,
            hover_border=self.colors.BORDER_DARK
        )
    
    def get_cluster_chart_panel_style(self):
        # VS Code Light cluster chart panel
        return self._cluster_chart_panel_template(
            bg_color=self.colors.BG_SIDEBAR
        )
    
    def get_items_count_style(self):
        # Light theme items count
        return self._items_count_template(
            text_color=self.colors.TEXT_SUBTLE
        )
    
    def get_section_header_style(self):
        # Light theme section header
        return self._section_header_template(
            text_color=self.colors.TEXT_DARK
        )
    
    def get_subsection_header_style(self):
        # Light theme subsection header
        return self._subsection_header_template(
            text_color=self.colors.TEXT_SUBTLE
        )
    
    def get_graph_title_style(self):
        # Light theme graph title
        return self._graph_title_template(
            text_color=self.colors.TEXT_DARK
        )
    
    def get_detail_page_back_button_style(self):
        # Light theme detail page back button
        return self._detail_page_back_button_template(
            bg_color="transparent",
            text_color=self.colors.TEXT_SECONDARY,
            border_color=self.colors.BORDER_DARK,
            hover_bg=self.colors.BG_DARK,
            hover_text=self.colors.TEXT_DARK
        )
    
    def get_status_scroll_style(self):
        # Light theme status scroll
        return self._status_scroll_template(
            bg_color="transparent"
        )
    
    def get_main_style(self):
        return f"""
            QMainWindow, QWidget {{
                background-color: {self.colors.BG_MEDIUM};
                color: {self.colors.TEXT_DARK};
                font-family: 'Segoe UI', sans-serif;
            }}
            
            QTabWidget::pane {{
                border: none;
            }}
            
            QTabBar::tab {{
                background-color: transparent;
                color: {self.colors.TEXT_SECONDARY};
                padding: 8px 24px;
                border: none;
                margin-right: 2px;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                color: {self.colors.TEXT_DARK};
                border-bottom: 2px solid {self.colors.ACCENT_BLUE};
            }}
            QTabBar::tab:hover:!selected {{
                color: {self.colors.TEXT_DARK};
            }}
        """


# Global instance
_theme_manager = None

def get_theme_manager():
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager