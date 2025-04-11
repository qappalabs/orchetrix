from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QToolButton, QMenu, QCheckBox, QFrame, 
    QGraphicsDropShadowEffect, QSizePolicy, QStyleOptionButton, QStyle, QStyleOptionHeader, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QRect, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QLinearGradient, QPainterPath, QBrush, QCursor

from UI.Styles import AppStyles, AppColors
from utils.cluster_connector import get_cluster_connector
import random
import datetime
import re

#------------------------------------------------------------------
# GraphWidget
#------------------------------------------------------------------
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

        self.setMinimumHeight(120)
        self.setMaximumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Apply styles from Styles.py
        self.setStyleSheet(AppStyles.GRAPH_FRAME_STYLE)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"{title} (No node selected)")
        self.title_label.setStyleSheet(AppStyles.GRAPH_TITLE_STYLE)
        self.value_label = QLabel(f"0{unit}")
        self.value_label.setStyleSheet(AppStyles.graph_value_style(self.color))
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.value_label)
        layout.addLayout(header_layout)
        layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(3000)

    def generate_utilization_data(self, nodes_data):
        """Generate or update utilization data for nodes"""
        self.utilization_data = {}
        if not nodes_data:
            return
            
        for node in nodes_data:
            node_name = node.get("name", "unknown")
            
            # Extract utilization data from node info if available
            if self.title == "CPU Usage":
                if "cpu_usage" in node:
                    utilization = float(node.get("cpu_usage", 0))
                else:
                    utilization = random.uniform(10, 70)  # Fallback to random for demo
                self.utilization_data[node_name] = utilization
                    
            elif self.title == "Memory Usage":
                if "memory_usage" in node:
                    utilization = float(node.get("memory_usage", 0))
                else:
                    utilization = random.uniform(30, 80)  # Fallback to random for demo
                self.utilization_data[node_name] = utilization
                
            else:  # Disk Usage
                if "disk_usage" in node:
                    utilization = float(node.get("disk_usage", 0))
                else:
                    utilization = random.uniform(40, 90)  # Fallback to random for demo
                self.utilization_data[node_name] = utilization

    def get_node_utilization(self, node_name):
        return self.utilization_data.get(node_name, 0)

    def set_selected_node(self, node_data, node_name):
        """Set the selected node for this graph"""
        self.selected_node = node_data
        self.node_name = node_name
        self.title_label.setText(f"{self.title} ({node_name})")
        if node_name in self.utilization_data:
            self.current_value = round(self.utilization_data[node_name], 1)
            self.value_label.setText(f"{self.current_value}{self.unit}")
        self.update_data()

    def update_data(self):
        """Update the chart data"""
        if not self.selected_node or self.node_name not in self.utilization_data:
            return
            
        current_utilization = self.utilization_data[self.node_name]
        
        # Add a small variation to simulate real-time changes
        variation = random.uniform(-2, 2)
        new_value = current_utilization + variation
        
        # Keep values within reasonable limits
        if self.title == "CPU Usage":
            new_value = max(min(new_value, 95), 5)
        elif self.title == "Memory Usage":
            new_value = max(min(new_value, 95), 10)
        else:
            new_value = max(min(new_value, 98), 20)
            
        self.utilization_data[self.node_name] = new_value
        self.data.append(new_value)
        self.data.pop(0)
        self.current_value = round(new_value, 1)
        self.value_label.setText(f"{self.current_value}{self.unit}")
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width() - 32
        height = 60
        bottom = self.height() - 12
        top = bottom - height
        gradient = QLinearGradient(0, top, 0, bottom)
        base_color = QColor(self.color)
        gradient.setColorAt(0, QColor(base_color.red(), base_color.green(), base_color.blue(), 100))
        gradient.setColorAt(1, QColor(base_color.red(), base_color.green(), base_color.blue(), 5))
        min_value = min(self.data)
        max_value = max(self.data)
        value_range = max(max_value - min_value, 10)
        path = QPainterPath()
        line_path = QPainterPath()
        x_step = width / (len(self.data) - 1)
        x = 16
        y = bottom - ((self.data[0] - min_value) / value_range) * height
        path.moveTo(x, y)
        line_path.moveTo(x, y)
        for i in range(1, len(self.data)):
            x = 16 + i * x_step
            y = bottom - ((self.data[i] - min_value) / value_range) * height
            path.lineTo(x, y)
            line_path.lineTo(x, y)
        path.lineTo(x, bottom)
        path.lineTo(16, bottom)
        path.closeSubpath()
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(self.color), 2))
        painter.drawPath(line_path)
        painter.setPen(QPen(QColor(AppColors.TEXT_SUBTLE), 1))
        now = datetime.datetime.now()
        times = [now - datetime.timedelta(minutes=20),
                 now - datetime.timedelta(minutes=10),
                 now]
        x_positions = [16, 16 + width/2, 16 + width]
        for i, t in enumerate(times):
            time_str = t.strftime("%H:%M")
            x = x_positions[i]
            painter.drawText(QRectF(x - 20, bottom + 2, 40, 10),
                             Qt.AlignmentFlag.AlignCenter, time_str)
        if not self.selected_node:
            painter.setPen(QPen(QColor(AppColors.TEXT_SUBTLE)))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Select a node to view metrics")

#------------------------------------------------------------------
# Custom table item for numeric sorting
#------------------------------------------------------------------
class SortableTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, value=None):
        super().__init__(text)
        self.value = value

    def __lt__(self, other):
        if isinstance(other, SortableTableWidgetItem) and self.value is not None and other.value is not None:
            return self.value < other.value
        return super().__lt__(other)

#------------------------------------------------------------------
# CustomHeader
#------------------------------------------------------------------
class CustomHeader(QHeaderView):
    """
    A custom header that only enables sorting for a subset of columns (defined in self.sortable_columns)
    and shows a hover sort indicator arrow on those columns.
    """
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.sortable_columns = {1, 2, 3, 4}
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)

    def mousePressEvent(self, event):
        logicalIndex = self.logicalIndexAt(event.pos())
        if logicalIndex in self.sortable_columns:
            super().mousePressEvent(event)
        else:
            event.ignore()

    def paintSection(self, painter, rect, logicalIndex):
        option = QStyleOptionHeader()
        self.initStyleOption(option)
        option.rect = rect
        option.section = logicalIndex
        header_text = self.model().headerData(logicalIndex, self.orientation(), Qt.ItemDataRole.DisplayRole)
        option.text = str(header_text) if header_text is not None else ""
        option.textAlignment = Qt.AlignmentFlag.AlignCenter

        if logicalIndex in self.sortable_columns:
            mouse_pos = QCursor.pos()
            local_mouse = self.mapFromGlobal(mouse_pos)
            if rect.contains(local_mouse):
                option.state |= QStyle.StateFlag.State_MouseOver
                option.sortIndicator = QStyleOptionHeader.SortIndicator.SortDown
                option.state |= QStyle.StateFlag.State_Sunken
            else:
                option.state &= ~QStyle.StateFlag.State_MouseOver
        else:
            option.state &= ~QStyle.StateFlag.State_MouseOver

        self.style().drawControl(QStyle.ControlElement.CE_Header, option, painter, self)

# No Data Available Widget
class NoDataWidget(QWidget):
    """Widget shown when no data is available"""
    def __init__(self, message="No data available", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel("📊")
        icon_label.setStyleSheet("font-size: 48px; color: #666;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        message_label = QLabel(message)
        message_label.setStyleSheet("font-size: 18px; color: #666;")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(icon_label)
        layout.addWidget(message_label)

#------------------------------------------------------------------
# NodesPage
#------------------------------------------------------------------
class NodesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_row = -1
        self.selected_nodes = set()  # Track checked nodes
        self.select_all_checkbox = None  # Store reference to select-all checkbox
        
        # Get the cluster connector
        self.cluster_connector = get_cluster_connector()
        
        # Connect to node data signal
        self.cluster_connector.node_data_loaded.connect(self.update_nodes)
        
        # Initialize data structure
        self.nodes_data = []
        self.has_loaded_data = False  # Track if real data has been loaded
        
        # Set up UI
        self.setup_ui()
        self.installEventFilter(self)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Graphs (CPU, Memory, Disk)
        graphs_layout = QHBoxLayout()
        self.cpu_graph = GraphWidget("CPU Usage", "%", AppColors.ACCENT_ORANGE)
        self.mem_graph = GraphWidget("Memory Usage", "%", AppColors.ACCENT_BLUE)
        self.disk_graph = GraphWidget("Disk Usage", "%", AppColors.ACCENT_PURPLE)
        graphs_layout.addWidget(self.cpu_graph)
        graphs_layout.addWidget(self.mem_graph)
        graphs_layout.addWidget(self.disk_graph)
        layout.addLayout(graphs_layout)

        # Header: Title and item count
        header_layout = QHBoxLayout()
        title = QLabel("Nodes")
        title.setStyleSheet(AppStyles.TITLE_STYLE)
        self.items_count = QLabel("0 items")
        self.items_count.setStyleSheet(AppStyles.ITEMS_COUNT_STYLE)
        self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(title)
        header_layout.addWidget(self.items_count)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Content container - will hold either the table or no-data message
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # Table setup: 11 columns
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        headers = ["", "Name", "CPU", "Memory", "Disk", "Taints", "Roles", "Version", "Age", "Conditions", ""]
        self.table.setHorizontalHeaderLabels(headers)
        custom_header = CustomHeader(Qt.Orientation.Horizontal, self.table)
        self.table.setHorizontalHeader(custom_header)
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Fixed row height and disable vertical resizing
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(40)

        # Set column widths
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)
        for col in range(1, self.table.columnCount() - 1):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(10, 40)

        # Remove the horizontal scroll bar
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # "Select all" checkbox in header column 0
        select_all_checkbox = self.create_select_all_checkbox()
        self.set_header_widget(0, select_all_checkbox)

        # Override mouse press to handle selection
        self.table.mousePressEvent = self.custom_table_mousePressEvent
        
        # Add table to content container
        self.content_layout.addWidget(self.table)
        
        # Create no-data widget but don't add it yet
        self.no_data_widget = NoDataWidget("No node data available. Please connect to a cluster.")
        
        # Initially start with showing table (will be empty but with headers)
        layout.addWidget(self.content_container)
        
        # Connect to table signals
        self.table.cellClicked.connect(self.handle_row_click)
        
        # Show "No data" message instead of empty table initially
        self.show_no_data_message()

    def custom_table_mousePressEvent(self, event):
        index = self.table.indexAt(event.pos())
        if index.isValid():
            row = index.row()
            self.table.selectRow(row)
            QTableWidget.mousePressEvent(self.table, event)
        else:
            self.table.clearSelection()
            QTableWidget.mousePressEvent(self.table, event)

    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress:
            if not self.table.geometry().contains(event.pos()):
                self.table.clearSelection()
        return super().eventFilter(obj, event)
    
    def show_no_data_message(self):
        """Show no data message instead of empty table"""
        # Remove table from layout
        self.table.hide()
        
        # If no_data_widget is not already in layout, add it
        if self.no_data_widget.parent() != self.content_container:
            self.content_layout.addWidget(self.no_data_widget)
        
        self.no_data_widget.show()
    
    def show_table(self):
        """Show the table and hide no data message"""
        # Hide no data widget
        self.no_data_widget.hide()
        
        # Show table
        self.table.show()

    #------- Checkbox Helpers -------
    def create_checkbox(self, row, node_name):
        checkbox = QCheckBox()
        checkbox.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        checkbox.stateChanged.connect(lambda s: self.handle_checkbox_change(s, node_name))
        return checkbox

    def create_checkbox_container(self, row, node_name):
        container = QWidget()
        container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox = self.create_checkbox(row, node_name)
        layout.addWidget(checkbox)
        return container

    def handle_checkbox_change(self, state, node_name):
        if state == Qt.CheckState.Checked.value:
            self.selected_nodes.add(node_name)
        else:
            self.selected_nodes.discard(node_name)
            if self.select_all_checkbox is not None and self.select_all_checkbox.isChecked():
                self.select_all_checkbox.blockSignals(True)
                self.select_all_checkbox.setChecked(False)
                self.select_all_checkbox.blockSignals(False)
        print("Selected nodes:", self.selected_nodes)

    def create_select_all_checkbox(self):
        checkbox = QCheckBox()
        checkbox.setStyleSheet(AppStyles.SELECT_ALL_CHECKBOX_STYLE)
        checkbox.stateChanged.connect(self.handle_select_all)
        self.select_all_checkbox = checkbox
        return checkbox

    def handle_select_all(self, state):
        for row in range(self.table.rowCount()):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                for child in checkbox_container.children():
                    if isinstance(child, QCheckBox):
                        child.setChecked(state == Qt.CheckState.Checked.value)
                        break

    def set_header_widget(self, col, widget):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(col, 40)
        self.table.setHorizontalHeaderItem(col, QTableWidgetItem(""))
        container = QWidget()
        container.setStyleSheet(AppStyles.HEADER_CONTAINER_STYLE)
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(widget)
        container.setFixedHeight(header.height())
        container.setParent(header)
        container.setGeometry(header.sectionPosition(col), 0, header.sectionSize(col), header.height())
        container.show()

    #------- Action Menu -------
    def create_action_button(self, row):
        button = QToolButton()
        button.setText("⋮")
        button.setFixedWidth(30)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        menu = QMenu(button)
        menu.setStyleSheet(AppStyles.MENU_STYLE)
        edit_action = menu.addAction("Edit")
        edit_action.setIcon(QIcon("icons/edit.png"))
        edit_action.triggered.connect(lambda: self.handle_action("Edit", row))
        delete_action = menu.addAction("Delete")
        delete_action.setIcon(QIcon("icons/delete.png"))
        delete_action.setProperty("dangerous", True)
        delete_action.triggered.connect(lambda: self.handle_action("Delete", row))
        view_metrics = menu.addAction("View Metrics")
        view_metrics.setIcon(QIcon("icons/chart.png"))
        view_metrics.triggered.connect(lambda: self.select_node_for_graphs(row))
        button.setMenu(menu)
        return button

    def handle_action(self, action, row):
        node_name = self.table.item(row, 1).text()
        if action == "Edit":
            print(f"Editing node: {node_name}")
        elif action == "Delete":
            print(f"Deleting node: {node_name}")

    #------- Data Loading -------
    def update_nodes(self, nodes_data):
        """Update with real node data from the cluster"""
        if not nodes_data:
            self.nodes_data = []
            self.show_no_data_message()
            return
        
        # Store the node data
        self.nodes_data = nodes_data
        self.has_loaded_data = True
        
        # Make sure we show the table
        self.show_table()
        
        # Generate utilization data for graphs
        self.cpu_graph.generate_utilization_data(nodes_data)
        self.mem_graph.generate_utilization_data(nodes_data)
        self.disk_graph.generate_utilization_data(nodes_data)
        
        # Reset selected nodes
        self.selected_nodes = set()
        
        # Update the table
        self.table.setRowCount(len(nodes_data))
        
        for row, node in enumerate(nodes_data):
            node_name = node.get("name", "unknown")
            
            # Column 0: Checkbox
            checkbox_container = self.create_checkbox_container(row, node_name)
            self.table.setCellWidget(row, 0, checkbox_container)
            
            # Column 1: Name
            item_name = QTableWidgetItem(node_name)
            item_name.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item_name.setForeground(QColor(AppColors.TEXT_TABLE))
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, item_name)
            
            # Column 2: CPU with utilization from graph
            cpu_util = self.cpu_graph.get_node_utilization(node_name)
            cpu_capacity = node.get("cpu_capacity", "")
            display_cpu = f"{cpu_capacity} ({cpu_util:.1f}%)" if cpu_capacity else f"{cpu_util:.1f}%"
            item_cpu = SortableTableWidgetItem(display_cpu, cpu_util)
            item_cpu.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_cpu.setForeground(QColor(AppColors.TEXT_TABLE))
            item_cpu.setFlags(item_cpu.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, item_cpu)
            
            # Column 3: Memory with utilization from graph
            mem_util = self.mem_graph.get_node_utilization(node_name)
            mem_capacity = node.get("memory_capacity", "")
            display_mem = f"{mem_capacity} ({mem_util:.1f}%)" if mem_capacity else f"{mem_util:.1f}%"
            item_mem = SortableTableWidgetItem(display_mem, mem_util)
            item_mem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_mem.setForeground(QColor(AppColors.TEXT_TABLE))
            item_mem.setFlags(item_mem.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, item_mem)
            
            # Column 4: Disk with utilization from graph
            disk_util = self.disk_graph.get_node_utilization(node_name)
            disk_capacity = node.get("disk_capacity", "")
            display_disk = f"{disk_capacity} ({disk_util:.1f}%)" if disk_capacity else f"{disk_util:.1f}%"
            item_disk = SortableTableWidgetItem(display_disk, disk_util)
            item_disk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_disk.setForeground(QColor(AppColors.TEXT_TABLE))
            item_disk.setFlags(item_disk.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, item_disk)
            
            # Column 5: Taints
            taints = node.get("taints", "0")
            item_taints = QTableWidgetItem(str(taints))
            item_taints.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_taints.setForeground(QColor(AppColors.TEXT_TABLE))
            item_taints.setFlags(item_taints.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 5, item_taints)
            
            # Column 6: Roles
            roles = node.get("roles", [])
            if isinstance(roles, list):
                roles_text = ", ".join(roles)
            else:
                roles_text = str(roles)
            item_roles = QTableWidgetItem(roles_text)
            item_roles.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_roles.setForeground(QColor(AppColors.TEXT_TABLE))
            item_roles.setFlags(item_roles.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 6, item_roles)
            
            # Column 7: Version
            version = node.get("version", "Unknown")
            item_version = QTableWidgetItem(version)
            item_version.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_version.setForeground(QColor(AppColors.TEXT_TABLE))
            item_version.setFlags(item_version.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 7, item_version)
            
            # Column 8: Age
            age = node.get("age", "Unknown")
            item_age = QTableWidgetItem(age)
            item_age.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_age.setForeground(QColor(AppColors.TEXT_TABLE))
            item_age.setFlags(item_age.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 8, item_age)
            
            # Column 9: Conditions
            status = node.get("status", "Unknown")
            item_conditions = QTableWidgetItem(status)
            item_conditions.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if status.lower() == "ready":
                item_conditions.setForeground(QColor(AppColors.STATUS_ACTIVE))
            else:
                item_conditions.setForeground(QColor(AppColors.TEXT_TABLE))
            item_conditions.setFlags(item_conditions.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 9, item_conditions)
            
            # Column 10: Action button
            action_button = self.create_action_button(row)
            action_container = QWidget()
            action_layout = QHBoxLayout(action_container)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            action_layout.addWidget(action_button)
            action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
            self.table.setCellWidget(row, 10, action_container)
            
        # Update items count
        self.items_count.setText(f"{len(nodes_data)} items")

    def select_node_for_graphs(self, row):
        """Select a node to show in the graphs"""
        if row < 0 or row >= len(self.nodes_data):
            return
            
        self.selected_row = row
        node_name = self.table.item(row, 1).text()
        node_data = None
        
        # Find the node data
        for node in self.nodes_data:
            if node.get("name") == node_name:
                node_data = node
                break
                
        if not node_data:
            return
            
        self.table.selectRow(row)
        self.cpu_graph.set_selected_node(node_data, node_name)
        self.mem_graph.set_selected_node(node_data, node_name)
        self.disk_graph.set_selected_node(node_data, node_name)
        print(f"Selected node for metrics: {node_name}")

    def handle_row_click(self, row, column):
        if column != 10:  # Don't select when clicking on action menu
            self.select_node_for_graphs(row)