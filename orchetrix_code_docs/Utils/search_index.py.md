# search_index.py - Brief Documentation

**Path**: `orchetrix/Utils/search_index.py`
**Lines**: ~200
**Purpose**: Fast search indexing for resources

## Key Features
- Index resource names and labels
- Fuzzy search support
- Incremental updates
- Fast lookups

## Main Methods
- `index_resource(resource)` - Add to index
- `search(query)` - Search indexed resources
- `update_index(resources)` - Bulk update
- `clear_index()` - Clear all indexed data

## Used By
- SearchResourceLoadWorker
- Resource pages with search
- Quick filter functionality
