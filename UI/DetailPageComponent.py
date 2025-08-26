"""
Main DetailPage component that orchestrates all sections
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QFrame,
    QGraphicsDropShadowEffect, QToolButton, QSizePolicy, QApplication,
    QMessageBox, QDialog, QPushButton
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QRect, QEasingCurve, QSize, QTimer, pyqtSignal,
    QParallelAnimationGroup, QAbstractAnimation, QEvent
)
from PyQt6.QtGui import QColor, QIcon
from typing import Optional, Dict, Any
import logging
from UI.Icons import resource_path
import subprocess
import tempfile
import os

# Import Kubernetes client
from Utils.kubernetes_client import get_kubernetes_client

# Import section components
from .detail_sections.detailpage_overviewsection import DetailPageOverviewSection
from .detail_sections.detailpage_detailsection import DetailPageDetailsSection
from .detail_sections.detailpage_yamlsection import DetailPageYAMLSection
from .detail_sections.detailpage_eventssection import DetailPageEventsSection

from UI.Styles import AppStyles, AppColors
from PyQt6.QtWidgets import QPushButton, QFrame
# from Utils.helm_utils import ChartInstallDialog, install_helm_chart


class DetailPageComponent(QWidget):
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

        self.setup_ui()
        self.setup_sections()
        self.setup_animations()
        self.hide()

    def setup_ui(self):
        """Setup main UI structure"""
        self.setFixedWidth(AppStyles.DETAIL_PAGE_WIDTH)
        self.setMinimumWidth(AppStyles.DETAIL_PAGE_MIN_WIDTH)
        self.setMaximumWidth(AppStyles.DETAIL_PAGE_MAX_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self.setStyleSheet(f"""
            background-color: {AppColors.BG_SIDEBAR};
            border: none;
            border-radius: 8px;
        """)

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
        self.header.setStyleSheet(f"""
            background-color: {AppColors.BG_HEADER};
            border: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        """)

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(15, 10, 15, 10)

        # Back/Close button - FIXED: Added icon and proper styling
        self.back_button = QPushButton()
        self.back_button.setIcon(QIcon(resource_path("Icons/Detailpage_Close.svg")))
        self.back_button.setIconSize(QSize(20, 20))
        self.back_button.setFixedSize(40, 40)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)  # Hand cursor on hover
        self.back_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {AppColors.BORDER_LIGHT};
                border-radius: 20px;
            }}
            QPushButton:hover {{
                background-color: {AppColors.BG_LIGHT};
            }}
            QPushButton:pressed {{
                background-color: {AppColors.BG_MEDIUM};
            }}
        """)
        self.back_button.clicked.connect(self.close_detail)

        # Title
        self.title_label = QLabel("Resource Information")
        self.title_label.setStyleSheet(f"""
            color: {AppColors.TEXT_LIGHT};
            font-size: 16px;
            font-weight: bold;
            margin-left: 10px;
        """)
        self.title_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Action button (for Helm operations)
        self.action_button = QPushButton("Install Chart")
        self.action_button.setCursor(Qt.CursorShape.PointingHandCursor)  # Hand cursor on hover
        self.action_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {AppColors.ACCENT_GREEN};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
            QPushButton:pressed {{
                background-color: #3d8b40;
            }}
        """)
        self.action_button.clicked.connect(self.handle_action_button)
        self.action_button.hide()

        header_layout.addWidget(self.back_button)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.action_button)

        self.main_layout.addWidget(self.header)

    def create_resize_handle(self):
        """Create resize handle for panel resizing"""
        self.resize_handle = QFrame(self)
        self.resize_handle.setFixedWidth(5)
        self.resize_handle.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;
            }}
            QFrame:hover {{
                background-color: {AppColors.ACCENT_BLUE};
            }}
        """)
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
        self.content_area.setStyleSheet(f"background-color: {AppColors.BG_SIDEBAR}; border: none;")

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

        self.tab_widget.setStyleSheet(f"""
            QTabWidget {{
                border: none;
                background-color: {AppColors.BG_SIDEBAR};
            }}
            QTabWidget::pane {{
                border: none;
                background-color: {AppColors.BG_SIDEBAR};
                margin: 0px;
                padding: 0px;
                top: 0px;
            }}
            QTabBar {{
                qproperty-drawBase: 0;
                border: none;
                background-color: {AppColors.BG_SIDEBAR};
                outline: none;
                margin: 0px;
                padding: 0px;
            }}
            QTabBar::tab {{
                background-color: {AppColors.BG_SIDEBAR};
                color: {AppColors.TEXT_SECONDARY};
                padding: 12px 20px;
                border: none;
                border-top: none;
                border-left: none;
                border-right: none;
                border-bottom: 2px solid transparent;
                margin: 0px;
                margin-right: 2px;
                font-size: 13px;
                font-weight: 500;
                min-width: 70px;
                max-width: 120px;
            }}
            QTabBar::tab:selected {{
                color: {AppColors.TEXT_LIGHT};
                border-bottom: 2px solid {AppColors.ACCENT_BLUE};
                background-color: {AppColors.BG_SIDEBAR};
                font-weight: 600;
                border-top: none;
                border-left: none;
                border-right: none;
            }}
            QTabBar::tab:hover:!selected {{
                color: {AppColors.TEXT_LIGHT};
                background-color: {AppColors.HOVER_BG_DARKER};
                border-bottom: 2px solid transparent;
                border-top: none;
                border-left: none;
                border-right: none;
            }}
            QTabBar::scroller {{
                width: 0px;
                height: 0px;
            }}
        """)

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

        # Update title
        title_text = f"{resource_type}: {resource_name}"
        if namespace:
            title_text += f" (ns: {namespace})"
        self.title_label.setText(title_text)

        # Handle action button for Helm resources
        self.setup_action_button(resource_type)

        # Clear and setup sections
        self.clear_all_sections()
        self.set_resource_for_all_sections(resource_type, resource_name, namespace)
        self.tab_widget.setCurrentIndex(0)

        # Show with animation
        if not self.isVisible():
            self.show_with_animation()

        # Load data after animation completes
        QTimer.singleShot(300, self.load_current_tab_data)

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
            self.action_button.setText("Install Chart")
            self.action_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {AppColors.ACCENT_GREEN};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 20px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #45a049;
                }}
                QPushButton:pressed {{
                    background-color: #3d8b40;
                }}
            """)
            self.action_button.show()
        elif resource_type == "helmrelease":
            self.action_button.setText("Upgrade Release")
            self.action_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {AppColors.ACCENT_BLUE};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 20px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #0078e7;
                }}
                QPushButton:pressed {{
                    background-color: #0063b1;
                }}
            """)
            self.action_button.show()
        else:
            self.action_button.hide()

    def handle_action_button(self):
        # """Handle action button click"""
        # if self.resource_type == "chart":
        #     self._install_chart()
        # elif self.resource_type == "helmrelease":
        #     self._upgrade_chart()
        pass
    # def _install_chart(self):
    #     """Handle chart installation (Helm operations kept as subprocess)"""
    #     # Get chart info
    #     chart_name = self.resource_name
    #     repository = None

    #     # Create and show the installation dialog
    #     dialog = ChartInstallDialog(chart_name, repository, self)
    #     if dialog.exec() == QDialog.DialogCode.Accepted:
    #         # Get installation options
    #         options = dialog.get_values()

    #         # Install the chart
    #         success, message = install_helm_chart(chart_name, repository, options, self)

    #         # Show result message
    #         if success:
    #             QMessageBox.information(self, "Installation Successful", message)

    #             # Emit signal to refresh the Releases page
    #             self.resource_updated_signal.emit(
    #                 "helmrelease",
    #                 options["release_name"],
    #                 options["namespace"]
    #             )
    #         else:
    #             QMessageBox.critical(self, "Installation Failed", message)

    # def _upgrade_chart(self):
    #     """Handle chart upgrade (Helm operations kept as subprocess)"""
    #     # Find the Releases page instance first
    #     releases_page = None
    #     for widget in QApplication.allWidgets():
    #         if isinstance(widget, QWidget) and hasattr(widget, 'upgrade_release') and hasattr(widget, 'resource_type'):
    #             if getattr(widget, 'resource_type', None) == "helmreleases":
    #                 releases_page = widget
    #                 break

    #     if not releases_page:
    #         QMessageBox.information(
    #             self,
    #             "Upgrade",
    #             "Could not find releases manager. Chart upgrade functionality is currently unavailable."
    #         )
    #         return

    #     # Now call the upgrade_release method from the ReleasesPage
    #     releases_page.upgrade_release(self.resource_name, self.resource_namespace)

    #     # After upgrading, reload the details
    #     QTimer.singleShot(500, self.load_current_tab_data)

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

            # Check if this section already has data to avoid reloading
            if hasattr(current_section, 'current_data') and current_section.current_data:
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
        """Update global loading indicator based on section states"""
        any_loading = any(self.section_loading_states.values())

    # Resize handle methods
    def resize_handle_mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.resize_start_x = int(event.globalPosition().x())
            self.resize_start_width = self.width()

    def resize_handle_mouseMoveEvent(self, event):
        if hasattr(event, 'buttons') and event.buttons() == Qt.MouseButton.LeftButton:
            delta = self.resize_start_x - event.globalPosition().x()
            new_width = int(self.resize_start_width + delta)

            if new_width >= AppStyles.DETAIL_PAGE_MIN_WIDTH and new_width <= AppStyles.DETAIL_PAGE_MAX_WIDTH:
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
        """Close detail page"""
        # Clean up timers
        if hasattr(self, '_tab_change_timer'):
            self._tab_change_timer.stop()

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