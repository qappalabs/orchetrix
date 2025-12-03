# NodesPage.py - Brief Documentation

**Path**: `orchetrix/Pages/NodesPage.py`
**Lines**: ~350
**Extends**: BaseResourcePage

## Purpose
Display and manage Kubernetes Nodes

## Columns
- Name
- Status (Ready/NotReady)
- Roles (control-plane, worker)
- Version
- CPU Usage
- Memory Usage
- Age

## Key Features
- Node metrics display
- Node conditions
- Taints and labels
- Drain/cordon actions

## Resource Type
`nodes` (cluster-scoped)
