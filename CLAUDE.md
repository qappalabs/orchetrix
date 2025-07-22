# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Orchestrix is a PyQt6-based Kubernetes management desktop application that provides a graphical interface for managing Kubernetes clusters, resources, and Helm charts. The application offers comprehensive cluster management capabilities including resource monitoring, terminal access, and YAML editing.

## Development Environment

- **Language**: Python 3.13.5
- **GUI Framework**: PyQt6
- **Package Manager**: pip
- **Dependencies**: Managed via requirements.txt

## Common Development Commands

### Running the Application
```bash
python main.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Building Executable (PyInstaller)
```bash
pyinstaller Orchetrix.spec
```

## Architecture Overview

### Core Components

1. **Main Application** (`main.py`):
   - Entry point with comprehensive error handling and logging
   - Initializes PyQt6 application with custom styling
   - Manages splash screen and main window lifecycle
   - Handles resource path resolution for PyInstaller compatibility

2. **UI Structure**:
   - **Pages/**: Contains all application pages organized by functionality
     - `HomePage.py`: Landing page with cluster selection
     - `ClusterPage.py`: Main cluster overview
     - `WorkLoad/`: Pod, Deployment, StatefulSet management pages
     - `Config/`: ConfigMaps, Secrets, Resource management
     - `NetWork/`: Services, Ingress, Network policy pages
     - `Storage/`: Persistent volumes and storage classes
     - `AccessControl/`: RBAC management
     - `Helm/`: Chart and release management
   - **UI/**: Core UI components
     - `ClusterView.py`: Main cluster view container
     - `Sidebar.py`: Navigation sidebar
     - `TitleBar.py`: Custom window title bar
     - `TerminalPanel.py`: Integrated terminal functionality
     - `DetailPageComponent.py`: Resource detail views

3. **Utilities** (`utils/`):
   - `kubernetes_client.py`: Kubernetes API client wrapper
   - `cluster_connector.py`: Cluster connection management
   - `helm_client.py`: Helm operations (currently commented out)
   - `thread_manager.py`: Thread pool management
   - `enhanced_worker.py`: Base worker class for async operations

4. **Base Components** (`base_components/`):
   - `base_resource_page.py`: Base class for Kubernetes resource pages
   - `base_components.py`: Common UI component patterns

### Key Architectural Patterns

1. **State Management**: Uses `cluster_state_manager.py` for centralized cluster state
2. **Threading**: Extensive use of QThread and worker patterns for non-blocking operations
3. **Signal/Slot Communication**: PyQt6 signals for component communication
4. **Resource Management**: Comprehensive cleanup patterns to prevent memory leaks
5. **Error Handling**: Global exception handler and detailed logging

### Application Flow

1. Application starts with splash screen
2. Main window initializes with stacked widget navigation
3. Home page allows cluster selection and connection
4. Cluster view provides full resource management interface
5. Detail panels show resource-specific information and YAML editing

### Configuration and Settings

- Application settings stored in `settings/app_settings.json`
- Supports timezone configuration
- YAML editor preferences (font, line numbers, tab size)
- Cluster connection persistence

### Resource Handling

- All icons and images stored in `icons/` and `images/` directories
- PyInstaller spec file (`Orchetrix.spec`) handles resource bundling
- Runtime resource path resolution for development vs. packaged environments

### Development Notes

- Uses frameless window design with custom title bar
- Extensive logging to `logs/` directory
- Memory optimization with periodic cleanup
- Cross-platform compatibility considerations
- No formal testing framework detected - testing appears to be manual