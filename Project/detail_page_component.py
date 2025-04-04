# # Create this file as detail_page_component.py
# from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
#                            QPushButton, QTabWidget, QScrollArea, QFrame, QSplitter,
#                            QListWidget, QListWidgetItem, QGraphicsDropShadowEffect)
# from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QRect
# from PyQt6.QtGui import QColor, QFont

# from UI.Styles import AppColors, AppStyles

# class ResourceDetailPage(QWidget):
#     """A detail page that slides in from the right when a table item is clicked"""
    
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.parent_window = parent
#         self.is_visible = False
        
#         # Set default fixed width and the height to match parent
#         self.setFixedWidth(450)
        
#         # Track initial mouse position for dragging
#         self.drag_position = None
#         self.drag_enabled = False
#         self.drag_width = 450  # Default width
#         self.min_width = 400   # Minimum allowed width
#         self.max_width = 800   # Maximum allowed width
        
#         # Variables to store resource metadata
#         self.resource_name_text = ""
#         self.resource_type_text = ""
        
#         # Setup UI after initializing variables
#         self.setup_ui()
        
#         # Set initial position (off-screen to the right)
#         self.hide()
    
#     def setup_ui(self):
#         # Apply shadow effect
#         shadow = QGraphicsDropShadowEffect(self)
#         shadow.setBlurRadius(20)
#         shadow.setColor(QColor(0, 0, 0, 80))
#         shadow.setOffset(-5, 0)
#         self.setGraphicsEffect(shadow)
        
#         # Style the widget with borders
#         self.setStyleSheet(f"""
#             background-color: {AppColors.BG_SIDEBAR};
#             border-left: 1px solid {AppColors.BORDER_COLOR};
#         """)
        
#         # Main layout
#         self.main_layout = QVBoxLayout(self)
#         self.main_layout.setContentsMargins(0, 0, 0, 0)
#         self.main_layout.setSpacing(0)
        
#         # Create header with back button and title
#         self.header = QWidget()
#         self.header.setFixedHeight(60)
#         self.header.setStyleSheet(f"""
#             background-color: {AppColors.BG_HEADER};
#             border-bottom: 1px solid {AppColors.BORDER_COLOR};
#         """)
        
#         header_layout = QHBoxLayout(self.header)
#         header_layout.setContentsMargins(15, 10, 15, 10)
        
#         # Create back button
#         self.back_btn = QPushButton("←")
#         self.back_btn.setFixedSize(40, 40)
#         self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
#         self.back_btn.setStyleSheet("""
#             QPushButton {
#                 background-color: transparent;
#                 color: #8e9ba9;
#                 font-size: 18px;
#                 font-weight: bold;
#                 border: 1px solid #3a3e42;
#                 border-radius: 20px;
#             }
#             QPushButton:hover {
#                 background-color: #3a3e42;
#                 color: #ffffff;
#             }
#         """)
#         self.back_btn.clicked.connect(self.hide_detail)
        
#         # Create title label
#         self.title_label = QLabel("Resource Details")
#         self.title_label.setStyleSheet("""
#             color: #ffffff;
#             font-size: 16px;
#             font-weight: bold;
#             margin-left: 10px;
#         """)
        
#         # Add widgets to header layout
#         header_layout.addWidget(self.back_btn)
#         header_layout.addWidget(self.title_label)
#         header_layout.addStretch()
        
#         # Add header to main layout
#         self.main_layout.addWidget(self.header)
        
#         # Create content layout with resize handle on the left
#         content_layout = QHBoxLayout()
#         content_layout.setContentsMargins(0, 0, 0, 0)
#         content_layout.setSpacing(0)
        
#         # Resize handle
#         self.resize_handle = QWidget()
#         self.resize_handle.setFixedWidth(5)
#         self.resize_handle.setCursor(Qt.CursorShape.SizeHorCursor)
#         self.resize_handle.setStyleSheet("background-color: transparent;")
#         self.resize_handle.mousePressEvent = self.resize_mouse_press
#         self.resize_handle.mouseMoveEvent = self.resize_mouse_move
#         self.resize_handle.mouseReleaseEvent = self.resize_mouse_release
        
#         # Add resize handle to content layout
#         content_layout.addWidget(self.resize_handle)
        
#         # Create tabs container
#         tabs_container = QWidget()
#         tabs_layout = QVBoxLayout(tabs_container)
#         tabs_layout.setContentsMargins(0, 0, 0, 0)
        
#         # Tab widget for details, yaml, events
#         self.tabs = QTabWidget()
#         self.tabs.setStyleSheet(AppStyles.MAIN_STYLE)
        
#         # Create tabs
#         self.detail_tab = self.create_detail_tab()
#         self.yaml_tab = self.create_yaml_tab()
#         self.events_tab = self.create_events_tab()
        
#         self.tabs.addTab(self.detail_tab, "Details")
#         self.tabs.addTab(self.yaml_tab, "YAML")
#         self.tabs.addTab(self.events_tab, "Events")
        
#         # Add tabs to tabs container
#         tabs_layout.addWidget(self.tabs)
        
#         # Add tabs container to content layout
#         content_layout.addWidget(tabs_container)
        
#         # Add content layout to main layout
#         self.main_layout.addLayout(content_layout)
    
#     def create_detail_tab(self):
#         """Create detail tab with resource information"""
#         scroll = QScrollArea()
#         scroll.setWidgetResizable(True)
#         scroll.setFrameShape(QFrame.Shape.NoFrame)
        
#         content = QWidget()
#         layout = QVBoxLayout(content)
#         layout.setContentsMargins(20, 20, 20, 20)
#         layout.setSpacing(10)
        
#         # Resource summary section
#         summary_section = QWidget()
#         summary_layout = QVBoxLayout(summary_section)
#         summary_layout.setContentsMargins(0, 0, 0, 20)
        
#         # Add resource name heading
#         self.resource_name_label = QLabel("Resource Name")
#         self.resource_name_label.setStyleSheet("""
#             font-size: 20px;
#             font-weight: bold;
#             color: #ffffff;
#         """)
        
#         # Add resource type and namespace
#         self.resource_info_label = QLabel("Resource Type | default namespace")
#         self.resource_info_label.setStyleSheet("""
#             font-size: 14px;
#             color: #8e9ba9;
#             margin-bottom: 10px;
#         """)
        
#         # Add creation time
#         creation_time = QLabel("Created 2 days ago (Mar 1, 2023 09:12:30)")
#         creation_time.setStyleSheet("""
#             font-size: 13px;
#             color: #8e9ba9;
#         """)
        
#         summary_layout.addWidget(self.resource_name_label)
#         summary_layout.addWidget(self.resource_info_label)
#         summary_layout.addWidget(creation_time)
        
#         # Divider
#         divider1 = QFrame()
#         divider1.setFrameShape(QFrame.Shape.HLine)
#         divider1.setStyleSheet(f"background-color: {AppColors.BORDER_COLOR};")
        
#         # Status section
#         status_section = QWidget()
#         status_layout = QVBoxLayout(status_section)
#         status_layout.setContentsMargins(0, 20, 0, 20)
        
#         # Section title
#         status_title = QLabel("STATUS")
#         status_title.setStyleSheet("""
#             font-size: 12px;
#             font-weight: bold;
#             color: #8e9ba9;
#             text-transform: uppercase;
#         """)
        
#         # Status info
#         status_info = QHBoxLayout()
        
#         status_value = QLabel("Running")
#         status_value.setStyleSheet("""
#             font-size: 14px;
#             font-weight: bold;
#             color: #4CAF50;  /* Green for running */
#         """)
        
#         status_text = QLabel("3/3 replicas available")
#         status_text.setStyleSheet("""
#             font-size: 14px;
#             color: #ffffff;
#             margin-left: 10px;
#         """)
        
#         status_info.addWidget(status_value)
#         status_info.addWidget(status_text)
#         status_info.addStretch()
        
#         status_layout.addWidget(status_title)
#         status_layout.addLayout(status_info)
        
#         # Divider
#         divider2 = QFrame()
#         divider2.setFrameShape(QFrame.Shape.HLine)
#         divider2.setStyleSheet(f"background-color: {AppColors.BORDER_COLOR};")
        
#         # Conditions section
#         conditions_section = QWidget()
#         conditions_layout = QVBoxLayout(conditions_section)
#         conditions_layout.setContentsMargins(0, 20, 0, 20)
        
#         # Section title
#         conditions_title = QLabel("CONDITIONS")
#         conditions_title.setStyleSheet("""
#             font-size: 12px;
#             font-weight: bold;
#             color: #8e9ba9;
#             text-transform: uppercase;
#         """)
        
#         # Conditions list (would be populated dynamically)
#         conditions_layout.addWidget(conditions_title)
        
#         conditions = [
#             {"type": "Available", "status": "True", "message": "Deployment has minimum availability."},
#             {"type": "Progressing", "status": "True", "message": "ReplicaSet is progressing with new replicas."}
#         ]
        
#         for condition in conditions:
#             condition_row = QHBoxLayout()
            
#             condition_type = QLabel(condition["type"])
#             condition_type.setFixedWidth(120)
#             condition_type.setStyleSheet("""
#                 font-size: 14px;
#                 color: #ffffff;
#             """)
            
#             condition_status = QLabel(condition["status"])
#             condition_status.setFixedWidth(60)
#             if condition["status"] == "True":
#                 condition_status.setStyleSheet("color: #4CAF50; font-size: 14px;")  # Green
#             else:
#                 condition_status.setStyleSheet("color: #FF5252; font-size: 14px;")  # Red
            
#             condition_message = QLabel(condition["message"])
#             condition_message.setStyleSheet("""
#                 font-size: 14px;
#                 color: #8e9ba9;
#                 margin-left: 10px;
#             """)
#             condition_message.setWordWrap(True)
            
#             condition_row.addWidget(condition_type)
#             condition_row.addWidget(condition_status)
#             condition_row.addWidget(condition_message)
            
#             conditions_layout.addLayout(condition_row)
        
#         # Divider
#         divider3 = QFrame()
#         divider3.setFrameShape(QFrame.Shape.HLine)
#         divider3.setStyleSheet(f"background-color: {AppColors.BORDER_COLOR};")
        
#         # Labels section
#         labels_section = QWidget()
#         labels_layout = QVBoxLayout(labels_section)
#         labels_layout.setContentsMargins(0, 20, 0, 20)
        
#         # Section title
#         labels_title = QLabel("LABELS")
#         labels_title.setStyleSheet("""
#             font-size: 12px;
#             font-weight: bold;
#             color: #8e9ba9;
#             text-transform: uppercase;
#         """)
        
#         # Labels list
#         labels_content = QLabel("app: nginx\napp.kubernetes.io/name: nginx\ntier: frontend")
#         labels_content.setStyleSheet("""
#             font-family: 'Consolas', 'Courier New', monospace;
#             font-size: 14px;
#             color: #ffffff;
#             margin-top: 10px;
#         """)
        
#         labels_layout.addWidget(labels_title)
#         labels_layout.addWidget(labels_content)
        
#         # Add all sections to main layout
#         layout.addWidget(summary_section)
#         layout.addWidget(divider1)
#         layout.addWidget(status_section)
#         layout.addWidget(divider2)
#         layout.addWidget(conditions_section)
#         layout.addWidget(divider3)
#         layout.addWidget(labels_section)
#         layout.addStretch()
        
#         scroll.setWidget(content)
#         return scroll
    
#     def create_yaml_tab(self):
#         """Create YAML tab with resource configuration"""
#         scroll = QScrollArea()
#         scroll.setWidgetResizable(True)
#         scroll.setFrameShape(QFrame.Shape.NoFrame)
        
#         content = QWidget()
#         layout = QVBoxLayout(content)
#         layout.setContentsMargins(0, 0, 0, 0)
        
#         # YAML content
#         yaml_text = QLabel("""apiVersion: apps/v1
# kind: Deployment
# metadata:
#   name: nginx-deployment
#   namespace: default
#   labels:
#     app: nginx
#     app.kubernetes.io/name: nginx
#     tier: frontend
# spec:
#   replicas: 3
#   selector:
#     matchLabels:
#       app: nginx
#   template:
#     metadata:
#       labels:
#         app: nginx
#     spec:
#       containers:
#       - name: nginx
#         image: nginx:1.14.2
#         ports:
#         - containerPort: 80
#         resources:
#           limits:
#             cpu: 500m
#             memory: 512Mi
#           requests:
#             cpu: 200m
#             memory: 256Mi
# status:
#   availableReplicas: 3
#   conditions:
#   - lastTransitionTime: "2023-03-01T09:12:35Z"
#     lastUpdateTime: "2023-03-01T09:12:35Z"
#     message: Deployment has minimum availability.
#     reason: MinimumReplicasAvailable
#     status: "True"
#     type: Available
#   - lastTransitionTime: "2023-03-01T09:12:30Z"
#     lastUpdateTime: "2023-03-01T09:12:35Z"
#     message: ReplicaSet "nginx-deployment-66b6c48dd5" has successfully progressed.
#     reason: NewReplicaSetAvailable
#     status: "True"
#     type: Progressing
#   observedGeneration: 1
#   readyReplicas: 3
#   replicas: 3
#   updatedReplicas: 3""")
        
#         yaml_text.setStyleSheet("""
#             font-family: 'Consolas', 'Courier New', monospace;
#             font-size: 13px;
#             color: #E0E0E0;
#             padding: 20px;
#             background-color: #1e1e1e;
#         """)
#         yaml_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
#         layout.addWidget(yaml_text)
#         scroll.setWidget(content)
#         return scroll
    
#     def create_events_tab(self):
#         """Create Events tab with resource events"""
#         scroll = QScrollArea()
#         scroll.setWidgetResizable(True)
#         scroll.setFrameShape(QFrame.Shape.NoFrame)
        
#         content = QWidget()
#         layout = QVBoxLayout(content)
#         layout.setContentsMargins(20, 20, 20, 20)
        
#         # Events list
#         events_list = QListWidget()
#         events_list.setStyleSheet("""
#             QListWidget {
#                 background-color: #1e1e1e;
#                 border: none;
#                 padding: 5px;
#             }
#             QListWidget::item {
#                 border-bottom: 1px solid #333;
#                 padding: 10px;
#             }
#             QListWidget::item:hover {
#                 background-color: rgba(255, 255, 255, 0.05);
#             }
#         """)
        
#         # Sample events (would be populated dynamically)
#         events = [
#             {"type": "Normal", "reason": "ScalingReplicaSet", "age": "2d", "message": "Scaled up replica set nginx-deployment-66b6c48dd5 to 3"},
#             {"type": "Normal", "reason": "SuccessfulCreate", "age": "2d", "message": "Created pod: nginx-deployment-66b6c48dd5-7vz5h"},
#             {"type": "Normal", "reason": "SuccessfulCreate", "age": "2d", "message": "Created pod: nginx-deployment-66b6c48dd5-9xf8z"},
#             {"type": "Normal", "reason": "SuccessfulCreate", "age": "2d", "message": "Created pod: nginx-deployment-66b6c48dd5-thklf"}
#         ]
        
#         for event in events:
#             item = QListWidgetItem()
            
#             # Create custom event item widget
#             event_widget = QWidget()
#             event_layout = QVBoxLayout(event_widget)
#             event_layout.setContentsMargins(0, 5, 0, 5)
            
#             # Event header (type, reason, age)
#             header_layout = QHBoxLayout()
            
#             event_type = QLabel(event["type"])
#             if event["type"] == "Normal":
#                 event_type.setStyleSheet("color: #4CAF50; font-weight: bold;")  # Green
#             else:
#                 event_type.setStyleSheet("color: #FF5252; font-weight: bold;")  # Red
            
#             event_reason = QLabel(event["reason"])
#             event_reason.setStyleSheet("color: #4A9EFF; font-weight: bold;")
            
#             event_age = QLabel(event["age"])
#             event_age.setStyleSheet("color: #8e9ba9;")
            
#             header_layout.addWidget(event_type)
#             header_layout.addWidget(event_reason)
#             header_layout.addStretch()
#             header_layout.addWidget(event_age)
            
#             # Event message
#             event_message = QLabel(event["message"])
#             event_message.setStyleSheet("color: #E0E0E0;")
#             event_message.setWordWrap(True)
            
#             event_layout.addLayout(header_layout)
#             event_layout.addWidget(event_message)
            
#             # Set the custom widget for this item
#             item.setSizeHint(event_widget.sizeHint())
#             events_list.addItem(item)
#             events_list.setItemWidget(item, event_widget)
        
#         layout.addWidget(events_list)
#         scroll.setWidget(content)
#         return scroll
    
#     def show_detail(self, resource_type, resource_name):
#         """Show detail page with animation and populate data"""
#         if self.is_visible:
#             return
            
#         self.is_visible = True
        
#         # Store the resource metadata
#         self.resource_type_text = resource_type
#         self.resource_name_text = resource_name
        
#         # Update labels with resource info
#         self.title_label.setText(f"{resource_type} Details")
#         self.resource_name_label.setText(resource_name)
#         self.resource_info_label.setText(f"{resource_type} | default namespace")
        
#         # Show the widget before animation
#         self.show()
        
#         # Get parent widget dimensions to calculate animation
#         parent_width = self.parent_window.width()
        
#         # Set the starting position (off-screen to the right)
#         self.move(parent_width, 0)
#         self.setFixedHeight(self.parent_window.height())
        
#         # Get the available width for our panel
#         available_width = parent_width
#         target_x = available_width - self.width()
        
#         # Create slide in animation from right
#         self.animation = QPropertyAnimation(self, b"pos")
#         self.animation.setDuration(300)
#         self.animation.setStartValue(QPoint(parent_width, 0))
#         self.animation.setEndValue(QPoint(target_x, 0))
#         self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
#         self.animation.start()
    
#     def hide_detail(self):
#         """Hide detail page with animation"""
#         if not self.is_visible:
#             return
            
#         self.is_visible = False
        
#         # Get parent widget dimensions to calculate animation
#         parent_width = self.parent_window.width()
        
#         # Create slide out animation to the right
#         self.animation = QPropertyAnimation(self, b"pos")
#         self.animation.setDuration(300)
#         self.animation.setStartValue(self.pos())
#         self.animation.setEndValue(QPoint(parent_width, 0))
#         self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
#         # Hide widget when animation finishes
#         self.animation.finished.connect(self.hide)
#         self.animation.start()
    
#     def toggle_detail(self):
#         """Toggle detail page visibility"""
#         if self.is_visible:
#             self.hide_detail()
#         else:
#             self.show_detail("Resource", "default-resource")
    
#     # Resize handle mouse events
#     def resize_mouse_press(self, event):
#         """Handle mouse press on resize handle"""
#         if event.button() == Qt.MouseButton.LeftButton:
#             self.drag_enabled = True
#             self.drag_position = event.globalPosition().toPoint()
#             event.accept()
#         else:
#             event.ignore()
    
#     def resize_mouse_move(self, event):
#         """Handle mouse move for resizing the panel"""
#         if self.drag_enabled and hasattr(self, 'drag_position'):
#             delta = event.globalPosition().toPoint() - self.drag_position
#             new_width = self.width() - delta.x()
            
#             # Constrain width between min and max
#             if new_width < self.min_width:
#                 new_width = self.min_width
#             elif new_width > self.max_width:
#                 new_width = self.max_width
            
#             # Update width and position
#             parent_width = self.parent_window.width()
            
#             self.setFixedWidth(new_width)
#             self.move(parent_width - new_width, 0)
            
#             # Update drag position
#             self.drag_position = event.globalPosition().toPoint()
#             event.accept()
#         else:
#             event.ignore()
    
#     def resize_mouse_release(self, event):
#         """Handle mouse release after resizing"""
#         self.drag_enabled = False
#         event.accept()





from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QTabWidget, QScrollArea, QFrame, QSplitter,
                           QListWidget, QListWidgetItem, QGraphicsDropShadowEffect, QProgressBar)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QRect, pyqtSlot
from PyQt6.QtGui import QColor, QFont

from UI.Styles import AppColors, AppStyles
import json
import yaml
import datetime

class ResourceDetailPage(QWidget):
    """A detail page that slides in from the right when a table item is clicked"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.is_visible = False
        
        # Set default fixed width and the height to match parent
        self.setFixedWidth(450)
        
        # Track initial mouse position for dragging
        self.drag_position = None
        self.drag_enabled = False
        self.drag_width = 450  # Default width
        self.min_width = 400   # Minimum allowed width
        self.max_width = 800   # Maximum allowed width
        
        # Variables to store resource metadata
        self.resource_name_text = ""
        self.resource_type_text = ""
        self.resource_namespace = "default"
        self.resource_data = {}
        
        # Setup UI after initializing variables
        self.setup_ui()
        
        # Set initial position (off-screen to the right)
        self.hide()
    
    def setup_ui(self):
        # Apply shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(-5, 0)
        self.setGraphicsEffect(shadow)
        
        # Style the widget with borders
        self.setStyleSheet(f"""
            background-color: {AppColors.BG_SIDEBAR};
            border-left: 1px solid {AppColors.BORDER_COLOR};
        """)
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create header with back button and title
        self.header = QWidget()
        self.header.setFixedHeight(60)
        self.header.setStyleSheet(f"""
            background-color: {AppColors.BG_HEADER};
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
        """)
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        # Create back button
        self.back_btn = QPushButton("←")
        self.back_btn.setFixedSize(40, 40)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8e9ba9;
                font-size: 18px;
                font-weight: bold;
                border: 1px solid #3a3e42;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #3a3e42;
                color: #ffffff;
            }
        """)
        self.back_btn.clicked.connect(self.hide_detail)
        
        # Create title label
        self.title_label = QLabel("Resource Details")
        self.title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
            margin-left: 10px;
        """)
        
        # Loading indicator for when we're fetching data
        self.loading_indicator = QProgressBar()
        self.loading_indicator.setFixedSize(100, 5)
        self.loading_indicator.setTextVisible(False)
        self.loading_indicator.setRange(0, 0)  # Indeterminate mode
        self.loading_indicator.setStyleSheet("""
            QProgressBar {
                background-color: #2d2d2d;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #0095ff;
            }
        """)
        self.loading_indicator.hide()
        
        # Add widgets to header layout
        header_layout.addWidget(self.back_btn)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.loading_indicator)
        
        # Add header to main layout
        self.main_layout.addWidget(self.header)
        
        # Create content layout with resize handle on the left
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Resize handle
        self.resize_handle = QWidget()
        self.resize_handle.setFixedWidth(5)
        self.resize_handle.setCursor(Qt.CursorShape.SizeHorCursor)
        self.resize_handle.setStyleSheet("background-color: transparent;")
        self.resize_handle.mousePressEvent = self.resize_mouse_press
        self.resize_handle.mouseMoveEvent = self.resize_mouse_move
        self.resize_handle.mouseReleaseEvent = self.resize_mouse_release
        
        # Add resize handle to content layout
        content_layout.addWidget(self.resize_handle)
        
        # Create tabs container
        tabs_container = QWidget()
        tabs_layout = QVBoxLayout(tabs_container)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget for details, yaml, events
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(AppStyles.MAIN_STYLE)
        
        # Create tabs
        self.detail_tab = self.create_detail_tab()
        self.yaml_tab = self.create_yaml_tab()
        self.events_tab = self.create_events_tab()
        
        self.tabs.addTab(self.detail_tab, "Details")
        self.tabs.addTab(self.yaml_tab, "YAML")
        self.tabs.addTab(self.events_tab, "Events")
        
        # Add tabs to tabs container
        tabs_layout.addWidget(self.tabs)
        
        # Add tabs container to content layout
        content_layout.addWidget(tabs_container)
        
        # Add content layout to main layout
        self.main_layout.addLayout(content_layout)
    
    def create_detail_tab(self):
        """Create detail tab with resource information"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        self.detail_layout = QVBoxLayout(content)
        self.detail_layout.setContentsMargins(20, 20, 20, 20)
        self.detail_layout.setSpacing(10)
        
        # Resource summary section
        summary_section = QWidget()
        summary_layout = QVBoxLayout(summary_section)
        summary_layout.setContentsMargins(0, 0, 0, 20)
        
        # Add resource name heading
        self.resource_name_label = QLabel("Resource Name")
        self.resource_name_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #ffffff;
        """)
        
        # Add resource type and namespace
        self.resource_info_label = QLabel("Resource Type | default namespace")
        self.resource_info_label.setStyleSheet("""
            font-size: 14px;
            color: #8e9ba9;
            margin-bottom: 10px;
        """)
        
        # Add creation time
        self.creation_time_label = QLabel("Created 2 days ago (Mar 1, 2023 09:12:30)")
        self.creation_time_label.setStyleSheet("""
            font-size: 13px;
            color: #8e9ba9;
        """)
        
        summary_layout.addWidget(self.resource_name_label)
        summary_layout.addWidget(self.resource_info_label)
        summary_layout.addWidget(self.creation_time_label)
        
        # Divider
        divider1 = QFrame()
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet(f"background-color: {AppColors.BORDER_COLOR};")
        
        # Status section
        status_section = QWidget()
        self.status_layout = QVBoxLayout(status_section)
        self.status_layout.setContentsMargins(0, 20, 0, 20)
        
        # Section title
        status_title = QLabel("STATUS")
        status_title.setStyleSheet("""
            font-size: 12px;
            font-weight: bold;
            color: #8e9ba9;
            text-transform: uppercase;
        """)
        
        # Status info
        status_info = QHBoxLayout()
        
        self.status_value = QLabel("Running")
        self.status_value.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #4CAF50;  /* Green for running */
        """)
        
        self.status_text = QLabel("3/3 replicas available")
        self.status_text.setStyleSheet("""
            font-size: 14px;
            color: #ffffff;
            margin-left: 10px;
        """)
        
        status_info.addWidget(self.status_value)
        status_info.addWidget(self.status_text)
        status_info.addStretch()
        
        self.status_layout.addWidget(status_title)
        self.status_layout.addLayout(status_info)
        
        # Divider
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet(f"background-color: {AppColors.BORDER_COLOR};")
        
        # Conditions section
        conditions_section = QWidget()
        self.conditions_layout = QVBoxLayout(conditions_section)
        self.conditions_layout.setContentsMargins(0, 20, 0, 20)
        
        # Section title
        conditions_title = QLabel("CONDITIONS")
        conditions_title.setStyleSheet("""
            font-size: 12px;
            font-weight: bold;
            color: #8e9ba9;
            text-transform: uppercase;
        """)
        
        self.conditions_layout.addWidget(conditions_title)
        
        # Divider
        divider3 = QFrame()
        divider3.setFrameShape(QFrame.Shape.HLine)
        divider3.setStyleSheet(f"background-color: {AppColors.BORDER_COLOR};")
        
        # Labels section
        labels_section = QWidget()
        self.labels_layout = QVBoxLayout(labels_section)
        self.labels_layout.setContentsMargins(0, 20, 0, 20)
        
        # Section title
        labels_title = QLabel("LABELS")
        labels_title.setStyleSheet("""
            font-size: 12px;
            font-weight: bold;
            color: #8e9ba9;
            text-transform: uppercase;
        """)
        
        # Labels list
        self.labels_content = QLabel("")
        self.labels_content.setStyleSheet("""
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 14px;
            color: #ffffff;
            margin-top: 10px;
        """)
        
        self.labels_layout.addWidget(labels_title)
        self.labels_layout.addWidget(self.labels_content)
        
        # Add all sections to main layout
        self.detail_layout.addWidget(summary_section)
        self.detail_layout.addWidget(divider1)
        self.detail_layout.addWidget(status_section)
        self.detail_layout.addWidget(divider2)
        self.detail_layout.addWidget(conditions_section)
        self.detail_layout.addWidget(divider3)
        self.detail_layout.addWidget(labels_section)
        self.detail_layout.addStretch()
        
        scroll.setWidget(content)
        return scroll
    
    def create_yaml_tab(self):
        """Create YAML tab with resource configuration"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # YAML content
        self.yaml_text = QLabel("")
        self.yaml_text.setStyleSheet("""
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13px;
            color: #E0E0E0;
            padding: 20px;
            background-color: #1e1e1e;
        """)
        self.yaml_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.yaml_text.setWordWrap(True)
        
        layout.addWidget(self.yaml_text)
        scroll.setWidget(content)
        return scroll
    
    def create_events_tab(self):
        """Create Events tab with resource events"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Events list
        self.events_list = QListWidget()
        self.events_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                padding: 5px;
            }
            QListWidget::item {
                border-bottom: 1px solid #333;
                padding: 10px;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        
        layout.addWidget(self.events_list)
        scroll.setWidget(content)
        return scroll
    
    def show_detail(self, resource_type, resource_name):
        """Show detail page with animation and populate data"""
        if self.is_visible:
            return
            
        self.is_visible = True
        
        # Store the resource metadata
        self.resource_type_text = resource_type
        self.resource_name_text = resource_name
        
        # Update labels with resource info
        self.title_label.setText(f"{resource_type} Details")
        self.resource_name_label.setText(resource_name)
        self.resource_info_label.setText(f"{resource_type} | {self.resource_namespace}")
        
        # Show loading indicator
        self.loading_indicator.show()
        
        # Show the widget before animation
        self.show()
        
        # Get parent widget dimensions to calculate animation
        parent_width = self.parent_window.width()
        
        # Set the starting position (off-screen to the right)
        self.move(parent_width, 0)
        self.setFixedHeight(self.parent_window.height())
        
        # Get the available width for our panel
        available_width = parent_width
        target_x = available_width - self.width()
        
        # Create slide in animation from right
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setStartValue(QPoint(parent_width, 0))
        self.animation.setEndValue(QPoint(target_x, 0))
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()
    
    def hide_detail(self):
        """Hide detail page with animation"""
        if not self.is_visible:
            return
            
        self.is_visible = False
        
        # Get parent widget dimensions to calculate animation
        parent_width = self.parent_window.width()
        
        # Create slide out animation to the right
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(QPoint(parent_width, 0))
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Hide widget when animation finishes
        self.animation.finished.connect(self.hide)
        self.animation.start()
    
    def toggle_detail(self):
        """Toggle detail page visibility"""
        if self.is_visible:
            self.hide_detail()
        else:
            self.show_detail("Resource", "default-resource")
    
    @pyqtSlot(dict)
    def update_resource_data(self, data):
        """Update the detail page with resource data"""
        # Hide loading indicator
        self.loading_indicator.hide()
        
        if not data:
            return
        
        self.resource_data = data
        
        # Update resource metadata
        resource_type = data.get("kind", self.resource_type_text)
        resource_name = data.get("metadata", {}).get("name", self.resource_name_text)
        namespace = data.get("metadata", {}).get("namespace", "default")
        self.resource_namespace = namespace
        
        # Update labels with resource info
        self.title_label.setText(f"{resource_type} Details")
        self.resource_name_label.setText(resource_name)
        self.resource_info_label.setText(f"{resource_type} | {namespace}")
        
        # Format creation timestamp to human-readable format
        creation_timestamp = data.get("metadata", {}).get("creationTimestamp")
        if creation_timestamp:
            try:
                # Parse ISO 8601 timestamp
                created_time = datetime.datetime.fromisoformat(creation_timestamp.replace('Z', '+00:00'))
                now = datetime.datetime.now(datetime.timezone.utc)
                diff = now - created_time
                
                days = diff.days
                if days > 0:
                    time_diff = f"{days} days ago"
                else:
                    hours = diff.seconds // 3600
                    if hours > 0:
                        time_diff = f"{hours} hours ago"
                    else:
                        minutes = (diff.seconds % 3600) // 60
                        time_diff = f"{minutes} minutes ago"
                
                formatted_time = created_time.strftime("%b %d, %Y %H:%M:%S")
                self.creation_time_label.setText(f"Created {time_diff} ({formatted_time})")
            except Exception as e:
                self.creation_time_label.setText(f"Created on {creation_timestamp}")
        
        # Update status section
        self.update_status_section(data)
        
        # Update conditions section
        self.update_conditions_section(data)
        
        # Update labels section
        self.update_labels_section(data)
        
        # Update YAML tab
        self.update_yaml_tab(data)
        
        # Update events tab
        self.update_events_tab(data)
    
    def update_status_section(self, data):
        """Update the status section with resource data"""
        status = data.get("status", {})
        
        # Different resources have different status formats
        resource_type = data.get("kind", "").lower()
        
        if resource_type == "pod":
            # For Pods
            phase = status.get("phase", "Unknown")
            self.status_value.setText(phase)
            
            # Set color based on phase
            if phase == "Running":
                self.status_value.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
            elif phase in ["Pending", "ContainerCreating"]:
                self.status_value.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFC107;")
            elif phase in ["Succeeded", "Completed"]:
                self.status_value.setStyleSheet("font-size: 14px; font-weight: bold; color: #2196F3;")
            else:
                self.status_value.setStyleSheet("font-size: 14px; font-weight: bold; color: #FF5252;")
            
            # Show ready containers
            ready_containers = 0
            total_containers = 0
            
            container_statuses = status.get("containerStatuses", [])
            total_containers = len(container_statuses)
            
            for container in container_statuses:
                if container.get("ready", False):
                    ready_containers += 1
            
            self.status_text.setText(f"{ready_containers}/{total_containers} containers ready")
            
        elif resource_type in ["deployment", "replicaset", "statefulset", "daemonset"]:
            # For workload controllers
            available_replicas = status.get("availableReplicas", 0)
            desired_replicas = status.get("replicas", 0)
            
            # Set status value based on readiness
            if available_replicas == desired_replicas and desired_replicas > 0:
                self.status_value.setText("Available")
                self.status_value.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
            elif available_replicas > 0:
                self.status_value.setText("Partially Available")
                self.status_value.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFC107;")
            else:
                self.status_value.setText("Not Available")
                self.status_value.setStyleSheet("font-size: 14px; font-weight: bold; color: #FF5252;")
            
            self.status_text.setText(f"{available_replicas}/{desired_replicas} replicas available")
            
        elif resource_type == "service":
            # For Services
            type_value = data.get("spec", {}).get("type", "ClusterIP")
            cluster_ip = data.get("spec", {}).get("clusterIP", "None")
            external_ip = "None"
            
            if type_value == "LoadBalancer":
                ingress = status.get("loadBalancer", {}).get("ingress", [])
                if ingress:
                    external_ip = ingress[0].get("ip", "Pending")
            
            self.status_value.setText(type_value)
            self.status_value.setStyleSheet("font-size: 14px; font-weight: bold; color: #2196F3;")
            
            if type_value == "LoadBalancer" and external_ip == "Pending":
                self.status_text.setText(f"ClusterIP: {cluster_ip}, External IP: Pending")
            else:
                self.status_text.setText(f"ClusterIP: {cluster_ip}")
            
        else:
            # Generic status (fallback)
            self.status_value.setText("Active")
            self.status_value.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
            self.status_text.setText("")
    
    def update_conditions_section(self, data):
        """Update the conditions section with resource data"""
        # Clear previous conditions
        for i in reversed(range(1, self.conditions_layout.count())):
            widget = self.conditions_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Get conditions from resource data
        conditions = data.get("status", {}).get("conditions", [])
        
        if not conditions:
            # Show "No conditions" message if none found
            no_conditions = QLabel("No conditions found")
            no_conditions.setStyleSheet("color: #8e9ba9; font-size: 14px;")
            self.conditions_layout.addWidget(no_conditions)
            return
        
        # Add each condition
        for condition in conditions:
            condition_row = QHBoxLayout()
            
            condition_type = QLabel(condition.get("type", "Unknown"))
            condition_type.setFixedWidth(120)
            condition_type.setStyleSheet("""
                font-size: 14px;
                color: #ffffff;
            """)
            
            condition_status = QLabel(condition.get("status", "Unknown"))
            condition_status.setFixedWidth(60)
            if condition.get("status") == "True":
                condition_status.setStyleSheet("color: #4CAF50; font-size: 14px;")  # Green
            else:
                condition_status.setStyleSheet("color: #FF5252; font-size: 14px;")  # Red
            
            condition_message = QLabel(condition.get("message", "No message"))
            condition_message.setStyleSheet("""
                font-size: 14px;
                color: #8e9ba9;
                margin-left: 10px;
            """)
            condition_message.setWordWrap(True)
            
            condition_row.addWidget(condition_type)
            condition_row.addWidget(condition_status)
            condition_row.addWidget(condition_message)
            
            # Wrap the row layout in a widget to add to the main layout
            condition_widget = QWidget()
            condition_widget.setLayout(condition_row)
            self.conditions_layout.addWidget(condition_widget)
    
    def update_labels_section(self, data):
        """Update the labels section with resource data"""
        # Get labels from resource data
        labels = data.get("metadata", {}).get("labels", {})
        
        if not labels:
            self.labels_content.setText("No labels found")
            return
        
        # Format labels as text
        labels_text = ""
        for key, value in labels.items():
            labels_text += f"{key}: {value}\n"
        
        self.labels_content.setText(labels_text.strip())
    
    def update_yaml_tab(self, data):
        """Update the YAML tab with resource data"""
        if not data:
            self.yaml_text.setText("No YAML data available")
            return
        
        try:
            # Convert dict to YAML
            yaml_str = yaml.dump(data, default_flow_style=False)
            self.yaml_text.setText(yaml_str)
        except Exception as e:
            self.yaml_text.setText(f"Error converting to YAML: {str(e)}")
    
    def update_events_tab(self, data):
        """Update the events tab with resource events"""
        # Clear events list
        self.events_list.clear()
        
        # Check if events are available in the data
        events = data.get("events", [])
        
        if not events:
            # Show placeholder item
            item = QListWidgetItem("No events found")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.events_list.addItem(item)
            return
        
        # Add events to list
        for event in events:
            item = QListWidgetItem()
            
            # Create custom event item widget
            event_widget = QWidget()
            event_layout = QVBoxLayout(event_widget)
            event_layout.setContentsMargins(0, 5, 0, 5)
            
            # Event header (type, reason, age)
            header_layout = QHBoxLayout()
            
            event_type = QLabel(event.get("type", "Normal"))
            if event.get("type") == "Warning":
                event_type.setStyleSheet("color: #FFC107; font-weight: bold;")
            else:
                event_type.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
            event_reason = QLabel(event.get("reason", "Unknown"))
            event_reason.setStyleSheet("color: #4A9EFF; font-weight: bold;")
            
            event_age = QLabel(event.get("age", "Unknown"))
            event_age.setStyleSheet("color: #8e9ba9;")
            
            header_layout.addWidget(event_type)
            header_layout.addWidget(event_reason)
            header_layout.addStretch()
            header_layout.addWidget(event_age)
            
            # Event message
            event_message = QLabel(event.get("message", "No message"))
            event_message.setStyleSheet("color: #E0E0E0;")
            event_message.setWordWrap(True)
            
            event_layout.addLayout(header_layout)
            event_layout.addWidget(event_message)
            
            # Set the custom widget for this item
            item.setSizeHint(event_widget.sizeHint())
            self.events_list.addItem(item)
            self.events_list.setItemWidget(item, event_widget)
    
    # Resize handle mouse events
    def resize_mouse_press(self, event):
        """Handle mouse press on resize handle"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_enabled = True
            self.drag_position = event.globalPosition().toPoint()
            event.accept()
        else:
            event.ignore()
    
    def resize_mouse_move(self, event):
        """Handle mouse move for resizing the panel"""
        if self.drag_enabled and hasattr(self, 'drag_position'):
            delta = event.globalPosition().toPoint() - self.drag_position
            new_width = self.width() - delta.x()
            
            # Constrain width between min and max
            if new_width < self.min_width:
                new_width = self.min_width
            elif new_width > self.max_width:
                new_width = self.max_width
            
            # Update width and position
            parent_width = self.parent_window.width()
            
            self.setFixedWidth(new_width)
            self.move(parent_width - new_width, 0)
            
            # Update drag position
            self.drag_position = event.globalPosition().toPoint()
            event.accept()
        else:
            event.ignore()
    
    def resize_mouse_release(self, event):
        """Handle mouse release after resizing"""
        self.drag_enabled = False
        event.accept()