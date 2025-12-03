# JobsPage.py Documentation

## File Information
- **Path**: `orchetrix/Pages/WorkLoad/JobsPage.py`
- **Lines**: 228
- **Purpose**: Kubernetes Jobs management page with completion tracking and colored conditions

## Overview
JobsPage displays and manages Kubernetes Jobs. Jobs create pods that run to completion - used for batch processing, one-time tasks, data processing, backups, etc. This page shows completion status (successful/total) and color-coded conditions (Complete=green, Failed=red).

---

## Class: JobsPage

### Constructor
```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.resource_type = "jobs"
    self.setup_page_ui()
```

### UI Setup
```python
def setup_page_ui(self):
    headers = ["", "Name", "Namespace", "Completions", "Age", "Conditions", ""]
    sortable_columns = {1, 2, 3, 4, 5}
```

**7 columns**: Checkbox, Name, Namespace, Completions, Age, Conditions, Actions

### Column Configuration
```python
column_specs = [
    (0, 40, "fixed"),        # Checkbox
    (1, 200, "interactive"), # Name
    (2, 100, "interactive"), # Namespace
    (3, 90, "interactive"),  # Completions
    (4, 50, "interactive"),  # Age
    (5, 70, "stretch"),      # Conditions
    (6, 40, "fixed")         # Actions
]
```

---

## Data Extraction

### Completions
```python
completions = "0/1"

if raw_data:
    spec = raw_data.get("spec", {})
    status = raw_data.get("status", {})
    
    successful = status.get("succeeded", 0)
    parallelism = spec.get("completions", 1)
    completions = f"{successful}/{parallelism}"
```

**Format**: `successful/total`
- `1/1` → Job completed successfully
- `0/1` → Job not finished yet
- `3/5` → 3 of 5 completions done (parallel jobs)
- `0/3` → Job failed or pending

### Conditions with Color Coding
```python
condition_list = status.get("conditions", [])
condition_types = []
for condition in condition_list:
    if condition.get("status") == "True":
        condition_types.append(condition.get("type", ""))
conditions = " ".join(condition_types)
```

**Common Job Conditions**:
- **Complete**: Job finished successfully
- **Failed**: Job failed (exceeded backoff limit)
- **Suspended**: Job is suspended

**Color Coding**:
```python
if col == 4:  # Conditions column
    if "Complete" in value:
        item.setForeground(QColor(AppColors.STATUS_ACTIVE))  # Green
    elif "Failed" in value:
        item.setForeground(QColor(AppColors.STATUS_DISCONNECTED))  # Red
    else:
        item.setForeground(QColor(AppColors.TEXT_TABLE))  # Default
```

---

## Sortable Columns

### Completions Sorting
```python
if col == 2:  # Completions column
    try:
        successful, total = value.split("/")
        completion_value = float(successful) / float(total) if float(total) > 0 else 0
    except (ValueError, ZeroDivisionError):
        completion_value = 0
    item = SortableTableWidgetItem(value, completion_value)
```

**Sorting Logic**:
- `3/3` = 1.0 (100%) - sorted first
- `2/3` = 0.666 (66%)
- `1/3` = 0.333 (33%)
- `0/3` = 0.0 (0%) - sorted last

### Age Sorting
```python
elif col == 3:  # Age column
    if 'd' in value:
        age_value = int(value.replace('d', '')) * 1440
    elif 'h' in value:
        age_value = int(value.replace('h', '')) * 60
    elif 'm' in value:
        age_value = int(value.replace('m', ''))
```

---

## Row Click with Raw Data
```python
def handle_row_click(self, row, column):
    # Get raw data from resources if available
    if row < len(getattr(self, 'resources', [])):
        resource = self.resources[row]
        raw_data = resource.get("raw_data")
    
    parent.detail_manager.show_detail(resource_type, resource_name, namespace, raw_data=raw_data)
```

**Unique Feature**: Passes raw_data to detail manager for richer job details

---

## Key Features

1. **Completion Tracking**: Shows successful/total completions
2. **Color-Coded Conditions**: Green for Complete, Red for Failed
3. **Age Display**: Human-readable format
4. **Sortable Columns**: Sort by completions percentage, age, name
5. **Detail View**: Click row for full job details with YAML
6. **Action Menu**: Edit and Delete options
7. **Bulk Selection**: Multi-delete via checkbox

## Action Menu Items
- **Edit**: Edit Job YAML
- **Delete**: Delete the Job (deletes pods)

## Job Characteristics

### What are Jobs?
Jobs create one or more pods and ensure a specified number complete successfully. Unlike Deployments, Jobs run to completion rather than running indefinitely.

### Job Types

**Single Job**:
```yaml
spec:
  completions: 1
  parallelism: 1
```
Display: `1/1` when done

**Parallel Jobs with Fixed Completion Count**:
```yaml
spec:
  completions: 5
  parallelism: 3
```
- Runs 3 pods in parallel
- Stops when 5 completions reached
- Display: `3/5` (in progress) → `5/5` (complete)

**Parallel Jobs with Work Queue**:
```yaml
spec:
  completions: null
  parallelism: 3
```
- Runs until all work items processed
- No fixed completion count

### Common Use Cases
- **Data Processing**: Process batch of files
- **Backups**: Database backups
- **Migrations**: Schema migrations
- **Report Generation**: Nightly reports
- **Cleanup Tasks**: Delete old resources

### Job Failure Handling
```yaml
spec:
  backoffLimit: 4
```
- Retries failed pods up to 4 times
- After 4 failures, Job marked as Failed

## Example Data Display

### Successful Job
```
Name: backup-job
Completions: 1/1
Conditions: Complete (green)
Age: 5m

Interpretation: Job completed successfully 5 minutes ago
```

### Failed Job
```
Name: migration-job
Completions: 0/1
Conditions: Failed (red)
Age: 10m

Interpretation: Job failed after exhausting retry limit
```

### Parallel Job In Progress
```
Name: data-processing
Completions: 7/10
Conditions: (empty)
Age: 2h

Interpretation: 7 of 10 parallel tasks completed, 3 remaining
```

### Parallel Job Complete
```
Name: data-processing
Completions: 10/10
Conditions: Complete (green)
Age: 3h

Interpretation: All 10 parallel tasks finished successfully
```

## Difference from CronJobs
| Feature | Job | CronJob |
|---------|-----|---------|
| Schedule | One-time | Recurring (cron) |
| Execution | Manual or event-triggered | Time-based |
| Management | Standalone | Creates Jobs |
| Use case | One-off tasks | Scheduled tasks |

## Dependencies
- BaseResourcePage
- SortableTableWidgetItem
- DetailManager
- AppStyles
- AppColors (for condition colors)
