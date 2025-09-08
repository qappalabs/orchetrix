#!/bin/bash

# Simple version builder for Orchetrix
# Usage: ./build_version.sh [version]
# Example: ./build_version.sh 1.1.0

set -e

VERSION="${1:-1.0.0}"

echo "Building Orchetrix version $VERSION"
echo "=================================="

# Set environment variable for the build script
export APP_VERSION="$VERSION"

# Clean previous build
rm -f orchetrix_*.deb

# Build the package
./build_deb_package.sh

echo ""
echo "✅ Package built: orchetrix_${VERSION}_amd64.deb"
echo ""
echo "Installation commands:"
echo "  Fresh install:    sudo dpkg -i orchetrix_${VERSION}_amd64.deb"
echo "  Upgrade:          sudo dpkg -i orchetrix_${VERSION}_amd64.deb"
echo "  Force reinstall:  sudo dpkg --force-reinstall -i orchetrix_${VERSION}_amd64.deb"