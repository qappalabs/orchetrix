# helm_utils.py - Brief Documentation

**Path**: `orchetrix/Utils/helm_utils.py`
**Lines**: ~300
**Purpose**: Helm chart operations and utilities

## Key Features
- List available Helm charts
- Get chart details (README, values.yaml)
- Install/upgrade/delete charts
- Repository management

## Main Functions
- `list_charts(repo)` - List charts in repository
- `get_chart_details(chart_name)` - Get README and values
- `install_chart(chart, release_name, namespace, values)` - Install
- `upgrade_release(release, values)` - Upgrade existing release
- `delete_release(release, namespace)` - Uninstall release
- `list_releases(namespace)` - List installed releases
- `get_release_history(release)` - Get revision history

## Used By
- ChartsPage
- ReleasesPage
- Helm operations
