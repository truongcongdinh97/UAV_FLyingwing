"""
Flask Web Server - Ground Station 5G Data Receiver
Receive telemetry, images, and detections from UAV
Provide web dashboard for monitoring and control
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

try:
    from flask import Flask, request, jsonify, render_template, send_from_directory
    from flask_socketio import SocketIO, emit
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Warning: Flask not installed. Install: pip install flask flask-socketio flask-cors")

from loguru import logger
import cv2
import numpy as np


# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'flying-wing-uav-secret-2025'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Enable CORS
if FLASK_AVAILABLE:
    CORS(app)
    socketio = SocketIO(app, cors_allowed_origins="*")

# Storage directories
UPLOAD_FOLDER = Path("uploads")
IMAGE_FOLDER = UPLOAD_FOLDER / "images"
TELEMETRY_FOLDER = UPLOAD_FOLDER / "telemetry"
DETECTION_FOLDER = UPLOAD_FOLDER / "detections"

# Create directories
for folder in [IMAGE_FOLDER, TELEMETRY_FOLDER, DETECTION_FOLDER]:
    folder.mkdir(parents=True, exist_ok=True)

# In-memory storage for latest data
latest_telemetry = {}
latest_detections = []
latest_target = None  # Lưu vị trí mục tiêu mới nhất
connected_clients = set()

# API key for authentication (optional)
API_KEY = "flyingwing2025"


def verify_api_key():
    """Verify API key from request header"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return True  # Allow without auth for now
    
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        return token == API_KEY
    
    return False


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get server status"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'connected_clients': len(connected_clients),
        'latest_telemetry': latest_telemetry,
        'recent_detections': len(latest_detections)
    })


@app.route('/api/telemetry', methods=['POST'])
def receive_telemetry():
    """Receive telemetry data from UAV"""
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Store latest telemetry
        global latest_telemetry
        latest_telemetry = data
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = TELEMETRY_FOLDER / f"telemetry_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Broadcast to connected clients via WebSocket
        socketio.emit('telemetry_update', data, broadcast=True)
        
        logger.info(f"Received telemetry: lat={data.get('latitude')}, lon={data.get('longitude')}")
        
        return jsonify({
            'status': 'success',
            'message': 'Telemetry received'
        })
    
    except Exception as e:
        logger.error(f"Error receiving telemetry: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/image', methods=['POST'])
def receive_image():
    """Receive image from UAV"""
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get image file
        if 'image' not in request.files:
            return jsonify({'error': 'No image file'}), 400
        
        image_file = request.files['image']
        
        # Get metadata
        metadata_str = request.form.get('metadata', '{}')
        metadata = json.loads(metadata_str)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"image_{timestamp}.jpg"
        filepath = IMAGE_FOLDER / filename
        
        # Save image
        image_file.save(str(filepath))
        
        # Save metadata
        metadata_file = IMAGE_FOLDER / f"image_{timestamp}_meta.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Broadcast to clients
        socketio.emit('new_image', {
            'filename': filename,
            'metadata': metadata,
            'url': f'/api/images/{filename}'
        }, broadcast=True)
        
        logger.info(f"Received image: {filename}")
        
        return jsonify({
            'status': 'success',
            'message': 'Image received',
            'filename': filename
        })
    
    except Exception as e:
        logger.error(f"Error receiving image: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/detection', methods=['POST'])
def receive_detection():
    """Receive AI detection from UAV"""
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Store detection
        global latest_detections
        latest_detections.append(data)
        
        # Keep only last 100 detections
        if len(latest_detections) > 100:
            latest_detections = latest_detections[-100:]
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = DETECTION_FOLDER / f"detection_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Broadcast to clients
        socketio.emit('new_detection', data, broadcast=True)
        
        logger.info(f"Received detection: {data.get('class')} @ confidence={data.get('confidence')}")
        
        return jsonify({
            'status': 'success',
            'message': 'Detection received'
        })
    
    except Exception as e:
        logger.error(f"Error receiving detection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/command', methods=['POST'])
def send_command():
    """Send command to UAV (not implemented - would require bidirectional connection)"""
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        command = data.get('command')
        params = data.get('params', {})
        
        logger.info(f"Command received: {command} with params {params}")
        
        # In real implementation, this would:
        # 1. Store command in queue
        # 2. Send to UAV via persistent connection (WebSocket/MQTT)
        # 3. Wait for acknowledgment
        
        return jsonify({
            'status': 'success',
            'message': 'Command queued',
            'command': command
        })
    
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/images/<filename>')
def serve_image(filename):
    """Serve uploaded images"""
    return send_from_directory(IMAGE_FOLDER, filename)


@app.route('/api/telemetry/history', methods=['GET'])
def get_telemetry_history():
    """Get telemetry history"""
    try:
        # Get limit parameter
        limit = int(request.args.get('limit', 100))
        
        # Read recent telemetry files
        telemetry_files = sorted(TELEMETRY_FOLDER.glob('telemetry_*.json'), reverse=True)
        
        history = []
        for file in telemetry_files[:limit]:
            with open(file, 'r') as f:
                history.append(json.load(f))
        
        return jsonify({
            'count': len(history),
            'data': history
        })
    
    except Exception as e:
        logger.error(f"Error getting telemetry history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/detections/history', methods=['GET'])
def get_detection_history():
    """Get detection history"""
    try:
        limit = int(request.args.get('limit', 100))
        
        return jsonify({
            'count': len(latest_detections),
            'data': latest_detections[-limit:]
        })
    
    except Exception as e:
        logger.error(f"Error getting detection history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/target', methods=['POST'])
def receive_target():
    """
    Nhận dữ liệu vị trí mục tiêu từ máy tính đồng hành (Companion Computer)
    Pipeline chuẩn: Sau khi UAV tính toán vị trí mục tiêu, gửi POST /api/target lên server.
    - Lưu file target
    - Broadcast WebSocket cho dashboard
    - Cập nhật biến latest_target
    """
    if not verify_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        # Lưu vị trí mục tiêu mới nhất
        global latest_target
        latest_target = data
        # Lưu file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        target_folder = UPLOAD_FOLDER / "targets"
        target_folder.mkdir(parents=True, exist_ok=True)
        filename = target_folder / f"target_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        # Broadcast WebSocket cho dashboard
        socketio.emit('target_update', data, broadcast=True)
        logger.info(f"Received target geolocation: lat={data.get('lat')}, lon={data.get('lon')}")
        return jsonify({
            'status': 'success',
            'message': 'Target geolocation received'
        })
    except Exception as e:
        logger.error(f"Error receiving target geolocation: {e}")
        return jsonify({'error': str(e)}), 500


# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    connected_clients.add(request.sid)
    logger.info(f"Client connected: {request.sid} (total: {len(connected_clients)})")
    
    # Send latest data to new client
    if latest_telemetry:
        emit('telemetry_update', latest_telemetry)
    
    if latest_detections:
        emit('detection_history', latest_detections[-10:])


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    connected_clients.discard(request.sid)
    logger.info(f"Client disconnected: {request.sid} (total: {len(connected_clients)})")


@socketio.on('request_status')
def handle_status_request():
    """Handle status request from client"""
    emit('status_update', {
        'telemetry': latest_telemetry,
        'detection_count': len(latest_detections)
    })


def run_server(host='0.0.0.0', port=5000, debug=False):
    """Run Flask web server"""
    if not FLASK_AVAILABLE:
        logger.error("Flask not installed")
        return
    
    logger.info(f"🌐 Starting web server on http://{host}:{port}")
    logger.info(f"📁 Upload folder: {UPLOAD_FOLDER.absolute()}")
    
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    print("=== Flying Wing UAV - Ground Station Web Server ===\n")
    print("Starting server on http://0.0.0.0:5000")
    print("Dashboard: http://localhost:5000")
    print("\nAPI Endpoints:")
    print("  POST /api/telemetry - Receive telemetry")
    print("  POST /api/image - Receive images")
    print("  POST /api/detection - Receive detections")
    print("  POST /api/command - Send commands to UAV")
    print("  GET  /api/status - Get server status")
    print("\nPress Ctrl+C to stop\n")
    
    run_server(debug=True)
