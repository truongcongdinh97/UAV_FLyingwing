# Communication Protocol Specification

## Flying Wing UAV - Communication Protocol v1.0

Protocol định nghĩa communication giữa các components:
- **Flight Controller (FC)** ↔ **Raspberry Pi (Companion)**
- **Raspberry Pi** ↔ **Ground Station**
- **Ground Station** ↔ **Flight Controller** (via Companion)

---

## 1. FC ↔ Raspberry Pi Communication

### Physical Layer
- **Interface**: UART (Serial)
- **Port**: `/dev/serial0` (RPi GPIO 14/15)
- **Baudrate**: 115200 bps
- **Protocol**: MAVLink v2.0 (primary) hoặc MSP (backup)

### MAVLink Messages

#### 1.1. Telemetry từ FC → Pi (High Frequency, 10-50 Hz)

**ATTITUDE** (30 Hz)
```
Message ID: 30
Fields:
  - time_boot_ms: uint32 (ms since boot)
  - roll: float (rad)
  - pitch: float (rad)
  - yaw: float (rad)
  - rollspeed: float (rad/s)
  - pitchspeed: float (rad/s)
  - yawspeed: float (rad/s)
```

**GLOBAL_POSITION_INT** (10 Hz)
```
Message ID: 33
Fields:
  - time_boot_ms: uint32
  - lat: int32 (degE7, latitude * 10^7)
  - lon: int32 (degE7, longitude * 10^7)
  - alt: int32 (mm, altitude MSL)
  - relative_alt: int32 (mm, altitude AGL)
  - vx: int16 (cm/s, velocity X)
  - vy: int16 (cm/s, velocity Y)
  - vz: int16 (cm/s, velocity Z)
  - hdg: uint16 (cdeg, heading * 100)
```

**SYS_STATUS** (1 Hz)
```
Message ID: 1
Fields:
  - voltage_battery: uint16 (mV)
  - current_battery: int16 (cA, 10mA)
  - battery_remaining: int8 (%)
  - drop_rate_comm: uint16 (%)
```

**GPS_RAW_INT** (5 Hz)
```
Message ID: 24
Fields:
  - time_usec: uint64
  - fix_type: uint8 (0=No, 3=3D Fix)
  - lat: int32 (degE7)
  - lon: int32 (degE7)
  - alt: int32 (mm)
  - eph: uint16 (cm, HDOP)
  - satellites_visible: uint8
```

#### 1.2. Commands từ Pi → FC (Event-driven)

**COMMAND_LONG** 
```
Message ID: 76
Common Commands:
  - MAV_CMD_NAV_TAKEOFF (22): Takeoff
  - MAV_CMD_NAV_LAND (21): Land
  - MAV_CMD_NAV_RETURN_TO_LAUNCH (20): RTH
  - MAV_CMD_DO_SET_MODE (176): Change flight mode
  - MAV_CMD_COMPONENT_ARM_DISARM (400): Arm/Disarm

Format:
  - command: uint16
  - param1-7: float
  - target_system: uint8
  - target_component: uint8
```

**MISSION_ITEM** (Waypoint Upload)
```
Message ID: 39
Fields:
  - seq: uint16 (waypoint sequence)
  - frame: uint8 (coordinate frame)
  - command: uint16 (MAV_CMD)
  - current: uint8 (1 if current)
  - autocontinue: uint8
  - param1-4: float
  - x: float (latitude)
  - y: float (longitude)
  - z: float (altitude)
```

**SET_POSITION_TARGET_GLOBAL_INT** (Position Control)
```
Message ID: 86
Fields:
  - time_boot_ms: uint32
  - target_system: uint8
  - coordinate_frame: uint8
  - type_mask: uint16
  - lat_int: int32 (degE7)
  - lon_int: int32 (degE7)
  - alt: float (m)
  - vx, vy, vz: float (m/s)
```

---

## 2. Custom Protocol Extension (Trên MAVLink)

### 2.1. Differential Thrust Control

**Custom Message: TWIN_ENGINE_CONTROL**
```
Message ID: 10001 (custom range)
Frequency: 50 Hz (khi active)
Direction: Pi → FC

Fields:
  - left_throttle: uint16 (1000-2000, PWM)
  - right_throttle: uint16 (1000-2000, PWM)
  - mode: uint8
    * 0 = MANUAL (override)
    * 1 = DIFFERENTIAL (automatic differential)
    * 2 = SYNCHRONIZED (same throttle)
  - differential_gain: float (0.0-1.0)
```

### 2.2. AI Detection Results

**Custom Message: AI_DETECTION**
```
Message ID: 10002
Frequency: Variable (khi có detection)
Direction: Pi → Ground Station (via FC relay hoặc direct 5G)

Fields:
  - timestamp: uint64 (us)
  - detection_count: uint8
  - detections: array[10] of:
    * class_id: uint8
    * confidence: float
    * bbox_x1: uint16 (pixel)
    * bbox_y1: uint16
    * bbox_x2: uint16
    * bbox_y2: uint16
    * gps_lat: int32 (degE7, if geo-referenced)
    * gps_lon: int32 (degE7)
```

### 2.3. System Health

**Custom Message: COMPANION_HEALTH**
```
Message ID: 10003
Frequency: 1 Hz
Direction: Pi → FC

Fields:
  - cpu_usage: uint8 (%)
  - cpu_temp: uint16 (0.01°C)
  - memory_usage: uint8 (%)
  - disk_usage: uint8 (%)
  - camera_status: uint8 (0=Off, 1=On, 2=Error)
  - ai_status: uint8
  - network_status: uint8 (0=Disconnected, 1=WiFi, 2=5G)
  - link_quality: uint8 (0-100%)
```

---

## 3. Pi ↔ Ground Station Communication

### 3.1. Transport Layer

**Primary**: 5G/WiFi TCP/IP
- **Port**: 14550 (MAVLink standard)
- **Protocol**: MAVLink v2.0 over TCP
- **Backup**: UDP port 14551

**Secondary**: Radio telemetry (long range)
- **Via**: FC radio module
- **Baudrate**: 57600 bps
- **Range**: 5-10 km

### 3.2. Video Streaming

**Protocol**: RTSP (Real-Time Streaming Protocol)
- **Port**: 8554
- **Format**: H.264
- **Resolution**: 640x480 @ 15fps (adjustable)
- **Bitrate**: 500-1000 kbps
- **URL**: `rtsp://192.168.1.10:8554/stream`

**Alternative**: WebRTC (low latency)
- **Port**: 8080
- **Latency**: <200ms
- **For**: Real-time control

### 3.3. Data Channels

**Channel 1: Telemetry** (High Priority)
- MAVLink HEARTBEAT (1 Hz)
- ATTITUDE, GPS, Battery (10-30 Hz)
- System Status (1 Hz)

**Channel 2: Video** (Medium Priority)
- RTSP stream
- Adaptive bitrate

**Channel 3: Commands** (Critical Priority)
- Waypoint upload
- Mode changes
- Emergency commands

**Channel 4: Data Logging** (Low Priority)
- Log file transfer
- Mission data download

---

## 4. Message Priorities & QoS

### Priority Levels

**CRITICAL** (P0)
- Emergency stop
- Failsafe triggers
- Disarm commands
- **Latency**: <50ms
- **Reliability**: Guaranteed delivery

**HIGH** (P1)
- Mode changes
- Waypoint commands
- Attitude control
- **Latency**: <100ms
- **Reliability**: Retry up to 3x

**NORMAL** (P2)
- Telemetry data
- GPS updates
- **Latency**: <500ms
- **Reliability**: Best effort

**LOW** (P3)
- Log data
- Statistics
- **Latency**: No limit
- **Reliability**: Best effort

---

## 5. Failsafe & Error Handling

### 5.1. Connection Loss Scenarios

**Scenario 1: Pi ↔ FC Link Lost**
```
Trigger: No HEARTBEAT for 3 seconds
FC Action:
  1. Log error
  2. Continue autonomous mission if active
  3. If no mission: Loiter mode
  4. After 30s: RTH

Pi Action:
  1. Attempt reconnect (10 retries)
  2. Log to local storage
  3. Notify Ground Station via 5G
```

**Scenario 2: Ground Station Link Lost**
```
Trigger: No GCS HEARTBEAT for 5 seconds
Pi Action:
  1. Continue mission autonomously
  2. Buffer telemetry data
  3. Reduce video bitrate (save bandwidth)
  4. Attempt reconnect

FC Action:
  1. No immediate action (Pi controls)
  2. Continue mission
  3. Monitor Pi health via COMPANION_HEALTH
```

**Scenario 3: Both Links Lost**
```
Trigger: No GCS and no manual control
FC Action:
  1. Execute pre-programmed failsafe
  2. If in mission: Continue to next waypoint
  3. If battery < 30%: RTH immediately
  4. If battery < 15%: Emergency land at safest location
```

### 5.2. Data Integrity

**CRC Check**: MAVLink built-in CRC
**Sequence Numbers**: Detect dropped packets
**Acknowledgments**: For critical commands
**Retry Logic**: 3 attempts with exponential backoff

---

## 6. Protocol State Machine

### Flight Controller States
```
BOOT → INIT → STANDBY → ARMED → FLYING → LANDING → DISARMED
         ↓                ↓        ↓         ↓
       ERROR ← ─ ─ ─ ─ ─ ─ ┴ ─ ─ ─ ┴ ─ ─ ─ ─ ┘
```

### Companion Computer States
```
BOOT → INIT → READY → STREAMING → MISSION_ACTIVE → LANDING
        ↓       ↓         ↓             ↓              ↓
      ERROR ← ─ ┴ ─ ─ ─ ─ ┴ ─ ─ ─ ─ ─ ─ ┴ ─ ─ ─ ─ ─ ─ ┘
```

### State Synchronization
- FC broadcasts state via HEARTBEAT.system_status
- Pi tracks FC state and adapts behavior
- GS monitors both states

---

## 7. Implementation Example

### Python (Raspberry Pi)

```python
from pymavlink import mavutil

# Connect to FC
master = mavutil.mavlink_connection('/dev/serial0', baud=115200)

# Wait for heartbeat
master.wait_heartbeat()
print(f"Connected to system {master.target_system}")

# Request data streams
master.mav.request_data_stream_send(
    master.target_system,
    master.target_component,
    mavutil.mavlink.MAV_DATA_STREAM_ALL,
    10,  # Hz
    1    # Start
)

# Read telemetry
while True:
    msg = master.recv_match(blocking=True)
    if msg.get_type() == 'ATTITUDE':
        print(f"Roll: {msg.roll}, Pitch: {msg.pitch}")
    
# Send command
master.mav.command_long_send(
    master.target_system,
    master.target_component,
    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
    0, 0, 0, 0, 0, 0, 0, 10  # 10m altitude
)
```

### C++ (Flight Controller - iNav)

```cpp
// Send attitude (in main loop)
mavlink_msg_attitude_send(
    MAVLINK_COMM_0,
    millis(),
    attitude.roll,
    attitude.pitch,
    attitude.yaw,
    gyro.x, gyro.y, gyro.z
);

// Receive command
mavlink_message_t msg;
mavlink_status_t status;

if (mavlink_parse_char(MAVLINK_COMM_0, byte, &msg, &status)) {
    if (msg.msgid == MAVLINK_MSG_ID_COMMAND_LONG) {
        mavlink_command_long_t cmd;
        mavlink_msg_command_long_decode(&msg, &cmd);
        
        if (cmd.command == MAV_CMD_NAV_TAKEOFF) {
            // Execute takeoff
        }
    }
}
```

---

## 8. Testing & Validation

### Test Cases

1. **Latency Test**: Measure round-trip time
2. **Throughput Test**: Maximum message rate
3. **Packet Loss Test**: Simulate poor connection
4. **Failsafe Test**: Trigger各種失connection scenarios
5. **State Sync Test**: Verify state machine transitions
6. **Command Response**: Test command execution
7. **Multi-stream Test**: Telemetry + Video + Commands

### Tools
- **MAVProxy**: Ground station testing
- **QGroundControl**: Full GCS testing
- **Wireshark**: Protocol analysis
- **tcpdump**: Network debugging

---

## 9. Security Considerations

### Authentication
- **Challenge-Response**: Verify GCS identity
- **Session Keys**: Encrypted communication
- **Command Validation**: Whitelist allowed commands

### Encryption
- **TLS/SSL**: For TCP connections
- **AES-256**: For sensitive data
- **Key Rotation**: Every flight session

### Access Control
- **Read-Only**: Telemetry access
- **Operator**: Basic commands
- **Admin**: Full control

---

## Summary

✅ **Standardized**: Based on MAVLink v2.0  
✅ **Extensible**: Custom messages for specific features  
✅ **Robust**: Failsafe & error handling  
✅ **Efficient**: Priority-based message routing  
✅ **Secure**: Authentication & encryption ready  
✅ **Testable**: Clear test procedures  

**Next**: Implement protocol handlers trong firmware và companion computer.
