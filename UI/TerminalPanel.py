import os
import sys
import platform
import re
import shutil
from datetime import datetime
from kubernetes import watch
from kubernetes.client.rest import ApiException
import logging
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QToolButton, QSizePolicy,QLineEdit,
    QFileDialog, QMenu, QLabel, QPushButton, QComboBox, QCheckBox
)
from PyQt6.QtGui import QAction, QColor, QTextCursor, QFont, QIcon, QTextCharFormat,QTextDocument, QKeySequence
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QPoint, QThread, QTimer, pyqtSignal, QProcess
from datetime import datetime
from enum import Enum

from Styles import AppColors


class StyleConstants:
    """Centralized stylesheet constants"""
    TERMINAL_TEXTEDIT = f"""
        QTextEdit {{
            background-color: #1E1E1E;
            color: #E0E0E0;
            border: none;
            selection-background-color: #264F78;
            selection-color: #E0E0E0;
            padding: 8px;
        }}
        QScrollBar:vertical {{
            border: none;
            background: #2D2D2D;
            width: 10px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: #555555;
            min-height: 20px;
            border-radius: 5px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    """
    TERMINAL_WRAPPER = f"""
        QWidget#terminal_wrapper {{
            background-color: {AppColors.BG_DARKER};
            border: 1px solid {AppColors.BORDER_COLOR};
            border-bottom: none;
        }}
    """
    HEADER_CONTENT = f"""
        background-color: {AppColors.BG_DARKER};
        border-bottom: 1px solid {AppColors.BORDER_COLOR};
    """
    TAB_LABEL = f"""
        color: {AppColors.TEXT_SECONDARY};
        background: transparent;
        font-size: 12px;
        text-decoration: none;
        border: none;
        outline: none;
    """
    TAB_CLOSE_BUTTON = f"""
        QPushButton {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
            border: none;
            font-size: 10px;
            font-weight: bold;
            padding: 0px;
            margin: 0px;
        }}
        QPushButton:hover {{
            background-color: #FF4D4D;
            color: white;
            border-radius: 8px;
        }}
    """
    TAB_BUTTON = f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            border-right: 1px solid {AppColors.BORDER_COLOR};
            border-left: 1px solid {AppColors.BORDER_COLOR};
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
            border-top: 1px solid {AppColors.BORDER_COLOR};
            padding: 0px 35px;
            margin: 0px;
        }}
        QPushButton:hover {{
            background-color: {AppColors.HOVER_BG};
        }}
        QPushButton:checked {{
            background-color: #1E1E1E;
            border-bottom: 2px solid {AppColors.ACCENT_BLUE};
        }}
    """
    HEADER_BUTTON = f"""
        QToolButton {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
            border: none;
            font-size: 12px;
            padding: 4px;
        }}
        QToolButton:hover {{
            background-color: {AppColors.HOVER_BG};
            color: #ffffff;
            border-radius: 4px;
        }}
    """
    RESIZE_HANDLE = """
        background-color: rgba(80, 80, 80, 0.3);
        border: none;
    """
    SHELL_DROPDOWN = f"""
        QComboBox {{
            background-color: {AppColors.BG_DARKER};
            color: {AppColors.TEXT_SECONDARY};
            border: 1px solid {AppColors.BORDER_COLOR};
            padding: 2px 4px;
            font-size: 12px;
        }}
        QComboBox:hover {{
            background-color: {AppColors.HOVER_BG};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: url(icons/dropdown_arrow.svg);
            width: 10px;
            height: 10px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {AppColors.BG_DARKER};
            color: {AppColors.TEXT_SECONDARY};
            selection-background-color: {AppColors.HOVER_BG};
            border: 1px solid {AppColors.BORDER_COLOR};
        }}
    """
    SEARCH_INPUT = f"""
        QLineEdit {{
            background-color: {AppColors.BG_DARKER};
            color: {AppColors.TEXT_SECONDARY};
            border: 1px solid {AppColors.BORDER_COLOR};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
            min-width: 200px;
        }}
        QLineEdit:focus {{
            border-color: {AppColors.ACCENT_BLUE};
            background-color: #242424;
        }}
        QLineEdit::placeholder {{
            color: #666666;
        }}
    """


class CommandConstants(Enum):
    CLEAR = "clear"
    EXIT = "exit"
    QUIT = "quit"

class UnifiedTerminalWidget(QTextEdit):
    """Unified terminal widget for input and output"""
    commandEntered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.command_history = []
        self.history_index = -1
        self.is_valid = True
        self.current_prompt = "PS > "
        self.input_position = 0
        self.current_input = ""
        self.edit_mode = False
        self.edit_file_path = None
        self.edit_start_pos = 0
        self.edit_end_pos = 0
        self.font_size = 9
        self.font_family = "Monospace"
        self.copy_paste_enabled = False
        self.search_highlights = []  # Store search highlight positions
        self.terminal_bg_color = QColor("#1E1E1E")  # Store terminal background color
        self.setup_ui()
        self.update_prompt_with_working_directory()
        self.append_prompt()
        print(f"UnifiedTerminalWidget initialized with copy_paste_enabled={self.copy_paste_enabled}")

    def setup_ui(self):
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont(self.font_family, self.font_size))
        self.setStyleSheet(StyleConstants.TERMINAL_TEXTEDIT)
        self.setAcceptRichText(False)

    def __del__(self):
        self.is_valid = False

    def set_copy_paste_enabled(self, enabled):
        self.copy_paste_enabled = enabled
        print(f"UnifiedTerminalWidget.set_copy_paste_enabled: copy_paste_enabled={enabled}")

    def set_font(self, font_family, font_size=None):
        print(f"UnifiedTerminalWidget.set_font: font_family={font_family}, font_size={font_size}")
        self.font_family = font_family
        if font_size is not None:
            self.font_size = max(6, min(int(font_size), 72))
            print(f"Updated font size to: {self.font_size}")

        new_font = QFont(self.font_family, self.font_size)
        self.setFont(new_font)

        current_text = self.toPlainText()
        cursor_pos = self.textCursor().position()
        scroll_pos = self.verticalScrollBar().value()

        self.clear()
        self.setFont(new_font)
        cursor = self.textCursor()
        char_format = QTextCharFormat()
        char_format.setFont(new_font)
        self.setCurrentCharFormat(char_format)
        self.insertPlainText(current_text)

        cursor.setPosition(cursor_pos)
        self.setTextCursor(cursor)
        self.verticalScrollBar().setValue(scroll_pos)

        self.document().setDefaultFont(new_font)
        self.repaint()
        self.update()
        print(f"Font updated: {self.font().family()}, size {self.font().pointSize()}")

    def update_prompt_with_working_directory(self):
        terminal_panel = self.parent()
        while terminal_panel and not isinstance(terminal_panel, TerminalPanel):
            terminal_panel = terminal_panel.parent()
        self.current_prompt = f"PS {terminal_panel.working_directory} > " if terminal_panel and hasattr(terminal_panel, 'working_directory') else "PS > "

    def append_output(self, text, color=None):
        if not self.is_valid:
            return
        try:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)

            # Create text format with proper background
            char_format = QTextCharFormat()
            char_format.setForeground(QColor(color or "#E0E0E0"))
            char_format.setBackground(self.terminal_bg_color)  # Ensure background is set

            # Apply format and insert text
            cursor.setCharFormat(char_format)
            cursor.insertText(text)

            if not self.edit_mode:
                self.input_position = cursor.position()
            else:
                self.update_edit_positions()
            self.ensure_cursor_at_input()
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        except RuntimeError:
            self.is_valid = False

    def append_prompt(self):
        self.update_prompt_with_working_directory()
        self.append_output(self.current_prompt)
        self.input_position = self.textCursor().position()

    def clear_output(self):
        if not self.is_valid:
            return
        try:
            self.clear()
            self.edit_mode = False
            self.edit_file_path = None
            self.edit_start_pos = self.edit_end_pos = 0
            self.search_highlights.clear()  # Clear search highlights

            # For SSH terminals, also clear pending input
            if hasattr(self, 'pending_input'):
                self.pending_input = ""
            if hasattr(self, 'last_output_position'):
                self.last_output_position = 0

            terminal_panel = self.parent()
            while terminal_panel and not isinstance(terminal_panel, TerminalPanel):
                terminal_panel = terminal_panel.parent()
            if terminal_panel and hasattr(terminal_panel, 'working_directory'):
                tab_index = next((i for i, tab_data in enumerate(terminal_panel.terminal_tabs) if tab_data.get('terminal_widget') == self), 0)
                welcome_msg = (
                    f"Kubernetes Terminal {tab_index + 1}\n"
                    f"Working directory: {terminal_panel.working_directory}\n"
                    "--------------------\n"
                    "Enter 'kubectl' commands to interact with your cluster.\n"
                    "Type 'clear' to clear the terminal.\n\n"
                )
                self.append_output(welcome_msg)
            self.append_prompt()
            self.ensure_cursor_at_input()
        except RuntimeError:
            self.is_valid = False

    def ensure_cursor_at_input(self):
        if not self.is_valid:
            return
        try:
            # Allow selection, so don't force cursor if there is a selection
            if self.textCursor().hasSelection():
                return
            cursor = self.textCursor()
            if self.edit_mode:
                 if cursor.position() < self.edit_start_pos or cursor.position() > self.edit_end_pos:
                    cursor.setPosition(self.edit_end_pos)
                    self.setTextCursor(cursor)
            else:
                if cursor.position() < self.input_position:
                    cursor.setPosition(self.document().characterCount() - 1)
                    self.setTextCursor(cursor)
        except RuntimeError:
            self.is_valid = False

    def contextMenuEvent(self, event):
        print(f"UnifiedTerminalWidget.contextMenuEvent: copy_paste_enabled={self.copy_paste_enabled}, edit_mode={self.edit_mode}")
        menu = self.createStandardContextMenu()

        menu.addSeparator()

        # Check if this is a logs tab
        is_logs_tab = self._is_logs_tab()

        if is_logs_tab:
            # Add logs-specific actions
            refresh_action = QAction("🔄 Refresh Logs", self)
            refresh_action.triggered.connect(self._refresh_logs)
            menu.addAction(refresh_action)

            # Search highlighting actions
            search_info = self._get_current_search_info()
            if search_info and search_info.get('search_text'):
                highlight_action = QAction(f"🔍 Highlighting: '{search_info['search_text']}'", self)
                highlight_action.setEnabled(False)  # Just for info
                menu.addAction(highlight_action)

                clear_search_action = QAction("❌ Clear Search", self)
                clear_search_action.triggered.connect(self._clear_search)
                menu.addAction(clear_search_action)

            menu.addSeparator()

            # Tail lines menu
            tail_menu = QMenu("📜 Show Lines", self)
            for lines in [50, 100, 200, 500, 1000]:
                action = QAction(f"Last {lines} lines", self)
                action.triggered.connect(lambda checked, l=lines: self._refresh_logs_with_lines(l))
                tail_menu.addAction(action)
            menu.addMenu(tail_menu)

            # Container selection if multiple containers
            containers = self._get_pod_containers()
            if len(containers) > 1:
                container_menu = QMenu("📦 Select Container", self)
                current_container = self._get_current_container()
                for container in containers:
                    action = QAction(container, self)
                    if container == current_container:
                        action.setCheckable(True)
                        action.setChecked(True)
                    action.triggered.connect(lambda checked, c=container: self._refresh_logs_for_container(c))
                    container_menu.addAction(action)
                menu.addMenu(container_menu)

            menu.addSeparator()

            # Follow mode toggle
            logs_info = self._get_current_logs_info()
            if logs_info:
                follow_enabled = self._is_follow_enabled()
                follow_action = QAction("📡 Follow Logs" if not follow_enabled else "⏸️ Stop Following", self)
                follow_action.triggered.connect(self._toggle_follow_mode)
                menu.addAction(follow_action)

        clear_action = QAction("🗑️ Clear", self)
        clear_action.triggered.connect(self.clear_output)
        menu.addAction(clear_action)

        menu.exec(event.globalPos())
        event.accept()
        print("UnifiedTerminalWidget: Enhanced context menu executed")

    def _get_current_search_info(self):
        """Get current search information from logs viewer"""
        try:
            logs_info = self._get_current_logs_info()
            if logs_info and hasattr(logs_info['logs_viewer'], 'search_text'):
                return {
                    'search_text': logs_info['logs_viewer'].search_text,
                    'matches': getattr(logs_info['logs_viewer'], 'search_matches', 0)
                }
        except Exception as e:
            logging.error(f"Error getting search info: {e}")
        return {}

    def _get_current_container(self):
        """Get currently selected container"""
        try:
            logs_info = self._get_current_logs_info()
            if logs_info and hasattr(logs_info['logs_viewer'], 'current_container'):
                return logs_info['logs_viewer'].current_container
        except Exception as e:
            logging.error(f"Error getting current container: {e}")
        return None

    def _is_follow_enabled(self):
        """Check if follow mode is enabled"""
        try:
            logs_info = self._get_current_logs_info()
            if logs_info and hasattr(logs_info['logs_viewer'], 'follow_enabled'):
                return logs_info['logs_viewer'].follow_enabled
        except Exception as e:
            logging.error(f"Error checking follow mode: {e}")
        return False

    def _toggle_follow_mode(self):
        """Toggle follow mode"""
        try:
            logs_info = self._get_current_logs_info()
            if logs_info and hasattr(logs_info['logs_viewer'], 'set_follow_mode'):
                current_follow = logs_info['logs_viewer'].follow_enabled
                logs_info['logs_viewer'].set_follow_mode(not current_follow)

                # Update the checkbox in header
                if hasattr(logs_info['logs_viewer'], 'header'):
                    logs_info['logs_viewer'].header.follow_checkbox.setChecked(not current_follow)

        except Exception as e:
            logging.error(f"Error toggling follow mode: {e}")

    def _clear_search(self):
        """Clear search in logs viewer"""
        try:
            # Clear search in terminal header
            terminal_panel = self.parent()
            while terminal_panel and not hasattr(terminal_panel, 'unified_header'):
                terminal_panel = terminal_panel.parent()

            if terminal_panel and hasattr(terminal_panel.unified_header, 'search_input'):
                terminal_panel.unified_header.search_input.clear()
                terminal_panel.unified_header._on_search_changed("")
        except Exception as e:
            logging.error(f"Error clearing search: {e}")

    def _refresh_logs_for_container(self, container_name):
        """Refresh logs for specific container"""
        logs_info = self._get_current_logs_info()
        if logs_info and hasattr(logs_info['logs_viewer'], 'set_container'):
            # Update the combo box
            if hasattr(logs_info['logs_viewer'], 'header'):
                logs_info['logs_viewer'].header.container_combo.setCurrentText(container_name)
            logs_info['logs_viewer'].set_container(container_name)

    def _refresh_logs_with_lines(self, tail_lines):
        """Refresh logs with specific number of lines"""
        logs_info = self._get_current_logs_info()
        if logs_info and hasattr(logs_info['logs_viewer'], 'set_tail_lines'):
            # Update the combo box
            if hasattr(logs_info['logs_viewer'], 'header'):
                logs_info['logs_viewer'].header.lines_combo.setCurrentText(str(tail_lines))
            logs_info['logs_viewer'].set_tail_lines(tail_lines)

    def _refresh_logs(self):
        """Refresh logs for current pod"""
        logs_info = self._get_current_logs_info()
        if logs_info and hasattr(logs_info['logs_viewer'], 'refresh_logs'):
            logs_info['logs_viewer'].refresh_logs()

    def _get_current_logs_info(self):
        """Get current logs tab information"""
        try:
            terminal_panel = self.parent()
            while terminal_panel and not hasattr(terminal_panel, 'terminal_tabs'):
                terminal_panel = terminal_panel.parent()

            if terminal_panel and hasattr(terminal_panel, 'active_terminal_index'):
                active_index = terminal_panel.active_terminal_index
                if active_index < len(terminal_panel.terminal_tabs):
                    tab_data = terminal_panel.terminal_tabs[active_index]
                    if tab_data.get('is_logs_tab', False):
                        return {
                            'pod_name': tab_data.get('pod_name'),
                            'namespace': tab_data.get('namespace'),
                            'terminal_panel': terminal_panel,
                            'tab_index': active_index,
                            'logs_viewer': tab_data.get('logs_viewer')
                        }
        except Exception as e:
            logging.error(f"Error getting logs info: {e}")
        return None

    def _is_logs_tab(self):
        """Check if this terminal widget is in a logs tab"""
        try:
            terminal_panel = self.parent()
            while terminal_panel and not hasattr(terminal_panel, 'terminal_tabs'):
                terminal_panel = terminal_panel.parent()

            if terminal_panel and hasattr(terminal_panel, 'active_terminal_index'):
                active_index = terminal_panel.active_terminal_index
                if active_index < len(terminal_panel.terminal_tabs):
                    tab_data = terminal_panel.terminal_tabs[active_index]
                    return tab_data.get('is_logs_tab', False)
        except Exception as e:
            logging.error(f"Error checking if logs tab: {e}")
        return False

    def _get_pod_containers(self):
        """Get list of containers for the current pod"""
        try:
            logs_info = self._get_current_logs_info()
            if not logs_info:
                return []

            # Get containers from the logs viewer header
            if (hasattr(logs_info['logs_viewer'], 'header') and
                hasattr(logs_info['logs_viewer'].header, 'containers')):
                return logs_info['logs_viewer'].header.containers

            # Fallback: Get containers directly from Kubernetes API
            from utils.kubernetes_client import get_kubernetes_client
            kube_client = get_kubernetes_client()

            if kube_client and kube_client.v1:
                try:
                    pod = kube_client.v1.read_namespaced_pod(
                        name=logs_info['pod_name'],
                        namespace=logs_info['namespace']
                    )
                    if pod.spec and pod.spec.containers:
                        return [c.name for c in pod.spec.containers]
                except Exception as e:
                    logging.error(f"Error getting pod containers: {e}")

            return []
        except Exception as e:
            logging.error(f"Error in _get_pod_containers: {e}")
            return []

    def mousePressEvent(self, event):
        print(f"UnifiedTerminalWidget.mousePressEvent: copy_paste_enabled={self.copy_paste_enabled}, button={event.button()}, edit_mode={self.edit_mode}")
        self.setFocus()
        if event.button() == Qt.MouseButton.RightButton:
            # The context menu will handle pasting.
            # We can optionally implement right-click-to-paste here if desired.
            if self.copy_paste_enabled and not self.edit_mode:
                self.paste()
            event.accept()
            return

        # For left-click, ensure the cursor moves to the input area
        # only if not selecting text.
        cursor = self.textCursor()
        if not cursor.hasSelection():
             self.ensure_cursor_at_input()

        super().mousePressEvent(event)
        print("UnifiedTerminalWidget: Mouse event passed to super")

    def mouseMoveEvent(self, event):
        # Allow default mouse move event for text selection
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # After releasing the mouse, ensure the cursor is in the right place
        # if no text has been selected.
        if not self.textCursor().hasSelection():
            self.ensure_cursor_at_input()

    def mouseDoubleClickEvent(self, event):
        # Allow default double click event for word selection
        super().mouseDoubleClickEvent(event)

    def paste(self):
        """
        Custom paste implementation to protect read-only parts of the terminal.
        """
        if not self.copy_paste_enabled or self.edit_mode:
            print("UnifiedTerminalWidget: Paste blocked (copy_paste_enabled=False or edit_mode=True)")
            return

        cursor = self.textCursor()
        # Only allow pasting at the input position
        if cursor.position() >= self.input_position:
            clipboard = QApplication.clipboard()
            text_to_paste = clipboard.text()
            if text_to_paste:
                # Use the base class paste to handle the actual insertion
                super().paste()
                self.current_input = self.toPlainText()[self.input_position:]
                print(f"UnifiedTerminalWidget: Pasted text: {text_to_paste[:50]}...")
        else:
            print("UnifiedTerminalWidget: Paste blocked (cursor in read-only area)")


    def keyPressEvent(self, event):
        cursor = self.textCursor()
        cursor_pos = cursor.position()
        key = event.key()

        # Handle Copy Shortcut (Ctrl+C or Cmd+C)
        if event.matches(QKeySequence.StandardKey.Copy):
            if self.textCursor().hasSelection():
                self.copy()
            event.accept()
            return
            
        # Handle Paste Shortcut (Ctrl+V or Cmd+V)
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste()
            event.accept()
            return

        if self.edit_mode:
            self._handle_edit_mode_keys(event, cursor, cursor_pos)
            return

        # Allow navigation keys (arrows, home, end, etc.) everywhere
        nav_keys = {
            Qt.Key.Key_Home, Qt.Key.Key_End, Qt.Key.Key_Up, Qt.Key.Key_Down,
            Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown
        }
        if cursor_pos < self.input_position and key not in nav_keys and not event.matches(QKeySequence.StandardKey.SelectAll):
             # If a non-navigation key is pressed in the output area, move the cursor to the end
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)


        if key == Qt.Key.Key_Home:
            cursor.setPosition(self.input_position)
            self.setTextCursor(cursor)
            event.accept()
            return

        if key == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            command = self.toPlainText()[self.input_position:].strip()
            if command:
                self.append_output("\n")
                self.commandEntered.emit(command)
                self.command_history.append(command)
                self.history_index = len(self.command_history)
                self.current_input = ""
            else:
                self.append_output("\n")
                self.append_prompt()
            event.accept()
            return

        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self._handle_history_navigation(key, cursor)
            event.accept()
            return

        if key == Qt.Key.Key_Backspace and cursor_pos <= self.input_position:
            event.accept()
            return

        if key == Qt.Key.Key_Tab:
            event.accept()
            return

        if key == Qt.Key.Key_Left and cursor_pos <= self.input_position:
            event.accept()
            return

        if cursor_pos >= self.input_position and event.text():
            self.current_input = self.toPlainText()[self.input_position:]

        super().keyPressEvent(event)

    def _handle_edit_mode_keys(self, event, cursor, cursor_pos):
        key = event.key()
        if cursor_pos < self.edit_start_pos or cursor_pos > self.edit_end_pos:
            if key not in {Qt.Key.Key_Home, Qt.Key.Key_End, Qt.Key.Key_Up, Qt.Key.Key_Down,
                           Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown}:
                cursor.setPosition(self.edit_end_pos)
                self.setTextCursor(cursor)

        if key == Qt.Key.Key_Home:
            cursor.setPosition(self.edit_start_pos)
            self.setTextCursor(cursor)
            event.accept()
        elif key == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if self.edit_start_pos <= cursor_pos <= self.edit_end_pos:
                super().keyPressEvent(event)
                self.update_edit_positions()
            event.accept()
        elif key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            super().keyPressEvent(event)
            cursor_pos = cursor.position()
            if cursor_pos < self.edit_start_pos:
                cursor.setPosition(self.edit_start_pos)
            elif cursor_pos > self.edit_end_pos:
                cursor.setPosition(self.edit_end_pos)
            self.setTextCursor(cursor)
            event.accept()
        elif key == Qt.Key.Key_Backspace and cursor_pos <= self.edit_start_pos:
            event.accept()
        elif key == Qt.Key.Key_Left and cursor_pos <= self.edit_start_pos:
            event.accept()
        elif key in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
            event.accept()
        else:
            super().keyPressEvent(event)
            self.update_edit_positions()

    def _handle_history_navigation(self, key, cursor):
        cursor.setPosition(self.input_position)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        if key == Qt.Key.Key_Up and self.command_history:
            if self.history_index > 0:
                self.history_index -= 1
                recalled_command = self.command_history[self.history_index]
                self.current_input = recalled_command
                self.setTextColor(QColor("#E0E0E0"))
                self.insertPlainText(recalled_command)
                self.input_position = cursor.position() - len(recalled_command)
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.setTextCursor(cursor)
        elif key == Qt.Key.Key_Down and self.command_history:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                recalled_command = self.command_history[self.history_index]
                self.current_input = recalled_command
                self.setTextColor(QColor("#E0E0E0"))
                self.insertPlainText(recalled_command)
                self.input_position = cursor.position() - len(recalled_command)
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.setTextCursor(cursor)
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                self.current_input = ""
                self.input_position = cursor.position()
                self.ensure_cursor_at_input()

    def get_current_command(self):
        return self.current_input

    def set_prompt(self, prompt):
        self.current_prompt = prompt

    def start_edit_mode(self, file_path, file_content):
        self.edit_mode = True
        self.edit_file_path = file_path
        self.setReadOnly(False)
        content = f"\n# Editing {file_path}\n{file_content}\n# COMMANDS:\n# Edit above. Save with 💾 button.\n"
        self.append_output(content)
        all_text = self.toPlainText()
        self.edit_start_pos = all_text.find(f"# Editing {file_path}\n") + len(f"# Editing {file_path}\n")
        self.edit_end_pos = all_text.find("\n# COMMANDS:")
        cursor = self.textCursor()
        cursor.setPosition(self.edit_start_pos)
        self.setTextCursor(cursor)
        self.setFocus()

    def exit_edit_mode(self):
        self.edit_mode = False
        self.edit_file_path = None
        self.edit_start_pos = self.edit_end_pos = 0
        self.setReadOnly(True)
        self.append_prompt()
        self.ensure_cursor_at_input()

    def search_in_terminal(self, search_text):
        """Non-destructive search and highlight text in terminal output"""
        if not self.is_valid:
            return

        try:
            # Clear previous search highlights only
            self.clear_terminal_search()

            if not search_text.strip():
                return

            document = self.document()
            text_content = document.toPlainText()

            # Store search highlights for future clearing
            self.search_highlights = []

            # Search for all occurrences case-insensitively
            search_lower = search_text.lower()
            text_lower = text_content.lower()

            start_index = 0
            while True:
                found_index = text_lower.find(search_lower, start_index)
                if found_index == -1:
                    break

                # Create cursor for this match
                cursor = QTextCursor(document)
                cursor.setPosition(found_index)
                cursor.setPosition(found_index + len(search_text), QTextCursor.MoveMode.KeepAnchor)

                # Store original format completely - including background
                original_format = QTextCharFormat(cursor.charFormat())

                # If original format has no background, set it to terminal background
                if not original_format.background().color().isValid():
                    original_format.setBackground(self.terminal_bg_color)

                # Create new format preserving colors but adding highlight
                highlight_format = QTextCharFormat(original_format)
                highlight_format.setBackground(QColor("#FFFF00"))  # Yellow background
                highlight_format.setForeground(QColor("#000000"))  # Black text for visibility

                # Apply the highlight
                cursor.setCharFormat(highlight_format)

                # Store highlight info for restoration
                self.search_highlights.append({
                    'start': found_index,
                    'end': found_index + len(search_text),
                    'original_format': original_format,
                    'original_background': original_format.background().color() if original_format.background().color().isValid() else self.terminal_bg_color
                })

                start_index = found_index + 1

        except Exception as e:
            logging.error(f"Error searching in terminal: {e}")


    def clear_terminal_search(self):
        """Clear search highlights while preserving other formatting"""
        if not self.is_valid:
            return

        try:
            # Restore original formatting for each highlight
            for highlight in self.search_highlights:
                cursor = self.textCursor()
                cursor.setPosition(highlight['start'])
                cursor.setPosition(highlight['end'], QTextCursor.MoveMode.KeepAnchor)

                # Restore original format with proper background
                restored_format = QTextCharFormat(highlight['original_format'])

                # Ensure background is properly restored
                original_bg = highlight.get('original_background', self.terminal_bg_color)
                if original_bg.isValid():
                    restored_format.setBackground(original_bg)
                else:
                    restored_format.setBackground(self.terminal_bg_color)

                cursor.setCharFormat(restored_format)

            # Clear the highlights list
            self.search_highlights.clear()

            # Force a repaint to ensure changes are visible
            self.update()

        except Exception as e:
            logging.error(f"Error clearing terminal search: {e}")



    def update_edit_positions(self):
        all_text = self.toPlainText()
        self.edit_start_pos = all_text.find(f"# Editing {self.edit_file_path}\n") + len(f"# Editing {self.edit_file_path}\n")
        self.edit_end_pos = all_text.find("\n# COMMANDS:", self.edit_start_pos)
        if self.edit_end_pos == -1:
            self.edit_end_pos = len(all_text)
        cursor = self.textCursor()
        cursor_pos = cursor.position()
        if cursor_pos < self.edit_start_pos or cursor_pos > self.edit_end_pos:
            cursor.setPosition(min(max(cursor_pos, self.edit_start_pos), self.edit_end_pos))
            self.setTextCursor(cursor)


class SSHTerminalWidget(UnifiedTerminalWidget):
    """Specialized terminal widget for SSH sessions with improved command handling"""

    def __init__(self, pod_name, namespace, parent=None):
        super().__init__(parent)
        self.pod_name = pod_name
        self.namespace = namespace
        self.ssh_session = None
        self.is_ssh_connected = False
        self.pending_input = ""  # Store what user is typing
        self.last_output_position = 0
        self.input_start_position = 0
        self.welcome_shown = False
        self.initial_prompt_received = False
        self.waiting_for_output = False

        # Override some behaviors for SSH
        self.current_prompt = f"Connecting to {pod_name}..."
        self.setReadOnly(False)  # Allow input for SSH

        # Initialize SSH session
        self.init_ssh_session()

    def init_ssh_session(self):
        """Initialize the SSH session to the pod"""
        try:
            from utils.kubernetes_client import KubernetesPodSSH

            self.ssh_session = KubernetesPodSSH(self.pod_name, self.namespace)

            # Connect signals
            self.ssh_session.data_received.connect(self.handle_ssh_data)
            self.ssh_session.error_occurred.connect(self.handle_ssh_error)
            self.ssh_session.session_status.connect(self.handle_ssh_status)
            self.ssh_session.session_closed.connect(self.handle_ssh_closed)

            # Start connection
            if self.ssh_session.connect_to_pod():
                self.append_output(f"🔄 Establishing SSH connection to {self.pod_name}...\n", "#4CAF50")
            else:
                self.append_output(f"❌ Failed to connect to {self.pod_name}\n", "#FF6B68")

        except Exception as e:
            logging.error(f"Error initializing SSH session: {e}")
            self.append_output(f"SSH initialization error: {str(e)}\n", "#FF6B68")

    def clean_terminal_output(self, data):
        """Clean terminal output by removing escape sequences and control characters"""
        if not data:
            return ""

        # Remove ANSI escape sequences but preserve content
        # Remove cursor movement and color codes
        data = re.sub(r'\x1b\[[0-9;]*[mK]', '', data)
        data = re.sub(r'\x1b\[[0-9;]*[ABCDEFGH]', '', data)

        # Remove bracketed paste mode sequences
        data = re.sub(r'\x1b\[?\?2004[hl]', '', data)

        # Remove other escape sequences
        data = re.sub(r'\x1b\][^\x07]*\x07', '', data)
        data = re.sub(r'\x1b[PX^_].*?\x1b\\', '', data)

        # Remove most control characters but keep newlines and tabs
        data = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', data)

        # Normalize line endings
        data = data.replace('\r\n', '\n').replace('\r', '\n')

        return data

    def is_shell_prompt(self, data):
        """Check if data contains a shell prompt"""
        if not data:
            return False

        # Look for common prompt patterns
        prompt_patterns = [
            r'.*[$#%>]\s*$',  # Ends with shell prompt characters
            r'.*@.*:.*[$#]\s*$',  # user@host:path$ format
            r'.*have no name.*[$#]\s*$',  # "I have no name" prompt
        ]

        lines = data.strip().split('\n')
        last_line = lines[-1] if lines else ''

        for pattern in prompt_patterns:
            if re.match(pattern, last_line.strip()):
                return True

        return False

    def handle_ssh_data(self, data):
        """Handle data received from SSH session"""
        if not data or not self.is_valid:
            return

        # Check for ANSI clear screen sequences before any other processing
        if '\x1b[2J' in data or '\x1b[3J' in data:
            self.clear_output()
            # Remove the clear codes from the data string
            # so we can still process the prompt that might be attached
            data = re.sub(r'\x1b\[[23]J', '', data)

        # Clean the rest of the data
        clean_data = self.clean_terminal_output(data)

        if not clean_data:
            return

        # Show welcome message only once when we get the first prompt
        if not self.welcome_shown and self.is_ssh_connected and self.is_shell_prompt(clean_data):
            if not self.initial_prompt_received:
                self._show_ssh_welcome()
                self.welcome_shown = True
                self.initial_prompt_received = True

        # Clear pending input display if we're showing output
        if self.pending_input and not self.is_shell_prompt(clean_data):
            self._clear_pending_input_display()

        # Display the output
        self.append_output(clean_data, "#E0E0E0")

        # Update positions
        cursor = self.textCursor()
        self.last_output_position = cursor.position()
        self.input_position = cursor.position()
        self.input_start_position = cursor.position()

        # If this looks like a prompt, we're ready for input
        if self.is_shell_prompt(clean_data):
            self.waiting_for_output = False
            # Redisplay pending input if any
            if self.pending_input:
                self._display_pending_input()

    def _clear_pending_input_display(self):
        """Clear the currently displayed pending input"""
        if not self.pending_input:
            return

        cursor = self.textCursor()
        cursor.setPosition(self.input_start_position)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        selected_text = cursor.selectedText()

        if self.pending_input in selected_text:
            cursor.removeSelectedText()

        cursor.setPosition(self.input_start_position)
        self.setTextCursor(cursor)

    def _display_pending_input(self):
        """Display the pending input"""
        if not self.pending_input or self.waiting_for_output:
            return

        cursor = self.textCursor()
        cursor.setPosition(self.input_start_position)
        self.setTextCursor(cursor)

        # Insert the pending input with proper formatting
        char_format = QTextCharFormat()
        char_format.setForeground(QColor("#E0E0E0"))
        char_format.setBackground(self.terminal_bg_color)
        cursor.setCharFormat(char_format)
        cursor.insertText(self.pending_input)

        # Move cursor to end
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

    def handle_ssh_error(self, error_message):
        """Handle SSH session errors"""
        if self.is_valid:
            self.append_output(f"\n❌ SSH Error: {error_message}\n", "#FF6B68")

    def handle_ssh_status(self, status_message):
        """Handle SSH session status updates"""
        if self.is_valid:
            if "Connected" in status_message:
                self.is_ssh_connected = True
                self.append_output(f"✅ {status_message}\n", "#4CAF50")

                # Set initial positions
                cursor = self.textCursor()
                self.input_position = cursor.position()
                self.last_output_position = cursor.position()
                self.input_start_position = cursor.position()
            elif "Establishing" in status_message or "Failed" in status_message:
                self.append_output(f"{status_message}\n", "#4CAF50" if "Establishing" in status_message else "#FF6B68")

    def handle_ssh_closed(self):
        """Handle SSH session closure"""
        if self.is_valid:
            self.is_ssh_connected = False
            self.append_output("\n🔴 SSH session closed\n", "#FFA500")
            self.append_output("Connection to pod terminated.\n", "#9ca3af")

    def execute_ssh_command(self, command):
        """Execute command in SSH session"""
        if not self.ssh_session or not self.is_ssh_connected:
            self.append_output("❌ Not connected to pod. Please check connection.\n", "#FF6B68")
            return

        # Handle local exit commands
        command_lower = command.strip().lower()
        if command_lower in ['exit', 'logout', 'quit']:
            self.ssh_session.disconnect()
            return

        # Handle clear command - use alternative if clear doesn't exist
        if command_lower == 'clear':
            # Try multiple clear methods
            commands_to_try = ['clear', 'printf "\\033c"', 'tput clear', 'reset']
            for cmd in commands_to_try:
                try:
                    success = self.ssh_session.send_command(cmd + '\n')
                    if success:
                        self.waiting_for_output = True
                        return
                except:
                    continue
            # If all fail, do local clear
            self.clear_output()
            return

        # For all other commands
        self.waiting_for_output = True

        try:
            if command.strip():
                success = self.ssh_session.send_command(command + '\n')
            else:
                success = self.ssh_session.send_command('\n')

            if not success:
                self.append_output("❌ Failed to send command to pod.\n", "#FF6B68")
                self.waiting_for_output = False
        except Exception as e:
            self.append_output(f"❌ Error sending command: {str(e)}\n", "#FF6B68")
            self.waiting_for_output = False

    def keyPressEvent(self, event):
        """Handle key events for SSH terminal"""
        if not self.is_ssh_connected:
             # Still allow copy/paste even if not connected
            if event.matches(QKeySequence.StandardKey.Copy) or event.matches(QKeySequence.StandardKey.Paste):
                super().keyPressEvent(event)
            else:
                event.accept()
            return

        key = event.key()

        # Allow copy/paste shortcuts to be handled by the parent
        if event.matches(QKeySequence.StandardKey.Copy) or event.matches(QKeySequence.StandardKey.Paste):
            super().keyPressEvent(event)
            return

        # Handle Ctrl+C and Ctrl+D
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_C:
                try:
                    if self.ssh_session:
                        self.ssh_session.send_command('\x03')
                        self.waiting_for_output = False
                except:
                    pass
                self._clear_all_pending_input()
                event.accept()
                return
            elif key == Qt.Key.Key_D:
                try:
                    if self.ssh_session:
                        self.ssh_session.send_command('\x04')
                except:
                    pass
                self._clear_all_pending_input()
                event.accept()
                return

        # Handle Enter key
        if key == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            command_to_send = self.pending_input
            self.append_output(f"\n")
            
            # Add to history if not empty
            if command_to_send.strip():
                self.command_history.append(command_to_send)
                self.history_index = len(self.command_history)

            # Execute the command
            self.execute_ssh_command(command_to_send)
            
            self._clear_all_pending_input()
            event.accept()
            return

        # Handle backspace
        if key == Qt.Key.Key_Backspace:
            if self.pending_input:
                self.pending_input = self.pending_input[:-1]
                self._update_input_display()
            event.accept()
            return

        # Handle history navigation
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self._handle_ssh_history_navigation(key)
            event.accept()
            return

        # Handle regular character input
        if event.text() and event.text().isprintable():
            self.pending_input += event.text()
            self._update_input_display()
            event.accept()
            return

        # Handle Tab key
        if key == Qt.Key.Key_Tab:
            try:
                if self.ssh_session:
                    self.ssh_session.send_command('\t')
            except:
                pass
            event.accept()
            return

        event.accept()

    def _update_input_display(self):
        """Update the display to show current pending input"""
        if not self.is_valid or self.waiting_for_output:
            return

        # Clear current display from input start position
        cursor = self.textCursor()
        cursor.setPosition(self.input_start_position)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

        # Display the pending input if any
        if self.pending_input:
            cursor.setPosition(self.input_start_position)
            self.setTextCursor(cursor)

            char_format = QTextCharFormat()
            char_format.setForeground(QColor("#E0E0E0"))
            char_format.setBackground(self.terminal_bg_color)
            cursor.setCharFormat(char_format)
            cursor.insertText(self.pending_input)

        # Position cursor at end
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

    def _clear_all_pending_input(self):
        """Clear all pending input and reset state"""
        if self.pending_input:
            cursor = self.textCursor()
            cursor.setPosition(self.input_start_position)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()

        self.pending_input = ""
        cursor = self.textCursor()
        self.input_start_position = cursor.position()

    def _show_ssh_welcome(self):
        """Show SSH welcome message once"""
        welcome_msg = (
            f"🔑 SSH Connected to Pod: {self.pod_name}\n"
            f"📍 Namespace: {self.namespace}\n"
            "────────────────────────────────────────\n"
            "✅ Shell session active. Type 'exit' to disconnect.\n"
            "💡 Note: Some containers may show 'I have no name' - this is normal.\n\n"
        )
        self.append_output(welcome_msg, "#4CAF50")

        # Update positions after welcome
        cursor = self.textCursor()
        self.input_start_position = cursor.position()
        self.input_position = cursor.position()
        self.last_output_position = cursor.position()

    def _handle_ssh_history_navigation(self, key):
        """Handle command history navigation"""
        if not self.command_history:
            return

        if key == Qt.Key.Key_Up and self.history_index > 0:
            self.history_index -= 1
            self.pending_input = self.command_history[self.history_index]
        elif key == Qt.Key.Key_Down:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.pending_input = self.command_history[self.history_index]
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                self.pending_input = ""

        self._update_input_display()

    def cleanup_ssh_session(self):
        """Clean up SSH session"""
        try:
            if self.ssh_session:
                self.ssh_session.disconnect()
                self.ssh_session = None
        except Exception as e:
            logging.error(f"Error cleaning up SSH session: {e}")

    def clear_output(self):
        """Override clear_output for SSH terminal"""
        if not self.is_valid:
            return
        try:
            # Clear the widget
            self.clear()

            # Reset state
            self.pending_input = ""
            self.last_output_position = 0
            self.input_position = 0
            self.input_start_position = 0
            self.welcome_shown = False
            self.initial_prompt_received = False
            self.waiting_for_output = False
            self.search_highlights.clear()

            if self.is_ssh_connected:
                self.append_output("🧹 Terminal cleared\n", "#4CAF50")
                cursor = self.textCursor()
                self.input_start_position = cursor.position()
                self.input_position = cursor.position()
                self.last_output_position = cursor.position()
            else:
                self.append_output(f"🔄 Connecting to {self.pod_name}...\n", "#4CAF50")

        except RuntimeError:
            self.is_valid = False

    def __del__(self):
        """Cleanup when widget is destroyed"""
        self.cleanup_ssh_session()
        super().__del__()


class ResizeHandle(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(5)
        self.setCursor(Qt.CursorShape.SizeVerCursor)
        self.setStyleSheet(StyleConstants.RESIZE_HANDLE)
        self.is_dragging = False
        self.drag_start_y = 0
        self.drag_start_height = 0

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start_y = event.globalPosition().y()
            terminal_panel = self.parent()
            while terminal_panel and not isinstance(terminal_panel, TerminalPanel):
                terminal_panel = terminal_panel.parent()
            self.terminal_panel = terminal_panel
            self.drag_start_height = terminal_panel.height() if terminal_panel else 0
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging and self.terminal_panel:
            delta = self.drag_start_y - event.globalPosition().y()
            top_level_window = self.terminal_panel.window()
            parent_height = top_level_window.height() if top_level_window else 1080
            new_height = max(150, min(self.drag_start_height + delta, parent_height - 50))
            self.terminal_panel.setFixedHeight(int(new_height))
            self.terminal_panel.normal_height = int(new_height)
            self.terminal_panel.reposition()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.terminal_panel = None
            event.accept()

class UnifiedTerminalHeader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_terminal = parent
        self.edit_mode = False
        self.current_file = None
        self.available_shells = self._detect_available_shells()
        self.selected_shell = self.available_shells[0][1] if self.available_shells else '/bin/bash'  # Store path only
        self.setup_ui()

    def _detect_available_shells(self):
        os_name = platform.system()
        shells = []
        default_shell = os.environ.get('SHELL', '/bin/bash') if os_name != 'Windows' else 'powershell.exe'

        if os_name == 'Windows':
            candidates = [
                ('PowerShell', 'powershell.exe'),
                ('PowerShell Core', 'pwsh.exe'),
                ('Command Prompt', 'cmd.exe')
            ]
            for name, shell in candidates:
                if shutil.which(shell):
                    shells.append((name, shutil.which(shell)))
        else:
            candidates = [
                ('Bash', '/bin/bash'),
                ('Zsh', '/bin/zsh'),
                ('Fish', '/bin/fish'),
                ('PowerShell Core', 'pwsh'),
                ('Sh', '/bin/sh')
            ]
            for name, shell in candidates:
                if shutil.which(shell):
                    shells.append((name, shutil.which(shell)))
            try:
                with open('/etc/shells', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and shutil.which(line):
                            shell_name = os.path.basename(line)
                            if not any(s[1] == line for s in shells):
                                shells.append((shell_name.capitalize(), line))
            except FileNotFoundError:
                pass

        shells = [(name, path) for name, path in shells if path != default_shell]
        shells.insert(0, (os.path.basename(default_shell).capitalize(), default_shell))
        return shells

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.resize_handle = ResizeHandle(self)
        main_layout.addWidget(self.resize_handle)

        self.header_content = QWidget()
        self.header_content.setFixedHeight(36)
        self.header_content.setStyleSheet(StyleConstants.HEADER_CONTENT)

        self.content_layout = QHBoxLayout(self.header_content)
        self.content_layout.setContentsMargins(8, 0, 16, 0)
        self.content_layout.setSpacing(4)

        # Tabs container
        self.tabs_container = QWidget()
        self.tabs_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(0)
        self.tabs_layout.addStretch()

        # Search input - always visible for all tabs
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setStyleSheet(StyleConstants.SEARCH_INPUT)
        self.search_input.textChanged.connect(self._on_search_changed)

        # Controls container
        self.controls = QWidget()
        self.controls_layout = QHBoxLayout(self.controls)
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_layout.setSpacing(4)

        # Shell dropdown (for regular terminals)
        self.shell_dropdown = QComboBox()
        self.shell_dropdown.setFixedSize(120, 24)
        self.shell_dropdown.setStyleSheet(StyleConstants.SHELL_DROPDOWN)
        for name, _ in self.available_shells:
            self.shell_dropdown.addItem(name)
        self.shell_dropdown.currentIndexChanged.connect(self._update_selected_shell)
        self.controls_layout.addWidget(self.shell_dropdown)

        # Create buttons
        buttons = [
            ("icons/terminal_add.svg", "New Terminal", self.add_new_tab),
            ("icons/terminal_refresh.svg", "Refresh Terminal / Refresh Logs", self.refresh_terminal),
            ("icons/terminal_download.svg", "Download Terminal Output / Download Logs", self.download_terminal_output),
            ("💾", "Save File", self.save_current_file),
            ("icons/terminal_up_down.svg", "Maximize/Restore Terminal", self.toggle_maximize),
            ("icons/terminal_close.svg", "Hide Terminal Panel", self.hide_terminal)
        ]
        self.new_tab_btn, self.refresh_btn, self.download_btn, self.save_btn, self.maximize_btn, self.close_btn = [
            self.create_header_button(text, tooltip, callback) for text, tooltip, callback in buttons
        ]
        self.save_btn.hide()

        for btn in (self.new_tab_btn, self.refresh_btn, self.download_btn, self.save_btn, self.maximize_btn, self.close_btn):
            self.controls_layout.addWidget(btn)

        # Add components to main layout
        self.content_layout.addWidget(self.tabs_container, 1)
        self.content_layout.addWidget(self.search_input)
        self.content_layout.addWidget(self.controls)
        main_layout.addWidget(self.header_content)

    def _update_selected_shell(self, index):
        if index >= 0 and index < len(self.available_shells):
            self.selected_shell = self.available_shells[index][1]  # Store path only
            print(f"Selected shell updated to: {self.selected_shell}")
            # Automatically create a new terminal tab with the selected shell
            self.add_new_tab()

    def _on_search_changed(self, text):
        """Handle search text change for both terminal and logs tabs"""
        if self._is_active_tab_logs():
            # Search in logs
            active_logs = self._get_active_logs_tab()
            if active_logs and hasattr(active_logs, 'set_search_filter'):
                active_logs.set_search_filter(text)
        else:
            # Search in terminal output
            active_terminal = self._get_active_terminal_widget()
            if active_terminal and hasattr(active_terminal, 'search_in_terminal'):
                active_terminal.search_in_terminal(text)

    def _get_active_terminal_widget(self):
        """Get the active terminal widget"""
        try:
            if (self.parent_terminal and
                hasattr(self.parent_terminal, 'active_terminal_index') and
                self.parent_terminal.active_terminal_index < len(self.parent_terminal.terminal_tabs)):

                active_tab_data = self.parent_terminal.terminal_tabs[self.parent_terminal.active_terminal_index]
                return active_tab_data.get('terminal_widget')
        except Exception as e:
            logging.error(f"Error getting active terminal widget: {e}")
        return None

    def update_header_for_tab_type(self, is_logs_tab):
        """Update header visibility based on tab type"""
        try:
            # Update search placeholder based on tab type
            if is_logs_tab:
                self.search_input.setPlaceholderText("Search in logs...")
            else:
                self.search_input.setPlaceholderText("Search in terminal...")

            # Show/hide shell dropdown (only for regular terminals)
            self.shell_dropdown.setVisible(not is_logs_tab)

            # Update button tooltips
            if is_logs_tab:
                self.refresh_btn.setToolTip("Refresh Logs")
                self.download_btn.setToolTip("Download Logs")
            else:
                self.refresh_btn.setToolTip("Refresh Terminal")
                self.download_btn.setToolTip("Download Terminal Output")
        except Exception as e:
            logging.error(f"Error checking if update header tab is logs: {e}")
        return False

    def _is_active_tab_logs(self):
        """Check if the active tab is a logs tab"""
        try:
            if (self.parent_terminal and
                hasattr(self.parent_terminal, 'active_terminal_index') and
                self.parent_terminal.active_terminal_index < len(self.parent_terminal.terminal_tabs)):

                active_tab_data = self.parent_terminal.terminal_tabs[self.parent_terminal.active_terminal_index]
                return active_tab_data.get('is_logs_tab', False)
        except Exception as e:
            logging.error(f"Error checking if active tab is logs: {e}")
        return False

    def _get_active_logs_tab(self):
        """Get the active logs tab viewer"""
        try:
            if (self.parent_terminal and
                hasattr(self.parent_terminal, 'active_terminal_index') and
                self.parent_terminal.active_terminal_index < len(self.parent_terminal.terminal_tabs)):

                active_tab_data = self.parent_terminal.terminal_tabs[self.parent_terminal.active_terminal_index]
                if active_tab_data.get('is_logs_tab', False):
                    return active_tab_data.get('logs_viewer')
        except Exception as e:
            logging.error(f"Error getting active logs tab: {e}")
        return None

    def update_header_for_ssh_tab(self):
        """Update header for SSH tab"""
        try:
            self.search_input.setPlaceholderText("Search in SSH session...")
            self.shell_dropdown.setVisible(False)  # Hide shell dropdown for SSH

            # Update button tooltips
            self.refresh_btn.setToolTip("Reconnect SSH Session")
            self.download_btn.setToolTip("Download SSH Session Log")

        except Exception as e:
            logging.error(f"Error updating header for SSH tab: {e}")

    def refresh_terminal(self):
        """Refresh terminal, logs, or SSH based on active tab"""
        if self.edit_mode:
            self.exit_edit_mode()
            return

        if self._is_active_tab_ssh():
            # Refresh SSH session
            self.refresh_ssh_session()
        elif self._is_active_tab_logs():
            # Refresh logs
            active_logs = self._get_active_logs_tab()
            if active_logs and hasattr(active_logs, 'refresh_logs'):
                active_logs.refresh_logs()
        else:
            # Refresh terminal
            if hasattr(self.parent_terminal, 'restart_active_terminal'):
                self.parent_terminal.restart_active_terminal()

    def refresh_ssh_session(self):
        """Refresh/reconnect SSH session"""
        if self._is_active_tab_ssh():
            active_ssh = self._get_active_ssh_tab()
            if active_ssh and hasattr(active_ssh, 'init_ssh_session'):
                active_ssh.cleanup_ssh_session()
                active_ssh.init_ssh_session()

    def download_terminal_output(self):
        """Download terminal output, logs, or SSH session based on active tab"""
        if self._is_active_tab_ssh():
            # Download SSH session log
            active_ssh = self._get_active_ssh_tab()
            if active_ssh:
                self._download_ssh_session(active_ssh)
        elif self._is_active_tab_logs():
            # Download logs
            active_logs = self._get_active_logs_tab()
            if active_logs:
                self._download_logs(active_logs)
        else:
            # Download terminal output
            if hasattr(self.parent_terminal, 'download_terminal_output'):
                self.parent_terminal.download_terminal_output()

    def _download_ssh_session(self, ssh_terminal):
        """Download SSH session content"""
        try:
            # Get SSH session content
            if hasattr(ssh_terminal, 'toPlainText'):
                session_content = ssh_terminal.toPlainText()

                # Get pod name for filename
                pod_name = getattr(ssh_terminal, 'pod_name', 'unknown-pod')
                namespace = getattr(ssh_terminal, 'namespace', 'default')

                # Open file dialog
                from PyQt6.QtWidgets import QFileDialog
                filename, _ = QFileDialog.getSaveFileName(
                    self.parent_terminal,
                    f"Save SSH Session for {pod_name}",
                    f"{pod_name}_{namespace}_ssh_session.txt",
                    "Text Files (*.txt);;All Files (*)"
                )

                if filename:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(f"# SSH Session for Pod: {pod_name}\n")
                        f.write(f"# Namespace: {namespace}\n")
                        f.write(f"# Downloaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write("# " + "="*50 + "\n\n")
                        f.write(session_content)

                    print(f"SSH session saved to: {filename}")

        except Exception as e:
            logging.error(f"Error downloading SSH session: {e}")

    def _is_active_tab_ssh(self):
        """Check if the active tab is an SSH tab"""
        try:
            if (self.parent_terminal and
                hasattr(self.parent_terminal, 'active_terminal_index') and
                self.parent_terminal.active_terminal_index < len(self.parent_terminal.terminal_tabs)):

                active_tab_data = self.parent_terminal.terminal_tabs[self.parent_terminal.active_terminal_index]
                return active_tab_data.get('is_ssh_tab', False)
        except Exception as e:
            logging.error(f"Error checking if active tab is SSH: {e}")
        return False

    def _get_active_ssh_tab(self):
        """Get the active SSH tab widget"""
        try:
            if (self.parent_terminal and
                hasattr(self.parent_terminal, 'active_terminal_index') and
                self.parent_terminal.active_terminal_index < len(self.parent_terminal.terminal_tabs)):

                active_tab_data = self.parent_terminal.terminal_tabs[self.parent_terminal.active_terminal_index]
                if active_tab_data.get('is_ssh_tab', False):
                    return active_tab_data.get('terminal_widget')
        except Exception as e:
            logging.error(f"Error getting active SSH tab: {e}")
        return None

    def create_header_button(self, text, tooltip, callback):
        button = QToolButton()
        if text.endswith('.svg'):
            button.setIcon(QIcon(text))
            button.setIconSize(QSize(10, 10))
        else:
            button.setText(text)
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(28, 28)
        button.setStyleSheet(StyleConstants.HEADER_BUTTON)
        button.clicked.connect(callback)
        return button

    def add_new_tab(self):
        if hasattr(self.parent_terminal, 'add_terminal_tab'):
            self.parent_terminal.add_terminal_tab(shell=self.selected_shell)

    def enter_edit_mode(self, file_path):
        self.edit_mode = True
        self.current_file = file_path
        self.save_btn.show()
        self.refresh_btn.setText("✖")
        self.refresh_btn.setToolTip("Cancel Editing")
        if self._active_terminal_widget():
            self._active_terminal_widget().start_edit_mode(file_path, self.read_file_content(file_path))

    def read_file_content(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            return f"# Error reading file: {str(e)}\n"

    def exit_edit_mode(self):
        self.edit_mode = False
        self.current_file = None
        self.save_btn.hide()
        self.refresh_btn.setIcon(QIcon("icons/terminal_refresh.svg"))
        self.refresh_btn.setToolTip("Refresh Terminal")
        if self._active_terminal_widget():
            self._active_terminal_widget().exit_edit_mode()

    def save_current_file(self):
        if not self.edit_mode or not self.current_file or not self._active_terminal_widget():
            return
        terminal_widget = self._active_terminal_widget()
        content = terminal_widget.toPlainText()
        start_marker = f"# Editing {self.current_file}\n"
        end_marker = "\n# COMMANDS:"
        start_idx = content.find(start_marker)
        if start_idx >= 0:
            start_idx += len(start_marker)
            end_idx = content.find(end_marker, start_idx)
            if end_idx >= 0:
                file_content = content[start_idx:end_idx].strip()
                try:
                    with open(self.current_file, 'w') as f:
                        f.write(file_content)
                    terminal_widget.append_output(f"\n# File saved successfully: {self.current_file}\n", "#4CAF50")
                    terminal_widget.append_output(f"\n$ kubectl apply -f {self.current_file}\n")
                    terminal_widget.commandEntered.emit(f"kubectl apply -f {self.current_file}")
                    self.exit_edit_mode()
                except Exception as e:
                    terminal_widget.append_output(f"\n# Error saving file: {str(e)}\n", "#FF6B68")
            else:
                terminal_widget.append_output("\n# Could not determine file content bounds\n", "#FF6B68")
        else:
            terminal_widget.append_output("\n# Could not determine file content bounds\n", "#FF6B68")

    def refresh_terminal(self):
        """Refresh terminal or logs based on active tab"""
        if self.edit_mode:
            self.exit_edit_mode()
            return

        if self._is_active_tab_logs():
            # Refresh logs
            active_logs = self._get_active_logs_tab()
            if active_logs and hasattr(active_logs, 'refresh_logs'):
                active_logs.refresh_logs()
        else:
            # Refresh terminal
            if hasattr(self.parent_terminal, 'restart_active_terminal'):
                self.parent_terminal.restart_active_terminal()

    def download_terminal_output(self):
        """Download terminal output or logs based on active tab"""
        if self._is_active_tab_logs():
            # Download logs
            active_logs = self._get_active_logs_tab()
            if active_logs:
                self._download_logs(active_logs)
        else:
            # Download terminal output
            if hasattr(self.parent_terminal, 'download_terminal_output'):
                self.parent_terminal.download_terminal_output()

    def _download_logs(self, logs_viewer):
        """Download logs from logs viewer"""
        try:
            # Get logs content
            if hasattr(logs_viewer, 'logs_display') and logs_viewer.logs_display:
                logs_content = logs_viewer.logs_display.toPlainText()

                # Get pod name for filename
                pod_name = getattr(logs_viewer, 'pod_name', 'unknown-pod')
                namespace = getattr(logs_viewer, 'namespace', 'default')

                # Open file dialog
                filename, _ = QFileDialog.getSaveFileName(
                    self.parent_terminal,
                    f"Save Logs for {pod_name}",
                    f"{pod_name}_{namespace}_logs.txt",
                    "Text Files (*.txt);;All Files (*)"
                )

                if filename:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(f"# Logs for Pod: {pod_name}\n")
                        f.write(f"# Namespace: {namespace}\n")
                        f.write(f"# Downloaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write("# " + "="*50 + "\n\n")
                        f.write(logs_content)

                    print(f"Logs saved to: {filename}")

        except Exception as e:
            logging.error(f"Error downloading logs: {e}")

    def toggle_maximize(self):
        if hasattr(self.parent_terminal, 'toggle_maximize'):
            self.parent_terminal.toggle_maximize()
            self.maximize_btn.setIcon(QIcon("icons/terminal_up_down.svg"))
            self.maximize_btn.setToolTip("Restore Terminal" if self.parent_terminal.is_maximized else "Maximize Terminal")

    def hide_terminal(self):
        if hasattr(self.parent_terminal, 'hide_terminal'):
            self.parent_terminal.hide_terminal()

    def add_tab(self, tab_container):
        self.tabs_layout.insertWidget(self.tabs_layout.count() - 1, tab_container)

    def remove_tab(self, tab_container):
        for i in range(self.tabs_layout.count()):
            if self.tabs_layout.itemAt(i).widget() == tab_container:
                widget = self.tabs_layout.takeAt(i).widget()
                widget.deleteLater()
                break

    def _active_terminal_widget(self):
        if self.parent_terminal and self.parent_terminal.active_terminal_index < len(self.parent_terminal.terminal_tabs):
            return self.parent_terminal.terminal_tabs[self.parent_terminal.active_terminal_index].get('terminal_widget')
        return None

class LogsHeaderWidget(QWidget):
    """Simplified header widget for logs viewer - search moved to terminal header"""

    container_changed = pyqtSignal(str)
    tail_lines_changed = pyqtSignal(int)
    follow_toggled = pyqtSignal(bool)
    refresh_requested = pyqtSignal()

    def __init__(self, pod_name, namespace, parent=None):
        super().__init__(parent)
        self.pod_name = pod_name
        self.namespace = namespace
        self.containers = []
        self.setup_ui()
        self.load_containers()

    def setup_ui(self):
        """Setup the simplified header UI components with fixed layout"""
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3d3d3d;
            }
            QComboBox {
                background-color: #1e1e1e;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                color: white;
                font-size: 12px;
                min-width: 80px;
                max-height: 24px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: white;
                selection-background-color: #2196F3;
            }
            QCheckBox {
                color: white;
                font-size: 12px;
                padding: 2px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #666;
                border-radius: 3px;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #2196F3;
                border-color: #2196F3;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(8)

        # Single row with all controls
        controls_row = QHBoxLayout()
        controls_row.setSpacing(12)

        # Pod info - compact
        self.pod_info = QLabel(f"📋 {self._truncate_name(self.pod_name, 20)}")
        self.pod_info.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 11px;")
        self.pod_info.setToolTip(f"Pod: {self.pod_name}\nNamespace: {self.namespace}")
        controls_row.addWidget(self.pod_info)

        controls_row.addStretch()

        # Container selection
        container_label = QLabel("📦")
        container_label.setFixedSize(20, 20)
        self.container_combo = QComboBox()
        self.container_combo.setFixedHeight(24)
        self.container_combo.currentTextChanged.connect(self.container_changed.emit)
        controls_row.addWidget(container_label)
        controls_row.addWidget(self.container_combo)

        # Tail lines selection
        lines_label = QLabel("📜")
        lines_label.setFixedSize(20, 20)
        self.lines_combo = QComboBox()
        self.lines_combo.setFixedHeight(24)
        self.lines_combo.addItems(["50", "100", "200", "500", "1000", "All"])
        self.lines_combo.setCurrentText("200")
        self.lines_combo.currentTextChanged.connect(self._on_lines_changed)
        controls_row.addWidget(lines_label)
        controls_row.addWidget(self.lines_combo)

        # Follow logs checkbox
        self.follow_checkbox = QCheckBox("Follow")
        self.follow_checkbox.setChecked(True)
        self.follow_checkbox.toggled.connect(self.follow_toggled.emit)
        controls_row.addWidget(self.follow_checkbox)

        # Search results label (updated by terminal header search)
        self.search_results_label = QLabel("")
        self.search_results_label.setStyleSheet("color: #4CAF50; font-size: 10px; font-weight: bold;")
        controls_row.addWidget(self.search_results_label)

        main_layout.addLayout(controls_row)

    def _truncate_name(self, name, max_length):
        """Truncate name if it's too long"""
        if len(name) <= max_length:
            return name
        return name[:max_length-3] + "..."

    def load_containers(self):
        """Load available containers for the pod"""
        try:
            from utils.kubernetes_client import get_kubernetes_client
            kube_client = get_kubernetes_client()

            if kube_client and kube_client.v1:
                pod = kube_client.v1.read_namespaced_pod(name=self.pod_name, namespace=self.namespace)
                if pod.spec and pod.spec.containers:
                    self.containers = [c.name for c in pod.spec.containers]
                    self.container_combo.clear()
                    self.container_combo.addItems(self.containers)

                    if len(self.containers) == 1:
                        self.container_combo.setCurrentText(self.containers[0])

        except Exception as e:
            logging.error(f"Error loading containers: {e}")
            self.containers = []

    def _on_lines_changed(self, text):
        """Handle tail lines change"""
        try:
            if text == "All":
                self.tail_lines_changed.emit(-1)
            else:
                self.tail_lines_changed.emit(int(text))
        except ValueError:
            self.tail_lines_changed.emit(200)

    def update_search_results(self, current_results, total_logs):
        """Update search results display"""
        if current_results > 0:
            self.search_results_label.setText(f"📍 {current_results}/{total_logs}")
        else:
            self.search_results_label.setText("")

    def update_status(self, message):
        """Update status - now handled by bottom indicator"""
        pass

class LogsStreamWorker(QThread):
    """Worker thread for streaming logs from Kubernetes API"""

    log_received = pyqtSignal(str, str)  # log_line, timestamp
    error_occurred = pyqtSignal(str)
    connection_status = pyqtSignal(str)  # status message

    def __init__(self, pod_name, namespace, container=None, follow=True, tail_lines=200):
        super().__init__()
        self.pod_name = pod_name
        self.namespace = namespace
        self.container = container
        self.follow = follow
        self.tail_lines = tail_lines
        self._stop_requested = False
        self._kube_client = None

    def stop(self):
        """Stop the streaming"""
        self._stop_requested = True
        self.quit()

    def run(self):
        """Run the log streaming"""
        try:
            from utils.kubernetes_client import get_kubernetes_client
            self._kube_client = get_kubernetes_client()

            if not self._kube_client or not self._kube_client.v1:
                self.error_occurred.emit("Kubernetes client not available")
                return

            self.connection_status.emit("Connecting to log stream...")

            if self.follow:
                self._stream_logs()
            else:
                self._fetch_static_logs()

        except Exception as e:
            self.error_occurred.emit(f"Log streaming error: {str(e)}")

    def _stream_logs(self):
        """Stream logs using Kubernetes watch API"""
        try:
            # First get recent logs
            self._fetch_initial_logs()

            if self._stop_requested:
                return

            # Then start streaming new logs
            self.connection_status.emit("🔴 Live streaming...")

            w = watch.Watch()
            stream = w.stream(
                self._kube_client.v1.read_namespaced_pod_log,
                name=self.pod_name,
                namespace=self.namespace,
                container=self.container,
                follow=True,
                timestamps=True,
                since_seconds=1  # Only get very recent logs for streaming
            )

            for event in stream:
                if self._stop_requested:
                    w.stop()
                    break

                # Parse the log line
                log_line = event
                timestamp = datetime.now().strftime("%H:%M:%S")

                # Extract timestamp if present
                if log_line and ' ' in log_line and log_line.startswith('20'):
                    parts = log_line.split(' ', 1)
                    if len(parts) == 2:
                        try:
                            timestamp = parts[0].split('T')[1][:8]  # Extract time part
                            log_line = parts[1]
                        except:
                            pass

                self.log_received.emit(log_line, timestamp)

        except ApiException as e:
            if not self._stop_requested:
                self.error_occurred.emit(f"API error during streaming: {e.reason}")
        except Exception as e:
            if not self._stop_requested:
                self.error_occurred.emit(f"Streaming error: {str(e)}")

    def _fetch_initial_logs(self):
        """Fetch initial logs before starting stream"""
        try:
            kwargs = {
                'name': self.pod_name,
                'namespace': self.namespace,
                'timestamps': True
            }

            if self.container:
                kwargs['container'] = self.container

            if self.tail_lines and self.tail_lines > 0:
                kwargs['tail_lines'] = self.tail_lines

            logs = self._kube_client.v1.read_namespaced_pod_log(**kwargs)

            if logs:
                for line in logs.strip().split('\n'):
                    if self._stop_requested:
                        break

                    if line.strip():
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        log_line = line

                        # Extract timestamp if present
                        if ' ' in line and line.startswith('20'):
                            parts = line.split(' ', 1)
                            if len(parts) == 2:
                                try:
                                    timestamp = parts[0].split('T')[1][:8]
                                    log_line = parts[1]
                                except:
                                    pass

                        self.log_received.emit(log_line, timestamp)

        except Exception as e:
            logging.error(f"Error fetching initial logs: {e}")

    def _fetch_static_logs(self):
        """Fetch static logs (non-streaming)"""
        self._fetch_initial_logs()
        self.connection_status.emit("📋 Static logs loaded")

class EnhancedLogsViewer(QWidget):
    """Enhanced logs viewer with search highlighting and improved functionality"""

    def __init__(self, pod_name, namespace, parent=None):
        super().__init__(parent)
        self.pod_name = pod_name
        self.namespace = namespace
        self.current_container = None
        self.follow_enabled = True
        self.search_text = ""
        self.tail_lines = 200

        # Log storage
        self.all_logs = []  # Store all logs for searching
        self.search_matches = 0  # Count of search matches

        # Worker thread
        self.stream_worker = None

        self.setup_ui()
        self.connect_signals()
        self.start_log_stream()

    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with controls (simplified - no search)
        self.header = LogsHeaderWidget(self.pod_name, self.namespace)
        layout.addWidget(self.header)

        # Main content area
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Logs display area
        self.logs_display = QTextEdit()
        self.logs_display.setReadOnly(True)
        self.logs_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Set font for logs
        font = QFont("Consolas", 9)
        self.logs_display.setFont(font)

        self.logs_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: none;
                selection-background-color: #264F78;
                padding: 8px;
            }
            QScrollBar:vertical {
                border: none;
                background: #2d2d2d;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
        """)

        content_layout.addWidget(self.logs_display)

        # Status indicator at bottom with transparent background
        self.status_indicator = QLabel()
        self.status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_indicator.setStyleSheet("""
            QLabel {
                background-color: rgba(45, 45, 45, 0.8);
                color: #4CAF50;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                margin: 4px;
            }
        """)
        self.status_indicator.setVisible(False)
        content_layout.addWidget(self.status_indicator)

        layout.addWidget(content_area)

    def connect_signals(self):
        """Connect header signals to handlers"""
        self.header.container_changed.connect(self.set_container)
        self.header.tail_lines_changed.connect(self.set_tail_lines)
        self.header.follow_toggled.connect(self.set_follow_mode)
        self.header.refresh_requested.connect(self.refresh_logs)

    def start_log_stream(self):
        """Start the log streaming worker"""
        self.stop_log_stream()

        self.stream_worker = LogsStreamWorker(
            self.pod_name,
            self.namespace,
            self.current_container,
            self.follow_enabled,
            self.tail_lines
        )

        self.stream_worker.log_received.connect(self.add_log_line)
        self.stream_worker.error_occurred.connect(self.handle_stream_error)
        self.stream_worker.connection_status.connect(self.update_status)

        self.stream_worker.start()

    def stop_log_stream(self):
        """Stop the current log stream"""
        if self.stream_worker and self.stream_worker.isRunning():
            self.stream_worker.stop()
            self.stream_worker.wait(2000)  # Wait up to 2 seconds
            if self.stream_worker.isRunning():
                self.stream_worker.terminate()

    def add_log_line(self, log_line, timestamp):
        """Add a new log line to the display"""
        if not log_line.strip():
            return

        # Store the original log
        log_entry = {
            'timestamp': timestamp,
            'line': log_line,
            'original': f"[{timestamp}] {log_line}"
        }
        self.all_logs.append(log_entry)

        # Display the log line with highlighting if needed
        self.display_log_line(log_entry)

        # Update search results if search is active
        if self.search_text:
            self.update_search_display()

        # Keep only last 10000 logs to prevent memory issues
        if len(self.all_logs) > 10000:
            self.all_logs = self.all_logs[-5000:]  # Keep last 5000
            if self.search_text:
                self.refresh_display()  # Refresh display after cleanup

    def display_log_line(self, log_entry):
        """Display a log line in the text widget with search highlighting"""
        cursor = self.logs_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        line_text = log_entry['original']

        # Check if this line should be displayed based on search
        if self.search_text and self.search_text.lower() not in log_entry['line'].lower():
            return  # Skip lines that don't match search

        # Determine base color based on log content
        line_lower = log_entry['line'].lower()
        base_color = self.get_log_color(line_lower)

        # If there's search text, highlight it
        if self.search_text and self.search_text.lower() in line_text.lower():
            self.insert_highlighted_text(cursor, line_text, self.search_text, base_color)
        else:
            # Insert without highlighting
            char_format = QTextCharFormat()
            char_format.setForeground(QColor(base_color))
            cursor.setCharFormat(char_format)
            cursor.insertText(f"{line_text}\n")

        # Auto-scroll to bottom if follow is enabled
        if self.follow_enabled:
            scrollbar = self.logs_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def insert_highlighted_text(self, cursor, text, search_term, base_color):
        """Insert text with search term highlighted"""
        search_lower = search_term.lower()
        text_lower = text.lower()

        # Find all occurrences of search term
        start_pos = 0

        while True:
            found_pos = text_lower.find(search_lower, start_pos)
            if found_pos == -1:
                # Insert remaining text
                if start_pos < len(text):
                    char_format = QTextCharFormat()
                    char_format.setForeground(QColor(base_color))
                    cursor.setCharFormat(char_format)
                    cursor.insertText(text[start_pos:])
                break

            # Insert text before match
            if found_pos > start_pos:
                char_format = QTextCharFormat()
                char_format.setForeground(QColor(base_color))
                cursor.setCharFormat(char_format)
                cursor.insertText(text[start_pos:found_pos])

            # Insert highlighted match
            match_text = text[found_pos:found_pos + len(search_term)]
            highlight_format = QTextCharFormat()
            highlight_format.setForeground(QColor("#000000"))  # Black text
            highlight_format.setBackground(QColor("#FFFF00"))  # Yellow background
            highlight_format.setFontWeight(QFont.Weight.Bold)
            cursor.setCharFormat(highlight_format)
            cursor.insertText(match_text)

            start_pos = found_pos + len(search_term)

        # Add newline
        char_format = QTextCharFormat()
        char_format.setForeground(QColor(base_color))
        char_format.setBackground(QColor())  # Clear background
        cursor.setCharFormat(char_format)
        cursor.insertText("\n")

    def get_log_color(self, line):
        """Get color for log line based on content"""
        if any(keyword in line for keyword in ['error', 'err', 'exception', 'failed', 'fatal']):
            return "#ff6b68"  # Red for errors
        elif any(keyword in line for keyword in ['warn', 'warning']):
            return "#ffa500"  # Orange for warnings
        elif any(keyword in line for keyword in ['info', 'information']):
            return "#4caf50"  # Green for info
        elif any(keyword in line for keyword in ['debug', 'trace']):
            return "#9ca3af"  # Gray for debug
        else:
            return "#e0e0e0"  # Default white

    def set_search_filter(self, search_text):
        """Set search filter and refresh display with highlighting"""
        self.search_text = search_text.strip()
        self.refresh_display()
        self.update_search_display()

    def update_search_display(self):
        """Update search results counter"""
        if self.search_text:
            # Count matches in current logs
            matches = 0
            for log_entry in self.all_logs:
                if self.search_text.lower() in log_entry['line'].lower():
                    matches += 1

            self.search_matches = matches
            self.header.update_search_results(matches, len(self.all_logs))
        else:
            self.search_matches = 0
            self.header.update_search_results(0, len(self.all_logs))

    def set_container(self, container):
        """Change container and restart stream"""
        if container != self.current_container:
            self.current_container = container
            self.clear_logs()
            self.start_log_stream()

    def set_tail_lines(self, lines):
        """Set tail lines and restart stream"""
        if lines != self.tail_lines:
            self.tail_lines = lines
            self.clear_logs()
            self.start_log_stream()

    def set_follow_mode(self, follow):
        """Enable/disable follow mode"""
        self.follow_enabled = follow
        if not follow:
            self.update_status("📋 Static mode - logs will not update automatically")
            self.show_status_indicator("📋 Static Mode", "#9ca3af")
        else:
            self.update_status("🔴 Live mode - following new logs")
            self.show_status_indicator("🔴 Live Mode", "#4CAF50")

    def show_status_indicator(self, text, color):
        """Show status indicator at bottom"""
        self.status_indicator.setText(text)
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(45, 45, 45, 0.8);
                color: {color};
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                margin: 4px;
            }}
        """)
        self.status_indicator.setVisible(True)

        # Hide after 3 seconds
        QTimer.singleShot(3000, lambda: self.status_indicator.setVisible(False))

    def refresh_logs(self):
        """Refresh the log stream"""
        self.clear_logs()
        self.start_log_stream()
        self.show_status_indicator("🔄 Refreshing...", "#2196F3")

    def clear_logs(self):
        """Clear all logs from display and storage"""
        self.all_logs.clear()
        self.search_matches = 0
        self.logs_display.clear()
        self.header.update_search_results(0, 0)

    def refresh_display(self):
        """Refresh the display with current search filter and highlighting"""
        self.logs_display.clear()

        displayed_count = 0
        for log_entry in self.all_logs:
            # Apply search filter
            if self.search_text:
                if self.search_text.lower() not in log_entry['line'].lower():
                    continue

            self.display_log_line(log_entry)
            displayed_count += 1

        # Auto-scroll to bottom
        if self.follow_enabled:
            scrollbar = self.logs_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def handle_stream_error(self, error_message):
        """Handle streaming errors"""
        self.header.update_status(f"❌ Error: {error_message}")
        self.show_status_indicator("❌ Error", "#ff6b68")
        logging.error(f"Log stream error: {error_message}")

    def update_status(self, message):
        """Update status label"""
        self.header.update_status(message)

    def closeEvent(self, event):
        """Handle close event"""
        self.stop_log_stream()
        super().closeEvent(event)

class TerminalPanel(QWidget):
    def __init__(self, parent, working_directory=""):
        super().__init__(parent)
        self.parent_window = parent
        self.active_terminal_index = 0
        self.is_visible = False
        self.is_maximized = False
        self.terminal_tabs = []
        self.sidebar_width = 0
        self.working_directory = self._resolve_working_directory(working_directory)
        self.normal_height = 300
        self.copy_paste_enabled = False
        self.setup_ui()
        self.add_terminal_tab()
        self.parent_window.installEventFilter(self)
        QApplication.instance().aboutToQuit.connect(self.terminate_all_processes)
        print(f"TerminalPanel initialized with copy_paste_enabled={self.copy_paste_enabled}")

    def _resolve_working_directory(self, relative_path):
        base_dir = os.getcwd()
        target_dir = os.path.normpath(os.path.join(base_dir, relative_path))
        if os.path.isdir(target_dir):
            return target_dir
        print(f"Warning: Working directory '{target_dir}' does not exist. Using default: {base_dir}")
        return base_dir

    def setup_ui(self):
        self.setWindowFlags(Qt.WindowType.Widget | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(self.normal_height)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.terminal_wrapper = QWidget()
        self.terminal_wrapper.setObjectName("terminal_wrapper")
        self.terminal_wrapper.setStyleSheet(StyleConstants.TERMINAL_WRAPPER)

        self.wrapper_layout = QVBoxLayout(self.terminal_wrapper)
        self.wrapper_layout.setContentsMargins(0, 0, 0, 0)
        self.wrapper_layout.setSpacing(0)

        self.unified_header = UnifiedTerminalHeader(self)
        self.wrapper_layout.addWidget(self.unified_header)

        self.terminal_stack = QWidget()
        self.stack_layout = QVBoxLayout(self.terminal_stack)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        self.stack_layout.setSpacing(0)

        self.wrapper_layout.addWidget(self.terminal_stack, 1)
        self.main_layout.addWidget(self.terminal_wrapper)

        self.unified_header.resize_handle.installEventFilter(self)

    def set_preferences(self, preferences):
        self.preferences = preferences
        self.preferences.copy_paste_changed.connect(self.apply_copy_paste_to_terminals)
        self.preferences.font_changed.connect(self.apply_font_to_terminals)
        self.preferences.font_size_changed.connect(self.apply_font_size_to_terminals)
        print("TerminalPanel: Preferences set, connected copy_paste_changed, font_changed, and font_size_changed signals")

    def apply_font_to_terminals(self, font_family):
        print(f"TerminalPanel.apply_font_to_terminals: font_family={font_family}")
        for terminal_data in self.terminal_tabs:
            terminal_widget = terminal_data.get('terminal_widget')
            if terminal_widget and terminal_widget.is_valid:
                terminal_widget.set_font(font_family)

    def apply_font_size_to_terminals(self, font_size):
        print(f"TerminalPanel.apply_font_size_to_terminals: font_size={font_size}, terminals={len(self.terminal_tabs)}")
        for i, terminal_data in enumerate(self.terminal_tabs):
            terminal_widget = terminal_data.get('terminal_widget')
            if terminal_widget and terminal_widget.is_valid:
                print(f"Applying font size to terminal {i}")
                terminal_widget.set_font(terminal_widget.font_family, font_size)
            else:
                print(f"Terminal {i} is invalid or not found")

    def apply_copy_paste_to_terminals(self, enabled):
        self.copy_paste_enabled = enabled
        print(f"TerminalPanel.apply_copy_paste_to_terminals: enabled={enabled}, terminals={len(self.terminal_tabs)}")
        for i, terminal_data in enumerate(self.terminal_tabs):
            terminal_widget = terminal_data.get('terminal_widget')
            if terminal_widget and terminal_widget.is_valid:
                print(f"Applying copy-paste to terminal {i}: enabled={enabled}")
                terminal_widget.set_copy_paste_enabled(enabled)
            else:
                print(f"Terminal {i} is invalid or not found")

    def closeEvent(self, event):
        self.terminate_all_processes()
        super().closeEvent(event)

    def __del__(self):
        self.terminate_all_processes()

    def terminate_all_processes(self):
        for terminal_data in self.terminal_tabs:
            process = terminal_data.get('process')
            if process and process.state() == QProcess.ProcessState.Running:
                try:
                    if platform.system() == 'Windows':
                        process.write(b"exit\r\n")
                        process.waitForFinished(1000)
                    else:
                        process.write(b"exit\n")
                        process.waitForFinished(500)
                        if process.state() == QProcess.ProcessState.Running:
                            process.terminate()
                            process.waitForFinished(500)
                        if process.state() == QProcess.ProcessState.Running:
                            process.kill()
                            process.waitForFinished(200)
                    print(f"Terminated process for terminal {terminal_data.get('tab_button').text()}")
                except Exception as e:
                    print(f"Error terminating process for terminal {terminal_data.get('tab_button').text()}: {e}")

    def add_terminal_tab(self, shell=None):
        tab_index = len(self.terminal_tabs)
        selected_shell = shell or self.unified_header.selected_shell
        if not shutil.which(selected_shell):
            selected_shell = os.environ.get('SHELL', '/bin/bash') if platform.system() != 'Windows' else 'powershell.exe'
            print(f"Selected shell {shell} not found, falling back to {selected_shell}")

        tab_widget = QWidget()
        tab_widget.setFixedHeight(28)
        tab_widget.setCursor(Qt.CursorShape.PointingHandCursor)

        tab_layout = QHBoxLayout(tab_widget)
        tab_layout.setContentsMargins(8, 0, 8, 0)
        tab_layout.setSpacing(6)

        label = QLabel(f"Terminal {tab_index + 1}")
        label.setStyleSheet(StyleConstants.TAB_LABEL)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(16, 16)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(StyleConstants.TAB_CLOSE_BUTTON)

        tab_layout.addWidget(label)
        tab_layout.addWidget(close_btn)

        tab_btn = QPushButton()
        tab_btn.setCheckable(True)
        tab_btn.setStyleSheet(StyleConstants.TAB_BUTTON)
        tab_btn.setLayout(tab_layout)

        tab_container = QWidget()
        container_layout = QHBoxLayout(tab_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(tab_btn)

        close_btn.clicked.connect(lambda: self.close_terminal_tab(tab_index))
        tab_btn.clicked.connect(lambda: self.switch_to_terminal_tab(tab_index))

        self.unified_header.add_tab(tab_container)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        terminal_widget = UnifiedTerminalWidget()
        terminal_widget.set_copy_paste_enabled(self.copy_paste_enabled)
        content_layout.addWidget(terminal_widget, 1)
        self.stack_layout.addWidget(content_widget)
        content_widget.setVisible(False)

        process = QProcess(self)
        process.readyReadStandardOutput.connect(lambda: self.handle_stdout(tab_index))
        process.readyReadStandardError.connect(lambda: self.handle_stderr(tab_index))
        process.finished.connect(lambda exit_code, exit_status: self.safe_handle_process_finished(tab_index, exit_code, exit_status))
        terminal_widget.commandEntered.connect(lambda cmd: self.execute_command(cmd, tab_index))

        terminal_data = {
            'tab_button': tab_btn,
            'tab_container': tab_container,
            'content_widget': content_widget,
            'terminal_widget': terminal_widget,
            'process': process,
            'shell': selected_shell,
            'started': False,
            'active': False
        }
        self.terminal_tabs.append(terminal_data)

        welcome_msg = (
            f"Kubernetes Terminal {tab_index + 1} ({os.path.basename(selected_shell)})\n"
            f"Working directory: {self.working_directory}\n"
            "--------------------\n"
            "Enter 'kubectl' commands to interact with your cluster.\n"
            "Type 'clear' to clear the terminal.\n\n"
        )
        terminal_widget.append_output(welcome_msg)
        terminal_widget.ensure_cursor_at_input()

        self.switch_to_terminal_tab(tab_index)
        if self.is_visible:
            self.start_terminal_process(tab_index)
        print(f"TerminalPanel: Added terminal tab {tab_index} with shell {selected_shell}, copy_paste_enabled={self.copy_paste_enabled}")
        return tab_index

    def safe_handle_process_finished(self, tab_index, exit_code, exit_status):
        if tab_index >= len(self.terminal_tabs):
            return
        terminal_data = self.terminal_tabs[tab_index]
        terminal_widget = terminal_data.get('terminal_widget')
        if not terminal_widget or not terminal_widget.is_valid:
            return
        try:
            if exit_status == QProcess.ExitStatus.CrashExit:
                terminal_widget.append_output("\nProcess crashed. Restarting...\n", "#FF6B68")
                QTimer.singleShot(1000, lambda: self.start_terminal_process(tab_index))
            elif exit_code != 0:
                terminal_widget.append_output(f"\nProcess exited with code {exit_code}. Restarting...\n", "#FFA500")
                QTimer.singleShot(1000, lambda: self.start_terminal_process(tab_index))
            else:
                terminal_widget.append_output("\nProcess exited normally.\n")
                terminal_widget.append_prompt()
        except Exception as e:
            print(f"Error in handle_process_finished: {e}")

    def start_terminal_process(self, tab_index=None):
        tab_index = tab_index if tab_index is not None else self.active_terminal_index
        if tab_index >= len(self.terminal_tabs):
            return
        terminal_data = self.terminal_tabs[tab_index]
        process = terminal_data.get('process')
        shell = terminal_data.get('shell')
        if process and process.state() == QProcess.ProcessState.NotRunning:
            if not shutil.which(shell):
                os_name = platform.system()
                shell = os.environ.get('SHELL', '/bin/bash') if os_name != 'Windows' else 'powershell.exe'
                terminal_data['shell'] = shell
                terminal_data['terminal_widget'].append_output(
                    f"\nShell {shell} not found. Falling back to {shell}\n", "#FFA500"
                )
                print(f"Shell {shell} not found, falling back to {shell} for terminal {tab_index}")

            try:
                process.setWorkingDirectory(self.working_directory)
                process.start(shell)
                if process.waitForStarted(1000):
                    terminal_data['started'] = True
                    print(f"Started {shell} for terminal {tab_index} in {self.working_directory}")
                else:
                    terminal_data['terminal_widget'].append_output(
                        f"\nFailed to start {shell}. Ensure it is installed and in PATH.\n", "#FF6B68"
                    )
                    print(f"Failed to start {shell} for terminal {tab_index}")
            except Exception as e:
                terminal_data['terminal_widget'].append_output(
                    f"\nError starting {shell}: {str(e)}\n", "#FF6B68"
                )
                print(f"Error starting {shell} for terminal {tab_index}: {e}")

    def execute_command(self, command, tab_index=None):
        tab_index = tab_index if tab_index is not None else self.active_terminal_index
        if tab_index >= len(self.terminal_tabs):
            return
        terminal_data = self.terminal_tabs[tab_index]
        terminal_widget = terminal_data.get('terminal_widget')
        process = terminal_data.get('process')
        if not terminal_widget or not terminal_widget.is_valid or not process:
            return

        command_lower = command.strip().lower()
        if command_lower == CommandConstants.CLEAR.value:
            terminal_widget.clear_output()
            return
        if command_lower in (CommandConstants.EXIT.value, CommandConstants.QUIT.value):
            if len(self.terminal_tabs) > 1:
                self.close_terminal_tab(tab_index)
            else:
                self.hide_terminal()
            return

        if process.state() == QProcess.ProcessState.NotRunning:
            self.start_terminal_process(tab_index)
        if process.state() == QProcess.ProcessState.Running:
            newline = b"\r\n" if platform.system() == 'Windows' else b"\n"
            process.write((command + newline.decode()).encode())

    def handle_stdout(self, tab_index=None):
        tab_index = tab_index if tab_index is not None else self.active_terminal_index
        if tab_index >= len(self.terminal_tabs):
            return
        terminal_data = self.terminal_tabs[tab_index]
        terminal_widget = terminal_data.get('terminal_widget')
        process = terminal_data.get('process')
        if terminal_widget and terminal_widget.is_valid and process:
            text = process.readAllStandardOutput().data().decode('utf-8', errors='replace')
            terminal_widget.append_output(text)

    def handle_stderr(self, tab_index=None):
        tab_index = tab_index if tab_index is not None else self.active_terminal_index
        if tab_index >= len(self.terminal_tabs):
            return
        terminal_data = self.terminal_tabs[tab_index]
        terminal_widget = terminal_data.get('terminal_widget')
        process = terminal_data.get('process')
        if terminal_widget and terminal_widget.is_valid and process:
            text = process.readAllStandardError().data().decode('utf-8', errors='replace')
            terminal_widget.append_output(text, "#FF6B68")

    def switch_to_terminal_tab(self, tab_index):
        if tab_index >= len(self.terminal_tabs):
            return

        # Update header based on tab type
        terminal_data = self.terminal_tabs[tab_index]
        is_logs_tab = terminal_data.get('is_logs_tab', False)
        is_ssh_tab = terminal_data.get('is_ssh_tab', False)

        # Update header for different tab types
        if is_logs_tab:
            self.unified_header.update_header_for_tab_type(True)
        elif is_ssh_tab:
            self.unified_header.update_header_for_ssh_tab()
        else:
            self.unified_header.update_header_for_tab_type(False)

        for i, tab_data in enumerate(self.terminal_tabs):
            tab_data['content_widget'].setVisible(i == tab_index)
            tab_data['tab_button'].setChecked(i == tab_index)
            tab_data['active'] = i == tab_index

        if terminal_widget := terminal_data.get('terminal_widget'):
            terminal_widget.setFocus()
            if hasattr(terminal_widget, 'ensure_cursor_at_input'):
                terminal_widget.ensure_cursor_at_input()
        elif logs_viewer := terminal_data.get('logs_viewer'):
            logs_viewer.setFocus()

        self.active_terminal_index = tab_index
        if not terminal_data.get('started', False) and not is_logs_tab and not is_ssh_tab:
            self.start_terminal_process(tab_index)

    def close_terminal_tab(self, tab_index):
        if tab_index >= len(self.terminal_tabs):
            return
        if len(self.terminal_tabs) <= 1:
            self.hide_terminal()
            return

        terminal_data = self.terminal_tabs[tab_index]
        # Handle different tab types
        if terminal_data.get('is_logs_tab', False):
            # Stop log streaming for logs tabs
            logs_viewer = terminal_data.get('logs_viewer')
            if logs_viewer and hasattr(logs_viewer, 'stop_log_stream'):
                logs_viewer.stop_log_stream()
        elif terminal_data.get('is_ssh_tab', False):
            # Cleanup SSH session for SSH tabs
            ssh_terminal = terminal_data.get('terminal_widget')
            if ssh_terminal and hasattr(ssh_terminal, 'cleanup_ssh_session'):
                ssh_terminal.cleanup_ssh_session()
        else:
            # Handle regular terminal process
            if process := terminal_data.get('process'):
                if process.state() == QProcess.ProcessState.Running:
                    try:
                        newline = b"\r\n" if platform.system() == 'Windows' else b"\n"
                        process.write(b"exit" + newline)
                        process.waitForFinished(500)
                        if process.state() == QProcess.ProcessState.Running:
                            process.terminate()
                            process.waitForFinished(500)
                        if process.state() == QProcess.ProcessState.Running:
                            process.kill()
                            process.waitForFinished(200)
                    except Exception as e:
                        print(f"Error terminating process: {e}")

        if tab_container := terminal_data.get('tab_container'):
            self.unified_header.remove_tab(tab_container)
        if content_widget := terminal_data.get('content_widget'):
            self.stack_layout.removeWidget(content_widget)
            content_widget.deleteLater()

        self.terminal_tabs.pop(tab_index)
        self.active_terminal_index = min(max(0, self.active_terminal_index), len(self.terminal_tabs) - 1)

        for i, tab_data in enumerate(self.terminal_tabs):
            if tab_container := tab_data.get('tab_container'):
                for child in tab_container.findChildren(QPushButton):
                    if child.text() == "✕":
                        try:
                            child.clicked.disconnect()
                        except TypeError:
                            pass
                        child.clicked.connect(lambda checked=False, idx=i: self.close_terminal_tab(idx))

        if self.terminal_tabs:
            self.switch_to_terminal_tab(self.active_terminal_index)
        self.renumber_tabs()

    def clear_active_terminal(self):
        if self.active_terminal_index < len(self.terminal_tabs):
            if terminal_widget := self.terminal_tabs[self.active_terminal_index].get('terminal_widget'):
                if terminal_widget.is_valid:
                    terminal_widget.clear_output()

    def restart_active_terminal(self):
        if self.active_terminal_index >= len(self.terminal_tabs):
            return
        terminal_data = self.terminal_tabs[self.active_terminal_index]

        # Only restart regular terminals, not logs tabs
        if terminal_data.get('is_logs_tab', False):
            # For logs tabs, refresh the logs instead
            logs_viewer = terminal_data.get('logs_viewer')
            if logs_viewer and hasattr(logs_viewer, 'refresh_logs'):
                logs_viewer.refresh_logs()
            return

        process = terminal_data.get('process')
        terminal_widget = terminal_data.get('terminal_widget')
        if not process or not terminal_widget or not terminal_widget.is_valid:
            return

        if process.state() == QProcess.ProcessState.Running:
            newline = b"\r\n" if platform.system() == 'Windows' else b"\n"
            process.write(b"exit" + newline)
            process.waitForFinished(500)
            if process.state() == QProcess.ProcessState.Running:
                process.terminate()
                process.waitForFinished(500)
            if process.state() == QProcess.ProcessState.Running:
                process.kill()
                process.waitForFinished(200)

        terminal_widget.clear_output()
        QTimer.singleShot(300, lambda: self.start_terminal_process(self.active_terminal_index))
        terminal_widget.append_output("Terminal restarted.\n")
        terminal_widget.ensure_cursor_at_input()

    def renumber_tabs(self):
        for i, tab_data in enumerate(self.terminal_tabs):
            if tab_container := tab_data.get('tab_container'):
                for child in tab_container.findChildren(QLabel):
                    if not tab_data.get('is_logs_tab', False):
                        child.setText(f"Terminal {i + 1}")
                    # For logs tabs, keep the original label (pod name)
                    break

    def toggle_terminal(self):
        self.hide_terminal() if self.is_visible else self.show_terminal()

    def show_terminal(self):
        if self.is_visible:
            return
        self.get_sidebar_width()
        self.reposition()
        if self.terminal_tabs and self.active_terminal_index < len(self.terminal_tabs):
            terminal_data = self.terminal_tabs[self.active_terminal_index]
            if not terminal_data.get('is_logs_tab', False):
                self.start_terminal_process(self.active_terminal_index)
        self.show()
        self.is_visible = True

        # Set focus based on tab type
        if self.terminal_tabs and self.active_terminal_index < len(self.terminal_tabs):
            terminal_data = self.terminal_tabs[self.active_terminal_index]
            if terminal_data.get('is_logs_tab', False):
                logs_viewer = terminal_data.get('logs_viewer')
                if logs_viewer:
                    logs_viewer.setFocus()
            else:
                terminal_widget = terminal_data.get('terminal_widget')
                if terminal_widget:
                    terminal_widget.setFocus()

    def get_sidebar_width(self):
        self.sidebar_width = getattr(getattr(self.parent_window, 'cluster_view', None), 'sidebar', None).width() if hasattr(self.parent_window, 'cluster_view') else 0
        return self.sidebar_width

    def hide_terminal(self):
        if self.is_visible:
            self.hide()
            self.is_visible = False
            self.terminate_all_processes()

    def toggle_maximize(self):
        self.is_maximized = not self.is_maximized
        top_level_window = self.window()
        if self.is_maximized:
            self.normal_height = self.height()
            max_height = top_level_window.height() - 50 if top_level_window else 1030
            self.setFixedHeight(int(max_height))
            self.unified_header.maximize_btn.setIcon(QIcon("icons/terminal_up_down.svg"))
            self.unified_header.maximize_btn.setToolTip("Restore Terminal")
        else:
            self.setFixedHeight(self.normal_height)
            self.unified_header.maximize_btn.setIcon(QIcon("icons/terminal_up_down.svg"))
            self.unified_header.maximize_btn.setToolTip("Maximize Terminal")
        self.reposition()

    def reposition(self):
        top_level_window = self.window()
        if top_level_window:
            parent_width = top_level_window.width()
            parent_height = top_level_window.height()
            if self.sidebar_width == 0:
                self.get_sidebar_width()
            terminal_width = max(parent_width - self.sidebar_width, 300)
            self.setFixedWidth(terminal_width)
            self.move(self.sidebar_width, parent_height - self.height())
            self.raise_()

    def animate_position(self, start_x, end_x):
        self.position_animation = QPropertyAnimation(self, b"pos")
        self.position_animation.setDuration(200)
        self.position_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.position_animation.valueChanged.connect(lambda value: self.update_width_with_sidebar(value.x()))
        self.position_animation.setStartValue(QPoint(start_x, self.y()))
        self.position_animation.setEndValue(QPoint(end_x, self.y()))
        self.position_animation.start()

    def update_width_with_sidebar(self, sidebar_width):
        top_level_window = self.window()
        if top_level_window:
            self.sidebar_width = sidebar_width
            self.setFixedWidth(max(top_level_window.width() - sidebar_width, 300))
            self.move(self.sidebar_width, top_level_window.height() - self.height())
            self.raise_()

    def download_terminal_output(self):
        if self.active_terminal_index >= len(self.terminal_tabs):
            return

        terminal_data = self.terminal_tabs[self.active_terminal_index]

        # Handle different tab types
        if terminal_data.get('is_logs_tab', False):
            # Download logs
            logs_viewer = terminal_data.get('logs_viewer')
            if logs_viewer:
                self.unified_header._download_logs(logs_viewer)
        else:
            # Download terminal output
            terminal_widget = terminal_data.get('terminal_widget')
            if not terminal_widget or not terminal_widget.is_valid:
                return

            file_name, _ = QFileDialog.getSaveFileName(self, "Save Terminal Output", "", "Text Files (*.txt);;All Files (*)")
            if file_name:
                try:
                    with open(file_name, 'w', encoding='utf-8') as f:
                        f.write(terminal_widget.toPlainText())
                    terminal_widget.append_output(f"\nTerminal output saved to {file_name}\n", "#4CAF50")
                except Exception as e:
                    terminal_widget.append_output(f"\nError saving terminal output: {str(e)}\n", "#FF6B68")

    def create_enhanced_logs_tab(self, pod_name, namespace):
        """Create an enhanced logs tab with search functionality moved to terminal header"""
        try:
            # Check if a logs tab for this pod already exists
            logs_tab_name = f"Logs: {pod_name}"
            existing_tab_index = None

            for i, tab_data in enumerate(self.terminal_tabs):
                if tab_data.get('is_logs_tab') and tab_data.get('pod_name') == pod_name:
                    existing_tab_index = i
                    break

            if existing_tab_index is not None:
                # Switch to existing logs tab and refresh
                self.switch_to_terminal_tab(existing_tab_index)
                logs_viewer = self.terminal_tabs[existing_tab_index].get('logs_viewer')
                if logs_viewer:
                    logs_viewer.refresh_logs()
            else:
                # Create new enhanced logs tab
                new_tab_index = self._create_new_enhanced_logs_tab(logs_tab_name, pod_name, namespace)
                if new_tab_index is not None:
                    self.switch_to_terminal_tab(new_tab_index)

        except Exception as e:
            logging.error(f"Error creating enhanced logs tab for {pod_name}: {e}")

    def _create_new_enhanced_logs_tab(self, tab_name, pod_name, namespace):
        """Create a new enhanced logs tab"""
        try:
            tab_index = len(self.terminal_tabs)

            # Create tab widget
            tab_widget = QWidget()
            tab_widget.setFixedHeight(28)
            tab_widget.setCursor(Qt.CursorShape.PointingHandCursor)

            tab_layout = QHBoxLayout(tab_widget)
            tab_layout.setContentsMargins(8, 0, 8, 0)
            tab_layout.setSpacing(6)

            # Create label with enhanced logs icon and name
            label = QLabel(f"📋 {pod_name}")
            label.setStyleSheet("""
                color: #4CAF50;
                background: transparent;
                font-size: 12px;
                font-weight: bold;
                text-decoration: none;
                border: none;
                outline: none;
            """)

            # Create close button
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(16, 16)
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setStyleSheet(StyleConstants.TAB_CLOSE_BUTTON)

            tab_layout.addWidget(label)
            tab_layout.addWidget(close_btn)

            # Create tab button
            tab_btn = QPushButton()
            tab_btn.setCheckable(True)
            tab_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-right: 1px solid #3d3d3d;
                    border-left: 1px solid #3d3d3d;
                    border-bottom: 1px solid #3d3d3d;
                    border-top: 1px solid #3d3d3d;
                    padding: 0px 35px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(76, 175, 80, 0.1);
                }
                QPushButton:checked {
                    background-color: #1E1E1E;
                    border-bottom: 2px solid #4CAF50;
                }
            """)
            tab_btn.setLayout(tab_layout)

            # Create tab container
            tab_container = QWidget()
            container_layout = QHBoxLayout(tab_container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)
            container_layout.addWidget(tab_btn)

            # Connect signals
            close_btn.clicked.connect(lambda: self.close_terminal_tab(tab_index))
            tab_btn.clicked.connect(lambda: self.switch_to_terminal_tab(tab_index))

            # Add tab to header
            self.unified_header.add_tab(tab_container)

            # Create enhanced logs viewer widget
            logs_viewer = EnhancedLogsViewer(pod_name, namespace)

            # Add the logs viewer to terminal stack
            self.stack_layout.addWidget(logs_viewer)
            logs_viewer.setVisible(False)

            # Store tab data with enhanced information
            terminal_data = {
                'tab_button': tab_btn,
                'tab_container': tab_container,
                'content_widget': logs_viewer,  # Use logs_viewer as content
                'logs_viewer': logs_viewer,     # Direct reference to logs viewer
                'terminal_widget': None,        # No terminal widget for logs tabs
                'process': None,                # No process for logs tabs
                'started': True,                # Always "started" for logs
                'active': False,
                'is_logs_tab': True,           # Mark as enhanced logs tab
                'pod_name': pod_name,
                'namespace': namespace
            }
            self.terminal_tabs.append(terminal_data)

            return tab_index

        except Exception as e:
            logging.error(f"Error creating new enhanced logs tab: {e}")
            return None

    def eventFilter(self, obj, event):
        return super().eventFilter(obj, event)
    def create_ssh_tab(self, pod_name, namespace):
        """Create an SSH tab for pod access"""
        try:
            tab_index = len(self.terminal_tabs)

            # Create tab widget
            tab_widget = QWidget()
            tab_widget.setFixedHeight(28)
            tab_widget.setCursor(Qt.CursorShape.PointingHandCursor)

            tab_layout = QHBoxLayout(tab_widget)
            tab_layout.setContentsMargins(8, 0, 8, 0)
            tab_layout.setSpacing(6)

            # Create label with SSH icon and pod name
            label = QLabel(f"🔑 {pod_name}")
            label.setStyleSheet("""
                color: #FF9800;
                background: transparent;
                font-size: 12px;
                font-weight: bold;
                text-decoration: none;
                border: none;
                outline: none;
            """)

            # Create close button
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(16, 16)
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setStyleSheet(StyleConstants.TAB_CLOSE_BUTTON)

            tab_layout.addWidget(label)
            tab_layout.addWidget(close_btn)

            # Create tab button
            tab_btn = QPushButton()
            tab_btn.setCheckable(True)
            tab_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-right: 1px solid #3d3d3d;
                    border-left: 1px solid #3d3d3d;
                    border-bottom: 1px solid #3d3d3d;
                    border-top: 1px solid #3d3d3d;
                    padding: 0px 35px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 152, 0, 0.1);
                }
                QPushButton:checked {
                    background-color: #1E1E1E;
                    border-bottom: 2px solid #FF9800;
                }
            """)
            tab_btn.setLayout(tab_layout)

            # Create tab container
            tab_container = QWidget()
            container_layout = QHBoxLayout(tab_container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)
            container_layout.addWidget(tab_btn)

            # Connect signals
            close_btn.clicked.connect(lambda: self.close_terminal_tab(tab_index))
            tab_btn.clicked.connect(lambda: self.switch_to_terminal_tab(tab_index))

            # Add tab to header
            self.unified_header.add_tab(tab_container)

            # Create SSH terminal widget
            ssh_terminal = SSHTerminalWidget(pod_name, namespace)

            # Add the SSH terminal to terminal stack
            self.stack_layout.addWidget(ssh_terminal)
            ssh_terminal.setVisible(False)

            # Store tab data
            terminal_data = {
                'tab_button': tab_btn,
                'tab_container': tab_container,
                'content_widget': ssh_terminal,
                'terminal_widget': ssh_terminal,  # SSH terminal acts as regular terminal
                'ssh_session': ssh_terminal.ssh_session,  # Direct reference to SSH session
                'process': None,                # No process for SSH tabs
                'started': True,                # Always "started" for SSH
                'active': False,
                'is_ssh_tab': True,            # Mark as SSH tab
                'pod_name': pod_name,
                'namespace': namespace
            }
            self.terminal_tabs.append(terminal_data)

            return tab_index

        except Exception as e:
            logging.error(f"Error creating SSH tab: {e}")
            return None
