# from PyQt6.QtWidgets import (
#     QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
#     QLabel, QHeaderView, QToolButton, QMenu, QCheckBox, QFrame, 
#     QGraphicsDropShadowEffect, QSizePolicy, QStyleOptionButton, QStyle, QStyleOptionHeader, QApplication
# )
# from PyQt6.QtCore import Qt, QTimer, QRect, QRectF, pyqtSignal
# from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QLinearGradient, QPainterPath, QBrush, QCursor
# import random, datetime, re

# #------------------------------------------------------------------
# # GraphWidget (unchanged)
# #------------------------------------------------------------------
# class GraphWidget(QFrame):
#     """Custom widget for displaying resource utilization graphs"""
#     def __init__(self, title, unit, color, parent=None):
#         super().__init__(parent)
#         self.title = title
#         self.unit = unit
#         self.color = color
#         self.data = [0] * 24  # Initialize with zeros
#         self.current_value = 0
#         self.selected_node = None  # Will store the selected node data
#         self.node_name = "None"
#         self.utilization_data = {}  # Store utilization data for all nodes

#         self.setMinimumHeight(120)
#         self.setMaximumHeight(120)
#         self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

#         self.setStyleSheet(f"""
#             QFrame {{
#                 background-color: #1e1e1e;
#                 border-radius: 4px;
#                 border: 1px solid #2d2d2d;
#             }}
#         """)

#         shadow = QGraphicsDropShadowEffect(self)
#         shadow.setBlurRadius(15)
#         shadow.setOffset(0, 2)
#         shadow.setColor(QColor(0, 0, 0, 80))
#         self.setGraphicsEffect(shadow)

#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(16, 12, 16, 12)

#         header_layout = QHBoxLayout()
#         self.title_label = QLabel(f"{title} (No node selected)")
#         self.title_label.setStyleSheet("""
#             color: #ffffff;
#             font-size: 14px;
#             font-weight: bold;
#         """)
#         self.value_label = QLabel(f"0{unit}")
#         self.value_label.setStyleSheet(f"""
#             color: {color};
#             font-size: 16px;
#             font-weight: bold;
#         """)
#         header_layout.addWidget(self.title_label)
#         header_layout.addStretch()
#         header_layout.addWidget(self.value_label)
#         layout.addLayout(header_layout)
#         layout.addStretch()

#         self.timer = QTimer(self)
#         self.timer.timeout.connect(self.update_data)
#         self.timer.start(3000)

#     def generate_utilization_data(self, nodes_data):
#         self.utilization_data = {}
#         for node in nodes_data:
#             node_name = node[0]
#             if self.title == "CPU Usage":
#                 utilization = random.uniform(10, 70)
#                 self.utilization_data[node_name] = utilization
#             elif self.title == "Memory Usage":
#                 utilization = random.uniform(30, 80)
#                 self.utilization_data[node_name] = utilization
#             else:  # Disk Usage
#                 utilization = random.uniform(40, 90)
#                 self.utilization_data[node_name] = utilization

#     def get_node_utilization(self, node_name):
#         return self.utilization_data.get(node_name, 0)

#     def set_selected_node(self, node_data, node_name):
#         self.selected_node = node_data
#         self.node_name = node_name
#         self.title_label.setText(f"{self.title} ({node_name})")
#         if node_name in self.utilization_data:
#             self.current_value = round(self.utilization_data[node_name], 1)
#             self.value_label.setText(f"{self.current_value}{self.unit}")
#         self.update_data()

#     def update_data(self):
#         if not self.selected_node or self.node_name not in self.utilization_data:
#             return
#         current_utilization = self.utilization_data[self.node_name]
#         variation = random.uniform(-2, 2)
#         new_value = current_utilization + variation
#         if self.title == "CPU Usage":
#             new_value = max(min(new_value, 95), 5)
#         elif self.title == "Memory Usage":
#             new_value = max(min(new_value, 95), 10)
#         else:
#             new_value = max(min(new_value, 98), 20)
#         self.utilization_data[self.node_name] = new_value
#         self.data.append(new_value)
#         self.data.pop(0)
#         self.current_value = round(new_value, 1)
#         self.value_label.setText(f"{self.current_value}{self.unit}")
#         self.update()

#     def paintEvent(self, event):
#         super().paintEvent(event)
#         painter = QPainter(self)
#         painter.setRenderHint(QPainter.RenderHint.Antialiasing)
#         width = self.width() - 32
#         height = 60
#         bottom = self.height() - 12
#         top = bottom - height
#         gradient = QLinearGradient(0, top, 0, bottom)
#         base_color = QColor(self.color)
#         gradient.setColorAt(0, QColor(base_color.red(), base_color.green(), base_color.blue(), 100))
#         gradient.setColorAt(1, QColor(base_color.red(), base_color.green(), base_color.blue(), 5))
#         min_value = min(self.data)
#         max_value = max(self.data)
#         value_range = max(max_value - min_value, 10)
#         path = QPainterPath()
#         line_path = QPainterPath()
#         x_step = width / (len(self.data) - 1)
#         x = 16
#         y = bottom - ((self.data[0] - min_value) / value_range) * height
#         path.moveTo(x, y)
#         line_path.moveTo(x, y)
#         for i in range(1, len(self.data)):
#             x = 16 + i * x_step
#             y = bottom - ((self.data[i] - min_value) / value_range) * height
#             path.lineTo(x, y)
#             line_path.lineTo(x, y)
#         path.lineTo(x, bottom)
#         path.lineTo(16, bottom)
#         path.closeSubpath()
#         painter.setBrush(QBrush(gradient))
#         painter.setPen(Qt.PenStyle.NoPen)
#         painter.drawPath(path)
#         painter.setBrush(Qt.BrushStyle.NoBrush)
#         painter.setPen(QPen(QColor(self.color), 2))
#         painter.drawPath(line_path)
#         painter.setPen(QPen(QColor("#6b7280"), 1))
#         now = datetime.datetime.now()
#         times = [now - datetime.timedelta(minutes=20),
#                  now - datetime.timedelta(minutes=10),
#                  now]
#         x_positions = [16, 16 + width/2, 16 + width]
#         for i, t in enumerate(times):
#             time_str = t.strftime("%H:%M")
#             x = x_positions[i]
#             painter.drawText(QRectF(x - 20, bottom + 2, 40, 10),
#                              Qt.AlignmentFlag.AlignCenter, time_str)
#         if not self.selected_node:
#             painter.setPen(QPen(QColor("#9ca3af")))
#             painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Select a node to view metrics")

# #------------------------------------------------------------------
# # Custom table item for numeric sorting
# #------------------------------------------------------------------
# class SortableTableWidgetItem(QTableWidgetItem):
#     def __init__(self, text, value=None):
#         super().__init__(text)
#         self.value = value

#     def __lt__(self, other):
#         if isinstance(other, SortableTableWidgetItem) and self.value is not None and other.value is not None:
#             return self.value < other.value
#         return super().__lt__(other)

# #------------------------------------------------------------------
# # CustomHeader: Only columns 1-4 are sortable; shows a hover sort indicator arrow.
# #------------------------------------------------------------------
# class CustomHeader(QHeaderView):
#     """
#     A custom header that only enables sorting for a subset of columns (defined in self.sortable_columns)
#     and shows a hover sort indicator arrow on those columns.
#     """
#     def __init__(self, orientation, parent=None):
#         super().__init__(orientation, parent)
#         # Only these columns will be sortable (for example: columns 1-4)
#         self.sortable_columns = {1, 2, 3, 4}
#         self.setSectionsClickable(True)
#         self.setHighlightSections(True)

#         # Set default alignment to center for all sections
#         self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

#     def mousePressEvent(self, event):
#         logicalIndex = self.logicalIndexAt(event.pos())
#         if logicalIndex in self.sortable_columns:
#             super().mousePressEvent(event)
#         else:
#             event.ignore()

#     def paintSection(self, painter, rect, logicalIndex):
#         option = QStyleOptionHeader()
#         self.initStyleOption(option)
#         option.rect = rect
#         option.section = logicalIndex
#         # Retrieve header text from the model and set it in the option.
#         header_text = self.model().headerData(logicalIndex, self.orientation(), Qt.ItemDataRole.DisplayRole)
#         option.text = str(header_text) if header_text is not None else ""

#         # Set text alignment to center
#         option.textAlignment = Qt.AlignmentFlag.AlignCenter

#         if logicalIndex in self.sortable_columns:
#             mouse_pos = QCursor.pos()
#             local_mouse = self.mapFromGlobal(mouse_pos)
#             if rect.contains(local_mouse):
#                 option.state |= QStyle.StateFlag.State_MouseOver
#                 # Use the Qt6 enum value for sort indicator (SortDown for descending)
#                 option.sortIndicator = QStyleOptionHeader.SortIndicator.SortDown
#                 option.state |= QStyle.StateFlag.State_Sunken
#             else:
#                 option.state &= ~QStyle.StateFlag.State_MouseOver
#         else:
#             option.state &= ~QStyle.StateFlag.State_MouseOver

#         self.style().drawControl(QStyle.ControlElement.CE_Header, option, painter, self)

# #------------------------------------------------------------------
# # NodesPage with fixed row height, responsive columns, header-based sorting,
# # and header-based sort only on specific columns (via CustomHeader)
# #------------------------------------------------------------------
# class NodesPage(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.selected_row = -1
#         self.selected_nodes = set()  # Track checked nodes
#         self.select_all_checkbox = None  # Store reference to select-all checkbox
#         self.setup_ui()
#         self.load_data()
#         self.installEventFilter(self)

#     def setup_ui(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(16, 16, 16, 16)
#         layout.setSpacing(16)

#         # Graphs (CPU, Memory, Disk)
#         graphs_layout = QHBoxLayout()
#         self.cpu_graph = GraphWidget("CPU Usage", "%", "#FF5733")
#         self.mem_graph = GraphWidget("Memory Usage", "%", "#33A8FF")
#         self.disk_graph = GraphWidget("Disk Usage", "%", "#8C33FF")
#         graphs_layout.addWidget(self.cpu_graph)
#         graphs_layout.addWidget(self.mem_graph)
#         graphs_layout.addWidget(self.disk_graph)
#         layout.addLayout(graphs_layout)

#         # Header: Title and item count (sorting handled via header clicks)
#         header_layout = QHBoxLayout()
#         title = QLabel("Nodes")
#         title.setStyleSheet("""
#             font-size: 20px;
#             font-weight: bold;
#             color: #ffffff;
#         """)
#         self.items_count = QLabel("0 items")
#         self.items_count.setStyleSheet("""
#             color: #9ca3af;
#             font-size: 12px;
#             margin-left: 8px;
#             font-family: 'Segoe UI';
#         """)
#         self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)
#         header_layout.addWidget(title)
#         header_layout.addWidget(self.items_count)
#         header_layout.addStretch()
#         layout.addLayout(header_layout)

#         # Table setup: 11 columns
#         self.table = QTableWidget()
#         self.table.setColumnCount(11)
#         headers = ["", "Name", "CPU", "Memory", "Disk", "Taints", "Roles", "Version", "Age", "Conditions", ""]
#         self.table.setHorizontalHeaderLabels(headers)
#         custom_header = CustomHeader(Qt.Orientation.Horizontal, self.table)
#         self.table.setHorizontalHeader(custom_header)
#         self.table.setSortingEnabled(True)
#         self.table.setStyleSheet("""
#             QTableWidget {
#                 background-color: #1e1e1e;
#                 border: none;
#                 gridline-color: #2d2d2d;
#                 outline: none;
#             }
#             QTableWidget::item {
#                 padding: 8px;
#                 border: none;
#                 outline: none;
#             }
#             QTableWidget::item:selected {
#                 background-color: rgba(33, 150, 243, 0.2);
#                 border: none;
#             }
#             QHeaderView::section {
#                 background-color: #252525;
#                 color: #888888;
#                 padding: 8px;
#                 border: none;
#                 border-bottom: 1px solid #2d2d2d;
#                 font-size: 12px;
#                 text-align: center;
#             }
#             QHeaderView::section:hover {
#                 background-color: #2d2d2d;
#             }
#         """)
#         self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
#         self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
#         self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

#         # Fixed row height and disable vertical resizing
#         self.table.verticalHeader().setVisible(False)
#         self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
#         self.table.verticalHeader().setDefaultSectionSize(40)

#         # Set the checkbox column fixed and let other columns stretch responsively
#         self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
#         self.table.setColumnWidth(0, 40)
#         for col in range(1, self.table.columnCount()):
#             self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

#         # Remove the horizontal scroll bar
#         self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

#         # "Select all" checkbox in header column 0
#         select_all_checkbox = self.create_select_all_checkbox()
#         self.set_header_widget(0, select_all_checkbox)

#         # Override mouse press to handle selection
#         self.table.mousePressEvent = self.custom_table_mousePressEvent

#         layout.addWidget(self.table)

#     def custom_table_mousePressEvent(self, event):
#         index = self.table.indexAt(event.pos())
#         if index.isValid():
#             row = index.row()

#             self.table.selectRow(row)
#             QTableWidget.mousePressEvent(self.table, event)
#         else:
#             self.table.clearSelection()
#             QTableWidget.mousePressEvent(self.table, event)

#     def eventFilter(self, obj, event):
#         if event.type() == event.Type.MouseButtonPress:
#             if not self.table.geometry().contains(event.pos()):
#                 self.table.clearSelection()
#         return super().eventFilter(obj, event)

#     #------- Checkbox Helpers -------
#     def create_checkbox(self, row, node_name):
#         checkbox = QCheckBox()
#         checkbox.setStyleSheet("""
#             QCheckBox {
#                 spacing: 5px;
#                 background: transparent;
#             }
#             QCheckBox::indicator {
#                 width: 16px;
#                 height: 16px;
#                 border: 2px solid #666666;
#                 border-radius: 3px;
#                 background: transparent;
#             }
#             QCheckBox::indicator:checked {
#                 background-color: #0095ff;
#                 border-color: #0095ff;
#             }
#             QCheckBox::indicator:hover {
#                 border-color: #888888;
#             }
#         """)
#         checkbox.stateChanged.connect(lambda s: self.handle_checkbox_change(s, node_name))
#         return checkbox

#     def create_checkbox_container(self, row, node_name):
#         container = QWidget()
#         container.setStyleSheet("background-color: transparent;")
#         layout = QHBoxLayout(container)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         checkbox = self.create_checkbox(row, node_name)
#         layout.addWidget(checkbox)
#         return container

#     def handle_checkbox_change(self, state, node_name):
#         if state == Qt.CheckState.Checked.value:
#             self.selected_nodes.add(node_name)
#         else:
#             self.selected_nodes.discard(node_name)
#             if self.select_all_checkbox is not None and self.select_all_checkbox.isChecked():
#                 # Block signals to prevent infinite recursion
#                 self.select_all_checkbox.blockSignals(True)
#                 self.select_all_checkbox.setChecked(False)
#                 self.select_all_checkbox.blockSignals(False)
#         print("Selected nodes:", self.selected_nodes)

#     def create_select_all_checkbox(self):
#         checkbox = QCheckBox()
#         checkbox.setStyleSheet("""
#             QCheckBox {
#                 spacing: 5px;
#                 background-color: #252525;
#             }
#             QCheckBox::indicator {
#                 width: 16px;
#                 height: 16px;
#                 border: 2px solid #666666;
#                 border-radius: 3px;
#                 background: transparent;
#             }
#             QCheckBox::indicator:checked {
#                 background-color: #0095ff;
#                 border-color: #0095ff;
#             }
#             QCheckBox::indicator:hover {
#                 border-color: #888888;
#             }
#         """)
#         checkbox.stateChanged.connect(self.handle_select_all)
#         self.select_all_checkbox = checkbox  # Store reference to the checkbox
#         return checkbox

#     def handle_select_all(self, state):
#         for row in range(self.table.rowCount()):
#             checkbox_container = self.table.cellWidget(row, 0)
#             if checkbox_container:
#                 for child in checkbox_container.children():
#                     if isinstance(child, QCheckBox):
#                         child.setChecked(state == Qt.CheckState.Checked.value)
#                         break

#     def set_header_widget(self, col, widget):
#         header = self.table.horizontalHeader()
#         header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
#         header.resizeSection(col, 40)
#         self.table.setHorizontalHeaderItem(col, QTableWidgetItem(""))
#         container = QWidget()
#         container.setStyleSheet("background-color: #252525;")
#         container_layout = QHBoxLayout(container)
#         container_layout.setContentsMargins(0, 0, 0, 0)
#         container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         container_layout.addWidget(widget)
#         container.setFixedHeight(header.height())
#         container.setParent(header)
#         container.setGeometry(header.sectionPosition(col), 0, header.sectionSize(col), header.height())
#         container.show()

#     #------- Action Menu -------
#     def create_action_button(self, row):
#         button = QToolButton()
#         button.setText("⋮")
#         button.setFixedWidth(30)
#         button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
#         button.setStyleSheet("""
#             QToolButton {
#                 color: #888888;
#                 font-size: 18px;
#                 background: transparent;
#                 padding: 2px;
#                 margin: 0;
#                 border: none;
#                 font-weight: bold;
#             }
#             QToolButton:hover {
#                 background-color: rgba(255, 255, 255, 0.1);
#                 border-radius: 3px;
#                 color: #ffffff;
#             }
#             QToolButton::menu-indicator {
#                 image: none;
#             }
#         """)
#         button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
#         button.setCursor(Qt.CursorShape.PointingHandCursor)
#         menu = QMenu(button)
#         menu.setStyleSheet("""
#             QMenu {
#                 background-color: #2d2d2d;
#                 border: 1px solid #3d3d3d;
#                 border-radius: 4px;
#                 padding: 4px;
#             }
#             QMenu::item {
#                 color: #ffffff;
#                 padding: 8px 24px 8px 36px;
#                 border-radius: 4px;
#                 font-size: 13px;
#             }
#             QMenu::item:selected {
#                 background-color: rgba(33, 150, 243, 0.2);
#                 color: #ffffff;
#             }
#             QMenu::item[dangerous="true"] {
#                 color: #ff4444;
#             }
#             QMenu::item[dangerous="true"]:selected {
#                 background-color: rgba(255, 68, 68, 0.1);
#             }
#         """)
#         edit_action = menu.addAction("Edit")
#         edit_action.setIcon(QIcon("icons/edit.png"))
#         edit_action.triggered.connect(lambda: self.handle_action("Edit", row))
#         delete_action = menu.addAction("Delete")
#         delete_action.setIcon(QIcon("icons/delete.png"))
#         delete_action.setProperty("dangerous", True)
#         delete_action.triggered.connect(lambda: self.handle_action("Delete", row))
#         view_metrics = menu.addAction("View Metrics")
#         view_metrics.setIcon(QIcon("icons/chart.png"))
#         view_metrics.triggered.connect(lambda: self.select_node_for_graphs(row))
#         button.setMenu(menu)
#         return button

#     def handle_action(self, action, row):
#         node_name = self.table.item(row, 1).text()
#         if action == "Edit":
#             print(f"Editing node: {node_name}")
#         elif action == "Delete":
#             print(f"Deleting node: {node_name}")

#     #------- Data Loading -------
#     def load_data(self):
#         self.nodes_data = [
#             ["docker-desktop", "2.0", "4 GiB", "20 GB", "0", "control-plane", "v1.30.2", "69d", "Running"],
#             ["worker-node-1", "4.0", "8 GiB", "50 GB", "1", "worker", "v1.30.2", "45d", "Running"],
#             ["worker-node-2", "4.0", "8 GiB", "50 GB", "0", "worker", "v1.30.2", "45d", "Running"],
#             ["storage-node-1", "8.0", "16 GiB", "500 GB", "1", "storage", "v1.30.2", "30d", "Running"]
#         ]
#         self.table.setRowCount(len(self.nodes_data))
#         # Generate utilization data for graphs
#         self.cpu_graph.generate_utilization_data(self.nodes_data)
#         self.mem_graph.generate_utilization_data(self.nodes_data)
#         self.disk_graph.generate_utilization_data(self.nodes_data)
#         self.selected_nodes = set()

#         for row, node in enumerate(self.nodes_data):
#             # Column 0: Checkbox
#             checkbox_container = self.create_checkbox_container(row, node[0])
#             self.table.setCellWidget(row, 0, checkbox_container)
#             # Column 1: Name
#             item_name = QTableWidgetItem(node[0])
#             item_name.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
#             item_name.setForeground(QColor("#e2e8f0"))
#             item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
#             self.table.setItem(row, 1, item_name)
#             # Column 2: CPU with utilization from graph
#             cpu_util = self.cpu_graph.get_node_utilization(node[0])
#             display_cpu = f"{node[1]} ({cpu_util:.1f}%)"
#             item_cpu = SortableTableWidgetItem(display_cpu, cpu_util)
#             item_cpu.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#             item_cpu.setForeground(QColor("#e2e8f0"))
#             item_cpu.setFlags(item_cpu.flags() & ~Qt.ItemFlag.ItemIsEditable)
#             self.table.setItem(row, 2, item_cpu)
#             # Column 3: Memory with utilization from graph
#             mem_util = self.mem_graph.get_node_utilization(node[0])
#             display_mem = f"{node[2]} ({mem_util:.1f}%)"
#             item_mem = SortableTableWidgetItem(display_mem, mem_util)
#             item_mem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#             item_mem.setForeground(QColor("#e2e8f0"))
#             item_mem.setFlags(item_mem.flags() & ~Qt.ItemFlag.ItemIsEditable)
#             self.table.setItem(row, 3, item_mem)
#             # Column 4: Disk with utilization from graph
#             disk_util = self.disk_graph.get_node_utilization(node[0])
#             display_disk = f"{node[3]} ({disk_util:.1f}%)"
#             item_disk = SortableTableWidgetItem(display_disk, disk_util)
#             item_disk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#             item_disk.setForeground(QColor("#e2e8f0"))
#             item_disk.setFlags(item_disk.flags() & ~Qt.ItemFlag.ItemIsEditable)
#             self.table.setItem(row, 4, item_disk)
#             # Column 5: Taints
#             item_taints = QTableWidgetItem(node[4])
#             item_taints.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#             item_taints.setForeground(QColor("#e2e8f0"))
#             item_taints.setFlags(item_taints.flags() & ~Qt.ItemFlag.ItemIsEditable)
#             self.table.setItem(row, 5, item_taints)
#             # Column 6: Roles
#             item_roles = QTableWidgetItem(node[5])
#             item_roles.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#             item_roles.setForeground(QColor("#e2e8f0"))
#             item_roles.setFlags(item_roles.flags() & ~Qt.ItemFlag.ItemIsEditable)
#             self.table.setItem(row, 6, item_roles)
#             # Column 7: Version
#             item_version = QTableWidgetItem(node[6])
#             item_version.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#             item_version.setForeground(QColor("#e2e8f0"))
#             item_version.setFlags(item_version.flags() & ~Qt.ItemFlag.ItemIsEditable)
#             self.table.setItem(row, 7, item_version)
#             # Column 8: Age
#             item_age = QTableWidgetItem(node[7])
#             item_age.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#             item_age.setForeground(QColor("#e2e8f0"))
#             item_age.setFlags(item_age.flags() & ~Qt.ItemFlag.ItemIsEditable)
#             self.table.setItem(row, 8, item_age)
#             # Column 9: Conditions
#             item_conditions = QTableWidgetItem(node[8])
#             item_conditions.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#             if node[8] == "Running":
#                 item_conditions.setForeground(QColor("#4CAF50"))
#             else:
#                 item_conditions.setForeground(QColor("#e2e8f0"))
#             item_conditions.setFlags(item_conditions.flags() & ~Qt.ItemFlag.ItemIsEditable)
#             self.table.setItem(row, 9, item_conditions)
#             # Column 10: Action button
#             action_button = self.create_action_button(row)
#             action_container = QWidget()
#             action_layout = QHBoxLayout(action_container)
#             action_layout.setContentsMargins(0, 0, 0, 0)
#             action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
#             action_layout.addWidget(action_button)
#             action_container.setStyleSheet("background-color: transparent;")
#             self.table.setCellWidget(row, 10, action_container)

#         self.table.cellClicked.connect(self.handle_row_click)
#         self.items_count.setText(f"{len(self.nodes_data)} items")

#     def select_node_for_graphs(self, row):
#         self.selected_row = row
#         node_name = self.table.item(row, 1).text()
#         node_data = None
#         for node in self.nodes_data:
#             if node[0] == node_name:
#                 node_data = node
#                 break
#         if not node_data:
#             return
#         self.table.selectRow(row)
#         self.cpu_graph.set_selected_node(node_data, node_name)
#         self.mem_graph.set_selected_node(node_data, node_name)
#         self.disk_graph.set_selected_node(node_data, node_name)
#         print(f"Selected node for metrics: {node_name}")

#     def handle_row_click(self, row, column):
#         if column != 10:
#             # self.select_node_for_graphs(row)
#             pass




from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QToolButton, QMenu, QCheckBox, QFrame, 
    QGraphicsDropShadowEffect, QSizePolicy, QStyleOptionButton, QStyle, QStyleOptionHeader, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QRect, QRectF, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QLinearGradient, QPainterPath, QBrush, QCursor
import datetime

from utils.kubernetes_client import get_kubernetes_client

#------------------------------------------------------------------
# GraphWidget - Updated to use real-time data from Kubernetes API
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

        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1e1e1e;
                border-radius: 4px;
                border: 1px solid #2d2d2d;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"{title} (No node selected)")
        self.title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
        """)
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

    def update_utilization_data(self, node_name, utilization):
        """Update the utilization data for a specific node"""
        self.utilization_data[node_name] = utilization
    
    def get_node_utilization(self, node_name):
        """Get the current utilization value for a node"""
        return self.utilization_data.get(node_name, 0)

    def set_selected_node(self, node_data, node_name):
        """Set the selected node and update the display"""
        self.selected_node = node_data
        self.node_name = node_name
        self.title_label.setText(f"{self.title} ({node_name})")
        
        if node_name in self.utilization_data:
            self.current_value = round(self.utilization_data[node_name], 1)
            self.value_label.setText(f"{self.current_value}{self.unit}")
            
            # Update the data array for the graph
            if isinstance(self.data, list) and len(self.data) > 0:
                # Shift data to the left and add new value
                self.data.append(self.current_value)
                self.data.pop(0)
        
        self.update()

    def update_data(self, history_data=None):
        """Update the graph data with new values"""
        if history_data and isinstance(history_data, list):
            # Replace data with provided history
            self.data = history_data
        elif self.node_name in self.utilization_data:
            # Add current value and shift
            current_utilization = self.utilization_data[self.node_name]
            self.data.append(current_utilization)
            self.data.pop(0)
            self.current_value = round(current_utilization, 1)
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
        painter.setPen(QPen(QColor("#6b7280"), 1))
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
            painter.setPen(QPen(QColor("#9ca3af")))
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
# CustomHeader: Only columns 1-4 are sortable; shows a hover sort indicator arrow.
#------------------------------------------------------------------
class CustomHeader(QHeaderView):
    """
    A custom header that only enables sorting for a subset of columns (defined in self.sortable_columns)
    and shows a hover sort indicator arrow on those columns.
    """
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        # Only these columns will be sortable (for example: columns 1-4)
        self.sortable_columns = {1, 2, 3, 4}
        self.setSectionsClickable(True)
        self.setHighlightSections(True)

        # Set default alignment to center for all sections
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

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
        # Retrieve header text from the model and set it in the option.
        header_text = self.model().headerData(logicalIndex, self.orientation(), Qt.ItemDataRole.DisplayRole)
        option.text = str(header_text) if header_text is not None else ""

        # Set text alignment to center
        option.textAlignment = Qt.AlignmentFlag.AlignCenter

        if logicalIndex in self.sortable_columns:
            mouse_pos = QCursor.pos()
            local_mouse = self.mapFromGlobal(mouse_pos)
            if rect.contains(local_mouse):
                option.state |= QStyle.StateFlag.State_MouseOver
                # Use the Qt6 enum value for sort indicator (SortDown for descending)
                option.sortIndicator = QStyleOptionHeader.SortIndicator.SortDown
                option.state |= QStyle.StateFlag.State_Sunken
            else:
                option.state &= ~QStyle.StateFlag.State_MouseOver
        else:
            option.state &= ~QStyle.StateFlag.State_MouseOver

        self.style().drawControl(QStyle.ControlElement.CE_Header, option, painter, self)

#------------------------------------------------------------------
# NodesPage with real-time data from Kubernetes API
#------------------------------------------------------------------
class NodesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_row = -1
        self.selected_nodes = set()  # Track checked nodes
        self.select_all_checkbox = None  # Store reference to select-all checkbox
        self.nodes_data = []  # Store node data
        
        # Get Kubernetes client instance
        self.kubernetes_client = get_kubernetes_client()
        
        # Connect signals
        self.kubernetes_client.node_metrics_updated.connect(self.update_node_metrics)
        
        self.setup_ui()
        
        # Initialize the graphs and table
        self.load_data()
        
        # Set up metrics update timer
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self.request_node_metrics)
        self.metrics_timer.start(5000)  # Update every 5 seconds
        
        self.installEventFilter(self)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Graphs (CPU, Memory, Disk)
        graphs_layout = QHBoxLayout()
        self.cpu_graph = GraphWidget("CPU Usage", "%", "#FF5733")
        self.mem_graph = GraphWidget("Memory Usage", "%", "#33A8FF")
        self.disk_graph = GraphWidget("Disk Usage", "%", "#8C33FF")
        graphs_layout.addWidget(self.cpu_graph)
        graphs_layout.addWidget(self.mem_graph)
        graphs_layout.addWidget(self.disk_graph)
        layout.addLayout(graphs_layout)

        # Header: Title and item count (sorting handled via header clicks)
        header_layout = QHBoxLayout()
        title = QLabel("Nodes")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #ffffff;
        """)
        self.items_count = QLabel("0 items")
        self.items_count.setStyleSheet("""
            color: #9ca3af;
            font-size: 12px;
            margin-left: 8px;
            font-family: 'Segoe UI';
        """)
        self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(title)
        header_layout.addWidget(self.items_count)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Table setup: 11 columns
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        headers = ["", "Name", "CPU", "Memory", "Disk", "Taints", "Roles", "Version", "Age", "Conditions", ""]
        self.table.setHorizontalHeaderLabels(headers)
        custom_header = CustomHeader(Qt.Orientation.Horizontal, self.table)
        self.table.setHorizontalHeader(custom_header)
        self.table.setSortingEnabled(True)
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
            QTableWidget::item:selected {
                background-color: rgba(33, 150, 243, 0.2);
                border: none;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #888888;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #2d2d2d;
                font-size: 12px;
                text-align: center;
            }
            QHeaderView::section:hover {
                background-color: #2d2d2d;
            }
        """)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Fixed row height and disable vertical resizing
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(40)

        # Set the checkbox column fixed and let other columns stretch responsively
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)
        for col in range(1, self.table.columnCount()):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

        # Remove the horizontal scroll bar
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # "Select all" checkbox in header column 0
        select_all_checkbox = self.create_select_all_checkbox()
        self.set_header_widget(0, select_all_checkbox)

        # Override mouse press to handle selection
        self.table.mousePressEvent = self.custom_table_mousePressEvent
        
        # Connect row clicks to show metrics
        self.table.cellClicked.connect(self.handle_row_click)

        layout.addWidget(self.table)

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

    #------- Checkbox Helpers -------
    def create_checkbox(self, row, node_name):
        checkbox = QCheckBox()
        checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #666666;
                border-radius: 3px;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #0095ff;
                border-color: #0095ff;
            }
            QCheckBox::indicator:hover {
                border-color: #888888;
            }
        """)
        checkbox.stateChanged.connect(lambda s: self.handle_checkbox_change(s, node_name))
        return checkbox

    def create_checkbox_container(self, row, node_name):
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
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
                # Block signals to prevent infinite recursion
                self.select_all_checkbox.blockSignals(True)
                self.select_all_checkbox.setChecked(False)
                self.select_all_checkbox.blockSignals(False)

    def create_select_all_checkbox(self):
        checkbox = QCheckBox()
        checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
                background-color: #252525;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #666666;
                border-radius: 3px;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #0095ff;
                border-color: #0095ff;
            }
            QCheckBox::indicator:hover {
                border-color: #888888;
            }
        """)
        checkbox.stateChanged.connect(self.handle_select_all)
        self.select_all_checkbox = checkbox  # Store reference to the checkbox
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
        container.setStyleSheet("background-color: #252525;")
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
        if row < 0 or row >= len(self.nodes_data):
            return
            
        node_name = self.nodes_data[row].get("name", "")
        if action == "Edit":
            print(f"Editing node: {node_name}")
        elif action == "Delete":
            print(f"Deleting node: {node_name}")

    #------- Data Loading -------
    def load_data(self):
        """Load node data from Kubernetes client"""
        # Get nodes data
        nodes = self.kubernetes_client._get_nodes()
        self.nodes_data = nodes
        
        if not nodes:
            self.items_count.setText("0 items")
            return
            
        self.items_count.setText(f"{len(nodes)} items")
        
        # Initialize the table
        self.table.setRowCount(len(nodes))
        
        # Initialize utilization data for graphs
        self.initialize_graph_data(nodes)
        
        # Check if we already have metrics data stored
        node_resources = self.kubernetes_client._get_node_resources()
        
        # Populate table with node data
        for row, node in enumerate(nodes):
            node_name = node.get("name", "")
            
            # Column 0: Checkbox
            checkbox_container = self.create_checkbox_container(row, node_name)
            self.table.setCellWidget(row, 0, checkbox_container)
            
            # Column 1: Name
            item_name = QTableWidgetItem(node_name)
            item_name.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item_name.setForeground(QColor("#e2e8f0"))
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, item_name)
            
            # Get resource metrics for this node
            node_metric = node_resources.get(node_name, {})
            
            # CPU
            cpu_capacity = node_metric.get("cpu_capacity", 0)
            cpu_used = node_metric.get("cpu_used", 0)
            cpu_percent = (cpu_used / cpu_capacity * 100) if cpu_capacity > 0 else 0
            
            # Update CPU graph data
            self.cpu_graph.update_utilization_data(node_name, cpu_percent)
            
            # Column 2: CPU
            cpu_text = f"{cpu_capacity:.1f} ({cpu_percent:.1f}%)"
            item_cpu = SortableTableWidgetItem(cpu_text, cpu_percent)
            item_cpu.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_cpu.setForeground(QColor("#e2e8f0"))
            item_cpu.setFlags(item_cpu.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, item_cpu)
            
            # Memory
            memory_capacity_gb = node_metric.get("memory_capacity", 0) / (1024 * 1024 * 1024)
            memory_used = node_metric.get("memory_used", 0)
            memory_capacity = node_metric.get("memory_capacity", 0)
            memory_percent = (memory_used / memory_capacity * 100) if memory_capacity > 0 else 0
            
            # Update Memory graph data
            self.mem_graph.update_utilization_data(node_name, memory_percent)
            
            # Column 3: Memory
            memory_text = f"{memory_capacity_gb:.1f} GiB ({memory_percent:.1f}%)"
            item_memory = SortableTableWidgetItem(memory_text, memory_percent)
            item_memory.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_memory.setForeground(QColor("#e2e8f0"))
            item_memory.setFlags(item_memory.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, item_memory)
            
            # Disk (Note: Kubernetes API doesn't provide disk usage directly)
            disk_percent = node_metric.get("disk_usage", 65.5)
            disk_capacity_gb = node_metric.get("disk_capacity", 100)
            
            # Update Disk graph data
            self.disk_graph.update_utilization_data(node_name, disk_percent)
            
            # Column 4: Disk
            disk_text = f"{disk_capacity_gb:.1f} GB ({disk_percent:.1f}%)"
            item_disk = SortableTableWidgetItem(disk_text, disk_percent)
            item_disk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_disk.setForeground(QColor("#e2e8f0"))
            item_disk.setFlags(item_disk.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, item_disk)
            
            # Column 5: Taints
            taints_count = "0"  # Would need to extract this from node data
            item_taints = QTableWidgetItem(taints_count)
            item_taints.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_taints.setForeground(QColor("#e2e8f0"))
            item_taints.setFlags(item_taints.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 5, item_taints)
            
            # Column 6: Roles
            roles = ", ".join(node.get("roles", ["<none>"]))
            item_roles = QTableWidgetItem(roles)
            item_roles.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_roles.setForeground(QColor("#e2e8f0"))
            item_roles.setFlags(item_roles.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 6, item_roles)
            
            # Column 7: Version
            version = node.get("version", "Unknown")
            item_version = QTableWidgetItem(version)
            item_version.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_version.setForeground(QColor("#e2e8f0"))
            item_version.setFlags(item_version.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 7, item_version)
            
            # Column 8: Age
            age = node.get("age", "Unknown")
            item_age = QTableWidgetItem(age)
            item_age.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_age.setForeground(QColor("#e2e8f0"))
            item_age.setFlags(item_age.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 8, item_age)
            
            # Column 9: Conditions
            status = node.get("status", "Unknown")
            item_conditions = QTableWidgetItem(status)
            item_conditions.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if status == "Ready":
                item_conditions.setForeground(QColor("#4CAF50"))
            else:
                item_conditions.setForeground(QColor("#FF5252"))
            item_conditions.setFlags(item_conditions.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 9, item_conditions)
            
            # Column 10: Action button
            action_button = self.create_action_button(row)
            action_container = QWidget()
            action_layout = QHBoxLayout(action_container)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            action_layout.addWidget(action_button)
            action_container.setStyleSheet("background-color: transparent;")
            self.table.setCellWidget(row, 10, action_container)

    def initialize_graph_data(self, nodes):
        """Initialize graph data for all nodes"""
        # Request resources data from client
        node_resources = self.kubernetes_client._get_node_resources()
        
        for node in nodes:
            node_name = node.get("name", "")
            node_metric = node_resources.get(node_name, {})
            
            # CPU utilization
            cpu_capacity = node_metric.get("cpu_capacity", 0)
            cpu_used = node_metric.get("cpu_used", 0)
            cpu_percent = (cpu_used / cpu_capacity * 100) if cpu_capacity > 0 else 0
            self.cpu_graph.update_utilization_data(node_name, cpu_percent)
            
            # Memory utilization
            memory_capacity = node_metric.get("memory_capacity", 0)
            memory_used = node_metric.get("memory_used", 0)
            memory_percent = (memory_used / memory_capacity * 100) if memory_capacity > 0 else 0
            self.mem_graph.update_utilization_data(node_name, memory_percent)
            
            # Disk utilization (estimated)
            disk_percent = node_metric.get("disk_usage", 65.5)
            self.disk_graph.update_utilization_data(node_name, disk_percent)

    def select_node_for_graphs(self, row):
        """Select node for metrics graph display"""
        if row < 0 or row >= len(self.nodes_data):
            return
            
        self.selected_row = row
        node = self.nodes_data[row]
        node_name = node.get("name", "")
        
        if not node_name:
            return
            
        self.table.selectRow(row)
        
        # Set selected node in graphs
        self.cpu_graph.set_selected_node(node, node_name)
        self.mem_graph.set_selected_node(node, node_name)
        self.disk_graph.set_selected_node(node, node_name)
        
        # Request metrics for this node
        self.kubernetes_client.get_node_metrics_async(node_name)

    def handle_row_click(self, row, column):
        """Handle row click event"""
        self.select_node_for_graphs(row)
    
    def request_node_metrics(self):
        """Request updated metrics for the selected node"""
        if self.selected_row >= 0 and self.selected_row < len(self.nodes_data):
            node_name = self.nodes_data[self.selected_row].get("name", "")
            if node_name:
                self.kubernetes_client.get_node_metrics_async(node_name)
    
    @pyqtSlot(dict)
    def update_node_metrics(self, metrics):
        """Handle updated metrics data for a node"""
        if not metrics:
            return
            
        node_name = metrics.get("name", "")
        if not node_name:
            return
            
        # Update CPU graph
        cpu_data = metrics.get("cpu", {})
        if cpu_data:
            usage_percent = cpu_data.get("usage_percent", 0)
            self.cpu_graph.update_utilization_data(node_name, usage_percent)
            
            if hasattr(self.cpu_graph, "node_name") and self.cpu_graph.node_name == node_name:
                history = cpu_data.get("history", [])
                if history:
                    self.cpu_graph.update_data(history)
        
        # Update Memory graph
        memory_data = metrics.get("memory", {})
        if memory_data:
            usage_percent = memory_data.get("usage_percent", 0)
            self.mem_graph.update_utilization_data(node_name, usage_percent)
            
            if hasattr(self.mem_graph, "node_name") and self.mem_graph.node_name == node_name:
                history = memory_data.get("history", [])
                if history:
                    self.mem_graph.update_data(history)
        
        # Update Disk graph
        disk_data = metrics.get("disk", {})
        if disk_data:
            usage_percent = disk_data.get("usage_percent", 0)
            self.disk_graph.update_utilization_data(node_name, usage_percent)
            
            if hasattr(self.disk_graph, "node_name") and self.disk_graph.node_name == node_name:
                history = disk_data.get("history", [])
                if history:
                    self.disk_graph.update_data(history)
        
        # Update table cells for the node if it's in the table
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1) and self.table.item(row, 1).text() == node_name:
                # Update CPU column
                if cpu_data:
                    cpu_capacity = cpu_data.get("capacity", 0)
                    usage_percent = cpu_data.get("usage_percent", 0)
                    cpu_text = f"{cpu_capacity:.1f} ({usage_percent:.1f}%)"
                    
                    cpu_item = SortableTableWidgetItem(cpu_text, usage_percent)
                    cpu_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    cpu_item.setForeground(QColor("#e2e8f0"))
                    cpu_item.setFlags(cpu_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, 2, cpu_item)
                
                # Update Memory column
                if memory_data:
                    memory_capacity_gb = memory_data.get("capacity", 0) / (1024 * 1024 * 1024)
                    usage_percent = memory_data.get("usage_percent", 0)
                    memory_text = f"{memory_capacity_gb:.1f} GiB ({usage_percent:.1f}%)"
                    
                    memory_item = SortableTableWidgetItem(memory_text, usage_percent)
                    memory_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    memory_item.setForeground(QColor("#e2e8f0"))
                    memory_item.setFlags(memory_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, 3, memory_item)
                
                # Update Disk column
                if disk_data:
                    disk_capacity_gb = disk_data.get("capacity", 0)
                    usage_percent = disk_data.get("usage_percent", 0)
                    disk_text = f"{disk_capacity_gb:.1f} GB ({usage_percent:.1f}%)"
                    
                    disk_item = SortableTableWidgetItem(disk_text, usage_percent)
                    disk_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    disk_item.setForeground(QColor("#e2e8f0"))
                    disk_item.setFlags(disk_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, 4, disk_item)
                
                break