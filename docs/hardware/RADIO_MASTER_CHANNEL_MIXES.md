# 🎮 RadioMaster Channel Mixes Setup Guide

> **Hướng dẫn cấu hình Channel Mixes cho Flying Wing UAV**  
> Tay cầm: RadioMaster Pocket / Boxer / TX16S  
> Receiver: ELRS XR1 Nano  
> Firmware: EdgeTX 2.10+

---

## 📋 Mục Lục

1. [Tổng Quan Hệ Thống](#-tổng-quan-hệ-thống)
2. [Cấu Hình Model](#-cấu-hình-model)
3. [Channel Assignment](#-channel-assignment)
4. [Mixes Setup](#-mixes-setup)
5. [Split Elevon Configuration](#-split-elevon-configuration)
6. [Flight Modes](#-flight-modes)
7. [AI Mission Modes](#-ai-mission-modes)
8. [Failsafe Configuration](#-failsafe-configuration)
9. [Testing Checklist](#-testing-checklist)

---

## 🎯 Tổng Quan Hệ Thống

### Kiến Trúc Điều Khiển

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  RadioMaster    │────►│   ELRS 2.4GHz   │────►│  LANRC F4 V3S   │
│  Pocket/Boxer   │     │   XR1 Nano RX   │     │  ArduPlane 4.6  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
       │                                                │
       │ EdgeTX 2.10+                                   │
       │ 12 Channels                                    ▼
       │                                    ┌───────────────────────┐
       │                                    │   Servo/Motor Out     │
       └───────────────────────────────────►│   - 2x Motor (Diff)   │
                                            │   - 4x Elevon Servo   │
                                            └───────────────────────┘
```

### Cấu Hình Servo Flying Wing (Split Elevon)

```
                    FLYING WING TOP VIEW
                         (Nose)
                           ▲
                           │
    ┌──────────────────────┴──────────────────────┐
    │                                              │
    │   SERVO3 ◄──┐              ┌──► SERVO4      │
    │   Left Outer│              │Right Outer     │
    │             │              │                │
    │   SERVO5 ◄──┤    BODY     ├──► SERVO6      │
    │   Left Inner│              │Right Inner     │
    │             │              │                │
    └─────────────┼──────────────┼────────────────┘
                  │              │
                  │   MOTOR 1    │   MOTOR 2
                  │   (Left)     │   (Right)
                  └──────────────┘
                      (Tail)
```

---

## 🛠️ Cấu Hình Model

### Bước 1: Tạo Model Mới

1. Vào **MODEL** → **Add New Model**
2. Đặt tên: `FlyingWing_UAV`
3. Chọn **Model Type**: `Plane`

### Bước 2: Setup Cơ Bản

| Setting | Value |
|---------|-------|
| **Internal RF** | ELRS |
| **External RF** | Off |
| **Receiver** | ELRS 2.4G |
| **Channel Order** | AETR (Aileron, Elevator, Throttle, Rudder) |
| **Trim** | On |

### Bước 3: USB Joystick Mode (Tùy chọn - cho Simulator)

| Setting | Value |
|---------|-------|
| **USB Mode** | Joystick |
| **Joystick Mode** | Classic |

---

## 📡 Channel Assignment

### Bảng Phân Bổ Channel Đầy Đủ

| Channel | Function | Input | ArduPilot | Ghi Chú |
|---------|----------|-------|-----------|---------|
| **CH1** | Aileron (Roll) | Stick Right X | SERVO1-4 mixing | Split Elevon left/right |
| **CH2** | Elevator (Pitch) | Stick Right Y | SERVO1-4 mixing | Split Elevon up/down |
| **CH3** | Throttle | Stick Left Y | SERVO1/2 Motor | Differential thrust |
| **CH4** | Rudder (Yaw) | Stick Left X | SERVO1/2 Diff | Yaw via differential |
| **CH5** | Flight Mode | SWA (3-pos) | FLTMODE | Manual/Stabilize/Auto |
| **CH6** | AI Mission Mode | SWB (3-pos) | RC6_OPTION | Search/Track/Recon |
| **CH7** | Detection Freq | SWC (3-pos) | RC7_OPTION | Low/Med/High |
| **CH8** | Emergency/RTH | SWD (2-pos) | RC8_OPTION | Normal/Emergency |
| **CH9** | Camera Trigger | POT1 | RC9_OPTION | Camera shutter |
| **CH10** | Gimbal Pitch | POT2 | RC10_OPTION | Camera angle |
| **CH11** | Reserved | - | - | Future use |
| **CH12** | Reserved | - | - | Future use |

### Switch Mapping (RadioMaster)

| Switch | Position | EdgeTX Value | Function |
|--------|----------|--------------|----------|
| **SWA** | Up | -100% | Manual Mode |
| **SWA** | Mid | 0% | Stabilize Mode |
| **SWA** | Down | +100% | Auto/Mission Mode |
| **SWB** | Up | -100% | AI: Search & Rescue |
| **SWB** | Mid | 0% | AI: People Counting |
| **SWB** | Down | +100% | AI: Reconnaissance |
| **SWC** | Up | -100% | Detection: Low (1 FPS) |
| **SWC** | Mid | 0% | Detection: Med (5 FPS) |
| **SWC** | Down | +100% | Detection: High (10 FPS) |
| **SWD** | Up | -100% | Normal Operation |
| **SWD** | Down | +100% | Emergency RTH |

---

## 🔧 Mixes Setup

### INPUTS Configuration

Vào **MODEL** → **INPUTS**:

```
I1: [Ail] Ail  Weight(+100%) Switch() Trim(ON)
    Source: J2 (Right Stick X)
    
I2: [Ele] Ele  Weight(+100%) Switch() Trim(ON)
    Source: J1 (Right Stick Y)
    
I3: [Thr] Thr  Weight(+100%) Switch() Trim(OFF)
    Source: J3 (Left Stick Y)
    
I4: [Rud] Rud  Weight(+100%) Switch() Trim(ON)
    Source: J4 (Left Stick X)
    
I5: [FMod] FMod Weight(+100%) Switch()
    Source: SA
    
I6: [AIMode] AIMode Weight(+100%) Switch()
    Source: SB
    
I7: [DetFrq] DetFrq Weight(+100%) Switch()
    Source: SC
    
I8: [Emerg] Emerg Weight(+100%) Switch()
    Source: SD
```

### MIXES Configuration

Vào **MODEL** → **MIXES**:

#### CH1 - Aileron (Left Elevon Mix)

```
CH1: [Ail-L]
├─ M1: Ail  Weight(+50%)  Multiplex: Add
│   Source: [Ail]
│   Curve: ---
│   
└─ M2: Ele  Weight(+50%)  Multiplex: Add
    Source: [Ele]
    Curve: ---
```

#### CH2 - Elevator (Right Elevon Mix)

```
CH2: [Ail-R]
├─ M1: Ail  Weight(-50%)  Multiplex: Add
│   Source: [Ail]
│   Curve: ---
│   
└─ M2: Ele  Weight(+50%)  Multiplex: Add
    Source: [Ele]
    Curve: ---
```

#### CH3 - Throttle (Left Motor)

```
CH3: [Thr-L]
├─ M1: Thr  Weight(+100%)  Multiplex: Replace
│   Source: [Thr]
│   
└─ M2: Rud  Weight(+25%)  Multiplex: Add
    Source: [Rud]
    Note: Differential thrust for yaw
```

#### CH4 - Throttle (Right Motor) 

```
CH4: [Thr-R]
├─ M1: Thr  Weight(+100%)  Multiplex: Replace
│   Source: [Thr]
│   
└─ M2: Rud  Weight(-25%)  Multiplex: Add
    Source: [Rud]
    Note: Differential thrust for yaw
```

#### CH5 - Flight Mode

```
CH5: [FMode]
└─ M1: FMod  Weight(+100%)  Multiplex: Replace
    Source: [FMod]
```

#### CH6 - AI Mission Mode

```
CH6: [AIMode]
└─ M1: AIMode  Weight(+100%)  Multiplex: Replace
    Source: [AIMode]
```

#### CH7 - Detection Frequency

```
CH7: [DetFrq]
└─ M1: DetFrq  Weight(+100%)  Multiplex: Replace
    Source: [DetFrq]
```

#### CH8 - Emergency

```
CH8: [Emerg]
└─ M1: Emerg  Weight(+100%)  Multiplex: Replace
    Source: [Emerg]
```

---

## ✈️ Split Elevon Configuration

### Tại Sao Dùng Split Elevon?

| Ưu Điểm | Mô Tả |
|---------|-------|
| **Diện tích điều khiển lớn** | 4 servo thay vì 2, tăng authority |
| **Redundancy** | 1 servo hỏng vẫn điều khiển được |
| **Roll rate cao** | Phù hợp cho aggressive maneuvers |
| **Horten 229 style** | Authentic flying wing design |

### ArduPilot Servo Functions

Cấu hình trong Mission Planner:

| Parameter | Value | Function |
|-----------|-------|----------|
| `SERVO1_FUNCTION` | 33 | Motor Left |
| `SERVO2_FUNCTION` | 34 | Motor Right |
| `SERVO3_FUNCTION` | 77 | Elevon Left Outer |
| `SERVO4_FUNCTION` | 78 | Elevon Right Outer |
| `SERVO5_FUNCTION` | 79 | Elevon Left Inner |
| `SERVO6_FUNCTION` | 80 | Elevon Right Inner |

### Servo Direction (SERVO_REVERSED)

```
SERVO3_REVERSED = 0  (hoặc 1 tùy hướng lắp)
SERVO4_REVERSED = 0
SERVO5_REVERSED = 0
SERVO6_REVERSED = 0
```

> ⚠️ **Kiểm tra trước khi bay**: Đẩy stick lên (pitch up), tất cả elevon phải đi LÊN!

### Mixing Gains

```
ELEVON_MIXING = 1  (Enable)
ELEVON_OUTPUT = 1  (Use SERVO3-6)

# Tuning
PTCH2SRV_RLL = 1.0   (Pitch roll compensation)
MIXING_GAIN = 0.5    (Reduce if twitchy)
```

---

## 🛫 Flight Modes

### ArduPilot Flight Mode Setup

| SWA Position | PWM Range | Mode | Mô Tả |
|--------------|-----------|------|-------|
| Up (-100%) | 900-1100 | MANUAL | Full manual control |
| Mid (0%) | 1400-1600 | FBWA | Fly-By-Wire A (stabilized) |
| Down (+100%) | 1900-2100 | AUTO | Autonomous mission |

### Mission Planner Configuration

```
FLTMODE_CH = 5
FLTMODE1 = 0   (Manual)
FLTMODE2 = 5   (FBWA)
FLTMODE3 = 10  (Auto)
FLTMODE4 = 11  (RTL) - Optional
FLTMODE5 = 4   (Guided) - Optional
FLTMODE6 = 17  (Takeoff) - Optional
```

---

## 🤖 AI Mission Modes

### Channel 6 - AI Mode Selection

| SWB Position | PWM | AI Mode | Detection Focus |
|--------------|-----|---------|-----------------|
| Up | 1000 | Search & Rescue | Người, thuyền |
| Mid | 1500 | People Counting | Người only |
| Down | 2000 | Reconnaissance | Tất cả objects |

### Channel 7 - Detection Frequency

| SWC Position | PWM | Frequency | Power Usage |
|--------------|-----|-----------|-------------|
| Up | 1000 | Low (1 FPS) | 🔋 Tiết kiệm |
| Mid | 1500 | Med (5 FPS) | 🔋🔋 Balanced |
| Down | 2000 | High (10 FPS) | 🔋🔋🔋 Max |

### ArduPilot RC Options

```
RC6_OPTION = 0   (AI Mode - handled by companion)
RC7_OPTION = 0   (Detection Freq - handled by companion)
RC8_OPTION = 4   (RTL - Emergency)
```

---

## ⚠️ Failsafe Configuration

### EdgeTX Failsafe

Vào **MODEL** → **FAILSAFE**:

| Channel | Mode | Value | Reason |
|---------|------|-------|--------|
| CH1 | Hold | - | Giữ roll hiện tại |
| CH2 | Hold | - | Giữ pitch hiện tại |
| CH3 | Custom | -50% | Giảm throttle |
| CH4 | Hold | - | Giữ yaw hiện tại |
| CH5 | Custom | +100% | AUTO mode (RTL) |
| CH6-8 | Hold | - | Giữ nguyên |

### ArduPilot Failsafe

```
# RC Failsafe
FS_SHORT_ACTN = 0    (Disabled - let FC handle)
FS_SHORT_TIMEOUT = 1.5
FS_LONG_ACTN = 1     (RTL)
FS_LONG_TIMEOUT = 5

# Throttle Failsafe
THR_FAILSAFE = 1     (Enabled)
THR_FS_VALUE = 950   (Below this = failsafe)

# GCS Failsafe
FS_GCS_ENABL = 1     (RTL on GCS loss)
```

### ELRS Failsafe

```
# In ELRS Configurator
Failsafe Mode: No Pulses
# ArduPilot will detect no signal and trigger failsafe
```

---

## ✅ Testing Checklist

### Bước 1: Bench Test (Không Cấp Nguồn Motor)

- [ ] Tất cả switch hoạt động đúng hướng
- [ ] Stick centering chính xác (1500us)
- [ ] Throttle từ 1000 đến 2000us
- [ ] Trim hoạt động cho Ail, Ele, Rud

### Bước 2: RC Range Test

```
# ELRS Range Test Mode
1. Đặt TX ở chế độ Range Test (giảm công suất)
2. Đi xa 50m
3. Kiểm tra RSSI > -90dBm
4. Kiểm tra LQ > 50%
```

### Bước 3: Servo Direction Test

| Input | Expected Servo Movement |
|-------|------------------------|
| Pitch Up (Ele stick back) | All elevons UP |
| Pitch Down (Ele stick forward) | All elevons DOWN |
| Roll Left (Ail stick left) | Left elevons UP, Right DOWN |
| Roll Right (Ail stick right) | Right elevons UP, Left DOWN |
| Yaw Left (Rud stick left) | Left motor SLOWER |
| Yaw Right (Rud stick right) | Right motor SLOWER |

### Bước 4: Flight Mode Test

- [ ] SWA Up → Mission Planner hiện MANUAL
- [ ] SWA Mid → Mission Planner hiện FBWA
- [ ] SWA Down → Mission Planner hiện AUTO

### Bước 5: Failsafe Test

1. **RC Loss Test**:
   - Tắt TX
   - Chờ 5s
   - FC chuyển sang RTL mode
   - Bật lại TX → resume control

2. **Low Battery Test**:
   - Giả lập voltage thấp
   - Kiểm tra cảnh báo GCS

---

## 📝 Troubleshooting

### Vấn Đề Thường Gặp

| Vấn Đề | Nguyên Nhân | Giải Pháp |
|--------|-------------|-----------|
| Servo đi sai hướng | SERVO_REVERSED sai | Đổi giá trị 0↔1 |
| Không có response | Channel mapping sai | Kiểm tra RC_MAP |
| Jitter trên servo | Noise / bad calibration | Re-calibrate, add capacitor |
| Flight mode không đổi | PWM range sai | Check FLTMODE_CH setting |
| AI mode không nhận | Companion không đọc RC | Check MAVLink connection |

### Debug Commands (Mission Planner)

```
# Xem RC Input
status RC_CHANNELS

# Xem Servo Output
status SERVO_OUTPUT_RAW

# Xem Flight Mode
status HEARTBEAT
```

---

## 📚 Tài Liệu Tham Khảo

- [EdgeTX Manual](https://edgetx.org/user-manual/)
- [ArduPlane Servo Functions](https://ardupilot.org/plane/docs/parameters.html#servo-functions)
- [ELRS Documentation](https://www.expresslrs.org/)
- [RadioMaster Pocket Manual](https://radiomasterrc.com/)

---

*Tài liệu này được tạo bởi: **Trương Công Định & Đặng Duy Long***  
*Cập nhật: 01/12/2025*  
*Version: 1.0.0*
