# ComparePage.py - Brief Documentation

**Path**: `orchetrix/Pages/ComparePage.py`
**Lines**: ~300

## Purpose
Compare two Kubernetes resources side-by-side

## Features
- YAML diff view
- Syntax highlighting
- Highlight differences (additions/deletions)
- Compare across namespaces/clusters
- Copy to clipboard

## UI Layout
```
+------------------+------------------+
| Resource 1 YAML  | Resource 2 YAML  |
+------------------+------------------+
```

## Use Cases
- Compare pod configurations
- Compare ConfigMap versions
- Compare deployments across environments
