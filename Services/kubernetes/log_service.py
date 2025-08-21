"""
Kubernetes Log Service - Handles log streaming and management
Split from kubernetes_client.py for better architecture
"""

import gc
import logging
from collections import defaultdict, deque
from datetime import datetime
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from kubernetes import watch
from kubernetes.client.rest import ApiException

# Log configuration constants
LOG_BUFFER_SIZE = 1000
MAX_STREAM_BUFFERS = 50
FLUSH_INTERVAL_MS = 100
CLEANUP_INTERVAL_MS = 30000


class LogStreamThread(QThread):
    """Thread for streaming logs from Kubernetes API"""

    def __init__(self, api_service, pod_name, namespace, container, tail_lines, buffer):
        super().__init__()
        self.api_service = api_service
        self.pod_name = pod_name
        self.namespace = namespace
        self.container = container
        self.tail_lines = tail_lines
        self.buffer = buffer
        self._stop_requested = False
    
    def stop(self):
        """Request thread to stop"""
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
            
            logs = self.api_service.v1.read_namespaced_pod_log(**kwargs)
            
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
            logging.error(f"Error fetching initial logs for {self.pod_name}: {e}")
    
    def _stream_live_logs(self):
        """Stream live logs using watch API"""
        try:
            kwargs = {
                'name': self.pod_name,
                'namespace': self.namespace,
                'follow': True,
                'timestamps': True
            }
            
            if self.container:
                kwargs['container'] = self.container
            
            w = watch.Watch()
            for line in w.stream(self.api_service.v1.read_namespaced_pod_log, **kwargs):
                if self._stop_requested:
                    break
                    
                if isinstance(line, str) and line.strip():
                    timestamp, content = self._parse_log_line(line)
                    self.buffer.append({
                        'timestamp': timestamp,
                        'content': content
                    })
                    
        except ApiException as e:
            if e.status != 404:  # Ignore pod not found errors
                logging.error(f"API error streaming logs for {self.pod_name}: {e}")
        except Exception as e:
            logging.error(f"Error streaming live logs for {self.pod_name}: {e}")
    
    def _parse_log_line(self, line: str) -> tuple:
        """Parse log line to extract timestamp and content"""
        try:
            # Format: "2023-01-01T00:00:00.000000000Z log content"
            if 'T' in line and 'Z' in line:
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    timestamp_str, content = parts
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    return timestamp.strftime('%H:%M:%S'), content
            
            # Fallback: use current time
            return datetime.now().strftime('%H:%M:%S'), line
            
        except Exception:
            return datetime.now().strftime('%H:%M:%S'), line


class KubernetesLogStreamer(QObject):
    """Kubernetes log streamer using watch API for real-time logs"""

    log_batch_received = pyqtSignal(str, list)  # pod_name, log_lines
    stream_error = pyqtSignal(str, str)  # pod_name, error_message
    stream_status = pyqtSignal(str, str)  # pod_name, status_message

    def __init__(self, api_service):
        super().__init__()
        self.api_service = api_service
        self.active_streams = {}
        self.log_buffers = defaultdict(lambda: deque(maxlen=LOG_BUFFER_SIZE))
        self._shutdown = False
        self._cleanup_timer = QTimer()
        
        # Buffer flush timer
        self._flush_timer = QTimer()
        self._flush_timer.timeout.connect(self._flush_buffers)
        self._flush_timer.start(FLUSH_INTERVAL_MS)
        
        # Cleanup timer to prevent memory leaks
        self._cleanup_timer.timeout.connect(self._periodic_cleanup)
        self._cleanup_timer.start(CLEANUP_INTERVAL_MS)
    
    def start_log_stream(self, pod_name, namespace, container=None, tail_lines=200):
        """Start optimized log streaming"""
        stream_key = f"{namespace}/{pod_name}"
        if container:
            stream_key += f"/{container}"
        
        # Stop existing stream
        self.stop_log_stream(stream_key)
        
        # Create buffered stream thread
        stream_thread = LogStreamThread(
            self.api_service,
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

    def _periodic_cleanup(self):
        """Periodic cleanup to prevent memory accumulation"""
        if self._shutdown:
            return
            
        # Force garbage collection
        gc.collect()
        
        # Clean up empty buffers
        empty_buffers = [key for key, buffer in self.log_buffers.items() if len(buffer) == 0]
        for key in empty_buffers:
            del self.log_buffers[key]
            
        # Limit total number of buffers
        if len(self.log_buffers) > MAX_STREAM_BUFFERS:
            # Remove oldest buffers
            keys_to_remove = list(self.log_buffers.keys())[:-25]  # Keep only last 25
            for key in keys_to_remove:
                del self.log_buffers[key]
    
    def cleanup(self):
        """Cleanup all streams"""
        self._shutdown = True
        
        # Stop timers
        if hasattr(self, '_flush_timer'):
            self._flush_timer.stop()
        if hasattr(self, '_cleanup_timer'):
            self._cleanup_timer.stop()
        
        # Stop all streams
        for stream_key in list(self.active_streams.keys()):
            self.stop_log_stream(stream_key)
            
        # Clear all buffers
        self.log_buffers.clear()
        self.active_streams.clear()

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            if hasattr(self, '_shutdown') and not self._shutdown:
                self.cleanup()
        except Exception as e:
            logging.error(f"Error in KubernetesLogStreamer destructor: {e}")


class KubernetesLogService:
    """Service for managing Kubernetes log operations"""
    
    def __init__(self, api_service):
        self.api_service = api_service
        self.log_streamer = KubernetesLogStreamer(api_service)
        logging.debug("KubernetesLogService initialized")
    
    def get_pod_logs(self, pod_name: str, namespace: str, container: Optional[str] = None, 
                     tail_lines: int = 100) -> Optional[str]:
        """Get pod logs synchronously"""
        try:
            kwargs = {
                'name': pod_name,
                'namespace': namespace,
                'timestamps': True,
                'tail_lines': tail_lines
            }
            
            if container:
                kwargs['container'] = container
            
            logs = self.api_service.v1.read_namespaced_pod_log(**kwargs)
            return logs if logs else ""
            
        except ApiException as e:
            logging.error(f"API error getting logs for {pod_name}: {e}")
            return None
        except Exception as e:
            logging.error(f"Error getting logs for {pod_name}: {e}")
            return None
    
    def start_log_stream(self, pod_name: str, namespace: str, container: Optional[str] = None, 
                        tail_lines: int = 200):
        """Start streaming logs for a pod"""
        self.log_streamer.start_log_stream(pod_name, namespace, container, tail_lines)
    
    def stop_log_stream(self, pod_name: str, namespace: str, container: Optional[str] = None):
        """Stop streaming logs for a pod"""
        stream_key = f"{namespace}/{pod_name}"
        if container:
            stream_key += f"/{container}"
        self.log_streamer.stop_log_stream(stream_key)
    
    def stop_all_streams(self):
        """Stop all active log streams"""
        self.log_streamer.stop_all_streams()
    
    def get_log_streamer(self) -> KubernetesLogStreamer:
        """Get the log streamer instance for signal connections"""
        return self.log_streamer
    
    def cleanup(self):
        """Cleanup log service resources"""
        logging.debug("Cleaning up KubernetesLogService")
        if self.log_streamer:
            self.log_streamer.cleanup()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            if hasattr(self, 'log_streamer'):
                self.cleanup()
        except Exception as e:
            logging.error(f"Error in KubernetesLogService destructor: {e}")


# Factory function
def create_kubernetes_log_service(api_service) -> KubernetesLogService:
    """Create a new Kubernetes log service instance"""
    return KubernetesLogService(api_service)