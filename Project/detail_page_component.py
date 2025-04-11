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
        self.setFixedWidth(AppStyles.DETAIL_PAGE_WIDTH)
        
        # Track initial mouse position for dragging
        self.drag_position = None
        self.drag_enabled = False
        self.drag_width = AppStyles.DETAIL_PAGE_WIDTH  # Default width
        self.min_width = AppStyles.DETAIL_PAGE_MIN_WIDTH   # Minimum allowed width
        self.max_width = AppStyles.DETAIL_PAGE_MAX_WIDTH   # Maximum allowed width
        
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
        shadow.setBlurRadius(AppStyles.DETAIL_PAGE_SHADOW_BLUR_RADIUS)
        shadow.setColor(QColor(*AppStyles.DETAIL_PAGE_SHADOW_COLOR))
        shadow.setOffset(AppStyles.DETAIL_PAGE_SHADOW_OFFSET_X, AppStyles.DETAIL_PAGE_SHADOW_OFFSET_Y)
        self.setGraphicsEffect(shadow)
        
        # Style the widget with borders
        self.setStyleSheet(AppStyles.DETAIL_PAGE_STYLE)
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create header with back button and title
        self.header = QWidget()
        self.header.setFixedHeight(AppStyles.DETAIL_PAGE_HEADER_HEIGHT)
        self.header.setStyleSheet(AppStyles.DETAIL_PAGE_HEADER_STYLE)
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(AppStyles.DETAIL_PAGE_HEADER_MARGIN_LEFT, 
                                       AppStyles.DETAIL_PAGE_HEADER_MARGIN_TOP, 
                                       AppStyles.DETAIL_PAGE_HEADER_MARGIN_RIGHT, 
                                       AppStyles.DETAIL_PAGE_HEADER_MARGIN_BOTTOM)
        
        # Create back button
        self.back_btn = QPushButton("←")
        self.back_btn.setFixedSize(AppStyles.DETAIL_PAGE_BACK_BUTTON_SIZE, AppStyles.DETAIL_PAGE_BACK_BUTTON_SIZE)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet(AppStyles.DETAIL_PAGE_BACK_BUTTON_STYLE)
        self.back_btn.clicked.connect(self.hide_detail)
        
        # Create title label
        self.title_label = QLabel("Resource Details")
        self.title_label.setStyleSheet(AppStyles.DETAIL_PAGE_TITLE_STYLE)
        
        # Loading indicator for when we're fetching data
        self.loading_indicator = QProgressBar()
        self.loading_indicator.setFixedSize(AppStyles.DETAIL_PAGE_LOADING_WIDTH, AppStyles.DETAIL_PAGE_LOADING_HEIGHT)
        self.loading_indicator.setTextVisible(False)
        self.loading_indicator.setRange(0, 0)  # Indeterminate mode
        self.loading_indicator.setStyleSheet(AppStyles.DETAIL_PAGE_LOADING_STYLE)
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
        self.resize_handle.setFixedWidth(AppStyles.DETAIL_PAGE_RESIZE_HANDLE_WIDTH)
        self.resize_handle.setCursor(Qt.CursorShape.SizeHorCursor)
        self.resize_handle.setStyleSheet(AppStyles.DETAIL_PAGE_RESIZE_HANDLE_STYLE)
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
        self.detail_layout.setContentsMargins(AppStyles.DETAIL_PAGE_CONTENT_MARGIN, 
                                            AppStyles.DETAIL_PAGE_CONTENT_MARGIN, 
                                            AppStyles.DETAIL_PAGE_CONTENT_MARGIN, 
                                            AppStyles.DETAIL_PAGE_CONTENT_MARGIN)
        self.detail_layout.setSpacing(AppStyles.DETAIL_PAGE_CONTENT_SPACING)
        
        # Resource summary section
        summary_section = QWidget()
        summary_layout = QVBoxLayout(summary_section)
        summary_layout.setContentsMargins(0, 0, 0, AppStyles.DETAIL_PAGE_SUMMARY_MARGIN_BOTTOM)
        
        # Add resource name heading
        self.resource_name_label = QLabel("Resource Name")
        self.resource_name_label.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_NAME_STYLE)
        
        # Add resource type and namespace
        self.resource_info_label = QLabel("Resource Type | default namespace")
        self.resource_info_label.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
        
        # Add creation time
        self.creation_time_label = QLabel("Created 2 days ago (Mar 1, 2023 09:12:30)")
        self.creation_time_label.setStyleSheet(AppStyles.DETAIL_PAGE_CREATION_TIME_STYLE)
        
        summary_layout.addWidget(self.resource_name_label)
        summary_layout.addWidget(self.resource_info_label)
        summary_layout.addWidget(self.creation_time_label)
        
        # Divider
        divider1 = QFrame()
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet(AppStyles.DETAIL_PAGE_DIVIDER_STYLE)
        
        # Status section
        status_section = QWidget()
        self.status_layout = QVBoxLayout(status_section)
        self.status_layout.setContentsMargins(0, AppStyles.DETAIL_PAGE_SECTION_MARGIN, 
                                             0, AppStyles.DETAIL_PAGE_SECTION_MARGIN)
        
        # Section title
        status_title = QLabel("STATUS")
        status_title.setStyleSheet(AppStyles.DETAIL_PAGE_SECTION_TITLE_STYLE)
        
        # Status info
        status_info = QHBoxLayout()
        
        self.status_value = QLabel("Running")
        self.status_value.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_RUNNING_STYLE)
        
        self.status_text = QLabel("3/3 replicas available")
        self.status_text.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_TEXT_STYLE)
        
        status_info.addWidget(self.status_value)
        status_info.addWidget(self.status_text)
        status_info.addStretch()
        
        self.status_layout.addWidget(status_title)
        self.status_layout.addLayout(status_info)
        
        # Divider
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet(AppStyles.DETAIL_PAGE_DIVIDER_STYLE)
        
        # Conditions section
        conditions_section = QWidget()
        self.conditions_layout = QVBoxLayout(conditions_section)
        self.conditions_layout.setContentsMargins(0, AppStyles.DETAIL_PAGE_SECTION_MARGIN, 
                                                0, AppStyles.DETAIL_PAGE_SECTION_MARGIN)
        
        # Section title
        conditions_title = QLabel("CONDITIONS")
        conditions_title.setStyleSheet(AppStyles.DETAIL_PAGE_SECTION_TITLE_STYLE)
        
        self.conditions_layout.addWidget(conditions_title)
        
        # Divider
        divider3 = QFrame()
        divider3.setFrameShape(QFrame.Shape.HLine)
        divider3.setStyleSheet(AppStyles.DETAIL_PAGE_DIVIDER_STYLE)
        
        # Labels section
        labels_section = QWidget()
        self.labels_layout = QVBoxLayout(labels_section)
        self.labels_layout.setContentsMargins(0, AppStyles.DETAIL_PAGE_SECTION_MARGIN, 
                                            0, AppStyles.DETAIL_PAGE_SECTION_MARGIN)
        
        # Section title
        labels_title = QLabel("LABELS")
        labels_title.setStyleSheet(AppStyles.DETAIL_PAGE_SECTION_TITLE_STYLE)
        
        # Labels list
        self.labels_content = QLabel("")
        self.labels_content.setStyleSheet(AppStyles.DETAIL_PAGE_LABELS_CONTENT_STYLE)
        
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
        self.yaml_text.setStyleSheet(AppStyles.DETAIL_PAGE_YAML_TEXT_STYLE)
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
        layout.setContentsMargins(AppStyles.DETAIL_PAGE_CONTENT_MARGIN, 
                                AppStyles.DETAIL_PAGE_CONTENT_MARGIN, 
                                AppStyles.DETAIL_PAGE_CONTENT_MARGIN, 
                                AppStyles.DETAIL_PAGE_CONTENT_MARGIN)
        
        # Events list
        self.events_list = QListWidget()
        self.events_list.setStyleSheet(AppStyles.DETAIL_PAGE_EVENTS_LIST_STYLE)
        
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
        self.animation.setDuration(AppStyles.DETAIL_PAGE_ANIMATION_DURATION)
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
        self.animation.setDuration(AppStyles.DETAIL_PAGE_ANIMATION_DURATION)
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
                self.status_value.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_RUNNING_STYLE)
            elif phase in ["Pending", "ContainerCreating"]:
                self.status_value.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_PENDING_STYLE)
            elif phase in ["Succeeded", "Completed"]:
                self.status_value.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_SUCCEEDED_STYLE)
            else:
                self.status_value.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_FAILED_STYLE)
            
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
                self.status_value.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_RUNNING_STYLE)
            elif available_replicas > 0:
                self.status_value.setText("Partially Available")
                self.status_value.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_PENDING_STYLE)
            else:
                self.status_value.setText("Not Available")
                self.status_value.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_FAILED_STYLE)
            
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
            self.status_value.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_SUCCEEDED_STYLE)
            
            if type_value == "LoadBalancer" and external_ip == "Pending":
                self.status_text.setText(f"ClusterIP: {cluster_ip}, External IP: Pending")
            else:
                self.status_text.setText(f"ClusterIP: {cluster_ip}")
            
        else:
            # Generic status (fallback)
            self.status_value.setText("Active")
            self.status_value.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_RUNNING_STYLE)
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
            no_conditions.setStyleSheet(AppStyles.DETAIL_PAGE_CONDITION_NO_DATA_STYLE)
            self.conditions_layout.addWidget(no_conditions)
            return
        
        # Add each condition
        for condition in conditions:
            condition_row = QHBoxLayout()
            
            condition_type = QLabel(condition.get("type", "Unknown"))
            condition_type.setFixedWidth(AppStyles.DETAIL_PAGE_CONDITION_TYPE_WIDTH)
            condition_type.setStyleSheet(AppStyles.DETAIL_PAGE_CONDITION_TYPE_STYLE)
            
            condition_status = QLabel(condition.get("status", "Unknown"))
            condition_status.setFixedWidth(AppStyles.DETAIL_PAGE_CONDITION_STATUS_WIDTH)
            if condition.get("status") == "True":
                condition_status.setStyleSheet(AppStyles.DETAIL_PAGE_CONDITION_STATUS_TRUE_STYLE)
            else:
                condition_status.setStyleSheet(AppStyles.DETAIL_PAGE_CONDITION_STATUS_FALSE_STYLE)
            
            condition_message = QLabel(condition.get("message", "No message"))
            condition_message.setStyleSheet(AppStyles.DETAIL_PAGE_CONDITION_MESSAGE_STYLE)
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
            event_layout.setContentsMargins(0, AppStyles.DETAIL_PAGE_EVENT_ITEM_MARGIN, 
                                          0, AppStyles.DETAIL_PAGE_EVENT_ITEM_MARGIN)
            
            # Event header (type, reason, age)
            header_layout = QHBoxLayout()
            
            event_type = QLabel(event.get("type", "Normal"))
            if event.get("type") == "Warning":
                event_type.setStyleSheet(AppStyles.DETAIL_PAGE_EVENT_TYPE_WARNING_STYLE)
            else:
                event_type.setStyleSheet(AppStyles.DETAIL_PAGE_EVENT_TYPE_NORMAL_STYLE)
            
            event_reason = QLabel(event.get("reason", "Unknown"))
            event_reason.setStyleSheet(AppStyles.DETAIL_PAGE_EVENT_REASON_STYLE)
            
            event_age = QLabel(event.get("age", "Unknown"))
            event_age.setStyleSheet(AppStyles.DETAIL_PAGE_EVENT_AGE_STYLE)
            
            header_layout.addWidget(event_type)
            header_layout.addWidget(event_reason)
            header_layout.addStretch()
            header_layout.addWidget(event_age)
            
            # Event message
            event_message = QLabel(event.get("message", "No message"))
            event_message.setStyleSheet(AppStyles.DETAIL_PAGE_EVENT_MESSAGE_STYLE)
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



