"""
Terminal Panel - Refactored from large monolithic file

This module contains the main TerminalPanel class which manages multiple terminal types
including regular terminals, SSH sessions, and log viewers.
"""

import os
import platform  
import shutil
import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QLabel, QPushButton
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer, QProcess

from UI.Styles import AppColors, AppStyles
from UI.Icons import resource_path
from .terminal.terminal_constants import CommandConstants, StyleConstants
from .terminal.terminal_widget import UnifiedTerminalWidget
from .terminal.ssh_terminal_widget import SSHTerminalWidget
from .terminal.terminal_components import UnifiedTerminalHeader
from .terminal.logs_components import EnhancedLogsViewer


class TerminalPanel(QWidget):
    """
    Main terminal panel widget that manages multiple terminal tabs.
    
    This panel provides a unified interface for managing terminal tabs,
    including regular terminals, SSH sessions, and log viewers.
    """

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

    def reset_all_tabs(self):
        """Reset terminal panel to fresh state with only one terminal tab"""
        try:
            # First terminate all processes
            self.terminate_all_processes()
            
            # Clear all widgets from stack layout
            while self.stack_layout.count():
                child = self.stack_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Clear all tabs from header
            self.unified_header.clear_all_tabs()
            
            # Reset tab data
            self.terminal_tabs.clear()
            self.active_terminal_index = 0
            
            # Add a fresh terminal tab
            self.add_terminal_tab()
            
        except Exception as e:
            logging.error(f"Error resetting terminal tabs: {e}")

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

        # Hide all tabs first, then show the selected one
        for i, tab_data in enumerate(self.terminal_tabs):
            is_selected = (i == tab_index)
            content_widget = tab_data.get('content_widget')
            tab_button = tab_data.get('tab_button')
            
            if content_widget:
                content_widget.setVisible(is_selected)
            if tab_button:
                tab_button.setChecked(is_selected)
            tab_data['active'] = is_selected

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
            self.reset_all_tabs()

    def toggle_maximize(self):
        self.is_maximized = not self.is_maximized
        top_level_window = self.window()
        if self.is_maximized:
            self.normal_height = self.height()
            max_height = top_level_window.height() - 50 if top_level_window else 1030
            self.setFixedHeight(int(max_height))
            self.unified_header.maximize_btn.setIcon(QIcon(resource_path("Icons/terminal_up_down.svg")))
            self.unified_header.maximize_btn.setToolTip("Restore Terminal")
        else:
            self.setFixedHeight(self.normal_height)
            self.unified_header.maximize_btn.setIcon(QIcon(resource_path("Icons/terminal_up_down.svg")))
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
            close_btn.setStyleSheet(AppStyles.TERMINAL_TAB_CLOSE_BUTTON)

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
            close_btn.setStyleSheet(AppStyles.TERMINAL_TAB_CLOSE_BUTTON)

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

            # Switch to the new SSH tab
            self.switch_to_terminal_tab(tab_index)

            return tab_index

        except Exception as e:
            logging.error(f"Error creating SSH tab: {e}")
            return None