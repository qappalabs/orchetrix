from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QPainter, QMovie
from UI.Styles import AppColors

class SplashScreen(QWidget):
    # Signal to notify when loading is complete
    finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loading")
        self.setFixedSize(700, 400)  # Wider and less tall
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Counter for progress
        self.counter = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Center container for content
        center_container = QWidget()
        center_container.setObjectName("center_container")
        center_container.setStyleSheet(f"""
            #center_container {{
                background-color: {AppColors.BG_DARK};
                border-radius: 10px;
            }}
        """)
        
        # Use a layout for content positioning
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)  # No margins to allow full-screen animation
        center_layout.setSpacing(0)
        
        # Create animation container that fills the whole background
        self.animation_container = QLabel(center_container)
        self.animation_container.setObjectName("animation_container")
        self.animation_container.setStyleSheet("""
            #animation_container {
                background-color: transparent;
                border-radius: 10px;
            }
        """)
        self.animation_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.animation_container.setFixedSize(680, 380)  # Make it fit the container
        
        try:
            # Try to load an animated GIF to fill the background
            self.movie = QMovie("animations/loading.gif")
            if self.movie.isValid():
                self.animation_container.setMovie(self.movie)
                self.movie.setScaledSize(self.animation_container.size())
                self.movie.start()
            else:
                # Fallback to a static color if GIF isn't available
                self.animation_container.setStyleSheet("#animation_container { background-color: #1E1E2E; border-radius: 10px; }")
        except Exception as e:
            print(f"Error loading animation: {e}")
            # Fallback to static color
            self.animation_container.setStyleSheet("#animation_container { background-color: #1E1E2E; border-radius: 10px; }")
        
        # Overlay layout for content on top of animation
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)
        
        # Add large spacer at the top to push content down
        top_spacer = QSpacerItem(20, 240, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        content_layout.addItem(top_spacer)
        
        # Add logo just above the progress bar
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        try:
            # Try to load the app logo
            logo_pixmap = QPixmap("logos/Group 31.png")
            if not logo_pixmap.isNull():
                scaled_logo = logo_pixmap.scaled(240, 60, Qt.AspectRatioMode.KeepAspectRatio, 
                                               Qt.TransformationMode.SmoothTransformation)
                self.logo_label.setPixmap(scaled_logo)
            else:
                # If logo can't be loaded, create a text label
                self.logo_label.setText("Orchestrix")
                self.logo_label.setStyleSheet("font-size: 36px; font-weight: bold; color: orange;")
        except Exception as e:
            print(f"Error loading logo: {e}")
            # Fallback to text
            self.logo_label.setText("Orchestrix")
            self.logo_label.setStyleSheet("font-size: 36px; font-weight: bold; color: white;")
        
        self.logo_label.setStyleSheet(self.logo_label.styleSheet() + "background-color: transparent;")
        content_layout.addWidget(self.logo_label)
        
        # Add a description or tagline
        self.description = QLabel("Kubernetes Management System")
        self.description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description.setStyleSheet("color: #ffffff; font-size: 16px; background-color: transparent;")
        content_layout.addWidget(self.description)
        
        # Small spacer before progress bar (just enough space to separate description and progress)
        small_spacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        content_layout.addItem(small_spacer)
        
        # Add loading text
        self.loading_label = QLabel("Loading...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color: white; font-size: 14px; background-color: transparent;")
        content_layout.addWidget(self.loading_label)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(30, 30, 46, 150);
                color: white;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }}
            
            QProgressBar::chunk {{
                background-color: {AppColors.ACCENT_BLUE};
                border-radius: 5px;
            }}
        """)
        content_layout.addWidget(self.progress_bar)
        
        # Version info
        self.version_label = QLabel("v1.0.0")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.version_label.setStyleSheet("color: #cccccc; font-size: 12px; margin-top: 10px; background-color: transparent;")
        content_layout.addWidget(self.version_label)
        
        # Set up layout structure - animation as background with content overlay
        center_container.setLayout(center_layout)
        center_layout.addWidget(self.animation_container)
        self.animation_container.setLayout(content_layout)
        
        # Add center container to main layout
        main_layout.addWidget(center_container)
        
        # Start a timer for progress animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(30)  # Update every 30ms
    
    def update_progress(self):
        # Update progress counter
        self.counter += 1
        self.progress_bar.setValue(self.counter)
        
        # Update loading text
        if self.counter <= 30:
            self.loading_label.setText("Loading components...")
        elif self.counter <= 50:
            self.loading_label.setText("Initializing UI...")
        elif self.counter <= 70:
            self.loading_label.setText("Connecting to services...")
        elif self.counter <= 90:
            self.loading_label.setText("Almost ready...")
        else:
            self.loading_label.setText("Loading complete!")
        
        # When progress reaches 100, emit finished signal
        if self.counter >= 100:
            self.timer.stop()
            self.finished.emit()
    
    def paintEvent(self, event):
        # Add shadow effect to the widget
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw shadow
        painter.setBrush(QColor(20, 20, 20, 60))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(10, 10, self.width() - 20, self.height() - 20, 10, 10)
        
    def closeEvent(self, event):
        # Clean up resources when the window is closed
        if hasattr(self, 'movie') and self.movie is not None:
            self.movie.stop()
        super().closeEvent(event)