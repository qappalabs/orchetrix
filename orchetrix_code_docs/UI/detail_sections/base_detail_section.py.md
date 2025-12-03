# base_detail_section.py - Brief Documentation

**Path**: `orchetrix/UI/detail_sections/base_detail_section.py`
**Lines**: ~100

## Purpose
Base class for all detail section tabs

## Provides
- Common section structure
- Loading state management
- Error display
- Data loading signals

## Signals
- `loading_started` - Section started loading
- `loading_finished` - Section finished loading
- `error_occurred` - Error during loading
- `data_loaded` - Data successfully loaded

## Subclasses
- DetailPageOverviewSection
- DetailPageDetailsSection
- DetailPageYAMLSection
- DetailPageEventsSection
