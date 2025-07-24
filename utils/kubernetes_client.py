"""
Optimized KubernetesClient with performance improvements:
- Request batching for multiple resource types
- Efficient log streaming with buffering
- Connection reuse and pooling
- Lazy API client initialization
- Optimized metrics calculation with caching
- Reduced memory footprint
"""

import os
import yaml
import time
import logging
import threading
import weakref
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import lru_cache
from typing import Optional, Dict, List, Any, Tuple

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread, QRunnable, QThreadPool
from dataclasses import dataclass
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException
from kubernetes.stream import stream

from utils.enhanced_worker import EnhancedBaseWorker
from utils.thread_manager import get_thread_manager

# Performance constants
API_TIMEOUT = 10
BATCH_REQUEST_SIZE = 50
LOG_BUFFER_SIZE = 1000
METRICS_CACHE_TTL = 10  # seconds - faster refresh for real-time data
EVENT_BATCH_SIZE = 100
MAX_CONCURRENT_REQUESTS = 5   

@dataclass
class KubeCluster:
    """Data class for Kubernetes cluster information"""
    name: str
    context: str
    kind: str = "Kubernetes Cluster"
    source: str = "local"
    label: str = "General"
    status: str = "disconnect"
    badge_color: Optional[str] = None
    server: Optional[str] = None
    user: Optional[str] = None
    namespace: Optional[str] = None
    version: Optional[str] = None


class LazyAPIClient:
    """Lazy initialization wrapper for Kubernetes API clients"""
    
    def __init__(self, api_class):
        self.api_class = api_class
        self._instance = None
        self._lock = threading.Lock()
        self._initialization_failed = False
        self._last_error = None
    
    def __getattr__(self, name):
        if self._instance is None and not self._initialization_failed:
            with self._lock:
                if self._instance is None and not self._initialization_failed:
                    try:
                        # FIXED: Add proper error handling for API client creation
                        self._instance = self.api_class()
                        logging.debug(f"Successfully initialized {self.api_class.__name__}")
                    except Exception as e:
                        self._initialization_failed = True
                        self._last_error = str(e)
                        logging.error(f"Failed to initialize {self.api_class.__name__}: {e}")
                        raise Exception(f"Failed to initialize Kubernetes API client {self.api_class.__name__}: {e}")
        
        if self._initialization_failed:
            raise Exception(f"API client initialization failed: {self._last_error}")
            
        if self._instance is None:
            raise Exception(f"API client not initialized: {self.api_class.__name__}")
            
        return getattr(self._instance, name)
    
    def reset(self):
        """Reset the cached instance"""
        with self._lock:
            self._instance = None
            self._initialization_failed = False
            self._last_error = None
            logging.debug(f"Reset {self.api_class.__name__} lazy client")


class WorkerSignals(QObject):
    """Signals for worker threads with proper lifecycle management"""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._is_valid = True
    
    def is_valid(self):
        return self._is_valid
    
    def invalidate(self):
        self._is_valid = False

class BaseWorker(QRunnable):
    """Base worker class with safe signal handling"""
    
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        
    def __del__(self):
        if hasattr(self, 'signals'):
            self.signals.invalidate()

    def safe_emit_finished(self, result):
        if hasattr(self, 'signals') and self.signals.is_valid():
            try:
                self.signals.finished.emit(result)
            except RuntimeError:
                logging.warning("Unable to emit finished signal - receiver may have been deleted")
                
    def safe_emit_error(self, error_message):
        if hasattr(self, 'signals') and self.signals.is_valid():
            try:
                self.signals.error.emit(error_message)
            except RuntimeError:
                logging.warning(f"Unable to emit error signal: {error_message}")

class KubeConfigWorker(EnhancedBaseWorker):
    def __init__(self, client_instance, config_path=None):
        super().__init__("kube_config_load")
        self.client_instance = client_instance
        self.config_path = config_path
        
    def execute(self):
        return self.client_instance.load_kube_config(self.config_path)

class KubeMetricsWorker(EnhancedBaseWorker):
    def __init__(self, client_instance, node_name=None):
        super().__init__("kube_metrics_fetch")
        self.client_instance = client_instance
        self.node_name = node_name
        
    def execute(self):
        if self.node_name:
            return self.client_instance.get_node_metrics(self.node_name)
        else:
            return self.client_instance.get_cluster_metrics()

class KubeIssuesWorker(EnhancedBaseWorker):
    def __init__(self, client_instance):
        super().__init__("kube_issues_fetch")
        self.client_instance = client_instance
        
    def execute(self):
        return self.client_instance.get_cluster_issues()
            
class ResourceDetailWorker(EnhancedBaseWorker):
    def __init__(self, client_instance, resource_type, resource_name, namespace):
        super().__init__(f"resource_detail_{resource_type}_{resource_name}")
        self.client_instance = client_instance
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace
        
    def execute(self):
        return self.client_instance.get_resource_detail(
            self.resource_type, 
            self.resource_name, 
            self.namespace
        )

class KubernetesLogStreamer(QObject):
    """Kubernetes log streamer using watch API for real-time logs"""

    log_batch_received = pyqtSignal(str, list)  # pod_name, log_lines
    # log_line_received = pyqtSignal(str, str, str)  # pod_name, log_line, timestamp
    stream_error = pyqtSignal(str, str)  # pod_name, error_message
    stream_status = pyqtSignal(str, str)  # pod_name, status_message

    def __init__(self, kube_client):
        super().__init__()
        self.kube_client = kube_client
        self.active_streams = {}
        self.log_buffers = defaultdict(lambda: deque(maxlen=1000))
        self._shutdown = False
        
        # Buffer flush timer
        self._flush_timer = QTimer()
        self._flush_timer.timeout.connect(self._flush_buffers)
        self._flush_timer.start(100)  # Flush every 100ms
    

    def start_log_stream(self, pod_name, namespace, container=None, tail_lines=200):
        """Start optimized log streaming"""
        stream_key = f"{namespace}/{pod_name}"
        if container:
            stream_key += f"/{container}"
        
        # Stop existing stream
        self.stop_log_stream(stream_key)
        
        # Create buffered stream thread
        stream_thread = LogStreamThread(
            self.kube_client,
            pod_name,
            namespace,
            container,
            tail_lines,
            self.log_buffers[stream_key]
        )
        
        self.active_streams[stream_key] = stream_thread
        stream_thread.start()
        
        self.stream_status.emit(pod_name, "Starting log stream...")
    
    def stop_log_stream(self, stream_key):
        """Stop a log stream and flush buffer"""
        if stream_key in self.active_streams:
            self.active_streams[stream_key].stop()
            self.active_streams[stream_key].wait(1000)
            del self.active_streams[stream_key]
        
        # Flush remaining logs
        if stream_key in self.log_buffers:
            self._flush_buffer(stream_key)
            del self.log_buffers[stream_key]
    
    def _flush_buffers(self):
        """Flush all log buffers"""
        for stream_key in list(self.log_buffers.keys()):
            self._flush_buffer(stream_key)
    
    def _flush_buffer(self, stream_key):
        """Flush a specific buffer"""
        buffer = self.log_buffers[stream_key]
        if not buffer:
            return
        
        # Extract pod name from stream key
        parts = stream_key.split('/')
        pod_name = parts[1] if len(parts) > 1 else stream_key
        
        # Emit batch of logs
        log_batch = []
        while buffer and len(log_batch) < LOG_BUFFER_SIZE:
            log_batch.append(buffer.popleft())
        
        if log_batch:
            self.log_batch_received.emit(pod_name, log_batch)
    

    def stop_all_streams(self):
        """Stop all active log streams"""
        self._shutdown = True
        for stream_key in list(self.active_streams.keys()):
            self.stop_log_stream(stream_key)

    def cleanup(self):
        """Cleanup all streams"""
        self._shutdown = True
        self._flush_timer.stop()
        
        for stream_key in list(self.active_streams.keys()):
            self.stop_log_stream(stream_key)

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_all_streams()


class LogStreamThread(QThread):
    """Thread for streaming logs from Kubernetes API"""


    def __init__(self, kube_client, pod_name, namespace, container, tail_lines, buffer):
        super().__init__()
        self.kube_client = kube_client
        self.pod_name = pod_name
        self.namespace = namespace
        self.container = container
        self.tail_lines = tail_lines
        self.buffer = buffer
        self._stop_requested = False
    
    def stop(self):
        self._stop_requested = True
    
    def run(self):
        """Stream logs with buffering"""
        try:
            # Get initial logs
            if self.tail_lines > 0:
                self._fetch_initial_logs()
            
            # Stream live logs
            if not self._stop_requested:
                self._stream_live_logs()
                
        except Exception as e:
            logging.error(f"Log streaming error for {self.pod_name}: {e}")
    
    def _fetch_initial_logs(self):
        """Fetch initial logs efficiently"""
        try:
            kwargs = {
                'name': self.pod_name,
                'namespace': self.namespace,
                'timestamps': True,
                'tail_lines': self.tail_lines
            }
            
            if self.container:
                kwargs['container'] = self.container
            
            logs = self.kube_client.v1.read_namespaced_pod_log(**kwargs)
            
            if logs:
                for line in logs.strip().split('\n'):
                    if self._stop_requested:
                        break
                    if line.strip():
                        timestamp, content = self._parse_log_line(line)
                        self.buffer.append({
                            'timestamp': timestamp,
                            'content': content
                        })
                        
        except Exception as e:
            logging.error(f"Error fetching initial logs: {e}")
    
    def _stream_live_logs(self):
        """Stream live logs with watch API"""
        try:
            w = watch.Watch()
            
            kwargs = {
                'name': self.pod_name,
                'namespace': self.namespace,
                'follow': True,
                'timestamps': True,
                '_preload_content': False
            }
            
            if self.container:
                kwargs['container'] = self.container
            
            for event in w.stream(self.kube_client.v1.read_namespaced_pod_log, **kwargs):
                if self._stop_requested:
                    w.stop()
                    break
                
                if isinstance(event, str) and event.strip():
                    timestamp, content = self._parse_log_line(event)
                    self.buffer.append({
                        'timestamp': timestamp,
                        'content': content
                    })
                    
        except Exception as e:
            if not self._stop_requested:
                logging.error(f"Error streaming logs: {e}")
    
    def _parse_log_line(self, log_line):
        """Parse log line efficiently"""
        try:
            if ' ' in log_line and log_line.startswith('20'):
                parts = log_line.split(' ', 1)
                if len(parts) == 2:
                    timestamp = parts[0].split('T')[1].split('.')[0][:8]
                    return timestamp, parts[1]
            return datetime.now().strftime("%H:%M:%S"), log_line
        except:
            return datetime.now().strftime("%H:%M:%S"), log_line

class ResourceBatcher:
    """Batches multiple resource requests for efficiency"""
    
    def __init__(self, kube_client):
        self.kube_client = kube_client
        self._request_queue = defaultdict(list)
        self._lock = threading.Lock()
    
    def queue_request(self, resource_type, namespace=None):
        """Queue a resource request"""
        with self._lock:
            key = (resource_type, namespace)
            self._request_queue[key].append(time.time())
    
    def process_batch(self):
        """Process queued requests in batch"""
        with self._lock:
            if not self._request_queue:
                return {}
            
            results = {}
            
            # Group by resource type
            for (resource_type, namespace), _ in self._request_queue.items():
                try:
                    if resource_type == "pods":
                        results[resource_type] = self._batch_get_pods(namespace)
                    elif resource_type == "services":
                        results[resource_type] = self._batch_get_services(namespace)
                    # Add other resource types as needed
                except Exception as e:
                    logging.error(f"Error batch loading {resource_type}: {e}")
            
            self._request_queue.clear()
            return results
    
    def _batch_get_pods(self, namespace):
        """Get pods with minimal API calls"""
        if namespace:
            return self.kube_client.v1.list_namespaced_pod(
                namespace=namespace,
                limit=BATCH_REQUEST_SIZE
            ).items
        else:
            return self.kube_client.v1.list_pod_for_all_namespaces(
                limit=BATCH_REQUEST_SIZE
            ).items
    
    def _batch_get_services(self, namespace):
        """Get services with minimal API calls"""
        if namespace:
            return self.kube_client.v1.list_namespaced_service(
                namespace=namespace,
                limit=BATCH_REQUEST_SIZE
            ).items
        else:
            return self.kube_client.v1.list_service_for_all_namespaces(
                limit=BATCH_REQUEST_SIZE
            ).items


class KubernetesPodSSH(QObject):
    """SSH-like connection to Kubernetes pods using exec API"""

    # Signals for SSH session
    data_received = pyqtSignal(str)  # Data from pod
    error_occurred = pyqtSignal(str)  # Error messages
    session_status = pyqtSignal(str)  # Status updates
    session_closed = pyqtSignal()    # Session ended

    def __init__(self, pod_name, namespace, container=None, shell="/bin/bash"):
        super().__init__()
        self.pod_name = pod_name
        self.namespace = namespace
        self.container = container
        self.shell = shell
        self.kube_client = get_kubernetes_client()
        self.exec_stream = None
        self.is_connected = False
        self._stop_requested = False

    def connect_to_pod(self):
        """Establish SSH-like connection to pod"""
        try:
            if not self.kube_client or not self.kube_client.v1:
                self.error_occurred.emit("Kubernetes client not available")
                return False

            self.session_status.emit(f"Connecting to {self.pod_name}...")

            # Determine available shells and container
            available_container, available_shell = self._detect_container_and_shell()
            if not available_container:
                self.error_occurred.emit("No suitable container found in pod")
                return False

            self.container = available_container
            self.shell = available_shell

            # Create exec command
            exec_command = [self.shell]

            # Create the exec session
            self.exec_stream = stream(
                self.kube_client.v1.connect_get_namespaced_pod_exec,
                name=self.pod_name,
                namespace=self.namespace,
                container=self.container,
                command=exec_command,
                stderr=True,
                stdin=True,
                stdout=True,
                tty=True,
                _preload_content=False
            )

            self.is_connected = True
            self.session_status.emit(f"🟢 Connected to {self.pod_name} ({self.container})")

            # Start listening for data
            self._start_reading_thread()

            return True

        except ApiException as e:
            error_msg = f"API error: {e.reason}"
            self.error_occurred.emit(error_msg)
            return False
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            self.error_occurred.emit(error_msg)
            return False

    def _detect_container_and_shell(self):
        """Detect the best container and shell to use"""
        try:
            # Get pod details
            pod = self.kube_client.v1.read_namespaced_pod(
                name=self.pod_name,
                namespace=self.namespace
            )

            # If container specified, use it; otherwise use first container
            target_container = self.container
            if not target_container and pod.spec.containers:
                target_container = pod.spec.containers[0].name

            # Try to detect available shell by checking common paths
            shells_to_try = ["/bin/bash", "/bin/sh", "/bin/ash", "/usr/bin/bash"]

            for shell in shells_to_try:
                try:
                    # Test if shell exists using a simple exec
                    test_stream = stream(
                        self.kube_client.v1.connect_get_namespaced_pod_exec,
                        name=self.pod_name,
                        namespace=self.namespace,
                        container=target_container,
                        command=["test", "-f", shell],
                        stderr=True,
                        stdin=False,
                        stdout=True,
                        tty=False
                    )
                    # If no exception, shell exists
                    return target_container, shell
                except:
                    continue

            # Fallback to /bin/sh which should exist in most containers
            return target_container, "/bin/sh"

        except Exception as e:
            logging.error(f"Error detecting container and shell: {e}")
            return None, "/bin/sh"

    def _start_reading_thread(self):
        """Start thread to read data from exec stream"""
        self.read_thread = SSHReadThread(self.exec_stream, self)
        self.read_thread.data_received.connect(self.data_received.emit)
        self.read_thread.error_occurred.connect(self.error_occurred.emit)
        self.read_thread.session_ended.connect(self._handle_session_end)
        self.read_thread.start()

    def send_command(self, command):
        """Send command to the pod"""
        try:
            if not self.is_connected or not self.exec_stream:
                return False

            # Add newline if not present
            if not command.endswith('\n'):
                command += '\n'

            self.exec_stream.write_stdin(command)
            return True

        except Exception as e:
            self.error_occurred.emit(f"Error sending command: {str(e)}")
            return False

    def send_signal(self, signal="SIGINT"):
        """Send signal to the running process (Ctrl+C, etc.)"""
        try:
            if signal == "SIGINT":
                # Send Ctrl+C
                self.exec_stream.write_stdin('\x03')
            elif signal == "SIGTERM":
                # Send Ctrl+D (EOF)
                self.exec_stream.write_stdin('\x04')
            return True
        except Exception as e:
            self.error_occurred.emit(f"Error sending signal: {str(e)}")
            return False

    def resize_terminal(self, rows, cols):
        """Resize the terminal (if supported)"""
        try:
            # Note: Terminal resizing in Kubernetes exec is limited
            # This is a placeholder for future enhancement
            pass
        except Exception as e:
            logging.error(f"Error resizing terminal: {e}")

    def disconnect(self):
        """Disconnect from the pod"""
        try:
            self._stop_requested = True
            self.is_connected = False

            if hasattr(self, 'read_thread') and self.read_thread.isRunning():
                self.read_thread.stop()
                self.read_thread.wait(2000)
                if self.read_thread.isRunning():
                    self.read_thread.terminate()
            if self.exec_stream:
                try:
                    self.exec_stream.close()
                except:
                    pass
                self.exec_stream = None

            self.session_closed.emit()

        except Exception as e:
            logging.error(f"Error disconnecting SSH session: {e}")

    def _handle_session_end(self):
        """Handle when the SSH session ends"""
        self.is_connected = False
        self.session_status.emit("🔴 Session ended")
        self.session_closed.emit()


class SSHReadThread(QThread):
    """Thread for reading data from SSH exec stream"""

    data_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    session_ended = pyqtSignal()

    def __init__(self, exec_stream, ssh_session):
        super().__init__()
        self.exec_stream = exec_stream
        self.ssh_session = ssh_session
        self._stop_requested = False

    def stop(self):
        """Stop the reading thread"""
        self._stop_requested = True

    def run(self):
        """Read data from the exec stream"""
        try:
            while not self._stop_requested and self.ssh_session.is_connected:
                try:
                    # Read from stdout/stderr
                    if self.exec_stream.is_open():
                        output = self.exec_stream.read_stdout(timeout=1)
                        if output:
                            self.data_received.emit(output)

                        error_output = self.exec_stream.read_stderr(timeout=1)
                        if error_output:
                            self.data_received.emit(error_output)
                    else:
                        # Stream closed
                        break

                except Exception as e:
                    if not self._stop_requested:
                        self.error_occurred.emit(f"Read error: {str(e)}")
                    break

            if not self._stop_requested:
                self.session_ended.emit()

        except Exception as e:
            if not self._stop_requested:
                self.error_occurred.emit(f"SSH read thread error: {str(e)}")

class ResourceUpdateWorker(EnhancedBaseWorker):
    def __init__(self, client_instance, resource_type, resource_name, namespace, yaml_data):
        super().__init__(f"resource_update_{resource_type}_{resource_name}")
        self.client_instance = client_instance
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace
        self.yaml_data = yaml_data

    def execute(self):
        return self.client_instance.update_resource(
            self.resource_type,
            self.resource_name,
            self.namespace,
            self.yaml_data
        )

class KubernetesClient(QObject):
    """Client for interacting with Kubernetes clusters using Python kubernetes library"""
    # Signals
    clusters_loaded = pyqtSignal(list)
    cluster_info_loaded = pyqtSignal(dict)
    cluster_metrics_updated = pyqtSignal(dict)
    cluster_issues_updated = pyqtSignal(list)
    resource_detail_loaded = pyqtSignal(dict)
    resource_updated = pyqtSignal(dict)
    pod_logs_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.clusters = []
        self.current_cluster = None
        self._default_kubeconfig = os.path.expanduser("~/.kube/config")
        
        # Lazy initialization of API clients
        self._api_clients = {}
        self._init_lazy_clients()

        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(8)  # Set appropriate thread count
        
        # Resource batcher
        self.resource_batcher = ResourceBatcher(self)
        
        # Optimized log streamer
        self.log_streamer = KubernetesLogStreamer(self)
        
        # Caching with size limits
        self._metrics_cache = {}
        self._metrics_cache_time = {}
        self._issues_cache = {}
        self._issues_cache_time = {}
        self.MAX_CACHE_ENTRIES = 50  # Limit cache size
        
        # Thread management
        self.thread_manager = get_thread_manager()
        self._active_workers = weakref.WeakSet()
        
        # Polling timers
        self._setup_timers()
        
        self._shutting_down = False

    def _init_lazy_clients(self):
        """Initialize lazy API clients"""
        self.v1 = LazyAPIClient(client.CoreV1Api)
        self.apps_v1 = LazyAPIClient(client.AppsV1Api)
        self.networking_v1 = LazyAPIClient(client.NetworkingV1Api)
        self.storage_v1 = LazyAPIClient(client.StorageV1Api)
        self.rbac_v1 = LazyAPIClient(client.RbacAuthorizationV1Api)
        self.batch_v1 = LazyAPIClient(client.BatchV1Api)
        self.autoscaling_v1 = LazyAPIClient(client.AutoscalingV1Api)
        self.custom_objects_api = LazyAPIClient(client.CustomObjectsApi)
        self.version_api = LazyAPIClient(client.VersionApi)

    def _setup_timers(self):
        """Setup polling timers"""
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self.refresh_metrics)
        
        self.issues_timer = QTimer(self)
        self.issues_timer.timeout.connect(self.refresh_issues)
    
    def __del__(self):
        """Clean up resources when object is deleted"""
        try:
            self._shutting_down = True
            
            logging.info("Starting KubernetesClient cleanup...")
            
            # Stop all timers
            self.stop_all_timers()
            
            # Stop all workers  
            self.stop_all_workers()
            
            # Wait for threadpool to finish
            if hasattr(self, 'threadpool'):
                self.threadpool.waitForDone(500)
                self.threadpool.clear()
                
            logging.info("KubernetesClient cleanup completed")
                
        except Exception as e:
            logging.error(f"Error during KubernetesClient cleanup: {str(e)}")

        
    def stop_all_timers(self):
        """Stop all timers safely"""
        try:
            timers = ['metrics_timer', 'issues_timer']
            for timer_name in timers:
                if hasattr(self, timer_name):
                    timer = getattr(self, timer_name)
                    if hasattr(timer, 'isActive') and timer.isActive():
                        timer.stop()
                        timer.deleteLater()
        except Exception as e:
            logging.error(f"Error stopping kubernetes client timers: {e}")

    def stop_all_workers(self):
        """Stop all active workers safely"""
        try:
            workers_to_stop = list(self._active_workers) if hasattr(self, '_active_workers') else []
            
            for worker in workers_to_stop:
                try:
                    if hasattr(worker, 'stop'):
                        worker.stop()
                    if hasattr(worker, 'signals'):
                        worker.signals.invalidate()
                except Exception as e:
                    logging.error(f"Error stopping kubernetes worker: {e}")
                    
        except Exception as e:
            logging.error(f"Error in stop_all_workers: {e}")

    def start_pod_log_stream(self, pod_name, namespace="default", container=None, tail_lines=200, follow=True):
        """Start streaming logs for a pod"""
        try:
            if self._shutting_down:
                return
            
            self.log_streamer.start_log_stream(pod_name, namespace, container, tail_lines, follow)
            
        except Exception as e:
            logging.error(f"Error starting pod log stream: {e}")
            self.error_occurred.emit(f"Failed to start log stream: {str(e)}")

    def stop_pod_log_stream(self, pod_name, namespace="default", container=None):
        """Stop streaming logs for a pod"""
        try:
            stream_key = f"{namespace}/{pod_name}"
            if container:
                stream_key += f"/{container}"
            
            self.log_streamer.stop_log_stream(stream_key)
            
        except Exception as e:
            logging.error(f"Error stopping pod log stream: {e}")

    def handle_log_line_received(self, pod_name, log_line, timestamp):
        """Handle received log line from stream"""
        try:
            if not self._shutting_down:
                # Emit signal with log data
                self.pod_log_line_received.emit({
                    'pod_name': pod_name,
                    'log_line': log_line,
                    'timestamp': timestamp
                })
        except Exception as e:
            logging.error(f"Error handling log line: {e}")

    def handle_stream_error(self, pod_name, error_message):
        """Handle streaming errors"""
        try:
            if not self._shutting_down:
                logging.error(f"Log stream error for {pod_name}: {error_message}")
                self.pod_log_stream_error.emit({
                    'pod_name': pod_name,
                    'error': error_message
                })
        except Exception as e:
            logging.error(f"Error handling stream error: {e}")

    def handle_stream_status(self, pod_name, status_message):
        """Handle streaming status updates"""
        try:
            if not self._shutting_down:
                self.pod_log_stream_status.emit({
                    'pod_name': pod_name,
                    'status': status_message
                })
        except Exception as e:
            logging.error(f"Error handling stream status: {e}")

    def force_shutdown(self):
        """Enhanced force shutdown that includes log streams"""
        try:
            logging.info("KubernetesClient force shutdown initiated...")
            
            self._shutting_down = True
            
            # Stop log streams first
            if hasattr(self, 'log_streamer'):
                self.log_streamer.stop_all_streams()
            
            # Disconnect all signals
            self.disconnect_all_signals()
            
            # Stop everything else
            self.stop_all_timers()
            self.stop_all_workers()
            
            # Clear data
            self.clusters.clear()
            self.current_cluster = None
            
            logging.info("KubernetesClient force shutdown completed")
            
        except Exception as e:
            logging.error(f"Error in kubernetes client force_shutdown: {e}")


    def force_shutdown(self):
        """Enhanced force shutdown that includes log streams"""
        try:
            logging.info("KubernetesClient force shutdown initiated...")

            self._shutting_down = True

            # Stop log streams first
            if hasattr(self, 'log_streamer'):
                self.log_streamer.stop_all_streams()

            # Disconnect all signals
            self.disconnect_all_signals()

            # Stop everything else
            self.stop_all_timers()
            self.stop_all_workers()

            # Clear data
            self.clusters.clear()
            self.current_cluster = None

            logging.info("KubernetesClient force shutdown completed")

        except Exception as e:
            logging.error(f"Error in kubernetes client force_shutdown: {e}")

    def disconnect_all_signals(self):
        """Disconnect all signals to prevent emission to deleted objects"""
        try:
            signals_to_disconnect = [
                'clusters_loaded', 'cluster_info_loaded', 'cluster_metrics_updated',
                'node_metrics_updated', 'cluster_issues_updated', 'resource_detail_loaded',
                'pod_logs_loaded', 'pod_log_line_received', 'pod_log_stream_error',
                'pod_log_stream_status', 'error_occurred'
            ]

            for signal_name in signals_to_disconnect:
                try:
                    signal = getattr(self, signal_name, None)
                    if signal:
                        signal.disconnect()
                except (TypeError, RuntimeError, AttributeError):
                    pass

        except Exception as e:
            logging.error(f"Error disconnecting kubernetes client signals: {e}")


    def _initialize_api_clients(self):
        """Initialize Kubernetes API clients with caching"""
        try:
            # Use cached clients if available and context hasn't changed
            if hasattr(self, '_cached_clients') and hasattr(self, '_cached_context'):
                if self._cached_context == self.current_cluster:
                    logging.debug("Using cached API clients")
                    return True
            
            # Initialize clients
            logging.debug("Initializing fresh API clients")
            
            # Core API
            self.v1 = client.CoreV1Api()

            # Apps API
            self.apps_v1 = client.AppsV1Api()

            # Admission Registration API
            self.admissionregistration_v1 = client.AdmissionregistrationV1Api()

            # Extensions API (for some legacy resources)
            try:
                self.extensions_v1beta1 = client.ExtensionsV1beta1Api()
            except:
                pass  # Not available in newer versions

            # Networking API
            self.networking_v1 = client.NetworkingV1Api()

            # Storage API
            self.storage_v1 = client.StorageV1Api()

            # RBAC API
            self.rbac_v1 = client.RbacAuthorizationV1Api()

            # Batch API
            self.batch_v1 = client.BatchV1Api()

            # Batch V1Beta1 API (for older CronJobs)
            try:
                self.batch_v1beta1 = client.BatchV1beta1Api()
            except:
                pass  # Not available in newer versions

            # Autoscaling API
            self.autoscaling_v1 = client.AutoscalingV1Api()

            # Autoscaling V2 API (for newer HPA features)
            try:
                self.autoscaling_v2 = client.AutoscalingV2Api()
            except:
                pass  # Not available in older versions

            # Custom Objects API
            self.custom_objects_api = client.CustomObjectsApi()

            # Version API
            self.version_api = client.VersionApi()

            # API Extensions API (for CRDs)
            self.api_extensions_v1 = client.ApiextensionsV1Api()

            # Events API (separate from core events in newer versions)
            try:
                self.events_v1 = client.EventsV1Api()
            except:
                pass  # Fallback to core events

            # Policy API (for PodDisruptionBudgets, PodSecurityPolicies)
            try:
                self.policy_v1 = client.PolicyV1Api()
            except:
                pass

            # Coordination API (for Leases)
            try:
                self.coordination_v1 = client.CoordinationV1Api()
            except:
                pass

            # Node API (for RuntimeClasses)
            try:
                self.node_v1 = client.NodeV1Api()
            except:
                pass

            # Scheduling API (for PriorityClasses)
            try:
                self.scheduling_v1 = client.SchedulingV1Api()
            except:
                pass

            # Cache the clients and context
            self._cached_clients = True
            self._cached_context = self.current_cluster
            logging.debug(f"Cached API clients for context: {self.current_cluster}")

            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to initialize API clients: {str(e)}")
            return False

    def start_metrics_polling(self, interval_ms=5000):
        """Start polling for metrics updates"""
        if not self._shutting_down:
            self.metrics_timer.start(interval_ms)
    
    def stop_metrics_polling(self):
        """Stop polling for metrics updates"""
        self.metrics_timer.stop()
    
    def start_issues_polling(self, interval_ms=10000):
        """Start polling for cluster issues"""
        if not self._shutting_down:
            self.issues_timer.start(interval_ms)
    
    def stop_issues_polling(self):
        """Stop polling for cluster issues"""
        self.issues_timer.stop()
    
    def refresh_metrics(self):
        """Refresh all metrics data"""
        if self.current_cluster and not self._shutting_down:
            self.get_cluster_metrics_async()
    
    def refresh_issues(self):
        """Refresh cluster issues data"""
        if self.current_cluster and not self._shutting_down:
            self.get_cluster_issues_async()
    
    def load_kube_config(self, config_path=None):
        """Load Kubernetes configuration from specified path or default"""
        try:
            path = config_path if config_path else self._default_kubeconfig
            
            # Check if config file exists
            if not os.path.isfile(path):
                logging.warning(f"Kubeconfig file not found: {path}")
                # Return empty list instead of raising error - allows app to continue
                return []
            
            # Load contexts using kubernetes library
            try:
                contexts, active_context = config.list_kube_config_contexts(config_file=path)
            except Exception as context_error:
                logging.error(f"Error reading kubeconfig contexts from {path}: {context_error}")
                # Return empty list for graceful degradation
                return []
            
            clusters = []
            
            for context_info in contexts:
                try:
                    context_name = context_info['name']
                    context_detail = context_info['context']
                    
                    cluster_name = context_detail.get('cluster', '')
                    user = context_detail.get('user', '')
                    namespace = context_detail.get('namespace', 'default')
                    
                    # Get server URL from cluster config
                    server = None
                    try:
                        # Load the full config to get server info
                        config_dict = config.load_kube_config_from_dict(
                            config_dict=yaml.safe_load(open(path, 'r')),
                            context=context_name,
                            persist_config=False
                        )
                        # This would require parsing the config dict, for now we'll skip server
                    except:
                        pass
                    
                    # Create cluster object
                    cluster = KubeCluster(
                        name=context_name,
                        context=context_name,
                        server=server,
                        user=user,
                        namespace=namespace
                    )
                    
                    # Check if this is the current context
                    if active_context and active_context['name'] == context_name:
                        cluster.status = "active"
                    
                    clusters.append(cluster)
                    
                except Exception as cluster_error:
                    logging.warning(f"Error processing cluster context {context_info.get('name', 'unknown')}: {cluster_error}")
                    continue
            
            self.clusters = clusters
            return clusters
            
        except Exception as e:
            logging.error(f"Error loading kubeconfig: {str(e)}")
            # Return empty list instead of raising error - allows graceful fallback
            return []
    
    
    def load_clusters_async(self, config_path=None):
        if self._shutting_down:
            return
            
        worker = KubeConfigWorker(self, config_path)
        worker.signals.finished.connect(lambda result: self.clusters_loaded.emit(result))
        worker.signals.error.connect(lambda error: self.error_occurred.emit(error))
        
        thread_manager = get_thread_manager()
        thread_manager.submit_worker("kube_config_load", worker)

    def switch_context(self, context_name: str) -> bool:
        """Switch to a specific Kubernetes context"""
        try:
            logging.info(f"Switching to Kubernetes context: {context_name}")
            
            # FIXED: Load configuration with better error handling
            try:
                config.load_kube_config(context=context_name)
            except Exception as e:
                logging.error(f"Failed to load kubeconfig for context {context_name}: {e}")
                return False
            
            # FIXED: Reset lazy clients with error handling
            lazy_clients = ['v1', 'apps_v1', 'networking_v1', 'storage_v1', 
                        'rbac_v1', 'batch_v1', 'autoscaling_v1', 'custom_objects_api', 
                        'version_api']
            
            for client_attr in lazy_clients:
                if hasattr(self, client_attr):
                    try:
                        getattr(self, client_attr).reset()
                        logging.debug(f"Reset {client_attr} client")
                    except Exception as e:
                        logging.warning(f"Error resetting {client_attr}: {e}")
            
            self.current_cluster = context_name
            
            # FIXED: Test connection immediately after switching
            try:
                # Try to access a simple API to verify connection
                version_info = self.version_api.get_code()
                logging.info(f"Successfully connected to cluster {context_name}, version: {version_info.git_version}")
            except Exception as e:
                logging.error(f"Failed to verify connection to {context_name}: {e}")
                self.error_occurred.emit(f"Failed to verify connection: {str(e)}")
                return False
            
            # Update cluster status
            for cluster in self.clusters:
                cluster.status = "active" if cluster.name == context_name else "disconnect"
            
            return True
            
        except Exception as e:
            logging.error(f"Error switching context to {context_name}: {e}")
            self.error_occurred.emit(f"Failed to switch context: {str(e)}")
            return False
    

    def get_cluster_info(self, cluster_name):
        """Get detailed information about a specific cluster"""
        try:
            # Switch to the cluster context
            if not self.switch_context(cluster_name):
                return None
            
            # Get cluster version
            try:
                version_info = self.version_api.get_code()
                version = f"{version_info.major}.{version_info.minor}"
            except Exception as e:
                logging.warning(f"Could not get cluster version: {e}")
                version = "Unknown"
            
            # Get nodes
            nodes = self._get_nodes()
            
            # Get namespaces
            namespaces = self._get_namespaces()
            
            # Get resource counts
            pods_count = self._get_resource_count("pods")
            services_count = self._get_resource_count("services")
            deployments_count = self._get_resource_count("deployments")
            
            # Find the cluster in our list
            cluster = next((c for c in self.clusters if c.name == cluster_name), None)
            if not cluster:
                self.error_occurred.emit(f"Cluster not found: {cluster_name}")
                return None
            
            info = {
                "name": cluster.name,
                "context": cluster.context,
                "server": cluster.server,
                "user": cluster.user,
                "namespace": cluster.namespace,
                "nodes": nodes,
                "version": version,
                "namespaces": namespaces,
                "pods_count": pods_count,
                "services_count": services_count,
                "deployments_count": deployments_count,
            }
            
            # Update cluster status
            for c in self.clusters:
                if c.name == cluster_name:
                    c.status = "available"
            
            if not self._shutting_down:
                self.cluster_info_loaded.emit(info)
            
            # Start polling for metrics and issues after connecting
            self.start_metrics_polling()
            self.start_issues_polling()
            
            return info
            
        except Exception as e:
            self.error_occurred.emit(f"Error getting cluster info: {str(e)}")
            return None
    
    def get_cluster_metrics_async(self):
        if self._shutting_down:
            return
            
        worker = KubeMetricsWorker(self)
        worker.signals.finished.connect(
            lambda result: self.cluster_metrics_updated.emit(result) if result and not self._shutting_down else None
        )
        worker.signals.error.connect(
            lambda error: self.error_occurred.emit(error) if not self._shutting_down else None
        )
        
        thread_manager = get_thread_manager()
        thread_manager.submit_worker("kube_metrics_fetch", worker)

    def get_cluster_issues_async(self):
        """Get cluster issues asynchronously with shutdown check"""
        if self._shutting_down:
            return
            
        # Additional check - verify threadpool is still valid
        if not hasattr(self, 'threadpool') or not self.threadpool:
            return
            
        try:
            worker = KubeIssuesWorker(self)
            
            worker.signals.finished.connect(
                lambda result: self.cluster_issues_updated.emit(result) if result is not None and not self._shutting_down else None
            )
            worker.signals.error.connect(
                lambda error: self.error_occurred.emit(error) if not self._shutting_down else None
            )
            
            self._active_workers.add(worker)
            
            def cleanup_worker(result=None):
                if worker in self._active_workers:
                    self._active_workers.remove(worker)
            
            worker.signals.finished.connect(cleanup_worker)
            worker.signals.error.connect(lambda _: cleanup_worker())
            
            self.threadpool.start(worker)
        except Exception as e:
            if not self._shutting_down:
                logging.error(f"Error starting issues worker: {e}")


    def get_resource_detail(self, resource_type, resource_name, namespace="default"):
        """Get detailed information about a specific Kubernetes resource"""
        try:
            resource_data = None

            # Special handling for CRDs clicked from the definitions list
            if resource_type.lower() in ["definitions", "customresourcedefinition", "customresourcedefinitions", "crd"]:
                resource_type = "customresourcedefinition"
                namespace = None  # CRDs are cluster-scoped

            resource_type = resource_type.strip().lower()

            # Handle common plural/singular issues
            if resource_type == "networkpolicie":
                resource_type = "networkpolicies"
            elif resource_type == "customresourcedefintion":  # common typo
                resource_type = "customresourcedefinition"
            elif resource_type == "validatingwebhookconfiguraton":  # common typo
                resource_type = "validatingwebhookconfiguration"

            resource_type_lower = resource_type.lower()

            # Ensure API clients are initialized (using cached version if available)
            if not hasattr(self, '_cached_clients') or not self._cached_clients:
                logging.debug("Initializing API clients for resource detail fetch")
                self._initialize_api_clients()

            # Core V1 API resources
            if resource_type_lower in ["pod", "pods"]:
                if namespace:
                    resource_data = self.v1.read_namespaced_pod(name=resource_name, namespace=namespace)
                else:
                    resource_data = self.v1.read_pod(name=resource_name)

            elif resource_type_lower in ["service", "services", "svc"]:
                resource_data = self.v1.read_namespaced_service(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["configmap", "configmaps", "cm"]:
                resource_data = self.v1.read_namespaced_config_map(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["secret", "secrets"]:
                resource_data = self.v1.read_namespaced_secret(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["node", "nodes"]:
                resource_data = self.v1.read_node(name=resource_name)

            elif resource_type_lower in ["namespace", "namespaces", "ns"]:
                resource_data = self.v1.read_namespace(name=resource_name)

            elif resource_type_lower in ["endpoint", "endpoints", "ep"]:
                resource_data = self.v1.read_namespaced_endpoints(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["persistentvolume", "persistentvolumes", "pv"]:
                resource_data = self.v1.read_persistent_volume(name=resource_name)

            elif resource_type_lower in ["persistentvolumeclaim", "persistentvolumeclaims", "pvc"]:
                resource_data = self.v1.read_namespaced_persistent_volume_claim(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["serviceaccount", "serviceaccounts", "sa"]:
                resource_data = self.v1.read_namespaced_service_account(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["event", "events"]:
                resource_data = self.v1.read_namespaced_event(name=resource_name, namespace=namespace)

            # Apps V1 API resources
            elif resource_type_lower in ["deployment", "deployments", "deploy"]:
                resource_data = self.apps_v1.read_namespaced_deployment(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["replicaset", "replicasets", "rs"]:
                resource_data = self.apps_v1.read_namespaced_replica_set(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["daemonset", "daemonsets", "ds"]:
                resource_data = self.apps_v1.read_namespaced_daemon_set(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["statefulset", "statefulsets", "sts"]:
                resource_data = self.apps_v1.read_namespaced_stateful_set(name=resource_name, namespace=namespace)

            # Batch V1 API resources
            elif resource_type_lower in ["job", "jobs"]:
                resource_data = self.batch_v1.read_namespaced_job(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["cronjob", "cronjobs", "cj"]:
                try:
                    # Try batch/v1 first (Kubernetes 1.21+)
                    batch_v1_api = client.BatchV1Api()
                    resource_data = batch_v1_api.read_namespaced_cron_job(name=resource_name, namespace=namespace)
                except:
                    # Fallback to batch/v1beta1 (older versions)
                    try:
                        batch_v1beta1_api = client.BatchV1beta1Api()
                        resource_data = batch_v1beta1_api.read_namespaced_cron_job(name=resource_name, namespace=namespace)
                    except Exception as e:
                        raise Exception(f"CronJob not found in batch/v1 or batch/v1beta1: {str(e)}")

            # Networking V1 API resources - FIXED: Added the missing networkpolicies handling
            elif resource_type_lower in ["ingress", "ingresses", "ing"]:
                resource_data = self.networking_v1.read_namespaced_ingress(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["networkpolicy", "networkpolicies", "netpol"]:
                resource_data = self.networking_v1.read_namespaced_network_policy(name=resource_name, namespace=namespace)

            # Storage V1 API resources
            elif resource_type_lower in ["storageclass", "storageclasses", "sc"]:
                resource_data = self.storage_v1.read_storage_class(name=resource_name)

            # RBAC V1 API resources
            elif resource_type_lower in ["role", "roles"]:
                resource_data = self.rbac_v1.read_namespaced_role(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["rolebinding", "rolebindings", "rb"]:
                resource_data = self.rbac_v1.read_namespaced_role_binding(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["clusterrole", "clusterroles", "cr"]:
                resource_data = self.rbac_v1.read_cluster_role(name=resource_name)

            elif resource_type_lower in ["clusterrolebinding", "clusterrolebindings", "crb"]:
                resource_data = self.rbac_v1.read_cluster_role_binding(name=resource_name)

            # Autoscaling V1 API resources
            elif resource_type_lower in ["horizontalpodautoscaler", "horizontalpodautoscalers", "hpa"]:
                resource_data = self.autoscaling_v1.read_namespaced_horizontal_pod_autoscaler(name=resource_name, namespace=namespace)

            # API Extensions V1 API resources - FIXED: Added the missing CustomResourceDefinition handling
            elif resource_type_lower in ["customresourcedefinition", "customresourcedefinitions", "crd"]:
                try:
                    if not hasattr(self, 'api_extensions_v1') or self.api_extensions_v1 is None:
                        self.api_extensions_v1 = client.ApiextensionsV1Api()
                    resource_data = self.api_extensions_v1.read_custom_resource_definition(name=resource_name)
                except ApiException as e:
                    if e.status == 404:
                        raise Exception(f"CustomResourceDefinition '{resource_name}' not found")
                    else:
                        raise Exception(f"Error fetching CustomResourceDefinition: {e.reason}")
                except Exception as e:
                    raise Exception(f"Failed to fetch CustomResourceDefinition: {str(e)}")

            # ValidatingWebhookConfiguration and MutatingWebhookConfiguration
            elif resource_type_lower in ["validatingwebhookconfiguration", "validatingwebhookconfigurations", "vwc"]:
                try:
                    if not hasattr(self, 'admissionregistration_v1') or self.admissionregistration_v1 is None:
                        self.admissionregistration_v1 = client.AdmissionregistrationV1Api()
                    resource_data = self.admissionregistration_v1.read_validating_webhook_configuration(name=resource_name)
                except Exception as e:
                    raise Exception(f"ValidatingWebhookConfiguration not found: {str(e)}")

            elif resource_type_lower in ["mutatingwebhookconfiguration", "mutatingwebhookconfigurations", "mwc"]:
                try:
                    if not hasattr(self, 'admissionregistration_v1') or self.admissionregistration_v1 is None:
                        self.admissionregistration_v1 = client.AdmissionregistrationV1Api()
                    resource_data = self.admissionregistration_v1.read_mutating_webhook_configuration(name=resource_name)
                except Exception as e:
                    raise Exception(f"MutatingWebhookConfiguration not found: {str(e)}")

            # Add ReplicationController and IngressClass support
            elif resource_type_lower in ["replicationcontroller", "replicationcontrollers", "rc"]:
                resource_data = self.v1.read_namespaced_replication_controller(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["ingressclass", "ingressclasses", "ic"]:
                resource_data = self.networking_v1.read_ingress_class(name=resource_name)


            # Scheduling V1 API resources (PriorityClasses)
            elif resource_type_lower in ["priorityclass", "priorityclasses", "pc"]:
                try:
                    if not hasattr(self, 'scheduling_v1') or self.scheduling_v1 is None:
                        scheduling_v1_api = client.SchedulingV1Api()
                    else:
                        scheduling_v1_api = self.scheduling_v1
                    resource_data = scheduling_v1_api.read_priority_class(name=resource_name)
                except Exception as e:
                    raise Exception(f"PriorityClass not found: {str(e)}")

            # Coordination V1 API resources (Leases)
            elif resource_type_lower in ["lease", "leases"]:
                try:
                    if not hasattr(self, 'coordination_v1') or self.coordination_v1 is None:
                        coordination_v1_api = client.CoordinationV1Api()
                    else:
                        coordination_v1_api = self.coordination_v1
                    resource_data = coordination_v1_api.read_namespaced_lease(name=resource_name, namespace=namespace)
                except Exception as e:
                    raise Exception(f"Lease not found: {str(e)}")

            # Policy V1 API resources
            elif resource_type_lower in ["poddisruptionbudget", "poddisruptionbudgets", "pdb"]:
                try:
                    if not hasattr(self, 'policy_v1') or self.policy_v1 is None:
                        policy_v1_api = client.PolicyV1Api()
                    else:
                        policy_v1_api = self.policy_v1
                    resource_data = policy_v1_api.read_namespaced_pod_disruption_budget(name=resource_name, namespace=namespace)
                except Exception as e:
                    raise Exception(f"PodDisruptionBudget not found: {str(e)}")

            # Node V1 API resources (RuntimeClasses)
            elif resource_type_lower in ["runtimeclass", "runtimeclasses", "rtc"]:
                try:
                    if not hasattr(self, 'node_v1') or self.node_v1 is None:
                        node_v1_api = client.NodeV1Api()
                    else:
                        node_v1_api = self.node_v1
                    resource_data = node_v1_api.read_runtime_class(name=resource_name)
                except Exception as e:
                    raise Exception(f"RuntimeClass not found: {str(e)}")

            # Additional Core V1 resources
            elif resource_type_lower in ["limitrange", "limitranges", "limits"]:
                resource_data = self.v1.read_namespaced_limit_range(name=resource_name, namespace=namespace)

            elif resource_type_lower in ["resourcequota", "resourcequotas", "quota"]:
                resource_data = self.v1.read_namespaced_resource_quota(name=resource_name, namespace=namespace)

            # Helm resources (assuming Helm CRDs are installed)
            elif resource_type_lower in ["helmrelease", "helmreleases", "hr"]:
                try:
                    # Try common Helm operator CRDs
                    resource_data = self.custom_objects_api.get_namespaced_custom_object(
                        group="helm.cattle.io",
                        version="v1",
                        namespace=namespace,
                        plural="helmreleases",
                        name=resource_name
                    )
                except:
                    try:
                        # Try Flux Helm Controller CRD
                        resource_data = self.custom_objects_api.get_namespaced_custom_object(
                            group="helm.toolkit.fluxcd.io",
                            version="v2beta1",
                            namespace=namespace,
                            plural="helmreleases",
                            name=resource_name
                        )
                    except Exception as e:
                        raise Exception(f"HelmRelease CRD not found: {str(e)}")

            elif resource_type_lower in ["chart", "charts"]:
                try:
                    # Try Helm Chart CRD
                    resource_data = self.custom_objects_api.get_namespaced_custom_object(
                        group="helm.cattle.io",
                        version="v1",
                        namespace=namespace,
                        plural="charts",
                        name=resource_name
                    )
                except Exception as e:
                    raise Exception(f"Chart CRD not found: {str(e)}")

            # Custom Resources - Generic handling
            else:
                # Try to handle as custom resource
                # This requires the resource type to include group and version info
                # Format expected: "group/version/kind" or just the plural name
                try:
                    # First, try to list all CRDs and find a match
                    if not hasattr(self, 'api_extensions_v1') or self.api_extensions_v1 is None:
                        api_client = client.ApiextensionsV1Api()
                    else:
                        api_client = self.api_extensions_v1
                    crds = api_client.list_custom_resource_definition()

                    matching_crd = None
                    for crd in crds.items:
                        crd_spec = crd.spec
                        # Check if resource_type matches any of the CRD names
                        if (crd_spec.names.plural.lower() == resource_type_lower or
                                crd_spec.names.singular.lower() == resource_type_lower or
                                crd_spec.names.kind.lower() == resource_type_lower):
                            matching_crd = crd
                            break

                    if matching_crd:
                        crd_spec = matching_crd.spec
                        group = crd_spec.group
                        # Get the latest version
                        version = crd_spec.versions[-1].name if crd_spec.versions else "v1"
                        plural = crd_spec.names.plural

                        if crd_spec.scope == "Namespaced":
                            resource_data = self.custom_objects_api.get_namespaced_custom_object(
                                group=group,
                                version=version,
                                namespace=namespace,
                                plural=plural,
                                name=resource_name
                            )
                        else:
                            resource_data = self.custom_objects_api.get_cluster_custom_object(
                                group=group,
                                version=version,
                                plural=plural,
                                name=resource_name
                            )
                    else:
                        raise Exception(f"Unknown resource type: {resource_type}")

                except Exception as e:
                    self.error_occurred.emit(f"Unknown resource type: {resource_type}. Error: {str(e)}")
                    return {}

            if resource_data:
                # Convert to dict
                if hasattr(resource_data, 'to_dict'):
                    resource_dict = resource_data.to_dict()
                else:
                    resource_dict = client.ApiClient().sanitize_for_serialization(resource_data)

                # Add related events (only for namespaced resources)
                if namespace:  # Only get events for namespaced resources
                    events = self._get_resource_events(resource_type, resource_name, namespace)
                    resource_dict["events"] = events
                else:
                    resource_dict["events"] = []  # Cluster-scoped resources don't have namespace events

                return resource_dict
            else:
                self.error_occurred.emit(f"Failed to retrieve resource: {resource_type}/{resource_name}")
                return {}

        except ApiException as e:
            if e.status == 404:
                self.error_occurred.emit(f"Resource not found: {resource_type}/{resource_name}")
            else:
                self.error_occurred.emit(f"API error getting resource: {e}")
            return {}
        except Exception as e:
            self.error_occurred.emit(f"Error getting resource details: {str(e)}")
            return {}

    def map_resource_type_from_ui(self, clicked_resource_type, resource_name):
        """Map UI resource type to API resource type"""
        type_mapping = {
            "definitions": "customresourcedefinition",
            "agents": "customresourcedefinition",
            "apikeys": "customresourcedefinition",
            "apmservers": "customresourcedefinition",
            "beats": "customresourcedefinition",
            "bookkeeperclusters": "customresourcedefinition",
            "connectorcatalogs": "customresourcedefinition",
            "consoles": "customresourcedefinition",
            "elasticmapsservers": "customresourcedefinition",
            "elasticsearchautoscalers": "customresourcedefinition",
            "elasticsearches": "customresourcedefinition",
            "enterprisesearches": "customresourcedefinition",
            "kafkaconnects": "customresourcedefinition",
            "kibanas": "customresourcedefinition",
        }
        return type_mapping.get(clicked_resource_type.lower(), clicked_resource_type)

    def get_resource_detail_async(self, resource_type, resource_name, namespace="default"):
        """Get resource details asynchronously"""
        if self._shutting_down:
            return

        # Map resource type if needed
        mapped_type = self.map_resource_type_from_ui(resource_type, resource_name)

        # CRDs are cluster-scoped, don't use namespace
        if mapped_type.lower() in ["customresourcedefinition", "customresourcedefinitions", "crd"]:
            namespace = None

        worker = ResourceDetailWorker(self, mapped_type, resource_name, namespace)
        
        worker.signals.finished.connect(
            lambda result: self.resource_detail_loaded.emit(result) if result and not self._shutting_down else None
        )
        worker.signals.error.connect(
            lambda error: self.error_occurred.emit(error) if not self._shutting_down else None
        )
        
        self._active_workers.add(worker)
        
        def cleanup_worker(result=None):
            if worker in self._active_workers:
                self._active_workers.remove(worker)
        
        worker.signals.finished.connect(cleanup_worker)
        worker.signals.error.connect(lambda _: cleanup_worker())
        
        self.threadpool.start(worker)

    def validate_kubernetes_schema(self, yaml_data):
        """Validate Kubernetes resource schema"""
        try:
            if not isinstance(yaml_data, dict):
                return False, "YAML must be a valid Kubernetes resource object"

            required_fields = ['apiVersion', 'kind', 'metadata']
            missing_fields = [field for field in required_fields if field not in yaml_data]

            if missing_fields:
                return False, f"Missing required fields: {', '.join(missing_fields)}"

            metadata = yaml_data.get('metadata', {})
            if 'name' not in metadata:
                return False, "metadata.name is required"

            return True, "Validation successful"

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def update_resource_async(self, resource_type, resource_name, namespace, yaml_data):
        """Update a Kubernetes resource asynchronously"""
        if self._shutting_down:
            return

        worker = ResourceUpdateWorker(self, resource_type, resource_name, namespace, yaml_data)

        worker.signals.finished.connect(
            lambda result: self.resource_updated.emit(result) if not self._shutting_down else None
        )
        worker.signals.error.connect(
            lambda error: self.resource_updated.emit({
                'success': False,
                'message': error
            }) if not self._shutting_down else None
        )

        thread_manager = get_thread_manager()
        thread_manager.submit_worker(f"resource_update_{resource_type}_{resource_name}", worker)

    def update_resource(self, resource_type, resource_name, namespace, yaml_data):
        """Update a Kubernetes resource"""
        try:
            resource_type_lower = resource_type.lower()

            if resource_type_lower in ["deployment", "deployments", "deploy"]:
                result = self.apps_v1.patch_namespaced_deployment(
                    name=resource_name,
                    namespace=namespace,
                    body=yaml_data
                )
            elif resource_type_lower in ["service", "services", "svc"]:
                result = self.v1.patch_namespaced_service(
                    name=resource_name,
                    namespace=namespace,
                    body=yaml_data
                )
            elif resource_type_lower in ["pod", "pods"]:
                result = self.v1.patch_namespaced_pod(
                    name=resource_name,
                    namespace=namespace,
                    body=yaml_data
                )
            else:
                return {"success": False, "message": f"Resource type '{resource_type}' update not supported"}

            return {"success": True, "message": f"Successfully updated {resource_type}/{resource_name}"}

        except ApiException as e:
            return {"success": False, "message": f"Kubernetes API error: {e.reason}"}
        except Exception as e:
            return {"success": False, "message": f"Update failed: {str(e)}"}

    def _get_resource_events(self, resource_type, resource_name, namespace="default"):
        """Get events related to a specific resource"""
        try:
            events = []
            
            # Always use a valid namespace, default to "default" if none provided
            if not namespace or namespace == "":
                namespace = "default"
            
            # Try to get events from the specified namespace
            try:
                events_list = self.v1.list_namespaced_event(namespace=namespace)
            except ApiException as api_e:
                # If namespace doesn't exist or no permission, try default namespace
                if api_e.status == 404 and namespace != "default":
                    logging.debug(f"Namespace '{namespace}' not found, trying default namespace")
                    events_list = self.v1.list_namespaced_event(namespace="default")
                else:
                    # If still failing, log and return empty
                    logging.debug(f"Could not access events in namespace '{namespace}': {api_e.reason}")
                    return []
            
            # Filter events for the specific resource
            for event in events_list.items:
                if (event.involved_object and 
                    event.involved_object.name == resource_name and
                    event.involved_object.kind.lower() == resource_type.lower()):
                    
                    age = self._format_age(event.metadata.creation_timestamp) if event.metadata.creation_timestamp else "Unknown"
                    
                    event_info = {
                        "type": event.type or "Normal",
                        "reason": event.reason or "Unknown",
                        "message": event.message or "No message",
                        "age": age,
                        "count": event.count or 1,
                        "source": event.source.component if event.source else "Unknown"
                    }
                    events.append(event_info)
            
            return events
                
        except ApiException as e:
            # Handle 404 errors gracefully - resource might not have events
            if e.status == 404:
                logging.debug(f"No events found for resource {resource_type}/{resource_name} in namespace {namespace}")
                return []
            else:
                logging.warning(f"API error getting resource events: {e.status} - {e.reason}")
                return []
        except Exception as e:
            logging.warning(f"Error getting resource events: {str(e)}")
            return []
    
    def _get_nodes(self):
        """Get cluster nodes"""
        try:
            nodes_list = self.v1.list_node()
            nodes = []
            
            for node in nodes_list.items:
                node_name = node.metadata.name
                status = "Unknown"
                
                # Check node conditions
                if node.status and node.status.conditions:
                    for condition in node.status.conditions:
                        if condition.type == "Ready":
                            status = "Ready" if condition.status == "True" else "NotReady"
                            break
                
                # Get node roles
                roles = []
                if node.metadata.labels:
                    for label, value in node.metadata.labels.items():
                        if label.startswith("node-role.kubernetes.io/"):
                            role = label.split("/")[1]
                            roles.append(role)
                
                # Get node version
                kubelet_version = "Unknown"
                if node.status and node.status.node_info:
                    kubelet_version = node.status.node_info.kubelet_version
                
                # Calculate node age
                age = self._format_age(node.metadata.creation_timestamp) if node.metadata.creation_timestamp else "Unknown"
                
                nodes.append({
                    "name": node_name,
                    "status": status,
                    "roles": roles,
                    "version": kubelet_version,
                    "age": age
                })
            
            return nodes
        except Exception as e:
            logging.warning(f"Error getting nodes: {e}")
            return []
    
    def _get_namespaces(self):
        """Get cluster namespaces"""
        try:
            namespaces_list = self.v1.list_namespace()
            return [ns.metadata.name for ns in namespaces_list.items]
        except Exception as e:
            logging.warning(f"Error getting namespaces: {e}")
            return []
    
    def _get_resource_count(self, resource_type):
        """Get count of resources of specified type"""
        try:
            if resource_type == "pods":
                items = self.v1.list_pod_for_all_namespaces()
            elif resource_type == "services":
                items = self.v1.list_service_for_all_namespaces()
            elif resource_type == "deployments":
                items = self.apps_v1.list_deployment_for_all_namespaces()
            else:
                return 0
            
            return len(items.items)
        except Exception as e:
            logging.warning(f"Error getting {resource_type} count: {e}")
            return 0
    
    def _generate_metrics_history(self, metric_key, points, current_value):
        """Generate historical data points for metrics visualization"""
        import random
        
        history = []
        base_value = current_value
        
        for i in range(points):
            variation = random.uniform(-5, 5)
            value = max(0, min(100, base_value + variation))
            
            if value > 95:
                value = random.uniform(85, 95)
            elif value < 5:
                value = random.uniform(5, 15)
            
            history.append(round(value, 2))
            base_value = value
        
        return history
    
    def _calculate_cluster_metrics(self):
        """Calculate cluster metrics efficiently with real data"""
        try:
            # Get nodes with their actual resource information
            nodes_list = self.v1.list_node()
            
            # Initialize totals
            cpu_total_cores = 0
            memory_total_bytes = 0
            pods_capacity_total = 0
            cpu_allocatable_cores = 0
            memory_allocatable_bytes = 0
            
            for node in nodes_list.items:
                if node.status and node.status.capacity:
                    # CPU capacity and allocatable
                    cpu_capacity = self._parse_cpu_value(node.status.capacity.get('cpu', '0'))
                    cpu_total_cores += cpu_capacity
                    
                    if node.status.allocatable:
                        cpu_allocatable = self._parse_cpu_value(node.status.allocatable.get('cpu', '0'))
                        cpu_allocatable_cores += cpu_allocatable
                    else:
                        cpu_allocatable_cores += cpu_capacity
                    
                    # Memory capacity and allocatable
                    memory_capacity = self._parse_memory_value(node.status.capacity.get('memory', '0Ki'))
                    memory_total_bytes += memory_capacity
                    
                    if node.status.allocatable:
                        memory_allocatable = self._parse_memory_value(node.status.allocatable.get('memory', '0Ki'))
                        memory_allocatable_bytes += memory_allocatable
                    else:
                        memory_allocatable_bytes += memory_capacity
                    
                    # Pod capacity
                    pods_capacity_total += int(node.status.capacity.get('pods', '110'))
            
            # Get actual pod resource usage
            pods_list = self.v1.list_pod_for_all_namespaces()
            
            # Calculate actual resource requests and usage
            cpu_requests_total = 0
            memory_requests_total = 0
            cpu_limits_total = 0
            memory_limits_total = 0
            running_pods_count = 0
            
            for pod in pods_list.items:
                # Only count running pods
                if pod.status and pod.status.phase == "Running":
                    running_pods_count += 1
                    
                    if pod.spec and pod.spec.containers:
                        for container in pod.spec.containers:
                            if container.resources:
                                # CPU requests
                                if container.resources.requests:
                                    cpu_request = container.resources.requests.get('cpu', '0')
                                    cpu_requests_total += self._parse_cpu_value(cpu_request)
                                    
                                    memory_request = container.resources.requests.get('memory', '0')
                                    memory_requests_total += self._parse_memory_value(memory_request)
                                
                                # CPU limits
                                if container.resources.limits:
                                    cpu_limit = container.resources.limits.get('cpu', '0')
                                    cpu_limits_total += self._parse_cpu_value(cpu_limit)
                                    
                                    memory_limit = container.resources.limits.get('memory', '0')
                                    memory_limits_total += self._parse_memory_value(memory_limit)
            
            # Calculate usage percentages based on requests vs capacity
            cpu_usage_percent = (cpu_requests_total / cpu_total_cores * 100) if cpu_total_cores > 0 else 0
            memory_usage_percent = (memory_requests_total / memory_total_bytes * 100) if memory_total_bytes > 0 else 0
            pods_usage_percent = (running_pods_count / pods_capacity_total * 100) if pods_capacity_total > 0 else 0
            
            # Ensure values are reasonable
            cpu_usage_percent = min(cpu_usage_percent, 100)
            memory_usage_percent = min(memory_usage_percent, 100)
            pods_usage_percent = min(pods_usage_percent, 100)
            
            metrics = {
                "cpu": {
                    "usage": round(cpu_usage_percent, 2),
                    "requests": round(cpu_requests_total, 2),
                    "limits": round(cpu_limits_total, 2),
                    "allocatable": round(cpu_allocatable_cores, 2),
                    "capacity": round(cpu_total_cores, 2)
                },
                "memory": {
                    "usage": round(memory_usage_percent, 2),
                    "requests": round(memory_requests_total / (1024**2), 2),  # Convert to MB
                    "limits": round(memory_limits_total / (1024**2), 2),      # Convert to MB
                    "allocatable": round(memory_allocatable_bytes / (1024**2), 2),  # Convert to MB
                    "capacity": round(memory_total_bytes / (1024**2), 2)     # Convert to MB
                },
                "pods": {
                    "usage": round(pods_usage_percent, 2),
                    "count": running_pods_count,
                    "capacity": pods_capacity_total
                }
            }
            
            logging.info(f"Calculated real cluster metrics: CPU {cpu_usage_percent:.1f}%, Memory {memory_usage_percent:.1f}%, Pods {pods_usage_percent:.1f}%")
            return metrics
            
        except Exception as e:
            logging.error(f"Error calculating cluster metrics: {e}")
            # Return default metrics if calculation fails
            return {
                "cpu": {"usage": 0, "requests": 0, "limits": 0, "allocatable": 0, "capacity": 1},
                "memory": {"usage": 0, "requests": 0, "limits": 0, "allocatable": 0, "capacity": 1024},
                "pods": {"usage": 0, "count": 0, "capacity": 100}
            }
    
    def _parse_cpu_value(self, cpu_str):
        """Parse CPU values (cores, millicores) to cores"""
        if not cpu_str or not isinstance(cpu_str, str):
            return 0.0
        
        cpu_str = cpu_str.strip()
        
        # Handle millicores (e.g., "500m" = 0.5 cores)
        if cpu_str.endswith('m'):
            try:
                return float(cpu_str[:-1]) / 1000.0
            except ValueError:
                return 0.0
        
        # Handle cores (e.g., "2" = 2 cores)
        try:
            return float(cpu_str)
        except ValueError:
            return 0.0
    
    def _parse_memory_value(self, memory_str):
        """Parse memory values to bytes"""
        if not memory_str or not isinstance(memory_str, str):
            return 0
        
        memory_str = memory_str.strip()
        
        # Memory unit multipliers
        multipliers = {
            'Ki': 1024,
            'Mi': 1024**2,
            'Gi': 1024**3,
            'Ti': 1024**4,
            'K': 1000,
            'M': 1000**2,
            'G': 1000**3,
            'T': 1000**4
        }
        
        # Check for unit suffixes
        for suffix, multiplier in multipliers.items():
            if memory_str.endswith(suffix):
                try:
                    value = float(memory_str[:-len(suffix)])
                    return int(value * multiplier)
                except ValueError:
                    return 0
        
        # Handle plain numbers (assume bytes)
        try:
            return int(float(memory_str))
        except ValueError:
            return 0

    def get_cluster_metrics(self):
        """Get cluster metrics with improved caching and real data"""
        # Check cache first
        cache_key = self.current_cluster
        if cache_key in self._metrics_cache:
            cache_time = self._metrics_cache_time.get(cache_key, 0)
            if time.time() - cache_time < METRICS_CACHE_TTL:
                cached_metrics = self._metrics_cache[cache_key]
                logging.debug(f"Using cached metrics for {cache_key}")
                return cached_metrics
        
        try:
            # Get real metrics
            metrics = self._calculate_cluster_metrics()
            
            # Cache results
            self._metrics_cache[cache_key] = metrics
            self._metrics_cache_time[cache_key] = time.time()
            
            # Clean old cache entries
            self._cleanup_cache()
            
            if not self._shutting_down:
                logging.info(f"KubernetesClient: Emitting real metrics data: {metrics}")
                # FIXED: Ensure signal emission with error handling
                try:
                    self.cluster_metrics_updated.emit(metrics)
                    logging.info(f"KubernetesClient: Successfully emitted cluster_metrics_updated signal")
                except Exception as signal_error:
                    logging.error(f"KubernetesClient: Error emitting metrics signal: {signal_error}")
            
            return metrics
            
        except Exception as e:
            if not self._shutting_down:
                logging.error(f"Error getting real metrics: {str(e)}")
                self.error_occurred.emit(f"Error getting metrics: {str(e)}")
            return None

    def get_cluster_issues(self):
        """Get cluster issues with real data and improved filtering"""
        # Check cache
        cache_key = self.current_cluster
        if cache_key in self._issues_cache:
            cache_time = self._issues_cache_time.get(cache_key, 0)
            if time.time() - cache_time < METRICS_CACHE_TTL:
                cached_issues = self._issues_cache[cache_key]
                logging.debug(f"Using cached issues for {cache_key}")
                return cached_issues
        
        try:
            issues = []
            
            # Get events efficiently with field selector for non-normal events
            try:
                events_list = self.v1.list_event_for_all_namespaces(
                    field_selector="type!=Normal",
                    limit=EVENT_BATCH_SIZE
                )
            except Exception as e:
                logging.warning(f"Failed to get events with field selector, trying without: {e}")
                events_list = self.v1.list_event_for_all_namespaces(limit=EVENT_BATCH_SIZE)
            
            # Process events and filter for actual issues
            for event in events_list.items:
                # Skip normal events if they got through
                if event.type == "Normal":
                    continue
                
                # Filter for recent events (last 24 hours)
                if event.metadata.creation_timestamp:
                    event_time = event.metadata.creation_timestamp
                    now = datetime.now(event_time.tzinfo) if event_time.tzinfo else datetime.now()
                    age_hours = (now - event_time).total_seconds() / 3600
                    
                    # Only include events from last 24 hours
                    if age_hours > 24:
                        continue
                
                # Create issue object
                issue = {
                    "type": event.type or "Warning",
                    "reason": event.reason or "Unknown",
                    "message": (event.message or "No message")[:200],  # Truncate long messages
                    "object": f"{event.involved_object.kind}/{event.involved_object.name}" if event.involved_object else "Unknown",
                    "age": self._format_age(event.metadata.creation_timestamp) if event.metadata.creation_timestamp else "Unknown",
                    "namespace": event.metadata.namespace or "default"
                }
                
                issues.append(issue)
            
            # Sort by most recent first
            issues.sort(key=lambda x: x.get("age", ""), reverse=False)
            
            # Limit to most recent issues
            issues = issues[:50]  # Limit to 50 most recent issues
            
            # Cache results
            self._issues_cache[cache_key] = issues
            self._issues_cache_time[cache_key] = time.time()
            
            logging.info(f"KubernetesClient: Found {len(issues)} real cluster issues")
            
            if not self._shutting_down:
                # FIXED: Ensure signal emission with error handling
                try:
                    self.cluster_issues_updated.emit(issues)
                    logging.info(f"KubernetesClient: Successfully emitted cluster_issues_updated signal")
                except Exception as signal_error:
                    logging.error(f"KubernetesClient: Error emitting issues signal: {signal_error}")
            
            return issues
            
        except Exception as e:
            if not self._shutting_down:
                logging.error(f"Error getting real issues: {str(e)}")
                self.error_occurred.emit(f"Error getting issues: {str(e)}")
            return []

    @lru_cache(maxsize=128)
    def _parse_resource_value(self, value_str):
        """Parse resource values with caching"""
        if not value_str or not isinstance(value_str, str):
            return 0.0
        
        # CPU parsing
        if value_str.endswith('m'):
            return float(value_str[:-1]) / 1000
        
        # Memory parsing
        multipliers = {
            'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3,
            'K': 1000, 'M': 1000**2, 'G': 1000**3
        }
        
        for suffix, multiplier in multipliers.items():
            if value_str.endswith(suffix):
                return float(value_str[:-len(suffix)]) * multiplier
        
        try:
            return float(value_str)
        except ValueError:
            return 0.0
    
    @lru_cache(maxsize=256)
    def _format_age(self, timestamp):
        """Format age with caching"""
        if not timestamp:
            return "Unknown"
        
        try:
            if isinstance(timestamp, str):
                created = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                created = timestamp
            
            now = datetime.now(created.tzinfo or datetime.now().astimezone().tzinfo)
            diff = now - created
            
            if diff.days > 0:
                return f"{diff.days}d"
            elif diff.seconds >= 3600:
                return f"{diff.seconds // 3600}h"
            else:
                return f"{diff.seconds // 60}m"
                
        except:
            return "Unknown"
    
    def _cleanup_cache(self):
        """Clean up old cache entries"""
        current_time = time.time()
        
        # Clean metrics cache - time-based cleanup
        old_metrics = [k for k, t in self._metrics_cache_time.items() 
                      if current_time - t > 300]
        for k in old_metrics:
            self._metrics_cache.pop(k, None)
            self._metrics_cache_time.pop(k, None)
        
        # Clean metrics cache - size-based cleanup
        if len(self._metrics_cache) > self.MAX_CACHE_ENTRIES:
            # Remove oldest half of entries
            sorted_items = sorted(self._metrics_cache_time.items(), key=lambda x: x[1])
            entries_to_remove = len(sorted_items) // 2
            for key, _ in sorted_items[:entries_to_remove]:
                self._metrics_cache.pop(key, None)
                self._metrics_cache_time.pop(key, None)
        
        # Clean issues cache - time-based cleanup
        old_issues = [k for k, t in self._issues_cache_time.items() 
                     if current_time - t > 300]
        for k in old_issues:
            self._issues_cache.pop(k, None)
            self._issues_cache_time.pop(k, None)
        
        # Clean issues cache - size-based cleanup
        if len(self._issues_cache) > self.MAX_CACHE_ENTRIES:
            # Remove oldest half of entries
            sorted_items = sorted(self._issues_cache_time.items(), key=lambda x: x[1])
            entries_to_remove = len(sorted_items) // 2
            for key, _ in sorted_items[:entries_to_remove]:
                self._issues_cache.pop(key, None)
                self._issues_cache_time.pop(key, None)
    
    def cleanup(self):
        """Cleanup resources"""
        self._shutting_down = True
        
        # Stop timers
        for timer in [self.metrics_timer, self.issues_timer]:
            if timer.isActive():
                timer.stop()
        
        # Cleanup log streamer
        if hasattr(self, 'log_streamer'):
            self.log_streamer.cleanup()
        
        # Clear caches
        self._metrics_cache.clear()
        self._issues_cache.clear()
        
        # Clear LRU caches
        self._parse_resource_value.cache_clear()
        self._format_age.cache_clear()


# Singleton management
_instance = None

def get_kubernetes_client():
    """Get or create Kubernetes client singleton"""
    global _instance
    if _instance is None:
        _instance = KubernetesClient()
    return _instance

def shutdown_kubernetes_client():
    """Shutdown the kubernetes client"""
    global _instance
    if _instance is not None:
        _instance.cleanup()
        _instance = None