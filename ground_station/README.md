# Ground Control Station (GCS)

Phần mềm điều khiển mặt đất cho Flying Wing UAV.

---

## ⚠️ CHIẾN LƯỢC (Cập nhật 01/12/2025)

**KHÔNG viết lại Mission Planner**. Dùng công cụ có sẵn:

| Công cụ | Mục đích |
|---------|----------|
| **Mission Planner** | Giám sát bay đầy đủ: Bản đồ, 3D View, Telemetry, Parameters |
| **Flask Web Server** | Video AI Stream + Target Detection Log (custom) |

---

## Features

### Mission Planner (Dùng có sẵn)
✅ **Real-time Telemetry**: Altitude, speed, battery, GPS  
✅ **3D View**: Hiển thị tư thế máy bay  
✅ **Map View**: Vị trí UAV, waypoints, geofence  
✅ **Mission Planning**: Tạo waypoints, missions  
✅ **Flight Modes**: Auto, Loiter, RTH, FBWA  
✅ **Parameters**: Cài đặt ArduPilot đầy đủ  

### Flask Web Server (Custom)
✅ **AI Video Stream**: Video với AI annotation  
✅ **Target Detection Log**: Lịch sử phát hiện mục tiêu  
✅ **Web Dashboard**: Giám sát từ xa qua browser  
✅ **REST API**: Integration với hệ thống khác  

---

## Architecture

```
ground_station/
├── src/
│   ├── web_server/           # Flask Web Server
│   │   ├── app.py            # REST API (387 lines)
│   │   └── templates/
│   │       └── dashboard.html # Web dashboard
│   ├── communication/        # MAVLink & network
│   │   ├── mavlink_client.py
│   │   └── video_receiver.py
│   └── main.py               # Entry point
├── config/                   # Configuration
├── ml_server.py              # ML Training Server
├── requirements.txt          # Web dependencies
└── README.md
```

---

## Installation

### Requirements
- Python 3.8+
- Flask
- pymavlink
- opencv-python

### Setup
```bash
cd ground_station
pip install -r requirements.txt
python src/web_server/app.py
```

---

## Usage

### Connect to UAV
1. Nhập IP companion computer (hoặc 4G module)
2. Port: 14550 (MAVLink), 8554 (RTSP video)
3. Click "Connect"

### Monitor Flight
- **Telemetry Panel**: Battery, GPS, altitude, speed
- **Video Feed**: Live camera view
- **Map**: UAV position và waypoints
- **AI Detections**: Object detection results

### Send Commands
- **Takeoff**: Auto takeoff to altitude
- **Land**: Auto landing
- **RTH**: Return to home
- **Arm/Disarm**: Motor control
- **Emergency Stop**: Cut motors (use carefully!)

### Mission Planning
1. Click "Mission Planner"
2. Add waypoints on map
3. Set altitude, speed
4. Upload to UAV
5. Start mission

---

## Configuration

`config/gcs_config.yaml`:
```yaml
connection:
  default_ip: "192.168.1.100"
  mavlink_port: 14550
  video_port: 8554
  connection_timeout: 5

display:
  update_rate: 10  # Hz
  map_center: [21.028511, 105.804817]  # Hanoi
  map_zoom: 15
  
telemetry:
  log_enabled: true
  log_path: "logs/telemetry"
  
video:
  codec: "h264"
  buffer_size: 2  # frames
  
alerts:
  battery_warning: 30  # percent
  battery_critical: 20
  distance_warning: 500  # meters
```

---

## Screenshots

[Sẽ thêm sau khi implement UI]

---

## Development

### Run from source
```bash
python src/main.py
```

### Build executable
```bash
pip install pyinstaller
pyinstaller --onefile --windowed src/main.py
```

### Testing
```bash
pytest tests/
```

---

## Safety Notes

⚠️ Luôn kiểm tra battery trước khi takeoff  
⚠️ Test emergency commands trước khi bay thật  
⚠️ Đảm bảo kết nối ổn định (check signal strength)  
⚠️ Có backup plan nếu mất kết nối  
⚠️ Không bay gần người hoặc tài sản  

---

## Next Steps

1. Implement full GUI
2. Add mission planning
3. Test với real hardware
4. Add flight data analysis tools
