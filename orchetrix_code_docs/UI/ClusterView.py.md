# ClusterView.py Documentation

## File Information
- **Path**: `orchetrix/UI/ClusterView.py`
- **Purpose**: **MAIN APPLICATION VIEW** - Container for all Kubernetes resource pages with sidebar navigation

## Overview
ClusterView is the primary container shown after selecting a cluster from HomeView. It contains:
- **Sidebar**: Navigation menu with dropdowns (Workloads, Config, Network, etc.)
- **Page Stack**: All resource pages (Pods, Deployments, Services, etc.)
- **Detail Manager**: Shows resource detail panels
- **Terminal Panel**: Integrated terminal for logs and SSH
- **Loading Overlay**: Animated loading indicator

---

## PAGE_CONFIG Dictionary

**Most Important Data Structure** - Maps page names to page classes:

```python
PAGE_CONFIG = {
    # Core pages (4)
    'Cluster': ClusterPage,
    'Nodes': NodesPage,
    'Events': EventsPage,
    'Namespaces': NamespacesPage,

    # Workload pages (9)
    'Overview': OverviewPage,
    'Pods': PodsPage,
    'Deployments': DeploymentsPage,
    'Stateful Sets': StatefulSetsPage,
    'Daemon Sets': DaemonSetsPage,
    'Replica Sets': ReplicaSetsPage,
    'Replication Controllers': ReplicaControllersPage,
    'Jobs': JobsPage,
    'Cron Jobs': CronJobsPage,

    # Config pages (11)
    'Config Maps': ConfigMapsPage,
    'Secrets': SecretsPage,
    'Resource Quotas': ResourceQuotasPage,
    'Limit Ranges': LimitRangesPage,
    'Horizontal Pod Autoscalers': HorizontalPodAutoscalersPage,
    'Pod Disruption Budgets': PodDisruptionBudgetsPage,
    'Priority Classes': PriorityClassesPage,
    'Runtime Classes': RuntimeClassesPage,
    'Leases': LeasesPage,
    'Mutating Webhook Configs': MutatingWebhookConfigsPage,
    'Validating Webhook Configs': ValidatingWebhookConfigsPage,

    # Network pages (6)
    'Services': ServicesPage,
    'Endpoints': EndpointsPage,
    'Ingresses': IngressesPage,
    'Ingress Classes': IngressClassesPage,
    'Network Policies': NetworkPoliciesPage,
    'Port Forwarding': PortForwardingPage,

    # Storage pages (3)
    'Persistent Volume Claims': PersistentVolumeClaimsPage,
    'Persistent Volumes': PersistentVolumesPage,
    'Storage Classes': StorageClassesPage,
    
    # Helm pages (2)
    'Charts': ChartsPage,
    'Releases': ReleasesPage,

    # Access Control pages (5)
    'Service Accounts': ServiceAccountsPage,
    'Cluster Roles': ClusterRolesPage,
    'Roles': RolesPage,
    'Cluster Role Bindings': ClusterRoleBindingsPage,
    'Role Bindings': RoleBindingsPage,

    # Custom Resource pages (1)
    'Definitions': DefinitionsPage,
    
    # Additional pages (2)
    'AppsChart': AppsPage,
    'Compare': ComparePage,
}

# Total: 45+ resource pages
```

---

## DROPDOWN_MENUS Dictionary

**Sidebar Organization** - Groups pages into dropdown menus:

```python
DROPDOWN_MENUS = {
    "Workloads": [
        "Overview", "Pods", "Deployments", "Daemon Sets",
        "Stateful Sets", "Replica Sets", "Replication Controllers",
        "Jobs", "Cron Jobs"
    ],
    "Config": [
        "Config Maps", "Secrets", "Resource Quotas", "Limit Ranges",
        "Horizontal Pod Autoscalers", "Pod Disruption Budgets",
        "Priority Classes", "Runtime Classes", "Leases",
        "Mutating Webhook Configs", "Validating Webhook Configs"
    ],
    "Network": [
        "Services", "Endpoints", "Ingresses", "Ingress Classes",
        "Network Policies", "Port Forwarding"
    ],
    "Storage": [
        "Persistent Volume Claims", "Persistent Volumes", "Storage Classes"
    ],
    "Access Control": [
        "Service Accounts", "Cluster Roles", "Roles",
        "Cluster Role Bindings", "Role Bindings"
    ],
    "Custom Resources": ["Definitions"]
}
```

**Sidebar Visual**:
```
┌─────────────────────┐
│ 🏠 Cluster          │
│ 🗂️  Nodes           │
│ 📋 Events           │
│ 📦 Namespaces       │
│ ───────────────────  │
│ ⚙️  Workloads ▾     │ ← Dropdown
│   ├ Overview        │
│   ├ Pods            │
│   ├ Deployments     │
│   └ ...             │
│ 📝 Config ▾         │ ← Dropdown
│ 🌐 Network ▾        │ ← Dropdown
│ 💾 Storage ▾        │ ← Dropdown
│ 🔐 Access Control ▾ │ ← Dropdown
└─────────────────────┘
```

---

## CLUSTER_SCOPED_RESOURCES Set

**Resources WITHOUT Namespaces**:

```python
CLUSTER_SCOPED_RESOURCES = {
    'node',                # Nodes are cluster-wide
    'persistentvolume',    # PVs are cluster-wide (PVCs are namespaced)
    'clusterrole',         # ClusterRoles apply to whole cluster
    'clusterrolebinding',  # ClusterRoleBindings apply to whole cluster
    'chart'                # Helm charts are cluster-wide
}
```

**Why This Matters**:
- Namespaced resources: Filtered by namespace dropdown (Pods, Deployments, etc.)
- Cluster-scoped resources: Show all, no namespace filter (Nodes, ClusterRoles, etc.)

---

## Class: LoadingOverlay

**Purpose**: Semi-transparent overlay with animated spinner

```python
class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            #loadingOverlay {
                background-color: rgba(20, 20, 20, 0.8);  # Dark semi-transparent
            }
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Create spinning animation
        self._setup_animation()
```

**Usage**:
```python
# Show loading while fetching pods
overlay.show()
load_pods_in_background()
overlay.hide()  # Hide when done
```

---

## Class: ClusterView

### Constructor: `__init__()`

```python
def __init__(self, cluster_name, parent=None):
    super().__init__(parent)
    self.cluster_name = cluster_name
    self.pages = {}  # Cache of instantiated pages
    
    # Create main layout
    main_layout = QHBoxLayout(self)
    
    # Create sidebar
    self.sidebar = Sidebar(self)
    main_layout.addWidget(self.sidebar)
    
    # Create page stack
    self.page_stack = QStackedWidget()
    main_layout.addWidget(self.page_stack)
    
    # Create detail manager
    self.detail_manager = DetailManager(self)
    
    # Create terminal panel
    self.terminal_panel = TerminalPanel(self)
    
    # Initialize pages
    self._init_pages()
    
    # Connect signals
    self.sidebar.page_selected.connect(self.switch_page)
```

**Structure**:
```
ClusterView
├── Sidebar (left, 180px or 50px when collapsed)
├── Page Stack (center, fills remaining space)
│   ├── PodsPage
│   ├── DeploymentsPage
│   ├── ServicesPage
│   └── ... (45+ pages)
├── Detail Manager (overlay panel on right)
└── Terminal Panel (bottom panel, toggleable)
```

---

### Method: `_init_pages()`

```python
def _init_pages(self):
    """Initialize all resource pages lazily"""
    for page_name, page_class in PAGE_CONFIG.items():
        # Don't create page yet, just store class reference
        self.pages[page_name] = {
            'class': page_class,
            'instance': None  # Created on first access
        }
```

**Lazy Loading Benefits**:
- **Fast Startup**: Don't create all 45+ pages immediately
- **Memory Efficient**: Only create pages when user navigates to them
- **Better Performance**: Reduces initial load time

---

### Method: `switch_page()`

```python
def switch_page(self, page_name):
    """Switch to a resource page"""
    # Get or create page
    if self.pages[page_name]['instance'] is None:
        # First time accessing this page - create it
        page_class = self.pages[page_name]['class']
        page_instance = page_class(self)
        self.pages[page_name]['instance'] = page_instance
        self.page_stack.addWidget(page_instance)
    
    # Switch to page
    page = self.pages[page_name]['instance']
    self.page_stack.setCurrentWidget(page)
    
    # Trigger page load if needed
    if hasattr(page, 'load_data'):
        page.load_data()
```

**Page Switching Flow**:
```
User clicks "Pods" in sidebar →
switch_page("Pods") called →
Check if PodsPage instance exists →
  No: Create PodsPage, add to stack →
  Yes: Use existing instance →
Set PodsPage as current widget →
Trigger PodsPage.load_data()
```

---

### Method: `set_cluster()`

```python
def set_cluster(self, cluster_name):
    """Switch to a different cluster"""
    self.cluster_name = cluster_name
    
    # Update kubernetes client context
    connector = get_cluster_connector()
    connector.switch_cluster(cluster_name)
    
    # Reload current page
    current_page = self.page_stack.currentWidget()
    if hasattr(current_page, 'load_data'):
        current_page.load_data()
```

**Use Case**: User switches from cluster A to cluster B without going back to HomeView

---

## Integration Points

### Detail Manager Integration

```python
# In PodsPage, when user clicks a row:
parent = self.parent()
while parent and not hasattr(parent, 'detail_manager'):
    parent = parent.parent()

if parent and hasattr(parent, 'detail_manager'):
    parent.detail_manager.show_detail("pod", pod_name, namespace)
```

**Result**: Detail panel slides in from right showing pod details

---

### Terminal Panel Integration

```python
# In PodsPage, when user clicks "View Logs":
parent = self.parent()
while parent and not hasattr(parent, 'terminal_panel'):
    parent = parent.parent()

if parent and hasattr(parent, 'terminal_panel'):
    parent.terminal_panel.create_enhanced_logs_tab(pod_name, namespace)
    parent.toggle_terminal()  # Show terminal if hidden
```

**Result**: Terminal panel appears at bottom with streaming logs

---

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ ClusterView (Full Window)                                    │
├────────┬────────────────────────────────────────────────────┤
│Sidebar │ Page Stack (Stacked Widget)                        │
│        │ ┌────────────────────────────────────────────────┐ │
│ 🏠     │ │ Current Page (e.g., PodsPage)                  │ │
│ 🗂️     │ │ ┌────────────────────────────────────────────┐ │ │
│ 📋     │ │ │ Search: [      ] Namespace: [default ▾]   │ │ │
│ 📦     │ │ ├────────────────────────────────────────────┤ │ │
│ ───    │ │ │ Table with pods                            │ │ │
│ ⚙️  ▾  │ │ │ ┌──────┬─────────┬────────┬────────┬─────┐ │ │ │
│   Pods │ │ │ │ Name │ NS      │ Status │ Age    │ ... │ │ │ │
│   Dep  │ │ │ ├──────┼─────────┼────────┼────────┼─────┤ │ │ │
│        │ │ │ │ nginx│ default │Running │ 5d     │  ⋮  │ │ │ │
│180px   │ │ │ └──────┴─────────┴────────┴────────┴─────┘ │ │ │
│or 50px │ │ └────────────────────────────────────────────┘ │ │
│        │ └────────────────────────────────────────────────┘ │
├────────┴────────────────────────────────────────────────────┤
│ Terminal Panel (toggleable, hidden by default)               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Logs | SSH | Terminal                                   │  │
│ │ ─────────────────────────────────────────────────────── │  │
│ │ [pod-1] 2025-01-15 10:30:00 Starting application...     │  │
│ └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                                                
Detail Panel (slides in from right when row clicked):          
                                           ┌──────────────────┐
                                           │ Pod Details      │
                                           │ ──────────────── │
                                           │ Name: nginx      │
                                           │ Namespace: ...   │
                                           │                  │
                                           │ YAML ▾           │
                                           │ Events ▾         │
                                           │ Logs ▾           │
                                           └──────────────────┘
```

---

## Key Features

1. ✅ **45+ Resource Pages**: All Kubernetes resources
2. ✅ **Lazy Loading**: Pages created on first access
3. ✅ **Sidebar Navigation**: Organized dropdown menus
4. ✅ **Detail Manager**: Slide-in detail panels
5. ✅ **Terminal Integration**: Logs and SSH
6. ✅ **Loading Overlay**: Visual feedback
7. ✅ **Cluster Switching**: Change clusters without restart
8. ✅ **Namespace Filtering**: Cluster vs namespaced resources
9. ✅ **PyInstaller Compatible**: Direct class references

---

## Dependencies
- Sidebar (navigation)
- DetailManager (detail panels)
- TerminalPanel (logs/SSH)
- 45+ Page classes (all resources)
- ClusterConnector (cluster switching)
- AppStyles (theming)

---

## Used By
- main.py (MainWindow creates ClusterView when cluster selected)
- HomeView (switches to ClusterView on cluster click)
