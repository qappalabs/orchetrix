# deployment_analyzer.py - Brief Documentation

**Path**: `orchetrix/Pages/AppsChart/deployment_analyzer.py`
**Lines**: ~150

## Purpose
Analyze deployment relationships

## Features
- Deployment → ReplicaSet → Pod chain
- Service selector matching
- ConfigMap/Secret references
- Volume mount analysis

## Main Functions
- `analyze_deployment(deployment)` - Analyze single deployment
- `find_related_resources()` - Find related services, CMs, secrets
