# 🎮 3D UAV Visualization Plan

> **Kế hoạch triển khai 3D Visualization cho Flying Wing UAV**  
> Ngày tạo: 01/12/2025  
> Phiên bản: 1.0.1

---

## 📋 Tổng Quan

### Mục tiêu
Hiển thị trạng thái UAV real-time dưới dạng 3D, bao gồm:
- Attitude (Roll, Pitch, Yaw)
- Position trên bản đồ
- Telemetry data
- AI Detection overlay

### Lựa chọn Implementation

| Option | Ưu điểm | Nhược điểm | Khuyến nghị |
|--------|---------|------------|-------------|
| **A: Web-based (Three.js)** | Cross-platform, dễ deploy | Performance hạn chế | ✅ **Chọn** |
| B: Mission Planner Plugin | Tích hợp sẵn | Cần C#/.NET, phức tạp | ❌ |
| C: Standalone Desktop | Performance tốt | Cần maintain riêng | ❌ |

> **Quyết định**: Sử dụng **Web-based với Three.js** vì:
> 1. Tích hợp với Flask Web Server hiện có
> 2. Cross-platform (Windows, Mac, Linux, Mobile)
> 3. Không cần cài đặt, truy cập qua browser
> 4. Có thể embed vào Mission Planner qua WebView

---

## 🏗️ Kiến Trúc

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      WEB BROWSER                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    3D VIEWER                             │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │    │
│  │  │  Three.js   │  │  Leaflet    │  │  Chart.js   │      │    │
│  │  │  3D Model   │  │    Map      │  │  Telemetry  │      │    │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘      │    │
│  │         │                │                │              │    │
│  │         └────────────────┼────────────────┘              │    │
│  │                          │                               │    │
│  │                  ┌───────▼───────┐                       │    │
│  │                  │   WebSocket   │                       │    │
│  │                  │   Client      │                       │    │
│  │                  └───────┬───────┘                       │    │
│  └──────────────────────────┼───────────────────────────────┘    │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │ Real-time Data
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FLASK WEB SERVER                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Routes:                                                 │    │
│  │  - /api/telemetry    → GET attitude, position           │    │
│  │  - /api/targets      → GET AI detections                │    │
│  │  - /api/mission      → GET/POST waypoints               │    │
│  │  - /ws/telemetry     → WebSocket stream                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │ MAVLink
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   COMPANION COMPUTER (Pi)                        │
│                   or MAVLink Telemetry Radio                     │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
UAV (FC) ──MAVLink──► Pi/Telemetry ──WiFi──► Flask Server
                                                  │
                                                  ▼
                                            WebSocket
                                                  │
                                                  ▼
                                           Browser (3D View)
```

---

## 🔧 Technical Stack

### Frontend

| Library | Version | Mục đích |
|---------|---------|----------|
| **Three.js** | r158+ | 3D Rendering, GLTF loader |
| **Leaflet** | 1.9+ | 2D Map overlay |
| **Chart.js** | 4.x | Real-time telemetry graphs |
| **Socket.io-client** | 4.x | WebSocket communication |

### Backend (Existing)

| Component | File | Cần bổ sung |
|-----------|------|-------------|
| Flask Server | `ground_station/src/web_server/app.py` | WebSocket route |
| MAVLink Handler | `communication/mavlink_handler.py` | Attitude data |

---

## 📁 File Structure

```
ground_station/
├── src/
│   └── web_server/
│       ├── app.py                    # Flask + Socket.IO
│       ├── static/
│       │   ├── js/
│       │   │   ├── three.min.js      # Three.js library
│       │   │   ├── GLTFLoader.js     # GLTF model loader
│       │   │   ├── OrbitControls.js  # Camera controls
│       │   │   └── uav_viewer.js     # Main 3D viewer code
│       │   ├── css/
│       │   │   └── viewer.css        # Styles
│       │   └── models/
│       │       └── flying_wing.glb   # 3D model (GLTF)
│       └── templates/
│           └── 3d_viewer.html        # 3D Viewer page
```

---

## 🎨 3D Model Specifications

### Flying Wing Model

| Thuộc tính | Giá trị |
|------------|---------|
| Format | GLTF/GLB |
| Polygons | <10,000 (optimized) |
| Textures | 1024x1024 max |
| Origin | Center of mass |
| Orientation | X=forward, Y=up, Z=right |

### Model Sources

1. **Option 1**: Export từ CAD (Fusion 360, SolidWorks)
2. **Option 2**: Tạo trong Blender
3. **Option 3**: Sử dụng low-poly free model và modify

### Coordinate System

```
        Y (Up)
        │
        │    
        │   ╱ X (Forward/Nose)
        │ ╱
        └──────── Z (Right Wing)

ArduPilot to Three.js conversion:
  Three.x = ArduPilot.x (North)
  Three.y = -ArduPilot.z (Up, inverted)
  Three.z = ArduPilot.y (East)
```

---

## 💻 Implementation Details

### 1. WebSocket Server (Flask-SocketIO)

```python
# app.py additions
from flask_socketio import SocketIO, emit

socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('request_telemetry')
def handle_telemetry_request():
    # Get latest telemetry from MAVLink
    telemetry = mavlink_handler.get_telemetry()
    emit('telemetry_update', {
        'roll': telemetry.roll,      # radians
        'pitch': telemetry.pitch,    # radians
        'yaw': telemetry.yaw,        # radians
        'lat': telemetry.lat,
        'lon': telemetry.lon,
        'alt': telemetry.alt,
        'groundspeed': telemetry.groundspeed,
        'airspeed': telemetry.airspeed,
        'heading': telemetry.heading,
        'battery_voltage': telemetry.battery_voltage,
        'battery_remaining': telemetry.battery_remaining,
        'gps_fix': telemetry.gps_fix,
        'satellites': telemetry.satellites
    })

# Telemetry broadcast loop (background thread)
def telemetry_broadcast():
    while True:
        telemetry = mavlink_handler.get_telemetry()
        socketio.emit('telemetry_update', telemetry)
        socketio.sleep(0.05)  # 20 Hz update rate
```

### 2. Three.js 3D Viewer

```javascript
// uav_viewer.js
class UAVViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, 
            this.container.clientWidth / this.container.clientHeight, 
            0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        
        this.uavModel = null;
        this.socket = null;
        
        this.init();
    }
    
    init() {
        // Setup renderer
        this.renderer.setSize(this.container.clientWidth, 
                              this.container.clientHeight);
        this.renderer.setClearColor(0x87CEEB); // Sky blue
        this.container.appendChild(this.renderer.domElement);
        
        // Camera position
        this.camera.position.set(5, 3, 5);
        this.camera.lookAt(0, 0, 0);
        
        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10, 20, 10);
        this.scene.add(directionalLight);
        
        // Grid helper (ground reference)
        const gridHelper = new THREE.GridHelper(20, 20);
        this.scene.add(gridHelper);
        
        // Axes helper
        const axesHelper = new THREE.AxesHelper(3);
        this.scene.add(axesHelper);
        
        // Load UAV model
        this.loadModel();
        
        // Setup controls
        this.controls = new THREE.OrbitControls(this.camera, 
                                                 this.renderer.domElement);
        
        // Connect WebSocket
        this.connectWebSocket();
        
        // Start animation loop
        this.animate();
    }
    
    loadModel() {
        const loader = new THREE.GLTFLoader();
        loader.load('/static/models/flying_wing.glb', (gltf) => {
            this.uavModel = gltf.scene;
            this.uavModel.scale.set(0.1, 0.1, 0.1); // Adjust scale
            this.scene.add(this.uavModel);
        });
    }
    
    connectWebSocket() {
        this.socket = io();
        
        this.socket.on('telemetry_update', (data) => {
            this.updateAttitude(data.roll, data.pitch, data.yaw);
            this.updateTelemetryDisplay(data);
        });
        
        // Request telemetry at 20Hz
        setInterval(() => {
            this.socket.emit('request_telemetry');
        }, 50);
    }
    
    updateAttitude(roll, pitch, yaw) {
        if (this.uavModel) {
            // Convert ArduPilot attitude to Three.js rotation
            // ArduPilot: roll=X, pitch=Y, yaw=Z (NED frame)
            // Three.js: rotation order XYZ
            this.uavModel.rotation.x = pitch;  // Pitch around X
            this.uavModel.rotation.y = -yaw;   // Yaw around Y (inverted)
            this.uavModel.rotation.z = -roll;  // Roll around Z (inverted)
        }
    }
    
    updateTelemetryDisplay(data) {
        // Update HTML elements with telemetry data
        document.getElementById('roll-value').textContent = 
            (data.roll * 180 / Math.PI).toFixed(1) + '°';
        document.getElementById('pitch-value').textContent = 
            (data.pitch * 180 / Math.PI).toFixed(1) + '°';
        document.getElementById('heading-value').textContent = 
            data.heading.toFixed(1) + '°';
        document.getElementById('altitude-value').textContent = 
            data.alt.toFixed(1) + 'm';
        document.getElementById('speed-value').textContent = 
            data.groundspeed.toFixed(1) + 'm/s';
        document.getElementById('battery-value').textContent = 
            data.battery_remaining.toFixed(0) + '%';
    }
    
    animate() {
        requestAnimationFrame(() => this.animate());
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
}

// Initialize viewer
const viewer = new UAVViewer('viewer-container');
```

### 3. HTML Template

```html
<!-- 3d_viewer.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flying Wing UAV - 3D Viewer</title>
    <link rel="stylesheet" href="/static/css/viewer.css">
</head>
<body>
    <div class="container">
        <!-- 3D Viewer -->
        <div id="viewer-container" class="viewer-panel"></div>
        
        <!-- Telemetry Panel -->
        <div class="telemetry-panel">
            <h2>Telemetry</h2>
            <div class="telemetry-grid">
                <div class="telemetry-item">
                    <span class="label">Roll</span>
                    <span id="roll-value" class="value">0.0°</span>
                </div>
                <div class="telemetry-item">
                    <span class="label">Pitch</span>
                    <span id="pitch-value" class="value">0.0°</span>
                </div>
                <div class="telemetry-item">
                    <span class="label">Heading</span>
                    <span id="heading-value" class="value">0.0°</span>
                </div>
                <div class="telemetry-item">
                    <span class="label">Altitude</span>
                    <span id="altitude-value" class="value">0.0m</span>
                </div>
                <div class="telemetry-item">
                    <span class="label">Speed</span>
                    <span id="speed-value" class="value">0.0m/s</span>
                </div>
                <div class="telemetry-item">
                    <span class="label">Battery</span>
                    <span id="battery-value" class="value">100%</span>
                </div>
            </div>
            
            <!-- Attitude Indicator -->
            <div class="attitude-indicator">
                <canvas id="attitude-canvas" width="200" height="200"></canvas>
            </div>
        </div>
    </div>
    
    <!-- Scripts -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.6.0/socket.io.min.js"></script>
    <script src="/static/js/three.min.js"></script>
    <script src="/static/js/GLTFLoader.js"></script>
    <script src="/static/js/OrbitControls.js"></script>
    <script src="/static/js/uav_viewer.js"></script>
</body>
</html>
```

---

## 📅 Implementation Timeline

### Phase 1: Basic 3D Viewer (1-2 tuần)
- [ ] Setup Flask-SocketIO
- [ ] Create/Import Flying Wing 3D model
- [ ] Basic Three.js viewer với rotation
- [ ] WebSocket telemetry stream

### Phase 2: Enhanced Features (1-2 tuần)
- [ ] Attitude indicator (artificial horizon)
- [ ] Compass/heading display
- [ ] Altitude tape
- [ ] Speed tape

### Phase 3: Map Integration (1 tuần)
- [ ] Leaflet map với UAV position marker
- [ ] Flight path trail
- [ ] Waypoint display
- [ ] Geofence visualization

### Phase 4: AI Overlay (1 tuần)
- [ ] Detection bounding boxes overlay
- [ ] Target markers on map
- [ ] Detection history list

---

## 🔗 Mission Planner Integration

### Option 1: Web Browser Widget (Đơn giản)

Mission Planner hỗ trợ mở custom web page:
1. Mở Mission Planner
2. Vào Actions → Custom
3. Mở URL: `http://localhost:5000/3d-viewer`

### Option 2: MAVLink Proxy (Nâng cao)

Chạy Flask server độc lập, kết nối MAVLink song song:

```
                    ┌─────────────────┐
                    │ Mission Planner │
                    │    (Primary)    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
UAV ───Telemetry───►│  MAVLink Proxy  │
                    │   (mavproxy)    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Flask Server   │
                    │   (3D Viewer)   │
                    └─────────────────┘
```

Command:
```bash
mavproxy.py --master=/dev/ttyUSB0 --out=udp:127.0.0.1:14550 --out=udp:127.0.0.1:14551
```
- Port 14550: Mission Planner
- Port 14551: Flask Server

---

## 📊 Performance Considerations

### Target Specifications

| Metric | Target | Notes |
|--------|--------|-------|
| Update Rate | 20 Hz | WebSocket telemetry |
| Frame Rate | 60 FPS | Three.js rendering |
| Latency | <100ms | End-to-end |
| Memory | <200MB | Browser tab |

### Optimization Tips

1. **Model LOD**: Sử dụng low-poly model (<10k polygons)
2. **Texture Compression**: Sử dụng compressed textures (KTX2)
3. **Throttle Updates**: Chỉ update khi có thay đổi đáng kể
4. **Dispose Resources**: Clean up Three.js objects khi không cần

---

## ✅ Checklist

### Prerequisites
- [ ] Flying Wing 3D model (GLTF format)
- [ ] Flask-SocketIO installed
- [ ] Three.js và dependencies

### Development
- [ ] WebSocket route trong app.py
- [ ] 3D Viewer page template
- [ ] UAV model loading
- [ ] Attitude update logic
- [ ] Telemetry panel

### Testing
- [ ] Rotation accuracy test
- [ ] Latency measurement
- [ ] Cross-browser testing
- [ ] Mobile responsiveness

### Deployment
- [ ] Production config
- [ ] HTTPS setup (optional)
- [ ] Documentation update

---

## 📚 References

- [Three.js Documentation](https://threejs.org/docs/)
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/)
- [ArduPilot MAVLink](https://ardupilot.org/dev/docs/mavlink-basics.html)
- [GLTF Specification](https://www.khronos.org/gltf/)

---

*Tài liệu này được tạo bởi: Trương Công Định & Đặng Duy Long*  
*Cập nhật: 01/12/2025*
