# EventsPage.py - Brief Documentation

**Path**: `orchetrix/Pages/EventsPage.py`
**Lines**: ~300
**Extends**: BaseResourcePage

## Purpose
Display cluster-wide Kubernetes events

## Columns
- Type (Normal/Warning)
- Reason
- Message
- Object (pod/deployment/etc)
- Source
- Count
- First Seen
- Last Seen

## Key Features
- Filter by type (Normal/Warning)
- Search events
- Auto-refresh
- Color-coded by type

## Resource Type
`events` (namespaced)
