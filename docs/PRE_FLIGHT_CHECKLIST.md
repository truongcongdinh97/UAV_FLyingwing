# Pre-Flight Checklist

## Flying Wing UAV - Twin Engine Configuration

**Date**: __________  
**Pilot**: __________  
**Location**: __________  
**Weather**: __________ (Wind: ____ km/h, Temp: ____°C)

---

## 🔋 Battery & Power (CRITICAL)

- [ ] **Battery Voltage Check**
  - [ ] Main battery: ≥ 16.4V (4S fully charged)
  - [ ] Raspberry Pi power: ≥ 5V/2A
  - [ ] FC power indicator: Green LED on
  
- [ ] **Battery Balance Check**
  - [ ] All cells within 0.05V difference
  - [ ] No swollen/damaged cells
  
- [ ] **Capacity Check**
  - [ ] Main battery: 10400mAh (full charge)
  - [ ] Expected flight time: 25-30 minutes
  - [ ] Reserve: 20% minimum for RTH

- [ ] **Connections Secure**
  - [ ] XT60 connectors locked
  - [ ] No exposed wires
  - [ ] Anti-spark connector if used

---

## ⚙️ Flight Controller Setup

- [ ] **Power On & Status**
  - [ ] FC boots successfully (LED pattern correct)
  - [ ] No continuous beeping (indicates error)
  - [ ] iNav Configurator connects via USB
  
- [ ] **GPS Lock**
  - [ ] Minimum 8 satellites
  - [ ] HDOP < 2.0
  - [ ] 3D Fix achieved
  - [ ] Home position set automatically
  
- [ ] **Sensors Calibration**
  - [ ] Accelerometer calibrated (within 7 days)
  - [ ] Magnetometer calibrated (within 30 days)
  - [ ] Barometer reading reasonable altitude
  
- [ ] **Failsafe Configuration**
  - [ ] Failsafe mode: RTH
  - [ ] Failsafe delay: 10 seconds
  - [ ] RTH altitude: 50m
  - [ ] Test failsafe by turning off TX

---

## 🎮 Radio Control

- [ ] **Transmitter Check**
  - [ ] TX battery: ≥ 50%
  - [ ] Model selected: Flying Wing Twin
  - [ ] All switches in default position
  
- [ ] **Receiver Binding**
  - [ ] RX bound to TX (green LED solid)
  - [ ] Signal strength: > 90%
  - [ ] No interference detected
  
- [ ] **Control Surface Test**
  - [ ] Pitch stick up → Both elevons up
  - [ ] Pitch stick down → Both elevons down
  - [ ] Roll stick right → Right elevon down, left up
  - [ ] Roll stick left → Left elevon up, right down
  - [ ] All movements smooth, no jitter
  
- [ ] **Motor Test (PROPS OFF!)**
  - [ ] Arm switch → Motors spin up
  - [ ] Throttle response linear
  - [ ] Left motor: ____ RPM (approx)
  - [ ] Right motor: ____ RPM (approx)
  - [ ] Yaw stick right → Right motor faster
  - [ ] Yaw stick left → Left motor faster
  - [ ] Emergency disarm works

---

## 🎥 Companion Computer (Raspberry Pi)

- [ ] **Power & Boot**
  - [ ] Pi powered via separate 5V regulator
  - [ ] Boot successful (LED activity stops after ~30s)
  - [ ] SSH accessible: `ssh pi@uav-companion.local`
  
- [ ] **Camera Check**
  - [ ] Camera detected: `vcgencmd get_camera`
  - [ ] Test image capture: `libcamera-jpeg -o test.jpg`
  - [ ] RTSP stream running: `rtsp://<IP>:8554/video`
  
- [ ] **MAVLink Communication**
  - [ ] UART connection to FC: `/dev/serial0`
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

## 📡 Ground Control Station

- [ ] **Connection Established**
  - [ ] GCS connected to Pi via WiFi/4G
  - [ ] Telemetry data received
  - [ ] Map showing UAV position
  
- [ ] **Video Stream**
  - [ ] Video feed visible in GCS
  - [ ] FPS: ≥ 15 fps
  - [ ] Latency: < 500ms
  
- [ ] **Commands Working**
  - [ ] Test ARM/DISARM
  - [ ] Test mode switches
  - [ ] Test emergency RTH
  - [ ] Test waypoint upload

---

## 🛠️ Physical Inspection

- [ ] **Airframe Structure**
  - [ ] Wings secured to fuselage
  - [ ] No cracks or damage
  - [ ] Control linkages tight
  - [ ] Control horns secure
  
- [ ] **Motors & Propellers**
  - [ ] Props: 10x7 or 11x7, correct direction
  - [ ] Props balanced (no vibration)
  - [ ] Motor mounting screws tight
  - [ ] Motor bearings smooth (no grinding)
  - [ ] ESC wires secure, no shorts
  
- [ ] **Control Surfaces**
  - [ ] Elevons move freely, no binding
  - [ ] Servo horns secure
  - [ ] Linkages not bent
  - [ ] Full range of motion (±30°)
  
- [ ] **Center of Gravity**
  - [ ] CG at 25-30% MAC (test with finger balance)
  - [ ] Battery position adjusted if needed
  - [ ] No nose/tail heavy
  
- [ ] **Weight Check**
  - [ ] Total weight: ~3.5-4.0 kg (with payload)
  - [ ] Within design limits

---

## 🌐 Network & Connectivity

- [ ] **WiFi/4G Module**
  - [ ] Module powered on
  - [ ] Signal strength: > -70 dBm
  - [ ] Ping test to GCS: < 100ms
  
- [ ] **Geofence Configured**
  - [ ] Radius: 500m from home
  - [ ] Max altitude: 150m
  - [ ] Action on breach: RTH
  - [ ] Enabled in FC settings

---

## 🎯 Mission Planning (If Autonomous)

- [ ] **Waypoints Uploaded**
  - [ ] Minimum 3 waypoints
  - [ ] Altitude: 50-100m
  - [ ] Speed: 15 m/s
  - [ ] All waypoints within geofence
  
- [ ] **Loiter Points (Optional)**
  - [ ] Loiter radius: 50m
  - [ ] Loiter altitude: 50m
  - [ ] Loiter time: 60s
  
- [ ] **Return Home Check**
  - [ ] RTH altitude set: 50m
  - [ ] RTH action: Auto-land at home
  - [ ] Emergency landing zone clear

---

## 🚁 Launch Preparation

- [ ] **Launch Area**
  - [ ] 50m clear radius
  - [ ] No obstacles in flight path
  - [ ] Wind direction noted
  - [ ] Spectators clear
  
- [ ] **Pilot Ready**
  - [ ] TX on, model armed
  - [ ] Observer assigned (if available)
  - [ ] Emergency procedures reviewed
  - [ ] First aid kit available
  
- [ ] **Final Checks**
  - [ ] All hatches closed and secured
  - [ ] Antennas secure and oriented
  - [ ] Camera lens clean
  - [ ] GPS antenna unobstructed

---

## ✈️ Launch Procedure

1. **Arm Sequence**
   - [ ] Announce "Arming"
   - [ ] Arm via switch
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

**Do NOT fly if:**
- ❌ Battery voltage < 16.0V
- ❌ GPS satellites < 6
- ❌ Wind speed > 20 km/h (for first flight)
- ❌ Rain or wet conditions
- ❌ Any control surface binding
- ❌ Motor vibration or unusual noise
- ❌ FC error codes
- ❌ Communication link unstable
- ❌ Any doubt about safety

---

## 📝 Post-Flight Checklist

- [ ] **Landing Sequence**
  - [ ] Approach into wind
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
  - [ ] Recharge batteries
  - [ ] Store in dry location

---

## 📞 Emergency Contacts

**Pilot**: __________  
**Observer**: __________  
**Emergency**: 115 (Vietnam)  
**Local Authority**: __________

---

**Checklist Version**: 1.0  
**Last Updated**: 2025-11-22

**Signature**: __________ **Date**: __________
