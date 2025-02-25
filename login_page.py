import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QStackedWidget, QMessageBox, QMenu
)
from PyQt6.QtGui import QFont, QPixmap, QColor, QAction
from PyQt6.QtCore import Qt, QSize
from home import BrowserWidget  # Import BrowserWidget from home.py

class LoginWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent  # Reference to MainWindow
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1A1A1A;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #2D2D2D;
                border: 1px solid #3D3D3D;
                border-radius: 8px;
                padding: 10px;
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #4A9EFF;
            }
            QPushButton#login {
                background-color: #4A9EFF;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton#login:hover {
                background-color: #3A8EDF;
            }
            QLabel#title {
                color: #ffffff;
                font-size: 28px;
                font-weight: bold;
            }
            QLabel#subtitle {
                color: #8e9ba9;
                font-size: 16px;
            }
            QLabel#link {
                color: #4A9EFF;
                font-size: 14px;
            }
            QLabel#link:hover {
                color: #3A8EDF;
                text-decoration: underline;
            }
        """)

        # Main vertical layout (center everything)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(0, 0, 0, 0)

        # Logo and Title
        logo_title_widget = QWidget()
        logo_title_layout = QVBoxLayout(logo_title_widget)
        logo_title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_title_layout.setSpacing(10)

        logo = QLabel()
        logo_path = "/home/sumant-verma/Desktop/Oaks/logo.png"  # Update to your actual logo path
        logo_pixmap = QPixmap(logo_path)
        if logo_pixmap.isNull():
            print(f"Warning: Could not load logo from {logo_path}")
            logo.setText("Orchestrix")
            logo.setStyleSheet("font-size: 32px; font-weight: bold; color: #4A9EFF;")
        else:
            scaled_pixmap = logo_pixmap.scaled(
                150, 40,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo.setPixmap(scaled_pixmap)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("Welcome Back")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("Sign in to continue")
        subtitle_label.setObjectName("subtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_title_layout.addWidget(logo)
        logo_title_layout.addWidget(title_label)
        logo_title_layout.addWidget(subtitle_label)

        layout.addWidget(logo_title_widget)

        # Input Fields (centered)
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        input_layout.setSpacing(15)
        input_layout.setContentsMargins(0, 0, 0, 0)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setFixedWidth(375)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedWidth(375)

        input_layout.addWidget(self.username_input)
        input_layout.addWidget(self.password_input)

        layout.addWidget(input_widget)

        # Login Button (centered)
        login_button = QPushButton("Sign In")
        login_button.setObjectName("login")
        login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        login_button.clicked.connect(self.handle_login)
        login_button.setFixedWidth(150)
        layout.addWidget(login_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Links (Forgot Password? and Sign up for Orchestrix)
        links_widget = QWidget()
        links_layout = QHBoxLayout(links_widget)
        links_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        links_layout.setSpacing(20)  # Adjust spacing between the two links

        forgot_password = QLabel("Forgot Password?")
        forgot_password.setObjectName("link")
        forgot_password.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot_password.mousePressEvent = self.forgot_password_clicked

        signup_link = QLabel("Sign up for Orchestrix")
        signup_link.setObjectName("link")
        signup_link.setCursor(Qt.CursorShape.PointingHandCursor)
        signup_link.mousePressEvent = self.signup_clicked

        links_layout.addWidget(forgot_password)
        links_layout.addWidget(signup_link)

        layout.addWidget(links_widget)

        layout.addStretch()

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        # Hardcoded credentials for demo (replace with actual authentication)
        if username == "admin" and password == "password123":
            if self.main_window:
                self.main_window.stack.setCurrentWidget(self.main_window.browser_widget)
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password!")

    def forgot_password_clicked(self, event):
        QMessageBox.information(self, "Forgot Password", "Please contact support to reset your password.")

    def signup_clicked(self, event):
        QMessageBox.information(self, "Sign Up", "Sign up functionality is not implemented yet. Please contact support.")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Orchestrix')
        self.setMinimumSize(800, 500)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1A1A1A;
                color: white;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header (only visible after login)
        self.header = QWidget()
        self.header.setFixedHeight(40)
        self.header.setStyleSheet("""
            QWidget {
                background-color: #1A1A1A;
                border-bottom: 1px solid #2D2D2D;
            }
        """)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 0, 10, 0)
        header_layout.setSpacing(50)
        
        logo = QLabel()
        logo_path = "/home/sumant-verma/Desktop/Oaks/logo.png"  # Update to your actual logo path
        logo_pixmap = QPixmap(logo_path)
        if logo_pixmap.isNull():
            print(f"Warning: Could not load logo from {logo_path}")
            logo.setText("Logo")
        else:
            scaled_pixmap = logo_pixmap.scaled(
                120, 30,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo.setPixmap(scaled_pixmap)
        logo.setStyleSheet("padding: 0; margin: 0;")
        
        cluster_container = QWidget()
        cluster_layout = QHBoxLayout(cluster_container)
        cluster_layout.setContentsMargins(0, 0, 0, 0)
        cluster_layout.setSpacing(0)

        self.cluster_dropdown = QPushButton()
        cluster_btn_layout = QHBoxLayout(self.cluster_dropdown)
        cluster_btn_layout.setContentsMargins(15, 0, 15, 0)
        cluster_btn_layout.setSpacing(0)

        cluster_text = QLabel("Select Cluster")
        cluster_arrow = QLabel("▼")
        cluster_arrow.setFixedWidth(20)

        cluster_btn_layout.addWidget(cluster_text)
        cluster_btn_layout.addStretch()
        cluster_btn_layout.addWidget(cluster_arrow)

        self.cluster_dropdown.setFixedWidth(200)
        self.cluster_dropdown.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                border: 1px solid #3D3D3D;
                border-radius: 4px;
                color: white;
                padding: 5px 0;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
            }
            QPushButton::menu-indicator {
                width: 0;
            }
            QLabel {
                background: transparent;
                color: white;
            }
        """)

        cluster_menu = QMenu()
        cluster_menu.setFixedWidth(self.cluster_dropdown.width())
        cluster_menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D2D;
                border: 1px solid #3D3D3D;
                padding: 5px 0px;
            }
            QMenu::item {
                padding: 8px 15px;
                color: white;
            }
            QMenu::item:selected {
                background-color: #3D3D3D;
            }
            QMenu::item:checked {
                background-color: #4A9EFF;
                color: white;
            }
        """)

        clusters = ["docker-desktop", "minikube", "kind-cluster"]
        for cluster in clusters:
            action = QAction(cluster, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, c=cluster: self.switch_cluster(c))
            cluster_menu.addAction(action)

        self.cluster_dropdown.setMenu(cluster_menu)
        cluster_layout.addWidget(self.cluster_dropdown)

        header_layout.addWidget(logo)
        header_layout.addStretch()
        header_layout.addWidget(cluster_container)
        header_layout.addStretch()
        
        main_layout.addWidget(self.header)
        self.header.setVisible(False)  # Hidden until login
        
        self.stack = QStackedWidget()
        self.login_widget = LoginWidget(self)
        self.browser_widget = BrowserWidget(self)
        
        self.stack.addWidget(self.login_widget)
        self.stack.addWidget(self.browser_widget)
        
        main_layout.addWidget(self.stack)
        
        # Set initial view to Login
        self.stack.setCurrentWidget(self.login_widget)

        # Connect stack change to show header after login
        self.stack.currentChanged.connect(self.on_stack_changed)

    def switch_cluster(self, cluster_name):
        text_label = self.cluster_dropdown.findChild(QLabel)
        if text_label:
            text_label.setText(cluster_name)
        menu = self.cluster_dropdown.menu()
        for action in menu.actions():
            action.setChecked(action.text() == cluster_name)

    def on_stack_changed(self, index):
        # Show header only when not on login page (index 0)
        self.header.setVisible(index != 0)

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()