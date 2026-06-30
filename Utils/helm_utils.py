"""
Enhanced utilities for working with Helm charts using ArtifactHub API integration.
Includes installation, management, and repository handling capabilities.
"""

import os
import yaml
import logging
import random
import string
import re
import json
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
from typing import Optional
from kubernetes import client



def find_helm_executable():
    """Find the helm executable on the system."""
    helm_exe = "helm.exe" if platform.system() == "Windows" else "helm"
    helm_path = shutil.which(helm_exe)
    if helm_path:
        return helm_path

    if platform.system() == "Windows":
        common_paths = [
            os.path.expanduser("~\\helm\\helm.exe"),
            "C:\\Program Files\\Helm\\helm.exe",
            "C:\\helm\\helm.exe",
            os.path.expanduser("~\\.windows-package-manager\\helm\\helm.exe"),
            os.path.expanduser("~\\AppData\\Local\\Programs\\Helm\\helm.exe"),
        ]
    else:
        common_paths = [
            "/usr/local/bin/helm",
            "/usr/bin/helm",
            os.path.expanduser("~/bin/helm"),
            "/opt/homebrew/bin/helm",
        ]

    for path in common_paths:
        if os.path.isfile(path):
            return path

    return None


def check_helm_installed():
    """Check if Helm CLI is installed and available"""
    helm_path = find_helm_executable() or 'helm'
    try:
        result = subprocess.run([helm_path, 'version', '--short'],
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
        logging.warning(f"Helm not found at resolved path: {helm_path}")
        return False, f"Helm not found at: {helm_path}"
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
    helm_path = find_helm_executable() or 'helm'
    try:
        cmd = [helm_path] + command_args
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


def install_helm_chart_cli(release_name, chart, namespace, values_file=None, values=None,
                           version=None, create_namespace=False, timeout=None,
                           wait=False, atomic=False, dry_run=False):
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

    # Honour advanced options collected by the install dialog.
    cmd_timeout = 180  # default subprocess timeout (seconds)
    if dry_run:
        cmd.append('--dry-run')
    if atomic:
        cmd.append('--atomic')  # --atomic implies --wait
    elif wait:
        cmd.append('--wait')
    if timeout:
        try:
            timeout_secs = int(timeout)
            if timeout_secs > 0:
                cmd.extend(['--timeout', f'{timeout_secs}s'])
                if atomic or wait:
                    # Give the subprocess headroom to honour Helm's own --timeout
                    # before we kill it.
                    cmd_timeout = max(cmd_timeout, timeout_secs + 60)
        except (TypeError, ValueError):
            pass

    # Add debugging flags to get more information if installation fails
    cmd.extend(['--debug'])

    return run_helm_command(cmd, timeout=cmd_timeout)


def upgrade_helm_chart_cli(release_name, chart, namespace, values_file=None, values=None, version=None):
    """Upgrade a chart using Helm CLI"""
    cmd = ['upgrade', release_name, chart, '--namespace', namespace]

    if version:
        cmd.extend(['--version', version])

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
            logging.info("Skipping repository update to avoid timeout")
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
