# """
# Enhanced Pure Python Helm client implementation with proper upgrade and rollback functionality.
# Fixes critical issues in upgrade process and adds comprehensive template processing.
# """

# import os
# import json
# import yaml
# import base64
# import requests
# import tarfile
# import tempfile
# import hashlib
# import logging
# import threading
# import time
# import subprocess
# import shutil
# import re
# import copy
# from datetime import datetime, timezone
# from typing import Dict, List, Optional, Any, Tuple
# from urllib.parse import urljoin, urlparse
# from dataclasses import dataclass, asdict
# from pathlib import Path
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from requests.adapters import HTTPAdapter
# from urllib3.util.retry import Retry

# from kubernetes import client
# from kubernetes.client.rest import ApiException


# @dataclass
# class HelmRepository:
#     """Helm repository configuration"""
#     name: str
#     url: str
#     username: Optional[str] = None
#     password: Optional[str] = None
#     insecure: bool = False


# @dataclass
# class HelmChart:
#     """Helm chart metadata"""
#     name: str
#     version: str
#     description: str
#     app_version: Optional[str] = None
#     repository: str = ""
#     repository_url: str = ""
#     icon_url: Optional[str] = None
#     keywords: List[str] = None
#     maintainers: List[Dict[str, str]] = None
#     sources: List[str] = None
#     dependencies: List[Dict[str, Any]] = None

#     def __post_init__(self):
#         if self.keywords is None:
#             self.keywords = []
#         if self.maintainers is None:
#             self.maintainers = []
#         if self.sources is None:
#             self.sources = []
#         if self.dependencies is None:
#             self.dependencies = []


# @dataclass
# class HelmRelease:
#     """Helm release information"""
#     name: str
#     namespace: str
#     chart_name: str
#     chart_version: str
#     app_version: str
#     status: str
#     revision: int
#     updated: datetime
#     notes: str = ""
#     values: Dict[str, Any] = None
#     manifest: str = ""

#     def __post_init__(self):
#         if self.values is None:
#             self.values = {}


# @dataclass
# class ReleaseRevision:
#     """Helm release revision for rollback"""
#     revision: int
#     values: Dict[str, Any]
#     manifest: str
#     chart_metadata: Dict[str, Any]
#     status: str
#     updated: datetime


# class OptimizedHelmRepositoryManager:
#     """Optimized Helm repository manager with OCI support"""
    
#     def __init__(self, config_dir: Optional[str] = None):
#         self.config_dir = config_dir or os.path.join(os.path.expanduser("~"), ".orchestrix", "helm")
#         self.repos_file = os.path.join(self.config_dir, "repositories.yaml")
#         self.cache_dir = os.path.join(self.config_dir, "cache")
        
#         # Ensure directories exist
#         os.makedirs(self.config_dir, exist_ok=True)
#         os.makedirs(self.cache_dir, exist_ok=True)
        
#         self._repositories: Dict[str, HelmRepository] = {}
#         self._cache_lock = threading.RLock()
#         self._session = None
#         self._load_repositories()
#         self._setup_session()

#     def _setup_session(self):
#         """Setup optimized HTTP session with connection pooling"""
#         self._session = requests.Session()
        
#         # Configure retry strategy
#         retry_strategy = Retry(
#             total=3,
#             backoff_factor=1,
#             status_forcelist=[429, 500, 502, 503, 504],
#         )
        
#         # Mount adapter with retry strategy and connection pooling
#         adapter = HTTPAdapter(
#             max_retries=retry_strategy,
#             pool_connections=10,
#             pool_maxsize=20
#         )
        
#         self._session.mount("http://", adapter)
#         self._session.mount("https://", adapter)
        
#         # Set default headers
#         self._session.headers.update({
#             'User-Agent': 'Orchestrix/1.0',
#             'Accept': 'application/yaml, application/json, */*',
#             'Connection': 'keep-alive'
#         })

#     def _load_repositories(self):
#         """Load repositories from configuration file"""
#         if os.path.exists(self.repos_file):
#             try:
#                 with open(self.repos_file, 'r') as f:
#                     data = yaml.safe_load(f) or {}
#                     for repo_data in data.get('repositories', []):
#                         repo = HelmRepository(**repo_data)
#                         self._repositories[repo.name] = repo
#             except Exception as e:
#                 logging.error(f"Error loading repositories: {e}")

#     def _save_repositories(self):
#         """Save repositories to configuration file"""
#         try:
#             with self._cache_lock:
#                 data = {
#                     'repositories': [asdict(repo) for repo in self._repositories.values()]
#                 }
#                 with open(self.repos_file, 'w') as f:
#                     yaml.dump(data, f, default_flow_style=False)
#         except Exception as e:
#             logging.error(f"Error saving repositories: {e}")

#     def add_repository(self, name: str, url: str, username: Optional[str] = None, 
#                     password: Optional[str] = None, insecure: bool = False):
#         """Add repository with OCI support detection"""
#         with self._cache_lock:
#             if name not in self._repositories:
#                 repo = HelmRepository(
#                     name=name, 
#                     url=url, 
#                     username=username, 
#                     password=password, 
#                     insecure=insecure
#                 )
                
#                 self._repositories[name] = repo
#                 self._save_repositories()
#                 logging.info(f"Added repository: {name}")

#     def remove_repository(self, name: str):
#         """Remove a repository"""
#         with self._cache_lock:
#             if name in self._repositories:
#                 del self._repositories[name]
#                 self._save_repositories()
#                 # Clean up cache
#                 cache_file = os.path.join(self.cache_dir, f"{name}-index.yaml")
#                 if os.path.exists(cache_file):
#                     try:
#                         os.remove(cache_file)
#                     except Exception as e:
#                         logging.warning(f"Failed to remove cache file for {name}: {e}")

#     def list_repositories(self) -> List[HelmRepository]:
#         """List all repositories"""
#         with self._cache_lock:
#             return list(self._repositories.values())

#     def get_repository(self, name: str) -> Optional[HelmRepository]:
#         """Get repository by name"""
#         with self._cache_lock:
#             return self._repositories.get(name)

#     def update_repository_index(self, repo_name: str, timeout: int = 15) -> bool:
#         """Update repository index with timeout and better error handling"""
#         repo = self._repositories.get(repo_name)
#         if not repo:
#             logging.error(f"Repository {repo_name} not found")
#             return False

#         try:
#             # Check if index is recent (less than 1 hour old)
#             cache_file = os.path.join(self.cache_dir, f"{repo_name}-index.yaml")
#             if os.path.exists(cache_file):
#                 file_age = time.time() - os.path.getmtime(cache_file)
#                 if file_age < 3600:  # 1 hour
#                     logging.debug(f"Repository {repo_name} index is recent, skipping update")
#                     return True

#             # Handle OCI repositories differently
#             if repo.url.startswith('oci://'):
#                 logging.info(f"Repository {repo_name} is OCI-based, creating synthetic index")
#                 return self._create_oci_index(repo_name, repo.url, cache_file)

#             # Construct proper index URL for traditional repositories
#             base_url = repo.url.rstrip('/')
#             index_url = f"{base_url}/index.yaml"
            
#             # Prepare authentication if needed
#             auth = None
#             if repo.username and repo.password:
#                 auth = (repo.username, repo.password)

#             # Make request with timeout
#             response = self._session.get(
#                 index_url, 
#                 auth=auth, 
#                 timeout=timeout,
#                 verify=not repo.insecure,
#                 stream=True
#             )
            
#             if response.status_code == 404:
#                 logging.error(f"Repository index not found at {index_url}")
#                 return False
            
#             response.raise_for_status()

#             # Read response in chunks to avoid memory issues with large indexes
#             content = ""
#             for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
#                 content += chunk

#             # Validate response content
#             if not content.strip():
#                 logging.error(f"Empty response from repository {repo_name}")
#                 return False

#             # Test parse the YAML to ensure it's valid
#             try:
#                 parsed_yaml = yaml.safe_load(content)
#                 if not parsed_yaml:
#                     logging.error(f"Invalid YAML structure in repository {repo_name}")
#                     return False
#             except yaml.YAMLError as e:
#                 logging.error(f"Invalid YAML in repository {repo_name} index: {e}")
#                 return False

#             # Save to cache atomically
#             temp_file = cache_file + ".tmp"
#             with open(temp_file, 'w', encoding='utf-8') as f:
#                 f.write(content)
            
#             # Atomic move
#             os.replace(temp_file, cache_file)

#             logging.info(f"Successfully updated repository {repo_name}")
#             return True

#         except requests.exceptions.Timeout:
#             logging.error(f"Timeout updating repository {repo_name}")
#             return False
#         except requests.exceptions.RequestException as e:
#             logging.error(f"Network error updating repository {repo_name}: {e}")
#             return False
#         except Exception as e:
#             logging.error(f"Unexpected error updating repository {repo_name}: {e}")
#             return False

#     def _create_oci_index(self, repo_name: str, oci_url: str, cache_file: str) -> bool:
#         """Create a synthetic index for OCI repositories"""
#         try:
#             synthetic_index = {
#                 'apiVersion': 'v1',
#                 'entries': {},
#                 'generated': datetime.now(timezone.utc).isoformat(),
#                 'serverInfo': {
#                     'contextPath': '/api/charts'
#                 }
#             }
            
#             # Save synthetic index
#             with open(cache_file, 'w', encoding='utf-8') as f:
#                 yaml.dump(synthetic_index, f, default_flow_style=False)
                
#             logging.info(f"Created synthetic index for OCI repository {repo_name}")
#             return True
            
#         except Exception as e:
#             logging.error(f"Error creating OCI index for {repo_name}: {e}")
#             return False

#     def update_all_repositories(self) -> Dict[str, bool]:
#         """Update all repository indexes with parallel processing"""
#         results = {}
        
#         # Use ThreadPoolExecutor for parallel updates with limited concurrency
#         with ThreadPoolExecutor(max_workers=3) as executor:
#             future_to_repo = {
#                 executor.submit(self.update_repository_index, repo_name): repo_name 
#                 for repo_name in self._repositories.keys()
#             }
            
#             for future in as_completed(future_to_repo, timeout=60):
#                 repo_name = future_to_repo[future]
#                 try:
#                     results[repo_name] = future.result(timeout=30)
#                 except Exception as e:
#                     logging.error(f"Failed to update repository {repo_name}: {e}")
#                     results[repo_name] = False
                    
#         return results

#     def search_charts(self, query: str = "", repo_name: Optional[str] = None) -> List[HelmChart]:
#         """Search for charts in repositories with caching"""
#         charts = []
        
#         repos_to_search = [repo_name] if repo_name else list(self._repositories.keys())
        
#         for repo in repos_to_search:
#             try:
#                 repo_charts = self._search_charts_in_repo(repo, query)
#                 charts.extend(repo_charts)
#             except Exception as e:
#                 logging.error(f"Error searching charts in repository {repo}: {e}")
        
#         return charts

#     def _search_charts_in_repo(self, repo_name: str, query: str) -> List[HelmChart]:
#         """Search charts in a specific repository with improved parsing"""
#         cache_file = os.path.join(self.cache_dir, f"{repo_name}-index.yaml")
        
#         if not os.path.exists(cache_file):
#             # Try to update repository first
#             if not self.update_repository_index(repo_name):
#                 return []

#         try:
#             # Load and parse index file efficiently
#             with open(cache_file, 'r', encoding='utf-8') as f:
#                 index_data = yaml.safe_load(f)

#             if not index_data or 'entries' not in index_data:
#                 return []

#             charts = []
#             repo = self._repositories.get(repo_name)
#             entries = index_data['entries']
            
#             # Filter charts by query first to reduce processing
#             matching_entries = {}
#             if query:
#                 query_lower = query.lower()
#                 for chart_name, versions in entries.items():
#                     if query_lower in chart_name.lower():
#                         matching_entries[chart_name] = versions
#             else:
#                 matching_entries = entries
            
#             # Process matching charts
#             for chart_name, versions in matching_entries.items():
#                 if versions:
#                     # Get latest version (first entry is typically latest)
#                     latest = versions[0]
#                     chart = HelmChart(
#                         name=latest.get('name', chart_name),
#                         version=latest.get('version', ''),
#                         description=latest.get('description', ''),
#                         app_version=latest.get('appVersion'),
#                         repository=repo_name,
#                         repository_url=repo.url if repo else '',
#                         icon_url=latest.get('icon'),
#                         keywords=latest.get('keywords', []),
#                         maintainers=latest.get('maintainers', []),
#                         sources=latest.get('sources', []),
#                         dependencies=latest.get('dependencies', [])
#                     )
#                     charts.append(chart)

#             return charts

#         except Exception as e:
#             logging.error(f"Error searching charts in repository {repo_name}: {e}")
#             return []

#     def get_chart_versions(self, repo_name: str, chart_name: str) -> List[str]:
#         """Get all versions of a specific chart"""
#         cache_file = os.path.join(self.cache_dir, f"{repo_name}-index.yaml")
        
#         if not os.path.exists(cache_file):
#             if not self.update_repository_index(repo_name):
#                 return []

#         try:
#             with open(cache_file, 'r') as f:
#                 index_data = yaml.safe_load(f)

#             versions = []
#             chart_entries = index_data.get('entries', {}).get(chart_name, [])
            
#             for entry in chart_entries:
#                 version = entry.get('version')
#                 if version:
#                     versions.append(version)

#             return versions

#         except Exception as e:
#             logging.error(f"Error getting chart versions: {e}")
#             return []

#     def download_chart(self, repo_name: str, chart_name: str, 
#                       version: str = "latest") -> Optional[str]:
#         """Download chart archive, handling both HTTP and OCI charts"""
#         repo = self._repositories.get(repo_name)
#         if not repo:
#             logging.error(f"Repository {repo_name} not found")
#             return None

#         # If the repository URL itself is OCI, try helm CLI if available
#         if repo.url.startswith('oci://'):
#             return self._try_helm_cli_pull(f"{repo.url}/{chart_name}", version, repo)

#         # For traditional repositories, parse the index file
#         cache_file = os.path.join(self.cache_dir, f"{repo_name}-index.yaml")
        
#         if not os.path.exists(cache_file):
#             if not self.update_repository_index(repo_name):
#                 logging.error(f"Failed to update index for repo '{repo_name}'.")
#                 return None

#         try:
#             with open(cache_file, 'r', encoding='utf-8') as f:
#                 index_data = yaml.safe_load(f)

#             chart_entries = index_data.get('entries', {}).get(chart_name, [])
#             if not chart_entries:
#                 logging.error(f"Chart '{chart_name}' not found in repository '{repo_name}' index.")
#                 return None

#             # Find the requested version or latest
#             chart_entry = None
#             if not version or version == "latest":
#                 chart_entry = chart_entries[0]
#             else:
#                 for entry in chart_entries:
#                     if entry.get('version') == version:
#                         chart_entry = entry
#                         break

#             if not chart_entry:
#                 logging.error(f"Version '{version}' for chart '{chart_name}' not found in repo '{repo_name}'.")
#                 return None

#             # Get download URL
#             urls = chart_entry.get('urls', [])
#             if not urls:
#                 logging.error(f"No download URL found for chart '{chart_name}' v{chart_entry.get('version')}.")
#                 return None
            
#             download_url = urls[0]

#             if download_url.startswith('oci://'):
#                 return self._try_helm_cli_pull(download_url, version, repo)
#             else:
#                 return self._download_traditional_chart(repo, download_url)
        
#         except Exception as e:
#             logging.error(f"Error processing chart download for {repo_name}/{chart_name}: {e}")
#             return None

#     def _try_helm_cli_pull(self, oci_ref: str, version: str, auth_repo: Optional[HelmRepository] = None) -> Optional[str]:
#         """Try to pull OCI chart using helm CLI if available"""
#         try:
#             if not self._is_helm_cli_available():
#                 logging.warning("Helm CLI not available for OCI chart download")
#                 return None

#             # Prepare the full OCI reference
#             full_ref = oci_ref
#             if version and version != "latest" and not full_ref.endswith(f":{version}"):
#                 full_ref = f"{oci_ref}:{version}"

#             # Create temporary directory
#             temp_dir = tempfile.mkdtemp(prefix="helm-oci-pull-")
            
#             # Build helm pull command
#             cmd = ["helm", "pull", full_ref, "--untar", "--untardir", temp_dir]
            
#             # Add authentication if available
#             if auth_repo and auth_repo.username and auth_repo.password:
#                 cmd.extend(["--username", auth_repo.username, "--password", auth_repo.password])

#             # Execute the command
#             result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
#             if result.returncode == 0:
#                 logging.info(f"Successfully pulled OCI chart: {full_ref}")
#                 return temp_dir
#             else:
#                 logging.error(f"Helm pull failed: {result.stderr}")
#                 shutil.rmtree(temp_dir, ignore_errors=True)
#                 return None

#         except Exception as e:
#             logging.error(f"Failed to pull OCI chart {oci_ref}: {e}")
#             return None

#     def _is_helm_cli_available(self) -> bool:
#         """Check if helm CLI is available"""
#         try:
#             result = subprocess.run(['helm', 'version'], 
#                                 capture_output=True, text=True, timeout=5)
#             return result.returncode == 0
#         except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
#             return False

#     def _download_traditional_chart(self, repo: HelmRepository, download_url: str) -> Optional[str]:
#         """Download chart from a traditional HTTP(S) URL"""
#         try:
#             # Make URL absolute if relative
#             if not download_url.startswith('http'):
#                 download_url = urljoin(repo.url, download_url)

#             # Prepare authentication
#             auth = None
#             if repo and repo.username and repo.password:
#                 auth = (repo.username, repo.password)

#             # Download chart archive with streaming
#             response = self._session.get(
#                 download_url, 
#                 auth=auth, 
#                 timeout=60,
#                 verify=not (repo and repo.insecure),
#                 stream=True
#             )
#             response.raise_for_status()

#             # Extract to temporary directory
#             chart_name_for_path = download_url.split('/')[-1].replace('.tgz', '')
#             temp_dir = tempfile.mkdtemp(prefix=f"helm-chart-{chart_name_for_path}-")
#             tmp_file_path = None
            
#             try:
#                 # Create temporary file
#                 tmp_file_fd, tmp_file_path = tempfile.mkstemp(suffix='.tgz', prefix=f"helm-{chart_name_for_path}-")
                
#                 # Write content to temporary file
#                 with os.fdopen(tmp_file_fd, 'wb') as tmp_file:
#                     for chunk in response.iter_content(chunk_size=8192):
#                         tmp_file.write(chunk)
#                     tmp_file.flush()
#                     os.fsync(tmp_file.fileno())
                
#                 # Extract tar.gz
#                 time.sleep(0.1)
#                 with tarfile.open(tmp_file_path, 'r:gz') as tar:
#                     # Security check: ensure all members are safe
#                     safe_members = []
#                     for member in tar.getmembers():
#                         if member.name.startswith('/') or '..' in member.name:
#                             logging.warning(f"Skipping unsafe tar member: {member.name}")
#                             continue
#                         safe_members.append(member)
                    
#                     tar.extractall(temp_dir, members=safe_members)
                
#                 return temp_dir

#             except Exception as extract_error:
#                 logging.error(f"Error extracting chart from URL {download_url}: {extract_error}")
#                 if os.path.exists(temp_dir):
#                     shutil.rmtree(temp_dir, ignore_errors=True)
#                 return None
                
#             finally:
#                 # Clean up temporary file
#                 if tmp_file_path and os.path.exists(tmp_file_path):
#                     max_retries = 5
#                     for attempt in range(max_retries):
#                         try:
#                             os.unlink(tmp_file_path)
#                             break
#                         except PermissionError:
#                             if attempt < max_retries - 1:
#                                 time.sleep(0.2 * (attempt + 1))
#                                 continue
#                             else:
#                                 logging.warning(f"Failed to delete temporary file {tmp_file_path}")

#         except Exception as e:
#             logging.error(f"Error downloading traditional chart from {download_url}: {e}")
#             return None

#     def cleanup(self):
#         """Cleanup resources"""
#         if self._session:
#             self._session.close()


# class EnhancedTemplateProcessor:
#     """Enhanced Helm template processor with support for more template functions"""
    
#     def __init__(self):
#         self.template_functions = {
#             'default': self._default_function,
#             'quote': self._quote_function,
#             'squote': self._squote_function,
#             'upper': self._upper_function,
#             'lower': self._lower_function,
#             'title': self._title_function,
#             'trim': self._trim_function,
#             'trimSuffix': self._trim_suffix_function,
#             'trimPrefix': self._trim_prefix_function,
#             'contains': self._contains_function,
#             'hasPrefix': self._has_prefix_function,
#             'hasSuffix': self._has_suffix_function,
#             'replace': self._replace_function,
#             'split': self._split_function,
#             'join': self._join_function,
#             'toString': self._to_string_function,
#             'toInt': self._to_int_function,
#             'toBool': self._to_bool_function,
#             'indent': self._indent_function,
#             'nindent': self._nindent_function,
#         }

#     def process_template(self, template: str, context: Dict[str, Any]) -> str:
#         """Enhanced template processing with support for Helm functions"""
#         try:
#             # Step 1: Replace basic variables
#             template = self._replace_basic_variables(template, context)
            
#             # Step 2: Process template functions
#             template = self._process_template_functions(template, context)
            
#             # Step 3: Handle control structures (simplified)
#             template = self._process_control_structures(template, context)
            
#             # Step 4: Clean up remaining template syntax
#             template = self._cleanup_remaining_templates(template)
            
#             return template
            
#         except Exception as e:
#             logging.error(f"Error processing template: {e}")
#             return template

#     def _replace_basic_variables(self, template: str, context: Dict[str, Any]) -> str:
#         """Replace basic template variables"""
#         release = context.get("Release", {})
#         chart = context.get("Chart", {})
#         values = context.get("Values", {})
        
#         # Replace simple variables
#         replacements = {
#             r'\{\{\s*\.Release\.Name\s*\}\}': release.get("Name", ""),
#             r'\{\{\s*\.Release\.Namespace\s*\}\}': release.get("Namespace", "default"),
#             r'\{\{\s*\.Release\.Service\s*\}\}': 'Helm',
#             r'\{\{\s*\.Chart\.Name\s*\}\}': chart.get("name", ""),
#             r'\{\{\s*\.Chart\.Version\s*\}\}': chart.get("version", "1.0.0"),
#             r'\{\{\s*\.Chart\.AppVersion\s*\}\}': chart.get("appVersion", "1.0.0"),
#         }
        
#         for pattern, replacement in replacements.items():
#             template = re.sub(pattern, str(replacement), template)
        
#         # Handle Values expressions
#         def replace_values(match):
#             path = match.group(1)
#             try:
#                 current = values
#                 for part in path.split('.'):
#                     if isinstance(current, dict) and part in current:
#                         current = current[part]
#                     else:
#                         return ""
#                 return str(current) if current is not None else ""
#             except:
#                 return ""
        
#         template = re.sub(r'\{\{\s*\.Values\.([a-zA-Z0-9\._-]+)\s*\}\}', replace_values, template)
        
#         return template

#     def _process_template_functions(self, template: str, context: Dict[str, Any]) -> str:
#         """Process template functions like | default, | quote, etc."""
#         # Pattern to match function calls: {{ .Values.something | function "arg" }}
#         function_pattern = r'\{\{\s*([^}]+?)\s*\|\s*([a-zA-Z]+)(?:\s+"([^"]*)")?\s*\}\}'
        
#         def process_function(match):
#             try:
#                 value_expr = match.group(1).strip()
#                 function_name = match.group(2)
#                 function_arg = match.group(3) if match.group(3) else ""
                
#                 # Get the value
#                 value = self._evaluate_expression(value_expr, context)
                
#                 # Apply the function
#                 if function_name in self.template_functions:
#                     result = self.template_functions[function_name](value, function_arg)
#                     return str(result)
#                 else:
#                     logging.warning(f"Unknown template function: {function_name}")
#                     return str(value)
                    
#             except Exception as e:
#                 logging.error(f"Error processing template function: {e}")
#                 return ""
        
#         return re.sub(function_pattern, process_function, template)

#     def _evaluate_expression(self, expr: str, context: Dict[str, Any]) -> Any:
#         """Evaluate a template expression like .Values.key"""
#         try:
#             if expr.startswith('.Values.'):
#                 path = expr[8:]  # Remove '.Values.'
#                 current = context.get("Values", {})
#                 for part in path.split('.'):
#                     if isinstance(current, dict) and part in current:
#                         current = current[part]
#                     else:
#                         return None
#                 return current
#             elif expr.startswith('.Release.'):
#                 path = expr[9:]  # Remove '.Release.'
#                 return context.get("Release", {}).get(path)
#             elif expr.startswith('.Chart.'):
#                 path = expr[7:]  # Remove '.Chart.'
#                 return context.get("Chart", {}).get(path)
#             else:
#                 return expr
#         except Exception:
#             return None

#     def _process_control_structures(self, template: str, context: Dict[str, Any]) -> str:
#         """Process basic control structures (simplified implementation)"""
#         # Handle simple if statements
#         if_pattern = r'\{\{\s*if\s+([^}]+)\s*\}\}(.*?)\{\{\s*end\s*\}\}'
        
#         def process_if(match):
#             try:
#                 condition = match.group(1).strip()
#                 content = match.group(2)
                
#                 # Simple condition evaluation
#                 if self._evaluate_condition(condition, context):
#                     return content
#                 else:
#                     return ""
#             except Exception:
#                 return ""
        
#         template = re.sub(if_pattern, process_if, template, flags=re.DOTALL)
        
#         return template

#     def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
#         """Evaluate a simple condition"""
#         try:
#             value = self._evaluate_expression(condition, context)
#             if value is None:
#                 return False
#             if isinstance(value, bool):
#                 return value
#             if isinstance(value, str):
#                 return len(value) > 0
#             if isinstance(value, (int, float)):
#                 return value != 0
#             if isinstance(value, (list, dict)):
#                 return len(value) > 0
#             return bool(value)
#         except Exception:
#             return False

#     def _cleanup_remaining_templates(self, template: str) -> str:
#         """Clean up any remaining template syntax"""
#         # Remove remaining control structures
#         template = re.sub(r'\{\{\s*-?\s*(if|range|define|template|include|with|block).*?\}\}', '', template)
#         template = re.sub(r'\{\{\s*-?\s*end\s*-?\s*\}\}', '', template)
#         template = re.sub(r'\{\{\s*-?\s*else\s*-?\s*\}\}', '', template)
        
#         # Remove any remaining template expressions
#         template = re.sub(r'\{\{[^}]*\}\}', '', template)
        
#         return template

#     # Template function implementations
#     def _default_function(self, value: Any, default_value: str) -> Any:
#         """Return default value if value is empty"""
#         if value is None or value == "":
#             return default_value
#         return value

#     def _quote_function(self, value: Any, _: str = "") -> str:
#         """Quote a value"""
#         return f'"{str(value)}"'

#     def _squote_function(self, value: Any, _: str = "") -> str:
#         """Single quote a value"""
#         return f"'{str(value)}'"

#     def _upper_function(self, value: Any, _: str = "") -> str:
#         """Convert to uppercase"""
#         return str(value).upper()

#     def _lower_function(self, value: Any, _: str = "") -> str:
#         """Convert to lowercase"""
#         return str(value).lower()

#     def _title_function(self, value: Any, _: str = "") -> str:
#         """Convert to title case"""
#         return str(value).title()

#     def _trim_function(self, value: Any, _: str = "") -> str:
#         """Trim whitespace"""
#         return str(value).strip()

#     def _trim_suffix_function(self, value: Any, suffix: str) -> str:
#         """Trim suffix"""
#         value_str = str(value)
#         if value_str.endswith(suffix):
#             return value_str[:-len(suffix)]
#         return value_str

#     def _trim_prefix_function(self, value: Any, prefix: str) -> str:
#         """Trim prefix"""
#         value_str = str(value)
#         if value_str.startswith(prefix):
#             return value_str[len(prefix):]
#         return value_str

#     def _contains_function(self, value: Any, substring: str) -> bool:
#         """Check if value contains substring"""
#         return substring in str(value)

#     def _has_prefix_function(self, value: Any, prefix: str) -> bool:
#         """Check if value has prefix"""
#         return str(value).startswith(prefix)

#     def _has_suffix_function(self, value: Any, suffix: str) -> bool:
#         """Check if value has suffix"""
#         return str(value).endswith(suffix)

#     def _replace_function(self, value: Any, args: str) -> str:
#         """Replace substring (simplified)"""
#         # This would need more complex parsing for multiple args
#         return str(value)

#     def _split_function(self, value: Any, delimiter: str) -> List[str]:
#         """Split string by delimiter"""
#         return str(value).split(delimiter)

#     def _join_function(self, value: Any, delimiter: str) -> str:
#         """Join list with delimiter"""
#         if isinstance(value, list):
#             return delimiter.join(str(item) for item in value)
#         return str(value)

#     def _to_string_function(self, value: Any, _: str = "") -> str:
#         """Convert to string"""
#         return str(value)

#     def _to_int_function(self, value: Any, _: str = "") -> int:
#         """Convert to int"""
#         try:
#             return int(value)
#         except (ValueError, TypeError):
#             return 0

#     def _to_bool_function(self, value: Any, _: str = "") -> bool:
#         """Convert to bool"""
#         if isinstance(value, bool):
#             return value
#         if isinstance(value, str):
#             return value.lower() in ('true', '1', 'yes', 'on')
#         return bool(value)

#     def _indent_function(self, value: Any, spaces: str) -> str:
#         """Indent text"""
#         try:
#             num_spaces = int(spaces) if spaces else 2
#             lines = str(value).split('\n')
#             indented_lines = [' ' * num_spaces + line for line in lines]
#             return '\n'.join(indented_lines)
#         except (ValueError, TypeError):
#             return str(value)

#     def _nindent_function(self, value: Any, spaces: str) -> str:
#         """Indent text with newline"""
#         return '\n' + self._indent_function(value, spaces)


# class HelmClient:
#     """Enhanced Helm client with proper upgrade, rollback, and template processing"""
    
#     def __init__(self, kube_client: Optional[client.CoreV1Api] = None):
#         self.kube_client = kube_client
#         self.repo_manager = OptimizedHelmRepositoryManager()
#         self._release_cache = {}
#         self._cache_lock = threading.RLock()
#         self.template_processor = EnhancedTemplateProcessor()
        
#     def _ensure_kube_client(self):
#         """Ensure Kubernetes client is available"""
#         if not self.kube_client:
#             raise RuntimeError("Kubernetes client not configured")

#     def _get_helm_secret_name(self, release_name: str, revision: int) -> str:
#         """Generate Helm secret name"""
#         return f"sh.helm.release.v1.{release_name}.v{revision}"

#     def get_chart_values(self, chart_path: str) -> Dict[str, Any]:
#         """Get default values from a chart"""
#         try:
#             values_yaml_path = os.path.join(chart_path, "values.yaml")
#             if os.path.exists(values_yaml_path):
#                 with open(values_yaml_path, 'r') as f:
#                     return yaml.safe_load(f) or {}
#             return {}
#         except Exception as e:
#             logging.error(f"Error loading chart values: {e}")
#             return {}
    
#     def get_chart_metadata(self, chart_path: str) -> Dict[str, Any]:
#         """Get chart metadata from Chart.yaml"""
#         try:
#             chart_yaml_path = os.path.join(chart_path, "Chart.yaml")
#             if os.path.exists(chart_yaml_path):
#                 with open(chart_yaml_path, 'r') as f:
#                     return yaml.safe_load(f) or {}
#             return {}
#         except Exception as e:
#             logging.error(f"Error loading chart metadata: {e}")
#             return {}

#     def _decode_helm_secret(self, secret_data: str) -> Dict[str, Any]:
#         """Decode Helm secret data"""
#         try:
#             import gzip
            
#             # Helm 3 secrets are base64 encoded, then gzipped, then base64 encoded again
#             decoded_data = base64.b64decode(secret_data)
            
#             # Check if data is gzipped
#             if len(decoded_data) >= 2 and decoded_data[0] == 0x1f and decoded_data[1] == 0x8b:
#                 decompressed_data = gzip.decompress(decoded_data)
#                 release_data = json.loads(decompressed_data.decode('utf-8'))
#             else:
#                 # Try as plain JSON first
#                 try:
#                     release_data = json.loads(decoded_data.decode('utf-8'))
#                 except (json.JSONDecodeError, UnicodeDecodeError):
#                     # If that fails, it might be double base64 encoded
#                     try:
#                         double_decoded = base64.b64decode(decoded_data)
#                         if len(double_decoded) >= 2 and double_decoded[0] == 0x1f and double_decoded[1] == 0x8b:
#                             decompressed_data = gzip.decompress(double_decoded)
#                             release_data = json.loads(decompressed_data.decode('utf-8'))
#                         else:
#                             release_data = json.loads(double_decoded.decode('utf-8'))
#                     except Exception:
#                         release_data = json.loads(decoded_data.decode('utf-8', errors='ignore'))
            
#             return release_data
#         except Exception as e:
#             logging.error(f"Error decoding Helm secret: {e}")
#             return {}

#     def list_releases(self, namespace: str = None, all_namespaces: bool = False) -> List[HelmRelease]:
#         """List Helm releases with caching"""
#         cache_key = f"{namespace}:{all_namespaces}"
        
#         with self._cache_lock:
#             # Check cache (5 minute expiry)
#             if cache_key in self._release_cache:
#                 cached_data, timestamp = self._release_cache[cache_key]
#                 if time.time() - timestamp < 300:  # 5 minutes
#                     return cached_data

#         self._ensure_kube_client()
        
#         releases = []
        
#         try:
#             # Get Helm secrets
#             if all_namespaces or namespace is None:
#                 secrets = self.kube_client.list_secret_for_all_namespaces(
#                     label_selector="owner=helm"
#                 )
#                 secret_items = secrets.items
#             else:
#                 secrets = self.kube_client.list_namespaced_secret(
#                     namespace=namespace,
#                     label_selector="owner=helm"
#                 )
#                 secret_items = secrets.items

#             # Group secrets by release name to get latest revision
#             release_secrets = {}
            
#             for secret in secret_items:
#                 secret_name = secret.metadata.name
                
#                 # Parse secret name: sh.helm.release.v1.{release-name}.v{revision}
#                 if secret_name.startswith("sh.helm.release.v1."):
#                     parts = secret_name.split(".")
#                     if len(parts) >= 5:
#                         release_name = ".".join(parts[3:-1])  # Handle names with dots
#                         revision_str = parts[-1].replace("v", "")
                        
#                         try:
#                             revision = int(revision_str)
#                             key = f"{secret.metadata.namespace}/{release_name}"
                            
#                             if key not in release_secrets or revision > release_secrets[key][1]:
#                                 release_secrets[key] = (secret, revision)
#                         except ValueError:
#                             continue

#             # Process latest revision of each release
#             for (secret, revision) in release_secrets.values():
#                 try:
#                     release_data_raw = secret.data.get('release')
#                     if not release_data_raw:
#                         continue

#                     release_data = self._decode_helm_secret(release_data_raw)
#                     if not release_data:
#                         continue

#                     # Extract release information
#                     info = release_data.get('info', {})
#                     chart = release_data.get('chart', {})
#                     chart_metadata = chart.get('metadata', {})
                    
#                     # Parse timestamp
#                     updated_str = info.get('last_deployed')
#                     updated = datetime.now(timezone.utc)
#                     if updated_str:
#                         try:
#                             updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
#                         except:
#                             pass

#                     # Get manifest if available
#                     manifest = release_data.get('manifest', '')

#                     release = HelmRelease(
#                         name=release_data.get('name', ''),
#                         namespace=release_data.get('namespace', secret.metadata.namespace),
#                         chart_name=chart_metadata.get('name', ''),
#                         chart_version=chart_metadata.get('version', ''),
#                         app_version=chart_metadata.get('appVersion', ''),
#                         status=info.get('status', ''),
#                         revision=revision,
#                         updated=updated,
#                         notes=info.get('notes', ''),
#                         values=release_data.get('config', {}),
#                         manifest=manifest
#                     )
                    
#                     releases.append(release)

#                 except Exception as e:
#                     logging.error(f"Error processing release secret {secret.metadata.name}: {e}")
#                     continue

#             # Update cache
#             with self._cache_lock:
#                 self._release_cache[cache_key] = (releases, time.time())

#         except ApiException as e:
#             logging.error(f"Kubernetes API error listing releases: {e}")
#         except Exception as e:
#             logging.error(f"Error listing releases: {e}")

#         return releases

#     def get_release(self, name: str, namespace: str) -> Optional[HelmRelease]:
#         """Get specific release details"""
#         releases = self.list_releases(namespace=namespace)
#         for release in releases:
#             if release.name == name and release.namespace == namespace:
#                 return release
#         return None

#     def get_release_history(self, name: str, namespace: str) -> List[ReleaseRevision]:
#         """Get release revision history for rollback"""
#         self._ensure_kube_client()
#         revisions = []
        
#         try:
#             # Get all secrets for this release
#             secrets = self.kube_client.list_namespaced_secret(
#                 namespace=namespace,
#                 label_selector=f"owner=helm,name={name}"
#             )
            
#             for secret in secrets.items:
#                 secret_name = secret.metadata.name
                
#                 # Parse revision from secret name
#                 if secret_name.startswith(f"sh.helm.release.v1.{name}.v"):
#                     try:
#                         revision_str = secret_name.split(".")[-1].replace("v", "")
#                         revision = int(revision_str)
                        
#                         release_data_raw = secret.data.get('release')
#                         if release_data_raw:
#                             release_data = self._decode_helm_secret(release_data_raw)
                            
#                             info = release_data.get('info', {})
#                             chart = release_data.get('chart', {})
                            
#                             # Parse timestamp
#                             updated_str = info.get('last_deployed')
#                             updated = datetime.now(timezone.utc)
#                             if updated_str:
#                                 try:
#                                     updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
#                                 except:
#                                     pass
                            
#                             revision_obj = ReleaseRevision(
#                                 revision=revision,
#                                 values=release_data.get('config', {}),
#                                 manifest=release_data.get('manifest', ''),
#                                 chart_metadata=chart.get('metadata', {}),
#                                 status=info.get('status', ''),
#                                 updated=updated
#                             )
                            
#                             revisions.append(revision_obj)
                            
#                     except (ValueError, KeyError) as e:
#                         logging.warning(f"Error parsing revision from secret {secret_name}: {e}")
#                         continue
                        
#         except Exception as e:
#             logging.error(f"Error getting release history: {e}")
        
#         # Sort by revision number (newest first)
#         revisions.sort(key=lambda x: x.revision, reverse=True)
#         return revisions

#     def install_release(self, release_name: str, chart_path: str, namespace: str,
#                     values: Dict[str, Any] = None, 
#                     create_namespace: bool = False,
#                     timeout: int = 300) -> bool:
#         """Install a Helm release"""
#         self._ensure_kube_client()
        
#         if values is None:
#             values = {}

#         try:
#             logging.info(f"Starting installation of release '{release_name}' from chart '{chart_path}'")
            
#             # Check if release already exists
#             existing_release = self.get_release(release_name, namespace)
#             if existing_release:
#                 logging.info(f"Release '{release_name}' already exists, performing upgrade instead")
#                 return self.upgrade_release(release_name, namespace, chart_path, values)
            
#             # Validate chart path
#             if not os.path.exists(chart_path):
#                 logging.error(f"Chart path does not exist: {chart_path}")
#                 return False
                
#             chart_yaml_path = os.path.join(chart_path, "Chart.yaml")
#             if not os.path.exists(chart_yaml_path):
#                 logging.error(f"Chart.yaml not found in {chart_path}")
#                 return False

#             # Load chart metadata
#             with open(chart_yaml_path, 'r', encoding='utf-8') as f:
#                 chart_metadata = yaml.safe_load(f)
                
#             if not chart_metadata:
#                 logging.error(f"Invalid Chart.yaml in {chart_path}")
#                 return False

#             # Load default values and merge
#             default_values = {}
#             values_yaml_path = os.path.join(chart_path, "values.yaml")
#             if os.path.exists(values_yaml_path):
#                 with open(values_yaml_path, 'r', encoding='utf-8') as f:
#                     default_values = yaml.safe_load(f) or {}

#             final_values = {**default_values, **values}

#             # Create namespace if requested
#             if create_namespace:
#                 try:
#                     namespace_obj = client.V1Namespace(
#                         metadata=client.V1ObjectMeta(name=namespace)
#                     )
#                     self.kube_client.create_namespace(body=namespace_obj)
#                     logging.info(f"Created namespace: {namespace}")
#                 except ApiException as e:
#                     if e.status != 409:  # Ignore if namespace already exists
#                         logging.error(f"Error creating namespace {namespace}: {e}")

#             # Process templates and generate manifests
#             manifests = self._render_chart_templates(chart_path, final_values, release_name, namespace)
            
#             if not manifests:
#                 logging.error("No valid manifests generated from chart templates")
#                 return False

#             # Store rendered manifest for history
#             rendered_manifest = self._manifests_to_yaml_string(manifests)

#             # Apply manifests to Kubernetes
#             applied_objects = []
#             for i, manifest in enumerate(manifests):
#                 try:
#                     applied_obj = self._apply_manifest(manifest, namespace)
#                     if applied_obj:
#                         applied_objects.append(applied_obj)
                        
#                 except Exception as e:
#                     logging.error(f"Error applying manifest {i+1}: {e}")
#                     # Rollback applied objects
#                     self._cleanup_applied_objects(applied_objects, namespace)
#                     return False

#             # Create Helm release secret
#             try:
#                 self._create_release_secret(
#                     release_name, namespace, chart_metadata, final_values, 
#                     "deployed", 1, rendered_manifest
#                 )
#             except Exception as e:
#                 logging.error(f"Error creating release secret: {e}")

#             # Clear cache
#             with self._cache_lock:
#                 keys_to_remove = [k for k in self._release_cache.keys() if namespace in k]
#                 for key in keys_to_remove:
#                     del self._release_cache[key]

#             logging.info(f"Successfully installed release '{release_name}' with {len(applied_objects)} resources")
#             return True

#         except Exception as e:
#             logging.error(f"Error installing release {release_name}: {e}")
#             return False

#     def upgrade_release(self, release_name: str, namespace: str, chart_path: str, 
#                        values: Dict[str, Any] = None, atomic: bool = True) -> bool:
#         """Proper Helm release upgrade implementation"""
#         self._ensure_kube_client()
        
#         if values is None:
#             values = {}

#         try:
#             logging.info(f"Starting upgrade of release '{release_name}'")
            
#             # Get current release
#             current_release = self.get_release(release_name, namespace)
#             if not current_release:
#                 logging.error(f"Release '{release_name}' not found")
#                 return False
            
#             # Load chart metadata
#             chart_yaml_path = os.path.join(chart_path, "Chart.yaml")
#             if not os.path.exists(chart_yaml_path):
#                 logging.error(f"Chart.yaml not found in {chart_path}")
#                 return False
                
#             with open(chart_yaml_path, 'r', encoding='utf-8') as f:
#                 new_chart_metadata = yaml.safe_load(f)
            
#             # Load default values and merge with current values
#             default_values = {}
#             values_yaml_path = os.path.join(chart_path, "values.yaml")
#             if os.path.exists(values_yaml_path):
#                 with open(values_yaml_path, 'r', encoding='utf-8') as f:
#                     default_values = yaml.safe_load(f) or {}
            
#             # Merge values: defaults -> current -> new
#             final_values = {**default_values, **current_release.values, **values}
            
#             # Calculate new revision
#             new_revision = current_release.revision + 1
            
#             # Backup current state for rollback
#             backup_data = {
#                 'release': current_release,
#                 'revision': current_release.revision,
#                 'values': current_release.values,
#                 'manifest': current_release.manifest
#             }
            
#             try:
#                 # Render new templates
#                 new_manifests = self._render_chart_templates(chart_path, final_values, release_name, namespace)
                
#                 if not new_manifests:
#                     logging.error("No valid manifests generated for upgrade")
#                     return False
                
#                 rendered_manifest = self._manifests_to_yaml_string(new_manifests)
                
#                 # Compare and apply changes
#                 upgrade_success = self._perform_upgrade_diff(
#                     current_release, new_manifests, namespace
#                 )
                
#                 if not upgrade_success:
#                     if atomic:
#                         logging.warning("Upgrade failed, performing rollback")
#                         self._rollback_to_revision(release_name, namespace, backup_data)
#                     return False
                
#                 # Update release secret with new revision
#                 self._create_release_secret(
#                     release_name, namespace, new_chart_metadata, final_values,
#                     "deployed", new_revision, rendered_manifest
#                 )
                
#                 # Clear cache
#                 with self._cache_lock:
#                     keys_to_remove = [k for k in self._release_cache.keys() if namespace in k]
#                     for key in keys_to_remove:
#                         del self._release_cache[key]
                
#                 logging.info(f"Successfully upgraded release '{release_name}' to revision {new_revision}")
#                 return True
                
#             except Exception as e:
#                 logging.error(f"Error during upgrade: {e}")
#                 if atomic:
#                     logging.warning("Upgrade failed, performing rollback")
#                     self._rollback_to_revision(release_name, namespace, backup_data)
#                 return False
            
#         except Exception as e:
#             logging.error(f"Error upgrading release {release_name}: {e}")
#             return False

#     def _perform_upgrade_diff(self, current_release: HelmRelease, 
#                              new_manifests: List[Dict[str, Any]], namespace: str) -> bool:
#         """Perform upgrade by comparing current and new manifests"""
#         try:
#             # Parse current manifest to get existing resources
#             current_resources = self._parse_manifest_to_resources(current_release.manifest)
            
#             # Create lookup for current resources
#             current_lookup = {}
#             for resource in current_resources:
#                 key = self._get_resource_key(resource)
#                 current_lookup[key] = resource
            
#             # Create lookup for new resources
#             new_lookup = {}
#             for manifest in new_manifests:
#                 key = self._get_resource_key(manifest)
#                 new_lookup[key] = manifest
            
#             # Find resources to create, update, or delete
#             to_create = []
#             to_update = []
#             to_delete = []
            
#             # Check for creates and updates
#             for key, new_resource in new_lookup.items():
#                 if key in current_lookup:
#                     # Check if resource needs update
#                     if self._resource_needs_update(current_lookup[key], new_resource):
#                         to_update.append(new_resource)
#                 else:
#                     to_create.append(new_resource)
            
#             # Check for deletes
#             for key, current_resource in current_lookup.items():
#                 if key not in new_lookup:
#                     to_delete.append(current_resource)
            
#             logging.info(f"Upgrade plan: {len(to_create)} creates, {len(to_update)} updates, {len(to_delete)} deletes")
            
#             # Apply changes in order: creates, updates, deletes
#             for resource in to_create:
#                 self._apply_manifest(resource, namespace)
                
#             for resource in to_update:
#                 self._update_manifest(resource, namespace)
                
#             for resource in to_delete:
#                 self._delete_manifest(resource, namespace)
            
#             return True
            
#         except Exception as e:
#             logging.error(f"Error performing upgrade diff: {e}")
#             return False

#     def _parse_manifest_to_resources(self, manifest_yaml: str) -> List[Dict[str, Any]]:
#         """Parse YAML manifest string to list of resources"""
#         if not manifest_yaml:
#             return []
            
#         try:
#             resources = []
#             for doc in yaml.safe_load_all(manifest_yaml):
#                 if doc and isinstance(doc, dict) and doc.get('kind'):
#                     resources.append(doc)
#             return resources
#         except Exception as e:
#             logging.error(f"Error parsing manifest: {e}")
#             return []

#     def _get_resource_key(self, resource: Dict[str, Any]) -> str:
#         """Get unique key for a Kubernetes resource"""
#         kind = resource.get('kind', '')
#         name = resource.get('metadata', {}).get('name', '')
#         namespace = resource.get('metadata', {}).get('namespace', 'default')
#         return f"{kind}/{namespace}/{name}"

#     def _resource_needs_update(self, current: Dict[str, Any], new: Dict[str, Any]) -> bool:
#         """Check if a resource needs to be updated"""
#         # Simple comparison - in production, you'd want more sophisticated diffing
#         current_spec = current.get('spec', {})
#         new_spec = new.get('spec', {})
#         return current_spec != new_spec

#     def _update_manifest(self, manifest: Dict[str, Any], namespace: str):
#         """Update an existing Kubernetes resource"""
#         try:
#             api_version = manifest.get('apiVersion', '')
#             kind = manifest.get('kind', '')
#             name = manifest.get('metadata', {}).get('name', '')
            
#             # Ensure namespace is set
#             if 'metadata' in manifest and 'namespace' not in manifest['metadata']:
#                 manifest['metadata']['namespace'] = namespace
            
#             # Core API (v1)
#             if api_version == 'v1':
#                 if kind == 'Service':
#                     self.kube_client.patch_namespaced_service(name=name, namespace=namespace, body=manifest)
#                 elif kind == 'ConfigMap':
#                     self.kube_client.patch_namespaced_config_map(name=name, namespace=namespace, body=manifest)
#                 elif kind == 'Secret':
#                     self.kube_client.patch_namespaced_secret(name=name, namespace=namespace, body=manifest)
#                 elif kind == 'ServiceAccount':
#                     self.kube_client.patch_namespaced_service_account(name=name, namespace=namespace, body=manifest)
                    
#             # Apps API (apps/v1)
#             elif api_version in ['apps/v1', 'extensions/v1beta1']:
#                 apps_api = client.AppsV1Api()
#                 if kind == 'Deployment':
#                     apps_api.patch_namespaced_deployment(name=name, namespace=namespace, body=manifest)
#                 elif kind == 'StatefulSet':
#                     apps_api.patch_namespaced_stateful_set(name=name, namespace=namespace, body=manifest)
                    
#         except ApiException as e:
#             if e.status == 404:
#                 # Resource doesn't exist, create it instead
#                 self._apply_manifest(manifest, namespace)
#             else:
#                 raise

#     def _delete_manifest(self, manifest: Dict[str, Any], namespace: str):
#         """Delete a Kubernetes resource"""
#         try:
#             api_version = manifest.get('apiVersion', '')
#             kind = manifest.get('kind', '')
#             name = manifest.get('metadata', {}).get('name', '')
            
#             # Core API (v1)
#             if api_version == 'v1':
#                 if kind == 'Service':
#                     self.kube_client.delete_namespaced_service(name=name, namespace=namespace)
#                 elif kind == 'ConfigMap':
#                     self.kube_client.delete_namespaced_config_map(name=name, namespace=namespace)
#                 elif kind == 'Secret':
#                     self.kube_client.delete_namespaced_secret(name=name, namespace=namespace)
#                 elif kind == 'ServiceAccount':
#                     self.kube_client.delete_namespaced_service_account(name=name, namespace=namespace)
                    
#             # Apps API (apps/v1)
#             elif api_version in ['apps/v1', 'extensions/v1beta1']:
#                 apps_api = client.AppsV1Api()
#                 if kind == 'Deployment':
#                     apps_api.delete_namespaced_deployment(name=name, namespace=namespace)
#                 elif kind == 'StatefulSet':
#                     apps_api.delete_namespaced_stateful_set(name=name, namespace=namespace)
                    
#         except ApiException as e:
#             if e.status == 404:
#                 logging.warning(f"Resource {kind}/{name} not found, skipping deletion")
#             else:
#                 logging.error(f"Error deleting resource {kind}/{name}: {e}")

#     def rollback_release(self, release_name: str, namespace: str, revision: int = None) -> bool:
#         """Rollback release to a previous revision"""
#         try:
#             logging.info(f"Starting rollback of release '{release_name}' to revision {revision}")
            
#             # Get release history
#             history = self.get_release_history(release_name, namespace)
#             if not history:
#                 logging.error(f"No history found for release '{release_name}'")
#                 return False
            
#             # Find target revision
#             target_revision = None
#             if revision is None:
#                 # Rollback to previous revision (second in list since first is current)
#                 if len(history) >= 2:
#                     target_revision = history[1]
#                 else:
#                     logging.error("No previous revision found for rollback")
#                     return False
#             else:
#                 for rev in history:
#                     if rev.revision == revision:
#                         target_revision = rev
#                         break
                        
#                 if target_revision is None:
#                     logging.error(f"Revision {revision} not found")
#                     return False
            
#             # Perform rollback
#             current_release = self.get_release(release_name, namespace)
#             if not current_release:
#                 logging.error(f"Current release '{release_name}' not found")
#                 return False
            
#             backup_data = {
#                 'release': current_release,
#                 'revision': current_release.revision,
#                 'values': current_release.values,
#                 'manifest': current_release.manifest
#             }
            
#             success = self._rollback_to_revision(release_name, namespace, {
#                 'revision': target_revision.revision,
#                 'values': target_revision.values,
#                 'manifest': target_revision.manifest,
#                 'chart_metadata': target_revision.chart_metadata
#             })
            
#             if success:
#                 logging.info(f"Successfully rolled back release '{release_name}' to revision {target_revision.revision}")
            
#             return success
            
#         except Exception as e:
#             logging.error(f"Error rolling back release {release_name}: {e}")
#             return False

#     def _rollback_to_revision(self, release_name: str, namespace: str, revision_data: Dict[str, Any]) -> bool:
#         """Rollback to a specific revision"""
#         try:
#             # Parse the manifest from the target revision
#             target_manifest = revision_data.get('manifest', '')
#             if not target_manifest:
#                 logging.error("No manifest found in target revision")
#                 return False
            
#             target_resources = self._parse_manifest_to_resources(target_manifest)
#             if not target_resources:
#                 logging.error("No resources found in target manifest")
#                 return False
            
#             # Get current release to compare
#             current_release = self.get_release(release_name, namespace)
#             if not current_release:
#                 logging.error(f"Current release '{release_name}' not found")
#                 return False
            
#             # Apply the rollback diff
#             success = self._perform_upgrade_diff(current_release, target_resources, namespace)
            
#             if success:
#                 # Create new release secret with incremented revision
#                 new_revision = current_release.revision + 1
#                 chart_metadata = revision_data.get('chart_metadata', {})
#                 values = revision_data.get('values', {})
                
#                 self._create_release_secret(
#                     release_name, namespace, chart_metadata, values,
#                     "deployed", new_revision, target_manifest
#                 )
                
#                 # Clear cache
#                 with self._cache_lock:
#                     keys_to_remove = [k for k in self._release_cache.keys() if namespace in k]
#                     for key in keys_to_remove:
#                         del self._release_cache[key]
            
#             return success
            
#         except Exception as e:
#             logging.error(f"Error in rollback to revision: {e}")
#             return False

#     def _render_chart_templates(self, chart_path: str, values: Dict[str, Any], 
#                             release_name: str, namespace: str) -> List[Dict[str, Any]]:
#         """Enhanced chart template rendering with better template processing"""
#         templates_dir = os.path.join(chart_path, "templates")
#         manifests = []
        
#         if not os.path.exists(templates_dir):
#             # Create fallback manifest if no templates
#             return [self._create_fallback_manifest(release_name, namespace)]

#         try:
#             # Load chart metadata
#             chart_metadata = {}
#             chart_yaml_path = os.path.join(chart_path, "Chart.yaml")
#             if os.path.exists(chart_yaml_path):
#                 with open(chart_yaml_path, 'r') as f:
#                     chart_metadata = yaml.safe_load(f) or {}

#             # Create template context
#             context = {
#                 "Release": {
#                     "Name": release_name,
#                     "Namespace": namespace,
#                     "Service": "Helm"
#                 },
#                 "Chart": chart_metadata,
#                 "Values": values
#             }

#             # Process template files
#             for root, dirs, files in os.walk(templates_dir):
#                 for file in files:
#                     if file.endswith(('.yaml', '.yml')) and not file.startswith('NOTES'):
#                         template_path = os.path.join(root, file)
                        
#                         try:
#                             with open(template_path, 'r', encoding='utf-8') as f:
#                                 template_content = f.read()

#                             if not template_content.strip():
#                                 continue

#                             # Process template with enhanced processor
#                             processed_content = self.template_processor.process_template(
#                                 template_content, context
#                             )
                            
#                             # Parse YAML documents
#                             try:
#                                 docs = list(yaml.safe_load_all(processed_content))
#                                 for doc in docs:
#                                     if doc and isinstance(doc, dict) and doc.get('kind'):
#                                         # Fix manifest structure
#                                         fixed_manifest = self._fix_manifest(doc, release_name, namespace)
#                                         if fixed_manifest:
#                                             manifests.append(fixed_manifest)
#                             except yaml.YAMLError as e:
#                                 logging.warning(f"YAML error in template {file}: {e}")
#                                 # Create fallback manifest for failed templates
#                                 manifests.append(self._create_fallback_manifest(release_name, namespace))
                                
#                         except Exception as e:
#                             logging.error(f"Error processing template {file}: {e}")
#                             continue

#             # Ensure at least one manifest exists
#             if not manifests:
#                 manifests.append(self._create_fallback_manifest(release_name, namespace))

#             return manifests

#         except Exception as e:
#             logging.error(f"Error in template rendering: {e}")
#             return [self._create_fallback_manifest(release_name, namespace)]

#     def _manifests_to_yaml_string(self, manifests: List[Dict[str, Any]]) -> str:
#         """Convert manifests list to YAML string"""
#         try:
#             yaml_parts = []
#             for manifest in manifests:
#                 yaml_str = yaml.dump(manifest, default_flow_style=False)
#                 yaml_parts.append(yaml_str)
#             return "---\n".join(yaml_parts)
#         except Exception as e:
#             logging.error(f"Error converting manifests to YAML: {e}")
#             return ""

#     def _fix_manifest(self, manifest: Dict[str, Any], release_name: str, namespace: str) -> Dict[str, Any]:
#         """Fix manifest structure and ensure validity"""
#         try:
#             # Ensure basic structure
#             if not manifest.get('apiVersion'):
#                 manifest['apiVersion'] = 'v1'
            
#             if not manifest.get('kind'):
#                 manifest['kind'] = 'ConfigMap'
            
#             # Fix metadata
#             if 'metadata' not in manifest or not isinstance(manifest['metadata'], dict):
#                 manifest['metadata'] = {}
            
#             metadata = manifest['metadata']
            
#             # Ensure valid name
#             if not metadata.get('name'):
#                 manifest_kind = manifest.get('kind', 'resource').lower()
#                 metadata['name'] = f"{release_name}-{manifest_kind}"
            
#             # Sanitize name
#             name = metadata['name']
#             if name.startswith('-') or not name:
#                 metadata['name'] = f"{release_name}-resource"
            
#             metadata['namespace'] = namespace
            
#             # Add labels
#             if 'labels' not in metadata:
#                 metadata['labels'] = {}
#             metadata['labels'].update({
#                 'app': release_name,
#                 'release': release_name,
#                 'app.kubernetes.io/managed-by': 'Helm'
#             })
            
#             return manifest
            
#         except Exception as e:
#             logging.error(f"Error fixing manifest: {e}")
#             return self._create_fallback_manifest(release_name, namespace)

#     def _create_fallback_manifest(self, release_name: str, namespace: str) -> Dict[str, Any]:
#         """Create a fallback ConfigMap manifest"""
#         return {
#             'apiVersion': 'v1',
#             'kind': 'ConfigMap',
#             'metadata': {
#                 'name': f"{release_name}-config",
#                 'namespace': namespace,
#                 'labels': {
#                     'app': release_name,
#                     'release': release_name,
#                     'app.kubernetes.io/managed-by': 'Helm'
#                 }
#             },
#             'data': {
#                 'status': 'Chart installation completed'
#             }
#         }

#     def _apply_manifest(self, manifest: Dict[str, Any], namespace: str) -> Optional[Dict[str, Any]]:
#         """Apply Kubernetes manifest"""
#         try:
#             api_version = manifest.get('apiVersion', '')
#             kind = manifest.get('kind', '')
            
#             # Ensure namespace is set for namespaced resources
#             namespaced_resources = {
#                 'Service', 'Deployment', 'ConfigMap', 'Secret', 'Pod', 'PersistentVolumeClaim',
#                 'Ingress', 'NetworkPolicy', 'ServiceAccount', 'Role', 'RoleBinding',
#                 'HorizontalPodAutoscaler', 'Job', 'CronJob', 'DaemonSet', 'StatefulSet'
#             }
            
#             if kind in namespaced_resources and 'metadata' in manifest:
#                 if 'namespace' not in manifest['metadata']:
#                     manifest['metadata']['namespace'] = namespace

#             # Core API (v1)
#             if api_version == 'v1':
#                 if kind == 'Service':
#                     return self.kube_client.create_namespaced_service(namespace=namespace, body=manifest)
#                 elif kind == 'ConfigMap':
#                     return self.kube_client.create_namespaced_config_map(namespace=namespace, body=manifest)
#                 elif kind == 'Secret':
#                     return self.kube_client.create_namespaced_secret(namespace=namespace, body=manifest)
#                 elif kind == 'ServiceAccount':
#                     return self.kube_client.create_namespaced_service_account(namespace=namespace, body=manifest)
                
#             # Apps API (apps/v1)
#             elif api_version in ['apps/v1', 'extensions/v1beta1']:
#                 apps_api = client.AppsV1Api()
#                 if kind == 'Deployment':
#                     return apps_api.create_namespaced_deployment(namespace=namespace, body=manifest)
#                 elif kind == 'StatefulSet':
#                     return apps_api.create_namespaced_stateful_set(namespace=namespace, body=manifest)
                    
#             # Other APIs can be added as needed
#             else:
#                 logging.warning(f"Unsupported resource type: {api_version}/{kind}")
#                 return None
                
#         except ApiException as e:
#             if e.status == 409:  # Already exists
#                 logging.info(f"Resource {kind}/{manifest.get('metadata', {}).get('name')} already exists")
#                 return manifest
#             else:
#                 logging.error(f"Error applying manifest {kind}: {e}")
#                 raise
#         except Exception as e:
#             logging.error(f"Unexpected error applying manifest {kind}: {e}")
#             raise

#         return None

#     def _cleanup_applied_objects(self, applied_objects: List[Dict[str, Any]], namespace: str):
#         """Clean up applied objects in case of failure"""
#         for obj in reversed(applied_objects):
#             try:
#                 # Cleanup logic would go here
#                 pass
#             except Exception as e:
#                 logging.error(f"Error cleaning up object: {e}")

#     def _create_release_secret(self, release_name: str, namespace: str, 
#                               chart_metadata: Dict[str, Any], values: Dict[str, Any], 
#                               status: str, revision: int = 1, manifest: str = ""):
#         """Create Helm release secret"""
#         release_data = {
#             'name': release_name,
#             'namespace': namespace,
#             'info': {
#                 'first_deployed': datetime.now(timezone.utc).isoformat(),
#                 'last_deployed': datetime.now(timezone.utc).isoformat(),
#                 'status': status,
#                 'notes': '',
#                 'revision': revision
#             },
#             'chart': {
#                 'metadata': chart_metadata
#             },
#             'config': values,
#             'version': revision,
#             'manifest': manifest
#         }

#         # Encode release data
#         release_json = json.dumps(release_data)
        
#         import gzip
#         compressed_data = gzip.compress(release_json.encode('utf-8'))
#         encoded_data = base64.b64encode(compressed_data).decode('utf-8')

#         secret_name = self._get_helm_secret_name(release_name, revision)
        
#         secret = client.V1Secret(
#             metadata=client.V1ObjectMeta(
#                 name=secret_name,
#                 namespace=namespace,
#                 labels={
#                     'owner': 'helm',
#                     'name': release_name,
#                     'status': status,
#                     'version': str(revision)
#                 }
#             ),
#             data={
#                 'release': encoded_data
#             }
#         )

#         self.kube_client.create_namespaced_secret(namespace=namespace, body=secret)

#     def delete_release(self, name: str, namespace: str, purge_resources: bool = True) -> bool:
#         """Delete a Helm release and optionally purge all associated resources"""
#         self._ensure_kube_client()
        
#         try:
#             logging.info(f"Starting deletion of release '{name}' in namespace '{namespace}'")
            
#             # Get release to find associated resources
#             release = self.get_release(name, namespace)
#             if not release:
#                 logging.warning(f"Release {name} not found in namespace {namespace}")
#                 return False

#             if purge_resources:
#                 # Delete associated Kubernetes resources
#                 self._delete_release_resources(name, namespace)

#             # Delete Helm secrets
#             try:
#                 secrets = self.kube_client.list_namespaced_secret(
#                     namespace=namespace,
#                     label_selector=f"owner=helm,name={name}"
#                 )
                
#                 for secret in secrets.items:
#                     try:
#                         self.kube_client.delete_namespaced_secret(
#                             name=secret.metadata.name,
#                             namespace=namespace
#                         )
#                         logging.info(f"Deleted Helm secret: {secret.metadata.name}")
#                     except Exception as e:
#                         logging.error(f"Error deleting secret {secret.metadata.name}: {e}")
                        
#             except Exception as e:
#                 logging.error(f"Error deleting Helm secrets for release {name}: {e}")

#             # Clear cache
#             with self._cache_lock:
#                 keys_to_remove = [k for k in self._release_cache.keys() if namespace in k]
#                 for key in keys_to_remove:
#                     del self._release_cache[key]

#             logging.info(f"Successfully deleted release '{name}' from namespace '{namespace}'")
#             return True

#         except Exception as e:
#             logging.error(f"Error deleting release {name}: {e}")
#             return False

#     def _delete_release_resources(self, release_name: str, namespace: str):
#         """Delete all Kubernetes resources associated with a Helm release"""
#         try:
#             # Find resources by labels
#             release_selector = f"app={release_name}"
            
#             # Delete different resource types
#             self._delete_deployments(release_name, namespace, release_selector)
#             self._delete_services(release_name, namespace, release_selector)
#             self._delete_configmaps(release_name, namespace, release_selector)
#             self._delete_secrets(release_name, namespace, release_selector)
                
#         except Exception as e:
#             logging.error(f"Error deleting release resources: {e}")

#     def _delete_deployments(self, release_name: str, namespace: str, selector: str):
#         """Delete deployments"""
#         try:
#             apps_api = client.AppsV1Api()
#             deployments = apps_api.list_namespaced_deployment(
#                 namespace=namespace,
#                 label_selector=selector
#             )
            
#             for deployment in deployments.items:
#                 try:
#                     apps_api.delete_namespaced_deployment(
#                         name=deployment.metadata.name,
#                         namespace=namespace
#                     )
#                     logging.info(f"Deleted deployment: {deployment.metadata.name}")
#                 except Exception as e:
#                     logging.error(f"Error deleting deployment {deployment.metadata.name}: {e}")
                    
#         except Exception as e:
#             logging.error(f"Error listing deployments: {e}")

#     def _delete_services(self, release_name: str, namespace: str, selector: str):
#         """Delete services"""
#         try:
#             services = self.kube_client.list_namespaced_service(
#                 namespace=namespace,
#                 label_selector=selector
#             )
            
#             for service in services.items:
#                 try:
#                     self.kube_client.delete_namespaced_service(
#                         name=service.metadata.name,
#                         namespace=namespace
#                     )
#                     logging.info(f"Deleted service: {service.metadata.name}")
#                 except Exception as e:
#                     logging.error(f"Error deleting service {service.metadata.name}: {e}")
                    
#         except Exception as e:
#             logging.error(f"Error listing services: {e}")

#     def _delete_configmaps(self, release_name: str, namespace: str, selector: str):
#         """Delete configmaps"""
#         try:
#             configmaps = self.kube_client.list_namespaced_config_map(
#                 namespace=namespace,
#                 label_selector=selector
#             )
            
#             for configmap in configmaps.items:
#                 try:
#                     self.kube_client.delete_namespaced_config_map(
#                         name=configmap.metadata.name,
#                         namespace=namespace
#                     )
#                     logging.info(f"Deleted configmap: {configmap.metadata.name}")
#                 except Exception as e:
#                     logging.error(f"Error deleting configmap {configmap.metadata.name}: {e}")
                    
#         except Exception as e:
#             logging.error(f"Error listing configmaps: {e}")

#     def _delete_secrets(self, release_name: str, namespace: str, selector: str):
#         """Delete secrets (excluding Helm secrets)"""
#         try:
#             secrets = self.kube_client.list_namespaced_secret(
#                 namespace=namespace,
#                 label_selector=selector
#             )
            
#             for secret in secrets.items:
#                 # Skip Helm secrets - they're handled separately
#                 if secret.metadata.labels and secret.metadata.labels.get('owner') == 'helm':
#                     continue
                    
#                 try:
#                     self.kube_client.delete_namespaced_secret(
#                         name=secret.metadata.name,
#                         namespace=namespace
#                     )
#                     logging.info(f"Deleted secret: {secret.metadata.name}")
#                 except Exception as e:
#                     logging.error(f"Error deleting secret {secret.metadata.name}: {e}")
                    
#         except Exception as e:
#             logging.error(f"Error listing secrets: {e}")

#     def cleanup(self):
#         """Cleanup resources"""
#         if self.repo_manager:
#             self.repo_manager.cleanup()

#     # Repository management methods (delegate to repository manager)
#     def add_repository(self, name: str, url: str, username: str = None, password: str = None):
#         """Add Helm repository"""
#         self.repo_manager.add_repository(name, url, username, password)

#     def remove_repository(self, name: str):
#         """Remove Helm repository"""
#         self.repo_manager.remove_repository(name)

#     def list_repositories(self) -> List[Dict[str, str]]:
#         """List Helm repositories"""
#         repos = self.repo_manager.list_repositories()
#         return [{'name': repo.name, 'url': repo.url} for repo in repos]

#     def update_repositories(self):
#         """Update all repository indexes"""
#         return self.repo_manager.update_all_repositories()

#     def search_charts(self, query: str = "", repo_name: str = None) -> List[HelmChart]:
#         """Search for charts"""
#         return self.repo_manager.search_charts(query, repo_name)