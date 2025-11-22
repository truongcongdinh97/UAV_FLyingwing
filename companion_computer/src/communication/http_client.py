"""
HTTP Client for 5G Data Upload
Upload telemetry, images, and detections to ground station web server
"""

import time
import json
import threading
from queue import Queue
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests not installed. Install: pip install requests")

from loguru import logger
import cv2
import numpy as np


class HTTPUploadClient:
    """HTTP client for uploading data to ground station"""
    
    def __init__(self, server_url: str = "http://192.168.1.100:5000",
                 api_key: Optional[str] = None,
                 max_queue_size: int = 100):
        """
        Initialize HTTP upload client
        
        Args:
            server_url: Ground station server URL
            api_key: Optional API key for authentication
            max_queue_size: Maximum upload queue size
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        
        # Upload queues
        self.telemetry_queue = Queue(maxsize=max_queue_size)
        self.image_queue = Queue(maxsize=max_queue_size)
        self.detection_queue = Queue(maxsize=max_queue_size)
        
        # Worker threads
        self.is_running = False
        self.telemetry_worker = None
        self.image_worker = None
        self.detection_worker = None
        
        # Statistics
        self.stats = {
            "telemetry_uploaded": 0,
            "images_uploaded": 0,
            "detections_uploaded": 0,
            "upload_errors": 0,
            "last_upload": None
        }
        
        logger.info(f"📡 HTTP Upload Client initialized: {server_url}")
    
    def start(self):
        """Start upload workers"""
        if not REQUESTS_AVAILABLE:
            logger.error("Cannot start: requests library not available")
            return False
        
        if self.is_running:
            logger.warning("Upload client already running")
            return False
        
        self.is_running = True
        
        # Start worker threads
        self.telemetry_worker = threading.Thread(
            target=self._telemetry_upload_worker,
            daemon=True
        )
        self.image_worker = threading.Thread(
            target=self._image_upload_worker,
            daemon=True
        )
        self.detection_worker = threading.Thread(
            target=self._detection_upload_worker,
            daemon=True
        )
        
        self.telemetry_worker.start()
        self.image_worker.start()
        self.detection_worker.start()
        
        logger.success("📡 HTTP Upload Client STARTED")
        return True
    
    def stop(self):
        """Stop upload workers"""
        self.is_running = False
        
        if self.telemetry_worker:
            self.telemetry_worker.join(timeout=2)
        if self.image_worker:
            self.image_worker.join(timeout=2)
        if self.detection_worker:
            self.detection_worker.join(timeout=2)
        
        logger.info("📡 HTTP Upload Client STOPPED")
    
    def queue_telemetry(self, telemetry: Dict):
        """Queue telemetry data for upload"""
        try:
            # Add timestamp
            telemetry['timestamp'] = datetime.now().isoformat()
            
            self.telemetry_queue.put_nowait(telemetry)
            logger.debug(f"Queued telemetry (queue size: {self.telemetry_queue.qsize()})")
            
        except Exception as e:
            logger.warning(f"Failed to queue telemetry: {e}")
    
    def queue_image(self, image: np.ndarray, metadata: Dict):
        """Queue image for upload"""
        try:
            # Add timestamp to metadata
            metadata['timestamp'] = datetime.now().isoformat()
            
            self.image_queue.put_nowait((image, metadata))
            logger.debug(f"Queued image (queue size: {self.image_queue.qsize()})")
            
        except Exception as e:
            logger.warning(f"Failed to queue image: {e}")
    
    def queue_detection(self, detection: Dict):
        """Queue AI detection for upload"""
        try:
            # Add timestamp
            detection['timestamp'] = datetime.now().isoformat()
            
            self.detection_queue.put_nowait(detection)
            logger.debug(f"Queued detection (queue size: {self.detection_queue.qsize()})")
            
        except Exception as e:
            logger.warning(f"Failed to queue detection: {e}")
    
    def _telemetry_upload_worker(self):
        """Background worker for telemetry upload"""
        while self.is_running:
            try:
                # Get telemetry from queue (with timeout)
                telemetry = self.telemetry_queue.get(timeout=1.0)
                
                # Upload
                success = self._upload_telemetry(telemetry)
                
                if success:
                    self.stats['telemetry_uploaded'] += 1
                    self.stats['last_upload'] = datetime.now().isoformat()
                else:
                    self.stats['upload_errors'] += 1
                
            except Exception as e:
                # Queue empty or other error
                pass
    
    def _image_upload_worker(self):
        """Background worker for image upload"""
        while self.is_running:
            try:
                # Get image from queue
                image, metadata = self.image_queue.get(timeout=1.0)
                
                # Upload
                success = self._upload_image(image, metadata)
                
                if success:
                    self.stats['images_uploaded'] += 1
                    self.stats['last_upload'] = datetime.now().isoformat()
                else:
                    self.stats['upload_errors'] += 1
                
            except Exception as e:
                pass
    
    def _detection_upload_worker(self):
        """Background worker for detection upload"""
        while self.is_running:
            try:
                # Get detection from queue
                detection = self.detection_queue.get(timeout=1.0)
                
                # Upload
                success = self._upload_detection(detection)
                
                if success:
                    self.stats['detections_uploaded'] += 1
                    self.stats['last_upload'] = datetime.now().isoformat()
                else:
                    self.stats['upload_errors'] += 1
                
            except Exception as e:
                pass
    
    def _upload_telemetry(self, telemetry: Dict) -> bool:
        """Upload telemetry to server"""
        try:
            url = f"{self.server_url}/api/telemetry"
            
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            response = requests.post(
                url,
                json=telemetry,
                headers=headers,
                timeout=5.0
            )
            
            if response.status_code == 200:
                logger.debug("Telemetry uploaded successfully")
                return True
            else:
                logger.warning(f"Telemetry upload failed: {response.status_code}")
                return False
            
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error - server unreachable")
            return False
        except requests.exceptions.Timeout:
            logger.warning("Upload timeout")
            return False
        except Exception as e:
            logger.error(f"Telemetry upload error: {e}")
            return False
    
    def _upload_image(self, image: np.ndarray, metadata: Dict) -> bool:
        """Upload image to server"""
        try:
            url = f"{self.server_url}/api/image"
            
            # Encode image as JPEG
            _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            image_bytes = buffer.tobytes()
            
            # Prepare multipart form data
            files = {
                'image': ('image.jpg', image_bytes, 'image/jpeg')
            }
            
            data = {
                'metadata': json.dumps(metadata)
            }
            
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            response = requests.post(
                url,
                files=files,
                data=data,
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                logger.debug("Image uploaded successfully")
                return True
            else:
                logger.warning(f"Image upload failed: {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"Image upload error: {e}")
            return False
    
    def _upload_detection(self, detection: Dict) -> bool:
        """Upload AI detection to server"""
        try:
            url = f"{self.server_url}/api/detection"
            
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            response = requests.post(
                url,
                json=detection,
                headers=headers,
                timeout=5.0
            )
            
            if response.status_code == 200:
                logger.debug("Detection uploaded successfully")
                return True
            else:
                logger.warning(f"Detection upload failed: {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"Detection upload error: {e}")
            return False
    
    def send_command_request(self, command: str, params: Dict = None) -> Optional[Dict]:
        """Request command execution from ground station"""
        try:
            url = f"{self.server_url}/api/command"
            
            data = {
                'command': command,
                'params': params or {},
                'timestamp': datetime.now().isoformat()
            }
            
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=5.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Command request failed: {response.status_code}")
                return None
            
        except Exception as e:
            logger.error(f"Command request error: {e}")
            return None
    
    def get_status(self) -> Dict:
        """Get upload client status"""
        return {
            "running": self.is_running,
            "server_url": self.server_url,
            "queue_sizes": {
                "telemetry": self.telemetry_queue.qsize(),
                "images": self.image_queue.qsize(),
                "detections": self.detection_queue.qsize()
            },
            "statistics": self.stats
        }


# Example usage
if __name__ == "__main__":
    print("=== HTTP Upload Client Test ===\n")
    
    if not REQUESTS_AVAILABLE:
        print("ERROR: requests library not installed")
        print("Install: pip install requests")
        exit(1)
    
    # Create client
    client = HTTPUploadClient(server_url="http://192.168.1.100:5000")
    client.start()
    
    # Test telemetry upload
    print("Queueing test telemetry...")
    telemetry = {
        "latitude": 21.028511,
        "longitude": 105.804817,
        "altitude": 50.0,
        "battery": 85,
        "speed": 15.0
    }
    client.queue_telemetry(telemetry)
    
    # Test detection upload
    print("Queueing test detection...")
    detection = {
        "class": "person",
        "confidence": 0.92,
        "bbox": [100, 200, 150, 250],
        "gps": {"lat": 21.028511, "lon": 105.804817}
    }
    client.queue_detection(detection)
    
    # Status
    time.sleep(2)
    status = client.get_status()
    print(f"\nStatus: {json.dumps(status, indent=2)}")
    
    # Stop
    print("\nStopping client...")
    client.stop()
