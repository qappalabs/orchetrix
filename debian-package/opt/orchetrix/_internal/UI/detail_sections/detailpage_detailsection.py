"""
Details section for DetailPage component
"""

from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from typing import Dict, Any
import logging

from .base_detail_section import BaseDetailSection
from UI.Styles import AppStyles, AppColors, EnhancedStyles


class DetailPageDetailsSection(BaseDetailSection):
    """Details section showing detailed resource information"""

    def __init__(self, kubernetes_client, parent=None):
        super().__init__("Details", kubernetes_client, parent)
        self.setup_details_ui()

    def setup_details_ui(self):
        """Setup details-specific UI"""
        # Create scroll area for details content
        scroll_area = QScrollArea()
        scroll_area.setStyleSheet(AppStyles.DETAIL_PAGE_DETAILS_STYLE)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Details content widget
        self.details_content = QWidget()
        self.details_content.setStyleSheet(f"background-color: {AppColors.BG_SIDEBAR}; border: none;")
        self.details_layout = QVBoxLayout(self.details_content)
        self.details_layout.setContentsMargins(
            EnhancedStyles.CONTENT_PADDING,
            EnhancedStyles.CONTENT_PADDING,
            EnhancedStyles.CONTENT_PADDING,
            EnhancedStyles.CONTENT_PADDING
        )
        self.details_layout.setSpacing(EnhancedStyles.SECTION_GAP)

        scroll_area.setWidget(self.details_content)
        self.content_layout.addWidget(scroll_area)

    def _load_data_async(self):
        """Load overview data using Kubernetes API"""
        try:
            self.connect_api_signals()
            self.kubernetes_client.get_resource_detail_async(
                self.resource_type,
                self.resource_name,
                self.resource_namespace or "default"
            )
        except Exception as e:
            self.handle_error(f"Failed to start data loading: {str(e)}")

    def handle_api_data_loaded(self, data):
        """Handle data loaded from Kubernetes API"""
        try:
            self.disconnect_api_signals()
            self.handle_data_loaded(data)
        except Exception as e:
            self.handle_error(f"Error processing loaded data: {str(e)}")

    def handle_api_error(self, error_message):
        """Handle API error"""
        self.disconnect_api_signals()
        self.handle_error(error_message)

    def update_ui_with_data(self, data: Dict[str, Any]):
        """Update details UI with loaded resource data"""
        if not data:
            return

        try:
            # Clear existing content
            self.clear_content()

            # Add metadata section
            self.add_metadata_section(data)

            # Add spec section if available
            spec = data.get("spec", {})
            if spec:
                self.add_spec_section(spec)

            # Add status section if available
            status = data.get("status", {})
            if status:
                self.add_status_section(status)

        except Exception as e:
            self.handle_error(f"Error updating details UI: {str(e)}")

    def add_metadata_section(self, data):
        """Add metadata section"""
        metadata_title = QLabel("METADATA")
        metadata_title.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.details_layout.addWidget(metadata_title)

        metadata = data.get("metadata", {})

        metadata_fields = [
            ("Name", metadata.get("name", "")),
            ("Namespace", metadata.get("namespace", "")),
            ("UID", metadata.get("uid", "")),
            ("Creation Timestamp", metadata.get("creationTimestamp", "")),
            ("Resource Version", metadata.get("resourceVersion", ""))
        ]

        # Add annotations if available
        annotations = metadata.get("annotations", {})
        if annotations:
            annotations_text = "\n".join([f"{k}={v}" for k, v in annotations.items()])
            metadata_fields.append(("Annotations", annotations_text))

        # Add finalizers if available
        finalizers = metadata.get("finalizers", [])
        if finalizers:
            metadata_fields.append(("Finalizers", ", ".join(finalizers)))

        for field_name, field_value in metadata_fields:
            if field_value:
                self.add_field_widget(field_name, field_value)

    def add_spec_section(self, spec):
        """Add spec section"""
        spec_title = QLabel("SPEC")
        spec_title.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.details_layout.addWidget(spec_title)

        self.add_object_fields(spec, self.details_layout)

    def add_status_section(self, status):
        """Add status section"""
        status_title = QLabel("STATUS")
        status_title.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.details_layout.addWidget(status_title)

        self.add_object_fields(status, self.details_layout)

    def add_field_widget(self, field_name, field_value):
        """Add a field widget to display key-value pairs"""
        field_container = QWidget()
        field_layout = QHBoxLayout(field_container)
        field_layout.setContentsMargins(0, 0, 0, 0)

        name_label = QLabel(field_name + ":")
        name_label.setFixedWidth(150)
        name_label.setStyleSheet(EnhancedStyles.get_field_label_style())

        value_label = QLabel(str(field_value))
        value_label.setStyleSheet(EnhancedStyles.get_field_value_style())
        value_label.setWordWrap(True)

        field_layout.addWidget(name_label)
        field_layout.addWidget(value_label, 1)

        self.details_layout.addWidget(field_container)

    def add_object_fields(self, obj, parent_layout, prefix="", depth=0):
        """Recursively add object fields with better limits"""
        if depth > 2 or len(str(obj)) > 10000:  # Stricter limits
            truncated_label = QLabel("... (data truncated for performance)")
            truncated_label.setStyleSheet(f"color: {AppColors.TEXT_SUBTLE}; font-style: italic;")
            parent_layout.addWidget(truncated_label)
            return

        for key, value in obj.items():
            field_name = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict) and value:
                # Add section header for nested objects
                field_title = QLabel(field_name.upper())
                field_title.setStyleSheet(f"""
                    font-weight: bold;
                    color: {AppColors.TEXT_SECONDARY};
                    margin-left: {depth * 10}px;
                    margin-top: 10px;
                """)
                parent_layout.addWidget(field_title)

                # Recursively add nested fields
                self.add_object_fields(value, parent_layout, field_name, depth + 1)

            elif isinstance(value, list) and value:
                if all(isinstance(item, dict) for item in value):
                    # List of objects
                    field_title = QLabel(field_name.upper())
                    field_title.setStyleSheet(f"""
                        font-weight: bold;
                        color: {AppColors.TEXT_SECONDARY};
                        margin-left: {depth * 10}px;
                        margin-top: 10px;
                    """)
                    parent_layout.addWidget(field_title)

                    # Show first few items
                    for i, item in enumerate(value[:3]):
                        item_title = QLabel(f"{field_name}[{i}]")
                        item_title.setStyleSheet(f"""
                            font-weight: normal;
                            color: {AppColors.TEXT_SUBTLE};
                            margin-left: {(depth + 1) * 10}px;
                        """)
                        parent_layout.addWidget(item_title)

                        self.add_object_fields(item, parent_layout, "", depth + 2)

                    if len(value) > 3:
                        more_items = QLabel(f"... and {len(value) - 3} more items")
                        more_items.setStyleSheet(f"""
                            color: {AppColors.TEXT_SUBTLE};
                            margin-left: {(depth + 1) * 10}px;
                        """)
                        parent_layout.addWidget(more_items)
                else:
                    # List of simple values
                    if all(isinstance(item, str) for item in value):
                        value_str = ", ".join(value)
                    else:
                        value_str = str(value)
                    self.add_field_widget(field_name, value_str)
            else:
                # Simple field
                self.add_field_widget(field_name, str(value))

    def clear_content(self):
        """Clear all details content"""
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()