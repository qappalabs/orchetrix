"""
Enhanced Kubernetes Cluster Connector - Single Responsibility Version
Replaces the complex monolithic cluster_connector.py with a clean, maintainable solution.
"""

import logging
import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, Qt, QMetaObject
from enum import Enum

from Utils.kubernetes_client import get_kubernetes_client
from Utils.enhanced_worker import EnhancedBaseWorker
from Utils.thread_manager import get_thread_manager
from Utils.unified_resource_loader import get_unified_resource_loader
from Utils.unified_cache_system import get_unified_cache
from Utils.data_formatters import parse_age_to_seconds, format_age
from log_handler import class_logger

# Maximum age (in seconds) for events included in the issues cache.
# Events older than this threshold are excluded by _event_item_to_issue.
_EVENT_MAX_AGE_SECONDS = 86400  # 24 hours


@dataclass
class ClusterMetrics:
    """Data structure for cluster metrics"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    pods_count: int = 0
    nodes_count: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class NodeInfo:
    """Data structure for processed node information"""
    name: str
    status: str
    roles: List[str]
    cpu_capacity: str
    memory_capacity: str
    disk_capacity: str
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    taints: str = "0"
    version: str = "Unknown"
    age: str = "Unknown"
    raw_data: Optional[Dict] = None


@dataclass
class ConnectionState:
    """Thread-safe connection state"""
    cluster_name: str
    is_connected: bool = False
    is_connecting: bool = False
    last_error: Optional[str] = None
    connected_at: Optional[float] = None
    health_status: 'ClusterHealthStatus' = field(default_factory=lambda: ClusterHealthStatus.UNKNOWN)

    def __post_init__(self):
        self._lock = threading.RLock()

    def update_state(self, connected: bool, connecting: bool = False, error: str = None):
        """Thread-safe state update"""
        with self._lock:
            self.is_connected = connected
            self.is_connecting = connecting
            if error:
                self.last_error = error
            if connected:
                self.connected_at = time.time()
                self.last_error = None
                self.health_status = ClusterHealthStatus.HEALTHY


class ClusterHealthStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ClusterHealthMonitor:
    """
    Monitors cluster health and implements Circuit Breaker pattern.
    Prevents retry storms by blocking connections to known-bad clusters.
    """
    def __init__(self, recovery_timeout: int = 30):
        self._health_states: Dict[str, ClusterHealthStatus] = defaultdict(lambda: ClusterHealthStatus.UNKNOWN)
        self._last_failure_times: Dict[str, float] = {}
        self._recovery_timeout = recovery_timeout
        self._lock = threading.RLock()

    def report_success(self, cluster_name: str):
        """Report a successful operation"""
        with self._lock:
            if self._health_states[cluster_name] != ClusterHealthStatus.HEALTHY:
                logging.info(f"Cluster {cluster_name} recovered and is now HEALTHY")
            self._health_states[cluster_name] = ClusterHealthStatus.HEALTHY
            if cluster_name in self._last_failure_times:
                del self._last_failure_times[cluster_name]

    def report_failure(self, cluster_name: str, error: str):
        """Report a failure (opens circuit if critical)"""
        if not error:
            return
            
        # Only trigger for connection refusal type errors
        critical_errors = ["connection refused", "target machine actively refused", "10061", "timeout"]
        is_critical = any(c in str(error).lower() for c in critical_errors)
        
        if is_critical:
            with self._lock:
                if self._health_states[cluster_name] != ClusterHealthStatus.UNHEALTHY:
                    logging.warning(f"Marking cluster {cluster_name} as UNHEALTHY (Circuit Open) due to: {error}")
                self._health_states[cluster_name] = ClusterHealthStatus.UNHEALTHY
                self._last_failure_times[cluster_name] = time.time()

    def is_healthy(self, cluster_name: str) -> bool:
        """Check if cluster is healthy or ready for retry (auto-recovery)"""
        with self._lock:
            state = self._health_states[cluster_name]
            
            if state == ClusterHealthStatus.HEALTHY or state == ClusterHealthStatus.UNKNOWN:
                return True
                
            # If UNHEALTHY, check for auto-recovery timeout
            last_fail = self._last_failure_times.get(cluster_name, 0)
            if time.time() - last_fail > self._recovery_timeout:
                logging.info(f"Auto-recovering cluster {cluster_name} for health check (Circuit Half-Open)")
                # Tentatively set to UNKNOWN to allow one retry
                self._health_states[cluster_name] = ClusterHealthStatus.UNKNOWN
                return True
                
            return False

    def get_status(self, cluster_name: str) -> ClusterHealthStatus:
        with self._lock:
            return self._health_states[cluster_name]


# DataCache class replaced by unified cache system
# Now using get_unified_cache() for all caching needs


class ClusterConnectionWorker(EnhancedBaseWorker):
    """Worker for establishing cluster connections"""

    def __init__(self, client, cluster_name: str):
        super().__init__(f"cluster_connection_{cluster_name}")
        self.client = client
        self.cluster_name = cluster_name
        self._timeout = 30

    def execute(self) -> Tuple[str, bool, str]:
        """Execute connection attempt"""
        try:
            # Attempt to switch context
            success = self.client.switch_context(self.cluster_name)
            if not success:
                return self.cluster_name, False, "Failed to switch cluster context"

            # Validate connection with version check
            version_info = self.client.version_api.get_code()
            if not version_info:
                return self.cluster_name, False, "Failed to validate cluster connection"

            message = f"Connected to Kubernetes {version_info.git_version}"
            return self.cluster_name, True, message

        except Exception as e:
            error_msg = self._format_error(str(e))
            return self.cluster_name, False, error_msg

    def _format_error(self, error: str) -> str:
        """Format error message for user display"""
        error_lower = error.lower()

        if "docker-desktop" in self.cluster_name.lower() and "refused" in error_lower:
            return "Docker Desktop Kubernetes is not running. Please start Docker Desktop and enable Kubernetes."
        elif "timeout" in error_lower:
            return f"Connection timeout. Check if cluster '{self.cluster_name}' is accessible."
        elif "certificate" in error_lower:
            return f"Certificate error. Check your kubeconfig for '{self.cluster_name}'."
        else:
            return f"Connection failed: {error[:100]}"


class DataLoadWorker(EnhancedBaseWorker):
    """Worker for loading various types of cluster data"""

    def __init__(self, client, data_type: str, cluster_name: str, processor: Callable = None):
        super().__init__(f"{data_type}_load_{cluster_name}")
        self.client = client
        self.data_type = data_type
        self.cluster_name = cluster_name
        self.processor = processor or self._default_processor

    def execute(self) -> Tuple[str, Any]:
        """Execute data loading"""
        try:
            if self.data_type == "nodes":
                data = self.client._get_nodes()
            elif self.data_type == "metrics":
                self.client.get_cluster_metrics_async()
                return self.data_type, None  # Metrics are handled via signals
            elif self.data_type == "issues":
                self.client.get_cluster_issues_async()
                return self.data_type, None  # Issues are handled via signals
            elif self.data_type == "cluster_info":
                data = self.client.get_cluster_info(self.cluster_name)
            else:
                raise ValueError(f"Unknown data type: {self.data_type}")

            processed_data = self.processor(data) if data else None
            return self.data_type, processed_data

        except Exception as e:
            logging.error(f"Error loading {self.data_type} for {self.cluster_name}: {e}")
            raise

    def _default_processor(self, data: Any) -> Any:
        """Default data processor - returns data as-is"""
        return data


@class_logger(log_level=logging.INFO)
class EnhancedClusterConnector(QObject):
    """
    Enhanced Kubernetes Cluster Connector with single responsibility design.
    Replaces the complex monolithic cluster_connector.py.
    """

    # Signals
    connection_started = pyqtSignal(str)
    connection_complete = pyqtSignal(str, bool, str)
    cluster_data_loaded = pyqtSignal(dict)
    node_data_loaded = pyqtSignal(list)
    metrics_data_loaded = pyqtSignal(dict)
    issues_data_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()

        # Core dependencies
        self.kube_client = get_kubernetes_client()
        self.thread_manager = get_thread_manager()

        # State management (thread-safe)
        self._connection_states: Dict[str, ConnectionState] = {}
        self._current_cluster: Optional[str] = None
        self._state_lock = threading.RLock()

        # Data management
        # Use unified cache system instead of custom DataCache
        self._cache = get_unified_cache()

        # Polling management with load detection
        self._polling_active = False
        self._polling_lock = threading.RLock()
        self._events_watch_active = False  # True when watch replaces issues polling
        # QTimer instances are created in _setup_timers so their thread affinity
        # is bound to the UI thread rather than whatever thread built the connector.
        # Shared-Informer-style incremental cache: only holds Warning/Error events
        # updated one item at a time by on_added/on_modified/on_deleted handlers.
        self._issues_delta_cache: Dict[str, Dict] = {}  # keyed by event uid
        # Lock that must be held for all reads and writes of _issues_delta_cache.
        # The watch callbacks run on a background thread; _flush_events_update
        # runs on the main thread — both must synchronise through this lock.
        self._issues_delta_lock = threading.Lock()

        # Load detection for dynamic polling
        self._cluster_load_level = "normal"  # normal, heavy, critical
        self._last_poll_times = {"metrics": 0, "issues": 0}
        self._poll_intervals = {
            "normal": {"metrics": 30000, "issues": 60000},    # 30s/60s for normal load
            "heavy": {"metrics": 60000, "issues": 120000},    # 60s/120s for heavy load
            "critical": {"metrics": 120000, "issues": 300000} # 120s/300s for critical load
        }

        # Health Monitor (Circuit Breaker)
        self.health_monitor = ClusterHealthMonitor(recovery_timeout=30)  # 30s auto-recovery

        # Polling recovery state
        self._metrics_default_interval = 30000
        self._issues_default_interval = 60000
        self._metrics_success_count = 0
        self._issues_success_count = 0
        self._polling_paused = False

        # RBAC watch permission — True until proven otherwise by _check_watch_permission()
        self._watch_verb_allowed = True

        # Shutdown management
        self._shutting_down = False
        self._active_workers = set()
        self._workers_lock = threading.RLock()

        # Initialize
        self._setup_timers()
        self._connect_client_signals()
        self._connect_resource_loader_signals()

        logging.info("Cluster Connector initialized")

    def _setup_timers(self):
        """Initialize and configure timers"""
        # Ensure timers are created on main thread
        from PyQt6.QtWidgets import QApplication
        if self.thread() != QApplication.instance().thread():
            logging.warning("ClusterConnector timers being created from non-main thread - deferring to main thread")
            QMetaObject.invokeMethod(self, "_setup_timers_on_main_thread", Qt.ConnectionType.QueuedConnection)
            return

        # Create timers here so both creation and configuration happen on the
        # UI thread, giving the QTimer instances the correct thread affinity.
        self._metrics_timer = QTimer()
        self._issues_timer = QTimer()
        self._cleanup_timer = QTimer()
        self._events_debounce_timer = QTimer()  # Coalesces rapid event deltas
        self._events_debounce_timer.setSingleShot(True)
        self._events_debounce_timer.setInterval(3000)  # 3 s quiet window

        # Metrics polling timer
        self._metrics_timer.timeout.connect(self._poll_metrics)

        # Issues polling timer
        self._issues_timer.timeout.connect(self._poll_issues)

        # Events watch debounce timer — flushes coalesced deltas every 3 s
        self._events_debounce_timer.timeout.connect(self._flush_events_update)

        # Cache cleanup timer - reduced frequency for better performance
        self._cleanup_timer.timeout.connect(self._cleanup_cache)
        self._cleanup_timer.start(300000)  # Cleanup every 5 minutes instead of 1 minute

    @pyqtSlot()
    def _setup_timers_on_main_thread(self):
        """Setup timers on main thread - called via QMetaObject.invokeMethod"""
        self._setup_timers()

    def _connect_client_signals(self):
        """Connect to Kubernetes client signals"""
        try:
            # Disconnect existing connections first
            try:
                self.kube_client.cluster_info_loaded.disconnect()
                self.kube_client.cluster_metrics_updated.disconnect()
                self.kube_client.cluster_issues_updated.disconnect()
                self.kube_client.error_occurred.disconnect()
            except (TypeError, RuntimeError):
                pass  # No existing connections

            # Connect signals
            self.kube_client.cluster_info_loaded.connect(self._handle_cluster_info)
            self.kube_client.cluster_metrics_updated.connect(self._handle_metrics_update)
            self.kube_client.cluster_issues_updated.connect(self._handle_issues_update)
            self.kube_client.error_occurred.connect(self._handle_client_error)

        except Exception as e:
            logging.error(f"Error connecting client signals: {e}")

    def _connect_resource_loader_signals(self):
        """Connect to unified resource loader signals"""
        try:
            unified_loader = get_unified_resource_loader()

            # Connect to resource loading completion signal
            unified_loader.loading_completed.connect(self._handle_resource_loading_completed)
            unified_loader.loading_error.connect(self._handle_resource_loading_error)

            logging.debug("Connected to unified resource loader signals")
        except Exception as e:
            logging.error(f"Error connecting resource loader signals: {e}")

    def _handle_resource_loading_completed(self, resource_type: str, load_result):
        """Handle completion of resource loading from unified loader"""
        try:
            if resource_type == "nodes" and load_result.success:
                # The unified loader already processed the data into dictionaries
                # No need to process again - just emit the processed data
                nodes_data = load_result.items

                logging.debug(f"Received {len(nodes_data)} processed nodes from unified loader")

                # Only cache and emit non-empty node data
                # Empty results could be from transient issues (cluster disconnect, API error)
                # and we don't want to overwrite valid cached data with empty results
                if nodes_data:
                    # Cache the nodes data first to ensure consistency with get_cached_data
                    if self.current_cluster:
                        cache_key = f"{self.current_cluster}:nodes"
                        self._cache.cache_resources('cluster_data', cache_key, nodes_data)

                    self.node_data_loaded.emit(nodes_data)
                    logging.debug(f"Emitted {len(nodes_data)} processed nodes to UI")
                else:
                    logging.warning("Received empty nodes data from unified loader - not caching or emitting")

        except Exception as e:
            logging.error(f"Error handling resource loading completion: {e}")
            self.error_occurred.emit(resource_type, str(e))

    def _handle_resource_loading_error(self, resource_type: str, error_message: str):
        """Handle resource loading errors from unified loader"""
        logging.error(f"Resource loading error for {resource_type}: {error_message}")
        self.error_occurred.emit(resource_type, error_message)

    @property
    def current_cluster(self) -> Optional[str]:
        """Thread-safe current cluster getter"""
        with self._state_lock:
            return self._current_cluster

    def connect_to_cluster(self, cluster_name: str) -> None:
        """Connect to a Kubernetes cluster"""
        if self._shutting_down:
            return

        with self._state_lock:
            # Initialize connection state if needed
            if cluster_name not in self._connection_states:
                self._connection_states[cluster_name] = ConnectionState(cluster_name)

            connection_state = self._connection_states[cluster_name]

            # Check if already connected
            if connection_state.is_connected:
                logging.info(f"Already connected to {cluster_name}")
                self.connection_complete.emit(cluster_name, True, "Already connected")
                return

            # Check if currently connecting
            if connection_state.is_connecting:
                logging.info(f"Already connecting to {cluster_name}")
                return

            # Update state and start connection
            connection_state.update_state(connected=False, connecting=True)

        # CHECK HEALTH (Circuit Breaker)
        if not self.health_monitor.is_healthy(cluster_name):
            logging.warning(f"Connection blocked to unhealthy cluster {cluster_name} (Circuit Open)")
            # Emit error immediately without attempting connection
            self.connection_complete.emit(cluster_name, False, "Cluster is unhealthy/unreachable (Circuit Open)")
            self.error_occurred.emit("connection", f"Connection to {cluster_name} blocked due to recent failures")
            
            # Reset connecting state
            with self._state_lock:
                 if cluster_name in self._connection_states:
                    self._connection_states[cluster_name].update_state(connected=False, connecting=False)
            return

        self.connection_started.emit(cluster_name)
        self._start_connection_worker(cluster_name)

    def _start_connection_worker(self, cluster_name: str) -> None:
        """Start connection worker for cluster"""
        worker = ClusterConnectionWorker(self.kube_client, cluster_name)

        # Setup worker callbacks
        worker.signals.finished.connect(self._handle_connection_complete)
        worker.signals.error.connect(lambda error: self._handle_connection_error(cluster_name, str(error)))

        # Track worker
        with self._workers_lock:
            self._active_workers.add(worker)

        # Submit to thread manager
        self.thread_manager.submit_worker(f"connect_{cluster_name}", worker)

    def _handle_connection_complete(self, result: Tuple[str, bool, str]) -> None:
        """Handle connection completion"""
        if self._shutting_down:
            return

        cluster_name, success, message = result

        with self._state_lock:
            if cluster_name in self._connection_states:
                self._connection_states[cluster_name].update_state(
                    connected=success,
                    connecting=False,
                    error=None if success else message
                )

                if success:
                    self._current_cluster = cluster_name

        self.connection_complete.emit(cluster_name, success, message)

        # Start data loading and polling if successful
        # Report success to health monitor
        if success:
            self.health_monitor.report_success(cluster_name)
            # Check whether the cluster allows the 'watch' verb.  If not, the
            # ResourceWatchManager would silently fail, so we degrade gracefully
            # to polling-only mode before starting data loading.
            self._update_watch_permission(cluster_name)
            self._start_data_loading(cluster_name)
            self._start_polling()
        else:
            # Report failure (managed in _handle_connection_error but added here for completeness)
            self.health_monitor.report_failure(cluster_name, message)

    def _check_watch_permission(self) -> bool:
        """Query SelfSubjectAccessReview to check if the 'watch' verb is allowed on events.

        'events' is the resource actually used by the watch that has no fallback:
        if the events watch is denied it dies silently on its background thread
        (start_watch never raises) while issues polling stays suppressed, leaving
        the issues view permanently empty.  The node watch — gated by the same
        flag — always has an unconditional LIST path, so probing events is the
        decision that matters.  Returns True when the check passes or when the
        API itself is unavailable (fail-open so we don't break clusters that
        don't expose the authorization API).
        """
        try:
            from kubernetes.client import (
                AuthorizationV1Api,
                V1SelfSubjectAccessReview,
                V1SelfSubjectAccessReviewSpec,
                V1ResourceAttributes,
            )
            auth_api = AuthorizationV1Api(self.kube_client.v1.api_client)
            review = V1SelfSubjectAccessReview(
                spec=V1SelfSubjectAccessReviewSpec(
                    resource_attributes=V1ResourceAttributes(
                        verb='watch',
                        resource='events',
                        group='',
                    )
                )
            )
            response = auth_api.create_self_subject_access_review(review)
            allowed = getattr(response.status, 'allowed', True)
            logging.info(f"RBAC watch permission check: {'allowed' if allowed else 'DENIED'}")
            return allowed
        except Exception as e:
            # Fail open — if we can't check, assume watch is allowed
            logging.debug(f"RBAC watch permission check failed (assuming allowed): {e}")
            return True

    def _update_watch_permission(self, cluster_name: str) -> None:
        """Check watch RBAC permission and update self._watch_verb_allowed.

        Centralises the check-log-assign pattern that is needed both after a
        fresh connection (_handle_connection_complete) and when re-initialising
        the data pipeline for an already-connected cluster
        (initialize_data_pipeline).
        """
        watch_allowed = self._check_watch_permission()
        if not watch_allowed:
            logging.warning(
                f"Cluster {cluster_name}: 'watch' verb denied by RBAC — "
                "falling back to polling-only mode"
            )
            self._watch_verb_allowed = False
        else:
            self._watch_verb_allowed = True

    def _handle_connection_error(self, cluster_name: str, error_message: str) -> None:
        """Handle connection errors"""
        with self._state_lock:
            if cluster_name in self._connection_states:
                self._connection_states[cluster_name].update_state(
                    connected=False,
                    connecting=False,
                    error=error_message
                )

        self.connection_complete.emit(cluster_name, False, error_message)
        self.error_occurred.emit("connection", error_message)

    def _start_data_loading(self, cluster_name: str) -> None:
        """Start loading initial data for cluster"""
        # Load cluster info
        self._start_data_worker("cluster_info", cluster_name)

        # Start node watch stream only when the 'watch' verb is allowed.
        # _watch_verb_allowed is set by _update_watch_permission() during connection.
        if self._watch_verb_allowed:
            try:
                unified_loader = get_unified_resource_loader()
                unified_loader.start_node_watch()
            except Exception as e:
                logging.warning(f"Failed to start node watch, falling back to LIST: {e}")
        else:
            logging.info("Skipping node watch — watch verb denied by RBAC, using LIST polling")

        # Load nodes (will use watch cache if available, else LIST)
        self._start_data_worker("nodes", cluster_name, self._process_nodes_data)

        # Metrics via signal; issues initial fetch is deferred to _start_polling
        # so it can be skipped when the events watch provides live data instead.
        self._start_data_worker("metrics", cluster_name)

    def _start_data_worker(self, data_type: str, cluster_name: str, processor: Callable = None) -> None:
        """Start a data loading worker"""
        worker = DataLoadWorker(self.kube_client, data_type, cluster_name, processor)

        # Setup callbacks
        worker.signals.finished.connect(self._handle_data_loaded)
        worker.signals.error.connect(lambda error: self._handle_data_error(data_type, str(error)))

        # Track worker
        with self._workers_lock:
            self._active_workers.add(worker)

        # Submit to thread manager
        self.thread_manager.submit_worker(f"{data_type}_{cluster_name}", worker)

    def _handle_data_loaded(self, result: Tuple[str, Any]) -> None:
        """Handle data loading completion"""
        if self._shutting_down:
            return

        data_type, data = result

        if data is None:
            return  # Some data types (metrics, issues) are handled via signals

        # Cache the data
        cache_key = f"{self.current_cluster}:{data_type}"
        self._cache.cache_resources('cluster_data', cache_key, data)

        # Emit appropriate signal
        if data_type == "cluster_info":
            self.cluster_data_loaded.emit(data)
        elif data_type == "nodes":
            self.node_data_loaded.emit(data)

    def _handle_data_error(self, data_type: str, error_message: str) -> None:
        """Handle data loading errors"""
        logging.error(f"Error loading {data_type}: {error_message}")
        self.error_occurred.emit(f"{data_type}_loading", error_message)

    def _process_nodes_data(self, raw_nodes: List) -> List[NodeInfo]:
        """Process raw Kubernetes node objects into NodeInfo objects"""
        if not raw_nodes:
            return []

        processed_nodes = []

        for node in raw_nodes:
            try:
                # Extract basic information
                node_name = node.metadata.name
                node_labels = node.metadata.labels or {}

                # Determine status
                conditions = node.status.conditions or []
                status = "Unknown"
                for condition in conditions:
                    if condition.type == "Ready":
                        status = "Ready" if condition.status == "True" else "NotReady"
                        break

                # Extract capacity
                capacity = node.status.capacity or {}
                cpu_capacity = capacity.get("cpu", "")
                memory_capacity = self._format_memory_capacity(capacity.get("memory", ""))
                storage_capacity = self._format_storage_capacity(capacity.get("ephemeral-storage", ""))

                # Extract roles
                roles = self._extract_node_roles(node_labels)

                # Extract other info
                taints_count = len(node.spec.taints) if node.spec.taints else 0
                kubelet_version = node.status.node_info.kubelet_version if node.status.node_info else "Unknown"
                age = self._calculate_age(node.metadata.creation_timestamp)

                # Create NodeInfo object
                node_info = NodeInfo(
                    name=node_name,
                    status=status,
                    roles=roles,
                    cpu_capacity=cpu_capacity,
                    memory_capacity=memory_capacity,
                    disk_capacity=storage_capacity,
                    taints=str(taints_count),
                    version=kubelet_version,
                    age=age,
                    raw_data=self.kube_client.v1.api_client.sanitize_for_serialization(node)
                )

                processed_nodes.append(node_info)

            except Exception as e:
                meta = getattr(node, "metadata", None)
                node_name = getattr(meta, "name", "unknown")
                logging.error(f"Error processing node {node_name}: {e}")
                continue

        logging.info(f"Processed {len(processed_nodes)} nodes")
        return processed_nodes

    def _format_memory_capacity(self, memory_str: str) -> str:
        """Format memory capacity for display"""
        if not memory_str:
            return ""
        from Utils.data_formatters import parse_memory_value
        parsed = parse_memory_value(memory_str)
        return parsed.formatted if parsed.value else memory_str

    def _format_storage_capacity(self, storage_str: str) -> str:
        """Format storage capacity for display"""
        return self._format_memory_capacity(storage_str)  # Same logic

    def _extract_node_roles(self, labels: Dict[str, str]) -> List[str]:
        """Extract node roles from labels"""
        roles = []
        for label_key in labels:
            if "node-role.kubernetes.io/" in label_key:
                role = label_key.replace("node-role.kubernetes.io/", "")
                if role:
                    roles.append(role)

        return roles if roles else ["<none>"]

    def _calculate_age(self, creation_timestamp) -> str:
        """Calculate age string from creation timestamp"""
        return format_age(creation_timestamp)

    def _start_polling(self) -> None:
        """Start polling for metrics; replace issues polling with an events watch."""
        with self._polling_lock:
            if self._polling_active or self._shutting_down:
                return

            self._polling_active = True

            # Start with appropriate intervals based on current load level
            current_intervals = self._poll_intervals[self._cluster_load_level]

            if hasattr(self, '_metrics_timer') and self._metrics_timer:
                self._metrics_timer.start(current_intervals["metrics"])
                logging.info(f"Started metrics polling every {current_intervals['metrics']}ms ({self._cluster_load_level} load)")

            # Replace issues polling with a server-filtered events watch.
            # field_selector keeps only Warning/Error events on the wire.
            # Delta handlers (Shared Informer pattern) update _issues_delta_cache
            # one item at a time — no full-list copies on each delta.
            # Only start the events watch when RBAC allows the 'watch' verb
            # (_watch_verb_allowed is set by _update_watch_permission during
            # connection). If watch is denied, start_watch can fail silently
            # while issues polling stays suppressed, leaving the issues view
            # empty — so we fall through to polling, matching the node watch.
            if self._watch_verb_allowed:
                try:
                    unified_loader = get_unified_resource_loader()
                    unified_loader.start_watch(
                        'events',
                        list_kwargs={'field_selector': 'type!=Normal'},
                        on_added=self._on_event_added,
                        on_modified=self._on_event_modified,
                        on_deleted=self._on_event_deleted,
                    )
                    self._events_watch_active = True
                    logging.info("Events watch started (field_selector=type!=Normal) — "
                                 "issues polling timer suppressed")
                except Exception as e:
                    logging.warning(f"Failed to start events watch, falling back to issues polling: {e}")
                    self._events_watch_active = False
            else:
                logging.info("Skipping events watch — watch verb denied by RBAC, using issues polling")
                self._events_watch_active = False

            if not self._events_watch_active:
                # No events watch — fire a one-time snapshot fetch then start the timer
                if self.current_cluster:
                    self._start_data_worker("issues", self.current_cluster)
                if hasattr(self, '_issues_timer') and self._issues_timer:
                    self._issues_timer.start(current_intervals["issues"])
                    logging.info(f"Started issues polling every {current_intervals['issues']}ms ({self._cluster_load_level} load)")

    def _stop_polling(self) -> None:
        """Stop all polling and tear down the events watch if active."""
        with self._polling_lock:
            self._polling_active = False
            if hasattr(self, '_metrics_timer') and self._metrics_timer:
                self._metrics_timer.stop()
            if hasattr(self, '_issues_timer') and self._issues_timer:
                self._issues_timer.stop()

        if self._events_watch_active:
            try:
                unified_loader = get_unified_resource_loader()
                unified_loader.stop_watch('events')
            except Exception as e:
                logging.debug(f"Error stopping events watch: {e}")
            finally:
                self._events_watch_active = False
                self._events_debounce_timer.stop()  # cancel any pending flush racing the cache clear
                with self._issues_delta_lock:
                    self._issues_delta_cache.clear()

    def stop_polling(self) -> None:
        """Public method to stop all polling - calls internal _stop_polling"""
        self._stop_polling()

    def pause_polling(self) -> None:
        """Pause polling timers while UI is not visible. Preserves polling state
        so resume_polling() can restart at the correct adaptive interval.
        The events watch keeps running in the background regardless of visibility."""
        with self._polling_lock:
            if not self._polling_active:
                return
            self._polling_paused = True
            if hasattr(self, '_metrics_timer') and self._metrics_timer:
                self._metrics_timer.stop()
            # Only stop issues timer when not using the watch stream
            if not self._events_watch_active and hasattr(self, '_issues_timer') and self._issues_timer:
                self._issues_timer.stop()
            logging.debug("Connector polling paused (UI not visible)")

    def resume_polling(self) -> None:
        """Resume polling timers when UI becomes visible again."""
        with self._polling_lock:
            if not self._polling_active or not self._polling_paused:
                return
            self._polling_paused = False

            current_intervals = self._poll_intervals[self._cluster_load_level]
            if hasattr(self, '_metrics_timer') and self._metrics_timer:
                self._metrics_timer.start(current_intervals["metrics"])
            # Only restart issues timer when not using the watch stream
            if not self._events_watch_active and hasattr(self, '_issues_timer') and self._issues_timer:
                self._issues_timer.start(current_intervals["issues"])
            logging.debug(f"Connector polling resumed ({self._cluster_load_level} load)")

    def _poll_metrics(self) -> None:
        """Poll for cluster metrics with load detection"""
        if self._shutting_down or not self.current_cluster:
            return

        try:
            start_time = time.time()
            self.kube_client.get_cluster_metrics_async()
            poll_time = (time.time() - start_time) * 1000

            # Update load level based on polling performance
            # Update load level and success count
            self._update_load_level("metrics", poll_time)
            
            # Handle recovery logic
            self._metrics_success_count += 1
            if self._metrics_success_count >= 3:
                self._adjust_polling_intervals()
                # We don't reset count here to avoid constant resets, 
                # but _adjust_polling_intervals will ensure we are at the target interval

        except Exception as e:
            logging.warning(f"Error polling metrics: {e}")
            # Increase polling interval on errors
            self._adjust_polling_on_error("metrics")

    def _poll_issues(self) -> None:
        """Poll for cluster issues with load detection"""
        if self._shutting_down or not self.current_cluster:
            return

        try:
            start_time = time.time()
            self.kube_client.get_cluster_issues_async()
            poll_time = (time.time() - start_time) * 1000

            # Update load level based on polling performance
            # Update load level and success count
            self._update_load_level("issues", poll_time)
            
            # Handle recovery logic
            self._issues_success_count += 1
            if self._issues_success_count >= 3:
                self._adjust_polling_intervals()

        except Exception as e:
            logging.warning(f"Error polling issues: {e}")
            # Increase polling interval on errors
            self._adjust_polling_on_error("issues")

    # ── Shared-Informer delta handlers for the events watch ──────────────────

    def _event_item_to_issue(self, item: dict) -> Optional[dict]:
        """Convert a single processed event item to the ClusterPage issues format.
        Returns None if the event should be excluded (Normal type or too old)."""
        raw = item.get('raw_data') or {}
        event_type = raw.get('type') or ''

        # Server-side field_selector already blocks Normal events; guard anyway.
        if event_type == 'Normal':
            return None

        created = item.get('created')
        if created:
            try:
                now = datetime.now(timezone.utc)
                if not getattr(created, 'tzinfo', None):
                    created = created.replace(tzinfo=timezone.utc)
                if (now - created).total_seconds() > _EVENT_MAX_AGE_SECONDS:
                    return None
            except Exception:
                pass

        involved = raw.get('involvedObject') or {}
        obj_ref = (
            f"{involved.get('kind', '')}/{involved.get('name', '')}"
            if involved else item.get('name', 'Unknown')
        )
        return {
            'type': event_type or 'Warning',
            'reason': raw.get('reason') or 'Unknown',
            'message': (raw.get('message') or 'No message')[:200],
            'object': obj_ref,
            'age': item.get('age', 'Unknown'),
            'namespace': item.get('namespace') or 'default',
            '_uid': item.get('uid') or item.get('name', ''),
            # Kept so _flush_events_update can re-check the TTL for entries that
            # are added once and never updated. 'age' is frozen at insert time
            # and cannot be used for this.
            '_created': created,
        }

    @pyqtSlot()
    def _start_events_debounce_timer(self) -> None:
        """Start (or restart) the debounce timer on the main thread.

        Must only be called on the thread that owns _events_debounce_timer.
        The delta handlers dispatch here via QMetaObject.invokeMethod with
        QueuedConnection so the call is always delivered to the main thread.
        """
        # A queued start can arrive after _stop_polling has torn the watch down
        # and cleared the delta cache; ignore it so the timer is not resurrected.
        if self._shutting_down or not self._events_watch_active:
            return
        self._events_debounce_timer.start()

    def _on_event_added(self, item: dict) -> None:
        """AddFunc: insert one event into the incremental issues cache."""
        if self._shutting_down or not self._events_watch_active:
            return
        uid = item.get('uid') or item.get('name', '')
        if not uid:
            return
        issue = self._event_item_to_issue(item)
        with self._issues_delta_lock:
            if issue:
                self._issues_delta_cache[uid] = issue
        # Marshal timer.start() to the main thread — QTimer must only be
        # started from its owning thread; this callback runs on the watcher thread.
        QMetaObject.invokeMethod(self, "_start_events_debounce_timer", Qt.ConnectionType.QueuedConnection)

    def _on_event_modified(self, item: dict) -> None:
        """UpdateFunc: update one event in the incremental issues cache."""
        if self._shutting_down or not self._events_watch_active:
            return
        uid = item.get('uid') or item.get('name', '')
        if not uid:
            return
        issue = self._event_item_to_issue(item)
        with self._issues_delta_lock:
            if issue:
                self._issues_delta_cache[uid] = issue
            else:
                # Event may have aged out — remove it
                self._issues_delta_cache.pop(uid, None)
        QMetaObject.invokeMethod(self, "_start_events_debounce_timer", Qt.ConnectionType.QueuedConnection)

    def _on_event_deleted(self, uid: str) -> None:
        """DeleteFunc: remove one event from the incremental issues cache."""
        if self._shutting_down or not self._events_watch_active:
            return
        with self._issues_delta_lock:
            self._issues_delta_cache.pop(uid, None)
        QMetaObject.invokeMethod(self, "_start_events_debounce_timer", Qt.ConnectionType.QueuedConnection)

    def _flush_events_update(self) -> None:
        """Debounce callback: prune stale entries then emit the issues cache to the UI."""
        if self._shutting_down:
            return
        try:
            # Snapshot the cache under the lock (minimal hold time) so that
            # watcher-thread mutations don't race with iteration here.
            # First prune entries whose creation time is now past the max age:
            # an event added once and never updated would otherwise outlive the
            # TTL applied in _event_item_to_issue.
            now = datetime.now(timezone.utc)
            with self._issues_delta_lock:
                expired = []
                for uid, issue in self._issues_delta_cache.items():
                    created = issue.get('_created')
                    if not created:
                        continue
                    try:
                        if not getattr(created, 'tzinfo', None):
                            created = created.replace(tzinfo=timezone.utc)
                        if (now - created).total_seconds() > _EVENT_MAX_AGE_SECONDS:
                            expired.append(uid)
                            continue
                        # Refresh the displayed age (and the sort key). The
                        # stored value is frozen at insert time because age-only
                        # MODIFIED events are filtered out by _VOLATILE_KEYS in
                        # the watch loop, so without this the UI age would never
                        # advance for long-lived warnings.
                        issue['age'] = format_age(created)
                    except Exception:
                        pass
                for uid in expired:
                    self._issues_delta_cache.pop(uid, None)
                # Emit even when empty so the UI clears after the last event is
                # deleted or aged out (do not early-return on an empty cache).
                snapshot = list(self._issues_delta_cache.values())

            # Sort by parsed age (ascending = newest first).
            # parse_age_to_seconds returns 0 for unparseable strings; those
            # sort first which is an acceptable fallback for ambiguous ages.
            issues = sorted(
                snapshot,
                key=lambda x: parse_age_to_seconds(x.get('age', ''))
            )[:50]
            self._handle_issues_update(issues)
        except Exception as e:
            logging.debug(f"ClusterConnector: error flushing events update: {e}")

    def _update_load_level(self, poll_type: str, poll_time_ms: float):
        """Update cluster load level based on polling performance"""
        self._last_poll_times[poll_type] = poll_time_ms

        # Calculate average poll time only over measured (non-zero) entries
        measured_times = [t for t in self._last_poll_times.values() if t > 0]
        if not measured_times:
            return
        avg_poll_time = sum(measured_times) / len(measured_times)

        # Determine load level based on response times
        old_level = self._cluster_load_level

        if avg_poll_time > 5000:  # > 5 seconds indicates critical load
            new_level = "critical"
        elif avg_poll_time > 2000:  # > 2 seconds indicates heavy load
            new_level = "heavy"
        else:
            new_level = "normal"

        # Update load level and adjust polling if needed
        if new_level != old_level:
            self._cluster_load_level = new_level
            self._adjust_polling_intervals()
            logging.info(f"Cluster load level changed from {old_level} to {new_level} (avg poll time: {avg_poll_time:.1f}ms)")

    def _adjust_polling_intervals(self):
        """Adjust polling intervals based on current load level"""
        if not self._polling_active:
            return

        current_intervals = self._poll_intervals[self._cluster_load_level]

        with self._polling_lock:
            # Update metrics timer
            if hasattr(self, '_metrics_timer') and self._metrics_timer and self._metrics_timer.isActive():
                self._metrics_timer.setInterval(current_intervals["metrics"])

            # Update issues timer
            if hasattr(self, '_issues_timer') and self._issues_timer and self._issues_timer.isActive():
                self._issues_timer.setInterval(current_intervals["issues"])

        logging.debug(f"Adjusted polling intervals to {current_intervals} for {self._cluster_load_level} load")

    def _adjust_polling_on_error(self, poll_type: str):
        """Adjust polling interval when errors occur"""
        try:
            # Temporarily increase the specific timer interval on errors
            if poll_type == "metrics" and hasattr(self, '_metrics_timer') and self._metrics_timer:
                current_interval = self._metrics_timer.interval()
                new_interval = min(current_interval * 2, 300000)  # Max 5 minutes
                self._metrics_timer.setInterval(new_interval)
                self._metrics_success_count = 0  # Reset success counter on error
                logging.debug(f"Increased metrics polling interval to {new_interval}ms due to error")

            elif poll_type == "issues" and hasattr(self, '_issues_timer') and self._issues_timer:
                current_interval = self._issues_timer.interval()
                new_interval = min(current_interval * 2, 600000)  # Max 10 minutes
                self._issues_timer.setInterval(new_interval)
                self._issues_success_count = 0  # Reset success counter on error
                logging.debug(f"Increased issues polling interval to {new_interval}ms due to error")

        except Exception as e:
            logging.error(f"Error adjusting polling on error: {e}")

    def _handle_cluster_info(self, info: Dict) -> None:
        """Handle cluster info updates from client"""
        if self._shutting_down:
            return

        cluster_name = getattr(self.kube_client, 'current_cluster', self.current_cluster)
        if cluster_name:
            cache_key = f"{cluster_name}:cluster_info"
            self._cache.cache_resources('cluster_info', cache_key, info)

        self.cluster_data_loaded.emit(info)

    def _handle_metrics_update(self, metrics: Dict) -> None:
        """Handle metrics updates from client"""
        if self._shutting_down:
            return

        cluster_name = getattr(self.kube_client, 'current_cluster', self.current_cluster)
        if cluster_name:
            cache_key = f"{cluster_name}:metrics"
            self._cache.cache_resources('metrics', cache_key, metrics)

        self.metrics_data_loaded.emit(metrics)

    def _handle_issues_update(self, issues: List) -> None:
        """Handle issues updates from client"""
        if self._shutting_down:
            return

        cluster_name = getattr(self.kube_client, 'current_cluster', self.current_cluster)
        if cluster_name:
            cache_key = f"{cluster_name}:issues"
            self._cache.cache_resources('issues', cache_key, issues)

        self.issues_data_loaded.emit(issues)

    def _handle_client_error(self, error_message: str) -> None:
        """Handle Kubernetes client errors"""
        if self._shutting_down:
            return

        # Filter out non-critical errors
        error_lower = error_message.lower()
        if any(keyword in error_lower for keyword in [
            'connection refused', 'timeout', 'certificate', 'authentication',
            'authorization', 'permission denied', 'config'
        ]):
            self.error_occurred.emit("kubernetes", error_message)
        else:
            logging.warning(f"Kubernetes client error (suppressed): {error_message}")

    def _cleanup_cache(self) -> None:
        """Periodic cache cleanup - handled by unified cache system"""
        try:
            self._cache.optimize_caches()
            logging.debug("Cache optimization completed")
        except Exception as e:
            logging.error(f"Error during cache cleanup: {e}")

    def disconnect_cluster(self, cluster_name: str) -> None:
        """Disconnect from a cluster"""
        with self._state_lock:
            if cluster_name in self._connection_states:
                self._connection_states[cluster_name].update_state(connected=False)

            if self._current_cluster == cluster_name:
                self._current_cluster = None
                self._stop_polling()

                # Stop all watch streams
                try:
                    unified_loader = get_unified_resource_loader()
                    unified_loader.stop_all_watches()
                except Exception as e:
                    logging.debug(f"Error stopping watches: {e}")

        # Clear cache for this cluster
        # Clear cache for this cluster using specific keys
        self._cache.clear_resource_cache('metrics', f'{cluster_name}:metrics')
        self._cache.clear_resource_cache('issues', f'{cluster_name}:issues')
        self._cache.clear_resource_cache('cluster_info', f'{cluster_name}:cluster_info')
        self._cache.clear_resource_cache('cluster_data', f'{cluster_name}:nodes')

        logging.info(f"Disconnected from cluster: {cluster_name}")

    def load_nodes(self):
        """Load nodes data using unified resource loader"""
        try:
            unified_loader = get_unified_resource_loader()
            operation_id = unified_loader.load_resources_async('nodes')
            logging.debug(f"Started loading nodes, operation_id: {operation_id}")
        except Exception as e:
            error_msg = f"Failed to load nodes: {e}"
            logging.error(error_msg)
            self.error_occurred.emit("nodes", error_msg)

    def load_metrics(self):
        """Load cluster metrics data"""
        try:
            if hasattr(self.kube_client, 'get_cluster_metrics_async'):
                logging.debug("Loading cluster metrics...")
                self.kube_client.get_cluster_metrics_async()
            else:
                logging.warning("Kubernetes client does not support metrics loading")
        except Exception as e:
            error_msg = f"Failed to load metrics: {e}"
            logging.error(error_msg)
            self.error_occurred.emit("metrics", error_msg)

    def load_issues(self):
        """Load cluster issues data"""
        try:
            if hasattr(self.kube_client, 'get_cluster_issues_async'):
                logging.debug("Loading cluster issues...")
                self.kube_client.get_cluster_issues_async()
            else:
                logging.warning("Kubernetes client does not support issues loading")
        except Exception as e:
            error_msg = f"Failed to load issues: {e}"
            logging.error(error_msg)
            self.error_occurred.emit("issues", error_msg)

    def get_cached_data(self, cluster_name: str) -> Dict[str, Any]:
        """Get cached data for a cluster"""
        cached_data = {}

        data_types = ["cluster_info", "metrics", "issues", "nodes"]
        
        # Map data types to resource types
        type_mapping = {
            "cluster_info": "cluster_info",
            "metrics": "metrics",
            "issues": "issues",
            "nodes": "cluster_data"
        }
        
        for data_type in data_types:
            cache_key = f"{cluster_name}:{data_type}"
            resource_type = type_mapping.get(data_type, "cluster_data")
            
            data = self._cache.get_cached_resources(resource_type, cache_key)
            if data:
                cached_data[data_type] = data

        return cached_data

    def get_connection_state(self, cluster_name: str) -> str:
        """Get current connection state for a cluster"""
        with self._state_lock:
            if cluster_name not in self._connection_states:
                return "disconnected"

            state = self._connection_states[cluster_name]
            if state.is_connected:
                return "connected"
            elif state.is_connecting:
                return "connecting"
            else:
                return "disconnected"

    def set_current_cluster(self, cluster_name: str) -> None:
        """Set the current cluster (called from ClusterView or cluster_state_manager)"""
        with self._state_lock:
            if cluster_name != self._current_cluster:
                logging.info(f"Setting current cluster to {cluster_name}")
                self._current_cluster = cluster_name

                # Create connection state if it doesn't exist, then mark as connected
                # This ensures pages checking get_connection_state() see the correct state
                if cluster_name not in self._connection_states:
                    self._connection_states[cluster_name] = ConnectionState(cluster_name)
                self._connection_states[cluster_name].update_state(connected=True)

    def initialize_data_pipeline(self, cluster_name: str) -> None:
        """Initialize data loading and polling for an already-connected cluster.

        Called by ClusterStateManager after a successful cluster switch to restart
        watch streams, data workers, and polling that were stopped when the old
        cluster was disconnected. Without this, pages would show empty data until
        the user manually refreshes.
        """
        if self._shutting_down:
            return

        logging.info(f"Initializing data pipeline for cluster: {cluster_name}")

        # Check watch permission and start data loading
        self._update_watch_permission(cluster_name)

        self._start_data_loading(cluster_name)
        self._start_polling()

    def cleanup(self) -> None:
        """Cleanup all resources"""
        logging.info("Starting Enhanced Cluster Connector cleanup")
        self._shutting_down = True

        # Stop polling (also tears down the events watch)
        self._stop_polling()

        # Tear down the node watch started in _start_data_loading. _stop_polling
        # only stops the events watch, so without this the node watch stream
        # outlives the connector at shutdown. Guarded by the same flag used to
        # start it; refcounted stop_node_watch is a no-op if already detached.
        if self._watch_verb_allowed:
            try:
                get_unified_resource_loader().stop_node_watch()
            except Exception as e:
                logging.debug(f"Error stopping node watch during cleanup: {e}")

        if hasattr(self, '_cleanup_timer') and self._cleanup_timer:
            self._cleanup_timer.stop()

        # Cancel active workers
        with self._workers_lock:
            for worker in list(self._active_workers):
                if hasattr(worker, 'cancel'):
                    worker.cancel()
            self._active_workers.clear()

        # Skip cache clearing during shutdown to avoid performance hit
        # Caches will be cleaned up naturally when the application shuts down
        # if hasattr(self, '_current_cluster') and self._current_cluster:
        #     self._cache.clear_resource_cache(f'cluster_{self._current_cluster}')

        # Reset state
        with self._state_lock:
            self._connection_states.clear()
            self._current_cluster = None

        logging.info("Enhanced Cluster Connector cleanup completed")

    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            if hasattr(self, '_shutting_down') and not self._shutting_down:
                self.cleanup()
        except Exception as e:
            logging.error(f"Error in Enhanced Cluster Connector destructor: {e}")


# Singleton management
_connector_instance = None
_connector_lock = threading.Lock()


def get_cluster_connector() -> EnhancedClusterConnector:
    """Get or create the cluster connector singleton (thread-safe)"""
    global _connector_instance
    if _connector_instance is None:
        with _connector_lock:
            # Double-checked locking
            if _connector_instance is None:
                _connector_instance = EnhancedClusterConnector()
    return _connector_instance

def shutdown_cluster_connector():
    """Shutdown the cluster connector"""
    global _connector_instance
    if _connector_instance is not None:
        _connector_instance.cleanup()
        _connector_instance = None

# Backward compatibility aliases
get_enhanced_cluster_connector = get_cluster_connector
shutdown_enhanced_cluster_connector = shutdown_cluster_connector
ClusterConnection = EnhancedClusterConnector
