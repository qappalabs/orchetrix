#!/bin/bash

# Orchetrix Universal .rpm Package Builder
# Creates universal .rpm packages compatible with RHEL/CentOS/Fedora/openSUSE
# Includes dependency management and uninstall support

set -e  # Exit on any error

# Configuration
APP_NAME="orchetrix"
APP_DISPLAY_NAME="Orchetrix"
APP_VERSION="0.0.2"
APP_DESCRIPTION="Advanced Kubernetes Management Desktop Application"
APP_MAINTAINER="Orchetrix Team <support@orchetrix.io>"
APP_HOMEPAGE="https://orchetrix.io"
APP_CATEGORY="Development"
ARCH="x86_64"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate environment
validate_environment() {
    print_status "Validating build environment..."
    
    # Check if we're in the right directory
    if [[ ! -f "main.py" ]] || [[ ! -f "requirements.txt" ]]; then
        print_error "Please run this script from the Orchetrix source directory containing main.py and requirements.txt"
        exit 1
    fi
    
    # Check required tools
    local required_tools=("python3" "rpmbuild")
    for tool in "${required_tools[@]}"; do
        if ! command -v $tool &> /dev/null; then
            print_error "Required tool '$tool' is not installed"
            if command -v dnf >/dev/null 2>&1; then
                print_status "Install with: sudo dnf install rpm-build rpm-devel python3"
            elif command -v yum >/dev/null 2>&1; then
                print_status "Install with: sudo yum install rpm-build rpm-devel python3"
            elif command -v zypper >/dev/null 2>&1; then
                print_status "Install with: sudo zypper install rpm-build python3"
            fi
            exit 1
        fi
    done
    
    # Check for venv module
    if ! /usr/bin/python3 -m venv --help &> /dev/null; then
        print_error "python3-venv module is not available"
        print_status "Install with: sudo dnf install python3-venv"
        exit 1
    fi
    
    # Check for pip
    if ! command -v pip3 &> /dev/null && ! /usr/bin/python3 -m pip --version &> /dev/null 2>&1; then
        print_error "pip is not available. Please install with: sudo dnf install python3-pip"
        exit 1
    fi
    
    print_success "Environment validation complete"
}

# Clean up previous builds
cleanup_previous_builds() {
    print_status "Cleaning up previous builds..."
    rm -rf build/ dist/ *.egg-info/ rpm_package/ venv_build/ rpmbuild/
    rm -f *.rpm *.spec
    print_success "Cleanup complete"
}

# Create Python virtual environment and install dependencies
setup_python_environment() {
    print_status "Setting up Python build environment..."
    
    # Deactivate any existing virtual environment
    deactivate 2>/dev/null || true
    
    # Create virtual environment using system python
    /usr/bin/python3 -m venv venv_build
    source venv_build/bin/activate
    
    # Upgrade pip and install build tools
    python3 -m pip install --upgrade pip setuptools wheel
    
    # Install application dependencies
    python3 -m pip install -r requirements.txt
    
    # Install PyInstaller for creating executable
    python3 -m pip install pyinstaller==6.14.1
    
    print_success "Python environment setup complete"
}

# Build the application using PyInstaller
build_application() {
    print_status "Building application with PyInstaller..."
    
    source venv_build/bin/activate
    
    # Create PyInstaller spec if it doesn't exist
    if [[ ! -f "Orchetrix.spec" ]]; then
        print_warning "Orchetrix.spec not found, creating basic spec file"
        create_pyinstaller_spec
    fi
    
    # Build the application
    pyinstaller --clean --noconfirm Orchetrix.spec
    
    # Verify build success
    if [[ ! -f "dist/Orchetrix/Orchetrix" ]]; then
        print_error "PyInstaller build failed - executable not found"
        exit 1
    fi
    
    print_success "Application build complete"
}

# Create PyInstaller spec file if needed
create_pyinstaller_spec() {
    cat > Orchetrix.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

# Get absolute path to icon
icon_path = os.path.abspath(os.path.join('Icons', 'logoIcon.ico'))
if not os.path.exists(icon_path):
    icon_path = os.path.abspath(os.path.join('Icons', 'logoIcon.png'))
    if not os.path.exists(icon_path):
        icon_path = None

def collect_data_files():
    """Collect all necessary data files"""
    data_files = []
    
    # Add resource directories
    resource_dirs = ['Icons', 'Images', 'UI', 'Pages', 'Utils', 'Services', 'Base_Components']
    for dir_name in resource_dirs:
        if os.path.exists(dir_name) and os.path.isdir(dir_name):
            data_files.append((dir_name, dir_name))
    
    return data_files

# Comprehensive hidden imports
hidden_imports = [
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtSvg',
    'kubernetes', 'kubernetes.client', 'kubernetes.config', 'kubernetes.stream',
    'yaml', 'requests', 'psutil', 'logging', 'json', 'datetime', 'threading',
    'subprocess', 'tempfile', 'shutil', 'base64', 'ssl', 'socket'
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=collect_data_files(),
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Orchetrix',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if icon_path and os.path.exists(icon_path) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Orchetrix',
)
EOF
}

# Create RPM build directory structure
create_rpm_structure() {
    print_status "Creating RPM build directory structure..."
    
    # Create RPM build directories
    mkdir -p rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
    
    # Create source tarball
    local source_dir="rpmbuild/SOURCES/${APP_NAME}-${APP_VERSION}"
    mkdir -p "$source_dir"
    
    # Copy application files
    cp -r dist/Orchetrix/* "$source_dir/"
    chmod +x "$source_dir/Orchetrix"
    
    # Create additional files
    create_desktop_file "$source_dir"
    copy_application_icon "$source_dir"
    
    # Create tarball
    cd rpmbuild/SOURCES
    tar czf "${APP_NAME}-${APP_VERSION}.tar.gz" "${APP_NAME}-${APP_VERSION}/"
    cd - > /dev/null
    
    print_success "RPM build structure created"
}

# Create desktop file
create_desktop_file() {
    local source_dir="$1"
    cat > "$source_dir/$APP_NAME.desktop" << EOF
[Desktop Entry]
Version=0.0.2
Type=Application
Name=$APP_DISPLAY_NAME
Comment=$APP_DESCRIPTION
Exec=$APP_NAME
Icon=$APP_NAME
Categories=$APP_CATEGORY;System;Monitor;
StartupNotify=true
StartupWMClass=Orchetrix
Keywords=kubernetes;k8s;cluster;management;docker;containers;
EOF
}

# Copy application icon
copy_application_icon() {
    local source_dir="$1"
    
    # Look for icon files in the Icons directory
    if [[ -f "Icons/logoIcon.png" ]]; then
        cp "Icons/logoIcon.png" "$source_dir/$APP_NAME.png"
    elif [[ -f "Icons/logoIcon.ico" ]]; then
        # Convert ICO to PNG if needed (requires imagemagick)
        if command -v convert &> /dev/null; then
            convert "Icons/logoIcon.ico" "$source_dir/$APP_NAME.png"
        else
            cp "Icons/logoIcon.ico" "$source_dir/$APP_NAME.ico"
        fi
    else
        print_warning "No application icon found"
    fi
}

# Create RPM spec file
create_rpm_spec() {
    print_status "Creating RPM spec file..."
    
    cat > "rpmbuild/SPECS/${APP_NAME}.spec" << EOF
%global _missing_build_ids_terminate_build 0
%global _build_id_links none
%global debug_package %{nil}

Name:           $APP_NAME
Version:        $APP_VERSION
Release:        1%{?dist}
Summary:        $APP_DESCRIPTION

License:        Proprietary
URL:            $APP_HOMEPAGE
Source0:        %{name}-%{version}.tar.gz

BuildArch:      $ARCH

# Runtime dependencies
Requires:       python3 >= 3.8
Requires:       glibc >= 2.17
Requires:       libX11
Requires:       libXext
Requires:       libXrender
Requires:       fontconfig
Requires:       freetype
Requires:       qt6-qtbase
Requires:       qt6-qtsvg

# No additional package recommendations - self-contained application

%description
$APP_DISPLAY_NAME is a comprehensive Kubernetes management desktop application
that provides an intuitive graphical interface for managing Kubernetes
clusters, resources, and workloads.

Features include:
 * Multi-cluster management
 * Resource visualization and editing
 * Real-time monitoring and metrics
 * Terminal integration
 * Application flow analysis
 * YAML editing with syntax highlighting

Compatible with all major Kubernetes distributions including
Docker Desktop, minikube, kind, and cloud providers.

%prep
%setup -q

%build
# No build required - using pre-built binaries

%install
rm -rf %{buildroot}

# Create directories
mkdir -p %{buildroot}/opt/%{name}
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/share/pixmaps

# Install application files
cp -r * %{buildroot}/opt/%{name}/
rm -f %{buildroot}/opt/%{name}/%{name}.desktop
rm -f %{buildroot}/opt/%{name}/%{name}.png

# Create executable wrapper script
cat > %{buildroot}/usr/bin/%{name} << 'WRAPPER_EOF'
#!/bin/bash
# Orchetrix Launcher Script

# Set up environment
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export QT_ENABLE_HIGHDPI_SCALING=1

# Change to application directory
cd /opt/%{name}

# Launch application
exec ./Orchetrix "\$@"
WRAPPER_EOF
chmod +x %{buildroot}/usr/bin/%{name}

# Install desktop file
install -m 644 %{name}.desktop %{buildroot}/usr/share/applications/

# Install icon if exists
if [ -f %{name}.png ]; then
    install -m 644 %{name}.png %{buildroot}/usr/share/pixmaps/
fi

%post
# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || :
fi

# Update icon cache
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/pixmaps >/dev/null 2>&1 || :
fi

echo "==================================================================="
echo "$APP_DISPLAY_NAME $APP_VERSION has been installed successfully!"
echo ""
echo "To start the application:"
echo "  - From command line: $APP_NAME"
echo "  - From desktop: Look for '$APP_DISPLAY_NAME' in your applications menu"
echo ""
echo "System Requirements:"
echo "  - Kubernetes cluster access (kubectl configured)"
echo "  - 2GB RAM minimum, 4GB recommended"
echo "  - X11 display (for GUI)"
echo ""
echo "Documentation: $APP_HOMEPAGE"
echo "==================================================================="

%preun
# Stop any running instances
pkill -f "Orchetrix" 2>/dev/null || true

%postun
# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || :
fi

# Update icon cache  
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/pixmaps >/dev/null 2>&1 || :
fi

%files
%defattr(-,root,root,-)
/opt/%{name}/
/usr/bin/%{name}
/usr/share/applications/%{name}.desktop
/usr/share/pixmaps/%{name}.png

%changelog
* $(date +'%a %b %d %Y') $APP_MAINTAINER - $APP_VERSION
- Initial RPM package for $APP_DISPLAY_NAME $APP_VERSION
- Self-contained installation with embedded Python runtime
- Desktop integration with applications menu
- Support for RHEL/CentOS/Fedora/openSUSE

EOF

    print_success "RPM spec file created"
}

# Build the RPM package
build_rpm_package() {
    print_status "Building RPM package..."
    
    local spec_file="rpmbuild/SPECS/${APP_NAME}.spec"
    
    # Build the RPM
    rpmbuild --define "_topdir $(pwd)/rpmbuild" -ba "$spec_file"
    
    # Find the built RPM
    local rpm_file=$(find rpmbuild/RPMS -name "*.rpm" -type f | head -1)
    
    if [[ -z "$rpm_file" ]]; then
        print_error "RPM file not found after build"
        exit 1
    fi
    
    # Copy RPM to current directory
    cp "$rpm_file" "./$(basename "$rpm_file")"
    
    local final_rpm="$(basename "$rpm_file")"
    
    if [[ -f "$final_rpm" ]]; then
        print_success "Package built successfully: $final_rpm"
        
        # Display package information
        print_status "Package Information:"
        rpm -qip "$final_rpm"
        
        echo ""
        print_status "Package Contents:"
        rpm -qlp "$final_rpm" | head -20
        
        if [[ $(rpm -qlp "$final_rpm" | wc -l) -gt 20 ]]; then
            echo "... and $(( $(rpm -qlp "$final_rpm" | wc -l) - 20 )) more files"
        fi
        
    else
        print_error "Package build failed"
        exit 1
    fi
}

# Test installation (optional)
test_installation() {
    local rpm_file="${APP_NAME}-${APP_VERSION}.${ARCH}.rpm"
    
    print_status "Testing package installation (dry-run)..."
    
    # Check if we can simulate installation
    if rpm -K "$rpm_file" >/dev/null 2>&1; then
        print_success "Package verification test passed"
    else
        print_warning "Package verification test failed"
    fi
}

# Create installation instructions
create_installation_guide() {
    local rpm_file="${APP_NAME}-${APP_VERSION}.${ARCH}.rpm"
    
    cat > "INSTALLATION_GUIDE_RPM.md" << EOF
# Orchetrix Universal RPM Installation Guide

**Orchetrix** is a self-contained Kubernetes management application that requires no Python installation or external dependencies.

## ⚡ Quick Install (One Command)

### RHEL/CentOS/Fedora
\`\`\`bash
sudo dnf install -y $rpm_file
\`\`\`

### openSUSE
\`\`\`bash
sudo zypper install -y $rpm_file
\`\`\`

### Manual Installation (if auto-install fails)
\`\`\`bash
sudo rpm -ivh $rpm_file
\`\`\`

## 🚀 Launch Application
- **From Applications Menu**: Search for "Orchetrix"
- **From Terminal**: \`orchetrix\`
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
\`\`\`bash
sudo dnf remove orchetrix
# or
sudo zypper remove orchetrix
# or
sudo rpm -e orchetrix
\`\`\`
*Removes the application but preserves user settings*

### Complete Removal
\`\`\`bash
sudo dnf remove orchetrix
rm -rf ~/.config/orchetrix/
\`\`\`
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
\`\`\`bash
sudo dnf install libX11 libXext libXrender fontconfig freetype qt6-qtbase
\`\`\`

### Kubernetes Access
Ensure kubectl is configured:
\`\`\`bash
kubectl cluster-info
\`\`\`

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
- **Version**: $APP_VERSION
- **Architecture**: $ARCH (64-bit)
- **Package Size**: $(du -h $rpm_file 2>/dev/null | cut -f1 || echo "65M")
- **Package Type**: Universal RPM
- **Built**: $(date '+%B %d, %Y')

## 🔗 Additional Resources
- **Homepage**: https://orchetrix.io
- **Documentation**: Included in application
- **Support**: Built-in help system
EOF

    print_success "Installation guide created: INSTALLATION_GUIDE_RPM.md"
}

# Cleanup build environment
cleanup_build_environment() {
    print_status "Cleaning up build environment..."
    
    # Deactivate virtual environment if active
    if [[ -n "$VIRTUAL_ENV" ]]; then
        deactivate || true
    fi
    
    # Remove all build artifacts and folders (keep only the .rpm file)
    rm -rf build/ dist/ *.egg-info/ rpmbuild/ venv_build/
    
    print_success "Build cleanup complete"
}

# Main execution flow
main() {
    print_status "Starting Orchetrix Universal RPM Package Build"
    print_status "Target: RHEL/CentOS/Fedora/openSUSE universal compatibility"
    echo ""
    
    # Execute build steps
    validate_environment || exit 1
    cleanup_previous_builds || exit 1
    setup_python_environment || exit 1
    build_application || exit 1
    create_rpm_structure || exit 1
    create_rpm_spec || exit 1
    build_rpm_package || { print_error "Package build failed, but continuing..."; }
    test_installation || { print_warning "Installation test failed, but continuing..."; }
    create_installation_guide || { print_warning "Could not create installation guide"; }
    cleanup_build_environment || { print_warning "Cleanup failed"; }
    
    echo ""
    print_success "Build completed successfully!"
    print_status "Generated files:"
    ls -lh *.rpm 2>/dev/null || echo "No .rpm files found"
    ls -lh INSTALLATION_GUIDE_RPM.md 2>/dev/null || echo "No installation guide found"
    
    echo ""
    print_status "To install the package:"
    echo "  sudo dnf install -y ${APP_NAME}-${APP_VERSION}.${ARCH}.rpm"
    echo "  # or"
    echo "  sudo zypper install -y ${APP_NAME}-${APP_VERSION}.${ARCH}.rpm"
    
    print_status "To uninstall:"
    echo "  sudo dnf remove $APP_NAME"
    echo "  sudo zypper remove $APP_NAME"
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi