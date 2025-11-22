#!/bin/bash
# Quick build script for iNav custom firmware
# Run this after setup_wsl.sh

set -e

echo "=========================================="
echo "iNav Firmware Builder"
echo "=========================================="

# Configuration
INAV_VERSION="7.1.2"
TARGET="MATEKF722"
WORKSPACE="$HOME/inav_workspace"

# Check if we're in the right directory
if [ ! -d "$WORKSPACE/inav" ]; then
    echo "iNav not found. Cloning repository..."
    cd $WORKSPACE
    git clone https://github.com/iNavFlight/inav.git
    cd inav
    git checkout $INAV_VERSION
    git submodule update --init --recursive
else
    cd $WORKSPACE/inav
    echo "Using existing iNav repository"
fi

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
make clean

# Build firmware
echo ""
echo "Building firmware for $TARGET..."
echo "This may take 2-5 minutes..."
make TARGET=$TARGET

# Check result
if [ -f "obj/inav_${INAV_VERSION}_${TARGET}.hex" ]; then
    echo ""
    echo "=========================================="
    echo "✓ Build successful!"
    echo "=========================================="
    echo ""
    echo "Firmware location:"
    echo "  $WORKSPACE/inav/obj/inav_${INAV_VERSION}_${TARGET}.hex"
    echo ""
    echo "File size:"
    ls -lh "obj/inav_${INAV_VERSION}_${TARGET}.hex" | awk '{print "  " $5}'
    echo ""
    echo "To copy to Windows:"
    echo "  cp obj/inav_${INAV_VERSION}_${TARGET}.hex /mnt/h/VSCode/Flying_Wing_UAV/firmware/"
    echo ""
    echo "=========================================="
else
    echo ""
    echo "✗ Build failed!"
    echo "Check output above for errors"
    exit 1
fi
