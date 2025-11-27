# Flying Wing UAV - Web Server & 5G Data System

## Overview

Complete web-based ground station for receiving and displaying UAV telemetry, images, and AI detections over 5G/WiFi.

## Features

- 📡 **Real-time Telemetry**: Receive GPS, battery, speed, altitude
- 📷 **Image Upload**: High-resolution images with metadata
- 🎯 **AI Detection Alerts**: Object detection results with GPS coordinates
- 🗺️ **Live Map**: Real-time UAV position tracking
- 🎮 **Command Interface**: Send commands to UAV (ARM/DISARM/RTH/LAND)
- 📊 **WebSocket Updates**: Live dashboard with Socket.IO

## Installation

```bash
# Install dependencies
pip install flask flask-socketio flask-cors requests python-socketio

# Or use requirements
cd ground_station
pip install -r requirements_web.txt
```

## Quick Start

### 1. Start Ground Station Server

```bash
# On ground station laptop/PC
cd ground_station/src/web_server
python app.py

# Server starts on http://0.0.0.0:5000
# Dashboard: http://localhost:5000
```

### 2. Configure UAV Client

```python
# On Raspberry Pi
from communication.http_client import HTTPUploadClient

# Point to ground station IP
client = HTTPUploadClient(server_url="http://192.168.1.100:5000")
client.start()

# Queue data for upload
client.queue_telemetry({
    "latitude": 21.028511,
    "longitude": 105.804817,
    "altitude": 50.0,
    "battery": 85,
    "speed": 15.0
})
```

### 3. Open Dashboard

Open browser: `http://localhost:5000` (or ground station IP)

## API Endpoints

### POST /api/telemetry
Receive telemetry data from UAV

**Request:**
```json
{
  "latitude": 21.028511,
  "longitude": 105.804817,
  "altitude": 50.0,
  "speed": 15.0,
  "battery": 85,
  "heading": 90,
  "timestamp": "2025-11-22T10:30:00"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Telemetry received"
}
```

### POST /api/image
Upload image with metadata

**Request:** Multipart form data
- `image`: JPEG file
- `metadata`: JSON string

**Response:**
```json
{
  "status": "success",
  "message": "Image received",
  "filename": "image_20251122_103000.jpg"
}
```

### POST /api/detection
Report AI detection

**Request:**
```json
{
  "class": "person",
  "confidence": 0.92,
  "bbox": [100, 200, 150, 250],
  "gps": {
    "lat": 21.028511,
    "lon": 105.804817
  },
  "timestamp": "2025-11-22T10:30:00"
}
```

### POST /api/command
Send command to UAV (stores for polling)

**Request:**
```json
{
  "command": "RTH",
  "params": {},
  "timestamp": "2025-11-22T10:30:00"
}
```

### GET /api/status
Get server status

**Response:**
```json
{
  "status": "online",
  "timestamp": "2025-11-22T10:30:00",
  "connected_clients": 3,
  "latest_telemetry": {...},
  "recent_detections": 5
}
```

## Integration Example

Complete integration on Raspberry Pi:

```python
from communication.http_client import HTTPUploadClient
from communication.mavlink_handler import MAVLinkHandler
from ai.object_detector import ObjectDetector
from camera.camera_interface import CameraInterface
import time

# Initialize components
mavlink = MAVLinkHandler(port="/dev/ttyS0")
mavlink.connect()

camera = CameraInterface()
camera.start_camera()

detector = ObjectDetector()

# Initialize HTTP client
http_client = HTTPUploadClient(server_url="http://192.168.1.100:5000")
http_client.start()

# Main loop
while True:
    # Capture frame
    frame = camera.capture_frame()
    
    # Run AI detection
    detections = detector.detect(frame)
    
    # Get GPS from MAVLink
    gps = mavlink.last_gps
    
    # Upload telemetry
    http_client.queue_telemetry({
        "latitude": gps['lat'],
        "longitude": gps['lon'],
        "altitude": gps['alt'],
        "battery": mavlink.last_battery['remaining'],
        "speed": 15.0
    })
    
    # Upload detections
    for det in detections:
        http_client.queue_detection({
            "class": det.class_name,
            "confidence": det.confidence,
            "bbox": det.bbox,
            "gps": {"lat": gps['lat'], "lon": gps['lon']}
        })
    
    # Upload image every 10 seconds
    if int(time.time()) % 10 == 0:
        http_client.queue_image(frame, {
            "gps": {"lat": gps['lat'], "lon": gps['lon']},
            "altitude": gps['alt']
        })
    
    time.sleep(1)
```

## 5G Hotspot Setup

### Hardware
- USB 5G modem or smartphone hotspot
- Raspberry Pi with WiFi/Ethernet

### Configuration

1. **On Ground Station**:
```bash
# Check IP address
ip addr show

# Example: 192.168.1.100
```

2. **On Raspberry Pi**:
```bash
# Connect to 5G hotspot
sudo nmcli dev wifi connect "UAV_5G_Hotspot" password "your_password"

# Test connection
ping 192.168.1.100
```

3. **Update Python code**:
```python
# Use ground station IP
client = HTTPUploadClient(server_url="http://192.168.1.100:5000")
```

## Performance

- **Telemetry**: 1-2 Hz (every 0.5-1 second)
- **Images**: On-demand or periodic (every 5-10 seconds)
- **Detections**: Real-time (as detected)
- **Latency**: <100ms on good 5G connection
- **Bandwidth**: ~50 KB/s telemetry + 50-200 KB/s images

## Storage

All uploaded data stored in:
```
ground_station/src/web_server/uploads/
├── images/
│   ├── image_20251122_103000.jpg
│   └── image_20251122_103000_meta.json
├── telemetry/
│   └── telemetry_20251122_103000.json
└── detections/
    └── detection_20251122_103000.json
```

## Security

### API Key Authentication

Set API key in `app.py`:
```python
API_KEY = "your_secret_key_here"
```

Use in client:
```python
client = HTTPUploadClient(
    server_url="http://192.168.1.100:5000",
    api_key="your_secret_key_here"
)
```

## Troubleshooting

### Connection refused
- Check firewall: `sudo ufw allow 5000`
- Verify server running: `curl http://localhost:5000/api/status`
- Check network: `ping <ground_station_ip>`

### Upload failures
- Check queue sizes: `client.get_status()`
- Verify network quality
- Reduce upload frequency

### Dashboard not updating
- Check WebSocket connection in browser console
- Verify Socket.IO client loaded
- Check CORS settings

## Future Enhancements

- [ ] HTTPS/TLS encryption
- [ ] Authentication system
- [ ] Video streaming (RTSP/WebRTC)
- [ ] Mission planning interface
- [ ] Historical data visualization
- [ ] Mobile app
- [ ] Multi-UAV support
