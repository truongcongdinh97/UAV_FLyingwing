"""
Flying Wing UAV - Companion Computer Main Application
Raspberry Pi 3B+ - Edge Computing & Control

Author: Trương Công Định & Đặng Duy Long
Date: 2025-11-22
"""

import sys
import os
import time
import argparse
import threading
from queue import Queue, Full, Empty
from loguru import logger
import yaml

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules
from camera import CameraInterface
from ai import AdaptiveDetector
from communication.mavlink_handler import MAVLinkHandler
from data_logging import DataLogger
from navigation.geolocation import calculate_target_geolocation


class CompanionComputer:
    """Main application cho Raspberry Pi companion computer"""
    
    def __init__(self, config_path: str = "config/system_config.yaml"):
        """
        Khởi tạo companion computer
        
        Args:
            config_path: Đường dẫn đến file config
        """
        logger.info("=" * 70)
        logger.info("FLYING WING UAV - COMPANION COMPUTER")
        logger.info("=" * 70)
        
        # Load config
        self.config = self._load_config(config_path)
        
                # Initialize modules
        self.camera = None
        self.detector = None
        self.comm = None
        self.data_logger = None
        self.http_client = None
        
        # AI mode tracking
        self.current_ai_mode = "reconnaissance"  # Default
        self.ai_mode_changes = 0
        
        self.is_running = False
        self.frame_count = 0
        self.watchdog = None
        
        # Pipeline queues (size=2 để drop frame cũ, ưu tiên real-time)
        self.frame_queue = Queue(maxsize=2)
        self.upload_queue = Queue(maxsize=50)
        
        # Pipeline threads
        self.camera_thread = None
        self.ai_thread = None
        self.upload_thread = None
        
        logger.info("Companion computer initialized")
    
    def _load_config(self, config_path: str) -> dict:
        """Load system configuration"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"Config not found: {config_path}, using defaults")
            return {'system': {'debug': True}}
    
    def setup(self) -> bool:
        """
        Setup tất cả các modules
        
        Returns:
            True nếu thành công
        """
        logger.info("Setting up modules...")
        
        system_config = self.config.get('system', {})
        auto_start = system_config.get('auto_start', {})
        
        try:
            # Data Logger (always setup first)
            if system_config.get('logging', {}).get('enabled', True):
                self.data_logger = DataLogger()
                self.data_logger.log_event("STARTUP", "Companion computer starting")
            # Watchdog Timer
            from watchdog import WatchdogTimer
            self.watchdog = WatchdogTimer(timeout_s=15)
            self.watchdog.start()
            # HTTP Client
            self.http_client = None
            http_config = system_config.get('http_upload', {})
            if http_config.get('enabled', True):
                from communication.http_client import HTTPUploadClient
                server_url = http_config.get('server_url', 'http://192.168.1.100:5000')
                api_key = http_config.get('api_key', None)
                self.http_client = HTTPUploadClient(server_url=server_url, api_key=api_key)
                self.http_client.start()
            
            # Camera
            if auto_start.get('camera', True):
                self.camera = CameraInterface()
                if not self.camera.start():
                    logger.warning("Camera failed to start")
                else:
                    logger.info("✓ Camera ready")
            
                        # AI Detector với RC mode switching
            if auto_start.get('ai', True) and self.comm:
                self.detector = AdaptiveDetector(self.comm)
                logger.info("✓ Adaptive AI Detector with RC mode switching ready")
            
            # MAVLink Communication (ArduPilot)
            # Check for connection config (Simulation/TCP) or Serial config
            conn_config = self.config.get('connection', {})
            serial_config = self.config.get('system', {}).get('serial', {})
            
            port = conn_config.get('connection_string') or serial_config.get('port', '/dev/serial0')
            baud = conn_config.get('baudrate') or serial_config.get('baudrate', 921600)
            
            logger.info(f"Initializing MAVLink on {port} at {baud}")
            self.comm = MAVLinkHandler(port=port, baudrate=baud)
            
            if self.comm.connect():
                logger.info("✓ MAVLink communication ready")
            else:
                logger.warning("MAVLink communication failed (normal on test systems)")
            
            logger.info("Setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False
    
    def run(self):
        """Main run loop với 3 luồng song song"""
        logger.info("Starting parallel pipeline...")
        
        if self.data_logger:
            self.data_logger.log_event("RUNNING", "Parallel pipeline started")
        
        self.is_running = True
        
        try:
            # Start 3 parallel threads
            self.camera_thread = threading.Thread(target=self._camera_telemetry_loop, daemon=True)
            self.ai_thread = threading.Thread(target=self._ai_geolocation_loop, daemon=True)
            self.upload_thread = threading.Thread(target=self._upload_loop, daemon=True)
            
            self.camera_thread.start()
            self.ai_thread.start()
            self.upload_thread.start()
            
            logger.info("✓ All 3 parallel threads started")
            
            # Main thread chỉ monitor và kick watchdog
            while self.is_running:
                if self.watchdog:
                    self.watchdog.kick()
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            if self.data_logger:
                self.data_logger.log_event("ERROR", f"Main loop error: {e}")
        
        finally:
            self.shutdown()
    
    def _camera_telemetry_loop(self):
        """Luồng 1: Camera & Telemetry (Real-time)"""
        logger.info("Thread 1: Camera & Telemetry started")
        while self.is_running:
            try:
                if self.camera is None:
                    time.sleep(0.1)
                    continue
                
                # Chụp frame và lấy timestamp ngay lập tức
                result = self.camera.read_frame()
                if result is None:
                    continue
                
                frame, frame_timestamp = result
                
                # Lấy telemetry NGAY sau khi chụp để đồng bộ thời gian
                telemetry_snapshot = None
                if self.comm and self.comm.is_connected:
                    gps = self.comm.get_gps()
                    attitude = self.comm.get_attitude()
                    battery = self.comm.get_battery()
                    if gps and attitude:
                        telemetry_snapshot = {
                            'lat': gps.get('lat'),
                            'lon': gps.get('lon'),
                            'alt': gps.get('alt', 0),
                            'roll': attitude.get('roll', 0),
                            'pitch': attitude.get('pitch', 0),
                            'yaw': attitude.get('yaw', 0),
                            'battery': battery
                        }
                
                # Đưa vào queue (drop frame cũ nếu đầy)
                package = {
                    'frame': frame,
                    'timestamp': frame_timestamp,
                    'telemetry': telemetry_snapshot
                }
                
                try:
                    self.frame_queue.put_nowait(package)
                except Full:
                    # Drop frame cũ, lấy frame mới (real-time strategy)
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(package)
                    except:
                        pass
                
                self.frame_count += 1
                
                # Log telemetry
                if self.data_logger and telemetry_snapshot:
                    self.data_logger.log_telemetry(telemetry_snapshot)
                    if 'lat' in telemetry_snapshot and 'lon' in telemetry_snapshot:
                        self.data_logger.log_gps(
                            telemetry_snapshot['lat'],
                            telemetry_snapshot['lon'],
                            telemetry_snapshot.get('alt', 0)
                        )
                
                # Performance monitor
                if self.frame_count % 300 == 0:
                    now = time.time()
                    if not hasattr(self, '_last_perf_time'):
                        self._last_perf_time = now
                        self._last_perf_frame = self.frame_count
                    elapsed = now - self._last_perf_time
                    frames = self.frame_count - getattr(self, '_last_perf_frame', 0)
                    fps = frames / elapsed if elapsed > 0 else 0
                    import psutil
                    process = psutil.Process(os.getpid())
                    mem_mb = process.memory_info().rss / (1024 * 1024)
                    logger.info(f"Camera: {self.frame_count} frames | FPS: {fps:.2f} | RAM: {mem_mb:.1f}MB | Queue: {self.frame_queue.qsize()}")
                    self._last_perf_time = now
                    self._last_perf_frame = self.frame_count
                
                time.sleep(0.001)  # Minimal delay
                
            except Exception as e:
                logger.error(f"Error in camera thread: {e}")
                time.sleep(0.1)
    
    def _ai_geolocation_loop(self):
        """Luồng 2: AI & Geolocation (Heavy Processing)"""
        logger.info("Thread 2: AI & Geolocation started")
        while self.is_running:
            try:
                # Lấy package từ queue (timeout 1s)
                try:
                    package = self.frame_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                frame = package['frame']
                frame_timestamp = package['timestamp']
                telemetry_snapshot = package['telemetry']
                
                # AI Detection
                if self.detector:
                    detections = self.detector.process_frame(frame)
                    
                    if detections:
                        detector_status = self.detector.get_status()
                        current_mode = detector_status.get('current_mode', 'unknown')
                        
                        if current_mode != self.current_ai_mode:
                            self.current_ai_mode = current_mode
                            self.ai_mode_changes += 1
                            logger.info(f"AI Mode: {current_mode.upper()} (Change #{self.ai_mode_changes})")
                        
                        # Log detection
                        if self.data_logger:
                            self.data_logger.log_detection(detections, {
                                'ai_mode': current_mode,
                                'detection_frequency': detector_status.get('detection_frequency'),
                                'is_tracking': detector_status.get('is_tracking', False),
                                'frame_timestamp': frame_timestamp
                            })
                        
                        # Tính toán geolocation
                        target_bbox = detections[0]['bbox'] if 'bbox' in detections[0] else None
                        if target_bbox and telemetry_snapshot:
                            image_height, image_width = frame.shape[:2]
                            target_geolocation = calculate_target_geolocation(
                                target_bbox, telemetry_snapshot, image_width, image_height)
                            
                            if target_geolocation:
                                target_geolocation['frame_timestamp'] = frame_timestamp
                                logger.info(f"Target geolocation: {target_geolocation}")
                                
                                # Đưa vào upload queue
                                try:
                                    self.upload_queue.put_nowait({
                                        'type': 'target',
                                        'data': target_geolocation
                                    })
                                except Full:
                                    logger.warning("Upload queue full, dropping data")
                                
                                # Log ngay
                                if self.data_logger:
                                    self.data_logger.log_target_geolocation(target_geolocation)
            
            except Exception as e:
                logger.error(f"Error in AI thread: {e}")
                time.sleep(0.1)
    
    def _upload_loop(self):
        """Luồng 3: Network Upload (Background)"""
        logger.info("Thread 3: Network Upload started")
        while self.is_running:
            try:
                # Lấy package từ upload queue
                try:
                    package = self.upload_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                # Upload qua HTTP client
                if self.http_client:
                    if package['type'] == 'target':
                        self.http_client.queue_target_geolocation(package['data'])
            
            except Exception as e:
                logger.error(f"Error in upload thread: {e}")
                time.sleep(0.5)
    
    def shutdown(self):
        """Shutdown tất cả modules và threads"""
        logger.info("Shutting down...")
        
        self.is_running = False
        
        if self.data_logger:
            self.data_logger.log_event("SHUTDOWN", "Companion computer shutting down")
        
        # Wait for threads to finish
        if self.camera_thread:
            self.camera_thread.join(timeout=2)
        if self.ai_thread:
            self.ai_thread.join(timeout=2)
        if self.upload_thread:
            self.upload_thread.join(timeout=2)
        
        # Stop watchdog
        if self.watchdog:
            self.watchdog.stop()
        
        # Stop camera
        if self.camera:
            self.camera.stop()
            logger.info("Camera stopped")
        
        # Stop HTTP client
        if self.http_client:
            self.http_client.stop()
            logger.info("HTTP client stopped")
        
        # Disconnect serial
        if self.comm:
            self.comm.disconnect()
            logger.info("Serial disconnected")
        
        # Close logger
        if self.data_logger:
            self.data_logger.close()
            logger.info("Logger closed")
        
        logger.info("Shutdown complete")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Flying Wing UAV Companion Computer"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/system_config.yaml',
        help='Path to system config file'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    if args.debug:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    # Create and run companion computer
    companion = CompanionComputer(config_path=args.config)
    
    if not companion.setup():
        logger.error("Setup failed - exiting")
        return 1
    
    companion.run()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
