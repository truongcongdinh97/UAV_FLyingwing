#!/bin/bash

# Flying Wing UAV - Raspberry Pi Installation Script
# Tự động cài đặt dependencies và setup system

set -e  # Exit on error

echo "=================================================="
echo "🚀 Flying Wing UAV - Raspberry Pi Installation"
echo "=================================================="

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠️  Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# System information
echo "📋 System Information:"
echo "    Model: $(cat /proc/device-tree/model 2>/dev/null || echo 'Unknown')"
echo "    Architecture: $(uname -m)"
echo "    OS: $(lsb_release -d | cut -f2)"

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "    Python: $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" < "3.7" ]]; then
    echo "❌ Python 3.7+ required. Current: $PYTHON_VERSION"
    exit 1
fi

# Update system
echo ""
echo "🔄 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    cmake \
    git \
    libatlas-base-dev \
    libhdf5-dev \
    libhdf5-serial-dev \
    libjasper-dev \
    libqtgui4 \
    libqt4-test \
    libopenblas-dev \
    libopenmpi-dev \
    libtiff5 \
    libjpeg-dev \
    libpng-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libgtk-3-dev \
    libcanberra-gtk* \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libx264-dev \
    libx265-dev \
    libv4l-dev \
    v4l-utils

# Enable camera interface
echo ""
echo "📷 Enabling camera interface..."
if ! grep -q "start_x=1" /boot/config.txt; then
    echo "start_x=1" | sudo tee -a /boot/config.txt
fi
if ! grep -q "gpu_mem=128" /boot/config.txt; then
    echo "gpu_mem=128" | sudo tee -a /boot/config.txt
fi

# Enable serial interface for MAVLink
echo ""
echo "🔌 Enabling serial interface..."
sudo raspi-config nonint do_serial 0  # Enable serial, disable console

# Increase swap space for compilation
echo ""
echo "💾 Configuring swap space..."
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Create virtual environment
echo ""
echo "🐍 Creating Python virtual environment..."
python3 -m venv uav_env
source uav_env/bin/activate

# Upgrade pip
echo ""
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install Python packages
echo ""
echo "📚 Installing Python packages..."

# Install base packages first
pip install numpy==1.21.6
pip install opencv-python==4.5.5.64
pip install Pillow==9.5.0
pip install pyyaml==6.0
pip install loguru==0.7.2

# Install MAVLink and hardware packages
pip install pymavlink==2.4.37
pip install picamera2==0.3.7
pip install RPi.GPIO==0.7.1
pip install smbus2==0.4.3

# Install TensorFlow Lite runtime
# Try multiple sources for compatibility
echo ""
echo "🤖 Installing TensorFlow Lite runtime..."

# Method 1: Try official package
if pip install tflite-runtime==2.13.0; then
    echo "✅ TensorFlow Lite installed from PyPI"
else
    echo "⚠️  Falling back to alternative installation..."
    # Method 2: Try pre-built wheel for armv7l
    ARCH=$(uname -m)
    if [[ "$ARCH" == "armv7l" ]]; then
        wget -q https://github.com/google-coral/pycoral/releases/download/v2.0.0/tflite_runtime-2.5.0-cp39-cp39-linux_armv7l.whl
        pip install tflite_runtime-2.5.0-cp39-cp39-linux_armv7l.whl
        rm tflite_runtime-2.5.0-cp39-cp39-linux_armv7l.whl
        echo "✅ TensorFlow Lite installed from pre-built wheel"
    else
        echo "❌ Could not install TensorFlow Lite for architecture: $ARCH"
        echo "   Manual installation required"
    fi
fi

# Install optional packages for development
read -p "Install development packages? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔧 Installing development packages..."
    pip install pytest==7.4.3
    pip install matplotlib==3.7.2
    pip install jupyter==1.0.0
    pip install pandas==2.0.3
fi

# Install quantum packages (optional)
read -p "Install quantum computing packages? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔮 Installing quantum computing packages..."
    pip install qiskit==0.44.1
    pip install qiskit-aer==0.12.2
    pip install qiskit-machine-learning==0.6.0
fi

# Create startup script
echo ""
echo "🚀 Creating startup script..."
cat > start_uav.sh << 'EOF'
#!/bin/bash
# Flying Wing UAV Startup Script

# Activate virtual environment
source $(dirname "$0")/uav_env/bin/activate

# Start companion computer
cd $(dirname "$0")/companion_computer
python src/main.py

EOF

chmod +x start_uav.sh

# Create systemd service (optional)
read -p "Create systemd service for auto-start? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "⚙️ Creating systemd service..."
    
    SERVICE_FILE="/etc/systemd/system/flying-wing-uav.service"
    
    sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=Flying Wing UAV Companion Computer
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)/companion_computer
ExecStart=$(pwd)/uav_env/bin/python src/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable flying-wing-uav.service
    
    echo "✅ Systemd service created and enabled"
    echo "   Start: sudo systemctl start flying-wing-uav"
    echo "   Status: sudo systemctl status flying-wing-uav"
    echo "   Logs: sudo journalctl -u flying-wing-uav -f"
fi

# Final instructions
echo ""
echo "=================================================="
echo "🎉 Installation Completed Successfully!"
echo "=================================================="
echo ""
echo "📝 Next Steps:"
echo "   1. Reboot to enable camera and serial: sudo reboot"
echo "   2. Test camera: libcamera-hello --list-cameras"
echo "   3. Start UAV system: ./start_uav.sh"
echo "   4. Check MAVLink connection"
echo ""
echo "🔧 Useful Commands:"
echo "   • Activate environment: source uav_env/bin/activate"
echo "   • Test installation: python tests/test_rc_mode_system.py"
echo "   • Check camera: python -c 'from src.camera import CameraInterface; c = CameraInterface(); c.start(); print(c.read_frame().shape if c.read_frame() else "No frame")'"
echo ""
echo "📞 Support:"
echo "   • Check logs in: companion_computer/logs/"
echo "   • Configuration: companion_computer/config/"
echo ""

# Test basic functionality
echo "🧪 Running basic tests..."
source uav_env/bin/activate
cd companion_computer
python -c "
import sys
sys.path.append('src')
try:
    import numpy as np
    import cv2
    import yaml
    from loguru import logger
    print('✅ Basic imports successful')
    
    # Test OpenCV
    test_img = np.zeros((100, 100, 3), dtype=np.uint8)
    print(f'✅ OpenCV test: {test_img.shape}')
    
    # Test configuration
    import os
    if os.path.exists('config/system_config.yaml'):
        with open('config/system_config.yaml') as f:
            config = yaml.safe_load(f)
        print('✅ Configuration test successful')
    
    print('🎉 All basic tests passed!')
    
except Exception as e:
    print(f'❌ Test failed: {e}')
    sys.exit(1)
"

echo ""
echo "🚀 Ready for Flying Wing UAV operations!"

# Display resource usage
echo ""
echo "📊 Resource Usage:"
echo "   RAM: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "   Storage: $(df -h / | grep / | awk '{print $3 "/" $2 " (" $5 ")"})')"