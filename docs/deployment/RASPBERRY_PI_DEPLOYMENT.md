# Raspberry Pi Deployment Guide

Hướng dẫn deploy companion computer code lên Raspberry Pi 3B+

---

## Prerequisites

### Hardware
- ✅ Raspberry Pi 3B+ with SD card (16GB+)
- ✅ Raspberry Pi Camera Module (OV5647)
- ✅ USB cable để connect FC
- ✅ Power supply 5V/3A
- ✅ WiFi/Ethernet connection

### Software
- Raspberry Pi OS Lite (64-bit recommended)
- Python 3.9+

---

## Step 1: Setup Raspberry Pi OS

### Flash OS
```bash
# Download Raspberry Pi Imager
# https://www.raspberrypi.com/software/

# Flash: Raspberry Pi OS Lite (64-bit)
# Enable SSH trong advanced settings
# Set hostname: uav-companion
# Set username/password
```

### First Boot
```bash
# SSH vào Pi
ssh pi@uav-companion.local
# Or: ssh pi@<IP_ADDRESS>

# Update system
sudo apt update
sudo apt upgrade -y

# Install essentials
sudo apt install -y git python3-pip python3-venv
```

---

## Step 2: Install Dependencies

### System packages
```bash
# Camera support
sudo apt install -y python3-picamera2 libcamera-dev

# OpenCV dependencies
sudo apt install -y python3-opencv

# Serial communication
sudo apt install -y python3-serial

# Optional: TensorFlow Lite
wget https://github.com/PINTO0309/TensorflowLite-bin/releases/download/v2.14.0/tflite_runtime-2.14.0-py39-none-linux_aarch64.whl
pip3 install tflite_runtime-2.14.0-py39-none-linux_aarch64.whl
```

### Python packages
```bash
# Create virtual environment
python3 -m venv ~/uav_env
source ~/uav_env/bin/activate

# Install requirements
pip install --upgrade pip
pip install numpy opencv-python PyYAML loguru pyserial pymavlink
```

---

## Step 3: Copy Project Files

### From Windows to Pi

**Method A: Using SCP (from Windows PowerShell)**
```powershell
# Copy entire companion_computer directory
scp -r H:\VSCode\Flying_Wing_UAV\companion_computer pi@uav-companion.local:~/
```

**Method B: Using Git**
```bash
# On Pi
cd ~
git clone <your_repo_url>
cd Flying_Wing_UAV/companion_computer
```

**Method C: Manual (USB drive)**
```bash
# Copy files to USB
# Plug USB to Pi
sudo mount /dev/sda1 /mnt
cp -r /mnt/companion_computer ~/
sudo umount /mnt
```

---

## Step 4: Configure Hardware

### Enable Camera
```bash
# Edit config
sudo nano /boot/firmware/config.txt

# Add lines:
camera_auto_detect=1
dtoverlay=ov5647

# Reboot
sudo reboot
```

### Enable Serial (for FC communication)
```bash
# Disable serial console
sudo raspi-config
# Interface Options → Serial Port
# - "Login shell over serial?" → No
# - "Serial port hardware enabled?" → Yes

# Or edit directly:
sudo nano /boot/firmware/cmdline.txt
# Remove: console=serial0,115200

# Edit config
sudo nano /boot/firmware/config.txt
# Add:
enable_uart=1
```

### Test Camera
```bash
# Test with libcamera
libcamera-hello --list-cameras
libcamera-jpeg -o test.jpg

# Test with Python
python3 -c "from picamera2 import Picamera2; cam = Picamera2(); print('Camera OK')"
```

### Test Serial
```bash
# List serial devices
ls -l /dev/serial*
ls -l /dev/ttyAMA* /dev/ttyUSB*

# Should see: /dev/serial0 or /dev/ttyAMA0

# Test with screen
sudo apt install screen
sudo screen /dev/serial0 115200
# Should see MAVLink telemetry when FC connected
```

---

## Step 5: Configure Application

### Edit config files
```bash
cd ~/companion_computer

# Camera config
nano config/camera_config.yaml
# Set: camera_type: "picamera"

# System config
nano config/system_config.yaml
# Set: serial_port: "/dev/serial0"
```

### Test modules individually
```bash
source ~/uav_env/bin/activate
cd ~/companion_computer

# Test camera
python3 src/camera/camera_interface.py

# Test logging
python3 src/data_logging/data_logger.py

# Test serial (with FC connected)
python3 src/communication/serial_comm.py
```

---

## Step 6: Configure System for Parallel Processing

### System Architecture Notes

The companion computer uses a **3-thread parallel architecture**:
1. **Thread 1**: Camera capture + telemetry snapshot (real-time)
2. **Thread 2**: AI detection + geolocation calculation (heavy processing)
3. **Thread 3**: HTTP upload to ground station (network I/O)

**Key Features**:
- Queue-based communication between threads (no blocking)
- Watchdog timer for automatic recovery
- Performance monitoring (FPS & RAM)
- Frame dropping strategy for real-time operation

### Camera Optimization

The camera is configured for optimal UAV reconnaissance:
- **Shutter speed**: >1/1000s (reduced motion blur)
- **ISO**: Automatic gain control
- **Frame synchronization**: Timestamp captured with frame

These settings are automatically applied in `camera_interface.py`.

### Watchdog Configuration

Default watchdog timeout: **60 seconds**

To adjust timeout, edit `config/system_config.yaml`:
```yaml
watchdog:
  timeout_seconds: 60  # Increase for slower systems
```

If any thread hangs for >60s, system will automatically reset.

---

## Step 7: Run Application

### Manual run
```bash
source ~/uav_env/bin/activate
cd ~/companion_computer
python3 src/main.py
```

**You should see**:
- `[INFO] Camera thread started`
- `[INFO] AI thread started`
- `[INFO] Upload thread started`
- `[INFO] Watchdog timer started (60s timeout)`
- `[INFO] FPS: X.X | RAM: XX.X MB`

### Create systemd service (auto-start on boot)
```bash
# Create service file
sudo nano /etc/systemd/system/uav-companion.service
```

**Service file content:**
```ini
[Unit]
Description=UAV Companion Computer
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/companion_computer
Environment="PATH=/home/pi/uav_env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/pi/uav_env/bin/python3 /home/pi/companion_computer/src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable service:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable uav-companion.service

# Start service
sudo systemctl start uav-companion.service

# Check status
sudo systemctl status uav-companion.service

# View logs
sudo journalctl -u uav-companion.service -f
```

---

## Step 7: Network Setup

### WiFi AP Mode (optional - for direct connection)
```bash
# Install hostapd and dnsmasq
sudo apt install -y hostapd dnsmasq

# Configure access point
sudo nano /etc/hostapd/hostapd.conf
```

**hostapd.conf:**
```ini
interface=wlan0
driver=nl80211
ssid=UAV-Companion
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=uav12345
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
```

**Or use 4G module** (recommended for long range)

---

## Step 8: Video Streaming Setup

### Install RTSP server
```bash
# Install v4l2rtspserver
cd ~
git clone https://github.com/mpromonet/v4l2rtspserver.git
cd v4l2rtspserver
cmake . && make
sudo make install

# Run RTSP server
v4l2rtspserver -W 640 -H 480 -F 30 /dev/video0
# Stream available at: rtsp://Pi_IP:8554/unicast
```

### Add to systemd
```bash
sudo nano /etc/systemd/system/rtsp-server.service
```

```ini
[Unit]
Description=RTSP Video Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/v4l2rtspserver -W 640 -H 480 -F 30 /dev/video0
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable rtsp-server.service
sudo systemctl start rtsp-server.service
```

---

## Troubleshooting

### Camera not detected
```bash
vcgencmd get_camera
# Should return: supported=1 detected=1

# Check ribbon cable connection
# Try different camera_auto_detect settings
```

### Serial permission denied
```bash
# Add user to dialout group
sudo usermod -a -G dialout pi
sudo reboot
```

### High CPU usage
```bash
# Check performance metrics in logs
# Look for: [INFO] FPS: X.X | RAM: XX.X MB

# Reduce camera resolution in config/system_config.yaml
# The parallel pipeline should keep CPU manageable

# If one thread is slow, others continue (non-blocking design)
```

### Thread hangs / System not responding
```bash
# Check watchdog logs
journalctl -u uav-companion.service | grep "Watchdog"

# Watchdog should show periodic "kick" messages
# If watchdog triggered reset, you'll see: "CRITICAL: Watchdog timeout! Resetting system"

# Adjust timeout if needed in config/system_config.yaml
```

### Queue overflows
```bash
# Check logs for queue warnings
journalctl -u uav-companion.service | grep "queue"

# Symptoms:
#   - "Frame queue full, dropping old frame" (normal, by design)
#   - "Upload queue full" (network too slow)

# Solutions:
#   - Frame drops are intentional (real-time design)
#   - If upload queue full, check ground station connectivity
```

### No video stream
```bash
# Check camera working
libcamera-hello

# Check RTSP server running
sudo systemctl status rtsp-server

# Check firewall
sudo ufw allow 8554
```

### AI detection slow
```bash
# Check AI thread performance
journalctl -u uav-companion.service | grep "AI"

# AdaptiveDetector automatically switches between:
#   - Full detection (slower, more accurate)
#   - Tracking mode (faster, follows known target)

# If still slow, consider:
#   - Lower camera resolution
#   - Use lighter TFLite model
#   - Increase AI skip rate in config
```

---

## Performance Optimization

### Overclock (optional)
```bash
sudo nano /boot/firmware/config.txt

# Add:
over_voltage=2
arm_freq=1400
gpu_freq=500
```

### Disable unnecessary services
```bash
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
```

---

## Next Steps

1. ✅ Deploy code to Pi
2. ✅ Connect FC via UART
3. ✅ Test MAVLink communication
4. ✅ Test camera stream
5. ✅ Ground station connection
6. 🚁 Flight test!

---

## Quick Commands Reference

```bash
# Start companion
sudo systemctl start uav-companion

# Stop companion
sudo systemctl stop uav-companion

# View logs
sudo journalctl -u uav-companion -f

# Restart all
sudo systemctl restart uav-companion
sudo systemctl restart rtsp-server

# Check status
sudo systemctl status uav-companion
sudo systemctl status rtsp-server
```
