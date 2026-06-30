"""
Details section for DetailPage component
"""

from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, QByteArray
from PyQt6.QtGui import QColor, QFont, QPixmap, QPainter, QCursor, QTextOption
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QTextEdit
from PyQt6.QtSvg import QSvgRenderer
from typing import Dict, Any
import logging
import re
import sys
import os
from .base_detail_section import BaseDetailSection
import Styles.BaseDetailSectionStyles as BaseDetailSectionStyles
import Styles.DetailSectionStyles as DetailSectionStyles
from Utils.time_utils import TimezoneManager


def _is_too_large(obj, max_items=1000):
    """
    Lightweight size heuristic to avoid expensive serialization.

    Checks container sizes without converting to string, using:
    - len() for dict, list, tuple, set (with capping)
    - __len__ for other objects that support it
    - sys.getsizeof() as fallback for other objects

    Args:
        obj: Object to check size of
        max_items: Maximum number of items to count before stopping

    Returns:
        bool: True if object appears too large to display
    """
    try:
        # For container types, use len() with capping
        if isinstance(obj, (dict, list, tuple, set)):
            count = 0
            if isinstance(obj, dict):
                # Count keys only (shallow)
                count = len(obj)
            else:
                # Count items, but cap at max_items to avoid expensive counting
                count = min(len(obj), max_items)

            return count >= max_items

        # For objects with __len__, use that
        elif hasattr(obj, '__len__'):
            try:
                length = len(obj)
                return length >= max_items
            except (TypeError, AttributeError):
                pass

        # Fallback: use memory size estimate
        size_bytes = sys.getsizeof(obj)
        # Consider "too large" if object uses more than ~1MB
        return size_bytes > 1024 * 1024

    except Exception:
        # If anything goes wrong, err on the side of caution
        return True


class DetailPageDetailsSection(BaseDetailSection):
    """Details section showing detailed resource information"""

    def __init__(self, kubernetes_client, parent=None):
        super().__init__("Details", kubernetes_client, parent)
        self.current_data = None
        self._metadata_icon_label = None  # Store for theme updates
        self.setup_details_ui()

    def _on_theme_changed(self, theme_name):
        """Refresh styles when theme changes"""
        # Refresh static widgets
        if hasattr(self, 'details_content'):
            self.details_content.setStyleSheet(DetailSectionStyles.get_content_style())
        
        # Refresh scroll area
        if hasattr(self, 'scroll_area'):
            self.scroll_area.setStyleSheet(DetailSectionStyles.get_scroll_area_style())
        
        # Refresh metadata icon Color
        if self._metadata_icon_label:
            theme = BaseDetailSectionStyles._get_theme()
            self._metadata_icon_label.setPixmap(self._render_svg_icon(
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Icons", "info.svg"),
                theme.colors.TEXT_SECONDARY
            ))

        # Refresh all dynamic widgets by iterating through the layout
        if hasattr(self, 'details_layout'):
            self._refresh_dynamic_widgets_in_layout(self.details_layout)

    def _refresh_dynamic_widgets_in_layout(self, layout):
        """Recursively iterate through layout and refresh stylesheets of all widgets"""
        if not layout:
            return
        
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item:
                if item.widget():
                    widget = item.widget()
                    # Determine widget type and apply appropriate stylesheet
                    class_name = widget.__class__.__name__
                    
                    if class_name == 'QLabel':
                        # Check if it's a section header (all caps text) or field label/value
                        text = widget.text()
                        if text and text.isupper() and len(text.split()) <= 2:
                            # Section header like "METADATA", "SPEC", "STATUS"
                            widget.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
                        elif text.endswith(':'):
                            # Field label (ends with colon)
                            widget.setStyleSheet(BaseDetailSectionStyles.get_field_label_style())
                        else:
                            # Field value (most common)
                            # Check for specialized labels by object name or style hints if possible.
                            # Badges have "True" or "False" text usually (for conditions).
                            if text in ["True", "False"]:
                                if text == "True":
                                    widget.setStyleSheet(BaseDetailSectionStyles.get_condition_badge_true_style())
                                else:
                                    widget.setStyleSheet(BaseDetailSectionStyles.get_condition_badge_false_style())
                                widget.setAlignment(Qt.AlignmentFlag.AlignCenter) # Badges are centered
                            else:
                                # Standard value
                                widget.setStyleSheet(BaseDetailSectionStyles.get_field_value_style())

                    elif class_name == 'QFrame':
                        obj_name = widget.objectName()
                        if obj_name == "info_card":
                            widget.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
                        elif obj_name == "handler_card":
                             theme = BaseDetailSectionStyles._get_theme()
                             widget.setStyleSheet(f"""
                                QFrame#handler_card {{
                                    background-color: transparent;
                                    border: 1px solid {theme.colors.BORDER_LIGHT};
                                    border-radius: 6px;
                                }}
                            """)
                        
                        # Force style re-application
                        widget.style().unpolish(widget)
                        widget.style().polish(widget)

                    # Recurse into widget's layout (CRITICAL for updating children of containers)
                    if widget.layout():
                        self._refresh_dynamic_widgets_in_layout(widget.layout())

                elif item.layout():
                    # Recursively refresh nested layouts
                    self._refresh_dynamic_widgets_in_layout(item.layout())

    def _render_svg_icon(self, file_path, color_hex, size=18):
        """Render SVG with dynamic color — replaces ALL stroke/fill colors with theme color"""
        if not os.path.exists(file_path):
            logging.warning(f"SVG icon not found: {file_path}")
            return QPixmap()

        try:
            with open(file_path, 'r') as f:
                svg_data = f.read()

            # Replace any hardcoded color value in stroke/fill attributes with the theme color
            # Covers: stroke="#RRGGBB", fill="#RRGGBB", stroke="#RGB", currentColor, black, #000000
            svg_data = re.sub(r'stroke="#[0-9A-Fa-f]{3,6}"', f'stroke="{color_hex}"', svg_data)
            svg_data = re.sub(r'fill="#[0-9A-Fa-f]{3,6}"', f'fill="{color_hex}"', svg_data)
            svg_data = svg_data.replace('currentColor', color_hex)
            svg_data = svg_data.replace('stroke="black"', f'stroke="{color_hex}"')
            svg_data = svg_data.replace('fill="black"', f'fill="{color_hex}"')

            renderer = QSvgRenderer(QByteArray(svg_data.encode()))
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            return pixmap
        except Exception as e:
            logging.error(f"Error rendering SVG icon {file_path}: {str(e)}")
            return QPixmap()

    def set_raw_data(self, raw_data):
        """Set raw data for special resources like charts and releases"""
        logging.info(f"Details section: Received raw data for {self.resource_type}, keys: {list(raw_data.keys()) if raw_data else 'None'}")
        self.current_data = raw_data
        self.update_ui_with_data(raw_data)

    def setup_details_ui(self):
        """Setup details-specific UI"""
        # Create scroll area for details content
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet(DetailSectionStyles.get_scroll_area_style())
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Details content widget
        self.details_content = QWidget()
        self.details_content.setStyleSheet(DetailSectionStyles.get_content_style())
        self.details_layout = QVBoxLayout(self.details_content)
        padding = BaseDetailSectionStyles.CONTENT_PADDING
        self.details_layout.setContentsMargins(padding, padding, padding, padding)
        self.details_layout.setSpacing(BaseDetailSectionStyles.SECTION_GAP)

        self.scroll_area.setWidget(self.details_content)
        self.content_layout.addWidget(self.scroll_area)

    def _load_data_async(self):
        """Load overview data using Kubernetes API"""
        try:
            # CRITICAL FIX: Check if we already have raw_data from the page (e.g., CustomResourcePages, NodesPage)
            # This prevents unnecessary API calls and empty detail sections
            if self.current_data is not None:
                logging.info(f"Details section: Using existing raw_data for {self.resource_type}/{self.resource_name}")
                # Use the existing data directly instead of making API call
                self.handle_data_loaded(self.current_data)
                return
            
            # Only make API call if we don't have current_data
            logging.info(f"Details section: No raw_data available, fetching from API for {self.resource_type}/{self.resource_name}")
            self.connect_api_signals()
            self.kubernetes_client.get_resource_detail(
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


    def is_node(self):
        """Check if current resource is a Node"""
        return self.resource_type and self.resource_type.lower() in ["node", "nodes"]

    def is_pod(self):
        """Check if current resource is a Pod"""
        return self.resource_type and self.resource_type.lower() in ["pod", "pods"]

    def is_workload(self):
        """Check if current resource is a workload with a pod template"""
        workload_types = [
            "deployment", "deployments",
            "statefulset", "statefulsets",
            "daemonset", "daemonsets",
            "job", "jobs",
            "cronjob", "cronjobs",
            "replicaset", "replicasets",
            "replicationcontroller", "replicationcontrollers"
        ]
        return self.resource_type and self.resource_type.lower() in workload_types

    def _get_pod_template_spec(self, data):
        """Extract pod template spec from workload data"""
        if not data:
            return None
        
        spec = data.get("spec", {})
        
        # 1. CronJob specific (spec.jobTemplate.spec.template.spec)
        if self.resource_type and self.resource_type.lower() in ["cronjob", "cronjobs"]:
            job_template = spec.get("jobTemplate", {})
            job_spec = job_template.get("spec", {})
            template = job_spec.get("template", {})
            return template.get("spec")
        
        # 2. Most workloads (spec.template.spec)
        template = spec.get("template", {})
        if template:
            return template.get("spec")
            
        return None

    def update_ui_with_data(self, data: Dict[str, Any]):
        """Update details UI with loaded resource data"""
        if not data:
            return

        try:
            # Clear existing content
            self.clear_content()

            # Add metadata section (Always first)
            self.add_metadata_section(data)
            
            status = data.get("status", {})
            spec = data.get("spec", {})
            
            excluded_status_keys = []
            excluded_spec_keys = []
            
            # --- Specialized Resource-Specific Sections ---
            if self.is_node():
                # Specialized Node view pattern matching the screenshot
                self.add_node_capacity_allocatable_section(data)
                self.add_node_addresses_section(status.get("addresses", []))
                self.add_node_container_images_section(status.get("images", []))
                
                # Claims these keys to avoid duplication in generic cards
                excluded_status_keys.extend(["allocatable", "capacity", "addresses", "images"])

            # --- Universal Specialized Sections ---
            
            # 1. Conditions Section (for any resource that has them)
            conditions = status.get("conditions", [])
            if conditions:
                self.add_conditions_section(conditions)
                excluded_status_keys.append("conditions")

            if self.is_node():
                # Node Info Section (Separate from Status, above Spec)
                node_info = status.get("nodeInfo", {})
                if node_info:
                    self.add_node_info_section(node_info)
                    excluded_status_keys.append("nodeInfo")
                
                # Daemon Endpoints Section
                daemon_endpoints = status.get("daemonEndpoints", {})
                if daemon_endpoints:
                    self.add_daemon_endpoints_section(daemon_endpoints)
                    excluded_status_keys.append("daemonEndpoints")

            if self.is_pod():
                # For Pods, we use the unified specialized spec section
                self.add_pod_spec_section(spec, exclude_keys=excluded_spec_keys)
                # Mark spec as None so generic catch-all doesn't show it again
                spec = None

            elif self.is_workload():
                # Specialized Workload view (Deployment, Job, etc.)
                pod_template_spec = self._get_pod_template_spec(data)
                
                # Extract Template Metadata (for labels)
                template_metadata = {}
                if self.resource_type.lower() in ["cronjob", "cronjobs"]:
                    job_tpl = spec.get("jobTemplate", {})
                    job_spec = job_tpl.get("spec", {})
                    tpl = job_spec.get("template", {})
                    template_metadata = tpl.get("metadata", {})
                else:
                    template_metadata = spec.get("template", {}).get("metadata", {})

                if pod_template_spec:
                    # Consolidate workload-level spec fields (replicas, selector, strategy) 
                    # into the pod template rendering's ADDITIONAL SPEC section.
                    workload_excludes = ["template", "jobTemplate"]
                    workload_info = {k: v for k, v in spec.items() if k not in workload_excludes and k not in excluded_spec_keys}
                    
                    # 1. Add specialized pod sections (Containers, Volumes, etc.)
                    # and pass workload_info to be included in the ADDITIONAL SPEC card
                    self.add_pod_spec_section(pod_template_spec, extra_data=workload_info, template_metadata=template_metadata)
                    
                    # Mark all as handled
                    spec = None
                    excluded_spec_keys.extend(["template", "jobTemplate"])

            # --- Generic Catch-All Sections (Filtered) ---
            
            # Add remaining spec section (if not already handled)
            if spec:
                self.add_spec_section(spec, exclude_keys=excluded_spec_keys)

            # Add remaining status section
            if status:
                self.add_status_section(status, exclude_keys=excluded_status_keys)

            # Add stretch at the end with weight 1 to robustly claim all extra space
            self.details_layout.addStretch(1)

            # Ensure UI recalculates flexible height for the scroll area content
            self.details_content.adjustSize()
            self.details_content.updateGeometry()

        except Exception as e:
            self.handle_error(f"Error updating details UI: {str(e)}")

    def add_pod_scheduling_section(self, scheduling_info):
        """Add POD SCHEDULING & CONFIG section (Node Selector + Config)"""
        if not scheduling_info:
            return

        # Filters - skip affinity as it is now moved to ADDITIONAL SPEC
        display_info = {k: v for k, v in scheduling_info.items() if k != "affinity"}
        if not display_info:
             return

        # Standardized Section Container
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5)

        # Header Container
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Icon
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", "info.svg")
        
        if os.path.exists(icon_path):
             icon_label = QLabel()
             theme = BaseDetailSectionStyles._get_theme()
             icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
             header_layout.addWidget(icon_label)

        title_label = QLabel("NODE SELECTOR") 
        title_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        header_layout.addWidget(title_label)
        
        section_layout.addWidget(header_container)

        # Content Card
        card = QFrame()
        card.setObjectName("info_card")
        card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING)
        card_layout.setSpacing(BaseDetailSectionStyles.FIELD_GAP)

        # Manually render to ensure order and formatting
        # 1. Node Name
        if "nodeName" in scheduling_info:
            self.add_field_widget("nodeName", scheduling_info["nodeName"], card_layout)
            
        # 2. Node Selector labels (Flattened key=value pairs)
        if "nodeSelector" in scheduling_info:
            ns = scheduling_info["nodeSelector"]
            if isinstance(ns, dict):
                for k, v in ns.items():
                     self.add_field_widget(f"nodeSelector.{k}", str(v), card_layout)
        

        # Ensure card can grow if fields wrap
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        section_layout.addWidget(card)
        self.details_layout.addWidget(section_container)

    def add_pod_tolerations_section(self, tolerations):
        """Add certain TOLERATIONS section for Pods"""
        if not tolerations:
            return

        # Standardized Section Container
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5)

        # Header Container
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Icon (Using same or similar to Node Selector/Conditions)
        # Maybe a shield or list icon? Using conditions pulse icon or generic info for now?
        # User said "just like images and condtions".
        # Let's use a list icon if available, or just re-use spec-icon.svg or create one.
        # check available icons?
        # I'll use spec-icon.svg for consistency as it is configuration.
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", "info.svg")
        
        if os.path.exists(icon_path):
             icon_label = QLabel()
             theme = BaseDetailSectionStyles._get_theme()
             icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
             header_layout.addWidget(icon_label)

        title_label = QLabel("TOLERATIONS")
        title_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        header_layout.addWidget(title_label)
        
        section_layout.addWidget(header_container)

        # Content Card
        card = QFrame()
        card.setObjectName("info_card")
        card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING)
        card_layout.setSpacing(10) # Using slightly larger spacing between items

        # Render Tolerations List
        # Each toleration is a dict: {key: "...", operator: "...", effect: "...", tolerationSeconds: ...}
        # We can render them as blocks.
        
        if not tolerations:
            lbl = QLabel("No tolerations")
            lbl.setStyleSheet(f"color: {BaseDetailSectionStyles._get_theme().colors.TEXT_SECONDARY};")
            card_layout.addWidget(lbl)
        else:
            for i, tol in enumerate(tolerations):
                # Separator for items after the first
                if i > 0:
                    line = QFrame()
                    line.setFrameShape(QFrame.Shape.HLine)
                    line.setFrameShadow(QFrame.Shadow.Sunken)
                    line.setStyleSheet(f"background-color: {BaseDetailSectionStyles._get_theme().colors.BORDER_COLOR}; max-height: 1px;")
                    card_layout.addWidget(line)

                # Toleration Item Block
                item_container = QWidget()
                item_layout = QVBoxLayout(item_container)
                item_layout.setContentsMargins(0, 5, 0, 5)
                item_layout.setSpacing(2)
                
                # Title for the item (optional, e.g. "tolerations[0]")
                # header_lbl = QLabel(f"tolerations[{i}]")
                # header_lbl.setStyleSheet(f"color: {BaseDetailSectionStyles._get_theme().colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
                # item_layout.addWidget(header_lbl)
                
                # Fields
                # Key, Operator, Effect, TolerationSeconds
                # Render as small Key-Value pairs
                
                def add_small_field(k, v):
                    row = QWidget()
                    row_layout = QHBoxLayout(row)
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    row_layout.setSpacing(10)
                    
                    k_lbl = QLabel(str(k))
                    k_lbl.setStyleSheet(BaseDetailSectionStyles.get_field_label_style())
                    k_lbl.setMinimumWidth(120) 
                    k_lbl.setWordWrap(True)
                    
                    v_lbl = QLabel(str(v))
                    v_lbl.setStyleSheet(BaseDetailSectionStyles.get_field_value_style())
                    v_lbl.setWordWrap(True)
                    v_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
                    v_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                    
                    row_layout.setSpacing(0)
                    row_layout.addWidget(k_lbl, 1)
                    row_layout.addWidget(v_lbl, 1)
                    item_layout.addWidget(row)

                if "key" in tol: add_small_field("key", tol["key"])
                if "operator" in tol: add_small_field("operator", tol["operator"])
                if "effect" in tol: add_small_field("effect", tol["effect"])
                if "tolerationSeconds" in tol: add_small_field("tolerationSeconds", tol["tolerationSeconds"])
                
                # Fallback for other keys
                for k, v in tol.items():
                    if k not in ["key", "operator", "effect", "tolerationSeconds"]:
                         add_small_field(k, v)

                card_layout.addWidget(item_container)
        
        # Ensure card can grow if fields wrap
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        card_layout.addStretch(1) # Fix large vertical gaps
        section_layout.addWidget(card)
        self.details_layout.addWidget(section_container)

    def add_daemon_endpoints_section(self, daemon_endpoints):
        """Add specialized DAEMON ENDPOINTS section for Nodes"""
        if not daemon_endpoints:
            return

        # Standardized Section Container
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5)

        # Header Container
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Icon (Using generic network/info icon or spec icon)
        # Using spec-icon.svg for consistency
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", "endpoint.svg")
        
        if os.path.exists(icon_path):
             icon_label = QLabel()
             theme = BaseDetailSectionStyles._get_theme()
             icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
             header_layout.addWidget(icon_label)

        title_label = QLabel("DAEMON ENDPOINTS")
        title_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        header_layout.addWidget(title_label)
        
        section_layout.addWidget(header_container)

        # Content Card
        card = QFrame()
        card.setObjectName("info_card")
        card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING)
        card_layout.setSpacing(10)

        # Render Endpoints
        # Format: Key (uppercase) Value (Port only)
        # e.g. "KUBELETENDPOINT 10250"
        
        # We need a table-like layout or just rows.
        # User example: "KUBELETENDPOINT       10250"
        # Let's use QHBoxLayout with fixed width for key or spacing.
        
        if not daemon_endpoints:
            lbl = QLabel("No endpoints")
            lbl.setStyleSheet(f"color: {BaseDetailSectionStyles._get_theme().colors.TEXT_SECONDARY};")
            card_layout.addWidget(lbl)
        else:
            sorted_keys = sorted(daemon_endpoints.keys())
            for key in sorted_keys:
                raw_value = daemon_endpoints[key]
                # Value is typically {"Port": 10250}
                port_value = raw_value
                if isinstance(raw_value, dict) and "Port" in raw_value:
                    port_value = raw_value["Port"]
                
                # Upper case key
                display_key = key.upper().replace("ENDPOINT", "ENDPOINT") # Ensure ENDPOINT is preserved if in name
                # Actually user just said "KUBELETENDPOINT", previously it was "kubeletEndpoint".
                # So just .upper() is fine.
                
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(20) # Good spacing
                
                k_lbl = QLabel(display_key)
                k_lbl.setStyleSheet(BaseDetailSectionStyles.get_field_label_style())
                k_lbl.setMinimumWidth(160) # Scaled minimum width
                k_lbl.setWordWrap(True)
                
                v_lbl = QLabel(str(port_value))
                v_lbl.setStyleSheet(BaseDetailSectionStyles.get_field_value_style())
                v_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
                v_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
                v_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                
                row_layout.setSpacing(0)
                row_layout.addWidget(k_lbl, 1)
                row_layout.addWidget(v_lbl, 1)
                
                card_layout.addWidget(row)

        # Ensure card can grow if fields wrap
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        section_layout.addWidget(card)
        self.details_layout.addWidget(section_container)

    def add_conditions_section(self, conditions):
        """Add specialized CONDITIONS section for any resource"""
        if not conditions:
            return
            
        # Standardized Section Container
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5) # 5px margin between header and card

        # Header
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0) # Removed bottom margin as we use spacing now
        
        # Icon (Activity/Pulse) — loaded from Icons folder
        icon_label = QLabel()
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        activity_icon_path = os.path.join(base_path, "Icons", "activity.svg")
        theme = BaseDetailSectionStyles._get_theme()
        icon_label.setPixmap(self._render_svg_icon(activity_icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
        
        title_label = QLabel("CONDITIONS")
        title_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        section_layout.addWidget(header_container)
        
        # Details Card
        card = QFrame()
        card.setObjectName("info_card")
        card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(16)
        
        # Render each condition
        for cond in conditions:
            cond_type = cond.get("type", "Unknown")
            status_val = cond.get("status", "Unknown")
            reason = cond.get("reason", "")
            message = cond.get("message", "")
            last_transition = cond.get("lastTransitionTime", "")
            last_heartbeat = cond.get("lastHeartbeatTime", "")
            
            # Container for the condition entry
            entry_container = QWidget()
            entry_layout = QVBoxLayout(entry_container)
            entry_layout.setContentsMargins(0, 0, 0, 0)
            entry_layout.setSpacing(6) # Increased spacing for better readability
            
            # Top row: Type and Status Badge
            top_row = QHBoxLayout()
            
            type_label = QLabel(cond_type)
            type_label.setStyleSheet(BaseDetailSectionStyles.get_field_value_style()) # Use bold/primary style for Type
            
            status_label = QLabel(str(status_val))
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Apply Badge Style
            if str(status_val).lower() == "true":
                status_label.setStyleSheet(BaseDetailSectionStyles.get_condition_badge_true_style())
            else:
                status_label.setStyleSheet(BaseDetailSectionStyles.get_condition_badge_false_style())
            
            top_row.addWidget(type_label)
            top_row.addStretch()
            top_row.addWidget(status_label)
            
            entry_layout.addLayout(top_row)
            
            # Message/Reason if available
            if message or reason:
                desc_text = f"{reason}: {message}" if reason and message else (reason or message)
                desc_label = QLabel(desc_text)
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet(BaseDetailSectionStyles.get_condition_message_style())
                entry_layout.addWidget(desc_label)

            # Timestamps Row
            if last_transition or last_heartbeat:
                time_layout = QHBoxLayout()
                time_layout.setSpacing(16)
                
                time_style = f"color: {BaseDetailSectionStyles._get_theme().colors.TEXT_SUBTLE}; font-size: 11px;"
                
                from Utils.time_utils import TimezoneManager
                
                if last_transition:
                    try:
                        last_transition = TimezoneManager.get_instance().format_time(last_transition)
                    except Exception:
                        pass
                    trans_label = QLabel(f"Last Transition: {last_transition}")
                    trans_label.setStyleSheet(time_style)
                    time_layout.addWidget(trans_label)
                    
                if last_heartbeat:
                    try:
                        last_heartbeat = TimezoneManager.get_instance().format_time(last_heartbeat)
                    except Exception:
                        pass
                    beat_label = QLabel(f"Last Heartbeat: {last_heartbeat}")
                    beat_label.setStyleSheet(time_style)
                    time_layout.addWidget(beat_label)
                    
                time_layout.addStretch()
                entry_layout.addLayout(time_layout)
            
            card_layout.addWidget(entry_container)
            
            # Separator if not last
            if cond != conditions[-1]:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setStyleSheet(f"background-color: {BaseDetailSectionStyles._get_theme().colors.BORDER_COLOR}; max-height: 1px; border: none;")
                card_layout.addWidget(line)
                
        section_layout.addWidget(card)
        self.details_layout.addWidget(section_container)


    def _create_section_container(self, title, icon_filename, card_widget):
        """
        Helper to create a standardized section with Header outside the Card.
        spacing(5) as requested by user.
        """
        section_widget = QWidget()
        section_layout = QVBoxLayout(section_widget)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5) # 5px margin between header and card
        
        # --- HEADER ---
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Icon
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", icon_filename) if icon_filename else None
        
        if icon_path and os.path.exists(icon_path):
             icon_label = QLabel()
             stroke_color = BaseDetailSectionStyles.get_section_header_color()
             icon_label.setPixmap(self._render_svg_icon(icon_path, stroke_color, size=18))
             header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        section_layout.addWidget(header_container)
        section_layout.addWidget(card_widget)
        
        return section_widget

    def add_node_capacity_allocatable_section(self, data):
        """Add Allocatable and Capacity cards side-by-side for Nodes"""
        
        status = data.get("status", {})
        allocatable = status.get("allocatable", {})
        capacity = status.get("capacity", {})
        
        # Create container for side-by-side cards
        cards_container = QWidget()
        cards_layout = QHBoxLayout(cards_container)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(15)
        
        # Get base path for icons
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Helper to create content card (inner part only)
        def create_content_card(data_dict):
            card = QFrame()
            card.setObjectName("info_card") 
            card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
            
            # Shadow effect
            shadow = QGraphicsDropShadowEffect(card)
            shadow.setBlurRadius(8)
            shadow.setOffset(0, 1)
            shadow.setColor(QColor(0, 0, 0, 40))
            card.setGraphicsEffect(shadow)
            
            card_inner_layout = QVBoxLayout(card)
            card_inner_layout.setContentsMargins(16, 16, 16, 16)
            card_inner_layout.setSpacing(12)
            
            # Data Rows
            target_keys = ["cpu", "memory", "pods", "ephemeral-storage"]
            
            found_data = False
            for key in target_keys:
                if key in data_dict:
                    found_data = True
                    row_layout = QHBoxLayout()
                    
                    # Format Key
                    key_display = key.capitalize()
                    if key == "cpu": key_display = "CPU"
                    elif key == "ephemeral-storage": key_display = "Ephemeral Storage"
                    elif key == "pods": key_display = "Pods"
                    
                    key_label = QLabel(key_display)
                    key_label.setStyleSheet(BaseDetailSectionStyles.get_field_label_style())
                    
                    value_label = QLabel(str(data_dict[key]))
                    value_label.setStyleSheet(BaseDetailSectionStyles.get_field_value_style())
                    value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    
                    row_layout.setSpacing(0)
                    row_layout.addWidget(key_label, 1)
                    row_layout.addWidget(value_label, 1)
                    
                    card_inner_layout.addLayout(row_layout)
                    
            if not found_data:
                no_data_label = QLabel("No data available")
                no_data_label.setStyleSheet(BaseDetailSectionStyles.get_secondary_text_style())
                card_inner_layout.addWidget(no_data_label)
            
            card_inner_layout.addStretch(1) # Fix large vertical gaps
            return card

        # Create Allocatable Section
        alloc_card = create_content_card(allocatable)
        allocatable_section = self._create_section_container("ALLOCATABLE", "allocatable.svg", alloc_card)
        
        # Create Capacity Section
        cap_card = create_content_card(capacity)
        capacity_section = self._create_section_container("CAPACITY", "capacity.svg", cap_card)
        
        cards_layout.addWidget(allocatable_section, 1)
        cards_layout.addWidget(capacity_section, 1)
        
        self.details_layout.addWidget(cards_container)

    def add_node_addresses_section(self, addresses):
        """Add ADDRESSES section for Node"""
        if not addresses:
            return
            
        # Standardized Section Container
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5) # 5px margin between header and card

        # Header
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Icon (ip-addresses.svg)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", "ip-addresses.svg")
        
        if os.path.exists(icon_path):
             icon_label = QLabel()
             theme = BaseDetailSectionStyles._get_theme()
             icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
             header_layout.addWidget(icon_label)
        
        title_label = QLabel("ADDRESSES")
        title_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        section_layout.addWidget(header_container)
        
        # Card
        card = QFrame()
        card.setObjectName("info_card")
        card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(12)
        
        # Pill Style for values
        theme = BaseDetailSectionStyles._get_theme()
        pill_style = f'''
            QLabel {{
                background-color: transparent;
                border: 1px solid #000000;
                border-radius: 8px;
                padding: 4px 12px;
                color: {theme.colors.TEXT_LIGHT};
                font-size: 14px;
                font-weight: 600;
            }}
        '''
        
        for addr in addresses:
            addr_type = addr.get("type", "Unknown")
            addr_value = addr.get("address", "")
            
            row_layout = QHBoxLayout()
            
            type_label = QLabel(addr_type)
            type_label.setStyleSheet(BaseDetailSectionStyles.get_field_label_style())
            type_label.setMinimumWidth(100)
            type_label.setWordWrap(True)
            
            value_label = QLabel(addr_value)
            value_label.setStyleSheet(pill_style)
            value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            row_layout.setSpacing(10)
            row_layout.addWidget(type_label)
            row_layout.addStretch()
            row_layout.addWidget(value_label)
            
            card_layout.addLayout(row_layout)
        
        card_layout.addStretch(1) # Fix large vertical gaps
        section_layout.addWidget(card)
        self.details_layout.addWidget(section_container)

    def add_node_info_section(self, node_info):
        """Add NODE INFO section separate from Status"""
        if not node_info:
            return

        # Standardized Section Container
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5)

        # Header Container
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Icon (Info)
        icon_label = QLabel()
        theme = BaseDetailSectionStyles._get_theme()
        # Use existing info icon or fallback to settings if unavailable, or create generic info path
        # Using settings-icon.svg as placeholder or we can use spec-icon (info circle)
        # Let's use spec-icon.svg as it is an "Info" circle
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", "info.svg")
        
        if os.path.exists(icon_path):
             icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
             header_layout.addWidget(icon_label)

        title_label = QLabel("NODE INFO")
        title_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        header_layout.addWidget(title_label)
        
        section_layout.addWidget(header_container)

        # Content Card (Same style as Metadata)
        card = QFrame()
        card.setObjectName("info_card")
        card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING)
        card_layout.setSpacing(BaseDetailSectionStyles.FIELD_GAP)

        # Render fields
        self.add_object_fields(node_info, card_layout)
        
        card_layout.addStretch(1) # Fix large vertical gaps
        section_layout.addWidget(card)
        self.details_layout.addWidget(section_container)

    def add_node_container_images_section(self, images):
        """Add CONTAINER IMAGES section for Node with collapsible view"""
        if not images:
            return
            
        # Standardized Section Container
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5) # 5px margin between header and card

        # Header
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Icon (container-images.svg)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", "container-images.svg")
        
        if os.path.exists(icon_path):
             icon_label = QLabel()
             theme = BaseDetailSectionStyles._get_theme()
             icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
             header_layout.addWidget(icon_label)
        
        title_label = QLabel("CONTAINER IMAGES")
        title_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        
        # Total count
        count_label = QLabel(f"Total: {len(images)}")
        count_label.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 500;")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(count_label)
        
        section_layout.addWidget(header_container)
        
        # Card/List
        main_card = QFrame()
        main_card.setObjectName("info_card")
        main_card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        main_layout = QVBoxLayout(main_card)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Secondary text style for size
        theme = BaseDetailSectionStyles._get_theme()
        size_style = f"color: {theme.colors.TEXT_SUBTLE}; font-size: 11px;"
        name_style = f"color: {theme.colors.TEXT_LIGHT}; font-size: 13px; font-weight: 600;"
        
        # Helper to create image row
        def create_image_row(img_data):
            names = img_data.get("names", [])
            full_name = names[0] if names else "Unknown Image"
            size_bytes = img_data.get("sizeBytes", 0)
            
            # Format size
            if size_bytes > 1024*1024*1024:
                size_str = f"{size_bytes / (1024*1024*1024):.1f} GB"
            else:
                size_str = f"{size_bytes / (1024*1024):.1f} MB"
                
            img_container = QWidget()
            img_layout = QVBoxLayout(img_container)
            img_layout.setContentsMargins(0, 0, 0, 0)
            img_layout.setSpacing(4)
            
            name_label = QLabel(full_name)
            name_label.setStyleSheet(name_style)
            name_label.setWordWrap(True)
            name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            
            size_label = QLabel(size_str)
            size_label.setStyleSheet(size_style)
            
            img_layout.addWidget(name_label)
            img_layout.addWidget(size_label)
            
            return img_container

        # Add separator line helper
        def add_separator(layout):
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet(f"background-color: {theme.colors.BORDER_COLOR}; max-height: 1px; border: none;")
            layout.addWidget(line)

        # 1. Add first 3 images directly
        initial_count = min(len(images), 3)
        for i in range(initial_count):
            row = create_image_row(images[i])
            main_layout.addWidget(row)
            
            # Add separator if not the absolute last item of *displayed* items
            # Logic: if we have more items (images > 3), add separator after 3rd too (for the hidden part)
            # If images <= 3, add separator only if not last
            if i < initial_count - 1:
                add_separator(main_layout)

        # 2. Add remaining images in a hidden container
        if len(images) > 3:
            hidden_widget = QWidget()
            hidden_layout = QVBoxLayout(hidden_widget)
            hidden_layout.setContentsMargins(0, 0, 0, 0)
            hidden_layout.setSpacing(16)
            
            # Start hidden part with a separator
            add_separator(hidden_layout)
            
            for i in range(3, len(images)):
                row = create_image_row(images[i])
                hidden_layout.addWidget(row)
                if i < len(images) - 1:
                    add_separator(hidden_layout)
            
            hidden_widget.setVisible(False)
            main_layout.addWidget(hidden_widget)
            
            # 3. Add toggle button with separator
            add_separator(main_layout)
            
            view_all_btn = QPushButton("View all images")
            view_all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            view_all_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {theme.colors.ACCENT_ORANGE}; /* Orange or accent color */
                    border: none;
                    background: transparent;
                    font-size: 13px;
                    font-weight: 600;
                    text-align: center;
                }}
                QPushButton:hover {{
                    text-decoration: underline;
                }}
            """)
            
            def toggle_images():
                is_visible = hidden_widget.isVisible()
                hidden_widget.setVisible(not is_visible)
                view_all_btn.setText("View all images" if is_visible else "View less images")
                
            view_all_btn.clicked.connect(toggle_images)
            main_layout.addWidget(view_all_btn)

        section_layout.addWidget(main_card)
        self.details_layout.addWidget(section_container)



    def add_metadata_section(self, data):
        """Add metadata section"""
        from Utils.time_utils import TimezoneManager
        
        # Standardized Section Container
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5) # 5px margin between header and card

        # Header Container
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Add Settings Icon
        theme = BaseDetailSectionStyles._get_theme()
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Icons", "info.svg")
        
        self._metadata_icon_label = QLabel()
        if self._metadata_icon_label:
             self._metadata_icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color()))
        header_layout.addWidget(self._metadata_icon_label)

        metadata_title = QLabel("METADATA")
        metadata_title.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        metadata_title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        header_layout.addWidget(metadata_title)
        
        section_layout.addWidget(header_container)

        from PyQt6.QtWidgets import QGridLayout
        
        # Content Card
        card = QFrame()
        card.setObjectName("info_card")
        card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        
        # Use QGridLayout for pixel-perfect vertical alignment across all rows
        grid_layout = QGridLayout(card)
        grid_layout.setContentsMargins(BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING)
        grid_layout.setHorizontalSpacing(0) # Pixel-perfect center split
        grid_layout.setVerticalSpacing(BaseDetailSectionStyles.FIELD_GAP)
        grid_layout.setColumnStretch(0, 1) # 50% width
        grid_layout.setColumnStretch(1, 1) # 50% width

        metadata = data.get("metadata", {})

        creation_timestamp = metadata.get("creationTimestamp", "")
        if creation_timestamp:
            try:
                creation_timestamp = TimezoneManager.get_instance().format_time(creation_timestamp)
            except Exception:
                pass

        # 1. Basic Metadata (Restored Order: Top of the card)
        metadata_fields = [
            ("Name", metadata.get("name", "")),
            ("Namespace", metadata.get("namespace", "")),
            ("UID", metadata.get("uid", "")),
            ("Created", creation_timestamp),
            ("Resource Version", metadata.get("resourceVersion", ""))
        ]

        current_row = 0
        collapsible_widgets = []
        more_indicators = []
        large_text_edits = []
        
        # Global Toggle Button
        toggle_btn = QPushButton("View more")
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                color: {theme.colors.ACCENT_ORANGE};
                border: none;
                background: transparent;
                font-size: 13px;
                font-weight: 600;
                margin-top: 10px;
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        toggle_btn.setVisible(False)

        class ExpansionState:
            is_expanded = False
            has_collapsible_rows = False

        state = ExpansionState()

        def update_global_toggle():
            needs_toggle = state.has_collapsible_rows or any(getattr(te, 'has_clamping', False) for te in large_text_edits)
            toggle_btn.setVisible(needs_toggle)

        def toggle_metadata_action():
            state.is_expanded = not state.is_expanded
            toggle_btn.setText("View less" if state.is_expanded else "View more")
            
            for w in collapsible_widgets:
                w.setVisible(state.is_expanded)
            for ind in more_indicators:
                ind.setVisible(not state.is_expanded)
                
            for te in large_text_edits:
                if getattr(te, 'has_clamping', False):
                    full = int(te.document().documentLayout().documentSize().height()) + 5
                    te.setFixedHeight(full if state.is_expanded else 80)
                    
        toggle_btn.clicked.connect(toggle_metadata_action)
        
        def add_grid_row(label_text, value_text, is_collapsible=False, indicator_count=0):
            nonlocal current_row
            if not value_text: return
            
            # Label
            name_label = QLabel(label_text)
            name_label.setWordWrap(True)
            name_label.setMinimumWidth(160)
            name_label.setStyleSheet(BaseDetailSectionStyles.get_field_label_style() + "padding-right: 20px;")
            name_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            grid_layout.addWidget(name_label, current_row, 0)
            
            # Value Container (to support "more" indicator)
            value_container = QWidget()
            value_h_layout = QHBoxLayout(value_container)
            value_h_layout.setContentsMargins(0, 0, 0, 0)
            value_h_layout.setSpacing(8)
            value_h_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

            import re
            raw_string_value = str(value_text)
            has_long_word = bool(re.search(r'[^\s\-\.\/\,\:\;\"\{\}\[\]\(\)\_\=\@]{30,}', raw_string_value))

            if len(raw_string_value) > 1200 or has_long_word:
                 from PyQt6.QtWidgets import QTextEdit
                 from PyQt6.QtGui import QTextOption
                 text_edit = QTextEdit(raw_string_value)
                 text_edit.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)
                 text_edit.setReadOnly(True)
                 text_edit.setFrameShape(QFrame.Shape.NoFrame)
                 text_edit.setStyleSheet(BaseDetailSectionStyles.get_field_value_style() + "background: transparent; padding: 0;")
                 text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                 text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                 text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                 
                 large_text_edits.append(text_edit)
                 
                 def update_large_te_height(size, te=text_edit):
                     full_height = int(size.height()) + 5
                     if full_height > 95:
                         te.has_clamping = True
                         if state.is_expanded:
                             te.setFixedHeight(full_height)
                         else:
                             te.setFixedHeight(80)
                     else:
                         te.has_clamping = False
                         te.setFixedHeight(full_height)
                     # Ping global toggle logic whenever a text widget realizes it needs clamping
                     update_global_toggle()
                 
                 text_edit.document().documentLayout().documentSizeChanged.connect(
                     lambda size, te=text_edit: update_large_te_height(size, te)
                 )
                 value_widget = text_edit
            else:
                 display_value = raw_string_value
                 for char in ['-', '.', '/', ',', ':', '"', '{', '}', '[', ']', '(', ')', '_', '=', ' ', '@']:
                     display_value = display_value.replace(char, char + '\u200b')
                 
                 value_widget = QLabel(display_value)
                 value_widget.setTextFormat(Qt.TextFormat.PlainText) # Prevent HTML parsing from hiding text containing < >
                 value_widget.setStyleSheet(BaseDetailSectionStyles.get_field_value_style())
                 value_widget.setWordWrap(True)
                 value_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                 value_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                 value_widget.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

            value_h_layout.addWidget(value_widget)

            # Optional Indicator (+N more) - Relocated to follow the value
            if indicator_count > 0:
                indicator = QLabel(f"(+{indicator_count} more)")
                indicator.setStyleSheet(f"color: {theme.colors.TEXT_SUBTLE}; font-size: 11px; font-weight: 500;")
                indicator.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                value_h_layout.addWidget(indicator)
                more_indicators.append(indicator)
            
            grid_layout.addWidget(value_container, current_row, 1)
            
            if is_collapsible:
                name_label.setVisible(False)
                value_container.setVisible(False)
                collapsible_widgets.append(name_label)
                collapsible_widgets.append(value_container)
            
            current_row += 1

        # Add regular fields first
        for field_name, field_value in metadata_fields:
            add_grid_row(field_name, field_value)

        # 2. Annotations
        annotations = metadata.get("annotations", {})
        if annotations:
            sorted_ann_keys = sorted(annotations.keys())
            hidden_count = len(sorted_ann_keys) - 1
            for i, ak in enumerate(sorted_ann_keys):
                label_name = "Annotations" if i == 0 else ""
                is_collapsible = i > 0
                if is_collapsible: state.has_collapsible_rows = True
                
                # Only show indicator on the first row if there are hidden rows
                indicator_count = hidden_count if i == 0 else 0
                add_grid_row(label_name, f"{ak}={annotations[ak]}", is_collapsible, indicator_count)

        # 3. Labels
        labels = metadata.get("labels", {})
        if labels:
            sorted_lbl_keys = sorted(labels.keys())
            hidden_count = len(sorted_lbl_keys) - 1
            for i, lk in enumerate(sorted_lbl_keys):
                label_name = "Labels" if i == 0 else ""
                is_collapsible = i > 0
                if is_collapsible: state.has_collapsible_rows = True
                
                # Only show indicator on the first row if there are hidden rows
                indicator_count = hidden_count if i == 0 else 0
                add_grid_row(label_name, f"{lk}={labels[lk]}", is_collapsible, indicator_count)
        
        # After inserting all rows, trigger an initial check just in case
        update_global_toggle()

        # Add the pre-configured toggle button to the layout
        grid_layout.addWidget(toggle_btn, current_row, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
        current_row += 1

        # Add stretch at the bottom to fix vertical gaps
        grid_layout.setRowStretch(current_row, 1)
        
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        section_layout.addWidget(card)
        self.details_layout.addWidget(section_container)

    def add_pod_spec_section(self, spec, exclude_keys=None, extra_data=None, template_metadata=None):
        """Unified Specialized Spec section for Pods and Workload Pod Templates"""
        if not spec:
            return

        # 2. Containers Card
        containers = spec.get("containers", [])
        if containers:
            self._add_pod_containers_card("CONTAINERS", containers)

        # 2. Init Containers (if any)
        init_containers = spec.get("initContainers", [])
        if init_containers:
            self._add_pod_containers_card("INIT CONTAINERS", init_containers)

        # 3. Volumes Card
        volumes = spec.get("volumes", [])
        if volumes:
            self._add_pod_volumes_card(volumes)

        # 4. Scheduling Info (Node Selector, Node Name, Affinity)
        scheduling_fields = ["nodeSelector", "nodeName", "affinity"]
        scheduling_info = {f: spec[f] for f in scheduling_fields if f in spec}
        if scheduling_info:
            self.add_pod_scheduling_section(scheduling_info)

        # 5. Tolerations Section
        tolerations = spec.get("tolerations", [])
        if tolerations:
            self.add_pod_tolerations_section(tolerations)

        # 6. Strategy Container section (Workloads only) - Moved here below Tolerations
        if extra_data:
            strategy_data = extra_data.get("strategy") or extra_data.get("updateStrategy")
            if strategy_data:
                title = "UPDATE STRATEGY" if "updateStrategy" in extra_data else "STRATEGY"
                self._add_workload_strategy_section(strategy_data, title=title)

        # 7. ADDITIONAL SPEC card — shows scheduling/config fields + any remaining spec keys
        # Keys already handled by specialized cards
        base_handled_keys = ["containers", "initContainers", "volumes", "nodeSelector", "nodeName", "affinity", "tolerations"]
        
        current_exclude = exclude_keys if exclude_keys else []
        base_final_exclude = list(set(current_exclude + base_handled_keys))

        # Fields to explicitly show in ADDITIONAL SPEC
        additional_spec_fields = [
            "schedulerName",
            "priority",
            "priorityClassName",
            "preemptionPolicy",
            "restartPolicy",
            "terminationGracePeriodSeconds",
            "serviceAccount",
            "serviceAccountName",
            "securityContext",
            "dnsPolicy",
            "hostname",
            "subdomain",
        ]

        # Collect the explicit additional spec fields present in spec
        explicit_fields = [(k, spec[k]) for k in additional_spec_fields if k in spec and k not in base_final_exclude]

        # Also find any remaining spec keys not handled anywhere
        all_handled = list(set(base_final_exclude + additional_spec_fields))
        remaining_keys = [k for k in spec.keys() if k not in all_handled]

        if explicit_fields or remaining_keys or extra_data:
            # Standardized Section Container for ADDITIONAL SPEC
            section_container = QWidget()
            section_layout = QVBoxLayout(section_container)
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(5)

            # Header
            header_container = QWidget()
            header_layout = QHBoxLayout(header_container)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(10)
            header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Icon
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            icon_path = os.path.join(base_path, "Icons", "file-text.svg")
            
            if os.path.exists(icon_path):
                 icon_label = QLabel()
                 theme = BaseDetailSectionStyles._get_theme()
                 icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
                 header_layout.addWidget(icon_label)

            spec_title = QLabel("ADDITIONAL SPEC")
            spec_title.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
            header_layout.addWidget(spec_title)
            section_layout.addWidget(header_container)

            # Card
            card = QFrame()
            card.setObjectName("info_card")
            card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING)
            card_layout.setSpacing(BaseDetailSectionStyles.FIELD_GAP)

            theme = BaseDetailSectionStyles._get_theme()
            text_color = theme.colors.TEXT_LIGHT

            # 1. Strategy & Replicas (if extra_data)
            if extra_data:
                 # Exclude strategy as it has its own section now
                 ed_filtered = {k: v for k, v in extra_data.items() if k not in ["strategy", "updateStrategy", "selector"]}
                 
                 # Explicitly handle selector for better formatting
                 selector = extra_data.get("selector")
                 if selector:
                      selector_header = QLabel("SELECTOR")
                      selector_header.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {text_color};")
                      card_layout.addWidget(selector_header)
                      
                      match_labels = selector.get("matchLabels")
                      if match_labels:
                           self.add_field_widget("  Match Labels", "", card_layout)
                           for k, v in match_labels.items():
                                self.add_field_widget(f"    {k}", str(v), card_layout)
                      
                      # Handle matchExpressions if any
                      match_expr = selector.get("matchExpressions")
                      if match_expr:
                           self.add_field_widget("  Match Expressions", str(match_expr), card_layout)
                 
                 card_layout.addSpacing(10)
                 # Show other extra data (replicas, etc.)
                 self.add_object_fields(ed_filtered, card_layout)

            # 2. Template Metadata (Labels/Annotations)
            if template_metadata:
                 labels = template_metadata.get("labels")
                 if labels:
                      card_layout.addSpacing(15)
                      labels_header = QLabel("TEMPLATE LABELS")
                      labels_header.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {text_color};")
                      card_layout.addWidget(labels_header)
                      for k, v in labels.items():
                           self.add_field_widget(f"  {k}", str(v), card_layout)

            # 3. Affinity (Moved here from Node Selector card)
            if spec and "affinity" in spec:
                 affinity = spec["affinity"]
                 if isinstance(affinity, dict):
                      card_layout.addSpacing(15)
                      aff_header = QLabel("AFFINITY")
                      aff_header.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {text_color};")
                      card_layout.addWidget(aff_header)
                      
                      aff_details = []
                      if "nodeAffinity" in affinity: aff_details.append("Node Affinity")
                      if "podAffinity" in affinity: aff_details.append("Pod Affinity")
                      if "podAntiAffinity" in affinity: aff_details.append("Pod Anti-Affinity")
                      self.add_field_widget("  Status", ", ".join(aff_details) if aff_details else "Present", card_layout)

            # 4. Explicit additional fields from Pod Spec
            if explicit_fields:
                 card_layout.addSpacing(15)
                 spec_fields_header = QLabel("SPECIFICATION PROPERTIES")
                 spec_fields_header.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {text_color};")
                 card_layout.addWidget(spec_fields_header)
                 
                 for k, v in explicit_fields:
                     if k == "securityContext" and isinstance(v, dict):
                         self.add_field_widget(k, str(v) if v else "{}", card_layout)
                     else:
                         self.add_field_widget(k, str(v), card_layout)

            # Render any other remaining spec keys
            self.add_object_fields(spec, card_layout, exclude_keys=all_handled)
            
            if card_layout.count() > 0:
                # Ensure card can grow
                card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
                card_layout.addStretch(1) # Fix large vertical gaps
                section_layout.addWidget(card)
                self.details_layout.addWidget(section_container)


    def _add_workload_strategy_section(self, strategy, title="STRATEGY"):
        """Add specialized STRATEGY section for Workloads with cards"""
        if not strategy:
            return

        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5)

        # Header
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Icon
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", "info.svg")
        
        if os.path.exists(icon_path):
             icon_label = QLabel()
             theme = BaseDetailSectionStyles._get_theme()
             icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
             header_layout.addWidget(icon_label)

        header_label = QLabel(title)
        header_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        header_layout.addWidget(header_label)
        section_layout.addWidget(header_container)

        # Method: Each strategy type (rollingUpdate, etc.) gets its own card
        strategy_type = strategy.get("type", "Unknown")
        
        # Generic Type Fields (if any)
        fields = {k: v for k, v in strategy.items() if k != "type" and not isinstance(v, dict)}
        
        # 1. Main Strategy Type Card or Component Cards
        # We'll treat things like 'rollingUpdate' as specialized components
        components = {k: v for k, v in strategy.items() if isinstance(v, dict)}
        
        if not components:
            # Just show a single card with the type
            card = QFrame()
            card.setObjectName("info_card")
            card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            self.add_field_widget("Type", strategy_type, card_layout)
            self.add_object_fields(fields, card_layout)
            section_layout.addWidget(card)
        else:
            # Add a card for the general type if it has extra fields or just to show the type
            type_card = QFrame()
            type_card.setObjectName("info_card")
            type_card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
            type_card_layout = QVBoxLayout(type_card)
            type_card_layout.setContentsMargins(16, 16, 16, 16)
            self.add_field_widget("Type", strategy_type, type_card_layout)
            self.add_object_fields(fields, type_card_layout)
            section_layout.addWidget(type_card)

            # Add separate cards for components (like ROLLINGUPDATE)
            for comp_name, comp_val in components.items():
                card = QFrame()
                card.setObjectName("info_card")
                card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(16, 16, 16, 16)
                card_layout.setSpacing(10)

                # Header for component
                theme = BaseDetailSectionStyles._get_theme()
                text_color = theme.colors.TEXT_LIGHT
                name_lbl = QLabel(comp_name.upper())
                name_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {text_color};")
                card_layout.addWidget(name_lbl)
                
                # Render fields
                self.add_object_fields(comp_val, card_layout)
                section_layout.addWidget(card)

        self.details_layout.addWidget(section_container)

    def _add_pod_containers_card(self, title, containers):
        """Helper to render a list of containers in a card"""
        try:
            section_container = QWidget()
            section_layout = QVBoxLayout(section_container)
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(5)

            # Header
            header_container = QWidget()
            header_layout = QHBoxLayout(header_container)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Icon
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            icon_path = os.path.join(base_path, "Icons", "package-box.svg")
            
            if os.path.exists(icon_path):
                 icon_label = QLabel()
                 theme = BaseDetailSectionStyles._get_theme()
                 icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
                 header_layout.addWidget(icon_label)

            header_label = QLabel(title)
            header_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
            header_layout.addWidget(header_label)
            section_layout.addWidget(header_container)

            # Containers
            for container in containers:
                card = QFrame()
                card.setObjectName("info_card")
                card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(16, 16, 16, 16)
                card_layout.setSpacing(10)

                # Container Name & Image
                name = container.get("name", "Unknown")
                image = container.get("image", "Unknown")
                
                # Header Row for Container
                top_row = QHBoxLayout()
                name_lbl = QLabel(name)
                # Ensure theme is accessible
                try:
                    theme = BaseDetailSectionStyles._get_theme()
                    text_color = theme.colors.ACCENT_ORANGE
                except:
                    text_color = "#FF6B00" # Fallback orange
                    
                name_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {text_color};")
                top_row.addWidget(name_lbl)
                top_row.addStretch()
                card_layout.addLayout(top_row)
                
                self.add_field_widget("Image", image, card_layout)
                
                # Image Pull Policy
                pull_policy = container.get("imagePullPolicy")
                if pull_policy:
                    self.add_field_widget("Image Pull Policy", pull_policy, card_layout)
                
                # Ports
                ports = container.get("ports", [])
                if ports:
                    try:
                        port_str = ", ".join([f"{p.get('containerPort')}/{p.get('protocol', 'TCP')}" for p in ports])
                        self.add_field_widget("Ports", port_str, card_layout)
                    except Exception as e:
                         pass

                # Command & Args
                cmd = container.get("command", [])
                if cmd:
                     self.add_field_widget("Command", " ".join(cmd), card_layout)
                args = container.get("args", [])
                if args:
                     self.add_field_widget("Args", " ".join(args), card_layout)

                # Probes
                liveness = container.get("livenessProbe")
                if liveness:
                    probe_desc = []
                    if "httpGet" in liveness:
                        probe_desc.append(f"HTTP :{liveness['httpGet'].get('port', '?')}{liveness['httpGet'].get('path', '')}")
                    if "exec" in liveness:
                         probe_desc.append("Exec")
                    if "tcpSocket" in liveness:
                         probe_desc.append(f"TCP :{liveness['tcpSocket'].get('port', '?')}")
                    
                    delay = liveness.get("initialDelaySeconds")
                    timeout = liveness.get("timeoutSeconds")
                    period = liveness.get("periodSeconds")
                    
                    details = f"delay={delay}s timeout={timeout}s period={period}s"
                    self.add_field_widget("Liveness Probe", f"{', '.join(probe_desc)} ({details})", card_layout)

                readiness = container.get("readinessProbe")
                if readiness:
                    probe_desc = []
                    if "httpGet" in readiness:
                        probe_desc.append(f"HTTP :{readiness['httpGet'].get('port', '?')}{readiness['httpGet'].get('path', '')}")
                    if "exec" in readiness:
                         probe_desc.append("Exec")
                    if "tcpSocket" in readiness:
                         probe_desc.append(f"TCP :{readiness['tcpSocket'].get('port', '?')}")
                    
                    delay = readiness.get("initialDelaySeconds")
                    timeout = readiness.get("timeoutSeconds")
                    period = readiness.get("periodSeconds")
                    
                    details = f"delay={delay}s timeout={timeout}s period={period}s"
                    self.add_field_widget("Readiness Probe", f"{', '.join(probe_desc)} ({details})", card_layout)

                # Resources
                resources = container.get("resources", {})
                if resources:
                    req = resources.get("requests", {})
                    lim = resources.get("limits", {})
                    res_text = []
                    if req:
                        res_text.append(f"Requests: {', '.join([f'{k}={v}' for k, v in req.items()])}")
                    if lim:
                        res_text.append(f"Limits: {', '.join([f'{k}={v}' for k, v in lim.items()])}")
                    
                    if res_text:
                        self.add_field_widget("Resources", "\n".join(res_text), card_layout)

                # Security Context
                sec_ctx = container.get("securityContext", {})
                if sec_ctx:
                    # Format nicely
                    sec_text = ", ".join([f"{k}={v}" for k, v in sec_ctx.items()])
                    self.add_field_widget("Security Context", sec_text, card_layout)

                # Termination Message
                term_path = container.get("terminationMessagePath")
                term_policy = container.get("terminationMessagePolicy")
                if term_path:
                    self.add_field_widget("Termination Msg Path", term_path, card_layout)
                if term_policy:
                    self.add_field_widget("Termination Msg Policy", term_policy, card_layout)

                # Environment Variables (Collapsible/Truncated)
                env = container.get("env", [])
                if env:
                    if len(env) > 5:
                        self.add_field_widget("Environment", f"{len(env)} variables defined", card_layout)
                    else:
                        env_str = ", ".join([e.get("name", "") for e in env])
                        self.add_field_widget("Environment", env_str, card_layout)

                # Volume Mounts
                mounts = container.get("volumeMounts", [])
                if mounts:
                     mount_texts = []
                     for m in mounts:
                         m_path = m.get("mountPath", "")
                         m_name = m.get("name", "")
                         if m_path and m_name:
                             mount_texts.append(f"{m_path} -> {m_name}")
                     
                     if mount_texts:
                         # Join with newlines to show a list under one label
                         mounts_str = "\n".join(mount_texts)
                         self.add_field_widget("Volume Mounts", mounts_str, card_layout)

                # Ensure card doesn't stretch vertically
                card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                section_layout.addWidget(card)

            self.details_layout.addWidget(section_container)
        except Exception as e:
             raise e

    def _add_pod_volumes_card(self, volumes):
        """Helper to render volumes"""
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5)

        # Header
        # Icon
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", "nav_storage.svg")
        
        # We need a proper header layout to align icon and text
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        if os.path.exists(icon_path):
             icon_label = QLabel()
             theme = BaseDetailSectionStyles._get_theme()
             icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
             header_layout.addWidget(icon_label)

        header_label = QLabel("VOLUMES")
        header_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        header_layout.addWidget(header_label)
        section_layout.addWidget(header_container)

        card = QFrame()
        card.setObjectName("info_card")
        card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        for vol in volumes:
            name = vol.get("name", "Unknown")
            # Determine type
            vol_type = "Unknown"
            details = ""
            
            if "configMap" in vol:
                vol_type = "ConfigMap"
                details = vol["configMap"].get("name", "")
            elif "secret" in vol:
                vol_type = "Secret"
                details = vol["secret"].get("secretName", "")
            elif "persistentVolumeClaim" in vol:
                vol_type = "PVC"
                details = vol["persistentVolumeClaim"].get("claimName", "")
            elif "hostPath" in vol:
                vol_type = "HostPath"
                details = vol["hostPath"].get("path", "")
            elif "emptyDir" in vol:
                vol_type = "EmptyDir"
            elif "projected" in vol:
                vol_type = "Projected"
                # aggregated info
                sources = vol["projected"].get("sources", [])
                details = f"{len(sources)} sources"
            
            val_text = f"{vol_type}: {details}" if details else vol_type
            self.add_field_widget(name, val_text, card_layout)

        section_layout.addWidget(card)
        self.details_layout.addWidget(section_container)


    def add_spec_section(self, spec, exclude_keys=None):
        """Add spec section"""
        if not spec or (exclude_keys and all(k in exclude_keys for k in spec.keys())):
            return

        # Special handling for Pods to use the new redesigned section
        # Check against both "pods" and "pod" just in case of singular/plural mismatch
        if self.resource_type.lower() in ["pods", "pod"]:
            self.add_pod_spec_section(spec, exclude_keys)
            return

        # Standardized Section Container
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5) # 5px margin between header and card

        # Header container
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Icon
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", "info.svg")
        
        if os.path.exists(icon_path):
             icon_label = QLabel()
             theme = BaseDetailSectionStyles._get_theme()
             icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
             header_layout.addWidget(icon_label)

        # Header Title
        spec_title = QLabel("SPEC")
        spec_title.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        spec_title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        header_layout.addWidget(spec_title)
        
        section_layout.addWidget(header_container)

        # Card
        card = QFrame()
        card.setObjectName("info_card")
        card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING)
        card_layout.setSpacing(BaseDetailSectionStyles.FIELD_GAP)

        self.add_object_fields(spec, card_layout, exclude_keys=exclude_keys)
        # Check if card has any visible items (it might be empty if all top-level keys were excluded)
        if card_layout.count() > 0:
            # Ensure card doesn't stretch vertically
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            section_layout.addWidget(card)
            self.details_layout.addWidget(section_container)
        else:
            # Cleanup if empty
            section_container.deleteLater()

    def add_pod_status_section(self, status, exclude_keys=None):
        """Specialized Status section for Pods"""
        if not status:
            return

        # 1. Pod Conditions Card - REMOVED as per user request
        # conditions = status.get("conditions", [])
        # if conditions:
        #      self._add_pod_conditions_card(conditions)

        # 2. Container Statuses Card
        container_statuses = status.get("containerStatuses", [])
        if container_statuses:
             self._add_container_statuses_card("CONTAINER STATUSES", container_statuses)
        
        init_container_statuses = status.get("initContainerStatuses", [])
        if init_container_statuses:
             self._add_container_statuses_card("INIT CONTAINER STATUSES", init_container_statuses)

        # 3. IPs & Network Card
        # Gather network info
        network_info = {}
        if "podIP" in status:
            network_info["Pod IP"] = status["podIP"]
        if "hostIP" in status:
            network_info["Host IP"] = status["hostIP"]
        if "qosClass" in status:
            network_info["QoS Class"] = status["qosClass"]
        if "startTime" in status:
            start_time = status["startTime"]
            try:
                start_time = TimezoneManager.get_instance().format_time(start_time)
            except Exception:
                pass
            network_info["Start Time"] = start_time
        if "phase" in status:
            network_info["Phase"] = status["phase"]
            
        if network_info:
            self._add_pod_network_card(network_info)

        # 4. Raw Status Fallback
        handled_keys = ["conditions", "containerStatuses", "initContainerStatuses", "podIP", "hostIP", "podIPs", "qosClass", "startTime", "phase"]
        current_exclude = exclude_keys if exclude_keys else []
        final_exclude = list(set(current_exclude + handled_keys))
        
        remaining_keys = [k for k in status.keys() if k not in final_exclude]
        if remaining_keys:
             # Standardized Section Container for Raw Data
            section_container = QWidget()
            section_layout = QVBoxLayout(section_container)
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(5)

            # Header
            header_container = QWidget()
            header_layout = QHBoxLayout(header_container)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(10)
            header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Icon
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            icon_path = os.path.join(base_path, "Icons", "status.svg")
            
            if os.path.exists(icon_path):
                 icon_label = QLabel()
                 theme = BaseDetailSectionStyles._get_theme()
                 icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
                 header_layout.addWidget(icon_label)

            status_title = QLabel("ADDITIONAL STATUS")
            status_title.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
            header_layout.addWidget(status_title)
            section_layout.addWidget(header_container)

            # Card
            card = QFrame()
            card.setObjectName("info_card")
            card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING)
            card_layout.setSpacing(BaseDetailSectionStyles.FIELD_GAP)

            self.add_object_fields(status, card_layout, exclude_keys=final_exclude)
            
            if card_layout.count() > 0:
                # Ensure card can grow if fields wrap
                card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
                card_layout.addStretch(1) # Fix large vertical gaps
                section_layout.addWidget(card)
                self.details_layout.addWidget(section_container)

    def _add_pod_conditions_card(self, conditions):
        """Helper for Pod Conditions"""
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5)

        header_label = QLabel("CONDITIONS")
        header_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        section_layout.addWidget(header_label)

        card = QFrame()
        card.setObjectName("info_card")
        card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        for cond in conditions:
            c_type = cond.get("type", "Unknown")
            c_status = cond.get("status", "Unknown")
            c_msg = cond.get("message", "")
            c_reason = cond.get("reason", "")
            
            # Row for Condition
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            
            # Status Badge (approximate)
            color = BaseDetailSectionStyles._get_theme().colors.STATUS_ACTIVE if c_status == "True" else BaseDetailSectionStyles._get_theme().colors.STATUS_ERROR
            status_lbl = QLabel(c_type)
            status_lbl.setStyleSheet(f"font-weight: bold; color: {color};")
            row_layout.addWidget(status_lbl)
            
            # Details
            details_text = []
            if c_reason: details_text.append(f"Reason: {c_reason}")
            if c_msg: details_text.append(c_msg)
            
            if details_text:
                details_lbl = QLabel(" - ".join(details_text))
                details_lbl.setWordWrap(True)
                theme = BaseDetailSectionStyles._get_theme()
                details_lbl.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY}; font-size: 12px;")
                row_layout.addWidget(details_lbl, 1) # stretch
            else:
                row_layout.addStretch()

            card_layout.addWidget(row)

        section_layout.addWidget(card)
        self.details_layout.addWidget(section_container)

    def _add_container_statuses_card(self, title, statuses):
        """Helper for Container Statuses"""
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5)

        # Header
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Icon
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", "activity.svg")
        
        if os.path.exists(icon_path):
             icon_label = QLabel()
             theme = BaseDetailSectionStyles._get_theme()
             icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
             header_layout.addWidget(icon_label)

        header_label = QLabel(title)
        header_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        header_layout.addWidget(header_label)
        section_layout.addWidget(header_container)

        for status in statuses:
            card = QFrame()
            card.setObjectName("info_card")
            card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            card_layout.setSpacing(8)

            # Name & State
            name = status.get("name", "Unknown")
            state_info = status.get("state", {})
            state_str = "Unknown"
            state_reason = ""
            
            if "running" in state_info:
                state_str = "Running"
                started_at = state_info["running"].get("startedAt", "")
                if started_at: 
                    try:
                        started_at = TimezoneManager.get_instance().format_time(started_at)
                    except Exception:
                        pass
                    state_reason = f"Started: {started_at}"
            elif "waiting" in state_info:
                state_str = "Waiting"
                state_reason = state_info["waiting"].get("reason", "") + ": " + state_info["waiting"].get("message", "")
            elif "terminated" in state_info:
                state_str = "Terminated"
                state_reason = f"Exit Code: {state_info['terminated'].get('exitCode')} - {state_info['terminated'].get('reason', '')}"

            # Header Row
            top_row = QHBoxLayout()
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {BaseDetailSectionStyles._get_theme().colors.ACCENT_ORANGE};")
            top_row.addWidget(name_lbl)
            
            state_lbl = QLabel(state_str)
            status_type = 'success' if state_str == "Running" else ('warning' if state_str == "Waiting" else 'error')
            state_lbl.setStyleSheet(BaseDetailSectionStyles.get_status_badge_style(status_type, is_small=True))
            state_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            top_row.addWidget(state_lbl)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            if state_reason:
                self.add_field_widget("State Details", state_reason, card_layout)

            self.add_field_widget("Ready", str(status.get("ready", False)), card_layout)
            self.add_field_widget("Restarts", str(status.get("restartCount", 0)), card_layout)
            self.add_field_widget("Image", status.get("image", ""), card_layout)

            # imageID
            image_id = status.get("imageID", "")
            if image_id:
                self.add_field_widget("Image ID", image_id, card_layout)

            # containerID
            container_id = status.get("containerID", "")
            if container_id:
                self.add_field_widget("Container ID", container_id, card_layout)

            # LAST STATE — previous terminated/waiting state info
            last_state = status.get("lastState", {})
            if last_state:
                last_str = ""
                last_reason_str = ""
                if "terminated" in last_state:
                    lt = last_state["terminated"]
                    last_str = "Terminated"
                    parts = []
                    if lt.get("exitCode") is not None:
                        parts.append(f"Exit Code: {lt['exitCode']}")
                    if lt.get("reason"):
                        parts.append(f"Reason: {lt['reason']}")
                    if lt.get("startedAt"):
                        st = lt['startedAt']
                        try:
                            st = TimezoneManager.get_instance().format_time(st)
                        except Exception: pass
                        parts.append(f"Started: {st}")
                    if lt.get("finishedAt"):
                        ft = lt['finishedAt']
                        try:
                            from Utils.time_utils import TimezoneManager
                            ft = TimezoneManager.get_instance().format_time(ft)
                        except Exception: pass
                        parts.append(f"Finished: {ft}")
                    last_reason_str = " | ".join(parts)
                elif "waiting" in last_state:
                    lw = last_state["waiting"]
                    last_str = "Waiting"
                    last_reason_str = lw.get("reason", "") + (": " + lw.get("message", "") if lw.get("message") else "")
                elif "running" in last_state:
                    last_str = "Running"
                    start_val = last_state['running'].get('startedAt', '')
                    if start_val:
                        try:
                            from Utils.time_utils import TimezoneManager
                            start_val = TimezoneManager.get_instance().format_time(start_val)
                        except Exception: pass
                    last_reason_str = f"Started: {start_val}"
                if last_str:
                    self.add_field_widget("Last State", last_str, card_layout)
                if last_reason_str:
                    self.add_field_widget("Last State Details", last_reason_str, card_layout)

            # ALLOCATED RESOURCES — runtime resource allocation (k8s 1.24+)
            allocated = status.get("allocatedResources", {})
            if allocated:
                alloc_parts = [f"{k}: {v}" for k, v in allocated.items()]
                self.add_field_widget("Allocated Resources", " | ".join(alloc_parts), card_layout)

            # VOLUME MOUNTS (from status) — actual runtime mounted paths
            vol_mounts = status.get("volumeMounts", [])
            if vol_mounts:
                mount_lines = []
                for m in vol_mounts:
                    path = m.get("mountPath", "")
                    vol_name = m.get("name", "")
                    ro = " (ro)" if m.get("readOnly") else ""
                    recursive = " [recursive]" if m.get("recursiveReadOnly") == "Enabled" else ""
                    if path and vol_name:
                        mount_lines.append(f"{path} -> {vol_name}{ro}{recursive}")
                if mount_lines:
                    self.add_field_widget("Volume Mounts", "\n".join(mount_lines), card_layout)

            section_layout.addWidget(card)

        self.details_layout.addWidget(section_container)

    def _add_pod_network_card(self, info):
        """Helper for Network/Lifecycle Info"""
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5)

        # Header
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Icon
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", "globe.svg")
        
        if os.path.exists(icon_path):
             icon_label = QLabel()
             theme = BaseDetailSectionStyles._get_theme()
             icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
             header_layout.addWidget(icon_label)

        header_label = QLabel("IPs & NETWORK")
        header_label.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        header_layout.addWidget(header_label)
        section_layout.addWidget(header_container)

        card = QFrame()
        card.setObjectName("info_card")
        card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        for k, v in info.items():
            self.add_field_widget(k, str(v), card_layout)

        # Ensure card doesn't stretch vertically
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        section_layout.addWidget(card)
        self.details_layout.addWidget(section_container)

    def add_status_section(self, status, exclude_keys=None):
        """Add status section"""
        if not status or (exclude_keys and all(k in exclude_keys for k in status.keys())):
            return

        # Special handling for Pods to use the new redesigned section
        if self.resource_type.lower() in ["pods", "pod"]:
            self.add_pod_status_section(status, exclude_keys)
            return

        # Standardized Section Container
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5) # 5px margin between header and card

        # Header Container
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Icon
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", "status.svg")
        
        if os.path.exists(icon_path):
             icon_label = QLabel()
             theme = BaseDetailSectionStyles._get_theme()
             icon_label.setPixmap(self._render_svg_icon(icon_path, BaseDetailSectionStyles.get_section_header_color(), size=18))
             header_layout.addWidget(icon_label)

        status_title = QLabel("STATUS")
        status_title.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        status_title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        header_layout.addWidget(status_title)
        
        section_layout.addWidget(header_container)

        # Card
        card = QFrame()
        card.setObjectName("info_card")
        card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING, BaseDetailSectionStyles.CONTENT_PADDING)
        card_layout.setSpacing(BaseDetailSectionStyles.FIELD_GAP)

        if exclude_keys is None:
            exclude_keys = []
        
        # Runtime Handlers Section (Formatted at the top of Status Card)
        runtime_handlers = status.get("runtimeHandlers", [])
        if runtime_handlers:
            # 1. Header (Custom style: Standard Header but 15px)
            theme = BaseDetailSectionStyles._get_theme()
            rh_header = QLabel("RUNTIME HANDLERS")
            # Standard is 16px, user wants 1px less -> 15px. match other props.
            rh_header.setStyleSheet(f"""
                font-size: 15px; 
                font-weight: 700; 
                color: {theme.colors.TEXT_SECONDARY}; 
                letter-spacing: 0.5px; 
                margin-bottom: 5px;
            """)
            card_layout.addWidget(rh_header)

            # 2. List of Handlers
            for handler in runtime_handlers:
                # Container for each handler
                h_card = QFrame()
                h_card.setObjectName("handler_card")
                h_card.setStyleSheet(f"""
                    QFrame#handler_card {{
                        background-color: transparent;
                        border: 1px solid {theme.colors.BORDER_LIGHT};
                        border-radius: 6px;
                    }}
                """)
                h_layout = QVBoxLayout(h_card)
                h_layout.setContentsMargins(10, 10, 10, 10)
                h_layout.setSpacing(5)
                
                # Features (Placed FIRST)
                features = handler.get("features", {})
                if features:
                    f_header = QLabel("FEATURES")
                    # "text FEATURES style should be black just what we use for value like True and False"
                    # "and for FEATURES use little bit increased font" -> 11px (was 10px)
                    f_header.setStyleSheet(f"color: {theme.colors.TEXT_LIGHT}; font-size: 11px; font-weight: 600; margin-bottom: 5px;")
                    h_layout.addWidget(f_header)
                    
                    for f_key, f_val in features.items():
                        self.add_field_widget(f_key, str(f_val), h_layout)
                
                # Handler Name (Placed UNDER feature)
                # "do same font style for name value and lables which we use for userNamespaces"
                # Use standard add_field_widget to match exactly
                name_val = handler.get("name", "Unknown")
                self.add_field_widget("name", name_val, h_layout)
                
                card_layout.addWidget(h_card)

            # Add separator after handlers
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet(f"background-color: {BaseDetailSectionStyles._get_theme().colors.BORDER_LIGHT}; max-height: 1px; border: none; margin-top: 10px; margin-bottom: 10px;")
            card_layout.addWidget(line)

            # Mark as excluded so add_object_fields doesn't duplicate it
            exclude_keys.append("runtimeHandlers")

        # Render remaining fields
        self.add_object_fields(status, card_layout, exclude_keys=exclude_keys)
        
        # Check if card has any visible items
        if card_layout.count() > 0:
            # Ensure card doesn't stretch vertically
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            section_layout.addWidget(card)
            self.details_layout.addWidget(section_container)
        else:
            # Cleanup if empty
            section_container.deleteLater()

    def add_field_widget(self, field_name, field_value, parent_layout=None):
        """Add a field widget to display key-value pairs"""
        if parent_layout is None:
            parent_layout = self.details_layout
            
        field_container = QWidget()
        field_layout = QHBoxLayout(field_container)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(0) # Pixel-perfect 50/50 split
        field_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        name_label = QLabel(field_name)
        # Increased minimum width and allowed wrapping for labels to prevent occlusion
        name_label.setMinimumWidth(160)
        name_label.setWordWrap(True)
        # Add padding to keep text from touching the 50% line
        name_label.setStyleSheet(BaseDetailSectionStyles.get_field_label_style() + "padding-right: 20px;")
        name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        name_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        raw_string_value = str(field_value)
        # Check for sequences of 30+ characters with no spaces or standard punctuation
        has_long_word = bool(re.search(r'[^\s\-\.\/\,\:\;\"\{\}\[\]\(\)\_\=\@]{30,}', raw_string_value))

        # Format value for wrapping: inject zero-width space after more separators for robust wrapping
        display_value = raw_string_value
        for char in ['-', '.', '/', ',', ':', '"', '{', '}', '[', ']', '(', ')', '_', '=', ' ', '@']:
            display_value = display_value.replace(char, char + '\u200b')
            
        if len(display_value) > 1200 or has_long_word:


             # For long unbroken sequences, use QTextEdit to break anywhere naturally without polluting clipboard with \u200b
             from PyQt6.QtWidgets import QTextEdit
             from PyQt6.QtGui import QTextOption
             value_widget = QTextEdit(raw_string_value)
             value_widget.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)
             value_widget.setReadOnly(True)
             value_widget.setFrameShape(QFrame.Shape.NoFrame)
             value_widget.setStyleSheet(BaseDetailSectionStyles.get_field_value_style() + "background: transparent; padding: 0;")
             value_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
             value_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
             value_widget.document().documentLayout().documentSizeChanged.connect(
                 lambda size: value_widget.setFixedHeight(int(size.height()) + 5)
             )
             value_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        else:
             value_widget = QLabel(display_value)
             value_widget.setTextFormat(Qt.TextFormat.PlainText) # Prevent HTML parsing from hiding text containing < >
             value_widget.setStyleSheet(BaseDetailSectionStyles.get_field_value_style())
             value_widget.setWordWrap(True)
             # Use Expanding (H) / Preferred (V) to ensure it grows to fit wrapped text but doesn't take extra V space
             value_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
             value_widget.setMinimumWidth(0) 
             value_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
             # Left-aligned starting from center of card as requested
             value_widget.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        field_layout.addWidget(name_label, 1)
        field_layout.addWidget(value_widget, 1)

        # Row container should not stretch vertically
        field_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        parent_layout.addWidget(field_container)

    def add_object_fields(self, obj, parent_layout, prefix="", depth=0, exclude_keys=None):
        """Recursively add object fields with better limits and exclusion support"""
        if depth > 3 or _is_too_large(obj):  # Slightly deeper depth allowed for production-grade
            truncated_label = QLabel("... (data truncated for performance)")
            truncated_label.setStyleSheet(DetailSectionStyles.get_truncated_label_style())
            parent_layout.addWidget(truncated_label)
            return

        # Sort keys for deterministic output
        keys = sorted(obj.keys())
        for key in keys:
            if exclude_keys and key in exclude_keys and depth == 0:
                continue
                
            value = obj[key]
            field_name = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict) and value:
                # Add section header for nested objects
                field_title = QLabel(field_name.upper())
                field_title.setStyleSheet(DetailSectionStyles.get_nested_field_title_style(depth))
                parent_layout.addWidget(field_title)

                # Recursively add nested fields
                self.add_object_fields(value, parent_layout, field_name, depth + 1)

            elif isinstance(value, list) and value:
                if all(isinstance(item, dict) for item in value):
                    # List of objects
                    field_title = QLabel(field_name.upper())
                    field_title.setStyleSheet(DetailSectionStyles.get_nested_field_title_style(depth))
                    parent_layout.addWidget(field_title)

                    # Show first few items
                    for i, item in enumerate(value[:3]):
                        item_title = QLabel(f"{field_name}[{i}]")
                        item_title.setStyleSheet(DetailSectionStyles.get_item_title_style(depth))
                        parent_layout.addWidget(item_title)

                        self.add_object_fields(item, parent_layout, "", depth + 2)

                    if len(value) > 3:
                        more_items = QLabel(f"... and {len(value) - 3} more items")
                        more_items.setStyleSheet(DetailSectionStyles.get_more_items_label_style(depth))
                        parent_layout.addWidget(more_items)
                else:
                    # List of simple values
                    if all(isinstance(item, str) for item in value):
                        value_str = ", ".join(value)
                    else:
                        value_str = str(value)
                    self.add_field_widget(field_name, value_str, parent_layout)
            else:
                # Simple field
                self.add_field_widget(field_name, str(value), parent_layout)

    def clear_content(self):
        """Clear all details content, including layout items and stretches"""
        if not self.details_layout:
            return
            
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                # Recursively clear sub-layouts
                self._clear_layout(item.layout())
            # Spacers/Stretches are handled by takeAt(0)
        
        # Reset references to deleted widgets
        self._metadata_icon_label = None
