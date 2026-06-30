"""
CustomComboBox — A fully-styled, theme-aware dropdown replacement for QComboBox.

Unlike QComboBox, this widget renders its own popup using Qt.WindowType.Popup
so we get pixel-perfect styling without any Windows native popup borders.

Usage:
    combo = CustomComboBox(parent)
    combo.addItems(["Dark", "Light"])
    combo.currentTextChanged.connect(my_slot)
    combo.setCurrentText("Dark")
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QScrollArea, QLabel, QSizePolicy, QLineEdit, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QEvent, QTimer, QVariantAnimation, QSize
from PyQt6.QtGui import QColor, QPainter, QIcon, QPixmap
import time
import os
import logging

from UI.Icons import resource_path

class _DropdownItem(QFrame):
    """A single item in the popup list."""
    
    hover_changed = pyqtSignal()
    clicked = pyqtSignal(bool)
    unpin_clicked = pyqtSignal()

    def __init__(self, text: str, is_selected: bool, accent: str,
                 bg: str, text_color: str, hover_bg: str, parent=None, show_unpin=False):
        super().__init__(parent)
        self._text = text
        self._accent = accent
        self._bg = bg
        self._text_color = text_color
        self._hover_bg = hover_bg
        self._is_selected = is_selected
        self._any_hovered = False
        self._is_active = False  # keyboard-navigation highlight
        self._show_unpin = show_unpin
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.installEventFilter(self)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(8)
        
        self.text_label = QLabel(text)
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.text_label)
        layout.addStretch()
        
        if self._show_unpin:
            self.unpin_btn = QToolButton()
            self.unpin_btn.setIcon(QIcon(resource_path("Icons/unpin.svg")))
            self.unpin_btn.setFixedSize(16, 16)
            self.unpin_btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    border: none;
                }
                QToolButton:hover {
                    background: rgba(128, 128, 128, 0.2);
                    border-radius: 4px;
                }
            """)
            self.unpin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.unpin_btn.clicked.connect(self.unpin_clicked.emit)
            layout.addWidget(self.unpin_btn)

        self._update_style()
        
    def text(self):
        return self._text
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # check if click is on unpin button
            if hasattr(self, 'unpin_btn') and self.childAt(event.position().toPoint()) == self.unpin_btn:
                return # handled by unpin_btn
            self.clicked.emit(False)
        super().mouseReleaseEvent(event)

    def set_any_hovered(self, any_hov: bool):
        if self._any_hovered != any_hov:
            self._any_hovered = any_hov
            self._update_style()

    def set_active(self, active: bool):
        """Toggle the keyboard-navigation highlight (rendered like hover)."""
        if self._is_active != active:
            self._is_active = active
            self._update_style()

    def _update_style(self):
        hovered = self.underMouse() or self._is_active
        
        if self._is_selected:
            color = self._accent
            weight = "600"
            if hovered or not self._any_hovered:
                bg = self._hover_bg
            else:
                bg = "transparent"
        else:
            color = self._text_color
            weight = "400"
            if hovered:
                bg = self._hover_bg
            else:
                bg = "transparent"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: none;
                border-radius: 6px;
            }}
            QLabel {{
                color: {color};
                font-size: 13px;
                font-weight: {weight};
                background: transparent;
            }}
        """)

    def eventFilter(self, obj, event):
        if obj is self:
            if event.type() in (QEvent.Type.Enter, QEvent.Type.Leave):
                self._update_style()
                self.hover_changed.emit()
        return super().eventFilter(obj, event)


class _DropdownPopup(QWidget):
    """Frameless popup overlay that appears below the combo button."""

    item_selected = pyqtSignal(str)
    unpin_requested = pyqtSignal(str)
    hidden = pyqtSignal()  # Custom signal emitted when popup hides

    def __init__(self, items, current_text, colors, is_searchable=False, show_unpin=False, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")
        self.setObjectName("DropdownPopup")

        self._colors = colors
        self._is_searchable = is_searchable
        self._show_unpin = show_unpin
        self._active_index = -1  # currently keyboard-highlighted item
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._setup_ui(items, current_text)

    def hideEvent(self, event):
        self.hidden.emit()
        super().hideEvent(event)

    def _setup_ui(self, items, current_text):
        accent = self._colors['accent']
        bg = self._colors['bg']
        text_color = self._colors['text']
        border = self._colors['border']
        hover_bg = f"rgba(255, 107, 53, 0.15)"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Inner card — this is what gets the border/radius
        card = QFrame()
        card.setObjectName("PopupCard")
        card.setStyleSheet(f"""
            QFrame#PopupCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(6, 6, 6, 6)
        card_layout.setSpacing(0)

        # Search bar if enabled
        if self._is_searchable:
            search_wrapper = QWidget()
            search_layout = QVBoxLayout(search_wrapper)
            search_layout.setContentsMargins(6, 4, 6, 8)
            search_layout.setSpacing(0)

            self._search_input = QLineEdit()
            self._search_input.setPlaceholderText("Search...")
            self._search_input.setFixedHeight(30)
            self._search_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {self._colors.get('bg_button', '#1e1e1e')};
                    color: {text_color};
                    border: 1px solid {border};
                    border-radius: 6px;
                    padding: 0 10px;
                    font-size: 13px;
                }}
                QLineEdit:focus {{
                    border: 1px solid {accent};
                }}
            """)
            self._search_input.textChanged.connect(self._on_search_text_changed)
            # Let arrow/enter/escape navigate the list while typing in search.
            self._search_input.installEventFilter(self)
            search_layout.addWidget(self._search_input)
            card_layout.addWidget(search_wrapper)
            # Focus search after a small delay once shown
            QTimer.singleShot(10, self._search_input.setFocus)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent; border: none;")
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 10px;
                margin: 4px 4px 4px 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #777777;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                border: none;
                background: none;
            }
        """)

        content_widget = QWidget()
        content_widget.setObjectName("scrollContent")
        content_widget.setStyleSheet("#scrollContent { background: transparent; border: none; }")
        
        content_layout = QVBoxLayout(content_widget)
        # Add slight margins to keep the hover highlights from touching the rounded popup border
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(2)

        self._items_widgets = []
        for item_text in items:
            is_selected = (item_text == current_text)
            btn = _DropdownItem(
                item_text, is_selected, accent, bg, text_color, hover_bg, self, self._show_unpin
            )
            btn.clicked.connect(lambda checked, t=item_text: self._on_item_clicked(t))
            btn.unpin_clicked.connect(lambda t=item_text: self.unpin_requested.emit(t))
            btn.hover_changed.connect(self._on_item_hover_changed)
            content_layout.addWidget(btn)
            self._items_widgets.append(btn)
            
        scroll.setWidget(content_widget)
        # 36px per item approximately. Max 6 items visible.
        max_height = min(len(items) * 36 + 12, 228) 
        scroll.setMinimumHeight(min(len(items) * 36 + 12, max_height))
        scroll.setMaximumHeight(max_height)

        card_layout.addWidget(scroll)
        outer.addWidget(card)

    def update_items(self, items, current_text):
        scroll_area = self.findChild(QScrollArea)
        if not scroll_area: return
        content_widget = scroll_area.widget()
        if not content_widget: return
        content_layout = content_widget.layout()
        
        # remove old
        for btn in self._items_widgets:
            content_layout.removeWidget(btn)
            btn.setParent(None)
            btn.deleteLater()
            
        self._items_widgets.clear()
        self._active_index = -1
        
        accent = self._colors['accent']
        bg = self._colors['bg']
        text_color = self._colors['text']
        hover_bg = f"rgba(255, 107, 53, 0.15)"
        
        for item_text in items:
            is_selected = (item_text == current_text)
            btn = _DropdownItem(
                item_text, is_selected, accent, bg, text_color, hover_bg, self, self._show_unpin
            )
            btn.clicked.connect(lambda checked, t=item_text: self._on_item_clicked(t))
            btn.unpin_clicked.connect(lambda t=item_text: self.unpin_requested.emit(t))
            btn.hover_changed.connect(self._on_item_hover_changed)
            content_layout.addWidget(btn)
            self._items_widgets.append(btn)
            
        if hasattr(self, '_search_input'):
            self._on_search_text_changed(self._search_input.text())
        else:
            self._on_search_text_changed("")

    def _on_search_text_changed(self, text):
        search_text = text.lower()
        visible_count = 0
        for btn in self._items_widgets:
            is_visible = search_text in btn.text().lower()
            btn.setVisible(is_visible)
            if is_visible:
                visible_count += 1
        
        scroll_area = self.findChild(QScrollArea)
        if scroll_area:
            content_widget = scroll_area.widget()
            if content_widget:
                # Force immediate layout update to get correct sizeHint
                content_widget.layout().update()
                target_height = content_widget.sizeHint().height()
            else:
                target_height = visible_count * 36 + 12
                
            max_scroll = getattr(self, '_max_scroll_avail', 228)
            target_scroll_height = min(max(target_height, 12), max_scroll)
            scroll_area.setFixedHeight(target_scroll_height)
            
            search_overhead = 42 if getattr(self, '_is_searchable', False) else 0
            card_overhead = 12
            new_popup_height = target_scroll_height + search_overhead + card_overhead
            self.setFixedHeight(new_popup_height)
            
            if getattr(self, '_opens_upwards', False):
                base_pos = getattr(self, '_base_pos', None)
                if base_pos:
                    self.move(base_pos.x(), base_pos.y() - new_popup_height)

    def _on_item_hover_changed(self):
        any_hovered = any(btn.underMouse() for btn in self._items_widgets)
        for btn in self._items_widgets:
            btn.set_any_hovered(any_hovered)

    def _on_item_clicked(self, text):
        self.item_selected.emit(text)
        self.close()

    # ── Keyboard navigation ────────────────────────────────────────────────

    def _visible_item_widgets(self):
        return [b for b in self._items_widgets if b.isVisible()]

    def _set_active_widget(self, widget):
        for b in self._items_widgets:
            b.set_active(b is widget)
        self._active_index = self._items_widgets.index(widget)
        scroll_area = self.findChild(QScrollArea)
        if scroll_area:
            scroll_area.ensureWidgetVisible(widget)

    def _move_active(self, delta):
        visible = self._visible_item_widgets()
        if not visible:
            return
        current = None
        if 0 <= self._active_index < len(self._items_widgets):
            candidate = self._items_widgets[self._active_index]
            if candidate in visible:
                current = candidate
        if current is None:
            new_index = 0 if delta > 0 else len(visible) - 1
        else:
            new_index = (visible.index(current) + delta) % len(visible)
        self._set_active_widget(visible[new_index])

    def _activate_current(self):
        if 0 <= self._active_index < len(self._items_widgets):
            widget = self._items_widgets[self._active_index]
            if widget.isVisible():
                self._on_item_clicked(widget.text())
                return True
        return False

    def _handle_nav_key(self, key):
        if key == Qt.Key.Key_Down:
            self._move_active(1)
            return True
        if key == Qt.Key.Key_Up:
            self._move_active(-1)
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return self._activate_current()
        if key == Qt.Key.Key_Escape:
            self.close()
            return True
        return False

    def keyPressEvent(self, event):
        if self._handle_nav_key(event.key()):
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        # Forward navigation keys from the search box into the list.
        if (getattr(self, '_search_input', None) is obj
                and event.type() == QEvent.Type.KeyPress):
            if self._handle_nav_key(event.key()):
                return True
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        super().showEvent(event)
        # Take focus so the popup receives key events. When searchable, the
        # search box grabs focus instead (see the singleShot in _setup_ui).
        if not self._is_searchable:
            self.setFocus()


class CustomComboBox(QWidget):
    """
    Fully custom dropdown widget. Replaces QComboBox with pixel-perfect popup.
    API compatible with QComboBox for common usage:
      - addItems(list)
      - setCurrentText(text)
      - currentText() → str
      - currentTextChanged signal
    """

    currentTextChanged = pyqtSignal(str)
    currentIndexChanged = pyqtSignal(int)   # ← required by some callers
    unpin_clicked = pyqtSignal(str)

    def __init__(self, parent=None, is_searchable=False, show_unpin=False, force_dark=False):
        super().__init__(parent)
        self._items: list[str] = []
        self._current_text: str = ""
        self._is_searchable = is_searchable
        self._show_unpin = show_unpin
        self._force_dark = force_dark
        self._placeholder = "Select..."
        self._popup: _DropdownPopup | None = None
        # seed with defaults; overwritten on first _apply_theme call
        self._colors_cache = {
            'accent': '#FF6B35', 'bg': '#f5f5f5', 'text': '#222222',
            'border': '#dddddd', 'bg_button': '#ffffff',
        }
        self._setup_ui()
        self._apply_theme()

        # Watch for theme changes if not forced to dark
        if not self._force_dark:
            try:
                from UI.ThemeManager import get_theme_manager
                get_theme_manager().theme_changed.connect(self._on_theme_changed)
            except (ImportError, AttributeError):
                # Theme manager unavailable — safe to ignore; widget keeps cached colors.
                pass
            except Exception:
                logging.exception("CustomComboBox: failed to connect to theme_changed signal")


    def _setup_ui(self):
        # Outer clickable container
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._button = QWidget(self)
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Reachable by Tab and openable from the keyboard, like a real combo.
        self._button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._button.mousePressEvent = lambda e: self._toggle_popup()
        self._button.installEventFilter(self)

        row = QHBoxLayout(self._button)
        row.setContentsMargins(16, 0, 14, 0)
        row.setSpacing(10)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(20, 20)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setStyleSheet("background: transparent; border: none;")
        self._icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._icon_lbl.hide()
        row.addWidget(self._icon_lbl)

        self._text_lbl = QLabel("Select...")
        self._text_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._text_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._arrow_lbl = QLabel()   # Will hold the SVG pixmap
        self._arrow_lbl.setFixedWidth(20)
        self._arrow_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        self._arrow_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        row.addWidget(self._text_lbl)
        row.addStretch()
        row.addWidget(self._arrow_lbl)

        outer.addWidget(self._button)

    def _get_colors(self):
        if self._force_dark:
            try:
                from UI.Styles import AppColors
                return {
                    'accent': getattr(AppColors, 'ACCENT_ORANGE', '#FF6B35'),
                    'bg': AppColors.BG_MEDIUM,
                    'text': AppColors.TEXT_LIGHT,
                    'border': AppColors.BORDER_COLOR,
                    'bg_button': AppColors.BG_DARK,
                }
            except Exception:
                return {
                    'accent': '#FF6B35',
                    'bg': '#2a2a2a',
                    'text': '#ffffff',
                    'border': '#3a3a3a',
                    'bg_button': '#1e1e1e',
                }

        try:
            from UI.ThemeManager import get_theme_manager
            theme = get_theme_manager().get_current_theme()
            return {
                'accent': getattr(theme.colors, 'ACCENT_ORANGE', '#FF6B35'),
                'bg': theme.colors.BG_MEDIUM,
                'text': theme.colors.TEXT_LIGHT,
                'border': theme.colors.BORDER_COLOR,
                'bg_button': theme.colors.BG_DARK,
            }
        except Exception:
            return {
                'accent': '#FF6B35',
                'bg': '#2a2a2a',
                'text': '#ffffff',
                'border': '#3a3a3a',
                'bg_button': '#1e1e1e',
            }

    def _apply_theme(self):
        colors = self._get_colors()
        self._colors_cache = colors
        self._set_button_normal()
        self._update_button_text()

    def _set_button_normal(self):
        c = self._colors_cache
        self._button.setStyleSheet(f"""
            QWidget {{
                background-color: {c['bg_button']};
                border: 1px solid {c['border']};
                border-radius: 6px;
            }}
        """)
        self._text_lbl.setStyleSheet(
            f"color: {c['text']}; font-size: 14px; background: transparent; border: none;"
        )
        self._arrow_lbl.setStyleSheet("background: transparent; border: none;")
        self._update_arrow_pixmap(0)

    def _set_button_hover(self):
        c = self._colors_cache
        self._button.setStyleSheet(f"""
            QWidget {{
                background-color: {c['bg_button']};
                border: 1px solid {c['accent']};
                border-radius: 6px;
            }}
        """)

    def eventFilter(self, obj, event):
        if obj is self._button:
            if event.type() == QEvent.Type.Enter:
                self._set_button_hover()
            elif event.type() == QEvent.Type.Leave:
                # Keep the accent border while focused, so the focus ring stays.
                if not self._button.hasFocus():
                    self._set_button_normal()
            elif event.type() == QEvent.Type.FocusIn:
                self._set_button_hover()
            elif event.type() == QEvent.Type.FocusOut:
                self._set_button_normal()
            elif event.type() == QEvent.Type.KeyPress:
                if event.key() in (
                    Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter,
                    Qt.Key.Key_Down, Qt.Key.Key_Up,
                ):
                    self._toggle_popup()
                    return True
        return super().eventFilter(obj, event)

    def _update_button_text(self):
        label = self._current_text if self._current_text else self._placeholder
        self._text_lbl.setText(label)
        
    def _animate_arrow(self, is_open: bool):
        target_angle = 180 if is_open else 0
        
        if not hasattr(self, '_arrow_anim'):
            self._arrow_anim = QVariantAnimation(self)
            self._arrow_anim.setDuration(200)
            self._arrow_anim.valueChanged.connect(self._on_arrow_animate)
            self._current_angle = 0.0
            
        if self._arrow_anim.state() == QVariantAnimation.State.Running:
            self._arrow_anim.stop()
            
        self._arrow_anim.setStartValue(self._current_angle)
        self._arrow_anim.setEndValue(float(target_angle))
        self._arrow_anim.start()
        
    def _on_arrow_animate(self, angle):
        self._current_angle = float(angle)
        self._update_arrow_pixmap(self._current_angle)
        
    def _update_arrow_pixmap(self, angle=0):
        
        # High DPI rendering: Render at 2x size for sharp borders
        render_scale = 2
        logical_size = 20
        real_size = logical_size * render_scale
        
        icon_path = resource_path('Icons/down_arrow.svg')
        if not os.path.exists(icon_path):
            icon_path = 'Icons/down_arrow.svg'
            
        icon = QIcon(icon_path)
        base_pixmap = icon.pixmap(QSize(real_size, real_size))
        
        # Create an empty transparent pixmap to draw into
        pixmap = QPixmap(real_size, real_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        
        # Rotate the painter directly around the center point
        if angle != 0:
            painter.translate(real_size / 2.0, real_size / 2.0)
            painter.rotate(angle)
            painter.translate(-real_size / 2.0, -real_size / 2.0)
            
        # Paint icon
        painter.drawPixmap(0, 0, base_pixmap)
        
        # Colorize to match theme
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(self._colors_cache.get('text', '#000000')))
        painter.end()
            
        # Scale back down to logical size for crisp display
        final_pixmap = pixmap.scaled(
            logical_size, logical_size, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        final_pixmap.setDevicePixelRatio(1.0) 
            
        self._arrow_lbl.setPixmap(final_pixmap)

    def _on_theme_changed(self, *_):
        self._apply_theme()

    def _toggle_popup(self):
        # Prevent reopening if the popup just closed due to losing focus
        # from this exact mouse click.
        if hasattr(self, '_last_close_time') and time.time() - self._last_close_time < 0.15:
            return
            
        if self._popup and self._popup.isVisible():
            self._popup.close()
            # Animation is handled by the popup's hidden signal now
            return
        self._open_popup()

    def _on_popup_hidden(self):
        self._last_close_time = time.time()
        self._animate_arrow(False)
        # Fully dispose of the closed popup instead of leaving it hidden.
        if self._popup is not None:
            self._popup.deleteLater()
            self._popup = None

    def _open_popup(self):
        # Dispose of any prior popup so hidden instances don't pile up as
        # children of this widget.
        if self._popup is not None:
            self._popup.deleteLater()
            self._popup = None
        colors = self._get_colors()
        self._popup = _DropdownPopup(self._items, self._current_text, colors, is_searchable=self._is_searchable, show_unpin=self._show_unpin, parent=self)
        self._popup.item_selected.connect(self._on_item_selected)
        self._popup.unpin_requested.connect(self._on_unpin_requested)
        self._popup.hidden.connect(self._on_popup_hidden)

        # Base calculations
        desired_width = max(self._button.width(), 160)
        self._popup.setFixedWidth(desired_width)

        # Get screen geometry to prevent cutoff
        screen_geo = self.window().screen().availableGeometry()
        
        # Calculate global positions for top and bottom of the button
        global_bottom_pos = self._button.mapToGlobal(QPoint(0, self._button.height() + 2))
        global_top_pos = self._button.mapToGlobal(QPoint(0, -2))
        
        # Calculate available space
        space_below = screen_geo.bottom() - global_bottom_pos.y()
        space_above = global_top_pos.y() - screen_geo.top()
        
        # Default popup layout height preference in CustomComboBox
        # Card margins: 12px (6 top + 6 bottom)
        # Scroll content margins: 8px (4 top + 4 bottom)
        # Search wrapper height: 42px (30 input + 12 margins)
        card_overhead = 12
        scroll_overhead = 8
        search_overhead = 42 if self._is_searchable else 0
        
        max_scroll_allowed = 228
        scroll_area = self._popup.findChild(QScrollArea)
        
        if scroll_area and scroll_area.widget():
            # Force immediate layout update to get correct sizeHint
            scroll_area.widget().layout().update()
            items_height = scroll_area.widget().sizeHint().height()
        else:
            items_height = len(self._items) * 36 + scroll_overhead
            
        actual_scroll_pref = min(items_height, max_scroll_allowed)
        pref_height = actual_scroll_pref + search_overhead + card_overhead
        
        # Layout decisions
        opens_upwards = space_below < pref_height and space_above >= space_below
            
        if not opens_upwards:
            # Open downwards (default)
            height_avail = space_below - 10
            base_pos = global_bottom_pos
        else:
            # Open upwards
            height_avail = space_above - 10
            base_pos = global_top_pos
            
        final_height = min(pref_height, max(100, height_avail))
        
        self._popup._base_pos = base_pos
        self._popup._opens_upwards = opens_upwards
        
        if scroll_area:
            scroll_avail = min(final_height - search_overhead - card_overhead, max_scroll_allowed)
            self._popup._max_scroll_avail = scroll_avail
            
            target_scroll_height = min(items_height, scroll_avail)
            scroll_area.setFixedHeight(target_scroll_height)
            
            actual_popup_height = target_scroll_height + search_overhead + card_overhead
            self._popup.setFixedHeight(actual_popup_height)
            
            if opens_upwards:
                self._popup.move(base_pos.x(), base_pos.y() - actual_popup_height)
            else:
                self._popup.move(base_pos)
        else:
            self._popup.setFixedHeight(final_height)
            if opens_upwards:
                self._popup.move(base_pos.x(), base_pos.y() - final_height)
            else:
                self._popup.move(base_pos)
        
        self._popup.show()
        self._animate_arrow(True)

    def _on_item_selected(self, text: str):
        if text != self._current_text:
            old_idx = self.currentIndex()
            self._current_text = text
            self._update_button_text()
            self.currentTextChanged.emit(text)
            new_idx = self.currentIndex()
            if new_idx != old_idx:
                self.currentIndexChanged.emit(new_idx)
                
    def _on_unpin_requested(self, text: str):
        self.unpin_clicked.emit(text)

    # ── Public QComboBox-compatible API ────────────────────────────────────

    def setItems(self, items: list):
        self._items = list(items)
        if self._popup and self._popup.isVisible():
            self._popup.update_items(self._items, self._current_text)

    def addItems(self, items: list):
        self._items.extend(items)
        self._update_button_text()

    def addItem(self, item: str):
        self._items.append(item)
        self._update_button_text()

    def setCurrentText(self, text: str):
        if text in self._items:
            self._current_text = text
        else:
            # Allow setting to empty string to show placeholder
            self._current_text = text if text else ""
        self._update_button_text()

    def setPlaceholderText(self, text: str):
        self._placeholder = text
        self._update_button_text()

    def setSearchEnabled(self, enabled: bool):
        self._is_searchable = enabled

    def setIcon(self, icon):
        if not icon or icon.isNull():
            self._icon_lbl.setPixmap(QPixmap())
            self._icon_lbl.hide()
            return

        if isinstance(icon, QIcon):
            pixmap = icon.pixmap(18, 18)
        elif isinstance(icon, QPixmap):
            pixmap = icon.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        else:
            # Fallback for unexpected types
            self._icon_lbl.hide()
            return

        self._icon_lbl.setPixmap(pixmap)
        self._icon_lbl.show()

    def currentText(self) -> str:
        return self._current_text

    def currentIndex(self) -> int:
        try:
            return self._items.index(self._current_text)
        except ValueError:
            return -1

    def setCurrentIndex(self, index: int):
        if 0 <= index < len(self._items):
            self.setCurrentText(self._items[index])

    def findText(self, text: str) -> int:
        try:
            return self._items.index(text)
        except ValueError:
            return -1

    def count(self) -> int:
        return len(self._items)

    def itemText(self, index: int) -> str:
        if 0 <= index < len(self._items):
            return self._items[index]
        return ""

    def blockSignals(self, block: bool) -> bool:
        return super().blockSignals(block)

    def setCursor(self, cursor):
        self._button.setCursor(cursor)

    # Stubs for rarely-used QComboBox methods so callers don't crash
    # Allowed standard setStyleSheet to work again
    # Removed the previous no-op override

    def clear(self):
        self._items.clear()
        self._current_text = ""
        self._update_button_text()

    def setEditable(self, editable: bool):
        pass

    def setInsertPolicy(self, policy):
        pass

    def setSizeAdjustPolicy(self, policy):
        pass

    def setMinimumContentsLength(self, length: int):
        pass

    def setView(self, view):
        pass

    def setMaxVisibleItems(self, maxItems: int):
        pass
