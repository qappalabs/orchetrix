from PyQt6.QtCore import Qt
from UI.ThemeManager import get_theme_manager
from Styles import BaseResourcePageStyles

class ResourcePageStyleManager:
    """
    Manages styling for ResourcePage components to separate UI concerns.
    """

    @staticmethod
    def apply_title_style(title_label, items_count_label):
        """Apply theme-aware styles to the title block."""
        theme = get_theme_manager().get_current_theme()
        
        if title_label:
            title_label.setStyleSheet(
                f"font-size: 20px; font-weight: bold; color: {theme.colors.TEXT_LIGHT};"
            )
            
        if items_count_label:
            items_count_label.setStyleSheet(
                f"color: {theme.colors.TEXT_SUBTLE}; font-size: 12px; margin-left: 8px;"
            )
            items_count_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    @staticmethod
    def get_delete_button_style():
        """Get the style for the delete button."""
        return BaseResourcePageStyles.get_delete_button_style()

    @staticmethod
    def get_search_label_style():
        return BaseResourcePageStyles.get_search_label_style()

    @staticmethod
    def apply_search_input_style(search_bar):
        """Apply style to search input."""
        if search_bar:
            search_bar.setStyleSheet(BaseResourcePageStyles.get_search_input_style())

    @staticmethod
    def get_namespace_label_style():
        return BaseResourcePageStyles.get_namespace_label_style()


    @staticmethod
    def get_empty_title_style():
        return BaseResourcePageStyles.get_empty_title_style()

    @staticmethod
    def get_empty_subtitle_style():
        return BaseResourcePageStyles.get_empty_subtitle_style()

    @staticmethod
    def get_error_label_style():
        return BaseResourcePageStyles.get_error_label_style()
