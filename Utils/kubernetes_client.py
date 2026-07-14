"""
Optimized Kubernetes Client - Streamlined backward compatibility wrapper
Provides high - performance access to the new service architecture while maintaining API compatibility.
Designed for minimal overhead and maximum performance.
"""

import datetime as _dt
import logging
import sys
import threading
import time
from typing import Optional, Dict, List, Any
from kubernetes.client.rest import ApiException
from PyQt6.QtCore import QObject, pyqtSignal as Signal, QProcess

# Import the new service architecture
from Services.kubernetes.kubernetes_service import get_kubernetes_service
from Services.kubernetes.api_config import APIClientConfig
from Utils import SUBPROCESS_FLAGS
from Utils.enhanced_worker import EnhancedBaseWorker
from Utils.thread_manager import get_thread_manager


class ResourceUpdateWorker(EnhancedBaseWorker):

    def __init__(self, client_instance, resource_type, resource_name, namespace, yaml_data):

        super().__init__(f"resource_update_{resource_type}_{namespace}/{resource_name}")
        self.client_instance = client_instance
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace
        self.yaml_data = yaml_data

    def execute(self):
        return self.client_instance._update_resource_sync(
            self.resource_type,
            self.resource_name,
            self.namespace,
            self.yaml_data
        )


class KubernetesClient(QObject):
    """
    Backward compatibility wrapper for KubernetesService
    Maintains the same API as the original monolithic client
    """

    # Signals - same as before for compatibility
    clusters_loaded = Signal(list)
    cluster_info_loaded = Signal(dict)
    cluster_metrics_updated = Signal(dict)
    cluster_issues_updated = Signal(list)
    resource_detail_loaded = Signal(dict)
    resource_updated = Signal(dict)
    pod_logs_loaded = Signal(str)
    error_occurred = Signal(str)

    # Deployment rollback signals
    deployment_history_loaded = Signal(list)
    deployment_rollback_completed = Signal(dict)

    # Deployment scale / restart-rollout signals (Phase 2).
    # Both emit a dict shaped like rollback's: success bool, message, deployment,
    # namespace, plus op-specific fields ("replicas" for scale, "restarted_at"
    # for restart).  Failures are emitted on the SAME signal with success=False.
    deployment_scale_completed = Signal(dict)
    deployment_restart_completed = Signal(dict)
    # HPA discovery for scale-pre-flight: emits {"deployment", "namespace",
    # "hpas": [names...]} so the UI can warn the operator that any manual scale
    # will be reverted by the autoscaler's next reconciliation pass.
    hpas_for_deployment_loaded = Signal(dict)

    # Fork B: StatefulSet / DaemonSet mutation signals.  Same payload shape as
    # the Deployment variants, with the workload kind in the dict key for the
    # name field ("statefulset" / "daemonset" rather than "deployment").
    statefulset_scale_completed = Signal(dict)
    statefulset_restart_completed = Signal(dict)
    daemonset_restart_completed = Signal(dict)

    # ── Phase 4: live watch event bus ─────────────────────────────────────
    # Global firehose carrying ADDED/MODIFIED/DELETED events parsed from
    # every active watch stream in unified_resource_loader.  Payload shape:
    #   {
    #     "type": "ADDED" | "MODIFIED" | "DELETED",
    #     "resource_type": str,        # e.g. "deployments"
    #     "namespace": Optional[str],  # None for cluster-scoped
    #     "name": str,
    #     "uid": Optional[str],
    #     "raw_object": dict,          # the marshalled resource dict
    #   }
    # Consumers (DetailManager, dropdowns, etc.) filter by (resource_type,
    # namespace, name) and short-circuit on mismatches.  Separate from the
    # legacy resource_updated signal which is dedicated to post-edit results.
    global_resource_watch_event = Signal(dict)
    # Namespace lifecycle signals — derived from the app-lifetime namespace
    # watch daemon started in __init__.  Emit just the namespace name so
    # dropdown slots can findText/addItem/removeItem without parsing.
    namespace_added_signal = Signal(str)
    namespace_deleted_signal = Signal(str)

    # Pod data signals
    pods_data_loaded = Signal(list)
    api_error = Signal(str)

    def __init__(self):
        super().__init__()

        # Get the new service architecture
        self.service = get_kubernetes_service()

        # Connect signals for backward compatibility
        self._connect_service_signals()

        # Maintain backward compatibility attributes
        self.clusters = []
        self.current_cluster = None
        self._shutting_down = False

        # Phase 4: subscribe to our own global watch event so namespace
        # ADDED/DELETED events fan out as namespace_added_signal /
        # namespace_deleted_signal for dropdown consumers without each
        # dropdown having to filter the firehose itself.
        self.global_resource_watch_event.connect(self._fanout_namespace_events)
        # Started lazily on first cluster connect — see _ensure_namespace_watch.
        self._namespace_watch_manager = None
        self._namespace_watch_cluster = None
        self._namespace_watch_lock = threading.Lock()
        # Phase 5: authoritative in-memory set of namespaces currently known
        # to exist in the connected cluster.  Maintained silently by the
        # _fanout_namespace_events fanout — ADDED -> add, DELETED -> discard.
        # Pages consult this BEFORE starting watches to avoid issuing
        # requests against namespaces that were deleted out-of-band while
        # the page was hidden.  Empty until the namespace daemon fires its
        # initial bulk of ADDED events on first cluster connect.
        self._known_namespaces: set = set()

        logging.info("KubernetesClient initialized")

    def _connect_service_signals(self):

        self.service.clusters_loaded.connect(self.clusters_loaded.emit)
        self.service.cluster_info_loaded.connect(self.cluster_info_loaded.emit)
        self.service.cluster_metrics_updated.connect(
            self.cluster_metrics_updated.emit)
        self.service.cluster_issues_updated.connect(
            self.cluster_issues_updated.emit)
        self.service.resource_detail_loaded.connect(
            self.resource_detail_loaded.emit)
        self.service.resource_updated.connect(self.resource_updated.emit)
        self.service.pod_logs_loaded.connect(self.pod_logs_loaded.emit)
        self.service.error_occurred.connect(self.error_occurred.emit)

    # ── Phase 4: namespace lifecycle plumbing ──────────────────────────────

    def _fanout_namespace_events(self, payload):
        """Translate global watch events for resource_type == 'namespaces'
        into the high-level namespace_added_signal / namespace_deleted_signal
        consumed by dropdowns.  Other resource types pass through untouched.

        Phase 5: also maintain the authoritative _known_namespaces set so
        pages can synchronously validate their namespace_filter against
        cluster reality before starting watches (see
        get_known_namespaces and BaseResourcePage.showEvent).
        """
        try:
            if payload.get("resource_type") != "namespaces":
                return
            event_type = payload.get("type")
            name = payload.get("name")
            if not name:
                return
            with self._namespace_watch_lock:
                if event_type == "ADDED":
                    self._known_namespaces.add(name)
                elif event_type == "DELETED":
                    self._known_namespaces.discard(name)
            # MODIFIED events for namespaces (label/annotation changes) do
            # not affect the dropdown list or the existence set — ignore.
            # Emit signals outside the lock: signal handlers should not
            # be invoked while holding a threading lock.
            if event_type == "ADDED":
                self.namespace_added_signal.emit(name)
            elif event_type == "DELETED":
                self.namespace_deleted_signal.emit(name)
        except Exception as e:
            logging.debug(f"namespace event fanout failed: {e}")

    def get_known_namespaces(self) -> set:
        """Return a snapshot of namespaces currently known to exist in the
        connected cluster.

        Phase 5 oracle for synchronous filter validation.  Returns an empty
        set when the namespace daemon has not yet fired any events (early
        startup or pre-connect) — callers must guard against this empty
        case to avoid false-positive "filter dead" verdicts during boot.

        Returns a copy so downstream callers cannot mutate internal state.
        """
        with self._namespace_watch_lock:
            return set(self._known_namespaces)

    def ensure_namespace_watch(self):
        """Start the app-lifetime namespace watch daemon if not already running.

        Called on successful cluster connection so namespace add/delete events
        flow regardless of which page the user is on.  The underlying
        ResourceWatchManager uses a dedicated daemon thread (not the
        QThreadPool), already handles 410 Gone via re-list, and pushes events
        through the global_resource_watch_event bus the same as every other
        watch.  Idempotent — safe to call repeatedly.
        
        Thread-safe and cluster-aware: detects cluster switches and restarts
        the watch to prevent stale namespace events from leaking across clusters.
        """
        current_context = self.service.get_current_cluster()
        
        with self._namespace_watch_lock:
            # Check if we have a watch manager and if it's for the current cluster
            if self._namespace_watch_manager is not None:
                # If we're on the same cluster, nothing to do
                if self._namespace_watch_cluster == current_context:
                    return
                # Different cluster - stop the old watch
                try:
                    self._namespace_watch_manager.stop()
                except Exception as e:
                    logging.debug(f"namespace watch stop failed during cluster switch: {e}")
                self._namespace_watch_manager = None
                self._namespace_watch_cluster = None
                self._known_namespaces.clear()
            
            try:
                from Utils.unified_resource_loader import (
                    get_unified_resource_loader,
                    ResourceWatchManager,
                )
                loader = get_unified_resource_loader()
                self._namespace_watch_manager = ResourceWatchManager(
                    loader=loader,
                    resource_type="namespaces",
                    namespace=None,  # cluster-scoped
                )
                # Seed the authority set from a one-shot LIST before the watch
                # opens.  The stream begins at the LIST resourceVersion and only
                # carries namespaces created/deleted afterwards, so it never
                # replays the namespaces that already exist at connect time —
                # without this seed _known_namespaces would stay empty for every
                # pre-existing namespace and get_known_namespaces() callers would
                # wrongly treat live namespaces as gone.
                self._seed_known_namespaces()
                self._namespace_watch_manager.start()
                self._namespace_watch_cluster = current_context
                logging.info(f"App-lifetime namespace watch daemon started for cluster {current_context}")
            except Exception as e:
                logging.warning(f"Failed to start namespace watch daemon: {e}")
                self._namespace_watch_manager = None
                self._namespace_watch_cluster = None

    def _seed_known_namespaces(self):
        """Populate _known_namespaces from a one-shot namespace LIST.

        The namespace watch opens its stream at the LIST resourceVersion and
        therefore only delivers namespaces created or deleted AFTER it starts;
        it never replays the namespaces that already existed at connect time.
        This best-effort seed captures that initial state so the authority set
        is complete from the first connect.  A failed LIST leaves the set as-is
        and callers fall back to their existing empty-set guard.
        """
        try:
            response = self.v1.list_namespace(
                _request_timeout=APIClientConfig.REQUEST_TIMEOUT,
            )
            for item in (getattr(response, "items", None) or []):
                name = getattr(getattr(item, "metadata", None), "name", None)
                if name:
                    self._known_namespaces.add(name)
        except Exception as e:
            logging.debug(f"namespace seed LIST failed: {e}")

    def _disconnect_service_signals(self):
        """Disconnect service signals to prevent emission during cleanup"""
        try:
            self.service.clusters_loaded.disconnect(self.clusters_loaded.emit)
            self.service.cluster_info_loaded.disconnect(self.cluster_info_loaded.emit)
            self.service.cluster_metrics_updated.disconnect(
                self.cluster_metrics_updated.emit)
            self.service.cluster_issues_updated.disconnect(
                self.cluster_issues_updated.emit)
            self.service.resource_detail_loaded.disconnect(
                self.resource_detail_loaded.emit)
            self.service.resource_updated.disconnect(self.resource_updated.emit)
            self.service.pod_logs_loaded.disconnect(self.pod_logs_loaded.emit)
            self.service.error_occurred.disconnect(self.error_occurred.emit)
        except Exception as e:
            logging.debug(f"Error disconnecting service signals: {e}")

    # Backward compatibility API methods

    @property
    def v1(self):

        return self.service.api_service.v1

    @property
    def apps_v1(self):

        return self.service.api_service.apps_v1

    @property
    def networking_v1(self):

        return self.service.api_service.networking_v1

    @property
    def storage_v1(self):

        return self.service.api_service.storage_v1

    @property
    def rbac_v1(self):

        return self.service.api_service.rbac_v1

    @property
    def batch_v1(self):

        return self.service.api_service.batch_v1

    @property
    def autoscaling_v1(self):

        return self.service.api_service.autoscaling_v1

    @property
    def autoscaling_v2(self):

        return self.service.api_service.autoscaling_v2

    @property
    def policy_v1(self):

        return self.service.api_service.policy_v1

    @property
    def scheduling_v1(self):

        return self.service.api_service.scheduling_v1

    @property
    def node_v1(self):

        return self.service.api_service.node_v1

    @property
    def admissionregistration_v1(self):

        return self.service.api_service.admissionregistration_v1

    @property
    def coordination_v1(self):

        return self.service.api_service.coordination_v1

    @property
    def apiextensions_v1(self):

        return self.service.api_service.apiextensions_v1

    @property
    def custom_objects_api(self):

        return self.service.api_service.custom_objects_api

    @property
    def metrics_service(self):

        return self.service.metrics_service

    @property
    def version_api(self):

        return self.service.api_service.version_api

    @property
    def log_streamer(self):

        return self.service.get_log_streamer()

    def load_kube_config(self, context_name: str = None) -> bool:

        return self.service.api_service.load_kube_config(context_name)

    def connect_to_cluster(self, cluster_name: str, context: str = None) -> bool:

        result = self.service.connect_to_cluster(cluster_name, context)
        if result:
            self.current_cluster = cluster_name
            # Phase 4: kick off the app-lifetime namespace watch so dropdowns
            # stay live regardless of which page the user is on.
            self.ensure_namespace_watch()
        return result

    def disconnect_from_cluster(self):

        self.service.disconnect_from_cluster()
        self.current_cluster = None
        # Phase 4: stop the namespace watch on disconnect so cluster-switch
        # picks up a fresh namespace list on the next connect (ResourceWatch
        # Manager's daemon thread is unjoined; setting None lets a new one
        # spin up cleanly via ensure_namespace_watch).
        # Hold the same lock ensure_namespace_watch uses so the watch-manager
        # and known-namespaces state are mutated consistently.
        with self._namespace_watch_lock:
            if self._namespace_watch_manager is not None:
                try:
                    self._namespace_watch_manager.stop()
                except Exception as e:
                    logging.debug(f"namespace watch stop failed: {e}")
                self._namespace_watch_manager = None
            # Phase 5: purge the namespace authority cache so the new cluster
            # context does not inherit dead namespaces from the prior one.
            self._known_namespaces.clear()

    def get_cluster_metrics(self) -> Optional[Dict[str, Any]]:

        metrics = self.service.get_cluster_metrics()
        if metrics:
            # Update current_cluster for compatibility
            self.current_cluster = self.service.get_current_cluster()
        return metrics

    def get_cluster_issues(self) -> List[Dict[str, Any]]:

        return self.service.get_cluster_issues()

    def get_pod_logs(self, pod_name: str, namespace: str, container: str = None, tail_lines: int = 100):
        """Get pod logs - backward compatibility"""
        return self.service.get_pod_logs(pod_name, namespace, container, tail_lines)

    def start_log_stream(self, pod_name: str, namespace: str, container: str = None, tail_lines: int = 100):
        """Start log stream - backward compatibility"""
        self.service.start_log_stream(
            pod_name, namespace, container, tail_lines)

    def stop_log_stream(self, pod_name: str, namespace: str, container: str = None):

        self.service.stop_log_stream(pod_name, namespace, container)

    def get_events_for_resource(self, resource_type: str, resource_name: str, namespace: str = None):
        """Get events for resource - backward compatibility"""
        return self.service.get_events_for_resource(resource_type, resource_name, namespace)

    def get_node_metrics(self, node_name: str) -> Optional[Dict[str, Any]]:

        return self.service.get_node_metrics(node_name)

    def get_cluster_version(self) -> Optional[str]:

        return self.service.get_cluster_version()

    def is_connected(self) -> bool:

        return self.service.is_connected()

    def start_metrics_polling(self, interval_ms: int = 5000):

        self.service.start_polling(metrics_interval=interval_ms)

    def stop_metrics_polling(self):

        self.service.stop_polling()

    def start_issues_polling(self, interval_ms: int = 10000):

        self.service.start_polling(issues_interval=interval_ms)

    def stop_issues_polling(self):

        self.service.stop_polling()

    def refresh_metrics(self):

        # Trigger immediate polling
        if self.service.current_cluster:
            self.service._poll_metrics_async()

    def refresh_issues(self):

        # Trigger immediate polling
        if self.service.current_cluster:
            self.service._poll_issues_async()

    def load_clusters_async(self):

        self.service.load_clusters_async()

    # Deployment rollback functionality
    def get_deployment_rollout_history_async(self, deployment_name: str, namespace: str = "default"):

        logging.info(
            f"Getting rollout history for deployment {deployment_name} in namespace {namespace}")

        class RolloutHistoryWorker(EnhancedBaseWorker):
            def __init__(self, client_instance, deployment_name, namespace):
                super().__init__(f"rollout_history_{namespace}/{deployment_name}")
                self.client_instance = client_instance
                self.deployment_name = deployment_name
                self.namespace = namespace

            def execute(self):
                return self.client_instance._get_deployment_rollout_history_sync(
                    self.deployment_name, self.namespace
                )

        worker = RolloutHistoryWorker(self, deployment_name, namespace)

        # Connect signals with proper error handling
        def handle_success(result):
            try:
                self.deployment_history_loaded.emit(result)
            except Exception as e:
                logging.error(f"Error emitting history result: {str(e)}")
                self.api_error.emit(
                    f"Failed to emit rollout history: {str(e)}")

        def handle_error(error):
            try:
                self.api_error.emit(
                    f"Failed to get rollout history: {str(error)}")
            except Exception as e:
                logging.error(f"Error emitting history error: {str(e)}")

        worker.signals.finished.connect(handle_success)
        worker.signals.error.connect(handle_error)

        # Submit to thread manager
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(
            f"rollout_history_{namespace}/{deployment_name}", worker)

    def rollback_deployment_async(self, deployment_name: str, revision: int, namespace: str = "default"):

        logging.info(
            f"Rolling back deployment {deployment_name} to revision {revision} in namespace {namespace}")

        class RollbackWorker(EnhancedBaseWorker):
            def __init__(self, client_instance, deployment_name, revision, namespace):
                super().__init__(f"rollback_{namespace}/{deployment_name}")
                self.client_instance = client_instance
                self.deployment_name = deployment_name
                self.revision = revision
                self.namespace = namespace

            def execute(self):
                return self.client_instance._rollback_deployment_sync(
                    self.deployment_name, self.revision, self.namespace
                )

        worker = RollbackWorker(self, deployment_name, revision, namespace)

        # Connect signals with proper error handling
        def handle_success(result):
            try:
                self.deployment_rollback_completed.emit(result)
            except Exception as e:
                logging.error(f"Error emitting rollback result: {str(e)}")
                error_result = {
                    "success": False,
                    "message": f"Signal emission failed: {str(e)}",
                    "deployment": deployment_name,
                    "revision": revision,
                    "namespace": namespace
                }
                self.deployment_rollback_completed.emit(error_result)

        def handle_error(error):
            try:
                error_result = {
                    "success": False,
                    "message": str(error),
                    "deployment": deployment_name,
                    "revision": revision,
                    "namespace": namespace
                }
                self.deployment_rollback_completed.emit(error_result)
            except Exception as e:
                logging.error(f"Error emitting rollback error: {str(e)}")

        worker.signals.finished.connect(handle_success)
        worker.signals.error.connect(handle_error)

        # Submit to thread manager
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(f"rollback_{namespace}/{deployment_name}", worker)

    # ──── Phase 2: Scale / Restart Rollout / HPA discovery ─────────────────

    @staticmethod
    def _format_api_exception(error):
        """Map a kubernetes ApiException to a human-readable message.

        Returns str(error) for non-ApiException errors.  Centralises the
        401/403/409/422 → readable-string mapping so each operation handler
        does not duplicate the table.
        """
        if not isinstance(error, ApiException):
            return str(error)
        status_messages = {
            401: "Authentication failed (401). Re-authenticate to the cluster.",
            403: "Permission denied (403). The current user lacks the required RBAC permission for this operation.",
            409: "Conflict (409). The resource was modified concurrently — refresh and retry.",
            422: "Invalid request payload (422). The Kubernetes API rejected the patch structure.",
        }
        return status_messages.get(
            error.status,
            f"Kubernetes API error {error.status}: {error.reason}",
        )

    def _scale_deployment_sync(self, deployment_name: str, namespace: str, replicas: int) -> dict:
        """Patch the deployment's scale subresource and return a result dict.

        Uses the dedicated /scale endpoint so RBAC policies that grant
        deployments/scale without deployments/patch continue to work.

        Defensively coalesces ``result.spec.replicas`` from None to 0: the
        kubernetes client has been observed to deserialize scale-to-zero
        responses as None (Go's omitempty interacting with the OpenAPI
        generator).  Harmless if the upstream library has been fixed.
        """
        body = {"spec": {"replicas": int(replicas)}}
        try:
            result = self.apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=namespace,
                body=body,
                _request_timeout=APIClientConfig.DEPLOYMENT_OPERATION_TIMEOUT,
            )
            resolved_replicas = (
                result.spec.replicas if result.spec.replicas is not None else 0
            )
            return {
                "success": True,
                "message": f"Scaled deployment {deployment_name} to {resolved_replicas} replicas.",
                "deployment": deployment_name,
                "namespace": namespace,
                "replicas": resolved_replicas,
            }
        except Exception as e:
            msg = self._format_api_exception(e)
            logging.error(f"Scale failed for {deployment_name}: {msg}")
            return {
                "success": False,
                "message": msg,
                "deployment": deployment_name,
                "namespace": namespace,
                "replicas": int(replicas),
                "error_type": type(e).__name__,
            }

    def scale_deployment_async(self, deployment_name: str, namespace: str, replicas: int):
        logging.info(
            f"Scaling deployment {deployment_name} in {namespace} to {replicas} replicas"
        )

        class ScaleWorker(EnhancedBaseWorker):
            def __init__(self, client_instance, deployment_name, namespace, replicas):
                super().__init__(f"scale_{namespace}/{deployment_name}")
                self.client_instance = client_instance
                self.deployment_name = deployment_name
                self.namespace = namespace
                self.replicas = replicas

            def execute(self):
                return self.client_instance._scale_deployment_sync(
                    self.deployment_name, self.namespace, self.replicas
                )

        worker = ScaleWorker(self, deployment_name, namespace, replicas)

        def handle_success(result):
            try:
                self.deployment_scale_completed.emit(result)
            except Exception as e:
                logging.error(f"Error emitting scale result: {str(e)}")

        def handle_error(error):
            # Defensive: exceptions that escape _scale_deployment_sync's own
            # try/except still produce a failure dict on the same signal so
            # the UI never silently misses an error.
            try:
                self.deployment_scale_completed.emit({
                    "success": False,
                    "message": self._format_api_exception(error),
                    "deployment": deployment_name,
                    "namespace": namespace,
                    "replicas": int(replicas),
                    "error_type": type(error).__name__,
                })
            except Exception as e:
                logging.error(f"Error emitting scale error: {str(e)}")

        worker.signals.finished.connect(handle_success)
        worker.signals.error.connect(handle_error)

        get_thread_manager().submit_worker(f"scale_{namespace}/{deployment_name}", worker)

    def _restart_deployment_rollout_sync(self, deployment_name: str, namespace: str) -> dict:
        """Trigger a rollout restart by patching the kubectl.kubernetes.io/restartedAt
        annotation in spec.template.metadata.annotations.

        Strategic merge patch leaves sibling annotations and template fields
        untouched, so service-mesh sidecar injection markers, Prometheus scrape
        configs, etc. survive.  The new template hash makes the controller
        provision a new ReplicaSet and rotate pods per the deployment's
        configured strategy (RollingUpdate or Recreate).
        """

        # Timezone-aware UTC, second precision — mirrors kubectl rollout restart.
        current_timestamp = _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": current_timestamp
                        }
                    }
                }
            }
        }
        try:
            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=body,
                _request_timeout=APIClientConfig.DEPLOYMENT_OPERATION_TIMEOUT,
            )
            return {
                "success": True,
                "message": f"Restart triggered for deployment {deployment_name}.",
                "deployment": deployment_name,
                "namespace": namespace,
                "restarted_at": current_timestamp,
            }
        except Exception as e:
            msg = self._format_api_exception(e)
            logging.error(f"Restart rollout failed for {deployment_name}: {msg}")
            return {
                "success": False,
                "message": msg,
                "deployment": deployment_name,
                "namespace": namespace,
                "restarted_at": current_timestamp,
                "error_type": type(e).__name__,
            }

    def restart_deployment_rollout_async(self, deployment_name: str, namespace: str):
        logging.info(
            f"Restarting rollout for deployment {deployment_name} in {namespace}"
        )

        class RestartWorker(EnhancedBaseWorker):
            def __init__(self, client_instance, deployment_name, namespace):
                super().__init__(f"restart_{namespace}/{deployment_name}")
                self.client_instance = client_instance
                self.deployment_name = deployment_name
                self.namespace = namespace

            def execute(self):
                return self.client_instance._restart_deployment_rollout_sync(
                    self.deployment_name, self.namespace
                )

        worker = RestartWorker(self, deployment_name, namespace)

        def handle_success(result):
            try:
                self.deployment_restart_completed.emit(result)
            except Exception as e:
                logging.error(f"Error emitting restart result: {str(e)}")

        def handle_error(error):
            try:
                self.deployment_restart_completed.emit({
                    "success": False,
                    "message": self._format_api_exception(error),
                    "deployment": deployment_name,
                    "namespace": namespace,
                    "error_type": type(error).__name__,
                })
            except Exception as e:
                logging.error(f"Error emitting restart error: {str(e)}")

        worker.signals.finished.connect(handle_success)
        worker.signals.error.connect(handle_error)

        get_thread_manager().submit_worker(f"restart_{namespace}/{deployment_name}", worker)

    def _find_hpas_for_workload_sync(self, kind: str, name: str, namespace: str) -> dict:
        """List HPAs in the namespace, return those targeting (kind, name).

        Fork B generalisation of the Deployment-only HPA scan.  HPAs can target
        anything with a /scale subresource: Deployments, StatefulSets,
        ReplicaSets, and certain CRDs.  The discovery logic is identical
        regardless of kind — only the scaleTargetRef.kind comparison changes.

        Prefers autoscaling/v2 (used elsewhere in the codebase); falls back
        to autoscaling/v1 on 404 so legacy clusters still work.  Returns the
        names of all matching HPAs (typically zero or one in practice).
        """
        try:
            try:
                hpas = self.autoscaling_v2.list_namespaced_horizontal_pod_autoscaler(
                    namespace=namespace,
                    _request_timeout=APIClientConfig.DEPLOYMENT_OPERATION_TIMEOUT,
                )
            except ApiException as e:
                if getattr(e, "status", None) == 404:
                    hpas = self.autoscaling_v1.list_namespaced_horizontal_pod_autoscaler(
                        namespace=namespace,
                        _request_timeout=APIClientConfig.DEPLOYMENT_OPERATION_TIMEOUT,
                    )
                else:
                    raise

            matches = []
            for hpa in (hpas.items or []):
                try:
                    ref = hpa.spec.scale_target_ref
                    if (
                        ref
                        and getattr(ref, "kind", "") == kind
                        and getattr(ref, "name", "") == name
                    ):
                        matches.append(hpa.metadata.name)
                except AttributeError:
                    continue
            return {
                "success": True,
                "kind": kind,
                "name": name,
                "namespace": namespace,
                "hpas": matches,
            }
        except Exception as e:
            msg = self._format_api_exception(e)
            logging.warning(f"HPA scan failed for {kind}/{name}: {msg}")
            return {
                "success": False,
                "message": msg,
                "kind": kind,
                "name": name,
                "namespace": namespace,
                "hpas": [],
                "error_type": type(e).__name__,
            }

    def _find_hpas_for_deployment_sync(self, deployment_name: str, namespace: str) -> dict:
        """Backward-compat wrapper preserving the original (deployment, namespace)
        payload shape used by the Phase 2 deployment_scale flow.  New code
        should call _find_hpas_for_workload_sync directly."""
        result = self._find_hpas_for_workload_sync("Deployment", deployment_name, namespace)
        # Translate the workload-shape payload back to the deployment-shape
        # payload that existing callers expect.
        if result.get("success"):
            return {
                "success": True,
                "deployment": deployment_name,
                "namespace": namespace,
                "hpas": result.get("hpas", []),
            }
        # Failure path: preserve original keys.
        return {
            "success": False,
            "message": result.get("message", ""),
            "deployment": deployment_name,
            "namespace": namespace,
            "hpas": [],
            "error_type": result.get("error_type", "Exception"),
        }

    def find_hpas_for_deployment(self, deployment_name: str, namespace: str) -> dict:
        """Synchronous version of find_hpas_for_deployment_async.

        Used by the Scale dialog's HPA pre-scan: blocks the calling thread
        for up to ~DEPLOYMENT_OPERATION_TIMEOUT (10s worst case, typically
        <500ms).  Acceptable on the main thread only as a deliberate
        user-initiated pre-flight before a modal dialog opens.  Do NOT call
        this from background watch handlers or paint paths.
        """
        return self._find_hpas_for_deployment_sync(deployment_name, namespace)

    def find_hpas_for_deployment_async(self, deployment_name: str, namespace: str):
        logging.debug(
            f"Scanning HPAs for deployment {deployment_name} in {namespace}"
        )

        class HpaScanWorker(EnhancedBaseWorker):
            def __init__(self, client_instance, deployment_name, namespace):
                super().__init__(f"hpa_scan_{namespace}/{deployment_name}")
                self.client_instance = client_instance
                self.deployment_name = deployment_name
                self.namespace = namespace

            def execute(self):
                return self.client_instance._find_hpas_for_deployment_sync(
                    self.deployment_name, self.namespace
                )

        worker = HpaScanWorker(self, deployment_name, namespace)

        def handle_success(result):
            try:
                self.hpas_for_deployment_loaded.emit(result)
            except Exception as e:
                logging.error(f"Error emitting HPA scan result: {str(e)}")

        def handle_error(error):
            try:
                self.hpas_for_deployment_loaded.emit({
                    "success": False,
                    "message": self._format_api_exception(error),
                    "deployment": deployment_name,
                    "namespace": namespace,
                    "hpas": [],
                    "error_type": type(error).__name__,
                })
            except Exception as e:
                logging.error(f"Error emitting HPA scan error: {str(e)}")

        worker.signals.finished.connect(handle_success)
        worker.signals.error.connect(handle_error)

        get_thread_manager().submit_worker(f"hpa_scan_{namespace}/{deployment_name}", worker)

    # ──── Fork B: StatefulSet Scale ───────────────────────────────────────

    def _scale_statefulset_sync(self, statefulset_name: str, namespace: str, replicas: int) -> dict:
        """Patch the StatefulSet's /scale subresource and return a result dict.

        Mirrors _scale_deployment_sync.  StatefulSets share the same OpenAPI
        client generator, so the same defensive None-to-0 coalesce applies
        on scale-to-zero responses (harmless if the upstream library returns
        0 correctly).  Uses the dedicated subresource so RBAC policies that
        grant statefulsets/scale without statefulsets/patch still work.
        """
        body = {"spec": {"replicas": int(replicas)}}
        try:
            result = self.apps_v1.patch_namespaced_stateful_set_scale(
                name=statefulset_name,
                namespace=namespace,
                body=body,
                _request_timeout=APIClientConfig.DEPLOYMENT_OPERATION_TIMEOUT,
            )
            resolved_replicas = (
                result.spec.replicas if result.spec.replicas is not None else 0
            )
            return {
                "success": True,
                "message": f"Scaled StatefulSet {statefulset_name} to {resolved_replicas} replicas.",
                "statefulset": statefulset_name,
                "namespace": namespace,
                "replicas": resolved_replicas,
            }
        except Exception as e:
            msg = self._format_api_exception(e)
            logging.error(f"StatefulSet scale failed for {statefulset_name}: {msg}")
            return {
                "success": False,
                "message": msg,
                "statefulset": statefulset_name,
                "namespace": namespace,
                "replicas": int(replicas),
                "error_type": type(e).__name__,
            }

    def scale_statefulset_async(self, statefulset_name: str, namespace: str, replicas: int):
        logging.info(
            f"Scaling StatefulSet {statefulset_name} in {namespace} to {replicas} replicas"
        )

        class ScaleStatefulSetWorker(EnhancedBaseWorker):
            def __init__(self, client_instance, statefulset_name, namespace, replicas):
                super().__init__(f"scale_ss_{namespace}/{statefulset_name}")
                self.client_instance = client_instance
                self.statefulset_name = statefulset_name
                self.namespace = namespace
                self.replicas = replicas

            def execute(self):
                return self.client_instance._scale_statefulset_sync(
                    self.statefulset_name, self.namespace, self.replicas
                )

        worker = ScaleStatefulSetWorker(self, statefulset_name, namespace, replicas)

        def handle_success(result):
            try:
                self.statefulset_scale_completed.emit(result)
            except Exception as e:
                logging.error(f"Error emitting statefulset scale result: {str(e)}")

        def handle_error(error):
            try:
                self.statefulset_scale_completed.emit({
                    "success": False,
                    "message": self._format_api_exception(error),
                    "statefulset": statefulset_name,
                    "namespace": namespace,
                    "replicas": int(replicas),
                    "error_type": type(error).__name__,
                })
            except Exception as e:
                logging.error(f"Error emitting statefulset scale error: {str(e)}")

        worker.signals.finished.connect(handle_success)
        worker.signals.error.connect(handle_error)

        get_thread_manager().submit_worker(f"scale_ss_{namespace}/{statefulset_name}", worker)

    # ──── Fork B: StatefulSet Restart Rollout ────────────────────────────

    def _restart_statefulset_rollout_sync(self, statefulset_name: str, namespace: str) -> dict:
        """Trigger a StatefulSet restart by patching the restartedAt annotation.

        Same RFC3339 second-precision UTC format the Deployment restart uses,
        for consistency with kubectl rollout restart.  Uses strategic merge
        patch via patch_namespaced_stateful_set so sibling annotations are
        preserved.  Note: StatefulSets cannot be paused (no spec.paused), so
        the only no-op-warning pre-flight is OnDelete strategy — handled by
        the page-side handler before this dispatches.
        """
        current_timestamp = _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": current_timestamp
                        }
                    }
                }
            }
        }
        try:
            self.apps_v1.patch_namespaced_stateful_set(
                name=statefulset_name,
                namespace=namespace,
                body=body,
                _request_timeout=APIClientConfig.DEPLOYMENT_OPERATION_TIMEOUT,
            )
            return {
                "success": True,
                "message": f"Restart triggered for StatefulSet {statefulset_name}.",
                "statefulset": statefulset_name,
                "namespace": namespace,
                "restarted_at": current_timestamp,
            }
        except Exception as e:
            msg = self._format_api_exception(e)
            logging.error(f"StatefulSet restart failed for {statefulset_name}: {msg}")
            return {
                "success": False,
                "message": msg,
                "statefulset": statefulset_name,
                "namespace": namespace,
                "restarted_at": current_timestamp,
                "error_type": type(e).__name__,
            }

    def restart_statefulset_rollout_async(self, statefulset_name: str, namespace: str):
        logging.info(
            f"Restarting rollout for StatefulSet {statefulset_name} in {namespace}"
        )

        class RestartStatefulSetWorker(EnhancedBaseWorker):
            def __init__(self, client_instance, statefulset_name, namespace):
                super().__init__(f"restart_ss_{namespace}/{statefulset_name}")
                self.client_instance = client_instance
                self.statefulset_name = statefulset_name
                self.namespace = namespace

            def execute(self):
                return self.client_instance._restart_statefulset_rollout_sync(
                    self.statefulset_name, self.namespace
                )

        worker = RestartStatefulSetWorker(self, statefulset_name, namespace)

        def handle_success(result):
            try:
                self.statefulset_restart_completed.emit(result)
            except Exception as e:
                logging.error(f"Error emitting statefulset restart result: {str(e)}")

        def handle_error(error):
            try:
                self.statefulset_restart_completed.emit({
                    "success": False,
                    "message": self._format_api_exception(error),
                    "statefulset": statefulset_name,
                    "namespace": namespace,
                    "error_type": type(error).__name__,
                })
            except Exception as e:
                logging.error(f"Error emitting statefulset restart error: {str(e)}")

        worker.signals.finished.connect(handle_success)
        worker.signals.error.connect(handle_error)

        get_thread_manager().submit_worker(f"restart_ss_{namespace}/{statefulset_name}", worker)

    # ──── Fork B: DaemonSet Restart Rollout ──────────────────────────────

    def _restart_daemonset_rollout_sync(self, daemonset_name: str, namespace: str) -> dict:
        """Trigger a DaemonSet restart by patching the restartedAt annotation.

        Identical mechanism to Deployment/StatefulSet restart — strategic
        merge patch of spec.template.metadata.annotations with kubectl's
        canonical restartedAt key.  DaemonSet has no replicas concept, so
        no scale operation.  No spec.paused either, so the only pre-flight
        warning is OnDelete (which produces a cluster-wide stuck rollout —
        page-side handler distinguishes this from StatefulSet's
        ordered-pod stuck rollout in the user-facing copy).
        """
        current_timestamp = _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": current_timestamp
                        }
                    }
                }
            }
        }
        try:
            self.apps_v1.patch_namespaced_daemon_set(
                name=daemonset_name,
                namespace=namespace,
                body=body,
                _request_timeout=APIClientConfig.DEPLOYMENT_OPERATION_TIMEOUT,
            )
            return {
                "success": True,
                "message": f"Restart triggered for DaemonSet {daemonset_name}.",
                "daemonset": daemonset_name,
                "namespace": namespace,
                "restarted_at": current_timestamp,
            }
        except Exception as e:
            msg = self._format_api_exception(e)
            logging.error(f"DaemonSet restart failed for {daemonset_name}: {msg}")
            return {
                "success": False,
                "message": msg,
                "daemonset": daemonset_name,
                "namespace": namespace,
                "restarted_at": current_timestamp,
                "error_type": type(e).__name__,
            }

    def restart_daemonset_rollout_async(self, daemonset_name: str, namespace: str):
        logging.info(
            f"Restarting rollout for DaemonSet {daemonset_name} in {namespace}"
        )

        class RestartDaemonSetWorker(EnhancedBaseWorker):
            def __init__(self, client_instance, daemonset_name, namespace):
                super().__init__(f"restart_ds_{namespace}/{daemonset_name}")
                self.client_instance = client_instance
                self.daemonset_name = daemonset_name
                self.namespace = namespace

            def execute(self):
                return self.client_instance._restart_daemonset_rollout_sync(
                    self.daemonset_name, self.namespace
                )

        worker = RestartDaemonSetWorker(self, daemonset_name, namespace)

        def handle_success(result):
            try:
                self.daemonset_restart_completed.emit(result)
            except Exception as e:
                logging.error(f"Error emitting daemonset restart result: {str(e)}")

        def handle_error(error):
            try:
                self.daemonset_restart_completed.emit({
                    "success": False,
                    "message": self._format_api_exception(error),
                    "daemonset": daemonset_name,
                    "namespace": namespace,
                    "error_type": type(error).__name__,
                })
            except Exception as e:
                logging.error(f"Error emitting daemonset restart error: {str(e)}")

        worker.signals.finished.connect(handle_success)
        worker.signals.error.connect(handle_error)

        get_thread_manager().submit_worker(f"restart_ds_{namespace}/{daemonset_name}", worker)

    # ──── Fork B: public sync HPA wrapper for any workload kind ──────────

    def find_hpas_for_workload(self, kind: str, name: str, namespace: str) -> dict:
        """Synchronous HPA scan for any workload kind.  Used by StatefulSet
        and DaemonSet scale dialogs (DaemonSets cannot scale, but the public
        helper supports them for future-proofing).  Same blocking caveats
        as find_hpas_for_deployment."""
        return self._find_hpas_for_workload_sync(kind, name, namespace)

    def get_cluster_metrics_async(self):

        # Trigger async metrics polling
        self.service._poll_metrics_async()

    def get_cluster_issues_async(self):

        # Trigger async issues polling
        self.service._poll_issues_async()

    def update_resource_async(self, resource_type: str, resource_name: str, namespace: str, resource_data: dict):

        logging.info(
            f"Starting async update for {resource_type}/{resource_name} in namespace {namespace}")

        worker = ResourceUpdateWorker(
            self, resource_type, resource_name, namespace, resource_data)

        # Connect worker signals
        worker.signals.finished.connect(
            lambda result: self.resource_updated.emit(
                result) if result else None
        )
        worker.signals.error.connect(
            lambda error: self.resource_updated.emit({
                'success': False,
                'message': f"Update failed: {error}"
            })
        )

        # Submit worker to thread manager
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(
            f"resource_update_{resource_type}_{namespace}/{resource_name}", worker)

    def _update_resource_sync(self, resource_type: str, resource_name: str, namespace: str, resource_data: dict):

        try:
            logging.info(
                f"Starting resource update for {resource_type}/{resource_name} in namespace {namespace}")

            # For YAML updates, we need to ensure we're doing a proper patch operation
            # that handles both additions and removals correctly
            resource_body = resource_data

            # Log the resource data for debugging (but limit size)
            data_summary = str(resource_data)[
                :500] + "..." if len(str(resource_data)) > 500 else str(resource_data)
            logging.debug(f"Resource update data: {data_summary}")

            # Validate the resource has required fields
            if not isinstance(resource_data, dict):
                raise ValueError("Resource data must be a dictionary")

            if not resource_data.get('apiVersion'):
                raise ValueError(
                    "Resource data missing required 'apiVersion' field")

            if not resource_data.get('kind'):
                raise ValueError("Resource data missing required 'kind' field")

            if not resource_data.get('metadata', {}).get('name'):
                raise ValueError(
                    "Resource data missing required 'metadata.name' field")

            # Map resource type to appropriate API call
            result = None

            if resource_type.lower() == "pod":
                result = self.v1.patch_namespaced_pod(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "service":
                result = self.v1.patch_namespaced_service(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "deployment":
                result = self.apps_v1.patch_namespaced_deployment(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "configmap":
                result = self.v1.patch_namespaced_config_map(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "secret":
                result = self.v1.patch_namespaced_secret(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "statefulset":
                result = self.apps_v1.patch_namespaced_stateful_set(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "daemonset":
                result = self.apps_v1.patch_namespaced_daemon_set(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "replicaset":
                result = self.apps_v1.patch_namespaced_replica_set(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "ingress":
                result = self.networking_v1.patch_namespaced_ingress(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "networkpolicy":
                result = self.networking_v1.patch_namespaced_network_policy(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            # Non - namespaced resources
            elif resource_type.lower() == "node":
                result = self.v1.patch_node(
                    name=resource_name,
                    body=resource_body
                )
            elif resource_type.lower() == "namespace":
                result = self.v1.patch_namespace(
                    name=resource_name,
                    body=resource_body
                )
            elif resource_type.lower() == "serviceaccount":
                result = self.v1.patch_namespaced_service_account(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["job", "jobs"]:
                result = self.batch_v1.patch_namespaced_job(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["cronjob", "cronjobs"]:
                result = self.batch_v1.patch_namespaced_cron_job(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["persistentvolumeclaim", "persistentvolumeclaims", "pvc"]:
                result = self.v1.patch_namespaced_persistent_volume_claim(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["persistentvolume", "persistentvolumes", "pv"]:
                result = self.v1.patch_persistent_volume(
                    name=resource_name,
                    body=resource_body
                )
            elif resource_type.lower() in ["endpoints"]:
                result = self.v1.patch_namespaced_endpoints(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["limitrange", "limitranges"]:
                result = self.v1.patch_namespaced_limit_range(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["resourcequota", "resourcequotas"]:
                result = self.v1.patch_namespaced_resource_quota(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["replicationcontroller", "replicationcontrollers", "rc"]:
                result = self.v1.patch_namespaced_replication_controller(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["role", "roles"]:
                result = self.rbac_v1.patch_namespaced_role(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["rolebinding", "rolebindings"]:
                result = self.rbac_v1.patch_namespaced_role_binding(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["clusterrole", "clusterroles"]:
                result = self.rbac_v1.patch_cluster_role(
                    name=resource_name,
                    body=resource_body
                )
            elif resource_type.lower() in ["clusterrolebinding", "clusterrolebindings"]:
                result = self.rbac_v1.patch_cluster_role_binding(
                    name=resource_name,
                    body=resource_body
                )
            elif resource_type.lower() in ["horizontalpodautoscaler", "horizontalpodautoscalers", "hpa"]:
                result = self.autoscaling_v2.patch_namespaced_horizontal_pod_autoscaler(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["poddisruptionbudget", "poddisruptionbudgets", "pdb"]:
                result = self.policy_v1.patch_namespaced_pod_disruption_budget(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            else:
                return {
                    "success": False,
                    "message": f"Resource type '{resource_type}' is not supported for updates"
                }

            if result:
                logging.info(
                    f"Successfully updated {resource_type}/{resource_name}")
                return {
                    "success": True,
                    "message": f"Successfully updated {resource_type}/{resource_name}",
                    "resource": result.to_dict() if hasattr(result, 'to_dict') else str(result)
                }
            else:
                return {
                    "success": False,
                    "message": f"No result returned for {resource_type}/{resource_name} update"
                }

        except Exception as e:
            # Extract more readable error from Kubernetes API exceptions
            error_message = self._extract_readable_error(e)
            logging.error(
                f"Failed to update {resource_type}/{resource_name}: {error_message}")
            return {
                "success": False,
                "message": error_message
            }

    def _extract_readable_error(self, error) -> str:

        try:
            # Handle Kubernetes API exceptions
            if hasattr(error, 'body'):
                import json
                body = json.loads(error.body)
                if 'message' in body:
                    message = body['message']

                    # Make common errors more user - friendly
                    if "forbidden" in message.lower():
                        return f"Permission denied: {message}\n\nTip: Check if you have the necessary RBAC permissions to edit this resource."
                    elif "invalid" in message.lower() and "immutable" in message.lower():
                        return f"Field cannot be changed: {message}\n\nTip: Some fields cannot be modified after resource creation."
                    elif "conflict" in message.lower():
                        return f"Resource conflict: {message}\n\nTip: Another process may have modified this resource. Try refreshing and editing again."
                    elif "not found" in message.lower():
                        return f"Resource not found: {message}\n\nTip: The resource may have been deleted by another process."
                    else:
                        return message

            # Handle standard exceptions with better context
            error_str = str(error)
            if "connection" in error_str.lower():
                return f"Connection error: {error_str}\n\nTip: Check your cluster connection and try again."
            elif "timeout" in error_str.lower():
                return f"Request timeout: {error_str}\n\nTip: The cluster may be slow to respond. Try again in a moment."
            else:
                return error_str

        except Exception:
            # Fallback to string representation
            return str(error)

    def validate_kubernetes_schema(self, resource_data: dict) -> tuple[bool, str]:

        try:
            # Basic validation - check for required fields
            if not isinstance(resource_data, dict):
                return False, "Resource data must be a dictionary"

            if 'apiVersion' not in resource_data:
                return False, "Missing required field: apiVersion"

            if 'kind' not in resource_data:
                return False, "Missing required field: kind"

            if 'metadata' not in resource_data:
                return False, "Missing required field: metadata"

            # Validate metadata has name
            metadata = resource_data.get('metadata', {})
            if not isinstance(metadata, dict):
                return False, "metadata field must be a dictionary"

            if not metadata.get('name'):
                return False, "Missing required field: metadata.name"

            # Check for invalid field values
            name = metadata.get('name', '')
            if not isinstance(name, str) or not name.strip():
                return False, "metadata.name must be a non-empty string"

            # For Pod validation, be more lenient with container validation
            if resource_data.get('kind') == 'Pod':
                spec = resource_data.get('spec', {})
                containers = spec.get('containers', [])

                if containers:
                    container_names = [c.get('name', '') for c in containers]
                    # Only check for empty names, allow duplicate names (some use cases need this)
                    if any(not container_name for container_name in container_names):
                        return False, "All containers must have names"

                # Check for basic container structure
                for container in containers:
                    if not isinstance(container, dict):
                        return False, "Each container must be a dictionary"
                    if not container.get('image'):
                        return False, "All containers must have an image specified"

            return True, "Valid Kubernetes resource"

        except Exception as e:
            return False, f"Schema validation error: {str(e)}"

    def get_resource_detail(self, resource_type: str, resource_name: str, namespace: str = None):

        try:
            # Map resource type to appropriate API call
            resource_detail = None

            if resource_type.lower() == "pod":
                if namespace:
                    resource_detail = self.v1.read_namespaced_pod(
                        name=resource_name, namespace=namespace)
                else:
                    # Search efficiently in common namespaces instead of all namespaces
                    common_namespaces = ["default",
                                         "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.v1.read_namespaced_pod(
                                name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            # Only log if it's not a simple "not found" error
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(
                                    f"Error searching for {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() == "service":
                if namespace:
                    resource_detail = self.v1.read_namespaced_service(
                        name=resource_name, namespace=namespace)
                else:
                    # Search efficiently in common namespaces instead of all namespaces
                    common_namespaces = ["default",
                                         "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.v1.read_namespaced_service(
                                name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(
                                    f"Error searching for service {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() == "deployment":
                if namespace:
                    resource_detail = self.apps_v1.read_namespaced_deployment(
                        name=resource_name, namespace=namespace)
                else:
                    # Search efficiently in common namespaces instead of all namespaces
                    common_namespaces = ["default",
                                         "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.apps_v1.read_namespaced_deployment(
                                name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(
                                    f"Error searching for deployment {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() == "replicaset":
                if namespace:
                    resource_detail = self.apps_v1.read_namespaced_replica_set(
                        name=resource_name, namespace=namespace)
                else:
                    # Search efficiently in common namespaces instead of all namespaces
                    common_namespaces = ["default",
                                         "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.apps_v1.read_namespaced_replica_set(
                                name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(
                                    f"Error searching for replicaset {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() == "daemonset":
                if namespace:
                    resource_detail = self.apps_v1.read_namespaced_daemon_set(
                        name=resource_name, namespace=namespace)
                else:
                    common_namespaces = ["default", "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.apps_v1.read_namespaced_daemon_set(
                                name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(
                                    f"Error searching for daemonset {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() == "statefulset":
                if namespace:
                    resource_detail = self.apps_v1.read_namespaced_stateful_set(
                        name=resource_name, namespace=namespace)
                else:
                    common_namespaces = ["default", "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.apps_v1.read_namespaced_stateful_set(
                                name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(
                                    f"Error searching for statefulset {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() == "job":
                if namespace:
                    resource_detail = self.batch_v1.read_namespaced_job(
                        name=resource_name, namespace=namespace)
                else:
                    common_namespaces = ["default", "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.batch_v1.read_namespaced_job(
                                name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(
                                    f"Error searching for job {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() == "cronjob":
                if namespace:
                    resource_detail = self.batch_v1.read_namespaced_cron_job(
                        name=resource_name, namespace=namespace)
                else:
                    common_namespaces = ["default", "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.batch_v1.read_namespaced_cron_job(
                                name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(
                                    f"Error searching for cronjob {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() == "node":
                resource_detail = self.v1.read_node(name=resource_name)
            elif resource_type.lower() == "namespace":
                resource_detail = self.v1.read_namespace(name=resource_name)
            elif resource_type.lower() == "configmap":
                if namespace:
                    resource_detail = self.v1.read_namespaced_config_map(
                        name=resource_name, namespace=namespace)
            elif resource_type.lower() == "secret":
                if namespace:
                    resource_detail = self.v1.read_namespaced_secret(
                        name=resource_name, namespace=namespace)
            elif resource_type.lower() == "ingress":
                if namespace:
                    resource_detail = self.networking_v1.read_namespaced_ingress(
                        name=resource_name, namespace=namespace)
            elif resource_type.lower() == "persistentvolume":
                resource_detail = self.v1.read_persistent_volume(
                    name=resource_name)
            elif resource_type.lower() == "persistentvolumeclaim":
                if namespace:
                    resource_detail = self.v1.read_namespaced_persistent_volume_claim(
                        name=resource_name, namespace=namespace)
            elif resource_type.lower() == "replicationcontroller":
                if namespace:
                    resource_detail = self.v1.read_namespaced_replication_controller(
                        name=resource_name, namespace=namespace)
            elif resource_type.lower() == "limitrange":
                if namespace:
                    resource_detail = self.v1.read_namespaced_limit_range(
                        name=resource_name, namespace=namespace)
            elif resource_type.lower() == "resourcequota":
                if namespace:
                    resource_detail = self.v1.read_namespaced_resource_quota(
                        name=resource_name, namespace=namespace)
            elif resource_type.lower() == "serviceaccount":
                if namespace:
                    resource_detail = self.v1.read_namespaced_service_account(
                        name=resource_name, namespace=namespace)
            elif resource_type.lower() in ["endpoint", "endpoints"]:
                if namespace:
                    resource_detail = self.v1.read_namespaced_endpoints(
                        name=resource_name, namespace=namespace)
                else:
                    common_namespaces = ["default", "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.v1.read_namespaced_endpoints(
                                name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(
                                    f"Error searching for endpoints {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() == "lease":
                if namespace:
                    resource_detail = self.coordination_v1.read_namespaced_lease(
                        name=resource_name, namespace=namespace)
            elif resource_type.lower() == "horizontalpodautoscaler":
                if namespace:
                    resource_detail = self.autoscaling_v2.read_namespaced_horizontal_pod_autoscaler(
                        name=resource_name, namespace=namespace)
            elif resource_type.lower() == "poddisruptionbudget":
                if namespace:
                    resource_detail = self.policy_v1.read_namespaced_pod_disruption_budget(
                        name=resource_name, namespace=namespace)
            elif resource_type.lower() == "priorityclass":
                resource_detail = self.scheduling_v1.read_priority_class(
                    name=resource_name)
            elif resource_type.lower() == "runtimeclass":
                resource_detail = self.node_v1.read_runtime_class(
                    name=resource_name)
            elif resource_type.lower() == "mutatingwebhookconfiguration":
                resource_detail = self.admissionregistration_v1.read_mutating_webhook_configuration(
                    name=resource_name)
            elif resource_type.lower() == "validatingwebhookconfiguration":
                resource_detail = self.admissionregistration_v1.read_validating_webhook_configuration(
                    name=resource_name)
            elif resource_type.lower() == "role":
                if namespace:
                    resource_detail = self.rbac_v1.read_namespaced_role(
                        name=resource_name, namespace=namespace)
            elif resource_type.lower() == "clusterrole":
                resource_detail = self.rbac_v1.read_cluster_role(
                    name=resource_name)
            elif resource_type.lower() == "rolebinding":
                if namespace:
                    resource_detail = self.rbac_v1.read_namespaced_role_binding(
                        name=resource_name, namespace=namespace)
            elif resource_type.lower() == "clusterrolebinding":
                resource_detail = self.rbac_v1.read_cluster_role_binding(
                    name=resource_name)
            elif resource_type.lower() == "customresourcedefinition":
                resource_detail = self.apiextensions_v1.read_custom_resource_definition(
                    name=resource_name)
            elif resource_type.lower() in ["networkpolicy", "networkpolicies"]:
                if namespace:
                    resource_detail = self.networking_v1.read_namespaced_network_policy(
                        name=resource_name, namespace=namespace)
                else:
                    common_namespaces = ["default", "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.networking_v1.read_namespaced_network_policy(
                                name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(
                                    f"Error searching for networkpolicy {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() in ["ingressclass", "ingressclasses"]:
                resource_detail = self.networking_v1.read_ingress_class(name=resource_name)
            elif resource_type.lower() in ["storageclass", "storageclasses"]:
                resource_detail = self.storage_v1.read_storage_class(name=resource_name)
            elif resource_type.lower() in ["event", "events"]:
                if namespace:
                    resource_detail = self.v1.read_namespaced_event(
                        name=resource_name, namespace=namespace)
                else:
                    common_namespaces = ["default", "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.v1.read_namespaced_event(
                                name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(
                                    f"Error searching for event {resource_name} in namespace {ns}: {ns_error}")
                            continue

            if resource_detail:
                # Convert to dictionary format for compatibility
                detail_dict = self.v1.api_client.sanitize_for_serialization(
                    resource_detail)
                # Emit signal with the resource detail
                self.resource_detail_loaded.emit(detail_dict)
                return detail_dict
            else:
                logging.debug(
                    f"Resource {resource_type}/{resource_name} not found - may not exist or be accessible")
                return None

        except Exception as e:
            # Handle API exceptions more gracefully
            error_str = str(e)
            if "404" in error_str or "not found" in error_str.lower():
                logging.debug(
                    f"Resource {resource_type}/{resource_name} not found in cluster")
                return None
            elif "403" in error_str or "forbidden" in error_str.lower():
                logging.debug(
                    f"Access denied to resource {resource_type}/{resource_name}")
                return None
            else:
                logging.error(
                    f"Error getting resource detail for {resource_type}/{resource_name}: {e}")
                self.error_occurred.emit(
                    f"Failed to get resource detail: {str(e)}")
                return None

    def _get_nodes(self):

        from Utils import get_timestamp_with_ms
        start_time = time.time()
        logging.debug(
            f"[API FETCH] {get_timestamp_with_ms()} - Kubernetes Client: Starting to fetch nodes from API")
        try:
            api_call_start = time.time()
            logging.debug(
                f"[API CALL] {get_timestamp_with_ms()} - Calling v1.list_node() API")
            nodes = self.v1.list_node().items
            api_call_time = (time.time() - api_call_start) * 1000

            logging.info(
                f"[API SUCCESS] {get_timestamp_with_ms()} - Fetched {len(nodes)} nodes in {api_call_time:.1f}ms")

            # Log detailed node data
            for i, node in enumerate(nodes[:5]):  # Log first 5 nodes in detail
                node_name = node.metadata.name if hasattr(
                    node.metadata, 'name') else f'unknown-{i}'
                node_status = 'Unknown'
                if hasattr(node, 'status') and node.status and hasattr(node.status, 'conditions'):
                    for condition in node.status.conditions:
                        if condition.type == 'Ready':
                            node_status = 'Ready' if condition.status == 'True' else 'NotReady'
                            break

                logging.debug(
                    f"[NODE DATA] {get_timestamp_with_ms()} - Node {i + 1}: name='{node_name}', status='{node_status}', has_capacity={hasattr(node.status, 'capacity') if hasattr(node, 'status') and node.status else False}")

            if len(nodes) > 5:
                logging.debug(
                    f"[NODE DATA] {get_timestamp_with_ms()} - ... and {len(nodes) - 5} more nodes")

            total_time = (time.time() - start_time) * 1000
            logging.debug(
                f"[API COMPLETE] {get_timestamp_with_ms()} - Total API fetch time: {total_time:.1f}ms")
            return nodes
        except Exception as e:
            error_time = (time.time() - start_time) * 1000
            logging.error(
                f'[API ERROR] {get_timestamp_with_ms()} - Failed to get nodes after {error_time:.1f}ms: {e}')
            return []

    def _get_namespaces(self):

        try:
            return self.v1.list_namespace().items
        except Exception as e:
            logging.error(f'Failed to get namespaces: {e}')
            return []

    def get_cache_stats(self) -> Dict[str, Any]:

        return self.service.get_cache_stats()

    def get_pods_for_node_async(self, node_name: str):

        logging.info(f"Getting pods for node {node_name}")

        class NodePodsWorker(EnhancedBaseWorker):
            def __init__(self, client_instance, node_name):
                super().__init__(f"node_pods_{node_name}")
                self.client_instance = client_instance
                self.node_name = node_name

            def execute(self):
                try:
                    # Get all pods for the specific node using field selector
                    all_pods = self.client_instance.v1.list_pod_for_all_namespaces(
                        field_selector=f"spec.nodeName={self.node_name}"
                    )

                    node_pods = []
                    for pod in all_pods.items:
                        pod_data = {
                            'name': pod.metadata.name,
                            'namespace': pod.metadata.namespace,
                            'status': pod.status.phase if pod.status and pod.status.phase else 'Unknown',
                            'cpu_usage': "N/A",
                            'memory_usage': "N/A"
                        }
                        node_pods.append(pod_data)

                    return node_pods

                except Exception as e:
                    logging.error(
                        f"Failed to get pods for node {self.node_name}: {str(e)}")
                    raise Exception(
                        f"Failed to get pods for node {self.node_name}: {str(e)}")

        worker = NodePodsWorker(self, node_name)

        # Connect signals with proper error handling
        def handle_success(result):
            try:
                self.pods_data_loaded.emit(result)
            except Exception as e:
                logging.error(f"Error emitting node pods result: {str(e)}")
                self.api_error.emit(f"Failed to emit node pods: {str(e)}")

        def handle_error(error):
            try:
                self.api_error.emit(
                    f"Failed to get pods for node: {str(error)}")
            except Exception as e:
                logging.error(f"Error emitting node pods error: {str(e)}")

        worker.signals.finished.connect(handle_success)
        worker.signals.error.connect(handle_error)

        # Submit to thread manager
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(f"node_pods_{node_name}", worker)

    def _get_deployment_rollout_history_sync(self, deployment_name: str, namespace: str = "default"):

        try:
            logging.info(
                f"Getting rollout history for deployment {deployment_name} in namespace {namespace}")

            # Get deployment with timeout protection
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                _request_timeout=APIClientConfig.DEPLOYMENT_OPERATION_TIMEOUT
            )

            # Get all ReplicaSets in the namespace first
            all_replica_sets = self.apps_v1.list_namespaced_replica_set(
                namespace=namespace,
                _request_timeout=APIClientConfig.DEPLOYMENT_OPERATION_TIMEOUT
            )

            # Filter ReplicaSets owned by this deployment
            deployment_replica_sets = []
            for rs in all_replica_sets.items:
                owner_refs = rs.metadata.owner_references or []
                for owner in owner_refs:
                    if (owner.kind == "Deployment"
                        and owner.name == deployment_name
                            and owner.uid == deployment.metadata.uid):
                        deployment_replica_sets.append(rs)
                        break

            logging.info(
                f"Found {len(deployment_replica_sets)} ReplicaSets for deployment {deployment_name}")

            history = []
            current_deployment_revision = int(deployment.metadata.annotations.get(
                "deployment.kubernetes.io/revision", "1"))

            for rs in deployment_replica_sets:
                annotations = rs.metadata.annotations or {}
                revision_str = annotations.get(
                    "deployment.kubernetes.io/revision", "1")

                try:
                    revision = int(revision_str)
                except (ValueError, TypeError):
                    revision = 1

                # Get creation timestamp
                creation_time = rs.metadata.creation_timestamp

                # Check if this is the current revision
                is_current = revision == current_deployment_revision

                # Get replicas info
                desired_replicas = rs.spec.replicas or 0
                ready_replicas = (
                    rs.status.ready_replicas or 0) if rs.status else 0
                available_replicas = (
                    rs.status.available_replicas or 0) if rs.status else 0

                # Extract change cause
                change_cause = annotations.get(
                    "kubernetes.io/change-cause", "No change cause recorded")

                # Get image information from the pod template
                containers = rs.spec.template.spec.containers or []
                images = [
                    container.image for container in containers] if containers else []

                history_item = {
                    "revision": revision,
                    "name": rs.metadata.name,
                    "creation_time": creation_time.isoformat() if creation_time else "",
                    "replicas": desired_replicas,
                    "ready_replicas": ready_replicas,
                    "available_replicas": available_replicas,
                    "current": is_current,
                    "change_cause": change_cause,
                    "images": images,
                    "template_hash": annotations.get("pod-template-hash", ""),
                    "status": "Current" if is_current else ("Available" if available_replicas > 0 else "Inactive")
                }
                history.append(history_item)
                logging.debug(f"Added revision {revision}: {history_item}")

            # Sort by revision number (descending)
            history.sort(key=lambda x: x["revision"], reverse=True)

            logging.info(
                f"Successfully processed {len(history)} revisions for deployment {deployment_name}")
            for item in history:
                logging.debug(
                    f"Revision {item['revision']}: Current={item['current']}, Status={item['status']}")

            return history

        except Exception as e:
            error_msg = f"Failed to get rollout history for deployment {deployment_name}: {str(e)}"
            logging.error(error_msg)
            raise Exception(error_msg)

    def _rollback_deployment_sync(self, deployment_name: str, revision: int, namespace: str = "default"):

        try:
            logging.info(
                f"Starting rollback of deployment {deployment_name} to revision {revision}")

            # Step 1: Get current deployment with timeout
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                _request_timeout=APIClientConfig.DEPLOYMENT_OPERATION_TIMEOUT
            )

            original_template_hash = deployment.spec.template.metadata.labels.get(
                "pod-template-hash", "")
            logging.debug(
                f"Current deployment template hash: {original_template_hash}")

            # Step 2: Find target ReplicaSet more robustly
            deployment_labels = deployment.metadata.labels or {}
            app_label = deployment_labels.get('app', deployment_name)

            # Try multiple label selectors
            selectors = [
                f"app={app_label}",
                f"app.kubernetes.io/name={deployment_name}",
                f"app.kubernetes.io/instance={deployment_name}"
            ]

            target_rs = None
            for selector in selectors:
                try:
                    replica_sets = self.apps_v1.list_namespaced_replica_set(
                        namespace=namespace,
                        label_selector=selector,
                        _request_timeout=APIClientConfig.DEPLOYMENT_OPERATION_TIMEOUT
                    )

                    for rs in replica_sets.items:
                        # Verify ownership
                        owner_refs = rs.metadata.owner_references or []
                        is_owned = any(
                            ref.kind == "Deployment" and ref.name == deployment_name
                            for ref in owner_refs
                        )

                        if is_owned:
                            annotations = rs.metadata.annotations or {}
                            rs_revision_str = annotations.get(
                                "deployment.kubernetes.io/revision", "1")
                            try:
                                rs_revision = int(rs_revision_str)
                                if rs_revision == revision:
                                    target_rs = rs
                                    break
                            except (ValueError, TypeError):
                                continue

                    if target_rs:
                        break

                except Exception as e:
                    logging.debug(
                        f"Selector {selector} failed during rollback: {str(e)}")
                    continue

            if not target_rs:
                raise Exception(
                    f"Revision {revision} not found for deployment {deployment_name}. Available revisions might be limited.")

            target_template_hash = target_rs.spec.template.metadata.labels.get(
                "pod-template-hash", "")
            logging.info(
                f"Found target ReplicaSet {target_rs.metadata.name} with template hash: {target_template_hash}")

            # Step 3: Prepare rollback patch
            # Clone the deployment spec to avoid mutations
            import copy
            rollback_deployment = copy.deepcopy(deployment)

            # Update the deployment template with target ReplicaSet template
            rollback_deployment.spec.template = target_rs.spec.template

            # Update annotations
            if not rollback_deployment.metadata.annotations:
                rollback_deployment.metadata.annotations = {}

            # Add rollback metadata
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            rollback_deployment.metadata.annotations.update({
                "kubernetes.io/change-cause": f"Rolled back to revision {revision} at {timestamp}",
                "deployment.kubernetes.io/rollback-revision": str(revision),
                "orchetrix.io/rollback-timestamp": timestamp
            })

            # Step 4: Perform the rollback with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logging.debug(
                        f"Rollback attempt {attempt + 1}/{max_retries}")

                    self.apps_v1.patch_namespaced_deployment(
                        name=deployment_name,
                        namespace=namespace,
                        body=rollback_deployment,
                        _request_timeout=APIClientConfig.ROLLBACK_OPERATION_TIMEOUT
                    )

                    logging.info(
                        f"Rollback patch applied successfully on attempt {attempt + 1}")
                    break

                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logging.warning(
                        f"Rollback attempt {attempt + 1} failed: {str(e)}, retrying...")
                    time.sleep(1)  # Brief delay before retry

            # Step 5: Verify rollback success
            success_msg = f"Successfully rolled back deployment {deployment_name} to revision {revision}"

            return {
                "success": True,
                "message": success_msg,
                "deployment": deployment_name,
                "revision": revision,
                "namespace": namespace,
                "original_template_hash": original_template_hash,
                "target_template_hash": target_template_hash,
                "target_replicaset": target_rs.metadata.name,
                "timestamp": timestamp
            }

        except Exception as e:
            error_msg = f"Failed to rollback deployment {deployment_name} to revision {revision}: {str(e)}"
            logging.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "deployment": deployment_name,
                "revision": revision,
                "namespace": namespace,
                "error_type": type(e).__name__
            }

    def cleanup(self):

        self._shutting_down = True
        self._disconnect_service_signals()
        self.service.cleanup()
        logging.info("KubernetesClient cleanup completed")

    def __del__(self):

        try:
            if hasattr(self, '_shutting_down') and not self._shutting_down:
                self.cleanup()
        except Exception as e:
            logging.error(f"Error in KubernetesClient destructor: {e}")

# Singleton management - backward compatibility
_instance = None
_instance_lock = threading.Lock()


def get_kubernetes_client():

    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = KubernetesClient()
    return _instance


def reset_kubernetes_client():

    global _instance
    if _instance:
        _instance.cleanup()
    _instance = None


def get_kubernetes_client_for_cluster(cluster_name: str):
    """Build an ApiClient bound strictly to a kubeconfig context.

    Unlike get_kubernetes_client() (a process-wide singleton whose context is
    mutated when the user switches clusters), this returns a fresh ApiClient
    isolated from global state — safe to use from background workers across
    fast cluster switches. Caller owns the client and must close() it.
    """
    if not cluster_name:
        return None
    try:
        from kubernetes import config as k8s_config
        return k8s_config.new_client_from_config(context=cluster_name)
    except Exception as e:
        logging.warning(f"get_kubernetes_client_for_cluster({cluster_name}) failed: {e}")
        return None


class KubernetesPodSSH(QObject):
    """
    SSH session manager for Kubernetes pods using kubectl exec
    """

    # Signals for SSH session management
    session_status = Signal(str)
    session_closed = Signal()
    data_received = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, pod_name: str, namespace: str, context: str = None):
        super().__init__()

        self.pod_name = pod_name
        self.namespace = namespace
        self.context = context
        self.process = None
        self.is_connected = False
        self._connecting = False  # Flag to suppress TTY errors during connection attempts
        self._shell_error_detected = False  # Track shell-not-found errors for fallback

    def connect_to_pod(self) -> bool:
        """
        Connect to pod using kubectl exec with improved shell detection and error handling
        """
        try:
            self.process = QProcess()
            self.process.readyReadStandardOutput.connect(self._handle_stdout)
            self.process.readyReadStandardError.connect(self._handle_stderr)
            self.process.finished.connect(self._handle_finished)
            self.process.errorOccurred.connect(self._handle_error)

            # Windows configuration to prevent terminal window
            if sys.platform == 'win32':
                self.process.setProcessEnvironment(
                    self.process.processEnvironment())
                try:
                    # Try to use setCreateProcessArgumentsModifier if available (PyQt6.5+)
                    if hasattr(self.process, 'setCreateProcessArgumentsModifier'):
                        self.process.setCreateProcessArgumentsModifier(
                            lambda args: args.setFlags(SUBPROCESS_FLAGS)
                        )
                except Exception as e:
                    # Fallback: method not available in this PyQt6 version
                    print(f"Note: setCreateProcessArgumentsModifier not available: {e}")

            # Try to connect with different shell options
            self._connecting = True  # Suppress TTY errors during connection attempts
            success = self._try_shell_connection()
            self._connecting = False

            if success:
                self.is_connected = True
                self.session_status.emit("Connected")
                return True
            else:
                self.error_occurred.emit("Failed to establish shell connection - no compatible shell found")
                return False

        except Exception as e:
            self._connecting = False
            # Check if this is a compatibility issue with setCreateProcessArgumentsModifier
            if "setCreateProcessArgumentsModifier" in str(e):
                # This is a known compatibility issue, not a real error
                logging.info(f"Compatibility note for pod {self.pod_name}: {e}")
                # Continue with connection - this is not a blocking error
                return True
            else:
                # Real connection error
                logging.error(f"Error connecting to pod {self.pod_name}: {e}")
                self.error_occurred.emit(f"Connection error: {str(e)}")
                return False

    def _try_shell_connection(self) -> bool:
        """
        Try different shell options and connection methods.

        Note: On Windows, the TTY error "Unable to use a TTY" is just a warning.
        The shell can still work with -it flags even after this warning.
        """
        # List of shells to try in order of preference
        shells = ["/bin/bash", "/bin/sh", "/bin/ash", "/usr/bin/sh"]

        # Try with -it flags first (works even on Windows despite TTY warning)
        for shell in shells:
            if self._attempt_connection_with_it_flags(shell):
                return True

        # Fallback to -i only for containers that really can't handle -t
        for shell in shells:
            if self._attempt_connection_without_tty(shell):
                return True

        return False

    def _attempt_connection_with_it_flags(self, shell: str) -> bool:
        """
        Attempt connection with -it flags.
        On Windows, this shows a TTY warning but the shell still works.
        """
        try:
            logging.info(f"Trying TTY connection to {self.pod_name} with {shell}")
            self._shell_error_detected = False  # Reset error flag for this attempt

            # Create a fresh process for each attempt to avoid "Process is already running" error
            if self.process:
                self.process.terminate()
                self.process.waitForFinished(1000)
                self.process.kill()  # Force kill if terminate didn't work
                self.process.waitForFinished(500)

            self.process = QProcess()
            self.process.readyReadStandardOutput.connect(self._handle_stdout)
            self.process.readyReadStandardError.connect(self._handle_stderr)
            self.process.finished.connect(self._handle_finished)
            self.process.errorOccurred.connect(self._handle_error)

            # Windows configuration
            if sys.platform == 'win32':
                self.process.setProcessEnvironment(self.process.processEnvironment())
                try:
                    if hasattr(self.process, 'setCreateProcessArgumentsModifier'):
                        self.process.setCreateProcessArgumentsModifier(
                            lambda args: args.setFlags(SUBPROCESS_FLAGS)
                        )
                except Exception:
                    pass

            cmd = "kubectl"
            args = ["exec", "-it", self.pod_name, "-n", self.namespace]
            if self.context:
                args.extend(["--context", self.context])
            args.extend(["--", shell])

            self.process.start(cmd, args)

            if self.process.waitForStarted(3000):
                # Give shell time to start
                self.process.waitForReadyRead(2000)

                # Wait for shell errors to propagate - kubectl exec takes time:
                # (connect to API → request exec → container tries shell → error)
                # Use waitForFinished instead of msleep to process Qt events (signals)
                self.process.waitForFinished(500)

                # Check if shell error was detected by stderr handler
                if self._shell_error_detected:
                    logging.info(f"Shell {shell} not available (error detected)")
                    return False

                # Check if process terminated quickly (sign of shell failure)
                if self.process.state() != QProcess.ProcessState.Running:
                    logging.info(f"Shell {shell} not available (process exited)")
                    return False

                logging.info(f"Connected to {self.pod_name} using {shell}")
                return True
            else:
                logging.info("Failed to start kubectl")
                return False

        except Exception as e:
            # Check if this is a compatibility issue with setCreateProcessArgumentsModifier
            if "setCreateProcessArgumentsModifier" in str(e):
                # This is a known compatibility issue, not a real error
                logging.info(f"Compatibility note for TTY connection: {e}")
                # Continue with connection - this is not a blocking error
                return True
            else:
                logging.error(f"Exception trying {shell} with TTY: {e}")
                return False

    def _attempt_connection_without_tty(self, shell: str) -> bool:
        """
        Attempt connection without TTY support (fallback for containers without TTY)
        """
        try:
            logging.info(f"Trying non-TTY connection to {self.pod_name} with {shell}")
            self._shell_error_detected = False  # Reset error flag for this attempt

            # Create a new process for non-TTY connection
            if self.process:
                self.process.terminate()
                self.process.waitForFinished(2000)
                if self.process.state() == QProcess.ProcessState.Running:
                    self.process.kill()
                    self.process.waitForFinished(500)

            self.process = QProcess()
            self.process.readyReadStandardOutput.connect(self._handle_stdout)
            self.process.readyReadStandardError.connect(self._handle_stderr)
            self.process.finished.connect(self._handle_finished)
            self.process.errorOccurred.connect(self._handle_error)

            # Windows configuration
            if sys.platform == 'win32':
                self.process.setProcessEnvironment(self.process.processEnvironment())
                try:
                    if hasattr(self.process, 'setCreateProcessArgumentsModifier'):
                        self.process.setCreateProcessArgumentsModifier(
                            lambda args: args.setFlags(SUBPROCESS_FLAGS)
                        )
                except Exception as e:
                    print(f"Note: setCreateProcessArgumentsModifier not available: {e}")

            cmd = "kubectl"
            args = ["exec", "-i", self.pod_name, "-n", self.namespace]
            if self.context:
                args.extend(["--context", self.context])
            args.extend(["--", shell])
            logging.info(f"Starting: {cmd} {' '.join(args)}")

            self.process.start(cmd, args)

            if self.process.waitForStarted(3000):
                # Give shell time to start
                self.process.waitForReadyRead(2000)

                # Wait for shell errors to propagate - kubectl exec takes time
                # Use waitForFinished instead of msleep to process Qt events (signals)
                self.process.waitForFinished(500)

                # Check if shell error was detected by stderr handler
                if self._shell_error_detected:
                    logging.info(f"Shell {shell} not available (non-TTY, error detected)")
                    return False

                # Check if process terminated quickly (sign of shell failure)
                if self.process.state() != QProcess.ProcessState.Running:
                    logging.info(f"Shell {shell} not available (non-TTY, process exited)")
                    return False

                logging.info(f"Connected to {self.pod_name} using {shell} (non-TTY)")
                return True
            else:
                logging.info("Failed to start kubectl (non-TTY)")
                return False

        except Exception as e:
            # Check if this is a compatibility issue with setCreateProcessArgumentsModifier
            if "setCreateProcessArgumentsModifier" in str(e):
                # This is a known compatibility issue, not a real error
                logging.info(f"Compatibility note for non-TTY connection: {e}")
                # Continue with connection - this is not a blocking error
                return True
            else:
                logging.error(f"Exception trying {shell} without TTY: {e}")
                return False

    def send_command(self, command: str):

        if self.process and self.is_connected:
            try:
                self.process.write(command.encode('utf-8'))
                return True
            except Exception as e:
                self.error_occurred.emit(f"Failed to send command: {str(e)}")
                return False
        return False

    def disconnect(self):

        if self.process:
            self.process.terminate()
            if not self.process.waitForFinished(500):
                self.process.kill()
                self.process.waitForFinished(200)
            self.is_connected = False
            self.session_status.emit("disconnected")
            self.session_closed.emit()  # Notify UI that session is closed

    def cleanup_ssh_session(self):

        self.disconnect()

    def _handle_stdout(self):

        if self.process:
            data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
            if data:
                self.data_received.emit(data)

    def _handle_stderr(self):

        if self.process:
            data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
            if data:
                # TTY warnings are expected on Windows - don't show them as errors
                if "Unable to use a TTY" in data or "input is not a terminal" in data:
                    logging.debug(f"TTY warning (expected): {data.strip()}")
                    return
                # During connection attempts, detect shell-not-found errors for fallback
                if self._connecting:
                    shell_errors = ["no such file", "not found", "cannot execute", "exec failed"]
                    if any(err in data.lower() for err in shell_errors):
                        self._shell_error_detected = True
                        logging.debug(f"Shell error detected during connection: {data.strip()}")
                        return  # Don't emit error - let fallback mechanism try other shells
                self.error_occurred.emit(data)

    def _handle_finished(self, exit_code, exit_status):

        # During connection attempts, process may be terminated for fallback - don't emit signals
        if self._connecting:
            logging.debug(f"Process finished during connection attempt (exit code {exit_code})")
            return
        self.is_connected = False
        self.session_status.emit("finished")
        self.session_closed.emit()
        logging.info(
            f"SSH session to {self.pod_name} finished with exit code {exit_code}")

    def _handle_error(self, error):

        self.is_connected = False
        error_msg = f"Process error: {error}"
        self.error_occurred.emit(error_msg)
        self.session_closed.emit()  # Notify UI that session is closed
        logging.error(f"SSH process error for {self.pod_name}: {error_msg}")
