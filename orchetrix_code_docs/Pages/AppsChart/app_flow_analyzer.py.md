# app_flow_analyzer.py - Brief Documentation

**Path**: `orchetrix/Pages/AppsChart/app_flow_analyzer.py`
**Lines**: ~200

## Purpose
Analyze application flow and dependencies

## Features
- Detect service dependencies
- Trace request paths
- Identify ingress → service → pod chains
- Build dependency graph

## Main Functions
- `analyze_flow(namespace)` - Analyze namespace
- `build_dependency_graph()` - Create graph
- `find_entry_points()` - Find ingresses
