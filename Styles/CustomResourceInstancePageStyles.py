"""
CustomResourceInstancePage-specific styles
Contains styles that are unique to CustomResourceInstancePage and defined inline in the page.
"""

import textwrap


def get_empty_state_overlay_style(object_name: str) -> str:
    """Style for empty state overlay label"""
    return textwrap.dedent(f"""
        QLabel#{object_name} {{
            color: white;
            background: transparent;
            border: none;
        }}
    """).strip()
