"""
Terminal widget components - Split from TerminalPanel.py

This module contains the UnifiedTerminalWidget class which provides
the core terminal functionality for input/output handling.
"""

import logging
from datetime import datetime
from PyQt6.QtWidgets import QTextEdit, QApplication, QMenu
from PyQt6.QtGui import QAction, QColor, QTextCursor, QFont, QTextCharFormat, QKeySequence
from PyQt6.QtCore import Qt, pyqtSignal

from UI.Styles import AppStyles
from Utils.kubernetes_client import get_kubernetes_client
from .terminal_constants import StyleConstants, CommandConstants


class UnifiedTerminalWidget(QTextEdit):
    """
    Unified terminal widget for input and output handling.
    
    This widget provides a terminal-like interface with command history,
    input validation, search functionality, and proper text formatting.
    Supports both regular terminal operations and edit mode for file editing.
    """
    
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
        """Initialize the UI components and styling."""
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont(self.font_family, self.font_size))
        self.setStyleSheet(StyleConstants.TERMINAL_TEXTEDIT)
        self.setAcceptRichText(False)

    def __del__(self):
        self.is_valid = False

    def set_copy_paste_enabled(self, enabled):
        """Enable or disable copy/paste functionality."""
        self.copy_paste_enabled = enabled
        print(f"UnifiedTerminalWidget.set_copy_paste_enabled: copy_paste_enabled={enabled}")

    def set_font(self, font_family, font_size=None):
        """
        Set the terminal font family and optionally the size.
        
        Args:
            font_family (str): The font family name
            font_size (int, optional): The font size (6-72 range)
        """
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
        """Update the terminal prompt to include the current working directory."""
        # Find the terminal panel parent to get working directory
        terminal_panel = self.parent()
        while terminal_panel and not hasattr(terminal_panel, 'working_directory'):
            terminal_panel = terminal_panel.parent()
        
        if terminal_panel and hasattr(terminal_panel, 'working_directory'):
            self.current_prompt = f"PS {terminal_panel.working_directory} > "
        else:
            self.current_prompt = "PS > "

    def append_output(self, text, color=None):
        """
        Append text output to the terminal with optional color formatting.
        
        Args:
            text (str): The text to append
            color (str, optional): Hex color code for the text
        """
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
        """Append a new command prompt to the terminal."""
        self.update_prompt_with_working_directory()
        self.append_output(self.current_prompt)
        self.input_position = self.textCursor().position()

    def clear_output(self):
        """Clear the terminal output and reset to initial state."""
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

            # Find terminal panel for working directory
            terminal_panel = self.parent()
            while terminal_panel and not hasattr(terminal_panel, 'working_directory'):
                terminal_panel = terminal_panel.parent()
            
            if terminal_panel and hasattr(terminal_panel, 'working_directory'):
                # Find terminal tab index for welcome message
                tab_index = 0
                if hasattr(terminal_panel, 'terminal_tabs'):
                    tab_index = next((i for i, tab_data in enumerate(terminal_panel.terminal_tabs) 
                                    if tab_data.get('terminal_widget') == self), 0)
                
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
        """Ensure the cursor is positioned at the input area."""
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
        """Create and show the context menu with terminal-specific actions."""
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
        """Get current search information from logs viewer."""
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
        """Get currently selected container."""
        try:
            logs_info = self._get_current_logs_info()
            if logs_info and hasattr(logs_info['logs_viewer'], 'current_container'):
                return logs_info['logs_viewer'].current_container
        except Exception as e:
            logging.error(f"Error getting current container: {e}")
        return None

    def _is_follow_enabled(self):
        """Check if follow mode is enabled."""
        try:
            logs_info = self._get_current_logs_info()
            if logs_info and hasattr(logs_info['logs_viewer'], 'follow_enabled'):
                return logs_info['logs_viewer'].follow_enabled
        except Exception as e:
            logging.error(f"Error checking follow mode: {e}")
        return False

    def _toggle_follow_mode(self):
        """Toggle follow mode."""
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
        """Clear search in logs viewer."""
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
        """Refresh logs for specific container."""
        logs_info = self._get_current_logs_info()
        if logs_info and hasattr(logs_info['logs_viewer'], 'set_container'):
            # Update the combo box
            if hasattr(logs_info['logs_viewer'], 'header'):
                logs_info['logs_viewer'].header.container_combo.setCurrentText(container_name)
            logs_info['logs_viewer'].set_container(container_name)

    def _refresh_logs_with_lines(self, tail_lines):
        """Refresh logs with specific number of lines."""
        logs_info = self._get_current_logs_info()
        if logs_info and hasattr(logs_info['logs_viewer'], 'set_tail_lines'):
            # Update the combo box
            if hasattr(logs_info['logs_viewer'], 'header'):
                logs_info['logs_viewer'].header.lines_combo.setCurrentText(str(tail_lines))
            logs_info['logs_viewer'].set_tail_lines(tail_lines)

    def _refresh_logs(self):
        """Refresh logs for current pod."""
        logs_info = self._get_current_logs_info()
        if logs_info and hasattr(logs_info['logs_viewer'], 'refresh_logs'):
            logs_info['logs_viewer'].refresh_logs()

    def _get_current_logs_info(self):
        """Get current logs tab information."""
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
        """Check if this terminal widget is in a logs tab."""
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
        """Get list of containers for the current pod."""
        try:
            logs_info = self._get_current_logs_info()
            if not logs_info:
                return []

            # Get containers from the logs viewer header
            if (hasattr(logs_info['logs_viewer'], 'header') and
                    hasattr(logs_info['logs_viewer'].header, 'containers')):
                return logs_info['logs_viewer'].header.containers

            # Fallback: Get containers directly from Kubernetes API
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
        """Handle mouse press events."""
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
        """Handle mouse move events - allow default behavior for text selection."""
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        super().mouseReleaseEvent(event)
        # After releasing the mouse, ensure the cursor is in the right place
        # if no text has been selected.
        if not self.textCursor().hasSelection():
            self.ensure_cursor_at_input()

    def mouseDoubleClickEvent(self, event):
        """Handle double-click events - allow default behavior for word selection."""
        super().mouseDoubleClickEvent(event)

    def paste(self):
        """Custom paste implementation to protect read-only parts of the terminal."""
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
        """Handle keyboard input events."""
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
        """Handle keyboard input during edit mode."""
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
        """Handle command history navigation with up/down arrows."""
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
        """Get the current command text being typed."""
        return self.current_input

    def set_prompt(self, prompt):
        """Set the terminal prompt text."""
        self.current_prompt = prompt

    def start_edit_mode(self, file_path, file_content):
        """
        Start file editing mode.
        
        Args:
            file_path (str): Path to the file being edited
            file_content (str): Content of the file
        """
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
        """Exit file editing mode and return to normal terminal mode."""
        self.edit_mode = False
        self.edit_file_path = None
        self.edit_start_pos = self.edit_end_pos = 0
        self.setReadOnly(True)
        self.append_prompt()
        self.ensure_cursor_at_input()

    def search_in_terminal(self, search_text):
        """
        Non-destructive search and highlight text in terminal output.
        
        Args:
            search_text (str): Text to search for
        """
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
        """Clear search highlights while preserving other formatting."""
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
        """Update edit mode position markers after text changes."""
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