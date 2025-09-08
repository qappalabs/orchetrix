#!/usr/bin/env python3
"""
Orchetrix Universal Build Script
This script handles building for multiple platforms (Linux, Windows, macOS)
"""

import os
import sys
import subprocess
import platform
import argparse
import shutil
from pathlib import Path

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def log_info(message):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")

def log_success(message):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

def log_warning(message):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

def log_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

def run_command(cmd, shell=False):
    """Run a command and return its output"""
    try:
        if shell:
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        log_error(f"Command failed: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        log_error(f"Error: {e.stderr}")
        return None

def check_dependencies():
    """Check if required dependencies are installed"""
    log_info("Checking dependencies...")
    
    # Check Python
    try:
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            log_error("Python 3.8 or higher is required")
            return False
        log_success(f"Python {python_version.major}.{python_version.minor}.{python_version.micro} found")
    except Exception as e:
        log_error(f"Python check failed: {e}")
        return False
    
    # Check PyInstaller
    try:
        result = run_command(['pyinstaller', '--version'])
        if result:
            log_success(f"PyInstaller found: {result}")
        else:
            log_info("Installing PyInstaller...")
            run_command([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
    except Exception as e:
        log_error(f"PyInstaller check failed: {e}")
        return False
    
    return True

def clean_build():
    """Clean previous build artifacts"""
    log_info("Cleaning previous build artifacts...")
    
    dirs_to_clean = ['build', 'dist', 'debian-package']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            log_info(f"Removed {dir_name} directory")
    
    # Remove .spec files artifacts
    for file_path in Path('.').glob('*.spec'):
        try:
            os.remove(file_path)
            log_info(f"Removed {file_path}")
        except Exception as e:
            log_warning(f"Could not remove {file_path}: {e}")

def build_executable():
    """Build the executable using PyInstaller"""
    log_info("Building executable with PyInstaller...")
    
    if not os.path.exists('Orchetrix.spec'):
        log_error("Orchetrix.spec file not found")
        return False
    
    result = run_command(['pyinstaller', '--clean', 'Orchetrix.spec'])
    if result is None:
        log_error("PyInstaller build failed")
        return False
    
    # Check if executable was created
    system = platform.system().lower()
    if system == 'windows':
        exe_path = 'dist/Orchetrix/Orchetrix.exe'
    else:
        exe_path = 'dist/Orchetrix/Orchetrix'
    
    if os.path.exists(exe_path):
        log_success(f"Executable created: {exe_path}")
        return True
    else:
        log_error(f"Executable not found at {exe_path}")
        return False

def build_linux_deb():
    """Build Linux .deb package"""
    log_info("Building Linux .deb package...")
    
    if not os.path.exists('build_deb_package.sh'):
        log_error("build_deb_package.sh not found")
        return False
    
    # Make script executable
    os.chmod('build_deb_package.sh', 0o755)
    
    result = run_command(['bash', 'build_deb_package.sh'])
    if result is None:
        log_error("Debian package build failed")
        return False
    
    # Check if .deb file was created
    deb_files = list(Path('.').glob('*.deb'))
    if deb_files:
        log_success(f"Debian package created: {deb_files[0]}")
        return True
    else:
        log_error("No .deb file found")
        return False

def build_windows_installer():
    """Build Windows installer"""
    log_info("Building Windows installer...")
    
    if platform.system().lower() != 'windows':
        log_warning("Windows installer can only be built on Windows")
        return False
    
    if not os.path.exists('build_windows.bat'):
        log_error("build_windows.bat not found")
        return False
    
    result = run_command(['build_windows.bat'], shell=True)
    if result is None:
        log_error("Windows installer build failed")
        return False
    
    log_success("Windows installer build completed")
    return True

def create_portable_package():
    """Create a portable package from the dist directory"""
    log_info("Creating portable package...")
    
    system = platform.system().lower()
    if system == 'windows':
        archive_name = f'orchetrix_portable_windows.zip'
        import zipfile
        with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk('dist/Orchetrix'):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, 'dist')
                    zipf.write(file_path, arcname)
    else:
        archive_name = f'orchetrix_portable_linux.tar.gz'
        run_command(['tar', '-czf', archive_name, '-C', 'dist', 'Orchetrix'])
    
    if os.path.exists(archive_name):
        log_success(f"Portable package created: {archive_name}")
        return True
    else:
        log_error("Failed to create portable package")
        return False

def main():
    parser = argparse.ArgumentParser(description='Orchetrix Universal Build Script')
    parser.add_argument('--clean', action='store_true', help='Clean build artifacts only')
    parser.add_argument('--no-package', action='store_true', help='Skip package creation')
    parser.add_argument('--portable-only', action='store_true', help='Create only portable package')
    parser.add_argument('--deb-only', action='store_true', help='Create only .deb package (Linux)')
    parser.add_argument('--installer-only', action='store_true', help='Create only installer (Windows)')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Orchetrix Universal Build Script")
    print(f"Platform: {platform.system()} {platform.architecture()[0]}")
    print("=" * 50)
    
    # Clean only mode
    if args.clean:
        clean_build()
        log_success("Clean completed")
        return
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Clean previous builds
    clean_build()
    
    # Build executable
    if not build_executable():
        sys.exit(1)
    
    if args.no_package:
        log_success("Build completed (packages skipped)")
        return
    
    # Platform-specific packaging
    system = platform.system().lower()
    
    if args.portable_only:
        create_portable_package()
    elif args.deb_only and system == 'linux':
        build_linux_deb()
    elif args.installer_only and system == 'windows':
        build_windows_installer()
    else:
        # Build appropriate packages for platform
        if system == 'linux':
            build_linux_deb()
        elif system == 'windows':
            build_windows_installer()
        
        # Always create portable package
        create_portable_package()
    
    print("\n" + "=" * 50)
    log_success("Build process completed!")
    print("=" * 50)
    
    # Show created files
    print("\nCreated files:")
    for file_pattern in ['*.deb', '*.exe', '*.zip', '*.tar.gz']:
        files = list(Path('.').glob(file_pattern))
        for file in files:
            print(f"  - {file}")

if __name__ == '__main__':
    main()