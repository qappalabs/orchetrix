"""
Extended BaseTablePage for handling Kubernetes resources with live data.
This module handles common resource operations like listing, deletion, and editing.
"""

import os
import tempfile
import yaml
import subprocess
from PyQt6.QtWidgets import (
     QMessageBox, QWidget, QVBoxLayout, QLineEdit, QComboBox,
    QLabel, QProgressBar, QHBoxLayout, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from base_components.base_components import BaseTablePage
from UI.Styles import AppStyles

class KubernetesResourceLoader(QThread):
    """Thread for loading Kubernetes resources without blocking the UI."""
    resources_loaded = pyqtSignal(list, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, resource_type, namespace=None):
        super().__init__()
        self.resource_type = resource_type
        self.namespace = namespace
        
    def run(self):
        """Execute the kubectl command and emit results."""
        try:
            cmd = ["kubectl", "get", self.resource_type]
            
            # Use namespace if specified
            if self.namespace and self.namespace != "all":
                cmd.extend(["-n", self.namespace])
            else:
                cmd.append("--all-namespaces")
                
            cmd.extend(["-o", "json"])
            
            # Execute the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Process the result
            import json
            data = json.loads(result.stdout)
            
            # Extract and format items
            resources = []
            if "items" in data:
                for item in data["items"]:
                    # Get resource details
                    metadata = item.get("metadata", {})
                    name = metadata.get("name", "")
                    namespace = metadata.get("namespace", "default")
                    
                    # Get resource age
                    creation_time = metadata.get("creationTimestamp", "")
                    age = self._format_age(creation_time)
                    
                    # Create resource object with common fields
                    resource = {
                        "name": name,
                        "namespace": namespace,
                        "age": age,
                        "raw_data": item  # Store the raw data for editing
                    }
                    
                    # Add resource-specific fields based on type
                    self._add_resource_specific_fields(resource, item)
                    resources.append(resource)
            
            # Emit the result
            self.resources_loaded.emit(resources, self.resource_type)
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Error loading {self.resource_type}: {e.stderr}"
            self.error_occurred.emit(error_msg)
        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
            
    def _format_age(self, timestamp):
        """Format the age field from a timestamp."""
        if not timestamp:
            return "Unknown"
            
        import datetime
        try:
            # Convert ISO timestamp to Python datetime
            timestamp = timestamp.replace('Z', '+00:00')
            created_time = datetime.datetime.fromisoformat(timestamp)
            now = datetime.datetime.now(datetime.timezone.utc)
            
            # Calculate the difference
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
            
    def _add_resource_specific_fields(self, resource, item):
        """Add fields specific to the resource type."""
        # This can be extended for specific resource types
        # For now, handle basic types

        # For ConfigMaps, get keys
        if self.resource_type == "configmaps":
            data_keys = list(item.get("data", {}).keys())
            resource["keys"] = ", ".join(data_keys) if data_keys else "<none>"
            
        # For Secrets, get type and keys
        elif self.resource_type == "secrets":
            resource["type"] = item.get("type", "Opaque")
            data_keys = list(item.get("data", {}).keys())
            resource["keys"] = ", ".join(data_keys) if data_keys else "<none>"
            
            # Add labels field
            labels = item.get("metadata", {}).get("labels", {})
            label_str = ", ".join([f"{k}={v}" for k, v in labels.items()]) if labels else "<none>"
            resource["labels"] = label_str
            
        # For ResourceQuotas
        elif self.resource_type == "resourcequotas":
            pass  # Basic fields are sufficient
            
        # For LimitRanges
        elif self.resource_type == "limitranges":
            pass  # Basic fields are sufficient
            
        # For HPA
        elif self.resource_type == "horizontalpodautoscalers":
            spec = item.get("spec", {})
            status = item.get("status", {})
            
            resource["min_pods"] = str(spec.get("minReplicas", "N/A"))
            resource["max_pods"] = str(spec.get("maxReplicas", "N/A"))
            resource["current_replicas"] = str(status.get("currentReplicas", "0"))
            
            # Get metrics
            metrics = []
            for metric in spec.get("metrics", []):
                metric_type = metric.get("type", "")
                if metric_type == "Resource" and "resource" in metric:
                    resource_name = metric["resource"].get("name", "")
                    if "targetAverageUtilization" in metric["resource"]:
                        metrics.append(f"{resource_name}/{metric['resource']['targetAverageUtilization']}%")
                    elif "targetAverageValue" in metric["resource"]:
                        metrics.append(f"{resource_name}/{metric['resource']['targetAverageValue']}")
            
            resource["metrics"] = ", ".join(metrics) if metrics else "None"
            resource["status"] = "Scaling" if status.get("currentReplicas") != status.get("desiredReplicas") else "Healthy"
            
        # For PodDisruptionBudgets
        elif self.resource_type == "poddisruptionbudgets":
            spec = item.get("spec", {})
            status = item.get("status", {})
            
            resource["min_available"] = str(spec.get("minAvailable", "N/A")) 
            resource["max_unavailable"] = str(spec.get("maxUnavailable", "N/A"))
            resource["current_healthy"] = str(status.get("currentHealthy", "0"))
            resource["desired_healthy"] = str(status.get("desiredHealthy", "0"))
            
        # For PriorityClasses
        elif self.resource_type == "priorityclasses":
            resource["value"] = str(item.get("value", "0"))
            resource["global_default"] = str(item.get("globalDefault", False)).lower()
            
        # For RuntimeClasses
        elif self.resource_type == "runtimeclasses":
            resource["handler"] = item.get("handler", "")
            
        # For Leases
        elif self.resource_type == "leases":
            spec = item.get("spec", {})
            resource["holder"] = spec.get("holderIdentity", "")
            
        # For MutatingWebhookConfigurations
        elif self.resource_type in ["mutatingwebhookconfigurations", "validatingwebhookconfigurations"]:
            webhooks = item.get("webhooks", [])
            resource["webhooks"] = str(len(webhooks))
            
        # For Endpoints
        elif self.resource_type == "endpoints":
            subsets = item.get("subsets", [])
            endpoints = []
            
            for subset in subsets:
                addresses = subset.get("addresses", [])
                for address in addresses:
                    ip = address.get("ip", "")
                    if ip:
                        endpoints.append(ip)
            
            resource["endpoints"] = ", ".join(endpoints) if endpoints else "<none>"


class ResourceEditorThread(QThread):
    """Thread for editing Kubernetes resources."""
    edit_completed = pyqtSignal(bool, str)
    
    def __init__(self, resource_type, resource_name, namespace, yaml_content):
        super().__init__()
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace
        self.yaml_content = yaml_content
        
    def run(self):
        """Save the edited resource."""
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w") as temp:
                temp.write(self.yaml_content)
                temp_path = temp.name
            
            # Apply the updated resource
            cmd = ["kubectl", "apply", "-f", temp_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Clean up the temp file
            os.unlink(temp_path)
            
            # Report success
            self.edit_completed.emit(True, result.stdout)
            
        except subprocess.CalledProcessError as e:
            # Report error
            self.edit_completed.emit(False, f"Error applying changes: {e.stderr}")
        except Exception as e:
            self.edit_completed.emit(False, f"Error: {str(e)}")


class ResourceDeleterThread(QThread):
    """Thread for deleting Kubernetes resources."""
    delete_completed = pyqtSignal(bool, str, str, str)
    
    def __init__(self, resource_type, resource_name, namespace):
        super().__init__()
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace
        
    def run(self):
        """Delete the specified resource."""
        try:
            cmd = ["kubectl", "delete", self.resource_type, self.resource_name]
            
            # Use namespace if not a cluster-scoped resource
            if self.namespace:
                cmd.extend(["-n", self.namespace])
                
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Report success
            self.delete_completed.emit(
                True, 
                f"{self.resource_type}/{self.resource_name} deleted successfully", 
                self.resource_name,
                self.namespace
            )
            
        except subprocess.CalledProcessError as e:
            # Report error
            self.delete_completed.emit(
                False, 
                f"Error deleting {self.resource_type}/{self.resource_name}: {e.stderr}",
                self.resource_name,
                self.namespace
            )
        except Exception as e:
            self.delete_completed.emit(
                False, 
                f"Error: {str(e)}", 
                self.resource_name,
                self.namespace
            )


class BatchResourceDeleterThread(QThread):
    """Thread for deleting multiple Kubernetes resources."""
    batch_delete_progress = pyqtSignal(int, int)
    batch_delete_completed = pyqtSignal(list, list)
    
    def __init__(self, resource_type, resources):
        super().__init__()
        self.resource_type = resource_type
        self.resources = resources  # List of (name, namespace) tuples
        
    def run(self):
        """Delete all specified resources."""
        success_list = []
        error_list = []
        
        for i, (name, namespace) in enumerate(self.resources):
            try:
                cmd = ["kubectl", "delete", self.resource_type, name]
                
                # Use namespace if not a cluster-scoped resource
                if namespace:
                    cmd.extend(["-n", namespace])
                    
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # Add to success list
                success_list.append((name, namespace))
                
            except subprocess.CalledProcessError as e:
                # Add to error list
                error_list.append((name, namespace, str(e.stderr)))
            except Exception as e:
                # Add to error list
                error_list.append((name, namespace, str(e)))
                
            # Report progress
            self.batch_delete_progress.emit(i + 1, len(self.resources))
            
        # Report final results
        self.batch_delete_completed.emit(success_list, error_list)


class BaseResourcePage(BaseTablePage):
    """
    A base class for all Kubernetes resource pages that handles:
    1. Loading and displaying dynamic data from kubectl
    2. Editing resources
    3. Deleting resources (individual and batch)
    4. Handling error states
    
    This should be subclassed for specific resource types.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = None  # To be set by subclasses
        self.resources = []
        self.namespace_filter = "all"  # Default to all namespaces
        self.loading_thread = None
        self.delete_thread = None
        self.edit_thread = None
        self.batch_delete_thread = None
        self.is_loading = False
        self.selected_items = set()  # Track selected items by (name, namespace)
        self.reload_on_show = True  # Always reload data when page is shown
        
    def setup_ui(self, title, headers, sortable_columns=None):
        """Set up the UI with an added refresh button and namespace selector."""
        layout = super().setup_ui(title, headers, sortable_columns)
        
        # Create a refresh button in the header
        self._add_refresh_button()
        
        return layout

    def _add_filter_controls(self, header_layout):
        """Add namespace filter dropdown and search bar to the header layout"""
        # Check if this resource has a namespace column
        has_namespace_column = False
        if hasattr(self, 'table') and self.table.columnCount() > 0:
            for col in range(self.table.columnCount()):
                header_item = self.table.horizontalHeaderItem(col)
                if header_item and header_item.text() == "Namespace":
                    has_namespace_column = True
                    break
        
        # Create a layout for the filters
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)
        
        # Create search bar matching the header style
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search resources...")
        self.search_bar.setFixedHeight(AppStyles.SEARCH_BAR_HEIGHT)
        self.search_bar.setMinimumWidth(AppStyles.SEARCH_BAR_MIN_WIDTH)
        self.search_bar.setStyleSheet(AppStyles.SEARCH_BAR_STYLE)
        self.search_bar.textChanged.connect(self._handle_search)
        filters_layout.addWidget(self.search_bar)
        
        # Create namespace filter dropdown if needed
        if has_namespace_column:
            self.namespace_combo = QComboBox()
            self.namespace_combo.setFixedHeight(AppStyles.SEARCH_BAR_HEIGHT)  # Match search bar height
            self.namespace_combo.setMinimumWidth(150)
            self.namespace_combo.setStyleSheet("""
                QComboBox {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-size: 13px;
                }
                QComboBox:hover {
                    border: 1px solid #555555;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox::down-arrow {
                    image: none;
                    color: #aaaaaa;
                }
                QComboBox QAbstractItemView {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    selection-background-color: #0078d7;
                    border: 1px solid #3d3d3d;
                    padding: 5px;
                }
            """)
            self.namespace_combo.addItem("All Namespaces")
            self.namespace_combo.currentTextChanged.connect(self._handle_namespace_change)
            filters_layout.addWidget(self.namespace_combo)
            
            # Load namespaces
            self._load_namespaces()
        
        # Add the filters layout to the header layout
        header_layout.addLayout(filters_layout)
        header_layout.addStretch()
    def _handle_search(self, text):
        """Filter resources based on search text"""
        self._apply_filters()

    def _handle_namespace_change(self, namespace):
        """Filter resources based on selected namespace"""
        self._apply_filters()

    def _apply_filters(self):
        """Apply both namespace and search filters"""
        if not hasattr(self, 'table') or self.table.rowCount() == 0:
            return
            
        # Get the search text
        search_text = self.search_bar.text().lower() if hasattr(self, 'search_bar') else ""
        
        # Get the selected namespace
        selected_namespace = None
        if hasattr(self, 'namespace_combo') and self.namespace_combo.currentText() != "All Namespaces":
            selected_namespace = self.namespace_combo.currentText()
        
        # Hide rows that don't match the filters
        for row in range(self.table.rowCount()):
            show_row = True
            
            # Apply namespace filter if selected
            if selected_namespace:
                namespace_col = None
                for col in range(self.table.columnCount()):
                    header_item = self.table.horizontalHeaderItem(col)
                    if header_item and header_item.text() == "Namespace":
                        namespace_col = col
                        break
                
                if namespace_col is not None:
                    namespace_text = ""
                    item = self.table.item(row, namespace_col)
                    if item:
                        namespace_text = item.text()
                    else:
                        # Check if the cell has a widget (like a QLabel)
                        cell_widget = self.table.cellWidget(row, namespace_col)
                        if cell_widget:
                            for label in cell_widget.findChildren(QLabel):
                                namespace_text = label.text()
                                break
                    
                    if namespace_text != selected_namespace:
                        show_row = False
            
            # Apply search filter if text is entered
            if show_row and search_text:
                row_matches = False
                for col in range(1, self.table.columnCount() - 1):  # Skip checkbox and actions columns
                    # Check regular table items
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        row_matches = True
                        break
                    
                    # Check for cell widgets (like status labels)
                    cell_widget = self.table.cellWidget(row, col)
                    if cell_widget:
                        widget_text = ""
                        # Handle StatusLabel widgets which contain a QLabel
                        for label in cell_widget.findChildren(QLabel):
                            widget_text += label.text() + " "
                        
                        if search_text in widget_text.lower():
                            row_matches = True
                            break
                
                if not row_matches:
                    show_row = False
            
            # Show or hide the row based on filters
            self.table.setRowHidden(row, not show_row)

    def _load_namespaces(self):
        """Load namespaces from Kubernetes cluster"""
        if not hasattr(self, 'namespace_combo'):
            return
            
        try:
            import subprocess
            import json
            
            # Run kubectl command to get namespaces
            result = subprocess.run(
                ["kubectl", "get", "namespaces", "-o", "json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                namespaces = []
                
                for item in data.get("items", []):
                    name = item.get("metadata", {}).get("name")
                    if name:
                        namespaces.append(name)
                
                # Update the combo box
                current_selection = self.namespace_combo.currentText()
                self.namespace_combo.clear()
                self.namespace_combo.addItem("All Namespaces")
                self.namespace_combo.addItems(sorted(namespaces))
                
                # Restore the previous selection if it still exists
                index = self.namespace_combo.findText(current_selection)
                if index >= 0:
                    self.namespace_combo.setCurrentIndex(index)
        except Exception as e:
            print(f"Error loading namespaces: {str(e)}")
            # If we can't load namespaces, just add default namespace
            self.namespace_combo.clear()
            self.namespace_combo.addItem("All Namespaces")
            self.namespace_combo.addItem("default")
    
    def _add_refresh_button(self):
        """Add a refresh button and filter controls to the page header."""
        # Find the header layout
        header_layout = None
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if isinstance(item, QHBoxLayout):
                header_layout = item
                break
                
        if not header_layout:
            # Create a new header layout if none exists
            header_layout = QHBoxLayout()
            self.layout().insertLayout(0, header_layout)
        
        # Add filter controls first (to the left of the refresh button)
        self._add_filter_controls(header_layout)
        
        # Create refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        refresh_btn.clicked.connect(self.load_data)
        
        # Add button to header (no more stretch before it)
        header_layout.addWidget(refresh_btn)
    def force_load_data(self):
        """Force reload data regardless of loading state."""
        # Reset loading state and call load_data
        self.is_loading = False
        self.load_data()
    
    def showEvent(self, event):
        """Load data when the page is shown."""
        super().showEvent(event)
        
        # Load data if needed
        if self.reload_on_show and not self.is_loading:
            self.load_data()
    
    def __del__(self):
        """Ensure proper cleanup of threads before destruction"""
        self.cleanup_threads()
    def cleanup_threads(self):
        """Clean up any running threads safely"""
        threads_to_cleanup = [
            'loading_thread', 
            'delete_thread', 
            'edit_thread', 
            'batch_delete_thread'
        ]
        
        for thread_name in threads_to_cleanup:
            thread = getattr(self, thread_name, None)
            if thread and thread.isRunning():
                thread.wait(300)  # Wait up to 300ms for thread to finish
    def hideEvent(self, event):
        """Clean up threads when the page is hidden"""
        super().hideEvent(event)
        # This ensures threads are stopped when switching away from this page
        self.cleanup_threads()
            
    def load_data(self):
        """Load resource data from Kubernetes."""
        if self.is_loading:
            return
        
        # Clean up any existing loading thread first    
        if hasattr(self, 'loading_thread') and self.loading_thread and self.loading_thread.isRunning():
            self.loading_thread.wait(300)  # Wait for it to finish with timeout
        
            # Reset search filter if it exists
        if hasattr(self, 'search_bar'):
            self.search_bar.blockSignals(True)  # Prevent triggering filter while loading
            self.search_bar.clear()
            self.search_bar.blockSignals(False)
            
        self.is_loading = True
        self.resources = []
        self.selected_items.clear()
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        # Show loading indicator
        loading_row = self.table.rowCount()
        self.table.setRowCount(loading_row + 1)
        self.table.setSpan(loading_row, 0, 1, self.table.columnCount())
        
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_layout.setContentsMargins(20, 20, 20, 20)
        
        loading_bar = QProgressBar()
        loading_bar.setRange(0, 0)  # Indeterminate
        loading_bar.setTextVisible(False)
        loading_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                background-color: #1e1e1e;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
            }
        """)
        
        loading_text = QLabel(f"Loading {self.resource_type}...")
        loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        loading_layout.addWidget(loading_text)
        loading_layout.addWidget(loading_bar)
        
        self.table.setCellWidget(loading_row, 0, loading_widget)
        
        # Start loading thread
        self.loading_thread = KubernetesResourceLoader(self.resource_type, self.namespace_filter)
        self.loading_thread.resources_loaded.connect(self.on_resources_loaded)
        self.loading_thread.error_occurred.connect(self.on_load_error)
        self.loading_thread.start()
    
    def on_resources_loaded(self, resources, resource_type):
        """Handle loaded resources with empty message overlaying the table area."""
        self.is_loading = False
        
        # Store resources
        self.resources = resources
        
        # Update the item count
        self.items_count.setText(f"{len(resources)} items")
        
        # Check if resources list is empty
        if not resources:
            # Clear all rows but keep table visible
            self.table.setRowCount(0)
            
            # Create overlay label if it doesn't exist
            if not hasattr(self, 'empty_overlay'):
                # Create an overlay widget that sits on top of the table body area
                self.empty_overlay = QLabel("Item list is empty")
                self.empty_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.empty_overlay.setStyleSheet("""
                    color: #888888;
                    font-size: 16px;
                    font-weight: bold;
                    background-color: transparent;
                """)
                
                # Add the widget as sibling to the table
                self.layout().addWidget(self.empty_overlay)
                
                # Initially hidden
                self.empty_overlay.hide()
            
            # Position the overlay to cover the table body area (but below headers)
            header_height = self.table.horizontalHeader().height()
            self.empty_overlay.setGeometry(
                self.table.x(),
                self.table.y() + header_height,
                self.table.width(),
                self.table.height() - header_height
            )
            
            # Show the overlay
            self.empty_overlay.raise_()  # Bring to front
            self.empty_overlay.show()
            
            # Disable sorting when empty
            self.table.setSortingEnabled(False)
        else:
            # Normal case - populate the table with data
            self.table.setRowCount(0)  # Clear first
            self.populate_table(resources)
            self.table.setSortingEnabled(True)
            
            # Hide the overlay if it exists
            if hasattr(self, 'empty_overlay'):
                self.empty_overlay.hide()
        # Refresh namespaces list in the dropdown
        if hasattr(self, 'namespace_combo'):
            self._load_namespaces()
        
        # Apply any existing filters
        self._apply_filters()
        
    def resizeEvent(self, event):
        """Handle resizing of the widget to properly position the empty overlay."""
        super().resizeEvent(event)
        
        # Update empty overlay position if it exists
        if hasattr(self, 'empty_overlay') and self.empty_overlay.isVisible():
            header_height = self.table.horizontalHeader().height()
            self.empty_overlay.setGeometry(
                self.table.x(),
                self.table.y() + header_height,
                self.table.width(),
                self.table.height() - header_height
            )
            
    def eventFilter(self, watched, event):
        """Filter events to update overlay position when table geometry changes."""
        if (watched == self.table and event.type() in 
                (event.Type.Resize, event.Type.Move, event.Type.Show)):
            if hasattr(self, 'empty_overlay') and self.empty_overlay.isVisible():
                header_height = self.table.horizontalHeader().height()
                self.empty_overlay.setGeometry(
                    self.table.x(),
                    self.table.y() + header_height,
                    self.table.width(),
                    self.table.height() - header_height
                )
        
        return super().eventFilter(watched, event)
    def on_load_error(self, error_message):
        """Handle loading errors."""
        self.is_loading = False
        
        # Clear loading indicator
        self.table.setRowCount(0)
        
        # Show error message
        error_row = self.table.rowCount()
        self.table.setRowCount(error_row + 1)
        self.table.setSpan(error_row, 0, 1, self.table.columnCount())
        
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_layout.setContentsMargins(20, 30, 20, 30)
        
        error_text = QLabel(f"Error: {error_message}")
        error_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_text.setStyleSheet("color: #ff6b6b; font-size: 14px;")
        error_text.setWordWrap(True)
        
        retry_button = QPushButton("Retry")
        retry_button.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
                max-width: 100px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
        """)
        retry_button.clicked.connect(self.load_data)
        
        error_layout.addWidget(error_text)
        error_layout.addSpacing(10)
        error_layout.addWidget(retry_button, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.table.setCellWidget(error_row, 0, error_widget)
        
        # Log the error
        print(f"Error loading {self.resource_type}: {error_message}")
        
    def populate_table(self, resources):
        """Populate the table with resources."""
        # Set row count
        self.table.setRowCount(len(resources))
        
        # Fill the table
        for row, resource in enumerate(resources):
            self.populate_resource_row(row, resource)
        
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with resource data.
        This should be overridden by subclasses to handle resource-specific columns.
        """
        pass  # Implemented by subclasses
        
    def _create_action_button(self, row, resource_name, resource_namespace):
        """Create an action button with edit and delete options only."""
        return super()._create_action_button(row, [
            {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True}
        ])
        
    def _handle_action(self, action, row):
        """Handle action button clicks."""
        if row >= len(self.resources):
            return
            
        resource = self.resources[row]
        resource_name = resource.get("name", "")
        resource_namespace = resource.get("namespace", "")
        
        if action == "Edit":
            self.edit_resource(resource)
        elif action == "Delete":
            self.delete_resource(resource_name, resource_namespace)
            
    def _handle_checkbox_change(self, state, item_name):
        """Handle checkbox state changes with namespace awareness."""
        # Find the namespace for this item
        namespace = None
        for resource in self.resources:
            if resource["name"] == item_name:
                namespace = resource.get("namespace", "")
                break
                
        # Store the (name, namespace) tuple for deletion
        item_key = (item_name, namespace)
        
        if state == Qt.CheckState.Checked.value:
            self.selected_items.add(item_key)
        else:
            self.selected_items.discard(item_key)
            
            # If any checkbox is unchecked, uncheck the select-all checkbox
            if self.select_all_checkbox is not None and self.select_all_checkbox.isChecked():
                # Block signals to prevent infinite recursion
                self.select_all_checkbox.blockSignals(True)
                self.select_all_checkbox.setChecked(False)
                self.select_all_checkbox.blockSignals(False)
                
    def _handle_select_all(self, state):
        """Handle select-all checkbox state changes."""
        super()._handle_select_all(state)
        
        # Update selected_items set based on state
        self.selected_items.clear()
        
        if state == Qt.CheckState.Checked.value:
            # Add all items to selected set
            for resource in self.resources:
                self.selected_items.add((resource["name"], resource.get("namespace", "")))
                
    def delete_selected_resources(self):
        """Delete all selected resources."""

        # Clean up any existing delete thread first
        if hasattr(self, 'delete_thread') and self.delete_thread and self.delete_thread.isRunning():
            self.delete_thread.wait(300)  # Wait for it to finish with timeout

        if not self.selected_items:
            QMessageBox.information(
                self, 
                "No Selection", 
                "No resources selected for deletion."
            )
            return
            
        # Confirm deletion
        count = len(self.selected_items)
        result = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {count} selected {self.resource_type}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        # Start batch deletion
        resources_list = list(self.selected_items)
        
        # Create and show progress dialog
        from PyQt6.QtWidgets import QProgressDialog
        progress = QProgressDialog(f"Deleting {count} {self.resource_type}...", "Cancel", 0, count, self)
        progress.setWindowTitle("Deleting Resources")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setValue(0)
        
        # Start batch delete thread
        self.batch_delete_thread = BatchResourceDeleterThread(self.resource_type, resources_list)
        self.batch_delete_thread.batch_delete_progress.connect(progress.setValue)
        self.batch_delete_thread.batch_delete_completed.connect(
            lambda success, errors: self.on_batch_delete_completed(success, errors, progress)
        )
        self.batch_delete_thread.start()
        
    def on_batch_delete_completed(self, success_list, error_list, progress_dialog):
        """Handle batch deletion completion."""
        # Close progress dialog
        progress_dialog.close()
        
        # Show results
        success_count = len(success_list)
        error_count = len(error_list)
        
        result_message = f"Deleted {success_count} of {success_count + error_count} {self.resource_type}."
        
        if error_count > 0:
            result_message += f"\n\nFailed to delete {error_count} resources:"
            for name, namespace, error in error_list[:5]:  # Show first 5 errors
                ns_text = f" in namespace {namespace}" if namespace else ""
                result_message += f"\n- {name}{ns_text}: {error}"
                
            if error_count > 5:
                result_message += f"\n... and {error_count - 5} more."
                
        QMessageBox.information(self, "Deletion Results", result_message)
        
        # Reload data
        self.load_data()
        
    def delete_resource(self, resource_name, resource_namespace):
        """Delete a single resource."""
        # Clean up any existing delete thread first
        if hasattr(self, 'delete_thread') and self.delete_thread and self.delete_thread.isRunning():
            self.delete_thread.wait(300)  # Wait for it to finish with timeout
        # Confirm deletion
        ns_text = f" in namespace {resource_namespace}" if resource_namespace else ""
        result = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {self.resource_type}/{resource_name}{ns_text}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        # Start deletion thread
        self.delete_thread = ResourceDeleterThread(self.resource_type, resource_name, resource_namespace)
        self.delete_thread.delete_completed.connect(self.on_delete_completed)
        self.delete_thread.start()
        
    def on_delete_completed(self, success, message, resource_name, resource_namespace):
        """Handle deletion completion."""
        if success:
            # Show success message
            QMessageBox.information(self, "Deletion Successful", message)
            
            # Remove from selected items if present
            self.selected_items.discard((resource_name, resource_namespace))
            
            # Remove from resources list
            self.resources = [r for r in self.resources if not (
                r["name"] == resource_name and r.get("namespace", "") == resource_namespace
            )]
            
            # Reload data
            self.load_data()
        else:
            # Show error message
            QMessageBox.critical(self, "Deletion Failed", message)
            
    def edit_resource(self, resource):
        """Edit a resource using the app's terminal with improved editing workflow."""
    
        resource_name = resource["name"]
        resource_namespace = resource.get("namespace", "")
        raw_data = resource.get("raw_data", {})
        
        if not raw_data:
            QMessageBox.critical(self, "Error", "No raw data available for editing.")
            return
        
        # Convert to YAML
        yaml_content = yaml.dump(raw_data, default_flow_style=False)
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w") as temp:
            temp.write(yaml_content)
            temp_path = temp.name
        
        # Find terminal in the application
        terminal_panel = None
        parent = self
        while parent and not terminal_panel:
            if hasattr(parent, 'terminal_panel'):
                terminal_panel = parent.terminal_panel
                break
            if hasattr(parent, 'parent_window') and parent.parent_window:
                if hasattr(parent.parent_window, 'terminal_panel'):
                    terminal_panel = parent.parent_window.terminal_panel
                    break
                if hasattr(parent.parent_window, 'cluster_view') and hasattr(parent.parent_window.cluster_view, 'terminal_panel'):
                    terminal_panel = parent.parent_window.cluster_view.terminal_panel
                    break
            parent = parent.parent()
        
        if not terminal_panel:
            QMessageBox.warning(self, "Terminal Not Found", "Terminal not found. Using external editor.")
            self._edit_with_external_editor(resource_name, resource_namespace, temp_path)
            return
        
        # Show terminal
        if not terminal_panel.is_visible:
            terminal_panel.show_terminal()
        
        # Add a new terminal tab specifically for editing
        tab_index = terminal_panel.add_terminal_tab()
        terminal_data = terminal_panel.terminal_tabs[tab_index]
        terminal_widget = terminal_data.get('terminal_widget')
        
        if not terminal_widget:
            QMessageBox.warning(self, "Terminal Not Available", "Terminal widget not found.")
            self._edit_with_external_editor(resource_name, resource_namespace, temp_path)
            return
        
        # Set the title for the terminal tab
        for child in terminal_data.get('tab_container', QWidget()).findChildren(QLabel):
            child.setText(f"Edit: {resource_name}")
            break
        
        # Enable edit mode in the terminal header
        if hasattr(terminal_panel, 'unified_header'):
            terminal_panel.unified_header.enter_edit_mode(temp_path)
        
        # Display header information
        ns_text = f" -n {resource_namespace}" if resource_namespace else ""
        terminal_widget.append_output(f"\n# Editing {self.resource_type}/{resource_name}{ns_text}\n", "#4CAF50")
        
        # Read and display file content
        try:
            with open(temp_path, 'r') as f:
                file_content = f.read()
            terminal_widget.append_output(file_content + "\n")
        except Exception as e:
            terminal_widget.append_output(f"Error reading file: {str(e)}\n", "#FF6B68")
        
        # Show commands
        terminal_widget.append_output("\n# COMMANDS:\n", "#FFA500")
        terminal_widget.append_output(f"# The content above is editable. Make your changes directly here.\n", "#FFA500")
        terminal_widget.append_output(f"# When finished, click the 💾 button in the terminal header to save and apply changes.\n", "#FFA500")
        
        # Set cursor at the beginning of the content for editing
        cursor = terminal_widget.textCursor()
        start_pos = terminal_widget.toPlainText().find("\n# Editing ")
        if start_pos >= 0:
            start_pos = terminal_widget.toPlainText().find("\n", start_pos + 10) + 1
            cursor.setPosition(start_pos)
            terminal_widget.setTextCursor(cursor)
            
        # Focus the terminal widget
        terminal_widget.setFocus()    
    
    def on_edit_completed(self, success, message):
        """Handle edit completion."""
        if success:
            # Show success message
            QMessageBox.information(self, "Update Successful", message)
            
            # Reload data
            self.load_data()
        else:
            # Show error message
            QMessageBox.critical(self, "Update Failed", message)