#!/bin/bash
# Universal Linux build script for Orchetrix
# Builds AppImage, Flatpak, and Snap packages

set -e

echo "🚀 Building Universal Linux Packages for Orchetrix"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    echo "🔍 Checking prerequisites..."
    
    commands=("python3" "pip3" "wget")
    for cmd in "${commands[@]}"; do
        if command -v $cmd &> /dev/null; then
            print_status "$cmd is installed"
        else
            print_error "$cmd is required but not installed"
            exit 1
        fi
    done
}

# Build AppImage
build_appimage() {
    echo ""
    echo "📦 Building AppImage (Universal Linux Package)..."
    
    if [ -f "build-appimage.sh" ]; then
        chmod +x build-appimage.sh
        ./build-appimage.sh
        print_status "AppImage built successfully!"
    else
        print_error "build-appimage.sh not found"
    fi
}

# Build Flatpak
build_flatpak() {
    echo ""
    echo "📦 Building Flatpak Package..."
    
    if command -v flatpak-builder &> /dev/null; then
        if [ -f "com.orchetrix.Orchetrix.yml" ]; then
            flatpak-builder --repo=repo --force-clean build-dir com.orchetrix.Orchetrix.yml
            flatpak build-bundle repo orchetrix.flatpak com.orchetrix.Orchetrix
            print_status "Flatpak built successfully!"
        else
            print_error "com.orchetrix.Orchetrix.yml not found"
        fi
    else
        print_warning "flatpak-builder not installed, skipping Flatpak build"
        echo "Install with: sudo apt install flatpak-builder"
    fi
}

# Build Snap
build_snap() {
    echo ""
    echo "📦 Building Snap Package..."
    
    if command -v snapcraft &> /dev/null; then
        if [ -d "snap" ] && [ -f "snap/snapcraft.yaml" ]; then
            snapcraft --destructive-mode
            print_status "Snap built successfully!"
        else
            print_error "snap/snapcraft.yaml not found"
        fi
    else
        print_warning "snapcraft not installed, skipping Snap build"
        echo "Install with: sudo snap install snapcraft --classic"
    fi
}

# Main execution
main() {
    check_prerequisites
    
    echo ""
    echo "🎯 Select build type:"
    echo "1) AppImage only (Recommended - runs everywhere)"
    echo "2) All packages (AppImage + Flatpak + Snap)"
    echo "3) Exit"
    
    read -p "Enter choice (1-3): " choice
    
    case $choice in
        1)
            build_appimage
            ;;
        2)
            build_appimage
            build_flatpak
            build_snap
            ;;
        3)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
    
    echo ""
    echo "🎉 Build completed!"
    echo ""
    echo "📋 Distribution guide:"
    echo "• AppImage: ./Orchetrix-x86_64.AppImage (runs on ALL Linux)"
    echo "• Flatpak: flatpak install orchetrix.flatpak"
    echo "• Snap: sudo snap install orchetrix_*.snap --dangerous"
    echo ""
    echo "🌍 Universal compatibility:"
    echo "✅ Ubuntu (all versions)"
    echo "✅ Debian, Fedora, CentOS, Arch Linux"
    echo "✅ Any Linux distribution with glibc 2.17+"
}

main "$@"