# Quay lại main branch
git checkout main

# Xóa branch rc-mode-switching (tùy chọn)
git branch -D rc-mode-switching

# Kiểm tra đang ở main branch
git branch# 🚀 Flying Wing UAV - Hướng Dẫn Cài Đặt

## 📋 Tổng Quan

Hệ thống Flying Wing UAV Companion Computer chạy trên **Raspberry Pi 3B+** với các tính năng:
- 🤖 AI Object Detection với TensorFlow Lite
- 🎮 RC-based Mode Switching từ RadioMaster
- 📡 MAVLink Communication với ArduPilot
- 📷 Camera OV5647 interface
- 🔬 Quantum Computing Research (Optional)

---

## 🛠️ Yêu Cầu Hệ Thống

### Phần Cứng
- **Raspberry Pi 3B+** (khuyến nghị) hoặc 4B
- **Pi Camera OV5647** (Camera Module)
- **Thẻ nhớ 16GB+** Class 10
- **Nguồn 5V 2.5A+** ổn định
- **Flight Controller**: LANRC F4 V3S Plus (ArduPilot)
- **Radio**: Radiomaster Pocket + XR1 Nano Receiver

### Phần Mềm
- **Raspberry Pi OS** (64-bit) khuyến nghị
- **Python 3.9+**
- **Git**

---

## 🚀 Cài Đặt Tự Động (Khuyến Nghị)

### Bước 1: Chuẩn Bị Hệ Thống
```bash
# Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y

# Cài đặt git nếu chưa có
sudo apt install -y git
```

### Bước 2: Clone Repository
```bash
git clone https://github.com/your-username/flying-wing-uav.git
cd flying-wing-uav
```

### Bước 3: Chạy Script Cài Đặt
```bash
# Cấp quyền thực thi
chmod +x install_rpi.sh

# Chạy script cài đặt
./install_rpi.sh
```

**Script sẽ tự động:**
- ✅ Cập nhật hệ thống
- ✅ Cài đặt system dependencies
- ✅ Bật camera interface
- ✅ Bật serial interface cho MAVLink
- ✅ Tạo Python virtual environment
- ✅ Cài đặt tất cả Python packages
- ✅ Tạo startup script

---

## 🔧 Cài Đặt Thủ Công

### Bước 1: Cài Đặt System Dependencies
```bash
sudo apt update
sudo apt install -y \
    python3-pip python3-venv python3-dev \
    build-essential cmake git \
    libatlas-base-dev libhdf5-dev \
    libopenblas-dev libjasper-dev \
    libqtgui4 libqt4-test \
    libavcodec-dev libavformat-dev \
    libswscale-dev libgtk-3-dev
```

### Bước 2: Bật Camera & Serial
```bash
# Bật camera interface
sudo raspi-config nonint do_camera 0

# Bật serial interface (disable console)
sudo raspi-config nonint do_serial 0

# Thêm vào /boot/config.txt
echo "start_x=1" | sudo tee -a /boot/config.txt
echo "gpu_mem=128" | sudo tee -a /boot/config.txt
```

### Bước 3: Tạo Virtual Environment
```bash
python3 -m venv uav_env
source uav_env/bin/activate
```

### Bước 4: Cài Đặt Python Packages
```bash
# Sử dụng requirements optimized
pip install -r requirements_rpi_optimized.txt

# Hoặc cài từng package
pip install numpy==1.21.6 opencv-python==4.5.5.64 Pillow==9.5.0
pip install pyyaml==6.0 loguru==0.7.2
pip install pymavlink==2.4.37 picamera2==0.3.7
pip install RPi.GPIO==0.7.1 smbus2==0.4.3
pip install tflite-runtime==2.13.0
```

---

## 🧪 Kiểm Tra Cài Đặt

### Test Camera
```bash
source uav_env/bin/activate
cd companion_computer
python -c "
from src.camera import CameraInterface
camera = CameraInterface()
if camera.start():
    frame = camera.read_frame()
    if frame is not None:
        print(f'✅ Camera working: {frame.shape}')
    else:
        print('❌ No frame received')
else:
    print('❌ Camera failed to start')
"
```

### Test AI Detection
```bash
python tests/test_rc_mode_system.py
```

### Test MAVLink
```bash
python -c "
from src.communication.mavlink_handler import MAVLinkHandler
mavlink = MAVLinkHandler(port='/dev/serial0', baudrate=921600)
if mavlink.connect():
    print('✅ MAVLink connected')
else:
    print('⚠️ MAVLink not connected (normal on test systems)')
"
```

---

## ⚙️ Cấu Hình Hệ Thống

### Camera Configuration
Chỉnh sửa `companion_computer/config/camera_config.yaml`:
```yaml
camera:
  resolution:
    width: 640    # Giảm từ 1920 để tiết kiệm CPU
    height: 480   # Giảm từ 1080
  framerate: 15   # Giảm từ 30
```

### AI Configuration
Chỉnh sửa `companion_computer/config/ai_config.yaml`:
```yaml
ai:
  model_path: "models/mobilenet_ssd_v1_0.75_192.tflite"  # Model nhẹ
  input_size: [192, 192]  # Input size nhỏ hơn
  num_threads: 2          # Tránh over-threading
```

### RC Mode Configuration
Chỉnh sửa `companion_computer/config/rc_mode_config.yaml` để mapping switches.

---

## 🎮 Cấu Hình RadioMaster

### Channel Mapping trên RadioMaster Pocket:
| Switch | Channel | Chức Năng |
|--------|---------|-----------|
| SWA | CH5 (AUX1) | Primary AI Mission Mode |
| SWB | CH6 (AUX2) | AI Sub-mode |
| SWC | CH7 (AUX3) | Detection Frequency |
| SWD | CH8 (AUX4) | Emergency Override |

### Model Setup:
1. Tạo model mới "FlyingWing_AI"
2. Map switches đến các channels tương ứng
3. Test PWM output: 1000=DOWN, 1500=MIDDLE, 2000=UP

---

## 🚀 Khởi Chạy Hệ Thống

### Manual Start
```bash
cd flying-wing-uav
source uav_env/bin/activate
cd companion_computer
python src/main.py
```

### Auto-start với Systemd
```bash
# Enable service
sudo systemctl enable flying-wing-uav.service

# Start service
sudo systemctl start flying-wing-uav

# Check status
sudo systemctl status flying-wing-uav

# View logs
sudo journalctl -u flying-wing-uav -f
```

---

## 🔧 Troubleshooting

### Lỗi Camera
```bash
# Test camera hardware
libcamera-hello --list-cameras

# Check camera enabled
vcgencmd get_camera
```

### Lỗi Memory
```bash
# Tăng swap space
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Lỗi TensorFlow Lite
```bash
# Thử cài đặt từ wheel
pip install https://github.com/google-coral/pycoral/releases/download/v2.0.0/tflite_runtime-2.5.0-cp39-cp39-linux_armv7l.whl
```

### Lỗi MAVLink
```bash
# Check serial device
ls -la /dev/serial*

# Test serial communication
sudo stty -F /dev/serial0 921600
```

---

## 📊 Performance Optimization

### Cho Raspberry Pi 3B+:
- **Camera**: 640x480 @ 15fps
- **AI Model**: MobileNet SSD nhẹ
- **Detection Interval**: 5-15 frames
- **CPU Governor**: performance
- **Memory**: Đủ swap space

### Monitoring:
```bash
# CPU usage
top

# Memory usage
free -h

# Temperature
vcgencmd measure_temp

# GPU memory
vcgencmd get_mem gpu
```

---

## 🆘 Hỗ Trợ

### Log Files
- Ứng dụng logs: `companion_computer/logs/`
- System logs: `sudo journalctl -u flying-wing-uav`
- Camera logs: Kiểm tra `dmesg | grep camera`

### Common Issues
1. **Camera không hoạt động**: Kiểm tra `raspi-config` và cable
2. **MAVLink timeout**: Kiểm tra baudrate và cable
3. **High CPU usage**: Giảm camera resolution và detection frequency
4. **Memory errors**: Tăng swap space

### Debug Mode
```bash
python src/main.py --debug
```

---

## 🎉 Kết Thúc

Sau khi cài đặt thành công, hệ thống sẽ:
- ✅ Tự động khởi động với Raspberry Pi
- ✅ Nhận RC commands từ RadioMaster
- ✅ Xử lý AI detection với mode switching
- ✅ Giao tiếp với Flight Controller qua MAVLink
- ✅ Log dữ liệu flight và detections

**Chúc bạn flight test thành công!** 🚀