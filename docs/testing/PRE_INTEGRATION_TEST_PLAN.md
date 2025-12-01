# Pre-Integration Test Plan
## Flying Wing UAV - Component Testing Before System Integration

**Document Date**: 2025-11-28  
**Version**: 1.0  
**Purpose**: Hướng dẫn test từng thành phần trước khi ghép thành hệ thống hoàn chỉnh

---

## 📋 Tổng Quan

Trước khi tích hợp toàn bộ hệ thống, mỗi module cần được test riêng lẻ theo 2 cách:
- **🖥️ Mô phỏng (Simulation)**: Test trên Windows/Linux không cần hardware
- **🔧 Thực tế (Hardware)**: Test trên Raspberry Pi với thiết bị thật

### Test Flow
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Unit Test      │ → │  Module Test    │ → │  Integration    │
│  (Mô phỏng)     │    │  (Hardware)     │    │  Test           │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🔹 Module 1: Camera Interface

### File: `companion_computer/src/camera/camera_interface.py`

| Test | Mô phỏng | Thực tế | Cách Test |
|------|----------|---------|-----------|
| Import module | ✅ | ✅ | `python -c "from camera import CameraInterface"` |
| OpenCV fallback | ✅ | ❌ | Chạy trên Windows với webcam |
| Picamera2 init | ❌ | ✅ | Chỉ trên Raspberry Pi |
| Shutter speed config | ❌ | ✅ | Cần Pi Camera hardware |
| Frame timestamp sync | ✅ | ✅ | `camera.read_frame()` returns (frame, timestamp) |
| Frame rate (FPS) | ✅ | ✅ | Đo thời gian 100 frames |

### Test Mô Phỏng (Windows)
```bash
cd companion_computer
python -c "
from src.camera.camera_interface import CameraInterface
cam = CameraInterface()
cam.start()
for i in range(10):
    frame, ts = cam.read_frame()
    print(f'Frame {i}: shape={frame.shape}, timestamp={ts}')
cam.stop()
"
```

### Test Thực Tế (Raspberry Pi)
```bash
# SSH vào Pi
cd ~/companion_computer
python3 -c "
from src.camera.camera_interface import CameraInterface
cam = CameraInterface()
cam.start()

# Check camera config
print('Camera type:', cam.camera_type)
print('Shutter speed configured')

# Capture test frames
import time
start = time.time()
for i in range(100):
    frame, ts = cam.read_frame()
elapsed = time.time() - start
print(f'FPS: {100/elapsed:.1f}')

cam.stop()
"
```

### ✅ Pass Criteria
- [ ] Frame shape: (480, 640, 3) hoặc configured resolution
- [ ] Timestamp: Monotonic increasing
- [ ] FPS: >15 fps trên Pi
- [ ] No memory leaks sau 1000 frames

---

## 🔹 Module 2: AI Object Detector

### Files:
- `companion_computer/src/ai/object_detector.py`
- `companion_computer/src/ai/adaptive_detector.py`

| Test | Mô phỏng | Thực tế | Cách Test |
|------|----------|---------|-----------|
| TFLite model load | ⚠️ (mock) | ✅ | Cần model file |
| Detection output format | ✅ | ✅ | Check bbox, confidence, class_id |
| Adaptive mode switching | ✅ | ✅ | Mock RC channels |
| Detection FPS | ✅ | ✅ | Đo thời gian inference |
| Memory bounded deque | ✅ | ✅ | Check detection_times.maxlen |

### Test Mô Phỏng (Windows)
```bash
cd companion_computer
python src/ai/object_detector.py
# Sẽ chạy với mock mode nếu không có model
```

### Test Thực Tế (Raspberry Pi)
```bash
cd ~/companion_computer

# Download model nếu chưa có
mkdir -p models
wget -O models/mobilenet_ssd_v2.tflite \
  https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip

# Test detector
python3 -c "
from src.ai.object_detector import ObjectDetector
import numpy as np

detector = ObjectDetector()

# Create test image
test_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

# Run detection
import time
start = time.time()
for i in range(10):
    results = detector.detect(test_img)
elapsed = time.time() - start
print(f'Inference time: {elapsed/10*1000:.1f}ms per frame')
print(f'Detection FPS: {10/elapsed:.1f}')
"
```

### Test Adaptive Detector
```bash
python3 tests/test_rc_mode_system.py
```

### ✅ Pass Criteria
- [ ] Inference time: <500ms trên Pi 3B+
- [ ] Detection output: list of (class_id, confidence, bbox)
- [ ] Adaptive mode: Switches correctly based on RC input
- [ ] Memory: deque(maxlen=1000) không tràn

---

## 🔹 Module 3: MAVLink Communication

### File: `companion_computer/src/communication/mavlink_handler.py`

| Test | Mô phỏng | Thực tế | Cách Test |
|------|----------|---------|-----------|
| Import pymavlink | ✅ | ✅ | `import pymavlink` |
| Serial connection | ❌ | ✅ | Cần FC connected |
| TCP/UDP connection | ✅ | ✅ | SITL simulator hoặc mock |
| Telemetry parsing | ✅ | ✅ | Mock MAVLink messages |
| Command sending | ⚠️ | ✅ | Send to SITL/hardware |
| Heartbeat | ✅ | ✅ | Check message rate |

### Test Mô Phỏng (Windows - với SITL)
```bash
# Cài đặt ArduPilot SITL (WSL hoặc Docker)
# Sau đó:
cd companion_computer
python -c "
from src.communication.mavlink_handler import MAVLinkHandler

# Connect to SITL
mavlink = MAVLinkHandler(connection_string='tcp:127.0.0.1:5760')
mavlink.connect()

# Wait for heartbeat
import time
time.sleep(2)

# Get telemetry
telem = mavlink.get_telemetry()
print('GPS:', telem.get('lat'), telem.get('lon'))
print('Altitude:', telem.get('altitude'))
print('Battery:', telem.get('battery_remaining'))

mavlink.disconnect()
"
```

### Test Thực Tế (Raspberry Pi + Flight Controller)
```bash
# Connect FC to Pi via USB/UART
cd ~/companion_computer
python3 -c "
from src.communication.mavlink_handler import MAVLinkHandler

# Serial connection to FC
mavlink = MAVLinkHandler(connection_string='/dev/serial0:115200')
mavlink.connect()

import time
time.sleep(3)

# Get real telemetry
telem = mavlink.get_telemetry()
print('GPS Fix:', telem.get('fix_type'))
print('Satellites:', telem.get('satellites'))
print('Position:', telem.get('lat'), telem.get('lon'))
print('Attitude:', telem.get('roll'), telem.get('pitch'), telem.get('yaw'))

mavlink.disconnect()
"
```

### ✅ Pass Criteria
- [ ] Connection: No timeout errors
- [ ] Heartbeat: Received within 3s
- [ ] Telemetry: GPS, attitude, battery valid
- [ ] Commands: ARM/DISARM works (test with SITL first!)

---

## 🔹 Module 4: Geolocation Calculator

### File: `companion_computer/src/navigation/geolocation.py`

| Test | Mô phỏng | Thực tế | Cách Test |
|------|----------|---------|-----------|
| Algorithm accuracy | ✅ | ✅ | Known test cases |
| Edge cases | ✅ | ✅ | Extreme angles, altitudes |
| Performance | ✅ | ✅ | 1000 calculations timing |

### Test Mô Phỏng (Windows)
```python
# test_geolocation.py
from src.navigation.geolocation import calculate_target_geolocation

# Test case: Target directly below UAV
telemetry = {
    'lat': 21.028511,
    'lon': 105.804817,
    'altitude': 100,  # meters AGL
    'roll': 0,
    'pitch': 0,
    'yaw': 0
}

bbox = (320, 240, 340, 260)  # Center of 640x480 image
result = calculate_target_geolocation(bbox, telemetry, 640, 480)

print(f"Target lat: {result['latitude']:.6f}")
print(f"Target lon: {result['longitude']:.6f}")
print(f"Expected: ~21.028511, ~105.804817 (directly below)")

# Test case: Target offset to the right
telemetry['yaw'] = 90  # Facing East
bbox = (600, 240, 620, 260)  # Right side of image
result = calculate_target_geolocation(bbox, telemetry, 640, 480)
print(f"Offset target: {result['latitude']:.6f}, {result['longitude']:.6f}")
```

### ✅ Pass Criteria
- [ ] Accuracy: <5m error at 100m altitude
- [ ] Performance: <1ms per calculation
- [ ] No NaN/Inf outputs

---

## 🔹 Module 5: HTTP Upload Client

### File: `companion_computer/src/communication/http_client.py`

| Test | Mô phỏng | Thực tế | Cách Test |
|------|----------|---------|-----------|
| Queue mechanism | ✅ | ✅ | Add 100 items, check queue size |
| Fire-and-forget | ✅ | ✅ | Upload không block main thread |
| Retry logic | ✅ | ✅ | Kill server, check retry |
| Server connection | ✅ (local) | ✅ | POST to /api/target |

### Test Mô Phỏng (Windows)
```bash
# Terminal 1: Start mock server
cd ground_station
python src/web_server/app.py

# Terminal 2: Test upload
cd companion_computer
python -c "
from src.communication.http_client import HTTPUploadClient
import time

client = HTTPUploadClient(base_url='http://localhost:5000')

# Queue 10 targets
for i in range(10):
    target = {
        'timestamp': time.time(),
        'class_name': 'person',
        'confidence': 0.85,
        'latitude': 21.028 + i*0.0001,
        'longitude': 105.804 + i*0.0001
    }
    client.queue_target_geolocation(target)
    print(f'Queued target {i+1}')

# Wait for upload
time.sleep(3)
print('Uploads should be complete')
"
```

### ✅ Pass Criteria
- [ ] Queue: maxsize=50, FIFO behavior
- [ ] Upload: Non-blocking (returns immediately)
- [ ] Server down: Items remain in queue for retry
- [ ] Success: 200 OK from server

---

## 🔹 Module 6: Watchdog Timer

### File: `companion_computer/src/watchdog.py`

| Test | Mô phỏng | Thực tế | Cách Test |
|------|----------|---------|-----------|
| Timer start/stop | ✅ | ✅ | Start, stop, check state |
| Kick mechanism | ✅ | ✅ | Kick before timeout |
| Timeout trigger | ✅ | ✅ | Don't kick, wait for reset |
| Recovery action | ⚠️ | ✅ | Check system reset |

### Test Mô Phỏng (Windows)
```python
from src.watchdog import WatchdogTimer
import time

# Short timeout for testing
watchdog = WatchdogTimer(timeout_s=5)
watchdog.start()

print("Watchdog started with 5s timeout")
print("Kicking every 2 seconds...")

for i in range(3):
    time.sleep(2)
    watchdog.kick()
    print(f"Kicked at {i*2+2}s")

print("Stopping kicks, waiting for timeout...")
time.sleep(6)  # Should trigger timeout

watchdog.stop()
```

### ✅ Pass Criteria
- [ ] Timer: Starts/stops cleanly
- [ ] Kick: Resets countdown
- [ ] Timeout: Triggers recovery action
- [ ] Thread-safe: No race conditions

---

## 🔹 Module 7: Data Logger

### File: `companion_computer/src/data_logging/data_logger.py`

| Test | Mô phỏng | Thực tế | Cách Test |
|------|----------|---------|-----------|
| Log file creation | ✅ | ✅ | Check file exists |
| Telemetry logging | ✅ | ✅ | CSV format valid |
| Target logging | ✅ | ✅ | JSONL format valid |
| Disk space check | ✅ | ✅ | Log rotation |

### Test Mô Phỏng (Windows)
```bash
cd companion_computer
python src/data_logging/data_logger.py
# Check created log files in logs/ directory
```

### ✅ Pass Criteria
- [ ] Files: Created in logs/ directory
- [ ] Format: Valid CSV/JSONL
- [ ] Rotation: New file per session
- [ ] Performance: <1ms per log write

---

## 🔹 Module 8: Ground Station Web Server

### Files:
- `ground_station/src/web_server/app.py`
- `ground_station/src/web_server/templates/dashboard.html`

| Test | Mô phỏng | Thực tế | Cách Test |
|------|----------|---------|-----------|
| Server startup | ✅ | ✅ | `python app.py` |
| Dashboard load | ✅ | ✅ | Browser http://localhost:5000 |
| WebSocket | ✅ | ✅ | Real-time updates |
| API endpoints | ✅ | ✅ | POST /api/target, /api/telemetry |

### Test Mô Phỏng (Windows)
```bash
cd ground_station
python src/web_server/app.py

# Open browser: http://localhost:5000
# Check dashboard loads

# Test API
curl -X POST http://localhost:5000/api/target \
  -H "Content-Type: application/json" \
  -d '{"latitude": 21.028, "longitude": 105.804, "class_name": "person"}'
```

### ✅ Pass Criteria
- [ ] Dashboard: Map displays correctly
- [ ] WebSocket: Connects without errors
- [ ] API: Returns 200 OK
- [ ] Target marker: Appears on map

---

## 🔹 Module 9: Parallel Pipeline (Main)

### File: `companion_computer/src/main.py`

| Test | Mô phỏng | Thực tế | Cách Test |
|------|----------|---------|-----------|
| 3-thread startup | ✅ | ✅ | Check thread names |
| Queue communication | ✅ | ✅ | Frame flows through pipeline |
| Exception isolation | ✅ | ✅ | Kill one thread, others survive |
| Watchdog integration | ✅ | ✅ | Main thread kicks watchdog |
| Performance metrics | ✅ | ✅ | FPS/RAM logging |

### Test Mô Phỏng (Windows - Partial)
```bash
cd companion_computer
python -c "
from src.main import CompanionComputer
import time

# Create but don't start (no hardware)
cc = CompanionComputer()
print('Companion computer created')
print('Threads: Camera, AI, Upload')
print('Queues: frame_queue(2), upload_queue(50)')
"
```

### Test Thực Tế (Raspberry Pi)
```bash
cd ~/companion_computer
python3 src/main.py

# Expected output:
# [INFO] Camera thread started
# [INFO] AI thread started
# [INFO] Upload thread started
# [INFO] Watchdog timer started (60s timeout)
# [INFO] FPS: 28.3 | RAM: 245.2 MB
```

### ✅ Pass Criteria
- [ ] All 3 threads: Running
- [ ] Queues: Not filling up indefinitely
- [ ] FPS: >15 on Pi 3B+
- [ ] RAM: <400MB steady state
- [ ] No crashes: 1 hour continuous run

---

## 📊 Test Summary Matrix

| Module | Mô Phỏng Windows | Thực Tế Pi | Test File |
|--------|------------------|------------|-----------|
| Camera | ✅ (OpenCV) | ✅ (Picamera2) | `test_windows.py` |
| AI Detector | ⚠️ (mock model) | ✅ | `test_rc_mode_system.py` |
| MAVLink | ⚠️ (SITL) | ✅ (FC) | manual test |
| Geolocation | ✅ | ✅ | unit test |
| HTTP Client | ✅ (local server) | ✅ | `test_mock_companion.py` |
| Watchdog | ✅ | ✅ | unit test |
| Data Logger | ✅ | ✅ | `test_windows.py` |
| Web Server | ✅ | ✅ | `test_mock_gcs.py` |
| Main Pipeline | ⚠️ (partial) | ✅ | integration test |

---

## 🚀 Integration Test Sequence

Sau khi tất cả module tests pass, thực hiện integration test:

### Phase 1: Pi-Only Integration
```bash
# Trên Raspberry Pi (không cần FC)
cd ~/companion_computer
python3 -c "
from src.main import CompanionComputer
import time

cc = CompanionComputer()
cc.start()

# Run for 5 minutes
time.sleep(300)

cc.stop()
print('Phase 1 complete')
"
```

### Phase 2: Pi + Flight Controller (SITL)
```bash
# Chạy SITL trên laptop
# Connect Pi to laptop via network
# Run companion computer với SITL connection
```

### Phase 3: Pi + Ground Station
```bash
# Laptop: chạy ground_station/src/web_server/app.py
# Pi: chạy companion_computer/src/main.py với ground_station_url
# Verify: target markers appear on dashboard
```

### Phase 4: Full Hardware Integration
- Pi + Camera + FC + Ground Station
- Outdoor test với GPS fix
- Full pipeline verification

---

## 📝 Test Checklist

### Trước khi bay thực tế:
- [ ] Tất cả module tests pass
- [ ] Phase 1-3 integration tests pass
- [ ] Ground test với FC armed (không cánh quạt)
- [ ] 30 phút stress test không crash
- [ ] Memory usage stable
- [ ] Log files ghi đúng format
- [ ] Dashboard hiển thị real-time

### Safety checks:
- [ ] Watchdog timeout hoạt động
- [ ] Geofencing active
- [ ] Failsafe triggers correctly
- [ ] RTH command works

---

## 📌 Quick Reference Commands

```bash
# Test all modules on Windows
cd companion_computer
python test_windows.py

# Test RC mode switching
python tests/test_rc_mode_system.py

# Test quantum filter (nếu có)
python tests/test_quantum_filtering.py

# Full integration test on Pi
python3 src/main.py --test-mode
```
