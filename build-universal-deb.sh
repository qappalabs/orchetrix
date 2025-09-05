#!/bin/bash

# Universal .deb Builder for Orchetrix Kubernetes Manager
# Builds compatible packages for Ubuntu 20.04+ and Debian 11+

set -e  # Exit on any error

# Configuration
APP_NAME="orchetrix"
APP_VERSION="1.0.0"
APP_DESCRIPTION="Orchetrix Kubernetes Manager - Desktop GUI for Kubernetes cluster management"
MAINTAINER="Your Name <your.email@example.com>"
ARCHITECTURE=$(dpkg --print-architecture)
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Orchetrix Universal .deb Builder ===${NC}"
echo -e "Version: ${APP_VERSION}"
echo -e "Architecture: ${ARCHITECTURE}"
echo -e "Python: ${PYTHON_VERSION}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if we're on a supported system
    if ! command -v dpkg >/dev/null 2>&1; then
        print_error "dpkg not found. This script requires a Debian-based system."
        exit 1
    fi
    
    # Check Python version (minimum 3.8 for compatibility)
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
        print_error "Python 3.8+ required for building"
        exit 1
    fi
    
    # Check PyInstaller
    if ! python3 -c "import PyInstaller" 2>/dev/null; then
        print_error "PyInstaller not found. Install with: pip install pyinstaller"
        exit 1
    fi
    
    # Check if required directories exist
    if [[ ! -f "main.py" ]] || [[ ! -f "Orchetrix.spec" ]]; then
        print_error "main.py or Orchetrix.spec not found. Run this script from the project root."
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Clean previous builds
clean_build() {
    print_status "Cleaning previous builds..."
    rm -rf build/ dist/ *.deb
    rm -rf debian-package/
    print_status "Cleaned build artifacts"
}

# Build application with PyInstaller
build_application() {
    print_status "Building application with PyInstaller..."
    
    # Build the application
    pyinstaller Orchetrix.spec --clean --noconfirm
    
    if [[ ! -d "dist/Orchetrix" ]]; then
        print_error "PyInstaller build failed - dist/Orchetrix directory not found"
        exit 1
    fi
    
    print_status "PyInstaller build completed successfully"
}

# Create Debian package structure
create_package_structure() {
    print_status "Creating Debian package structure..."
    
    PACKAGE_DIR="debian-package"
    PACKAGE_NAME="${APP_NAME}_${APP_VERSION}_${ARCHITECTURE}"
    
    # Create base directories
    mkdir -p "${PACKAGE_DIR}/DEBIAN"
    mkdir -p "${PACKAGE_DIR}/usr/lib/${APP_NAME}"
    mkdir -p "${PACKAGE_DIR}/usr/bin"
    mkdir -p "${PACKAGE_DIR}/usr/share/applications"
    mkdir -p "${PACKAGE_DIR}/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "${PACKAGE_DIR}/usr/share/doc/${APP_NAME}"
    
    print_status "Package structure created"
}

# Copy application files
copy_application_files() {
    print_status "Copying application files..."
    
    # Copy the entire PyInstaller dist directory
    cp -r dist/Orchetrix/* debian-package/usr/lib/${APP_NAME}/
    
    # Make the main executable... executable
    chmod +x debian-package/usr/lib/${APP_NAME}/Orchetrix
    
    # Create symlink in /usr/bin
    ln -sf "/usr/lib/${APP_NAME}/Orchetrix" "debian-package/usr/bin/${APP_NAME}"
    
    # Copy icon if it exists
    if [[ -f "Icons/logoIcon.png" ]]; then
        cp Icons/logoIcon.png debian-package/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png
    elif [[ -f "Icons/logoIcon.ico" ]]; then
        # Convert ICO to PNG if needed (requires imagemagick)
        if command -v convert >/dev/null 2>&1; then
            convert Icons/logoIcon.ico debian-package/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png
        else
            print_warning "ImageMagick not found, skipping icon conversion"
        fi
    fi
    
    print_status "Application files copied"
}

# Create DEBIAN control file
create_control_file() {
    print_status "Creating DEBIAN control file..."
    
    # Calculate installed size (in KB)
    INSTALLED_SIZE=$(du -sk debian-package | cut -f1)
    
    cat > debian-package/DEBIAN/control << EOF
Package: ${APP_NAME}
Version: ${APP_VERSION}
Section: utils
Priority: optional
Architecture: ${ARCHITECTURE}
Installed-Size: ${INSTALLED_SIZE}
Depends: libc6 (>= 2.31), libqt6core6 (>= 6.2.0) | libqt6core5compat6, libqt6gui6 (>= 6.2.0), libqt6widgets6 (>= 6.2.0), python3 (>= 3.8), libssl3 | libssl1.1
Recommends: kubectl, helm
Suggests: kubernetes-client
Maintainer: ${MAINTAINER}
Description: ${APP_DESCRIPTION}
 Orchetrix is a comprehensive PyQt6-based Kubernetes cluster management
 application that provides a desktop GUI for managing Kubernetes resources.
 .
 Features include:
  - Resource browsing and management
  - YAML editing with syntax highlighting
  - Port forwarding capabilities
  - Integrated terminal access
  - Helm chart management
  - Multi-cluster support
Homepage: https://github.com/yourusername/orchetrix
EOF

    print_status "Control file created"
}

# Create desktop entry
create_desktop_entry() {
    print_status "Creating desktop entry..."
    
    cat > debian-package/usr/share/applications/${APP_NAME}.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Orchetrix
Comment=Kubernetes Cluster Management Tool
Exec=${APP_NAME}
Icon=${APP_NAME}
Terminal=false
StartupNotify=true
Categories=Development;System;Network;
Keywords=kubernetes;k8s;cluster;management;devops;
MimeType=application/x-kubernetes-config;
EOF

    print_status "Desktop entry created"
}

# Create postinst script
create_postinst_script() {
    print_status "Creating post-installation script..."
    
    cat > debian-package/DEBIAN/postinst << 'EOF'
#!/bin/bash
set -e

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications
fi

# Update icon cache
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor
fi

# Create application directory for user data
mkdir -p /var/lib/orchetrix
chmod 755 /var/lib/orchetrix

echo "Orchetrix has been installed successfully!"
echo "You can start it from the applications menu or run 'orchetrix' in terminal."

exit 0
EOF

    chmod 755 debian-package/DEBIAN/postinst
    print_status "Post-installation script created"
}

# Create prerm script
create_prerm_script() {
    print_status "Creating pre-removal script..."
    
    cat > debian-package/DEBIAN/prerm << 'EOF'
#!/bin/bash
set -e

# Stop any running orchetrix processes
pkill -f orchetrix || true

# Clean up temporary files
rm -rf /tmp/orchetrix-* || true

exit 0
EOF

    chmod 755 debian-package/DEBIAN/prerm
    print_status "Pre-removal script created"
}

# Create copyright file
create_copyright_file() {
    print_status "Creating copyright file..."
    
    cat > debian-package/usr/share/doc/${APP_NAME}/copyright << EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: orchetrix
Source: https://github.com/yourusername/orchetrix

Files: *
Copyright: 2025 Your Name
License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included in all
 copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
EOF

    print_status "Copyright file created"
}

# Build the .deb package
build_deb_package() {
    print_status "Building .deb package..."
    
    PACKAGE_NAME="${APP_NAME}_${APP_VERSION}_${ARCHITECTURE}.deb"
    
    # Build the package
    dpkg-deb --root-owner-group --build debian-package "${PACKAGE_NAME}"
    
    if [[ -f "${PACKAGE_NAME}" ]]; then
        print_status "Package built successfully: ${PACKAGE_NAME}"
        
        # Show package info
        echo -e "\n${BLUE}Package Information:${NC}"
        dpkg-deb --info "${PACKAGE_NAME}"
        
        # Show package contents
        echo -e "\n${BLUE}Package Contents:${NC}"
        dpkg-deb --contents "${PACKAGE_NAME}" 2>/dev/null | head -20 || true
        
        # Check for errors
        echo -e "\n${BLUE}Package Validation:${NC}"
        if command -v lintian >/dev/null 2>&1; then
            lintian "${PACKAGE_NAME}" || true
        else
            print_warning "lintian not available for package validation"
        fi
        
    else
        print_error "Package build failed"
        exit 1
    fi
}

# Test installation (optional)
test_installation() {
    if [[ "$1" == "--test" ]]; then
        print_status "Testing package installation..."
        PACKAGE_NAME="${APP_NAME}_${APP_VERSION}_${ARCHITECTURE}.deb"
        
        print_warning "This will install the package for testing. Continue? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            sudo dpkg -i "${PACKAGE_NAME}" || {
                print_warning "Installation failed, attempting to fix dependencies..."
                sudo apt-get install -f -y
            }
            
            print_status "Testing if orchetrix command works..."
            if command -v orchetrix >/dev/null 2>&1; then
                print_status "Installation test successful!"
            else
                print_error "Installation test failed - orchetrix command not found"
            fi
        fi
    fi
}

# Main build process
main() {
    echo -e "${BLUE}Starting build process...${NC}\n"
    
    check_prerequisites
    clean_build
    build_application
    create_package_structure
    copy_application_files
    create_control_file
    create_desktop_entry
    create_postinst_script
    create_prerm_script
    create_copyright_file
    build_deb_package
    
    echo -e "\n${GREEN}✅ Build completed successfully!${NC}"
    echo -e "Package: ${APP_NAME}_${APP_VERSION}_${ARCHITECTURE}.deb"
    echo -e "\nTo install: sudo dpkg -i ${APP_NAME}_${APP_VERSION}_${ARCHITECTURE}.deb"
    echo -e "To test:    ./build-universal-deb.sh --test"
    
    # Test if requested
    test_installation "$1"
}

# Run main function with all arguments
main "$@"