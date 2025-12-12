# 🛩️ Flying Wing UAV - Project Portfolio

<div align="center">

![UAV Type](https://img.shields.io/badge/Type-Modified%20BWB%20Flying%20Wing-blue?style=for-the-badge)
![Flight Time](https://img.shields.io/badge/Flight%20Time-25--30%20min-green?style=for-the-badge)
![Payload](https://img.shields.io/badge/Payload-~6%20kg-orange?style=for-the-badge)
![Speed](https://img.shields.io/badge/Speed-50--80%20km/h-red?style=for-the-badge)

**"Bay để thực hiện nhiệm vụ (UAV Engineer), không chỉ là bay được"**

*Modified Blended Wing Body với Vertical Stabilizers - Tích hợp AI tại biên, Quantum-inspired Filtering, và hệ thống chống GPS Jamming*

</div>

---

## 📋 Mục Lục

1. [Tổng Quan Hệ Thống](#-tổng-quan-hệ-thống)
2. [Kiến Trúc Phần Mềm](#-kiến-trúc-phần-mềm)
3. [Tính Năng Nổi Bật](#-tính-năng-nổi-bật)
4. [Quantum-Inspired Kalman Filter](#-quantum-inspired-kalman-filter)
5. [Hybrid GPS Denial System](#-hybrid-gps-denial-system)
6. [Ground Control Station](#-ground-control-station)
7. [AI Edge Processing](#-ai-edge-processing)
8. [Safety & Failsafe Logic](#-safety--failsafe-logic)
9. [Thông Số Kỹ Thuật](#-thông-số-kỹ-thuật)
10. [Codebase Statistics](#-codebase-statistics)

---

## 🎯 Tổng Quan Hệ Thống

### Điểm Khác Biệt So Với UAV Thông Thường

| Tiêu Chí | UAV Thương Mại | Flying Wing UAV (Dự án này) | Ghi Chú Kỹ Thuật |
|----------|----------------|---------------------------|------------------|
| **Xử lý AI** | Cloud-based, độ trễ cao | Edge Processing trên RPi, real-time | TFLite MobileNet SSD, ~100ms/frame |
| **GPS Denial** | Mất kiểm soát | EKF Dead Reckoning (không dùng camera) | 15-state EKF + IMU + Airspeed, ~120s max |
| **Sensor Filtering** | EKF tiêu chuẩn | Quantum-Inspired KF (nghiên cứu) | VQC 4-qubit, shadow mode only |
| **Điều khiển** | Chỉ RC < 2km | 5G BVLOS + RC fallback | MAVLink 2.0 qua REST API |
| **Decision Making** | Passive | State-machine Autonomous | Python asyncio, 50Hz loop |
| **Data Logging** | Basic telemetry | Blackbox + Quantum research data | SQLite + CSV, ~10KB/s |

> ⚠️ **Lưu ý về GPS Denial**: Hệ thống **KHÔNG sử dụng Visual Odometry hoặc SLAM** vì RPi 3B+ không đủ tài nguyên. Thay vào đó, chúng tôi dùng **Extended Kalman Filter 15-state** kết hợp IMU + Airspeed sensor + Compass để ước lượng vị trí khi mất GPS. Đây là phương pháp tính toán thuần túy, không xử lý ảnh.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FLYING WING UAV ECOSYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                         🛩️ AIRBORNE SYSTEMS                                │ │
│  │  ┌─────────────┐    ┌──────────────────┐    ┌────────────────────────────┐ │ │
│  │  │  LANRC F4   │◄──►│  Raspberry Pi    │◄──►│   Sensor Suite            │ │ │
│  │  │  V3S Plus   │    │     3B+          │    │   • OV5647 Camera (5MP)   │ │ │
│  │  │  (ArduPlane)│    │  ┌─────────────┐ │    │   • MS4525DO Pitot        │ │ │
│  │  │             │    │  │ AI Detector │ │    │   • VL53L1X LiDAR         │ │ │
│  │  │ • EKF Fusion│    │  │ TFLite Edge │ │    │   • QMC5883L Compass      │ │ │
│  │  │ • MAVLink   │    │  ├─────────────┤ │    └────────────────────────────┘ │ │
│  │  │ • PWM Out   │    │  │ Quantum KF  │ │                                   │ │
│  │  └─────────────┘    │  │ Shadow Mode │ │    ┌────────────────────────────┐ │ │
│  │        │            │  ├─────────────┤ │    │   Power System (6S2P)      │ │ │
│  │   MAVLink UART      │  │ GPS Denial  │ │    │   • 2x CNHL 6S 5200mAh    │ │ │
│  │                     │  │ Handler     │ │    │   • 2x D4250 600KV Motor  │ │ │
│  │                     │  └─────────────┘ │    │   • 2x ESC 100A           │ │ │
│  │                     └──────────────────┘    └────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                            │
│              ┌─────────────────────┼─────────────────────┐                      │
│              │                     │                     │                      │
│              ▼                     ▼                     ▼                      │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐           │
│  │ ELRS 2.4GHz       │  │ 5G/LTE Modem      │  │ ESP32 Blackbox    │           │
│  │ (RC Control)      │  │ (BVLOS Data)      │  │ (Independent Log) │           │
│  │ 250mW, Low Latency│  │ REST API + Video  │  │ SD Card + Camera  │           │
│  └─────────┬─────────┘  └─────────┬─────────┘  └───────────────────┘           │
│            │                      │                                             │
├────────────┼──────────────────────┼─────────────────────────────────────────────┤
│            │                      │                                             │
│  ┌─────────▼──────────────────────▼──────────────────────────────────────────┐ │
│  │                        🖥️ GROUND CONTROL STATION                          │ │
│  │                                                                           │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                      Mission Planner / QGroundControl                │ │ │
│  │  │  • Bản đồ + Waypoint Editor      • 3D View          • Telemetry      │ │ │
│  │  │  • ArduPilot Parameters          • Logs             • Failsafe       │ │ │
│  │  └──────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                           │ │
│  │  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐  │ │
│  │  │  Flask Web Server  │  │  ML Training Server │  │  Data Logger       │  │ │
│  │  │  Video AI Stream   │  │  Model Sync to UAV  │  │  SQLite + CSV      │  │ │
│  │  │  Target Log        │  │                     │  │                    │  │ │
│  │  └────────────────────┘  └────────────────────┘  └────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Kiến Trúc Phần Mềm

### Cấu Trúc Thư Mục Dự Án (Root)

```
Flying_Wing_UAV/
├── companion_computer/          # 🛩️ Raspberry Pi onboard software
├── ground_station/              # 🖥️ GCS Desktop & Web applications
├── design_calculations/         # 📐 Aerodynamics & CG calculations
├── simulation/                  # 🎮 SITL testing & tuning scripts
├── docs/                        # 📚 Documentation & research
├── firmware/                    # 🔧 ArduPilot configuration
├── tests/                       # 🧪 Integration tests
├── logs/                        # 📊 Flight logs storage
├── uploads/                     # 📤 Uploaded data (images, telemetry)
│
├── FlyingWing_BOM.csv           # Bill of Materials
├── Design_Comparison.csv        # Design iterations comparison
├── Main_Parameter.param         # ArduPilot parameters
├── geofence_config.json         # Geofence configuration
├── mission_example.txt          # Example mission file
├── install_rpi.sh               # RPi installation script
├── requirements.txt             # Python dependencies
└── README.md                    # Project overview
```

### Companion Computer Stack (Raspberry Pi)

```
companion_computer/
├── src/
│   ├── main.py                          # 🚀 Application entry point
│   ├── watchdog.py                      # 🔍 System health monitoring
│   ├── __init__.py
│   │
│   ├── ai/                              # 🤖 AI Edge Processing
│   │   ├── object_detector.py           # TFLite MobileNet SSD
│   │   ├── adaptive_detector.py         # Adaptive threshold detection
│   │   ├── optimized_tracker.py         # Multi-object tracking
│   │   ├── rc_mode_controller.py        # AI-RC mode switching
│   │   └── __init__.py
│   │
│   ├── quantum/                         # ⚛️ Quantum Research Module
│   │   ├── quantum_kalman_filter.py     # VQC-based Kalman Filter
│   │   ├── quantum_integration.py       # Shadow mode integration
│   │   ├── quantum_imu_drift_filter.py  # IMU drift correction
│   │   └── __init__.py
│   │
│   ├── navigation/                      # 🧭 Navigation & GPS Denial
│   │   ├── autonomous.py                # Waypoint navigation
│   │   ├── geolocation.py               # Target GPS calculation
│   │   ├── ekf_integrated_gps_denial.py # 15-state EKF Dead Reckoning
│   │   ├── hybrid_gps_denial_system.py  # 3-tier Hybrid System (1048 lines)
│   │   └── __init__.py
│   │
│   ├── safety/                          # 🛡️ Safety Systems
│   │   ├── geofencing.py                # Polygon-based geofence
│   │   ├── battery_failsafe.py          # Energy-based decisions
│   │   ├── gps_denial_handler.py        # Jamming detection & escape
│   │   └── __init__.py
│   │
│   ├── communication/                   # 📡 Communication
│   │   └── (mavlink_manager, http_client)
│   │
│   ├── camera/                          # 📷 Camera Module
│   │   └── (camera_manager, video_streamer)
│   │
│   ├── data_logging/                    # 📊 Data Logging
│   │   └── (flight_logger)
│   │
│   └── scheduler/                       # ⏰ Task Scheduler
│       └── (mission_scheduler)
│
├── config/                              # ⚙️ Configuration files
├── tests/                               # 🧪 Unit tests
│   ├── test_quantum_filtering.py
│   ├── test_quantum_imu_drift.py
│   ├── test_camera.py
│   ├── test_android_detection.py
│   └── ...
├── models/                              # 🧠 AI models (TFLite)
├── logs/                                # 📊 Log files
├── tools/                               # 🔧 Utility scripts
├── examples/                            # 📖 Usage examples
└── README.md
```

### Ground Control Station Stack

> ⚠️ **Lưu ý**: GCS Desktop (PyQt6) đã bị hủy bỏ (01/12/2025).
> Dùng Mission Planner cho giám sát bay, Flask Web Server cho Video AI.

```
ground_station/
├── src/                                 # 🌐 Web & Communication
│   ├── main.py
│   ├── mission_planner.py
│   ├── web_server/
│   │   ├── app.py                       # Flask REST API (387 lines)
│   │   └── templates/dashboard.html     # Web dashboard (427 lines)
│   │
│   └── communication/
│       ├── mavlink_client.py
│       └── video_receiver.py
│
├── config/                              # ⚙️ Server configuration
├── tests/                               # 🧪 Server tests
├── ml_server.py                         # 🧠 ML Training Server
├── requirements.txt                     # Web dependencies
└── README.md
```

### Phiên bản công cụ sử dụng

| Công cụ | Mục đích | Lý do chọn |
|---------|----------|------------|
| **Mission Planner** | Giám sát bay đầy đủ | Đã hoàn hảo: 3D, Map, Telemetry, Parameters |
| **Flask Web Server** | Video AI Stream + Target Log | Custom - không có trong Mission Planner |

### Other Project Directories

```
design_calculations/                     # 📐 Engineering Calculations
├── aerodynamics_calculator.py           # Lift, drag, efficiency
├── cg_calculator.py                     # Center of gravity analysis
├── simulation_6s.py                     # 6S power system simulation
├── redesign_1400mm.py                   # Wingspan optimization
├── redesign_v2_solver.py                # Design iteration solver
├── run_all.py                           # Run all calculations
├── aerodynamics_report.json             # Generated report
├── cg_visualization.png                 # CG plot output
└── README.md

simulation/                              # 🎮 SITL Testing & Tuning
├── run_sitl_test.py                     # SITL test runner
├── reboot_sitl.py                       # SITL reboot utility
├── tune_flight_stability.py             # PID tuning for stability
├── tune_flight_smoothness.py            # Smooth flight tuning
├── tune_flight_balanced.py              # Balanced performance
├── tune_stop_weaving.py                 # Anti-weaving tuning
├── fix_roll_oscillation.py              # Roll oscillation fix
├── fix_yaw_oscillation.py               # Yaw oscillation fix
├── fix_accel_error.py                   # Accelerometer error fix
├── fix_gps_error.py                     # GPS error handling
└── README_SITL.md                       # SITL guide

docs/                                    # 📚 Documentation
├── PROJECT_PORTFOLIO.md                 # This file - Project overview
├── PROJECT_PROGRESS.md                  # Development progress
├── design/                              # Design documents
├── hardware/                            # Hardware documentation
├── technical/                           # Technical specifications
├── research/                            # Research papers & notes
├── testing/                             # Test procedures
└── deployment/                          # Deployment guides
```

---

## ✨ Tính Năng Nổi Bật

### 1. 🧠 Edge AI Processing

**TensorFlow Lite trên Raspberry Pi 3B+** - Xử lý AI hoàn toàn trên máy bay, không phụ thuộc kết nối.

> **Thuật toán**: MobileNet SSD v2 (quantized INT8) chạy trên TFLite Runtime. Model được tối ưu cho ARM Cortex-A53, inference ~100ms/frame. Tracking sử dụng VIT tracker (OpenCV 4.12) với ~47 FPS, fallback sang MIL tracker nếu cần.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Thread 1       │     │  Thread 2       │     │  Thread 3       │
│  Frame Capture  │────►│  TFLite Detect  │────►│  Geolocation    │
│  10 FPS @ 1080p │     │  MobileNet SSD  │     │  GPS + Camera   │
│  OV5647 Camera  │     │  ~100ms/frame   │     │  Fusion         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  5G Upload      │
                        │  Detection +    │
                        │  Coordinates    │
                        └─────────────────┘
```

**Khả năng:**
- Phát hiện & theo dõi đa đối tượng (người, xe, tàu thuyền...)
- Tính toán tọa độ GPS của mục tiêu từ camera (trigonometry + altitude)
- Gửi cảnh báo real-time về Ground Station qua MAVLink STATUSTEXT

### 2. 🎯 TRUE Asynchronous Hybrid Verification

**Giải quyết "Bẫy Latency Mismatch"** - Tracker nhanh (40 FPS) + Detector chậm (300ms) chạy song song.

> **Vấn đề**: Khi detector xử lý xong frame 100, tracker đã ở frame 110. So sánh trực tiếp → IoU sai!
> 
> **Giải pháp**: 
> - **Time Machine Buffer**: Lưu 50 frames tracker bbox gần nhất
> - **Motion Prediction**: Dự đoán vị trí dựa trên velocity
> - **TRUE ASYNC**: Detector chạy riêng thread, không block tracker

```
┌─────────────────────────────────────────────────────────────────┐
│           TRUE ASYNC HYBRID VERIFICATION SYSTEM                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MAIN THREAD (40 FPS - Không bị block)                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Frame ──► VIT Tracker ──► Time Machine Buffer ──► Output│   │
│  │          (~2ms/frame)    (lưu 50 frames)                │   │
│  └─────────────────────────────────────────────────────────┘   │
│           │                         ▲                          │
│           │ Mỗi 30 frames           │ Kết quả                  │
│           ▼                         │                          │
│  BACKGROUND THREAD (300ms - Không block main)                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Queue ──► Detector ──► Time-Aligned IoU ──► Result Queue│   │
│  │ (2 frames)  (300ms)   (Motion Compensated)              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  IoU THRESHOLDS                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ IoU > 0.5: ✅ EXCELLENT - Reset tracker nhẹ             │   │
│  │ IoU > 0.3: ⚠️ WARNING - Tracker đang drift              │   │
│  │ IoU > 0.1: 🚨 DANGER - Cảnh báo phi công                │   │
│  │ IoU < 0.1: 💀 CRITICAL - Reinitialize tracker           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  GRACE PERIOD: 60 frames (2 giây) cho phép occlusion           │
└─────────────────────────────────────────────────────────────────┘
```

**Tính năng:**
- **Non-blocking**: Tracker chạy 40 FPS liên tục, không bị giật
- **Time Machine Buffer**: Giải quyết latency mismatch (9 frames = 300ms)
- **Motion Prediction**: Bù trừ chuyển động trong thời gian detector chạy
- **Grace Period**: Cho phép vật thể bị che khuất 2 giây trước khi mất tracking

---

## ⚛️ Quantum-Inspired Kalman Filter

**Nghiên cứu đột phá**: Sử dụng Variational Quantum Circuits để lọc nhiễu phi tuyến tính của cảm biến MEMS giá rẻ.

> **Thuật toán**: Variational Quantum Eigensolver (VQE) với 4-qubit circuit, 3 variational layers. Sử dụng Qiskit Aer simulator (không cần quantum hardware thật). Chạy ở **Shadow Mode** - chỉ so sánh với EKF, không can thiệp điều khiển. Mục đích: nghiên cứu, không phải production.

### Mục Tiêu Nghiên Cứu
1. **Triển khai thuật toán lượng tử cảm hứng** trên Raspberry Pi để lọc nhiễu phi tuyến tính của cảm biến MEMS giá rẻ
2. **Xử lý drift IMU khi mất GPS** sử dụng Quantum Kalman Filter để duy trì độ chính xác định vị
3. **So sánh hiệu suất** với bộ lọc EKF tiêu chuẩn của ArduPilot

### Kiến Trúc VQC

```
┌─────────────────────────────────────────────────────────────────┐
│              QUANTUM KALMAN FILTER ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  IMU Raw Data ─────┐                                           │
│  (Accel, Gyro,     │                                           │
│   Magnetometer)    │                                           │
│                    ▼                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           VARIATIONAL QUANTUM CIRCUIT (VQC)             │   │
│  │                                                         │   │
│  │   ┌──────┐   ┌──────────────────────┐   ┌──────────┐   │   │
│  │   │Angle │   │  3-Layer Variational │   │   VQE    │   │   │
│  │   │Encode│──►│  Circuit (4 qubits)  │──►│Optimizer │   │   │
│  │   │      │   │                      │   │          │   │   │
│  │   │ θ=f(x)│  │  ┌──┐ ┌──┐ ┌──┐ ┌──┐│   │ COBYLA   │   │   │
│  │   └──────┘   │  │q0│─│q1│─│q2│─│q3││   └──────────┘   │   │
│  │              │  └──┘ └──┘ └──┘ └──┘│                   │   │
│  │              │    Ry + CNOT Gates  │                   │   │
│  │              └──────────────────────┘                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                     │
│                          ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   SHADOW MODE                            │   │
│  │   ┌──────────────┐         ┌──────────────┐             │   │
│  │   │   QKF State  │ compare │  EKF State   │             │   │
│  │   │   Estimate   │◄───────►│  (ArduPilot) │             │   │
│  │   └──────────────┘         └──────────────┘             │   │
│  │           │                        │                     │   │
│  │           └────────┬───────────────┘                     │   │
│  │                    ▼                                     │   │
│  │   ┌─────────────────────────────────────────────────┐   │   │
│  │   │  Performance Metrics Logging (Research Data)    │   │   │
│  │   │  • RMSE Comparison  • Processing Time           │   │   │
│  │   │  • Confidence Score • Noise Rejection Rate      │   │   │
│  │   └─────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Thành Phần Chính

| Component | Description | Lines of Code |
|-----------|-------------|---------------|
| `VariationalQuantumCircuit` | 4-qubit, 3-layer VQC với angle encoding | 370 |
| `QuantumKalmanFilter` | State estimation sử dụng VQE | - |
| `ShadowModeComparator` | Real-time QKF vs EKF comparison | - |
| `QuantumFilteringIntegration` | Integration vào hệ thống chính | 241 |

### Shadow Mode Operation

- **Không can thiệp**: Chạy song song với hệ thống điều khiển chính
- **So sánh thời gian thực**: QKF vs EKF performance
- **Thu thập dữ liệu**: Comprehensive metrics collection
- **Fallback**: Tự động chuyển sang Kalman cổ điển nếu cần

### Kết Quả Mong Đợi

- **Cải thiện độ chính xác**: Giảm nhiễu cảm biến MEMS
- **Benchmark hiệu suất**: So sánh quantum vs classical
- **Nghiên cứu thực tiễn**: Ứng dụng lượng tử trên edge device
- **Tài liệu mở**: Code và data cho cộng đồng nghiên cứu

---

## 🛡️ Hybrid GPS Denial System

**Giải pháp thực tế**: Tin tưởng EKF3 của Flight Controller, Pi chỉ làm việc nhẹ (phát hiện + cảnh báo), phi công quyết định.

> ⚠️ **TRIẾT LÝ THIẾT KẾ - GPS DENIAL:**
>
> **KHÔNG LÀM trên Pi:**
> - ❌ Tính toán lại vị trí (trùng lặp FC's EKF)
> - ❌ IMU Integration bằng Python (sai số tích lũy nhanh)
> - ❌ Gửi Position Command khi không có GPS (nguy hiểm)
> - ❌ Tự động RTH khi mất GPS (có thể bay sai hướng)
>
> **CHỈ LÀM trên Pi:**
> - ✅ Phát hiện GPS Anomaly (HDOP, satellite count, position jump)
> - ✅ Cảnh báo phi công ngay lập tức (âm thanh + màn hình)
> - ✅ Gửi Velocity/Heading Command nếu cần hỗ trợ
> - ✅ Hiển thị hướng về nhà trên màn hình FPV
>
> **PHI CÔNG quyết định:**
> - Chuyển FBWA/AltHold (cân bằng tự động)
> - Lái tay qua FPV về hướng nhà
> - Chờ GPS phục hồi → Gạt RTL

### Vấn Đề

Khi GPS bị phá sóng (jamming) hoặc giả mạo (spoofing), Flight Controller không thể RTH vì không biết vị trí. Đây là điểm yếu nghiêm trọng của UAV thương mại.

### Giải Pháp: Tin Tưởng FC + Phi Công Điều Khiển

> **Giao thức**: MAVLink 2.0 để đọc GPS_RAW_INT, ATTITUDE, VFR_HUD. Pi **CHỈ** phát hiện và cảnh báo. Phi công chuyển FBWA và lái tay về nhà.

#### Tham số ArduPilot EKF3:
```
EK3_ENABLE = 1              # Bật EKF3
AHRS_EKF_TYPE = 3           # Dùng EKF3  
EK3_SRC1_VELXY = 0          # None khi mất GPS (FC tự xử lý)
EK3_DRAG_BCOEF_X = 0.1      # Ước tính sức cản gió
EK3_DRAG_BCOEF_Y = 0.1      
FS_EKF_ACTION = 2           # Land khi EKF fail (an toàn nhất)
```

```
┌─────────────────────────────────────────────────────────────────┐
│           GPS DENIAL RESPONSE SYSTEM                            │
│                (Pilot-Assisted Recovery)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ╔═══════════════════════════════════════════════════════════╗ │
│  ║  LAYER 1: NORMAL MODE (GPS Available)                     ║ │
│  ║  └─► ArduPilot EKF3 Fusion                                ║ │
│  ║  └─► GPS + IMU + Barometer + Compass                      ║ │
│  ║  └─► Độ tin cậy: 100%                                     ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
│                          │                                      │
│         Pi phát hiện GPS Anomaly (Score > 50)                   │
│                          ▼                                      │
│  ╔═══════════════════════════════════════════════════════════╗ │
│  ║  LAYER 2: PILOT ALERT (GPS Denied)                        ║ │
│  ║  └─► Pi cảnh báo: "GPS LOST - SWITCH FBWA"                ║ │
│  ║  └─► Hiển thị hướng về nhà trên OSD                       ║ │
│  ║  └─► FC's EKF3 vẫn hoạt động (IMU + Compass + Baro)       ║ │
│  ║  └─► Phi công chuyển FBWA/AltHold                         ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
│                          │                                      │
│            Phi công lái tay về hướng nhà                        │
│                          ▼                                      │
│  ╔═══════════════════════════════════════════════════════════╗ │
│  ║  LAYER 3: GPS RECOVERY                                    ║ │
│  ║  └─► Bay ra khỏi vùng nhiễu                               ║ │
│  ║  └─► GPS phục hồi → Pi thông báo                          ║ │
│  ║  └─► Phi công gạt RTL → Về nhà tự động                    ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Phương Pháp Phát Hiện GPS Anomaly

> **Thuật toán phát hiện**: Hệ thống chấm điểm có trọng số. Tổng điểm > 50 = Cảnh báo phi công. Pi **CHỈ** phát hiện và cảnh báo, không tự động điều khiển.

| Phương pháp | Ngưỡng | Độ tin cậy | Trọng số |
|-------------|--------|------------|----------|
| Nhảy vị trí | >50m trong 1 lần cập nhật | Cao | 30 |
| Sai lệch vận tốc (GPS vs IMU) | >10 m/s | Cao | 25 |
| Mất vệ tinh đột ngột | ≥4 vệ tinh | Trung bình | 20 |
| HDOP tăng đột biến | >3.0 | Trung bình | 15 |
| Mất tín hiệu 3D Fix | fix_type < 3 | Cao | 30 |

### Quy Trình Xử Lý GPS Lost (Phi Công)

```
┌─────────────────────────────────────────────────────────────────┐
│  1. PI PHÁT HIỆN GPS LOST                                       │
│     └─► Cảnh báo âm thanh + Màn hình OSD                        │
│                          ▼                                      │
│  2. PHI CÔNG CHUYỂN MODE                                        │
│     └─► Gạt sang FBWA (Fly-By-Wire A) hoặc AltHold              │
│     └─► FC tự cân bằng, phi công điều khiển hướng               │
│                          ▼                                      │
│  3. PHI CÔNG LÁI TAY VỀ NHÀ                                     │
│     └─► Nhìn FPV Camera hoặc bản đồ telemetry                   │
│     └─► Giữ heading về hướng nhà                                │
│     └─► Duy trì độ cao an toàn                                  │
│                          ▼                                      │
│  4. CHỜ GPS PHỤC HỒI                                            │
│     └─► Bay ra khỏi vùng nhiễu (jamming zone)                   │
│     └─► Pi thông báo "GPS OK"                                   │
│                          ▼                                      │
│  5. GẠT RTL                                                     │
│     └─► Khi GPS ổn định → Chuyển RTL                            │
│     └─► FC tự động về nhà và hạ cánh                            │
└─────────────────────────────────────────────────────────────────┘
```

### Tại Sao Không Tự Động RTH Khi Mất GPS?

| Phương án | Rủi ro | Quyết định |
|-----------|--------|------------|
| **Tự động RTH bằng Dead Reckoning** | Sai số tích lũy → Bay sai hướng → Mất máy bay | ❌ Không dùng |
| **Tự động Land tại chỗ** | Có thể land vào vùng nguy hiểm | ⚠️ Chỉ khi EKF fail |
| **Phi công điều khiển** | Phi công thấy FPV, biết tình huống | ✅ An toàn nhất |

### Tích Hợp Cảm Biến Tốc Độ Khí

> **Vai trò của Airspeed Sensor**: Khi mất GPS, FC's EKF3 dùng airspeed để ước lượng ground speed (kết hợp với wind estimation). Phi công dựa vào airspeed để duy trì tốc độ an toàn khi lái tay.

| Cảm biến | Mã | Địa chỉ I2C | Chức năng |
|-----------|-----|-------------|----------|
| Áp suất vi sai | MS4525DO | 0x28 | Đo chênh áp từ ống Pitot |
| Ống Pitot | Tiêu chuẩn | - | Thu áp động cho tốc độ khí |
| Dải đo | -1 đến 1 PSI | - | 0-100 m/s |

---

## 🖥️ Trạm Điều Khiển Mặt Đất

---

## 🖥️ Trạm Điều Khiển Mặt Đất

**Chiến lược thực tế**: Dùng công cụ có sẵn, KHÔNG viết lại Mission Planner.

> ⚠️ **Quyết định quan trọng (01/12/2025)**: Hủy bỏ kế hoạch GCS Desktop PyQt6.
> 
> **Lý do**: Viết lại Mission Planner (3D View, Google Maps, MAVLink handler ~4000 dòng code)
> là **lãng phí 2+ tháng** cho thứ **KHÔNG GIÚP MÁY BAY BAY TỐT HƠN**.

### Phân Công Công Cụ

| Nhiệm vụ | Công cụ | Lý do |
|----------|---------|-------|
| Bản đồ, waypoint | **Mission Planner** | Đã hoàn hảo, không cần viết lại |
| Telemetry, cảm biến | **Mission Planner** | Real-time graphs có sẵn |
| 3D View máy bay | **Mission Planner** | OpenGL đã implement |
| Cài đặt ArduPilot | **Mission Planner** | Full Parameter Tree |
| **Video AI Stream** | **Flask Web Server** | Custom - không có trong MP |
| **Target Detection Log** | **Flask Web Server** | Custom - AI tracking data |
| **Web Dashboard** | **Flask Web Server** | Remote monitoring |

### Flask Web Server

```
ground_station/src/web_server/
├── app.py                      # REST API (387 lines)
│   ├── /api/telemetry         # Lấy dữ liệu telemetry
│   ├── /api/targets           # Danh sách mục tiêu AI
│   ├── /api/stream            # Video stream endpoint
│   └── /api/logs              # Flight logs
│
└── templates/
    └── dashboard.html          # Web dashboard (427 lines)
        ├── Video Stream Panel  # AI annotated video
        ├── Target Log Panel    # Detection history
        └── Basic Telemetry     # GPS, altitude, battery
```

> **Lưu ý**: Video AI và Target Log là những thứ Mission Planner KHÔNG CÓ.
> Đây mới là giá trị thực sự của Flask Web Server trong dự án này.

---

## 🔒 Logic An Toàn & Failsafe

**Ra quyết định tự động dựa trên máy trạng thái**

> **Triển khai**: Máy trạng thái Python asyncio với vòng lặp chính 50Hz. Các chuyển đổi trạng thái được định nghĩa rõ ràng, có bảo vệ quá thời gian. Mỗi tình huống có mức độ ưu tiên, sự kiện ưu tiên cao có thể ngắt sự kiện ưu tiên thấp hơn. Tất cả quyết định của AI đều được ghi nhật ký để phân tích.

```
┌─────────────────────────────────────────────────────────────────┐
│                   MÁY TRẠNG THÁI FAILSAFE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  TÌNH HUỐNG 1: Mất RC, Còn 5G                           │   │
│  │  ───────────────────────────────────────────────────────│   │
│  │  Hành động: LOITER → Cảnh báo GCS → Chuyển điều khiển 5G│   │
│  │  Phi công có thể điều khiển qua laptop/điện thoại       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  TÌNH HUỐNG 2: Mất tất cả kết nối                       │   │
│  │  ───────────────────────────────────────────────────────│   │
│  │  Hành động: Tăng cao 50m → RTH → Hạ cánh tại nhà        │   │
│  │  Tự động quay về, không cần can thiệp phi công          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  TÌNH HUỐNG 3: Pin yếu, xa nhà                          │   │
│  │  ───────────────────────────────────────────────────────│   │
│  │  Hành động: Tính năng lượng → Nếu không đủ:             │   │
│  │          Tìm vùng hạ cánh khẩn cấp → Hạ cánh            │   │
│  │  Quyết định dựa trên năng lượng, không chỉ ngưỡng điện  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  TÌNH HUỐNG 4: Phát hiện nhiễu/giả mạo GPS              │   │
│  │  ───────────────────────────────────────────────────────│   │
│  │  Hành động: Kích hoạt DR → Tăng cao +30m → Quay 180°    │   │
│  │          → Thoát vùng nhiễu → Cảnh báo phi công         │   │
│  │  Khả năng độc đáo không có ở UAV thương mại             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  GEOFENCING: Dựa trên đa giác với nhiều hành động       │   │
│  │  ───────────────────────────────────────────────────────│   │
│  │  • CẢNH BÁO: Chỉ cảnh báo                               │   │
│  │  • LOITER: Dừng tại ranh giới                           │   │
│  │  • RTH: Quay về nhà                                     │   │
│  │  • HẠ CÁNH: Hạ cánh khẩn cấp                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Thông Số Kỹ Thuật

### Khung thân & Nguồn

| Thành phần | Thông số |
|------------|----------|
| **Loại** | BWB Flying Wing cải tiến + Đuôi đứng |
| **Sải cánh** | ~1400mm (tối ưu cho tải trọng) |
| **Trọng lượng cất cánh tối đa** | ~6 kg (AUW - All Up Weight) |
| **Thời gian bay** | 25-30 phút |
| **Tốc độ hành trình** | 50-80 km/h |
| **Động cơ** | 2x DXW D4250 600KV (cấu hình đẩy) |
| **ESC** | 2x 100A OPTO BLHeli_S |
| **Pin** | 2x CNHL 6S 5200mAh 65C (6S2P = 10400mAh) |
| **Cánh quạt** | 2x 13x8 Sợi carbon |

### Mặt điều khiển (Kiểu Horten 229 Split Elevon)

| Servo | Vị trí | Chức năng ArduPilot |
|-------|--------|--------------------|
| MG996R #1 | Elevon ngoài trái | SERVO3 = 77 |
| MG996R #2 | Elevon ngoài phải | SERVO4 = 78 |
| MG996R #3 | Elevon trong trái | SERVO5 = 79 |
| MG996R #4 | Elevon trong phải | SERVO6 = 80 |

**Ưu điểm Split Elevon:**
- Tăng diện tích điều khiển (4 servo thay vì 2)
- Cải thiện tốc độ lật và khả năng điều khiển pitch
- Dự phòng: 1 servo hỏng vẫn điều khiển được
- Phù hợp thiết kế Horten 229 với cánh lớn

### Điện tử hàng không

| Linh kiện | Mã | Thông số |
|----------|-----|----------|
| **Bộ điều khiển bay** | LANRC F4 V3S Plus | ArduPlane, MPU6000 IMU |
| **GPS** | NEO-M8N | Ublox, 72 kênh, 10Hz |
| **La bàn** | QMC5883L | I2C ngoài @ 0x0D |
| **LiDAR** | VL53L1X | ToF, 0.04-4m |
| **Cảm biến tốc độ khí** | MS4525DO | Áp suất vi sai, ống Pitot |
| **Điều khiển từ xa** | ELRS 2.4GHz | RadioMaster Pocket + XR1 Nano |

### Máy tính đi kèm

| Linh kiện | Mã | Chức năng |
|----------|-----|----------|
| **Máy tính** | Raspberry Pi 3B+ | AI, MAVLink, Nghiên cứu lượng tử |
| **Camera** | OV5647 (Pi Camera v1) | 5MP, 1080p30, nhận dạng vật thể |
| **Modem** | USB Dongle 5G | Liên lạc BVLOS |

### Hệ thống hộp đen (ESP32 - Độc lập)

| Linh kiện | Mã | Ghi chú |
|----------|-----|--------|
| Bộ điều khiển | ESP32-CAM | Ghi log, tải GPS qua HTTP |
| IMU | GY-9250 | MPU9250 9 trục, độc lập |
| Siêu âm | HC-SR04 | Ghi khoảng cách |
| Lưu trữ | Thẻ SD | Lưu dữ liệu bay |

> **Ghi chú**: Hộp đen dùng nguồn riêng và có thể tháo rời khỏi UAV. Chỉ gắn trong các chuyến bay thử nghiệm để thu thập dữ liệu.

### Sơ đồ kết nối Servo (Mission Planner)

```
Ngõ ra động cơ:
  M1 (SERVO1) ─── Động cơ trái (D4250 600KV)
  M2 (SERVO2) ─── Động cơ phải (D4250 600KV)

Ngõ ra Servo (Split Elevon):
  M3 (SERVO3) ─── Elevon ngoài trái (MG996R) ─── Chức năng 77
  M4 (SERVO4) ─── Elevon ngoài phải (MG996R) ─── Chức năng 78
  M5 (SERVO5) ─── Elevon trong trái (MG996R) ─── Chức năng 79
  M6 (SERVO6) ─── Elevon trong phải (MG996R) ─── Chức năng 80
```

---

## 📈 Thống Kê Mã Nguồn

### Tổng số dòng mã

| Module | Số file | Tổng dòng | Mô tả |
|--------|----------|------------|-------|
| **Điều hướng** | 5 | ~2,500+ | GPS denial, tự động, định vị |
| **Lượng tử** | 3 | ~850+ | QKF, tích hợp, trôi IMU |
| **An toàn** | 3 | ~600+ | Geofencing, pin, GPS denial |
| **AI** | 4 | ~800+ | Nhận dạng vật thể, theo dõi |
| **GCS Desktop** | 6 | ~4,000+ | Giao diện, xử lý, ghi log |
| **GCS Web** | 2 | ~800+ | Flask API, bảng điều khiển |
| **Tính toán thiết kế** | 6 | ~1,000+ | Khí động học, CG, mô phỏng |
| **Tổng** | **29+** | **~10,500+** | |

### Các file chính

| File | Dòng | Ý nghĩa |
|------|------|--------|
| `hybrid_gps_denial_system.py` | 1,048 | Hệ thống điều hướng phức tạp nhất |
| `main_window.py` | 1,161 | Giao diện GCS đầy đủ |
| `styles.py` | 761 | Quản lý giao diện |
| `config_manager.py` | 656 | Hệ thống cấu hình |
| `mavlink_handler.py` | 595 | Giao tiếp MAVLink |
| `data_logger.py` | 590 | Ghi dữ liệu bay |

---

## 🎓 Đóng Góp Nghiên Cứu

### Lọc Nhiễu Lấy Cảm Hứng Lượng Tử
- **Triển khai đầu tiên** Variational Quantum Circuits cho lọc nhiễu cảm biến MEMS trên thiết bị biên
- **Khung so sánh chế độ bóng** cho đánh giá hiệu suất cổ điển vs lượng tử thời gian thực
- **Mã nguồn mở** và dữ liệu cho cộng đồng nghiên cứu

### Điều Hướng Khi GPS Bị Từ Chối
- **Hệ thống dự phòng 3 tầng** với chuyển chế độ tự động
- **Điều chỉnh ML thích ứng** với kiến trúc hỗn hợp biên/máy chủ
- **Tích hợp cảm biến tốc độ khí** để cải thiện độ chính xác Dead Reckoning

### Xử Lý AI Biên
- **Nhận dạng vật thể thời gian thực** trên Raspberry Pi với TFLite
- **Đường ống đa luồng** cho camera, AI, và truyền thông
- **Kết hợp định vị** để ước tính tọa độ mục tiêu

---

## 📝 Nhiệm Vụ Hỗ Trợ

Thiết kế dạng module cho phép thay đổi cấu hình tùy theo mục đích:

| Nhiệm vụ | Mô tả |
|----------|-------|
| **Trinh sát Thời gian thực** | AI trên máy tính nhúng phát hiện vật thể, gửi cảnh báo tọa độ về GCS qua 5G |
| **Lập bản đồ** | Thu thập ảnh độ phân giải cao + log GPS đồng bộ, phục vụ dựng mô hình địa hình |
| **Nghiên cứu Quantum Filtering** | Thử nghiệm VQC cho lọc nhiễu cảm biến MEMS trong điều kiện thực tế |
| **Auto Landing** (Nâng cao) | Hạ cánh an toàn, sử dụng phân tích ảnh để tìm đường băng |
| **Trinh sát định kỳ** (Nâng cao) | Tự cất cánh theo lịch, bay đến các vị trí định trước, chụp ảnh, gửi lên web |

---

## 🚀 Kết Luận

Dự án Flying Wing UAV không chỉ là một chiếc máy bay điều khiển từ xa - đó là một **hệ thống nghiên cứu và trinh sát hoàn chỉnh** với:

1. **Edge AI** - Xử lý AI hoàn toàn trên máy bay (TFLite MobileNet SSD)
2. **Quantum Research** - Nghiên cứu ứng dụng lượng tử thực tiễn (VQC-based KF)
3. **GPS Denial Resilience** - Khả năng chống phá sóng (EKF3 + Pilot Alert)
4. **Autonomous Decision Making** - Ra quyết định thông minh dựa trên tình huống
5. **TRUE Async Verification** - Time Machine Buffer giải quyết latency mismatch

> **"Cất cánh là tùy chọn, nhưng hạ cánh là bắt buộc."**
>
> **"We don't just build UAVs that fly - we build systems that think and research."**

---

## 📚 Tài Liệu Quan Trọng

### Documentation Map

| File | Mô tả | Đường dẫn |
|------|-------|-----------|
| 📋 **PROJECT_PORTFOLIO.md** | Tổng quan dự án, kiến trúc, tính năng | `docs/PROJECT_PORTFOLIO.md` |
| 📊 **PROJECT_PROGRESS.md** | Tiến độ dự án, trạng thái modules | `docs/PROJECT_PROGRESS.md` |
| 🏗️ **ARCHITECTURE.md** | Kiến trúc hệ thống chi tiết | `docs/technical/ARCHITECTURE.md` |
| 📡 **COMMUNICATION_PROTOCOL.md** | Giao thức MAVLink & 5G | `docs/technical/COMMUNICATION_PROTOCOL.md` |
| 🛡️ **GEOFENCING.md** | Hệ thống geofence và safety | `docs/technical/GEOFENCING.md` |
| 🌐 **WEB_SERVER.md** | Web server documentation | `docs/technical/WEB_SERVER.md` |

> **Lưu ý**: GCS Desktop (PyQt6) đã được hủy bỏ. Dùng Mission Planner + Flask Web Server.

### Testing & Deployment

| File | Mô tả | Đường dẫn |
|------|-------|-----------|
| 🧪 **PRE_INTEGRATION_TEST_PLAN.md** | Kế hoạch test tích hợp | `docs/testing/PRE_INTEGRATION_TEST_PLAN.md` |
| ✅ **PRE_FLIGHT_CHECKLIST.md** | Checklist trước khi bay | `docs/testing/PRE_FLIGHT_CHECKLIST.md` |
| 🔬 **COMPANION_TESTING.md** | Test companion computer | `docs/testing/COMPANION_TESTING.md` |
| 📦 **COMPANION_DEPLOYMENT.md** | Deployment companion | `docs/deployment/COMPANION_DEPLOYMENT.md` |
| 🍓 **RASPBERRY_PI_DEPLOYMENT.md** | Deployment Raspberry Pi | `docs/deployment/RASPBERRY_PI_DEPLOYMENT.md` |
| 📖 **INSTALLATION_GUIDE.md** | Hướng dẫn cài đặt | `docs/deployment/INSTALLATION_GUIDE.md` |

### Hardware & Design

| File | Mô tả | Đường dẫn |
|------|-------|-----------|
| 🔌 **HARDWARE_WIRING_GUIDE.md** | Sơ đồ đấu nối phần cứng | `docs/hardware/HARDWARE_WIRING_GUIDE.md` |
| 📊 **flowchart.md** | Flowchart hệ thống | `docs/design/flowchart.md` |
| 📝 **Design_note.txt** | Ghi chú thiết kế & so sánh | `docs/design/Design_note.txt` |
| 🎮 **RADIO_MASTER_CHANNEL_MIXES.md** | Hướng dẫn setup tay cầm RC | `docs/hardware/RADIO_MASTER_CHANNEL_MIXES.md` |

### Quantum EKF Documentation

| File | Mô tả | Đường dẫn |
|------|-------|-----------|
| ⚛️ **EKF_IMPLEMENTATION_PLAN.md** | Kế hoạch implement EKF | `companion_computer/docs/technical/EKF_IMPLEMENTATION_PLAN.md` |
| 🚀 **EKF_DEPLOYMENT_ROADMAP.md** | Roadmap triển khai EKF | `companion_computer/docs/technical/EKF_DEPLOYMENT_ROADMAP.md` |

---

<div align="center">

**Trương Công Định & Đặng Duy Long**

*Date: December 2025*

*Version: 1.0.1 (Initial Release - 01/12/2025)*

**BOM List Chi Tiết**: Xem file `FlyingWing_BOM.csv`

</div>
