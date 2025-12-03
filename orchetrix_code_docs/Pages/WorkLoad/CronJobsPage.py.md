# CronJobsPage.py Documentation

## File Information
- **Path**: `orchetrix/Pages/WorkLoad/CronJobsPage.py`
- **Lines**: 276
- **Purpose**: Kubernetes CronJobs management page with schedule, suspend status, and last execution tracking

## Overview
CronJobsPage displays and manages Kubernetes CronJobs. CronJobs run Jobs on a time-based schedule (like cron in Linux). Used for recurring tasks like backups, report generation, data cleanup, etc. This page shows schedule (cron format), suspend status (red when suspended), active jobs count (green when active), and last schedule time.

---

## Class: CronJobsPage

### Constructor
```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.resource_type = "cronjobs"
    self.setup_page_ui()
```

### UI Setup
```python
def setup_page_ui(self):
    headers = ["", "Name", "Namespace", "Schedule", "Suspend", "Active", "Last Schedule", "Age", ""]
    sortable_columns = {1, 2, 3, 4, 5, 6, 7}
```

**9 columns**: Checkbox, Name, Namespace, Schedule, Suspend, Active, Last Schedule, Age, Actions

### Column Configuration
```python
column_specs = [
    (0, 40, "fixed"),        # Checkbox
    (1, 200, "interactive"), # Name
    (2, 100, "interactive"), # Namespace
    (3, 80, "interactive"),  # Schedule
    (4, 60, "interactive"),  # Suspend
    (5, 60, "interactive"),  # Active
    (6, 60, "interactive"),  # Last Schedule
    (7, 50, "stretch"),      # Age
    (8, 40, "fixed")         # Actions
]
```

---

## Data Extraction

### Schedule (Cron Format)
```python
schedule = ""
if raw_data:
    spec = raw_data.get("spec", {})
    schedule = spec.get("schedule", "")
```

**Cron Format Examples**:
- `0 0 * * *` → Daily at midnight
- `*/15 * * * *` → Every 15 minutes
- `0 2 * * 0` → Weekly on Sunday at 2 AM
- `0 0 1 * *` → Monthly on the 1st at midnight
- `0 9-17 * * 1-5` → Every hour 9-5 on weekdays

### Suspend Status (Color-Coded)
```python
suspend = "False"
if raw_data:
    spec = raw_data.get("spec", {})
    suspend = str(spec.get("suspend", False))
```

**Color Coding**:
```python
if col == 3:  # Suspend column
    if value.lower() == "true":
        item.setForeground(QColor(AppColors.STATUS_DISCONNECTED))  # Red
    else:
        item.setForeground(QColor(AppColors.TEXT_TABLE))  # Default
```

**When Suspended**:
- CronJob stops creating new Jobs
- Existing Jobs continue running
- Useful for maintenance or debugging

### Active Jobs Count (Color-Coded)
```python
active = "0"
if raw_data:
    status = raw_data.get("status", {})
    active_list = status.get("active", [])
    active = str(len(active_list))
```

**Color Coding**:
```python
elif col == 4:  # Active column
    try:
        if int(value) > 0:
            item.setForeground(QColor(AppColors.STATUS_ACTIVE))  # Green
        else:
            item.setForeground(QColor(AppColors.TEXT_TABLE))  # Default
    except ValueError:
        item.setForeground(QColor(AppColors.TEXT_TABLE))
```

**Interpretation**:
- `0` → No jobs currently running
- `1` → One job running (normal for single completions)
- `5` → Five jobs running (multiple parallel jobs or backlog)

### Last Schedule Time
```python
last_schedule = "Never"
if raw_data:
    status = raw_data.get("status", {})
    last_schedule_time = status.get("lastScheduleTime", "")
    if last_schedule_time:
        from dateutil import parser
        try:
            last_time = parser.parse(last_schedule_time)
            now = datetime.datetime.now(datetime.timezone.utc)
            diff = now - last_time
            
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            
            if days > 0:
                last_schedule = f"{days}d ago"
            elif hours > 0:
                last_schedule = f"{hours}h ago"
            else:
                last_schedule = f"{minutes}m ago"
        except Exception:
            last_schedule = "Error"
```

**Format**: Relative time
- `5m ago` → Ran 5 minutes ago
- `2h ago` → Ran 2 hours ago
- `3d ago` → Ran 3 days ago
- `Never` → Never executed yet

---

## Sortable Columns

### Suspend Sorting (Boolean)
```python
if col == 3:  # Suspend column (boolean as string)
    num = 1 if value.lower() == "true" else 0
    item = SortableTableWidgetItem(value, num)
```
Suspended (True=1) sort after non-suspended (False=0)

### Active Sorting (Numeric)
```python
elif col == 4:  # Active column (numeric)
    try:
        num = int(value)
    except ValueError:
        num = 0
    item = SortableTableWidgetItem(value, num)
```

### Last Schedule Sorting
```python
elif col == 5:  # Last Schedule column
    try:
        if value == "Never":
            num = 99999  # Put at end
        elif "d ago" in value:
            num = int(value.replace("d ago", "")) * 1440
        elif "h ago" in value:
            num = int(value.replace("h ago", "")) * 60
        elif "m ago" in value:
            num = int(value.replace("m ago", ""))
        else:
            num = 0
    except ValueError:
        num = 0
    item = SortableTableWidgetItem(value, num)
```

**Sorting Logic**:
- Most recent first: `5m ago` < `2h ago` < `3d ago` < `Never`

---

## Key Features

1. **Cron Schedule Display**: Shows when jobs will run
2. **Suspend Status**: Red when suspended, prevents new job creation
3. **Active Jobs Tracking**: Green when jobs running, shows count
4. **Last Execution**: Shows when last job was triggered
5. **Age Display**: How long CronJob has existed
6. **Sortable Columns**: Sort by schedule, suspend, active, last run
7. **Detail View**: Click row for full CronJob details
8. **Action Menu**: Edit and Delete options
9. **Bulk Selection**: Multi-delete via checkbox

## Action Menu Items
- **Edit**: Edit CronJob YAML (change schedule, suspend, etc.)
- **Delete**: Delete the CronJob (stops creating jobs)

## CronJob Characteristics

### What are CronJobs?
CronJobs create Jobs on a repeating schedule using cron syntax. They are Kubernetes' way of running scheduled tasks.

### Cron Schedule Format
```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday=0)
│ │ │ │ │
* * * * *
```

**Common Patterns**:
- `* * * * *` → Every minute
- `0 * * * *` → Every hour
- `0 0 * * *` → Daily at midnight
- `0 0 * * 0` → Weekly on Sunday
- `0 0 1 * *` → Monthly on 1st
- `0 0 1 1 *` → Yearly on Jan 1st

### Common Use Cases
- **Backups**: Database backups every night
- **Reports**: Generate reports daily/weekly
- **Cleanup**: Delete old data hourly
- **Monitoring**: Health checks every 5 minutes
- **Data Sync**: Sync data between systems

### CronJob Policies

**Concurrency Policy** (how to handle overlapping jobs):
```yaml
spec:
  concurrencyPolicy: Allow  # (default)
  # Options: Allow, Forbid, Replace
```
- **Allow**: Allow concurrent jobs (default)
- **Forbid**: Skip new job if previous still running
- **Replace**: Cancel previous job and start new one

**Failed Job History**:
```yaml
spec:
  failedJobsHistoryLimit: 1
  successfulJobsHistoryLimit: 3
```
- Keeps last 1 failed job
- Keeps last 3 successful jobs
- Older jobs automatically deleted

### Suspend vs Delete
- **Suspend**: Stops creating new jobs, keeps CronJob config
- **Delete**: Removes CronJob entirely (can't resume)

## Example Data Display

### Active CronJob
```
Name: backup-db
Schedule: 0 2 * * *
Suspend: False
Active: 1 (green)
Last Schedule: 5h ago
Age: 30d

Interpretation: 
- Runs daily at 2 AM
- Not suspended
- Job currently running (started 5h ago at 2 AM)
- CronJob created 30 days ago
```

### Suspended CronJob
```
Name: backup-db
Schedule: 0 2 * * *
Suspend: True (red)
Active: 0
Last Schedule: 1d ago
Age: 30d

Interpretation:
- Scheduled for daily 2 AM but suspended
- No jobs running
- Last ran 1 day ago (before suspension)
- Won't create new jobs until unsuspended
```

### Frequent CronJob
```
Name: health-check
Schedule: */5 * * * *
Suspend: False
Active: 0
Last Schedule: 2m ago
Age: 7d

Interpretation:
- Runs every 5 minutes
- Not suspended
- Last job finished (Active=0)
- Last ran 2 minutes ago
```

### Never Run CronJob
```
Name: new-report
Schedule: 0 0 * * 0
Suspend: False
Active: 0
Last Schedule: Never
Age: 1h

Interpretation:
- Runs weekly on Sunday at midnight
- Just created 1 hour ago
- Hasn't reached first schedule time yet
```

## Difference from Jobs
| Feature | Job | CronJob |
|---------|-----|---------|
| Execution | One-time | Recurring (scheduled) |
| Schedule | Manual/triggered | Cron format |
| Creates | Pods | Jobs (which create Pods) |
| History | Single run | Multiple runs |
| Use case | Batch task | Scheduled task |

## Dependencies
- BaseResourcePage
- SortableTableWidgetItem
- DetailManager
- AppStyles
- AppColors (for suspend/active colors)
- dateutil.parser (for timestamp parsing)
