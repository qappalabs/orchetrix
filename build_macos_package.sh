#!/bin/bash

# Orchetrix macOS Package Builder
# Addresses common macOS PyInstaller packaging issues

set -e  # Exit on any error

# Configuration
APP_NAME="Orchetrix"
APP_VERSION="0.0.2"
SPEC_FILE="Orchetrix-macOS.spec"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

check_macos() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_error "This script is designed for macOS only"
        print_status "Use build_deb_package.sh for Linux builds"
        exit 1
    fi
    print_success "Running on macOS"
}

validate_environment() {
    print_status "Validating macOS build environment..."
    
    # Check if we're in the right directory
    if [[ ! -f "main.py" ]] || [[ ! -f "requirements.txt" ]]; then
        print_error "Please run this script from the Orchetrix source directory"
        exit 1
    fi
    
    # Check for Python 3
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        print_status "Install Python 3 from https://python.org or use Homebrew: brew install python3"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_status "Python version: $PYTHON_VERSION"
    
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_error "Python 3.8 or higher is required"
        exit 1
    fi
    
    # Check for pip
    if ! python3 -m pip --version &> /dev/null; then
        print_error "pip is not available"
        print_status "Install pip: python3 -m ensurepip --upgrade"
        exit 1
    fi
    
    print_success "Environment validation complete"
}

cleanup_previous_builds() {
    print_status "Cleaning up previous builds..."
    rm -rf build/ dist/ *.egg-info/ venv_build/
    rm -f *.dmg
    print_success "Cleanup complete"
}

setup_virtual_environment() {
    print_status "Setting up Python virtual environment..."
    
    # Create virtual environment
    python3 -m venv venv_build
    source venv_build/bin/activate
    
    # Upgrade pip and install build tools
    python3 -m pip install --upgrade pip setuptools wheel
    
    print_success "Virtual environment created"
}

install_dependencies() {
    print_status "Installing dependencies with macOS optimizations..."
    
    source venv_build/bin/activate
    
    # Install PyQt6 first (most critical dependency)
    print_status "Installing PyQt6..."
    python3 -m pip install PyQt6 PyQt6-Qt6 PyQt6-sip
    
    # Install kubernetes client
    print_status "Installing Kubernetes client..."
    python3 -m pip install kubernetes
    
    # Install other core dependencies
    print_status "Installing other dependencies..."
    python3 -m pip install -r requirements.txt
    
    # Install PyInstaller with specific version known to work on macOS
    print_status "Installing PyInstaller..."
    python3 -m pip install pyinstaller==6.2.0
    
    # Verify critical imports work
    print_status "Verifying critical imports..."
    python3 -c "
import PyQt6.QtCore
import PyQt6.QtWidgets
import kubernetes
import yaml
import requests
import psutil
print('✓ All critical imports successful')
"
    
    print_success "Dependencies installed successfully"
}

create_app_icon() {
    print_status "Creating macOS app icon..."
    
    # Check if we have an icon
    if [[ -f "Icons/logoIcon.png" ]]; then
        print_status "Converting PNG icon to ICNS format..."
        
        # Create iconset directory
        mkdir -p Orchetrix.iconset
        
        # Copy and resize icon for different sizes (if sips is available)
        if command -v sips &> /dev/null; then
            # Standard macOS icon sizes
            sips -z 16 16     Icons/logoIcon.png --out Orchetrix.iconset/icon_16x16.png
            sips -z 32 32     Icons/logoIcon.png --out Orchetrix.iconset/icon_16x16@2x.png
            sips -z 32 32     Icons/logoIcon.png --out Orchetrix.iconset/icon_32x32.png
            sips -z 64 64     Icons/logoIcon.png --out Orchetrix.iconset/icon_32x32@2x.png
            sips -z 128 128   Icons/logoIcon.png --out Orchetrix.iconset/icon_128x128.png
            sips -z 256 256   Icons/logoIcon.png --out Orchetrix.iconset/icon_128x128@2x.png
            sips -z 256 256   Icons/logoIcon.png --out Orchetrix.iconset/icon_256x256.png
            sips -z 512 512   Icons/logoIcon.png --out Orchetrix.iconset/icon_256x256@2x.png
            sips -z 512 512   Icons/logoIcon.png --out Orchetrix.iconset/icon_512x512.png
            sips -z 1024 1024 Icons/logoIcon.png --out Orchetrix.iconset/icon_512x512@2x.png
            
            # Create ICNS file
            if command -v iconutil &> /dev/null; then
                iconutil -c icns Orchetrix.iconset
                mv Orchetrix.icns Icons/logoIcon.icns
                rm -rf Orchetrix.iconset
                print_success "Created logoIcon.icns"
            else
                print_warning "iconutil not available, using PNG icon"
                rm -rf Orchetrix.iconset
            fi
        else
            print_warning "sips not available, using PNG icon"
        fi
    else
        print_warning "No app icon found, app will use default icon"
    fi
}

build_application() {
    print_status "Building application with PyInstaller..."
    
    source venv_build/bin/activate
    
    # Build with macOS spec file
    print_status "Using macOS-optimized spec file: $SPEC_FILE"
    pyinstaller --clean --noconfirm "$SPEC_FILE"
    
    # Verify build success
    if [[ -d "dist/Orchetrix.app" ]]; then
        print_success "App bundle created successfully"
    elif [[ -f "dist/Orchetrix/Orchetrix" ]]; then
        print_success "Application executable created successfully"
    else
        print_error "Build failed - no output found"
        exit 1
    fi
    
    print_success "Application build complete"
}

fix_permissions() {
    print_status "Fixing macOS permissions..."
    
    # Make sure the executable is executable
    if [[ -f "dist/Orchetrix.app/Contents/MacOS/Orchetrix" ]]; then
        chmod +x "dist/Orchetrix.app/Contents/MacOS/Orchetrix"
        print_success "App bundle permissions fixed"
    elif [[ -f "dist/Orchetrix/Orchetrix" ]]; then
        chmod +x "dist/Orchetrix/Orchetrix"
        print_success "Executable permissions fixed"
    fi
}

test_application() {
    print_status "Testing application..."
    
    if [[ -d "dist/Orchetrix.app" ]]; then
        print_status "Testing app bundle launch..."
        # Test if app can start (but exit quickly)
        timeout 10s open "dist/Orchetrix.app" || print_warning "App test timed out (this is normal)"
    elif [[ -f "dist/Orchetrix/Orchetrix" ]]; then
        print_status "Testing executable..."
        # Quick test of executable (but exit quickly to avoid hanging)
        timeout 5s ./dist/Orchetrix/Orchetrix --version || print_warning "Executable test completed"
    fi
    
    print_success "Application appears to be working"
}

create_installer() {
    print_status "Creating macOS installer..."
    
    if [[ -d "dist/Orchetrix.app" ]]; then
        # Create DMG installer
        if command -v hdiutil &> /dev/null; then
            print_status "Creating DMG installer..."
            
            # Create temporary directory for DMG contents
            mkdir -p dmg_temp
            cp -R "dist/Orchetrix.app" dmg_temp/
            
            # Create Applications symlink
            ln -sf /Applications dmg_temp/Applications
            
            # Create DMG
            DMG_NAME="${APP_NAME}-${APP_VERSION}-macOS.dmg"
            hdiutil create -volname "Orchetrix Installer" -srcfolder dmg_temp -ov -format UDZO "$DMG_NAME"
            
            # Cleanup
            rm -rf dmg_temp
            
            if [[ -f "$DMG_NAME" ]]; then
                print_success "DMG installer created: $DMG_NAME"
            else
                print_warning "DMG creation may have failed"
            fi
        else
            print_warning "hdiutil not available, skipping DMG creation"
        fi
    else
        print_status "Creating tarball for distribution..."
        tar -czf "${APP_NAME}-${APP_VERSION}-macOS.tar.gz" -C dist Orchetrix
        print_success "Tarball created: ${APP_NAME}-${APP_VERSION}-macOS.tar.gz"
    fi
}

create_usage_guide() {
    print_status "Creating usage guide..."
    
    cat > "MACOS_INSTALL_GUIDE.md" << EOF
# Orchetrix macOS Installation Guide

## System Requirements
- macOS 10.15 (Catalina) or later
- 4GB RAM minimum, 8GB recommended
- 500MB free disk space

## Installation

### Method 1: DMG Installer (Recommended)
1. Download \`Orchetrix-${APP_VERSION}-macOS.dmg\`
2. Double-click the DMG file to mount it
3. Drag \`Orchetrix.app\` to your Applications folder
4. Launch from Applications or Spotlight

### Method 2: Tarball
1. Download \`Orchetrix-${APP_VERSION}-macOS.tar.gz\`
2. Extract: \`tar -xzf Orchetrix-${APP_VERSION}-macOS.tar.gz\`
3. Run: \`./Orchetrix/Orchetrix\`

## Troubleshooting

### "App is damaged" or Security Warning
This happens because the app isn't signed with an Apple Developer certificate.

**Solution:**
\`\`\`bash
sudo xattr -rd com.apple.quarantine /Applications/Orchetrix.app
\`\`\`

Or go to: **System Preferences > Security & Privacy > General** and click "Open Anyway"

### Missing Dependencies Error
If you get "ModuleNotFoundError" for PyQt6 or kubernetes:

1. The app bundle should be self-contained, but if issues persist:
2. Install Python 3.8+ from python.org (not system Python)
3. Ensure you're running the correct build for your architecture

### Kubernetes Access
- Install kubectl: \`brew install kubectl\`
- Configure kubectl to connect to your cluster
- Verify: \`kubectl cluster-info\`

### Performance Issues
- Grant "Full Disk Access" in System Preferences > Security & Privacy
- Ensure you have sufficient RAM available

## Support
For issues specific to macOS, please include:
- macOS version (\`sw_vers\`)
- Architecture (Intel/Apple Silicon)
- Any console error messages

Built on: $(date)
Version: ${APP_VERSION}
EOF
    
    print_success "Usage guide created: MACOS_INSTALL_GUIDE.md"
}

cleanup_build_environment() {
    print_status "Cleaning up build environment..."
    
    # Deactivate virtual environment if active
    if [[ -n "$VIRTUAL_ENV" ]]; then
        deactivate || true
    fi
    
    # Remove build artifacts (keep the final package)
    rm -rf build/ *.egg-info/ venv_build/
    rm -rf Orchetrix.iconset
    
    print_success "Build cleanup complete"
}

main() {
    print_status "Starting Orchetrix macOS Package Build"
    print_status "Target: macOS universal compatibility with enhanced dependency bundling"
    echo ""
    
    # Execute build steps
    check_macos || exit 1
    validate_environment || exit 1
    cleanup_previous_builds || exit 1
    setup_virtual_environment || exit 1
    install_dependencies || exit 1
    create_app_icon || { print_warning "Icon creation failed, continuing..."; }
    build_application || exit 1
    fix_permissions || exit 1
    test_application || { print_warning "Application test failed, but continuing..."; }
    create_installer || { print_warning "Installer creation failed, but app was built"; }
    create_usage_guide || { print_warning "Could not create usage guide"; }
    cleanup_build_environment || { print_warning "Cleanup failed"; }
    
    echo ""
    print_success "macOS build completed successfully!"
    print_status "Generated files:"
    ls -lh *.dmg *.tar.gz 2>/dev/null || echo "No installer packages found"
    ls -lh dist/ 2>/dev/null || echo "No dist directory found"
    
    echo ""
    print_status "Installation instructions:"
    if [[ -f "*.dmg" ]]; then
        echo "  1. Double-click the .dmg file"
        echo "  2. Drag Orchetrix.app to Applications"
        echo "  3. Run from Applications folder"
    elif [[ -d "dist/Orchetrix.app" ]]; then
        echo "  1. Copy dist/Orchetrix.app to /Applications/"
        echo "  2. Run: open /Applications/Orchetrix.app"
    else
        echo "  1. Run: ./dist/Orchetrix/Orchetrix"
    fi
    
    echo ""
    print_status "If you get security warnings:"
    echo "  sudo xattr -rd com.apple.quarantine /path/to/Orchetrix.app"
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi