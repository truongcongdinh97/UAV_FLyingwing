# ROADMAP TRIỂN KHAI GẤP: BIẾN RPi THÀNH VỊ TƯỚNG THÔNG MINH

## 🎯 MỤC TIÊU
**RPi (Tướng) + EKF (Quân sư) = TẦM NHÌN CHÍNH XÁC NHẤT**

## 📋 CHECKLIST ƯU TIÊN TRIỂN KHAI GẤP

### 🔥 ƯU TIÊN CAO (Tuần 1-2) - NỀN TẢNG

#### 1. [URGENT] Level Shifter cho UART MAVLink
**Mục tiêu:** Thiết lập communication giữa RPi và FC
**Công việc:**
- Mua TXB0104 level shifter hoặc làm voltage divider (1kΩ + 2kΩ)
- Kết nối vật lý:
  ```
  RPi GPIO14 (TXD) → Level Shifter → FC RX2
  RPi GPIO15 (RXD) ← Level Shifter ← FC TX2
  GND chung
  ```
- Test MAVLink communication với `mavproxy`
- Baudrate: 115200

**File cần tạo:**
- `companion_computer/config/uart_config.yaml`
- `companion_computer/tools/test_mavlink.py`

#### 2. [URGENT] Sensor Data Acquisition System
**Mục tiêu:** Đọc tất cả sensor data vào RPi
**Công việc:**

**a. MAVLink Interface (IMU/GPS từ FC):**
```python
# src/communication/mavlink_sensor_reader.py
class MAVLinkSensorReader:
    def read_imu(self):      # RAW_IMU message
    def read_gps(self):      # GPS_RAW_INT message  
    def read_barometer(self): # SCALED_PRESSURE message
```

**b. I2C Drivers (Compass & Lidar):**
```python
# src/sensors/qmc5883l_driver.py
class QMC5883LDriver:  # Address 0x0D

# src/sensors/vl53l1x_driver.py  
class VL53L1XDriver:   # Address 0x29
```

**c. Data Synchronization:**
- Hardware timestamps cho mỗi measurement
- Ring buffer với fixed size
- Thread-safe data access

#### 3. [HIGH] EKF Core Implementation
**Mục tiêu:** Basic EKF chạy với simulated data
**Công việc:**

**a. 15-state EKF với quaternion:**
```python
# src/navigation/ekf_core.py
class ExtendedKalmanFilter:
    # State: [pos(3), vel(3), quat(4), accel_bias(3), gyro_bias(3)]
    
    def predict(self, imu_data, dt):
        # IMU integration prediction
        
    def update_gps(self, gps_data):
        # GPS position/velocity update
        
    def update_compass(self, mag_data):
        # Magnetometer heading update
        
    def update_lidar(self, distance):
        # Altitude update
```

**b. Testing với simulated data:**
- Tạo synthetic sensor data
- Validate EKF convergence
- Benchmark performance

### 🚀 ƯU TIÊN TRUNG (Tuần 3-4) - INTEGRATION

#### 4. [HIGH] Sensor Fusion Pipeline
**Mục tiêu:** Robust fusion với fault tolerance
**Công việc:**
- Adaptive noise covariance estimation
- Outlier rejection using Mahalanobis distance
- Sensor health monitoring
- Graceful degradation khi sensors fail

#### 5. [MEDIUM] State Estimation API cho AI
**Mục tiêu:** Clean interface cho AI modules
**Công việc:**
```python
# src/navigation/state_provider.py
class StateProvider:
    def get_position(self):      # Returns (lat, lon, alt) với confidence
    def get_velocity(self):      # Returns (vx, vy, vz) trong NED frame
    def get_attitude(self):      # Returns (roll, pitch, yaw) với accuracy
    def get_confidence(self):    # Overall estimation confidence
    def get_prediction(self, dt): # Predicted state after dt seconds
```

#### 6. [MEDIUM] Integration với Quantum Filter
**Mục tiêu:** So sánh EKF vs Quantum Filter
**Công việc:**
- Shadow mode operation
- Performance metrics collection
- Hybrid fusion strategy
- Research data logging

### 🎯 ƯU TIÊN THẤP (Tuần 5-6) - OPTIMIZATION

#### 7. [LOW] Performance Optimization
**Mục tiêu:** Tối ưu cho RPi 3B+
**Công việc:**
- Numba JIT compilation cho matrix operations
- Fixed-point arithmetic cho critical paths
- Memory optimization với numpy arrays
- Cache optimization

#### 8. [LOW] Real-time Scheduling
**Mục tiêu:** Đảm bảo real-time performance
**Công việc:**
- Multi-threaded architecture
- Priority scheduling cho EKF thread
- Latency monitoring và optimization
- CPU affinity settings

## 🔧 CÔNG CỤ CẦN THIẾT NGAY

### Hardware:
1. **TXB0104 Level Shifter** (~50k VND) hoặc resistors cho voltage divider
2. **Jumper wires** cho kết nối
3. **Heat sink** cho RPi 3B+
4. **Power supply** 5V/2.5A minimum

### Software:
```bash
# Dependencies cần cài đặt
sudo apt-get update
sudo apt-get install -y python3-pip python3-numpy python3-scipy
sudo apt-get install -y python3-numba libatlas-base-dev libopenblas-dev

pip3 install pymavlink mavproxy smbus2
pip3 install numba  # Performance optimization
```

### Testing Tools:
- MAVLink simulator (ArduPilot SITL)
- Sensor mock data generator
- Performance profiling tools

## 📊 METRICS THÀNH CÔNG

### Sau 2 tuần (Milestone 1):
- ✅ MAVLink communication established
- ✅ All sensor data being read (IMU, GPS, compass, lidar)
- ✅ Basic EKF running @ 30Hz
- ✅ Position accuracy: < 2m (improved from 3-5m GPS only)
- ✅ CPU usage: < 20% trên RPi 3B+

### Sau 4 tuần (Milestone 2):
- ✅ EKF fusion @ 50Hz với all sensors
- ✅ Position accuracy: 0.8-1.5m
- ✅ Velocity accuracy: < 0.3m/s  
- ✅ Attitude accuracy: < 2 degrees
- ✅ Integrated với AI object detection

### Sau 6 tuần (Milestone 3):
- ✅ Optimized performance (Numba, fixed-point)
- ✅ Real-time scheduling implemented
- ✅ Quantum vs EKF comparison complete
- ✅ Research paper data collected

## 💡 CHIẾN LƯỢC TRIỂN KHAI

### 1. START SMALL
- Bắt đầu với chỉ GPS + IMU từ FC
- Basic EKF với linear models
- Offline testing với recorded data

### 2. ADD GRADUALLY
- Tuần 2: Thêm compass (QMC5883L)
- Tuần 3: Thêm lidar (VL53L1X)
- Tuần 4: Thêm adaptive noise estimation

### 3. TEST OFFLINE
- Sử dụng recorded flight data
- Validate với ground truth (nếu có)
- Performance benchmarking

### 4. DEPLOY INCREMENTALLY
- **Stage 1:** Shadow mode (logging only)
- **Stage 2:** Advisory mode (monitoring)
- **Stage 3:** Control input (waypoint guidance)
- **Stage 4:** Full autonomy (AI decisions)

## ⚠️ RISK MITIGATION

### Safety First:
- **FC là primary controller** - Luôn có quyền cao nhất
- **EKF chạy shadow mode đầu tiên** - Không can thiệp control
- **Manual override** - RC transmitter luôn available
- **Fallback mechanisms** - GPS-only mode nếu EKF fails

### Technical Risks:
1. **Level Shifter Failure**: Test với multimeter trước khi kết nối
2. **MAVLink Latency**: Implement timeout và retry logic
3. **Sensor Noise**: Adaptive filtering và outlier rejection
4. **CPU Overload**: Performance monitoring và throttling

### Research Risks:
1. **Quantum Filter Complexity**: Bắt đầu với classical EKF trước
2. **Data Synchronization**: Hardware timestamps và interpolation
3. **Validation Difficulty**: Use simulated data với known ground truth

## 🎯 CÁC FILE CẦN TẠO/TRIỂN KHAI GẤP

### Tuần 1:
```
companion_computer/
├── config/
│   └── uart_config.yaml          # UART/MAVLink configuration
├── tools/
│   └── test_mavlink.py           # MAVLink communication test
└── src/
    ├── communication/
    │   └── mavlink_sensor_reader.py  # Read IMU/GPS từ FC
    └── sensors/
        ├── qmc5883l_driver.py    # Compass driver
        └── vl53l1x_driver.py     # Lidar driver
```

### Tuần 2:
```
companion_computer/src/
├── navigation/
│   ├── ekf_core.py              # Core EKF implementation
│   └── sensor_fusion.py         # Fusion pipeline
└── utils/
    ├── data_sync.py             # Data synchronization
    └── ring_buffer.py           # Thread-safe buffers
```

### Tuần 3:
```
companion_computer/src/
├── navigation/
│   └── state_provider.py        # API cho AI modules
└── tests/
    ├── test_ekf_basic.py        # Basic EKF tests
    └── test_sensor_fusion.py    # Fusion pipeline tests
```

## ✅ KẾT LUẬN

### Triển khai GẤP trong 2 tuần đầu:
1. **Level shifter + MAVLink connection** - Hardware foundation
2. **Sensor data acquisition system** - Data pipeline
3. **EKF core implementation** - Brain của quân sư

### Sau khi triển khai, RPi (Tướng) sẽ có EKF (Quân sư) cung cấp:

#### 1. TẦM NHÌN CHÍNH XÁC
- **Vị trí**: 0.8-1.5m accuracy (vs 3-5m GPS only)
- **Vận tốc**: < 0.3m/s error
- **Góc nghiêng**: < 2 degrees accuracy
- **Tần suất cập nhật**: 50Hz (vs 1-10Hz GPS)

#### 2. DỰ ĐOÁN TƯƠNG LAI
- Predicted position 0.5-1.0 seconds ahead
- Estimated trajectory cho obstacle avoidance
- Energy consumption prediction

#### 3. CẢNH BÁO NGUY HIỂM
- Sensor fault detection
- GPS signal loss prediction
- Boundary violation warnings
- Battery depletion alerts

#### 4. CHIẾN LƯỢC TỐI ƯU
- Optimal path planning với accurate state
- Adaptive sensor weighting
- Resource-aware decision making
- Mission success probability estimation

### LỢI ÍCH CHO HỆ THỐNG:
- **AI Object Detection**: Better target geolocation
- **Autonomous Navigation**: Precise waypoint following
- **Obstacle Avoidance**: Accurate trajectory prediction
- **Research Value**: Quantum vs Classical comparison
- **Mission Success**: Higher reliability và accuracy

**EKF không chỉ là filter - đó là "đôi mắt tinh anh" và "bộ não chiến lược" cho vị tướng RPi của bạn.**
