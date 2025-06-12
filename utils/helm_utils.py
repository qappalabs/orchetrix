"""
Utilities for working with Helm charts with proper threading and progress indication
Provides dialog and functionality for installing and managing Helm charts without UI freezing
"""

import os
import tempfile
import subprocess
import platform
import shutil
import re
import json
import random
import string
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QTextEdit, QHBoxLayout, QPushButton, QProgressDialog, QMessageBox,
    QCheckBox, QLabel, QRadioButton, QButtonGroup, QApplication 
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QEventLoop
from UI.Styles import AppColors

class HelmInstallThread(QThread):
    """Thread for installing Helm charts without blocking the UI"""
    
    # Signals for progress updates
    progress_update = pyqtSignal(str)  # Progress message
    progress_percentage = pyqtSignal(int)  # Progress percentage (0-100)
    installation_complete = pyqtSignal(bool, str)  # Success, message
    
    def __init__(self, chart_name, repository, options):
        super().__init__()
        self.chart_name = chart_name
        self.repository = repository
        self.options = options
        self._is_cancelled = False
        
    def cancel(self):
        """Cancel the installation"""
        self._is_cancelled = True
        
    def run(self):
        """Execute the Helm installation in a separate thread"""
        try:
            self.progress_update.emit("Initializing installation...")
            self.progress_percentage.emit(5)
            
            if self._is_cancelled:
                return
                
            # Find the helm binary
            self.progress_update.emit("Locating Helm executable...")
            self.progress_percentage.emit(10)
            
            helm_exe = "helm.exe" if platform.system() == "Windows" else "helm"
            helm_path = shutil.which(helm_exe)
            
            if not helm_path:
                common_paths = self._get_common_helm_paths()
                for path in common_paths:
                    if os.path.isfile(path):
                        helm_path = path
                        break
            
            if not helm_path:
                self.installation_complete.emit(False, "Helm executable not found. Please install Helm to install charts.")
                return
                
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
                
            self.progress_update.emit("Checking for existing releases...")
            self.progress_percentage.emit(15)
            
            # Check if release already exists
            if self._check_release_exists(helm_path, release_name):
                return
                
            if self._is_cancelled:
                return
                
            # Get repository information
            repository_info = self.options.get("repository", {})
            if not repository_info:
                repository_info = {
                    "type": "name" if not self.repository or not self.repository.startswith(("http://", "https://")) else "url",
                    "value": self.repository
                }
                
            self.progress_update.emit("Setting up repository...")
            self.progress_percentage.emit(25)
            
            # Setup repository
            if not self._setup_repository(helm_path, repository_info):
                return
                
            if self._is_cancelled:
                return
                
            self.progress_update.emit("Creating namespace if needed...")
            self.progress_percentage.emit(35)
            
            # Create namespace if needed
            if create_namespace:
                self._create_namespace_if_needed(namespace)
                
            if self._is_cancelled:
                return
                
            self.progress_update.emit("Preparing installation command...")
            self.progress_percentage.emit(45)
            
            # Prepare installation command
            install_cmd = self._build_install_command(helm_path, release_name, repository_info, namespace, version, values_yaml, create_namespace)
            
            if self._is_cancelled:
                return
                
            self.progress_update.emit(f"Installing {self.chart_name}...")
            self.progress_percentage.emit(60)
            
            # Execute the command
            self._execute_install_command(install_cmd)
            
        except Exception as e:
            logging.error(f"Error in helm install thread: {e}")
            self.installation_complete.emit(False, f"Installation error: {str(e)}")
            
    def _get_common_helm_paths(self):
        """Get common Helm installation paths"""
        if platform.system() == "Windows":
            return [
                os.path.expanduser("~\\helm\\helm.exe"),
                "C:\\Program Files\\Helm\\helm.exe",
                "C:\\helm\\helm.exe",
                os.path.expanduser("~\\.windows-package-manager\\helm\\helm.exe"),
                os.path.expanduser("~\\AppData\\Local\\Programs\\Helm\\helm.exe")
            ]
        else:
            return [
                "/usr/local/bin/helm",
                "/usr/bin/helm",
                os.path.expanduser("~/bin/helm"),
                "/opt/homebrew/bin/helm"
            ]
            
    def _check_release_exists(self, helm_path, release_name):
        """Check if release already exists"""
        try:
            check_release = subprocess.run(
                [helm_path, "list", "--all-namespaces", "--filter", release_name, "--output", "json"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if check_release.returncode == 0:
                try:
                    releases = json.loads(check_release.stdout)
                    if releases:
                        exact_matches = [r for r in releases if r.get("name") == release_name]
                        if exact_matches:
                            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                            suggested_name = f"{release_name}-{suffix}"
                            self.installation_complete.emit(False, f"Release name '{release_name}' is already in use. Try using '{suggested_name}' instead.")
                            return True
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logging.warning(f"Error checking release existence: {e}")
            
        return False
        
    def _setup_repository(self, helm_path, repository_info):
        """Setup Helm repository"""
        try:
            repo_type = repository_info.get("type", "name")
            repo_value = repository_info.get("value", "")
            
            repository_urls = {
                "apache": "https://pulsar.apache.org/charts",
                "bitnami": "https://charts.bitnami.com/bitnami",
                "elastic": "https://helm.elastic.co",
                "prometheus": "https://prometheus-community.github.io/helm-charts",
                "jetstack": "https://charts.jetstack.io",
                "nginx": "https://helm.nginx.com/stable",
                "grafana": "https://grafana.github.io/helm-charts",
                "hashicorp": "https://helm.releases.hashicorp.com",
            }
            
            if repo_type == "name" and repo_value:
                # Check if repository exists
                repo_check = subprocess.run(
                    [helm_path, "repo", "list", "-o", "json"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                repo_exists = False
                if repo_check.returncode == 0:
                    try:
                        repos = json.loads(repo_check.stdout)
                        for repo in repos:
                            if repo.get("name") == repo_value:
                                repo_exists = True
                                break
                    except json.JSONDecodeError:
                        pass
                
                if not repo_exists:
                    self.progress_update.emit(f"Adding repository {repo_value}...")
                    
                    repo_url = repository_urls.get(repo_value)
                    if not repo_url:
                        # Try different URL patterns
                        url_patterns = [
                            f"https://{repo_value}.github.io/helm-charts",
                            f"https://charts.{repo_value}.io",
                            f"https://{repo_value}.github.io/charts",
                        ]
                        
                        for pattern in url_patterns:
                            try:
                                test_result = subprocess.run(
                                    [helm_path, "repo", "add", "--force-update", repo_value, pattern],
                                    capture_output=True,
                                    text=True,
                                    timeout=15
                                )
                                
                                if test_result.returncode == 0:
                                    repo_url = pattern
                                    repo_exists = True
                                    break
                            except:
                                continue
                    
                    if repo_url and not repo_exists:
                        add_result = subprocess.run(
                            [helm_path, "repo", "add", "--force-update", repo_value, repo_url],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if add_result.returncode != 0:
                            self.installation_complete.emit(False, f"Error adding repository: {add_result.stderr}")
                            return False
                    
                    # Update repos
                    self.progress_update.emit("Updating repositories...")
                    try:
                        subprocess.run(
                            [helm_path, "repo", "update"],
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                    except Exception as e:
                        logging.warning(f"Warning: Error updating repositories: {e}")
                        
            return True
            
        except Exception as e:
            self.installation_complete.emit(False, f"Error setting up repository: {str(e)}")
            return False
            
    def _create_namespace_if_needed(self, namespace):
        """Create namespace if it doesn't exist"""
        try:
            ns_check = subprocess.run(
                ["kubectl", "get", "namespace", namespace],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if ns_check.returncode != 0:
                subprocess.run(
                    ["kubectl", "create", "namespace", namespace],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
        except Exception as e:
            logging.warning(f"Warning: Namespace creation failed: {e}")
            
    def _build_install_command(self, helm_path, release_name, repository_info, namespace, version, values_yaml, create_namespace):
        """Build the Helm install command"""
        install_cmd = [helm_path, "install", release_name]
        
        if create_namespace:
            install_cmd.append("--create-namespace")
        
        # Add chart name with repository or URL
        repo_type = repository_info.get("type", "name")
        repo_value = repository_info.get("value", "")
        
        if repo_type == "name" and repo_value:
            install_cmd.append(f"{repo_value}/{self.chart_name}")
        elif repo_type == "url" and repo_value:
            install_cmd.append(self.chart_name)
            install_cmd.extend(["--repo", repo_value])
        else:
            install_cmd.append(self.chart_name)
        
        install_cmd.extend(["-n", namespace])
        
        if version:
            install_cmd.extend(["--version", version])
        
        # Add values if provided
        if values_yaml:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w") as temp:
                    temp.write(values_yaml)
                    values_file = temp.name
                install_cmd.extend(["-f", values_file])
                self._values_file = values_file  # Store for cleanup
            except Exception as e:
                self.installation_complete.emit(False, f"Error creating values file: {str(e)}")
                return None
                
        return install_cmd
        
    def _execute_install_command(self, install_cmd):
        """Execute the Helm install command with improved monitoring"""
        try:
            if self._is_cancelled:
                return
                
            logging.info(f"Executing: {' '.join(install_cmd)}")
            
            # Start the process
            process = subprocess.Popen(
                install_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.progress_percentage.emit(70)
            
            # Monitor process with better timeout handling
            check_interval = 1.0  # Check every second
            max_wait_time = 300  # 5 minutes maximum
            elapsed_time = 0
            last_progress_update = 70
            
            while process.poll() is None and elapsed_time < max_wait_time:
                if self._is_cancelled:
                    logging.info("Installation cancelled by user, terminating process")
                    try:
                        process.terminate()
                        # Give process 10 seconds to terminate gracefully
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        logging.warning("Process didn't terminate gracefully, killing it")
                        process.kill()
                        process.wait()
                    return
                
                # Update progress gradually
                if elapsed_time > 30 and last_progress_update < 80:
                    self.progress_percentage.emit(80)
                    last_progress_update = 80
                elif elapsed_time > 60 and last_progress_update < 85:
                    self.progress_percentage.emit(85)
                    last_progress_update = 85
                elif elapsed_time > 120 and last_progress_update < 90:
                    self.progress_percentage.emit(90)
                    last_progress_update = 90
                elif elapsed_time > 180 and last_progress_update < 95:
                    self.progress_percentage.emit(95)
                    last_progress_update = 95
                
                # Wait and update elapsed time
                self.msleep(int(check_interval * 1000))
                elapsed_time += check_interval
            
            # Handle timeout
            if elapsed_time >= max_wait_time and process.poll() is None:
                logging.error("Helm installation timed out")
                try:
                    process.terminate()
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                
                # Clean up values file if created
                if hasattr(self, '_values_file') and os.path.exists(self._values_file):
                    os.unlink(self._values_file)
                
                self.installation_complete.emit(False, "Installation timed out. The process took longer than expected.")
                return
            
            # Get the result
            stdout, stderr = process.communicate()
            
            # Clean up values file if created
            if hasattr(self, '_values_file') and os.path.exists(self._values_file):
                os.unlink(self._values_file)
            
            self.progress_percentage.emit(100)
            
            if process.returncode == 0:
                success_msg = f"Chart installed successfully as '{self.options.get('release_name')}' in namespace '{self.options.get('namespace', 'default')}'."
                
                # Add helpful information for common charts
                if self.chart_name == "nginx-ingress" or self.chart_name == "ingress-nginx":
                    success_msg += "\n\nTo access the NGINX Ingress Controller, you may need to set up port forwarding or a LoadBalancer service."
                elif self.chart_name == "prometheus":
                    success_msg += f"\n\nAccess Prometheus UI with: kubectl port-forward -n {self.options.get('namespace', 'default')} svc/{self.options.get('release_name')}-prometheus-server 9090:80"
                elif self.chart_name == "grafana":
                    success_msg += f"\n\nAccess Grafana with: kubectl port-forward -n {self.options.get('namespace', 'default')} svc/{self.options.get('release_name')}-grafana 3000:80"
                
                logging.info(f"Helm installation successful: {success_msg}")
                self.installation_complete.emit(True, success_msg)
            else:
                error_msg = stderr.strip() if stderr.strip() else stdout.strip()
                logging.error(f"Helm installation failed with return code {process.returncode}: {error_msg}")
                
                # Handle specific error cases
                if "already exists" in error_msg or "cannot re-use a name" in error_msg:
                    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                    suggested_name = f"{self.options.get('release_name')}-{suffix}"
                    self.installation_complete.emit(False, f"Release name '{self.options.get('release_name')}' is already in use. Try using '{suggested_name}' instead.")
                else:
                    self.installation_complete.emit(False, f"Error installing chart: {error_msg}")
                    
        except Exception as e:
            logging.error(f"Exception during Helm installation: {str(e)}")
            # Clean up values file if created
            if hasattr(self, '_values_file') and os.path.exists(self._values_file):
                os.unlink(self._values_file)
            self.installation_complete.emit(False, f"Error during installation: {str(e)}")


class ChartInstallDialog(QDialog):
    """Dialog for installing Helm charts with customization options"""
    
    def __init__(self, chart_name, repository=None, parent=None):
        super().__init__(parent)
        self.chart_name = chart_name
        self.repository = repository
        self.setWindowTitle(f"Install Chart: {chart_name}")
        self.setMinimumWidth(550)
        self.setStyleSheet(f"""
            background-color: {AppColors.BG_DARK};
            color: {AppColors.TEXT_LIGHT};
        """)
        self.setup_ui()
        
        # Generate default name and check if it exists
        self.check_existing_release(self.release_name_input.text())
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Form for installation settings
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        # Release name
        name_layout = QVBoxLayout()
        
        self.release_name_input = QLineEdit()
        self.release_name_input.setStyleSheet("""
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
        """)
        # Generate a default release name based on chart name with random suffix
        import re
        default_name = re.sub(r'[^a-z0-9-]', '', self.chart_name.lower())
        if not default_name:
            default_name = "release"
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        default_name = f"{default_name}-{suffix}"
        self.release_name_input.setText(default_name)
        self.release_name_input.textChanged.connect(self.check_existing_release)
        
        # Add warning label for existing release
        self.name_warning = QLabel("")
        self.name_warning.setStyleSheet("color: #ff4d4d; font-size: 12px; margin-top: 2px;")
        self.name_warning.setVisible(False)
        
        name_layout.addWidget(self.release_name_input)
        name_layout.addWidget(self.name_warning)
        
        form_layout.addRow("Release Name:", name_layout)
        
        # Repository selection
        repo_layout = QVBoxLayout()
        
        # Create radio buttons for repository selection
        self.repo_button_group = QButtonGroup(self)
        
        self.use_existing_repo = QRadioButton("Use existing repository")
        self.use_existing_repo.setStyleSheet("""
            QRadioButton {
                color: #ffffff;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        self.use_existing_repo.setChecked(True)
        
        self.use_custom_repo = QRadioButton("Use custom repository URL")
        self.use_custom_repo.setStyleSheet("""
            QRadioButton {
                color: #ffffff;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        
        self.repo_button_group.addButton(self.use_existing_repo)
        self.repo_button_group.addButton(self.use_custom_repo)
        
        repo_layout.addWidget(self.use_existing_repo)
        
        # Repository name
        self.repo_name_input = QLineEdit()
        self.repo_name_input.setStyleSheet("""
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
        """)
        if self.repository:
            self.repo_name_input.setText(self.repository)
        else:
            self.repo_name_input.setText("bitnami")
        
        repo_layout.addWidget(self.repo_name_input)
        repo_layout.addWidget(self.use_custom_repo)
        
        # Repository URL
        self.repo_url_input = QLineEdit()
        self.repo_url_input.setStyleSheet("""
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
            QLineEdit:disabled {
                background-color: #1e1e1e;
                color: #666666;
            }
        """)
        self.repo_url_input.setPlaceholderText("https://example.github.io/charts")
        self.repo_url_input.setEnabled(False)
        
        repo_layout.addWidget(self.repo_url_input)
        
        # Connect radio buttons to enable/disable repository fields
        self.use_existing_repo.toggled.connect(self.toggle_repo_inputs)
        self.use_custom_repo.toggled.connect(self.toggle_repo_inputs)
        
        form_layout.addRow("Repository:", repo_layout)
        
        # Namespace selector
        self.namespace_combo = QComboBox()
        self.namespace_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
            QComboBox:hover {
                border: 1px solid #555555;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                selection-background-color: #0078d7;
                selection-color: #ffffff;
            }
        """)
        self.load_namespaces()
        form_layout.addRow("Namespace:", self.namespace_combo)
        
        # Version selector (optional)
        self.version_combo = QComboBox()
        self.version_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
            QComboBox:hover {
                border: 1px solid #555555;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                selection-background-color: #0078d7;
                selection-color: #ffffff;
            }
        """)
        self.version_combo.addItem("Latest")
        form_layout.addRow("Version:", self.version_combo)
        
        # Values editor - simple for now, could be expanded to a full editor
        self.values_editor = QTextEdit()
        self.values_editor.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                font-family: Consolas, 'Courier New', monospace;
            }
            QTextEdit:focus {
                border: 1px solid #0078d7;
            }
        """)
        self.values_editor.setMinimumHeight(150)
        self.values_editor.setPlaceholderText("# Add custom values in YAML format\n# Example:\n# service:\n#   type: ClusterIP\n#   port: 80")
        form_layout.addRow("Custom Values:", self.values_editor)
        
        # Create namespace if it doesn't exist
        self.create_namespace_checkbox = QCheckBox("Create namespace if it doesn't exist")
        self.create_namespace_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        self.create_namespace_checkbox.setChecked(True)
        form_layout.addRow("", self.create_namespace_checkbox)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        
        self.install_button = QPushButton("Install")
        self.install_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #2d5a2f;
                color: #aaaaaa;
            }
        """)
        self.install_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.install_button)
        
        layout.addLayout(button_layout)
    
    def toggle_repo_inputs(self, checked):
        """Toggle repository input fields based on selected option"""
        if self.use_existing_repo.isChecked():
            self.repo_name_input.setEnabled(True)
            self.repo_url_input.setEnabled(False)
        else:
            self.repo_name_input.setEnabled(False)
            self.repo_url_input.setEnabled(True)
    
    def check_existing_release(self, release_name=None):
        """Check if a release name is already in use"""
        if not release_name:
            return
            
        try:
            # Check if release exists
            result = subprocess.run(
                ["helm", "list", "--all-namespaces", "--filter", release_name, "--output", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                # If command fails, assume it's safe to use
                self.name_warning.setVisible(False)
                self.install_button.setEnabled(True)
                return
                
            try:
                releases = json.loads(result.stdout)
                if releases and len(releases) > 0:
                    # Find if there's an exact match
                    exact_match = any(r.get("name") == release_name for r in releases)
                    
                    if exact_match:
                        # Name is already in use
                        self.name_warning.setText(f"Name '{release_name}' is already in use. Please choose another name.")
                        self.name_warning.setVisible(True)
                        self.install_button.setEnabled(False)
                    else:
                        # No exact match
                        self.name_warning.setVisible(False)
                        self.install_button.setEnabled(True)
                else:
                    # No releases found
                    self.name_warning.setVisible(False)
                    self.install_button.setEnabled(True)
            except json.JSONDecodeError:
                # Can't parse JSON, assume it's safe
                self.name_warning.setVisible(False)
                self.install_button.setEnabled(True)
                
        except Exception as e:
            # Error checking, play it safe
            logging.warning(f"Error checking release name: {e}")
            self.name_warning.setVisible(False)
            self.install_button.setEnabled(True)
    
    def load_namespaces(self):
        """Load Kubernetes namespaces for the dropdown"""
        try:
            import subprocess
            import json
            
            # Get namespaces using kubectl
            result = subprocess.run(
                ["kubectl", "get", "namespaces", "-o", "json"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            
            namespaces = []
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for item in data.get("items", []):
                    name = item.get("metadata", {}).get("name")
                    if name:
                        namespaces.append(name)
                
                # Sort and add to combo box
                namespaces.sort()
                self.namespace_combo.addItems(namespaces)
                
                # Pre-select 'default' namespace if it exists
                default_index = self.namespace_combo.findText("default")
                if default_index >= 0:
                    self.namespace_combo.setCurrentIndex(default_index)
            else:
                # Fall back to default namespace only
                self.namespace_combo.addItem("default")
                
        except Exception as e:
            logging.warning(f"Error loading namespaces: {e}")
            self.namespace_combo.addItem("default")
    
    def get_values(self):
        """Get entered values from the dialog"""
        repository_info = {}
        
        if self.use_existing_repo.isChecked():
            repository_info["type"] = "name"
            repository_info["value"] = self.repo_name_input.text().strip()
        else:
            repository_info["type"] = "url"
            repository_info["value"] = self.repo_url_input.text().strip()
        
        return {
            "release_name": self.release_name_input.text().strip(),
            "namespace": self.namespace_combo.currentText(),
            "version": None if self.version_combo.currentText() == "Latest" else self.version_combo.currentText(),
            "values": self.values_editor.toPlainText().strip(),
            "create_namespace": self.create_namespace_checkbox.isChecked(),
            "repository": repository_info
        }


# def install_helm_chart(chart_name, repository, options, parent=None):
#     """
#     Install a Helm chart with the specified options using proper threading
    
#     Args:
#         chart_name: Name of the chart to install
#         repository: Repository information (can be URL or repo name)
#         options: Dictionary with installation options (release_name, namespace, version, values)
#         parent: Parent widget for displaying progress dialog
    
#     Returns:
#         Tuple of (success, message)
#     """
    
#     # Create and show progress dialog with longer timeout
#     progress = QProgressDialog("Preparing installation...", "Cancel", 0, 100, parent)
#     progress.setWindowTitle("Installing Chart")
#     progress.setWindowModality(Qt.WindowModality.WindowModal)
#     progress.setMinimumDuration(0)
#     progress.setValue(0)
#     progress.setAutoClose(False)
#     progress.setAutoReset(False)  # Prevent automatic reset
#     progress.show()
#     QApplication.processEvents()
    
#     # Create and start the installation thread
#     install_thread = HelmInstallThread(chart_name, repository, options)
    
#     # Track the result and completion state
#     result = {"success": False, "message": "Installation cancelled"}
#     installation_completed = {"completed": False}
#     user_cancelled = {"cancelled": False}
#     dialog_closed_programmatically = {"closed": False}
    
#     def on_progress_update(message):
#         try:
#             if not installation_completed["completed"] and not user_cancelled["cancelled"]:
#                 progress.setLabelText(message)
#                 QApplication.processEvents()
#                 logging.info(f"Helm installation progress: {message}")
#         except RuntimeError:
#             # Dialog might be deleted, ignore
#             pass
    
#     def on_progress_percentage(percentage):
#         try:
#             if not installation_completed["completed"] and not user_cancelled["cancelled"]:
#                 progress.setValue(percentage)
#                 QApplication.processEvents()
#         except RuntimeError:
#             # Dialog might be deleted, ignore
#             pass
    
#     def on_installation_complete(success, message):
#         installation_completed["completed"] = True
#         result["success"] = success
#         result["message"] = message
#         logging.info(f"Helm installation completed: success={success}, message={message}")
        
#         try:
#             if progress and not progress.wasCanceled() and not user_cancelled["cancelled"]:
#                 progress.setValue(100)
#                 progress.setLabelText("Installation completed successfully!" if success else "Installation failed!")
#                 QApplication.processEvents()
#         except RuntimeError:
#             pass
        
#         # Disconnect the cancelled signal before closing to prevent spurious cancellation
#         try:
#             progress.canceled.disconnect()
#         except (TypeError, RuntimeError):
#             pass
        
#         # Mark as programmatically closed and close after a delay
#         dialog_closed_programmatically["closed"] = True
#         QTimer.singleShot(1500, lambda: close_progress_dialog())
        
#         # Ensure thread stops
#         if install_thread.isRunning():
#             install_thread.quit()
#             install_thread.wait(2000)
    
#     def close_progress_dialog():
#         """Safely close the progress dialog"""
#         try:
#             if progress and not progress.wasCanceled():
#                 progress.close()
#         except RuntimeError:
#             pass
    
#     def on_progress_cancelled():
#         # Only process cancellation if installation hasn't completed and wasn't closed programmatically
#         if (not installation_completed["completed"] and 
#             not dialog_closed_programmatically["closed"] and
#             not user_cancelled["cancelled"]):
            
#             user_cancelled["cancelled"] = True
#             logging.info("User cancelled Helm installation")
#             install_thread.cancel()
#             result["success"] = False
#             result["message"] = "Installation cancelled by user"
            
#             # Give thread time to cleanup gracefully
#             if install_thread.isRunning():
#                 install_thread.quit()
#                 install_thread.wait(3000)
#         else:
#             # This is a spurious cancellation signal, ignore it
#             if installation_completed["completed"]:
#                 logging.info("Ignoring spurious cancellation signal - installation already completed")
    
#     # Connect signals
#     install_thread.progress_update.connect(on_progress_update)
#     install_thread.progress_percentage.connect(on_progress_percentage)
#     install_thread.installation_complete.connect(on_installation_complete)
#     progress.canceled.connect(on_progress_cancelled)
    
#     # Start the thread
#     install_thread.start()
#     logging.info(f"Started Helm installation thread for {chart_name}")
    
#     # Process events while waiting for completion - but don't auto-cancel on dialog close
#     max_wait_time = 300000  # 5 minutes maximum wait time
#     wait_interval = 100  # Check every 100ms
#     elapsed_time = 0
    
#     while (install_thread.isRunning() and 
#            not installation_completed["completed"] and 
#            elapsed_time < max_wait_time):
        
#         QApplication.processEvents()
#         install_thread.msleep(wait_interval)
#         elapsed_time += wait_interval
        
#         # Only check for user cancellation if not completed and not programmatically closed
#         if (progress.wasCanceled() and 
#             not installation_completed["completed"] and 
#             not dialog_closed_programmatically["closed"] and
#             not user_cancelled["cancelled"]):
#             user_cancelled["cancelled"] = True
#             install_thread.cancel()
#             break
    
#     # Handle timeout case
#     if elapsed_time >= max_wait_time and install_thread.isRunning():
#         logging.warning("Helm installation timed out")
#         install_thread.cancel()
#         install_thread.wait(5000)
#         if install_thread.isRunning():
#             install_thread.terminate()
#         result["success"] = False
#         result["message"] = "Installation timed out after 5 minutes"
    
#     # Wait for thread to finish gracefully
#     if install_thread.isRunning():
#         install_thread.wait(5000)  # Wait up to 5 seconds
#         if install_thread.isRunning():
#             logging.warning("Force terminating Helm installation thread")
#             install_thread.terminate()
    
#     # Ensure progress dialog is closed
#     try:
#         if progress and not dialog_closed_programmatically["closed"]:
#             # Disconnect cancelled signal before closing
#             try:
#                 progress.canceled.disconnect()
#             except (TypeError, RuntimeError):
#                 pass
#             progress.close()
#     except RuntimeError:
#         pass
    
#     logging.info(f"Final installation result: success={result['success']}, message={result['message']}")
#     return result["success"], result["message"]

def install_helm_chart(chart_name, repository, options, parent=None):
    """
    Install a Helm chart with the specified options using a robust, event-driven approach.

    Args:
        chart_name: Name of the chart to install
        repository: Repository information (can be URL or repo name)
        options: Dictionary with installation options (release_name, namespace, version, values)
        parent: Parent widget for displaying progress dialog

    Returns:
        Tuple of (success, message)
    """
    progress = QProgressDialog("Preparing installation...", "Cancel", 0, 100, parent)
    progress.setWindowTitle("Installing Chart")
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setMinimumDuration(0)
    progress.setValue(0)
    progress.setAutoClose(False)
    progress.setAutoReset(False)
    progress.show()

    install_thread = HelmInstallThread(chart_name, repository, options)
    
    # Use a dictionary to hold the result, allowing it to be modified by nested functions
    result = {"success": False, "message": "Installation was cancelled or failed."}
    
    # The QEventLoop will block execution of this function while still processing signals
    event_loop = QEventLoop()
    
    # A timer to prevent the installation from running indefinitely
    timeout_timer = QTimer()
    timeout_timer.setSingleShot(True)
    timeout_timer.setInterval(300000)  # 5-minute timeout

    def on_progress_update(message):
        if progress.isVisible():
            progress.setLabelText(message)

    def on_progress_percentage(percentage):
        if progress.isVisible():
            progress.setValue(percentage)

    def on_installation_complete(success, message):
        if not event_loop.isRunning(): return
        timeout_timer.stop()  # Stop the timeout timer on completion
        result["success"] = success
        result["message"] = message
        logging.info(f"Helm installation completed: success={success}, message={message}")
        if progress.isVisible():
            progress.setValue(100)
            progress.setLabelText("Installation finished.")
            # Disconnect the canceled signal to prevent it from firing when we programmatically close the dialog
            try:
                progress.canceled.disconnect(on_progress_cancelled)
            except (TypeError, RuntimeError):
                pass
            QTimer.singleShot(1500, progress.close) # Close the dialog after a short delay
        event_loop.quit()  # Unblock the install_helm_chart function

    def on_progress_cancelled():
        if not event_loop.isRunning(): return
        timeout_timer.stop()
        logging.info("User cancelled Helm installation")
        install_thread.cancel()  # Signal the thread to stop
        result["success"] = False
        result["message"] = "Installation cancelled by user."
        event_loop.quit()

    def on_timeout():
        if not event_loop.isRunning(): return
        logging.error("Helm installation timed out.")
        install_thread.cancel()
        result["success"] = False
        result["message"] = "Installation timed out after 5 minutes."
        if progress.isVisible():
            progress.close()
        event_loop.quit()

    # Connect all signals
    install_thread.progress_update.connect(on_progress_update)
    install_thread.progress_percentage.connect(on_progress_percentage)
    install_thread.installation_complete.connect(on_installation_complete)
    progress.canceled.connect(on_progress_cancelled)
    timeout_timer.timeout.connect(on_timeout)

    # Start the operation
    install_thread.start()
    timeout_timer.start()
    
    # This call blocks until event_loop.quit() is called
    event_loop.exec()

    # ---- Execution continues here after completion, cancellation, or timeout ----

    # Final cleanup
    timeout_timer.stop()
    if install_thread.isRunning():
        install_thread.wait(2000) # Give the thread a moment to finish cleanly

    logging.info(f"Final installation result: success={result['success']}, message={result['message']}")
    return result["success"], result["message"]