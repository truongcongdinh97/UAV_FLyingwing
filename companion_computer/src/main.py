"""
Flying Wing UAV - Companion Computer Main Application
Raspberry Pi 3B+ - Edge Computing & Control

Author: Flying Wing UAV Team
Date: 2025-11-22
"""

import sys
import os
import time
import argparse
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
        """Main run loop"""
        logger.info("Starting main loop...")
        
        if self.data_logger:
            self.data_logger.log_event("RUNNING", "Main loop started")
        
        self.is_running = True
        
        try:
            while self.is_running:
                self._process_frame()
                
                # Small delay để không quá tải CPU
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            if self.data_logger:
                self.data_logger.log_event("ERROR", f"Main loop error: {e}")
        
        finally:
            self.shutdown()
    
    def _process_frame(self):
        """Xử lý một frame (đã thêm exception handling cho từng frame)"""
        try:
            # Kick watchdog mỗi frame
            if self.watchdog:
                self.watchdog.kick()
            # Read camera frame
            if self.camera is None:
                time.sleep(0.1)
                return
            frame = self.camera.read_frame()
            if frame is None:
                return
            self.frame_count += 1
            # AI Detection với adaptive strategy
            if self.detector:
                detections = self.detector.process_frame(frame)
                if detections:
                    # Log mode changes
                    detector_status = self.detector.get_status()
                    current_mode = detector_status.get('current_mode', 'unknown')
                    if current_mode != self.current_ai_mode:
                        self.current_ai_mode = current_mode
                        self.ai_mode_changes += 1
                        logger.info(f"AI Mode: {current_mode.upper()} (Change #{self.ai_mode_changes})")
                    # Log detections với mode context
                    if self.data_logger:
                        self.data_logger.log_detection(detections, {
                            'ai_mode': current_mode,
                            'detection_frequency': detector_status.get('detection_frequency'),
                            'is_tracking': detector_status.get('is_tracking', False)
                        })
                    # === TÍCH HỢP TÍNH TOÁN VỊ TRÍ MỤC TIÊU ===
                    target_bbox = detections[0]['bbox'] if 'bbox' in detections[0] else None
                    if target_bbox:
                        gps = self.comm.get_gps() if self.comm else None
                        attitude = self.comm.get_attitude() if self.comm else None
                        if gps and attitude:
                            uav_telemetry = {
                                'lat': gps.get('lat'),
                                'lon': gps.get('lon'),
                                'alt': gps.get('alt', 0),
                                'roll': attitude.get('roll', 0),
                                'pitch': attitude.get('pitch', 0),
                                'yaw': attitude.get('yaw', 0)
                            }
                            image_height, image_width = frame.shape[:2]
                            target_geolocation = calculate_target_geolocation(
                                target_bbox, uav_telemetry, image_width, image_height)
                            if target_geolocation:
                                logger.info(f"Target geolocation: {target_geolocation}")
                                if self.http_client:
                                    self.http_client.queue_target_geolocation(target_geolocation)
                                if self.data_logger:
                                    self.data_logger.log_target_geolocation(target_geolocation)
            # Read telemetry from FC (Non-blocking)
            if self.comm and self.comm.is_connected:
                gps = self.comm.get_gps()
                attitude = self.comm.get_attitude()
                battery = self.comm.get_battery()
                if self.data_logger:
                    telemetry = {}
                    if gps: telemetry.update(gps)
                    if attitude: telemetry.update(attitude)
                    if battery: telemetry.update(battery)
                    if telemetry:
                        self.data_logger.log_telemetry(telemetry)
                    if gps and 'lat' in gps and 'lon' in gps:
                        self.data_logger.log_gps(
                            gps['lat'],
                            gps['lon'],
                            gps.get('alt', 0)
                        )
            # Log system status periodically
            if self.frame_count % 300 == 0:
                # Performance Monitor: FPS & Memory
                now = time.time()
                if not hasattr(self, '_last_perf_time'):
                    self._last_perf_time = now
                    self._last_perf_frame = self.frame_count
                elapsed = now - self._last_perf_time
                frames = self.frame_count - getattr(self, '_last_perf_frame', 0)
                fps = frames / elapsed if elapsed > 0 else 0
                import psutil, os
                process = psutil.Process(os.getpid())
                mem_mb = process.memory_info().rss / (1024 * 1024)
                status_info = f"Processed {self.frame_count} frames | FPS: {fps:.2f} | RAM: {mem_mb:.1f}MB"
                if self.detector:
                    detector_status = self.detector.get_status()
                    status_info += f", AI Mode: {detector_status.get('current_mode', 'unknown')}"
                    status_info += f", Tracking: {detector_status.get('is_tracking', False)}"
                logger.info(status_info)
                self._last_perf_time = now
                self._last_perf_frame = self.frame_count
        except Exception as e:
            logger.error(f"Error in _process_frame: {e}")
    
    def shutdown(self):
        """Shutdown tất cả modules"""
        logger.info("Shutting down...")
        
        self.is_running = False
        
        if self.data_logger:
            self.data_logger.log_event("SHUTDOWN", "Companion computer shutting down")
        
        # Stop camera
        if self.camera:
            self.camera.stop()
            logger.info("Camera stopped")
        
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
