from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QFrame, QScrollArea, QLineEdit, QComboBox)
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, pyqtSignal, QEvent
from PyQt6.QtGui import QFont, QPixmap, QColor, QCursor

class ProfileScreen(QWidget):
    """
    Profile settings screen that displays user information and allows editing.
    Appears from the right side of the main window with a dark theme.
    Does not cover the titlebar but has the same height as the main screen.
    """
    closed = pyqtSignal()  # Signal emitted when profile screen is closed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.is_visible = False
        self.setFixedWidth(800)  # Width of the profile panel
        self.is_editing = False  # Track editing state
        self.is_shortcuts_editing = False  # Track shortcuts editing state

        # Calculate titlebar height (typical value for Windows)
        self.titlebar_height = 0  # Set to 0 to make it equal to main screen height

        # Create icons as class attributes so they can be accessed from other methods
        from PyQt6.QtGui import QIcon
        self.down_icon = QIcon("icons/down_btn.svg")
        self.close_icon = QIcon("icons/close_btn.svg")

        # Store shortcut keys for editing
        self.windows_shortcuts_data = {}
        self.macos_shortcuts_data = {}

        self.setup_ui()

        # Set initial position off-screen to the right
        self.hide()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Important: Make sure it can receive mouse events but doesn't pass them through
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        # Install event filter on parent to detect outside clicks
        if self.parent:
            self.parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Filter events to detect clicks outside the profile panel"""
        if obj == self.parent and self.is_visible and event.type() == QEvent.Type.MouseButtonPress:
            # Get the position of the click relative to the parent widget
            pos = event.pos()

            # Get the geometry of the profile panel
            profile_rect = self.geometry()

            # If the click is outside the profile panel, hide it
            if not profile_rect.contains(pos):
                self.hide_profile()
                return True  # Event handled

        # For all other events, let the default handler take care of it
        return super().eventFilter(obj, event)

    def setup_ui(self):
        """Initialize the UI components with dark theme styling"""
        # Define dark theme colors
        self.dark_bg = "#1E1E1E"
        self.darker_bg = "#121212"
        self.card_bg = "#262626"
        self.text_primary = "#FFFFFF"
        self.text_secondary = "#AAAAAA"
        self.accent_color = "#2884FF"
        self.input_bg = "#333333"
        self.input_border = "#444444"
        self.button_hover = "#3A8EDF"
        self.email_item_bg = "#333333"
        self.add_email_bg = "#1F374A"
        self.add_email_text = "#4C9EFF"
        self.add_email_hover = "#284969"
        self.shortcut_bg = "#1a1a1a"
        self.close_button_bg = "#FF3B30"  # Red background for close button
        self.close_button_hover = "#FF5147"  # Lighter red for hover effect

        # Set main widget background
        self.setStyleSheet(f"background-color: {self.dark_bg};")

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top header bar
        header = QWidget()
        header.setFixedHeight(70)
        header.setStyleSheet(f"background-color: {self.darker_bg};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        # Welcome text
        welcome_label = QLabel("Welcome, Amanda")
        welcome_label.setObjectName("welcome_label")
        welcome_label.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 22px;
            font-weight: bold;
            color: {self.text_primary};
        """)

        # Close button using icon from icons folder with transparent background and increased size
        close_button = QPushButton()
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setFixedSize(48, 48)  # Increased size from 36x36 to 48x48

        # Load the icon directly using QIcon instead of CSS background
        # Using class attribute self.close_icon instead of a local variable
        close_button.setIcon(self.close_icon)
        close_button.setIconSize(QPixmap(24, 24).size())  # Set the icon size

        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 24px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);  /* Subtle hover effect */
            }}
        """)
        close_button.clicked.connect(self.hide_profile)

        header_layout.addWidget(welcome_label)
        header_layout.addStretch()
        header_layout.addWidget(close_button)

        main_layout.addWidget(header)

        # Content area with dark background
        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {self.darker_bg};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {self.dark_bg};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.input_border};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        # Scrollable content
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)  # Increased spacing for the shortcut section

        # Profile card - dark card background
        profile_card = QWidget()
        profile_card.setStyleSheet(f"""
            QWidget {{
                background-color: {self.card_bg};
                border-radius: 10px;
            }}
        """)

        profile_layout = QVBoxLayout(profile_card)
        profile_layout.setContentsMargins(25, 25, 25, 25)
        profile_layout.setSpacing(30)

        # Profile header with photo, name and edit button
        profile_header = QWidget()
        profile_header_layout = QHBoxLayout(profile_header)
        profile_header_layout.setContentsMargins(0, 0, 0, 0)
        profile_header_layout.setSpacing(0)

        # Profile photo and name/email
        profile_info = QWidget()
        profile_info_layout = QHBoxLayout(profile_info)
        profile_info_layout.setContentsMargins(0, 0, 0, 0)
        profile_info_layout.setSpacing(15)

        # Profile photo - larger circle
        user_photo = QLabel()
        user_photo.setObjectName("profile_avatar")
        user_photo.setFixedSize(54, 54)
        self.set_avatar(user_photo, 54, "AR")

        # Name and email
        user_details = QWidget()
        user_details_layout = QVBoxLayout(user_details)
        user_details_layout.setContentsMargins(0, 0, 0, 0)
        user_details_layout.setSpacing(5)

        name_label = QLabel("Alexa Rawles")
        name_label.setObjectName("profile_name_label")
        name_label.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 18px;
            font-weight: bold;
            color: {self.text_primary};
        """)

        email_label = QLabel("alexarawles@gmail.com")
        email_label.setObjectName("profile_email_label")
        email_label.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 14px;
            color: {self.text_secondary};
        """)

        user_details_layout.addWidget(name_label)
        user_details_layout.addWidget(email_label)

        profile_info_layout.addWidget(user_photo)
        profile_info_layout.addWidget(user_details)
        profile_info_layout.addStretch()

        # Edit button
        self.edit_button = QPushButton("Edit")
        self.edit_button.setObjectName("edit_button")
        self.edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_button.setFixedSize(75, 36)
        self.edit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.accent_color};
                color: {self.text_primary};
                border: none;
                border-radius: 5px;
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.button_hover};
            }}
        """)
        self.edit_button.clicked.connect(self.toggle_edit_mode)

        profile_header_layout.addWidget(profile_info)
        profile_header_layout.addWidget(self.edit_button)

        profile_layout.addWidget(profile_header)

        # Form fields in two columns
        form_grid = QWidget()
        form_grid_layout = QVBoxLayout(form_grid)
        form_grid_layout.setContentsMargins(0, 0, 0, 0)
        form_grid_layout.setSpacing(25)

        # Common style for all input fields
        input_style = f"""
            background-color: {self.input_bg};
            border: 1px solid {self.input_border};
            border-radius: 5px;
            padding: 0 15px;
            font-family: 'Segoe UI';
            font-size: 14px;
            color: {self.text_primary};
        """

        placeholder_style = f"color: {self.text_secondary};"

        # Custom style for dropdown fields - using icon from icons folder
        dropdown_style = f"""
            background-color: {self.input_bg};
            border: 1px solid {self.input_border};
            border-radius: 5px;
            padding: 0 15px;
            font-family: 'Segoe UI';
            font-size: 14px;
            color: {self.text_primary};
        """

        # Apply QIcon to all dropdown fields instead of CSS background
        # Using class attribute self.down_icon instead of local down_icon

        # Common style for dropdown arrows using QIcon instead of CSS
        dropdown_arrow_style = f"""
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
        """

        # Row 1: First Name & Last Name
        row1 = QWidget()
        row1_layout = QHBoxLayout(row1)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(20)

        # First Name field
        first_name_container = QWidget()
        first_name_layout = QVBoxLayout(first_name_container)
        first_name_layout.setContentsMargins(0, 0, 0, 0)
        first_name_layout.setSpacing(8)

        first_name_label = QLabel("First Name")
        first_name_label.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 14px;
            color: {self.text_secondary};
        """)

        first_name_input = QLineEdit()
        first_name_input.setObjectName("first_name_input")
        first_name_input.setPlaceholderText("Your First Name")
        first_name_input.setFixedHeight(40)
        first_name_input.setReadOnly(True)  # Initially read-only
        first_name_input.setStyleSheet(f"""
            QLineEdit {{ {input_style} }}
            QLineEdit::placeholder {{ {placeholder_style} }}
        """)

        first_name_layout.addWidget(first_name_label)
        first_name_layout.addWidget(first_name_input)

        # Last Name field
        last_name_container = QWidget()
        last_name_layout = QVBoxLayout(last_name_container)
        last_name_layout.setContentsMargins(0, 0, 0, 0)
        last_name_layout.setSpacing(8)

        last_name_label = QLabel("Last Name")
        last_name_label.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 14px;
            color: {self.text_secondary};
        """)

        last_name_input = QLineEdit()
        last_name_input.setObjectName("last_name_input")
        last_name_input.setPlaceholderText("Your Last Name")
        last_name_input.setFixedHeight(40)
        last_name_input.setReadOnly(True)  # Initially read-only
        last_name_input.setStyleSheet(f"""
            QLineEdit {{ {input_style} }}
            QLineEdit::placeholder {{ {placeholder_style} }}
        """)

        last_name_layout.addWidget(last_name_label)
        last_name_layout.addWidget(last_name_input)

        row1_layout.addWidget(first_name_container)
        row1_layout.addWidget(last_name_container)

        # Row 2: Gender & Country
        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(20)

        # Gender field
        gender_container = QWidget()
        gender_layout = QVBoxLayout(gender_container)
        gender_layout.setContentsMargins(0, 0, 0, 0)
        gender_layout.setSpacing(8)

        gender_label = QLabel("Gender")
        gender_label.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 14px;
            color: {self.text_secondary};
        """)

        gender_combo = QComboBox()
        gender_combo.setObjectName("gender_combo")
        gender_combo.addItems(["Male", "Female", "Other", "Prefer not to say"])
        # The icon will be applied later after combo box is created
        gender_combo.setFixedHeight(40)
        gender_combo.setEnabled(False)  # Initially disabled
        gender_combo.setStyleSheet(f"""
            QComboBox {{ {dropdown_style} }}
            QComboBox:hover {{ border: 1px solid {self.accent_color}; }}
            {dropdown_arrow_style}
        """)

        gender_layout.addWidget(gender_label)
        gender_layout.addWidget(gender_combo)

        # Country field
        country_container = QWidget()
        country_layout = QVBoxLayout(country_container)
        country_layout.setContentsMargins(0, 0, 0, 0)
        country_layout.setSpacing(8)

        country_label = QLabel("Country")
        country_label.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 14px;
            color: {self.text_secondary};
        """)

        country_combo = QComboBox()
        country_combo.setObjectName("country_combo")
        # Expanded list of countries
        countries = [
            "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda",
            "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain",
            "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan",
            "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria",
            "Burkina Faso", "Burundi", "Cabo Verde", "Cambodia", "Cameroon", "Canada",
            "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros",
            "Congo", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic", "Denmark",
            "Djibouti", "Dominica", "Dominican Republic", "Ecuador", "Egypt", "El Salvador",
            "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Fiji",
            "Finland", "France", "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece",
            "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Honduras",
            "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel",
            "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Korea, North",
            "Korea, South", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho",
            "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Madagascar",
            "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania",
            "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro",
            "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands",
            "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Macedonia", "Norway",
            "Oman", "Pakistan", "Palau", "Panama", "Papua New Guinea", "Paraguay", "Peru",
            "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda",
            "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines",
            "Samoa", "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal",
            "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia",
            "Solomon Islands", "Somalia", "South Africa", "South Sudan", "Spain", "Sri Lanka",
            "Sudan", "Suriname", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan",
            "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago",
            "Tunisia", "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine",
            "United Arab Emirates", "United Kingdom", "United States", "Uruguay",
            "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela", "Vietnam", "Yemen",
            "Zambia", "Zimbabwe"
        ]
        country_combo.addItems(countries)
        country_combo.setCurrentIndex(0)
        country_combo.setFixedHeight(40)
        country_combo.setEnabled(False)  # Initially disabled
        country_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.input_bg};
                border: 1px solid {self.input_border};
                border-radius: 5px;
                padding: 0 30px 0 15px;  /* Increased right padding for icon */
                font-family: 'Segoe UI';
                font-size: 14px;
                color: {self.text_primary};
            }}
            QComboBox:hover {{ 
                border: 1px solid {self.accent_color}; 
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: right center;
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: url("icons/down_btn.svg");
                width: 12px;
                height: 12px;
                margin-right: 10px;
            }}
        """)

        # No need to set icon since we're using CSS styling
        # country_combo.setItemIcon(country_combo.currentIndex(), self.down_icon)

        country_layout.addWidget(country_label)
        country_layout.addWidget(country_combo)

        row2_layout.addWidget(gender_container)
        row2_layout.addWidget(country_container)

        # Row 3: Email & Time Zone
        row3 = QWidget()
        row3_layout = QHBoxLayout(row3)
        row3_layout.setContentsMargins(0, 0, 0, 0)
        row3_layout.setSpacing(20)

        # Email field
        email_container = QWidget()
        email_layout = QVBoxLayout(email_container)
        email_layout.setContentsMargins(0, 0, 0, 0)
        email_layout.setSpacing(8)

        email_label = QLabel("Email")
        email_label.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 14px;
            color: {self.text_secondary};
        """)

        email_input = QLineEdit()
        email_input.setObjectName("email_input")
        email_input.setPlaceholderText("Your Email Address")
        email_input.setFixedHeight(40)
        email_input.setReadOnly(True)  # Initially read-only
        email_input.setStyleSheet(f"""
            QLineEdit {{ {input_style} }}
            QLineEdit::placeholder {{ {placeholder_style} }}
        """)

        email_layout.addWidget(email_label)
        email_layout.addWidget(email_input)

        # Time Zone field
        timezone_container = QWidget()
        timezone_layout = QVBoxLayout(timezone_container)
        timezone_layout.setContentsMargins(0, 0, 0, 0)
        timezone_layout.setSpacing(8)

        timezone_label = QLabel("Time Zone")
        timezone_label.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 14px;
            color: {self.text_secondary};
        """)

        timezone_combo = QComboBox()
        timezone_combo.setObjectName("timezone_combo")
        # Expanded list of timezones
        timezones = [
            "(UTC-12:00) International Date Line West",
            "(UTC-11:00) Coordinated Universal Time-11",
            "(UTC-10:00) Hawaii",
            "(UTC-09:00) Alaska",
            "(UTC-08:00) Pacific Time (US & Canada)",
            "(UTC-07:00) Mountain Time (US & Canada)",
            "(UTC-06:00) Central Time (US & Canada)",
            "(UTC-05:00) Eastern Time (US & Canada)",
            "(UTC-04:00) Atlantic Time (Canada)",
            "(UTC-03:30) Newfoundland",
            "(UTC-03:00) Brasilia",
            "(UTC-02:00) Mid-Atlantic",
            "(UTC-01:00) Azores",
            "(UTC+00:00) GMT",
            "(UTC+01:00) London, Dublin, Edinburgh",
            "(UTC+01:00) Berlin, Vienna, Rome, Paris",
            "(UTC+02:00) Athens, Istanbul, Helsinki",
            "(UTC+03:00) Moscow, St. Petersburg, Volgograd",
            "(UTC+03:30) Tehran",
            "(UTC+04:00) Abu Dhabi, Muscat",
            "(UTC+04:30) Kabul",
            "(UTC+05:00) Islamabad, Karachi",
            "(UTC+05:30) Chennai, Kolkata, Mumbai, New Delhi",
            "(UTC+05:45) Kathmandu",
            "(UTC+06:00) Astana, Dhaka",
            "(UTC+06:30) Yangon (Rangoon)",
            "(UTC+07:00) Bangkok, Hanoi, Jakarta",
            "(UTC+08:00) Beijing, Hong Kong, Singapore",
            "(UTC+08:45) Eucla",
            "(UTC+09:00) Tokyo, Seoul, Osaka",
            "(UTC+09:30) Adelaide",
            "(UTC+10:00) Sydney, Melbourne, Brisbane",
            "(UTC+11:00) Vladivostok",
            "(UTC+12:00) Auckland, Wellington",
            "(UTC+13:00) Nuku'alofa"
        ]
        timezone_combo.addItems(timezones)
        timezone_combo.setCurrentIndex(0)
        timezone_combo.setFixedHeight(40)
        timezone_combo.setEnabled(False)  # Initially disabled
        timezone_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.input_bg};
                border: 1px solid {self.input_border};
                border-radius: 5px;
                padding: 0 30px 0 15px;  /* Increased right padding for icon */
                font-family: 'Segoe UI';
                font-size: 14px;
                color: {self.text_primary};
            }}
            QComboBox:hover {{ 
                border: 1px solid {self.accent_color}; 
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: right center;
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: url("icons/down_btn.svg");
                width: 12px;
                height: 12px;
                margin-right: 10px;
            }}
        """)

        timezone_layout.addWidget(timezone_label)
        timezone_layout.addWidget(timezone_combo)

        row3_layout.addWidget(email_container)
        row3_layout.addWidget(timezone_container)

        # Add all rows to form grid
        form_grid_layout.addWidget(row1)
        form_grid_layout.addWidget(row2)
        form_grid_layout.addWidget(row3)

        profile_layout.addWidget(form_grid)

        # Add everything to main layouts
        content_layout.addWidget(profile_card)

        # Shortcuts section with separate categories for Windows and macOS
        shortcuts_card = QWidget()
        shortcuts_card.setStyleSheet(f"""
            QWidget {{
                background-color: {self.card_bg};
                border-radius: 10px;
            }}
        """)

        shortcuts_layout = QVBoxLayout(shortcuts_card)
        shortcuts_layout.setContentsMargins(25, 25, 25, 25)
        shortcuts_layout.setSpacing(20)

        # Section title and edit button in a row
        shortcuts_header = QWidget()
        shortcuts_header_layout = QHBoxLayout(shortcuts_header)
        shortcuts_header_layout.setContentsMargins(0, 0, 0, 0)
        shortcuts_header_layout.setSpacing(0)

        # Section title
        shortcuts_title = QLabel("Keyboard Shortcuts")
        shortcuts_title.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 18px;
            font-weight: bold;
            color: {self.text_primary};
        """)

        # Edit shortcuts button - similar to profile edit button
        self.shortcuts_edit_button = QPushButton("Edit")
        self.shortcuts_edit_button.setObjectName("shortcuts_edit_button")
        self.shortcuts_edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.shortcuts_edit_button.setFixedSize(75, 36)
        self.shortcuts_edit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.accent_color};
                color: {self.text_primary};
                border: none;
                border-radius: 5px;
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.button_hover};
            }}
        """)
        self.shortcuts_edit_button.clicked.connect(self.toggle_shortcuts_edit_mode)

        shortcuts_header_layout.addWidget(shortcuts_title)
        shortcuts_header_layout.addStretch()
        shortcuts_header_layout.addWidget(self.shortcuts_edit_button)

        shortcuts_layout.addWidget(shortcuts_header)

        # Create tabs for Windows and macOS shortcuts
        shortcut_tabs = QWidget()
        shortcut_tabs_layout = QHBoxLayout(shortcut_tabs)
        shortcut_tabs_layout.setContentsMargins(0, 0, 0, 15)
        shortcut_tabs_layout.setSpacing(10)

        # Windows tab button
        self.windows_tab = QPushButton("Windows")
        self.windows_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.windows_tab.setCheckable(True)
        self.windows_tab.setChecked(True)  # Windows tab active by default
        self.windows_tab.setFixedHeight(36)
        self.windows_tab.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.shortcut_bg};
                color: {self.text_primary};
                border: none;
                border-radius: 5px;
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: bold;
                padding: 0 15px;
            }}
            QPushButton:checked {{
                background-color: {self.accent_color};
                color: {self.text_primary};
            }}
            QPushButton:hover:!checked {{
                background-color: #252525;
            }}
        """)
        self.windows_tab.clicked.connect(self.show_windows_shortcuts)

        # macOS tab button
        self.macos_tab = QPushButton("macOS")
        self.macos_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.macos_tab.setCheckable(True)
        self.macos_tab.setFixedHeight(36)
        self.macos_tab.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.shortcut_bg};
                color: {self.text_primary};
                border: none;
                border-radius: 5px;
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: bold;
                padding: 0 15px;
            }}
            QPushButton:checked {{
                background-color: {self.accent_color};
                color: {self.text_primary};
            }}
            QPushButton:hover:!checked {{
                background-color: #252525;
            }}
        """)
        self.macos_tab.clicked.connect(self.show_macos_shortcuts)

        shortcut_tabs_layout.addWidget(self.windows_tab)
        shortcut_tabs_layout.addWidget(self.macos_tab)
        shortcut_tabs_layout.addStretch()

        shortcuts_layout.addWidget(shortcut_tabs)

        # Stacked widget to hold Windows and macOS shortcut content
        self.shortcuts_stack = QWidget()
        self.shortcuts_stack_layout = QVBoxLayout(self.shortcuts_stack)
        self.shortcuts_stack_layout.setContentsMargins(0, 0, 0, 0)
        self.shortcuts_stack_layout.setSpacing(0)

        # Windows shortcuts content
        self.windows_shortcuts = QWidget()
        windows_shortcuts_layout = QVBoxLayout(self.windows_shortcuts)
        windows_shortcuts_layout.setContentsMargins(0, 0, 0, 0)
        windows_shortcuts_layout.setSpacing(15)

        # macOS shortcuts content
        self.macos_shortcuts = QWidget()
        macos_shortcuts_layout = QVBoxLayout(self.macos_shortcuts)
        macos_shortcuts_layout.setContentsMargins(0, 0, 0, 0)
        macos_shortcuts_layout.setSpacing(15)

        # Helper function to create category headers
        def create_category_header(text):
            header = QLabel(text)
            header.setStyleSheet(f"""
                font-family: 'Segoe UI';
                font-size: 16px;
                font-weight: bold;
                color: {self.text_primary};
                padding-top: 10px;
                padding-bottom: 5px;
            """)
            return header

        # Initial shortcut data for Windows
        windows_shortcuts_data = {
            "Profile Controls": {
                "Close Profile": "Esc",
                "Save Profile": "Ctrl+S",
                "Toggle Edit Mode": "Ctrl+E",
                "Navigate Form Fields": "Tab / Shift+Tab",
                "Open Dropdown Menu": "Alt+↓"
            },
            "Application Navigation": {
                "Open Command Palette": "Ctrl+P",
                "Search in Files": "Ctrl+Shift+F",
                "Switch Between Tabs": "Ctrl+Tab",
                "Close Current Tab": "Ctrl+W",
                "Switch to Tab 1–9": "Ctrl+1–9",
                "Switch Between Clusters": "Ctrl+Shift+C"
            },
            "Cluster Management": {
                "Refresh Current Cluster View": "Ctrl+R",
                "Reload All Clusters": "Ctrl+Shift+R",
                "Open Cluster Settings": "Ctrl+Shift+E"
            },
            "Pod and Terminal": {
                "Open Terminal for Pod": "T",
                "View Logs for Pod": "L",
                "New Terminal Tab": "Ctrl+Shift+T",
                "Open Logs in New Tab": "Ctrl+Shift+L"
            },
            "View Control": {
                "Zoom In": "Ctrl++",
                "Zoom Out": "Ctrl+-",
                "Reset Zoom": "Ctrl+0",
                "Toggle Dev Tools": "Ctrl+Shift+D"
            }
        }

        # Initial shortcut data for macOS
        macos_shortcuts_data = {
            "Profile Controls": {
                "Close Profile": "Esc",
                "Save Profile": "Cmd+S",
                "Toggle Edit Mode": "Cmd+E",
                "Navigate Form Fields": "Tab / Shift+Tab",
                "Open Dropdown Menu": "Option+↓"
            },
            "Application Navigation": {
                "Open Command Palette": "Cmd+P",
                "Search in Files": "Cmd+Shift+F",
                "Switch Between Tabs": "Cmd+Option+→/←",
                "Close Current Tab": "Cmd+W",
                "Switch to Tab 1–9": "Cmd+1–9",
                "Switch Between Clusters": "Cmd+Shift+C"
            },
            "Cluster Management": {
                "Refresh Current Cluster View": "Cmd+R",
                "Reload All Clusters": "Cmd+Shift+R",
                "Open Cluster Settings": "Cmd+Shift+E"
            },
            "Pod and Terminal": {
                "Open Terminal for Pod": "T",
                "View Logs for Pod": "L",
                "New Terminal Tab": "Cmd+Shift+T",
                "Open Logs in New Tab": "Cmd+Shift+L"
            },
            "View Control": {
                "Zoom In": "Cmd++",
                "Zoom Out": "Cmd+-",
                "Reset Zoom": "Cmd+0",
                "Toggle Dev Tools": "Cmd+Shift+D"
            }
        }

        # Store shortcut data
        self.windows_shortcuts_data = windows_shortcuts_data
        self.macos_shortcuts_data = macos_shortcuts_data

        # Create the UI for Windows shortcuts
        self.create_shortcuts_ui(self.windows_shortcuts, windows_shortcuts_layout, windows_shortcuts_data, "windows")

        # Create the UI for macOS shortcuts
        self.create_shortcuts_ui(self.macos_shortcuts, macos_shortcuts_layout, macos_shortcuts_data, "macos")

        # Add both to the stack layout
        self.shortcuts_stack_layout.addWidget(self.windows_shortcuts)
        self.shortcuts_stack_layout.addWidget(self.macos_shortcuts)

        # Initially hide macOS shortcuts
        self.windows_shortcuts.show()
        self.macos_shortcuts.hide()

        shortcuts_layout.addWidget(self.shortcuts_stack)

        # Add shortcuts card to content layout
        content_layout.addWidget(shortcuts_card)
        content_layout.addStretch()

        content_scroll.setWidget(content_widget)
        main_layout.addWidget(content_scroll)

        # Store references to form fields to toggle edit mode
        self.form_fields = {
            'first_name': first_name_input,
            'last_name': last_name_input,
            'gender': gender_combo,
            'country': country_combo,
            'email': email_input,
            'timezone': timezone_combo
        }

    def create_shortcuts_ui(self, parent_widget, parent_layout, shortcuts_data, os_type):
        """Create UI for shortcuts based on the given data and OS type"""
        # Clear the existing layout while properly destroying widgets
        self.clear_layout(parent_layout)

        # Store the shortcut input widgets for access during editing
        shortcut_inputs = {}

        # Add category headers and shortcut rows
        for category, shortcuts in shortcuts_data.items():
            # Add category header
            parent_layout.addWidget(self.create_category_header(category))

            # Dictionary to store input widgets for this category
            category_inputs = {}

            # Add shortcut rows for each item in this category
            for action, key in shortcuts.items():
                # Pass os_type explicitly to ensure correct object naming
                shortcut_row = self.create_shortcut_row(action, key, self.is_shortcuts_editing, os_type)
                parent_layout.addWidget(shortcut_row)

                # Store reference to input widget if we're in edit mode
                if self.is_shortcuts_editing:
                    shortcut_input = shortcut_row.findChild(QLineEdit, f"{os_type}_{action.replace(' ', '_').lower()}_input")
                    if shortcut_input:
                        category_inputs[action] = shortcut_input

            # Add the category's inputs to the main dict
            if category_inputs:
                shortcut_inputs[category] = category_inputs

        # Store references based on OS type
        if os_type == "windows":
            self.windows_shortcut_inputs = shortcut_inputs
        else:
            self.macos_shortcut_inputs = shortcut_inputs

    def clear_layout(self, layout):
        """Properly clear a layout, ensuring all child widgets are deleted"""
        if layout is None:
            return

        while layout.count():
            item = layout.takeAt(0)

            if item.widget():
                # Delete any widget
                item.widget().deleteLater()
            elif item.layout():
                # Recursively clear child layouts
                self.clear_layout(item.layout())
                item.layout().deleteLater()
            else:
                # Handle spacer items or other non-widget, non-layout items
                pass

    def create_category_header(self, text):
        """Create a category header label"""
        header = QLabel(text)
        header.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 16px;
            font-weight: bold;
            color: {self.text_primary};
            padding-top: 10px;
            padding-bottom: 5px;
        """)
        return header

    def create_shortcut_row(self, action, keys, edit_mode=False, os_type=None):
        """Create a row for a keyboard shortcut (edit_mode determines if it's editable)"""
        row = QWidget()
        row.setStyleSheet(f"background-color: {self.shortcut_bg}; border-radius: 8px;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(15, 10, 15, 10)

        # Action label (always shown)
        action_label = QLabel(action)
        action_label.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 14px;
            color: {self.text_primary};
        """)

        row_layout.addWidget(action_label)
        row_layout.addStretch()

        # In edit mode, use a text input for the keys
        if edit_mode:
            keys_input = QLineEdit(keys)

            # If os_type is not provided, determine based on active tab
            if os_type is None:
                os_type = "macos" if self.macos_tab.isChecked() else "windows"

            # Set a unique object name for the input based on the action
            keys_input.setObjectName(f"{os_type}_{action.replace(' ', '_').lower()}_input")
            keys_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {self.input_bg};
                    color: {self.text_primary};
                    border: 1px solid {self.input_border};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-family: 'Segoe UI';
                    font-size: 14px;
                    font-weight: bold;
                    max-width: 150px;
                }}
                QLineEdit:focus {{
                    border: 1px solid {self.accent_color};
                }}
            """)
            row_layout.addWidget(keys_input)
        else:
            # In view mode, just use a label
            keys_label = QLabel(keys)
            keys_label.setStyleSheet(f"""
                font-family: 'Segoe UI';
                font-size: 14px;
                color: {self.text_secondary};
                font-weight: bold;
            """)
            row_layout.addWidget(keys_label)

        return row

    def toggle_shortcuts_edit_mode(self):
        """Toggle between view and edit modes for shortcuts section"""
        # Store the previous state to detect if we're entering or exiting edit mode
        was_editing = self.is_shortcuts_editing

        # Toggle the edit state
        self.is_shortcuts_editing = not self.is_shortcuts_editing

        # Initialize button container if it doesn't exist already
        if not hasattr(self, 'shortcut_action_buttons'):
            self.shortcut_action_buttons = QWidget()
            self.shortcut_action_buttons.setContentsMargins(0, 10, 0, 0)
            action_layout = QHBoxLayout(self.shortcut_action_buttons)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(10)

            # Add spacer to push buttons to the right
            action_layout.addStretch()

            # Create cancel button
            self.cancel_shortcuts_button = QPushButton("Cancel")
            self.cancel_shortcuts_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.cancel_shortcuts_button.setFixedSize(75, 36)
            self.cancel_shortcuts_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.shortcut_bg};
                    color: {self.text_primary};
                    border: none;
                    border-radius: 5px;
                    font-family: 'Segoe UI';
                    font-size: 14px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #333333;
                }}
            """)
            self.cancel_shortcuts_button.clicked.connect(self.cancel_shortcuts_edit)
            action_layout.addWidget(self.cancel_shortcuts_button)

            # Create save button
            self.save_shortcuts_button = QPushButton("Save")
            self.save_shortcuts_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.save_shortcuts_button.setFixedSize(75, 36)
            self.save_shortcuts_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.accent_color};
                    color: {self.text_primary};
                    border: none;
                    border-radius: 5px;
                    font-family: 'Segoe UI';
                    font-size: 14px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self.button_hover};
                }}
            """)
            self.save_shortcuts_button.clicked.connect(self.apply_shortcuts_edit)
            action_layout.addWidget(self.save_shortcuts_button)

            # Add to appropriate parent - we'll add it to the active shortcuts layout
            shortcuts_stack_layout = self.shortcuts_stack.layout()
            if shortcuts_stack_layout:
                shortcuts_stack_layout.addWidget(self.shortcut_action_buttons)
                self.shortcut_action_buttons.hide()  # Initially hidden

        # Change button text and visibility based on mode
        if self.is_shortcuts_editing:
            self.shortcuts_edit_button.setText("Edit")  # Just show "Edit" since we have separate Save/Cancel
            self.shortcuts_edit_button.setVisible(False)  # Hide the edit button while in edit mode
            self.shortcut_action_buttons.show()  # Show the action buttons

            # Store original data for cancel functionality
            self.original_windows_data = self.copy_shortcuts_data(self.windows_shortcuts_data)
            self.original_macos_data = self.copy_shortcuts_data(self.macos_shortcuts_data)
        else:
            self.shortcuts_edit_button.setText("Edit")
            self.shortcuts_edit_button.setVisible(True)  # Show the edit button again
            self.shortcut_action_buttons.hide()  # Hide the action buttons

            if not was_editing:
                # If we were not in edit mode before, no need to save
                pass
            else:
                # Save the changed shortcuts when exiting edit mode
                self.save_shortcuts()

        # Refresh the UI for the currently visible OS (Windows or macOS)
        if self.windows_tab.isChecked():
            self.create_shortcuts_ui(
                self.windows_shortcuts,
                self.windows_shortcuts.layout(),
                self.windows_shortcuts_data,
                "windows"
            )
        else:
            self.create_shortcuts_ui(
                self.macos_shortcuts,
                self.macos_shortcuts.layout(),
                self.macos_shortcuts_data,
                "macos"
            )

    def apply_shortcuts_edit(self):
        """Apply and save the shortcut edits"""
        # Save the changes
        self.save_shortcuts()

        # Exit edit mode
        self.is_shortcuts_editing = False
        self.shortcuts_edit_button.setVisible(True)
        self.shortcut_action_buttons.hide()

        # Refresh the UI
        if self.windows_tab.isChecked():
            self.create_shortcuts_ui(
                self.windows_shortcuts,
                self.windows_shortcuts.layout(),
                self.windows_shortcuts_data,
                "windows"
            )
        else:
            self.create_shortcuts_ui(
                self.macos_shortcuts,
                self.macos_shortcuts.layout(),
                self.macos_shortcuts_data,
                "macos"
            )

    def cancel_shortcuts_edit(self):
        """Cancel the shortcut edits and revert to original values"""
        # Restore original data
        if hasattr(self, 'original_windows_data'):
            self.windows_shortcuts_data = self.original_windows_data
        if hasattr(self, 'original_macos_data'):
            self.macos_shortcuts_data = self.original_macos_data

        # Exit edit mode
        self.is_shortcuts_editing = False
        self.shortcuts_edit_button.setVisible(True)
        self.shortcut_action_buttons.hide()

        # Refresh the UI
        if self.windows_tab.isChecked():
            self.create_shortcuts_ui(
                self.windows_shortcuts,
                self.windows_shortcuts.layout(),
                self.windows_shortcuts_data,
                "windows"
            )
        else:
            self.create_shortcuts_ui(
                self.macos_shortcuts,
                self.macos_shortcuts.layout(),
                self.macos_shortcuts_data,
                "macos"
            )

    def copy_shortcuts_data(self, data):
        """Create a deep copy of shortcuts data"""
        if not data:
            return {}

        # Deep copy the dictionary
        copy = {}
        for category, shortcuts in data.items():
            copy[category] = {}
            for action, shortcut in shortcuts.items():
                copy[category][action] = shortcut

        return copy

    def save_shortcuts(self, os_type=None):
        """
        Save the edited shortcuts

        Args:
            os_type (str, optional): Explicitly specify which OS shortcuts to save ('windows' or 'macos').
                                     If None, it's determined based on the active tab.
        """
        # Determine which OS shortcuts are currently being edited
        if os_type == "windows" or (os_type is None and self.windows_tab.isChecked()):
            # Save Windows shortcuts
            shortcuts_data = self.windows_shortcuts_data
            shortcut_inputs = getattr(self, 'windows_shortcut_inputs', {})
            current_os = "windows"
        else:
            # Save macOS shortcuts
            shortcuts_data = self.macos_shortcuts_data
            shortcut_inputs = getattr(self, 'macos_shortcut_inputs', {})
            current_os = "macos"

        # Validate and update shortcuts data with values from inputs
        for category, actions in shortcut_inputs.items():
            for action, input_widget in actions.items():
                if category in shortcuts_data and action in shortcuts_data[category]:
                    shortcut_value = input_widget.text().strip()

                    # Basic validation - ensure not empty
                    if not shortcut_value:
                        # If empty, use the original value from data
                        shortcut_value = shortcuts_data[category][action]

                    # Update the shortcut data with the validated value
                    shortcuts_data[category][action] = shortcut_value

        # Store the updated data in the appropriate property
        if current_os == "windows":
            self.windows_shortcuts_data = shortcuts_data
        else:
            self.macos_shortcuts_data = shortcuts_data

        # Here you would typically also save to persistent storage
        # For example: save_to_settings(self.windows_shortcuts_data, self.macos_shortcuts_data)

    def toggle_edit_mode(self):
        """Toggle between view and edit modes"""
        self.is_editing = not self.is_editing

        if self.is_editing:
            # Switch to edit mode
            self.edit_button.setText("Save")

            # Common styling for input fields in edit mode
            input_edit_style = f"""
                background-color: {self.input_bg};
                border: 1px solid {self.accent_color};
                border-radius: 5px;
                padding: 0 15px;
                font-family: 'Segoe UI';
                font-size: 14px;
                color: {self.text_primary};
            """

            # Dropdown-specific styling in edit mode with right-aligned dropdown icon
            dropdown_edit_style = f"""
                background-color: {self.input_bg};
                border: 1px solid {self.accent_color};
                border-radius: 5px;
                padding: 0 30px 0 15px;  /* Increased right padding for icon */
                font-family: 'Segoe UI';
                font-size: 14px;
                color: {self.text_primary};
            """

            # Apply styles to all form fields
            for field_name, field in self.form_fields.items():
                if isinstance(field, QLineEdit):
                    field.setReadOnly(False)
                    field.setStyleSheet(f"""
                        QLineEdit {{ {input_edit_style} }}
                        QLineEdit::placeholder {{ color: {self.text_secondary}; }}
                    """)
                elif isinstance(field, QComboBox):
                    field.setEnabled(True)
                    field.setStyleSheet(f"""
                        QComboBox {{
                            background-color: {self.input_bg};
                            border: 1px solid {self.accent_color};
                            border-radius: 5px;
                            padding: 0 30px 0 15px;
                            font-family: 'Segoe UI';
                            font-size: 14px;
                            color: {self.text_primary};
                        }}
                        QComboBox::drop-down {{
                            subcontrol-origin: padding;
                            subcontrol-position: right center;
                            border: none;
                            width: 30px;
                        }}
                        QComboBox::down-arrow {{
                            image: url("icons/down_btn.svg");
                            width: 12px;
                            height: 12px;
                            margin-right: 10px;
                        }}
                    """)
                    # field.setItemIcon(field.currentIndex(), self.down_icon)
        else:
            # Switch back to view mode and save changes
            self.edit_button.setText("Edit")

            # Update profile header with new values
            first_name = self.form_fields['first_name'].text() or self.form_fields['first_name'].placeholderText()
            last_name = self.form_fields['last_name'].text() or self.form_fields['last_name'].placeholderText()
            full_name = f"{first_name} {last_name}".strip()
            email = self.form_fields['email'].text() or self.form_fields['email'].placeholderText()

            if full_name:
                self.findChild(QLabel, "profile_name_label").setText(full_name)
                self.findChild(QLabel, "welcome_label").setText(f"Welcome, {first_name}")

            if email:
                self.findChild(QLabel, "profile_email_label").setText(email)

            # Reset fields to read-only mode
            # Common input style for view mode
            input_view_style = f"""
                background-color: {self.input_bg};
                border: 1px solid {self.input_border};
                border-radius: 5px;
                padding: 0 15px;
                font-family: 'Segoe UI';
                font-size: 14px;
                color: {self.text_primary};
            """

            # Dropdown style for view mode with right-aligned dropdown icon
            dropdown_view_style = f"""
                background-color: {self.input_bg};
                border: 1px solid {self.input_border};
                border-radius: 5px;
                padding: 0 30px 0 15px;  /* Increased right padding for icon */
                font-family: 'Segoe UI';
                font-size: 14px;
                color: {self.text_primary};
            """

            # Apply styles to all form fields
            for field_name, field in self.form_fields.items():
                if isinstance(field, QLineEdit):
                    field.setReadOnly(True)
                    field.setStyleSheet(f"""
                        QLineEdit {{ {input_view_style} }}
                        QLineEdit::placeholder {{ color: {self.text_secondary}; }}
                    """)
                elif isinstance(field, QComboBox):
                    field.setEnabled(False)
                    field.setStyleSheet(f"""
                        QComboBox {{
                            background-color: {self.input_bg};
                            border: 1px solid {self.input_border};
                            border-radius: 5px;
                            padding: 0 30px 0 15px;
                            font-family: 'Segoe UI';
                            font-size: 14px;
                            color: {self.text_primary};
                        }}
                        QComboBox::drop-down {{
                            subcontrol-origin: padding;
                            subcontrol-position: right center;
                            border: none;
                            width: 30px;
                        }}
                        QComboBox::down-arrow {{
                            image: url("icons/down_btn.svg");
                            width: 12px;
                            height: 12px;
                            margin-right: 10px;
                        }}
                    """)
                    # field.setItemIcon(field.currentIndex(), self.down_icon)

    def set_avatar(self, label, size, initials):
        """Create a circular avatar with initials"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        from PyQt6.QtGui import QPainter, QBrush
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw circle
        painter.setBrush(QBrush(QColor(self.accent_color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)

        # Draw initials
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Segoe UI", int(size/3))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)

        painter.end()
        label.setPixmap(pixmap)
        label.setScaledContents(True)

    def set_user_info(self, name, email, username=None, gender=None, country=None, timezone=None, organization="", team="", role=""):
        """Set user information to display"""
        # Split the name into first and last
        parts = name.split()
        first_name = parts[0] if parts else ""
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        # Update welcome text
        welcome_label = self.findChild(QLabel, "welcome_label")
        if welcome_label:
            welcome_label.setText(f"Welcome, {first_name}")

        # Update profile name and email
        profile_name = self.findChild(QLabel, "profile_name_label")
        if profile_name:
            profile_name.setText(name)

        profile_email = self.findChild(QLabel, "profile_email_label")
        if profile_email:
            profile_email.setText(email)

        # Generate initials for avatar
        initials = ""
        if name:
            parts = name.split()
            if len(parts) >= 2:
                initials = parts[0][0] + parts[-1][0]
            else:
                initials = parts[0][0:2]

        # Update avatar
        profile_avatar = self.findChild(QLabel, "profile_avatar")
        if profile_avatar:
            self.set_avatar(profile_avatar, 54, initials)

        # Set field values and placeholders
        if 'first_name' in self.form_fields:
            self.form_fields['first_name'].setText(first_name)
            self.form_fields['first_name'].setPlaceholderText(first_name)

        if 'last_name' in self.form_fields:
            self.form_fields['last_name'].setText(last_name)
            self.form_fields['last_name'].setPlaceholderText(last_name)

        if 'email' in self.form_fields:
            self.form_fields['email'].setText(email)
            self.form_fields['email'].setPlaceholderText(email)

        # Set dropdown values if provided
        if gender is not None and 'gender' in self.form_fields:
            index = self.form_fields['gender'].findText(gender)
            if index >= 0:
                self.form_fields['gender'].setCurrentIndex(index)

        if country is not None and 'country' in self.form_fields:
            index = self.form_fields['country'].findText(country)
            if index >= 0:
                self.form_fields['country'].setCurrentIndex(index)

        if timezone is not None and 'timezone' in self.form_fields:
            index = self.form_fields['timezone'].findText(timezone, Qt.MatchFlag.MatchContains)
            if index >= 0:
                self.form_fields['timezone'].setCurrentIndex(index)

        # The username, organization, team, and role parameters are accepted but not used
        # in the current UI, so they're just placeholders for future expansion

    def show_profile(self):
        """Show the profile panel with animation from the right side with full height"""
        if self.is_visible:
            return

        self.is_visible = True
        self.show()

        # Ensure the event filter is installed
        if self.parent:
            self.parent.installEventFilter(self)

        # Position off-screen to the right
        parent_width = self.parent.width() if self.parent else 1000
        parent_height = self.parent.height() if self.parent else 700

        # Start position - off-screen to the right
        self.setGeometry(parent_width, 0, self.width(), parent_height)

        # Create animation to slide in from right
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(250)
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(QRect(parent_width - self.width(), 0, self.width(), parent_height))
        self.anim.start()

    def hide_profile(self):
        """Hide the profile panel with animation to the right"""
        if not self.is_visible:
            return

        self.is_visible = False

        # If in edit mode, exit edit mode before hiding
        if self.is_editing:
            self.toggle_edit_mode()

        # If in shortcuts edit mode, exit that mode too
        if self.is_shortcuts_editing:
            self.toggle_shortcuts_edit_mode()

        # Create animation to slide out to the right
        parent_width = self.parent.width() if self.parent else 1000
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(250)
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(QRect(parent_width, 0, self.width(), self.height()))
        self.anim.finished.connect(self._on_hide_finished)
        self.anim.start()

    def _on_hide_finished(self):
        """Called when the hide animation finishes"""
        self.hide()
        # Remove the event filter when the profile is hidden
        if self.parent:
            self.parent.removeEventFilter(self)
        self.closed.emit()

    def toggle_profile(self):
        """Toggle the profile screen visibility"""
        if self.is_visible:
            self.hide_profile()
        else:
            self.show_profile()

    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        if self.parent and self.is_visible:
            # Maintain position at the right edge with full height
            self.setGeometry(
                self.parent.width() - self.width(),
                0,
                self.width(),
                self.parent.height()
            )

    def mousePressEvent(self, event):
        """Override mousePressEvent to prevent clicks from passing through"""
        # Process the mouse press event as normal
        super().mousePressEvent(event)
        # Don't let the event propagate further
        event.accept()

    def keyPressEvent(self, event):
        """Handle key press events - close profile on Escape key"""
        super().keyPressEvent(event)
        # Close the profile panel when Escape key is pressed
        if event.key() == Qt.Key.Key_Escape and self.is_visible:
            self.hide_profile()
            event.accept()
        # Save both profile and shortcuts when Ctrl+S is pressed (prioritize based on what's active)
        elif event.key() == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if self.is_shortcuts_editing:
                self.toggle_shortcuts_edit_mode()  # Save shortcut changes
                event.accept()
            elif self.is_editing:
                self.toggle_edit_mode()  # Save profile changes
                event.accept()
        # Toggle edit mode when Ctrl+E is pressed
        elif event.key() == Qt.Key.Key_E and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.toggle_edit_mode()
            event.accept()
        # Toggle shortcuts edit mode when Ctrl+K is pressed
        elif event.key() == Qt.Key.Key_K and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.toggle_shortcuts_edit_mode()
            event.accept()

    def show_windows_shortcuts(self):
        """Show Windows shortcuts and update tab buttons"""
        # If we're in edit mode and switching from macOS tab, save those changes first
        if self.is_shortcuts_editing and self.macos_tab.isChecked():
            # Save the current macOS edits before switching
            self.save_shortcuts(os_type="macos")

        # Update tab state
        self.windows_tab.setChecked(True)
        self.macos_tab.setChecked(False)
        self.windows_shortcuts.show()
        self.macos_shortcuts.hide()

        # If in edit mode, refresh the UI to show edit fields for Windows shortcuts
        if self.is_shortcuts_editing:
            self.create_shortcuts_ui(
                self.windows_shortcuts,
                self.windows_shortcuts.layout(),
                self.windows_shortcuts_data,
                "windows"
            )

    def show_macos_shortcuts(self):
        """Show macOS shortcuts and update tab buttons"""
        # If we're in edit mode and switching from Windows tab, save those changes first
        if self.is_shortcuts_editing and self.windows_tab.isChecked():
            # Save the current Windows edits before switching
            self.save_shortcuts(os_type="windows")

        # Update tab state
        self.windows_tab.setChecked(False)
        self.macos_tab.setChecked(True)
        self.windows_shortcuts.hide()
        self.macos_shortcuts.show()

        # If in edit mode, refresh the UI to show edit fields for macOS shortcuts
        if self.is_shortcuts_editing:
            self.create_shortcuts_ui(
                self.macos_shortcuts,
                self.macos_shortcuts.layout(),
                self.macos_shortcuts_data,
                "macos"
            )