#!/bin/bash
# iNav 8.0 Build Script (Compatible with Configurator 8.0.1)

set -e

echo "=========================================="
echo "🚀 iNav 8.0 Setup & Build"
echo "=========================================="

# Step 1: Update system
echo ""
echo "📦 [1/6] Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Step 2: Install build tools
echo ""
echo "🔧 [2/6] Installing build tools..."
sudo apt install -y \
    git \
    build-essential \
    cmake \
    ninja-build \
    gcc-arm-none-eabi \
    python3 \
    python3-pip \
    wget \
    curl

# Step 3: Verify installations
echo ""
echo "✅ [3/6] Verifying installations..."
echo "  Git: $(git --version | head -n1)"
echo "  GCC: $(gcc --version | head -n1)"
echo "  ARM GCC: $(arm-none-eabi-gcc --version | head -n1)"
echo "  CMake: $(cmake --version | head -n1)"

# Step 4: Clone iNav
echo ""
echo "📥 [4/6] Cloning iNav 8.0 repository..."
mkdir -p ~/inav_workspace
cd ~/inav_workspace

if [ ! -d "inav" ]; then
    git clone https://github.com/iNavFlight/inav.git
    cd inav
    git checkout 8.0.1  # Latest stable 8.x
    git submodule update --init --recursive
else
    echo "  ℹ️  iNav already exists, switching to 8.0.1..."
    cd inav
    git fetch
    git checkout 8.0.1
    git submodule update --init --recursive
fi

# Step 5: Build firmware
echo ""
echo "🏗️  [5/6] Building firmware (this takes 2-5 minutes)..."
make clean
make TARGET=MATEKF722

# Step 6: Copy to Windows
echo ""
echo "📋 [6/6] Copying firmware to Windows..."
WINDOWS_PATH="/mnt/h/VSCode/Flying_Wing_UAV/firmware"
if [ -d "$WINDOWS_PATH" ]; then
    cp obj/inav_8.0.1_MATEKF722.hex "$WINDOWS_PATH/"
    echo "  ✓ Copied to: H:\\VSCode\\Flying_Wing_UAV\\firmware\\inav_8.0.1_MATEKF722.hex"
else
    echo "  ⚠️  Windows path not found, file location:"
    echo "  $(pwd)/obj/inav_8.0.1_MATEKF722.hex"
fi

# Summary
echo ""
echo "=========================================="
echo "✅ Build Complete!"
echo "=========================================="
echo ""
echo "📄 Firmware files:"
ls -lh obj/*.hex 2>/dev/null || echo "  (No .hex files found)"
echo ""
echo "📍 Build location:"
echo "  $(pwd)/obj/"
echo ""
echo "🎯 Compatible with:"
echo "  iNav Configurator 8.0.1 ✓"
echo ""
echo "🎯 Next steps:"
echo "  1. Open iNav Configurator 8.0.1"
echo "  2. Connect your flight controller via USB"
echo "  3. Flash the firmware .hex file"
echo "  4. Configure via CLI"
echo ""
echo "=========================================="
