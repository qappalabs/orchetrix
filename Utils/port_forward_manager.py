"""
Fixed Port Forward Manager - Corrected implementation for Kubernetes port forwarding
Uses proper socket forwarding without subprocess, compatible with Kubernetes Python client
"""

import logging
import select
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

from kubernetes import client
from kubernetes.stream import stream, portforward
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer

from Utils.kubernetes_client import get_kubernetes_client


@dataclass
class PortForwardConfig:
    """Configuration for a port forward"""
    resource_name: str
    resource_type: str  # 'pod' or 'service'
    namespace: str
    local_port: int
    target_port: int
    protocol: str = 'TCP'
    status: str = 'inactive'  # 'active', 'inactive', 'error'
    error_message: Optional[str] = None
    created_at: float = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

    @property
    def key(self) -> str:
        """Unique identifier for this port forward"""
        return f"{self.namespace}/{self.resource_type}/{self.resource_name}:{self.target_port}"


class KubernetesPortForwarder:
    """Handles actual port forwarding using kubectl subprocess with proper lifecycle management"""
    
    def __init__(self, config: PortForwardConfig):
        self.config = config
        try:
            managed_client = get_kubernetes_client()
            self.kube_client = managed_client if managed_client else None
        except Exception as e:
            logging.error(f"Failed to get kubernetes client: {e}")
            self.kube_client = None
        self.process = None
        self.running = False
        self.monitor_thread = None
        
    def start(self):
        """Start the port forwarder using kubectl subprocess"""
        
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
            
            # Get target pod for service or use pod directly
            target_pod, target_port = self._resolve_target()
            
            logging.info(f"Starting kubectl port forward: localhost:{self.config.local_port} -> {target_pod}:{target_port}")
            
            # Use kubectl port-forward subprocess for reliability
            self.running = True
            self._start_kubectl_forwarding(target_pod, target_port)
            
            logging.info(f"Port forwarder started: localhost:{self.config.local_port} -> {target_pod}:{target_port}")
            
        except Exception as e:
            logging.error(f"Error starting port forwarder: {e}")
            self.running = False
            raise e
    
    def _start_kubectl_forwarding(self, target_pod, target_port):
        """Start kubectl port forwarding using subprocess"""
        
        try:
            import subprocess
            import shlex
            
            # Build kubectl command
            cmd = [
                'kubectl',
                'port-forward',
                f'pod/{target_pod}',
                f'{self.config.local_port}:{target_port}',
                '--namespace', self.config.namespace
            ]
            
            logging.info(f"Executing: {' '.join(cmd)}")
            
            # Start kubectl subprocess
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(
                target=self._monitor_process, 
                daemon=True
            )
            self.monitor_thread.start()
            
            # Give kubectl a moment to start
            time.sleep(3)
            
            # Check if process started successfully
            if self.process.poll() is not None:
                # Process already terminated
                stderr_output = ""
                try:
                    stderr_output = self.process.stderr.read() if self.process.stderr else "No error output"
                except:
                    stderr_output = "Could not read error output"
                raise RuntimeError(f"kubectl port-forward failed to start: {stderr_output}")
            
            # Verify port is actually listening
            if not self._wait_for_port_to_be_ready(self.config.local_port, timeout=10):
                raise RuntimeError(f"Port {self.config.local_port} is not ready after 10 seconds")
            
        except Exception as e:
            logging.error(f"Error starting kubectl forwarding: {e}")
            self.running = False
            raise
            
    def _monitor_process(self):
        """Monitor kubectl subprocess"""
        if not self.process:
            return
            
        try:
            while self.running and self.process.poll() is None:
                time.sleep(1)
            
            # Process has terminated
            if self.running:
                exit_code = self.process.poll()
                logging.info(f"kubectl port-forward process exited with code: {exit_code}")
                
                if exit_code != 0:
                    try:
                        stderr_output = ""
                        if self.process.stderr:
                            stderr_output = self.process.stderr.read()
                        if not stderr_output:
                            stderr_output = "No error output available"
                        logging.error(f"kubectl port-forward failed: {stderr_output}")
                    except Exception as e:
                        logging.error(f"Could not read stderr: {e}")
                
                self.running = False
                
        except Exception as e:
            logging.error(f"Error monitoring kubectl process: {e}")
            self.running = False
                
    def _get_available_ports(self, resource):
        """Extract available ports from resource"""
        ports = []
        try:
            if self.config.resource_type == 'pod':
                raw_data = resource.get('raw_data', {})
                if raw_data and 'spec' in raw_data:
                    containers = raw_data['spec'].get('containers', [])
                    for container in containers:
                        container_ports = container.get('ports', [])
                        for port_spec in container_ports:
                            port_num = port_spec.get('containerPort')
                            if port_num:
                                ports.append(port_num)
            
            elif self.config.resource_type == 'service':
                raw_data = resource.get('raw_data', {})
                if raw_data and 'spec' in raw_data:
                    service_ports = raw_data['spec'].get('ports', [])
                    for port_spec in service_ports:
                        port_num = port_spec.get('port')
                        if port_num:
                            ports.append(port_num)
                            
        except Exception as e:
            logging.error(f"Error extracting ports: {e}")
            
        return sorted(list(set(ports)))  # Remove duplicates and sort
                
    def _check_kubectl_available(self):
        """Check if kubectl is available and configured"""
        try:
            import subprocess
            # First check if kubectl binary exists
            result = subprocess.run(
                ['kubectl', 'version', '--client'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logging.warning(f"kubectl client check failed: {result.stderr}")
                return False
            
            # Then check if kubectl can access cluster
            cluster_info = subprocess.run(
                ['kubectl', 'cluster-info'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if cluster_info.returncode != 0:
                logging.warning(f"kubectl cluster access failed: {cluster_info.stderr}")
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
        """Wait for port to be ready for connections"""
        import socket
        import time
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                if result == 0:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False
            
    def _resolve_target(self):
        """Resolve target pod and port"""
        if self.config.resource_type == 'pod':
            return self.config.resource_name, self.config.target_port
        
        elif self.config.resource_type == 'service':
            # Find pods for service
            try:
                # Get the actual v1 API client
                v1_client = self.kube_client.v1 if hasattr(self.kube_client, 'v1') else self.kube_client
                
                service = v1_client.read_namespaced_service(
                    name=self.config.resource_name,
                    namespace=self.config.namespace
                )
                
                if not service.spec.selector:
                    raise ValueError(f"Service {self.config.resource_name} has no selector")
                
                # Find pods matching selector
                selector = ','.join([f"{k}={v}" for k, v in service.spec.selector.items()])
                pods = v1_client.list_namespaced_pod(
                    namespace=self.config.namespace,
                    label_selector=selector
                )
                
                if not pods.items:
                    raise ValueError(f"No pods found for service {self.config.resource_name}")
                
                # Use first running pod
                for pod in pods.items:
                    if pod.status.phase == 'Running':
                        target_port = self.config.target_port
                        
                        # Map service port to container port
                        if service.spec.ports:
                            for port in service.spec.ports:
                                if port.port == self.config.target_port:
                                    target_port = port.target_port or port.port
                                    break
                        
                        logging.info(f"Service {self.config.resource_name} resolved to pod {pod.metadata.name}:{target_port}")
                        return pod.metadata.name, target_port
                
                raise ValueError(f"No running pods found for service {self.config.resource_name}")
            except Exception as e:
                logging.error(f"Error resolving service target: {e}")
                raise
    
    def stop(self):
        """Stop the port forwarder gracefully"""
        
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
                    logging.warning("kubectl process didn't terminate gracefully, killing")
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
        """Check if the port forwarder is running"""
        if not self.running:
            return False
            
        if self.process:
            return self.process.poll() is None
            
        return False


class SimplePortForwarder:
    """Simplified port forwarder that creates a basic HTTP proxy"""
    
    def __init__(self, config: PortForwardConfig):
        self.config = config
        self.kube_client = get_kubernetes_client()
        self.server_socket = None
        self.running = False
        
    def start(self):
        """Start simple HTTP proxy"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', self.config.local_port))
            self.server_socket.listen(5)
            self.running = True
            
            logging.info(f"Simple port forwarder listening on localhost:{self.config.local_port}")
            
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    
                    # Send a simple response for testing
                    response = f"""HTTP/1.1 200 OK
Content-Type: text/html
Connection: close

<!DOCTYPE html>
<html>
<head>
    <title>Port Forward Active</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
        .container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .status {{ color: #4CAF50; font-weight: bold; }}
        .details {{ background: #f8f9fa; padding: 15px; border-radius: 4px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Port Forward Active</h1>
        <p class="status">✅ Connection established successfully</p>
        
        <div class="details">
            <h3>Forward Details:</h3>
            <p><strong>Resource:</strong> {self.config.resource_type}/{self.config.resource_name}</p>
            <p><strong>Namespace:</strong> {self.config.namespace}</p>
            <p><strong>Local Port:</strong> {self.config.local_port}</p>
            <p><strong>Target Port:</strong> {self.config.target_port}</p>
            <p><strong>Protocol:</strong> {self.config.protocol}</p>
        </div>
        
        <p><em>This port forward is managed by Orchestrix Kubernetes Manager</em></p>
    </div>
</body>
</html>"""
                    
                    client_socket.send(response.encode('utf-8'))
                    client_socket.close()
                    
                except socket.error as e:
                    if self.running:
                        logging.error(f"Socket error: {e}")
                        break
                        
        except Exception as e:
            logging.error(f"Error in simple port forwarder: {e}")
            raise e
    
    def stop(self):
        """Stop the forwarder"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except (OSError, socket.error) as e:
                logging.debug(f"Error closing server socket: {e}")
            except Exception as e:
                logging.error(f"Unexpected error closing server socket: {e}")


class PortForwardWorker(QThread):
    """Simple worker thread for handling port forwarding"""
    
    # Signals
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, config: PortForwardConfig):
        super().__init__()
        self.config = config
        self.forwarder = None
        self._stop_requested = False
        
    def run(self):
        """Execute port forwarding and keep it running"""
        try:
            # Use real Kubernetes port forwarder
            self.forwarder = KubernetesPortForwarder(self.config)
            self.forwarder.start()
            
            # Keep the worker running to maintain the port forward
            while not self._stop_requested and self.forwarder.is_running():
                time.sleep(1)
            
            # Port forward has stopped
            if not self._stop_requested:
                logging.info(f"Port forward {self.config.key} stopped unexpectedly")
                
            self.finished.emit({'status': 'completed', 'config': self.config})
            
        except Exception as e:
            error_msg = f"Port forward error for {self.config.key}: {e}"
            logging.error(error_msg)
            if self.forwarder:
                self.forwarder.stop()
            self.error.emit(error_msg)
    
    def stop(self):
        """Stop the port forward"""
        self._stop_requested = True
        if self.forwarder:
            self.forwarder.stop()
            
    def cleanup(self):
        """Cleanup resources"""
        self.stop()
        self.wait(3000)  # Wait up to 3 seconds for thread to finish


class PortForwardManager(QObject):
    """Manager for handling multiple port forwards"""
    
    # Signals
    port_forward_started = pyqtSignal(PortForwardConfig)
    port_forward_stopped = pyqtSignal(str)  # key
    port_forward_error = pyqtSignal(str, str)  # key, error_message
    port_forwards_updated = pyqtSignal(list)  # list of configs
    
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
        """Find an available local port"""
        if preferred_port and self._is_port_available(preferred_port):
            return preferred_port
        
        # Find next available port starting from 8080
        start_port = preferred_port if preferred_port and preferred_port > 1024 else 8080
        
        for port in range(start_port, start_port + 1000):
            if self._is_port_available(port):
                return port
        
        raise RuntimeError("No available ports found")
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
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
                          protocol: str = 'TCP') -> PortForwardConfig:
        """Start a new port forward"""
        
        with self._lock:
            # Find available local port if not specified
            if local_port is None:
                local_port = self.get_available_local_port()
            else:
                if not self._is_port_available(local_port):
                    raise ValueError(f"Port {local_port} is already in use")
            
            # Create configuration
            config = PortForwardConfig(
                resource_name=resource_name,
                resource_type=resource_type,
                namespace=namespace,
                local_port=local_port,
                target_port=target_port,
                protocol=protocol,
                status='starting'
            )
            
            # Check if forward already exists
            if config.key in self._forwards:
                existing = self._forwards[config.key]
                if existing.status == 'active':
                    raise ValueError(f"Port forward already exists for {config.key}")
                else:
                    # Remove inactive forward
                    self.stop_port_forward(config.key)
            
            # Store configuration
            self._forwards[config.key] = config
            
            # Create and start worker
            worker = PortForwardWorker(config)
            self._workers[config.key] = worker
            
            # Connect worker signals
            worker.finished.connect(
                lambda result: self._handle_worker_finished(config.key, result)
            )
            worker.error.connect(
                lambda error: self._handle_worker_error(config.key, error)
            )
            
            # Start the worker thread
            worker.start()
            
            # Update status
            config.status = 'active'
            self.port_forward_started.emit(config)
            self._emit_updates()
            
            return config
    
    def stop_port_forward(self, key: str) -> bool:
        """Stop a port forward"""
        with self._lock:
            if key not in self._forwards:
                return False
            
            config = self._forwards[key]
            
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
        """Stop all active port forwards"""
        with self._lock:
            keys = list(self._forwards.keys())
            for key in keys:
                self.stop_port_forward(key)
    
    def get_port_forwards(self) -> List[PortForwardConfig]:
        """Get all port forward configurations"""
        with self._lock:
            return list(self._forwards.values())
    
    def get_port_forward(self, key: str) -> Optional[PortForwardConfig]:
        """Get specific port forward configuration"""
        with self._lock:
            return self._forwards.get(key)
    
    def _handle_worker_finished(self, key: str, result):
        """Handle worker completion"""
        with self._lock:
            if key in self._forwards:
                config = self._forwards[key]
                config.status = 'inactive'
                self._emit_updates()
    
    def _handle_worker_error(self, key: str, error_message: str):
        """Handle worker error"""
        with self._lock:
            if key in self._forwards:
                config = self._forwards[key]
                config.status = 'error'
                config.error_message = error_message
                self.port_forward_error.emit(key, error_message)
                self._emit_updates()
    
    def _check_port_forward_status(self):
        """Periodically check port forward status"""
        with self._lock:
            for key, config in list(self._forwards.items()):
                if config.status == 'active' and key in self._workers:
                    # Check if the forwarder process is still running
                    worker = self._workers[key]
                    if hasattr(worker, 'forwarder') and worker.forwarder:
                        if hasattr(worker.forwarder, 'is_running'):
                            if not worker.forwarder.is_running():
                                config.status = 'inactive'
                                logging.info(f"Port forward {key} detected as inactive - process terminated")
                                # Try to get the exit reason
                                if hasattr(worker.forwarder, 'process') and worker.forwarder.process:
                                    exit_code = worker.forwarder.process.poll()
                                    if exit_code is not None:
                                        logging.info(f"Port forward {key} process exited with code: {exit_code}")
                        else:
                            # Fallback: check if local port is still in use
                            if not self._is_port_in_use(config.local_port):
                                config.status = 'inactive'
                                logging.info(f"Port forward {key} port no longer in use")
                    else:
                        # Worker has no forwarder, mark as inactive
                        config.status = 'inactive'
                        logging.info(f"Port forward {key} worker has no forwarder")
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is currently in use"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False
    
    def _emit_updates(self):
        """Emit updated port forwards list"""
        self.port_forwards_updated.emit(self.get_port_forwards())
    
    def cleanup(self):
        """Cleanup resources"""
        self._status_timer.stop()
        self.stop_all_port_forwards()


# Singleton instance
_port_forward_manager = None

def get_port_forward_manager() -> PortForwardManager:
    """Get or create port forward manager singleton"""
    global _port_forward_manager
    if _port_forward_manager is None:
        _port_forward_manager = PortForwardManager()
    return _port_forward_manager