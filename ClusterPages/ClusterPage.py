# from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
#                              QTabWidget, QGridLayout)
# from PyQt6.QtCore import Qt


# class ClusterPage(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.parent = parent
        
#         # Colors
#         self.bg_dark = "#1a1a1a"
#         self.bg_header = "#1e1e1e" 
#         self.text_light = "#ffffff"
#         self.text_secondary = "#888888"
#         self.border_color = "#2d2d2d"
#         self.tab_inactive = "#2d2d2d"
#         self.card_bg = "#1e1e1e"
        
#         self.setup_ui()
        
#     def setup_ui(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setSpacing(0)

#         # Add tab container
#         tab_container = self.create_tab_container()
#         layout.addWidget(tab_container)

#         # Add content area
#         content_area = self.create_content_area()
#         layout.addWidget(content_area)
        
#     def create_tab_container(self):
#         tab_widget = QTabWidget()
#         tab_widget.setFixedHeight(44)
#         tab_widget.addTab(QWidget(), "Master")
#         tab_widget.addTab(QWidget(), "Worker")
#         tab_widget.setCurrentIndex(0)
#         return tab_widget
    
#     def create_content_area(self):
#         content_widget = QWidget()
#         content_layout = QGridLayout(content_widget)
#         content_layout.setContentsMargins(16, 16, 16, 16)
#         content_layout.setSpacing(16)
        
#         metric_panel1 = self.create_metric_panel()
#         metric_panel2 = self.create_metric_panel()
#         status_panel = self.create_status_panel()
        
#         content_layout.addWidget(metric_panel1, 0, 0)
#         content_layout.addWidget(metric_panel2, 0, 1)
#         content_layout.addWidget(status_panel, 1, 0, 1, 2)
        
#         return content_widget
    
#     def create_metric_panel(self):
#         panel = QWidget()
#         panel.setStyleSheet(f"""
#             QWidget {{
#                 background-color: {self.card_bg};
#                 border-radius: 4px;
#             }}
#         """)

#         layout = QVBoxLayout(panel)
#         layout.setContentsMargins(16, 16, 16, 16)
#         layout.setSpacing(16)

#         # Tab-like buttons
#         tabs = QWidget()
#         tabs_layout = QHBoxLayout(tabs)
#         tabs_layout.setContentsMargins(0, 0, 0, 0)
#         tabs_layout.setSpacing(4)

#         cpu_btn = QPushButton("CPU")
#         cpu_btn.setStyleSheet("""
#             QPushButton {
#                 background-color: #333333;
#                 color: #ffffff;
#                 border: none;
#                 padding: 6px 16px;
#                 font-size: 13px;
#                 border-radius: 4px;
#             }
#         """)

#         memory_btn = QPushButton("Memory")
#         memory_btn.setStyleSheet("""
#             QPushButton {
#                 background-color: transparent;
#                 color: #888888;
#                 border: none;
#                 padding: 6px 16px;
#                 font-size: 13px;
#             }
#             QPushButton:hover {
#                 color: #ffffff;
#             }
#         """)

#         tabs_layout.addWidget(cpu_btn)
#         tabs_layout.addWidget(memory_btn)
#         tabs_layout.addStretch()

#         # Info message
#         info_container = QWidget()
#         info_layout = QVBoxLayout(info_container)
#         info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         info_msg = QLabel("Metrics are not available due to missing or invalid Prometheus")
#         info_msg.setStyleSheet("color: #888888; font-size: 13px;")
#         info_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         settings_link = QLabel("Open cluster settings")
#         settings_link.setStyleSheet("""
#             color: #0095ff;
#             font-size: 13px;
#             margin-top: 8px;
#         """)
#         settings_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         settings_link.setCursor(Qt.CursorShape.PointingHandCursor)

#         info_layout.addWidget(info_msg)
#         info_layout.addWidget(settings_link)

#         layout.addWidget(tabs)
#         layout.addWidget(info_container, 1, Qt.AlignmentFlag.AlignCenter)

#         return panel

#     def create_status_panel(self):
#         panel = QWidget()
#         panel.setStyleSheet(f"""
#             background-color: {self.card_bg};
#             border-radius: 4px;
#         """)

#         layout = QVBoxLayout(panel)
#         layout.setContentsMargins(32, 48, 32, 48)
#         layout.setSpacing(8)
#         layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         # Success icon
#         success_icon = QLabel("✓")
#         success_icon.setFixedSize(80, 80)
#         success_icon.setStyleSheet("""
#             background-color: #4CAF50;
#             color: white;
#             font-size: 40px;
#             border-radius: 40px;
#             qproperty-alignment: AlignCenter;
#         """)

#         # Status text
#         status_title = QLabel("No issues found")
#         status_title.setStyleSheet("""
#             color: white;
#             font-size: 20px;
#             font-weight: 500;
#             margin-top: 16px;
#         """)
#         status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         status_subtitle = QLabel("Everything is fine in the Cluster")
#         status_subtitle.setStyleSheet("""
#             color: #888888;
#             font-size: 14px;
#             margin-top: 4px;
#         """)
#         status_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         layout.addWidget(success_icon, 0, Qt.AlignmentFlag.AlignCenter)
#         layout.addWidget(status_title)
#         layout.addWidget(status_subtitle)

#         return panel

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QGridLayout, QTabWidget)
from PyQt6.QtCore import Qt

class ClusterPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Colors
        self.bg_dark = "#1a1a1a"
        self.card_bg = "#1e1e1e"
        self.border_color = "#2d2d2d"
        self.tab_inactive = "#2d2d2d"
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add tab container
        tab_container = self.create_tab_container()
        layout.addWidget(tab_container)

        # Add content area
        content_area = self.create_content_area()
        layout.addWidget(content_area)
        
    def create_tab_container(self):
        tab_widget = QTabWidget()
        tab_widget.setFixedHeight(44)
        tab_widget.addTab(QWidget(), "Master")
        tab_widget.addTab(QWidget(), "Worker")
        tab_widget.setCurrentIndex(0)
        return tab_widget
    
    def create_content_area(self):
        content_widget = QWidget()
        content_layout = QGridLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        metric_panel1 = self.create_metric_panel()
        metric_panel2 = self.create_metric_panel()
        status_panel = self.create_status_panel()
        
        content_layout.addWidget(metric_panel1, 0, 0)
        content_layout.addWidget(metric_panel2, 0, 1)
        content_layout.addWidget(status_panel, 1, 0, 1, 2)
        
        return content_widget
    
    def create_metric_panel(self):
        panel = QWidget()
        panel.setStyleSheet(f"""
            QWidget {{
                background-color: {self.card_bg};
                border-radius: 4px;
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Tab-like buttons
        tabs = QWidget()
        tabs_layout = QHBoxLayout(tabs)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(4)

        cpu_btn = QPushButton("CPU")
        cpu_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border: none;
                padding: 6px 16px;
                font-size: 13px;
                border-radius: 4px;
            }
        """)

        memory_btn = QPushButton("Memory")
        memory_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: none;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)

        tabs_layout.addWidget(cpu_btn)
        tabs_layout.addWidget(memory_btn)
        tabs_layout.addStretch()

        # Info message
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        info_msg = QLabel("Metrics are not available due to missing or invalid Prometheus")
        info_msg.setStyleSheet("color: #888888; font-size: 13px;")
        info_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        settings_link = QLabel("Open cluster settings")
        settings_link.setStyleSheet("""
            color: #0095ff;
            font-size: 13px;
            margin-top: 8px;
        """)
        settings_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        settings_link.setCursor(Qt.CursorShape.PointingHandCursor)

        info_layout.addWidget(info_msg)
        info_layout.addWidget(settings_link)

        layout.addWidget(tabs)
        layout.addWidget(info_container, 1, Qt.AlignmentFlag.AlignCenter)

        return panel

    def create_status_panel(self):
        panel = QWidget()
        panel.setStyleSheet(f"""
            background-color: {self.card_bg};
            border-radius: 4px;
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 48, 32, 48)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Success icon
        success_icon = QLabel("✓")
        success_icon.setFixedSize(80, 80)
        success_icon.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            font-size: 40px;
            border-radius: 40px;
            qproperty-alignment: AlignCenter;
        """)

        # Status text
        status_title = QLabel("No issues found")
        status_title.setStyleSheet("""
            color: white;
            font-size: 20px;
            font-weight: 500;
            margin-top: 16px;
        """)
        status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status_subtitle = QLabel("Everything is fine in the Cluster")
        status_subtitle.setStyleSheet("""
            color: #888888;
            font-size: 14px;
            margin-top: 4px;
        """)
        status_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(success_icon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_title)
        layout.addWidget(status_subtitle)

        return panel