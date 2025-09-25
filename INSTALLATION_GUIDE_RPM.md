# Orchetrix Universal RPM Installation Guide

**Orchetrix** is a self-contained Kubernetes management application that requires no Python installation or external dependencies.

## ⚡ Quick Install (One Command)

### RHEL/CentOS/Fedora
```bash
sudo dnf install -y orchetrix-0.0.2.x86_64.rpm
```

### openSUSE
```bash
sudo zypper install -y orchetrix-0.0.2.x86_64.rpm
```

### Manual Installation (if auto-install fails)
```bash
sudo rpm -ivh orchetrix-0.0.2.x86_64.rpm
```

## 🚀 Launch Application
- **From Applications Menu**: Search for "Orchetrix"
- **From Terminal**: `orchetrix`
- **Desktop Integration**: Appears in Development category

## 📦 What's Included
- ✅ Complete Python runtime (no system Python needed)
- ✅ All Kubernetes client libraries
- ✅ PyQt6 GUI framework
- ✅ All required dependencies bundled
- ✅ Desktop integration files
- ✅ Application icons and themes

## 🗑️ Uninstalling

### Standard Removal
```bash
sudo dnf remove orchetrix
# or
sudo zypper remove orchetrix
# or
sudo rpm -e orchetrix
```
*Removes the application but preserves user settings*

### Complete Removal
```bash
sudo dnf remove orchetrix
rm -rf ~/.config/orchetrix/
```
*Completely removes application and all user data*

## 🛠️ Troubleshooting

### System Compatibility
Orchetrix works on:
- ✅ RHEL/CentOS 7, 8, 9
- ✅ Fedora 35+
- ✅ openSUSE Leap 15.3+, Tumbleweed
- ✅ Rocky Linux/AlmaLinux 8, 9
- ✅ Most 64-bit RPM-based distributions

### Missing System Libraries (Rare)
On very minimal systems, you might need:
```bash
sudo dnf install libX11 libXext libXrender fontconfig freetype qt6-qtbase
```

### Kubernetes Access
Ensure kubectl is configured:
```bash
kubectl cluster-info
```

## 💻 System Requirements

### Minimum Requirements
- **OS**: Any 64-bit RPM-based Linux distribution
- **RAM**: 2GB minimum, 4GB recommended  
- **Storage**: 200MB free disk space
- **Display**: X11 or Wayland display server

### What You DON'T Need
- ❌ Python installation
- ❌ pip packages
- ❌ Virtual environments  
- ❌ Development tools
- ❌ Additional GUI frameworks

## 📋 Package Information
- **Version**: 0.0.2
- **Architecture**: x86_64 (64-bit)
- **Package Size**: 
- **Package Type**: Universal RPM
- **Built**: September 25, 2025

## 🔗 Additional Resources
- **Homepage**: https://orchetrix.io
- **Documentation**: Included in application
- **Support**: Built-in help system
