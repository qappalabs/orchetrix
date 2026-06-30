import logging
from PyQt6.QtWidgets import QMessageBox, QProgressDialog, QApplication
from PyQt6.QtCore import Qt
from .resource_deleters import ResourceDeleterThread, BatchResourceDeleterThread

class ResourceDeletionManager:
    """
    Manages resource deletion operations for BaseResourcePage.
    """

    def __init__(self, page):
        self.page = page  # The BaseResourcePage instance
        self.delete_thread = None
        self.batch_delete_thread = None
        self.deletion_in_flight = False

    def handle_delete_selected(self, selected_items):
        """Handle the delete selected button click."""
        # Enhanced debugging for selection
        logging.debug(
            f"_handle_delete_selected called. Selected items: {len(selected_items) if selected_items else 0}")

        if not selected_items:
            QMessageBox.information(self.page, "No Selection",
                                    "Please select resources to delete by checking the checkboxes in the first column.")
            return

        # Convert to list once and reuse
        items_list = list(selected_items)
        logging.debug(f"Selected items content: {items_list}")

        # Confirmation dialog
        if not self.confirm_deletion(items_list):
            logging.debug("User cancelled deletion in confirmation dialog")
            return

        # Start deletion process (confirmation already done)
        logging.debug("Starting deletion process after confirmation")
        self.start_deletion_process(items_list)

    def confirm_deletion(self, selected_items):
        """Show confirmation dialog for multiple deletion."""
        count = len(selected_items)
        resource_name = self.page.resource_type or "resource"

        reply = QMessageBox.question(
            self.page,
            "Confirm Deletion",
            f"Are you sure you want to delete {count} {resource_name}(s)?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        return reply == QMessageBox.StandardButton.Yes

    def start_deletion_process(self, selected_items):
        """Internal method to trigger the appropriate deletion logic."""
        # Check if the page has specific deletion implementation overrides
        if hasattr(self.page, '_perform_deletion_without_confirmation'):
            self.page._perform_deletion_without_confirmation()
        elif hasattr(self.page, 'delete_selected_resources'):
            # If the page has its own delete logic, let it handle it
            # (though normally we'd want to consolidate here.
            #  For now, assume BaseResourcePage uses this manager for the default logic)
            self.delete_selected_resources(selected_items)
        else:
            QMessageBox.information(
                self.page,
                "Not Implemented",
                "Delete functionality not implemented for this resource type."
            )

    def delete_selected_resources(self, selected_items_list):
        """Perform batch deletion."""
        # Shared gate: blocks any new deletion while either a single or batch
        # delete is already in flight, preventing duplicate DELETEs and racing
        # completion callbacks.
        if self.deletion_in_flight:
            QMessageBox.information(
                self.page, "Deletion In Progress",
                "A deletion is already in progress. Please wait for it to complete.")
            return

        if not selected_items_list:
            logging.warning("No items to delete")
            return

        # Validation (using page's validation logic if available)
        validated_items = []
        for resource_name, namespace in selected_items_list:
            # Check if page has validation method, default to valid if not
            if hasattr(self.page, '_validate_resource_name'):
                is_valid = self.page._validate_resource_name(resource_name)
            else:
                is_valid = True  # Default: treat as valid if no validation exists
            
            if is_valid:
                validated_items.append((resource_name, namespace))
            else:
                logging.warning(
                    f"Skipping invalid resource name for deletion: {resource_name}")

        if not validated_items:
            QMessageBox.information(
                self.page, "Invalid Selection", "No valid resources selected for deletion.")
            return

        count = len(validated_items)
        
        # NOTE: Confirmation redundant if called from handle_delete_selected, 
        # but kept if called directly. Assuming handle_delete_selected flow.

        progress = QProgressDialog(
            f"Deleting {count} {self.page.resource_type}...", "Cancel", 0, count, self.page)
        progress.setWindowTitle("Deleting Resources")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setValue(0)
        progress.show()

        QApplication.processEvents()

        try:
            self.batch_delete_thread = BatchResourceDeleterThread(
                self.page.resource_type, validated_items)
            self.batch_delete_thread.batch_delete_progress.connect(
                lambda current, total: progress.setValue(current))
            self.batch_delete_thread.batch_delete_completed.connect(
                lambda success, errors: self.on_batch_delete_completed(success, errors, progress))
            # finished is a safety net: clears the flag even if the completion
            # signal is never emitted (e.g. thread crash or force-quit).
            self.batch_delete_thread.finished.connect(self._clear_deletion_flag)
            self.deletion_in_flight = True
            self.batch_delete_thread.start()
        except Exception as e:
            self.deletion_in_flight = False
            progress.close()
            QMessageBox.critical(self.page, "Delete Error",
                                 f"Failed to start deletion process: {str(e)}")
            logging.error(f"Error starting batch delete thread: {e}")

    def on_batch_delete_completed(self, success_list, error_list, progress_dialog):
        """Callback for batch deletion completion."""
        self.deletion_in_flight = False
        try:
            progress_dialog.close()
            success_count = len(success_list)
            error_count = len(error_list)
            result_message = f"Deleted {success_count} of {success_count + error_count} {self.page.resource_type}."

            if error_count > 0:
                result_message += f"\n\nFailed to delete {error_count} resources:"
                for name, namespace, error in error_list[:5]:
                    ns_text = f" in namespace {namespace}" if namespace else ""
                    result_message += f"\n- {name}{ns_text}: {error}"
                if error_count > 5:
                    result_message += f"\n... and {error_count - 5} more."

            # Clear selected items on page
            if hasattr(self.page, 'selected_items'):
                self.page.selected_items.clear()

            QMessageBox.information(self.page, "Deletion Results", result_message)

            self._refresh_after_delete()

        except Exception as e:
            logging.error(f"Error in batch delete completion handler: {e}")
            QMessageBox.critical(
                self.page, "Error", f"Error processing deletion results: {str(e)}")
            try:
                self._refresh_after_delete()
            except Exception as inner_exc:
                logging.error(f"Failed to refresh data after deletion error: {inner_exc}")

    def delete_resource_single(self, resource_name, resource_namespace):
        """Delete a single resource."""
        if self.deletion_in_flight:
            QMessageBox.information(
                self.page, "Deletion In Progress",
                "A deletion is already in progress. Please wait for it to complete.")
            return

        ns_text = f" in namespace {resource_namespace}" if resource_namespace else ""
        result = QMessageBox.warning(
            self.page, "Confirm Deletion",
            f"Are you sure you want to delete {self.page.resource_type}/{resource_name}{ns_text}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        self.delete_thread = ResourceDeleterThread(
            self.page.resource_type, resource_name, resource_namespace)
        self.delete_thread.delete_completed.connect(self.on_delete_completed)
        self.delete_thread.finished.connect(self._clear_deletion_flag)
        self.deletion_in_flight = True
        self.delete_thread.start()

    def on_delete_completed(self, success, message, resource_name, resource_namespace):
        """Callback for single resource deletion."""
        self.deletion_in_flight = False
        if success:
            QMessageBox.information(self.page, "Deletion Successful", message)
            if hasattr(self.page, 'selected_items'):
                self.page.selected_items.discard((resource_name, resource_namespace))
            self._refresh_after_delete()
        else:
            QMessageBox.critical(self.page, "Deletion Failed", message)

    def _clear_deletion_flag(self):
        """Safety net: reset the in-flight flag when a thread finishes for any reason."""
        self.deletion_in_flight = False

    def _refresh_after_delete(self):
        # When a watch is active for this page's (resource_type, namespace),
        # the kubelet's MODIFIED (Terminating) and DELETED events will reach
        # the table via the normal watch path within the throttle window.
        # Calling force_load_data() here issues a redundant LIST that
        # interrupts the watch stream and causes the visible UI lag.
        if not hasattr(self.page, 'force_load_data') or not callable(self.page.force_load_data):
            logging.warning("Page does not have force_load_data method, skipping refresh")
            return
        try:
            from Utils.unified_resource_loader import get_unified_resource_loader
            resource_type = getattr(self.page, 'resource_type', None)
            # Read via the public watch_namespace property so this module never
            # depends on the page's internal storage name.  Defaults to None for
            # pages without watches (e.g. ChartsPage), which makes has_active_watch
            # return False and falls through to force_load_data().
            watch_ns = getattr(self.page, 'watch_namespace', None)
            if resource_type is not None and get_unified_resource_loader().has_active_watch(resource_type, watch_ns):
                return
        except Exception as e:
            logging.debug(f"Watch-active check failed; falling back to force_load_data: {e}")
        self.page.force_load_data()

    def cleanup(self):
        """Stop any running threads."""
        if self.delete_thread and self.delete_thread.isRunning():
            self.delete_thread.quit()
            self.delete_thread.wait()
        if self.batch_delete_thread and self.batch_delete_thread.isRunning():
            self.batch_delete_thread.quit()
            self.batch_delete_thread.wait()
        self.deletion_in_flight = False
