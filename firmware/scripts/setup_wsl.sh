#!/bin/bash
# iNav Build Environment Setup Script
# Run this in WSL Ubuntu after installation

set -e  # Exit on error

echo "=========================================="
echo "iNav Firmware Build Environment Setup"
echo "=========================================="

# Update system
echo ""
echo "[1/5] Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install build tools
echo ""
echo "[2/5] Installing build tools..."
sudo apt install -y \
    git \
    build-essential \
    cmake \
    ninja-build \
    python3 \
    python3-pip

# Install ARM toolchain
echo ""
echo "[3/5] Installing ARM GCC toolchain..."
sudo apt install -y gcc-arm-none-eabi

# Verify installation
echo ""
echo "[4/5] Verifying installations..."
echo "Git version:"
git --version

echo ""
echo "GCC version:"
gcc --version | head -n1

echo ""
echo "ARM GCC version:"
arm-none-eabi-gcc --version | head -n1

echo ""
echo "CMake version:"
cmake --version | head -n1

# Create workspace directory
echo ""
echo "[5/5] Creating workspace..."
mkdir -p ~/inav_workspace
cd ~/inav_workspace

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. cd ~/inav_workspace"
echo "2. git clone https://github.com/iNavFlight/inav.git"
echo "3. cd inav"
echo "4. git checkout 7.1.2"
echo "5. make TARGET=MATEKF722"
echo ""
echo "Workspace location: ~/inav_workspace"
echo "=========================================="
