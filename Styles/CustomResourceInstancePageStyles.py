"""
CustomResourceInstancePage-specific styles
Contains styles that are unique to CustomResourceInstancePage and defined inline in the page.
"""


def get_empty_state_overlay_style(object_name):
    """Style for empty state overlay label"""
    return f"""
                QLabel#{object_name} {{
                    color: white;
                    background: transparent;
                    border: none;
                }}
            """
