import logging
from PyQt6.QtCore import QThread, pyqtSignal
from Services.kubernetes.api_service import get_kubernetes_api_service
from Utils.thread_manager import is_shutdown_requested


class ResourceDeleterThread(QThread):
    """Thread for deleting a single Kubernetes resource"""
    delete_completed = pyqtSignal(bool, str, str, str)

    def __init__(self, resource_type, resource_name, namespace, parent=None):
        super().__init__(parent)
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace
        self.api_service = get_kubernetes_api_service()
        self._is_running = True

    def stop(self):
        """Stop the deletion thread"""
        self._is_running = False

    def is_interrupted(self):
        """Check if worker should stop or if global shutdown is requested"""
        return not self._is_running or is_shutdown_requested()

    def run(self):
        """Execute the resource deletion"""
        if self.is_interrupted():
            return

        try:
            self.api_service.delete_resource(
                resource_type=self.resource_type,
                name=self.resource_name,
                namespace=self.namespace
            )

            if self.is_interrupted():
                return

            self.delete_completed.emit(
                True,
                f"{self.resource_type}/{self.resource_name} deleted successfully.",
                self.resource_name,
                self.namespace
            )

        except Exception as e:
            if self.is_interrupted():
                return
            
            error_msg = self._format_error(e)
            logging.error(f"Deletion failed for {self.resource_type}/{self.resource_name}: {error_msg}")
            
            self.delete_completed.emit(
                False,
                error_msg,
                self.resource_name,
                self.namespace
            )

    def _format_error(self, e):
        """Standardize error message formatting."""
        reason = getattr(e, 'reason', None)
        if reason:
            return f"API error: {reason}"
        return str(e)


class BatchResourceDeleterThread(QThread):
    """Thread for deleting multiple Kubernetes resources in batch"""
    batch_delete_progress = pyqtSignal(int, int)
    batch_delete_completed = pyqtSignal(list, list)

    def __init__(self, resource_type, resources_to_delete, parent=None):
        super().__init__(parent)
        self.resource_type = resource_type
        self.resources_to_delete = resources_to_delete
        self.api_service = get_kubernetes_api_service()
        self._is_running = True

    def stop(self):
        """Stop the batch deletion thread"""
        self._is_running = False

    def is_interrupted(self):
        """Check if worker should stop or if global shutdown is requested"""
        return not self._is_running or is_shutdown_requested()

    def run(self):
        """Execute batch resource deletion"""
        if self.is_interrupted():
            return

        success_list = []
        error_list = []
        total_count = len(self.resources_to_delete)

        for index, (resource_name, namespace) in enumerate(self.resources_to_delete):
            if self.is_interrupted():
                break

            try:
                self.batch_delete_progress.emit(index, total_count)

                self.api_service.delete_resource(
                    resource_type=self.resource_type,
                    name=resource_name,
                    namespace=namespace
                )
                success_list.append((resource_name, namespace))

            except Exception as e:
                error_msg = self._format_error(e, resource_name)
                error_list.append((resource_name, namespace, error_msg))

        if not self.is_interrupted():
            self.batch_delete_progress.emit(total_count, total_count)
            self.batch_delete_completed.emit(success_list, error_list)

    def _format_error(self, e, resource_name):
        """Format batch error with context."""
        status_code = getattr(e, 'status', None)
        reason = getattr(e, 'reason', None)
        
        if status_code == 404:
            return "Resource not found (already deleted)"
        if reason:
            return f"API error: {reason}"
        return str(e)
