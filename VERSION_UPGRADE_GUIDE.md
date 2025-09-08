# Orchetrix Version Management Guide

## ✅ Version Conflicts - SOLVED!

The package now handles version conflicts automatically using Debian package management features.

## How Version Upgrades Work

### 1. **Conflict Prevention**
```
Conflicts: orchetrix (<< $APP_VERSION)
Replaces: orchetrix (<< $APP_VERSION)
```
- Automatically removes older versions
- Prevents file conflicts
- Ensures clean upgrades

### 2. **Smart Upgrade Process**
When installing a new version:
1. **Stops running instances** of old version
2. **Cleans conflicting files** (.pyc, .lock, .old files)
3. **Replaces old files** with new ones
4. **Fixes permissions** automatically
5. **Verifies installation** works

### 3. **No Manual Cleanup Needed**
Old approach (problematic):
```bash
# Manual cleanup required
sudo dpkg -r orchetrix       # Remove old
rm -rf /opt/orchetrix         # Clean files  
sudo dpkg -i new_version.deb # Install new
```

New approach (automatic):
```bash
# Just install - everything handled automatically
sudo dpkg -i orchetrix_1.1.0_amd64.deb
```

## Building Different Versions

### Quick Version Build
```bash
./build_version.sh 1.1.0
# Creates: orchetrix_1.1.0_amd64.deb
```

### Custom Versions
```bash
./build_version.sh 2.0.0-beta
./build_version.sh 1.5.2
./build_version.sh 3.0.0-rc1
```

## Version Scenarios

### Scenario 1: Minor Update (1.0.0 → 1.0.1)
```bash
sudo dpkg -i orchetrix_1.0.1_amd64.deb
```
**Result:** Smooth upgrade, settings preserved

### Scenario 2: Major Update (1.0.0 → 2.0.0)  
```bash
sudo dpkg -i orchetrix_2.0.0_amd64.deb
```
**Result:** Old version replaced, conflicts handled

### Scenario 3: Downgrade (2.0.0 → 1.9.0)
```bash
sudo dpkg --force-downgrade -i orchetrix_1.9.0_amd64.deb
```
**Result:** Explicit downgrade with force flag

### Scenario 4: Same Version Reinstall
```bash
sudo dpkg --force-reinstall -i orchetrix_1.0.0_amd64.deb
```
**Result:** Fixes corrupted installations

## What Gets Cleaned During Upgrade

### Automatic Cleanup
- ✅ **Process cleanup:** Stops running instances
- ✅ **File cleanup:** Removes .pyc, .lock, .old files  
- ✅ **Permission fixes:** Resets all file permissions
- ✅ **Symlink updates:** Fixes broken symbolic links

### Preserved Data
- ✅ **User settings:** Configuration files kept
- ✅ **Logs:** Application logs maintained
- ✅ **Desktop integration:** Menu entries updated

## Rollback Strategy

### If New Version Has Issues
1. **Keep old .deb file:**
   ```bash
   # Downgrade to previous version
   sudo dpkg --force-downgrade -i orchetrix_1.0.0_amd64.deb
   ```

2. **Or remove completely:**
   ```bash
   sudo dpkg --purge orchetrix
   # Then reinstall preferred version
   ```

## Development Workflow

### For Developers
```bash
# Build development version
./build_version.sh 1.1.0-dev

# Test installation
sudo dpkg -i orchetrix_1.1.0-dev_amd64.deb

# Build release version  
./build_version.sh 1.1.0

# Deploy
sudo dpkg -i orchetrix_1.1.0_amd64.deb
```

### For Users
```bash
# Just install any version - conflicts handled automatically
sudo dpkg -i orchetrix_[any_version]_amd64.deb
```

## Summary

**Before:** Manual cleanup required, version conflicts, broken installations  
**After:** Automatic conflict resolution, smooth upgrades, no manual intervention

The system now handles **all version scenarios gracefully** without user intervention!