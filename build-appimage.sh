#!/bin/bash
# AppImage build script for Orchetrix
# This creates a single Linux package that runs on all distributions

set -e

echo "Building Orchetrix AppImage for universal Linux distribution..."

# Install required tools
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv wget fuse

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build with PyInstaller
pyinstaller Orchetrix.spec --clean

# Download AppImage tools
wget -c https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage

# Create AppDir structure
mkdir -p Orchetrix.AppDir/usr/bin
mkdir -p Orchetrix.AppDir/usr/share/applications
mkdir -p Orchetrix.AppDir/usr/share/icons/hicolor/256x256/apps

# Copy built application
cp -r dist/Orchetrix/* Orchetrix.AppDir/usr/bin/

# Create desktop file
cat > Orchetrix.AppDir/orchetrix.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Orchetrix
Comment=Kubernetes Management GUI
Exec=orchetrix
Icon=orchetrix
Categories=Development;System;
StartupWMClass=Orchetrix
EOF

# Copy desktop file to proper location
cp Orchetrix.AppDir/orchetrix.desktop Orchetrix.AppDir/usr/share/applications/

# Copy icon
cp Icons/logoIcon.png Orchetrix.AppDir/orchetrix.png
cp Icons/logoIcon.png Orchetrix.AppDir/usr/share/icons/hicolor/256x256/apps/orchetrix.png

# Create AppRun script
cat > Orchetrix.AppDir/AppRun << 'EOF'
#!/bin/bash
# AppRun script for Orchetrix

HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"

# Set up environment
export QT_QPA_PLATFORM_PLUGIN_PATH="${HERE}/usr/bin"
export QT_PLUGIN_PATH="${HERE}/usr/bin"

# Run the application
cd "${HERE}/usr/bin"
exec "${HERE}/usr/bin/Orchetrix/Orchetrix" "$@"
EOF

chmod +x Orchetrix.AppDir/AppRun

# Build AppImage
./appimagetool-x86_64.AppImage Orchetrix.AppDir Orchetrix-x86_64.AppImage

echo "✅ AppImage created: Orchetrix-x86_64.AppImage"
echo "This single file runs on ALL Linux distributions!"
echo ""
echo "Usage:"
echo "  chmod +x Orchetrix-x86_64.AppImage"
echo "  ./Orchetrix-x86_64.AppImage"