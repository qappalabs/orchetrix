# ServicesPage.py - Brief Documentation

**Path**: `orchetrix/Pages/NetWork/ServicesPage.py`
**Lines**: ~250
**Extends**: BaseResourcePage

## Purpose
Display and manage Kubernetes Services

## Columns
- Name
- Namespace
- Type (ClusterIP, NodePort, LoadBalancer)
- Cluster IP
- External IP
- Ports
- Age

## Key Features
- Port forwarding integration
- Service endpoint display
- Type-specific actions

## Resource Type
`services` (namespaced)
