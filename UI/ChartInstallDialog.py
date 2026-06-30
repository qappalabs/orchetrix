import os
import yaml
import logging
import random
import string
import re
import json
import base64
import gzip
import datetime
from typing import Optional
from kubernetes import client
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QTextEdit, QHBoxLayout, QPushButton, QProgressDialog, QMessageBox,
    QCheckBox, QLabel, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QCoreApplication
from UI.ThemeManager import get_theme_manager
from UI.ThemeAwarePage import ThemeAwareMixin
from UI.CustomComboBox import CustomComboBox
from Utils.helm_utils import (
    ensure_helm_available,
    setup_helm_repositories,
    add_repository_for_chart,
    install_helm_chart_cli,
    upgrade_helm_chart_cli,
    get_chart_from_artifacthub,
)

class HelmInstallThread(QThread):
    """Enhanced thread for installing Helm charts using Kubernetes API."""
    progress_update = pyqtSignal(str)
    progress_percentage = pyqtSignal(int)
    installation_complete = pyqtSignal(bool, str)

    def __init__(self, chart_name, repository, options):
        super().__init__()
        self.chart_name = chart_name
        self.repository = repository
        self.options = options
        self._is_cancelled = False

    def cancel(self):
        """Cancel the installation"""
        self._is_cancelled = True
        self.progress_update.emit("Cancelling installation...")

    def run(self):
        """Execute the Helm installation using Helm CLI"""
        try:
            logging.info("HelmInstallThread: Starting installation process")
            self.progress_update.emit("Checking Helm installation...")
            self.progress_percentage.emit(5)
            logging.info("HelmInstallThread: Emitted initial progress")
            self.msleep(500)  # Small delay to show progress

            if self._is_cancelled:
                return

            # Ensure Helm is available
            helm_available, helm_message = ensure_helm_available()
            if not helm_available:
                self.installation_complete.emit(False, f"Helm not available: {helm_message}")
                return

            self.progress_update.emit("Setting up repositories...")
            self.progress_percentage.emit(15)
            logging.info("HelmInstallThread: Setting up repositories")
            self.msleep(500)  # Small delay to show progress

            if self._is_cancelled:
                return

            # Setup basic repositories and add the specific repository for this chart
            setup_helm_repositories()

            # Add repository for this chart dynamically
            if self.repository:
                repo_success, repo_message = add_repository_for_chart(self.chart_name, self.repository)
                if not repo_success:
                    logging.warning(f"Failed to add repository: {repo_message}")

            self.progress_update.emit("Preparing installation...")
            self.progress_percentage.emit(25)
            logging.info("HelmInstallThread: Preparing installation")
            self.msleep(300)  # Small delay to show progress

            if self._is_cancelled:
                return

            # Validate inputs
            release_name = self.options.get("release_name", "").strip()
            namespace = self.options.get("namespace", "default").strip()
            version = self.options.get("version")
            values_yaml = self.options.get("values", "").strip()
            create_namespace = self.options.get("create_namespace", True)

            if not release_name:
                self.installation_complete.emit(False, "Release name is required.")
                return

            # Determine chart reference
            if self.repository:
                chart_ref = f"{self.repository}/{self.chart_name}"
            else:
                chart_ref = self.chart_name

            self.progress_update.emit(f"Installing {chart_ref}...")
            self.progress_percentage.emit(50)
            logging.info(f"HelmInstallThread: Installing {chart_ref}")

            if self._is_cancelled:
                return

            # Create values file if provided
            values_file = None
            if values_yaml:
                values_file = self._create_temp_values_file(values_yaml)

            try:
                # Run Helm install command with timeout handling
                success, message = install_helm_chart_cli(
                    release_name=release_name,
                    chart=chart_ref,
                    namespace=namespace,
                    values_file=values_file,
                    version=version,
                    create_namespace=create_namespace,
                    timeout=self.options.get("timeout"),
                    wait=self.options.get("wait", False),
                    atomic=self.options.get("atomic", False),
                    dry_run=self.options.get("dry_run", False),
                )

                if self._is_cancelled:
                    return

                if success:
                    logging.info("HelmInstallThread: Installation successful")
                    self.progress_percentage.emit(100)
                    self.installation_complete.emit(True, f"Successfully installed chart '{self.chart_name}' as release '{release_name}'\n\nHelm output:\n{message}")
                else:
                    logging.error("HelmInstallThread: Installation failed")
                    self.installation_complete.emit(False, f"Helm installation failed:\n{message}")

            finally:
                # Clean up temp values file
                if values_file and os.path.exists(values_file):
                    try:
                        os.remove(values_file)
                    except Exception as e:
                        logging.warning(f"Failed to remove temp values file: {e}")

        except Exception as e:
            logging.error(f"Error in helm install thread: {e}")
            import traceback
            logging.error(f"Full error traceback: {traceback.format_exc()}")
            self.installation_complete.emit(False, f"Installation error: {str(e)}\n\nPlease check the logs for more details.")

    def _create_temp_values_file(self, values_yaml):
        """Create a temporary values file"""
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(values_yaml)
                return f.name
        except Exception as e:
            logging.error(f"Failed to create temp values file: {e}")
            return None

    def _check_release_exists_api(self, k8s_client, release_name, namespace):
        """Check if release already exists using Kubernetes API"""
        try:
            secrets = k8s_client.v1.list_namespaced_secret(
                namespace=namespace,
                label_selector=f"owner=helm,name={release_name}"
            )

            if secrets.items:
                suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                suggested_name = f"{release_name}-{suffix}"
                self.installation_complete.emit(False, f"Release name '{release_name}' is already in use. Try using '{suggested_name}' instead.")
                return True

            return False

        except Exception as e:
            logging.warning(f"Error checking release existence: {e}")
            return False

    def _create_namespace_if_needed_api(self, k8s_client, namespace):
        """Create namespace if it doesn't exist using Kubernetes API"""
        try:
            # Check if namespace exists
            try:
                k8s_client.v1.read_namespace(name=namespace)
                return  # Namespace already exists
            except client.exceptions.ApiException as e:
                if e.status != 404:
                    raise

            # Create namespace
            namespace_manifest = client.V1Namespace(
                metadata=client.V1ObjectMeta(name=namespace)
            )
            k8s_client.v1.create_namespace(body=namespace_manifest)
            logging.info(f"Created namespace: {namespace}")

        except Exception as e:
            logging.warning(f"Error creating namespace: {e}")

    def _apply_manifests_to_cluster(self, k8s_client, manifests, release_name, namespace):
        """Apply Kubernetes manifests to cluster"""
        try:
            for manifest in manifests:
                # Add Helm labels
                if "metadata" not in manifest:
                    manifest["metadata"] = {}
                if "labels" not in manifest["metadata"]:
                    manifest["metadata"]["labels"] = {}

                manifest["metadata"]["labels"].update({
                    "app.kubernetes.io/managed-by": "Helm",
                    "app.kubernetes.io/instance": release_name
                })

                # Apply manifest based on kind
                kind = manifest.get("kind", "").lower()

                if kind == "deployment":
                    deployment = client.V1Deployment(
                        metadata=client.V1ObjectMeta(
                            name=manifest["metadata"]["name"],
                            namespace=namespace,
                            labels=manifest["metadata"]["labels"]
                        ),
                        spec=manifest["spec"]
                    )
                    k8s_client.apps_v1.create_namespaced_deployment(
                        namespace=namespace,
                        body=deployment
                    )

                elif kind == "service":
                    service = client.V1Service(
                        metadata=client.V1ObjectMeta(
                            name=manifest["metadata"]["name"],
                            namespace=namespace,
                            labels=manifest["metadata"]["labels"]
                        ),
                        spec=manifest["spec"]
                    )
                    k8s_client.v1.create_namespaced_service(
                        namespace=namespace,
                        body=service
                    )

                # Add more resource types as needed

            return True

        except Exception as e:
            logging.error(f"Error applying manifests: {e}")
            import traceback
            logging.error(f"Full manifest application error: {traceback.format_exc()}")
            return False

    def _create_helm_release_secret(self, k8s_client, release_name, namespace, chart_info, values_yaml):
        """Create Helm release secret"""
        try:
            # Create release info
            release_info = {
                "name": release_name,
                "info": {
                    "first_deployed": datetime.datetime.now().isoformat() + "Z",
                    "last_deployed": datetime.datetime.now().isoformat() + "Z",
                    "status": "deployed",
                    "description": "Install complete"
                },
                "chart": {
                    "metadata": {
                        "name": self.chart_name,
                        "version": chart_info.get("version", "1.0.0"),
                        "appVersion": chart_info.get("app_version", "1.0.0"),
                        "description": chart_info.get("description", "")
                    }
                },
                "config": yaml.safe_load(values_yaml) if values_yaml else {},
                "version": 1,
                "namespace": namespace
            }

            # Encode release data
            release_json = json.dumps(release_info)
            release_compressed = gzip.compress(release_json.encode('utf-8'))
            release_encoded = base64.b64encode(release_compressed).decode('utf-8')

            # Create secret
            secret_name = f"sh.helm.release.v1.{release_name}.v1"
            secret = client.V1Secret(
                metadata=client.V1ObjectMeta(
                    name=secret_name,
                    namespace=namespace,
                    labels={
                        "owner": "helm",
                        "name": release_name,
                        "status": "deployed",
                        "version": "1"
                    }
                ),
                data={
                    "release": release_encoded
                }
            )

            k8s_client.v1.create_namespaced_secret(
                namespace=namespace,
                body=secret
            )

            logging.info(f"Created Helm release secret: {secret_name}")

        except Exception as e:
            logging.error(f"Error creating Helm release secret: {e}")


class ChartInstallDialog(ThemeAwareMixin, QDialog):
    """Enhanced chart install dialog with improved validation and user experience"""

    # Class variable to track dialog instances
    _active_dialogs = set()

    def __init__(self, chart_name, repository, parent=None):
        super().__init__(parent)
        self.chart_name = chart_name
        self.repository = repository
        self.default_values = {}
        self.chart_metadata = {}
        self.validation_timer = QTimer()
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self._validate_form)

        # Track this dialog instance
        ChartInstallDialog._active_dialogs.add(self)

        self.setWindowTitle(f"Install Chart: {chart_name}")
        self.setMinimumSize(600, 500)
        
        self.setup_ui()
        
        # Apply theme-aware styling
        self.apply_styles()
    
    def apply_styles(self):
        """Apply comprehensive theme-aware styling to the dialog"""
        theme = get_theme_manager().get_current_theme()
        
        # Store theme manager for theme changes
        self._theme_manager = get_theme_manager()
        
        # Apply main dialog styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme.colors.BG_DARK};
                color: {theme.colors.TEXT_LIGHT};
            }}
            QTabWidget::pane {{
                border: 1px solid {theme.colors.BORDER_COLOR};
                background-color: {theme.colors.BG_DARK};
            }}
            QTabWidget::tab-bar {{
                alignment: left;
            }}
            QTabBar::tab {{
                background-color: {theme.colors.BG_MEDIUM};
                color: {theme.colors.TEXT_LIGHT};
                border: 1px solid {theme.colors.BORDER_COLOR};
                padding: 8px 16px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {theme.colors.BG_DARK};
                border-bottom: 2px solid {theme.colors.ACCENT_BLUE};
            }}
            QTabBar::tab:hover {{
                background-color: {theme.colors.HOVER_BG};
            }}
        """)
        
        # Apply input field styling - match releases page theme consistency
        if hasattr(self, 'release_name_input'):
            self.release_name_input.setStyleSheet(self._get_input_field_style())
        
        if hasattr(self, 'namespace_combo'):
            # CustomComboBox handles its own theme styling natively
            pass
        
        if hasattr(self, 'version_input'):
            self.version_input.setStyleSheet(self._get_input_field_style())
        
        if hasattr(self, 'values_editor'):
            self.values_editor.setStyleSheet(self._get_text_edit_style())
        
        if hasattr(self, 'timeout_input'):
            self.timeout_input.setStyleSheet(self._get_input_field_style())
        
        # Apply checkbox styling
        checkboxes = [
            getattr(self, 'create_namespace_checkbox', None),
            getattr(self, 'wait_checkbox', None),
            getattr(self, 'atomic_checkbox', None),
            getattr(self, 'dry_run_checkbox', None)
        ]
        
        for checkbox in checkboxes:
            if checkbox:
                checkbox.setStyleSheet(f"color: {theme.colors.TEXT_LIGHT}; font-size: 13px;")
        
        # Apply label styling for validation labels
        if hasattr(self, 'yaml_validation_label') and self.yaml_validation_label:
            self.yaml_validation_label.setStyleSheet(f"color: {theme.colors.TEXT_SUBTLE}; font-size: 12px; margin-top: 5px;")

        if hasattr(self, 'validation_status') and self.validation_status:
            self.validation_status.setStyleSheet(f"color: {theme.colors.TEXT_SUBTLE}; font-size: 12px; margin: 5px 0;")

        # Apply header label styling
        if hasattr(self, 'name_label') and self.name_label:
            self.name_label.setStyleSheet(f"color: {theme.colors.TEXT_LIGHT}; font-weight: bold;")

        if hasattr(self, 'repo_label') and self.repo_label:
            self.repo_label.setStyleSheet(f"color: {theme.colors.TEXT_SUBTLE}; font-size: 14px;")

        # Note: Button styling is kept as original inline styles in create_button_box()
        # to preserve the install button's font-weight: bold and original colors

    def _get_input_field_style(self):
        """Input field (QLineEdit, QSpinBox) style - theme-aware, matches releases page"""
        theme = get_theme_manager().get_current_theme()
        return f"""
            QLineEdit, QSpinBox {{
                background-color: {theme.colors.BG_LIGHT};
                color: {theme.colors.TEXT_LIGHT};
                border: 1px solid {theme.colors.BORDER_COLOR};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border-color: {theme.colors.ACCENT_BLUE};
                background-color: {theme.colors.BG_MEDIUM};
            }}
        """

    def _get_dropdown_style(self):
        """Dropdown (QComboBox) style - theme-aware, matches original sizing"""
        theme = get_theme_manager().get_current_theme()
        return f"""
            QComboBox {{
                background-color: {theme.colors.BG_LIGHT};
                color: {theme.colors.TEXT_LIGHT};
                border: 1px solid {theme.colors.BORDER_COLOR};
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                min-width: 150px;
            }}
            QComboBox:focus {{
                border: 1px solid {theme.colors.ACCENT_BLUE};
                background-color: {theme.colors.BG_MEDIUM};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {theme.colors.TEXT_LIGHT};
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.colors.BG_LIGHT};
                color: {theme.colors.TEXT_LIGHT};
                border: 1px solid {theme.colors.BORDER_COLOR};
                selection-background-color: {theme.colors.ACCENT_BLUE};
            }}
        """

    def _get_text_edit_style(self):
        """Text editor (QTextEdit) style - theme-aware, matches releases page"""
        theme = get_theme_manager().get_current_theme()
        return f"""
            QTextEdit {{
                background-color: {theme.colors.BG_DARK};
                color: {theme.colors.TEXT_LIGHT};
                border: 1px solid {theme.colors.BORDER_COLOR};
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 13px;
                line-height: 1.4;
            }}
            QTextEdit:focus {{
                border-color: {theme.colors.ACCENT_BLUE};
                background-color: {theme.colors.BG_MEDIUM};
            }}
        """

    def _on_theme_changed(self, theme_name):
        """Handle theme change events"""
        # Refresh all styling
        self.apply_styles()

    def closeEvent(self, event):
        """Handle dialog close event"""
        # Remove this dialog from active dialogs
        ChartInstallDialog._active_dialogs.discard(self)
        super().closeEvent(event)

    def reject(self):
        """Handle dialog rejection"""
        # Remove this dialog from active dialogs
        ChartInstallDialog._active_dialogs.discard(self)
        super().reject()

    def accept(self):
        """Handle dialog acceptance"""
        # Remove this dialog from active dialogs
        ChartInstallDialog._active_dialogs.discard(self)
        super().accept()

    @classmethod
    def has_active_dialogs(cls):
        """Check if there are any active install dialogs"""
        return len(cls._active_dialogs) > 0

    @classmethod
    def get_active_dialog_count(cls):
        """Get the number of active install dialogs"""
        return len(cls._active_dialogs)
        
    def setup_ui(self):
        """Setup the enhanced dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Chart info header
        self.create_chart_info_header(layout)
        
        # Tab widget for different sections
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Basic configuration tab
        self.setup_basic_config_tab()
        
        # Values tab
        self.setup_values_tab()
        
        # Advanced tab
        self.setup_advanced_tab()
        
        # Validation status
        self.setup_validation_status(layout)
        
        # Button box
        self.create_button_box(layout)

    def create_chart_info_header(self, layout):
        """Create enhanced chart information header"""
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 10)

        # Title row
        title_layout = QHBoxLayout()

        self.name_label = QLabel(f"<h2>{self.chart_name}</h2>")
        title_layout.addWidget(self.name_label)

        title_layout.addStretch()

        self.repo_label = QLabel(f"Repository: {self.repository}")
        title_layout.addWidget(self.repo_label)

        info_layout.addLayout(title_layout)
        layout.addWidget(info_widget)

    def setup_basic_config_tab(self):
        """Setup enhanced basic configuration tab"""
        basic_widget = QWidget()
        basic_layout = QFormLayout(basic_widget)
        basic_layout.setSpacing(15)
        
        # Release name with validation
        self.release_name_input = QLineEdit()
        self.release_name_input.setText(f"{self.chart_name}-{''.join(random.choices(string.ascii_lowercase, k=4))}")
        self.release_name_input.setStyleSheet(self._get_input_field_style())
        self.release_name_input.textChanged.connect(self._start_validation_timer)
        basic_layout.addRow("Release Name:", self.release_name_input)
        
        # Namespace dropdown
        self.namespace_combo = CustomComboBox()
        # CustomComboBox handles its own styling and is currently read-only
        self.load_namespaces()
        self.namespace_combo.currentTextChanged.connect(self._start_validation_timer)
        basic_layout.addRow("Namespace:", self.namespace_combo)
        
        # Version
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("Latest")
        self.version_input.setStyleSheet(self._get_input_field_style())
        basic_layout.addRow("Chart Version:", self.version_input)
        
        # Create namespace option
        self.create_namespace_checkbox = QCheckBox("Create namespace if it doesn't exist")
        self.create_namespace_checkbox.setChecked(True)
        self.create_namespace_checkbox.setStyleSheet(f"color: {get_theme_manager().get_current_theme().colors.TEXT_LIGHT}; font-size: 13px;")
        basic_layout.addRow("", self.create_namespace_checkbox)
        
        self.tab_widget.addTab(basic_widget, "Basic Configuration")

    def setup_values_tab(self):
        """Setup enhanced values editing tab"""
        values_widget = QWidget()
        values_layout = QVBoxLayout(values_widget)
        
        # Values editor
        self.values_editor = QTextEdit()
        self.values_editor.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.4;
            }
            QTextEdit:focus {
                border: 1px solid #0078d7;
            }
        """)
        self.values_editor.setPlaceholderText("# Your custom values will appear here\n# Edit as needed before installation")
        self.values_editor.textChanged.connect(self._start_validation_timer)
        values_layout.addWidget(self.values_editor)
        
        # Validation status for YAML
        self.yaml_validation_label = QLabel("")
        self.yaml_validation_label.setStyleSheet("color: #888888; font-size: 12px; margin-top: 5px;")
        values_layout.addWidget(self.yaml_validation_label)
        
        self.tab_widget.addTab(values_widget, "Values Configuration")

    def setup_advanced_tab(self):
        """Setup enhanced advanced configuration tab"""
        advanced_widget = QWidget()
        advanced_layout = QFormLayout(advanced_widget)
        advanced_layout.setSpacing(15)
        
        # Timeout
        self.timeout_input = QLineEdit()
        self.timeout_input.setText("300")
        self.timeout_input.setPlaceholderText("300")
        self.timeout_input.setStyleSheet(self.get_input_style())
        advanced_layout.addRow("Timeout (seconds):", self.timeout_input)
        
        # Wait for resources
        self.wait_checkbox = QCheckBox("Wait for all resources to be ready")
        self.wait_checkbox.setChecked(True)
        self.wait_checkbox.setStyleSheet("color: #ffffff; font-size: 13px;")
        advanced_layout.addRow("", self.wait_checkbox)
        
        # Atomic installation
        self.atomic_checkbox = QCheckBox("Atomic installation (rollback on failure)")
        self.atomic_checkbox.setChecked(True)
        self.atomic_checkbox.setStyleSheet("color: #ffffff; font-size: 13px;")
        advanced_layout.addRow("", self.atomic_checkbox)
        
        # Dry run
        self.dry_run_checkbox = QCheckBox("Dry run (validate without installing)")
        self.dry_run_checkbox.setStyleSheet("color: #ffffff; font-size: 13px;")
        advanced_layout.addRow("", self.dry_run_checkbox)
        
        self.tab_widget.addTab(advanced_widget, "Advanced Options")

    def setup_validation_status(self, layout):
        """Setup form validation status display"""
        self.validation_status = QLabel("")
        self.validation_status.setStyleSheet("color: #888888; font-size: 12px; margin: 5px 0;")
        layout.addWidget(self.validation_status)

    def _on_cancel_clicked(self):
        """Handle cancel button click"""
        self.reject()
        
    def create_button_box(self, layout):
        """Create enhanced dialog button box"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        
        self.install_button = QPushButton("Install Chart")
        self.install_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0086e7;
            }
            QPushButton:pressed {
                background-color: #0063b1;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.install_button.clicked.connect(self._on_install_clicked)
        self.install_button.setEnabled(True)
    
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.install_button)
        
        layout.addLayout(button_layout)
    
    def _on_install_clicked(self):
        """Handle install button click with validation"""
        # Prevent multiple installations if other dialogs are active
        if ChartInstallDialog.get_active_dialog_count() > 1:
            QMessageBox.warning(self, "Multiple Dialogs", 
                               "Please close other installation dialogs before proceeding.")
            return
        
        # Run final validation synchronously so a quick click cannot bypass
        # the 500ms debounced validation (e.g. type an invalid name then
        # immediately click Install before the timer fires).
        self.validation_timer.stop()
        self._validate_form()
        if not self.install_button.isEnabled():
            return

        # Proceed with acceptance
        self.accept()

    def get_input_style(self):
        """Get consistent input field styling"""
        return """
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }
        """

    def get_combo_style(self):
        """Get consistent combo box styling"""
        return """
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                min-width: 150px;
            }
            QComboBox:focus {
                border: 1px solid #0078d7;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                selection-background-color: #0078d7;
            }
        """

    def load_namespaces(self):
        """Load available namespaces using Kubernetes API"""
        try:
            from Utils.kubernetes_client import get_kubernetes_client
            
            k8s_client = get_kubernetes_client()
            if k8s_client and k8s_client.v1:
                # Get namespaces using Kubernetes API
                namespaces_list = k8s_client.v1.list_namespace()
                namespaces = sorted([ns.metadata.name for ns in namespaces_list.items])
                self.namespace_combo.addItems(namespaces)
                if "default" in namespaces:
                    self.namespace_combo.setCurrentText("default")
            else:
                self.namespace_combo.addItem("default")
        except Exception as e:
            self.namespace_combo.addItem("default")
            logging.warning(f"Could not load namespaces: {e}")

    def _start_validation_timer(self):
        """Start validation timer to avoid excessive validation"""
        self.validation_timer.start(500)  # 500ms delay

    def _validate_form(self):
        """Enhanced form validation with detailed feedback"""
        errors = []
        warnings = []
        
        # Validate release name
        release_name = self.release_name_input.text().strip()
        if not release_name:
            errors.append("Release name is required")
        elif not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', release_name):
            errors.append("Release name must be lowercase alphanumeric with hyphens")
        elif len(release_name) > 53:
            errors.append("Release name must be 53 characters or less")
        
        # Validate namespace
        namespace = self.namespace_combo.currentText().strip()
        if not namespace:
            errors.append("Namespace is required")
        elif not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', namespace):
            errors.append("Namespace must be lowercase alphanumeric with hyphens")
        
        # Validate YAML
        yaml_error = self._validate_yaml()
        if yaml_error:
            errors.append(f"YAML Error: {yaml_error}")

        # Validate timeout (consumed as int seconds in get_values)
        timeout_text = self.timeout_input.text().strip() or "300"
        if not timeout_text.isdigit() or int(timeout_text) <= 0:
            errors.append("Timeout must be a positive whole number of seconds")

        # Update validation status
        if errors:
            self.validation_status.setText(f"❌ {'; '.join(errors)}")
            self.validation_status.setStyleSheet("color: #f44336; font-size: 12px; margin: 5px 0;")
            self.install_button.setEnabled(False)
        elif warnings:
            self.validation_status.setText(f"⚠️ {'; '.join(warnings)}")
            self.validation_status.setStyleSheet("color: #ff9800; font-size: 12px; margin: 5px 0;")
            self.install_button.setEnabled(True)
        else:
            self.validation_status.setText("✅ All validations passed")
            self.validation_status.setStyleSheet("color: #4CAF50; font-size: 12px; margin: 5px 0;")
            self.install_button.setEnabled(True)

    def _validate_yaml(self) -> Optional[str]:
        """Validate YAML syntax in the editor"""
        try:
            text = self.values_editor.toPlainText().strip()
            if text:
                yaml.safe_load(text)
                self.yaml_validation_label.setText("✅ Valid YAML")
                self.yaml_validation_label.setStyleSheet("color: #4CAF50; font-size: 12px; margin-top: 5px;")
            else:
                self.yaml_validation_label.setText("Empty values")
                self.yaml_validation_label.setStyleSheet("color: #888888; font-size: 12px; margin-top: 5px;")
            return None
        except yaml.YAMLError as e:
            error_msg = str(e)
            self.yaml_validation_label.setText(f"❌ YAML Error: {error_msg}")
            self.yaml_validation_label.setStyleSheet("color: #f44336; font-size: 12px; margin-top: 5px;")
            return error_msg

    def get_values(self):
        """Get validated values from the dialog"""
        # Final validation before accepting
        if not self.install_button.isEnabled():
            return None
        
        values_text = self.values_editor.toPlainText().strip()

        if values_text:
            try:
                yaml.safe_load(values_text)
            except yaml.YAMLError as e:
                QMessageBox.critical(self, "Invalid YAML", f"Error parsing values: {e}")
                return None

        # Coerce timeout defensively even though _validate_form already guards it.
        try:
            timeout_value = int(self.timeout_input.text().strip() or "300")
            if timeout_value <= 0:
                timeout_value = 300
        except ValueError:
            timeout_value = 300

        return {
            "release_name": self.release_name_input.text().strip(),
            "namespace": self.namespace_combo.currentText().strip(),
            "version": self.version_input.text().strip() or None,
            "values": values_text,
            "create_namespace": self.create_namespace_checkbox.isChecked(),
            "timeout": timeout_value,
            "wait": self.wait_checkbox.isChecked(),
            "atomic": self.atomic_checkbox.isChecked(),
            "dry_run": self.dry_run_checkbox.isChecked(),
            "repository": {
                "type": "name",
                "value": self.repository
            }
        }


# Global variable to track installation state and prevent duplicates
_installation_in_progress = False
_current_progress_dialog = None

def install_helm_chart(chart_name, repository, options, parent=None):
    """
    Enhanced function to trigger Helm installation with better error handling and user feedback.
    Includes duplicate installation prevention.
    """
    global _installation_in_progress, _current_progress_dialog

    # Prevent multiple installations from running simultaneously
    if _installation_in_progress:
        error_msg = "Another chart installation is already in progress. Please wait for it to complete."
        if parent:
            QMessageBox.warning(parent, "Installation in Progress", error_msg)
        else:
            logging.warning(error_msg)
        return False, error_msg

    if not chart_name or not repository:
        error_msg = "Chart name and repository are required."
        if parent:
            QMessageBox.critical(parent, "Installation Error", error_msg)
        else:
            logging.error(error_msg)
        return False, error_msg

    if options is None:
        error_msg = "Installation options are missing."
        if parent:
            QMessageBox.critical(parent, "Installation Error", error_msg)
        else:
            logging.error(error_msg)
        return False, error_msg

    try:
        # Set global installation state
        _installation_in_progress = True

        # Create enhanced progress dialog
        progress = QProgressDialog("Preparing installation...", "Cancel", 0, 100, parent)
        progress.setWindowTitle(f"Installing {chart_name}")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        # Store reference to current progress dialog
        _current_progress_dialog = progress

        # Create installation thread
        install_thread = HelmInstallThread(chart_name, repository, options)

        # Track completion
        result = {"success": False, "message": "", "completed": False}

        def on_complete(success, message):
            global _installation_in_progress, _current_progress_dialog

            logging.info(f"install_helm_chart: on_complete called with success={success}")

            # Close progress dialog
            if progress:
                progress.close()
            _current_progress_dialog = None

            result["success"] = success
            result["message"] = message
            result["completed"] = True

            # Reset global installation state
            _installation_in_progress = False

            logging.info(f"install_helm_chart: result set to success={success}")

            # Don't show result dialogs here - let the calling code handle them
            # This prevents duplicate dialogs

        # Connect signals with direct connection to ensure they work across threads
        install_thread.progress_update.connect(progress.setLabelText, Qt.ConnectionType.QueuedConnection)
        install_thread.progress_percentage.connect(progress.setValue, Qt.ConnectionType.QueuedConnection)
        install_thread.installation_complete.connect(on_complete, Qt.ConnectionType.BlockingQueuedConnection)

        # Handle cancellation
        def on_canceled():
            # Only request cancellation here. Do NOT release the global install
            # lock yet — the worker may still be blocked in subprocess.run().
            # The lock is released after install_thread.wait() returns below,
            # once the worker has actually stopped.
            install_thread.cancel()

        progress.canceled.connect(on_canceled)

        # Start installation
        install_thread.start()

        # Process events while waiting to keep UI responsive and show progress
        timeout_counter = 0
        # Poll long enough to cover the user-selected Helm --timeout (plus a
        # buffer) so --wait/--atomic installs aren't terminated prematurely.
        try:
            _helm_timeout_secs = int(options.get("timeout") or 300)
        except (TypeError, ValueError):
            _helm_timeout_secs = 300
        max_timeout = max(3600, int((_helm_timeout_secs + 120) * 1000 / 50))  # 50ms per tick

        while install_thread.isRunning() and timeout_counter < max_timeout and not result["completed"]:
            QCoreApplication.processEvents()
            install_thread.msleep(50)  # Small delay
            timeout_counter += 1

        # Check for timeout
        if timeout_counter >= max_timeout and not result["completed"]:
            logging.error("install_helm_chart: Installation timed out")
            install_thread.cancel()
            install_thread.wait(2000)  # Wait 2 seconds for graceful shutdown
            if install_thread.isRunning():
                install_thread.terminate()  # Force terminate if still running
            result["success"] = False
            _timed_out_secs = int(max_timeout * 50 / 1000)
            result["message"] = (f"Installation command timed out after {_timed_out_secs} seconds. This usually happens when:\n\n"
                              "1. Chart download is slow\n"
                              "2. Kubernetes cluster is not responding\n"
                              "3. Network connectivity issues\n\n"
                              "Note: The chart may still be installing in the background.\n"
                              "Check the Releases page to see if installation completed.")
            result["completed"] = True

        # Ensure thread is fully finished
        install_thread.wait()

        # Worker has fully stopped. Release the global lock here so it is held
        # for the entire lifetime of the background process, including the
        # cancellation path where on_complete never fires.
        _installation_in_progress = False
        _current_progress_dialog = None

        # If the completion callback wasn't called but the thread finished, check the thread state
        if not result["completed"]:
            logging.warning("install_helm_chart: Thread finished but completion callback not called")
            # Check if the thread has a result stored
            if hasattr(install_thread, 'install_success') and hasattr(install_thread, 'install_message'):
                result["success"] = install_thread.install_success
                result["message"] = install_thread.install_message
                logging.info(f"install_helm_chart: Retrieved result from thread: success={result['success']}")
            else:
                # Default to failure if we can't determine the result
                result["success"] = False
                result["message"] = "Installation completed but result unknown"

        logging.info(f"install_helm_chart: Returning success={result['success']}, message='{result['message'][:100] if result['message'] else 'No message'}...'")
        return result["success"], result["message"]

    except Exception as e:
        # Reset global state on error
        _installation_in_progress = False
        _current_progress_dialog = None

        import traceback
        error_msg = f"Installation failed: {str(e)}"
        logging.error(f"Install function error: {error_msg}")
        logging.error(f"Full traceback: {traceback.format_exc()}")
        if parent:
            QMessageBox.critical(parent, "Installation Error", error_msg)
        return False, error_msg


class HelmUpgradeThread(QThread):
    """Thread for upgrading Helm releases using Kubernetes API"""
    progress_update = pyqtSignal(str)
    progress_percentage = pyqtSignal(int)
    upgrade_complete = pyqtSignal(bool, str)

    def __init__(self, release_name, namespace, chart_name, repository, options):
        super().__init__()
        self.release_name = release_name
        self.namespace = namespace
        self.chart_name = chart_name
        self.repository = repository
        self.options = options
        self._is_cancelled = False

    def cancel(self):
        """Cancel the upgrade"""
        self._is_cancelled = True
        self.progress_update.emit("Cancelling upgrade...")

    def run(self):
        """Execute the Helm upgrade using the Helm CLI.

        The previous implementation rendered manifests via the now-deprecated
        download_chart_manifest() (which returns None) and applied them by hand
        through the Kubernetes API. That path always failed and could not update
        a real Helm release. We now drive `helm upgrade` directly, mirroring the
        proven install path.
        """
        values_file = None
        try:
            self.progress_update.emit("Initializing upgrade...")
            self.progress_percentage.emit(5)

            if self._is_cancelled:
                return

            # Ensure Helm is available
            helm_available, helm_message = ensure_helm_available()
            if not helm_available:
                self.upgrade_complete.emit(False, f"Helm not available: {helm_message}")
                return

            if self._is_cancelled:
                return

            self.progress_update.emit("Setting up repositories...")
            self.progress_percentage.emit(20)

            setup_helm_repositories()
            if self.repository:
                add_repository_for_chart(self.chart_name, self.repository)

            if self._is_cancelled:
                return

            version = self.options.get("version")
            values_yaml = self.options.get("values", "").strip()

            # Determine chart reference
            if self.repository:
                chart_ref = f"{self.repository}/{self.chart_name}"
            else:
                chart_ref = self.chart_name

            # Write custom values to a temp file if provided
            if values_yaml:
                try:
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                        f.write(values_yaml)
                        values_file = f.name
                except Exception as e:
                    logging.warning(f"Failed to create temp values file: {e}")

            self.progress_update.emit(f"Upgrading {self.release_name}...")
            self.progress_percentage.emit(60)

            if self._is_cancelled:
                return

            success, message = upgrade_helm_chart_cli(
                release_name=self.release_name,
                chart=chart_ref,
                namespace=self.namespace,
                values_file=values_file,
                version=version,
            )

            if self._is_cancelled:
                return

            if success:
                self.progress_percentage.emit(100)
                self.upgrade_complete.emit(True, f"Successfully upgraded release '{self.release_name}' to chart '{self.chart_name}'\n\nHelm output:\n{message}")
            else:
                self.upgrade_complete.emit(False, f"Helm upgrade failed:\n{message}")

        except Exception as e:
            logging.error(f"Error in helm upgrade thread: {e}")
            self.upgrade_complete.emit(False, f"Upgrade error: {str(e)}")
        finally:
            if values_file and os.path.exists(values_file):
                try:
                    os.remove(values_file)
                except Exception as e:
                    logging.warning(f"Failed to remove temp values file: {e}")

    def _check_release_exists_api(self, k8s_client, release_name, namespace):
        """Check if release exists using Kubernetes API"""
        try:
            secrets = k8s_client.v1.list_namespaced_secret(
                namespace=namespace,
                label_selector=f"owner=helm,name={release_name}"
            )
            return len(secrets.items) > 0
        except Exception as e:
            logging.warning(f"Error checking release existence: {e}")
            return False

    def _update_manifests_in_cluster(self, k8s_client, manifests, release_name, namespace):
        """Update Kubernetes manifests in cluster"""
        try:
            for manifest in manifests:
                # Add Helm labels
                if "metadata" not in manifest:
                    manifest["metadata"] = {}
                if "labels" not in manifest["metadata"]:
                    manifest["metadata"]["labels"] = {}

                manifest["metadata"]["labels"].update({
                    "app.kubernetes.io/managed-by": "Helm",
                    "app.kubernetes.io/instance": release_name
                })

                # Apply manifest based on kind
                kind = manifest.get("kind", "").lower()
                name = manifest["metadata"]["name"]

                if kind == "deployment":
                    deployment = client.V1Deployment(
                        metadata=client.V1ObjectMeta(
                            name=name,
                            namespace=namespace,
                            labels=manifest["metadata"]["labels"]
                        ),
                        spec=manifest["spec"]
                    )
                    try:
                        # Try to patch existing deployment
                        k8s_client.apps_v1.patch_namespaced_deployment(
                            name=name,
                            namespace=namespace,
                            body=deployment
                        )
                    except client.exceptions.ApiException as e:
                        if e.status == 404:
                            # Create if doesn't exist
                            k8s_client.apps_v1.create_namespaced_deployment(
                                namespace=namespace,
                                body=deployment
                            )
                        else:
                            raise

                elif kind == "service":
                    service = client.V1Service(
                        metadata=client.V1ObjectMeta(
                            name=name,
                            namespace=namespace,
                            labels=manifest["metadata"]["labels"]
                        ),
                        spec=manifest["spec"]
                    )
                    try:
                        # Try to patch existing service
                        k8s_client.v1.patch_namespaced_service(
                            name=name,
                            namespace=namespace,
                            body=service
                        )
                    except client.exceptions.ApiException as e:
                        if e.status == 404:
                            # Create if doesn't exist
                            k8s_client.v1.create_namespaced_service(
                                namespace=namespace,
                                body=service
                            )
                        else:
                            raise

                # Add more resource types as needed

            return True

        except Exception as e:
            logging.error(f"Error updating manifests: {e}")
            return False

    def _update_helm_release_secret(self, k8s_client, release_name, namespace, chart_info, values_yaml):
        """Update Helm release secret with new revision"""
        try:
            # Get existing release secrets
            secrets = k8s_client.v1.list_namespaced_secret(
                namespace=namespace,
                label_selector=f"owner=helm,name={release_name}"
            )

            # Find highest revision
            current_revision = 0
            for secret in secrets.items:
                secret_name = secret.metadata.name
                if secret_name.startswith(f"sh.helm.release.v1.{release_name}.v"):
                    try:
                        rev = int(secret_name.split('.v')[-1])
                        current_revision = max(current_revision, rev)
                    except (ValueError, IndexError):
                        continue

            new_revision = current_revision + 1

            # Create updated release info
            release_info = {
                "name": release_name,
                "info": {
                    "first_deployed": datetime.datetime.now().isoformat() + "Z",
                    "last_deployed": datetime.datetime.now().isoformat() + "Z",
                    "status": "deployed",
                    "description": "Upgrade complete"
                },
                "chart": {
                    "metadata": {
                        "name": self.chart_name,
                        "version": chart_info.get("version", "1.0.0"),
                        "appVersion": chart_info.get("app_version", "1.0.0"),
                        "description": chart_info.get("description", "")
                    }
                },
                "config": yaml.safe_load(values_yaml) if values_yaml else {},
                "version": new_revision,
                "namespace": namespace
            }

            # Encode release data
            release_json = json.dumps(release_info)
            release_compressed = gzip.compress(release_json.encode('utf-8'))
            release_encoded = base64.b64encode(release_compressed).decode('utf-8')

            # Create new secret
            secret_name = f"sh.helm.release.v1.{release_name}.v{new_revision}"
            secret = client.V1Secret(
                metadata=client.V1ObjectMeta(
                    name=secret_name,
                    namespace=namespace,
                    labels={
                        "owner": "helm",
                        "name": release_name,
                        "status": "deployed",
                        "version": str(new_revision)
                    }
                ),
                data={
                    "release": release_encoded
                }
            )

            k8s_client.v1.create_namespaced_secret(
                namespace=namespace,
                body=secret
            )

            logging.info(f"Created Helm release secret: {secret_name}")

        except Exception as e:
            logging.error(f"Error updating Helm release secret: {e}")



def upgrade_helm_release(release_name, namespace, chart_name, repository, options, parent=None):
    """Function to trigger Helm release upgrade"""
    if not all([release_name, namespace, chart_name, repository]):
        error_msg = "Release name, namespace, chart name, and repository are required."
        if parent:
            QMessageBox.critical(parent, "Upgrade Error", error_msg)
        else:
            logging.error(error_msg)
        return False, error_msg

    if options is None:
        error_msg = "Upgrade options are missing."
        if parent:
            QMessageBox.critical(parent, "Upgrade Error", error_msg)
        else:
            logging.error(error_msg)
        return False, error_msg

    try:
        # Create progress dialog
        progress = QProgressDialog("Preparing upgrade...", "Cancel", 0, 100, parent)
        progress.setWindowTitle(f"Upgrading {release_name}")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        # Create upgrade thread
        upgrade_thread = HelmUpgradeThread(release_name, namespace, chart_name, repository, options)

        # Track completion
        result = {"success": False, "message": "", "completed": False}

        def on_complete(success, message):
            progress.close()
            result["success"] = success
            result["message"] = message
            result["completed"] = True

        # Connect signals
        upgrade_thread.progress_update.connect(progress.setLabelText)
        upgrade_thread.progress_percentage.connect(progress.setValue)
        upgrade_thread.upgrade_complete.connect(on_complete, Qt.ConnectionType.BlockingQueuedConnection)
        progress.canceled.connect(upgrade_thread.cancel)

        # Start upgrade
        upgrade_thread.start()

        # Keep the Qt event loop running instead of blocking on wait() so the
        # progress dialog repaints and Cancel works while the worker runs.
        while upgrade_thread.isRunning() and not result["completed"]:
            QCoreApplication.processEvents()
            upgrade_thread.msleep(50)
        upgrade_thread.wait()  # returns immediately; thread already finished

        return result["success"], result["message"]

    except Exception as e:
        error_msg = f"Upgrade failed: {str(e)}"
        if parent:
            QMessageBox.critical(parent, "Upgrade Error", error_msg)
        return False, error_msg
