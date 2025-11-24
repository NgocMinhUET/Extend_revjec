#!/bin/bash
# VVenC Installation Script
# Installs VVenC encoder and decoder for the project

set -e  # Exit on error

echo "=========================================="
echo "VVenC Installation Script"
echo "=========================================="
echo ""

# Configuration
VVENC_VERSION="v1.11.1"
INSTALL_DIR="${HOME}/vvenc"
BUILD_TYPE="Release"

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="Windows"
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

echo "Detected OS: $OS"
echo "VVenC Version: $VVENC_VERSION"
echo "Install Directory: $INSTALL_DIR"
echo ""

# Check dependencies
echo "Checking dependencies..."

if ! command -v git &> /dev/null; then
    echo "Error: git is not installed"
    exit 1
fi

if ! command -v cmake &> /dev/null; then
    echo "Error: cmake is not installed"
    exit 1
fi

if [[ "$OS" == "Linux" ]]; then
    if ! command -v g++ &> /dev/null; then
        echo "Error: g++ is not installed"
        echo "Install with: sudo apt-get install build-essential"
        exit 1
    fi
fi

echo "✓ All dependencies found"
echo ""

# Clone VVenC
echo "Cloning VVenC repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory $INSTALL_DIR already exists"
    read -p "Remove and re-clone? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        echo "Using existing directory"
    fi
fi

if [ ! -d "$INSTALL_DIR" ]; then
    git clone https://github.com/fraunhoferhhi/vvenc.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    git checkout "$VVENC_VERSION"
else
    cd "$INSTALL_DIR"
fi

echo "✓ VVenC repository ready"
echo ""

# Build VVenC
echo "Building VVenC..."
mkdir -p build
cd build

if [[ "$OS" == "Windows" ]]; then
    # Windows build with Visual Studio
    cmake .. -G "Visual Studio 16 2019" -A x64 -DCMAKE_BUILD_TYPE=$BUILD_TYPE
    cmake --build . --config $BUILD_TYPE --parallel
else
    # Linux/macOS build
    cmake .. -DCMAKE_BUILD_TYPE=$BUILD_TYPE
    make -j$(nproc)
fi

echo "✓ VVenC built successfully"
echo ""

# Install (optional)
echo "Installing VVenC..."
if [[ "$OS" == "Linux" || "$OS" == "macOS" ]]; then
    read -p "Install system-wide? (requires sudo) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo make install
        echo "✓ VVenC installed system-wide"
    else
        echo "Skipping system-wide installation"
    fi
fi

# Test installation
echo ""
echo "Testing VVenC installation..."
if [[ "$OS" == "Windows" ]]; then
    VVENC_BIN="$INSTALL_DIR/build/bin/Release/vvencapp.exe"
    VVDEC_BIN="$INSTALL_DIR/build/bin/Release/vvdecapp.exe"
else
    VVENC_BIN="$INSTALL_DIR/build/bin/release-static/vvencapp"
    VVDEC_BIN="$INSTALL_DIR/build/bin/release-static/vvdecapp"
fi

if [ -f "$VVENC_BIN" ]; then
    echo "✓ vvencapp found: $VVENC_BIN"
    $VVENC_BIN --version
else
    echo "✗ vvencapp not found"
fi

if [ -f "$VVDEC_BIN" ]; then
    echo "✓ vvdecapp found: $VVDEC_BIN"
    $VVDEC_BIN --version
else
    echo "✗ vvdecapp not found"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "VVenC binaries location:"
echo "  Encoder: $VVENC_BIN"
echo "  Decoder: $VVDEC_BIN"
echo ""
echo "Add to PATH (add to ~/.bashrc or ~/.zshrc):"
if [[ "$OS" == "Windows" ]]; then
    echo "  set PATH=%PATH%;$INSTALL_DIR\\build\\bin\\Release"
else
    echo "  export PATH=\$PATH:$INSTALL_DIR/build/bin/release-static"
fi
echo ""
echo "Or create symbolic links:"
echo "  sudo ln -s $VVENC_BIN /usr/local/bin/vvencapp"
echo "  sudo ln -s $VVDEC_BIN /usr/local/bin/vvdecapp"
echo ""
