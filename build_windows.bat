@echo off
REM Orchetrix Windows Build Script
REM This script creates a Windows executable and installer using PyInstaller and NSIS

setlocal enabledelayedexpansion

REM Configuration
set APP_NAME=Orchetrix
set APP_VERSION=1.0.0
set COMPANY_NAME=Orchetrix Team
set COPYRIGHT=Copyright (C) 2025 Orchetrix Team

REM Colors (Windows cmd doesn't support ANSI by default, but these are for future use)
set RED=[31m
set GREEN=[32m
set YELLOW=[33m
set BLUE=[34m
set NC=[0m

echo [INFO] Starting Windows build process...
echo [INFO] App Name: %APP_NAME%
echo [INFO] Version: %APP_VERSION%

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    exit /b 1
)

REM Check if PyInstaller is available
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller not found, installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller
        exit /b 1
    )
)

REM Clean previous builds
if exist "build" (
    echo [INFO] Cleaning previous build directory...
    rmdir /s /q "build"
)

if exist "dist" (
    echo [INFO] Cleaning previous dist directory...
    rmdir /s /q "dist"
)

REM Build with PyInstaller
echo [INFO] Building Windows executable with PyInstaller...
pyinstaller --clean Orchetrix.spec

REM Check if build was successful
if not exist "dist\Orchetrix\Orchetrix.exe" (
    echo [ERROR] Build failed - executable not found
    exit /b 1
)

echo [SUCCESS] Build completed successfully!
echo [INFO] Executable location: dist\Orchetrix\Orchetrix.exe

REM Create a simple batch launcher
echo [INFO] Creating launcher script...
(
echo @echo off
echo REM Orchetrix Launcher
echo cd /d "%%~dp0"
echo start "" "Orchetrix.exe" %%*
) > "dist\Orchetrix\Launch_Orchetrix.bat"

REM Test the executable
echo [INFO] Testing executable...
"dist\Orchetrix\Orchetrix.exe" --help >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Executable test returned error, but this might be normal for GUI apps
) else (
    echo [SUCCESS] Executable test passed
)

REM Create installer script (NSIS)
echo [INFO] Creating NSIS installer script...
(
echo ; Orchetrix Windows Installer
echo ; Auto-generated installer script
echo !define APP_NAME "%APP_NAME%"
echo !define APP_VERSION "%APP_VERSION%"
echo !define COMPANY_NAME "%COMPANY_NAME%"
echo !define COPYRIGHT "%COPYRIGHT%"
echo !define APP_EXE "Orchetrix.exe"
echo.
echo ; Installer properties
echo Name "${APP_NAME}"
echo OutFile "${APP_NAME}_${APP_VERSION}_Setup.exe"
echo InstallDir "$PROGRAMFILES64\${APP_NAME}"
echo RequestExecutionLevel admin
echo.
echo ; Modern UI
echo !include "MUI2.nsh"
echo !define MUI_ABORTWARNING
echo !define MUI_ICON "Icons\logoIcon.ico"
echo !define MUI_UNICON "Icons\logoIcon.ico"
echo.
echo ; Pages
echo !insertmacro MUI_PAGE_LICENSE "LICENSE"
echo !insertmacro MUI_PAGE_DIRECTORY
echo !insertmacro MUI_PAGE_INSTFILES
echo !insertmacro MUI_PAGE_FINISH
echo.
echo !insertmacro MUI_UNPAGE_CONFIRM
echo !insertmacro MUI_UNPAGE_INSTFILES
echo.
echo ; Languages
echo !insertmacro MUI_LANGUAGE "English"
echo.
echo ; Installer sections
echo Section "MainSection" SEC01
echo  SetOutPath "$INSTDIR"
echo  File /r "dist\Orchetrix\*"
echo  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
echo  CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
echo  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
echo  WriteUninstaller "$INSTDIR\Uninstall.exe"
echo SectionEnd
echo.
echo ; Uninstaller section
echo Section "Uninstall"
echo  Delete "$INSTDIR\*.*"
echo  RMDir /r "$INSTDIR"
echo  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
echo  Delete "$DESKTOP\${APP_NAME}.lnk"
echo  RMDir "$SMPROGRAMS\${APP_NAME}"
echo SectionEnd
) > "installer.nsi"

REM Check if NSIS is available and create installer
makensis --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] NSIS not found - installer will not be created
    echo [INFO] You can manually install NSIS and run: makensis installer.nsi
) else (
    echo [INFO] Creating Windows installer...
    makensis installer.nsi
    if errorlevel 1 (
        echo [ERROR] Installer creation failed
    ) else (
        echo [SUCCESS] Installer created successfully: %APP_NAME%_%APP_VERSION%_Setup.exe
    )
)

echo.
echo [INFO] Build process completed!
echo [INFO] Files created:
echo   - Executable: dist\Orchetrix\Orchetrix.exe
echo   - Launcher: dist\Orchetrix\Launch_Orchetrix.bat
if exist "%APP_NAME%_%APP_VERSION%_Setup.exe" (
    echo   - Installer: %APP_NAME%_%APP_VERSION%_Setup.exe
)
echo.
echo [INFO] To test the application:
echo   cd dist\Orchetrix
echo   Orchetrix.exe
echo.

pause