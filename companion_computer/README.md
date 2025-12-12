# Raspberry Pi Companion Computer

Code chạy trên Raspberry Pi 3B+ để xử lý AI tại biên, điều khiển camera, và giao tiếp với Flight Controller.

## Tính Năng

### 1. Camera Interface (OV5647)
- Video capture & streaming
- Image processing pipeline
- Resolution & frame rate control

### 2. AI Object Detection
- Edge computing với TensorFlow Lite
- Real-time object detection
- Bounding box & classification

### 3. Communication
- UART/Serial với Flight Controller (iNav)
- MAVLink protocol support
- 5G/WiFi streaming

### 4. Data Logging
- GPS data với timestamp
- Flight telemetry
- Image/video recording
- Black box functionality

## Cấu Trúc

```
companion_computer/
├── src/
│   ├── camera/           # Camera interface & processing
│   ├── ai/              # AI models & inference
│   ├── communication/   # Serial/UART với FC
│   ├── networking/      # 5G/WiFi streaming
│   ├── logging/         # Data logging
│   └── main.py          # Main application
├── config/
│   ├── camera_config.yaml
│   ├── ai_config.yaml
│   └── system_config.yaml
├── models/              # AI models (TFLite)
├── logs/                # Log files
└── requirements.txt     # Python dependencies
```

## Setup

### Trên Raspberry Pi:

```bash
# 1. Update system
sudo apt-get update
sudo apt-get upgrade -y

# 2. Install system dependencies
sudo apt-get install -y python3-pip python3-opencv
sudo apt-get install -y libatlas-base-dev libopenjp2-7
sudo apt-get install -y python3-picamera2

# 3. Install Python packages
cd companion_computer
pip3 install -r requirements.txt

# 4. Enable camera
sudo raspi-config
# Enable Camera Interface

# 5. Enable UART
# Edit /boot/config.txt, add:
# enable_uart=1
# dtoverlay=disable-bt
```

### Trên VS Code (Development):

```bash
# Install dependencies locally cho development
pip install -r requirements.txt
```

## Usage

```bash
# Run main application
python3 src/main.py

# Run với config tùy chỉnh
python3 src/main.py --config config/system_config.yaml

# Test camera
python3 src/camera/test_camera.py

# Test AI detection
python3 src/ai/test_detection.py
```

## Configuration

Các file cấu hình trong `config/`:
- `camera_config.yaml`: Cài đặt camera (resolution, FPS, etc.)
- `ai_config.yaml`: Model settings, confidence threshold
- `system_config.yaml`: System-wide settings

## Development on Windows

Bạn có thể develop code trên Windows và test logic, sau đó deploy lên Pi:

```powershell
# Test các module (không cần camera thật)
python src/communication/test_serial.py
python src/logging/test_logger.py
```
