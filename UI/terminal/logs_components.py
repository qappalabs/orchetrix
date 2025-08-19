"""
Logs components - Split from TerminalPanel.py

This module contains the LogsHeaderWidget, LogsStreamWorker, and EnhancedLogsViewer 
classes which provide comprehensive log viewing functionality for Kubernetes pods.
"""

import logging
from datetime import datetime
from kubernetes import watch
from kubernetes.client.rest import ApiException
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QComboBox, 
    QCheckBox, QLabel
)
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

from UI.Styles import AppStyles


class LogsHeaderWidget(QWidget):
    """
    Simplified header widget for logs viewer.
    
    This widget provides controls for log viewing including container selection,
    tail lines configuration, follow mode toggle, and search results display.
    """

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
        """Setup the simplified header UI components with fixed layout."""
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
        self.container_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.container_combo.currentTextChanged.connect(self.container_changed.emit)
        controls_row.addWidget(container_label)
        controls_row.addWidget(self.container_combo)

        # Tail lines selection
        lines_label = QLabel("📜")
        lines_label.setFixedSize(20, 20)
        self.lines_combo = QComboBox()
        self.lines_combo.setFixedHeight(24)
        self.lines_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lines_combo.addItems(["50", "100", "200", "500", "1000", "All"])
        self.lines_combo.setCurrentText("200")
        self.lines_combo.currentTextChanged.connect(self._on_lines_changed)
        controls_row.addWidget(lines_label)
        controls_row.addWidget(self.lines_combo)

        # Follow logs checkbox
        self.follow_checkbox = QCheckBox("Follow")
        self.follow_checkbox.setChecked(True)
        self.follow_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.follow_checkbox.toggled.connect(self.follow_toggled.emit)
        controls_row.addWidget(self.follow_checkbox)

        # Search results label (updated by terminal header search)
        self.search_results_label = QLabel("")
        self.search_results_label.setStyleSheet("color: #4CAF50; font-size: 10px; font-weight: bold;")
        controls_row.addWidget(self.search_results_label)

        main_layout.addLayout(controls_row)

    def _truncate_name(self, name, max_length):
        """Truncate name if it's too long."""
        if len(name) <= max_length:
            return name
        return name[:max_length-3] + "..."

    def load_containers(self):
        """Load available containers for the pod."""
        try:
            from Utils.kubernetes_client import get_kubernetes_client
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
        """Handle tail lines change."""
        try:
            if text == "All":
                self.tail_lines_changed.emit(-1)
            else:
                self.tail_lines_changed.emit(int(text))
        except ValueError:
            self.tail_lines_changed.emit(200)

    def update_search_results(self, current_results, total_logs):
        """Update search results display."""
        if current_results > 0:
            self.search_results_label.setText(f"📍 {current_results}/{total_logs}")
        else:
            self.search_results_label.setText("")

    def update_status(self, message):
        """Update status - now handled by bottom indicator."""
        pass


class LogsStreamWorker(QThread):
    """
    Worker thread for streaming logs from Kubernetes API.
    
    This thread handles the continuous streaming of pod logs from the Kubernetes API,
    processing both initial logs and real-time updates when follow mode is enabled.
    """

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
        """Stop the streaming."""
        self._stop_requested = True
        self.quit()

    def run(self):
        """Run the log streaming."""
        try:
            from Utils.kubernetes_client import get_kubernetes_client
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
        """Stream logs using Kubernetes watch API."""
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
                        except (IndexError, ValueError) as e:
                            logging.debug(f"Error parsing log timestamp: {e}")

                self.log_received.emit(log_line, timestamp)

        except ApiException as e:
            if not self._stop_requested:
                self.error_occurred.emit(f"API error during streaming: {e.reason}")
        except Exception as e:
            if not self._stop_requested:
                self.error_occurred.emit(f"Streaming error: {str(e)}")

    def _fetch_initial_logs(self):
        """Fetch initial logs before starting stream."""
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
                                except (IndexError, ValueError) as e:
                                    logging.debug(f"Error parsing log timestamp: {e}")

                        self.log_received.emit(log_line, timestamp)

        except Exception as e:
            logging.error(f"Error fetching initial logs: {e}")

    def _fetch_static_logs(self):
        """Fetch static logs (non-streaming)."""
        self._fetch_initial_logs()
        self.connection_status.emit("📋 Static logs loaded")


class EnhancedLogsViewer(QWidget):
    """
    Enhanced logs viewer with search highlighting and improved functionality.
    
    This widget provides a comprehensive log viewing experience with features like
    real-time streaming, search and highlighting, container selection, and 
    configurable display options.
    """

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
        """Setup the UI components."""
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
        self.logs_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: none;
                selection-background-color: #264F78;
                padding: 8px;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
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
        """Connect header signals to handlers."""
        self.header.container_changed.connect(self.set_container)
        self.header.tail_lines_changed.connect(self.set_tail_lines)
        self.header.follow_toggled.connect(self.set_follow_mode)
        self.header.refresh_requested.connect(self.refresh_logs)

    def start_log_stream(self):
        """Start the log streaming worker."""
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
        """Stop the current log stream."""
        if self.stream_worker and self.stream_worker.isRunning():
            self.stream_worker.stop()
            self.stream_worker.wait(2000)  # Wait up to 2 seconds
            if self.stream_worker.isRunning():
                self.stream_worker.terminate()

    def add_log_line(self, log_line, timestamp):
        """Add a new log line to the display."""
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
        """Display a log line in the text widget with search highlighting."""
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
        """Insert text with search term highlighted."""
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
        """Get color for log line based on content."""
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
        """Set search filter and refresh display with highlighting."""
        self.search_text = search_text.strip()
        self.refresh_display()
        self.update_search_display()

    def update_search_display(self):
        """Update search results counter."""
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
        """Change container and restart stream."""
        if container != self.current_container:
            self.current_container = container
            self.clear_logs()
            self.start_log_stream()

    def set_tail_lines(self, lines):
        """Set tail lines and restart stream."""
        if lines != self.tail_lines:
            self.tail_lines = lines
            self.clear_logs()
            self.start_log_stream()

    def set_follow_mode(self, follow):
        """Enable/disable follow mode."""
        self.follow_enabled = follow
        if not follow:
            self.update_status("📋 Static mode - logs will not update automatically")
            self.show_status_indicator("📋 Static Mode", "#9ca3af")
        else:
            self.update_status("🔴 Live mode - following new logs")
            self.show_status_indicator("🔴 Live Mode", "#4CAF50")

    def show_status_indicator(self, text, color):
        """Show status indicator at bottom."""
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
        """Refresh the log stream."""
        self.clear_logs()
        self.start_log_stream()
        self.show_status_indicator("🔄 Refreshing...", "#2196F3")

    def clear_logs(self):
        """Clear all logs from display and storage."""
        self.all_logs.clear()
        self.search_matches = 0
        self.logs_display.clear()
        self.header.update_search_results(0, 0)

    def refresh_display(self):
        """Refresh the display with current search filter and highlighting."""
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
        """Handle streaming errors."""
        self.header.update_status(f"❌ Error: {error_message}")
        self.show_status_indicator("❌ Error", "#ff6b68")
        logging.error(f"Log stream error: {error_message}")

    def update_status(self, message):
        """Update status label."""
        self.header.update_status(message)

    def closeEvent(self, event):
        """Handle close event."""
        self.stop_log_stream()
        super().closeEvent(event)