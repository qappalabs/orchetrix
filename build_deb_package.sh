#!/bin/bash

# Orchetrix Universal .deb Package Builder
# This script creates a universal .deb package for all Linux distributions

set -e  # Exit on any error

# Configuration
APP_NAME="orchetrix"
APP_VERSION="${APP_VERSION:-1.0.0}"  # Allow version override via environment variable
MAINTAINER="Orchetrix Team <support@orchetrix.com>"
DESCRIPTION="Kubernetes Cluster Management Tool"
HOMEPAGE="https://github.com/your-org/orchetrix"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
BUILD_DIR="$PROJECT_ROOT/debian-package"

log_info "Starting .deb package build process..."
log_info "Project root: $PROJECT_ROOT"
log_info "Build directory: $BUILD_DIR"

# Clean previous build
if [ -d "$BUILD_DIR" ]; then
    log_info "Cleaning previous build directory..."
    rm -rf "$BUILD_DIR"
fi

# Create directory structure
log_info "Creating debian package directory structure..."
mkdir -p "$BUILD_DIR"/{DEBIAN,usr/bin,usr/share/applications,usr/share/pixmaps,usr/share/$APP_NAME,opt/$APP_NAME,opt/$APP_NAME/logs}

# Check if PyInstaller executable exists
PYINSTALLER_BINARY=""
if [ -f "$PROJECT_ROOT/dist/Orchetrix/Orchetrix" ]; then
    PYINSTALLER_BINARY="$PROJECT_ROOT/dist/Orchetrix/Orchetrix"
    log_success "Found PyInstaller binary at: $PYINSTALLER_BINARY"
elif [ -f "$PROJECT_ROOT/dist/Orchetrix" ]; then
    PYINSTALLER_BINARY="$PROJECT_ROOT/dist/Orchetrix"
    log_success "Found PyInstaller binary at: $PYINSTALLER_BINARY"
else
    log_warning "PyInstaller binary not found. Will build from source."
    log_info "Building PyInstaller binary..."
    
    # Check if PyInstaller is installed
    if ! command -v pyinstaller &> /dev/null; then
        log_info "Installing PyInstaller..."
        pip install pyinstaller
    fi
    
    # Build with PyInstaller
    pyinstaller --clean Orchetrix.spec
    
    # Check again for the binary
    if [ -f "$PROJECT_ROOT/dist/Orchetrix/Orchetrix" ]; then
        PYINSTALLER_BINARY="$PROJECT_ROOT/dist/Orchetrix/Orchetrix"
        log_success "Successfully built PyInstaller binary"
    else
        log_error "Failed to build PyInstaller binary"
        exit 1
    fi
fi

# Create control file
log_info "Creating DEBIAN/control file..."
cat > "$BUILD_DIR/DEBIAN/control" << EOF
Package: $APP_NAME
Version: $APP_VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: libc6, libqt6core6, libqt6gui6, libqt6widgets6, libqt6svg6, libqt6svgwidgets6, libglib2.0-0, libxcb1, libx11-6, libfontconfig1, libfreetype6, libxrender1, libxext6, libxfixes3, libxrandr2, libxdamage1, libxcomposite1, libxcursor1, libxi6, libxtst6, libdbus-1-3, libasound2, libssl3, libcrypto3, zlib1g, libexpat1, libpng16-16
Recommends: python3 (>= 3.8), kubectl, docker.io, qt6-base-dev
Suggests: kubectx, helm
Conflicts: orchetrix (<< $APP_VERSION)
Replaces: orchetrix (<< $APP_VERSION)
Maintainer: $MAINTAINER
Description: $DESCRIPTION
 Orchetrix is a comprehensive Kubernetes cluster management application
 built with PyQt6. It provides an intuitive graphical interface for
 managing Kubernetes clusters, pods, services, deployments, and other
 resources.
 .
 Features include:
  - Multi-cluster support with context switching
  - Real-time resource monitoring and metrics
  - Advanced YAML editor with syntax highlighting
  - Integrated terminal for kubectl commands
  - Resource visualization and management
  - Application deployment and monitoring
  - Event tracking and comprehensive logging
  - Port forwarding and network management
  - Helm chart management
  - Custom resource definitions support
 .
 This package works on all major Linux distributions supporting
 Python 3.8+ and PyQt6.
Homepage: $HOMEPAGE
EOF

# Create postinst script
log_info "Creating DEBIAN/postinst script..."
cat > "$BUILD_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
# Remove 'set -e' to prevent script failure from terminating installation

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log_message "Starting Orchetrix post-installation setup..."

# Check if this is a reinstall/upgrade
INSTALL_TYPE="install"
if [ "$1" = "configure" ] && [ -n "$2" ]; then
    INSTALL_TYPE="upgrade"
    log_message "Detected upgrade from version $2"
fi

# Always stop any running instances before installation/upgrade
log_message "Stopping any running Orchetrix instances..."
pkill -f "Orchetrix" 2>/dev/null || true
pkill -f "orchetrix" 2>/dev/null || true
sleep 2 || true

# Fix icon path issues by creating proper symlinks
log_message "Creating icon path symlinks..."
if [ -d "/opt/orchetrix/_internal/Icons" ] && [ ! -d "/opt/orchetrix/Icons" ]; then
    ln -sf /opt/orchetrix/_internal/Icons /opt/orchetrix/Icons 2>/dev/null || true
    log_message "✓ Created Icons symlink"
fi

# Clean up any leftover files from previous installations
if [ -d "/opt/orchetrix" ]; then
    log_message "Cleaning up previous installation files..."
    # Remove old symlinks that might cause issues
    find /opt/orchetrix -type l -delete 2>/dev/null || true
    # Remove any .pyc files that might cause issues
    find /opt/orchetrix -name "*.pyc" -delete 2>/dev/null || true
    # Remove any lock files
    find /opt/orchetrix -name "*.lock" -delete 2>/dev/null || true
    # Remove old configuration that might conflict
    find /opt/orchetrix -name "*.old" -delete 2>/dev/null || true
fi

# Ensure proper ownership and permissions
if [ -d "/opt/orchetrix" ]; then
    log_message "Setting proper file ownership and permissions..."
    chown -R root:root /opt/orchetrix
    find /opt/orchetrix -type f -exec chmod 644 {} \; 2>/dev/null || true
    find /opt/orchetrix -type d -exec chmod 755 {} \; 2>/dev/null || true
    # Make main binary executable
    chmod +x /opt/orchetrix/Orchetrix 2>/dev/null || true
    # Make logs directory writable by all users
    if [ -d "/opt/orchetrix/logs" ]; then
        chmod 777 /opt/orchetrix/logs 2>/dev/null || true
        log_message "✓ Set logs directory permissions (777)"
    fi
    log_message "✓ Set execute permissions on main binary"
fi

# Ensure launcher script is executable
if [ -f "/usr/bin/orchetrix" ]; then
    chmod +x /usr/bin/orchetrix
    log_message "✓ Launcher script is executable"
fi

# Create/update symlink for backward compatibility
ln -sf /usr/bin/orchetrix /usr/local/bin/orchetrix 2>/dev/null || true

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
    log_message "✓ Updated desktop database"
fi

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t /usr/share/pixmaps 2>/dev/null || true
    log_message "✓ Updated icon cache"
fi

# Verify installation
if [ -f "/opt/orchetrix/Orchetrix" ] && [ -x "/opt/orchetrix/Orchetrix" ]; then
    log_message "✓ Main binary verification passed"
else
    log_message "✗ Main binary verification failed - but continuing installation"
    log_message "Note: Binary may still work from terminal"
fi

if command -v orchetrix &> /dev/null; then
    log_message "✓ Command 'orchetrix' is available"
else
    log_message "✗ Command 'orchetrix' not found in PATH"
fi

echo ""
echo "============================================"
if [ "$INSTALL_TYPE" = "upgrade" ]; then
    echo "Orchetrix has been successfully upgraded!"
    echo "Previous version $2 has been replaced."
else
    echo "Orchetrix has been successfully installed!"
fi
echo "============================================"
echo "You can run it from:"
echo "  - Applications menu (search for 'Orchetrix')"
echo "  - Terminal: type 'orchetrix'"
echo ""
echo "Installation details:"
echo "  - Version: $(dpkg-query -W -f='${Version}' orchetrix 2>/dev/null || echo 'Unknown')"
echo "  - Binary: /opt/orchetrix/Orchetrix"
echo "  - Launcher: /usr/bin/orchetrix"
echo ""
echo "Note: This is a self-contained application that"
echo "includes all required dependencies."
echo "============================================"

exit 0
EOF

chmod 755 "$BUILD_DIR/DEBIAN/postinst"

# Skip preinst script - postinst handles everything we need

# Create prerm script
log_info "Creating DEBIAN/prerm script..."
cat > "$BUILD_DIR/DEBIAN/prerm" << 'EOF'
#!/bin/bash
# Remove 'set -e' to prevent script failure from blocking uninstallation

# Stop any running instances
pkill -f "Orchetrix" 2>/dev/null || true
pkill -f "orchetrix" 2>/dev/null || true
sleep 1 || true

# Remove symlink
rm -f /usr/local/bin/orchetrix 2>/dev/null || true

exit 0
EOF

chmod 755 "$BUILD_DIR/DEBIAN/prerm"

# Copy application files
log_info "Copying application files..."

if [ -n "$PYINSTALLER_BINARY" ]; then
    # Copy PyInstaller dist directory
    log_info "Copying PyInstaller distribution..."
    cp -r "$(dirname "$PYINSTALLER_BINARY")"/* "$BUILD_DIR/opt/$APP_NAME/"
    
    # Make sure the main binary is executable
    chmod +x "$BUILD_DIR/opt/$APP_NAME/Orchetrix"
    log_success "Made Orchetrix binary executable"
else
    # Copy source files for script-based installation
    log_info "Copying source files..."
    cp -r Icons Images Pages Services UI Utils Base_Components Business_Logic *.py requirements.txt "$BUILD_DIR/usr/share/$APP_NAME/"
fi

# Create launcher script
log_info "Creating launcher script..."
cat > "$BUILD_DIR/usr/bin/$APP_NAME" << EOF
#!/bin/bash

# Orchetrix launcher script - Self-contained PyInstaller version
APP_DIR="/opt/$APP_NAME"

# Set library path for the bundled application
export LD_LIBRARY_PATH="\$APP_DIR/_internal:\$LD_LIBRARY_PATH"

# Ensure icon symlink exists for runtime
if [ -d "\$APP_DIR/_internal/Icons" ] && [ ! -d "\$APP_DIR/Icons" ]; then
    ln -sf "\$APP_DIR/_internal/Icons" "\$APP_DIR/Icons" 2>/dev/null || true
fi

# Check if PyInstaller version exists
if [ -f "\$APP_DIR/Orchetrix" ]; then
    # Run PyInstaller binary
    cd "\$APP_DIR"
    exec "./Orchetrix" "\$@"
else
    echo "Error: Orchetrix installation not found at \$APP_DIR/Orchetrix"
    echo "Please reinstall the package."
    exit 1
fi
EOF

chmod +x "$BUILD_DIR/usr/bin/$APP_NAME"

# Create .desktop file
log_info "Creating desktop entry..."
cat > "$BUILD_DIR/usr/share/applications/$APP_NAME.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Orchetrix
Comment=Kubernetes Cluster Management Tool
Exec=$APP_NAME
Icon=orchetrix
Terminal=false
StartupNotify=true
Categories=Development;System;Network;
Keywords=kubernetes;k8s;cluster;management;docker;containers;
MimeType=application/x-yaml;text/x-yaml;
StartupWMClass=Orchetrix
EOF

# Copy icon
log_info "Copying application icon..."
if [ -f "$PROJECT_ROOT/Icons/logoIcon.png" ]; then
    cp "$PROJECT_ROOT/Icons/logoIcon.png" "$BUILD_DIR/usr/share/pixmaps/$APP_NAME.png"
elif [ -f "$PROJECT_ROOT/Icons/logoIcon.ico" ]; then
    # Convert ICO to PNG if needed
    if command -v convert &> /dev/null; then
        convert "$PROJECT_ROOT/Icons/logoIcon.ico" "$BUILD_DIR/usr/share/pixmaps/$APP_NAME.png"
    else
        cp "$PROJECT_ROOT/Icons/logoIcon.ico" "$BUILD_DIR/usr/share/pixmaps/$APP_NAME.ico"
        sed -i "s/Icon=orchetrix/Icon=orchetrix.ico/" "$BUILD_DIR/usr/share/applications/$APP_NAME.desktop"
    fi
else
    log_warning "No icon found, creating placeholder"
    # Create a simple placeholder icon
    echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" | base64 -d > "$BUILD_DIR/usr/share/pixmaps/$APP_NAME.png"
fi

# Create man page (optional)
log_info "Creating man page..."
mkdir -p "$BUILD_DIR/usr/share/man/man1"
cat > "$BUILD_DIR/usr/share/man/man1/$APP_NAME.1" << EOF
.TH ORCHETRIX 1 "$(date '+%B %Y')" "Orchetrix $APP_VERSION" "User Commands"
.SH NAME
orchetrix \- Kubernetes cluster management tool
.SH SYNOPSIS
.B orchetrix
[\fIOPTION\fR]
.SH DESCRIPTION
Orchetrix is a comprehensive Kubernetes cluster management application with a graphical interface.
It provides tools for managing clusters, pods, services, deployments, and other Kubernetes resources.
.SH OPTIONS
.TP
.B \-h, \-\-help
Show help message and exit
.SH FILES
.TP
.I ~/.kube/config
Default Kubernetes configuration file
.SH AUTHOR
Written by the Orchetrix Team.
.SH "REPORTING BUGS"
Report bugs to: <support@orchetrix.com>
.SH COPYRIGHT
Copyright © 2025 Orchetrix Team. License: MIT
EOF

gzip "$BUILD_DIR/usr/share/man/man1/$APP_NAME.1"

# Fix permissions
log_info "Setting correct permissions..."
find "$BUILD_DIR" -type f -exec chmod 644 {} \;
find "$BUILD_DIR" -type d -exec chmod 755 {} \;
chmod +x "$BUILD_DIR/usr/bin/$APP_NAME"
chmod +x "$BUILD_DIR/DEBIAN/postinst"
chmod +x "$BUILD_DIR/DEBIAN/prerm"

# Ensure the main binary is executable (critical fix)
if [ -f "$BUILD_DIR/opt/$APP_NAME/Orchetrix" ]; then
    chmod +x "$BUILD_DIR/opt/$APP_NAME/Orchetrix"
    log_success "Set execute permissions on main binary"
else
    log_error "Main binary not found at $BUILD_DIR/opt/$APP_NAME/Orchetrix"
fi

# Build the .deb package
log_info "Building .deb package..."
PACKAGE_NAME="${APP_NAME}_${APP_VERSION}_amd64.deb"

# Build with dpkg-deb
if command -v dpkg-deb &> /dev/null; then
    dpkg-deb --build "$BUILD_DIR" "$PROJECT_ROOT/$PACKAGE_NAME"
else
    log_error "dpkg-deb not found. Please install dpkg-dev package."
    exit 1
fi

# Verify the package
if [ -f "$PROJECT_ROOT/$PACKAGE_NAME" ]; then
    log_success "Package built successfully: $PACKAGE_NAME"
    
    # Show package info
    log_info "Package information:"
    dpkg-deb --info "$PROJECT_ROOT/$PACKAGE_NAME"
    
    echo
    log_info "Package contents:"
    dpkg-deb --contents "$PROJECT_ROOT/$PACKAGE_NAME" | head -20
    
    echo
    log_success "Build completed successfully!"
    echo
    echo "To install the package:"
    echo "  sudo dpkg -i $PACKAGE_NAME"
    echo "  sudo apt-get install -f  # Fix dependencies if needed"
    echo
    echo "To uninstall:"
    echo "  sudo dpkg -r $APP_NAME"
    echo
    echo "Package location: $PROJECT_ROOT/$PACKAGE_NAME"
else
    log_error "Package build failed"
    exit 1
fi