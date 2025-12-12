# Pre-Flight Checklist

## Flying Wing UAV - Twin Engine + 4 Split Elevon Configuration

**Date**: __________  
**Pilot**: __________  
**Location**: __________  
**Weather**: __________ (Wind: ____ km/h, Temp: ____°C)

---

# PHẦN 1: CẤU HÌNH PHẦN CỨNG (HARDWARE SETUP)

## 🔌 1.1 Hệ thống Nguồn (Power Distribution) - BẮT BUỘC TÁCH BIỆT

- [ ] **UBEC 3A (Hobbywing)**: Cấp nguồn vào chân Servo Rail (Dây đỏ/đen)
  - [ ] Rút dây đỏ ESC ra (nếu ESC có BEC) để tránh conflict nguồn
- [ ] **Buck Converter 3A**: Cấp nguồn riêng cho Raspberry Pi (qua GPIO 5V hoặc MicroUSB)
- [ ] **F4 V3S Plus**: Nhận nguồn từ VBAT (trực tiếp từ pin 6S) để đo áp
- [ ] **Kiểm tra Level Shifter**: Nếu FC không tolerant 3.3V, cần level shifter cho RPi

## 🔗 1.2 Đấu nối Tín hiệu (Signal Wiring)

### Motor & Servo Outputs:
- [ ] **S1**: Motor Trái (ESC 100A → D4250 600KV)
- [ ] **S2**: Motor Phải (ESC 100A → D4250 600KV)
- [ ] **S3**: Servo Ngoài Trái (Left Outer Elevon - MG996R)
- [ ] **S4**: Servo Ngoài Phải (Right Outer Elevon - MG996R)
- [ ] **S5**: Servo Trong Trái (Left Inner Elevon - MG996R)
- [ ] **S6**: Servo Trong Phải (Right Inner Elevon - MG996R)

### Cảm biến & Giao tiếp:
- [ ] **I2C Bus (TX3/RX3)**: Hàn chập 3 thiết bị:
  - [ ] La bàn QMC5883L (Address 0x0D)
  - [ ] LiDAR VL53L1X (Address 0x29)
  - [ ] Airspeed MS4525DO (Address 0x28) - nếu có
- [ ] **UART6 (T6/R6)**: GPS NEO-M8N
- [ ] **UART1 (TX1/RX1)**: Receiver ELRS (Radiomaster XR1 Nano)
- [ ] **UART2 (TX2/RX2)**: Raspberry Pi (TX Pi → RX2 FC, RX Pi → TX2 FC, GND chung)

### Anten:
- [ ] **Anten GPS**: Hướng lên trời, không bị che
- [ ] **Anten ELRS**: Đặt vuông góc 90° với nhau (diversity)

## 🔧 1.3 Cơ khí & Khí động học

- [ ] **Barometer**: Dán mút xốp đen che kín cảm biến trên mạch F4
- [ ] **Cánh gập (Folding Prop)**: 
  - [ ] Đã lắp miếng chặn (Stopper) in 3D PETG-CF đặc 100%
  - [ ] Kiểm tra mở ra gập vào trơn tru
- [ ] **Trọng tâm (CG)**: 
  - [ ] Đánh dấu điểm CG trên cánh (25-30% MAC)
  - [ ] Xếp pin sao cho máy bay cân bằng (hơi chúi mũi 1 chút xíu là an toàn)
- [ ] **Dây servo**: Kiểm tra không chạm cánh quạt khi quay

---

# PHẦN 2: CẤU HÌNH ARDUPILOT (MISSION PLANNER)

Vào **Full Parameter List**, tìm và sửa các thông số sau:

## ⚡ 2.1 Kích hoạt 6 Cổng PWM (QUAN TRỌNG NHẤT VỚI F4 V3S)

```
BRD_PWM_COUNT = 6    (Sau đó Reboot FC)
```

## 🎚️ 2.2 Gán chức năng Servo & Motor

```
SERVO1_FUNCTION = 73   # Throttle Left (Motor trái)
SERVO2_FUNCTION = 74   # Throttle Right (Motor phải)
SERVO3_FUNCTION = 77   # Elevon Left Outer
SERVO4_FUNCTION = 78   # Elevon Right Outer
SERVO5_FUNCTION = 79   # Elevon Left Inner
SERVO6_FUNCTION = 80   # Elevon Right Inner

# Servo Travel (MG996R)
SERVO3_MIN = 1000      SERVO3_MAX = 2000
SERVO4_MIN = 1000      SERVO4_MAX = 2000
SERVO5_MIN = 1000      SERVO5_MAX = 2000
SERVO6_MIN = 1000      SERVO6_MAX = 2000
```

## ✈️ 2.3 Thiết lập Twin Engine (Lái hướng bằng động cơ)

```
RUDD_DT_GAIN = 10      # Thử từ 10, nếu lái yếu thì tăng lên 20-50
```

## 🌬️ 2.4 Cảm biến Tốc độ gió (Airspeed)

**Nếu chưa có cảm biến MS4525DO:**
```
ARSPD_TYPE = 0         # Disabled
ARSPD_USE = 0
TECS_SYNAIRSPEED = 1   # Bật giả lập airspeed từ GPS
TRIM_THROTTLE = 45     # Mức ga bay hành trình dự kiến (45%)
```

**Nếu đã lắp MS4525DO:**
```
ARSPD_TYPE = 1         # I2C-MS4525DO
ARSPD_USE = 1          # Enable
ARSPD_PIN = 15         # I2C
```

## 📏 2.5 Cảm biến Độ cao & LiDAR

```
EK3_SRC1_POSZ = 1      # Barometer làm nguồn chính

# VL53L1X Rangefinder
RNGFND1_TYPE = 16      # VL53L1X
RNGFND1_MIN_CM = 5
RNGFND1_MAX_CM = 350
RNGFND1_ORIENT = 25    # Down facing
RNGFND1_ADDR = 41      # I2C address 0x29
```

## 🔋 2.6 Giám sát Pin (Battery Monitor) - 6S2P

```
BATT_MONITOR = 4       # Analog Voltage + Current
BATT_CAPACITY = 10400  # mAh (2x 5200mAh)
BATT_ARM_VOLT = 21.0   # Min voltage để arm (3.5V/cell × 6)
BATT_LOW_VOLT = 20.4   # Low warning (3.4V/cell × 6)
BATT_CRT_VOLT = 19.8   # Critical (3.3V/cell × 6)
BATT_FS_LOWACT = 2     # RTL khi low voltage
BATT_FS_CRT_ACT = 1    # Land khi critical
```

## 🛡️ 2.7 Failsafe Configuration

```
FS_SHORT_ACTN = 0      # Continue mission on short failsafe
FS_LONG_ACTN = 1       # RTL on long failsafe (>5s)
THR_FAILSAFE = 1       # Enable throttle failsafe
FS_GCS_ENABL = 1       # GCS failsafe enable

# Arming
ARMING_CHECK = 1       # Enable all pre-arm checks
ARMING_REQUIRE = 1     # Require throttle down to arm
```

## 🚧 2.8 Geofence (Hàng rào ảo)

```
FENCE_ENABLE = 1       # Enable geofence
FENCE_TYPE = 7         # Alt + Circle + Polygon
FENCE_ACTION = 1       # RTL khi vi phạm
FENCE_ALT_MAX = 120    # Max altitude (m)
FENCE_RADIUS = 500     # Max radius from home (m)
```

## 🛬 2.9 Crow Braking / Airbrake

```
DSPOILER_OPTS = 7      # Enable crow + elevon airbrake
DSPOILER_CROW_W1 = 50  # Inner elevon UP 50%
DSPOILER_CROW_W2 = 100 # Outer elevon DOWN 100%
RC6_OPTION = 208       # RC6 = Airbrake switch
FLAP_1_PERCNT = 50     # Stage 1: 50% crow
FLAP_2_PERCNT = 100    # Stage 2: Full crow
LAND_FLAP_PERCNT = 100 # Auto crow khi landing
```

## 📡 2.10 Giao tiếp Serial

```
# UART1 - ELRS Receiver
SERIAL1_PROTOCOL = 23  # RCIN (CRSF)
SERIAL1_BAUD = 115     # 115200

# UART2 - Raspberry Pi (MAVLink)
SERIAL2_PROTOCOL = 2   # MAVLink 2
SERIAL2_BAUD = 921     # 921600 - Tốc độ cao

# UART4/6 - GPS
SERIAL4_PROTOCOL = 5   # GPS
SERIAL4_BAUD = 38      # 38400 (M8N)
GPS1_TYPE = 1          # Auto detect
```

## 🎮 2.11 Chế độ bay (Flight Modes)

```
FLTMODE_CH = 5         # Channel 5 for mode switch
FLTMODE1 = 0           # MANUAL (Cứu máy bay/cân chỉnh)
FLTMODE2 = 5           # FBWA (Fly By Wire A - Bay cân bằng)
FLTMODE3 = 11          # RTL (Return To Launch)
FLTMODE4 = 10          # AUTO (Bay theo Mission)
FLTMODE5 = 12          # LOITER
FLTMODE6 = 11          # RTL
```

---

# PHẦN 3: CẤU HÌNH RASPBERRY PI (COMPANION COMPUTER)

## 💻 3.1 Hệ điều hành & Kết nối

- [ ] Dùng **Raspberry Pi OS Lite (64-bit)**
- [ ] Bật Serial Port, tắt Serial Console:
  ```bash
  sudo raspi-config → Interface Options → Serial Port
  # "Would you like a login shell?" → No
  # "Would you like serial port hardware enabled?" → Yes
  ```
- [ ] Cấu hình `/boot/config.txt`:
  ```
  enable_uart=1
  dtoverlay=disable-bt
  gpu_mem=128
  start_x=1
  ```
- [ ] Reboot sau khi thay đổi

## 📦 3.2 Phần mềm & Dependencies

```bash
# Cài đặt thư viện
pip install pymavlink opencv-python-headless tflite-runtime

# Test MAVLink connection
mavproxy.py --master=/dev/serial0 --baudrate=921600
```

## 🔄 3.3 Triển khai Code Multiprocessing

```
Process 1: Camera Capture (CSI - OV5647)
Process 2: AI Logic (TFLite + Geolocation Math)
Process 3: MAVLink Comms (UART - /dev/serial0)
```

## 🚀 3.4 Service systemd

```bash
# Enable service để tự chạy khi boot
sudo cp uav-companion.service /etc/systemd/system/
sudo systemctl enable uav-companion
sudo systemctl start uav-companion
```

---

# PHẦN 4: HIỆU CHỈNH TRƯỚC KHI BAY (PRE-FLIGHT CALIBRATION)

**⚠️ Làm dưới mặt đất, đừng để lên trời mới làm!**

## 📐 4.1 Accelerometer Calibration

- [ ] Mission Planner → Setup → Mandatory Hardware → Accel Calibration
- [ ] Đặt máy bay lên mặt phẳng
- [ ] Cân chỉnh 6 mặt theo hướng dẫn
- [ ] **Lưu ý**: Lúc cân mức (Level), kê mũi máy bay lên khoảng **2-3 độ** (Góc tấn hành trình)

## 🧭 4.2 Compass Calibration

- [ ] Mission Planner → Setup → Mandatory Hardware → Compass
- [ ] Xoay máy bay theo hướng dẫn (tất cả các hướng)
- [ ] Kiểm tra **Compass Offset < 600**
- [ ] Không có warning màu đỏ

## 📻 4.3 Radio Calibration

- [ ] Mission Planner → Setup → Mandatory Hardware → Radio Calibration
- [ ] Calib hết hành trình các cần gạt (Stick) trên tay khiển
- [ ] Di chuyển tất cả switch
- [ ] Lưu calibration

## ⚡ 4.4 ESC Calibration

- [ ] **THÁO CÁNH QUẠT** trước khi làm!
- [ ] Đẩy ga MAX → Cắm pin → Nghe nhạc beep
- [ ] Hạ ga MIN → Nghe nhạc xác nhận
- [ ] Hoặc: Mission Planner → Setup → Mandatory Hardware → ESC Calibration

## 🔄 4.5 Kiểm tra chiều Motor

- [ ] Motor Trái: **CCW** (Counter-Clockwise, nhìn từ phía sau)
- [ ] Motor Phải: **CW** (Clockwise, nhìn từ phía sau)
- [ ] Test: Rudder Left → Motor Trái tăng, Motor Phải giảm
- [ ] Nếu sai chiều → Đảo 2 dây phase bất kỳ trên ESC

## ✋ 4.6 Kiểm tra chiều Servo (High-Five Test)

- [ ] Chuyển sang mode **FBWA** (Fly By Wire A)
- [ ] **Nghiêng máy bay sang Trái**:
  - [ ] Cánh lái bên Trái phải **Đi Xuống** (để nâng cánh lên)
  - [ ] Cánh lái bên Phải phải **Đi Lên**
  - [ ] Nếu ngược → Vào Servo Output, đặt `SERVOx_REVERSED = 1`
- [ ] **Chốc mũi máy bay Xuống**:
  - [ ] Cả 4 cánh lái phải **Vểnh Lên** (trailing edge up)

## 🛬 4.7 Test Crow Braking

- [ ] Gạt switch RC6 (Airbrake)
- [ ] Outer elevon (M3, M4) → **Trailing edge DOWN**
- [ ] Inner elevon (M5, M6) → **Trailing edge UP**
- [ ] Kiểm tra không có binding/jamming

---

# PHẦN 5: PRE-ARM CHECKS (KIỂM TRA TRƯỚC KHI ARM)
  - [ ] RTSP stream running: `rtsp://<IP>:8554/video`
  
- [ ] **MAVLink Communication**
  - [ ] UART connection to FC: `/dev/serial0` @ 921600 baud
  - [ ] Heartbeat messages received
  - [ ] Telemetry data updating
  - [ ] Companion service running: `systemctl status uav-companion`
  
- [ ] **AI Detection (Optional)**
  - [ ] TFLite model loaded
  - [ ] Detection running (check logs)
  - [ ] Inference time < 200ms
  
- [ ] **Data Logging**
  - [ ] Logging service active
  - [ ] SD card space: ≥ 2GB free
  - [ ] Previous logs backed up

---

## 🔋 5.1 Battery & Power

- [ ] Main battery voltage: **≥ 25.2V** (6S fully charged, 4.2V/cell)
- [ ] Min voltage to arm: **≥ 21.0V** (3.5V/cell)
- [ ] All cells within 0.05V difference
- [ ] Raspberry Pi power: ≥ 5V/2A (separate regulator)
- [ ] FC power indicator: Green LED on

## 📡 5.2 GPS & Sensors

- [ ] GPS: **≥ 8 satellites**
- [ ] HDOP: **< 2.0**
- [ ] 3D Fix achieved
- [ ] Home position set automatically
- [ ] Compass: No errors, offset < 600
- [ ] EKF: **Green** trong Mission Planner

## ✅ 5.3 System Status

- [ ] **No pre-arm warnings** trong Messages tab
- [ ] All sensors healthy
- [ ] Radio calibrated
- [ ] Geofence enabled (FENCE_ENABLE = 1)

---

# PHẦN 6: LAUNCH & FLIGHT

## 🚁 6.1 Launch Preparation

- [ ] **Launch Area**
  - [ ] 50m clear radius
  - [ ] No obstacles in flight path
  - [ ] Wind direction noted: __________
  - [ ] Spectators clear
  
- [ ] **Pilot Ready**
  - [ ] TX on, throttle at minimum
  - [ ] Observer assigned (if available)
  - [ ] Emergency procedures reviewed
  - [ ] First aid kit available
  
- [ ] **Final Checks**
  - [ ] All hatches closed and secured
  - [ ] Antennas secure and oriented correctly
  - [ ] Camera lens clean
  - [ ] GPS antenna unobstructed

## ✈️ 6.2 Launch Procedure

1. **Arm Sequence**
   - [ ] Announce "Arming"
   - [ ] Arm via switch (throttle down + rudder right)
   - [ ] Motors spin at idle
   - [ ] Throttle to 30% for 3 seconds (test)

2. **Hand Launch**
   - [ ] Throttle to 80-100%
   - [ ] Throw forward at 15° angle
   - [ ] Immediately check attitude
   - [ ] Climb to 50m

3. **First Circuit**
   - [ ] Level flight test (1 minute)
   - [ ] Control surface response test
   - [ ] Differential thrust test (gentle yaw)
   - [ ] Confirm telemetry updating

---

## ⚠️ ABORT CONDITIONS

**❌ KHÔNG BAY nếu:**
- ❌ Battery voltage < 21.0V (6S)
- ❌ GPS satellites < 6
- ❌ Wind speed > 20 km/h (cho chuyến bay đầu)
- ❌ Mưa hoặc ẩm ướt
- ❌ Control surface bị kẹt
- ❌ Motor rung hoặc tiếng lạ
- ❌ FC có error codes
- ❌ Kết nối không ổn định
- ❌ Bất kỳ nghi ngờ nào về an toàn

---

## 📝 Post-Flight Checklist

- [ ] **Landing Sequence**
  - [ ] Approach into wind
  - [ ] Deploy Crow braking (RC6 switch)
  - [ ] Flare at 1m altitude
  - [ ] Cut throttle before touchdown
  
- [ ] **Immediate Actions**
  - [ ] Disarm motors
  - [ ] Disconnect main battery
  - [ ] Check for damage
  
- [ ] **Data Collection**
  - [ ] Download telemetry logs
  - [ ] Download video recordings
  - [ ] Note any issues
  - [ ] Update flight logbook

- [ ] **Maintenance**
  - [ ] Clean airframe
  - [ ] Check for loose screws
  - [ ] Recharge batteries (storage charge if not flying soon)
  - [ ] Store in dry location

---

## 📞 Emergency Contacts

**Pilot**: __________  
**Observer**: __________  
**Emergency**: 115 (Vietnam)  
**Local Authority**: __________

---

**Checklist Version**: 2.0  
**Last Updated**: 2025-12-01  
**Configuration**: Twin Engine (D4250 600KV) + 4 Split Elevon (MG996R)

**Signature**: __________ **Date**: __________
