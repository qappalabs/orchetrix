# Preferences.py - Brief Documentation

**Path**: `orchetrix/Pages/Preferences.py`
**Lines**: ~400

## Purpose
Application preferences and settings dialog

## Settings Categories
- **Theme**: Light/Dark mode
- **Font**: Terminal font family and size
- **Auto-refresh**: Refresh intervals for pages
- **Terminal**: Copy/paste, shell selection
- **Performance**: Cache settings, batch sizes

## Signals
- `theme_changed` - Theme selection changed
- `font_changed` - Font settings changed
- `copy_paste_changed` - Copy/paste toggle

## Persistence
Settings saved to `~/.orchetrix/config.json`
