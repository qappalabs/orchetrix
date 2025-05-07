"""
Utilities for working with Helm charts
Provides dialog and functionality for installing and managing Helm charts
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
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QTextEdit, QHBoxLayout, QPushButton, QProgressDialog, QMessageBox,
    QCheckBox, QLabel, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QTimer
from UI.Styles import AppColors

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
                text=True
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
            print(f"Error checking release name: {e}")
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
                check=True
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
            print(f"Error loading namespaces: {e}")
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


def install_helm_chart(chart_name, repository, options, parent=None):
    """
    Install a Helm chart with the specified options
    
    Args:
        chart_name: Name of the chart to install
        repository: Repository information (can be URL or repo name)
        options: Dictionary with installation options (release_name, namespace, version, values)
        parent: Parent widget for displaying progress dialog
    
    Returns:
        Tuple of (success, message)
    """
    try:
        import subprocess
        import tempfile
        import os
        import platform
        import shutil
        import json
        
        # Find the helm binary
        helm_exe = "helm.exe" if platform.system() == "Windows" else "helm"
        helm_path = shutil.which(helm_exe)
        
        # Check common installation locations if not found in PATH
        if not helm_path:
            common_paths = []
            if platform.system() == "Windows":
                common_paths = [
                    os.path.expanduser("~\\helm\\helm.exe"),
                    "C:\\Program Files\\Helm\\helm.exe",
                    "C:\\helm\\helm.exe",
                    os.path.expanduser("~\\.windows-package-manager\\helm\\helm.exe"),
                    os.path.expanduser("~\\AppData\\Local\\Programs\\Helm\\helm.exe")
                ]
            else:
                common_paths = [
                    "/usr/local/bin/helm",
                    "/usr/bin/helm",
                    os.path.expanduser("~/bin/helm"),
                    "/opt/homebrew/bin/helm"  # Common on macOS with Homebrew
                ]
                
            for path in common_paths:
                if os.path.isfile(path):
                    helm_path = path
                    break
        
        if not helm_path:
            return False, "Helm executable not found. Please install Helm to install charts."
        
        # Get options
        release_name = options.get("release_name", "").strip()
        namespace = options.get("namespace", "default").strip()
        version = options.get("version")
        values_yaml = options.get("values", "").strip()
        create_namespace = options.get("create_namespace", True)
        
        # Get repository information (either from options or from legacy parameter)
        repository_info = options.get("repository", {})
        if not repository_info:
            # Legacy mode - convert string repository to dict
            repository_info = {
                "type": "name" if not repository or not repository.startswith(("http://", "https://")) else "url",
                "value": repository
            }
        
        # Validate inputs
        if not release_name:
            return False, "Release name is required."
        
        # Check if release already exists
        try:
            check_release = subprocess.run(
                [helm_path, "list", "--all-namespaces", "--filter", release_name, "--output", "json"],
                capture_output=True,
                text=True
            )
            
            if check_release.returncode == 0:
                try:
                    releases = json.loads(check_release.stdout)
                    if releases:
                        exact_matches = [r for r in releases if r.get("name") == release_name]
                        if exact_matches:
                            # Generate a suggested name with random suffix
                            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                            suggested_name = f"{release_name}-{suffix}"
                            return False, f"Release name '{release_name}' is already in use. Try using '{suggested_name}' instead."
                except json.JSONDecodeError:
                    pass  # Ignore JSON errors, continue with installation
        except Exception as e:
            print(f"Error checking release existence: {e}")
            # Continue even if check fails
        
        # Show progress dialog
        progress = None
        if parent:
            progress = QProgressDialog("Preparing to install chart...", "Cancel", 0, 0, parent)
            progress.setWindowTitle("Installing Chart")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.show()
        
        # Get repository type and value
        repo_type = repository_info.get("type", "name")
        repo_value = repository_info.get("value", "")
        
        # Update known repositories mapping with more accurate URLs
        repository_urls = {
            "apache": "https://pulsar.apache.org/charts",
            "bitnami": "https://charts.bitnami.com/bitnami",
            "elastic": "https://helm.elastic.co",
            "prometheus": "https://prometheus-community.github.io/helm-charts",
            "jetstack": "https://charts.jetstack.io",
            "nginx": "https://helm.nginx.com/stable",
            "grafana": "https://grafana.github.io/helm-charts",
            "hashicorp": "https://helm.releases.hashicorp.com",
            "kong": "https://charts.konghq.com",
            "jenkins": "https://charts.jenkins.io",
            "startx": "https://startxfr.github.io/helm-repository/packages/",
            "kafka": "https://kafka.github.io/helm-charts",
            "cass-operator": "https://k8ssandra.github.io/cass-operator/",
            "strimzi": "https://strimzi.io/charts/",
            "pulsar": "https://pulsar.apache.org/charts"
        }
        
        # Check if repository needs to be added
        if repo_type == "name" and repo_value:
            # Check if repository exists
            repo_check = subprocess.run(
                [helm_path, "repo", "list", "-o", "json"],
                capture_output=True,
                text=True
            )
            
            # Parse repo list
            repo_exists = False
            if repo_check.returncode == 0:
                try:
                    repos = json.loads(repo_check.stdout)
                    for repo in repos:
                        if repo.get("name") == repo_value:
                            repo_exists = True
                            break
                except json.JSONDecodeError:
                    # Empty repo list returns invalid JSON sometimes
                    pass
            
            # Add repository if needed
            if not repo_exists:
                if progress:
                    progress.setLabelText(f"Adding repository {repo_value}...")
                
                # Get URL from known repositories
                repo_url = repository_urls.get(repo_value)
                
                # If URL is unknown, try to guess based on common patterns
                if not repo_url:
                    if repo_value in ["stable", "incubator"]:
                        repo_url = f"https://kubernetes-charts.storage.googleapis.com/{repo_value}"
                    else:
                        # Try different URL patterns
                        url_patterns = [
                            f"https://{repo_value}.github.io/helm-charts",
                            f"https://charts.{repo_value}.io",
                            f"https://{repo_value}.github.io/charts",
                            f"https://{repo_value}.dev/charts",
                            f"https://{repo_value}.github.io/{repo_value}"
                        ]
                        
                        for pattern in url_patterns:
                            try:
                                # Try to add the repository with this URL pattern
                                test_url_result = subprocess.run(
                                    [helm_path, "repo", "add", "--force-update", repo_value, pattern],
                                    capture_output=True,
                                    text=True,
                                    timeout=10
                                )
                                
                                if test_url_result.returncode == 0:
                                    repo_url = pattern
                                    repo_exists = True
                                    break
                            except:
                                continue
                
                if repo_url and not repo_exists:
                    try:
                        add_result = subprocess.run(
                            [helm_path, "repo", "add", "--force-update", repo_value, repo_url],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if add_result.returncode != 0:
                            if progress:
                                progress.close()
                            return False, f"Error adding repository: {add_result.stderr}"
                    except Exception as e:
                        if progress:
                            progress.close()
                        return False, f"Error adding repository: {str(e)}"
                
                # Update repos
                try:
                    if progress:
                        progress.setLabelText("Updating repositories...")
                    
                    update_result = subprocess.run(
                        [helm_path, "repo", "update"],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                except Exception as e:
                    print(f"Warning: Error updating repositories: {e}")
                    # Continue despite error
        
        if progress:
            progress.setLabelText("Installing chart...")
        
        # Create namespace if it doesn't exist and option is checked
        if create_namespace:
            try:
                ns_check = subprocess.run(
                    ["kubectl", "get", "namespace", namespace],
                    capture_output=True,
                    text=True
                )
                
                if ns_check.returncode != 0:
                    # Create namespace
                    if progress:
                        progress.setLabelText(f"Creating namespace {namespace}...")
                    
                    create_result = subprocess.run(
                        ["kubectl", "create", "namespace", namespace],
                        capture_output=True,
                        text=True
                    )
                    if create_result.returncode != 0:
                        print(f"Warning: Failed to create namespace: {create_result.stderr}")
            except Exception as e:
                print(f"Warning: Namespace check/creation failed: {e}")
                # Continue with installation - helm will handle namespace issues
        
        # Prepare installation command
        install_cmd = [helm_path, "install", release_name]
        
        # Add create-namespace flag if option is checked
        if create_namespace:
            install_cmd.append("--create-namespace")
        
        # Add chart name with repository or URL
        if repo_type == "name" and repo_value:
            install_cmd.append(f"{repo_value}/{chart_name}")
        elif repo_type == "url" and repo_value:
            install_cmd.append(chart_name)
            install_cmd.extend(["--repo", repo_value])
        else:
            install_cmd.append(chart_name)
        
        # Add namespace
        install_cmd.extend(["-n", namespace])
        
        # Add version if specified
        if version:
            install_cmd.extend(["--version", version])
        
        # Add values if provided
        values_file = None
        if values_yaml:
            try:
                # Create a temporary file for values
                with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w") as temp:
                    temp.write(values_yaml)
                    values_file = temp.name
                
                install_cmd.extend(["-f", values_file])
            except Exception as e:
                if progress:
                    progress.close()
                return False, f"Error creating values file: {str(e)}"
        
        # Execute the command with increased timeout and handle specific errors
        try:
            # Print the command for debugging
            print(f"Executing: {' '.join(install_cmd)}")
            
            result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                check=False,  # Don't raise exception so we can handle errors ourselves
                timeout=60  # Increased timeout for slow networks/clusters
            )
            
            # Clean up temporary file if created
            if values_file and os.path.exists(values_file):
                os.unlink(values_file)
            
            # Handle different error cases
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                
                # Handle specific error cases
                if "already exists" in error_msg or "cannot re-use a name" in error_msg:
                    # Generate a suggested name with random suffix
                    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                    suggested_name = f"{release_name}-{suffix}"
                    
                    if progress:
                        progress.close()
                    return False, f"Release name '{release_name}' is already in use. Try using '{suggested_name}' instead."
                
                elif "not found in" in error_msg or "is not a chart repository" in error_msg:
                    # Repository issues
                    if progress:
                        progress.close()
                        
                    # Suggest alternative repositories based on chart name
                    suggestions = []
                    if chart_name == "pulsar":
                        suggestions.append(("apache", "https://pulsar.apache.org/charts"))
                    elif chart_name == "kafka" or "kafka" in chart_name:
                        suggestions.append(("strimzi", "https://strimzi.io/charts/"))
                    elif chart_name == "airflow":
                        suggestions.append(("apache", "https://airflow.apache.org/charts/"))
                    
                    suggestion_msg = ""
                    if suggestions:
                        suggestion_msg = "\n\nTry one of these repositories instead:\n"
                        for name, url in suggestions:
                            suggestion_msg += f"- {name} ({url})\n"
                            
                    return False, f"Chart repository error: {error_msg}{suggestion_msg}"
                
                # Generic error case
                if progress:
                    progress.close()
                return False, f"Error installing chart: {error_msg}"
            
            # Success case
            if progress:
                progress.close()
            
            # Add instructions for accessing the resource
            success_msg = f"Chart installed successfully as '{release_name}' in namespace '{namespace}'."
            
            # Add additional help for common charts
            if chart_name == "nginx-ingress" or chart_name == "ingress-nginx":
                success_msg += "\n\nTo access the NGINX Ingress Controller, you may need to set up port forwarding or a LoadBalancer service."
            elif chart_name == "prometheus":
                success_msg += f"\n\nAccess Prometheus UI with: kubectl port-forward -n {namespace} svc/{release_name}-prometheus-server 9090:80"
            elif chart_name == "grafana":
                success_msg += f"\n\nAccess Grafana with: kubectl port-forward -n {namespace} svc/{release_name}-grafana 3000:80"
            
            return True, success_msg
            
        except subprocess.TimeoutExpired:
            # Clean up temporary file if created
            if values_file and os.path.exists(values_file):
                os.unlink(values_file)
                
            # Update UI
            if progress:
                progress.close()
                
            return False, "Installation timed out. The chart might still be installing in the background."
            
    except Exception as e:
        # Update UI
        if progress:
            progress.close()
            
        return False, f"Error during installation: {str(e)}"