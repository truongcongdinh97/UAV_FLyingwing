# Ground Control Station (GCS)

Phần mềm điều khiển mặt đất cho Flying Wing UAV.

---

## Features

✅ **Real-time Telemetry**: Hiển thị altitude, speed, battery, GPS  
✅ **Video Streaming**: RTSP stream từ companion computer  
✅ **Map View**: Hiển thị vị trí UAV trên bản đồ  
✅ **Mission Planning**: Tạo waypoints, geofence  
✅ **Flight Modes**: Manual control, Auto, Loiter, RTH  
✅ **Emergency Commands**: RTH, Land, Disarm  
✅ **Data Logging**: Ghi lại telemetry và events  
✅ **AI Detections**: Hiển thị kết quả object detection  

---

## Architecture

```
ground_station/
├── src/
│   ├── ui/               # GUI components (PyQt5)
│   │   ├── main_window.py
│   │   ├── telemetry_panel.py
│   │   ├── video_widget.py
│   │   ├── map_widget.py
│   │   └── control_panel.py
│   ├── communication/    # MAVLink & network
│   │   ├── mavlink_client.py
│   │   ├── video_receiver.py
│   │   └── telemetry_receiver.py
│   ├── data/             # Data management
│   │   ├── telemetry_store.py
│   │   └── mission_planner.py
│   ├── utils/            # Utilities
│   │   ├── logger.py
│   │   └── config.py
│   └── main.py           # Entry point
├── config/
│   └── gcs_config.yaml
├── resources/            # Icons, maps, etc.
├── requirements.txt
└── README.md
```

---

## Installation

### Requirements
- Python 3.8+
- PyQt5
- pymavlink
- opencv-python
- folium (maps)

### Setup
```bash
cd ground_station
pip install -r requirements.txt
python src/main.py
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
