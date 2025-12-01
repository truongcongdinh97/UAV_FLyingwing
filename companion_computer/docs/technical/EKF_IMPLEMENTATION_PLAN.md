# Kế Hoạch Triển Khai Extended Kalman Filter (EKF) trên Raspberry Pi 3B+ cho UAV

## 📋 Tổng Quan

Tài liệu này trình bày kế hoạch chi tiết để triển khai Extended Kalman Filter (EKF) cho sensor fusion trên **Raspberry Pi 3B+** trong hệ thống UAV Flying Wing thực tế.

## 🎯 Mục Tiêu (Tối Ưu cho RPi 3B+)

1. **Độ chính xác**: Cải thiện độ chính xác định vị từ 3-5m (GPS only) xuống **0.8-1.5m**
2. **Tốc độ cập nhật**: Tăng từ 1-10Hz (GPS) lên **30-50Hz** (sensor fusion)
3. **Độ ổn định**: Giảm noise và drift từ IMU (MPU6000 tích hợp trong FC)
4. **Fault tolerance**: Khả năng hoạt động khi sensors bị lỗi
5. **Real-time performance**: Đảm bảo < 15% CPU usage trên RPi 3B+

## 🔧 Hiện Trạng Hệ Thống

### Các Filters Hiện Có:
- **Quantum Kalman Filter**: `src/quantum/quantum_kalman_filter.py` (15.3 KB)
- **Quantum IMU Drift Filter**: `src/quantum/quantum_imu_drift_filter.py` (45.3 KB)
- **Quantum Integration**: `src/quantum/quantum_integration.py` (8.7 KB)

### Sensors Thực Tế (Theo HARDWARE_WIRING_GUIDE.md):
- **IMU**: Từ **LANRC F4 V3S Plus** (MPU6000 tích hợp) - qua MAVLink
- **GPS**: **NEO-M8N** - UART @ 38400 baud, 1-10Hz
- **Compass**: **QMC5883L** - I2C @ 0x0D
- **Lidar**: **VL53L1X** - I2C @ 0x29, khoảng cách
- **Barometer**: Từ **LANRC F4 V3S Plus** (tích hợp) - qua MAVLink
- **Flight Controller**: **LANRC F4 V3S Plus** - MAVLink via UART

> **Lưu ý**: GY-9250 và HC-SR04 thuộc hệ thống Hộp đen (ESP32-CAM), độc lập với UAV

## 🏗️ Kiến Trúc Hệ Thống EKF

### 1. Hierarchical Architecture

```
┌─────────────────────────────────────────────────┐
│              HIGH-LEVEL (10-50Hz)               │
│  • Navigation & Control                         │
│  • Mission Planning                            │
│  • Obstacle Avoidance                          │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│              MID-LEVEL (10-100Hz)               │
│  • EKF Sensor Fusion                            │
│  • State Estimation                             │
│  • Fault Detection                             │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│              LOW-LEVEL (100-1000Hz)             │
│  • IMU Pre-processing                          │
│  • Sensor Reading                              │
│  • Data Validation                             │
└─────────────────────────────────────────────────┘
```

### 2. State Vector (15 States)

```python
state_vector = [
    # Position (3)
    'pos_x', 'pos_y', 'pos_z',
    
    # Velocity (3)
    'vel_x', 'vel_y', 'vel_z',
    
    # Attitude - Quaternion (4)
    'q0', 'q1', 'q2', 'q3',
    
    # IMU Biases (5)
    'accel_bias_x', 'accel_bias_y', 'accel_bias_z',
    'gyro_bias_x', 'gyro_bias_y', 'gyro_bias_z'
]
```

### 3. Measurement Vector

```python
measurements = {
    'fc_imu': {  # Từ Flight Controller qua MAVLink
        'accelerometer': ['accel_x', 'accel_y', 'accel_z'],
        'gyroscope': ['gyro_x', 'gyro_y', 'gyro_z']
    },
    'gps': {
        'position': ['lat', 'lon', 'alt'],
        'velocity': ['vel_n', 'vel_e', 'vel_d']
    },
    'fc_barometer': ['pressure', 'temperature'],  # Từ LANRC F4 V3S Plus (tích hợp)
    'compass': ['mag_x', 'mag_y', 'mag_z'],  # QMC5883L external
    'lidar': ['distance']  # VL53L1X
}
```

## ⚡ Phân Tích Hiệu Năng Raspberry Pi 3B+ (Thực Tế)

### Computational Requirements (Tối Ưu cho RPi 3B+):

| Component | Operations/Update | Frequency | Total Ops/s |
|-----------|-------------------|-----------|-------------|
| EKF Prediction | ~7,500 FLOPs | 50 Hz | 375,000 FLOPs |
| EKF Update | ~7,500 FLOPs | 50 Hz | 375,000 FLOPs |
| IMU Pre-process | ~1,000 FLOPs | 200 Hz | 200,000 FLOPs |
| **TOTAL** | **~16,000 FLOPs** | **-** | **0.95 MFLOPS** |

### RPi 3B+ Capacity (Thực Tế):
- **CPU**: Quad-core Cortex-A53 @ 1.2GHz
- **Performance**: ~2,500 MFLOPS (2.5 GFLOPS)
- **RAM**: 1GB LPDDR2
- **Theoretical CPU Usage**: 0.04%
- **Real-world với Python**: 5-15% (với optimization)

### Memory Requirements:
- State vector: 15 floats × 4 bytes = 60 bytes
- Covariance matrix: 15×15 × 4 bytes = 900 bytes
- Jacobian matrices: ~2 KB
- Sensor buffers: 5-10 KB
- **TOTAL**: < 20 KB (không đáng kể so với 1GB RAM)

### So Sánh với RPi 4:
```
┌─────────────────┬────────────┬────────────┐
│ Metric          │ RPi 3B+    │ RPi 4      │
├─────────────────┼────────────┼────────────┤
│ Max EKF Rate    │ 30-50Hz    │ 50-100Hz   │
│ CPU Usage       │ 5-15%      │ 2-8%       │
│ Accuracy        │ 0.8-1.5m   │ 0.5-1m     │
│ Latency         │ 15-25ms    │ 10-20ms    │
│ Power Draw      │ ~2A @ 5V   │ ~2.5A @ 5V │
└─────────────────┴────────────┴────────────┘
```

## 🔌 Kết Nối Thực Tế với Raspberry Pi 3B+

### 1. I2C Bus Configuration (Theo Wiring Guide)

```python
# I2C Devices Configuration - THỰC TẾ của bạn
# Lưu ý: IMU lấy từ FC qua MAVLink, không dùng I2C trực tiếp
i2c_devices = {
    'compass': {
        'address': 0x0D,      # QMC5883L - Compass
        'bus': 1,
        'rate': 100000,       # 100 kHz (standard)
        'sensors': ['mag_x', 'mag_y', 'mag_z']
    },
    'lidar': {
        'address': 0x29,      # VL53L1X - Time-of-Flight
        'bus': 1,
        'rate': 400000,       # 400 kHz
        'sensors': ['distance']
    }
}
```

### 2. UART Configuration cho MAVLink với FC

```python
# MAVLink Configuration với LANRC F4 V3S Plus
mavlink_config = {
    'port': '/dev/ttyAMA0',   # RPi 3B+ UART
    'baudrate': 115200,       # MAVLink standard
    'timeout': 0.1,           # 100ms timeout
    'source_system': 1,       # Companion computer ID
    'source_component': 1,    # MAV_COMP_ID_ONBOARD_COMPUTER
    'protocol': 'mavlink2'    # MAVLink 2.0
}

# ⚠️ QUAN TRỌNG: Level Shifting Required
# RPi 3B+: 3.3V logic | FC: 5V logic
# Cần: TXB0104 hoặc voltage divider (2 resistors)
```

### 3. Wiring Diagram Thực Tế

```
Raspberry Pi 3B+ (Companion Computer)
├── I2C Bus 1 (SDA: GPIO2, SCL: GPIO3)
│   ├── QMC5883L (Compass) @ 0x0D
│   └── VL53L1X (Lidar) @ 0x29
├── UART (GPIO14/TXD, GPIO15/RXD)
│   └── LANRC F4 V3S Plus (FC) via Level Shifter
│       └── IMU data (MPU6000) qua MAVLink
│       └── Barometer data qua MAVLink  
└── Power
    ├── 5V/2.5A minimum cho RPi 3B+
    └── 3.3V cho sensors (từ RPi hoặc regulator)

Lưu ý: GY-9250 và HC-SR04 thuộc ESP32 Hộp đen (độc lập)
```

### 4. Level Shifter Circuit (Bắt Buộc)

```
RPi 3B+ (3.3V)          Level Shifter           FC (5V)
GPIO14 (TXD) ──────► LV1 ──────► HV1 ──────► RX2
GPIO15 (RXD) ◄────── LV2 ◄────── HV2 ◄────── TX2
GND ──────────────── GND ──────── GND ─────── GND

Component: TXB0104 (4-channel bi-directional)
Hoặc: Voltage divider (2 resistors: 1kΩ + 2kΩ)
```

## 💻 Implementation Plan

### Phase 1: Foundation & Hardware (Tuần 1-2)

#### 1.1. Hardware Setup cho RPi 3B+
```bash
# Enable interfaces trên RPi 3B+
sudo raspi-config
# → Interface Options
#   → I2C: Enable (cho QMC5883L, VL53L1X)
#   → Serial Port: Enable (disable login shell)

# Cài đặt dependencies tối ưu cho RPi 3B+
sudo apt-get update
sudo apt-get install -y python3-pip python3-numpy python3-scipy
sudo apt-get install -y python3-numba  # Performance optimization

# Python packages
pip3 install smbus2 pyserial adafruit-circuitpython-mpu9250
pip3 install mavproxy pymavlink  # MAVLink communication
pip3 install numba               # JIT compilation for performance

# Enable hardware acceleration
sudo apt-get install -y libatlas-base-dev  # BLAS/LAPACK
sudo apt-get install -y libopenblas-dev    # Optimized linear algebra
```

#### 1.2. Sensor Drivers cho Hardware Thực Tế
```python
# src/sensors/qmc5883l_driver.py
class QMC5883LDriver:
    """Driver cho QMC5883L Compass"""
    def __init__(self, bus=1, address=0x0D):
        self.bus = smbus2.SMBus(bus)
        self.address = address
        
    def read_compass(self):
        """Đọc magnetometer data"""
        # QMC5883L registers
        data = self.bus.read_i2c_block_data(self.address, 0x00, 6)
        mag_x = self._convert(data[1], data[0])
        mag_y = self._convert(data[3], data[2])
        mag_z = self._convert(data[5], data[4])
        
        return {
            'mag': [mag_x, mag_y, mag_z],
            'timestamp': time.time()
        }

# src/sensors/mavlink_imu.py  
class MAVLinkIMU:
    """Nhận IMU data từ Flight Controller qua MAVLink"""
    def __init__(self, mavlink_connection):
        self.mav = mavlink_connection
        
    def read_imu(self):
        """Đọc RAW_IMU message từ FC"""
        msg = self.mav.recv_match(type='RAW_IMU', blocking=True, timeout=0.1)
        if msg:
            return {
                'accel': [msg.xacc, msg.yacc, msg.zacc],
                'gyro': [msg.xgyro, msg.ygyro, msg.zgyro],
                'timestamp': msg.time_usec / 1e6
            }
        return None
```

> **Lưu ý**: IMU data lấy từ Flight Controller (LANRC F4 V3S Plus có MPU6000) 
> qua MAVLink, không cần driver I2C riêng. GY-9250 thuộc hệ thống Hộp đen ESP32.

### Phase 2: EKF Core (Tuần 3-4)

#### 2.1. EKF Implementation
```python
# src/navigation/ekf_filter.py
class ExtendedKalmanFilter:
    def __init__(self, n_states=15):
        self.n_states = n_states
        self.x = np.zeros(n_states)  # State vector
        self.P = np.eye(n_states)    # Covariance matrix
        self.Q = np.eye(n_states)    # Process noise
        self.R = np.eye(6)           # Measurement noise
        
    def predict(self, dt, imu_data):
        # Prediction step
        # x = f(x, u)
        # P = F * P * F^T + Q
        pass
        
    def update(self, measurement, measurement_type):
        # Update step
        # K = P * H^T * (H * P * H^T + R)^-1
        # x = x + K * (z - h(x))
        # P = (I - K * H) * P
        pass
```

#### 2.2. State Transition Models
```python
# IMU-based motion model
def imu_motion_model(state, imu_data, dt):
    # Quaternion integration
    # Velocity integration
    # Position integration
    # Bias estimation
    pass

# GPS update model
def gps_measurement_model(state):
    # Convert ECEF to Lat/Lon/Alt
    # Convert body velocity to NED
    pass
```

### Phase 3: Optimization (Tuần 5-6)

#### 3.1. Performance Optimization
```python
# Use NumPy vectorization
@numba.jit(nopython=True)
def fast_matrix_multiply(A, B):
    return np.dot(A, B)

# Pre-compute Jacobians
class PrecomputedJacobians:
    def __init__(self):
        self.F = None  # State transition Jacobian
        self.H_gps = None  # GPS measurement Jacobian
        self.H_imu = None  # IMU measurement Jacobian
```

#### 3.2. Real-time Scheduling
```python
# Multi-threaded architecture
import threading
import queue

class RealTimeEKF:
    def __init__(self):
        self.imu_queue = queue.Queue(maxsize=100)
        self.gps_queue = queue.Queue(maxsize=10)
        self.ekf_thread = threading.Thread(target=self.ekf_loop)
        self.imu_thread = threading.Thread(target=self.imu_loop)
```

### Phase 4: Integration & Testing (Tuần 7-8)

#### 4.1. Integration với Hiện Trạng
```python
# src/navigation/sensor_fusion.py
class SensorFusionSystem:
    def __init__(self):
        self.ekf = ExtendedKalmanFilter()
        self.quantum_filter = QuantumKalmanFilter()  # Existing
        self.fusion_strategy = 'adaptive'  # adaptive/ekf/quantum
        
    def fuse_sensors(self, sensor_data):
        if self.fusion_strategy == 'ekf':
            return self.ekf.fuse(sensor_data)
        elif self.fusion_strategy == 'quantum':
            return self.quantum_filter.fuse(sensor_data)
        else:  # adaptive
            # Choose best based on conditions
            pass
```

#### 4.2. Testing Framework
```python
# tests/test_ekf_performance.py
class TestEKFPerformance:
    def test_real_time_performance(self):
        # Test 100Hz update rate
        # Test CPU usage < 10%
        # Test memory usage < 50MB
        pass
        
    def test_accuracy_improvement(self):
        # Compare with raw GPS
        # Compare with quantum filter
        pass
```

## 📊 Đánh Giá Rủi Ro & Giải Pháp

### 1. Rủi Ro: Python Real-time Performance
**Giải pháp**:
- Sử dụng Numba/Cython cho critical sections
- Implement ring buffers cho sensor data
- Use `time.perf_counter()` cho precise timing
- Consider RT-Preempt kernel nếu cần hard real-time

### 2. Rủi Ro: Sensor Synchronization
**Giải pháp**:
- Hardware timestamps cho mỗi measurement
- Interpolation cho mismatched rates
- Kalman filter prediction between measurements

### 3. Rủi Ro: Power Management
**Giải pháp**:
- Dynamic frequency scaling
- Sleep modes khi idle
- Power monitoring và alerts

### 4. Rủi Ro: Thermal Management
**Giải pháp**:
- Heat sinks cho RPi
- Thermal throttling monitoring
- Ventilation design trong UAV

## 🧪 Testing & Validation

### 1. Unit Tests
```bash
# Run EKF unit tests
cd companion_computer
python -m pytest tests/test_ekf_core.py -v
```

### 2. Performance Tests
```bash
# Test real-time performance
python tests/test_ekf_performance.py --duration 60 --rate 100
```

### 3. Field Tests
```python
# Test scenarios
test_scenarios = [
    'static_position_hold',
    'slow_movement_2m_s',
    'fast_movement_10m_s',
    'gps_signal_loss_30s',
    'imu_saturation_recovery'
]
```

### 4. Validation Metrics
```python
validation_metrics = {
    'position_accuracy': 'RMSE vs ground truth (m)',
    'velocity_accuracy': 'RMSE vs ground truth (m/s)',
    'update_rate': 'Actual vs target (Hz)',
    'cpu_usage': 'Percentage during operation',
    'memory_usage': 'MB during operation',
    'latency': 'End-to-end delay (ms)'
}
```

## 🚀 Deployment Strategy

### 1. Gradual Rollout
1. **Stage 1**: Logging only - record sensor data + EKF output
2. **Stage 2**: Advisory mode - EKF output for monitoring only
3. **Stage 3**: Control input - EKF used for stabilization
4. **Stage 4**: Full autonomy - EKF used for navigation

### 2. Fallback Mechanisms
```python
class FaultTolerantEKF:
    def __init__(self):
        self.primary_ekf = ExtendedKalmanFilter()
        self.backup_filter = QuantumKalmanFilter()  # Existing
        self.degraded_mode = 'gps_only'  # Fallback modes
        
    def handle_sensor_failure(self, failed_sensor):
        if failed_sensor == 'gps':
            self.degraded_mode = 'imu_only'
        elif failed_sensor == 'imu':
            self.degraded_mode = 'gps_only'
```

### 3. Health Monitoring
```python
class EKFHealthMonitor:
    def check_health(self):
        metrics = {
            'innovation_bounds': self.check_innovation(),
            'covariance_stability': self.check_covariance(),
            'real_time_performance': self.check_timing(),
            'sensor_consistency': self.check_sensors()
        }
        return all(metrics.values())
```

## 📈 Expected Improvements

### 1. Position Accuracy
| Scenario | GPS Only | EKF Fusion | Improvement |
|----------|----------|------------|-------------|
| Static | 1.5-3m | 0.5-1m | 2-3x |
| Slow movement | 2-4m | 0.8-1.5m | 2.5x |
| Fast movement | 3-5m | 1-2m | 3x |
| GPS denied | N/A | 1-3m (drift) | N/A |

### 2. Update Rate
| Sensor | Raw Rate | EKF Output |
|--------|----------|------------|
| GPS | 1-10Hz | 50-100Hz |
| IMU | 100-1000Hz | 50-100Hz (fused) |

### 3. Reliability
- **GPS signal loss**: Continue navigation for 30-60 seconds
- **IMU failure**: Degrade to GPS-only mode
- **Sensor disagreement**: Automatic outlier rejection

## 🔄 Integration với Hiện Trạng

### 1. Quantum Filters Integration
```python
# Hybrid EKF-Quantum Filter
class HybridNavigationFilter:
    def __init__(self):
        self.ekf = ExtendedKalmanFilter()
        self.quantum = QuantumKalmanFilter()
        self.mode = 'ekf'  # 'ekf', 'quantum', 'hybrid'
        
    def get_estimate(self):
        if self.mode == 'ekf':
            return self.ekf.get_state()
        elif self.mode == 'quantum':
            return self.quantum.get_state()
        else:  # hybrid
            # Weighted average based on confidence
            ekf_conf = self.ekf.get_confidence()
            quantum_conf = self.quantum.get_confidence()
            return weighted_average(ekf_conf, quantum_conf)
```

### 2. MAVLink Integration
```python
# Send EKF estimates via MAVLink
class EKFMAVLinkInterface:
    def send_ekf_status(self):
        msg = mavlink.MAVLink_ekf_status_message(
            flags=self.ekf.get_flags(),
            velocity_variance=self.ekf.get_velocity_variance(),
            pos_horiz_variance=self.ekf.get_position_variance(),
            pos_vert_variance=self.ekf.get_altitude_variance(),
            compass_variance=self.ekf.get_heading_variance()
        )
        self.mavlink.send(msg)
```

## 📋 Checklist Triển Khai

### Trước Triển Khai
- [ ] Verify sensor compatibility
- [ ] Test I2C
