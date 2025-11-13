"""
Enhanced utilities for working with Helm charts using ArtifactHub API integration.
Includes installation, management, and repository handling capabilities.
"""

import os
import time
import yaml
import logging
import random
import string
import traceback
import re
import json
import tempfile
import requests
import base64
import gzip
import datetime
import subprocess
import sys
import platform
import shutil

# Windows subprocess configuration to prevent terminal popup
if sys.platform == 'win32':
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    SUBPROCESS_FLAGS = 0
from typing import Dict, Any, Optional
from kubernetes import client
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QTextEdit, QHBoxLayout, QPushButton, QProgressDialog, QMessageBox,
    QCheckBox, QLabel, QListWidget, QListWidgetItem, QDialogButtonBox,
    QTabWidget, QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView, QWidget, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QCoreApplication
from PyQt6.QtGui import QFont
from UI.Styles import AppColors


def check_helm_installed():
    """Check if Helm CLI is installed and available"""
    try:
        result = subprocess.run(['helm', 'version', '--short'], 
                              capture_output=True, text=True, timeout=10,
                              creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
        if result.returncode == 0:
            version = result.stdout.strip()
            logging.info(f"Helm is installed: {version}")
            return True, version
        else:
            logging.warning("Helm command failed")
            return False, "Helm command failed"
    except FileNotFoundError:
        logging.warning("Helm not found in PATH")
        return False, "Helm not found"
    except subprocess.TimeoutExpired:
        logging.error("Helm version check timed out")
        return False, "Helm check timeout"
    except Exception as e:
        logging.error(f"Error checking Helm: {e}")
        return False, str(e)


def install_helm():
    """Install Helm CLI automatically"""
    try:
        system = platform.system().lower()
        logging.info(f"Installing Helm for {system}")
        
        if system == "linux":
            return _install_helm_linux()
        elif system == "darwin":  # macOS
            return _install_helm_macos()
        elif system == "windows":
            return _install_helm_windows()
        else:
            return False, f"Unsupported operating system: {system}"
            
    except Exception as e:
        logging.error(f"Error installing Helm: {e}")
        return False, str(e)


def _install_helm_linux():
    """Install Helm on Linux"""
    try:
        # Download and install Helm using the official script
        install_script = """
        curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
        chmod 700 get_helm.sh
        ./get_helm.sh
        rm get_helm.sh
        """
        
        result = subprocess.run(install_script, shell=True, capture_output=True, 
                              text=True, timeout=300,
                              creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
        
        if result.returncode == 0:
            logging.info("Helm installed successfully on Linux")
            return True, "Helm installed successfully"
        else:
            logging.error(f"Helm installation failed: {result.stderr}")
            return False, f"Installation failed: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return False, "Helm installation timed out"
    except Exception as e:
        return False, str(e)


def _install_helm_macos():
    """Install Helm on macOS"""
    try:
        # Try with Homebrew first
        if shutil.which('brew'):
            result = subprocess.run(['brew', 'install', 'helm'], 
                                  capture_output=True, text=True, timeout=300,
                                  creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
            if result.returncode == 0:
                return True, "Helm installed via Homebrew"
        
        # Fallback to script installation
        return _install_helm_script_macos()
        
    except Exception as e:
        return False, str(e)


def _install_helm_script_macos():
    """Install Helm on macOS using script"""
    try:
        install_script = """
        curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
        chmod 700 get_helm.sh
        ./get_helm.sh
        rm get_helm.sh
        """
        
        result = subprocess.run(install_script, shell=True, capture_output=True, 
                              text=True, timeout=300,
                              creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
        
        if result.returncode == 0:
            return True, "Helm installed successfully on macOS"
        else:
            return False, f"Installation failed: {result.stderr}"
            
    except Exception as e:
        return False, str(e)


def _install_helm_windows():
    """Install Helm on Windows"""
    try:
        # Try with Chocolatey first
        if shutil.which('choco'):
            result = subprocess.run(['choco', 'install', 'kubernetes-helm', '-y'], 
                                  capture_output=True, text=True, timeout=300,
                                  creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
            if result.returncode == 0:
                return True, "Helm installed via Chocolatey"
        
        # Try with Scoop
        if shutil.which('scoop'):
            result = subprocess.run(['scoop', 'install', 'helm'], 
                                  capture_output=True, text=True, timeout=300,
                                  creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
            if result.returncode == 0:
                return True, "Helm installed via Scoop"
        
        return False, "Please install Helm manually from https://helm.sh/docs/intro/install/"
        
    except Exception as e:
        return False, str(e)


def ensure_helm_available():
    """Ensure Helm is available, install if necessary"""
    is_installed, message = check_helm_installed()
    
    if is_installed:
        return True, message
    
    logging.info("Helm not found, attempting to install...")
    return install_helm()


def run_helm_command(command_args, timeout=120):
    """Run a Helm command safely"""
    try:
        cmd = ['helm'] + command_args
        logging.info(f"Running Helm command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                                creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
        
        if result.returncode == 0:
            logging.info(f"Helm command successful: {result.stdout[:200]}...")
            return True, result.stdout
        else:
            logging.error(f"Helm command failed: {result.stderr}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        return False, f"Helm command timed out after {timeout} seconds"
    except Exception as e:
        return False, str(e)


def add_helm_repository(repo_name, repo_url):
    """Add a Helm repository"""
    return run_helm_command(['repo', 'add', repo_name, repo_url])


def update_helm_repositories():
    """Update Helm repositories with reasonable timeout"""
    return run_helm_command(['repo', 'update'], timeout=60)


def search_helm_chart(chart_name, repo=None):
    """Search for charts in Helm repositories"""
    if repo:
        search_term = f"{repo}/{chart_name}"
    else:
        search_term = chart_name
    
    return run_helm_command(['search', 'repo', search_term])


def install_helm_chart_cli(release_name, chart, namespace, values_file=None, values=None, version=None, create_namespace=False):
    """Install a chart using Helm CLI"""
    cmd = ['install', release_name, chart, '--namespace', namespace]
    
    if create_namespace:
        cmd.append('--create-namespace')
    
    if version:
        cmd.extend(['--version', version])
    
    if values_file and os.path.exists(values_file):
        cmd.extend(['--values', values_file])
    
    if values:
        for key, value in values.items():
            cmd.extend(['--set', f"{key}={value}"])
    
    # Add debugging flags to get more information if installation fails
    # Remove --wait to allow installation to complete in background and not timeout
    cmd.extend(['--debug'])
    
    return run_helm_command(cmd, timeout=180)  # 3 minutes should be enough without --wait


def upgrade_helm_chart_cli(release_name, chart, namespace, values_file=None, values=None):
    """Upgrade a chart using Helm CLI"""
    cmd = ['upgrade', release_name, chart, '--namespace', namespace]
    
    if values_file and os.path.exists(values_file):
        cmd.extend(['--values', values_file])
    
    if values:
        for key, value in values.items():
            cmd.extend(['--set', f"{key}={value}"])
    
    return run_helm_command(cmd, timeout=300)


def uninstall_helm_release_cli(release_name, namespace, keep_history=False):
    """Uninstall a Helm release using Helm CLI"""
    cmd = ['uninstall', release_name, '--namespace', namespace]
    
    if keep_history:
        cmd.append('--keep-history')
    
    return run_helm_command(cmd, timeout=300)


def list_helm_releases(namespace=None):
    """List Helm releases"""
    cmd = ['list']
    if namespace:
        cmd.extend(['--namespace', namespace])
    else:
        cmd.append('--all-namespaces')
    
    return run_helm_command(cmd)


def get_chart_from_artifacthub(chart_name, repository=None):
    """Get chart information from ArtifactHub API"""
    try:
        # Search for the chart
        search_url = "https://artifacthub.io/api/v1/packages/search"
        
        params = {
            "kind": "0",  # Helm charts
            "ts_query_web": chart_name
        }
        
        if repository:
            params["repo"] = repository
        
        response = requests.get(search_url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        packages = data.get("packages", [])
        
        # Find exact match
        for package in packages:
            if package.get("name") == chart_name:
                return package
        
        # Return first result if exact match not found
        return packages[0] if packages else None
        
    except Exception as e:
        logging.error(f"Error fetching chart from ArtifactHub: {e}")
        return None


def get_chart_versions(chart_name, repository=None):
    """Get available versions for a chart"""
    try:
        chart_info = get_chart_from_artifacthub(chart_name, repository)
        if not chart_info:
            return []
        
        package_id = chart_info.get("package_id")
        if not package_id:
            return []
        
        # Get chart versions
        versions_url = f"https://artifacthub.io/api/v1/packages/{package_id}"
        response = requests.get(versions_url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        available_versions = data.get("available_versions", [])
        
        return [v.get("version") for v in available_versions if v.get("version")]
        
    except Exception as e:
        logging.error(f"Error fetching chart versions: {e}")
        return []


def get_repository_url_from_artifacthub(repo_name):
    """Get repository URL from ArtifactHub for dynamic repository addition"""
    try:
        # Search for repositories on ArtifactHub
        search_url = "https://artifacthub.io/api/v1/repositories/search"
        params = {
            "name": repo_name,
            "kind": "0",  # Helm charts
            "limit": 10
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Handle different API response formats
            repositories = []
            if isinstance(data, list):
                # Direct list response
                repositories = data
                logging.debug(f"Received direct list response with {len(repositories)} repositories")
            elif isinstance(data, dict):
                # Dictionary response with repositories key
                repositories = data.get("repositories", [])
                logging.debug(f"Received dict response with {len(repositories)} repositories")
            else:
                logging.warning(f"Unexpected API response format: {type(data)}")
                return None
            
            if isinstance(repositories, list):
                for repo in repositories:
                    # Ensure repo is a dictionary before calling .get()
                    if isinstance(repo, dict):
                        repo_name_from_api = repo.get("name", "")
                        if isinstance(repo_name_from_api, str) and repo_name_from_api.lower() == repo_name.lower():
                            repo_url = repo.get("url")
                            if isinstance(repo_url, str):
                                logging.info(f"Found repository URL for {repo_name}: {repo_url}")
                                return repo_url
                    else:
                        logging.debug(f"Skipping non-dict repository entry: {type(repo)}")
            else:
                logging.warning(f"Unexpected repositories format: {type(repositories)}, value: {repositories}")
                    
        # Fallback to common known repositories
        known_repos = {
            "bitnami": "https://charts.bitnami.com/bitnami",
            "stable": "https://charts.helm.sh/stable",
            "ingress-nginx": "https://kubernetes.github.io/ingress-nginx",
            "jetstack": "https://charts.jetstack.io",
            "prometheus-community": "https://prometheus-community.github.io/helm-charts",
            "grafana": "https://grafana.github.io/helm-charts",
            "elastic": "https://helm.elastic.co",
            "codecentric": "https://codecentric.github.io/helm-charts",
            "hashicorp": "https://helm.releases.hashicorp.com",
            "gitlab": "https://charts.gitlab.io",
            "datadog": "https://helm.datadoghq.com",
            "kong": "https://charts.konghq.com",
            "vmware-tanzu": "https://vmware-tanzu.github.io/helm-charts",
            "argo": "https://argoproj.github.io/argo-helm",
            "traefik": "https://traefik.github.io/charts",
            "cert-manager": "https://charts.jetstack.io",
            "external-dns": "https://kubernetes-sigs.github.io/external-dns/",
            "metallb": "https://metallb.github.io/metallb",
            "nginx": "https://kubernetes.github.io/ingress-nginx"
        }
        
        return known_repos.get(repo_name.lower())
        
    except Exception as e:
        logging.error(f"Error getting repository URL for {repo_name}: {e}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        
        # Fallback to known repositories even on API error
        known_repos = {
            "bitnami": "https://charts.bitnami.com/bitnami",
            "stable": "https://charts.helm.sh/stable",
            "ingress-nginx": "https://kubernetes.github.io/ingress-nginx",
            "jetstack": "https://charts.jetstack.io",
            "prometheus-community": "https://prometheus-community.github.io/helm-charts",
            "grafana": "https://grafana.github.io/helm-charts",
            "elastic": "https://helm.elastic.co",
            "codecentric": "https://codecentric.github.io/helm-charts",
            "hashicorp": "https://helm.releases.hashicorp.com",
            "gitlab": "https://charts.gitlab.io",
            "datadog": "https://helm.datadoghq.com",
            "kong": "https://charts.konghq.com",
            "vmware-tanzu": "https://vmware-tanzu.github.io/helm-charts",
            "argo": "https://argoproj.github.io/argo-helm",
            "traefik": "https://traefik.github.io/charts",
            "cert-manager": "https://charts.jetstack.io",
            "external-dns": "https://kubernetes-sigs.github.io/external-dns/",
            "metallb": "https://metallb.github.io/metallb",
            "nginx": "https://kubernetes.github.io/ingress-nginx"
        }
        
        fallback_url = known_repos.get(repo_name.lower())
        if fallback_url:
            logging.info(f"Using fallback URL for {repo_name}: {fallback_url}")
        return fallback_url


def add_repository_for_chart(chart_name, repository_name):
    """Add a repository dynamically for a specific chart with improved error handling"""
    if not repository_name:
        logging.warning(f"No repository specified for chart {chart_name}")
        return False, "No repository specified"
    
    try:
        # Check if repository is already added
        success, output = run_helm_command(['repo', 'list'], timeout=10)
        if success and repository_name in output:
            logging.info(f"Repository {repository_name} already exists, skipping update")
            return True, "Repository already exists"
        
        # Get repository URL
        repo_url = get_repository_url_from_artifacthub(repository_name)
        if not repo_url:
            logging.error(f"Could not find URL for repository: {repository_name}")
            # Try alternative repository names for common charts
            alt_repos = {
                "argo": "argoproj",
                "prometheus": "prometheus-community",
                "cert-manager": "jetstack",
                "nginx": "ingress-nginx",
                "external-secrets": "external-secrets"
            }
            
            alt_name = alt_repos.get(repository_name.lower())
            if alt_name:
                logging.info(f"Trying alternative repository name: {alt_name}")
                repo_url = get_repository_url_from_artifacthub(alt_name)
            
            if not repo_url:
                return False, f"Repository URL not found for: {repository_name}. Please ensure the repository name is correct."
        
        logging.info(f"Adding repository {repository_name} with URL: {repo_url}")
        
        # Add the repository
        success, message = add_helm_repository(repository_name, repo_url)
        if success:
            logging.info(f"Successfully added repository: {repository_name}")
            # Skip update since it takes too long and is optional for installation
            logging.info(f"Skipping repository update to avoid timeout")
            return True, f"Successfully added repository: {repository_name}"
        else:
            logging.error(f"Failed to add repository {repository_name}: {message}")
            return False, f"Failed to add repository {repository_name}: {message}"
            
    except Exception as e:
        logging.error(f"Error in add_repository_for_chart: {e}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return False, f"Error adding repository: {str(e)}"


def setup_helm_repositories():
    """Setup basic Helm repositories and update them"""
    # Just add a few essential repositories, others will be added dynamically
    essential_repos = [
        ("bitnami", "https://charts.bitnami.com/bitnami"),
        ("stable", "https://charts.helm.sh/stable"),
    ]
    
    success_count = 0
    total_count = len(essential_repos)
    
    for repo_name, repo_url in essential_repos:
        success, message = add_helm_repository(repo_name, repo_url)
        if success:
            success_count += 1
            logging.info(f"Added essential repository: {repo_name}")
        else:
            logging.warning(f"Failed to add repository {repo_name}: {message}")
    
    # Skip repository update to speed up installation - it's optional
    # Most repositories are already added and charts can be installed without update
    logging.info("Skipping repository update to speed up installation")
    
    return success_count, total_count


def download_chart_manifest(chart_name, repository=None, version=None):
    """
    DEPRECATED: This function is replaced by direct Helm CLI usage.
    Use install_helm_chart_cli() instead for proper chart installation.
    """
    logging.error("download_chart_manifest() is deprecated. Use Helm CLI functions instead.")
    return None

def _generate_basic_chart_manifests(chart_name, chart_type, chart_info):
    """Generate basic manifests for well-known chart types"""
    manifests = []
    
    # Common labels
    common_labels = {
        "app.kubernetes.io/name": chart_name,
        "app.kubernetes.io/managed-by": "Helm",
        "app.kubernetes.io/instance": chart_name
    }
    
    if chart_type == "nginx":
        # NGINX deployment
        manifests.append({
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": chart_name,
                "labels": common_labels
            },
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": common_labels},
                "template": {
                    "metadata": {"labels": common_labels},
                    "spec": {
                        "containers": [{
                            "name": "nginx",
                            "image": "nginx:1.24-alpine",
                            "ports": [{"containerPort": 80}],
                            "resources": {
                                "requests": {"memory": "64Mi", "cpu": "250m"},
                                "limits": {"memory": "128Mi", "cpu": "500m"}
                            }
                        }]
                    }
                }
            }
        })
        
        # NGINX service
        manifests.append({
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": chart_name,
                "labels": common_labels
            },
            "spec": {
                "selector": common_labels,
                "ports": [{"port": 80, "targetPort": 80}],
                "type": "ClusterIP"
            }
        })
    
    elif chart_type in ["redis", "postgresql", "mysql", "mongodb"]:
        # Database deployment with stable tags
        image_map = {
            "redis": "redis:7-alpine",
            "postgresql": "postgres:15-alpine", 
            "mysql": "mysql:8.0",
            "mongodb": "mongo:7"
        }
        
        port_map = {
            "redis": 6379,
            "postgresql": 5432,
            "mysql": 3306, 
            "mongodb": 27017
        }
        
        manifests.append({
            "apiVersion": "apps/v1",
            "kind": "Deployment", 
            "metadata": {
                "name": chart_name,
                "labels": common_labels
            },
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": common_labels},
                "template": {
                    "metadata": {"labels": common_labels},
                    "spec": {
                        "containers": [{
                            "name": chart_type,
                            "image": image_map[chart_type],
                            "ports": [{"containerPort": port_map[chart_type]}],
                            "resources": {
                                "requests": {"memory": "256Mi", "cpu": "250m"},
                                "limits": {"memory": "512Mi", "cpu": "500m"}
                            },
                            "env": [{
                                "name": "ALLOW_EMPTY_PASSWORD",
                                "value": "yes"
                            }] if chart_type in ["redis", "mysql", "mongodb"] else [{
                                "name": "POSTGRES_PASSWORD",
                                "value": "password"
                            }]
                        }]
                    }
                }
            }
        })
        
        # Service
        manifests.append({
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": chart_name,
                "labels": common_labels
            },
            "spec": {
                "selector": common_labels,
                "ports": [{"port": port_map[chart_type], "targetPort": port_map[chart_type]}],
                "type": "ClusterIP"
            }
        })
    
    return manifests

def _generate_generic_deployment(chart_name, chart_info):
    """Generate a generic deployment for unknown charts"""
    common_labels = {
        "app.kubernetes.io/name": chart_name,
        "app.kubernetes.io/managed-by": "Helm",
        "app.kubernetes.io/instance": chart_name
    }
    
    # For unknown charts, use a simple nginx as a placeholder
    # In production, you would parse the actual chart templates
    logging.warning(f"Using generic nginx deployment for unknown chart: {chart_name}")
    
    manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": chart_name,
            "labels": common_labels,
            "annotations": {
                "description": chart_info.get("description", ""),
                "source": "ArtifactHub via Orchetrix",
                "warning": "This is a generic deployment. The actual chart may require different configuration."
            }
        },
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": common_labels},
            "template": {
                "metadata": {"labels": common_labels},
                "spec": {
                    "containers": [{
                        "name": chart_name,
                        "image": "nginx:1.24-alpine",
                        "ports": [{"containerPort": 80}],
                        "resources": {
                            "requests": {"memory": "64Mi", "cpu": "250m"},
                            "limits": {"memory": "128Mi", "cpu": "500m"}
                        }
                    }]
                }
            }
        }
    }
    
    # Add a service for the generic deployment
    service_manifest = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": chart_name,
            "labels": common_labels
        },
        "spec": {
            "selector": common_labels,
            "ports": [{"port": 80, "targetPort": 80}],
            "type": "ClusterIP"
        }
    }
    
    return [manifest, service_manifest]


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
                    create_namespace=create_namespace
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
                    "description": f"Install complete"
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


class ChartInstallDialog(QDialog):
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
        
        name_label = QLabel(f"<h2>{self.chart_name}</h2>")
        name_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        title_layout.addWidget(name_label)
        
        title_layout.addStretch()
        
        repo_label = QLabel(f"Repository: {self.repository}")
        repo_label.setStyleSheet("color: #888888; font-size: 14px;")
        title_layout.addWidget(repo_label)
        
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
            "values": values_text,
            "create_namespace": self.create_namespace_checkbox.isChecked(),
            "timeout": int(self.timeout_input.text() or "300"),
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
            global _installation_in_progress, _current_progress_dialog
            install_thread.cancel()
            _installation_in_progress = False
            _current_progress_dialog = None
        
        progress.canceled.connect(on_canceled)
        
        # Start installation
        install_thread.start()
        
        # Process events while waiting to keep UI responsive and show progress
        timeout_counter = 0
        max_timeout = 3600  # 180 seconds (3600 * 50ms) - match helm command timeout
        
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
            result["message"] = ("Installation command timed out after 180 seconds. This usually happens when:\n\n"
                              "1. Chart download is slow\n"
                              "2. Kubernetes cluster is not responding\n"
                              "3. Network connectivity issues\n\n"
                              "Note: The chart may still be installing in the background.\n"
                              "Check the Releases page to see if installation completed.")
            result["completed"] = True
        
        # Ensure thread is fully finished
        install_thread.wait()
        
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
        """Execute the Helm upgrade using Helm CLI"""
        try:
            self.progress_update.emit("Initializing upgrade...")
            self.progress_percentage.emit(5)
            
            if self._is_cancelled:
                return
                
            self.progress_update.emit("Connecting to Kubernetes API...")
            self.progress_percentage.emit(10)
            
            # Get Kubernetes client
            from Utils.kubernetes_client import get_kubernetes_client
            
            k8s_client = get_kubernetes_client()
            if not k8s_client or not k8s_client.v1:
                self.upgrade_complete.emit(False, "Kubernetes client not available. Please connect to a cluster.")
                return
                
            if self._is_cancelled:
                return
                
            # Validate inputs
            version = self.options.get("version")
            values_yaml = self.options.get("values", "").strip()
            
            self.progress_update.emit("Checking release existence...")
            self.progress_percentage.emit(15)
            
            # Check if release exists
            if not self._check_release_exists_api(k8s_client, self.release_name, self.namespace):
                self.upgrade_complete.emit(False, f"Release '{self.release_name}' not found in namespace '{self.namespace}'")
                return
                
            if self._is_cancelled:
                return
                
            self.progress_update.emit("Fetching chart information...")
            self.progress_percentage.emit(35)
            
            # Get chart information from ArtifactHub
            chart_info = get_chart_from_artifacthub(self.chart_name, self.repository)
            if not chart_info:
                self.upgrade_complete.emit(False, f"Chart '{self.chart_name}' not found in repository '{self.repository}'")
                return
            
            if self._is_cancelled:
                return
                
            self.progress_update.emit("Generating updated manifests...")
            self.progress_percentage.emit(50)
            
            # Download and render chart manifests
            manifests = download_chart_manifest(self.chart_name, self.repository, version)
            if not manifests:
                self.upgrade_complete.emit(False, "Failed to generate Kubernetes manifests")
                return
            
            if self._is_cancelled:
                return
                
            self.progress_update.emit(f"Upgrading {self.release_name}...")
            self.progress_percentage.emit(70)
            
            # Apply updated manifests to cluster
            success = self._update_manifests_in_cluster(k8s_client, manifests, self.release_name, self.namespace)
            
            if self._is_cancelled:
                return
            
            if success:
                self.progress_update.emit("Updating Helm release record...")
                self.progress_percentage.emit(90)
                
                # Update Helm release secret
                self._update_helm_release_secret(k8s_client, self.release_name, self.namespace, chart_info, values_yaml)
                
                self.progress_percentage.emit(100)
                self.upgrade_complete.emit(True, f"Successfully upgraded release '{self.release_name}' to chart '{self.chart_name}'")
            else:
                self.upgrade_complete.emit(False, "Failed to apply updated manifests to cluster")
            
        except Exception as e:
            logging.error(f"Error in helm upgrade thread: {e}")
            self.upgrade_complete.emit(False, f"Upgrade error: {str(e)}")

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
                    "description": f"Upgrade complete"
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
        result = {"success": False, "message": ""}

        def on_complete(success, message):
            progress.close()
            result["success"] = success
            result["message"] = message

        # Connect signals
        upgrade_thread.progress_update.connect(progress.setLabelText)
        upgrade_thread.progress_percentage.connect(progress.setValue)
        upgrade_thread.upgrade_complete.connect(on_complete)
        progress.canceled.connect(upgrade_thread.cancel)
        
        # Start upgrade
        upgrade_thread.start()
        upgrade_thread.wait()  # Wait for completion

        return result["success"], result["message"]

    except Exception as e:
        error_msg = f"Upgrade failed: {str(e)}"
        if parent:
            QMessageBox.critical(parent, "Upgrade Error", error_msg)
        return False, error_msg


def uninstall_helm_release(release_name, namespace, parent=None, keep_history=False):
    """Function to uninstall a Helm release"""
    if not all([release_name, namespace]):
        error_msg = "Release name and namespace are required."
        if parent:
            QMessageBox.critical(parent, "Uninstall Error", error_msg)
        else:
            logging.error(error_msg)
        return False, error_msg

    try:
        # Ensure Helm is available
        helm_available, helm_message = ensure_helm_available()
        if not helm_available:
            error_msg = f"Helm not available: {helm_message}"
            if parent:
                QMessageBox.critical(parent, "Uninstall Error", error_msg)
            return False, error_msg

        # Create progress dialog
        progress = QProgressDialog("Uninstalling Helm release...", "Cancel", 0, 100, parent)
        progress.setWindowTitle(f"Uninstalling {release_name}")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        
        progress.setValue(25)

        # Run Helm uninstall command
        success, message = uninstall_helm_release_cli(release_name, namespace, keep_history)
        
        progress.setValue(100)
        progress.close()

        if success:
            success_msg = f"Successfully uninstalled release '{release_name}' from namespace '{namespace}'"
            logging.info(success_msg)
            return True, success_msg
        else:
            # Handle specific error cases
            if "no release provided" in message.lower():
                error_msg = f"Release '{release_name}' not found. It may have been already deleted or the name is incorrect."
            elif "not found" in message.lower():
                error_msg = f"Release '{release_name}' not found in namespace '{namespace}'."
            else:
                error_msg = f"Failed to uninstall release '{release_name}': {message}"
            
            logging.error(error_msg)
            return False, error_msg

    except Exception as e:
        error_msg = f"Uninstall failed: {str(e)}"
        logging.error(error_msg)
        if parent:
            QMessageBox.critical(parent, "Uninstall Error", error_msg)
        return False, error_msg