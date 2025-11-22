# iNav Custom Firmware Architecture

## Flying Wing UAV - Firmware Customization Guide

Tài liệu này mô tả custom firmware dựa trên iNav cho UAV cánh bay động cơ kép.

---

## 1. Base Firmware: iNav

### Version
- **Base**: iNav 7.x hoặc mới hơn
- **Target**: Generic STM32F4/F7 boards (LANRC F4 V3S Plus)
- **Build System**: Make/CMake

### Why iNav?
✅ **Autonomous Navigation**: Waypoint mission planner  
✅ **GPS Features**: RTH, Position Hold  
✅ **Configurable**: Mixer support cho custom layouts  
✅ **Open Source**: Full source code access  
✅ **Active Community**: Regular updates & support  

---

## 2. Custom Features to Implement

### 2.1. Differential Thrust Control

**Purpose**: Điều khiển yaw bằng 2 động cơ độc lập

**Implementation**:
```
File: src/main/flight/mixer_custom.c

Features:
- Independent throttle control per motor
- Yaw authority calculation
- Auto-mixing với aileron (elevon)
- Emergency symmetry mode
```

**Mixer Configuration**:
```c
// Twin engine flying wing mixer
const mixerRule_t customMixerTwinEngine[] = {
    // Motor 1 (Left): Throttle + Yaw
    { MIXER_MOTOR1, INPUT_THROTTLE, 1000, 0, MIXER_OP_ADD },
    { MIXER_MOTOR1, INPUT_YAW, -500, 0, MIXER_OP_ADD },
    
    // Motor 2 (Right): Throttle - Yaw
    { MIXER_MOTOR2, INPUT_THROTTLE, 1000, 0, MIXER_OP_ADD },
    { MIXER_MOTOR2, INPUT_YAW, 500, 0, MIXER_OP_ADD },
    
    // Elevon Left: Pitch + Roll
    { MIXER_SERVO1, INPUT_PITCH, 500, 0, MIXER_OP_ADD },
    { MIXER_SERVO1, INPUT_ROLL, -500, 0, MIXER_OP_ADD },
    
    // Elevon Right: Pitch - Roll
    { MIXER_SERVO2, INPUT_PITCH, 500, 0, MIXER_OP_ADD },
    { MIXER_SERVO2, INPUT_ROLL, 500, 0, MIXER_OP_ADD },
};
```

**Control Logic**:
```c
// Differential thrust gain (settable via CLI)
float differentialThrustGain = 0.5f; // 0.0 - 1.0

void applyDifferentialThrust(void) {
    int16_t yawInput = rcCommand[YAW];
    int16_t throttle = rcCommand[THROTTLE];
    
    // Calculate differential
    int16_t differential = yawInput * differentialThrustGain;
    
    // Apply to motors
    motor[MOTOR_LEFT] = constrain(throttle + differential, 1000, 2000);
    motor[MOTOR_RIGHT] = constrain(throttle - differential, 1000, 2000);
    
    // Log for telemetry
    blackboxWriteMotorDifferential(differential);
}
```

### 2.2. Loiter Mode

**Purpose**: Bay vòng tròn quanh điểm cố định

**Implementation**:
```
File: src/main/navigation/navigation_pos_estimator.c
File: src/main/navigation/navigation_loiter.c
```

**Mode Configuration**:
```c
typedef struct {
    gpsLocation_t center;     // Tâm vòng tròn
    float radius;             // Bán kính (m)
    float altitude;           // Độ cao (m)
    float speed;              // Tốc độ (m/s)
    bool clockwise;           // Chiều quay
} loiterConfig_t;

// Default config
loiterConfig_t loiterConfig = {
    .radius = 50.0f,          // 50m radius
    .altitude = 50.0f,        // 50m altitude
    .speed = 15.0f,           // 15 m/s
    .clockwise = true,
};
```

**Control Algorithm**:
```c
void navigationLoiterUpdate(void) {
    // Calculate vector from UAV to center
    float dx = loiterCenter.lon - gpsPosition.lon;
    float dy = loiterCenter.lat - gpsPosition.lat;
    float distanceToCenter = sqrtf(dx*dx + dy*dy);
    
    // Calculate tangent vector (perpendicular)
    float tangentX = -dy;
    float tangentY = dx;
    
    // Normalize
    float tangentMag = sqrtf(tangentX*tangentX + tangentY*tangentY);
    tangentX /= tangentMag;
    tangentY /= tangentMag;
    
    // PID controller to maintain radius
    float radiusError = distanceToCenter - loiterConfig.radius;
    float correction = pidControllerApply(&loiterPID, radiusError);
    
    // Calculate desired velocity
    velocityTarget.x = tangentX * loiterConfig.speed + correction * dx;
    velocityTarget.y = tangentY * loiterConfig.speed + correction * dy;
    
    // Apply to navigation
    navigationSetVelocityTarget(&velocityTarget);
}
```

### 2.3. Geofencing

**Purpose**: Hàng rào ảo giới hạn vùng bay

**Implementation**:
```
File: src/main/navigation/navigation_geofence.c
```

**Geofence Types**:

**Cylindrical Geofence** (đơn giản nhất)
```c
typedef struct {
    gpsLocation_t center;
    float radius;             // m
    float minAltitude;        // m
    float maxAltitude;        // m
    bool enabled;
} geofenceConfig_t;

bool isInsideGeofence(gpsLocation_t position) {
    float distance = calculateDistance(geofenceConfig.center, position);
    
    if (distance > geofenceConfig.radius)
        return false;
    
    if (position.alt < geofenceConfig.minAltitude || 
        position.alt > geofenceConfig.maxAltitude)
        return false;
    
    return true;
}
```

**Polygon Geofence** (advanced)
```c
typedef struct {
    gpsLocation_t vertices[MAX_VERTICES];
    uint8_t vertexCount;
    float minAltitude;
    float maxAltitude;
} polygonGeofence_t;

// Point-in-polygon algorithm (ray casting)
bool isInsidePolygon(gpsLocation_t position, polygonGeofence_t* fence);
```

**Geofence Actions**:
```c
typedef enum {
    GEOFENCE_ACTION_NONE = 0,
    GEOFENCE_ACTION_WARNING,      // Just warn
    GEOFENCE_ACTION_LOITER,       // Stop and loiter
    GEOFENCE_ACTION_RTH,          // Return to home
    GEOFENCE_ACTION_LAND,         // Emergency land
} geofenceAction_e;

void handleGeofenceViolation(geofenceAction_e action) {
    switch (action) {
        case GEOFENCE_ACTION_WARNING:
            beeper(BEEPER_GEOFENCE_WARNING);
            telemetryLog("Geofence warning");
            break;
            
        case GEOFENCE_ACTION_LOITER:
            setFlightMode(NAV_LOITER_MODE);
            break;
            
        case GEOFENCE_ACTION_RTH:
            setFlightMode(NAV_RTH_MODE);
            break;
            
        case GEOFENCE_ACTION_LAND:
            setFlightMode(NAV_LAND_MODE);
            break;
    }
}
```

### 2.4. Failsafe State Machine

**Purpose**: Xử lý tình huống mất kết nối

**States**:
```
NORMAL → LINK_DEGRADED → LINK_LOST → EMERGENCY
   ↑                                      ↓
   └──────────────────────────────────────┘
```

**Implementation**:
```
File: src/main/fc/failsafe.c
```

**State Machine**:
```c
typedef enum {
    FAILSAFE_IDLE,
    FAILSAFE_RX_LOSS_DETECTED,
    FAILSAFE_RX_LOSS_IDLE,
    FAILSAFE_RX_LOSS_RECOVERY,
    FAILSAFE_LANDED,
    FAILSAFE_EMERGENCY
} failsafeState_e;

typedef struct {
    uint32_t lastRxUpdate;
    uint32_t lastCompanionUpdate;
    uint32_t lastGCSUpdate;
    failsafeState_e state;
    uint8_t phase;
} failsafeState_t;

void failsafeUpdateState(void) {
    uint32_t now = millis();
    
    // Check RX link
    bool rxLost = (now - failsafeState.lastRxUpdate) > 1000; // 1s timeout
    
    // Check Companion link
    bool companionLost = (now - failsafeState.lastCompanionUpdate) > 3000; // 3s
    
    // Check GCS link (via companion)
    bool gcsLost = (now - failsafeState.lastGCSUpdate) > 5000; // 5s
    
    // State machine
    switch (failsafeState.state) {
        case FAILSAFE_IDLE:
            if (rxLost && companionLost) {
                failsafeState.state = FAILSAFE_RX_LOSS_DETECTED;
                failsafeState.phase = 0;
            }
            break;
            
        case FAILSAFE_RX_LOSS_DETECTED:
            // Phase 0: First 10 seconds - continue mission
            if (failsafeState.phase == 0) {
                if ((now - failsafeState.lastRxUpdate) > 10000) {
                    failsafeState.phase = 1;
                }
            }
            // Phase 1: Check battery
            else if (failsafeState.phase == 1) {
                if (getBatteryPercent() < 30) {
                    // Low battery - RTH immediately
                    activateFailsafe(FAILSAFE_RTH);
                } else {
                    // Continue mission but monitor
                    failsafeState.phase = 2;
                }
            }
            // Phase 2: After 30 seconds - RTH
            else if (failsafeState.phase == 2) {
                if ((now - failsafeState.lastRxUpdate) > 30000) {
                    activateFailsafe(FAILSAFE_RTH);
                }
            }
            break;
            
        case FAILSAFE_RX_LOSS_RECOVERY:
            if (!rxLost || !companionLost) {
                failsafeState.state = FAILSAFE_IDLE;
                resumeNormalOperation();
            }
            break;
    }
}
```

**Failsafe Actions**:
```c
void activateFailsafe(failsafeAction_e action) {
    switch (action) {
        case FAILSAFE_CONTINUE:
            // Continue current mission
            break;
            
        case FAILSAFE_LOITER:
            setFlightMode(NAV_LOITER_MODE);
            break;
            
        case FAILSAFE_RTH:
            setFlightMode(NAV_RTH_MODE);
            break;
            
        case FAILSAFE_LAND:
            setFlightMode(NAV_LAND_MODE);
            break;
            
        case FAILSAFE_EMERGENCY:
            // Emergency land at current position
            emergencyLanding();
            break;
    }
    
    // Log event
    blackboxLogFailsafeEvent(action);
    telemetrySendFailsafeAlert(action);
}
```

---

## 3. Configuration Parameters

### CLI Commands (iNav Configurator)

```bash
# Differential thrust
set differential_thrust_enabled = ON
set differential_thrust_gain = 50    # 0-100%
set differential_thrust_expo = 0.3   # Exponential curve

# Loiter mode
set nav_loiter_radius = 50           # meters
set nav_loiter_speed = 1500          # cm/s
set nav_loiter_climb_rate = 200      # cm/s
set nav_loiter_direction = CW        # CW or CCW

# Geofence
set geofence_enabled = ON
set geofence_radius = 500            # meters
set geofence_altitude_min = 10       # meters
set geofence_altitude_max = 150      # meters
set geofence_action = RTH            # WARNING, LOITER, RTH, LAND

# Failsafe
set failsafe_procedure = RTH
set failsafe_delay = 10              # seconds
set failsafe_throttle = 1300         # PWM value
set failsafe_off_delay = 5           # seconds to disarm after landing
```

---

## 4. Build & Flash Process

### Prerequisites
```bash
# Install ARM toolchain
sudo apt-get install gcc-arm-none-eabi

# Clone iNav
git clone https://github.com/iNavFlight/inav.git
cd inav

# Checkout stable version
git checkout 7.1.2
```

### Apply Custom Patches
```bash
# Create feature branch
git checkout -b flying-wing-custom

# Copy custom files
cp custom/mixer_twin_engine.c src/main/flight/
cp custom/navigation_loiter.c src/main/navigation/
cp custom/navigation_geofence.c src/main/navigation/

# Edit Makefile to include custom files
```

### Build
```bash
# Set target
make TARGET=MATEKF722

# Clean build
make clean
make

# Output: obj/inav_7.1.2_MATEKF722.hex
```

### Flash
```bash
# Using DFU (USB)
dfu-util -a 0 -s 0x08000000 -D obj/inav_7.1.2_MATEKF722.hex

# Or using ST-Link
st-flash write obj/inav_7.1.2_MATEKF722.bin 0x08000000

# Or using iNav Configurator (GUI)
```

---

## 5. Testing & Validation

### Test Cases

**1. Differential Thrust Test**
```
- Ground test với props off
- Verify motor response to yaw stick
- Check differential gain scaling
- Test emergency symmetry mode
```

**2. Loiter Mode Test**
```
- Activate loiter tại vị trí cố định
- Verify circular path
- Check radius accuracy
- Test wind compensation
```

**3. Geofence Test**
```
- Configure test geofence (small radius)
- Fly to boundary
- Verify warning/action activation
- Test recovery behavior
```

**4. Failsafe Test**
```
- Simulate RX loss
- Verify phase transitions
- Test RTH activation
- Check landing sequence
```

### Debugging Tools
- **iNav Configurator**: Configuration & monitoring
- **Blackbox**: Flight data logging
- **UART Debug**: Real-time debug output
- **LED Codes**: Status indication

---

## 6. Integration với Companion Computer

### MAVLink Custom Messages

Xem `COMMUNICATION_PROTOCOL.md` cho chi tiết.

### Command Interface
```c
// Receive commands from companion
void processCompanionCommand(mavlink_message_t* msg) {
    switch (msg->msgid) {
        case MAVLINK_MSG_ID_COMMAND_LONG:
            handleCommandLong(msg);
            break;
            
        case MSG_TWIN_ENGINE_CONTROL:
            handleTwinEngineControl(msg);
            break;
            
        case MSG_COMPANION_HEALTH:
            handleCompanionHealth(msg);
            break;
    }
}
```

---

## 7. Safety Features

### Pre-Flight Checks
✅ GPS fix (minimum 6 satellites)  
✅ Battery voltage (minimum 14.0V for 4S)  
✅ Calibration status  
✅ Geofence configured  
✅ Companion computer connected  
✅ Control surface test  
✅ Motor differential test  

### In-Flight Monitoring
📊 Battery voltage & current  
📊 GPS quality  
📊 Link quality (RX, Companion, GCS)  
📊 Motor temperature  
📊 Airspeed (if sensor available)  
📊 Altitude & distance from home  

### Emergency Procedures
🚨 **Battery Critical**: Force RTH  
🚨 **GPS Lost**: Switch to stabilized mode  
🚨 **Link Lost**: Execute failsafe  
🚨 **Geofence Violation**: Loiter or RTH  
🚨 **Motor Failure**: Attempt controlled landing  

---

## Summary

✅ **Differential Thrust**: Custom mixer cho twin-engine  
✅ **Loiter Mode**: Circular patrol capability  
✅ **Geofencing**: Virtual boundaries  
✅ **Failsafe**: Multi-phase intelligent recovery  
✅ **MAVLink Integration**: Communication với companion  
✅ **Safety First**: Comprehensive checks & monitoring  

**Next**: Build firmware và test trên bench trước khi bay thử.
