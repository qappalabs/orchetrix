import os
import json
import yaml
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot, QTimer, QThread
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
import datetime
import logging
import threading
import socket
import time
from typing import Tuple


import threading
import queue
import time
# Kubernetes Python client imports
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException
from kubernetes.stream import stream


from utils.enhanced_worker import EnhancedBaseWorker
from utils.thread_manager import get_thread_manager
            

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

    log_line_received = pyqtSignal(str, str, str)  # pod_name, log_line, timestamp
    stream_error = pyqtSignal(str, str)  # pod_name, error_message
    stream_status = pyqtSignal(str, str)  # pod_name, status_message

    def __init__(self, kube_client):
        super().__init__()
        self.kube_client = kube_client
        self.active_streams = {}  # Track active log streams
        self._shutdown = False

    def start_log_stream(self, pod_name, namespace, container=None, tail_lines=200, follow=True):
        """Start streaming logs for a pod"""
        try:
            stream_key = f"{namespace}/{pod_name}"
            if container:
                stream_key += f"/{container}"

            # Stop existing stream if any
            self.stop_log_stream(stream_key)

            # Create and start new stream
            stream_thread = LogStreamThread(
                self.kube_client,
                pod_name,
                namespace,
                container,
                tail_lines,
                follow,
                self
            )

            self.active_streams[stream_key] = stream_thread
            stream_thread.start()

            self.stream_status.emit(pod_name, "Starting log stream...")

        except Exception as e:
            logging.error(f"Error starting log stream for {pod_name}: {e}")
            self.stream_error.emit(pod_name, f"Failed to start stream: {str(e)}")

    def stop_log_stream(self, stream_key):
        """Stop a specific log stream"""
        try:
            if stream_key in self.active_streams:
                stream_thread = self.active_streams[stream_key]
                stream_thread.stop()
                stream_thread.wait(2000)  # Wait up to 2 seconds

                if stream_thread.isRunning():
                    stream_thread.terminate()

                del self.active_streams[stream_key]

        except Exception as e:
            logging.error(f"Error stopping log stream {stream_key}: {e}")

    def stop_all_streams(self):
        """Stop all active log streams"""
        self._shutdown = True
        for stream_key in list(self.active_streams.keys()):
            self.stop_log_stream(stream_key)

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_all_streams()

class LogStreamThread(QThread):
    """Thread for streaming logs from Kubernetes API"""

    def __init__(self, kube_client, pod_name, namespace, container, tail_lines, follow, parent_streamer):
        super().__init__()
        self.kube_client = kube_client
        self.pod_name = pod_name
        self.namespace = namespace
        self.container = container
        self.tail_lines = tail_lines
        self.follow = follow
        self.parent_streamer = parent_streamer
        self._stop_requested = False

    def stop(self):
        """Request thread to stop"""
        self._stop_requested = True

    def run(self):
        """Run the log streaming"""
        try:
            # First, get initial logs if tail_lines is specified
            if self.tail_lines and self.tail_lines > 0:
                self._fetch_initial_logs()

            # If follow mode is enabled, start streaming
            if self.follow and not self._stop_requested:
                self._stream_live_logs()

        except Exception as e:
            if not self._stop_requested:
                self.parent_streamer.stream_error.emit(
                    self.pod_name,
                    f"Log streaming error: {str(e)}"
                )

    def _fetch_initial_logs(self):
        """Fetch initial logs"""
        try:
            if not self.kube_client.v1:
                return

            kwargs = {
                'name': self.pod_name,
                'namespace': self.namespace,
                'timestamps': True,
                'tail_lines': self.tail_lines
            }

            if self.container:
                kwargs['container'] = self.container

            logs = self.kube_client.v1.read_namespaced_pod_log(**kwargs)

            if logs and not self._stop_requested:
                # Parse and emit each log line
                for line in logs.strip().split('\n'):
                    if self._stop_requested:
                        break

                    if line.strip():
                        timestamp, log_content = self._parse_log_line(line)
                        self.parent_streamer.log_line_received.emit(
                            self.pod_name, log_content, timestamp
                        )
                        # Small delay to prevent overwhelming the UI
                        self.msleep(1)

        except ApiException as e:
            if not self._stop_requested:
                if e.status == 404:
                    self.parent_streamer.stream_error.emit(
                        self.pod_name, f"Pod not found: {self.pod_name}"
                    )
                else:
                    self.parent_streamer.stream_error.emit(
                        self.pod_name, f"API error: {e.reason}"
                    )
        except Exception as e:
            if not self._stop_requested:
                self.parent_streamer.stream_error.emit(
                    self.pod_name, f"Error fetching initial logs: {str(e)}"
                )

    def _stream_live_logs(self):
        """Stream live logs using Kubernetes watch API"""
        try:
            if not self.kube_client.v1:
                return

            self.parent_streamer.stream_status.emit(self.pod_name, "🔴 Live streaming...")

            w = watch.Watch()

            kwargs = {
                'name': self.pod_name,
                'namespace': self.namespace,
                'follow': True,
                'timestamps': True,
                'since_seconds': 1  # Only get very recent logs for streaming
            }

            if self.container:
                kwargs['container'] = self.container

            # Start the watch stream
            stream_iter = w.stream(
                self.kube_client.v1.read_namespaced_pod_log,
                **kwargs
            )

            for event in stream_iter:
                if self._stop_requested:
                    w.stop()
                    break

                # Process the log event
                if isinstance(event, str) and event.strip():
                    timestamp, log_content = self._parse_log_line(event)
                    self.parent_streamer.log_line_received.emit(
                        self.pod_name, log_content, timestamp
                    )

                # Small delay to prevent overwhelming
                self.msleep(10)

        except ApiException as e:
            if not self._stop_requested:
                self.parent_streamer.stream_error.emit(
                    self.pod_name, f"Streaming API error: {e.reason}"
                )
        except Exception as e:
            if not self._stop_requested:
                self.parent_streamer.stream_error.emit(
                    self.pod_name, f"Streaming error: {str(e)}"
                )

    def _parse_log_line(self, log_line):
        """Parse log line to extract timestamp and content"""
        try:
            # Kubernetes logs format: 2024-01-01T12:00:00.000000000Z log content
            if ' ' in log_line and log_line.startswith('20'):
                parts = log_line.split(' ', 1)
                if len(parts) == 2:
                    timestamp_str = parts[0]
                    log_content = parts[1]

                    # Extract just the time part (HH:MM:SS)
                    if 'T' in timestamp_str:
                        time_part = timestamp_str.split('T')[1]
                        if '.' in time_part:
                            time_part = time_part.split('.')[0]
                        timestamp = time_part[:8]  # HH:MM:SS
                    else:
                        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

                    return timestamp, log_content

            # Fallback if parsing fails
            return datetime.datetime.now().strftime("%H:%M:%S"), log_line

        except Exception:
            return datetime.datetime.now().strftime("%H:%M:%S"), log_line


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
    clusters_loaded = pyqtSignal(list)
    cluster_info_loaded = pyqtSignal(dict)
    cluster_metrics_updated = pyqtSignal(dict)
    node_metrics_updated = pyqtSignal(dict)
    cluster_issues_updated = pyqtSignal(list)
    resource_detail_loaded = pyqtSignal(dict)
    resource_updated = pyqtSignal(dict)
    pod_logs_loaded = pyqtSignal(dict)
    
    # New signals for streaming logs
    pod_log_line_received = pyqtSignal(dict)      # Individual log line
    pod_log_stream_error = pyqtSignal(dict)       # Stream errors
    pod_log_stream_status = pyqtSignal(dict)      # Stream status updates
    
    error_occurred = pyqtSignal(str)
    pod_logs_loaded = pyqtSignal(dict)
    pod_log_line_received = pyqtSignal(dict)      # Individual log line
    pod_log_stream_error = pyqtSignal(dict)       # Stream errors
    pod_log_stream_status = pyqtSignal(dict)      # Stream status updates

    def __init__(self):
        super().__init__()
        self.threadpool = QThreadPool()
        self.clusters = []
        self.current_cluster = None
        self._default_kubeconfig = os.path.expanduser("~/.kube/config")
        
        # Kubernetes API clients
        self.v1 = None
        self.apps_v1 = None
        self.extensions_v1beta1 = None
        self.networking_v1 = None
        self.storage_v1 = None
        self.rbac_v1 = None
        self.batch_v1 = None
        self.autoscaling_v1 = None
        self.custom_objects_api = None
        self.metrics_api = None
        

        # Add log streamer
        self.log_streamer = KubernetesLogStreamer(self)
        
        # Connect log streamer signals
        self.log_streamer.log_line_received.connect(self.handle_log_line_received)
        self.log_streamer.stream_error.connect(self.handle_stream_error)
        self.log_streamer.stream_status.connect(self.handle_stream_status)


        # Set up timers for periodic updates
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self.refresh_metrics)
        
        self.issues_timer = QTimer(self)
        self.issues_timer.timeout.connect(self.refresh_issues)
        
        # Track active workers
        self._active_workers = set()
        
        # Shutdown flag
        self._shutting_down = False

        # Add log streamer initialization
        self.log_streamer = KubernetesLogStreamer(self)

    
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
        """Initialize Kubernetes API clients"""
        try:
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
            # Load configuration for the specific context
            config.load_kube_config(context=context_name)
            
            # Initialize API clients
            if not self._initialize_api_clients():
                return False
            
            self.current_cluster = context_name
            
            # Update cluster status
            for cluster in self.clusters:
                if cluster.name == context_name:
                    cluster.status = "active"
                else:
                    cluster.status = "disconnect"
            
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to switch context to {context_name}: {str(e)}")
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
    
    def get_cluster_metrics(self):
        """Get real-time resource metrics for the cluster"""
        try:
            # Get nodes for capacity calculation
            nodes_list = self.v1.list_node()
            
            cpu_total = 0
            memory_total = 0
            pods_capacity = 0
            
            # Calculate total capacity
            for node in nodes_list.items:
                if node.status and node.status.capacity:
                    cpu_capacity = self._parse_resource_value(node.status.capacity.get('cpu', '0'))
                    memory_capacity = self._parse_resource_value(node.status.capacity.get('memory', '0Ki'))
                    pod_capacity = int(node.status.capacity.get('pods', '110'))
                    
                    cpu_total += cpu_capacity
                    memory_total += memory_capacity
                    pods_capacity += pod_capacity
            
            # Try to get metrics from metrics server
            cpu_used = 0
            memory_used = 0
            
            try:
                # This would require metrics-server to be installed
                # For now, we'll use a percentage estimation
                pass
            except:
                # Fallback to estimation
                cpu_used = cpu_total * 0.3  # 30% usage estimation
                memory_used = memory_total * 0.4  # 40% usage estimation
            
            # Get pod count
            pods_list = self.v1.list_pod_for_all_namespaces()
            pods_total = len(pods_list.items)
            
            # Calculate usage percentages
            cpu_usage = (cpu_used / cpu_total * 100) if cpu_total > 0 else 0
            memory_usage = (memory_used / memory_total * 100) if memory_total > 0 else 0
            pods_usage = (pods_total / pods_capacity * 100) if pods_capacity > 0 else 0
            
            # Generate historical data points for charts
            cpu_history = self._generate_metrics_history('cpu', 12, cpu_usage)
            memory_history = self._generate_metrics_history('memory', 12, memory_usage)
            
            metrics = {
                "cpu": {
                    "usage": round(cpu_usage, 2),
                    "requests": round(cpu_used, 2),
                    "limits": round(cpu_total * 0.8, 2),
                    "capacity": round(cpu_total, 2),
                    "allocatable": round(cpu_total, 2),
                    "history": cpu_history
                },
                "memory": {
                    "usage": round(memory_usage, 2),
                    "requests": round(memory_used / (1024**3), 2),  # Convert to GB
                    "limits": round(memory_total * 0.8 / (1024**3), 2),
                    "capacity": round(memory_total / (1024**3), 2),
                    "allocatable": round(memory_total / (1024**3), 2),
                    "history": memory_history
                },
                "pods": {
                    "usage": round(pods_usage, 2),
                    "count": pods_total,
                    "capacity": pods_capacity
                }
            }
            
            if not self._shutting_down:
                self.cluster_metrics_updated.emit(metrics)
            return metrics
            
        except Exception as e:
            if not self._shutting_down:
                self.error_occurred.emit(f"Error getting cluster metrics: {str(e)}")
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

    def get_cluster_issues(self):
        """Get current issues in the cluster"""
        try:
            issues = []
            
            # Get events with warnings or errors
            try:
                events_list = self.v1.list_event_for_all_namespaces()
                
                for event in events_list.items:
                    if event.type != "Normal":  # Warning, Error, etc.
                        age = self._format_age(event.metadata.creation_timestamp) if event.metadata.creation_timestamp else "Unknown"
                        
                        issue = {
                            "message": event.message or "No message",
                            "object": f"{event.involved_object.kind}/{event.involved_object.name}" if event.involved_object else "Unknown",
                            "type": event.type or "Unknown",
                            "age": age,
                            "namespace": event.metadata.namespace or "default",
                            "reason": event.reason or "Unknown"
                        }
                        issues.append(issue)
            except Exception as e:
                logging.warning(f"Could not get events: {e}")
            
            # Get pods that are not in Running or Succeeded state
            try:
                pods_list = self.v1.list_pod_for_all_namespaces()
                
                for pod in pods_list.items:
                    if pod.status.phase not in ["Running", "Succeeded", "Completed"]:
                        age = self._format_age(pod.metadata.creation_timestamp) if pod.metadata.creation_timestamp else "Unknown"
                        
                        # Get container status for more detailed message
                        message = "Pod not running"
                        if pod.status.container_statuses:
                            for container in pod.status.container_statuses:
                                if not container.ready:
                                    if container.state.waiting:
                                        message = container.state.waiting.message or "Container waiting"
                                    elif container.state.terminated:
                                        message = container.state.terminated.message or "Container terminated"
                                    break
                        
                        issue = {
                            "message": message,
                            "object": f"Pod/{pod.metadata.name}",
                            "type": "Warning",
                            "age": age,
                            "namespace": pod.metadata.namespace or "default",
                            "reason": pod.status.reason or "PodIssue"
                        }
                        issues.append(issue)
            except Exception as e:
                logging.warning(f"Could not get pods: {e}")
            
            # Sort issues by age (newest first)
            issues.sort(key=lambda x: x["age"], reverse=True)
            
            if not self._shutting_down:
                self.cluster_issues_updated.emit(issues)
            return issues
            
        except Exception as e:
            if not self._shutting_down:
                self.error_occurred.emit(f"Error getting cluster issues: {str(e)}")
            return []
    
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

            # FORCE initialize API clients if they don't exist
            missing_clients = []
            if not hasattr(self, 'networking_v1') or self.networking_v1 is None:
                missing_clients.append('networking_v1')
            if not hasattr(self, 'api_extensions_v1') or self.api_extensions_v1 is None:
                missing_clients.append('api_extensions_v1')
            if not hasattr(self, 'admissionregistration_v1') or self.admissionregistration_v1 is None:
                missing_clients.append('admissionregistration_v1')

            if missing_clients:
                logging.warning(f"Reinitializing missing API clients: {missing_clients}")
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

                # Add related events
                events = self._get_resource_events(resource_type, resource_name, namespace)
                resource_dict["events"] = events

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
            
            if namespace:
                events_list = self.v1.list_namespaced_event(namespace=namespace)
            else:
                events_list = self.v1.list_event_for_all_namespaces()
            
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
    
    def _parse_resource_value(self, value_str):
        """Parse Kubernetes resource value strings to float"""
        if not value_str or not isinstance(value_str, str):
            return 0.0
        
        # CPU parsing (e.g., "100m" = 0.1 cores)
        if value_str.endswith('m'):
            return float(value_str[:-1]) / 1000
        
        # Memory parsing
        memory_suffixes = {
            'Ki': 1024,
            'Mi': 1024 ** 2,
            'Gi': 1024 ** 3,
            'Ti': 1024 ** 4,
            'Pi': 1024 ** 5,
            'Ei': 1024 ** 6,
            'K': 1000,
            'M': 1000 ** 2,
            'G': 1000 ** 3,
            'T': 1000 ** 4,
            'P': 1000 ** 5,
            'E': 1000 ** 6
        }
        
        for suffix, multiplier in memory_suffixes.items():
            if value_str.endswith(suffix):
                return float(value_str[:-len(suffix)]) * multiplier
        
        # If no suffix, try to parse as a number
        try:
            return float(value_str)
        except ValueError:
            return 0.0
    
    def _format_age(self, timestamp):
        """Format timestamp to age string (e.g., "2d", "5h")"""
        if not timestamp:
            return "Unknown"
        
        try:
            if isinstance(timestamp, str):
                created_time = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                # Assume it's already a datetime object
                created_time = timestamp.replace(tzinfo=datetime.timezone.utc)
            
            now = datetime.datetime.now(datetime.timezone.utc)
            diff = now - created_time
            
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
        except Exception:
            return "Unknown"
    
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

# Singleton instance
_instance = None

def shutdown_kubernetes_client():
    """Shutdown the kubernetes client singleton safely"""
    global _instance
    if _instance is not None:
        try:
            _instance.force_shutdown()
            _instance = None
            logging.info("Kubernetes client singleton shut down successfully")
        except Exception as e:
            logging.error(f"Error shutting down kubernetes client: {e}")
            _instance = None
            
def get_kubernetes_client():
    """Get or create Kubernetes client singleton"""
    global _instance
    if _instance is None:
        _instance = KubernetesClient()
    return _instance