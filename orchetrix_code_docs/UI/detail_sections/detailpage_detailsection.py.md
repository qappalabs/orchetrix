# detailpage_detailsection.py - Brief Documentation

**Path**: `orchetrix/UI/detail_sections/detailpage_detailsection.py`
**Lines**: ~350

## Purpose
Details tab showing field-by-field breakdown

## Features
- Expandable sections (Metadata, Spec, Status)
- Field labels and values
- Copy to clipboard buttons
- Nested field display

## Layout
```
Metadata ▼
  Name: nginx-abc123
  Namespace: default
  UID: a1b2c3...
Spec ▼
  Containers: [...]
  Volumes: [...]
Status ▼
  Phase: Running
  Conditions: [...]
```

## Pattern
Extends BaseDetailSection
