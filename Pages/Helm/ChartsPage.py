"""
Dynamic implementation of the Charts page for Helm charts.
"""

from PyQt6.QtWidgets import (
    QHeaderView, QWidget, QLabel, QProgressBar, QVBoxLayout, 
    QHBoxLayout, QPushButton, QToolButton, QMenu, QTableWidget, 
    QTableWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QEvent
from PyQt6.QtGui import QColor, QIcon, QCursor
import subprocess
import json
import shutil
import os
from functools import partial

from base_components.base_components import SortableTableWidgetItem
from UI.Styles import AppStyles, AppColors

class SortableHeader(QHeaderView):
    """Custom header for sortable columns only"""
    def __init__(self, orientation, sortable_columns=None, parent=None):
        super().__init__(orientation, parent)
        self.sortable_columns = sortable_columns or set()
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        logicalIndex = self.logicalIndexAt(event.pos())
        if logicalIndex in self.sortable_columns:
            super().mousePressEvent(event)
        else:
            event.ignore()

class HelmChartsLoader(QThread):
    """Thread for loading Helm charts without blocking the UI."""
    charts_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def run(self):
        """Execute helm search repo and emit results."""
        try:
            # Check if helm is installed and available in PATH
            helm_path = shutil.which("helm")
            if not helm_path:
                self.error_occurred.emit("Helm command not found. Please install Helm or ensure it's in your PATH.")
                return
                
            # Run helm search repo command
            cmd = ["helm", "search", "repo", "--output", "json"]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError as e:
                if "no repositories found" in str(e.stderr).lower():
                    # No repositories configured
                    self.charts_loaded.emit([])  # Empty list
                    return
                else:
                    # Other subprocess error
                    raise
            
            # Parse JSON output
            charts = json.loads(result.stdout)
            
            # Format the charts
            formatted_charts = []
            for chart in charts:
                # Extract fields
                name = chart.get("name", "")
                version = chart.get("version", "")
                app_version = chart.get("app_version", "")
                description = chart.get("description", "")
                
                # Get repository
                repo = name.split("/")[0] if "/" in name else "unknown"
                
                # Create a resource object
                resource = {
                    "name": name,
                    "repo": repo,
                    "version": version,
                    "app_version": app_version,
                    "description": description,
                    "raw_data": chart  # Store the raw data
                }
                
                formatted_charts.append(resource)
            
            # Emit the result
            self.charts_loaded.emit(formatted_charts)
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Error loading Helm charts: {e.stderr}"
            self.error_occurred.emit(error_msg)
        except json.JSONDecodeError:
            self.error_occurred.emit("Invalid JSON returned from Helm command")
        except FileNotFoundError:
            self.error_occurred.emit("Helm command not found. Please install Helm or ensure it's in your PATH.")
        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")

class ChartsPage(QWidget):
    """
    Displays Helm charts with live data and operations.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resources = []
        self.is_loading = False
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the main UI elements for the Charts page"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header with title and controls
        header_layout = QHBoxLayout()
        
        # Title
        title = QLabel("Charts")
        title.setStyleSheet(AppStyles.TITLE_STYLE)
        
        # Item count
        self.items_count = QLabel("0 items")
        self.items_count.setStyleSheet(AppStyles.ITEMS_COUNT_STYLE)
        self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(self.items_count)
        header_layout.addStretch()
        
        # Add refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(AppStyles.BUTTON_PRIMARY_STYLE)
        refresh_btn.clicked.connect(self.load_data)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Create the table
        self.table = QTableWidget()
        self.table.setColumnCount(6)  # No checkbox column
        
        # Table headers
        headers = ["Chart", "Repository", "Version", "App Version", "Description", ""]
        self.table.setHorizontalHeaderLabels(headers)
        
        # Define sortable columns
        sortable_columns = {0, 1, 2, 3}
        
        # Apply custom header for sortable columns
        custom_header = SortableHeader(Qt.Orientation.Horizontal, sortable_columns, self.table)
        self.table.setHorizontalHeader(custom_header)
        self.table.setSortingEnabled(True)
        
        # Apply styling
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        # Configure table behavior
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        
        # Configure column widths
        self.configure_columns()
        
        # Connect signals
        self.table.cellClicked.connect(self.handle_row_click)
        
        # Add table to layout
        layout.addWidget(self.table)
        
        # Create empty state label
        self.empty_label = QLabel("No charts found. Try adding a Helm repository.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(AppStyles.EMPTY_LABEL_STYLE)
        self.empty_label.hide()
        layout.addWidget(self.empty_label)
        
        # Install event filter for click handling
        self.installEventFilter(self)
        
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Chart column (stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        # Repository column (fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 120)
        
        # Version column (fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 100)
        
        # App Version column (fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 100)
        
        # Description column (stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        # Actions column (fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 40)
    
    def eventFilter(self, obj, event):
        """Handle events for window click tracking"""
        if event.type() == QEvent.Type.MouseButtonPress:
            pos = event.pos()
            if not self.table.geometry().contains(pos):
                self.table.clearSelection()
        return super().eventFilter(obj, event)
    
    def load_data(self):
        """Load Helm charts data."""
        if self.is_loading:
            return
            
        self.is_loading = True
        
        # Clear existing data
        self.resources = []
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        # Show loading indicator
        loading_row = self.table.rowCount()
        self.table.setRowCount(loading_row + 1)
        self.table.setSpan(loading_row, 0, 1, self.table.columnCount())
        
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_layout.setContentsMargins(20, 20, 20, 20)
        
        loading_bar = QProgressBar()
        loading_bar.setRange(0, 0)  # Indeterminate
        loading_bar.setTextVisible(False)
        loading_bar.setStyleSheet(AppStyles.PROGRESS_BAR_STYLE)
        
        loading_text = QLabel("Loading Helm charts...")
        loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        loading_layout.addWidget(loading_text)
        loading_layout.addWidget(loading_bar)
        
        self.table.setCellWidget(loading_row, 0, loading_widget)
        
        # Create and start Helm loader thread
        self.helm_loader = HelmChartsLoader()
        self.helm_loader.charts_loaded.connect(self.on_charts_loaded)
        self.helm_loader.error_occurred.connect(self.on_load_error)
        self.helm_loader.start()
    
    def on_charts_loaded(self, charts):
        """Handle the loaded Helm charts"""
        self.is_loading = False
        
        # Store the charts
        self.resources = charts
        
        # Update the item count
        self.items_count.setText(f"{len(charts)} items")
        
        if not charts:
            # Show empty state
            self.table.setRowCount(0)
            self.empty_label.show()
            self.table.hide()
        else:
            # Populate the table
            self.table.show()
            self.empty_label.hide()
            self.populate_table(charts)
            
            # Re-enable sorting
            self.table.setSortingEnabled(True)
    
    def on_load_error(self, error_message):
        """Handle errors during loading"""
        self.is_loading = False
        self.table.setRowCount(0)
        
        # Add a single row with the error message
        self.table.setRowCount(1)
        self.table.setSpan(0, 0, 1, self.table.columnCount())
        
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setContentsMargins(20, 20, 20, 20)
        
        error_label = QLabel(f"Error: {error_message}")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet(f"color: {AppColors.TEXT_DANGER}; font-size: 14px;")
        error_label.setWordWrap(True)
        
        retry_button = QPushButton("Retry")
        retry_button.setStyleSheet(AppStyles.BUTTON_PRIMARY_STYLE)
        retry_button.clicked.connect(self.load_data)
        retry_button.setFixedWidth(100)
        
        error_layout.addWidget(error_label)
        error_layout.addWidget(retry_button, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.table.setCellWidget(0, 0, error_widget)
    
    def populate_table(self, charts):
        """Populate the table with chart data"""
        # Set row count
        self.table.setRowCount(len(charts))
        
        # Populate each row
        for row, chart in enumerate(charts):
            self.populate_chart_row(row, chart)
    
    def populate_chart_row(self, row, chart):
        """Populate a single row with chart data"""
        # Set row height
        self.table.setRowHeight(row, 40)
        
        # Prepare data columns
        columns = [
            chart["name"],
            chart["repo"],
            chart["version"],
            chart["app_version"],
            chart["description"]
        ]
        
        # Add columns to table
        for col, value in enumerate(columns):
            item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in [0, 4]:  # Name and Description
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Set text color
            item.setForeground(QColor(AppColors.TEXT_TABLE))
            
            # Add item to table
            self.table.setItem(row, col, item)
        
        # Create action button
        action_button = self.create_action_button(row, chart)
        
        # Create container for action button
        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(action_button)
        action_container.setStyleSheet("background-color: transparent;")
        
        # Add to table
        self.table.setCellWidget(row, len(columns), action_container)
    
    def create_action_button(self, row, chart):
        """Create an action button with menu"""
        button = QToolButton()
        button.setText("⋮")
        button.setFixedWidth(30)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Create menu
        menu = QMenu(button)
        menu.setStyleSheet(AppStyles.MENU_STYLE)
        
        # Add actions
        install_action = menu.addAction("Install")
        install_action.setIcon(QIcon("icons/install.png"))
        install_action.triggered.connect(partial(self.handle_action, "Install", row, chart))
        
        view_action = menu.addAction("View")
        view_action.setIcon(QIcon("icons/view.png"))
        view_action.triggered.connect(partial(self.handle_action, "View", row, chart))
        
        button.setMenu(menu)
        return button
    
    def handle_action(self, action, row, chart):
        """Handle action button clicks"""
        chart_name = chart["name"]
        
        if action == "Install":
            self.install_chart(chart)
        elif action == "View":
            self.view_chart(chart)
    
    def install_chart(self, chart):
        """Handle chart installation"""
        # This would be implemented based on your application's needs
        print(f"Installing chart: {chart['name']}")
        
        # Example implementation:
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, QComboBox, QCheckBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Install Chart: {chart['name']}")
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet(f"""
            background-color: {AppColors.BG_DARK};
            color: {AppColors.TEXT_LIGHT};
        """)
        
        layout = QVBoxLayout(dialog)
        
        form = QFormLayout()
        
        # Release name field
        release_name = QLineEdit()
        release_name.setStyleSheet(AppStyles.INPUT_STYLE)
        form.addRow("Release Name:", release_name)
        
        # Namespace field
        namespace = QLineEdit("default")
        namespace.setStyleSheet(AppStyles.INPUT_STYLE)
        form.addRow("Namespace:", namespace)
        
        # Version selection
        version = QComboBox()
        version.addItem(chart["version"])
        version.setStyleSheet(AppStyles.DROPDOWN_STYLE)
        form.addRow("Version:", version)
        
        # Values checkbox
        custom_values = QCheckBox("Use custom values file")
        custom_values.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        form.addRow("", custom_values)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Install")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setStyleSheet(AppStyles.BUTTON_PRIMARY_STYLE)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setStyleSheet(AppStyles.BUTTON_SECONDARY_STYLE)
        
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Here you would execute the helm install command
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Installation Started", 
                                  f"Starting installation of {chart['name']} as {release_name.text()} in namespace {namespace.text()}")
    
    def view_chart(self, chart):
        """View chart details"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QTextEdit, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Chart Details: {chart['name']}")
        dialog.setMinimumSize(600, 400)
        dialog.setStyleSheet(f"""
            background-color: {AppColors.BG_DARK};
            color: {AppColors.TEXT_LIGHT};
        """)
        
        layout = QVBoxLayout(dialog)
        
        # Create tabs
        tabs = QTabWidget()
        tabs.setStyleSheet(AppStyles.MAIN_STYLE)
        
        # Info tab
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # Chart info
        info_text = f"""
        <h2>{chart['name']}</h2>
        <p><b>Repository:</b> {chart['repo']}</p>
        <p><b>Version:</b> {chart['version']}</p>
        <p><b>App Version:</b> {chart['app_version']}</p>
        <p><b>Description:</b> {chart['description']}</p>
        """
        
        info_label = QLabel()
        info_label.setText(info_text)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {AppColors.TEXT_LIGHT}; font-size: 13px;")
        
        info_layout.addWidget(info_label)
        tabs.addTab(info_widget, "Information")
        
        # Raw tab with JSON data
        raw_widget = QWidget()
        raw_layout = QVBoxLayout(raw_widget)
        
        raw_text = QTextEdit()
        raw_text.setReadOnly(True)
        raw_text.setStyleSheet(f"""
            background-color: {AppColors.BG_SIDEBAR};
            color: {AppColors.TEXT_LIGHT};
            border: 1px solid {AppColors.BORDER_COLOR};
            font-family: 'Courier New', monospace;
            font-size: 12px;
        """)
        
        import json
        raw_text.setText(json.dumps(chart["raw_data"], indent=2))
        
        raw_layout.addWidget(raw_text)
        tabs.addTab(raw_widget, "Raw Data")
        
        layout.addWidget(tabs)
        
        dialog.exec()
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != 5:  # Skip action column
            # Select the row
            self.table.selectRow(row)
    
    def showEvent(self, event):
        """Load data when the page is shown"""
        super().showEvent(event)
        # Load data if there's none loaded yet
        if not self.is_loading and len(self.resources) == 0:
            self.load_data()