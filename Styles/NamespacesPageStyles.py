"""
NamespacesPage-specific styles
Contains styles that are unique to NamespacesPage and defined inline in the page.
"""

# Fallback button style for add namespace button (used if AppStyles.BUTTON_STYLE is not available)
ADD_NAMESPACE_BUTTON_FALLBACK_STYLE = """
                    QPushButton {
                        background-color: #3d3d3d;
                        color: white;
                        padding: 5px 15px;
                        border-radius: 2px;
                    }
                    QPushButton:hover {
                        background-color: #333333;
                    }
                    QPushButton:pressed {
                        background-color: #388E3C;
                    }
                """
