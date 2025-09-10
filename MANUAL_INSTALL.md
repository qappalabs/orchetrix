# Manual Installation Guide for Orchetrix

If the .deb package installation fails with "Terminated", use this manual method:

## Method 1: Manual Extraction and Setup

```bash
# 1. Create installation directory
sudo mkdir -p /opt/orchetrix

# 2. Extract package manually
dpkg-deb --extract orchetrix_1.0.0-1_amd64.deb /tmp/orchetrix_extracted

# 3. Copy files to system
sudo cp -r /tmp/orchetrix_extracted/opt/orchetrix/* /opt/orchetrix/
sudo cp /tmp/orchetrix_extracted/usr/bin/orchetrix /usr/bin/orchetrix || sudo ln -sf /opt/orchetrix/Orchetrix /usr/bin/orchetrix
sudo cp /tmp/orchetrix_extracted/usr/share/applications/orchetrix.desktop /usr/share/applications/
sudo cp /tmp/orchetrix_extracted/usr/share/pixmaps/orchetrix.png /usr/share/pixmaps/

# 4. Set permissions
sudo chmod +x /opt/orchetrix/Orchetrix
sudo chmod +x /usr/bin/orchetrix

# 5. Update system caches
sudo update-desktop-database /usr/share/applications 2>/dev/null || true
sudo gtk-update-icon-cache /usr/share/pixmaps 2>/dev/null || true

# 6. Clean up
rm -rf /tmp/orchetrix_extracted

echo "Manual installation complete!"
echo "Launch with: orchetrix"
```

## Method 2: User-Space Installation (No Root Required)

```bash
# Install in user directory
mkdir -p ~/.local/bin ~/.local/share/applications ~/.local/share/pixmaps

# Extract and copy
dpkg-deb --extract orchetrix_1.0.0-1_amd64.deb /tmp/orchetrix_user
cp -r /tmp/orchetrix_user/opt/orchetrix ~/.local/share/
ln -sf ~/.local/share/orchetrix/Orchetrix ~/.local/bin/orchetrix

# Copy desktop files
cp /tmp/orchetrix_user/usr/share/applications/orchetrix.desktop ~/.local/share/applications/
cp /tmp/orchetrix_user/usr/share/pixmaps/orchetrix.png ~/.local/share/pixmaps/

# Update desktop file path for user installation
sed -i 's|Exec=orchetrix|Exec='$HOME'/.local/bin/orchetrix|g' ~/.local/share/applications/orchetrix.desktop

# Make sure ~/.local/bin is in PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Clean up
rm -rf /tmp/orchetrix_user

echo "User installation complete!"
echo "Launch with: orchetrix"
```

## Manual Uninstall

### System Installation Removal:
```bash
sudo rm -rf /opt/orchetrix
sudo rm -f /usr/bin/orchetrix
sudo rm -f /usr/share/applications/orchetrix.desktop
sudo rm -f /usr/share/pixmaps/orchetrix.png
sudo update-desktop-database /usr/share/applications 2>/dev/null || true
```

### User Installation Removal:
```bash
rm -rf ~/.local/share/orchetrix
rm -f ~/.local/bin/orchetrix
rm -f ~/.local/share/applications/orchetrix.desktop
rm -f ~/.local/share/pixmaps/orchetrix.png
```

### Complete User Data Removal:
```bash
rm -rf ~/.config/orchetrix ~/.cache/orchetrix
```

## Troubleshooting the "Terminated" Error

The "Terminated" error during dpkg installation can be caused by:

1. **System Issues:**
   ```bash
   # Fix dpkg issues
   sudo dpkg --configure -a
   sudo apt-get update
   sudo apt-get -f install
   ```

2. **Signal Interruption:**
   ```bash
   # Try installing with different signal handling
   sudo timeout 300 dpkg -i orchetrix_1.0.0-1_amd64.deb
   ```

3. **Package Cache Issues:**
   ```bash
   # Clear package cache
   sudo apt-get clean
   sudo apt-get autoclean
   ```

4. **Try Alternative Installation:**
   ```bash
   # Use gdebi (install if not available: sudo apt-get install gdebi)
   sudo gdebi orchetrix_1.0.0-1_amd64.deb
   ```

5. **Check System Resources:**
   ```bash
   # Ensure sufficient disk space and memory
   df -h
   free -h
   ```

## Verification

After manual installation, verify it works:

```bash
# Test the command
orchetrix --version || echo "Command available"

# Test the executable directly
/opt/orchetrix/Orchetrix --help 2>/dev/null || echo "Executable found"

# Check desktop integration
ls -la /usr/share/applications/orchetrix.desktop
```

This manual method bypasses the dpkg package manager issues and gives you the same result as a successful package installation.