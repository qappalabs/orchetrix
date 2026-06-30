"""
Fixed Port Forward Manager - Corrected implementation for Kubernetes port forwarding
Uses proper socket forwarding without subprocess, compatible with Kubernetes Python client
"""

import logging
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, List

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer

from Utils import SUBPROCESS_FLAGS
from Utils.kubernetes_client import get_kubernetes_client
from Utils.thread_manager import is_shutdown_requested

@dataclass
class PortForwardConfig:
    """Configuration for port forwarding."""
    resource_name: str
    resource_type: str  # 'pod' or 'service'
    namespace: str
    local_port: int
    target_port: int
    kube_context: Optional[str] = None  # Explicit cluster context for kubectl
    protocol: str = 'TCP'
    bind_address: str = 'localhost'  # kubectl --address (e.g. 'localhost' or '0.0.0.0')
    status: str = 'inactive'  # 'starting', 'active', 'inactive', 'error'
    error_message: Optional[str] = None
    created_at: float = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

    @property
    def key(self) -> str:

        return f"{self.namespace}/{self.resource_type}/{self.resource_name}:{self.target_port}"


class KubernetesPortForwarder:
    """Handles kubectl port-forward subprocess."""

    def __init__(self, config: PortForwardConfig):
        self.config = config

        try:
            managed_client = get_kubernetes_client()
            self.kube_client = managed_client
        except Exception as e:
            logging.error(f"Failed to get kubernetes client: {e}")
            self.kube_client = None
        self.process = None
        self.running = False
        self.monitor_thread = None

    def start(self):
        """Start port forwarding."""
        try:
            if not self.kube_client:
                raise RuntimeError("Kubernetes client not available")

            # Check if kubectl is available
            if not self._check_kubectl_available():
                raise RuntimeError(
                    "kubectl is not available or not configured properly.\n"
                    "Please ensure kubectl is installed and configured to access your Kubernetes cluster.\n"
                    "You can test with: kubectl cluster-info"
                )

            # Resolve target resource reference (e.g. "pod/<name>" or "service/<name>")
            target_ref, target_port = self._resolve_target()

            logging.info(
                f"Starting kubectl port forward: localhost:{self.config.local_port} -> {target_ref}:{target_port}")

            # Use kubectl port-forward subprocess for reliability
            self.running = True
            self._start_kubectl_forwarding(target_ref, target_port)

            logging.info(
                f"Port forwarder started: localhost:{self.config.local_port} -> {target_ref}:{target_port}")

        except Exception as e:
            logging.error(f"Error starting port forwarder: {e}")
            self.running = False
            raise e

    def _start_kubectl_forwarding(self, target_ref, target_port):
        """Start kubectl port-forward subprocess."""
        try:
            # Build kubectl command — target_ref is already a full resource reference
            # e.g. "pod/<name>" or "service/<name>", so no prefix needed here
            cmd = [
                'kubectl',
                'port-forward',
                target_ref,
                f'{self.config.local_port}:{target_port}',
                '--namespace', self.config.namespace
            ]

            # Honor the bind address chosen in the dialog (defaults to localhost)
            if getattr(self.config, 'bind_address', None):
                cmd.extend(['--address', self.config.bind_address])

            if self.config.kube_context:
                cmd.extend(['--context', self.config.kube_context])

            logging.info(f"Executing: {' '.join(cmd)}")

            # Start kubectl subprocess
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0
            )

            # Give kubectl a moment to start before checking status.
            # NOTE: the monitor thread is intentionally NOT started yet — if kubectl
            # exits during this window we read stderr directly here with no race.
            time.sleep(3)

            # Check if process started successfully
            if self.process.poll() is not None:
                # Process already terminated — read stderr directly (no monitor
                # thread contention at this point)
                try:
                    stderr_output = self.process.stderr.read() if self.process.stderr else ""
                except Exception:
                    stderr_output = ""
                raise RuntimeError(
                    f"kubectl port-forward failed to start: {stderr_output.strip() or 'unknown error'}")

            # Verify port is actually listening
            if not self._wait_for_port_to_be_ready(self.config.local_port, timeout=10):
                raise RuntimeError(
                    f"Port {self.config.local_port} is not ready after 10 seconds")

            # Process is confirmed running — now start the monitor thread
            self.monitor_thread = threading.Thread(
                target=self._monitor_process,
                daemon=True
            )
            self.monitor_thread.start()

        except Exception as e:
            logging.error(f"Error starting kubectl forwarding: {e}")
            self.running = False
            raise

    def _monitor_process(self):
        """Monitor kubectl process."""
        if not self.process:
            return

        try:
            while self.running and self.process.poll() is None and not is_shutdown_requested():
                time.sleep(1)

            # Process has terminated
            if self.running:
                exit_code = self.process.poll()
                logging.info(
                    f"kubectl port-forward process exited with code: {exit_code}")

                if exit_code != 0:
                    try:
                        stderr_output = ""
                        if self.process.stderr:
                            stderr_output = self.process.stderr.read()
                        if not stderr_output:
                            stderr_output = "No error output available"
                        logging.error(
                            f"kubectl port-forward failed: {stderr_output}")
                    except Exception as e:
                        logging.error(f"Could not read stderr: {e}")

                self.running = False

        except Exception as e:
            logging.error(f"Error monitoring kubectl process: {e}")
            self.running = False

    def _check_kubectl_available(self):
        """Check if kubectl is available."""
        try:
            # First check if kubectl binary exists
            result = subprocess.run(
                ['kubectl', 'version', '--client'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0
            )
            if result.returncode != 0:
                logging.warning(
                    f"kubectl client check failed: {result.stderr}")
                return False

            # Then check if kubectl can access the target cluster
            cluster_info_cmd = ['kubectl', 'cluster-info']
            if self.config.kube_context:
                cluster_info_cmd.extend(['--context', self.config.kube_context])

            cluster_info = subprocess.run(
                cluster_info_cmd,
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0
            )
            if cluster_info.returncode != 0:
                logging.warning(
                    f"kubectl cluster access failed: {cluster_info.stderr}")
                return False

            return True
        except subprocess.TimeoutExpired:
            logging.error("kubectl commands timed out")
            return False
        except FileNotFoundError:
            logging.error("kubectl binary not found")
            return False
        except Exception as e:
            logging.error(f"kubectl not available: {e}")
            return False

    def _wait_for_port_to_be_ready(self, port, timeout=10):
        """Wait for port to be ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex(('localhost', port))
                    if result == 0:
                        return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def _resolve_target(self):
        """Return a kubectl resource reference and port for the configured target.

        Delegates resolution entirely to kubectl rather than re-implementing
        service-to-pod selector logic in Python.  This handles:
          - Standard selector-backed services
          - Selectorless services (e.g. the built-in 'kubernetes' service)
          - ExternalName services (kubectl will surface its own error)
        """
        if self.config.resource_type == 'pod':
            return f"pod/{self.config.resource_name}", self.config.target_port

        elif self.config.resource_type == 'service':
            # Pass service/<name> directly to kubectl.  kubectl resolves the
            # service port to a backing endpoint itself, so we never need to
            # inspect spec.selector or list pods here.
            return f"service/{self.config.resource_name}", self.config.target_port

        raise ValueError(f"Unsupported resource type: {self.config.resource_type}")

    def stop(self):
        """Stop port forwarding."""
        logging.info(f"Stopping port forward for {self.config.key}")
        self.running = False

        # Stop kubectl subprocess
        try:
            if self.process and self.process.poll() is None:
                logging.info("Terminating kubectl process")
                self.process.terminate()

                # Wait a moment for graceful termination
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logging.warning(
                        "kubectl process didn't terminate gracefully, killing")
                    self.process.kill()
                    self.process.wait()

                logging.info("kubectl process stopped")

            # Close file handles
            if self.process:
                if self.process.stdout:
                    self.process.stdout.close()
                if self.process.stderr:
                    self.process.stderr.close()

            if self.monitor_thread and self.monitor_thread.is_alive():
                # Thread will stop when self.running becomes False
                logging.info("Monitor thread will stop automatically")
                # Give monitor thread time to exit
                self.monitor_thread.join(timeout=2)

        except Exception as e:
            logging.error(f"Error stopping kubectl port forwarder: {e}")

        logging.info("Port forward stopped successfully")

    def is_running(self):
        """Check if port forwarding is running."""
        if not self.running:
            return False

        if self.process:
            return self.process.poll() is None

        return False


class PortForwardWorker(QThread):
    """Worker thread for port forwarding."""

    # Signals
    started = pyqtSignal()
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, config: PortForwardConfig):
        super().__init__()

        self.config = config
        self.forwarder = None
        self._stop_requested = False

    def run(self):
        """Run port forwarding."""
        try:
            # Use real Kubernetes port forwarder
            self.forwarder = KubernetesPortForwarder(self.config)
            self.forwarder.start()

            # Signal that port forward is confirmed running
            self.started.emit()

            # Keep the worker running to maintain the port forward
            while not self._stop_requested and self.forwarder.is_running() and not is_shutdown_requested():
                time.sleep(1)

            # Port forward has stopped
            if not self._stop_requested:
                logging.info(
                    f"Port forward {self.config.key} stopped unexpectedly")

            self.finished.emit({'status': 'completed', 'config': self.config})

        except Exception as e:
            logging.error(f"Port forward error for {self.config.key}: {e}")
            if self.forwarder:
                self.forwarder.stop()
            # Emit only the exception message — no internal key prefix in UI-facing text
            self.error.emit(str(e))

    def stop(self):
        """Stop port forwarding."""
        self._stop_requested = True
        if self.forwarder:
            self.forwarder.stop()

    def cleanup(self):
        """Cleanup resources."""
        self.stop()
        self.wait(3000)  # Wait up to 3 seconds for thread to finish


class PortForwardManager(QObject):
    """Manages multiple port forwards."""

    # Signals
    port_forward_started = pyqtSignal(object)   # config — emitted when worker thread begins (status='starting')
    port_forward_active = pyqtSignal(object)    # config — emitted when kubectl is confirmed running (status='active')
    port_forward_stopped = pyqtSignal(str)
    port_forward_error = pyqtSignal(str, str)
    port_forwards_updated = pyqtSignal(list)

    def __init__(self):
        super().__init__()

        self._forwards: Dict[str, PortForwardConfig] = {}
        self._workers: Dict[str, PortForwardWorker] = {}
        self._lock = threading.RLock()

        # Timer to check port forward status
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._check_port_forward_status)
        self._status_timer.start(5000)  # Check every 5 seconds

    def get_available_local_port(self, preferred_port: Optional[int] = None) -> int:
        """Get an available local port."""
        if preferred_port and self._is_port_available(preferred_port):
            return preferred_port

        # Find next available port starting from 8080
        start_port = preferred_port if preferred_port and preferred_port > 1024 else 8080

        for port in range(start_port, start_port + 1000):
            if self._is_port_available(port):
                return port

        raise RuntimeError("No available ports found")

    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False

    def start_port_forward(self,
                           resource_name: str,
                           resource_type: str,
                           namespace: str,
                           target_port: int,
                           local_port: Optional[int] = None,
                           kube_context: Optional[str] = None,
                           protocol: str = 'TCP',
                           bind_address: str = 'localhost') -> PortForwardConfig:
        """Start a new port forward with explicit context routing."""

        with self._lock:
            # Auto-resolve context from the app's active cluster if not provided
            resolved_context = kube_context
            if not resolved_context:
                try:
                    from Utils.cluster_connector import get_cluster_connector
                    connector = get_cluster_connector()
                    if hasattr(connector, 'current_cluster') and connector.current_cluster:
                        resolved_context = connector.current_cluster
                except Exception as e:
                    logging.debug(f"Could not auto-resolve kube_context for port forward: {e}")

            # Find available local port if not specified
            if local_port is None:
                local_port = self.get_available_local_port()
            else:
                if not self._is_port_available(local_port):
                    raise ValueError(f"Port {local_port} is already in use")

            # Create configuration with explicit context tracking
            config = PortForwardConfig(
                resource_name=resource_name,
                resource_type=resource_type,
                namespace=namespace,
                local_port=local_port,
                target_port=target_port,
                kube_context=resolved_context,
                protocol=protocol,
                bind_address=bind_address
            )

            # Check if forward already exists
            if config.key in self._forwards:
                existing = self._forwards[config.key]
                if existing.status == 'active':
                    raise ValueError(
                        f"Port forward already exists for {config.key}")
                else:
                    # Remove inactive forward
                    self.stop_port_forward(config.key)

            # Store configuration
            self._forwards[config.key] = config

            # Create and start worker
            worker = PortForwardWorker(config)
            self._workers[config.key] = worker

            # Connect worker signals
            worker.started.connect(
                lambda: self._handle_worker_started(config.key)
            )
            worker.finished.connect(
                lambda result: self._handle_worker_finished(config.key, result)
            )
            worker.error.connect(
                lambda error: self._handle_worker_error(config.key, error)
            )

            # Start the worker thread
            worker.start()

            # Update status - will transition to 'active' when worker confirms
            config.status = 'starting'
            self.port_forward_started.emit(config)
            self._emit_updates()

            return config

    def stop_port_forward(self, key: str) -> bool:
        """Stop a port forward."""
        with self._lock:
            if key not in self._forwards:
                return False

            # Stop worker if running
            if key in self._workers:
                worker = self._workers[key]
                worker.stop()
                worker.cleanup()
                del self._workers[key]

            # Remove configuration
            del self._forwards[key]

            self.port_forward_stopped.emit(key)
            self._emit_updates()

            return True

    def stop_all_port_forwards(self):
        """Stop all port forwards."""
        with self._lock:
            keys = list(self._forwards.keys())
            for key in keys:
                self.stop_port_forward(key)

    def get_port_forwards(self) -> List[PortForwardConfig]:
        """Get all port forwards."""
        with self._lock:
            return list(self._forwards.values())

    def get_port_forward(self, key: str) -> Optional[PortForwardConfig]:
        """Get a specific port forward."""
        with self._lock:
            return self._forwards.get(key)

    def _handle_worker_started(self, key: str):
        """Handle worker successfully started port forwarding."""
        with self._lock:
            if key in self._forwards:
                config = self._forwards[key]
                config.status = 'active'
                self.port_forward_active.emit(config)
                self._emit_updates()

    def _handle_worker_finished(self, key: str, result):
        """Handle worker finished."""
        with self._lock:
            if key in self._forwards:
                config = self._forwards[key]
                config.status = 'inactive'
                self._emit_updates()

    def _handle_worker_error(self, key: str, error_message: str):
        """Handle worker error."""
        with self._lock:
            if key in self._forwards:
                config = self._forwards[key]
                config.status = 'error'
                config.error_message = error_message
                self.port_forward_error.emit(key, error_message)
                # The worker thread has already exited (exception caused run() to return)
                # so remove the failed entry immediately — no point keeping it in the list
                del self._forwards[key]
                self._workers.pop(key, None)
                self._emit_updates()

    def _check_port_forward_status(self):
        """Check status of all port forwards."""
        with self._lock:
            for key, config in list(self._forwards.items()):
                if config.status == 'active' and key in self._workers:
                    # Check if the forwarder process is still running
                    worker = self._workers[key]
                    if hasattr(worker, 'forwarder') and worker.forwarder:
                        if hasattr(worker.forwarder, 'is_running'):
                            if not worker.forwarder.is_running():
                                config.status = 'inactive'
                                logging.info(
                                    f"Port forward {key} detected as inactive - process terminated")
                                # Try to get the exit reason
                                if hasattr(worker.forwarder, 'process') and worker.forwarder.process:
                                    exit_code = worker.forwarder.process.poll()
                                    if exit_code is not None:
                                        logging.info(
                                            f"Port forward {key} process exited with code: {exit_code}")
                        else:
                            # Fallback: check if local port is still in use
                            if not self._is_port_in_use(config.local_port):
                                config.status = 'inactive'
                                logging.info(
                                    f"Port forward {key} port no longer in use")
                    else:
                        # Worker has no forwarder, mark as inactive
                        config.status = 'inactive'
                        logging.info(
                            f"Port forward {key} worker has no forwarder")

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False

    def _emit_updates(self):
        """Emit port forwards updated signal."""
        self.port_forwards_updated.emit(self.get_port_forwards())

    def cleanup(self):
        """Cleanup all port forwards."""
        self._status_timer.stop()
        self.stop_all_port_forwards()

# Singleton instance
_port_forward_manager = None
_port_forward_manager_lock = threading.Lock()
_on_created_callbacks: list = []


def register_on_manager_created(callback) -> None:
    """Register a callback to be invoked when the PortForwardManager singleton
    is first created.  If the manager already exists the callback is called
    immediately.  This lets callers (e.g. MainWindow) wire up signal connections
    without forcing eager creation of the manager.

    Thread-safe: the check and the append are both performed while holding
    _port_forward_manager_lock so that a concurrent get_port_forward_manager
    call cannot create the manager and clear _on_created_callbacks in the
    gap between the two operations, which would silently drop the callback.
    The callback itself is invoked *outside* the lock to avoid a potential
    deadlock if the callback re-enters get_port_forward_manager.
    """
    global _port_forward_manager
    existing_manager = None
    with _port_forward_manager_lock:
        if _port_forward_manager is not None:
            # Capture under lock so the reference is consistent with what
            # get_port_forward_manager considers the authoritative instance.
            existing_manager = _port_forward_manager
        else:
            _on_created_callbacks.append(callback)

    # Invoke outside the lock to avoid holding it during arbitrary callback code.
    if existing_manager is not None:
        try:
            callback(existing_manager)
        except Exception as e:
            logging.warning(f"register_on_manager_created callback failed: {e}")


def get_port_forward_manager() -> PortForwardManager:
    global _port_forward_manager
    pending_callbacks: list = []
    if _port_forward_manager is None:
        with _port_forward_manager_lock:
            if _port_forward_manager is None:
                _port_forward_manager = PortForwardManager()
                # Snapshot and clear under the lock so callbacks fire exactly
                # once even if another thread registers concurrently.
                pending_callbacks = list(_on_created_callbacks)
                _on_created_callbacks.clear()

    # Invoke outside the lock to avoid deadlock if a callback re-enters
    # get_port_forward_manager (the lock is a plain Lock, not an RLock).
    for cb in pending_callbacks:
        try:
            cb(_port_forward_manager)
        except Exception as e:
            logging.warning(f"Port forward manager creation callback failed: {e}")

    return _port_forward_manager
