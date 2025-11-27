# Geofencing System Documentation

## Overview

Hệ thống geofencing nâng cao cho Flying Wing UAV với khả năng:
- ✅ **Polygon phức tạp**: Hình ngôi sao, đa giác bất kỳ (không chỉ hình tròn/chữ nhật)
- ✅ **Real-time monitoring**: Đọc GPS liên tục từ iNav qua MAVLink
- ✅ **Automatic response**: Tự động gửi lệnh RTH/LOITER/LAND khi vi phạm
- ✅ **3D geofencing**: Giới hạn cả vùng ngang (lat/lon) và cao độ
- ✅ **Intelligent return**: Tính toán điểm an toàn gần nhất để quay về
- ✅ **Visual editing**: Vẽ geofence trên bản đồ tương tác

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Companion Computer (RPi)                  │
│                                                              │
│  ┌──────────────┐      ┌──────────────┐     ┌────────────┐ │
│  │ GPS Monitor  │─────>│ Geofencing   │────>│  MAVLink   │ │
│  │              │      │ System       │     │  Handler   │ │
│  └──────────────┘      └──────────────┘     └────────────┘ │
│         │                     │                     │        │
│         │                     v                     v        │
│         │              ┌─────────────┐       ┌────────────┐ │
│         └─────────────>│  Position   │       │  Command   │ │
│                        │  Checker    │       │  Sender    │ │
│                        └─────────────┘       └────────────┘ │
└───────────────────────────────┬──────────────────┬──────────┘
                                │                  │
                         Check Position    Send RTH/LOITER/LAND
                                │                  │
                                v                  v
                        ┌───────────────────────────────┐
                        │   iNav Flight Controller      │
                        │   (LANRC F4 V3S Plus)         │
                        └───────────────────────────────┘
```

## Installation

```bash
# Install dependencies
pip install shapely folium loguru pymavlink

# Or use requirements
cd companion_computer
pip install -r requirements.txt
```

## Quick Start

### 1. Define Geofences

```python
from safety.geofencing import GeoPoint, GeofencingSystem, GeofenceTemplates

# Set home position (launch site)
home = GeoPoint(21.028511, 105.804817)  # Hanoi example

# Create geofencing system (max 1km from home)
geo_system = GeofencingSystem(home, max_distance=1000.0)

# Add star-shaped military base exclusion zone
military_base = GeoPoint(21.030, 105.806)
star_fence = GeofenceTemplates.create_star_exclusion(
    military_base, 
    radius=150.0,  # 150m radius
    name="Military Base"
)
geo_system.add_fence(star_fence)

# Add circular restricted area
restricted = GeoPoint(21.027, 105.803)
circle_fence = GeofenceTemplates.create_circular_exclusion(
    restricted,
    radius=80.0,
    name="Restricted Area"
)
geo_system.add_fence(circle_fence)

# Save configuration
geo_system.save_to_file("geofence_config.json")
```

### 2. Visualize on Map

```python
from tools.geofence_visualizer import GeofenceMapVisualizer

# Create visualizer
visualizer = GeofenceMapVisualizer(geo_system)

# Open in browser
visualizer.show_map()
```

### 3. Run Geofence Monitoring

```python
from examples.geofence_integration import GeofenceIntegration

# Initialize with MAVLink port
integration = GeofenceIntegration(mavlink_port="/dev/ttyS0")

# Run (will auto-setup after GPS lock)
integration.run()
```

## Usage Scenarios

### Scenario 1: Military Base Protection

**Problem**: Cần tạo vùng cấm bay hình ngôi sao xung quanh căn cứ quân sự

```python
# Create star-shaped exclusion zone
military = GeoPoint(21.030, 105.806)
star = GeofenceTemplates.create_star_exclusion(
    center=military,
    radius=150.0,
    name="Military Base"
)
geo_system.add_fence(star)
```

**Behavior**: 
- UAV bay vào vùng ngôi sao → Python phát hiện vi phạm
- Tính toán điểm an toàn gần nhất (20m ngoài biên)
- Gửi waypoint guided về điểm an toàn
- Fallback: RTH nếu không tính được

### Scenario 2: Airport No-Fly Zone

```python
# Rectangle around airport
sw = GeoPoint(21.029, 105.808)
ne = GeoPoint(21.031, 105.810)
airport = GeofenceTemplates.create_rectangle_exclusion(
    southwest=sw,
    northeast=ne,
    name="Airport Zone"
)
geo_system.add_fence(airport)
```

### Scenario 3: 3D Geofencing (Altitude Limits)

```python
from safety.geofencing import GeoFence

# Custom fence with altitude limits
points = [
    GeoPoint(21.028, 105.804),
    GeoPoint(21.029, 105.805),
    GeoPoint(21.030, 105.804),
]

fence = GeoFence(
    name="Low Altitude Zone",
    points=points,
    is_exclusion=True,
    altitude_min=0,
    altitude_max=30  # Only forbidden below 30m
)
geo_system.add_fence(fence)
```

### Scenario 4: Complex Custom Polygon

```python
# Define custom polygon (e.g., irregular border)
custom_points = [
    GeoPoint(21.028, 105.804),
    GeoPoint(21.029, 105.805),
    GeoPoint(21.030, 105.806),
    GeoPoint(21.031, 105.805),
    GeoPoint(21.030, 105.803),
    GeoPoint(21.028, 105.803),
]

custom_fence = GeoFence(
    name="Custom Border",
    points=custom_points,
    is_exclusion=True
)
geo_system.add_fence(custom_fence)
```

## Fence Actions

Khi vi phạm geofence, hệ thống có thể thực hiện các hành động:

| Action | Description | When to Use |
|--------|-------------|-------------|
| `WARN` | Chỉ log cảnh báo | Testing, non-critical zones |
| `RTH` | Return to Home | Critical violations, far from safe zone |
| `LOITER` | Loiter tại chỗ | Need operator intervention |
| `LAND` | Emergency land | Battery low + fence breach |
| `GUIDED_RETURN` | Tự động về điểm an toàn gần nhất | **Recommended** - intelligent response |

Default action: `GUIDED_RETURN` (tự động tính toán và bay về điểm an toàn)

## Configuration File Format

File: `geofence_config.json`

```json
{
  "home": {
    "lat": 21.028511,
    "lon": 105.804817
  },
  "max_distance": 1000.0,
  "fences": [
    {
      "name": "Military Base",
      "points": [
        {"lat": 21.030, "lon": 105.806},
        {"lat": 21.031, "lon": 105.807},
        ...
      ],
      "is_exclusion": true,
      "altitude_min": 0,
      "altitude_max": 1000
    }
  ]
}
```

## Integration with iNav

### iNav Configuration

```
# In iNav Configurator CLI

# Enable MAVLink on UART3
serial 2 1024 115200 57600 0 115200

# Set GPS failsafe to RTH (backup for Python system)
set failsafe_procedure = RTH

# Enable geofence in iNav (basic circular, Python will handle complex)
set nav_fw_control_smoothness = 2
set nav_max_altitude = 150
```

### Python Integration

```python
# In main.py or custom script
from communication.mavlink_handler import MAVLinkHandler
from safety.geofencing import GeofencingSystem, GeofenceMonitor

# Setup MAVLink
mavlink = MAVLinkHandler(port="/dev/ttyS0", baudrate=57600)
mavlink.connect()

# Setup geofencing (home will be set after GPS lock)
geo_system = GeofencingSystem(home=GeoPoint(0, 0), max_distance=1000)
geo_system.load_from_file("geofence_config.json")

# Create monitor
monitor = GeofenceMonitor(geo_system, mavlink)

# Register GPS callback
def handle_gps(msg):
    lat = msg.lat / 1e7
    lon = msg.lon / 1e7
    alt = msg.alt / 1000.0
    
    monitor.update_position(lat, lon, alt)

mavlink.register_callback('GPS_RAW_INT', handle_gps)

# Start monitoring
monitor.start_monitoring()
```

## Testing

### Test 1: Basic Fence Check

```bash
python companion_computer/src/safety/geofencing.py
```

### Test 2: Visualize Geofences

```bash
python companion_computer/tools/geofence_visualizer.py
```

### Test 3: Full Integration (requires hardware)

```bash
python companion_computer/examples/geofence_integration.py
```

### Test 4: Simulated GPS (no hardware)

```python
from safety.geofencing import GeofencingSystem, GeoPoint

# Create system
home = GeoPoint(21.028511, 105.804817)
geo_system = GeofencingSystem(home, max_distance=1000)

# Add test fence
from safety.geofencing import GeofenceTemplates
fence = GeofenceTemplates.create_star_exclusion(
    GeoPoint(21.030, 105.806),
    radius=100,
    name="Test Zone"
)
geo_system.add_fence(fence)

# Test positions
test_positions = [
    (GeoPoint(21.029, 105.805), 50.0, "Safe"),
    (GeoPoint(21.030, 105.806), 50.0, "Inside star - BREACH!"),
]

for pos, alt, desc in test_positions:
    is_safe, msg, action = geo_system.check_position(pos, alt)
    print(f"{desc}: {'SAFE' if is_safe else 'BREACH'} - {msg}")
```

## Performance

- **GPS Check Frequency**: 2 Hz (every 0.5s)
- **Polygon Check Algorithm**: 
  - With Shapely: O(log n) spatial index
  - Without Shapely: O(n) ray casting fallback
- **Latency**: <10ms per check on Raspberry Pi 3B+
- **Memory**: ~5MB for 10 complex polygons

## Troubleshooting

### Problem: "shapely not installed"

```bash
pip install shapely
```

### Problem: Geofence not triggering

1. Check GPS fix: `fix_type >= 3`
2. Check monitoring status: `monitor.is_monitoring == True`
3. Check fence loading: `len(geo_system.fences) > 0`
4. Test position manually:
   ```python
   is_safe, msg, action = geo_system.check_position(current_pos, altitude)
   print(f"Safe: {is_safe}, Message: {msg}")
   ```

### Problem: False positives at polygon edges

- Increase `warning_distance` buffer (default 30m)
- Use smoother polygon with more points
- Check GPS accuracy (HDOP < 2.0)

### Problem: MAVLink command not working

1. Check serial connection: `ls -l /dev/ttyS0`
2. Check baudrate match: iNav=57600, Python=57600
3. Test MAVLink manually:
   ```python
   mavlink.send_command(mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH)
   ```

## Safety Considerations

⚠️ **IMPORTANT SAFETY NOTES**

1. **Always have manual override**: Geofencing is NOT foolproof
2. **Test without props first**: Bench test all fence violations
3. **Set iNav failsafe**: Configure iNav RTH as backup
4. **Monitor battery**: Low battery + fence breach = dangerous
5. **GPS accuracy**: Require min 8 satellites, HDOP < 2.0
6. **Weather limits**: High wind can cause GPS drift
7. **Legal compliance**: Check local drone regulations
8. **Visual line of sight**: Never rely 100% on automation

## Advanced Features

### Custom Fence Actions

```python
class CustomGeofenceMonitor(GeofenceMonitor):
    def _handle_breach(self, action):
        # Custom logic
        if self.current_altitude > 100:
            # High altitude - immediate RTH
            self.mavlink.return_to_home()
        else:
            # Low altitude - loiter and wait
            self.mavlink.set_mode("LOITER")
            # Alert operator via radio
            self.send_alert_to_gcs()
```

### Multiple Geofence Priorities

```python
# Priority 1: Critical no-fly (immediate RTH)
critical_fence.priority = 1
critical_fence.action = FenceAction.RTH

# Priority 2: Warning zone (loiter)
warning_fence.priority = 2
warning_fence.action = FenceAction.LOITER
```

### Dynamic Geofence Updates

```python
# Update fence during flight (e.g., new restricted area)
new_fence = create_temporary_nfz(lat, lon, radius=100)
geo_system.add_fence(new_fence)

# Remove after timeout
time.sleep(600)  # 10 minutes
geo_system.remove_fence(new_fence.name)
```

## API Reference

See source code documentation:
- `safety/geofencing.py` - Core geofencing classes
- `examples/geofence_integration.py` - Integration example
- `tools/geofence_visualizer.py` - Map visualization

## License

Part of Flying Wing UAV project. Use at your own risk.
