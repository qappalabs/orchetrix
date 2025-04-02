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
        """Set up the terminal panel UI"""
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
        
        # Create terminal wrapper that includes header and content
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
        
        # Create terminal header with controls
        self.terminal_header = self.create_terminal_header()
        self.wrapper_layout.addWidget(self.terminal_header)
        
        # Terminal tabs row
        self.tabs_container = QWidget()
        self.tabs_container.setFixedHeight(36)
        self.tabs_container.setStyleSheet(f"""
            background-color: #252525;
            border-top: 1px solid {AppColors.BORDER_COLOR};
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
        """)
        
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 4, 0)
        self.tabs_layout.setSpacing(0)
        
        # Add new tab button
        self.new_tab_btn = QPushButton("+")
        self.new_tab_btn.setFixedSize(28, 28)
        self.new_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_tab_btn.setToolTip("New Terminal")
        self.new_tab_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {AppColors.TEXT_SECONDARY};
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 2px;
            }}
            QPushButton:hover {{
                background-color: {AppColors.HOVER_BG};
                color: {AppColors.TEXT_LIGHT};
                border-radius: 4px;
            }}
        """)
        self.new_tab_btn.clicked.connect(self.add_terminal_tab)
        
        self.tabs_layout.addStretch()
        self.tabs_layout.addWidget(self.new_tab_btn)
        
        self.wrapper_layout.addWidget(self.tabs_container)
        
        # Create content stack to hold terminal tabs
        self.terminal_stack = QWidget()
        self.stack_layout = QVBoxLayout(self.terminal_stack)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        self.stack_layout.setSpacing(0)
        
        self.wrapper_layout.addWidget(self.terminal_stack, 1)
        
        # Add wrapper to main layout
        self.main_layout.addWidget(self.terminal_wrapper)
        
        # Install event filter for resize handle
        self.terminal_header.installEventFilter(self)
        
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
    
    def create_terminal_header(self):
        """Create the terminal header with title and control buttons"""
        header = QWidget()
        header.setFixedHeight(40)
        header.setMouseTracking(True)
        header.setCursor(Qt.CursorShape.SizeVerCursor)  # Indicate resizable
        
        header.setStyleSheet(f"""
            background-color: {AppColors.BG_DARKER};
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)
        
        # Terminal title
        title = QLabel("Terminal")
        title.setStyleSheet(f"""
            color: {AppColors.TEXT_LIGHT};
            font-size: 14px;
            font-weight: bold;
        """)
        
        # Control buttons container
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)
        
        # Create control buttons
        self.clear_btn = self.create_header_button("🗑️", "Clear Terminal", 
                                                   self.clear_active_terminal)
        
        self.restart_btn = self.create_header_button("🔄", "Restart Terminal", 
                                                     self.restart_active_terminal)
        
        self.maximize_btn = self.create_header_button("🔼", "Maximize/Restore Terminal", 
                                                      self.toggle_maximize)
        
        self.close_all_btn = self.create_header_button("✕✕", "Close All Terminals", 
                                                     self.close_all_terminals)
        
        self.close_btn = self.create_header_button("✕", "Hide Terminal Panel", 
                                                   self.hide_terminal)
        
        # Add buttons to controls
        controls_layout.addWidget(self.clear_btn)
        controls_layout.addWidget(self.restart_btn)
        controls_layout.addWidget(self.maximize_btn)
        controls_layout.addWidget(self.close_all_btn)
        controls_layout.addWidget(self.close_btn)
        
        # Add widgets to layout
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(controls)
        
        return header
    
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
    
    def add_terminal_tab(self):
        """Add a new terminal tab"""
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
        
        # Add tab to layout
        self.tabs_layout.insertWidget(self.tabs_layout.count() - 1, tab_container)
        
        # Create terminal content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Create terminal output and input widgets
        terminal_output = TerminalOutputWidget()
        terminal_input = TerminalInputWidget()
        
        content_layout.addWidget(terminal_output, 1)
        content_layout.addWidget(terminal_input)
        
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
        
        # Connect input command signal
        terminal_input.commandEntered.connect(
            lambda cmd: self.execute_command(cmd, tab_index))
        
        # Start the process if terminal is visible
        if self.is_visible:
            self.start_terminal_process(tab_index)
        
        # Store terminal data
        terminal_data = {
            'tab_button': tab_btn,
            'tab_container': tab_container,
            'content_widget': content_widget,
            'output_widget': terminal_output,
            'input_widget': terminal_input,
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
        welcome_msg += "$ "
        
        terminal_output.append_output(welcome_msg)
        
        # Switch to this tab
        self.switch_to_terminal_tab(tab_index)
        
        return tab_index
    
    def safe_handle_process_finished(self, tab_index, exit_code, exit_status):
        """Safely handle process termination avoiding deleted widget errors"""
        try:
            if tab_index < len(self.terminal_tabs):
                terminal_data = self.terminal_tabs[tab_index]
                output_widget = terminal_data.get('output_widget')
                
                if output_widget and output_widget.is_valid:
                    if exit_status == QProcess.ExitStatus.CrashExit:
                        output_widget.append_output(
                            "\nProcess crashed. Restarting terminal...\n", "#FF6B68")
                        QTimer.singleShot(1000, lambda: self.start_terminal_process(tab_index))
                    elif exit_code != 0:
                        output_widget.append_output(
                            f"\nProcess exited with code {exit_code}. Restarting terminal...\n", "#FFA500")
                        QTimer.singleShot(1000, lambda: self.start_terminal_process(tab_index))
                    else:
                        output_widget.append_output("\nProcess exited normally.\n$ ")
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
        terminal_output = terminal_data.get('output_widget')
        process = terminal_data.get('process')
        
        if not terminal_output or not terminal_output.is_valid or not process:
            return
            
        # Show the command in the terminal output
        terminal_output.append_output(f"$ {command}\n")
        
        # Special case for 'clear' command
        if command.strip().lower() == "clear":
            terminal_output.clear_output()
            terminal_output.append_output("$ ")
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
        terminal_output = terminal_data.get('output_widget')
        process = terminal_data.get('process')
        
        if not terminal_output or not terminal_output.is_valid or not process:
            return
            
        data = process.readAllStandardOutput()
        text = bytes(data).decode('utf-8', errors='replace')
        terminal_output.append_output(text)
    
    def handle_stderr(self, tab_index=None):
        """Handle standard error from process"""
        if tab_index is None:
            tab_index = self.active_terminal_index
            
        if tab_index >= len(self.terminal_tabs):
            return
            
        terminal_data = self.terminal_tabs[tab_index]
        terminal_output = terminal_data.get('output_widget')
        process = terminal_data.get('process')
        
        if not terminal_output or not terminal_output.is_valid or not process:
            return
            
        data = process.readAllStandardError()
        text = bytes(data).decode('utf-8', errors='replace')
        # Show stderr in red
        terminal_output.append_output(text, "#FF6B68")
    
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
        
        # Focus the input widget
        if terminal_data.get('input_widget'):
            terminal_data['input_widget'].setFocus()
        
        # Update active index
        self.active_terminal_index = tab_index
        
        # Start process if needed
        if not terminal_data.get('started', False):
            self.start_terminal_process(tab_index)
    
    def close_terminal_tab(self, tab_index):
        """Close a terminal tab"""
        print(f"Closing terminal tab {tab_index}")
        
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
        
        # Remove tab container from layout
        tab_container = terminal_data.get('tab_container')
        if tab_container:
            # Find and remove from layout
            for i in range(self.tabs_layout.count()):
                if self.tabs_layout.itemAt(i).widget() == tab_container:
                    widget = self.tabs_layout.takeAt(i).widget()
                    if widget:
                        widget.deleteLater()
                    break
        
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
            output_widget = terminal_data.get('output_widget')
            if output_widget and output_widget.is_valid:
                output_widget.clear_output()
                output_widget.append_output("$ ")
    
    def restart_active_terminal(self):
        """Restart the active terminal process"""
        if self.active_terminal_index < len(self.terminal_tabs):
            terminal_data = self.terminal_tabs[self.active_terminal_index]
            process = terminal_data.get('process')
            output_widget = terminal_data.get('output_widget')
            
            if not process or not output_widget or not output_widget.is_valid:
                return
            
            # Try to terminate gracefully
            if process.state() == QProcess.ProcessState.Running:
                process.terminate()
                # Force kill after timeout if needed
                if not process.waitForFinished(500):
                    process.kill()
            
            # Clear terminal output
            output_widget.clear_output()
            
            # Start new process
            QTimer.singleShot(300, lambda: self.start_terminal_process(self.active_terminal_index))
            
            # Show restart message
            welcome_msg = "Terminal restarted.\n$ "
            output_widget.append_output(welcome_msg)

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
            self.maximize_btn.setText("🔼")
            self.maximize_btn.setToolTip("Maximize Terminal")
        else:
            # Save current height as normal height
            self.normal_height = self.height()
            
            # Calculate maximum height (leave room for title bar)
            max_height = self.parent_window.height() - 50
            
            # Set to maximum height
            self.setFixedHeight(max_height)
            self.maximize_btn.setText("🔽")
            self.maximize_btn.setToolTip("Restore Terminal")
        
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
        if obj == self.terminal_header:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                # Start resize operation
                self.resize_start_y = event.globalPosition().y()
                self.original_height = self.height()
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
                
            elif event.type() == QEvent.Type.MouseButtonRelease:
                # End resize operation
                self.resize_start_y = None
                self.original_height = None
                return True
        
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