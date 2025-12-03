# detailpage_overviewsection.py - Brief Documentation

**Path**: `orchetrix/UI/detail_sections/detailpage_overviewsection.py`
**Lines**: ~400

## Purpose
Overview tab showing key resource information

## Displays
- Resource status (with color)
- Key metadata (name, namespace, age)
- Important labels
- Resource-specific widgets (containers for pods, replicas for deployments)
- Quick action buttons

## Layout
- Top: Status and key info
- Middle: Labels and annotations
- Bottom: Resource-specific details
- Actions: Delete, Edit, Refresh

## Pattern
Extends BaseDetailSection
