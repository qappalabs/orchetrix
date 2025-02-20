import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

class SearchBar(QLineEdit):
    def __init__(self, table, parent=None):
        super().__init__(parent)
        self.table = table
        self.setPlaceholderText("Search...")
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2D2D2D;
                border: 1px solid #3D3D3D;
                border-radius: 4px;
                padding: 8px 32px;
                color: white;
                min-width: 200px;
            }
            QLineEdit:focus {
                background-color: #3D3D3D;
            }
        """)
        
        # Add search icon
        search_icon = QLabel(self)
        search_icon.setPixmap(QIcon.fromTheme("edit-find").pixmap(16, 16))
        search_icon.setStyleSheet("background: transparent;")
        search_icon.setGeometry(8, 8, 16, 16)
        search_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.textChanged.connect(self.on_search)

    def on_search(self, text):
        search_text = text.lower()
        for row in range(self.table.rowCount()):
            row_visible = False
            # Get text from widget in first column (Name column)
            name_widget = self.table.cellWidget(row, 0)
            if name_widget:
                label = name_widget.findChild(QLabel, "name_label")
                if label and search_text in label.text().lower():
                    row_visible = True
            # Search in other columns
            if not row_visible:
                for col in range(1, self.table.columnCount() - 1):  # Exclude last column (menu)
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        row_visible = True
                        break
            self.table.setRowHidden(row, not row_visible)

class NameCell(QWidget):
    def __init__(self, icon_text, name, color=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)
        if color:  # For colored tags (Ox, KD, etc.)
            icon = QLabel()
            icon.setFixedSize(28, 16)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setText(icon_text)
            icon.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    color: black;
                    border-radius: 2px;
                    font-size: 10px;
                    font-weight: bold;
                }}
            """)
        else:  # For emoji icons
            icon = QLabel(icon_text)
            icon.setFixedWidth(20)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label = QLabel(name)
        name_label.setObjectName("name_label")  # For search functionality
        layout.addWidget(icon)
        layout.addWidget(name_label)
        layout.addStretch()

class OrchestrixGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Orchetrix')
        self.setMinimumSize(1200, 700)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1A1A1A;
                color: white;
            }
        """)
        # Main widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        # Header
        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet("""
            QWidget {
                background-color: #1A1A1A;
                border-bottom: 1px solid #2D2D2D;
            }
        """)

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 50))  # Semi-transparent black
        shadow.setOffset(0, 2)
        header.setGraphicsEffect(shadow)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 10, 0)
        header_layout.setSpacing(50)  # Increased spacing between logo and add button
        
        # Logo
        logo = QLabel()
        logo_pixmap = QPixmap("C:/Developer/logos/Group 31.png")  # Replace with your logo path
        scaled_pixmap = logo_pixmap.scaled(120, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo.setPixmap(scaled_pixmap)
        logo.setStyleSheet("padding: 0; margin: 0;")
        
        # Cluster dropdown in center
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

        # Create cluster menu and set fixed width to match the dropdown button
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

        # Add sample clusters (replace with your actual cluster data)
        clusters = ["docker-desktop", "minikube", "kind-cluster"]
        for cluster in clusters:
            action = QAction(cluster, self)
            action.setCheckable(True)  # Make the action checkable
            action.triggered.connect(lambda checked, c=cluster: self.switch_cluster(c))
            cluster_menu.addAction(action)

        self.cluster_dropdown.setMenu(cluster_menu)
        cluster_layout.addWidget(self.cluster_dropdown)

        # Add to header layout
        header_layout.addWidget(logo)
        header_layout.addStretch()
        header_layout.addWidget(cluster_container)
        header_layout.addStretch()
        
        main_layout.addWidget(header)
        # Content area
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        # Left sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(183)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        # Browser All
        browser_btn = QPushButton("≡ Browser All")
        browser_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px 15px;
                border: none;
                color: #4A9EFF;
                width: 183px;
            }
            QPushButton:hover {
                background-color: #2D2D2D;
                width: 183px;
            }
        """)
        browser_btn.clicked.connect(self.on_browser_click)
        sidebar_layout.addWidget(browser_btn)
        # Category dropdown
        self.category_btn = QPushButton()
        category_layout = QHBoxLayout(self.category_btn)
        category_layout.setContentsMargins(15, 0, 15, 0)
        category_layout.setSpacing(0)

        text_label = QLabel("Category")
        arrow_label = QLabel("▼")
        arrow_label.setFixedWidth(20)

        category_layout.addWidget(text_label)
        category_layout.addStretch()
        category_layout.addWidget(arrow_label)

        self.category_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                border: none;
                background-color: #2D2D2D;
                color: white;
                width: 183px;
                padding: 10px 0;
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
        # Category menu
        self.category_menu = QMenu(self)
        self.category_menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D2D;
                border: 1px solid #3D3D3D;
                width: 183px;
                padding: 5px 0px;
            }
            QMenu::item {
                padding: 8px 15px;
                color: white;
                min-width: 183px;
                margin: 0px;
            }
            QMenu::item:selected {
                background-color: #3D3D3D;
            }
            QMenu::item:checked {
                background-color: #4A9EFF;
            }
            QMenu::indicator {
                width: 0px;
            }
        """)
        # Add keyboard navigation support
        self.category_menu.keyPressEvent = self.handle_menu_key_press
        # Add menu items
        categories = ["General", "Clusters", "Web Links"]
        self.category_actions = {}
        for category in categories:
            action = QAction(category, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, cat=category: self.filter_by_category(cat) if checked else None)
            self.category_menu.addAction(action)
            self.category_actions[category] = action
        # Connect button to menu
        self.category_btn.setMenu(self.category_menu)
        sidebar_layout.addWidget(self.category_btn)
        sidebar_layout.addStretch()
        sidebar.setStyleSheet("border-right: 1px solid #2D2D2D;")
        content_layout.addWidget(sidebar)
        # Main content area
        main_area = QWidget()
        main_area_layout = QVBoxLayout(main_area)
        main_area_layout.setContentsMargins(20, 10, 20, 20)
        main_area_layout.setSpacing(10)
        # Create table before the search bar
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Name", "Kind", "Source", "Label", "Status", ""])
        # Browser header with search
        browser_header = QWidget()
        browser_header_layout = QHBoxLayout(browser_header)
        browser_header_layout.setContentsMargins(0, 0, 0, 10)
        # Left side container
        header_left = QWidget()
        header_left_layout = QHBoxLayout(header_left)
        header_left_layout.setContentsMargins(0, 0, 0, 0)
        header_left_layout.setSpacing(10)
        self.title_label = QLabel("Browser All")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.count_label = QLabel("10 items")
        self.count_label.setStyleSheet("color: #666666;")
        header_left_layout.addWidget(self.title_label)
        header_left_layout.addSpacerItem(QSpacerItem(200, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        header_left_layout.addWidget(self.count_label)
        header_left.setLayout(header_left_layout)
        # Search container with fixed width
        search_container = QWidget()
        search_container.setFixedWidth(300)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        self.search_bar = SearchBar(self.table)
        search_layout.addWidget(self.search_bar)
        browser_header_layout.addWidget(header_left)
        browser_header_layout.addStretch(1)
        browser_header_layout.addWidget(search_container)
        main_area_layout.addWidget(browser_header)
        main_area_layout.addWidget(self.table)
        # Style the table
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1A1A1A;
                border: none;
                gridline-color: transparent;
            }
            QHeaderView::section {
                background-color: #1A1A1A;
                border: none;
                border-bottom: 1px solid #2D2D2D;
                padding: 8px;
                color: white;
                text-align: left;
            }
            QTableWidget::item {
                border-bottom: 1px solid #2D2D2D;
                padding: 4px;
            }
        """)
        # Add table data
        data = [
            ("⚙️", "Catalog", None, "General", "app", "", "active"),
            ("🏠", "Welcome Page", None, "General", "app", "", "active"),
            ("⚙️", "Preference", None, "General", "app", "", "active"),
            ("Ox", "Orchestrix Website", "#FFA500", "Web Links", "local", "", "available"),
            ("Ox", "Orchestrix Documentation", "#FFD700", "Web Links", "local", "", "available"),
            ("Ox", "Orchestrix Forum", "#800080", "Web Links", "local", "", "available"),
            ("Ox", "Orchestrix on X(Twitter)", "#00BFFF", "Web Links", "local", "", "available"),
            ("BL", "Orchestrix Official Blog", "#FF0000", "Web Links", "local", "", "available"),
            ("KD", "Kubernetes Documentation", "#32CD32", "Web Links", "local", "", "available"),
            ("DD", "docker-desktop", "#4CAF50", "Clusters", "local", "filter=~/.kube/cluster", "disconnected")
        ]
        self.table.setRowCount(len(data))
        for row, item in enumerate(data):
            icon, name, color, kind, source, label, status = item
            # Name column with icon
            self.table.setCellWidget(row, 0, NameCell(icon, name, color))
            # Other columns
            self.table.setItem(row, 1, QTableWidgetItem(kind))
            self.table.setItem(row, 2, QTableWidgetItem(source))
            self.table.setItem(row, 3, QTableWidgetItem(label))
            # Status with color
            status_item = QTableWidgetItem(status)
            if status == "available":
                status_item.setForeground(QColor("#00FF00"))
            elif status == "disconnected":
                status_item.setForeground(QColor("#FF0000"))
            self.table.setItem(row, 4, status_item)
            # Menu button
            menu_btn = QPushButton("⋮")
            menu_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    color: #666666;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #2D2D2D;
                    border-radius: 3px;
                }
            """)
            self.table.setCellWidget(row, 5, menu_btn)
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 30)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        for i in range(self.table.columnCount()):
            header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        content_layout.addWidget(main_area)
        main_layout.addWidget(content)
        
    def filter_by_category(self, category):
        for action in self.category_actions.values():
            action.setChecked(False)
        self.category_actions[category].setChecked(True)
        # Update the browser header
        self.update_browser_header(category)
        # Filter table
        visible_count = 0
        for row in range(self.table.rowCount()):
            if category == "All":
                self.table.setRowHidden(row, False)
                visible_count += 1
            else:
                kind = self.table.item(row, 1).text()
                is_visible = kind == category
                self.table.setRowHidden(row, not is_visible)
                if is_visible:
                    visible_count += 1
        # Update item count
        self.count_label.setText(f"{visible_count} items")

    def update_browser_header(self, category):
        self.title_label.setText(f"Browser {category}")

    def on_browser_click(self):
        # Show all items
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)
        self.update_browser_header("All")
        self.count_label.setText(f"{self.table.rowCount()} items")
        for action in self.category_actions.values():
            action.setChecked(False)

    def handle_menu_key_press(self, event):
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            # Let the default handler deal with up/down navigation
            QMenu.keyPressEvent(self.category_menu, event)
        elif event.key() == Qt.Key.Key_Return:
            # Trigger the selected action
            action = self.category_menu.activeAction()
            if action:
                action.trigger()
        else:
            # Handle other keys normally
            QMenu.keyPressEvent(self.category_menu, event)

    def switch_cluster(self, cluster_name):
        # Find the text label in the button's layout
        text_label = self.cluster_dropdown.findChild(QLabel)
        if text_label:
            text_label.setText(cluster_name)
        
        # Update the checked state of menu items
        menu = self.cluster_dropdown.menu()
        for action in menu.actions():
            action.setChecked(action.text() == cluster_name)

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = OrchestrixGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
