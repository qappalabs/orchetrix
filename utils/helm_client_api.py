"""
Enhanced Helm Client that uses Kubernetes API instead of subprocess calls.
Supports all major repositories and doesn't require external Helm installation.
"""

import os
import json
import yaml
import base64
import gzip
import tempfile
import requests
import tarfile
import io
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import logging

from kubernetes import client
from kubernetes.client.rest import ApiException
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from utils.kubernetes_client import get_kubernetes_client


class HelmRepositoryManager:
    """Manages Helm repositories and chart discovery"""
    
    # Comprehensive list of major Helm repositories
    OFFICIAL_REPOSITORIES = {
        # Bitnami - Most popular
        "bitnami": "https://charts.bitnami.com/bitnami",
        
        # Cloud Native Computing Foundation
        "prometheus-community": "https://prometheus-community.github.io/helm-charts",
        "grafana": "https://grafana.github.io/helm-charts",
        "jaeger": "https://jaegertracing.github.io/helm-charts",
        "keda": "https://kedacore.github.io/charts",
        "kubernetes-dashboard": "https://kubernetes.github.io/dashboard/",
        "ingress-nginx": "https://kubernetes.github.io/ingress-nginx",
        "external-dns": "https://kubernetes-sigs.github.io/external-dns/",
        "metrics-server": "https://kubernetes-sigs.github.io/metrics-server/",
        
        # HashiCorp
        "hashicorp": "https://helm.releases.hashicorp.com",
        
        # Elastic
        "elastic": "https://helm.elastic.co",
        
        # JetStack (cert-manager)
        "jetstack": "https://charts.jetstack.io",
        
        # NGINX
        "nginx-stable": "https://helm.nginx.com/stable",
        "nginx-edge": "https://helm.nginx.com/edge",
        
        # Apache projects
        "apache": "https://pulsar.apache.org/charts",
        "airflow": "https://airflow.apache.org/charts",
        "kafka": "https://strimzi.io/charts/",
        
        # Database systems
        "percona": "https://percona.github.io/percona-helm-charts/",
        "cockroachdb": "https://charts.cockroachdb.com/",
        "redis": "https://dandydeveloper.github.io/charts/",
        "mongodb": "https://mongodb.github.io/helm-charts",
        "postgresql": "https://charts.bitnami.com/bitnami",  # Part of bitnami
        
        # CI/CD
        "jenkins": "https://charts.jenkins.io",
        "argo": "https://argoproj.github.io/argo-helm",
        "gitlab": "https://charts.gitlab.io/",
        "tekton": "https://storage.googleapis.com/tekton-releases/charts/",
        "fluxcd": "https://charts.fluxcd.io",
        
        # Monitoring & Observability
        "datadog": "https://helm.datadoghq.com",
        "newrelic": "https://helm-charts.newrelic.com",
        "splunk": "https://splunk.github.io/splunk-connect-for-kubernetes/",
        "dynatrace": "https://raw.githubusercontent.com/Dynatrace/helm-charts/master/repos/stable",
        
        # Service Mesh
        "istio": "https://istio-release.storage.googleapis.com/charts",
        "linkerd": "https://helm.linkerd.io/stable",
        "consul": "https://helm.releases.hashicorp.com",  # Part of hashicorp
        
        # Security
        "falco": "https://falcosecurity.github.io/charts",
        "vault": "https://helm.releases.hashicorp.com",  # Part of hashicorp
        "sealed-secrets": "https://bitnami-labs.github.io/sealed-secrets",
        
        # Storage
        "rook": "https://charts.rook.io/release",
        "openebs": "https://openebs.github.io/charts",
        "longhorn": "https://charts.longhorn.io",
        
        # Networking
        "cilium": "https://helm.cilium.io/",
        "calico": "https://docs.projectcalico.org/charts",
        "metallb": "https://metallb.github.io/metallb",
        
        # Development Tools
        "codecov": "https://codecov.github.io/helm-charts",
        "sonarqube": "https://SonarSource.github.io/helm-chart-sonarqube",
        "harbor": "https://helm.goharbor.io",
        
        # Message Queues
        "rabbitmq": "https://charts.bitnami.com/bitnami",  # Part of bitnami
        "nats": "https://nats-io.github.io/k8s/helm/charts/",
        "activemq": "https://charts.bitnami.com/bitnami",  # Part of bitnami
        
        # Machine Learning
        "kubeflow": "https://charts.kubeflow.org",
        "mlflow": "https://charts.bitnami.com/bitnami",  # Part of bitnami
        
        # Edge Computing
        "k3s": "https://charts.rancher.io/",
        "kubeedge": "https://raw.githubusercontent.com/kubeedge/kubeedge/master/build/helm",
        
        # Backup & Disaster Recovery
        "velero": "https://vmware-tanzu.github.io/helm-charts/",
        "kasten": "https://charts.kasten.io/",
        
        # Legacy/Deprecated (still used by some)
        "stable": "https://charts.helm.sh/stable",
        "incubator": "https://charts.helm.sh/incubator",
    }
    
    def __init__(self):
        self.repositories = self.OFFICIAL_REPOSITORIES.copy()
        self.cache = {}
        
    def add_repository(self, name: str, url: str) -> bool:
        """Add a custom repository"""
        try:
            # Validate repository by trying to fetch index
            response = requests.get(f"{url.rstrip('/')}/index.yaml", timeout=10)
            if response.status_code == 200:
                self.repositories[name] = url
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to add repository {name}: {e}")
            return False
    
    def get_repository_url(self, name: str) -> Optional[str]:
        """Get repository URL by name"""
        return self.repositories.get(name)
    
    def search_repositories_for_chart(self, chart_name: str) -> List[Tuple[str, str]]:
        """Search all repositories for a specific chart"""
        found_repos = []
        
        for repo_name, repo_url in self.repositories.items():
            try:
                if self._chart_exists_in_repo(repo_url, chart_name):
                    found_repos.append((repo_name, repo_url))
            except Exception as e:
                logging.debug(f"Error checking {repo_name} for {chart_name}: {e}")
                continue
                
        return found_repos
    
    def _chart_exists_in_repo(self, repo_url: str, chart_name: str) -> bool:
        """Check if a chart exists in a repository"""
        try:
            # Try to fetch repository index
            response = requests.get(f"{repo_url.rstrip('/')}/index.yaml", timeout=5)
            if response.status_code == 200:
                index = yaml.safe_load(response.text)
                return chart_name in index.get('entries', {})
            return False
        except Exception:
            return False
    
    def get_chart_info(self, repo_url: str, chart_name: str) -> Optional[Dict]:
        """Get detailed information about a chart from repository"""
        try:
            response = requests.get(f"{repo_url.rstrip('/')}/index.yaml", timeout=10)
            if response.status_code == 200:
                index = yaml.safe_load(response.text)
                chart_versions = index.get('entries', {}).get(chart_name, [])
                if chart_versions:
                    # Return latest version info
                    return chart_versions[0]
            return None
        except Exception as e:
            logging.error(f"Error getting chart info: {e}")
            return None


class HelmChartInstaller:
    """Handles chart downloading and installation via Kubernetes API"""
    
    def __init__(self, kube_client=None):
        self.kube_client = kube_client or get_kubernetes_client()
        self.repo_manager = HelmRepositoryManager()
        
    def download_chart(self, chart_url: str, dest_dir: str) -> Optional[str]:
        """Download and extract chart from URL"""
        try:
            response = requests.get(chart_url, stream=True)
            response.raise_for_status()
            
            # Create temporary file for the chart
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tgz') as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            # Extract chart
            chart_dir = os.path.join(dest_dir, 'chart')
            with tarfile.open(temp_path, 'r:gz') as tar:
                tar.extractall(chart_dir)
            
            # Find the chart directory (usually the first directory in the archive)
            extracted_dirs = [d for d in os.listdir(chart_dir) 
                            if os.path.isdir(os.path.join(chart_dir, d))]
            if extracted_dirs:
                return os.path.join(chart_dir, extracted_dirs[0])
            
            return chart_dir
            
        except Exception as e:
            logging.error(f"Error downloading chart: {e}")
            return None
        finally:
            # Clean up temporary file
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except:
                    pass
    
    def install_chart(self, chart_name: str, release_name: str, namespace: str,
                     repository: str = None, repository_url: str = None, 
                     version: str = None, values: Dict = None,
                     create_namespace: bool = True) -> Tuple[bool, str]:
        """Install a chart using Kubernetes API"""
        try:
            # Determine repository URL
            repo_url = repository_url
            if not repo_url and repository:
                repo_url = self.repo_manager.get_repository_url(repository)
                if not repo_url:
                    # Try to find the chart in known repositories
                    found_repos = self.repo_manager.search_repositories_for_chart(chart_name)
                    if found_repos:
                        repo_url = found_repos[0][1]  # Use first found repository
                        logging.info(f"Found chart {chart_name} in repository: {found_repos[0][0]}")
                    else:
                        return False, f"Chart {chart_name} not found in any known repositories"
            
            if not repo_url:
                return False, "No repository specified or found"
            
            # Get chart information
            chart_info = self.repo_manager.get_chart_info(repo_url, chart_name)
            if not chart_info:
                return False, f"Chart {chart_name} not found in repository"
            
            # Select version
            chart_version = version or chart_info.get('version')
            chart_urls = chart_info.get('urls', [])
            if not chart_urls:
                return False, "No download URL found for chart"
            
            # Handle relative URLs
            chart_url = chart_urls[0]
            if not chart_url.startswith(('http://', 'https://')):
                chart_url = f"{repo_url.rstrip('/')}/{chart_url}"
            
            # Create namespace if needed
            if create_namespace:
                self._create_namespace_if_not_exists(namespace)
            
            # Download and process chart
            with tempfile.TemporaryDirectory() as temp_dir:
                chart_dir = self.download_chart(chart_url, temp_dir)
                if not chart_dir:
                    return False, "Failed to download chart"
                
                # Load Chart.yaml
                chart_yaml_path = os.path.join(chart_dir, 'Chart.yaml')
                if not os.path.exists(chart_yaml_path):
                    return False, "Invalid chart: Chart.yaml not found"
                
                with open(chart_yaml_path, 'r') as f:
                    chart_metadata = yaml.safe_load(f)
                
                # Process values
                final_values = self._merge_values(chart_dir, values or {})
                
                # Render templates
                manifests = self._render_chart_templates(chart_dir, release_name, namespace, final_values)
                if not manifests:
                    return False, "Failed to render chart templates"
                
                # Apply manifests to cluster
                success, message = self._apply_manifests(manifests, release_name, namespace)
                if not success:
                    return False, message
                
                # Create Helm release secret (for tracking)
                self._create_release_secret(release_name, namespace, chart_metadata, final_values, manifests)
                
                return True, f"Successfully installed {release_name}"
                
        except Exception as e:
            logging.error(f"Error installing chart: {e}")
            return False, f"Installation failed: {str(e)}"
    
    def _create_namespace_if_not_exists(self, namespace: str):
        """Create namespace if it doesn't exist"""
        try:
            self.kube_client.v1.read_namespace(name=namespace)
        except ApiException as e:
            if e.status == 404:
                # Namespace doesn't exist, create it
                namespace_manifest = client.V1Namespace(
                    metadata=client.V1ObjectMeta(name=namespace)
                )
                self.kube_client.v1.create_namespace(body=namespace_manifest)
                logging.info(f"Created namespace: {namespace}")
    
    def _merge_values(self, chart_dir: str, custom_values: Dict) -> Dict:
        """Merge default values with custom values"""
        # Load default values.yaml
        values_path = os.path.join(chart_dir, 'values.yaml')
        default_values = {}
        
        if os.path.exists(values_path):
            with open(values_path, 'r') as f:
                default_values = yaml.safe_load(f) or {}
        
        # Deep merge custom values
        return self._deep_merge(default_values, custom_values)
    
    def _deep_merge(self, dict1: Dict, dict2: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _render_chart_templates(self, chart_dir: str, release_name: str, 
                               namespace: str, values: Dict) -> List[Dict]:
        """Render chart templates with values"""
        try:
            templates_dir = os.path.join(chart_dir, 'templates')
            if not os.path.exists(templates_dir):
                return []
            
            manifests = []
            
            # Simple template rendering (basic variable substitution)
            # For production use, consider using a proper Helm template engine
            for root, dirs, files in os.walk(templates_dir):
                for file in files:
                    if file.endswith(('.yaml', '.yml')):
                        template_path = os.path.join(root, file)
                        try:
                            with open(template_path, 'r') as f:
                                content = f.read()
                            
                            # Basic variable substitution
                            rendered_content = self._substitute_template_vars(
                                content, release_name, namespace, values
                            )
                            
                            # Parse YAML documents
                            docs = list(yaml.safe_load_all(rendered_content))
                            for doc in docs:
                                if doc and isinstance(doc, dict):
                                    manifests.append(doc)
                                    
                        except Exception as e:
                            logging.error(f"Error rendering template {template_path}: {e}")
                            continue
            
            return manifests
            
        except Exception as e:
            logging.error(f"Error rendering chart templates: {e}")
            return []
    
    def _substitute_template_vars(self, content: str, release_name: str, 
                                 namespace: str, values: Dict) -> str:
        """Basic template variable substitution"""
        # This is a simplified implementation
        # For full Helm compatibility, you'd need a proper Go template engine
        
        substitutions = {
            '{{ .Release.Name }}': release_name,
            '{{ .Release.Namespace }}': namespace,
            '{{.Release.Name}}': release_name,
            '{{.Release.Namespace}}': namespace,
        }
        
        # Add values substitutions (basic dot notation)
        def add_value_substitutions(obj, prefix=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, (str, int, float, bool)):
                        substitutions[f'{{{{ .Values.{full_key} }}}}'] = str(value)
                        substitutions[f'{{{{.Values.{full_key}}}}}'] = str(value)
                    elif isinstance(value, dict):
                        add_value_substitutions(value, full_key)
        
        add_value_substitutions(values)
        
        # Apply substitutions
        result = content
        for placeholder, value in substitutions.items():
            result = result.replace(placeholder, value)
        
        return result
    
    def _apply_manifests(self, manifests: List[Dict], release_name: str, namespace: str) -> Tuple[bool, str]:
        """Apply Kubernetes manifests"""
        try:
            applied_resources = []
            
            for manifest in manifests:
                try:
                    api_version = manifest.get('apiVersion', '')
                    kind = manifest.get('kind', '')
                    
                    # Ensure namespace is set
                    if 'metadata' not in manifest:
                        manifest['metadata'] = {}
                    if 'namespace' not in manifest['metadata'] and kind not in ['Namespace', 'ClusterRole', 'ClusterRoleBinding']:
                        manifest['metadata']['namespace'] = namespace
                    
                    # Add labels for tracking
                    if 'labels' not in manifest['metadata']:
                        manifest['metadata']['labels'] = {}
                    manifest['metadata']['labels'].update({
                        'app.kubernetes.io/managed-by': 'orchestrix-helm',
                        'app.kubernetes.io/instance': release_name
                    })
                    
                    # Apply based on resource type
                    success = self._apply_single_manifest(manifest, api_version, kind, namespace)
                    if success:
                        applied_resources.append(f"{kind}/{manifest['metadata']['name']}")
                    
                except Exception as e:
                    logging.error(f"Error applying manifest: {e}")
                    continue
            
            if applied_resources:
                return True, f"Applied resources: {', '.join(applied_resources)}"
            else:
                return False, "No resources were applied"
                
        except Exception as e:
            logging.error(f"Error applying manifests: {e}")
            return False, f"Failed to apply manifests: {str(e)}"
    
    def _apply_single_manifest(self, manifest: Dict, api_version: str, kind: str, namespace: str) -> bool:
        """Apply a single Kubernetes manifest"""
        try:
            # Core resources
            if api_version == 'v1':
                if kind == 'Pod':
                    self.kube_client.v1.create_namespaced_pod(namespace=namespace, body=manifest)
                elif kind == 'Service':
                    self.kube_client.v1.create_namespaced_service(namespace=namespace, body=manifest)
                elif kind == 'ConfigMap':
                    self.kube_client.v1.create_namespaced_config_map(namespace=namespace, body=manifest)
                elif kind == 'Secret':
                    self.kube_client.v1.create_namespaced_secret(namespace=namespace, body=manifest)
                elif kind == 'ServiceAccount':
                    self.kube_client.v1.create_namespaced_service_account(namespace=namespace, body=manifest)
                elif kind == 'PersistentVolumeClaim':
                    self.kube_client.v1.create_namespaced_persistent_volume_claim(namespace=namespace, body=manifest)
                elif kind == 'Namespace':
                    self.kube_client.v1.create_namespace(body=manifest)
                else:
                    return False
            
            # Apps resources
            elif api_version == 'apps/v1':
                if kind == 'Deployment':
                    self.kube_client.apps_v1.create_namespaced_deployment(namespace=namespace, body=manifest)
                elif kind == 'StatefulSet':
                    self.kube_client.apps_v1.create_namespaced_stateful_set(namespace=namespace, body=manifest)
                elif kind == 'DaemonSet':
                    self.kube_client.apps_v1.create_namespaced_daemon_set(namespace=namespace, body=manifest)
                elif kind == 'ReplicaSet':
                    self.kube_client.apps_v1.create_namespaced_replica_set(namespace=namespace, body=manifest)
                else:
                    return False
            
            # RBAC resources
            elif api_version == 'rbac.authorization.k8s.io/v1':
                if kind == 'Role':
                    self.kube_client.rbac_v1.create_namespaced_role(namespace=namespace, body=manifest)
                elif kind == 'RoleBinding':
                    self.kube_client.rbac_v1.create_namespaced_role_binding(namespace=namespace, body=manifest)
                elif kind == 'ClusterRole':
                    self.kube_client.rbac_v1.create_cluster_role(body=manifest)
                elif kind == 'ClusterRoleBinding':
                    self.kube_client.rbac_v1.create_cluster_role_binding(body=manifest)
                else:
                    return False
            
            # Networking resources
            elif api_version == 'networking.k8s.io/v1':
                if kind == 'Ingress':
                    self.kube_client.networking_v1.create_namespaced_ingress(namespace=namespace, body=manifest)
                elif kind == 'NetworkPolicy':
                    self.kube_client.networking_v1.create_namespaced_network_policy(namespace=namespace, body=manifest)
                else:
                    return False
            
            # Batch resources
            elif api_version == 'batch/v1':
                if kind == 'Job':
                    self.kube_client.batch_v1.create_namespaced_job(namespace=namespace, body=manifest)
                else:
                    return False
            
            elif api_version == 'batch/v1beta1':
                if kind == 'CronJob':
                    # Note: CronJob API version might vary by Kubernetes version
                    self.kube_client.batch_v1.create_namespaced_cron_job(namespace=namespace, body=manifest)
                else:
                    return False
            
            else:
                # For other resources, try using the custom objects API
                try:
                    group, version = api_version.split('/')
                    self.kube_client.custom_objects_api.create_namespaced_custom_object(
                        group=group,
                        version=version,
                        namespace=namespace,
                        plural=kind.lower() + 's',  # Simple pluralization
                        body=manifest
                    )
                except Exception as e:
                    logging.error(f"Error creating custom resource {kind}: {e}")
                    return False
            
            return True
            
        except ApiException as e:
            if e.status == 409:  # Already exists
                logging.info(f"Resource {kind}/{manifest['metadata']['name']} already exists")
                return True
            else:
                logging.error(f"Error creating {kind}: {e}")
                return False
        except Exception as e:
            logging.error(f"Error applying {kind}: {e}")
            return False
    
    def _create_release_secret(self, release_name: str, namespace: str, 
                              chart_metadata: Dict, values: Dict, manifests: List[Dict]):
        """Create Helm release secret for tracking (mimics Helm 3 behavior)"""
        try:
            release_data = {
                'name': release_name,
                'info': {
                    'first_deployed': datetime.now(timezone.utc).isoformat(),
                    'last_deployed': datetime.now(timezone.utc).isoformat(),
                    'status': 'deployed',
                    'notes': f"Release {release_name} deployed successfully via Orchestrix"
                },
                'chart': chart_metadata,
                'config': values,
                'version': 1,
                'namespace': namespace
            }
            
            # Compress and encode release data (like Helm does)
            release_json = json.dumps(release_data).encode('utf-8')
            compressed_data = gzip.compress(release_json)
            encoded_data = base64.b64encode(compressed_data).decode('utf-8')
            
            # Create secret
            secret_name = f"sh.helm.release.v1.{release_name}.v1"
            secret_manifest = {
                'apiVersion': 'v1',
                'kind': 'Secret',
                'metadata': {
                    'name': secret_name,
                    'namespace': namespace,
                    'labels': {
                        'owner': 'helm',
                        'status': 'deployed',
                        'name': release_name,
                        'version': '1'
                    }
                },
                'type': 'helm.sh/release.v1',
                'data': {
                    'release': encoded_data
                }
            }
            
            self.kube_client.v1.create_namespaced_secret(
                namespace=namespace, 
                body=secret_manifest
            )
            
            logging.info(f"Created Helm release secret for {release_name}")
            
        except Exception as e:
            logging.error(f"Error creating release secret: {e}")


class HelmReleaseManager:
    """Manages Helm releases using Kubernetes API"""
    
    def __init__(self, kube_client=None):
        self.kube_client = kube_client or get_kubernetes_client()
    
    def list_releases(self, namespace: str = None) -> List[Dict]:
        """List Helm releases by reading Helm secrets"""
        try:
            releases = []
            
            # Get Helm release secrets
            if namespace and namespace != "all":
                secrets = self.kube_client.v1.list_namespaced_secret(
                    namespace=namespace,
                    field_selector="type=helm.sh/release.v1"
                )
            else:
                secrets = self.kube_client.v1.list_secret_for_all_namespaces(
                    field_selector="type=helm.sh/release.v1"
                )
            
            for secret in secrets.items:
                try:
                    release_data = self._decode_release_secret(secret)
                    if release_data:
                        releases.append(release_data)
                except Exception as e:
                    logging.error(f"Error decoding release secret {secret.metadata.name}: {e}")
                    continue
            
            return releases
            
        except Exception as e:
            logging.error(f"Error listing releases: {e}")
            return []
    
    def _decode_release_secret(self, secret) -> Optional[Dict]:
        """Decode Helm release data from secret"""
        try:
            if not secret.data or 'release' not in secret.data:
                return None
            
            # Decode and decompress release data
            encoded_data = secret.data['release']
            compressed_data = base64.b64decode(encoded_data)
            release_json = gzip.decompress(compressed_data).decode('utf-8')
            release_data = json.loads(release_json)
            
            # Extract relevant information
            return {
                'name': release_data.get('name'),
                'namespace': release_data.get('namespace'),
                'revision': release_data.get('version', 1),
                'updated': release_data.get('info', {}).get('last_deployed'),
                'status': release_data.get('info', {}).get('status'),
                'chart': release_data.get('chart', {}).get('name'),
                'app_version': release_data.get('chart', {}).get('appVersion'),
                'version': release_data.get('chart', {}).get('version')
            }
            
        except Exception as e:
            logging.error(f"Error decoding release secret: {e}")
            return None
    
    def uninstall_release(self, release_name: str, namespace: str) -> Tuple[bool, str]:
        """Uninstall a Helm release"""
        try:
            # Get resources managed by this release
            managed_resources = self._get_release_resources(release_name, namespace)
            
            # Delete resources
            deleted_resources = []
            for resource in managed_resources:
                try:
                    self._delete_resource(resource, namespace)
                    deleted_resources.append(f"{resource['kind']}/{resource['name']}")
                except Exception as e:
                    logging.error(f"Error deleting resource {resource}: {e}")
            
            # Delete Helm release secret
            try:
                secret_name = f"sh.helm.release.v1.{release_name}.v1"
                self.kube_client.v1.delete_namespaced_secret(
                    name=secret_name, 
                    namespace=namespace
                )
            except Exception as e:
                logging.error(f"Error deleting release secret: {e}")
            
            return True, f"Uninstalled release {release_name}. Deleted resources: {', '.join(deleted_resources)}"
            
        except Exception as e:
            logging.error(f"Error uninstalling release: {e}")
            return False, f"Failed to uninstall release: {str(e)}"
    
    def _get_release_resources(self, release_name: str, namespace: str) -> List[Dict]:
        """Get all resources managed by a release"""
        resources = []
        
        try:
            # Common resource types to check
            resource_checks = [
                ('v1', 'Pod', self.kube_client.v1.list_namespaced_pod),
                ('v1', 'Service', self.kube_client.v1.list_namespaced_service),
                ('v1', 'ConfigMap', self.kube_client.v1.list_namespaced_config_map),
                ('v1', 'Secret', self.kube_client.v1.list_namespaced_secret),
                ('apps/v1', 'Deployment', self.kube_client.apps_v1.list_namespaced_deployment),
                ('apps/v1', 'StatefulSet', self.kube_client.apps_v1.list_namespaced_stateful_set),
                ('apps/v1', 'DaemonSet', self.kube_client.apps_v1.list_namespaced_daemon_set),
            ]
            
            for api_version, kind, list_func in resource_checks:
                try:
                    items = list_func(
                        namespace=namespace,
                        label_selector=f"app.kubernetes.io/instance={release_name}"
                    )
                    
                    for item in items.items:
                        resources.append({
                            'apiVersion': api_version,
                            'kind': kind,
                            'name': item.metadata.name,
                            'namespace': item.metadata.namespace
                        })
                        
                except Exception as e:
                    logging.debug(f"Error listing {kind}: {e}")
                    continue
            
            return resources
            
        except Exception as e:
            logging.error(f"Error getting release resources: {e}")
            return []
    
    def _delete_resource(self, resource: Dict, namespace: str):
        """Delete a specific Kubernetes resource"""
        api_version = resource['apiVersion']
        kind = resource['kind']
        name = resource['name']
        
        if api_version == 'v1':
            if kind == 'Pod':
                self.kube_client.v1.delete_namespaced_pod(name=name, namespace=namespace)
            elif kind == 'Service':
                self.kube_client.v1.delete_namespaced_service(name=name, namespace=namespace)
            elif kind == 'ConfigMap':
                self.kube_client.v1.delete_namespaced_config_map(name=name, namespace=namespace)
            elif kind == 'Secret':
                self.kube_client.v1.delete_namespaced_secret(name=name, namespace=namespace)
        elif api_version == 'apps/v1':
            if kind == 'Deployment':
                self.kube_client.apps_v1.delete_namespaced_deployment(name=name, namespace=namespace)
            elif kind == 'StatefulSet':
                self.kube_client.apps_v1.delete_namespaced_stateful_set(name=name, namespace=namespace)
            elif kind == 'DaemonSet':
                self.kube_client.apps_v1.delete_namespaced_daemon_set(name=name, namespace=namespace)


class HelmAPIClient(QObject):
    """Main Helm API client that orchestrates all Helm operations"""
    
    # Signals for async operations
    chart_installed = pyqtSignal(bool, str)  # success, message
    release_uninstalled = pyqtSignal(bool, str)  # success, message
    releases_loaded = pyqtSignal(list)  # releases list
    repositories_updated = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, kube_client=None):
        super().__init__()
        self.kube_client = kube_client or get_kubernetes_client()
        self.installer = HelmChartInstaller(self.kube_client)
        self.release_manager = HelmReleaseManager(self.kube_client)
        self.repo_manager = HelmRepositoryManager()
    
    def install_chart_async(self, chart_name: str, release_name: str, namespace: str, **kwargs):
        """Install chart asynchronously"""
        worker = HelmInstallWorker(self.installer, chart_name, release_name, namespace, **kwargs)
        worker.finished.connect(self.chart_installed.emit)
        worker.start()
    
    def uninstall_release_async(self, release_name: str, namespace: str):
        """Uninstall release asynchronously"""
        worker = HelmUninstallWorker(self.release_manager, release_name, namespace)
        worker.finished.connect(self.release_uninstalled.emit)
        worker.start()
    
    def list_releases_async(self, namespace: str = None):
        """List releases asynchronously"""
        worker = HelmListWorker(self.release_manager, namespace)
        worker.finished.connect(self.releases_loaded.emit)
        worker.start()
    
    def get_supported_repositories(self) -> Dict[str, str]:
        """Get all supported repositories"""
        return self.repo_manager.repositories.copy()
    
    def add_repository(self, name: str, url: str) -> bool:
        """Add a custom repository"""
        return self.repo_manager.add_repository(name, url)
    
    def search_chart_in_repositories(self, chart_name: str) -> List[Tuple[str, str]]:
        """Search for a chart in all repositories"""
        return self.repo_manager.search_repositories_for_chart(chart_name)


class HelmInstallWorker(QThread):
    """Worker thread for chart installation"""
    
    finished = pyqtSignal(bool, str)
    
    def __init__(self, installer, chart_name, release_name, namespace, **kwargs):
        super().__init__()
        self.installer = installer
        self.chart_name = chart_name
        self.release_name = release_name
        self.namespace = namespace
        self.kwargs = kwargs
    
    def run(self):
        try:
            success, message = self.installer.install_chart(
                self.chart_name, self.release_name, self.namespace, **self.kwargs
            )
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, f"Installation error: {str(e)}")


class HelmUninstallWorker(QThread):
    """Worker thread for release uninstallation"""
    
    finished = pyqtSignal(bool, str)
    
    def __init__(self, release_manager, release_name, namespace):
        super().__init__()
        self.release_manager = release_manager
        self.release_name = release_name
        self.namespace = namespace
    
    def run(self):
        try:
            success, message = self.release_manager.uninstall_release(
                self.release_name, self.namespace
            )
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, f"Uninstall error: {str(e)}")


class HelmListWorker(QThread):
    """Worker thread for listing releases"""
    
    finished = pyqtSignal(list)
    
    def __init__(self, release_manager, namespace=None):
        super().__init__()
        self.release_manager = release_manager
        self.namespace = namespace
    
    def run(self):
        try:
            releases = self.release_manager.list_releases(self.namespace)
            self.finished.emit(releases)
        except Exception as e:
            logging.error(f"Error listing releases: {e}")
            self.finished.emit([])


# Singleton instance
_helm_client_instance = None

def get_helm_api_client():
    """Get or create Helm API client singleton"""
    global _helm_client_instance
    if _helm_client_instance is None:
        _helm_client_instance = HelmAPIClient()
    return _helm_client_instance