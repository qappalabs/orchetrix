"""
SSH Terminal widget components - Split from TerminalPanel.py

This module contains the SSHTerminalWidget class which provides
specialized terminal functionality for SSH connections to pods.
"""

import logging
import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QKeySequence

from Utils.kubernetes_client import KubernetesPodSSH
from UI.ThemeAwarePage import ThemeAwareMixin
from .terminal_widget import UnifiedTerminalWidget
from .terminal_constants import StyleConstants


class SSHTerminalWidget(UnifiedTerminalWidget, ThemeAwareMixin):
    """
    Specialized terminal widget for SSH sessions with improved command handling.
    This widget extends UnifiedTerminalWidget to provide SSH-specific functionality
    including connection management, command execution, and proper input/output handling
    for remote shell sessions.
    """

    def __init__(self, pod_name, namespace, context=None, parent=None):
        """
        Initialize SSH terminal widget.
        Args:
            pod_name (str): Name of the Kubernetes pod to connect to
            namespace (str): Kubernetes namespace containing the pod
            context (str, optional): Kubernetes context to use for connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.pod_name = pod_name
        self.namespace = namespace
        self.context = context
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

    def _on_theme_changed(self, theme_name):
        """Handle theme changes - SSH terminal colors are intentionally fixed for consistency"""
        # SSH terminal uses fixed colors for status messages to maintain consistency
        # across themes, but we still call parent to handle search highlights
        super()._on_theme_changed(theme_name)

    def init_ssh_session(self):
        """Initialize the SSH session to the pod."""
        try:
            self.ssh_session = KubernetesPodSSH(
                self.pod_name, self.namespace, self.context
            )
            # Connect signals
            self.ssh_session.data_received.connect(self.handle_ssh_data)
            self.ssh_session.error_occurred.connect(self.handle_ssh_error)
            self.ssh_session.session_status.connect(self.handle_ssh_status)
            self.ssh_session.session_closed.connect(self.handle_ssh_closed)
            # Start connection
            if self.ssh_session.connect_to_pod():
                self.append_output(
                    f"🔄 Establishing SSH connection to {self.pod_name}...\n",
                    StyleConstants.get_ssh_success_color(),
                )
            else:
                self.append_output(
                    f"❌ Failed to connect to {self.pod_name}\n",
                    StyleConstants.get_ssh_error_color(),
                )
        except Exception as e:
            logging.error(f"Error initializing SSH session: {e}")
            self.append_output(
                f"SSH initialization error: {str(e)}\n",
                StyleConstants.get_ssh_error_color(),
            )

    def clean_terminal_output(self, data):
        """
        Clean terminal output by removing escape sequences and control characters.
        Args:
            data (str): Raw terminal data
        Returns:
            str: Cleaned terminal data
        """
        if not data:
            return ""
        # Remove ANSI escape sequences but preserve content
        # Remove cursor movement and color codes
        data = re.sub(
            r"\x1b\[[0-9;]*[mKJ]", "", data
        )  # m=color, K=erase line, J=erase display
        data = re.sub(r"\x1b\[[0-9;]*[ABCDEFGH]", "", data)
        # Remove bracketed paste mode sequences
        data = re.sub(r"\x1b\[?\?2004[hl]", "", data)
        # Remove other escape sequences
        data = re.sub(r"\x1b\][^\x07]*\x07", "", data)
        data = re.sub(r"\x1b[PX^_].*?\x1b\\", "", data)
        # Remove most control characters but keep newlines and tabs
        data = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", data)
        # Normalize line endings
        data = data.replace("\r\n", "\n").replace("\r", "\n")
        return data

    def is_shell_prompt(self, data):
        """
        Check if data contains a shell prompt.
        Args:
            data (str): Terminal data to check
        Returns:
            bool: True if data contains a shell prompt
        """
        if not data:
            return False
        # Look for common prompt patterns
        prompt_patterns = [
            r".*[$#%>]\s*$",  # Ends with shell prompt characters
            r".*@.*:.*[$#]\s*$",  # user@host:path$ format
            r".*have no name.*[$#]\s*$",  # "I have no name" prompt
        ]
        lines = data.strip().split("\n")
        last_line = lines[-1] if lines else ""
        for pattern in prompt_patterns:
            if re.match(pattern, last_line.strip()):
                return True
        return False

    def handle_ssh_data(self, data):
        """
        Handle data received from SSH session.
        Args:
            data (str): Data received from the SSH session
        """
        if not data or not self.is_valid:
            return
        # Check for ANSI clear screen sequences before any other processing
        if "\x1b[2J" in data or "\x1b[3J" in data:
            self.clear_output()
            # Remove the clear codes from the data string
            # so we can still process the prompt that might be attached
            data = re.sub(r"\x1b\[[23]J", "", data)
        # Clean the rest of the data
        clean_data = self.clean_terminal_output(data)
        if not clean_data:
            return
        # Show welcome message only once when we get the first prompt
        if (
            not self.welcome_shown
            and self.is_ssh_connected
            and self.is_shell_prompt(clean_data)
        ):
            if not self.initial_prompt_received:
                self._show_ssh_welcome()
                self.welcome_shown = True
                self.initial_prompt_received = True
        # Clear pending input display if we're showing output
        if self.pending_input and not self.is_shell_prompt(clean_data):
            self._clear_pending_input_display()
        # Display the output
        self.append_output(clean_data, StyleConstants.get_ssh_text_color())
        # Update positions
        cursor = self.textCursor()
        self.last_output_position = cursor.position()
        self.input_position = cursor.position()
        self.input_start_position = cursor.position()
        # After receiving output, allow input (don't rely solely on prompt detection)
        self.waiting_for_output = False
        # Redisplay pending input if any
        if self.pending_input:
            self._display_pending_input()

    def _clear_pending_input_display(self):
        """Clear the currently displayed pending input."""
        if not self.pending_input:
            return
        cursor = self.textCursor()
        cursor.setPosition(self.input_start_position)
        cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor)
        selected_text = cursor.selectedText()
        if self.pending_input in selected_text:
            cursor.removeSelectedText()
        cursor.setPosition(self.input_start_position)
        self.setTextCursor(cursor)

    def _display_pending_input(self):
        """Display the pending input."""
        if not self.pending_input or self.waiting_for_output:
            return
        cursor = self.textCursor()
        cursor.setPosition(self.input_start_position)
        self.setTextCursor(cursor)
        # Insert the pending input with proper formatting
        char_format = QTextCharFormat()
        char_format.setForeground(QColor(StyleConstants.get_ssh_text_color()))
        char_format.setBackground(self.terminal_bg_color)
        cursor.setCharFormat(char_format)
        cursor.insertText(self.pending_input)
        # Move cursor to end
        cursor.movePosition(cursor.MoveOperation.End)
        self.setTextCursor(cursor)

    def handle_ssh_error(self, error_message):
        """
        Handle SSH session errors.
        Args:
            error_message (str): Error message from SSH session
        """
        if self.is_valid:
            self.waiting_for_output = False  # Reset so echo works after errors
            self.append_output(
                f"\n❌ SSH Error: {error_message}\n",
                StyleConstants.get_ssh_error_color(),
            )

    def handle_ssh_status(self, status_message):
        """
        Handle SSH session status updates.
        Args:
            status_message (str): Status message from SSH session
        """
        if self.is_valid:
            if "Connected" in status_message:
                self.is_ssh_connected = True
                self.append_output(
                    f"✅ {status_message}\n", StyleConstants.get_ssh_success_color()
                )
                # Set initial positions
                cursor = self.textCursor()
                self.input_position = cursor.position()
                self.last_output_position = cursor.position()
                self.input_start_position = cursor.position()
            elif "Establishing" in status_message or "Failed" in status_message:
                self.append_output(
                    f"{status_message}\n",
                    StyleConstants.get_ssh_success_color()
                    if "Establishing" in status_message
                    else StyleConstants.get_ssh_error_color(),
                )

    def handle_ssh_closed(self):
        """Handle SSH session closure."""
        logging.debug(
            f"handle_ssh_closed called, is_valid={self.is_valid}, is_ssh_connected={self.is_ssh_connected}"
        )
        # Guard: only show message if still connected (prevents duplicate messages)
        if self.is_valid and self.is_ssh_connected:
            self.is_ssh_connected = False
            self.append_output(
                "\n🔴 SSH session closed\n", StyleConstants.get_ssh_warning_color()
            )
            self.append_output(
                "Connection to pod terminated.\n", StyleConstants.get_ssh_info_color()
            )

    def execute_ssh_command(self, command):
        """
        Execute command in SSH session.
        Args:
            command (str): Command to execute
        """
        if not self.ssh_session or not self.is_ssh_connected:
            self.append_output(
                "❌ Not connected to pod. Please check connection.\n",
                StyleConstants.get_ssh_error_color(),
            )
            return
        # Handle local exit commands
        command_lower = command.strip().lower()
        if command_lower in ["exit", "logout", "quit"]:
            self.ssh_session.disconnect()
            self.handle_ssh_closed()  # Direct call - bypasses Qt signal issue
            return
        # Handle clear command - use alternative if clear doesn't exist
        if command_lower == "clear":
            # Try multiple clear methods
            commands_to_try = ["clear", 'printf "\\033c"', "tput clear", "reset"]
            for cmd in commands_to_try:
                try:
                    success = self.ssh_session.send_command(cmd + "\n")
                    if success:
                        self.clear_output()  # Reset state locally after sending clear
                        return
                except Exception as e:
                    logging.debug(f"Clear command '{cmd}' failed: {e}")
                    continue
            # If all fail, do local clear
            self.clear_output()
            return
        # For all other commands
        try:
            if command.strip():
                self.waiting_for_output = (
                    True  # Only wait for output if there's actual content
                )
                success = self.ssh_session.send_command(command + "\n")
            else:
                # Empty Enter - don't block echo, just send newline
                success = self.ssh_session.send_command("\n")
            if not success:
                self.append_output(
                    "❌ Failed to send command to pod.\n",
                    StyleConstants.get_ssh_error_color(),
                )
                self.waiting_for_output = False
        except Exception as e:
            self.append_output(
                f"❌ Error sending command: {str(e)}\n",
                StyleConstants.get_ssh_error_color(),
            )
            self.waiting_for_output = False

    def keyPressEvent(self, event):
        """Handle key events for SSH terminal."""
        if not self.is_ssh_connected:
            # Still allow copy/paste even if not connected
            if event.matches(QKeySequence.StandardKey.Copy) or event.matches(
                QKeySequence.StandardKey.Paste
            ):
                super().keyPressEvent(event)
            else:
                event.accept()
            return
        key = event.key()
        # Allow copy/paste shortcuts to be handled by the parent
        if event.matches(QKeySequence.StandardKey.Copy) or event.matches(
            QKeySequence.StandardKey.Paste
        ):
            super().keyPressEvent(event)
            return
        # Handle Ctrl+C and Ctrl+D
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_C:
                try:
                    if self.ssh_session:
                        self.ssh_session.send_command("\x03")
                        self.waiting_for_output = False
                except Exception as e:
                    logging.debug(f"Error sending Ctrl+C: {e}")
                self._clear_all_pending_input()
                event.accept()
                return
            elif key == Qt.Key.Key_D:
                try:
                    if self.ssh_session:
                        self.ssh_session.send_command("\x04")
                except Exception as e:
                    logging.debug(f"Error sending Ctrl+D: {e}")
                self._clear_all_pending_input()
                event.accept()
                return
        # Handle Enter key
        if (
            key == Qt.Key.Key_Return
            and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            command_to_send = self.pending_input
            # Add to history if not empty
            if command_to_send.strip():
                self.command_history.append(command_to_send)
                self.history_index = len(self.command_history)
            # Clear pending input FIRST (this updates input_start_position)
            self._clear_all_pending_input()
            # THEN append command (so it won't be cleared)
            self.append_output(command_to_send + "\n")
            # Execute the command
            self.execute_ssh_command(command_to_send)
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
                    self.ssh_session.send_command("\t")
            except Exception as e:
                logging.debug(f"Error sending tab: {e}")
            event.accept()
            return
        event.accept()

    def _update_input_display(self):
        """Update the display to show current pending input."""
        if not self.is_valid or self.waiting_for_output:
            return
        # Clear current display from input start position
        cursor = self.textCursor()
        cursor.setPosition(self.input_start_position)
        cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        # Display the pending input if any
        if self.pending_input:
            cursor.setPosition(self.input_start_position)
            self.setTextCursor(cursor)
            char_format = QTextCharFormat()
            char_format.setForeground(QColor(StyleConstants.get_ssh_text_color()))
            char_format.setBackground(self.terminal_bg_color)
            cursor.setCharFormat(char_format)
            cursor.insertText(self.pending_input)
        # Position cursor at end
        cursor.movePosition(cursor.MoveOperation.End)
        self.setTextCursor(cursor)

    def _clear_all_pending_input(self):
        """Clear all pending input and reset state."""
        if self.pending_input:
            cursor = self.textCursor()
            cursor.setPosition(self.input_start_position)
            cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        self.pending_input = ""
        cursor = self.textCursor()
        self.input_start_position = cursor.position()

    def _show_ssh_welcome(self):
        """Show SSH welcome message once."""
        welcome_msg = (
            f"🔑 SSH Connected to Pod: {self.pod_name}\n"
            f"📍 Namespace: {self.namespace}\n"
            "────────────────────────────────────────\n"
            "✅ Shell session active. Type 'exit' to disconnect.\n"
            "💡 Note: Some containers may show 'I have no name' - this is normal.\n\n"
        )
        self.append_output(welcome_msg, StyleConstants.get_ssh_success_color())
        # Update positions after welcome
        cursor = self.textCursor()
        self.input_start_position = cursor.position()
        self.input_position = cursor.position()
        self.last_output_position = cursor.position()

    def _handle_ssh_history_navigation(self, key):
        """Handle command history navigation."""
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
        """Clean up SSH session."""
        try:
            if self.ssh_session:
                self.ssh_session.disconnect()
                self.ssh_session = None
        except Exception as e:
            logging.error(f"Error cleaning up SSH session: {e}")

    def clear_output(self):
        """Override clear_output for SSH terminal."""
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
                self.append_output(
                    "🧹 Terminal cleared\n", StyleConstants.get_ssh_success_color()
                )
                cursor = self.textCursor()
                self.input_start_position = cursor.position()
                self.input_position = cursor.position()
                self.last_output_position = cursor.position()
            else:
                self.append_output(
                    f"🔄 Connecting to {self.pod_name}...\n",
                    StyleConstants.get_ssh_success_color(),
                )
        except RuntimeError:
            self.is_valid = False

    def __del__(self):
        """Cleanup when widget is destroyed."""
        self.cleanup_ssh_session()
        super().__del__()
