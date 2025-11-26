"""
Camera Interface Module
Xử lý camera OV5647 trên Raspberry Pi
"""

import cv2
import numpy as np
from typing import Optional, Tuple
from loguru import logger
import yaml
import os

# Try to import picamera2 (only available on RPi)
try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    logger.warning("picamera2 not available - using fallback mode")
    PICAMERA_AVAILABLE = False


class CameraInterface:
    """Interface cho Pi Camera OV5647"""
    
    def __init__(self, config_path: str = "config/camera_config.yaml"):
        """
        Khởi tạo camera interface
        
        Args:
            config_path: Đường dẫn đến file config
        """
        self.config = self._load_config(config_path)
        self.camera = None
        self.is_running = False
        self.frame_count = 0
        
        logger.info("Camera interface initialized")
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration từ YAML"""
        # Check system config first for override
        # Try multiple locations for system_config.yaml
        possible_paths = [
            "config/system_config.yaml",
            "companion_computer/config/system_config.yaml",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config/system_config.yaml")
        ]
        
        for sys_path in possible_paths:
            if os.path.exists(sys_path):
                try:
                    with open(sys_path, 'r') as f:
                        sys_conf = yaml.safe_load(f)
                        if sys_conf and 'camera' in sys_conf:
                            logger.info(f"Loaded camera config from {sys_path}")
                            return sys_conf['camera']
                except Exception as e:
                    logger.warning(f"Error loading config from {sys_path}: {e}")

        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config['camera']
        else:
            logger.warning(f"Config not found: {config_path}, using defaults")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """Default configuration"""
        return {
            'resolution': {'width': 640, 'height': 480},
            'framerate': 30,
            'flip_horizontal': False,
            'flip_vertical': False,
            'rotation': 0,
            'source': 'auto', # auto, picamera, opencv, mock, ip_webcam
            'ip_url': 'http://192.168.1.169:8080/video' # Default for IP Webcam
        }
    
    def start(self) -> bool:
        """
        Khởi động camera
        
        Returns:
            True nếu thành công
        """
        if self.is_running:
            logger.warning("Camera already running")
            return True
        
        source = self.config.get('source', 'auto')
        logger.info(f"Starting camera with source: {source}")

        try:
            if source == 'mock':
                self._start_mock_camera()
            elif source == 'ip_webcam':
                self._start_ip_webcam()
            elif source == 'picamera' or (source == 'auto' and PICAMERA_AVAILABLE):
                self._start_picamera()
            else:
                self._start_opencv_camera()
            
            self.is_running = True
            logger.info("Camera started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            return False

    def _start_mock_camera(self):
        """Start mock camera for simulation"""
        self.camera = "MOCK"
        logger.info("Mock camera started (simulation mode)")

    def _start_ip_webcam(self):
        """Start IP Webcam stream (Android)"""
        url = self.config.get('ip_url', 'http://192.168.1.169:8080/video')
        logger.info(f"Connecting to IP Webcam at {url}...")
        self.camera = cv2.VideoCapture(url)
        
        # Optimize for low latency
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not self.camera.isOpened():
            raise Exception(f"Could not open video stream from {url}")
            
        logger.info("IP Webcam connected")

    def _start_picamera(self):
        """Khởi động Pi Camera với picamera2"""
        self.camera = Picamera2()
        
        # Configure camera
        config = self.camera.create_preview_configuration(
            main={
                "size": (
                    self.config['resolution']['width'],
                    self.config['resolution']['height']
                ),
                "format": "RGB888"
            }
        )
        self.camera.configure(config)
        self.camera.start()
        
        logger.info("Pi Camera started with picamera2")
    
    def _start_opencv_camera(self):
        """Fallback: OpenCV camera (for testing on non-Pi systems)"""
        self.camera = cv2.VideoCapture(0)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 
                       self.config['resolution']['width'])
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 
                       self.config['resolution']['height'])
        self.camera.set(cv2.CAP_PROP_FPS, self.config['framerate'])
        
        logger.info("OpenCV camera started (fallback mode)")
    
    def read_frame(self) -> Optional[np.ndarray]:
        """
        Đọc frame từ camera
        
        Returns:
            Frame dạng numpy array (BGR) hoặc None nếu lỗi
        """
        if not self.is_running:
            logger.warning("Camera not running")
            return None
        
        try:
            if self.camera == "MOCK":
                # Generate mock frame (noise or black)
                width = self.config.get('width', 640)
                height = self.config.get('height', 480)
                # Create a dummy frame with some moving noise to simulate video
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                # Add some random noise
                noise = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
                frame = cv2.addWeighted(frame, 0.7, noise, 0.3, 0)
                # Add frame count text
                cv2.putText(frame, f"MOCK CAMERA {self.frame_count}", (50, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                # Simulate FPS delay
                import time
                time.sleep(1.0 / self.config.get('fps', 30))
                
            elif PICAMERA_AVAILABLE and isinstance(self.camera, Picamera2):
                # picamera2 returns RGB
                frame = self.camera.capture_array()
                # Convert RGB to BGR for OpenCV compatibility
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            else:
                # OpenCV camera
                ret, frame = self.camera.read()
                if not ret:
                    # If opencv fails (e.g. end of video file), loop or return None
                    # For now, just log error once per second to avoid spam
                    if self.frame_count % 30 == 0:
                        logger.error("Failed to read frame from OpenCV source")
                    return None
            
            # Apply transformations
            if self.camera != "MOCK":
                frame = self._apply_transformations(frame)
            
            self.frame_count += 1
            return frame
            
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            return None
    
    def _apply_transformations(self, frame: np.ndarray) -> np.ndarray:
        """Áp dụng flip và rotation"""
        if self.config.get('flip_horizontal', False):
            frame = cv2.flip(frame, 1)
        
        if self.config.get('flip_vertical', False):
            frame = cv2.flip(frame, 0)
        
        rotation = self.config.get('rotation', 0)
        if rotation == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif rotation == 270:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        return frame
    
    def get_frame_dimensions(self) -> Tuple[int, int]:
        """
        Lấy kích thước frame
        
        Returns:
            (width, height)
        """
        return (
            self.config['resolution']['width'],
            self.config['resolution']['height']
        )
    
    def stop(self):
        """Dừng camera"""
        if not self.is_running:
            return
        
        try:
            if PICAMERA_AVAILABLE and isinstance(self.camera, Picamera2):
                self.camera.stop()
            else:
                self.camera.release()
            
            self.is_running = False
            logger.info("Camera stopped")
            
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")
    
    def __del__(self):
        """Destructor"""
        self.stop()


def main():
    """Test camera interface"""
    print("Testing Camera Interface...")
    
    camera = CameraInterface()
    
    if not camera.start():
        print("Failed to start camera")
        return
    
    print("Camera started. Press 'q' to quit.")
    print(f"Frame dimensions: {camera.get_frame_dimensions()}")
    
    try:
        while True:
            frame = camera.read_frame()
            
            if frame is not None:
                # Display frame info
                cv2.putText(frame, f"Frame: {camera.frame_count}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           1, (0, 255, 0), 2)
                
                # Show frame
                cv2.imshow('Camera Test', frame)
            
            # Exit on 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        camera.stop()
        cv2.destroyAllWindows()
        print("Camera test completed")


if __name__ == "__main__":
    main()
