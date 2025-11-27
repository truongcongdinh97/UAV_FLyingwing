# Deployment Guide - Raspberry Pi

Hướng dẫn deploy code lên Raspberry Pi 3B+

## 1. Chuẩn Bị Raspberry Pi

### Flash OS
```bash
# Download Raspberry Pi OS Lite (64-bit)
# Flash lên SD card bằng Raspberry Pi Imager
```

### Setup SSH & WiFi
```bash
# Enable SSH: tạo file 'ssh' trong boot partition
touch /boot/ssh

# Setup WiFi: tạo file wpa_supplicant.conf
cat > /boot/wpa_supplicant.conf << EOF
country=VN
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YOUR_WIFI_SSID"
    psk="YOUR_WIFI_PASSWORD"
}
EOF
```

### First Boot
```bash
# SSH vào Pi (default password: raspberry)
ssh pi@raspberrypi.local

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Change password
passwd
```

## 2. Install Dependencies

```bash
# Python & pip
sudo apt-get install -y python3-pip python3-dev

# System packages
sudo apt-get install -y \
    python3-opencv \
    libatlas-base-dev \
    libopenjp2-7 \
    libtiff5 \
    libhdf5-dev \
    libharfbuzz0b \
    libwebp6

# Camera
sudo apt-get install -y python3-picamera2

# Serial
sudo apt-get install -y python3-serial
```

## 3. Enable Hardware

### Camera Interface
```bash
sudo raspi-config
# Interface Options -> Camera -> Enable
```

### UART/Serial
```bash
# Edit config
sudo nano /boot/config.txt
# Add these lines:
enable_uart=1
dtoverlay=disable-bt

# Disable serial console
sudo systemctl stop serial-getty@ttyAMA0.service
sudo systemctl disable serial-getty@ttyAMA0.service

# Reboot
sudo reboot
```

## 4. Transfer Code

### From Windows to Pi

```powershell
# Using SCP (trong PowerShell)
scp -r H:\VSCode\Flying_Wing_UAV\companion_computer pi@raspberrypi.local:~/
```

Hoặc:

```powershell
# Using rsync (nếu có)
rsync -avz --exclude='__pycache__' `
    H:\VSCode\Flying_Wing_UAV\companion_computer `
    pi@raspberrypi.local:~/
```

## 5. Install Python Packages

```bash
# On Raspberry Pi
cd ~/companion_computer
pip3 install -r requirements.txt

# TensorFlow Lite (ARM-specific)
pip3 install --extra-index-url https://google-coral.github.io/py-repo/ tflite-runtime
```

## 6. Download AI Model

```bash
cd ~/companion_computer/models

# Download MobileNet SSD
wget https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
unzip coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
mv detect.tflite mobilenet_ssd_v2.tflite
rm coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
```

## 7. Test Modules

```bash
# Test camera
python3 src/camera/camera_interface.py

# Test AI (nếu có model)
python3 src/ai/object_detector.py

# Test serial (cần kết nối FC)
python3 src/communication/serial_comm.py

# Test logger
python3 src/logging/data_logger.py
```

## 8. Run Main Application

```bash
# Run manually
cd ~/companion_computer
python3 src/main.py

# Run with debug
python3 src/main.py --debug

# Run with custom config
python3 src/main.py --config config/system_config.yaml
```

## 9. Auto-start on Boot (Optional)

```bash
# Create systemd service
sudo nano /etc/systemd/system/uav-companion.service
```

```ini
[Unit]
Description=Flying Wing UAV Companion Computer
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/companion_computer
ExecStart=/usr/bin/python3 /home/pi/companion_computer/src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable service
sudo systemctl enable uav-companion.service
sudo systemctl start uav-companion.service

# Check status
sudo systemctl status uav-companion.service

# View logs
sudo journalctl -u uav-companion.service -f
```

## 10. Monitoring

```bash
# CPU temperature
vcgencmd measure_temp

# CPU usage
htop

# View application logs
tail -f ~/companion_computer/logs/*/system.log
```

## Troubleshooting

### Camera không hoạt động
```bash
# Check camera
vcgencmd get_camera
# Should show: supported=1 detected=1

# Test with libcamera
libcamera-hello
```

### Serial không connect
```bash
# Check UART
ls -l /dev/serial*
# Should show /dev/serial0

# Test với minicom
sudo minicom -D /dev/serial0 -b 115200
```

### Out of memory
```bash
# Increase swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```
