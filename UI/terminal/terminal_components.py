"""
Terminal components - Split from TerminalPanel.py

This module contains the ResizeHandle and UnifiedTerminalHeader classes
which provide UI components for terminal management and interaction.
"""

import os
import platform
import shutil
import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QSizePolicy, QLineEdit,
    QFileDialog, QComboBox, QLabel
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize

from UI.Styles import AppStyles, AppColors
from UI.Icons import resource_path
from .terminal_constants import StyleConstants


class ResizeHandle(QWidget):
    """
    Resize handle widget for terminal panel resizing.
    
    This widget provides a draggable handle that allows users to resize
    the terminal panel vertically by dragging.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(5)
        self.setCursor(Qt.CursorShape.SizeVerCursor)
        self.setStyleSheet(StyleConstants.RESIZE_HANDLE)
        self.is_dragging = False
        self.drag_start_y = 0
        self.drag_start_height = 0

    def mousePressEvent(self, event):
        """Handle mouse press events to start dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start_y = event.globalPosition().y()
            
            # Find the terminal panel parent
            terminal_panel = self.parent()
            while terminal_panel and not hasattr(terminal_panel, 'normal_height'):
                terminal_panel = terminal_panel.parent()
            
            self.terminal_panel = terminal_panel
            self.drag_start_height = terminal_panel.height() if terminal_panel else 0
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move events during dragging to resize terminal."""
        if self.is_dragging and self.terminal_panel:
            delta = self.drag_start_y - event.globalPosition().y()
            top_level_window = self.terminal_panel.window()
            parent_height = top_level_window.height() if top_level_window else 1080
            new_height = max(150, min(self.drag_start_height + delta, parent_height - 50))
            self.terminal_panel.setFixedHeight(int(new_height))
            self.terminal_panel.normal_height = int(new_height)
            if hasattr(self.terminal_panel, 'reposition'):
                self.terminal_panel.reposition()
            event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release events to stop dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.terminal_panel = None
            event.accept()


class UnifiedTerminalHeader(QWidget):
    """
    Unified header widget for terminal management.
    
    This widget provides the main interface for terminal operations including
    tab management, shell selection, search functionality, and various terminal actions.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_terminal = parent
        self.edit_mode = False
        self.current_file = None
        self.available_shells = self._detect_available_shells()
        self.selected_shell = self.available_shells[0][1] if self.available_shells else '/bin/bash'  # Store path only
        self.setup_ui()

    def _detect_available_shells(self):
        """
        Detect available shells on the system.
        
        Returns:
            list: List of tuples (display_name, shell_path)
        """
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
            
            # Also check system shells file
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

        # Remove default shell from list and add it at the beginning
        shells = [(name, path) for name, path in shells if path != default_shell]
        shells.insert(0, (os.path.basename(default_shell).capitalize(), default_shell))
        return shells

    def setup_ui(self):
        """Initialize the UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add resize handle
        self.resize_handle = ResizeHandle(self)
        main_layout.addWidget(self.resize_handle)

        # Header content
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
        self.shell_dropdown.setFixedSize(160, 24)
        self.shell_dropdown.setStyleSheet(StyleConstants.SHELL_DROPDOWN)
        self.shell_dropdown.setCursor(Qt.CursorShape.PointingHandCursor)

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
        """Update selected shell and create new terminal tab."""
        if index >= 0 and index < len(self.available_shells):
            self.selected_shell = self.available_shells[index][1]  # Store path only
            print(f"Selected shell updated to: {self.selected_shell}")
            # Automatically create a new terminal tab with the selected shell
            self.add_new_tab()

    def _on_search_changed(self, text):
        """Handle search text change for both terminal and logs tabs."""
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
        """Get the active terminal widget."""
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
        """Update header visibility based on tab type."""
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
            logging.error(f"Error updating header for tab type: {e}")
        return False

    def _is_active_tab_logs(self):
        """Check if the active tab is a logs tab."""
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
        """Get the active logs tab viewer."""
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
        """Update header for SSH tab."""
        try:
            self.search_input.setPlaceholderText("Search in SSH session...")
            self.shell_dropdown.setVisible(False)  # Hide shell dropdown for SSH

            # Update button tooltips
            self.refresh_btn.setToolTip("Reconnect SSH Session")
            self.download_btn.setToolTip("Download SSH Session Log")

        except Exception as e:
            logging.error(f"Error updating header for SSH tab: {e}")

    def refresh_terminal(self):
        """Refresh terminal, logs, or SSH based on active tab."""
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
        """Refresh/reconnect SSH session."""
        if self._is_active_tab_ssh():
            active_ssh = self._get_active_ssh_tab()
            if active_ssh and hasattr(active_ssh, 'init_ssh_session'):
                active_ssh.cleanup_ssh_session()
                active_ssh.init_ssh_session()

    def download_terminal_output(self):
        """Download terminal output, logs, or SSH session based on active tab."""
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
        """Download SSH session content."""
        try:
            # Get SSH session content
            if hasattr(ssh_terminal, 'toPlainText'):
                session_content = ssh_terminal.toPlainText()

                # Get pod name for filename
                pod_name = getattr(ssh_terminal, 'pod_name', 'unknown-pod')
                namespace = getattr(ssh_terminal, 'namespace', 'default')

                # Open file dialog
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
        """Check if the active tab is an SSH tab."""
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
        """Get the active SSH tab widget."""
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
        """Create a header button with icon or text."""
        button = QToolButton()
        if text.endswith('.svg'):
            button.setIcon(QIcon(resource_path(text)))
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
        """Add a new terminal tab."""
        if hasattr(self.parent_terminal, 'add_terminal_tab'):
            self.parent_terminal.add_terminal_tab(shell=self.selected_shell)

    def enter_edit_mode(self, file_path):
        """Enter file editing mode."""
        self.edit_mode = True
        self.current_file = file_path
        self.save_btn.show()
        self.refresh_btn.setText("✖")
        self.refresh_btn.setToolTip("Cancel Editing")
        if self._active_terminal_widget():
            self._active_terminal_widget().start_edit_mode(file_path, self.read_file_content(file_path))

    def read_file_content(self, file_path):
        """Read file content for editing."""
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            return f"# Error reading file: {str(e)}\n"

    def exit_edit_mode(self):
        """Exit file editing mode."""
        self.edit_mode = False
        self.current_file = None
        self.save_btn.hide()
        self.refresh_btn.setIcon(QIcon(resource_path("icons/terminal_refresh.svg")))
        self.refresh_btn.setToolTip("Refresh Terminal")
        if self._active_terminal_widget():
            self._active_terminal_widget().exit_edit_mode()

    def save_current_file(self):
        """Save the currently edited file."""
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

    def _download_logs(self, logs_viewer):
        """Download logs from logs viewer."""
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
        """Toggle terminal maximize/restore state."""
        if hasattr(self.parent_terminal, 'toggle_maximize'):
            self.parent_terminal.toggle_maximize()
            self.maximize_btn.setIcon(QIcon(resource_path("icons/terminal_up_down.svg")))
            self.maximize_btn.setToolTip("Restore Terminal" if self.parent_terminal.is_maximized else "Maximize Terminal")

    def hide_terminal(self):
        """Hide the terminal panel."""
        if hasattr(self.parent_terminal, 'hide_terminal'):
            self.parent_terminal.hide_terminal()

    def add_tab(self, tab_container):
        """Add a tab container to the tabs layout."""
        self.tabs_layout.insertWidget(self.tabs_layout.count() - 1, tab_container)

    def remove_tab(self, tab_container):
        """Remove a tab container from the tabs layout."""
        for i in range(self.tabs_layout.count()):
            if self.tabs_layout.itemAt(i).widget() == tab_container:
                widget = self.tabs_layout.takeAt(i).widget()
                widget.deleteLater()
                break

    def _active_terminal_widget(self):
        """Get the currently active terminal widget."""
        if self.parent_terminal and self.parent_terminal.active_terminal_index < len(self.parent_terminal.terminal_tabs):
            return self.parent_terminal.terminal_tabs[self.parent_terminal.active_terminal_index].get('terminal_widget')
        return None