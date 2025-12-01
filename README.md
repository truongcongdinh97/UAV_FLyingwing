# Flying Wing UAV - Dự Án Trinh Sát & Lập Bản Đồ Động Cơ Kép

## I. Giới Thiệu Chung

Phát triển một chiếc UAV cánh bay (Flying Wing) sử dụng động cơ kép (Twin-Engine). Phục vụ các công việc trinh sát tự hành, lập bản đồ và xử lý AI ngay trên thiết bị (Edge Computing).

### 1. Thông Số Kỹ Thuật
*   **Cấu hình khí động học**: Modified Blended Wing Body (BWB) with Vertical Stabilizers (Thân cánh liền khối cải tiến tích hợp cánh ổn định dọc).
*   **Kiểu dáng**: Lấy cảm hứng từ Horten Ho 229.
*   **Profile cánh (Airfoil)**: NACA 4412.
*   **Sải cánh**: 2200mm (2.2m).
*   **Thời gian bay**: Khoảng 60-90 phút (với pin 6S2P).
*   **Tải trọng**: 3.5-4.0 kg.
*   **Tốc độ hành trình**: 50-80 km/h.
*   **Động lực**: 2x động cơ D4250 600KV, sử dụng lực đẩy vi sai (differential thrust) để điều hướng.
*   **Mặt điều khiển**: 4x servo MG996R cấu hình Split Elevon (Horten 229 style) - 2 outer + 2 inner.
*   **Pin**: Pack Li-ion 6S2P 10400mAh (2x CNHL 6S 5200mAh 65C mắc song song).
*   **Flight Controller (FC)**: LANRC F4 V3S Plus (STM32F405) - ArduPlane/Mission Planner.
*   **GPS**: NEO-M8N (Ublox M8N) + Compass QMC5883L.
*   **Radio**: Radiomaster Pocket TX + XR1 Nano RX (ELRS 2.4GHz).
*   **Companion Computer**: Raspberry Pi 3B+ với camera OV5647.

### 2. Tính Năng Nổi Bật
*   **Bay tự hành**: Tự động bay theo các điểm waypoint và bám đường bay đã lập trình.
*   **Loiter Mode**: Bay vòng tròn quanh một điểm để quan sát liên tục.
*   **Differential Thrust**: Điều khiển hướng (yaw) bằng cách tăng/giảm ga từng động cơ, không cần bánh lái (rudder) cơ khí.
*   **AI tại biên**: Nhúng model TensorFlow Lite lên Pi để nhận diện vật thể thời gian thực.
*   **An toàn**: Hàng rào ảo (Geofencing) đa giác, tự động tính toán năng lượng pin để RTH (Return-to-Home).
*   **Kết nối**: Dùng MAVLink qua UART giữa FC và Pi, và đẩy dữ liệu về trạm mặt đất qua 5G/WiFi.

---

## II. Kiến Trúc Hệ Thống

### 1. Flight Controller (Firmware)
Mình đã chuyển sang dùng **ArduPilot (ArduPlane)** thay vì iNav để hỗ trợ tốt hơn cho MAVLink và Twin Engine.
*   **Phần cứng**: LANRC F4 V3S Plus.
*   **Tính năng**: Hỗ trợ native Differential Thrust, Geofence 3D, Terrain Following.
*   **Failsafe**: Tự động RTL (Return to Launch) khi mất tín hiệu hoặc pin yếu.

### 2. Companion Computer (Raspberry Pi)
Đây là "bộ não" xử lý các tác vụ cao cấp.
*   **AI**: Chạy model MobileNet SSD để soi vật thể từ camera.
*   **Dẫn đường**: Tính toán đường bay phức tạp rồi gửi lệnh xuống FC.
*   **An toàn**: Giám sát xem máy bay có bay ra khỏi vùng an toàn (Geofence) hay không.
*   **Giao tiếp**: Cầu nối đẩy dữ liệu từ FC về máy tính qua 5G.

### 3. Ground Control Station (GCS)
Giao diện web để mình ngồi dưới đất giám sát.
*   **Web Server**: Viết bằng Flask (Python).
*   **Dashboard**: Hiển thị bản đồ, video stream và thông số bay (pin, tốc độ, độ cao).
*   **Mission Planner**: Chỗ để vẽ đường bay và upload lên máy bay.

---

## III. Phần Firmware (ArduPilot)

Sử dụng ArduPlane firmware cho khả năng bay tự hành chuyên nghiệp. Cấu hình qua **Mission Planner**.

### 1. Cấu hình Twin Engine (Differential Thrust)
*   **Motor Outputs**: 
    *   `SERVO1_FUNCTION` = 73 (ThrottleLeft) - Left Motor D4250 600KV
    *   `SERVO2_FUNCTION` = 74 (ThrottleRight) - Right Motor D4250 600KV
    *   `RUDD_DT_GAIN` = 10-50 (Độ nhạy lái hướng bằng chênh lệch ga)

### 2. Cấu hình Split Elevon (4 Servo - Kiểu Horten 229)
Sử dụng 4 servo MG996R cho cấu hình Split Elevon, tăng diện tích điều khiển và redundancy:
*   **Outer Elevons (Primary)**:
    *   `SERVO3_FUNCTION` = 77 (Elevon Left) - Left Outer Elevon
    *   `SERVO4_FUNCTION` = 78 (Elevon Right) - Right Outer Elevon
*   **Inner Elevons (Secondary)**:
    *   `SERVO5_FUNCTION` = 79 (Elevon Left 2) - Left Inner Elevon
    *   `SERVO6_FUNCTION` = 80 (Elevon Right 2) - Right Inner Elevon

*   **Ưu điểm Split Elevon**:
    *   Tăng roll rate và pitch authority cho cánh lớn 2.2m
    *   Redundancy: 1 servo hỏng vẫn điều khiển được
    *   Giảm tải trọng trên mỗi servo

### 3. Kết nối Companion
*   Cổng UART (TELEM1/2) cấu hình MAVLink 2.
*   Baudrate: 921600.

---

## IV. Phần Mềm Trên Pi (Companion)

Toàn bộ code trên Pi được viết bằng Python, chia thành các module để quản lýd.

### 1. Các Module Chính
a.  **AI & Camera (`src/ai`, `src/camera`)**:
    *   Lấy hình từ Picamera2.
    *   TensorFlow Lite để nhận diện.
    *   Gắn tọa độ GPS vào vật thể tìm thấy.

b.  **Dẫn Đường (`src/navigation`)**:
    *   `PathFollower`: Thuật toán bám điểm (Cso thể nâng cấp bám theo mục tiêu).
    *   `LoiterController`: Logic bay vòng tròn.

c.  **An Toàn (`src/safety`)**:
    *   `Geofencing`: Vẽ vùng đa giác, bay ra ngoài là tự RTH hoặc hạ cánh ngay.
    *   `BatteryFailsafe`: Tính toán xem còn đủ pin về nhà không. Nếu không là hạ cánh khẩn cấp luôn.

d.  **Giao Tiếp (`src/communication`)**:
    *   `MAVLinkHandler`: Giao tieesp với FC qua cổng Serial.
    *   `HTTPClient`: Gửi data về server qua 5G.

e.  **Lập Lịch (`src/scheduler`)**:
    *   Hẹn giờ tự động bay đi tuần tra (ví dụ 6h sáng hàng ngày).

### 2. Triển Khai
*   **OS**: Raspberry Pi OS Lite (64-bit).
*   **Thư viện**: Python 3.9+, OpenCV, TFLite, PyMAVLink.
*   **Tự chạy**: Mình đã config service systemd (`uav-companion.service`).

---

## V. Trạm Mặt Đất (Web Dashboard)

Giao diệm điều khiển

### 1. Giao Diện Web
*   **Tech stack**: Backend Flask, Frontend HTML/JS đơn giản.
*   **Chức năng**:
    *   Bản đồ Leaflet.js hiện vị trí máy bay.
    *   Xem thông số: Pin, tốc độ, độ cao.
    *   Nút bấm: Arm, Cất cánh, Về nhà (RTH).
    *   Xem lại ảnh trinh sát đã chụp.

### 2. Kết Nối
*   Dùng REST API để nhận ảnh/data.
*   Dùng Socket.IO để cập nhật thông số thời gian thực cho mượt.

---

## VI. Hệ Thống An Toàn (Safety First)


### 1. Hàng Rào Ảo (Geofencing)
Hỗ trợ vẽ đa giác phức tạp (để tránh khu dân cư hay vùng cấm bay).
*   **Xử lý**: Cảnh báo -> Bay chờ -> RTH -> Hạ cánh khẩn cấp.
*   **3D**: Giới hạn cả độ cao trần.

### 2. Giám Sát Pin Thông Minh
Không chỉ nhìn số Vol, hệ thống tính toán năng lượng tiêu thụ.
*   **Logic**: Luôn tính xem "với mức pin hiện tại có đủ bay về nhà không?".
*   **Kích hoạt**: Nếu pin chỉ vừa đủ về là nó ép máy bay quay về ngay.

### 3. Checklist Trước Bay
Quy trình:
*   Check áp từng cell pin.
*   Chờ GPS bắt đủ 6 vệ tinh trở lên.
*   Thử lắc máy bay xem cánh lái phản hồi đúng không.
*   Test thử nút Failsafe trên tay khiển.

---

## VII. Giao Thức Kết Nối

Hệ thống dùng kết hợp 2 loại giao thức.

### 1. Nội Bộ (FC <-> Pi)
*   Dùng **MAVLink v2.0** qua dây UART (tốc độ 115200).
*   Trao đổi các tin: Heartbeat, Góc bay (Attitude), Tọa độ (GPS), Pin.

### 2. Ra Ngoài (Pi <-> Laptop)
*   Dùng **HTTP/WebSocket** qua mạng 5G/WiFi.
*   Gửi về: JSON thông số, Ảnh JPEG, Lệnh điều khiển.

---

## VIII. Hướng Dẫn Cài Đặt

### 1. Setup Firmware (ArduPilot)
1.  Tải và cài đặt **Mission Planner**.
2.  Kết nối mạch F4 qua USB.
3.  Vào Setup -> Install Firmware -> Chọn **ArduPlane**.
4.  Flash firmware mới nhất cho mạch (MatekF405-SE hoặc tương đương).
5.  Vào Config/Tuning -> Full Parameter List để setup các tham số `SERVO_FUNCTION`.

### 2. Setup Raspberry Pi
1.  Cài Raspberry Pi OS Lite vào thẻ nhớ.
2.  Bật UART và Camera trong `raspi-config`.
3.  Copy thư mục `companion_computer` vào Pi.
4.  Cài thư viện: `pip install -r requirements.txt`.
5.  Bật service lên để nó tự chạy.

### 3. Setup Web Server
1.  Cài thư viện trên máy tính: `pip install -r ground_station/requirements_web.txt`.
2.  Chạy server: `python ground_station/src/web_server/app.py`.
3.  Mở trình duyệt: `http://localhost:5000`.

---

## IX. Quy Trình Bay

### 1. Chuẩn Bị
*   Bật Web Server trên laptop.
*   Cắm pin máy bay.
*   Chờ GPS lock (đèn xanh đứng).
*   Nhìn lên web thấy hiện thông số là OK.

### 2. Bay
*   **Tay**: Radiomaster pocket TX.
*   **Tự động**: Lên trời rồi thì gạt switch sang Auto hoặc upload nhiệm vụ.
*   **Giám sát**: Mắt luôn nhìn máy bay, thỉnh thoảng liếc màn hình check pin.

### 3. Thu Quân
*   Tải log từ Pi về để phân tích.
*   Kiểm tra xem cánh hay thân vỏ.
*   Xả pin.

---

## X. Tình Trạng Dự Án

Cập nhật: **01/12/2025** - Version 1.0.1 (Initial Release)

### ✅ Hoàn thành

| Module | File chính | Dòng code | Trạng thái |
|--------|-----------|-----------|------------|
| **AI Detection** | `ai/adaptive_detector.py` | 1,305 | ✅ |
| **Object Tracking** | `ai/optimized_tracker.py` | 422 | ✅ |
| **MAVLink** | `communication/mavlink_handler.py` | 535 | ✅ |
| **Navigation** | `navigation/autonomous.py` | 329 | ✅ |
| **GPS Monitor** | `safety/gps_monitor.py` | 369 | ✅ |
| **Geofencing** | `safety/geofencing.py` | 550 | ✅ |
| **Battery Failsafe** | `safety/battery_failsafe.py` | 480 | ✅ |
| **Mission Scheduler** | `scheduler/mission_scheduler.py` | 540 | ✅ |
| **Quantum EKF** | `quantum/quantum_kalman_filter.py` | 353 | ✅ |
| **Flask Web Server** | `web_server/app.py` | 344 | ✅ |

### 📊 Tổng kết

- **Tổng dòng code**: ~12,000+ lines Python
- **Companion Computer**: ~10,300 lines
- **Ground Station**: ~1,450 lines
- **Tiến độ**: 95%

### 🔧 Quyết định quan trọng (01/12/2025)

1. **Hủy bỏ GCS Desktop PyQt6** - Viết lại Mission Planner là lãng phí
2. **Dùng Mission Planner** - Cho giám sát bay, bản đồ, telemetry
3. **Flask Web Server** - Chỉ cho Video AI Stream + Target Log
4. **GPS Denial mới** - Trust FC's EKF3, Pi chỉ monitor + cảnh báo

---

## XI. Quantum-inspired Kalman Filter

### 🎯 Mục Tiêu Nghiên Cứu

Module này triển khai **Quantum-inspired Kalman Filter (QKF)** sử dụng **Variational Quantum Circuits (VQC)** cho việc lọc nhiễu phi tuyến tính của cảm biến MEMS rẻ tiền trong ứng dụng UAV.

**Câu hỏi nghiên cứu chính:**
- Thuật toán lượng tử có thể cải thiện lọc nhiễu cho cảm biến MEMS giá rẻ không?
- Bộ lọc dựa trên VQC so sánh thế nào với EKF cổ điển trong môi trường edge computing?
- Giới hạn thực tế của thuật toán lượng tử trên phần cứng hạn chế tài nguyên?

### 🧠 Phương Pháp Kỹ Thuật

#### 1. Kiến Trúc Variational Quantum Circuit
- **Qubits**: Hệ thống 4-qubit đại diện cho không gian trạng thái
- **Layers**: 3 lớp biến phân với các phép quay được tham số hóa
- **Entanglement**: Kết nối tuyến tính cho mô phỏng hiệu quả
- **Observable**: Đo lường Pauli-Z cho ước lượng trạng thái

#### 2. Hoạt Động Shadow Mode
- **So sánh thời gian thực**: QKF chạy song song với EKF tiêu chuẩn của ArduPilot
- **Không can thiệp**: Không ảnh hưởng đến hệ thống điều khiển bay
- **Thu thập dữ liệu**: Các chỉ số hiệu suất toàn diện
- **Fallback**: Tự động chuyển sang Kalman cổ điển nếu lượng tử thất bại

#### 3. Mô Hình Nhiễu MEMS
- **Nhiễu Gaussian**: Nhiễu cảm biến tiêu chuẩn
- **Bias Drift**: Độ lệch phi tuyến thay đổi theo thời gian
- **Cross-coupling**: Hiệu ứng giao thoa cảm biến
- **Ảnh hưởng nhiệt độ**: Mô phỏng drift nhiệt

### 📊 Chỉ Số Hiệu Suất

#### Chỉ Số Chính
- **Độ chính xác ước lượng trạng thái**: RMSE so với ground truth
- **Giảm nhiễu**: Cải thiện tỷ lệ tín hiệu-nhiễu
- **Thời gian xử lý**: So sánh lượng tử vs cổ điển
- **Điểm tin cậy**: Chỉ số độ tin cậy của bộ lọc

#### Chỉ Số Phụ
- **Sử dụng tài nguyên**: CPU, bộ nhớ, tiêu thụ điện năng
- **Hành vi hội tụ**: Độ ổn định tối ưu hóa lượng tử
- **Độ bền**: Hiệu suất trong các điều kiện nhiễu khác nhau

### 🛠️ Chi Tiết Triển Khai

#### Thành Phần Chính

##### 1. Lớp QuantumKalmanFilter
```python
class QuantumKalmanFilter:
    def predict(self, dt: float) -> np.ndarray
    def update_quantum(self, measurement: np.ndarray, dt: float) -> np.ndarray
    def update_classical(self, measurement: np.ndarray, dt: float) -> np.ndarray
```

##### 2. Lớp VariationalQuantumCircuit
```python
class VariationalQuantumCircuit:
    def build_circuit(self, initial_state: np.ndarray) -> QuantumCircuit
    def run_vqe(self, observable: SparsePauliOp, initial_point: np.ndarray) -> float
```

##### 3. Lớp ShadowModeComparator
```python
class ShadowModeComparator:
    def process_comparison(self, sensor_data, ekf_state, ekf_confidence, ekf_time)
    def generate_performance_report(self) -> Dict
```

### 🔬 Thiết Lập Thí Nghiệm

#### Môi Trường Phần Cứng
- **Companion Computer**: Raspberry Pi 3B+
- **Flight Controller**: LANRC F4 V3S Plus (có barometer tích hợp)
- **Cảm biến**: QMC5883L (Compass), VL53L1X (Lidar)
- **Lưu ý**: IMU sử dụng từ Flight Controller LANRC F4 V3S Plus (có MPU6000 tích hợp)
- **Giao tiếp**: UART cho MAVLink, 5G cho truyền dữ liệu

#### Stack Phần Mềm
- **Quantum Framework**: Qiskit Aer (simulator)
- **Baseline cổ điển**: Standard Kalman Filter
- **Xử lý dữ liệu**: NumPy, SciPy
- **Trực quan hóa**: Matplotlib (cho phân tích)

### 📈 Kết Quả Mong Đợi

#### Đóng Góp Kỹ Thuật
1. **Phương pháp lọc mới**: Ứng dụng đầu tiên của VQC cho sensor fusion MEMS trong UAV
2. **Benchmark hiệu suất**: So sánh định lượng với phương pháp cổ điển
3. **Phân tích tài nguyên**: Giới hạn thực tế của thuật toán lượng tử trên thiết bị biên
4. **Đặc trưng nhiễu**: Hiểu biết về lợi thế lượng tử cho các loại nhiễu cụ thể

#### Ý Nghĩa Thực Tiễn
- **Cải thiện ước lượng trạng thái**: Ước lượng attitude và position tốt hơn
- **Giảm chi phí**: Tiềm năng sử dụng cảm biến rẻ hơn với bộ lọc lượng tử
- **Nền tảng nghiên cứu**: Cơ sở cho các hệ thống navigation tăng cường lượng tử trong tương lai

### 🚀 Sử Dụng

#### Tích Hợp Cơ Bản
```python
from src.quantum.quantum_integration import QuantumFilteringIntegration

# Khởi tạo quantum filtering
quantum_integration = QuantumFilteringIntegration()

# Thêm dữ liệu cảm biến (shadow mode)
quantum_integration.add_imu_data(sensor_readings)
quantum_integration.add_ekf_data(ekf_state, confidence, processing_time)

# Bắt đầu xử lý
quantum_integration.start_shadow_mode()
```

#### Giám Sát Hiệu Suất
```python
# Lấy so sánh mới nhất
comparison = quantum_integration.get_latest_comparison()

# Tạo báo cáo hiệu suất
report = quantum_integration.comparator.generate_performance_report()
```

### ⚠️ Giới Hạn & Hướng Phát Triển

#### Giới Hạn Hiện Tại
- **Chỉ mô phỏng**: Không có truy cập phần cứng lượng tử thật
- **Chi phí tính toán**: Overhead đáng kể trên Raspberry Pi
- **Độ sâu mạch**: Bị giới hạn bởi khả năng mô phỏng cổ điển
- **Mô hình nhiễu**: Đơn giản hóa so với điều kiện thực tế

#### Hướng Phát Triển
- **Tăng tốc phần cứng**: Triển khai FPGA cho VQC
- **Thuật toán hybrid**: Các phương pháp lai cổ điển-lượng tử
- **Phần cứng lượng tử thật**: Triển khai trên cloud quantum computers
- **Mô hình nhiễu nâng cao**: Mô hình hóa lỗi cảm biến thực tế hơn

---

**Lưu ý**: Đây là module nghiên cứu tập trung vào khám phá lợi thế lượng tử trong sensor fusion, không phải code sẵn sàng cho sản xuất cho flight control.


