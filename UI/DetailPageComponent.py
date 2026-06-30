"""
Main DetailPage component that orchestrates all sections
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy, QApplication,
    QMessageBox, QDialog, QPushButton
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QRect, QEasingCurve, QSize, QTimer, pyqtSignal,
    QParallelAnimationGroup, QAbstractAnimation, QEvent, QByteArray
)
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from typing import Optional, Dict, Any
import logging
import os
import re
from UI.Icons import resource_path, Icons
from UI.ThemeManager import get_theme_manager

# Import Kubernetes client
from Utils.kubernetes_client import get_kubernetes_client

# Import section components
from .detail_sections.detailpage_overviewsection import DetailPageOverviewSection
from .detail_sections.detailpage_detailsection import DetailPageDetailsSection
from .detail_sections.detailpage_yamlsection import DetailPageYAMLSection
from .detail_sections.detailpage_eventssection import DetailPageEventsSection

from UI.ThemeAwarePage import ThemeAwareMixin
import Styles.DetailPageComponentStyles as DetailPageComponentStyles


class DetailPageComponent(ThemeAwareMixin, QWidget):
    """Main DetailPage component that manages all detail sections"""

    detail_closed_signal = pyqtSignal()
    back_signal = pyqtSignal()
    resource_updated_signal = pyqtSignal(str, str, str)
    refresh_main_page_signal = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.resource_type = None
        self.resource_name = None
        self.resource_namespace = None
        self.is_minimized = False
        self.animation_in_progress = False
        self._closing = False
        self._programmatic_close = False

        # Get Kubernetes client
        self.kubernetes_client = get_kubernetes_client()

        # Track section loading states
        self.section_loading_states = {}

        # Initialize raw data attributes to avoid hasattr checks
        self.chart_raw_data = None
        self.release_raw_data = None
        self.resource_raw_data = None
        self.event_raw_data = None

        self.setup_ui()
        self.setup_sections()
        self.setup_animations()
        # Note: Theme signals connected via ThemeAwareMixin
        self.hide()

    def _on_theme_changed(self, theme_name):
        """Refresh styles when theme changes"""
        # Refresh main widget style
        self.setStyleSheet(DetailPageComponentStyles.get_main_widget_style())
        # Refresh header
        if hasattr(self, 'header'):
            self.header.setStyleSheet(DetailPageComponentStyles.get_header_style())
        # Refresh back button
        if hasattr(self, 'back_button'):
            self.back_button.setStyleSheet(DetailPageComponentStyles.get_back_button_style())
        # Refresh title label
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(DetailPageComponentStyles.get_title_label_style())
        # Refresh resize handle
        if hasattr(self, 'resize_handle'):
            self.resize_handle.setStyleSheet(DetailPageComponentStyles.get_resize_handle_style())
        # Refresh content area
        if hasattr(self, 'content_area'):
            self.content_area.setStyleSheet(DetailPageComponentStyles.get_content_area_style())
        # Refresh tab widget
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setStyleSheet(DetailPageComponentStyles.get_tab_widget_style())
        
        # Update icon
        self._update_close_button_icon(theme_name)
        
        # Refresh header icon using the centralized method
        if hasattr(self, 'icon_label'):
             self.icon_label.setStyleSheet(DetailPageComponentStyles.get_header_icon_style())
             self._update_icon()

    def _update_close_button_icon(self, theme_name):
        """Update close button icon when theme changes"""
        if hasattr(self, 'back_button'):
            icon = Icons.get_theme_icon("Detailpage_Close.svg", theme_name)
            if icon and not icon.isNull():
                self.back_button.setIcon(icon)

    def _update_icon(self):
        """Update the header resource icon based on type with theme-aware orange color"""
        if not self.resource_type:
            self.icon_label.clear()
            return
            
        theme = get_theme_manager().get_current_theme()
        color = theme.colors.ACCENT_ORANGE
        
        # Clean and normalize resource type for mapping
        res_type = self.resource_type.lower()
        # Don't strip 's' from resources that end in 's' naturally or plural forms we want to handle in map
        if res_type.endswith('s') and res_type not in ["nodes", "pods", "services", "ingress", "storageclasses", "storageclass"]:
             icon_id = res_type[:-1]
        else:
             icon_id = res_type

        # Specific mapping for icons
        icon_map = {
             "node": "node.svg",
             "nodes": "node.svg",
             "pod": "pod.svg",
             "pods": "pod.svg",
             "configmap": "configmap.svg",
             "secret": "secret.svg",
             "service": "service.svg",
             "services": "service.svg",
             "deployment": "deployment.svg",
             "deployments": "deployment.svg",
             "ingress": "globe.svg",
             "namespace": "tag.svg",
             "namespaces": "tag.svg",
             "endpoint": "endpoint.svg",
             "endpoints": "endpoint.svg",
             "replicaset": "replica.svg",
             "replicasets": "replica.svg",
             "persistentvolume": "nav_storage.svg",
             "persistentvolumes": "nav_storage.svg",
             "persistentvolumeclaim": "nav_storage.svg",
             "persistentvolumeclaims": "nav_storage.svg",
             "storageclass": "nav_storage.svg",
             "storageclasse": "nav_storage.svg", # Handle common truncation
             "storagecla": "nav_storage.svg",    # Handle common truncation seen in screenshot
             "storageclasses": "nav_storage.svg",
             "pv": "nav_storage.svg",
             "pvc": "nav_storage.svg"
        }

        # Try to find SVG in the map, otherwise use default
        svg_filename = icon_map.get(icon_id, "details-default.svg")
        icon_path = resource_path(os.path.join("Icons", svg_filename))

        if os.path.exists(icon_path):
             pixmap = self._render_custom_svg(icon_path, color, size=32)
             if pixmap and not pixmap.isNull():
                  self.icon_label.setPixmap(pixmap)
                  return

        # Fallback to theme icon logic if SVG rendering fails
        icon = Icons.get_theme_icon_by_id(res_type, get_theme_manager().get_current_theme_name() or "Dark")
        if icon:
             self.icon_label.setPixmap(icon.pixmap(32, 32))
        else:
             self.icon_label.clear()

    def _render_custom_svg(self, icon_path, color, size=32):
        """Load an SVG from file, recolor it, and return a QPixmap."""
        if not icon_path or not os.path.exists(icon_path):
            return None
            
        try:
            with open(icon_path, 'r', encoding='utf-8') as f:
                svg_data = f.read()
                
            # Pattern to match stroke or fill attributes/styles with common sentinel colors
            # This catches #000000, #888888, #F5F5F5, black, etc.
            sentinel_pattern = r'(?:#[0-9a-fA-F]{3,6}|black|white|currentColor|gray)'
            
            # Replace attributes: stroke="color" or fill="color"
            svg_data = re.sub(rf'(stroke|fill)\s*=\s*["\']{sentinel_pattern}["\']', rf'\1="{color}"', svg_data, flags=re.IGNORECASE)
            
            # Replace inline styles: stroke: color or fill: color
            svg_data = re.sub(rf'(stroke|fill)\s*:\s*{sentinel_pattern}', rf'\1: {color}', svg_data, flags=re.IGNORECASE)

            renderer = QSvgRenderer(QByteArray(svg_data.encode('utf-8')))
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            return pixmap
        except Exception as e:
            logging.error(f"Error rendering custom SVG {icon_path}: {str(e)}")
            return None

    def setup_ui(self):
        """Setup main UI structure"""
        self.setFixedWidth(DetailPageComponentStyles.get_detail_page_width())
        self.setMinimumWidth(DetailPageComponentStyles.get_detail_page_min_width())
        self.setMaximumWidth(DetailPageComponentStyles.get_detail_page_max_width())
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self.setStyleSheet(DetailPageComponentStyles.get_main_widget_style())

        self.apply_shadow_effect()

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.create_header()
        self.create_resize_handle()
        self.create_content_area()

    def apply_shadow_effect(self):
        """Apply shadow effect to detail page"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow_color = QColor(0, 0, 0)
        shadow_color.setAlpha(80)
        shadow.setColor(shadow_color)
        shadow.setOffset(-2, 0)
        self.setGraphicsEffect(shadow)

    def create_header(self):
        """Create header with title and close button"""
        self.header = QWidget()
        self.header.setFixedHeight(60)
        self.header.setStyleSheet(DetailPageComponentStyles.get_header_style())

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(15, 10, 15, 10)

        # Back/Close button
        self.back_button = QPushButton()

        # Determine current theme and load correct icon
        theme_name = get_theme_manager().get_current_theme_name() or "Dark"
        self.back_button.setIcon(Icons.get_theme_icon("Detailpage_Close.svg", theme_name))
        self.back_button.setIconSize(QSize(20, 20))
        self.back_button.setFixedSize(40, 40)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)  # Hand cursor on hover
        self.back_button.setStyleSheet(DetailPageComponentStyles.get_back_button_style())
        self.back_button.clicked.connect(self.close_detail)

        # Resource Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setStyleSheet(DetailPageComponentStyles.get_header_icon_style())
        self.icon_label.setScaledContents(True)

        # Title
        self.title_label = QLabel("Resource Details")
        self.title_label.setStyleSheet(DetailPageComponentStyles.get_title_label_style())
        self.title_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Action button (for Helm operations)
        self.action_button = QPushButton("Install")
        self.action_button.setCursor(Qt.CursorShape.PointingHandCursor)  # Hand cursor on hover
        self.action_button.setStyleSheet(DetailPageComponentStyles.get_action_button_install_style())
        self.action_button.clicked.connect(self.handle_action_button)
        self.action_button.hide()

        header_layout.addWidget(self.back_button)
        header_layout.addSpacing(10) # Add spacing between back button and icon
        header_layout.addWidget(self.icon_label)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.action_button)

        self.main_layout.addWidget(self.header)

    def create_resize_handle(self):
        """Create resize handle for panel resizing"""
        self.resize_handle = QFrame(self)
        self.resize_handle.setFixedWidth(5)
        self.resize_handle.setStyleSheet(DetailPageComponentStyles.get_resize_handle_style())
        self.resize_handle.setCursor(Qt.CursorShape.SizeHorCursor)
        self.resize_handle.show()

        self.resize_start_x = 0
        self.resize_start_width = self.width()

        # Connect mouse events for resizing
        self.resize_handle.mousePressEvent = self.resize_handle_mousePressEvent
        self.resize_handle.mouseMoveEvent = self.resize_handle_mouseMoveEvent
        self.resize_handle.mouseReleaseEvent = self.resize_handle_mouseReleaseEvent

    def create_content_area(self):
        """Create main content area with tabs"""
        self.content_area = QWidget()
        self.content_area.setStyleSheet(DetailPageComponentStyles.get_content_area_style())

        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Create tab widget
        self.tab_widget = QTabWidget()
        # Completely disable tab scrolling behavior
        self.tab_widget.tabBar().setUsesScrollButtons(False)
        self.tab_widget.tabBar().setExpanding(True)
        self.tab_widget.tabBar().setMovable(False)
        self.tab_widget.tabBar().setDrawBase(False)  # Disable base drawing

        self.tab_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tab_widget.tabBar().setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Install event filter on tab bar to block wheel events
        self.tab_widget.tabBar().installEventFilter(self)

        self.tab_widget.setStyleSheet(DetailPageComponentStyles.get_tab_widget_style())

        # Set hand cursor for tabs when hovering
        self.tab_widget.tabBar().setCursor(Qt.CursorShape.PointingHandCursor)

        content_layout.addWidget(self.tab_widget)
        self.main_layout.addWidget(self.content_area)

    def setup_sections(self):
        """Setup all detail sections"""
        # Create sections
        self.overview_section = DetailPageOverviewSection(self.kubernetes_client, self)
        self.details_section = DetailPageDetailsSection(self.kubernetes_client, self)
        self.yaml_section = DetailPageYAMLSection(self.kubernetes_client, self)
        self.events_section = DetailPageEventsSection(self.kubernetes_client, self)

        # Add sections to tabs
        self.tab_widget.addTab(self.overview_section, "Overview")
        self.tab_widget.addTab(self.details_section, "Details")
        self.tab_widget.addTab(self.yaml_section, "YAML")
        self.tab_widget.addTab(self.events_section, "Events")

        # Set initial tab cleanly
        self.tab_widget.setCurrentIndex(0)

        # Connect section signals
        self.connect_section_signals()

        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self.handle_tab_changed)

    def connect_section_signals(self):
        """Connect signals from all sections"""
        sections = [self.overview_section, self.details_section, self.yaml_section, self.events_section]

        for section in sections:
            section.loading_started.connect(self.handle_section_loading_started)
            section.loading_finished.connect(self.handle_section_loading_finished)
            section.error_occurred.connect(self.handle_section_error)
            section.data_loaded.connect(self.handle_section_data_loaded)

    def setup_animations(self):
        """Setup animations for show/hide"""
        self.animation_group = QParallelAnimationGroup()

        self.slide_animation = QPropertyAnimation(self, b"geometry")
        self.slide_animation.setDuration(200)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutQuart)

        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutQuart)

        self.animation_group.addAnimation(self.slide_animation)
        self.animation_group.addAnimation(self.fade_animation)
        self.animation_group.finished.connect(self.on_animation_finished)

    def show_detail(self, resource_type: str, resource_name: str, namespace: Optional[str] = None):
        """Show detail for specified resource"""
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.resource_namespace = namespace
        
        # Format resource type for display (capitalize sections if needed)
        # e.g. "nodes" -> "Node"
        resource_type_display = resource_type.capitalize()
        if resource_type_display.endswith('s'):
             resource_type_display = resource_type_display[:-1]

        # Update title
        title_text = f"{resource_type_display}: {resource_name}"
        if namespace:
            title_text += f" (ns: {namespace})"
        self.title_label.setText(title_text)

        # Update header icon
        self._update_icon()

        # Handle action button for Helm resources
        self.setup_action_button(resource_type)

        # Clear and setup sections
        self.clear_all_sections()
        self.set_resource_for_all_sections(resource_type, resource_name, namespace)

        # Handle special raw data for charts and releases
        self._handle_special_resource_data(resource_type)

        self.tab_widget.setCurrentIndex(0)

        # Show with animation
        if not self.isVisible():
            self.show_with_animation()

        # Load data after animation completes
        QTimer.singleShot(300, self.load_current_tab_data)

    def _handle_special_resource_data(self, resource_type: str):
        """Handle special resource data for charts and releases"""
        raw_data = None

        # Get the appropriate raw data based on resource type
        # Attributes are initialized in __init__, so direct access is safe
        if resource_type.lower() in ["chart", "helmchart"] and self.chart_raw_data is not None:
            raw_data = self.chart_raw_data
            logging.info(f"DetailPageComponent: Using chart raw data for {resource_type}")
        elif resource_type.lower() in ["helmrelease", "release"] and self.release_raw_data is not None:
            raw_data = self.release_raw_data
            logging.info(f"DetailPageComponent: Using release raw data for {resource_type}")
        elif resource_type.lower() in ["event", "events"] and self.event_raw_data is not None:
            raw_data = self.event_raw_data
            logging.info(f"DetailPageComponent: Using event raw data for {resource_type}")
        elif self.resource_raw_data is not None:
            raw_data = self.resource_raw_data
            logging.info(f"DetailPageComponent: Using generic raw data for {resource_type}")

        if raw_data:
            logging.info(f"DetailPageComponent: Processing raw data for {resource_type}, data keys: {list(raw_data.keys())}")
            # Pass the raw data to all sections EXCEPT events section
            # Events section should ALWAYS fetch real kubernetes events regardless of generic raw data
            sections = [self.overview_section, self.details_section, self.yaml_section]
            for section in sections:
                if hasattr(section, 'set_raw_data'):
                    logging.info(f"DetailPageComponent: Setting raw data for {section.section_name}")
                    section.set_raw_data(raw_data)
                # Store data directly on the section for immediate access
                section.current_data = raw_data
        else:
            # Only warn if this is a resource type that should have raw data
            if resource_type.lower() in ["chart", "helmchart", "helmrelease", "release", "event", "events"]:
                logging.warning(f"DetailPageComponent: Expected raw data for {resource_type} but none found")
            else:
                logging.debug(f"DetailPageComponent: No special raw data handling needed for {resource_type}")

    def _post_show_setup(self):
        """Single post-show setup to avoid flickering"""
        try:
            # Load data for current tab only
            self.load_current_tab_data()
        except Exception as e:
            logging.error(f"Error in post-show setup: {e}")

    def setup_action_button(self, resource_type: str):
        """Setup action button based on resource type"""
        if resource_type == "chart":
            self.action_button.setText("Install")
            self.action_button.setStyleSheet(DetailPageComponentStyles.get_action_button_install_style())
            self.action_button.show()
        elif resource_type == "helmrelease":
            self.action_button.setText("Upgrade")
            self.action_button.setStyleSheet(DetailPageComponentStyles.get_action_button_upgrade_style())
            self.action_button.show()
        else:
            self.action_button.hide()

    def handle_action_button(self):
        """Handle action button click"""
        if self.resource_type == "chart":
            self._handle_install_chart()
        elif self.resource_type == "helmrelease":
            self._handle_upgrade_release()

    def _handle_install_chart(self):
        """Handle chart installation - copied from ChartsPage._handle_install_chart"""
        # Prevent multiple installations from running simultaneously
        if getattr(self, 'installation_in_progress', False):
            QMessageBox.warning(self, "Installation in Progress",
                               "Another chart installation is already in progress. Please wait for it to complete.")
            return

        # Get chart data - look for the data in the right place
        chart_data = None
        if hasattr(self, 'chart_raw_data') and self.chart_raw_data:
            chart_data = self.chart_raw_data
        elif hasattr(self, 'resource_raw_data') and self.resource_raw_data:
            chart_data = self.resource_raw_data

        if not chart_data:
            QMessageBox.warning(self, "Installation Error", "Chart data not available.")
            return

        # Extract chart information from raw data
        metadata = chart_data.get("metadata", {})
        labels = metadata.get("labels", {})
        spec = chart_data.get("spec", {})

        chart_name = self.resource_name
        repository = labels.get("repository", spec.get("repository", ""))

        if not repository:
            QMessageBox.critical(self, "Installation Error", "Repository information is missing for this chart.")
            return

        # Import the install dialog
        from UI.ChartInstallDialog import ChartInstallDialog, install_helm_chart

        # Create and show install dialog
        dialog = ChartInstallDialog(chart_name, repository, self)

        # Store reference to prevent multiple dialogs
        if getattr(self, 'current_installation_dialog', None) is not None:
            return  # Dialog already open

        self.current_installation_dialog = dialog

        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get installation options
                options = dialog.get_values()

                if options:
                    # Set installation state
                    self.installation_in_progress = True

                    try:
                        # Start installation
                        success, message = install_helm_chart(chart_name, repository, options, self)

                        # Show single result dialog
                        if success:
                            QMessageBox.information(self, "Installation Successful",
                                                   f"Chart '{chart_name}' has been successfully installed!\n\n{message}")
                        else:
                            QMessageBox.critical(self, "Installation Failed",
                                               f"Failed to install chart '{chart_name}'.\n\n{message}")
                    finally:
                        # Reset installation state
                        self.installation_in_progress = False
        finally:
            # Clear dialog reference
            self.current_installation_dialog = None

    def _handle_upgrade_release(self):
        """Show upgrade dialog for Helm release - copied from ReleasesPage._show_upgrade_dialog"""
        try:
            release_name = self.resource_name
            namespace = self.resource_namespace or "default"

            # Find the release data to get chart info
            release_data = None
            if hasattr(self, 'release_raw_data') and self.release_raw_data:
                release_data = self.release_raw_data
            elif hasattr(self, 'resource_raw_data') and self.resource_raw_data:
                release_data = self.resource_raw_data

            if not release_data:
                QMessageBox.warning(self, "Upgrade Error", f"Release data not found for {release_name}")
                return

            # Try to extract chart info from release data (similar to ReleasesPage)
            # The release_data comes from ReleasesPage with this structure:
            # metadata.labels.chart contains the chart info
            metadata = release_data.get("metadata", {})
            labels = metadata.get("labels", {})
            chart_info = labels.get("chart", "").split("-")
            chart_name = chart_info[0] if chart_info else "unknown"

            # For now, we'll use a default repository (in real scenarios, this should be stored with the release)
            repository = "bitnami"  # Default repository, could be enhanced to track original repo

            from UI.ChartInstallDialog import ChartInstallDialog, upgrade_helm_release

            # Create and show upgrade dialog (reusing install dialog)
            dialog = ChartInstallDialog(chart_name, repository, self)
            dialog.setWindowTitle(f"Upgrade Release: {release_name}")

            # Pre-populate with current release info
            dialog.release_name_input.setText(release_name)
            dialog.release_name_input.setEnabled(False)  # Don't allow changing release name during upgrade
            dialog.namespace_combo.setCurrentText(namespace)
            dialog.namespace_combo.setEnabled(False)  # Don't allow changing namespace during upgrade
            dialog.create_namespace_checkbox.setChecked(False)
            dialog.create_namespace_checkbox.setEnabled(False)  # Namespace already exists

            # Change button text to indicate upgrade
            dialog.install_button.setText("Upgrade Release")

            if dialog.exec() == QDialog.DialogCode.Accepted:
                options = dialog.get_values()
                if options:
                    # Perform upgrade
                    success, message = upgrade_helm_release(release_name, namespace, chart_name, repository, options, self)

                    if success:
                        QMessageBox.information(self, "Upgrade Successful", message)
                        # Reload releases to show updated data - emit refresh signal
                        self.refresh_main_page_signal.emit("helmrelease", release_name, namespace)
                    else:
                        QMessageBox.critical(self, "Upgrade Failed", message)

        except Exception as e:
            logging.error(f"Error showing upgrade dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to show upgrade dialog: {str(e)}")

    def set_resource_for_all_sections(self, resource_type: str, resource_name: str, namespace: Optional[str]):
        """Set resource information for all sections"""
        sections = [self.overview_section, self.details_section, self.yaml_section, self.events_section]

        for section in sections:
            section.set_resource(resource_type, resource_name, namespace)

    def clear_all_sections(self):
        """Clear content from all sections"""
        sections = [self.overview_section, self.details_section, self.yaml_section, self.events_section]

        for section in sections:
            section.clear_content()

    def handle_tab_changed(self, index):
        """Handle tab change - load data for newly active tab with optimization"""
        # Add small delay to prevent rapid tab switching issues
        if hasattr(self, '_tab_change_timer'):
            self._tab_change_timer.stop()

        self._tab_change_timer = QTimer()
        self._tab_change_timer.setSingleShot(True)
        self._tab_change_timer.timeout.connect(self.load_current_tab_data)
        self._tab_change_timer.start(50)  # 50ms delay for smooth switching

    def load_current_tab_data(self):
        """Load data for currently active tab with performance optimization"""
        current_index = self.tab_widget.currentIndex()
        sections = [self.overview_section, self.details_section, self.yaml_section, self.events_section]

        if 0 <= current_index < len(sections):
            current_section = sections[current_index]

            # Check if data matches current resource before reusing
            if (hasattr(current_section, 'current_data') and
                current_section.current_data and
                current_section.resource_type == self.resource_type and
                current_section.resource_name == self.resource_name and
                current_section.resource_namespace == self.resource_namespace):
                # Data is for current resource, safe to reuse
                return

            # Load data asynchronously
            QTimer.singleShot(0, current_section.load_data)

    def handle_section_loading_started(self, section_name: str):
        """Handle section loading started"""
        self.section_loading_states[section_name] = True
        self.update_global_loading_state()
        logging.debug(f"Section {section_name} started loading")

    def handle_section_loading_finished(self, section_name: str):
        """Handle section loading finished"""
        self.section_loading_states[section_name] = False
        self.update_global_loading_state()
        logging.debug(f"Section {section_name} finished loading")

    def handle_section_error(self, section_name: str, error_message: str):
        """Handle section error"""
        self.section_loading_states[section_name] = False
        self.update_global_loading_state()

        # Don't log missing resources as errors
        if ("not found" in error_message.lower() or
            "404" in error_message or
            "not available in this cluster" in error_message.lower()):
            logging.debug(f"Resource not available in {section_name}: {error_message}")
        else:
            logging.error(f"Error in {section_name}: {error_message}")

    def handle_section_data_loaded(self, section_name: str, data: Dict[str, Any]):
        """Handle section data loaded - including refresh requests"""
        logging.debug(f"Data loaded for {section_name}")

        # Check if this is a refresh request from YAML section
        if isinstance(data, dict) and data.get('action') == 'refresh_main_page':
            resource_type = data.get('resource_type')
            resource_name = data.get('resource_name')
            namespace = data.get('namespace')

            if resource_type and resource_name:
                # Emit signal to refresh main page
                self.refresh_main_page_signal.emit(resource_type, resource_name, namespace or "")
                logging.info(f"Requesting main page refresh for {resource_type}/{resource_name}")

    def setup_refresh_connection(self):
        """Setup connection for main page refresh"""
    # This will be connected by the DetailManager to ClusterView
    pass

    def update_global_loading_state(self):
        """Update global loading indicator based on section states."""
        # Placeholder: extend this to drive a global spinner if one is added.
        pass

    # Resize handle methods
    def resize_handle_mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.resize_start_x = int(event.globalPosition().x())
            self.resize_start_width = self.width()

    def resize_handle_mouseMoveEvent(self, event):
        if hasattr(event, 'buttons') and event.buttons() == Qt.MouseButton.LeftButton:
            delta = self.resize_start_x - event.globalPosition().x()
            new_width = int(self.resize_start_width + delta)

            if new_width >= DetailPageComponentStyles.get_detail_page_min_width() and new_width <= DetailPageComponentStyles.get_detail_page_max_width():
                self.setFixedWidth(new_width)
                if self.parent():
                    self.move(self.parent().width() - self.width(), 0)

    def resize_handle_mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.resize_start_width = self.width()

    # Animation methods
    def show_with_animation(self):
        """Show detail page with animation"""
        if self.isVisible():
            return

        # Temporarily disable shadow during animation
        self.setGraphicsEffect(None)

        if self.parent():
            self.move(self.parent().width(), 0)
            target_x = self.parent().width() - self.width()
            parent_height = self.parent().height()
        else:
            screen_width = QApplication.primaryScreen().geometry().width()
            screen_height = QApplication.primaryScreen().geometry().height()
            self.move(screen_width, 0)
            target_x = screen_width - self.width()
            parent_height = screen_height

        self.setFixedHeight(parent_height)
        self.show()
        self.raise_()

        self.slide_animation.setStartValue(self.geometry())
        self.slide_animation.setEndValue(QRect(target_x, 0, self.width(), parent_height))

        self.animation_group.setDirection(QAbstractAnimation.Direction.Forward)
        self.animation_group.start()

        def restore_effects():
            self.apply_shadow_effect()
            if self.parent_window:
                self.parent_window.removeEventFilter(self)
                self.parent_window.installEventFilter(self)

        QTimer.singleShot(250, restore_effects)

    def hide_with_animation(self):
        """Hide detail page with animation"""
        if not self.isVisible() or self.animation_in_progress:
            return

        self.animation_in_progress = True

        # Create hide animation
        self.hide_animation = QPropertyAnimation(self, b"geometry")
        self.hide_animation.setDuration(200)
        self.hide_animation.setEasingCurve(QEasingCurve.Type.OutQuart)
        self.hide_animation.setStartValue(self.geometry())

        # Calculate end position
        if self.parent():
            end_rect = QRect(self.parent().width(), 0, self.width(), self.height())
        else:
            screen_width = QApplication.primaryScreen().geometry().width()
            end_rect = QRect(screen_width, 0, self.width(), self.height())

        self.hide_animation.setEndValue(end_rect)

        def finish_hiding():
            self.hide()
            self.animation_in_progress = False
            self.hide_animation.deleteLater()

        self.hide_animation.finished.connect(finish_hiding)
        self.hide_animation.start()

        if not self._programmatic_close:
            self.back_signal.emit()

        self._programmatic_close = False

    def on_animation_finished(self):
        """Handle animation finished"""
        self.animation_in_progress = False
        if hasattr(self, '_closing') and self._closing:
            self.hide()
            self._closing = False

    def close_detail(self):
        """Close detail page with complete state cleanup"""
        # Clean up timers
        if hasattr(self, '_tab_change_timer'):
            self._tab_change_timer.stop()

        # CRITICAL: Disconnect all section signals to stop async operations
        sections = [self.overview_section, self.details_section, self.yaml_section, self.events_section]
        for section in sections:
            if hasattr(section, 'disconnect_api_signals'):
                section.disconnect_api_signals()

        # Clear all sections to remove data
        self.clear_all_sections()

        # Clear special resource data
        self.resource_type = None
        self.resource_name = None
        self.resource_namespace = None
        
        if hasattr(self, 'icon_label'):
            self.icon_label.clear()

        # Clear raw data to prevent reuse for wrong resources
        self.chart_raw_data = None
        self.release_raw_data = None
        self.resource_raw_data = None
        self.event_raw_data = None

        self.detail_closed_signal.emit()

        if self.parent_window:
            self.parent_window.removeEventFilter(self)

        self.hide_with_animation()

    # Event handling
    def resizeEvent(self, event):
        """Handle resize event"""
        super().resizeEvent(event)
        if hasattr(self, 'resize_handle'):
            self.resize_handle.setFixedHeight(self.height())
            self.resize_handle.move(0, 0)
            self.resize_handle.raise_()
            self.resize_handle.show()

    def eventFilter(self, obj, event):
        """Filter events for outside click detection and block wheel events on tabs"""
        # Block wheel events on tab bar to prevent tab scrolling
        if obj == self.tab_widget.tabBar() and event.type() == QEvent.Type.Wheel:
            return True  # Block the wheel event completely

        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            try:
                if hasattr(event, 'globalPosition'):
                    global_pos = event.globalPosition().toPoint()
                elif hasattr(event, 'globalPos'):
                    global_pos = event.globalPos()
                else:
                    return super().eventFilter(obj, event)

                # Check if click is outside detail panel
                detail_global_rect = self.geometry()
                if self.parent():
                    detail_global_rect.translate(self.parent().mapToGlobal(self.parent().pos()))

                if not detail_global_rect.contains(global_pos):
                    clicked_widget = QApplication.widgetAt(global_pos)

                    if clicked_widget:
                        parent = clicked_widget
                        while parent:
                            if (parent.inherits('QTableWidget') or
                                    parent.inherits('QTreeWidget') or
                                    parent.inherits('QListWidget')):
                                return super().eventFilter(obj, event)

                            if isinstance(parent, DetailPageComponent):
                                return super().eventFilter(obj, event)

                            parent = parent.parent()

                    self.close_detail()
                    return True

            except Exception as e:
                logging.error(f"Error in eventFilter: {e}")

        return super().eventFilter(obj, event)

    def showEvent(self, event):
        """Override showEvent to ensure proper tab widget rendering"""
        super().showEvent(event)


    def close_detail_panel(self):
        """Public method to close detail panel"""
        self._programmatic_close = True
        self.close_detail()
