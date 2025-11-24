@echo off
REM VVenC Installation Script for Windows
REM Requires: Git, CMake, Visual Studio 2019 or later

echo ==========================================
echo VVenC Installation Script for Windows
echo ==========================================
echo.

REM Configuration
set VVENC_VERSION=v1.11.1
set INSTALL_DIR=%USERPROFILE%\vvenc
set BUILD_TYPE=Release

echo VVenC Version: %VVENC_VERSION%
echo Install Directory: %INSTALL_DIR%
echo.

REM Check dependencies
echo Checking dependencies...

where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: git is not installed
    echo Download from: https://git-scm.com/download/win
    exit /b 1
)

where cmake >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: cmake is not installed
    echo Download from: https://cmake.org/download/
    exit /b 1
)

echo [OK] All dependencies found
echo.

REM Clone VVenC
echo Cloning VVenC repository...
if exist "%INSTALL_DIR%" (
    echo Directory %INSTALL_DIR% already exists
    set /p REPLY="Remove and re-clone? (y/n): "
    if /i "%REPLY%"=="y" (
        rmdir /s /q "%INSTALL_DIR%"
    )
)

if not exist "%INSTALL_DIR%" (
    git clone https://github.com/fraunhoferhhi/vvenc.git "%INSTALL_DIR%"
    cd /d "%INSTALL_DIR%"
    git checkout %VVENC_VERSION%
) else (
    cd /d "%INSTALL_DIR%"
)

echo [OK] VVenC repository ready
echo.

REM Build VVenC
echo Building VVenC...
if not exist build mkdir build
cd build

REM Detect Visual Studio version
where cl >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Setting up Visual Studio environment...
    call "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat"
)

REM Configure with CMake
cmake .. -G "Visual Studio 16 2019" -A x64 -DCMAKE_BUILD_TYPE=%BUILD_TYPE%
if %ERRORLEVEL% NEQ 0 (
    echo Error: CMake configuration failed
    echo Try: cmake .. -G "Visual Studio 17 2022" -A x64
    exit /b 1
)

REM Build
cmake --build . --config %BUILD_TYPE% --parallel
if %ERRORLEVEL% NEQ 0 (
    echo Error: Build failed
    exit /b 1
)

echo [OK] VVenC built successfully
echo.

REM Test installation
echo Testing VVenC installation...
set VVENC_BIN=%INSTALL_DIR%\build\bin\%BUILD_TYPE%\vvencapp.exe
set VVDEC_BIN=%INSTALL_DIR%\build\bin\%BUILD_TYPE%\vvdecapp.exe

if exist "%VVENC_BIN%" (
    echo [OK] vvencapp found: %VVENC_BIN%
    "%VVENC_BIN%" --version
) else (
    echo [ERROR] vvencapp not found
)

if exist "%VVDEC_BIN%" (
    echo [OK] vvdecapp found: %VVDEC_BIN%
    "%VVDEC_BIN%" --version
) else (
    echo [ERROR] vvdecapp not found
)

echo.
echo ==========================================
echo Installation Complete!
echo ==========================================
echo.
echo VVenC binaries location:
echo   Encoder: %VVENC_BIN%
echo   Decoder: %VVDEC_BIN%
echo.
echo Add to PATH:
echo   1. Open System Properties ^> Environment Variables
echo   2. Add to PATH: %INSTALL_DIR%\build\bin\%BUILD_TYPE%
echo.
echo Or run from this directory:
echo   %VVENC_BIN% --help
echo.

pause
