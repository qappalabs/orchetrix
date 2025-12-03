# app_flow_business.py - Brief Documentation

**Path**: `orchetrix/Business_Logic/app_flow_business.py`
**Lines**: ~300

## Purpose
Application flow and navigation logic

## Features
- Page navigation management
- Application state handling
- Flow control between pages
- Back/forward navigation
- Page history

## Main Methods
- `navigate_to_page(page_name)` - Navigate to specific page
- `go_back()` - Navigate to previous page
- `get_current_page()` - Get active page
- `handle_page_change(page)` - Handle page transitions

## Used By
- ClusterView
- main.py
- Sidebar (navigation)
