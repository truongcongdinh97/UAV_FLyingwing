# Flying Wing UAV - Dự Án Trinh Sát & Lập Bản Đồ Động Cơ Kép

## I. Giới Thiệu Chung

Phát triển một chiếc UAV cánh bay (Flying Wing) sử dụng động cơ kép (Twin-Engine). Phục vụ các công việc trinh sát tự hành, lập bản đồ và xử lý AI ngay trên thiết bị (Edge Computing).

### 1. Thông Số Kỹ Thuật
*   **Thời gian bay**: Khoảng 25-30 phút.
*   **Tải trọng**: 3.5-4.0 kg.
*   **Tốc độ hành trình**: 50-80 km/h.
*   **Động lực**: Cấu hình 2 động cơ D4250 800KV, sử dụng lực đẩy vi sai (differential thrust) để điều hướng.
*   **Pin**: Pack Li-ion 4S2P 10400mAh tự đóng.
*   **Flight Controller (FC)**: LANRC F4 V3S Plus (Chip STM32F405).
*   **Companion Computer**: Raspberry Pi 3B+.

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
Mình dùng iNav 8.0.1 và custom lại code. FC chịu trách nhiệm giữ cân bằng, trộn tín hiệu động cơ (mixing) và dẫn đường cơ bản.
*   **Phần cứng**: LANRC F4 V3S Plus.
*   **Custom**: Mình viết lại bộ mixer để hỗ trợ differential thrust cho cánh bay.
*   **Failsafe**: Tự động RTH khi mất tín hiệu.

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

## III. Phần Firmware (iNav Custom)

Can thiệp sâu vào code của iNav để tùy chỉnh.

### 1. Môi Trường Build
firmware được build trên Linux (dùng WSL2 Ubuntu 22.04 trên Windows) với bộ compiler ARM GCC.
*   **Toolchain**: gcc-arm-none-eabi
*   **Build System**: CMake/Ninja

### 2. Custom Mixer
Vì cánh bay này không có đuôi đứng (rudder), phải dùng chênh lệch lực đẩy 2 động cơ để xoay mũi.
*   **Nguyên lý**: Ga (Throttle) tăng cả 2 motor. Hướng (Yaw) sẽ làm một bên quay nhanh hơn, bên kia chậm lại.
*   **Code**: Nằm trong file `src/main/flight/mixer_custom_twin.c`.

### 3. Cách Cài Đặt
a.  **Build**: Chạy mấy script trong thư mục `firmware/scripts`.
b.  **Flash**: Dùng iNav Configurator nạp file `.hex` vào mạch `MATEKF405`.
c.  **Config**: Copy lệnh trong `firmware/config/inav_cli_config.txt` paste vào CLI để setup cổng với mixer.

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

### 1. Setup Firmware
1.  Cài WSL2 Ubuntu 22.04 trên Windows.
2.  Chạy script cài toolchain ARM.
3.  Build ra file hex cho `MATEKF405`.
4.  Cắm cáp USB, dùng iNav Configurator flash vào mạch.

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

cập nhật 22/11/2025.

*   **Firmware**: Đã build xong, mixer chạy ok
*   **Dẫn đường**: Đã test thuật toán bám đường và bay vòng tròn - lệch.
*   **AI**: chưa nhận diện được vật thể.
*   **An toàn**: Geofence và Failsafe pin / ok.
*   **Kết nối**: Web Server /ok.
*   **Lập lịch**: Đã test/ ok.


