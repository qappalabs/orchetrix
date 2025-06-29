"""
Enhanced utilities for working with Helm charts using the improved pure Python client.
Includes better error handling, validation, and integration with the new helm_client.
"""

import os
import time
import yaml
import logging
import random
import string
import shutil
import traceback
import re
from typing import Dict, Any, Optional
from types import MethodType
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QTextEdit, QHBoxLayout, QPushButton, QProgressDialog, QMessageBox,
    QCheckBox, QLabel, QListWidget, QListWidgetItem, QDialogButtonBox,
    QTabWidget, QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView, QWidget
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QCoreApplication
from PyQt6.QtGui import QFont
from UI.Styles import AppColors
from utils.kubernetes_client import get_kubernetes_client
from utils.helm_client import HelmClient

# --- Helper functions ---

def get_helm_client_instance():
    """Initializes and returns a HelmClient instance for non-CLI operations."""
    kube_client = get_kubernetes_client()
    if not kube_client or not kube_client.v1:
        raise ConnectionError("Kubernetes client is not available. Please connect to a cluster.")
    return HelmClient(kube_client.v1)

# --- Repository Management (uses Python client) ---

def get_helm_repos():
    """Gets a list of configured Helm repositories."""
    try:
        helm_client = get_helm_client_instance()
        return helm_client.list_repositories()
    except Exception as e:
        logging.error(f"Failed to get Helm repos using Python client: {e}")
        return []

def add_helm_repo(name, url, username=None, password=None):
    """Adds a new Helm repository."""
    helm_client = get_helm_client_instance()
    helm_client.add_repository(name, url, username, password)
    helm_client.repo_manager.update_repository_index(name)

def remove_helm_repo(name):
    """Removes a Helm repository."""
    helm_client = get_helm_client_instance()
    helm_client.remove_repository(name)

def update_helm_repos():
    """Updates all configured Helm repositories."""
    helm_client = get_helm_client_instance()
    helm_client.update_repositories()


class HelmInstallThread(QThread):
    """Enhanced thread for installing Helm charts with better validation and error handling."""
    progress_update = pyqtSignal(str)
    progress_percentage = pyqtSignal(int)
    installation_complete = pyqtSignal(bool, str)

    def __init__(self, chart: dict, options: dict):
        super().__init__()
        self.chart = chart
        self.options = options
        self._is_cancelled = False
        self.helm_client = None
        self.downloaded_chart_path = None

    def run(self):
        try:
            self.progress_update.emit("Initializing Helm client...")
            self.progress_percentage.emit(5)
            if self._is_cancelled: 
                return

            self.helm_client = get_helm_client_instance()

            repo_name = self.chart.get('repository')
            chart_name = self.chart.get('name')
            version = self.options.get("version") or "latest"

            if not repo_name or not chart_name:
                raise ValueError("Chart repository and name are required.")

            self.progress_update.emit(f"Downloading chart: {repo_name}/{chart_name}@{version}...")
            self.progress_percentage.emit(15)

            # Enhanced download with comprehensive fallback strategies
            self.downloaded_chart_path = self._download_chart_enhanced(repo_name, chart_name, version)

            if self._is_cancelled:
                self._cleanup()
                return

            if not self.downloaded_chart_path:
                self._handle_download_failure(repo_name, chart_name, version)
                return

            self.progress_update.emit("Chart downloaded successfully. Validating chart...")
            self.progress_percentage.emit(40)

            # Find and validate the chart directory
            chart_dir = self._find_and_validate_chart_directory(self.downloaded_chart_path, chart_name)
            if not chart_dir:
                raise FileNotFoundError(f"Valid chart directory not found within {self.downloaded_chart_path}")

            self.progress_update.emit("Validating installation options...")
            self.progress_percentage.emit(50)

            # Validate installation options
            validation_result = self._validate_installation_options()
            if not validation_result['valid']:
                raise ValueError(validation_result['error'])

            release_name = self.options.get("release_name")
            namespace = self.options.get("namespace", "default")
            values_dict = self.options.get("values", {})
            create_namespace = self.options.get("create_namespace", False)

            self.progress_update.emit(f"Installing '{release_name}' to namespace '{namespace}'...")
            self.progress_percentage.emit(70)

            # Perform the installation
            success = self.helm_client.install_release(
                release_name=release_name,
                chart_path=chart_dir,
                namespace=namespace,
                values=values_dict,
                create_namespace=create_namespace
            )

            if self._is_cancelled:
                # Clean up installed resources if cancelled
                try:
                    self.progress_update.emit("Cleaning up cancelled installation...")
                    self.helm_client.delete_release(release_name, namespace)
                except:
                    pass
                self._cleanup()
                return

            if success:
                self.progress_percentage.emit(100)
                success_message = self._generate_success_message(release_name, namespace)
                self.installation_complete.emit(True, success_message)
            else:
                raise Exception(f"Installation of release '{release_name}' failed. Check application logs for details.")

        except Exception as e:
            logging.error(f"Helm installation failed: {traceback.format_exc()}")
            error_message = self._format_error_message(str(e))
            self.installation_complete.emit(False, error_message)
        finally:
            self._cleanup()

    def _download_chart_enhanced(self, repo_name: str, chart_name: str, version: str) -> Optional[str]:
        """Enhanced chart download with comprehensive fallback strategies and better progress reporting"""
        strategies = [
            ('primary_repository', lambda: self._try_primary_repository_download(repo_name, chart_name, version)),
            ('repository_update', lambda: self._try_repository_update_download(repo_name, chart_name, version)),
            ('common_repositories', lambda: self._try_common_repositories_download(chart_name, version)),
            ('artifact_hub_discovery', lambda: self._try_artifact_hub_discovery_download(chart_name, version))
        ]
        
        for strategy_name, strategy_func in strategies:
            if self._is_cancelled:
                return None
                
            try:
                self.progress_update.emit(f"Trying {strategy_name.replace('_', ' ')} download...")
                result = strategy_func()
                if result and os.path.exists(result):
                    logging.info(f"Successfully downloaded chart using {strategy_name} strategy")
                    return result
            except Exception as e:
                logging.warning(f"Strategy {strategy_name} failed: {e}")
                continue
                
        return None

    def _try_primary_repository_download(self, repo_name: str, chart_name: str, version: str) -> Optional[str]:
        """Try downloading using the primary repository"""
        try:
            return self.helm_client.repo_manager.download_chart(repo_name, chart_name, version)
        except Exception as e:
            logging.debug(f"Primary repository download failed: {e}")
            return None

    def _try_repository_update_download(self, repo_name: str, chart_name: str, version: str) -> Optional[str]:
        """Try updating repository index and downloading"""
        try:
            self.progress_update.emit(f"Updating repository {repo_name} index...")
            update_success = self.helm_client.repo_manager.update_repository_index(repo_name)
            
            if update_success:
                return self.helm_client.repo_manager.download_chart(repo_name, chart_name, version)
            return None
        except Exception as e:
            logging.debug(f"Repository update download failed: {e}")
            return None

    def _try_common_repositories_download(self, chart_name: str, version: str) -> Optional[str]:
        """Try downloading from common well-known repositories"""
        common_repos = {
            'bitnami': 'https://charts.bitnami.com/bitnami',
            'stable': 'https://charts.helm.sh/stable',
            'ingress-nginx': 'https://kubernetes.github.io/ingress-nginx',
            'prometheus': 'https://prometheus-community.github.io/helm-charts',
            'grafana': 'https://grafana.github.io/helm-charts',
            'jetstack': 'https://charts.jetstack.io',
            'elastic': 'https://helm.elastic.co',
            'hashicorp': 'https://helm.releases.hashicorp.com'
        }
        
        for repo_name, repo_url in common_repos.items():
            if self._is_cancelled:
                return None
                
            try:
                self.progress_update.emit(f"Trying common repository {repo_name}...")
                
                # Add temporary repository
                temp_repo_name = f"temp-install-{repo_name}-{int(time.time())}"
                self.helm_client.repo_manager.add_repository(temp_repo_name, repo_url)
                
                # Update index
                self.helm_client.repo_manager.update_repository_index(temp_repo_name)
                
                # Try download
                result = self.helm_client.repo_manager.download_chart(temp_repo_name, chart_name, version)
                
                # Clean up temporary repository
                try:
                    self.helm_client.repo_manager.remove_repository(temp_repo_name)
                except:
                    pass
                
                if result and os.path.exists(result):
                    logging.info(f"Downloaded chart from common repository {repo_name}")
                    return result
                    
            except Exception as e:
                logging.debug(f"Common repository {repo_name} download failed: {e}")
                # Clean up temp repo on error
                try:
                    self.helm_client.repo_manager.remove_repository(f"temp-install-{repo_name}-{int(time.time())}")
                except:
                    pass
                continue
                
        return None

    def _try_artifact_hub_discovery_download(self, chart_name: str, version: str) -> Optional[str]:
        """Try discovering chart repository via Artifact Hub and downloading"""
        try:
            import requests
            import json
            
            self.progress_update.emit("Discovering chart via Artifact Hub...")
            
            # Search for the chart on Artifact Hub
            search_url = "https://artifacthub.io/api/v1/packages/search"
            params = {
                'kind': '0',  # Helm charts
                'ts_query_web': chart_name,
                'limit': 20
            }
            
            response = requests.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            packages = data.get('packages', [])
            
            # Find exact match with highest relevance
            target_package = None
            for package in packages:
                if package.get('name') == chart_name:
                    target_package = package
                    break
            
            if not target_package:
                return None
                
            # Get repository information
            repo_info = target_package.get('repository', {})
            repo_url = repo_info.get('url')
            repo_name = repo_info.get('name')
            
            if not repo_url:
                return None
                
            # Try to download from the discovered repository
            temp_repo_name = f"temp-discovery-{int(time.time())}"
            self.helm_client.repo_manager.add_repository(temp_repo_name, repo_url)
            self.helm_client.repo_manager.update_repository_index(temp_repo_name)
            
            result = self.helm_client.repo_manager.download_chart(temp_repo_name, chart_name, version)
            
            # Clean up
            try:
                self.helm_client.repo_manager.remove_repository(temp_repo_name)
            except:
                pass
                
            if result and os.path.exists(result):
                logging.info(f"Downloaded chart via Artifact Hub discovery from {repo_name}")
                return result
                
            return None
            
        except Exception as e:
            logging.debug(f"Artifact Hub discovery download failed: {e}")
            return None

    def _find_and_validate_chart_directory(self, downloaded_path: str, chart_name: str) -> Optional[str]:
        """Find and validate the chart directory within the downloaded path"""
        try:
            # Try expected chart directory first
            chart_dir = os.path.join(downloaded_path, chart_name)
            if self._validate_chart_directory(chart_dir):
                return chart_dir
                
            # Look for any subdirectory with valid Chart.yaml
            for item in os.listdir(downloaded_path):
                item_path = os.path.join(downloaded_path, item)
                if os.path.isdir(item_path) and self._validate_chart_directory(item_path):
                    logging.info(f"Found valid chart directory: {item_path}")
                    return item_path
                        
            # Last resort: look recursively
            for root, dirs, files in os.walk(downloaded_path):
                if self._validate_chart_directory(root):
                    logging.info(f"Found valid chart directory recursively: {root}")
                    return root
                    
            return None
            
        except Exception as e:
            logging.error(f"Error finding chart directory: {e}")
            return None

    def _validate_chart_directory(self, chart_dir: str) -> bool:
        """Validate that a directory contains a valid Helm chart"""
        try:
            chart_yaml_path = os.path.join(chart_dir, "Chart.yaml")
            if not os.path.exists(chart_yaml_path):
                return False
                
            # Try to parse Chart.yaml
            with open(chart_yaml_path, 'r', encoding='utf-8') as f:
                chart_metadata = yaml.safe_load(f)
                
            # Basic validation
            if not chart_metadata:
                return False
                
            required_fields = ['name', 'version']
            for field in required_fields:
                if field not in chart_metadata:
                    logging.warning(f"Chart.yaml missing required field: {field}")
                    return False
                    
            # Check for templates directory (optional but recommended)
            templates_dir = os.path.join(chart_dir, "templates")
            if not os.path.exists(templates_dir):
                logging.warning(f"Chart directory {chart_dir} has no templates directory")
                # Still valid, just warning
                
            return True
            
        except Exception as e:
            logging.error(f"Error validating chart directory {chart_dir}: {e}")
            return False

    def _validate_installation_options(self) -> Dict[str, Any]:
        """Validate installation options"""
        try:
            release_name = self.options.get("release_name")
            if not release_name:
                return {'valid': False, 'error': 'Release name is required'}
                
            # Validate release name format (Kubernetes naming rules)
            if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', release_name):
                return {
                    'valid': False, 
                    'error': 'Release name must be lowercase alphanumeric with hyphens (DNS-1123 compliant)'
                }
                
            namespace = self.options.get("namespace", "default")
            if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', namespace):
                return {
                    'valid': False, 
                    'error': 'Namespace must be lowercase alphanumeric with hyphens (DNS-1123 compliant)'
                }
                
            # Validate values YAML if provided
            values = self.options.get("values", {})
            if values and not isinstance(values, dict):
                return {'valid': False, 'error': 'Values must be a valid dictionary'}
                
            # Check if release already exists
            try:
                existing_release = self.helm_client.get_release(release_name, namespace)
                if existing_release:
                    return {
                        'valid': False, 
                        'error': f'Release "{release_name}" already exists in namespace "{namespace}". Use upgrade instead.'
                    }
            except Exception:
                # If we can't check, continue (release probably doesn't exist)
                pass
                
            return {'valid': True, 'error': None}
            
        except Exception as e:
            return {'valid': False, 'error': f'Validation error: {str(e)}'}

    def _generate_success_message(self, release_name: str, namespace: str) -> str:
        """Generate a detailed success message"""
        try:
            # Get release info for success message
            release = self.helm_client.get_release(release_name, namespace)
            if release:
                message = f"""Successfully installed Helm release '{release_name}'!

Release Details:
• Name: {release.name}
• Namespace: {namespace}
• Chart: {release.chart_name}-{release.chart_version}
• App Version: {release.app_version}
• Status: {release.status}
• Revision: {release.revision}

You can view the release in the Releases page or use kubectl to check the deployed resources.
"""
                return message
            else:
                return f"Successfully installed release '{release_name}' in namespace '{namespace}'."
                
        except Exception:
            return f"Successfully installed release '{release_name}' in namespace '{namespace}'."

    def _format_error_message(self, error: str) -> str:
        """Format error message with helpful troubleshooting information"""
        base_message = f"Installation failed: {error}"
        
        troubleshooting = """

Troubleshooting tips:
• Check that the cluster is accessible and you have proper permissions
• Verify the chart name and repository are correct
• Ensure the namespace exists or enable 'Create namespace'
• Check if the release name is already in use
• Review values for syntax errors
• Try refreshing repositories in 'Manage Repos'
"""
        
        return base_message + troubleshooting

    def _handle_download_failure(self, repo_name: str, chart_name: str, version: str):
        """Provide detailed feedback for download failures"""
        error_message = f"""Failed to download chart '{chart_name}' from repository '{repo_name}'.

Chart Details:
• Repository: {repo_name}
• Chart: {chart_name}
• Version: {version or 'latest'}

Troubleshooting steps:
1. Verify the chart name and repository are correct
2. Check if the chart version exists
3. Ensure internet connectivity
4. Try refreshing repositories in 'Manage Repos'
5. Check if the repository URL is accessible

Common fixes:
• Update repository indexes
• Try a different chart version
• Check repository configuration
• Verify network connectivity
        """.strip()
        
        self.installation_complete.emit(False, error_message)

    def _cleanup(self):
        """Clean up downloaded files and temporary resources"""
        if self.downloaded_chart_path and os.path.exists(self.downloaded_chart_path):
            try:
                shutil.rmtree(self.downloaded_chart_path, ignore_errors=True)
                self.downloaded_chart_path = None
                logging.debug("Cleaned up downloaded chart files")
            except Exception as e:
                logging.error(f"Error cleaning up download: {e}")

    def cancel(self):
        """Cancel the installation"""
        self._is_cancelled = True
        self.progress_update.emit("Cancelling installation...")

    def __del__(self):
        """Destructor to ensure cleanup"""
        self._cleanup()

# --- UI Components ---

class ScrollableMessageBox(QDialog):
    """Enhanced scrollable message box with better formatting"""
    
    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {AppColors.BG_DARK};
                color: {AppColors.TEXT_LIGHT};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Message text
        text_edit = QTextEdit(self)
        text_edit.setReadOnly(True)
        text_edit.setText(text)
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(text_edit)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.setStyleSheet("""
            QDialogButtonBox QPushButton {
                background-color: #0078d7;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
                min-width: 80px;
            }
            QDialogButtonBox QPushButton:hover {
                background-color: #0086e7;
            }
            QDialogButtonBox QPushButton:pressed {
                background-color: #0063b1;
            }
        """)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)


class ChartValuesThread(QThread):
    """Enhanced thread for loading chart values asynchronously with better error handling"""
    values_loaded = pyqtSignal(dict, dict)  # default_values, chart_metadata
    error_occurred = pyqtSignal(str)
    
    def __init__(self, chart, helm_client):
        super().__init__()
        self.chart = chart
        self.helm_client = helm_client
        self.downloaded_chart_path = None
        
    def run(self):
        try:
            repo_name = self.chart.get('repository')
            chart_name = self.chart.get('name')
            
            if not repo_name or not chart_name:
                self.error_occurred.emit("Chart repository and name are required")
                return
            
            # Download chart to get values
            self.downloaded_chart_path = self.helm_client.repo_manager.download_chart(
                repo_name, chart_name, "latest"
            )
            
            if not self.downloaded_chart_path:
                self.error_occurred.emit("Failed to download chart for values inspection")
                return
            
            # Find chart directory
            chart_dir = self._find_chart_directory(self.downloaded_chart_path, chart_name)
            if not chart_dir:
                self.error_occurred.emit("Chart directory not found")
                return
            
            # Load values and metadata
            default_values = self.helm_client.get_chart_values(chart_dir)
            chart_metadata = self.helm_client.get_chart_metadata(chart_dir)
            
            # Validate loaded data
            if not isinstance(default_values, dict):
                default_values = {}
            if not isinstance(chart_metadata, dict):
                chart_metadata = {}
            
            self.values_loaded.emit(default_values, chart_metadata)
            
        except Exception as e:
            error_msg = f"Error loading chart values: {str(e)}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
        finally:
            self._cleanup()
    
    def _find_chart_directory(self, downloaded_path: str, chart_name: str):
        """Find the chart directory within the downloaded path"""
        try:
            chart_dir = os.path.join(downloaded_path, chart_name)
            if os.path.exists(chart_dir) and os.path.exists(os.path.join(chart_dir, "Chart.yaml")):
                return chart_dir
            
            # Look for any subdirectory with Chart.yaml
            for item in os.listdir(downloaded_path):
                item_path = os.path.join(downloaded_path, item)
                if os.path.isdir(item_path):
                    if os.path.exists(os.path.join(item_path, "Chart.yaml")):
                        return item_path
            
            return None
        except Exception:
            return None
    
    def _cleanup(self):
        """Clean up downloaded files"""
        if self.downloaded_chart_path and os.path.exists(self.downloaded_chart_path):
            try:
                shutil.rmtree(self.downloaded_chart_path, ignore_errors=True)
            except Exception as e:
                logging.error(f"Error cleaning up values thread download: {e}")


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
    """Enhanced chart install dialog with improved validation and user experience"""
    
    def __init__(self, chart, parent=None):
        super().__init__(parent)
        self.chart = chart
        self.helm_client = None
        self.default_values = {}
        self.chart_metadata = {}
        self.validation_timer = QTimer()
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self._validate_form)
        
        # Initialize Helm client
        try:
            self.helm_client = get_helm_client_instance()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize Helm client: {e}")
            self.reject()
            return
        
        self.setWindowTitle(f"Install Chart: {self.chart.get('name')}")
        self.setMinimumSize(900, 700)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {AppColors.BG_DARK};
                color: {AppColors.TEXT_LIGHT};
            }}
            QTabWidget::pane {{
                border: 1px solid #3d3d3d;
                background-color: {AppColors.BG_DARK};
            }}
            QTabWidget::tab-bar {{
                alignment: left;
            }}
            QTabBar::tab {{
                background-color: #2d2d2d;
                color: {AppColors.TEXT_LIGHT};
                border: 1px solid #3d3d3d;
                padding: 8px 16px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {AppColors.BG_DARK};
                border-bottom: 2px solid #0078d7;
            }}
            QTabBar::tab:hover {{
                background-color: #3d3d3d;
            }}
        """)
        
        self.setup_ui()
        self.load_chart_values()

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
        
        name_label = QLabel(f"<h2>{self.chart.get('name', 'Unknown')}</h2>")
        name_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        title_layout.addWidget(name_label)
        
        title_layout.addStretch()
        
        version_label = QLabel(f"Version: {self.chart.get('version', 'Unknown')}")
        version_label.setStyleSheet("color: #888888; font-size: 14px;")
        title_layout.addWidget(version_label)
        
        repo_label = QLabel(f"Repository: {self.chart.get('repository', 'Unknown')}")
        repo_label.setStyleSheet("color: #888888; font-size: 14px;")
        title_layout.addWidget(repo_label)
        
        info_layout.addLayout(title_layout)
        
        # Description
        description = self.chart.get('description', 'No description available')
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #cccccc; font-style: italic; margin-bottom: 10px;")
        info_layout.addWidget(desc_label)
        
        layout.addWidget(info_widget)

    def setup_basic_config_tab(self):
        """Setup enhanced basic configuration tab"""
        basic_widget = QWidget()
        basic_layout = QFormLayout(basic_widget)
        basic_layout.setSpacing(15)
        
        # Release name with validation
        self.release_name_input = QLineEdit()
        self.release_name_input.setText(f"{self.chart.get('name')}-{''.join(random.choices(string.ascii_lowercase, k=4))}")
        self.release_name_input.setStyleSheet(self.get_input_style())
        self.release_name_input.textChanged.connect(self._start_validation_timer)
        basic_layout.addRow("Release Name:", self.release_name_input)
        
        # Namespace with autocomplete
        self.namespace_combo = QComboBox()
        self.namespace_combo.setEditable(True)
        self.namespace_combo.setStyleSheet(self.get_combo_style())
        self.load_namespaces()
        self.namespace_combo.currentTextChanged.connect(self._start_validation_timer)
        basic_layout.addRow("Namespace:", self.namespace_combo)
        
        # Version
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("Latest")
        self.version_input.setStyleSheet(self.get_input_style())
        basic_layout.addRow("Chart Version:", self.version_input)
        
        # Create namespace option
        self.create_namespace_checkbox = QCheckBox("Create namespace if it doesn't exist")
        self.create_namespace_checkbox.setChecked(True)
        self.create_namespace_checkbox.setStyleSheet("color: #ffffff; font-size: 13px;")
        basic_layout.addRow("", self.create_namespace_checkbox)
        
        self.tab_widget.addTab(basic_widget, "Basic Configuration")

    def setup_values_tab(self):
        """Setup enhanced values editing tab"""
        values_widget = QWidget()
        values_layout = QVBoxLayout(values_widget)
        
        # Loading message
        self.values_loading_label = QLabel("Loading chart values...")
        self.values_loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.values_loading_label.setStyleSheet("color: #888888; font-size: 14px; padding: 20px;")
        values_layout.addWidget(self.values_loading_label)
        
        # Splitter for values tree and editor
        self.values_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.values_splitter.hide()
        
        # Values tree view
        self.setup_values_tree()
        
        # Values editor
        self.setup_values_editor()
        
        self.values_splitter.addWidget(self.values_tree_container)
        self.values_splitter.addWidget(self.values_editor_container)
        self.values_splitter.setSizes([300, 500])
        
        values_layout.addWidget(self.values_splitter)
        
        self.tab_widget.addTab(values_widget, "Values Configuration")

    def setup_values_tree(self):
        """Setup enhanced values tree view"""
        self.values_tree_container = QWidget()
        tree_layout = QVBoxLayout(self.values_tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        
        tree_label = QLabel("Chart Values Structure:")
        tree_label.setStyleSheet("color: #ffffff; font-weight: bold; margin-bottom: 5px;")
        tree_layout.addWidget(tree_label)
        
        self.values_tree = QTreeWidget()
        self.values_tree.setHeaderLabel("Parameter")
        self.values_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 4px;
                border-bottom: 1px solid #3d3d3d;
            }
            QTreeWidget::item:selected {
                background-color: #0078d7;
            }
            QTreeWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.values_tree.itemClicked.connect(self.on_tree_item_clicked)
        tree_layout.addWidget(self.values_tree)
        
        # Tree controls
        button_layout = QHBoxLayout()
        expand_btn = QPushButton("Expand All")
        collapse_btn = QPushButton("Collapse All")
        
        for btn in [expand_btn, collapse_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
            """)
        
        expand_btn.clicked.connect(self.values_tree.expandAll)
        collapse_btn.clicked.connect(self.values_tree.collapseAll)
        
        button_layout.addWidget(expand_btn)
        button_layout.addWidget(collapse_btn)
        button_layout.addStretch()
        tree_layout.addLayout(button_layout)

    def setup_values_editor(self):
        """Setup enhanced values editor"""
        self.values_editor_container = QWidget()
        editor_layout = QVBoxLayout(self.values_editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        
        # Editor header
        editor_header = QHBoxLayout()
        editor_label = QLabel("Custom Values (YAML):")
        editor_label.setStyleSheet("color: #ffffff; font-weight: bold; margin-bottom: 5px;")
        editor_header.addWidget(editor_label)
        
        editor_header.addStretch()
        
        # Reset button
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f44336;
            }
        """)
        reset_btn.clicked.connect(self.reset_values_to_default)
        editor_header.addWidget(reset_btn)
        
        editor_layout.addLayout(editor_header)
        
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
        editor_layout.addWidget(self.values_editor)
        
        # Validation status for YAML
        self.yaml_validation_label = QLabel("")
        self.yaml_validation_label.setStyleSheet("color: #888888; font-size: 12px; margin-top: 5px;")
        editor_layout.addWidget(self.yaml_validation_label)

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
        self.cancel_button.clicked.connect(self.reject)
        
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
        self.install_button.clicked.connect(self.accept)
        self.install_button.setEnabled(False)  # Disabled until validation passes
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.install_button)
        
        layout.addLayout(button_layout)

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
        """Load available namespaces with error handling"""
        try:
            k8s_client = get_kubernetes_client().v1
            namespaces = sorted([ns.metadata.name for ns in k8s_client.list_namespace().items])
            self.namespace_combo.addItems(namespaces)
            if "default" in namespaces:
                self.namespace_combo.setCurrentText("default")
        except Exception as e:
            self.namespace_combo.addItem("default")
            logging.warning(f"Could not load namespaces: {e}")

    def load_chart_values(self):
        """Load chart values asynchronously with enhanced error handling"""
        if not self.helm_client:
            self.on_values_error("Helm client not available")
            return
        
        self.values_thread = ChartValuesThread(self.chart, self.helm_client)
        self.values_thread.values_loaded.connect(self.on_values_loaded)
        self.values_thread.error_occurred.connect(self.on_values_error)
        self.values_thread.start()

    def on_values_loaded(self, default_values, chart_metadata):
        """Handle loaded chart values with validation"""
        self.default_values = default_values
        self.chart_metadata = chart_metadata
        
        # Hide loading message and show values UI
        self.values_loading_label.hide()
        self.values_splitter.show()
        
        # Populate values tree
        self.populate_values_tree(default_values)
        
        # Set default values in editor
        if default_values:
            values_yaml = yaml.dump(default_values, default_flow_style=False, sort_keys=False)
            self.values_editor.setPlainText(values_yaml)
        else:
            self.values_editor.setPlaceholderText("# No default values found\n# Add your custom values here")
        
        # Enable validation and install button
        self._validate_form()
        
        # Switch to values tab
        self.tab_widget.setCurrentIndex(1)

    def on_values_error(self, error_message):
        """Handle values loading error with helpful feedback"""
        self.values_loading_label.setText(f"Error loading values: {error_message}\n\nYou can still install with custom values.")
        self.values_loading_label.setStyleSheet("color: #ff9800; font-size: 14px; padding: 20px;")
        
        # Enable validation anyway
        self._validate_form()

    def populate_values_tree(self, values, parent=None):
        """Populate the values tree widget with improved display"""
        if parent is None:
            parent = self.values_tree
            self.values_tree.clear()
        
        if isinstance(values, dict):
            for key, value in values.items():
                item = QTreeWidgetItem(parent)
                item.setText(0, str(key))
                
                if isinstance(value, (dict, list)):
                    self.populate_values_tree(value, item)
                    item.setToolTip(0, f"Type: {type(value).__name__}")
                else:
                    item.setText(0, f"{key}: {value}")
                    item.setToolTip(0, f"Value: {value}\nType: {type(value).__name__}")
        
        elif isinstance(values, list):
            for i, value in enumerate(values):
                item = QTreeWidgetItem(parent)
                if isinstance(value, (dict, list)):
                    item.setText(0, f"[{i}]")
                    self.populate_values_tree(value, item)
                else:
                    item.setText(0, f"[{i}]: {value}")
                    item.setToolTip(0, f"Value: {value}\nType: {type(value).__name__}")

    def on_tree_item_clicked(self, item, column):
        """Handle tree item click with path display"""
        # Get the path to this item
        path = []
        current = item
        while current is not None:
            path.insert(0, current.text(0).split(':')[0].strip('[]'))
            current = current.parent()
        
        # Show path in validation label
        if path:
            yaml_path = '.'.join(path)
            self.yaml_validation_label.setText(f"Selected: {yaml_path}")
            self.yaml_validation_label.setStyleSheet("color: #4CAF50; font-size: 12px; margin-top: 5px;")

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
        
        # Check for existing release (warning, not error)
        if not errors and self.helm_client:
            try:
                existing_release = self.helm_client.get_release(release_name, namespace)
                if existing_release:
                    warnings.append(f"Release '{release_name}' already exists in namespace '{namespace}'")
            except Exception:
                pass  # If we can't check, continue
        
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

    def reset_values_to_default(self):
        """Reset values editor to default values"""
        if self.default_values:
            values_yaml = yaml.dump(self.default_values, default_flow_style=False, sort_keys=False)
            self.values_editor.setPlainText(values_yaml)
        else:
            self.values_editor.clear()

    def get_values(self):
        """Get validated values from the dialog"""
        # Final validation before accepting
        if not self.install_button.isEnabled():
            return None
        
        values_text = self.values_editor.toPlainText().strip()
        values_dict = {}
        
        if values_text:
            try:
                values_dict = yaml.safe_load(values_text) or {}
            except yaml.YAMLError as e:
                QMessageBox.critical(self, "Invalid YAML", f"Error parsing values: {e}")
                return None
        
        return {
            "release_name": self.release_name_input.text().strip(),
            "namespace": self.namespace_combo.currentText().strip(),
            "version": self.version_input.text().strip() or None,
            "values": values_dict,
            "create_namespace": self.create_namespace_checkbox.isChecked(),
            "timeout": int(self.timeout_input.text() or "300"),
            "wait": self.wait_checkbox.isChecked(),
            "atomic": self.atomic_checkbox.isChecked(),
            "dry_run": self.dry_run_checkbox.isChecked(),
        }


class AddRepoDialog(QDialog):
    """Enhanced repository addition dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Helm Repository")
        self.setMinimumWidth(500)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {AppColors.BG_DARK};
                color: {AppColors.TEXT_LIGHT};
            }}
        """)
        
        layout = QFormLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Repository name
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet("""
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
        layout.addRow("Name:", self.name_input)
        
        # Repository URL
        self.url_input = QLineEdit()
        self.url_input.setStyleSheet("""
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
        layout.addRow("URL:", self.url_input)
        
        # Optional authentication
        self.user_input = QLineEdit()
        self.user_input.setStyleSheet("""
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
        layout.addRow("Username (optional):", self.user_input)
        
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setStyleSheet("""
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
        layout.addRow("Password (optional):", self.pass_input)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.setStyleSheet("""
            QDialogButtonBox QPushButton {
                background-color: #0078d7;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                min-width: 80px;
            }
            QDialogButtonBox QPushButton:hover {
                background-color: #0086e7;
            }
            QDialogButtonBox QPushButton[text="Cancel"] {
                background-color: #3d3d3d;
            }
            QDialogButtonBox QPushButton[text="Cancel"]:hover {
                background-color: #505050;
            }
        """)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_values(self):
        """Get repository values with validation"""
        name = self.name_input.text().strip()
        url = self.url_input.text().strip()
        
        if not name or not url:
            QMessageBox.warning(self, "Input Error", "Repository Name and URL are required.")
            return None
            
        # Basic URL validation
        if not (url.startswith('http://') or url.startswith('https://') or url.startswith('oci://')):
            QMessageBox.warning(self, "Invalid URL", "Repository URL must start with http://, https://, or oci://")
            return None
            
        return {
            "name": name,
            "url": url,
            "username": self.user_input.text().strip() or None,
            "password": self.pass_input.text().strip() or None,
        }


class ManageReposDialog(QDialog):
    """Enhanced repository management dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Helm Repositories")
        self.setMinimumSize(600, 400)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {AppColors.BG_DARK};
                color: {AppColors.TEXT_LIGHT};
            }}
        """)
        self.changes_made = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Repository list
        self.repo_list = QListWidget()
        self.repo_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3d3d3d;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.load_repos()
        layout.addWidget(self.repo_list)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        add_btn = QPushButton("Add Repository")
        remove_btn = QPushButton("Remove Selected")
        update_btn = QPushButton("Update All")
        close_btn = QPushButton("Close")

        for btn in [add_btn, remove_btn, update_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078d7;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #0086e7;
                }
            """)
        
        close_btn.setStyleSheet("""
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
        """)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(update_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        # Connect signals
        add_btn.clicked.connect(self.add_repo)
        remove_btn.clicked.connect(self.remove_repo)
        update_btn.clicked.connect(self.update_all_repos)
        close_btn.clicked.connect(self.accept)

    def load_repos(self):
        """Load repositories with enhanced display"""
        self.repo_list.clear()
        try:
            repos = get_helm_repos()
            for repo in repos:
                display_text = f"{repo['name']} - {repo['url']}"
                self.repo_list.addItem(display_text)
            
            if not repos:
                item = QListWidgetItem("No repositories configured")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self.repo_list.addItem(item)
                
        except Exception as e:
            error_item = QListWidgetItem(f"Error loading repositories: {e}")
            error_item.setFlags(error_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.repo_list.addItem(error_item)

    def add_repo(self):
        """Add repository with validation"""
        dialog = AddRepoDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            if values:
                try:
                    add_helm_repo(values['name'], values['url'], values['username'], values['password'])
                    self.changes_made = True
                    self.load_repos()
                    QMessageBox.information(self, "Success", f"Repository '{values['name']}' added successfully.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to add repository: {e}")

    def remove_repo(self):
        """Remove selected repository with confirmation"""
        selected = self.repo_list.currentItem()
        if not selected or not selected.flags() & Qt.ItemFlag.ItemIsSelectable:
            QMessageBox.warning(self, "Selection Error", "Please select a repository to remove.")
            return
        
        repo_name = selected.text().split(' - ')[0]
        reply = QMessageBox.question(
            self, 
            "Confirm Removal", 
            f"Are you sure you want to remove the '{repo_name}' repository?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                remove_helm_repo(repo_name)
                self.changes_made = True
                self.load_repos()
                QMessageBox.information(self, "Success", f"Repository '{repo_name}' removed successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove repository: {e}")

    def update_all_repos(self):
        """Update all repositories with progress feedback"""
        progress = QProgressDialog("Updating all repositories...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        
        QCoreApplication.processEvents()
        
        try:
            update_helm_repos()
            progress.close()
            self.changes_made = True
            QMessageBox.information(self, "Success", "All repositories updated successfully.")
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", f"Failed to update repositories: {e}")

    def exec(self):
        """Execute dialog and return whether changes were made"""
        super().exec()
        return self.changes_made


def install_helm_chart(chart: dict, options: dict, parent=None):
    """
    Enhanced function to trigger Helm installation with better error handling and user feedback.
    """
    if not chart or not isinstance(chart, dict):
        error_msg = "Invalid chart data provided."
        if parent:
            QMessageBox.critical(parent, "Installation Error", error_msg)
        else:
            logging.error(error_msg)
        return

    if options is None:
        error_msg = "Installation options are missing."
        if parent:
            QMessageBox.critical(parent, "Installation Error", error_msg)
        else:
            logging.error(error_msg)
        return

    # Validate required chart fields
    required_fields = ['name', 'repository']
    missing_fields = [field for field in required_fields if not chart.get(field)]
    if missing_fields:
        error_msg = f"Chart data missing required fields: {', '.join(missing_fields)}"
        if parent:
            QMessageBox.critical(parent, "Installation Error", error_msg)
        else:
            logging.error(error_msg)
        return

    # Create enhanced progress dialog
    progress = QProgressDialog("Preparing installation...", "Cancel", 0, 100, parent)
    progress.setWindowTitle(f"Installing {chart.get('name')}")
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setMinimumDuration(0)
    progress.show()

    # Create installation thread
    install_thread = HelmInstallThread(chart, options)

    def on_complete(success, message):
        progress.close()
        if success:
            msg_box = ScrollableMessageBox("Installation Success", message, parent)
            msg_box.exec()
        else:
            # Show error in scrollable box for better readability
            error_box = ScrollableMessageBox("Installation Failed", message, parent)
            error_box.exec()

    # Connect signals
    install_thread.progress_update.connect(progress.setLabelText)
    install_thread.progress_percentage.connect(progress.setValue)
    install_thread.installation_complete.connect(on_complete)
    progress.canceled.connect(install_thread.cancel)
    
    # Start installation
    install_thread.start()

    # Track thread for cleanup
    app_instance = QCoreApplication.instance()
    if not hasattr(app_instance, "running_threads"):
        app_instance.running_threads = []
    
    def cleanup_thread():
        if hasattr(app_instance, "running_threads") and install_thread in app_instance.running_threads:
            app_instance.running_threads.remove(install_thread)

    app_instance.running_threads.append(install_thread)
    install_thread.finished.connect(cleanup_thread)
