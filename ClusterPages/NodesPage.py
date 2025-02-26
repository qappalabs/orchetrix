from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QLabel, QHeaderView, QPushButton,
                           QMenu, QToolButton, QFrame, QGraphicsDropShadowEffect,
                           QSizePolicy, QComboBox)
from PyQt6.QtCore import Qt, QSize, QPoint, QTimer, QRectF
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QLinearGradient, QPainterPath, QBrush
import random
import datetime
import re

class GraphWidget(QFrame):
    """Custom widget for displaying resource utilization graphs"""
    def __init__(self, title, unit, color, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.color = color
        self.data = [0] * 24  # Initialize with zeros
        self.current_value = 0
        self.selected_node = None  # Will store the selected node data
        self.node_name = "None"
        self.utilization_data = {}  # Store utilization data for all nodes
        
        # Visual properties
        self.setMinimumHeight(120)
        self.setMaximumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Styling
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1e1e1e;
                border-radius: 4px;
                border: 1px solid #2d2d2d;
            }}
        """)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # Title and value layout
        header_layout = QHBoxLayout()
        
        # Title with node name
        self.title_label = QLabel(f"{title} (No node selected)")
        self.title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
        """)
        
        # Current value
        self.value_label = QLabel(f"0{unit}")
        self.value_label.setStyleSheet(f"""
            color: {color};
            font-size: 16px;
            font-weight: bold;
        """)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.value_label)
        
        layout.addLayout(header_layout)
        layout.addStretch()
        
        # Start update timer - update every 3 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(3000)
    
    def generate_utilization_data(self, nodes_data):
        """Generate utilization data for all nodes"""
        self.utilization_data = {}
        
        for node in nodes_data:
            node_name = node[0]
            
            if self.title == "CPU Usage":
                # CPU utilization between 10-70% for each node
                cpu_cores = float(node[1])
                utilization = random.uniform(10, 70)
                self.utilization_data[node_name] = utilization
                
            elif self.title == "Memory Usage":
                # Memory utilization between 30-80% for each node
                memory_value = float(re.search(r'(\d+)', node[2]).group(1))
                utilization = random.uniform(30, 80)
                self.utilization_data[node_name] = utilization
                
            else:  # Disk Usage
                # Disk utilization between 40-90% for each node
                disk_value = float(re.search(r'(\d+)', node[3]).group(1))
                utilization = random.uniform(40, 90)
                self.utilization_data[node_name] = utilization
        
    def get_node_utilization(self, node_name):
        """Get the utilization percentage for a specific node"""
        if node_name in self.utilization_data:
            return self.utilization_data[node_name]
        return 0

    def set_selected_node(self, node_data, node_name):
        """Set the selected node data"""
        self.selected_node = node_data
        self.node_name = node_name
        self.title_label.setText(f"{self.title} ({node_name})")
        
        # If we already have utilization data for this node, use it
        if node_name in self.utilization_data:
            self.current_value = round(self.utilization_data[node_name], 1)
            self.value_label.setText(f"{self.current_value}{self.unit}")
            
        self.update_data()  # Initial update

    def update_data(self):
        """Update graph data based on selected node information"""
        if not self.selected_node or self.node_name not in self.utilization_data:
            return
        
        # Get the current utilization value for this node
        current_utilization = self.utilization_data[self.node_name]
        
        # Add small variation for visual effect
        variation = random.uniform(-2, 2)
        new_value = current_utilization + variation
        
        # Keep within reasonable bounds for the resource type
        if self.title == "CPU Usage":
            new_value = max(min(new_value, 95), 5)
        elif self.title == "Memory Usage":
            new_value = max(min(new_value, 95), 10)
        else:  # Disk
            new_value = max(min(new_value, 98), 20)
        
        # Update the stored utilization for this node
        self.utilization_data[self.node_name] = new_value
        
        # Update data series
        self.data.append(new_value)
        self.data.pop(0)  # Remove oldest data point
        self.current_value = round(new_value, 1)
        self.value_label.setText(f"{self.current_value}{self.unit}")
        self.update()  # Trigger repaint

    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set up drawing area
        width = self.width() - 32  # Account for margins
        height = 60  # Fixed height for the graph
        bottom = self.height() - 12  # Bottom of the graph
        top = bottom - height  # Top of the graph
        
        # Create gradient for the area under the line
        gradient = QLinearGradient(0, top, 0, bottom)
        base_color = QColor(self.color)
        gradient.setColorAt(0, QColor(base_color.red(), base_color.green(), base_color.blue(), 100))
        gradient.setColorAt(1, QColor(base_color.red(), base_color.green(), base_color.blue(), 5))
        
        # Find min and max values for scaling
        min_value = min(self.data)
        max_value = max(self.data)
        value_range = max(max_value - min_value, 10)  # Ensure a minimum range
        
        # Create path for the line and area
        path = QPainterPath()
        line_path = QPainterPath()
        
        x_step = width / (len(self.data) - 1)
        
        # Start at the first point
        x = 16  # Start with left margin
        y = bottom - ((self.data[0] - min_value) / value_range) * height
        path.moveTo(x, y)
        line_path.moveTo(x, y)
        
        # Add points to the path
        for i in range(1, len(self.data)):
            x = 16 + i * x_step
            y = bottom - ((self.data[i] - min_value) / value_range) * height
            path.lineTo(x, y)
            line_path.lineTo(x, y)
        
        # Complete the fill path
        path.lineTo(x, bottom)
        path.lineTo(16, bottom)
        path.closeSubpath()
        
        # Draw the fill
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        
        # Draw the line
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(self.color), 2))
        painter.drawPath(line_path)
        
        # Draw time indicators
        painter.setPen(QPen(QColor("#6b7280"), 1))
        now = datetime.datetime.now()
        
        # Draw 3 time markers
        times = [
            now - datetime.timedelta(minutes=20),
            now - datetime.timedelta(minutes=10),
            now
        ]
        
        x_positions = [16, 16 + width/2, 16 + width]
        
        for i, t in enumerate(times):
            time_str = t.strftime("%H:%M")
            x = x_positions[i]
            painter.drawText(QRectF(x - 20, bottom + 2, 40, 10), 
                             Qt.AlignmentFlag.AlignCenter, time_str)
            
        # If no node is selected, show a message
        if not self.selected_node:
            painter.setPen(QPen(QColor("#9ca3af")))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Select a node to view metrics")

class SortableTableWidgetItem(QTableWidgetItem):
    """Custom QTableWidgetItem that can be sorted with utilization percentages"""
    def __init__(self, text, value=0, percentage=None):
        super().__init__(text)
        self.value = value
        self.percentage = percentage
        
    def __lt__(self, other):
        if hasattr(other, 'value'):
            return self.value < other.value
        return super().__lt__(other)

class NodesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_row = -1  # No row selected initially
        self.cpu_utilization = {}  # Store CPU utilization for each node
        self.memory_utilization = {}  # Store memory utilization for each node
        self.disk_utilization = {}  # Store disk utilization for each node
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Add graphs at the top
        graphs_layout = QHBoxLayout()
        
        # CPU usage graph
        self.cpu_graph = GraphWidget("CPU Usage", "%", "#FF5733")
        
        # Memory usage graph
        self.mem_graph = GraphWidget("Memory Usage", "%", "#33A8FF")
        
        # Disk usage graph
        self.disk_graph = GraphWidget("Disk Usage", "%", "#8C33FF")
        
        graphs_layout.addWidget(self.cpu_graph)
        graphs_layout.addWidget(self.mem_graph)
        graphs_layout.addWidget(self.disk_graph)
        
        layout.addLayout(graphs_layout)

        # Header section with sorting dropdown
        header = QHBoxLayout()
        title = QLabel("Nodes")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #ffffff;
        """)
        
        items_count = QLabel("4 items")
        items_count.setStyleSheet("""
            color: #9ca3af;
            font-size: 12px;
            margin-left: 8px;
            font-family: 'Segoe UI';
        """)
        items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        header.addWidget(title)
        header.addWidget(items_count)
        header.addStretch()
        
        # Add sorting dropdown
        sort_label = QLabel("Sort by:")
        sort_label.setStyleSheet("""
            color: #e2e8f0;
            font-size: 13px;
            margin-right: 8px;
        """)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Name")
        self.sort_combo.addItem("CPU (Highest)")
        self.sort_combo.addItem("Memory (Highest)")
        self.sort_combo.addItem("Disk (Highest)")
        self.sort_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #e2e8f0;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px 12px;
                min-width: 150px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border-left: none;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #e2e8f0;
                border: 1px solid #444444;
                selection-background-color: #2196F3;
            }
        """)
        
        self.sort_combo.currentTextChanged.connect(self.sort_table)
        
        header.addWidget(sort_label)
        header.addWidget(self.sort_combo)

        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(10)  # Removed checkbox column
        headers = ["Name", "CPU", "Memory", "Disk", "Taints", "Roles", 
                  "Version", "Age", "Conditions", ""]
        self.table.setHorizontalHeaderLabels(headers)
        
        # Style the table
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                border: none;
                gridline-color: #2d2d2d;
                outline: none;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
                outline: none;
            }
            QTableWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 4px;
            }
            QTableWidget::item:selected {
                background-color: rgba(33, 150, 243, 0.2);
                border: none;
            }
            QTableWidget::item:focus {
                border: none;
                outline: none;
                background-color: transparent;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #888888;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #2d2d2d;
                font-size: 12px;
            }
            QToolButton {
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        # Additional table properties
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Disable focus highlighting
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)  # Allow single row selection
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)  # Select entire rows
        
        # Configure table properties
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name column
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(9, 30)  # Width for action column
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        
        # Fixed widths for columns
        column_widths = [None, 120, 140, 140, 80, 120, 100, 80, 120, 40]  # Increased width for CPU/Memory/Disk
        for i, width in enumerate(column_widths):
            if i != 0:  # Skip the Name column which is set to stretch
                if width is not None:
                    self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                    self.table.setColumnWidth(i, width)

        layout.addLayout(header)
        layout.addWidget(self.table)

    def create_action_button(self, row):
        button = QToolButton()
        button.setText("⋮")  # Three dots
        button.setFixedWidth(30)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setStyleSheet("""
            QToolButton {
                color: #888888;
                font-size: 18px;
                background: transparent;
                padding: 2px;
                margin: 0;
                border: none;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
                color: #ffffff;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Create menu with actions
        menu = QMenu(button)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                color: #ffffff;
                padding: 8px 24px 8px 36px;
                border-radius: 4px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: rgba(33, 150, 243, 0.2);
                color: #ffffff;
            }
            QMenu::item[dangerous="true"] {
                color: #ff4444;
            }
            QMenu::item[dangerous="true"]:selected {
                background-color: rgba(255, 68, 68, 0.1);
            }
        """)
        
        # Create actions
        edit_action = menu.addAction("Edit")
        edit_action.setIcon(QIcon("icons/edit.png"))
        edit_action.triggered.connect(lambda: self.handle_action("Edit", row))

        delete_action = menu.addAction("Delete")
        delete_action.setIcon(QIcon("icons/delete.png"))
        delete_action.setProperty("dangerous", True)
        delete_action.triggered.connect(lambda: self.handle_action("Delete", row))

        # View metrics action
        view_metrics = menu.addAction("View Metrics")
        view_metrics.setIcon(QIcon("icons/chart.png"))
        view_metrics.triggered.connect(lambda: self.select_node_for_graphs(row))

        button.setMenu(menu)
        return button

    def handle_action(self, action, row):
        node_name = self.table.item(row, 0).text()
        if action == "Edit":
            print(f"Editing node: {node_name}")
        elif action == "Delete":
            print(f"Deleting node: {node_name}")
    
    def sort_table(self, sort_by):
        """Sort the table based on the selected criteria"""
        if sort_by == "Name":
            self.table.sortItems(0, Qt.SortOrder.AscendingOrder)
        elif sort_by == "CPU (Highest)":
            self.table.sortItems(1, Qt.SortOrder.DescendingOrder)
        elif sort_by == "Memory (Highest)":
            self.table.sortItems(2, Qt.SortOrder.DescendingOrder)
        elif sort_by == "Disk (Highest)":
            self.table.sortItems(3, Qt.SortOrder.DescendingOrder)
           
    def load_data(self):
        self.nodes_data = [
            ["docker-desktop", "2.0", "4 GiB", "20 GB", "0", "control-plane",
             "v1.30.2", "69d", "Running"],
            ["worker-node-1", "4.0", "8 GiB", "50 GB", "1", "worker",
             "v1.30.2", "45d", "Running"],
            ["worker-node-2", "4.0", "8 GiB", "50 GB", "0", "worker",
             "v1.30.2", "45d", "Running"],
            ["storage-node-1", "8.0", "16 GiB", "500 GB", "1", "storage",
             "v1.30.2", "30d", "Running"]
        ]

        # Generate utilization data for all nodes
        self.cpu_graph.generate_utilization_data(self.nodes_data)
        self.mem_graph.generate_utilization_data(self.nodes_data)
        self.disk_graph.generate_utilization_data(self.nodes_data)

        self.table.setRowCount(len(self.nodes_data))
        
        for row, node in enumerate(self.nodes_data):
            node_name = node[0]
            
            # Add node data columns
            for col, value in enumerate(node):
                # For resource columns, add the utilization percentage
                if col == 1:  # CPU column
                    cpu_utilization = self.cpu_graph.get_node_utilization(node_name)
                    display_text = f"{value} ({cpu_utilization:.1f}%)"
                    item = SortableTableWidgetItem(display_text, cpu_utilization)
                elif col == 2:  # Memory column
                    mem_utilization = self.mem_graph.get_node_utilization(node_name)
                    display_text = f"{value} ({mem_utilization:.1f}%)"
                    item = SortableTableWidgetItem(display_text, mem_utilization)
                elif col == 3:  # Disk column
                    disk_utilization = self.disk_graph.get_node_utilization(node_name)
                    display_text = f"{value} ({disk_utilization:.1f}%)"
                    item = SortableTableWidgetItem(display_text, disk_utilization)
                else:
                    item = QTableWidgetItem(value)
                
                # Set alignment based on column
                if col in [1, 2, 3, 4, 7]:  # CPU, Memory, Disk, Taints, Age columns
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                # Apply styling - all text same color except conditions
                if col == 8 and value == "Running":
                    item.setForeground(QColor("#4CAF50"))
                else:
                    item.setForeground(QColor("#e2e8f0"))
                
                self.table.setItem(row, col, item)
            
            # Add action button
            action_button = self.create_action_button(row)
            self.table.setCellWidget(row, 9, action_button)
            
        # Add click handler for rows
        self.table.cellClicked.connect(self.handle_row_click)
        
    def select_node_for_graphs(self, row):
        """Select a node and update graphs to show its metrics"""
        self.selected_row = row
        
        # Get the node name from the current table (might be reordered due to sorting)
        node_name = self.table.item(row, 0).text()
        
        # Find the original node data
        node_data = None
        for node in self.nodes_data:
            if node[0] == node_name:
                node_data = node
                break
        
        if not node_data:
            return
        
        # Highlight the selected row
        self.table.selectRow(row)
        
        # Update graphs with the selected node data
        self.cpu_graph.set_selected_node(node_data, node_name)
        self.mem_graph.set_selected_node(node_data, node_name)
        self.disk_graph.set_selected_node(node_data, node_name)
        
        print(f"Selected node for metrics: {node_name}")
        
    def handle_row_click(self, row, column):
        if column != 9:  # Don't trigger for action button column
            # Select the node for graphs when row is clicked
            self.select_node_for_graphs(row)