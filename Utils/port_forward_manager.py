"""
Fixed Port Forward Manager - Corrected implementation for Kubernetes port forwarding
Uses proper socket forwarding without subprocess, compatible with Kubernetes Python client
"""

import logging
import select
import socket
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
        self.kube_client = get_kubernetes_client()
        self.process = None
        self.running = False
        self.monitor_thread = None
        
    def start(self):
        """Start the port forwarder using native socket forwarding (subprocess removed for security)"""
        
        try:
            # Get target pod for service or use pod directly
            target_pod, target_port = self._resolve_target()
            
            logging.info(f"Starting native port forward: localhost:{self.config.local_port} -> {target_pod}:{target_port}")
            
            # Use native socket-based forwarding instead of subprocess
            self.running = True
            self._start_native_forwarding(target_pod, target_port)
            
            logging.info(f"Port forwarder started: localhost:{self.config.local_port} -> {target_pod}:{target_port}")
            
        except Exception as e:
            logging.error(f"Error starting port forwarder: {e}")
            self.running = False
            raise e
    
    def _start_native_forwarding(self, target_pod, target_port):
        """Start native Kubernetes port forwarding without subprocess"""
        
        try:
            # Create local server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', self.config.local_port))
            self.server_socket.listen(5)
            
            # Start accepting connections in a separate thread
            self.accept_thread = threading.Thread(target=self._accept_connections, 
                                                 args=(target_pod, target_port), daemon=True)
            self.accept_thread.start()
            
        except Exception as e:
            logging.error(f"Error starting native forwarding: {e}")
            self.running = False
            raise
            
    def _accept_connections(self, target_pod, target_port):
        """Accept and handle client connections"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                logging.info(f"Accepted connection from {addr}")
                
                # Handle connection in separate thread
                handler_thread = threading.Thread(
                    target=self._handle_connection,
                    args=(client_socket, target_pod, target_port),
                    daemon=True
                )
                handler_thread.start()
                
            except Exception as e:
                if self.running:
                    logging.error(f"Error accepting connection: {e}")
                break
                
    def _handle_connection(self, client_socket, target_pod, target_port):
        """Handle individual client connection with real Kubernetes port forwarding"""
        try:
            
            logging.info(f"Creating port forward connection to {target_pod}:{target_port}")
            
            # Create Kubernetes port forward stream
            pf = portforward(
                self.kube_client.v1,
                name=target_pod,
                namespace=self.config.namespace,
                ports=[str(target_port)],
                address='127.0.0.1'
            )
            
            # Start bidirectional data forwarding
            forward_thread = threading.Thread(
                target=self._forward_data,
                args=(client_socket, pf, target_port),
                daemon=True
            )
            forward_thread.start()
            forward_thread.join()
            
        except Exception as e:
            logging.error(f"Error handling connection: {e}")
            try:
                client_socket.close()
            except:
                pass
                
    def _forward_data(self, client_socket, pf, target_port):
        """Forward data between client and Kubernetes pod"""
        try:
            # Get the port forward socket
            pf_socket = pf.socket(target_port)
            
            def forward_client_to_pod():
                """Forward data from client to pod"""
                try:
                    while self.running:
                        data = client_socket.recv(4096)
                        if not data:
                            break
                        pf_socket.send(data)
                except Exception as e:
                    logging.debug(f"Client to pod forwarding stopped: {e}")
                    
            def forward_pod_to_client():
                """Forward data from pod to client"""
                try:
                    while self.running:
                        data = pf_socket.recv(4096)
                        if not data:
                            break
                        client_socket.send(data)
                except Exception as e:
                    logging.debug(f"Pod to client forwarding stopped: {e}")
            
            # Start both directions of forwarding
            client_to_pod = threading.Thread(target=forward_client_to_pod, daemon=True)
            pod_to_client = threading.Thread(target=forward_pod_to_client, daemon=True)
            
            client_to_pod.start()
            pod_to_client.start()
            
            # Wait for either thread to complete
            client_to_pod.join()
            pod_to_client.join()
            
        except Exception as e:
            logging.error(f"Error in data forwarding: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            try:
                pf.close()
            except:
                pass
            
    def _resolve_target(self):
        """Resolve target pod and port"""
        if self.config.resource_type == 'pod':
            return self.config.resource_name, self.config.target_port
        
        elif self.config.resource_type == 'service':
            # Find pods for service
            service = self.kube_client.v1.read_namespaced_service(
                name=self.config.resource_name,
                namespace=self.config.namespace
            )
            
            if not service.spec.selector:
                raise ValueError(f"Service {self.config.resource_name} has no selector")
            
            # Find pods matching selector
            selector = ','.join([f"{k}={v}" for k, v in service.spec.selector.items()])
            pods = self.kube_client.v1.list_namespaced_pod(
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
                    
                    return pod.metadata.name, target_port
            
            raise ValueError(f"No running pods found for service {self.config.resource_name}")
    
    def stop(self):
        """Stop the port forwarder gracefully"""
        
        logging.info(f"Stopping port forward for {self.config.key}")
        self.running = False
        
        # Stop native forwarding
        try:
            if hasattr(self, 'server_socket') and self.server_socket:
                self.server_socket.close()
                logging.info("Server socket closed")
                
            if hasattr(self, 'accept_thread') and self.accept_thread:
                # Thread will stop when self.running becomes False
                logging.info("Accept thread will stop automatically")
                
        except Exception as e:
            logging.error(f"Error stopping native port forwarder: {e}")
        
        # No monitor thread cleanup needed for native forwarding
        logging.info("Port forward stopped successfully")
    
    def is_running(self):
        """Check if the port forwarder is running"""
        return self.running and hasattr(self, 'server_socket') and self.server_socket


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