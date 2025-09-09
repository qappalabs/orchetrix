# Orchestrix .deb Package Building Guide

This guide explains how to build .deb packages for Orchestrix Kubernetes Manager that work across all major Linux distributions.

## Quick Start

```bash
# Install build dependencies
make install-deps

# Build packages for all distributions
make build

# Or for a quick test build
make build-simple
```

## Package Structure

The packaging system creates packages for multiple Linux distributions:

```
debian/                    # Debian packaging configuration
├── control               # Package metadata and dependencies
├── rules                 # Build rules
├── changelog             # Package changelog
├── copyright             # License information
├── compat                # Debhelper compatibility level
├── postinst              # Post-installation script
├── postrm                # Post-removal script
├── orchestrix.desktop    # Desktop entry file
└── source/
    └── format            # Source package format

build_deb.sh              # Main build script (all distributions)
build_simple.sh           # Simple build script (testing)
Makefile                  # Build automation
```

## Build Scripts

### 1. Full Build Script (`build_deb.sh`)

The main build script creates packages for all major Linux distributions:

- **Distributions**: Ubuntu, Debian, Mint, Pop!_OS, elementary, Kali, Parrot
- **Architectures**: amd64 (x86_64), arm64 (aarch64)
- **Features**: 
  - Distribution-specific packages
  - Generic packages for compatibility
  - Universal packages for maximum compatibility
  - Installation scripts for each distribution
  - Checksum generation
  - Comprehensive documentation

### 2. Simple Build Script (`build_simple.sh`)

Quick build script for development and testing:

```bash
./build_simple.sh
```

### 3. Makefile Automation

Provides convenient make targets:

```bash
make help           # Show available commands
make install-deps   # Install build dependencies
make build          # Full build for all distributions
make build-simple   # Quick build for testing
make clean          # Clean build directories
make test-package   # Test package installation
make dev-install    # Install package for development
make dev-remove     # Remove development package
```

## Building Process

### Prerequisites

1. **System Requirements**:
   - Debian/Ubuntu-based Linux distribution
   - Python 3.8 or higher
   - Build tools (automatically installed)

2. **Install Dependencies**:
   ```bash
   make install-deps
   ```
   
   Or manually:
   ```bash
   sudo apt-get update
   sudo apt-get install -y build-essential devscripts debhelper dh-python \
                           python3-dev python3-pip python3-venv
   ```

### Building Packages

#### Option 1: Full Build (Recommended for Release)

```bash
# Build packages for all distributions and architectures
./build_deb.sh
```

This creates:
- Distribution-specific packages in `dist_deb/distro_name/`
- Generic packages in `dist_deb/generic/`
- Universal packages in `dist_deb/universal/`
- Installation scripts for each distribution
- Documentation and checksums

#### Option 2: Quick Build (Development)

```bash
# Quick build for current architecture only
./build_simple.sh
```

This creates a single package in the parent directory.

#### Option 3: Makefile Build

```bash
# Full automated build
make build

# Or quick build
make build-simple
```

## Package Output

After building, you'll find packages in:

```
dist_deb/
├── ubuntu/          # Ubuntu-specific packages
│   ├── orchestrix_1.0.0-1_ubuntu_amd64.deb
│   └── install_orchestrix.sh
├── debian/          # Debian-specific packages
├── generic/         # Generic packages for any Debian/Ubuntu system
│   └── orchestrix_1.0.0-1_amd64.deb
├── universal/       # Universal packages with enhanced compatibility
│   └── orchestrix_1.0.0-1_all-linux_amd64.deb
├── install_orchestrix_universal.sh    # Universal installer
├── checksums.txt    # SHA256 checksums for all packages
└── README.md        # Installation instructions
```

## Installation

### For End Users

1. **Universal Installation (Recommended)**:
   ```bash
   cd dist_deb/
   chmod +x install_orchestrix_universal.sh
   ./install_orchestrix_universal.sh
   ```

2. **Manual Installation**:
   ```bash
   # Choose the appropriate package for your system
   sudo dpkg -i dist_deb/generic/orchestrix_1.0.0-1_amd64.deb
   sudo apt-get install -f  # Fix any missing dependencies
   ```

3. **Distribution-Specific Installation**:
   ```bash
   cd dist_deb/ubuntu/  # Replace with your distribution
   chmod +x install_orchestrix.sh
   ./install_orchestrix.sh
   ```

### For Developers

```bash
# Install for testing
make dev-install

# Remove after testing
make dev-remove
```

## Package Configuration

### Debian Control File

Key settings in `debian/control`:

```
Package: orchestrix
Version: 1.0.0
Architecture: amd64
Depends: python3 (>= 3.8), python3-pip, python3-venv
Recommends: docker.io, kubectl
Description: Orchestrix Kubernetes Manager
```

### Build Rules

The `debian/rules` file handles:

- Virtual environment creation
- Dependency installation
- PyInstaller-based application building
- File installation and permissions
- Desktop integration

## Customization

### Changing Package Information

Edit these files to customize the package:

1. **`debian/control`** - Package metadata, dependencies
2. **`debian/changelog`** - Version history
3. **`debian/copyright`** - License information
4. **`version_info.txt`** - Windows version info (used by PyInstaller)

### Adding Dependencies

To add system dependencies:

```bash
# Edit debian/control
Depends: python3 (>= 3.8), python3-pip, python3-venv, new-dependency
```

To add Python dependencies:

```bash
# Edit requirements.txt
new-python-package==1.0.0
```

### Supporting New Distributions

1. Add the distribution to the `DISTRIBUTIONS` array in `build_deb.sh`
2. Test the package on the new distribution
3. Create distribution-specific control files if needed

## Troubleshooting

### Common Issues

1. **Missing Dependencies**:
   ```bash
   make install-deps
   ```

2. **Build Failures**:
   - Check Python version (3.8+ required)
   - Verify all source files are present
   - Check build logs in `build_deb/build_*.log`

3. **Package Installation Issues**:
   ```bash
   sudo apt-get update
   sudo apt-get install -f
   ```

4. **Permission Issues**:
   ```bash
   sudo chown -R $USER:$USER build_deb/ dist_deb/
   ```

### Debug Mode

For verbose output during building:

```bash
# Enable debug mode
export VERBOSE=1
./build_deb.sh
```

### Clean Build

If builds are failing, try a clean build:

```bash
make clean
make build
```

## Testing

### Package Testing

1. **Dry-run Installation**:
   ```bash
   make test-package
   ```

2. **Full Installation Test**:
   ```bash
   make dev-install
   orchestrix  # Test the application
   make dev-remove
   ```

3. **Multi-architecture Testing**:
   - Test on different architectures (amd64, arm64)
   - Test on different distributions
   - Verify all dependencies are resolved

## Continuous Integration

For automated building in CI/CD:

```bash
# CI-friendly build (non-interactive)
make ci-build

# CI with testing
make ci-test
```

## Advanced Usage

### Cross-compilation

For ARM64 packages on x86_64 systems:

```bash
# May require additional setup for cross-compilation
# The build script will warn about this
./build_deb.sh
```

### Custom Build Locations

```bash
# Custom output directory
OUTPUT_DIR=/custom/path ./build_deb.sh
```

### Signing Packages

To sign packages for distribution:

```bash
# Add GPG signing to the build process
# Edit debian/rules and add signing commands
```

## Distribution

### Package Repository

To distribute packages via APT repository:

1. Create a repository structure
2. Generate package indices
3. Sign the repository
4. Provide installation instructions

### Release Process

1. Update version in `debian/changelog`
2. Update `version_info.txt`
3. Build packages: `make build`
4. Test packages on target systems
5. Generate checksums: automatically done
6. Upload to distribution channels

## License

The packaging configuration is part of the Orchestrix project and follows the same license terms (GPL-3.0).

## Support

For packaging issues:

1. Check this documentation
2. Review build logs
3. Test on clean systems
4. Create issue reports with full build logs

---

*This packaging system ensures Orchestrix can be easily installed on all major Linux distributions while maintaining compatibility and following Debian packaging standards.*