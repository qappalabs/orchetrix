import os
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel,
    QToolButton, QSizePolicy, QFileDialog, QMenu
)
from PyQt6.QtGui import QAction, QColor, QTextCursor, QFont, QIcon, QTextCharFormat, QTextDocument
from PyQt6.QtCore import Qt, QProcess, QTimer, pyqtSignal, QSize, QEvent, QPropertyAnimation, QEasingCurve, QPoint
from datetime import datetime
from enum import Enum

from Styles import AppColors, AppStyles
from Icons import Icons

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
        self.font_size = 9  # Changed from 12 to 9 - default terminal font size
        self.font_family = "Consolas"
        self.copy_paste_enabled = False  # For copy-paste toggle
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
        """Enable or disable copy-paste functionality."""
        self.copy_paste_enabled = enabled
        print(f"UnifiedTerminalWidget.set_copy_paste_enabled: copy_paste_enabled={enabled}")

    def set_font(self, font_family, font_size=None):
        """Set the font family and size for the terminal"""
        print(f"UnifiedTerminalWidget.set_font: font_family={font_family}, font_size={font_size}")
        self.font_family = font_family
        if font_size is not None:
            self.font_size = max(6, min(int(font_size), 72))
            print(f"Updated font size to: {self.font_size}")

        new_font = QFont(self.font_family, self.font_size)
        self.setFont(new_font)

        # Preserve current content and cursor position
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
        """Update prompt with current working directory"""
        terminal_panel = self.parent()
        while terminal_panel and not isinstance(terminal_panel, TerminalPanel):
            terminal_panel = terminal_panel.parent()
        self.current_prompt = f"PS {terminal_panel.working_directory} > " if terminal_panel and hasattr(terminal_panel, 'working_directory') else "PS > "

    def append_output(self, text, color=None):
        """Append text to terminal with optional color"""
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
        """Append new prompt"""
        self.update_prompt_with_working_directory()
        self.append_output(self.current_prompt)
        self.input_position = self.textCursor().position()

    def clear_output(self):
        """Clear terminal output and reset state"""
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
        """Position cursor at input area"""
        if not self.is_valid:
            return
        try:
            cursor = self.textCursor()
            cursor.setPosition(self.edit_start_pos if self.edit_mode and cursor.position() < self.edit_start_pos else
                              self.edit_end_pos if self.edit_mode and cursor.position() > self.edit_end_pos else
                              self.input_position)
            self.setTextCursor(cursor)
        except RuntimeError:
            self.is_valid = False

    def contextMenuEvent(self, event):
        """Customize context menu to respect copy_paste_enabled and edit_mode"""
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
        """Handle mouse press events for copy-paste and focus"""
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
        if self.copy_paste_enabled and event.button() == Qt.MouseButton.LeftButton:
            # Copy on selection
            cursor = self.textCursor()
            if cursor.hasSelection():
                clipboard = QApplication.clipboard()
                clipboard.setText(cursor.selectedText())
        self.ensure_cursor_at_input()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        event.accept()

    def keyPressEvent(self, event):
        """Handle key press events"""
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
        """Handle key events in edit mode"""
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
        """Navigate command history"""
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
        """Start file editing mode"""
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
        """Exit edit mode"""
        self.edit_mode = False
        self.edit_file_path = None
        self.edit_start_pos = self.edit_end_pos = 0
        self.setReadOnly(True)
        self.append_prompt()
        self.ensure_cursor_at_input()

    def update_edit_positions(self):
        """Update edit mode position markers"""
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

class ResizeHandle(QWidget):
    """Resize handle for terminal header"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(5)
        self.setCursor(Qt.CursorShape.SizeVerCursor)
        self.setStyleSheet(StyleConstants.RESIZE_HANDLE)

class UnifiedTerminalHeader(QWidget):
    """Header and tabs bar for terminal panel"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_terminal = parent
        self.edit_mode = False
        self.current_file = None
        self.setup_ui()

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
        self.content_layout.setSpacing(0)

        self.tabs_container = QWidget()
        self.tabs_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(0)
        self.tabs_layout.addStretch()

        self.controls = QWidget()
        self.controls_layout = QHBoxLayout(self.controls)
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_layout.setSpacing(8)

        buttons = [
            ("icons/terminal_add.svg", "New Terminal", self.add_new_tab),
            ("icons/terminal_refresh.svg", "Refresh Terminal", self.refresh_terminal),
            ("icons/terminal_download.svg", "Download Terminal Output", self.download_terminal_output),
            ("💾", "save File", self.save_current_file),
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

    def create_header_button(self, text, tooltip, callback):
        button = QToolButton()
        if text.endswith('.svg'):
            button.setIcon(QIcon(text))
            button.setIconSize(QSize(10, 10))  # Set icon size to 10px
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
            self.parent_terminal.add_terminal_tab()

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
        self.refresh_btn.setIcon(QIcon("icons/Terminal_Refresh.svg"))
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
    """Terminal panel that slides up from the bottom"""
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
        self.resize_start_y = None
        self.original_height = None
        self.copy_paste_enabled = False  # Initialize as disabled
        self.setup_ui()
        self.add_terminal_tab()
        self.parent_window.installEventFilter(self)
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
        self.hide()

    def set_preferences(self, preferences):
        """Connect preferences signals to terminal panel"""
        self.preferences = preferences
        self.preferences.copy_paste_changed.connect(self.apply_copy_paste_to_terminals)
        self.preferences.font_changed.connect(self.apply_font_to_terminals)
        self.preferences.font_size_changed.connect(self.apply_font_size_to_terminals)
        print("TerminalPanel: Preferences set, connected copy_paste_changed, font_changed, and font_size_changed signals")
        # Note: Not applying initial copy-paste state due to missing current_copy_paste_enabled
        # Rely on copy_paste_changed signal for updates

    def apply_font_to_terminals(self, font_family):
        """Apply the selected font to all terminal widgets"""
        print(f"TerminalPanel.apply_font_to_terminals: font_family={font_family}")
        for terminal_data in self.terminal_tabs:
            terminal_widget = terminal_data.get('terminal_widget')
            if terminal_widget and terminal_widget.is_valid:
                terminal_widget.set_font(font_family)

    def apply_font_size_to_terminals(self, font_size):
        """Apply the selected font size to all terminal widgets"""
        print(f"TerminalPanel.apply_font_size_to_terminals: font_size={font_size}, terminals={len(self.terminal_tabs)}")
        for i, terminal_data in enumerate(self.terminal_tabs):
            terminal_widget = terminal_data.get('terminal_widget')
            if terminal_widget and terminal_widget.is_valid:
                print(f"Applying font size to terminal {i}")
                terminal_widget.set_font(terminal_widget.font_family, font_size)
            else:
                print(f"Terminal {i} is invalid or not found")

    def apply_copy_paste_to_terminals(self, enabled):
        """Apply copy-paste setting to all terminal widgets"""
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
        """Terminate all running terminal processes"""
        for terminal_data in self.terminal_tabs:
            process = terminal_data.get('process')
            if process and process.state() == QProcess.ProcessState.Running:
                try:
                    if sys.platform == 'win32':
                        process.write(b"exit\r\n")
                        process.waitForFinished(500)
                    else:
                        process.terminate()
                        if not process.waitForFinished(500):
                            process.kill()
                            process.waitForFinished(200)
                    print(f"Terminated process for terminal {terminal_data.get('tab_button').text()}")
                except Exception as e:
                    print(f"Error terminating process for terminal {terminal_data.get('tab_button').text()}: {e}")

    def add_terminal_tab(self):
        tab_index = len(self.terminal_tabs)

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
        terminal_widget.set_copy_paste_enabled(self.copy_paste_enabled)  # Explicitly set copy-paste state
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
            'started': False,
            'active': False
        }
        self.terminal_tabs.append(terminal_data)

        welcome_msg = (
            f"Kubernetes Terminal {tab_index + 1}\n"
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
        print(f"TerminalPanel: Added terminal tab {tab_index}, copy_paste_enabled={self.copy_paste_enabled}")
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
        if process and process.state() == QProcess.ProcessState.NotRunning:
            shell = 'powershell.exe' if sys.platform == 'win32' else os.environ.get('SHELL', '/bin/bash')
            process.start(shell)
            process.waitForStarted(1000)
            terminal_data['started'] = True

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
            process.write((command + "\n").encode())

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
        if process := terminal_data.get('process'):
            if process.state() == QProcess.ProcessState.Running:
                try:
                    process.terminate()
                    if not process.waitForFinished(500):
                        process.kill()
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
            process.terminate()
            if not process.waitForFinished(500):
                process.kill()

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

    def toggle_maximize(self):
        self.is_maximized = not self.is_maximized
        if self.is_maximized:
            self.normal_height = self.height()
            max_height = self.parent_window.height() - 50
            self.setFixedHeight(max_height)
            self.unified_header.maximize_btn.setIcon(QIcon("icons/terminal_up_down.svg"))
            self.unified_header.maximize_btn.setToolTip("Restore Terminal")
        else:
            self.setFixedHeight(self.normal_height)
            self.unified_header.maximize_btn.setIcon(QIcon("icons/terminal_up_down.svg"))
            self.unified_header.maximize_btn.setToolTip("Maximize Terminal")
        self.reposition()

    def reposition(self):
        if self.parent_window:
            parent_width = self.parent_window.width()
            parent_height = self.parent_window.height()
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
        if self.parent_window:
            self.sidebar_width = sidebar_width
            self.setFixedWidth(max(self.parent_window.width() - sidebar_width, 300))
            self.move(self.sidebar_width, self.parent_window.height() - self.height())
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
        if obj == self.unified_header.resize_handle and event.type() == QEvent.Type.MouseButtonPress:
            self.resize_start_y = event.globalPosition().y()
            self.original_height = self.height()
            return True
        elif obj == self.unified_header.resize_handle and event.type() == QEvent.Type.MouseMove and self.resize_start_y is not None:
            delta = self.resize_start_y - event.globalPosition().y()
            new_height = max(150, min(self.original_height + delta, self.parent_window.height() - 50))
            self.setFixedHeight(new_height)
            self.normal_height = new_height
            self.reposition()
            return True
        elif obj == self.unified_header.resize_handle and event.type() == QEvent.Type.MouseButtonRelease:
            self.resize_start_y = None
            self.original_height = None
            return True
        elif obj == self.parent_window and event.type() == QEvent.Type.Resize:
            if self.is_visible:
                self.reposition()
        return super().eventFilter(obj, event)