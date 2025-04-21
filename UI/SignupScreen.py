# from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit,
#                              QHBoxLayout, QCheckBox, QFrame, QMessageBox, QSpacerItem, QSizePolicy)
# from PyQt6.QtCore import Qt, pyqtSignal, QSize, QMargins
# from PyQt6.QtGui import QPixmap, QColor, QPainter, QIcon, QFont, QCursor, QPen, QBrush

# def create_checkmark_image():
#     """Create a checkmark image for the checkbox"""
#     # Create a small transparent image for the checkmark
#     checkmark = QPixmap(14, 14)
#     checkmark.fill(Qt.GlobalColor.transparent)

#     # Create painter
#     painter = QPainter(checkmark)
#     painter.setRenderHint(QPainter.RenderHint.Antialiasing)

#     # Set up the pen for drawing
#     pen = QPen()
#     pen.setWidth(2)
#     pen.setColor(QColor("#FF6D3F"))  # Orange color matching your theme
#     painter.setPen(pen)

#     # Draw checkmark
#     painter.drawLine(3, 7, 6, 10)
#     painter.drawLine(6, 10, 11, 3)
#     painter.end()

#     # Save the checkmark
#     checkmark.save("images/checkmark.png")
#     return checkmark

# class SignupScreen(QWidget):
#     # Signal to notify when the 'Continue' button is clicked
#     welcome_completed = pyqtSignal()

#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("Welcome to Orchestrix")
#         self.setFixedSize(700, 400)  # Same size as splash screen
#         self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
#         self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

#         # Create checkmark image if needed
#         try:
#             checkmark_img = QPixmap("images/checkmark.png")
#             if checkmark_img.isNull():
#                 self.checkmark_img = create_checkmark_image()
#             else:
#                 self.checkmark_img = checkmark_img
#         except:
#             self.checkmark_img = create_checkmark_image()

#         # Try loading the background image
#         self.background_image = None
#         try:
#             self.background_image = QPixmap("images/SignupBG.png")
#         except Exception as e:
#             print(f"Error loading background image: {e}")

#         # Setup UI components
#         self.setup_ui()

#     def setup_ui(self):
#         # Create main layout
#         main_layout = QVBoxLayout(self)
#         main_layout.setContentsMargins(100, 20, 100, 20)  # Larger margins for better centering

#         # Create a main form container with better styling
#         form_container = QWidget()
#         form_container.setObjectName("form_container")
#         form_container.setFixedWidth(350)  # Control the width of the form
#         form_container.setStyleSheet("""
#             QWidget#form_container {
#                 background-color: rgba(0, 0, 0, 150);
#                 border-radius: 10px;
#                 border: 1px solid rgba(255, 255, 255, 30);
#             }
#         """)

#         form_layout = QVBoxLayout(form_container)
#         form_layout.setContentsMargins(25, 20, 25, 20)
#         form_layout.setSpacing(5)  # Reduced overall spacing

#         # Sign Up header - right aligned
#         signup_label = QLabel("Sign Up")
#         signup_label.setStyleSheet("""
#             font-size: 18px;
#             font-weight: bold;
#             color: white;
#         """)
#         signup_label.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left alignment

#         form_layout.addWidget(signup_label)
#         form_layout.addSpacing(5)

#         # Social login buttons
#         social_layout = QHBoxLayout()

#         # Google button - reduced size
#         google_button = QPushButton()
#         google_button.setFixedSize(32, 32)  # Reduced size
#         try:
#             google_icon = QPixmap("images/google_icon.png")
#             if not google_icon.isNull():
#                 google_button.setIcon(QIcon(google_icon))
#                 google_button.setIconSize(QSize(20, 20))  # Reduced icon size
#             else:
#                 google_button.setText("G")
#         except:
#             google_button.setText("G")

#         google_button.setStyleSheet("""
#             QPushButton {
#                 background-color: #ffffff;
#                 color: #4285F4;
#                 border-radius: 16px;  /* Half of the width/height */
#                 font-family: Arial;
#                 font-weight: bold;
#                 font-size: 14px;
#             }
#             QPushButton:hover {
#                 background-color: #f0f0f0;
#             }
#         """)
#         google_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
#         google_button.clicked.connect(self.on_google_clicked)

#         # GitHub button - reduced size
#         github_button = QPushButton()
#         github_button.setFixedSize(32, 32)  # Reduced size
#         try:
#             github_icon = QPixmap("images/github_icon.png")
#             if not github_icon.isNull():
#                 github_button.setIcon(QIcon(github_icon))
#                 github_button.setIconSize(QSize(20, 20))  # Reduced icon size
#             else:
#                 github_button.setText("GH")
#         except:
#             github_button.setText("GH")

#         github_button.setStyleSheet("""
#             QPushButton {
#                 background-color: #ffffff;
#                 color: #333333;
#                 border-radius: 16px;  /* Half of the width/height */
#                 font-family: Arial;
#                 font-weight: bold;
#                 font-size: 14px;
#             }
#             QPushButton:hover {
#                 background-color: #f0f0f0;
#             }
#         """)
#         github_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
#         github_button.clicked.connect(self.on_github_clicked)

#         # Increased distance between buttons
#         social_layout.addStretch(1)  # Add stretch before first button
#         social_layout.addWidget(google_button)
#         social_layout.addSpacing(30)  # Spacing between buttons
#         social_layout.addWidget(github_button)
#         social_layout.addStretch(1)  # Add equal stretch after second button

#         form_layout.addLayout(social_layout)
#         form_layout.addSpacing(10)  # Add space before divider

#         # Add horizontal divider line
#         divider = QFrame()
#         divider.setFrameShape(QFrame.Shape.HLine)
#         divider.setFrameShadow(QFrame.Shadow.Sunken)
#         divider.setStyleSheet("""
#             background-color: rgba(255, 255, 255, 80);
#             max-height: 1px;
#             margin: 5px 0px;
#         """)
#         form_layout.addWidget(divider)
#         form_layout.addSpacing(10)  # Add space after divider

#         # Form inputs
#         # Name
#         name_label = QLabel("Your Name")
#         name_label.setStyleSheet("color: white; font-size: 11px;")
#         form_layout.addWidget(name_label)
#         form_layout.setSpacing(2)  # Reduce spacing between label and field

#         self.name_input = QLineEdit()
#         self.name_input.setPlaceholderText("Your Name")
#         self.name_input.setFixedHeight(26)
#         self.name_input.setStyleSheet("""
#             QLineEdit {
#                 background-color: rgba(224, 224, 224, 220);
#                 border-radius: 5px;
#                 padding: 4px 8px;
#                 font-size: 12px;
#                 border: none;
#             }
#             QLineEdit:focus {
#                 background-color: white;
#                 border: 1px solid #FF6D3F;
#             }
#         """)
#         form_layout.addWidget(self.name_input)
#         form_layout.addSpacing(5)  # Add a bit of space before next item

#         # Email
#         email_label = QLabel("Your E-mail")
#         email_label.setStyleSheet("color: white; font-size: 11px;")
#         form_layout.addWidget(email_label)
#         form_layout.setSpacing(2)  # Reduce spacing between label and field

#         self.email_input = QLineEdit()
#         self.email_input.setPlaceholderText("Your E-mail")
#         self.email_input.setFixedHeight(26)
#         self.email_input.setStyleSheet("""
#             QLineEdit {
#                 background-color: rgba(224, 224, 224, 220);
#                 border-radius: 5px;
#                 padding: 4px 8px;
#                 font-size: 12px;
#                 border: none;
#             }
#             QLineEdit:focus {
#                 background-color: white;
#                 border: 1px solid #FF6D3F;
#             }
#         """)
#         form_layout.addWidget(self.email_input)
#         form_layout.addSpacing(5)  # Add a bit of space before next item

#         # Password
#         password_label = QLabel("Password")
#         password_label.setStyleSheet("color: white; font-size: 11px;")
#         form_layout.addWidget(password_label)
#         form_layout.setSpacing(2)  # Reduce spacing between label and field

#         self.password_input = QLineEdit()
#         self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
#         self.password_input.setPlaceholderText("Password")
#         self.password_input.setFixedHeight(26)
#         self.password_input.setStyleSheet("""
#             QLineEdit {
#                 background-color: rgba(224, 224, 224, 220);
#                 border-radius: 5px;
#                 padding: 4px 8px;
#                 font-size: 12px;
#                 border: none;
#             }
#             QLineEdit:focus {
#                 background-color: white;
#                 border: 1px solid #FF6D3F;
#             }
#         """)
#         form_layout.addWidget(self.password_input)
#         form_layout.addSpacing(5)  # Add space before terms

#         # Terms and Conditions checkbox - with checkmark styling
#         terms_layout = QHBoxLayout()
#         terms_layout.setContentsMargins(0, 2, 0, 2)  # Reduced vertical margins

#         self.terms_checkbox = QCheckBox()
#         self.terms_checkbox.setStyleSheet("""
#             QCheckBox {
#                 spacing: 5px;
#             }
#             QCheckBox::indicator {
#                 width: 14px;
#                 height: 14px;
#                 background-color: rgba(224, 224, 224, 220);
#                 border-radius: 2px;
#             }
#             QCheckBox::indicator:checked {
#                 background-color: white;
#                 border: 1px solid #FF6D3F;
#                 image: url(images/checkmark.png);
#             }
#         """)

#         terms_text = QLabel("I agree to all the")
#         terms_text.setStyleSheet("color: white; font-size: 11px; margin-right: 2px;")

#         terms_link = QLabel("<a href='#' style='color: #FF6D3F; text-decoration: none;'>Term</a>")
#         terms_link.setOpenExternalLinks(False)
#         terms_link.setStyleSheet("color: #FF6D3F; font-size: 11px;")
#         terms_link.linkActivated.connect(self.on_terms_clicked)

#         and_text = QLabel("and")
#         and_text.setStyleSheet("color: white; font-size: 11px; margin: 0 2px;")

#         privacy_link = QLabel("<a href='#' style='color: #FF6D3F; text-decoration: none;'>Privacy Policy</a>")
#         privacy_link.setOpenExternalLinks(False)
#         privacy_link.setStyleSheet("color: #FF6D3F; font-size: 11px;")
#         privacy_link.linkActivated.connect(self.on_privacy_clicked)

#         terms_layout.addWidget(self.terms_checkbox)
#         terms_layout.addWidget(terms_text, 0, Qt.AlignmentFlag.AlignVCenter)
#         terms_layout.addWidget(terms_link, 0, Qt.AlignmentFlag.AlignVCenter)
#         terms_layout.addWidget(and_text, 0, Qt.AlignmentFlag.AlignVCenter)
#         terms_layout.addWidget(privacy_link, 0, Qt.AlignmentFlag.AlignVCenter)
#         terms_layout.addStretch()

#         form_layout.addLayout(terms_layout)
#         form_layout.addSpacing(8)  # Reduced spacing before button

#         # Continue button with better visibility but same height
#         continue_button = QPushButton("Continue")
#         continue_button.setFixedSize(300, 26)  # Keep original height
#         continue_button.setStyleSheet("""
#             QPushButton {
#                 background-color: #FF6D3F;
#                 color: white;
#                 border: none;
#                 border-radius: 5px;
#                 padding: 0px;  /* Reduced padding to make text fit */
#                 font-weight: bold;
#                 font-size: 12px;
#                 text-align: center;
#             }
#             QPushButton:hover {
#                 background-color: #E55C30;
#             }
#             QPushButton:pressed {
#                 background-color: #D04B20;
#             }
#         """)
#         continue_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
#         continue_button.clicked.connect(self.on_continue_clicked)

#         button_layout = QHBoxLayout()
#         button_layout.setContentsMargins(0, 0, 0, 0)
#         button_layout.addWidget(continue_button, 0, Qt.AlignmentFlag.AlignCenter)

#         form_layout.addLayout(button_layout)
#         form_layout.addSpacing(5)  # Reduced spacing before login link

#         # Login link with improved visibility
#         login_layout = QHBoxLayout()
#         login_layout.setContentsMargins(0, 5, 0, 0)  # Reduced top margin

#         account_text = QLabel("Have an account?")
#         account_text.setStyleSheet("color: white; font-size: 11px;")

#         login_link = QLabel("<a href='#' style='color: #FF6D3F; text-decoration: none;'>Log In</a>")
#         login_link.setOpenExternalLinks(False)
#         login_link.setStyleSheet("color: #FF6D3F; font-size: 11px; font-weight: bold;")
#         login_link.linkActivated.connect(self.on_login_clicked)

#         login_layout.addWidget(account_text)
#         login_layout.addWidget(login_link)
#         login_layout.addStretch()

#         form_layout.addLayout(login_layout)

#         # Add the form container to the main layout
#         main_layout.addWidget(form_container, 1, Qt.AlignmentFlag.AlignCenter)

#     def on_back_clicked(self, event):
#         """Handle back button click - simply proceed to main app"""
#         self.welcome_completed.emit()

#     def on_google_clicked(self):
#         """Handle Google sign up"""
#         QMessageBox.information(self, "Google Sign Up", "Connecting to Google authentication...")
#         # In a real app, you would implement OAuth flow here
#         self.welcome_completed.emit()

#     def on_github_clicked(self):
#         """Handle GitHub sign up"""
#         QMessageBox.information(self, "GitHub Sign Up", "Connecting to GitHub authentication...")
#         # In a real app, you would implement OAuth flow here
#         self.welcome_completed.emit()

#     def on_terms_clicked(self):
#         """Handle Terms link click"""
#         QMessageBox.information(self, "Terms & Conditions", "This would display the Terms & Conditions.")

#     def on_privacy_clicked(self):
#         """Handle Privacy Policy link click"""
#         QMessageBox.information(self, "Privacy Policy", "This would display the Privacy Policy.")

#     def on_continue_clicked(self):
#         """Handle continue button click"""
#         # Simple validation
#         if not self.name_input.text():
#             QMessageBox.warning(self, "Validation Error", "Please enter your name.")
#             return

#         if not self.email_input.text() or '@' not in self.email_input.text():
#             QMessageBox.warning(self, "Validation Error", "Please enter a valid email address.")
#             return

#         if not self.password_input.text() or len(self.password_input.text()) < 6:
#             QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters.")
#             return

#         if not self.terms_checkbox.isChecked():
#             QMessageBox.warning(self, "Validation Error", "You must agree to the Terms and Privacy Policy.")
#             return

#         # In a real app, you would register the user here
#         QMessageBox.information(self, "Success", "Account created successfully!")
#         self.welcome_completed.emit()

#     def on_login_clicked(self):
#         """Handle login link click - for now just proceed to main app"""
#         # For simplicity we'll just emit the welcome_completed signal
#         # In a real app, you would switch to a login page
#         self.welcome_completed.emit()

#     def paintEvent(self, event):
#         # Set up the painter
#         painter = QPainter(self)
#         painter.setRenderHint(QPainter.RenderHint.Antialiasing)

#         # Draw the background image
#         if self.background_image and not self.background_image.isNull():
#             # Scale image to fill the entire widget
#             scaled_bg = self.background_image.scaled(
#                 self.size(),
#                 Qt.AspectRatioMode.IgnoreAspectRatio,
#                 Qt.TransformationMode.SmoothTransformation
#             )
#             painter.drawPixmap(0, 0, scaled_bg)


from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit,
                             QHBoxLayout, QCheckBox, QFrame, QMessageBox, QSpacerItem, QSizePolicy,
                             QStackedWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QMargins
from PyQt6.QtGui import QPixmap, QColor, QPainter, QIcon, QFont, QCursor, QPen, QBrush

def create_checkmark_image():
    """Create a checkmark image for the checkbox"""
    # Create a small transparent image for the checkmark
    checkmark = QPixmap(14, 14)
    checkmark.fill(Qt.GlobalColor.transparent)

    # Create painter
    painter = QPainter(checkmark)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Set up the pen for drawing
    pen = QPen()
    pen.setWidth(2)
    pen.setColor(QColor("#FF6D3F"))  # Orange color matching your theme
    painter.setPen(pen)

    # Draw checkmark
    painter.drawLine(3, 7, 6, 10)
    painter.drawLine(6, 10, 11, 3)
    painter.end()

    # Save the checkmark
    checkmark.save("images/checkmark.png")
    return checkmark

class SignupScreen(QWidget):
    # Signal to notify when the 'Continue' button is clicked
    welcome_completed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Welcome to Orchestrix")
        self.setFixedSize(700, 400)  # Same size as splash screen
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Create checkmark image if needed
        try:
            checkmark_img = QPixmap("images/checkmark.png")
            if checkmark_img.isNull():
                self.checkmark_img = create_checkmark_image()
            else:
                self.checkmark_img = checkmark_img
        except:
            self.checkmark_img = create_checkmark_image()

        # Try loading the background image
        self.background_image = None
        try:
            self.background_image = QPixmap("images/SignupBG.png")
        except Exception as e:
            print(f"Error loading background image: {e}")

        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Create a stacked widget to switch between signup and login forms
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        # Create signup and login forms
        self.signup_form = self.create_signup_form()
        self.login_form = self.create_login_form()

        # Add forms to stacked widget
        self.stacked_widget.addWidget(self.signup_form)
        self.stacked_widget.addWidget(self.login_form)

        # Show signup form by default
        self.stacked_widget.setCurrentWidget(self.signup_form)

    def create_signup_form(self):
        """Create the signup form widget"""
        signup_widget = QWidget()
        main_layout = QVBoxLayout(signup_widget)
        main_layout.setContentsMargins(100, 20, 100, 20)  # Larger margins for better centering

        # Create a main form container with better styling
        form_container = QWidget()
        form_container.setObjectName("form_container")
        form_container.setFixedWidth(350)  # Control the width of the form
        form_container.setStyleSheet("""
            QWidget#form_container {
                background-color: rgba(0, 0, 0, 150);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
        """)

        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(25, 20, 25, 20)
        form_layout.setSpacing(5)  # Reduced overall spacing

        # Sign Up header
        signup_label = QLabel("Sign Up")
        signup_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
        """)
        signup_label.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left alignment

        form_layout.addWidget(signup_label)
        form_layout.addSpacing(5)

        # Social login buttons
        social_layout = QHBoxLayout()

        # Google button - reduced size
        google_button = QPushButton()
        google_button.setFixedSize(32, 32)  # Reduced size
        try:
            google_icon = QPixmap("images/google_icon.png")
            if not google_icon.isNull():
                google_button.setIcon(QIcon(google_icon))
                google_button.setIconSize(QSize(20, 20))  # Reduced icon size
            else:
                google_button.setText("G")
        except:
            google_button.setText("G")

        google_button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #4285F4;
                border-radius: 16px;  /* Half of the width/height */
                font-family: Arial;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        google_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        google_button.clicked.connect(self.on_google_signup_clicked)

        # GitHub button - reduced size
        github_button = QPushButton()
        github_button.setFixedSize(32, 32)  # Reduced size
        try:
            github_icon = QPixmap("images/github_icon.png")
            if not github_icon.isNull():
                github_button.setIcon(QIcon(github_icon))
                github_button.setIconSize(QSize(20, 20))  # Reduced icon size
            else:
                github_button.setText("GH")
        except:
            github_button.setText("GH")

        github_button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #333333;
                border-radius: 16px;  /* Half of the width/height */
                font-family: Arial;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        github_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        github_button.clicked.connect(self.on_github_signup_clicked)

        # Increased distance between buttons
        social_layout.addStretch(1)  # Add stretch before first button
        social_layout.addWidget(google_button)
        social_layout.addSpacing(30)  # Spacing between buttons
        social_layout.addWidget(github_button)
        social_layout.addStretch(1)  # Add equal stretch after second button

        form_layout.addLayout(social_layout)
        form_layout.addSpacing(10)  # Add space before divider

        # Add horizontal divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("""
            background-color: rgba(255, 255, 255, 80);
            max-height: 1px;
            margin: 5px 0px;
        """)
        form_layout.addWidget(divider)
        form_layout.addSpacing(10)  # Add space after divider

        # Form inputs
        # Name
        name_label = QLabel("Your Name")
        name_label.setStyleSheet("color: white; font-size: 11px;")
        form_layout.addWidget(name_label)
        form_layout.setSpacing(2)  # Reduce spacing between label and field

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Your Name")
        self.name_input.setFixedHeight(26)
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(224, 224, 224, 220);
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 12px;
                border: none;
            }
            QLineEdit:focus {
                background-color: white;
                border: 1px solid #FF6D3F;
            }
        """)
        form_layout.addWidget(self.name_input)
        form_layout.addSpacing(5)  # Add a bit of space before next item

        # Email
        email_label = QLabel("Your E-mail")
        email_label.setStyleSheet("color: white; font-size: 11px;")
        form_layout.addWidget(email_label)
        form_layout.setSpacing(2)  # Reduce spacing between label and field

        self.signup_email_input = QLineEdit()
        self.signup_email_input.setPlaceholderText("Your E-mail")
        self.signup_email_input.setFixedHeight(26)
        self.signup_email_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(224, 224, 224, 220);
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 12px;
                border: none;
            }
            QLineEdit:focus {
                background-color: white;
                border: 1px solid #FF6D3F;
            }
        """)
        form_layout.addWidget(self.signup_email_input)
        form_layout.addSpacing(5)  # Add a bit of space before next item

        # Password
        password_label = QLabel("Password")
        password_label.setStyleSheet("color: white; font-size: 11px;")
        form_layout.addWidget(password_label)
        form_layout.setSpacing(2)  # Reduce spacing between label and field

        self.signup_password_input = QLineEdit()
        self.signup_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.signup_password_input.setPlaceholderText("Password")
        self.signup_password_input.setFixedHeight(26)
        self.signup_password_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(224, 224, 224, 220);
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 12px;
                border: none;
            }
            QLineEdit:focus {
                background-color: white;
                border: 1px solid #FF6D3F;
            }
        """)
        form_layout.addWidget(self.signup_password_input)
        form_layout.addSpacing(5)  # Add space before terms

        # Terms and Conditions checkbox - with checkmark styling
        terms_layout = QHBoxLayout()
        terms_layout.setContentsMargins(0, 2, 0, 2)  # Reduced vertical margins

        self.terms_checkbox = QCheckBox()
        self.terms_checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                background-color: rgba(224, 224, 224, 220);
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: white;
                border: 1px solid #FF6D3F;
                image: url(images/checkmark.png);
            }
        """)

        terms_text = QLabel("I agree to all the")
        terms_text.setStyleSheet("color: white; font-size: 11px; margin-right: 2px;")

        terms_link = QLabel("<a href='#' style='color: #FF6D3F; text-decoration: none;'>Term</a>")
        terms_link.setOpenExternalLinks(False)
        terms_link.setStyleSheet("color: #FF6D3F; font-size: 11px;")
        terms_link.linkActivated.connect(self.on_terms_clicked)

        and_text = QLabel("and")
        and_text.setStyleSheet("color: white; font-size: 11px; margin: 0 2px;")

        privacy_link = QLabel("<a href='#' style='color: #FF6D3F; text-decoration: none;'>Privacy Policy</a>")
        privacy_link.setOpenExternalLinks(False)
        privacy_link.setStyleSheet("color: #FF6D3F; font-size: 11px;")
        privacy_link.linkActivated.connect(self.on_privacy_clicked)

        terms_layout.addWidget(self.terms_checkbox)
        terms_layout.addWidget(terms_text, 0, Qt.AlignmentFlag.AlignVCenter)
        terms_layout.addWidget(terms_link, 0, Qt.AlignmentFlag.AlignVCenter)
        terms_layout.addWidget(and_text, 0, Qt.AlignmentFlag.AlignVCenter)
        terms_layout.addWidget(privacy_link, 0, Qt.AlignmentFlag.AlignVCenter)
        terms_layout.addStretch()

        form_layout.addLayout(terms_layout)
        form_layout.addSpacing(8)  # Reduced spacing before button

        # Continue button with better visibility but same height
        continue_button = QPushButton("Continue")
        continue_button.setFixedSize(300, 26)  # Keep original height
        continue_button.setStyleSheet("""
            QPushButton {
                background-color: #FF6D3F;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 0px;  /* Reduced padding to make text fit */
                font-weight: bold;
                font-size: 12px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #E55C30;
            }
            QPushButton:pressed {
                background-color: #D04B20;
            }
        """)
        continue_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        continue_button.clicked.connect(self.on_continue_clicked)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(continue_button, 0, Qt.AlignmentFlag.AlignCenter)

        form_layout.addLayout(button_layout)
        form_layout.addSpacing(5)  # Reduced spacing before login link

        # Login link with improved visibility
        login_layout = QHBoxLayout()
        login_layout.setContentsMargins(0, 5, 0, 0)  # Reduced top margin

        account_text = QLabel("Have an account?")
        account_text.setStyleSheet("color: white; font-size: 11px;")

        login_link = QLabel("<a href='#' style='color: #FF6D3F; text-decoration: none;'>Log In</a>")
        login_link.setOpenExternalLinks(False)
        login_link.setStyleSheet("color: #FF6D3F; font-size: 11px; font-weight: bold;")
        login_link.linkActivated.connect(self.on_login_clicked)

        login_layout.addWidget(account_text)
        login_layout.addWidget(login_link)
        login_layout.addStretch()

        form_layout.addLayout(login_layout)

        # Add the form container to the main layout
        main_layout.addWidget(form_container, 1, Qt.AlignmentFlag.AlignCenter)

        return signup_widget

    def create_login_form(self):
        """Create the login form widget"""
        login_widget = QWidget()
        main_layout = QVBoxLayout(login_widget)
        main_layout.setContentsMargins(100, 20, 100, 20)  # Larger margins for better centering

        # Create a main form container with better styling
        form_container = QWidget()
        form_container.setObjectName("form_container")
        form_container.setFixedWidth(350)  # Control the width of the form
        form_container.setStyleSheet("""
            QWidget#form_container {
                background-color: rgba(0, 0, 0, 150);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
        """)

        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(25, 20, 25, 20)
        form_layout.setSpacing(5)  # Reduced overall spacing

        # Login header
        login_label = QLabel("Login")
        login_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
        """)
        login_label.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left alignment

        form_layout.addWidget(login_label)
        form_layout.addSpacing(5)

        # Social login buttons
        social_layout = QHBoxLayout()

        # Google button - reduced size
        google_button = QPushButton()
        google_button.setFixedSize(32, 32)  # Reduced size
        try:
            google_icon = QPixmap("images/google_icon.png")
            if not google_icon.isNull():
                google_button.setIcon(QIcon(google_icon))
                google_button.setIconSize(QSize(20, 20))  # Reduced icon size
            else:
                google_button.setText("G")
        except:
            google_button.setText("G")

        google_button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #4285F4;
                border-radius: 16px;  /* Half of the width/height */
                font-family: Arial;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        google_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        google_button.clicked.connect(self.on_google_login_clicked)

        # GitHub button - reduced size
        github_button = QPushButton()
        github_button.setFixedSize(32, 32)  # Reduced size
        try:
            github_icon = QPixmap("images/github_icon.png")
            if not github_icon.isNull():
                github_button.setIcon(QIcon(github_icon))
                github_button.setIconSize(QSize(20, 20))  # Reduced icon size
            else:
                github_button.setText("GH")
        except:
            github_button.setText("GH")

        github_button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #333333;
                border-radius: 16px;  /* Half of the width/height */
                font-family: Arial;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        github_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        github_button.clicked.connect(self.on_github_login_clicked)

        # Increased distance between buttons
        social_layout.addStretch(1)  # Add stretch before first button
        social_layout.addWidget(google_button)
        social_layout.addSpacing(30)  # Spacing between buttons
        social_layout.addWidget(github_button)
        social_layout.addStretch(1)  # Add equal stretch after second button

        form_layout.addLayout(social_layout)
        form_layout.addSpacing(10)  # Add space before divider

        # Add horizontal divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("""
            background-color: rgba(255, 255, 255, 80);
            max-height: 1px;
            margin: 5px 0px;
        """)
        form_layout.addWidget(divider)
        form_layout.addSpacing(10)  # Add space after divider

        # Email
        email_label = QLabel("Your E-mail")
        email_label.setStyleSheet("color: white; font-size: 11px;")
        form_layout.addWidget(email_label)
        form_layout.setSpacing(2)  # Reduce spacing between label and field

        self.login_email_input = QLineEdit()
        self.login_email_input.setPlaceholderText("Your E-mail")
        self.login_email_input.setFixedHeight(26)
        self.login_email_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(224, 224, 224, 220);
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 12px;
                border: none;
            }
            QLineEdit:focus {
                background-color: white;
                border: 1px solid #FF6D3F;
            }
        """)
        form_layout.addWidget(self.login_email_input)
        form_layout.addSpacing(5)  # Add a bit of space before next item

        # Password
        password_label = QLabel("Password")
        password_label.setStyleSheet("color: white; font-size: 11px;")
        form_layout.addWidget(password_label)
        form_layout.setSpacing(2)  # Reduce spacing between label and field

        self.login_password_input = QLineEdit()
        self.login_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password_input.setPlaceholderText("Password")
        self.login_password_input.setFixedHeight(26)
        self.login_password_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(224, 224, 224, 220);
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 12px;
                border: none;
            }
            QLineEdit:focus {
                background-color: white;
                border: 1px solid #FF6D3F;
            }
        """)
        form_layout.addWidget(self.login_password_input)
        form_layout.addSpacing(5)  # Add space before remember me checkbox

        # Remember me checkbox
        remember_layout = QHBoxLayout()
        remember_layout.setContentsMargins(0, 2, 0, 2)  # Reduced vertical margins

        self.remember_checkbox = QCheckBox()
        self.remember_checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                background-color: rgba(224, 224, 224, 220);
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: white;
                border: 1px solid #FF6D3F;
                image: url(images/checkmark.png);
            }
        """)

        remember_text = QLabel("Remember me")
        remember_text.setStyleSheet("color: white; font-size: 11px; margin-right: 2px;")

        remember_layout.addWidget(self.remember_checkbox)
        remember_layout.addWidget(remember_text, 0, Qt.AlignmentFlag.AlignVCenter)
        remember_layout.addStretch()

        form_layout.addLayout(remember_layout)
        form_layout.addSpacing(8)  # Reduced spacing before button

        # Login button
        login_button = QPushButton("Login")
        login_button.setFixedSize(300, 26)  # Keep original height
        login_button.setStyleSheet("""
            QPushButton {
                background-color: #FF6D3F;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 0px;  /* Reduced padding to make text fit */
                font-weight: bold;
                font-size: 12px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #E55C30;
            }
            QPushButton:pressed {
                background-color: #D04B20;
            }
        """)
        login_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        login_button.clicked.connect(self.on_login_button_clicked)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(login_button, 0, Qt.AlignmentFlag.AlignCenter)

        form_layout.addLayout(button_layout)
        form_layout.addSpacing(5)  # Add space before signup link

        # Add a "Sign Up" link at the bottom
        signup_layout = QHBoxLayout()
        signup_layout.setContentsMargins(0, 5, 0, 0)

        no_account_text = QLabel("Don't have an account?")
        no_account_text.setStyleSheet("color: white; font-size: 11px;")

        signup_link = QLabel("<a href='#' style='color: #FF6D3F; text-decoration: none;'>Sign Up</a>")
        signup_link.setOpenExternalLinks(False)
        signup_link.setStyleSheet("color: #FF6D3F; font-size: 11px; font-weight: bold;")
        signup_link.linkActivated.connect(self.on_signup_clicked)

        signup_layout.addWidget(no_account_text)
        signup_layout.addWidget(signup_link)
        signup_layout.addStretch()

        form_layout.addLayout(signup_layout)

        # Add the form container to the main layout
        main_layout.addWidget(form_container, 1, Qt.AlignmentFlag.AlignCenter)

        return login_widget

    # Signup form event handlers
    def on_google_signup_clicked(self):
        """Handle Google sign up"""
        # No message box, just proceed directly
        self.welcome_completed.emit()

    def on_github_signup_clicked(self):
        """Handle GitHub sign up"""
        # No message box, just proceed directly
        self.welcome_completed.emit()

    def on_terms_clicked(self):
        """Handle Terms link click"""
        QMessageBox.information(self, "Terms & Conditions", "This would display the Terms & Conditions.")

    def on_privacy_clicked(self):
        """Handle Privacy Policy link click"""
        QMessageBox.information(self, "Privacy Policy", "This would display the Privacy Policy.")

    def on_continue_clicked(self):
        """Handle continue button click"""
        # Simple validation
        if not self.name_input.text():
            QMessageBox.warning(self, "Validation Error", "Please enter your name.")
            return

        if not self.signup_email_input.text() or '@' not in self.signup_email_input.text():
            QMessageBox.warning(self, "Validation Error", "Please enter a valid email address.")
            return

        if not self.signup_password_input.text() or len(self.signup_password_input.text()) < 6:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters.")
            return

        if not self.terms_checkbox.isChecked():
            QMessageBox.warning(self, "Validation Error", "You must agree to the Terms and Privacy Policy.")
            return

        # In a real app, you would register the user here
        # No success message - just proceed directly
        self.welcome_completed.emit()

    def on_login_clicked(self):
        """Switch to login form when login link is clicked"""
        self.stacked_widget.setCurrentWidget(self.login_form)

    # Login form event handlers
    def on_google_login_clicked(self):
        """Handle Google login"""
        # No message box, just proceed directly
        self.welcome_completed.emit()

    def on_github_login_clicked(self):
        """Handle GitHub login"""
        # No message box, just proceed directly
        self.welcome_completed.emit()

    def on_login_button_clicked(self):
        """Handle login button click"""
        # Simple validation
        if not self.login_email_input.text() or '@' not in self.login_email_input.text():
            QMessageBox.warning(self, "Validation Error", "Please enter a valid email address.")
            return

        if not self.login_password_input.text():
            QMessageBox.warning(self, "Validation Error", "Please enter your password.")
            return

        # In a real app, you would authenticate the user here
        # If remember me is checked, you would store credentials securely
        remember = self.remember_checkbox.isChecked()

        # No success message - just proceed directly
        self.welcome_completed.emit()

    def on_signup_clicked(self):
        """Switch to signup form when signup link is clicked"""
        self.stacked_widget.setCurrentWidget(self.signup_form)

    def paintEvent(self, event):
        # Set up the painter
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the background image
        if self.background_image and not self.background_image.isNull():
            # Scale image to fill the entire widget
            scaled_bg = self.background_image.scaled(
                self.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(0, 0, scaled_bg)