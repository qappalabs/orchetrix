# Orchestrix MVC Architecture Conversion Plan

## Executive Summary

This document outlines a comprehensive plan to convert the Orchestrix PyQt6 Kubernetes management application from its current monolithic GUI-centric architecture to a clean Model-View-Controller (MVC) architecture. The conversion will improve maintainability, testability, and extensibility while preserving all existing functionality.

## Current Architecture Issues

### Critical Problems
1. **Tight Coupling**: UI components directly access Kubernetes API
2. **Mixed Responsibilities**: BaseResourcePage contains UI, data access, and business logic
3. **Monolithic main.py**: 1,000+ lines handling everything from init to business logic
4. **No Clear Boundaries**: Components knowing too much about each other
5. **Difficult Testing**: Business logic embedded in UI components

## Target MVC Architecture

```
orchestrix/
├── models/                     # MODEL LAYER
│   ├── __init__.py
│   ├── domain/                 # Domain entities
│   │   ├── cluster.py
│   │   ├── deployment.py
│   │   ├── pod.py
│   │   ├── service.py
│   │   └── ...
│   ├── repositories/           # Data access abstractions
│   │   ├── base_repository.py
│   │   ├── kubernetes_repository.py
│   │   ├── cluster_repository.py
│   │   └── resource_repository.py
│   ├── services/               # Business logic services
│   │   ├── cluster_service.py
│   │   ├── resource_service.py
│   │   ├── diagram_service.py
│   │   └── validation_service.py
│   └── state/                  # Application state management
│       ├── app_state.py
│       ├── cluster_state.py
│       └── ui_state.py
├── views/                      # VIEW LAYER
│   ├── __init__.py
│   ├── main_window.py          # Main application window
│   ├── pages/                  # Page views (UI only)
│   │   ├── base_page_view.py
│   │   ├── cluster_page_view.py
│   │   ├── apps_page_view.py
│   │   └── ...
│   ├── components/             # Reusable UI components
│   │   ├── sidebar_view.py
│   │   ├── title_bar_view.py
│   │   ├── terminal_view.py
│   │   └── resource_table_view.py
│   ├── dialogs/                # Modal dialogs
│   │   ├── preferences_dialog.py
│   │   ├── cluster_dialog.py
│   │   └── ...
│   └── interfaces/             # View interfaces for testing
│       ├── i_main_view.py
│       ├── i_page_view.py
│       └── ...
├── controllers/                # CONTROLLER LAYER
│   ├── __init__.py
│   ├── application_controller.py
│   ├── cluster_controller.py
│   ├── resource_controller.py
│   ├── navigation_controller.py
│   ├── diagram_controller.py
│   └── terminal_controller.py
├── infrastructure/             # Infrastructure concerns
│   ├── __init__.py
│   ├── kubernetes_client.py    # Kubernetes API wrapper (refactored)
│   ├── threading/              # Thread management
│   ├── logging/                # Logging infrastructure
│   └── configuration/          # App configuration
├── utils/                      # Pure utility functions
└── main.py                     # Application entry point (minimal)
```

## Phase-by-Phase Conversion Plan

### Phase 1: Foundation Setup (Week 1-2)

#### 1.1 Create Core MVC Structure
```bash
# Create new directory structure
mkdir -p models/{domain,repositories,services,state}
mkdir -p views/{pages,components,dialogs,interfaces}
mkdir -p controllers
mkdir -p infrastructure/{kubernetes,threading,logging,configuration}
```

#### 1.2 Define Core Interfaces
```python
# views/interfaces/i_main_view.py
from abc import ABC, abstractmethod
from typing import Optional

class IMainView(ABC):
    @abstractmethod
    def show_page(self, page_name: str) -> None:
        pass
    
    @abstractmethod
    def show_error(self, message: str) -> None:
        pass
    
    @abstractmethod
    def show_loading(self, message: str) -> None:
        pass

# views/interfaces/i_page_view.py
class IPageView(ABC):
    @abstractmethod
    def update_data(self, data: Any) -> None:
        pass
    
    @abstractmethod
    def show_loading_state(self) -> None:
        pass
    
    @abstractmethod
    def show_error_state(self, error: str) -> None:
        pass
```

#### 1.3 Create Domain Models
```python
# models/domain/cluster.py
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class Cluster:
    name: str
    context: str
    server: str
    namespace: str
    version: Optional[str] = None
    status: str = "unknown"
    last_connected: Optional[datetime] = None
    
    def is_connected(self) -> bool:
        return self.status == "connected"

# models/domain/deployment.py
@dataclass
class Deployment:
    name: str
    namespace: str
    replicas: int
    ready_replicas: int
    labels: Dict[str, str]
    containers: List['Container']
    created: datetime
    
    @property
    def is_ready(self) -> bool:
        return self.ready_replicas == self.replicas
```

### Phase 2: Model Layer Implementation (Week 3-4)

#### 2.1 Create Repository Pattern
```python
# models/repositories/base_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar, Generic

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    @abstractmethod
    async def get_all(self, namespace: Optional[str] = None) -> List[T]:
        pass
    
    @abstractmethod
    async def get_by_name(self, name: str, namespace: str) -> Optional[T]:
        pass
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        pass
    
    @abstractmethod
    async def delete(self, name: str, namespace: str) -> bool:
        pass

# models/repositories/kubernetes_repository.py
class KubernetesRepository(BaseRepository[T]):
    def __init__(self, kubernetes_client: KubernetesClient, resource_type: str):
        self.client = kubernetes_client
        self.resource_type = resource_type
    
    async def get_all(self, namespace: Optional[str] = None) -> List[T]:
        # Implementation for fetching all resources
        pass
```

#### 2.2 Create Business Services
```python
# models/services/cluster_service.py
class ClusterService:
    def __init__(self, cluster_repo: ClusterRepository, state_manager: AppState):
        self.cluster_repo = cluster_repo
        self.state = state_manager
    
    async def connect_to_cluster(self, cluster_name: str) -> bool:
        try:
            cluster = await self.cluster_repo.get_by_name(cluster_name)
            if cluster:
                # Connection logic
                self.state.set_current_cluster(cluster)
                return True
        except Exception as e:
            self.state.set_error(f"Failed to connect: {e}")
            return False
    
    async def get_cluster_metrics(self, cluster_name: str) -> ClusterMetrics:
        # Business logic for calculating metrics
        pass
```

#### 2.3 Implement State Management
```python
# models/state/app_state.py
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, Dict, Any

class AppState(QObject):
    # Signals for state changes
    cluster_changed = pyqtSignal(object)  # Cluster
    error_occurred = pyqtSignal(str)
    loading_changed = pyqtSignal(bool)
    page_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._current_cluster: Optional[Cluster] = None
        self._current_page: str = "home"
        self._is_loading: bool = False
        self._error_message: Optional[str] = None
    
    @property
    def current_cluster(self) -> Optional[Cluster]:
        return self._current_cluster
    
    def set_current_cluster(self, cluster: Optional[Cluster]) -> None:
        if self._current_cluster != cluster:
            self._current_cluster = cluster
            self.cluster_changed.emit(cluster)
```

### Phase 3: Controller Layer Implementation (Week 5-6)

#### 3.1 Application Controller
```python
# controllers/application_controller.py
class ApplicationController:
    def __init__(self, main_view: IMainView, app_state: AppState):
        self.main_view = main_view
        self.state = app_state
        self.cluster_controller = ClusterController(app_state)
        self.navigation_controller = NavigationController(main_view, app_state)
        
        # Connect state changes to view updates
        self.state.error_occurred.connect(self.main_view.show_error)
        self.state.loading_changed.connect(self._handle_loading_change)
    
    async def initialize(self) -> None:
        """Initialize the application"""
        try:
            await self.cluster_controller.load_available_clusters()
            self.navigation_controller.navigate_to_home()
        except Exception as e:
            self.state.set_error(f"Failed to initialize: {e}")
    
    def _handle_loading_change(self, is_loading: bool) -> None:
        if is_loading:
            self.main_view.show_loading("Loading...")
        else:
            self.main_view.hide_loading()
```

#### 3.2 Resource Controller
```python
# controllers/resource_controller.py
class ResourceController:
    def __init__(self, resource_service: ResourceService, app_state: AppState):
        self.service = resource_service
        self.state = app_state
    
    async def load_resources(self, resource_type: str, namespace: Optional[str] = None) -> None:
        """Load resources of specified type"""
        self.state.set_loading(True)
        try:
            resources = await self.service.get_resources(resource_type, namespace)
            self.state.set_resources(resource_type, resources)
        except Exception as e:
            self.state.set_error(f"Failed to load {resource_type}: {e}")
        finally:
            self.state.set_loading(False)
    
    async def delete_resource(self, resource_type: str, name: str, namespace: str) -> bool:
        """Delete a specific resource"""
        try:
            success = await self.service.delete_resource(resource_type, name, namespace)
            if success:
                await self.load_resources(resource_type, namespace)  # Refresh
            return success
        except Exception as e:
            self.state.set_error(f"Failed to delete {name}: {e}")
            return False
```

### Phase 4: View Layer Refactoring (Week 7-8)

#### 4.1 Refactor Main Window
```python
# views/main_window.py
class MainWindow(QMainWindow, IMainView):
    def __init__(self, controller: ApplicationController):
        super().__init__()
        self.controller = controller
        self.setup_ui()
        
        # No business logic here - only UI setup and event forwarding
    
    def show_page(self, page_name: str) -> None:
        """Pure UI method - no business logic"""
        if page_name in self.pages:
            self.stacked_widget.setCurrentWidget(self.pages[page_name])
    
    def show_error(self, message: str) -> None:
        """Display error message"""
        QMessageBox.critical(self, "Error", message)
    
    def on_cluster_selected(self, cluster_name: str) -> None:
        """Forward events to controller"""
        asyncio.create_task(self.controller.cluster_controller.connect_to_cluster(cluster_name))
```

#### 4.2 Refactor Page Views
```python
# views/pages/base_page_view.py
class BasePageView(QWidget, IPageView):
    # Signals for user interactions (no business logic)
    refresh_requested = pyqtSignal()
    resource_selected = pyqtSignal(str, str)  # name, namespace
    resource_delete_requested = pyqtSignal(str, str)
    
    def __init__(self, controller: ResourceController):
        super().__init__()
        self.controller = controller
        self.setup_ui()
        
        # Connect UI events to controller
        self.refresh_requested.connect(
            lambda: asyncio.create_task(self.controller.load_resources(self.resource_type))
        )
    
    def update_data(self, resources: List[Any]) -> None:
        """Update view with new data - pure UI logic"""
        self.table.clear()
        for resource in resources:
            self.add_resource_to_table(resource)
    
    def show_loading_state(self) -> None:
        """Show loading UI"""
        self.loading_indicator.show()
        self.table.hide()
    
    def show_error_state(self, error: str) -> None:
        """Show error UI"""
        self.error_label.setText(error)
        self.error_widget.show()
```

### Phase 5: Infrastructure Layer (Week 9-10)

#### 5.1 Refactor Kubernetes Client
```python
# infrastructure/kubernetes_client.py
class KubernetesClient:
    """Pure data access - no business logic"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self._client_cache = {}
    
    async def get_deployments(self, namespace: Optional[str] = None) -> List[V1Deployment]:
        """Raw API call - no transformation"""
        try:
            if namespace:
                return self.apps_v1.list_namespaced_deployment(namespace).items
            else:
                return self.apps_v1.list_deployment_for_all_namespaces().items
        except ApiException as e:
            raise KubernetesApiError(f"Failed to get deployments: {e}")
    
    async def delete_deployment(self, name: str, namespace: str) -> None:
        """Raw API call"""
        await self.apps_v1.delete_namespaced_deployment(name, namespace)
```

#### 5.2 Threading Infrastructure
```python
# infrastructure/threading/async_qt.py
import asyncio
from PyQt6.QtCore import QThread, QObject, pyqtSignal

class AsyncWorker(QObject):
    """Worker for running async operations in Qt"""
    finished = pyqtSignal(object)
    error = pyqtSignal(Exception)
    
    def __init__(self, coro):
        super().__init__()
        self.coro = coro
    
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.coro)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(e)
        finally:
            loop.close()
```

### Phase 6: Migration Strategy (Week 11-12)

#### 6.1 Gradual Migration Approach
1. **Create MVC structure alongside existing code**
2. **Migrate one page at a time** (start with simplest)
3. **Keep existing functionality working** during migration
4. **Add feature flags** to switch between old/new implementations
5. **Comprehensive testing** at each step

#### 6.2 Migration Order
1. **Apps Page** (newest, least complex)
2. **Cluster Page** (well-defined scope)
3. **Simple resource pages** (Namespaces, Events)
4. **Complex resource pages** (Pods, Deployments)
5. **Main window and navigation**
6. **Remove old code**

#### 6.3 Testing Strategy
```python
# tests/controllers/test_resource_controller.py
class MockResourceView(IPageView):
    def __init__(self):
        self.data = None
        self.loading = False
        self.error = None
    
    def update_data(self, data):
        self.data = data

class TestResourceController:
    async def test_load_resources_success(self):
        # Test controller with mocked dependencies
        mock_service = Mock()
        mock_state = Mock()
        controller = ResourceController(mock_service, mock_state)
        
        await controller.load_resources("pods", "default")
        
        mock_service.get_resources.assert_called_once_with("pods", "default")
```

## Implementation Guidelines

### Code Quality Standards
1. **Single Responsibility**: Each class has one clear purpose
2. **Dependency Injection**: No direct instantiation of dependencies
3. **Interface Segregation**: Small, focused interfaces
4. **Async/Await**: Consistent async programming model
5. **Type Hints**: Full type annotation
6. **Error Handling**: Proper exception handling at each layer

### Testing Requirements
1. **Unit Tests**: 80%+ coverage for controllers and services
2. **Integration Tests**: End-to-end workflow testing
3. **Mock Strategy**: Mock external dependencies (K8s API)
4. **UI Testing**: Automated UI testing where possible

### Performance Considerations
1. **Lazy Loading**: Load data only when needed
2. **Caching**: Smart caching at repository level
3. **Background Operations**: All I/O operations async
4. **Memory Management**: Proper cleanup of resources

## Migration Timeline

| Phase | Duration | Deliverables |
|-------|----------|-------------|
| 1. Foundation | 2 weeks | MVC structure, interfaces, domain models |
| 2. Model Layer | 2 weeks | Repositories, services, state management |
| 3. Controllers | 2 weeks | All controller implementations |
| 4. View Refactoring | 2 weeks | Pure view components |
| 5. Infrastructure | 2 weeks | Kubernetes client, threading |
| 6. Migration & Testing | 2 weeks | Complete migration, testing |

**Total Timeline: 3 months**

## Risk Mitigation

### Technical Risks
1. **PyQt Signal/Slot with Async**: Use QTimer and event loop integration
2. **Performance Degradation**: Careful profiling and optimization
3. **Threading Complexity**: Simplified threading model with async/await

### Migration Risks
1. **Feature Regression**: Comprehensive testing suite
2. **User Disruption**: Gradual rollout with fallback options
3. **Team Learning Curve**: Documentation and code reviews

## Success Metrics

1. **Code Quality**: Reduced cyclomatic complexity, improved maintainability index
2. **Test Coverage**: 80%+ unit test coverage
3. **Performance**: No degradation in UI responsiveness
4. **Maintainability**: Faster feature development after migration

This MVC conversion will transform Orchestrix into a more maintainable, testable, and extensible application while preserving all existing functionality.