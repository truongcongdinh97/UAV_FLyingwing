# Hardware Wiring & Radio Setup Guide
## Flying Wing UAV - Twin Engine + 4 Servo Configuration

**Document Date**: 2025-11-28  
**Version**: 1.0  
**Flight Controller**: LANRC F4 V3S Plus  
**Configuration**: 2 Động cơ (Twin Engine) + 2 Servo MG996R (Elevon)

---

## 📋 Tổng Quan Cấu Hình

```
                    ┌─────────────────────────────────┐
                    │         FLYING WING             │
                    │                                 │
    ┌───────────────┼─────────────────────────────────┼───────────────┐
    │               │                                 │               │
    │  SERVO LEFT   │                                 │  SERVO RIGHT  │
    │  OUTER (M3)   │         FUSELAGE                │  OUTER (M4)   │
    │               │                                 │               │
    │  SERVO LEFT   │    ┌─────────────────────┐      │  SERVO RIGHT  │
    │  INNER (M5)   │    │   Flight Controller │      │  INNER (M6)   │
    │               │    │        (FC)         │      │               │
    └───────────────┤    └─────────────────────┘      ├───────────────┘
                    │                                 │
                    │   MOTOR LEFT    MOTOR RIGHT     │
                    │      (M1)          (M2)         │
                    └─────────────────────────────────┘
```

---

## 🔌 PHẦN 1: SƠ ĐỒ HÀN DÂY TRÊN FLIGHT CONTROLLER

### Nhìn Tổng Quan FC (SpeedyBee F405 V4)

```
                        ┌─────────────────────────────────────┐
                        │            TOP EDGE                 │
                        │   M1  M2  M3  M4  M5  M6  M7  M8    │
                        │   ○   ○   ○   ○   ○   ○   ○   ○    │
    ┌───────────────────┼─────────────────────────────────────┼───────────────────┐
    │                   │                                     │                   │
    │   LEFT EDGE       │                                     │   RIGHT EDGE      │
    │                   │                                     │                   │
    │   TX1 ○           │         SpeedyBee F405 V4           │           ○ TX3   │
    │   RX1 ○           │                                     │           ○ RX3   │
    │   5V  ○           │              [USB]                  │           ○ 5V    │
    │   GND ○           │                                     │           ○ GND   │
    │                   │                                     │                   │
    └───────────────────┼─────────────────────────────────────┼───────────────────┘
                        │                                     │
                        │            BOTTOM EDGE              │
                        │   T6  R6  5V  GND  ...              │
                        │   ○   ○   ○   ○                     │
                        └─────────────────────────────────────┘
```

---

### A. Cho La Bàn (QMC5883L) & Cảm Biến Lidar (VL53L1X)

**Giao tiếp**: I2C (dùng chung bus)

| Dây | Hàn Vào | Ghi Chú |
|-----|---------|---------|
| **SDA** (Data) | **RX3** | Cạnh phải FC |
| **SCL** (Clock) | **TX3** | Cạnh phải FC |
| **5V** | 5V | Hàng bên cạnh hoặc chung với GPS |
| **GND** | GND | Hàng bên cạnh hoặc chung với GPS |

```
        ┌─────────────┐     ┌─────────────┐
        │  QMC5883L   │     │  VL53L1X    │
        │  (Compass)  │     │  (Lidar)    │
        └──┬──┬──┬──┬─┘     └──┬──┬──┬──┬─┘
           │  │  │  │          │  │  │  │
          SDA SCL 5V GND      SDA SCL 5V GND
           │  │  │  │          │  │  │  │
           └──┼──┼──┼──────────┘  │  │  │
              │  │  └─────────────┼──┘  │
              │  └────────────────┼─────┼──→ TX3 (SCL)
              └───────────────────┘     └──→ 5V/GND
                     ↓
                   RX3 (SDA)
```

**Lưu ý quan trọng**:
- La bàn phải đặt **xa động cơ và ESC** (ít nhất 10cm) để tránh nhiễu từ
- Nên mount la bàn trên cột GPS
- I2C address mặc định: QMC5883L = 0x0D, VL53L1X = 0x29

---

### B. Cho GPS (NEO-M8N / M10)

**Giao tiếp**: UART6

| Dây GPS | Hàn Vào | Ghi Chú |
|---------|---------|---------|
| **TX** (từ GPS) | **R6** (RX6) | Cạnh đáy FC, góc phải |
| **RX** (vào GPS) | **T6** (TX6) | Cạnh đáy FC |
| **5V** | 5V | Cạnh đáy FC |
| **GND** | GND | Cạnh đáy FC |

```
        ┌─────────────────┐
        │   GPS Module    │
        │   NEO-M8N/M10   │
        └──┬──┬──┬──┬─────┘
           │  │  │  │
          TX  RX 5V GND
           │  │  │  │
           │  │  │  └──→ GND (Bottom Edge)
           │  │  └─────→ 5V  (Bottom Edge)
           │  └────────→ T6  (TX6)
           └───────────→ R6  (RX6)
           
    ════════════════════════════════════
              BOTTOM EDGE FC
         ... T6  R6  5V  GND ...
    ════════════════════════════════════
```

**Lưu ý**:
- Baudrate GPS: 38400 (M8N) hoặc 115200 (M10)
- Cấu hình trong Mission Planner: `GPS_TYPE = 1` (Auto)
- GPS cần clear sky để có fix

---

### C. Cho Động Cơ & Servo (Twin Engine + 4 Split Elevon)

**Giao tiếp**: PWM Output

**Cấu hình**: Split Elevon (Dual Elevon) - Kiểu Horten 229
- Mỗi cánh có 2 servo: Outer (cánh ngoài) + Inner (cánh trong)
- Tăng hiệu quả điều khiển roll và pitch
- Cho phép drag rudder (phanh không khí) để điều khiển yaw

| Output | Thiết Bị | Chức Năng ArduPilot | Mô Tả |
|--------|----------|-------------------|-------|
| **M1** | ESC 100A | ThrottleLeft (73) | Động cơ trái (D4250 600KV) |
| **M2** | ESC 100A | ThrottleRight (74) | Động cơ phải (D4250 600KV) |
| **M3** | Servo MG996R | Elevon 1 (77) | Cánh **ngoài trái** (Left Outer) |
| **M4** | Servo MG996R | Elevon 2 (78) | Cánh **ngoài phải** (Right Outer) |
| **M5** | Servo MG996R | Elevon 3 (79) | Cánh **trong trái** (Left Inner) |
| **M6** | Servo MG996R | Elevon 4 (80) | Cánh **trong phải** (Right Inner) |

```
    ════════════════════════════════════════════════════════════
                         TOP EDGE FC (LANRC F4 V3S)
         M1    M2    M3    M4    M5    M6    M7    M8
         ○     ○     ○     ○     ○     ○     ○     ○
    ════════════════════════════════════════════════════════════
         │     │     │     │     │     │
         │     │     │     │     │     │
         ▼     ▼     ▼     ▼     ▼     ▼
       ESC   ESC   Servo Servo Servo Servo
       100A  100A  MG996R MG996R MG996R MG996R
       Left  Right L-Out R-Out L-In  R-In
         │     │     │     │     │     │
         ▼     ▼     │     │     │     │
       D4250 D4250  │     │     │     │
       600KV 600KV  │     │     │     │
                    ▼     ▼     ▼     ▼
              ┌─────────────────────────────────────┐
              │         FLYING WING (Horten 229)       │
              │                                         │
              │   [L-Out]     [Fuselage]     [R-Out]   │
              │      ╲           │           ╱         │
              │   [L-In]    [Motors]      [R-In]      │
              │                                         │
              └─────────────────────────────────────┘
```

**Sơ đồ hàn chi tiết**:

```
Mỗi kênh có 3 pin: Signal (S), Voltage (+), Ground (-)

     M1         M2         M3         M4         M5         M6
    ┌─┬─┬─┐   ┌─┬─┬─┐   ┌─┬─┬─┐   ┌─┬─┬─┐   ┌─┬─┬─┐   ┌─┬─┬─┐
    │S│+│-│   │S│+│-│   │S│+│-│   │S│+│-│   │S│+│-│   │S│+│-│
    └─┴─┴─┘   └─┴─┴─┘   └─┴─┴─┘   └─┴─┴─┘   └─┴─┴─┘   └─┴─┴─┘
     │ │ │     │ │ │     │ │ │     │ │ │     │ │ │     │ │ │
     ▼ ▼ ▼     ▼ ▼ ▼     ▼ ▼ ▼     ▼ ▼ ▼     ▼ ▼ ▼     ▼ ▼ ▼
    ESC L     ESC R    Servo L   Servo R   Servo L   Servo R
   (Motor)   (Motor)   Outer     Outer     Inner     Inner
```

**Lưu ý quan trọng**:
- ESC cần kết nối thêm **nguồn chính** từ pin (không chỉ tín hiệu)
- Servo có thể dùng nguồn 5V từ BEC của ESC hoặc FC
- Thứ tự này sẽ được **map lại trong Mixer** ở phần mềm (xem bên dưới)

---

### D. Cho Bộ Thu ELRS (Receiver)

**Giao tiếp**: UART1 (CRSF Protocol)

| Dây RX | Hàn Vào | Ghi Chú |
|--------|---------|---------|
| **TX** (từ RX) | **RX1** | Cạnh trái FC |
| **RX** (vào RX) | **TX1** | Cạnh trái FC |
| **5V** | 5V | Cạnh trái FC |
| **GND** | GND | Cạnh trái FC |

```
    ┌─────────────────┐
    │   ELRS RX       │
    │   (Receiver)    │
    └──┬──┬──┬──┬─────┘
       │  │  │  │
      TX  RX 5V GND
       │  │  │  │
       │  │  │  └──→ GND (Left Edge)
       │  │  └─────→ 5V  (Left Edge)
       │  └────────→ TX1
       └───────────→ RX1
       
    ════════════════
       LEFT EDGE FC
      TX1  RX1  5V  GND
    ════════════════
```

**Cấu hình trong FC**:
```
SERIAL1_PROTOCOL = 23  (RCIN)
SERIAL1_BAUD = 420000  (CRSF default)
```

---

### E. Cho Raspberry Pi (Companion Computer)

**Giao tiếp**: UART (MAVLink)

| Dây Pi | Hàn Vào | Ghi Chú |
|--------|---------|---------|
| **TX** (GPIO 14) | **RX2** | Hoặc UART khả dụng |
| **RX** (GPIO 15) | **TX2** | Hoặc UART khả dụng |
| **GND** | GND | Kết nối chung GND |

**Lưu ý**: 
- Raspberry Pi dùng logic 3.3V, FC dùng 5V → Cần **level shifter** hoặc kiểm tra FC có tolerant 3.3V không
- Baudrate: 115200 (MAVLink default)

---

## 🎮 PHẦN 2: CẤU HÌNH TAY CẦM (RadioMaster)

### Cấu Hình Chế Độ Bay (Flight Modes)

#### Sơ Đồ Kênh RC

| Kênh | Chức Năng | Điều Khiển |
|------|-----------|------------|
| CH1 | **Aileron** (Roll) | Stick phải, trái/phải |
| CH2 | **Elevator** (Pitch) | Stick phải, lên/xuống |
| CH3 | **Throttle** | Stick trái, lên/xuống |
| CH4 | **Rudder** (Yaw) | Stick trái, trái/phải |
| CH5 | **Flight Mode** | Switch 3 vị trí (SWA) |
| CH6 | **Aux 1** | Switch (SWB) |
| CH7 | **Aux 2** | Switch (SWC) |
| CH8 | **Aux 3** | Switch (SWD) |

---

### Cấu Hình Switch Cho AI Mission Modes

```
┌─────────────────────────────────────────────────────────────┐
│                    RadioMaster TX                           │
│                                                             │
│   SWA (3-pos)          SWB (2-pos)      SWC (3-pos)        │
│   ┌───┐                ┌───┐            ┌───┐              │
│   │ ↑ │ People Count   │ ↑ │ Reserved   │ ↑ │ High Freq    │
│   ├───┤                └───┘            ├───┤              │
│   │ ─ │ Reconnaissance                  │ ─ │ Normal       │
│   ├───┤                                 ├───┤              │
│   │ ↓ │ Search&Rescue                   │ ↓ │ Low Freq     │
│   └───┘                                 └───┘              │
│                                                             │
│   SWD (2-pos)                                               │
│   ┌───┐                                                     │
│   │ ↑ │ Emergency Override                                  │
│   ├───┤                                                     │
│   │ ↓ │ Normal Operation                                    │
│   └───┘                                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### Cấu Hình Trong EdgeTX/OpenTX

#### Bước 1: Vào Model Setup → Inputs

```
Input 1: Ail    Source: [Gim R ←→]
Input 2: Ele    Source: [Gim R ↑↓]
Input 3: Thr    Source: [Gim L ↑↓]
Input 4: Rud    Source: [Gim L ←→]
Input 5: FM     Source: [SWA]
Input 6: Aux1   Source: [SWB]
Input 7: Aux2   Source: [SWC]
Input 8: Aux3   Source: [SWD]
```

#### Bước 2: Vào Mixes

```
Mix 1: CH1 = [Ail]     Weight: 100%
Mix 2: CH2 = [Ele]     Weight: 100%
Mix 3: CH3 = [Thr]     Weight: 100%
Mix 4: CH4 = [Rud]     Weight: 100%
Mix 5: CH5 = [FM]      Weight: 100%
Mix 6: CH6 = [Aux1]    Weight: 100%
Mix 7: CH7 = [Aux2]    Weight: 100%
Mix 8: CH8 = [Aux3]    Weight: 100%
```

---

### Cấu Hình Flight Modes (ArduPilot - Mission Planner)

#### Mission Planner → Config → Flight Modes

```
Flight Modes:
  Mode 1 (PWM < 1230):      MANUAL
  Mode 2 (1230 < PWM < 1360): STABILIZE
  Mode 3 (1360 < PWM < 1490): FBWA (Fly By Wire A)
  Mode 4 (1490 < PWM < 1620): AUTO
  Mode 5 (1620 < PWM < 1750): LOITER
  Mode 6 (PWM > 1750):       RTL (Return To Launch)

Channel Option:
  CH5 = Flight Mode
  CH6 = ARM/DISARM (optional)
  CH7 = AI Mode Control (for companion computer)
  CH8 = Emergency Override
```

---

## ⚙️ PHẦN 3: CẤU HÌNH MIXER CHO FLYING WING

### Cấu Hình Split Elevon (4 Servo) - Kiểu Horten 229

**Split Elevon** (hay Dual Elevon) là cấu hình chia mỗi elevon thành 2 phần:
- **Outer Elevon** (cánh ngoài): Hiệu quả hơn cho roll do cánh tay đòn dài
- **Inner Elevon** (cánh trong): Hiệu quả hơn cho pitch và có thể dùng làm drag rudder

#### Mission Planner → Setup → Servo Output

```
# ═══════════════════════════════════════════════════════════════
# TWIN ENGINE + 4 SPLIT ELEVON CONFIGURATION (Horten 229 Style)
# ═══════════════════════════════════════════════════════════════

# --- Motors (Differential Thrust) ---
SERVO1_FUNCTION = 73   # ThrottleLeft  - ESC 100A Left Motor
SERVO2_FUNCTION = 74   # ThrottleRight - ESC 100A Right Motor

# --- Split Elevon (4 Servo) ---
SERVO3_FUNCTION = 77   # Elevon 1 - LEFT OUTER  (Cánh ngoài trái)
SERVO4_FUNCTION = 78   # Elevon 2 - RIGHT OUTER (Cánh ngoài phải)
SERVO5_FUNCTION = 79   # Elevon 3 - LEFT INNER  (Cánh trong trái)
SERVO6_FUNCTION = 80   # Elevon 4 - RIGHT INNER (Cánh trong phải)

# ═══════════════════════════════════════════════════════════════
# SERVO DIRECTION (Điều chỉnh theo hướng lắp servo thực tế)
# ═══════════════════════════════════════════════════════════════
# 0 = Normal, 1 = Reversed
# Kiểm tra: Pitch up → Tất cả trailing edge lên
#           Roll right → Trái lên, Phải xuống

SERVO3_REVERSED = 0    # Left Outer  - Đảo nếu servo quay ngược
SERVO4_REVERSED = 0    # Right Outer - Đảo nếu servo quay ngược
SERVO5_REVERSED = 0    # Left Inner  - Đảo nếu servo quay ngược
SERVO6_REVERSED = 0    # Right Inner - Đảo nếu servo quay ngược

# ═══════════════════════════════════════════════════════════════
# SERVO TRIM (Điều chỉnh vị trí trung tâm)
# ═══════════════════════════════════════════════════════════════
SERVO3_TRIM = 1500     # Left Outer neutral position
SERVO4_TRIM = 1500     # Right Outer neutral position
SERVO5_TRIM = 1500     # Left Inner neutral position
SERVO6_TRIM = 1500     # Right Inner neutral position

# ═══════════════════════════════════════════════════════════════
# SERVO TRAVEL LIMITS (Giới hạn hành trình)
# ═══════════════════════════════════════════════════════════════
# MG996R: Khuyến nghị 1000-2000 (có thể mở rộng 900-2100)

SERVO3_MIN = 1000      SERVO3_MAX = 2000
SERVO4_MIN = 1000      SERVO4_MAX = 2000
SERVO5_MIN = 1000      SERVO5_MAX = 2000
SERVO6_MIN = 1000      SERVO6_MAX = 2000
```

### Sơ Đồ Mixing Logic (2 Motor + 4 Split Elevon)

```
                    ┌─────────────────┐
                    │   RC Commands   │
                    │ Throttle, Pitch │
                    │   Roll, Yaw     │
                    └────────┬────────┘
                             │
                             ▼
    ┌────────────────────────────────────────────────────────────┐
    │                      MIXER                                  │
    │                                                             │
    │  ┌─────────── MOTORS (Differential Thrust) ───────────┐   │
    │  │  M1 (Left Motor)  = Throttle + Yaw                  │   │
    │  │  M2 (Right Motor) = Throttle - Yaw                  │   │
    │  └─────────────────────────────────────────────────────┘   │
    │                                                             │
    │  ┌─────────── OUTER ELEVONS (Roll dominant) ───────────┐   │
    │  │  M3 (Left Outer)  = Pitch + Roll                    │   │
    │  │  M4 (Right Outer) = Pitch - Roll                    │   │
    │  └─────────────────────────────────────────────────────┘   │
    │                                                             │
    │  ┌─────────── INNER ELEVONS (Pitch dominant) ──────────┐   │
    │  │  M5 (Left Inner)  = Pitch + Roll * INNER_RATIO      │   │
    │  │  M6 (Right Inner) = Pitch - Roll * INNER_RATIO      │   │
    │  └─────────────────────────────────────────────────────┘   │
    │                                                             │
    └────────────────────────────────────────────────────────────┘
                             │
                             ▼
    ┌────────────────────────────────────────────────────────────┐
    │                  PHYSICAL OUTPUTS                           │
    │                                                             │
    │              ┌─────────────────────────────┐                │
    │              │      FLYING WING TOP VIEW   │                │
    │              │                             │                │
    │   Motor L    │  [M3]         [M4]          │    Motor R     │
    │   D4250      │  L-Out       R-Out          │    D4250       │
    │   600KV      │     ╲         ╱             │    600KV       │
    │     ↓        │  [M5]   ▲   [M6]            │      ↓         │
    │    ⟳        │  L-In   │   R-In            │     ⟳         │
    │   CCW        │         │                   │     CW         │
    │              │      NOSE                   │                │
    │              └─────────────────────────────┘                │
    │                                                             │
    └────────────────────────────────────────────────────────────┘
```

---

### Differential Thrust + Split Elevon Parameters

#### Mission Planner → Config → Full Parameter List

```
# ═══════════════════════════════════════════════════════════════
# DIFFERENTIAL THRUST (Điều khiển yaw bằng chênh lệch motor)
# ═══════════════════════════════════════════════════════════════

# Enable differential thrust for twin engine
RUDD_DT_GAIN = 50          # Differential thrust rate (0-100%)
                            # 50 = motor chênh lệch 50% khi full rudder

# ═══════════════════════════════════════════════════════════════
# ELEVON MIXING PARAMETERS
# ═══════════════════════════════════════════════════════════════

# Mixing gains - điều chỉnh tỷ lệ pitch/roll
MIXING_GAIN = 0.5           # Overall mixing gain
MIXING_OFFSET = 0           # Offset for trim

# Elevon output options
ELEVON_OUTPUT = 4           # 4 = Quad Elevon (4 servo split elevon)

# ═══════════════════════════════════════════════════════════════
# INNER ELEVON RATIO (Tỷ lệ roll cho cánh trong)
# ═══════════════════════════════════════════════════════════════
# Cánh trong ít hiệu quả cho roll, nên giảm tỷ lệ roll

# Option 1: Dùng SERVO_FUNCTION với custom mixing
# Hoặc điều chỉnh trong SERVOx_FUNCTION

# Khuyến nghị cho Horten style:
# - Outer elevon: Full pitch + Full roll
# - Inner elevon: Full pitch + 50% roll (hoặc pitch only)

# ═══════════════════════════════════════════════════════════════
# FLYING WING SPECIFIC PARAMETERS
# ═══════════════════════════════════════════════════════════════

# Frame type
FRAME_CLASS = 1             # Plane
FRAME_TYPE = 2              # Flying Wing

# Control surface throws
PTCH2SRV_RLL = 1.0         # Roll feedforward to pitch
PTCH_RATE_FF = 0.5         # Pitch rate feedforward

# Yaw control (via differential thrust + drag rudder)
YAW2SRV_RLL = 0.5          # Roll to yaw coupling
YAW2SRV_DAMP = 0.1         # Yaw damping

# ═══════════════════════════════════════════════════════════════
# RECOMMENDED TUNING STEPS
# ═══════════════════════════════════════════════════════════════
# 1. Calibrate radio (Radio Calibration)
# 2. Set servo functions như trên
# 3. Test servo direction (Manual mode, không arm)
# 4. Điều chỉnh REVERSED nếu servo sai hướng
# 5. Set TRIM cho mỗi servo (cánh thẳng khi stick neutral)
# 6. Điều chỉnh MIN/MAX cho throw phù hợp
# 7. AUTOTUNE khi bay ổn định
```

---

### 🎯 Differential Throw (Tối Ưu Khí Động Học)

**Differential Throw** là kỹ thuật đặt góc lệch elevon lên/xuống khác nhau để bù đọ adverse yaw:

```
# ═══════════════════════════════════════════════════════════════
# DIFFERENTIAL THROW CONFIGURATION
# ═══════════════════════════════════════════════════════════════
# Trailing edge UP tạo ít drag hơn trailing edge DOWN
# → Khi roll, cánh đi lên cần throw nhiều hơn cánh đi xuống

# Cấu hình thông qua SERVO MIN/MAX không đối xứng:
# Ví dụ: Outer Elevons với Differential 30%

SERVO3_MIN = 1000      # Left Outer - Down limit (normal)
SERVO3_MAX = 2100      # Left Outer - Up limit (+10% extra throw)
SERVO4_MIN = 1000      # Right Outer - Down limit (normal)  
SERVO4_MAX = 2100      # Right Outer - Up limit (+10% extra throw)

# Hoặc dùng MIXING parameter:
DSPOILER_AILMTCH = 100     # Aileron matching percentage
                            # >100 = More up travel than down
                            # <100 = Less up travel than down
```

**Sơ đồ Differential Throw:**
```
                Normal Throw           Differential Throw
                    │                        │
    ┌───────────────┼───────────────┐   ┌────┼────────────────┐
    │               │               │   │    │                │
    │   UP ↑        │    ↑ UP       │   │ UP ↑↑    ↑↑ UP     │ (30% more)
    │   ═══════     │    ═══════    │   │ ════════ ════════  │
    │   DOWN ↓      │    ↓ DOWN     │   │ DOWN ↓   ↓ DOWN    │
    │               │               │   │    │                │
    └───────────────┼───────────────┘   └────┼────────────────┘
         50/50 travel                   70% UP / 30% DOWN
```

---

### 🛬 Crow Braking / Airbrake (Phanh Khí)

**Crow Braking** sử dụng 4 elevon để tạo phanh khí mạnh khi hạ cánh:

```
# ═══════════════════════════════════════════════════════════════
# CROW BRAKING CONFIGURATION (Butterfly/Crow Mix)
# ═══════════════════════════════════════════════════════════════

# DSPOILER = Differential Spoiler
# Cho phép elevon hoạt động như spoiler/airbrake

DSPOILER_OPTS = 7          # Bitmask options:
                            # Bit 0 (1): Progressive crow when flaps deploy
                            # Bit 1 (2): Crow inverts at max flap
                            # Bit 2 (4): Use elevon for airbrake

# Crow mixing weights (%)
DSPOILER_CROW_W1 = 50      # Inner elevon crow percentage (pitch up amount)
DSPOILER_CROW_W2 = 100     # Outer elevon crow percentage (pitch down amount)

# Ý nghĩa:
# - Inner elevon (M5, M6): Trailing edge UP 50% → Tạo lift + drag
# - Outer elevon (M3, M4): Trailing edge DOWN 100% → Tạo drag mạnh

# ═══════════════════════════════════════════════════════════════
# FLAP/AIRBRAKE CHANNEL ASSIGNMENT
# ═══════════════════════════════════════════════════════════════

RC6_OPTION = 208           # RC6 = Airbrake/Crow control
                            # 208 = ARSPD_SW (Airspeed switch)
                            # Hoặc dùng RC6_OPTION = 4 (Flap)

# Flap deployment settings
FLAP_1_PERCNT = 50         # Flap stage 1: 50% crow
FLAP_1_SPEED = 15          # Speed below which flap 1 deploys (m/s)
FLAP_2_PERCNT = 100        # Flap stage 2: 100% crow (full airbrake)
FLAP_2_SPEED = 10          # Speed for full flap

# Landing flap
LAND_FLAP_PERCNT = 100     # Auto deploy 100% flap during landing

# Flap rate limiting
FLAP_SLEWRATE = 75         # Max flap change rate (%/sec)
```

**Sơ đồ Crow Braking:**
```
                NORMAL FLIGHT                    CROW BRAKING (FULL)
                                                
    ┌─────────────────────────────────┐     ┌─────────────────────────────────┐
    │                                 │     │                                 │
    │   [M3]═══════════════════[M4]   │     │   [M3]↘═════════════════↙[M4]   │
    │   L-Out     LEVEL      R-Out    │     │   L-Out   DOWN 100%    R-Out    │
    │         ╲         ╱             │     │         ╲         ╱             │
    │   [M5]═══════════════════[M6]   │     │   [M5]↗═════════════════↖[M6]   │
    │   L-In                  R-In    │     │   L-In    UP 50%       R-In     │
    │                                 │     │                                 │
    │           ▲ NOSE                │     │           ▲ NOSE                │
    └─────────────────────────────────┘     └─────────────────────────────────┘
    
    Drag: Minimal                            Drag: MAXIMUM (Airbrake)
    Lift: Normal                             Lift: Reduced + Pitch up tendency
```

**Ưu điểm Crow Braking:**
1. **Giảm tốc độ nhanh** - Drag lớn từ 4 mặt điều khiển
2. **Kiểm soát pitch** - Inner elevon up bù cho outer elevon down
3. **Landing ngắn** - Tiếp đất với tốc độ thấp hơn
4. **Descent nhanh** - Mất độ cao nhanh mà không tăng tốc

---

### Drag Rudder (Yaw Enhancement)

**Drag Rudder** sử dụng elevon trong để tạo phanh khí động học cho yaw:

```
# Bật drag rudder trên inner elevons
# Inner elevon có thể mở ngược nhau để tạo drag

# Ví dụ khi yaw left:
# - Left Inner mở lên (trailing edge up) → tạo drag bên trái
# - Right Inner mở xuống hoặc giữ neutral

# Cấu hình trong ArduPilot:
DSPOILER_CROW_W1 = 50      # Inner elevon drag percentage
DSPOILER_CROW_W2 = 50
```

---

## 🔧 PHẦN 4: KIỂM TRA SAU KHI HÀN

### Checklist Điện

- [ ] **Continuity test**: Kiểm tra ngắn mạch giữa 5V và GND
- [ ] **Solder joints**: Không có cold solder joints
- [ ] **Wire routing**: Dây không chạm vào cánh quạt/động cơ
- [ ] **Strain relief**: Dây có chống căng

### Checklist Tín Hiệu

- [ ] **GPS**: Nhấp nháy xanh khi có fix
- [ ] **Compass**: Calibrate thành công trong Mission Planner
- [ ] **Lidar**: Đọc khoảng cách chính xác
- [ ] **ELRS**: Bind thành công, RSSI hiển thị
- [ ] **Motor**: Quay đúng chiều
- [ ] **Servo (4x)**: Phản hồi đúng hướng stick

### Bảng Kiểm Tra Motor Direction

```
Nhìn từ phía sau máy bay:

         ↑ (Mũi)
    ⟲         ⟳
   Motor L  Motor R
   (CCW)    (CW)

Throttle tăng → Cả 2 quay
Yaw phải → Motor L tăng, Motor R giảm
```

### Bảng Kiểm Tra Servo Direction (4 Split Elevon)

```
                        ↑ (Mũi máy bay - NOSE)
                        │
    ┌───────────────────┼───────────────────┐
    │                   │                   │
    │   [M3]            │            [M4]   │
    │   L-OUTER         │          R-OUTER  │
    │     ↑             │             ↑     │
    │                   │                   │
    │   [M5]       [FUSELAGE]        [M6]   │
    │   L-INNER         │          R-INNER  │
    │     ↑             │             ↑     │
    │                   │                   │
    └───────────────────┴───────────────────┘
                   TRAILING EDGE
    
═══════════════════════════════════════════════════════════════
KIỂM TRA PITCH (Không arm, Manual mode):
═══════════════════════════════════════════════════════════════
Elevator stick UP (kéo về phía mình):
  → Tất cả 4 servo: Trailing edge UP ↑
  → M3, M4, M5, M6 đều đẩy lên

Elevator stick DOWN (đẩy ra):
  → Tất cả 4 servo: Trailing edge DOWN ↓
  → M3, M4, M5, M6 đều kéo xuống

═══════════════════════════════════════════════════════════════
KIỂM TRA ROLL (Không arm, Manual mode):
═══════════════════════════════════════════════════════════════
Aileron stick RIGHT (nghiêng phải):
  → Servo trái (M3, M5): Trailing edge UP ↑
  → Servo phải (M4, M6): Trailing edge DOWN ↓
  → Máy bay sẽ nghiêng phải

Aileron stick LEFT (nghiêng trái):
  → Servo trái (M3, M5): Trailing edge DOWN ↓
  → Servo phải (M4, M6): Trailing edge UP ↑
  → Máy bay sẽ nghiêng trái

═══════════════════════════════════════════════════════════════
NẾU SAI HƯỚNG → ĐẢO SERVO:
═══════════════════════════════════════════════════════════════
Trong Mission Planner → Config → Full Parameter List:
  SERVO3_REVERSED = 1  (nếu M3 sai hướng)
  SERVO4_REVERSED = 1  (nếu M4 sai hướng)
  SERVO5_REVERSED = 1  (nếu M5 sai hướng)
  SERVO6_REVERSED = 1  (nếu M6 sai hướng)
```

---

## 📝 PHẦN 5: TROUBLESHOOTING

### GPS Không Nhận

1. Kiểm tra TX/RX có bị đảo ngược không
2. Kiểm tra baudrate: 38400 (M8N) hoặc 115200 (M10)
3. Đưa ra ngoài trời, chờ 2-5 phút

### Compass Calibration Failed

1. La bàn quá gần động cơ/ESC → Di chuyển ra xa
2. Nhiễu từ trường → Tránh kim loại lớn gần đó
3. Thử calibrate ở nơi khác

### Motor Không Quay

1. ESC đã arm chưa? (cần tín hiệu throttle min trước)
2. ESC có beep khi cấp nguồn không?
3. Kiểm tra kết nối 3 pha motor

### Servo Jitter (Rung)

1. Nguồn BEC không đủ → Dùng BEC riêng cho servo
2. Tín hiệu nhiễu → Rút ngắn dây tín hiệu
3. FC PWM frequency → Set về 50Hz cho servo analog

### ELRS Không Bind

1. RX đúng version firmware với TX không?
2. Đúng binding phrase chưa?
3. TX/RX có bị đảo không?

---

## 📎 PHỤ LỤC

### A. Danh Sách Linh Kiện (BOM)

#### I. Hệ thống Điều khiển & Dẫn đường
| STT | Linh Kiện | Số Lượng | Ghi Chú |
|-----|-----------|----------|----------|
| 1 | LANRC F4 V3S Plus | 1 | Flight Controller chính |
| 2 | NEO-M8N (GPS) | 1 | Module định vị GPS |
| 3 | QMC5883L (Compass) | 1 | La bàn điện tử |
| 4 | VL53L1X | 1 | Cảm biến khoảng cách (landing) |

#### II. Hệ thống Liên lạc
| STT | Linh Kiện | Số Lượng | Ghi Chú |
|-----|-----------|----------|----------|
| 1 | Radiomaster Pocket | 1 | Tay cầm điều khiển |
| 2 | Radiomaster XR1 Nano 2.4GHz | 1 | Bộ thu ELRS |

#### III. Hệ thống Hộp Đen (ESP32 - ĐỘC LẬP VỚI UAV)
> ⚠️ **Lưu ý**: Hộp đen sử dụng nguồn riêng và có thể tháo rời khỏi UAV.
> Chỉ gắn vào khi bay test để thu thập dữ liệu nghiên cứu.

| STT | Linh Kiện | Số Lượng | Ghi Chú |
|-----|-----------|----------|----------|
| 1 | ESP32-CAM | 1 | Controller chính, gửi GPS về HTTP |
| 2 | GY-9250 | 1 | IMU 9-axis (cho logging riêng) |
| 3 | SD Card | 1 | Lưu trữ log |
| 4 | Module 5G Hotspot | 1 | Phát wifi, truyền video |
| 5 | HC-SR04 | 1 | Cảm biến siêu âm (logging) |
| 6 | Nguồn riêng | 1 | Độc lập với nguồn UAV |

#### IV. Máy tính đồng hành (AI)
| STT | Linh Kiện | Số Lượng | Ghi Chú |
|-----|-----------|----------|----------|
| 1 | Raspberry Pi 3B+ | 1 | Companion computer |
| 2 | Camera OV5647 | 1 | Pi Camera |

#### V. Hệ thống động lực
| STT | Linh Kiện | Số Lượng | Ghi Chú |
|-----|-----------|----------|----------|
| 1 | DXW D4250 600KV | 2 | Motor 3-7S Outrunner |
| 2 | ESC 100A | 2 | Bộ điều tốc động cơ |
| 3 | Servo MG996R | 4 | Split Elevon (2 outer + 2 inner) |
| 4 | Cánh quạt | 2 | In 3D tự thiết kế |

#### VI. Hệ thống nguồn
| STT | Linh Kiện | Số Lượng | Ghi Chú |
|-----|-----------|----------|----------|
| 1 | CNHL 6S 5200mAh 65C | 2 | Cấu hình 6S2P (10400mAh) |
| 2 | Hobbywing 3A UBEC | 1 | Ổn áp cho servo |
| 3 | Mini-360 Buck 3A | 2 | Nguồn ESP32 & Raspberry Pi |

### B. Công Cụ Cần Thiết

- Mỏ hàn có điều chỉnh nhiệt (300-350°C)
- Thiếc hàn 0.5-0.8mm (có chì hoặc không chì)
- Flux (nhựa thông)
- Dây silicon AWG 22-26
- Heat shrink tube
- Multimeter
- Tweezers

### C. Màu Dây Tiêu Chuẩn

| Màu | Chức Năng |
|-----|-----------|
| **Đỏ** | Nguồn dương (+5V, +12V, VBAT) |
| **Đen** | GND (Ground) |
| **Vàng/Cam** | Signal (PWM, UART TX) |
| **Trắng** | Signal (UART RX) |
| **Xanh lá** | SCL (I2C Clock) |
| **Xanh dương** | SDA (I2C Data) |

---

## ⚠️ CẢNH BÁO AN TOÀN

1. **LUÔN** tháo pin trước khi hàn
2. **KHÔNG** để động cơ có cánh quạt khi test
3. **KIỂM TRA** ngắn mạch trước khi cấp nguồn
4. **ARM** chỉ khi máy bay cố định an toàn
5. **FAILSAFE** phải hoạt động trước khi bay

---

*Document maintained by: Trương Công Định & Đặng Duy Long*  
*Last updated: 2025-11-28*
