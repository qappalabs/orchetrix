# Remaining Base_Components Files

## virtualized_table_model.py
**Purpose**: Qt data model for VirtualScrollTable
**Key Class**: `VirtualizedResourceModel(QAbstractTableModel)`
- Provides data to VirtualScrollTable
- Implements Qt's model-view pattern
- Handles data() requests for visible cells only
- Supports sorting via lessThan() comparisons

## paginated_resource_page.py
**Purpose**: Base class for paginated resource pages (alternative to virtual scrolling)
**Key Features**:
- Load-more pagination (e.g., "Load 100 more")
- Page number navigation (1, 2, 3, ...)
- Used for resources with simple pagination needs
- Less complex than virtual scrolling

## resource_processing_worker.py
**Purpose**: Background worker for processing resource data
**Key Class**: `ResourceProcessingWorker(QThread)`
- Processes raw Kubernetes API responses
- Formats data for display (age, memory, status, etc.)
- Runs in background to prevent UI freezing
- Emits processed data via signals

## __init__.py
**Purpose**: Package initialization
**Exports**:
- BaseResourcePage
- VirtualScrollTable
- Resource deleters
- All base components for easy import

---

**Note**: These files are less critical than base_resource_page.py, base_components.py, virtual_scroll_table.py, and resource_deleters.py. The main application flow uses the documented files primarily.
