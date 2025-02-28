from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QToolButton
from PyQt6.QtCore import Qt, QPoint,QEvent
from PyQt6.QtGui import QPixmap, QPainter, QLinearGradient, QColor, QFont

DARK_BG = "#1E1E1E"
DARKER_BG = "#151515"
SIDEBAR_BG = "#1A1A1A"
TEXT_COLOR = "#FFFFFF"
ACCENT_COLOR = "#00AAAA"
SECONDARY_ACCENT = "#FF00FF"
THIRD_ACCENT = "#00FF88"
CHART_BG = "#2A2A2A"
class TitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        self.setStyleSheet(f"background-color: {DARK_BG};")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        
        # Logo and title
        logo_label = QLabel()
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QColor(ACCENT_COLOR))
        painter.setBrush(QColor(ACCENT_COLOR))
        painter.drawEllipse(8, 8, 16, 16)
        painter.setPen(QColor(TEXT_COLOR))
        painter.drawText(10, 20, "O")
        painter.end()
        logo_label.setPixmap(pixmap)
        logo_label.setCursor(Qt.CursorShape.PointingHandCursor)
        
        title_label = QLabel("Orchetrix")
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; font-weight: bold;")
        
        # Window controls
        btn_minimize = QPushButton("−")
        btn_maximize = QPushButton("□")
        btn_close = QPushButton("×")
        
        for btn in [btn_minimize, btn_maximize, btn_close]:
            btn.setFixedSize(30, 30)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    border: none;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #555555;
                }
            """)
        
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #E81123;
            }
        """)
        
        # Profile button
        profile_btn = QPushButton()
        profile_btn.setFixedSize(30, 30)
        profile_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_COLOR};
                color: {TEXT_COLOR};
                border-radius: 15px;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        profile_btn.setText("DP")
        
        # Add spacer to push controls to the right
        layout.addWidget(logo_label)
        layout.addWidget(title_label)
        layout.addStretch()
        
        # Add notification and home icons
        home_btn = QPushButton("🏠")
        notif_btn = QPushButton("🔔")
        user_btn = QPushButton("👤")
        
        for btn in [home_btn, notif_btn, user_btn]:
            btn.setFixedSize(30, 30)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    border: none;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #555555;
                }
            """)
        
        layout.addWidget(home_btn)
        layout.addWidget(notif_btn)
        layout.addWidget(user_btn)
        layout.addWidget(profile_btn)
        layout.addWidget(btn_minimize)
        layout.addWidget(btn_maximize)
        layout.addWidget(btn_close)
        
        btn_minimize.clicked.connect(self.parent.showMinimized)
        btn_maximize.clicked.connect(self.toggleMaximize)
        btn_close.clicked.connect(self.parent.close)
        
        # For window dragging
        self.dragging = False
        self.drag_position = None
        
        # Install event filter for double-click
        self.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        # Handle double-click on titlebar to maximize
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self.toggleMaximize()
            return True
        return super().eventFilter(obj, event)
    
    def toggleMaximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.position().toPoint()
    
    def mouseMoveEvent(self, event):
        if self.dragging and self.drag_position is not None:
            self.parent.move(self.parent.pos() + event.position().toPoint() - self.drag_position)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
