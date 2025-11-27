Tiêu Đề:
Thiết kế và Chế tạo UAV Modified Blended Wing Body (BWB) with Vertical Stabilizers phục vụ trinh sát & lập bản đồ: Tích hợp xử lý ảnh tại biên, tối ưu hóa khí động học và thuật toán lượng tử cảm hứng giúp nâng cao thời gian bay và độ chính xác
Đặc điểm dự án:  Bay để thực hiện nhiệm vụ (UAV Engineer) chứ không phải chỉ BAY ĐƯỢC
-	Thời gian bay mục tiêu: 25 – 30 phút
-	Tải trọng mục tiêu: 3.5 – 4.0 kg.
-	Tốc độ dự kiến: 50 – 80 km/h
-	Nghiên cứu mới: Quantum-inspired Kalman Filter cho lọc nhiễu cảm biến MEMS
-	
1. Thuật toán điều khiển & tự hành
Hệ thống firmware ArduPilot được tùy biến, kết hợp với máy tính đồng hành để thực hiện các chế độ bay:
•	Autonomous Navigation: Bay tự động theo lộ trình đa điểm (Waypoint) định sẵn với độ chính xác cao nhờ module GPS M10.
•	Loiter Mode (Bay tuần tra): Chế độ bay vòng tròn quanh mục tiêu cố định, tối ưu hóa cho nhiệm vụ trinh sát
•	Differential Thrust Control: Thuật toán điều khiển hướng thông qua chênh lệch lực đẩy của 2 động cơ.
•	Geofencing (Hàng rào ảo): Thiết lập giới hạn vùng bay an toàn dựa trên GPS, tự động ngăn chặn UAV bay vào vùng cấm.
•	Quantum-inspired Kalman Filter: Thuật toán lọc nhiễu cảm biến MEMS sử dụng Variational Quantum Circuit, hoạt động ở chế độ Shadow Mode để so sánh với EKF tiêu chuẩn.
2. Kiến trúc Hệ thống / Kết nối
Mô hình tích hợp Flight Controller (MCU) và Máy tính đồng hành AI:
a. Tính toán tại biên: Raspberry Pi để xử lý dữ liệu hình ảnh, logic tự hành và thuật toán lượng tử ngay trên máy bay, giảm độ trễ và phụ thuộc vào đường truyền.
b. Kết hợp phương thức điều khiển (5G& tay cầm):
Điều khiển thủ công (tay cầm): độ trễ thấp.
Điều khiển không giới hạn: 5G/Wifi cho phép điều khiển không giới hạn khoảng cách (BVLOS).
c. Data Logging: Hộp đen ghi lại dữ liệu bay, video độ phân giải cao và dữ liệu nghiên cứu lượng tử vào thẻ nhớ.
d. Quantum Computing Research: Triển khai Variational Quantum Circuit trên Raspberry Pi cho nghiên cứu lọc nhiễu phi tuyến tính.
3. Logic An toàn:
Tự đưa ra quyết định dựa trên trạng thái kết nối và năng lượng (State-machine Failsafe):
Kịch bản 1: Mất tín hiệu tay cầm, còn kết nối 5G: Chuyển sang chế độ lượn tại chỗ. Hệ thống gửi cảnh báo về trạm mặt đất và chuyển quyền điều khiển qua Laptop/ Điện thoại. 
Kịch bản 2: Mất toàn bộ liên kết: Kích hoạt chế độ RTH. Máy bay tự động tăng độ cao an toàn và quay về vị trí cất cánh.
Kịch bản 3: % pin thấp, đang ở xa: Tính toán năng lượng tiêu thụ. Nếu không đủ pin để về nhà, tự động tìm khu vực hạ cánh khẩn cấp.
4. Nhiệm vụ
Thiết kế dạng module cho phép thay đổi cấu hình tùy theo mục đích:
•	Trinh sát Thời gian thực: Sử dụng AI trên máy tính nhúng để phát hiện vật thể, gửi cảnh báo tọa độ về trạm đất qua 5G.
•	Lập bản đồ: Thu thập dữ liệu hình ảnh độ phân giải cao kết hợp log GPS đồng bộ thời gian, phục vụ dựng mô hình địa hình và bản đồ.
•	Nghiên cứu Quantum Filtering: Thử nghiệm Variational Quantum Circuit cho lọc nhiễu cảm biến MEMS trong điều kiện thực tế.
•	(Nâng cao) Auto Landing: Hạ cánh an toàn, sử dụng phân tích ảnh để tìm đường băng.
•	(Nâng cao) Hệ thống trinh sát định kỳ: Theo lịch đặt sẵn, máy bay tự cất cánh, bay đến các vị trí đã cài đặt trước – chụp ảnh – gửi lên web.
•	Nghiên cứu học máy lượng tử: Nền tảng cho các thử nghiệm thuật toán lượng tử trên thiết bị biên. 
"Cất cánh là tùy chọn, nhưng hạ cánh là bắt buộc."

---

## NGHIÊN CỨU MỚI: QUANTUM-INSPIRED KALMAN FILTER

### Mục Tiêu Nghiên Cứu
1. **Triển khai thuật toán lượng tử cảm hứng** trên Raspberry Pi để lọc nhiễu phi tuyến tính của cảm biến MEMS giá rẻ
2. **Xử lý drift IMU khi mất GPS** sử dụng Quantum Kalman Filter để duy trì độ chính xác định vị
3. **So sánh hiệu suất** với bộ lọc EKF tiêu chuẩn của ArduPilot

### Ứng Dụng Thực Tế
- **Duy trì navigation accuracy** khi mất tín hiệu vệ tinh
- **Triệt tiêu sai số trôi** của cảm biến MEMS giá rẻ
- **Tăng độ tin cậy** cho autonomous flight trong điều kiện GPS không ổn định

### Tính Năng Nổi Bật

#### 1. Variational Quantum Circuit (VQC)
- **Kiến trúc**: 4 qubit, 3 lớp biến phân
- **Mã hóa**: Angle encoding cho dữ liệu cảm biến
- **Entanglement**: Linear connectivity cho hiệu quả
- **Ước lượng**: VQE (Variational Quantum Eigensolver)

#### 2. Shadow Mode Operation
- **Không can thiệp**: Chạy song song với hệ thống điều khiển chính
- **So sánh thời gian thực**: QKF vs EKF performance
- **Thu thập dữ liệu**: Comprehensive metrics collection
- **Fallback**: Tự động chuyển sang Kalman cổ điển nếu cần

#### 3. Non-linear Noise Modeling
- **Nhiễu Gaussian**: MEMS sensor noise tiêu chuẩn
- **Bias Drift**: Nhiễu phi tuyến thay đổi theo thời gian
- **Cross-coupling**: Hiệu ứng giao thoa cảm biến
- **Validation**: So sánh với dữ liệu thực tế

### Kết Quả Mong Đợi
- **Cải thiện độ chính xác**: Giảm nhiễu cảm biến MEMS
- **Benchmark hiệu suất**: So sánh quantum vs classical
- **Nghiên cứu thực tiễn**: Ứng dụng lượng tử trên edge device
- **Tài liệu mở**: Code và data cho cộng đồng nghiên cứu

### Module Đã Triển Khai
```python
companion_computer/src/quantum/
├── quantum_kalman_filter.py      # Core QKF implementation
├── quantum_integration.py        # Shadow mode integration
├── quantum_imu_drift_filter.py   # IMU drift correction khi mất GPS
├── test_quantum_filtering.py     # Comprehensive testing
└── test_quantum_imu_drift.py     # GPS loss scenario testing
```

### Công Nghệ Sử Dụng
- **Quantum Framework**: Qiskit Aer simulator
- **Classical Baseline**: Standard Kalman Filter
- **Data Processing**: NumPy, SciPy
- **Performance Analysis**: Real-time comparison metrics

---

## TÍNH NĂNG HỆ THỐNG ĐÃ HOÀN THÀNH

### Software Modules (100% Complete)
- **Companion Computer**: Raspberry Pi application với module hóa
- **MAVLink Communication**: Giao tiếp đầy đủ với ArduPilot
- **AI Object Detection**: TensorFlow Lite trên edge
- **Geofencing System**: Polygon-based với multiple actions
- **Data Logging**: Comprehensive flight data recording
- **Web Dashboard**: Real-time monitoring và control
- **Quantum Filtering**: Research module hoàn chỉnh
- **IMU Drift Correction**: Quantum Kalman Filter cho GPS loss scenarios

### Design Calculations
- **Aerodynamics Analysis**: Tính toán khí động học chi tiết
- **CG Calculation**: Phân tích trọng tâm
- **Performance Prediction**: Ước tính thời gian bay, tốc độ
- **6S Power System**: Tối ưu hóa cho motor 600KV

### Testing & Simulation
- **SITL Integration**: ArduPilot simulation testing
- **Controller Testing**: RadioMaster Pocket validation
- **AI Testing**: Object detection với synthetic data
- **Quantum Testing**: Performance comparison framework

---

## TRẠNG THÁI DỰ ÁN

**Cập nhật**: 26/11/2025

### ĐÃ HOÀN THÀNH
- Toàn bộ software development và testing
- Hardware specification finalization
- Quantum research module integration
- Documentation và deployment scripts

### ĐANG THỰC HIỆN
- Hardware integration và bench testing
- Field testing preparation
- Performance optimization

### KẾ HOẠCH
- Flight testing với quantum filtering
- Research data collection và analysis
- Publication preparation

---
"We don't just build UAVs that fly - we build systems that think and research."

BOM LIST: (kèm file excel) 