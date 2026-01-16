"""
Background Data Processing Worker
Moves heavy data processing off the main UI thread to prevent freezing

NOTE: This file is currently UNUSED. It was created to provide background processing
for PaginatedResourcePage, but PaginatedResourcePage itself is unused. The application
currently handles resource processing differently using the unified resource loader.
Kept for potential future adoption if heavy background processing is needed.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import List, Dict, Any, Optional, Callable
import logging
import time
from datetime import datetime, timezone
import threading
from Utils.thread_manager import is_shutdown_requested
from dateutil import parser as dateutil_parser


class ResourceProcessingWorker(QThread):
    """
    Base worker for processing resources in background thread.
    Handles progress reporting, cancellation, and error handling.
    """

    # Signals
    processing_started = pyqtSignal()
    progress_updated = pyqtSignal(int, str)
    data_processed = pyqtSignal(list)
    processing_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, raw_resources: List[Dict], resource_type: str,
                 batch_size: int = 50, process_func: Optional[Callable] = None):
        super().__init__()
        self.raw_resources = raw_resources or []
        self.resource_type = resource_type
        self.batch_size = batch_size
        self.process_func = process_func

        # Control flags
        self._cancelled = threading.Event()
        self._paused = threading.Event()

        # Statistics
        self.start_time = None
        self.end_time = None
        self.processed_count = 0

        # Cache system removed

        logging.info(
            f"ResourceProcessingWorker created for {len(self.raw_resources)} {resource_type} items")

    def run(self):
        """Main processing loop."""
        try:
            self.start_time = time.time()
            self.processing_started.emit()

            total_items = len(self.raw_resources)
            processed_resources = []

            self.progress_updated.emit(
                0, f"Starting to process {total_items} {self.resource_type}...")

            # Process in batches to allow for progress updates and cancellation
            for batch_start in range(0, total_items, self.batch_size):
                if self._cancelled.is_set():
                    logging.info(f"Processing cancelled at item {batch_start}")
                    return

                # Wait if paused
                while self._paused.is_set() and not self._cancelled.is_set():
                    self.msleep(100)

                if self._cancelled.is_set():
                    return

                # Process batch
                batch_end = min(batch_start + self.batch_size, total_items)
                batch = self.raw_resources[batch_start:batch_end]

                batch_processed = self._process_batch(batch, batch_start)
                processed_resources.extend(batch_processed)

                self.processed_count = len(processed_resources)

                # Update progress
                progress = int((batch_end / total_items) * 100)
                elapsed_time = time.time() - self.start_time
                items_per_second = batch_end / elapsed_time if elapsed_time > 0 else 0

                message = f"Processed {batch_end}/{total_items} {self.resource_type} ({items_per_second:.1f}/sec)"
                self.progress_updated.emit(progress, message)

                # Small delay to prevent overwhelming the UI thread
                self.msleep(1)

            if not self._cancelled.is_set():
                self.end_time = time.time()
                processing_time = self.end_time - self.start_time

                logging.info(
                    f"Processing completed: {len(processed_resources)} items in {processing_time:.2f}s")
                self.progress_updated.emit(
                    100, f"Completed processing {len(processed_resources)} items")
                self.data_processed.emit(processed_resources)

        except Exception as e:
            logging.error(f"Error in resource processing: {e}")
            self.error_occurred.emit(f"Processing error: {str(e)}")
        finally:
            self.processing_finished.emit()

    def _process_batch(self, batch: List[Dict], batch_start: int) -> List[Dict]:
        """Process a batch of resources."""
        processed_batch = []

        for i, resource in enumerate(batch):
            if self._cancelled.is_set():
                break

            try:
                # Process resource directly (no caching)
                if self.process_func:
                    processed = self.process_func(resource)
                else:
                    processed = self._process_single_resource(resource)

                processed_batch.append(processed)

            except Exception as e:
                logging.warning(
                    f"Error processing resource at index {batch_start + i}: {e}")
                # Add original resource with error marker
                error_resource = resource.copy()
                error_resource['_processing_error'] = str(e)
                processed_batch.append(error_resource)

        return processed_batch

    def _process_single_resource(self, resource: Dict) -> Dict:
        """
        Process individual resource - override in subclasses.
        Default implementation returns the resource unchanged.
        """
        return resource

    def cancel(self):
        """Cancel processing."""
        self._cancelled.set()
        logging.info(f"Processing cancelled for {self.resource_type}")

    def pause(self):
        """Pause processing."""
        self._paused.set()
        logging.info(f"Processing paused for {self.resource_type}")

    def resume(self):
        """Resume processing."""
        self._paused.clear()
        logging.info(f"Processing resumed for {self.resource_type}")

    def is_cancelled(self) -> bool:
        """Check if processing is cancelled or shutdown requested."""
        return self._cancelled.is_set() or is_shutdown_requested()

    def is_paused(self) -> bool:
        """Check if processing is paused."""
        return self._paused.is_set()

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        elapsed_time = (self.end_time or time.time()) - \
            (self.start_time or time.time())
        items_per_second = self.processed_count / \
            elapsed_time if elapsed_time > 0 else 0

        return {
            'resource_type': self.resource_type,
            'total_items': len(self.raw_resources),
            'processed_count': self.processed_count,
            'elapsed_time': elapsed_time,
            'items_per_second': round(items_per_second, 2),
            'is_cancelled': self.is_cancelled(),
            'is_paused': self.is_paused()
        }


class PodProcessingWorker(ResourceProcessingWorker):
    """Worker for processing pod resources."""

    def __init__(self, raw_resources: List[Dict]):
        super().__init__(raw_resources, "pods")

    def _process_single_resource(self, resource: Dict) -> Dict:
        """Process a single pod resource."""
        try:
            raw_data = resource.get("raw_data", {})
            if not raw_data:
                # If no raw_data, assume resource is already the raw pod data
                raw_data = resource

            # Extract pod information
            metadata = raw_data.get("metadata", {})
            spec = raw_data.get("spec", {})
            status = raw_data.get("status", {})

            processed = {
                "name": metadata.get("name", "Unknown"),
                "namespace": metadata.get("namespace", "default"),
                "status": self._calculate_pod_status(status),
                "ready": self._calculate_ready_status(status),
                "restarts": self._calculate_restarts(status),
                "age": self._calculate_age(metadata.get("creationTimestamp")),
                "node": spec.get("nodeName", ""),
                "containers": self._count_containers(spec),
                "cpu_requests": self._calculate_cpu_requests(spec),
                "memory_requests": self._calculate_memory_requests(spec),
                "labels": metadata.get("labels", {}),
                "raw_data": raw_data
            }

            return processed

        except Exception as e:
            logging.error(f"Error processing pod: {e}")
            return resource  # Return original on error

    def _calculate_pod_status(self, status: Dict) -> str:
        """Calculate pod status from status dict."""
        try:
            phase = status.get("phase", "Unknown")

            if phase == "Running":
                # Check container states
                container_statuses = status.get("containerStatuses", [])
                if not container_statuses:
                    return "Pending"

                for container_status in container_statuses:
                    state = container_status.get("state", {})
                    if "waiting" in state:
                        waiting = state["waiting"]
                        reason = waiting.get("reason", "")
                        if reason in ["ImagePullBackOff", "ErrImagePull", "CrashLoopBackOff"]:
                            return reason
                        return "Waiting"
                    elif "terminated" in state:
                        terminated = state["terminated"]
                        reason = terminated.get("reason", "")
                        if terminated.get("exitCode", 0) != 0:
                            return f"Error ({reason})"

                return "Running"

            elif phase == "Pending":
                # Check conditions for more specific status
                conditions = status.get("conditions", [])
                for condition in conditions:
                    if condition.get("type") == "PodScheduled" and condition.get("status") == "False":
                        return "Unschedulable"
                return "Pending"

            elif phase in ["Succeeded", "Failed"]:
                return phase

            else:
                return phase

        except Exception:
            return "Unknown"

    def _calculate_ready_status(self, status: Dict) -> str:
        """Calculate ready status string."""
        try:
            container_statuses = status.get("containerStatuses", [])
            if not container_statuses:
                return "0 / 0"

            ready_count = sum(
                1 for cs in container_statuses if cs.get("ready", False))
            total_count = len(container_statuses)

            return f"{ready_count}/{total_count}"
        except (KeyError, TypeError, AttributeError) as e:
            logging.debug(f"Could not calculate ready status: {e}")
            return "0 / 0"
        except Exception as e:
            logging.error(f"Unexpected error calculating ready status: {e}")
            return "0 / 0"

    def _calculate_restarts(self, status: Dict) -> int:
        """Calculate total restart count."""
        try:
            container_statuses = status.get("containerStatuses", [])
            return sum(cs.get("restartCount", 0) for cs in container_statuses)
        except (KeyError, TypeError, AttributeError) as e:
            logging.debug(f"Could not calculate restart count: {e}")
            return 0
        except Exception as e:
            logging.error(f"Unexpected error calculating restart count: {e}")
            return 0

    def _count_containers(self, spec: Dict) -> str:
        """Count containers in pod spec."""
        try:
            containers = spec.get("containers", [])
            init_containers = spec.get("initContainers", [])

            if init_containers:
                return f"{len(containers)}+{len(init_containers)}"
            else:
                return str(len(containers))
        except (KeyError, TypeError, AttributeError) as e:
            logging.debug(f"Could not count containers: {e}")
            return "0"
        except Exception as e:
            logging.error(f"Unexpected error counting containers: {e}")
            return "0"

    def _calculate_cpu_requests(self, spec: Dict) -> str:
        """Calculate total CPU requests."""
        try:
            total_cpu_millicores = 0
            containers = spec.get("containers", [])

            for container in containers:
                resources = container.get("resources", {})
                requests = resources.get("requests", {})
                cpu_request = requests.get("cpu", "0")

                # Parse CPU value
                if cpu_request.endswith("m"):
                    total_cpu_millicores += int(cpu_request[:-1])
                else:
                    total_cpu_millicores += int(float(cpu_request) * 1000)

            if total_cpu_millicores >= 1000:
                return f"{total_cpu_millicores / 1000:.1f}"
            else:
                return f"{total_cpu_millicores}m"

        except (KeyError, TypeError, AttributeError, ValueError) as e:
            logging.debug(f"Could not calculate CPU requests: {e}")
            return "0"
        except Exception as e:
            logging.error(f"Unexpected error calculating CPU requests: {e}")
            return "0"

    def _calculate_memory_requests(self, spec: Dict) -> str:
        """Calculate total memory requests."""
        try:
            total_memory_bytes = 0
            containers = spec.get("containers", [])

            for container in containers:
                resources = container.get("resources", {})
                requests = resources.get("requests", {})
                memory_request = requests.get("memory", "0")

                # Parse memory value
                if memory_request.endswith("Ki"):
                    total_memory_bytes += int(memory_request[:-2]) * 1024
                elif memory_request.endswith("Mi"):
                    total_memory_bytes += int(
                        memory_request[:-2]) * 1024 * 1024
                elif memory_request.endswith("Gi"):
                    total_memory_bytes += int(
                        memory_request[:-2]) * 1024 * 1024 * 1024
                else:
                    total_memory_bytes += int(
                        memory_request) if memory_request.isdigit() else 0

            # Format memory size
            if total_memory_bytes >= 1024 * 1024 * 1024:  # GB
                return f"{total_memory_bytes / (1024 * 1024 * 1024):.1f}Gi"
            elif total_memory_bytes >= 1024 * 1024:  # MB
                return f"{total_memory_bytes / (1024 * 1024):.0f}Mi"
            elif total_memory_bytes >= 1024:  # KB
                return f"{total_memory_bytes / 1024:.0f}Ki"
            else:
                return "0"

        except (KeyError, TypeError, AttributeError, ValueError) as e:
            logging.debug(f"Could not calculate memory requests: {e}")
            return "0"
        except Exception as e:
            logging.error(f"Unexpected error calculating memory requests: {e}")
            return "0"

    def _calculate_age(self, creation_timestamp) -> str:
        """Calculate age from creation timestamp."""
        try:
            if not creation_timestamp:
                return "Unknown"

            # Parse timestamp
            if isinstance(creation_timestamp, str):
                # Parse ISO format
                if creation_timestamp.endswith('Z'):
                    created = datetime.fromisoformat(
                        creation_timestamp.replace('Z', '+00:00'))
                else:
                    created = datetime.fromisoformat(creation_timestamp)
            else:
                # Assume it's already a datetime object
                created = creation_timestamp

            # Ensure timezone aware
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            age_delta = now - created

            days = age_delta.days
            hours = age_delta.seconds // 3600
            minutes = (age_delta.seconds % 3600) // 60

            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"

        except Exception as e:
            logging.debug(f"Error calculating age: {e}")
            return "Unknown"


class EventProcessingWorker(ResourceProcessingWorker):
    """Worker for processing event resources."""

    def __init__(self, raw_resources: List[Dict]):
        super().__init__(raw_resources, "events")

    def _process_single_resource(self, resource: Dict) -> Dict:
        """Process a single event resource."""
        try:
            raw_data = resource.get("raw_data", {})
            if not raw_data:
                raw_data = resource

            metadata = raw_data.get("metadata", {})

            processed = {
                "namespace": metadata.get("namespace", "default"),
                "name": metadata.get("name", "Unknown"),
                "type": raw_data.get("type", "Normal"),
                "reason": raw_data.get("reason", ""),
                "object": self._format_involved_object(raw_data.get("involvedObject", {})),
                "source": self._format_source(raw_data.get("source", {})),
                "message": raw_data.get("message", ""),
                "count": raw_data.get("count", 1),
                "first_timestamp": self._format_timestamp(raw_data.get("firstTimestamp")),
                "last_timestamp": self._format_timestamp(raw_data.get("lastTimestamp")),
                "age": self._calculate_age(raw_data.get("lastTimestamp")),
                "raw_data": raw_data
            }

            return processed

        except Exception as e:
            logging.error(f"Error processing event: {e}")
            return resource

    def _format_involved_object(self, involved_object: Dict) -> str:
        """Format involved object string."""
        try:
            kind = involved_object.get("kind", "")
            name = involved_object.get("name", "")
            return f"{kind}/{name}" if kind and name else "Unknown"
        except (KeyError, TypeError, AttributeError) as e:
            logging.debug(f"Could not format event object: {e}")
            return "Unknown"
        except Exception as e:
            logging.error(f"Unexpected error formatting event object: {e}")
            return "Unknown"

    def _format_source(self, source: Dict) -> str:
        """Format event source string."""
        try:
            component = source.get("component", "")
            host = source.get("host", "")
            if component and host:
                return f"{component}, {host}"
            elif component:
                return component
            elif host:
                return host
            else:
                return "Unknown"
        except (KeyError, TypeError, AttributeError) as e:
            logging.debug(f"Could not format event source: {e}")
            return "Unknown"
        except Exception as e:
            logging.error(f"Unexpected error formatting event source: {e}")
            return "Unknown"

    def _format_timestamp(self, timestamp) -> str:
        """Format timestamp to string."""
        try:
            if not timestamp:
                return ""

            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp

            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError, AttributeError) as e:
            logging.debug(f"Could not format timestamp: {e}")
            return ""
        except Exception as e:
            logging.error(f"Unexpected error formatting timestamp: {e}")
            return ""


class DeploymentProcessingWorker(ResourceProcessingWorker):
    """Worker for processing deployment resources."""

    def __init__(self, raw_resources: List[Dict]):
        super().__init__(raw_resources, "deployments")

    def _process_single_resource(self, resource: Dict) -> Dict:
        """Process a single deployment resource."""
        try:
            raw_data = resource.get("raw_data", {})
            if not raw_data:
                raw_data = resource

            metadata = raw_data.get("metadata", {})
            spec = raw_data.get("spec", {})
            status = raw_data.get("status", {})

            processed = {
                "name": metadata.get("name", "Unknown"),
                "namespace": metadata.get("namespace", "default"),
                "ready": self._calculate_ready_replicas(status),
                "up_to_date": status.get("updatedReplicas", 0),
                "available": status.get("availableReplicas", 0),
                "age": self._calculate_age(metadata.get("creationTimestamp")),
                "strategy": self._get_strategy(spec),
                "conditions": self._format_conditions(status.get("conditions", [])),
                "labels": metadata.get("labels", {}),
                "raw_data": raw_data
            }

            return processed

        except Exception as e:
            logging.error(f"Error processing deployment: {e}")
            return resource

    def _calculate_ready_replicas(self, status: Dict) -> str:
        """Calculate ready replicas string."""
        try:
            desired = status.get("replicas", 0)
            ready = status.get("readyReplicas", 0)
            return f"{ready}/{desired}"
        except (KeyError, TypeError, AttributeError) as e:
            logging.debug(f"Could not calculate deployment replicas: {e}")
            return "0 / 0"
        except Exception as e:
            logging.error(
                f"Unexpected error calculating deployment replicas: {e}")
            return "0 / 0"

    def _get_strategy(self, spec: Dict) -> str:
        """Get deployment strategy."""
        try:
            strategy = spec.get("strategy", {})
            return strategy.get("type", "RollingUpdate")
        except (KeyError, TypeError, AttributeError) as e:
            logging.debug(f"Could not get strategy: {e}")
            return "Unknown"
        except Exception as e:
            logging.error(f"Unexpected error getting strategy: {e}")
            return "Unknown"

    def _format_conditions(self, conditions: List[Dict]) -> str:
        """Format deployment conditions."""
        try:
            if not conditions:
                return "Unknown"

            # Sentinel datetime for missing or unparsable timestamps
            sentinel_dt = datetime(1900, 1, 1, tzinfo=timezone.utc)

            def parse_timestamp(condition: Dict) -> datetime:
                """Parse lastUpdateTime into datetime, returning sentinel for invalid timestamps."""
                timestamp_str = condition.get("lastUpdateTime")
                if not timestamp_str:
                    return sentinel_dt
                try:
                    # Try dateutil.parser.parse first for robustness
                    return dateutil_parser.parse(timestamp_str)
                except (ValueError, dateutil_parser.ParserError):
                    try:
                        # Fallback to datetime.fromisoformat
                        if timestamp_str.endswith('Z'):
                            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        else:
                            return datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        # Return sentinel for unparsable timestamps
                        return sentinel_dt

            # Get the most recent condition using parsed datetime
            latest_condition = max(conditions, key=parse_timestamp)
            condition_type = latest_condition.get("type", "")
            status = latest_condition.get("status", "")

            return f"{condition_type}: {status}"
        except (KeyError, TypeError, AttributeError, IndexError) as e:
            logging.debug(f"Could not format conditions: {e}")
            return "Unknown"
        except Exception as e:
            logging.error(f"Unexpected error formatting conditions: {e}")
            return "Unknown"


def create_processing_worker(resource_type: str, raw_resources: List[Dict]) -> ResourceProcessingWorker:
    """Factory function to create appropriate processing worker."""
    if resource_type.lower() in ["pod", "pods"]:
        return PodProcessingWorker(raw_resources)
    elif resource_type.lower() in ["event", "events"]:
        return EventProcessingWorker(raw_resources)
    elif resource_type.lower() in ["deployment", "deployments"]:
        return DeploymentProcessingWorker(raw_resources)
    else:
        # Generic worker for other resource types
        return ResourceProcessingWorker(raw_resources, resource_type)
