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
        self.setStyleSheet(AppStyles.TERMINAL_TEXTEDIT)
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
            self.setTextColor(QColor(color or "#E0E0E0"))
            self.insertPlainText(text)
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
        menu = QMenu(self)

        copy_action = QAction("Copy", self)
        copy_action.setEnabled(self.textCursor().hasSelection())
        copy_action.triggered.connect(self.copy)
        menu.addAction(copy_action)

        paste_action = QAction("Paste", self)
        paste_action.setEnabled(self.copy_paste_enabled and not self.edit_mode and QApplication.clipboard().text() != "")
        paste_action.triggered.connect(self.paste)
        menu.addAction(paste_action)

        menu.addSeparator()

        clear_action = QAction("Clear", self)
        clear_action.triggered.connect(self.clear_output)
        menu.addAction(clear_action)

        menu.exec(event.globalPos())
        event.accept()
        print("UnifiedTerminalWidget: Context menu executed")

    def mousePressEvent(self, event):
        print(f"UnifiedTerminalWidget.mousePressEvent: copy_paste_enabled={self.copy_paste_enabled}, button={event.button()}, edit_mode={self.edit_mode}")
        self.setFocus()
        if event.button() == Qt.MouseButton.RightButton:
            if not self.copy_paste_enabled or self.edit_mode:
                print("UnifiedTerminalWidget: Right-click pasting blocked (copy_paste_enabled=False or edit_mode=True)")
                event.accept()
                return
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text:
                cursor = self.textCursor()
                if cursor.position() >= self.input_position:
                    self.insertPlainText(text)
                    self.current_input = self.toPlainText()[self.input_position:]
                    print(f"UnifiedTerminalWidget: Pasted text: {text[:50]}...")
            event.accept()
            return
        self.ensure_cursor_at_input()
        super().mousePressEvent(event)
        print("UnifiedTerminalWidget: Mouse event passed to super")

    def mouseMoveEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # After releasing the mouse, ensure the cursor is in the right place
        # if no text has been selected.
        if not self.textCursor().hasSelection():
            self.ensure_cursor_at_input()

    def mouseDoubleClickEvent(self, event):
        event.accept()

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        cursor_pos = cursor.position()
        key = event.key()

        if self.edit_mode:
            self._handle_edit_mode_keys(event, cursor, cursor_pos)
            return

        if cursor_pos < self.input_position and key not in {
            Qt.Key.Key_Home, Qt.Key.Key_End, Qt.Key.Key_Up, Qt.Key.Key_Down,
            Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown
        }:
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

        if key in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
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
        self.header_content.setStyleSheet(AppStyles.TERMINAL_HEADER_CONTENT)

        self.content_layout = QHBoxLayout(self.header_content)
        self.content_layout.setContentsMargins(8, 0, 16, 0)
        self.content_layout.setSpacing(4)

        self.tabs_container = QWidget()
        self.tabs_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(0)
        self.tabs_layout.addStretch()

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

        self.content_layout.addWidget(self.tabs_container, 1)
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
        button.setStyleSheet(AppStyles.TERMINAL_HEADER_BUTTON)
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
        if self.edit_mode:
            self.exit_edit_mode()
        if hasattr(self.parent_terminal, 'restart_active_terminal'):
            self.parent_terminal.restart_active_terminal()

    def download_terminal_output(self):
        if hasattr(self.parent_terminal, 'download_terminal_output'):
            self.parent_terminal.download_terminal_output()

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
        self.terminal_wrapper.setStyleSheet(AppStyles.TERMINAL_WRAPPER)

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
        label.setStyleSheet(AppStyles.TERMINAL_TAB_LABEL)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(16, 16)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(AppStyles.TERMINAL_TAB_CLOSE_BUTTON)

        tab_layout.addWidget(label)
        tab_layout.addWidget(close_btn)

        tab_btn = QPushButton()
        tab_btn.setCheckable(True)
        tab_btn.setStyleSheet(AppStyles.TERMINAL_TAB_BUTTON)
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
        for i, tab_data in enumerate(self.terminal_tabs):
            tab_data['content_widget'].setVisible(i == tab_index)
            tab_data['tab_button'].setChecked(i == tab_index)
            tab_data['active'] = i == tab_index
        terminal_data = self.terminal_tabs[tab_index]
        if terminal_widget := terminal_data.get('terminal_widget'):
            terminal_widget.setFocus()
            terminal_widget.ensure_cursor_at_input()
        self.active_terminal_index = tab_index
        if not terminal_data.get('started', False):
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
                    child.setText(f"Terminal {i + 1}")
                    break

    def toggle_terminal(self):
        self.hide_terminal() if self.is_visible else self.show_terminal()

    def show_terminal(self):
        if self.is_visible:
            return
        self.get_sidebar_width()
        self.reposition()
        if self.terminal_tabs and self.active_terminal_index < len(self.terminal_tabs):
            self.start_terminal_process(self.active_terminal_index)
        self.show()
        self.is_visible = True
        if terminal_widget := self.terminal_tabs[self.active_terminal_index].get('terminal_widget'):
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
        terminal_widget = self.terminal_tabs[self.active_terminal_index].get('terminal_widget')
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
