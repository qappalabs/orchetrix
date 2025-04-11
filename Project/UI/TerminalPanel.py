import os
import sys
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QSplitter, QFrame, QToolButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QProcess, QTimer, pyqtSignal, QSize, QEvent
from PyQt6.QtGui import QColor, QTextCursor, QFont, QIcon

from UI.Styles import AppColors, AppStyles
from UI.Icons import Icons

class TerminalOutputWidget(QTextEdit):
    """Custom QTextEdit widget for terminal output with custom styling"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.is_valid = True  # Flag to track widget validity

    def setup_ui(self):
        # Configure appearance
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont("Consolas", 10))

        # Terminal-like styling
        self.setStyleSheet(f"""
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
        """)

    # Override destructor to set flag
    def __del__(self):
        self.is_valid = False

    def append_output(self, text, color=None):
        """Append text to the terminal with optional color"""
        # Check if widget is still valid
        if not self.is_valid:
            return

        try:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)

            if color:
                self.setTextColor(QColor(color))
            else:
                self.setTextColor(QColor("#E0E0E0"))  # Default light color

            self.insertPlainText(text)

            # Auto-scroll to the end
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        except RuntimeError:
            # Widget has been deleted
            self.is_valid = False

    def clear_output(self):
        """Clear all terminal output"""
        if self.is_valid:
            try:
                self.clear()
            except RuntimeError:
                self.is_valid = False

class UnifiedTerminalWidget(QTextEdit):
    """Unified terminal widget that combines input and output in a single view"""

    # Signal emitted when a command is entered
    commandEntered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.command_history = []
        self.history_index = -1
        self.is_valid = True  # Flag to track widget validity
        self.current_prompt = "$ "
        self.input_position = 0  # Tracks where user input begins

        # Set initial prompt
        self.append_prompt()

    def setup_ui(self):
        # Configure appearance
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont("Consolas", 10))

        # Terminal-like styling
        self.setStyleSheet(f"""
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
        """)

    def __del__(self):
        """Override destructor to set flag"""
        self.is_valid = False

    def append_output(self, text, color=None):
        """Append output text to the terminal"""
        if not self.is_valid:
            return

        try:
            # Save the current cursor position
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)

            # Set text color
            if color:
                self.setTextColor(QColor(color))
            else:
                self.setTextColor(QColor("#E0E0E0"))  # Default light color

            # Insert the text
            self.insertPlainText(text)

            # Update input position
            self.input_position = self.textCursor().position()

            # Auto-scroll to the end
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        except RuntimeError:
            # Widget has been deleted
            self.is_valid = False

    def append_prompt(self):
        """Append a new prompt to the terminal"""
        self.append_output(self.current_prompt)
        self.input_position = self.textCursor().position()

    def clear_output(self):
        """Clear all terminal output"""
        if self.is_valid:
            try:
                self.clear()
                self.append_prompt()
            except RuntimeError:
                self.is_valid = False

    def keyPressEvent(self, event):
        """Handle key press events"""
        cursor = self.textCursor()
        cursor_pos = cursor.position()

        # Only allow editing after the input position
        if cursor_pos < self.input_position and event.key() not in [
            Qt.Key.Key_Home, Qt.Key.Key_End, Qt.Key.Key_Up, Qt.Key.Key_Down,
            Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown
        ]:
            # Move to the end for any input attempts
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)

        # Special handling for home key to go to start of input, not line
        if event.key() == Qt.Key.Key_Home:
            cursor.setPosition(self.input_position)
            self.setTextCursor(cursor)
            event.accept()
            return

        # Handle Enter key for command execution
        if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Get the current text and extract command
            all_text = self.toPlainText()
            command = all_text[self.input_position:].strip()

            if command:
                # Append a newline for visual separation
                self.append_output("\n")

                # Emit command entered signal
                self.commandEntered.emit(command)

                # Add to history
                self.command_history.append(command)
                self.history_index = len(self.command_history)
            else:
                # Just add a new prompt if no command
                self.append_output("\n")
                self.append_prompt()

            event.accept()
            return

        # Handle Up/Down keys for command history
        if event.key() == Qt.Key.Key_Up and self.command_history:
            if self.history_index > 0:
                # Clear current input
                cursor = self.textCursor()
                cursor.setPosition(self.input_position)
                cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()

                # Get previous command
                self.history_index -= 1
                previous_command = self.command_history[self.history_index]

                # Insert the previous command
                self.append_output(previous_command)
            event.accept()
            return

        if event.key() == Qt.Key.Key_Down and self.command_history:
            # Clear current input
            cursor = self.textCursor()
            cursor.setPosition(self.input_position)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()

            if self.history_index < len(self.command_history) - 1:
                # Get next command
                self.history_index += 1
                next_command = self.command_history[self.history_index]

                # Insert the next command
                self.append_output(next_command)
            elif self.history_index == len(self.command_history) - 1:
                # Clear input if we're at the end of history
                self.history_index = len(self.command_history)
            event.accept()
            return

        # Handle Backspace key - prevent deleting beyond input position
        if event.key() == Qt.Key.Key_Backspace and cursor.position() <= self.input_position:
            event.accept()
            return

        # Tab for auto-completion (not implemented, but could be added later)
        if event.key() == Qt.Key.Key_Tab:
            event.accept()
            return

        # Default behavior for other keys
        super().keyPressEvent(event)

    def get_current_command(self):
        """Get the current command text"""
        all_text = self.toPlainText()
        return all_text[self.input_position:].strip()

    def set_prompt(self, prompt):
        """Change the prompt string"""
        self.current_prompt = prompt

class TerminalInputWidget(QTextEdit):
    """Custom input widget for terminal commands"""

    # Signal emitted when Enter key is pressed
    commandEntered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.command_history = []
        self.history_index = -1

    def setup_ui(self):
        # Set to single line mode, though we use QTextEdit for better control
        self.setFixedHeight(30)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont("Consolas", 10))

        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: #252525;
                color: #E0E0E0;
                border: none;
                border-top: 1px solid #3D3D3D;
                padding: 5px 8px;
                selection-background-color: #264F78;
            }}
        """)

    def keyPressEvent(self, event):
        # Handle Enter key for command execution
        if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Get command text and emit signal
            command = self.toPlainText().strip()
            if command:
                self.commandEntered.emit(command)
                # Add to history
                self.command_history.append(command)
                self.history_index = len(self.command_history)
                # Clear input
                self.clear()
            event.accept()
            return

        # Handle Up/Down keys for command history
        if event.key() == Qt.Key.Key_Up and self.command_history:
            if self.history_index > 0:
                self.history_index -= 1
                self.setPlainText(self.command_history[self.history_index])
                self.moveCursor(QTextCursor.MoveOperation.End)
            event.accept()
            return

        if event.key() == Qt.Key.Key_Down and self.command_history:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.setPlainText(self.command_history[self.history_index])
                self.moveCursor(QTextCursor.MoveOperation.End)
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                self.clear()
            event.accept()
            return

        # Tab for auto-completion (not implemented, but could be added later)
        if event.key() == Qt.Key.Key_Tab:
            event.accept()
            return

        # Default behavior for other keys
        super().keyPressEvent(event)

class ResizeHandle(QWidget):
    """A dedicated resize handle for the terminal header"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Set fixed height for the handle
        self.setFixedHeight(5)

        # Set cursor and style
        self.setCursor(Qt.CursorShape.SizeVerCursor)

        # Style with a subtle visual indicator
        self.setStyleSheet("""
            background-color: rgba(80, 80, 80, 0.3);
            border: none;
        """)

class UnifiedTerminalHeader(QWidget):
    """Combined header and tabs bar for the terminal panel with dedicated resize handle"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_terminal = parent

        # We don't need these for the dedicated handle approach
        # self.setMouseTracking(True)
        # self.in_resize_area = False

        self.setup_ui()

    def setup_ui(self):
        """Set up the unified header UI with resize handle"""
        # Set up the main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create and add the resize handle at the top
        self.resize_handle = ResizeHandle(self)
        main_layout.addWidget(self.resize_handle)

        # Create the header content container
        self.header_content = QWidget()
        self.header_content.setFixedHeight(36)  # Header height
        self.header_content.setStyleSheet(f"""
            background-color: {AppColors.BG_DARKER};
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
        """)

        # Set up the horizontal layout for tabs and controls
        self.content_layout = QHBoxLayout(self.header_content)
        self.content_layout.setContentsMargins(8, 0, 16, 0)
        self.content_layout.setSpacing(0)

        # Tabs area - taking most of the space
        self.tabs_container = QWidget()
        self.tabs_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(0)
        self.tabs_layout.addStretch()

        # Control buttons container
        self.controls = QWidget()
        self.controls_layout = QHBoxLayout(self.controls)
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_layout.setSpacing(8)

        # Create control buttons
        self.new_tab_btn = self.create_header_button("+", "New Terminal",
                                                     self.add_new_tab)

        self.refresh_btn = self.create_header_button("⟳", "Refresh Terminal",
                                                     self.refresh_terminal)

        self.download_btn = self.create_header_button("↓", "Download Terminal Output",
                                                      self.download_terminal_output)

        self.maximize_btn = self.create_header_button("🔼", "Maximize/Restore Terminal",
                                                      self.toggle_maximize)

        self.close_btn = self.create_header_button("✕", "Hide Terminal Panel",
                                                   self.hide_terminal)

        # Add buttons to controls
        self.controls_layout.addWidget(self.new_tab_btn)
        self.controls_layout.addWidget(self.refresh_btn)
        self.controls_layout.addWidget(self.download_btn)
        self.controls_layout.addWidget(self.maximize_btn)
        self.controls_layout.addWidget(self.close_btn)

        # Add tabs and controls to the content layout
        self.content_layout.addWidget(self.tabs_container, 1)
        self.content_layout.addWidget(self.controls)

        # Add header content to main layout
        main_layout.addWidget(self.header_content)

    def create_header_button(self, text, tooltip, callback):
        """Create a header control button"""
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(28, 28)

        button.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                color: {AppColors.TEXT_SECONDARY};
                border: none;
                font-size: 12px;
                padding: 4px;
            }}
            QToolButton:hover {{
                background-color: {AppColors.HOVER_BG};
                color: {AppColors.TEXT_LIGHT};
                border-radius: 4px;
            }}
        """)

        button.clicked.connect(callback)
        return button

    def add_new_tab(self):
        """Add a new terminal tab - forwards to parent terminal panel"""
        if self.parent_terminal and hasattr(self.parent_terminal, 'add_terminal_tab'):
            self.parent_terminal.add_terminal_tab()

    def refresh_terminal(self):
        """Refresh the active terminal - forwards to parent terminal panel"""
        if self.parent_terminal and hasattr(self.parent_terminal, 'restart_active_terminal'):
            self.parent_terminal.restart_active_terminal()

    def download_terminal_output(self):
        """Download terminal output - forwards to parent terminal panel"""
        if self.parent_terminal and hasattr(self.parent_terminal, 'download_terminal_output'):
            self.parent_terminal.download_terminal_output()

    def toggle_maximize(self):
        """Toggle maximize state - forwards to parent terminal panel"""
        if self.parent_terminal and hasattr(self.parent_terminal, 'toggle_maximize'):
            self.parent_terminal.toggle_maximize()

    def hide_terminal(self):
        """Hide terminal panel - forwards to parent terminal panel"""
        if self.parent_terminal and hasattr(self.parent_terminal, 'hide_terminal'):
            self.parent_terminal.hide_terminal()

    def add_tab(self, tab_container):
        """Add a tab container to the tabs layout"""
        # Insert before the stretch
        self.tabs_layout.insertWidget(self.tabs_layout.count() - 1, tab_container)

    def remove_tab(self, tab_container):
        """Remove a tab container from the tabs layout"""
        for i in range(self.tabs_layout.count()):
            if self.tabs_layout.itemAt(i).widget() == tab_container:
                widget = self.tabs_layout.takeAt(i).widget()
                if widget:
                    widget.deleteLater()
                break

class TerminalPanel(QWidget):
    """A terminal panel that slides up from the bottom of the screen"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.processes = []  # List to store all terminal processes
        self.active_terminal_index = 0  # Index of currently active terminal
        self.is_visible = False
        self.is_maximized = False
        self.terminal_tabs = []  # List to store terminal tab data

        # Store sidebar width for positioning
        self.sidebar_width = 0

        self.setup_ui()

        # Add the first terminal tab
        self.add_terminal_tab()

        # Track window state changes
        self.parent_window.installEventFilter(self)

    def setup_ui(self):
        """Set up the terminal panel UI with unified header/tabs"""
        # Set initial hidden position off-screen
        self.setWindowFlags(Qt.WindowType.Widget | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Initial size - will be positioned in showEvent
        self.normal_height = 300  # Default terminal height
        self.setFixedHeight(self.normal_height)

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Create terminal wrapper that includes unified header and content
        self.terminal_wrapper = QWidget()
        self.terminal_wrapper.setObjectName("terminal_wrapper")
        self.terminal_wrapper.setStyleSheet(f"""
            QWidget#terminal_wrapper {{
                background-color: {AppColors.BG_DARKER};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-bottom: none;
            }}
        """)

        self.wrapper_layout = QVBoxLayout(self.terminal_wrapper)
        self.wrapper_layout.setContentsMargins(0, 0, 0, 0)
        self.wrapper_layout.setSpacing(0)

        # Create unified terminal header with tabs
        self.unified_header = UnifiedTerminalHeader(self)
        self.wrapper_layout.addWidget(self.unified_header)

        # Create content stack to hold terminal tabs
        self.terminal_stack = QWidget()
        self.stack_layout = QVBoxLayout(self.terminal_stack)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        self.stack_layout.setSpacing(0)

        self.wrapper_layout.addWidget(self.terminal_stack, 1)

        # Add wrapper to main layout
        self.main_layout.addWidget(self.terminal_wrapper)

        # Install event filter for resize handle - the important change
        self.unified_header.resize_handle.installEventFilter(self)
        # We still need the header event filter for other purposes
        self.unified_header.installEventFilter(self)

        # Hide initially
        self.hide()

    def closeEvent(self, event):
        """Handle proper cleanup when terminal is closed"""
        self.terminate_all_processes()
        super().closeEvent(event)

    def __del__(self):
        """Clean up processes when the panel is destroyed"""
        self.terminate_all_processes()

    def terminate_all_processes(self):
        """Terminate all running processes"""
        for terminal_data in self.terminal_tabs:
            process = terminal_data.get('process')
            if process and process.state() == QProcess.ProcessState.Running:
                try:
                    process.terminate()
                    if not process.waitForFinished(500):
                        process.kill()
                except Exception:
                    # Process might already be gone
                    pass

    def add_terminal_tab(self):
        """Add a new terminal tab with unified terminal widget"""
        # Create a tab index for the new terminal
        tab_index = len(self.terminal_tabs)

        # Create tab widget with integrated close button
        tab_widget = QWidget()
        tab_widget.setFixedHeight(28)
        tab_widget.setCursor(Qt.CursorShape.PointingHandCursor)

        # Layout for the tab widget
        tab_layout = QHBoxLayout(tab_widget)
        tab_layout.setContentsMargins(8, 0, 8, 0)
        tab_layout.setSpacing(6)

        # Tab label
        label = QLabel(f"Terminal {tab_index + 1}")
        label.setStyleSheet(f"""
            color: {AppColors.TEXT_SECONDARY}; 
            background: transparent;
            font-size: 12px;
            text-decoration: none;
            border: none;
            border-bottom: none;
            outline: none;      
        """)

        # Create close button for the tab
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(16, 16)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
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
        """)

        # Add widgets to tab layout
        tab_layout.addWidget(label)
        tab_layout.addWidget(close_btn)

        # Create clickable tab area
        tab_btn = QPushButton()
        tab_btn.setCheckable(True)
        tab_btn.setStyleSheet(f"""
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
        """)

        # Create tab container that has the button and the tab widget
        tab_container = QWidget()
        container_layout = QHBoxLayout(tab_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Add tab button (for selection) and widget (for content) to container
        container_layout.addWidget(tab_btn)
        tab_btn.setLayout(tab_layout)

        # Connect close button to close this specific tab using a closure to preserve index
        close_btn.clicked.connect(lambda checked=False, idx=tab_index: self.close_terminal_tab(idx))

        # Connect tab button for selection
        tab_btn.clicked.connect(lambda checked=False, idx=tab_index: self.switch_to_terminal_tab(idx))

        # Add tab to unified header instead of tabs_layout
        self.unified_header.add_tab(tab_container)

        # Create terminal content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Create unified terminal widget (replaces separate input and output widgets)
        terminal_widget = UnifiedTerminalWidget()

        content_layout.addWidget(terminal_widget, 1)

        # Add to stack but hide initially
        self.stack_layout.addWidget(content_widget)
        content_widget.setVisible(False)

        # Initialize process for this terminal
        process = QProcess(self)

        # Connect process signals
        process.readyReadStandardOutput.connect(
            lambda: self.handle_stdout(tab_index))
        process.readyReadStandardError.connect(
            lambda: self.handle_stderr(tab_index))

        # Use lambda with weak reference to avoid referencing deleted objects
        process.finished.connect(
            lambda exit_code, exit_status, tab=tab_index:
            self.safe_handle_process_finished(tab, exit_code, exit_status))

        # Connect command entered signal
        terminal_widget.commandEntered.connect(
            lambda cmd: self.execute_command(cmd, tab_index))

        # Start the process if terminal is visible
        if self.is_visible:
            self.start_terminal_process(tab_index)

        # Store terminal data
        terminal_data = {
            'tab_button': tab_btn,
            'tab_container': tab_container,
            'content_widget': content_widget,
            'terminal_widget': terminal_widget,  # Unified widget reference
            'process': process,
            'started': False,
            'active': False
        }

        self.terminal_tabs.append(terminal_data)

        # Show welcome message
        welcome_msg = f"Kubernetes Terminal {tab_index + 1}\n"
        welcome_msg += "--------------------\n"
        welcome_msg += "Enter 'kubectl' commands to interact with your cluster.\n"
        welcome_msg += "Type 'clear' to clear the terminal.\n\n"

        terminal_widget.append_output(welcome_msg)
        # No need to append prompt, the widget automatically adds it on creation

        # Switch to this tab
        self.switch_to_terminal_tab(tab_index)

        return tab_index


    def safe_handle_process_finished(self, tab_index, exit_code, exit_status):
        """Safely handle process termination avoiding deleted widget errors"""
        try:
            if tab_index < len(self.terminal_tabs):
                terminal_data = self.terminal_tabs[tab_index]
                terminal_widget = terminal_data.get('terminal_widget')

                if terminal_widget and terminal_widget.is_valid:
                    if exit_status == QProcess.ExitStatus.CrashExit:
                        terminal_widget.append_output(
                            "\nProcess crashed. Restarting terminal...\n", "#FF6B68")
                        QTimer.singleShot(1000, lambda: self.start_terminal_process(tab_index))
                    elif exit_code != 0:
                        terminal_widget.append_output(
                            f"\nProcess exited with code {exit_code}. Restarting terminal...\n", "#FFA500")
                        QTimer.singleShot(1000, lambda: self.start_terminal_process(tab_index))
                    else:
                        terminal_widget.append_output("\nProcess exited normally.\n")
                        terminal_widget.append_prompt()
        except Exception as e:
            print(f"Error in handle_process_finished: {e}")

    def start_terminal_process(self, tab_index=None):
        """Start the terminal process if not already running"""
        if tab_index is None:
            tab_index = self.active_terminal_index

        if tab_index >= len(self.terminal_tabs):
            return

        terminal_data = self.terminal_tabs[tab_index]
        process = terminal_data.get('process')

        if not process:
            return

        if process.state() == QProcess.ProcessState.NotRunning:
            # Use system shell
            if sys.platform == 'win32':
                # Windows
                shell = 'cmd.exe'
                process.start(shell)
            else:
                # Unix-like systems
                shell = os.environ.get('SHELL', '/bin/bash')
                process.start(shell)

            # Wait for process to start
            process.waitForStarted(1000)
            terminal_data['started'] = True

    def execute_command(self, command, tab_index=None):
        """Execute a terminal command"""
        if tab_index is None:
            tab_index = self.active_terminal_index

        if tab_index >= len(self.terminal_tabs):
            return

        terminal_data = self.terminal_tabs[tab_index]
        terminal_widget = terminal_data.get('terminal_widget')
        process = terminal_data.get('process')

        if not terminal_widget or not terminal_widget.is_valid or not process:
            return

        # Special case for 'clear' command
        if command.strip().lower() == "clear":
            terminal_widget.clear_output()
            return

        # Special case for 'exit' command
        if command.strip().lower() in ["exit", "quit"]:
            if len(self.terminal_tabs) > 1:
                self.close_terminal_tab(tab_index)
            else:
                self.hide_terminal()
            return

        # Make sure process is running
        if process.state() == QProcess.ProcessState.NotRunning:
            self.start_terminal_process(tab_index)

        # Execute command
        if process.state() == QProcess.ProcessState.Running:
            command_bytes = (command + "\n").encode()
            process.write(command_bytes)


    def handle_stdout(self, tab_index=None):
        """Handle standard output from process"""
        if tab_index is None:
            tab_index = self.active_terminal_index

        if tab_index >= len(self.terminal_tabs):
            return

        terminal_data = self.terminal_tabs[tab_index]
        terminal_widget = terminal_data.get('terminal_widget')
        process = terminal_data.get('process')

        if not terminal_widget or not terminal_widget.is_valid or not process:
            return

        data = process.readAllStandardOutput()
        text = bytes(data).decode('utf-8', errors='replace')
        terminal_widget.append_output(text)

    def handle_stderr(self, tab_index=None):
        """Handle standard error from process"""
        if tab_index is None:
            tab_index = self.active_terminal_index

        if tab_index >= len(self.terminal_tabs):
            return

        terminal_data = self.terminal_tabs[tab_index]
        terminal_widget = terminal_data.get('terminal_widget')
        process = terminal_data.get('process')

        if not terminal_widget or not terminal_widget.is_valid or not process:
            return

        data = process.readAllStandardError()
        text = bytes(data).decode('utf-8', errors='replace')
        # Show stderr in red
        terminal_widget.append_output(text, "#FF6B68")

    def handle_process_finished(self, tab_index, exit_code, exit_status):
        """Handle process termination"""
        if tab_index >= len(self.terminal_tabs):
            return

        terminal_data = self.terminal_tabs[tab_index]
        terminal_output = terminal_data.get('output_widget')

        if not terminal_output or not terminal_output.is_valid:
            return

        if exit_status == QProcess.ExitStatus.CrashExit:
            terminal_output.append_output(
                "\nProcess crashed. Restarting terminal...\n", "#FF6B68")
            QTimer.singleShot(1000, lambda: self.start_terminal_process(tab_index))
        elif exit_code != 0:
            terminal_output.append_output(
                f"\nProcess exited with code {exit_code}. Restarting terminal...\n", "#FFA500")
            QTimer.singleShot(1000, lambda: self.start_terminal_process(tab_index))
        else:
            terminal_output.append_output("\nProcess exited normally.\n$ ")

    def switch_to_terminal_tab(self, tab_index):
        """Switch to the specified terminal tab"""
        if tab_index >= len(self.terminal_tabs):
            return

        # Hide all tab content
        for i, tab_data in enumerate(self.terminal_tabs):
            tab_data['content_widget'].setVisible(False)
            tab_data['tab_button'].setChecked(False)
            tab_data['active'] = False

        # Show the selected tab
        terminal_data = self.terminal_tabs[tab_index]
        terminal_data['content_widget'].setVisible(True)
        terminal_data['tab_button'].setChecked(True)
        terminal_data['active'] = True

        # Focus the terminal widget
        if terminal_data.get('terminal_widget'):
            terminal_data['terminal_widget'].setFocus()

        # Update active index
        self.active_terminal_index = tab_index

        # Start process if needed
        if not terminal_data.get('started', False):
            self.start_terminal_process(tab_index)


    def close_terminal_tab(self, tab_index):
        """Close a terminal tab with unified header integration"""
        # Make sure the tab index is valid and we're not closing the last tab
        if tab_index >= len(self.terminal_tabs) or len(self.terminal_tabs) <= 1:
            # Don't close the last tab - show a message in the terminal instead
            if len(self.terminal_tabs) <= 1:
                terminal_data = self.terminal_tabs[0]
                output_widget = terminal_data.get('output_widget')
                if output_widget and output_widget.is_valid:
                    output_widget.append_output("\nCannot close the last terminal tab.\n", "#FFA500")
            return

        # Get tab data
        terminal_data = self.terminal_tabs[tab_index]

        # Terminate process if running
        process = terminal_data.get('process')
        if process and process.state() == QProcess.ProcessState.Running:
            try:
                process.terminate()
                # Force kill after a timeout
                if not process.waitForFinished(500):
                    process.kill()
            except Exception as e:
                print(f"Error terminating process: {e}")

        # Remove tab container from unified header instead of tabs_layout
        tab_container = terminal_data.get('tab_container')
        if tab_container:
            self.unified_header.remove_tab(tab_container)

        # Remove content widget from stack
        content_widget = terminal_data.get('content_widget')
        if content_widget:
            self.stack_layout.removeWidget(content_widget)
            content_widget.deleteLater()

        # Store the original tabs for reference
        original_tabs = self.terminal_tabs.copy()

        # Remove from list
        self.terminal_tabs.pop(tab_index)

        # Update active index if needed
        if self.active_terminal_index >= len(self.terminal_tabs):
            # If we removed the last tab, switch to the new last tab
            self.active_terminal_index = max(0, len(self.terminal_tabs) - 1)
        elif self.active_terminal_index == tab_index:
            # If we removed the active tab, stay at the same index (which is now a different tab)
            # unless it was the last tab
            self.active_terminal_index = min(self.active_terminal_index, len(self.terminal_tabs) - 1)

        # Update tab indices for close button callbacks
        for i, tab_data in enumerate(self.terminal_tabs):
            # Find the close button and update its callback
            tab_container = tab_data.get('tab_container')
            if tab_container:
                for child in tab_container.findChildren(QPushButton):
                    if child.text() == "✕":  # Identify close button by text
                        # Disconnect old connections and connect to new index
                        try:
                            child.clicked.disconnect()
                        except TypeError:
                            pass  # No connections to disconnect
                        child.clicked.connect(lambda checked=False, idx=i: self.close_terminal_tab(idx))

        # Switch to the active tab
        if self.terminal_tabs:
            self.switch_to_terminal_tab(self.active_terminal_index)

        # Update tab numbers
        self.renumber_tabs()

    def clear_active_terminal(self):
        """Clear the active terminal output"""
        if self.active_terminal_index < len(self.terminal_tabs):
            terminal_data = self.terminal_tabs[self.active_terminal_index]
            terminal_widget = terminal_data.get('terminal_widget')
            if terminal_widget and terminal_widget.is_valid:
                terminal_widget.clear_output()

    def restart_active_terminal(self):
        """Restart the active terminal process"""
        if self.active_terminal_index < len(self.terminal_tabs):
            terminal_data = self.terminal_tabs[self.active_terminal_index]
            process = terminal_data.get('process')
            terminal_widget = terminal_data.get('terminal_widget')

            if not process or not terminal_widget or not terminal_widget.is_valid:
                return

            # Try to terminate gracefully
            if process.state() == QProcess.ProcessState.Running:
                process.terminate()
                # Force kill after timeout if needed
                if not process.waitForFinished(500):
                    process.kill()

            # Clear terminal output
            terminal_widget.clear_output()

            # Start new process
            QTimer.singleShot(300, lambda: self.start_terminal_process(self.active_terminal_index))

            # Show restart message
            welcome_msg = "Terminal restarted.\n"
            terminal_widget.append_output(welcome_msg)

    def renumber_tabs(self):
        """Update tab numbers after a tab is closed"""
        for i, terminal_data in enumerate(self.terminal_tabs):
            # Find tab container
            tab_container = terminal_data.get('tab_container')
            if not tab_container:
                continue

            # Find the label in the tab widget and update it
            for child in tab_container.findChildren(QLabel):
                child.setText(f"Terminal {i + 1}")
                break

    def toggle_terminal(self):
        """Toggle terminal visibility"""
        if self.is_visible:
            self.hide_terminal()
        else:
            self.show_terminal()

    def show_terminal(self):
        """Show the terminal panel with animation"""
        if not self.is_visible:
            # Make sure we're positioned correctly before showing
            self.get_sidebar_width()
            self.reposition()

            # Start the process for current tab if not running
            if len(self.terminal_tabs) > 0 and self.active_terminal_index < len(self.terminal_tabs):
                self.start_terminal_process(self.active_terminal_index)

            # Make visible
            self.show()
            self.is_visible = True

            # Focus the input widget
            if self.active_terminal_index < len(self.terminal_tabs):
                input_widget = self.terminal_tabs[self.active_terminal_index].get('input_widget')
                if input_widget:
                    input_widget.setFocus()

    def get_sidebar_width(self):
        """Get the current sidebar width from the parent window's cluster view"""
        self.sidebar_width = 0

        # Try to get sidebar from parent window's cluster view
        if hasattr(self.parent_window, 'cluster_view') and hasattr(self.parent_window.cluster_view, 'sidebar'):
            self.sidebar_width = self.parent_window.cluster_view.sidebar.width()

        return self.sidebar_width

    def hide_terminal(self):
        """Hide the terminal panel"""
        if self.is_visible:
            self.hide()
            self.is_visible = False

    def toggle_maximize(self):
        """Toggle between maximized and normal size"""
        if self.is_maximized:
            # Restore to normal size
            self.setFixedHeight(self.normal_height)
            self.unified_header.maximize_btn.setText("🔼")
            self.unified_header.maximize_btn.setToolTip("Maximize Terminal")
        else:
            # Save current height as normal height
            self.normal_height = self.height()

            # Calculate maximum height (leave room for title bar)
            max_height = self.parent_window.height() - 50

            # Set to maximum height
            self.setFixedHeight(max_height)
            self.unified_header.maximize_btn.setText("🔽")
            self.unified_header.maximize_btn.setToolTip("Restore Terminal")

        # Toggle maximized state
        self.is_maximized = not self.is_maximized

        # Update position
        self.reposition()

    def reposition(self):
        """Position the terminal at the bottom-right of the main window, respecting sidebar"""
        if self.parent_window:
            parent_width = self.parent_window.width()
            parent_height = self.parent_window.height()

            # Get current sidebar width if not already set
            if self.sidebar_width == 0:
                self.get_sidebar_width()

            # Set width to cover only the space right of sidebar
            terminal_width = parent_width - self.sidebar_width

            # Ensure width is at least a minimum value
            terminal_width = max(terminal_width, 300)

            # Set width
            self.setFixedWidth(terminal_width)

            # Position at bottom-right
            self.move(self.sidebar_width, parent_height - self.height())

            # Bring to front
            self.raise_()

    def resizeEvent(self, event):
        """Handle resize events"""
        # Keep terminal width in sync with available space
        if self.parent_window:
            # Only adjust width if not being manually resized vertically
            if self.resize_start_y is None:
                self.get_sidebar_width()
                self.setFixedWidth(self.parent_window.width() - self.sidebar_width)

        super().resizeEvent(event)

    def moveEvent(self, event):
        """Handle move events - keep terminal positioned correctly"""
        if self.parent_window and self.is_visible:
            # Only reposition horizontally to respect manual vertical resizing
            if self.resize_start_y is None:
                current_pos = self.pos()
                sidebar_width = self.get_sidebar_width()
                self.move(sidebar_width, current_pos.y())

        super().moveEvent(event)

    # Resize handling
    resize_start_y = None
    original_height = None

    def close_all_terminals(self):
        """Close all terminal tabs and hide the terminal panel"""
        # Terminate all processes
        self.terminate_all_processes()

        # Clear all tabs
        for tab_data in self.terminal_tabs:
            tab_container = tab_data.get('tab_container')
            if tab_container:
                tab_container.deleteLater()

            content_widget = tab_data.get('content_widget')
            if content_widget:
                content_widget.deleteLater()

        # Clear the tabs list
        self.terminal_tabs.clear()

        # Add one new tab
        self.add_terminal_tab()

        # Hide the terminal panel
        self.hide_terminal()

    def eventFilter(self, obj, event):
        """Handle events for resize capability and parent window resizing"""
        if obj == self.unified_header.resize_handle:
            # We only need to check for events on the resize handle
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                # Start resize operation
                self.resize_start_y = event.globalPosition().y()
                self.original_height = self.height()
                # Capture the mouse to continue tracking even if moved outside of handle
                obj.grabMouse()
                return True

            elif event.type() == QEvent.Type.MouseMove and self.resize_start_y is not None:
                # Resize while dragging
                delta_y = self.resize_start_y - event.globalPosition().y()
                new_height = min(max(100, self.original_height + delta_y),
                                 self.parent_window.height() - 50)

                self.setFixedHeight(int(new_height))
                self.normal_height = int(new_height)

                # Only adjust vertical position, preserve horizontal
                current_pos = self.pos()
                self.move(current_pos.x(), self.parent_window.height() - int(new_height))

                return True

            elif event.type() == QEvent.Type.MouseButtonRelease and self.resize_start_y is not None:
                # End resize operation
                self.resize_start_y = None
                self.original_height = None
                # Release the mouse grab
                obj.releaseMouse()
                return True

        elif obj == self.unified_header:
            # Pass through events for the header itself (no resize handling here anymore)
            pass

        # Also monitor parent window events to stay updated on size changes
        elif obj == self.parent_window:
            if event.type() == QEvent.Type.Resize:
                # Adjust terminal width and position when parent window resizes
                if self.is_visible:
                    # Preserve the current height during repositioning
                    current_height = self.height()

                    # Update sidebar width
                    self.get_sidebar_width()

                    # Update width
                    self.setFixedWidth(self.parent_window.width() - self.sidebar_width)

                    # Update position
                    self.move(self.sidebar_width, self.parent_window.height() - current_height)

            elif event.type() == QEvent.Type.WindowStateChange:
                # Handle window state changes (minimize/maximize)
                if self.parent_window.isMinimized() and self.is_visible:
                    # Hide terminal when main window is minimized
                    self.hide()
                elif not self.parent_window.isMinimized() and self.is_visible:
                    # Show terminal when main window is restored
                    self.show()
                    QTimer.singleShot(100, self.reposition)

        return super().eventFilter(obj, event)

    # Override show event to ensure we install the event filter on parent window
    def showEvent(self, event):
        super().showEvent(event)

        # Reposition to ensure we're in the right place
        QTimer.singleShot(10, self.reposition)

        # Install event filter on parent window to monitor size changes
        if self.parent_window and not self.parent_window.isAncestorOf(self):
            self.parent_window.installEventFilter(self)

    def download_terminal_output(self):
        """Save the current terminal output to a file"""
        if self.active_terminal_index < len(self.terminal_tabs):
            terminal_data = self.terminal_tabs[self.active_terminal_index]
            terminal_widget = terminal_data.get('terminal_widget')

            if not terminal_widget or not terminal_widget.is_valid:
                return

            from PyQt6.QtWidgets import QFileDialog
            from datetime import datetime

            # Get current date/time for default filename
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"terminal_output_{current_time}.txt"

            # Open file dialog
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Terminal Output",
                default_filename,
                "Text Files (*.txt);;All Files (*)"
            )

            # If a filename was selected (dialog not canceled)
            if filename:
                try:
                    with open(filename, 'w', encoding='utf-8') as file:
                        # Get text from the terminal widget
                        text = terminal_widget.toPlainText()
                        file.write(text)

                    # Flash confirmation to user in terminal
                    terminal_widget.append_output(
                        f"\nTerminal output saved to: {filename}\n",
                        "#00FF00"  # Green text for success
                    )
                    terminal_widget.append_prompt()
                except Exception as e:
                    # Show error in terminal
                    terminal_widget.append_output(
                        f"\nError saving terminal output: {str(e)}\n",
                        "#FF6B68"  # Red text for error
                    )
                    terminal_widget.append_prompt()

