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
from ai import ObjectDetector
from communication import SerialCommunication
from data_logging import DataLogger


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
        
        self.is_running = False
        self.frame_count = 0
        
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
            
            # Camera
            if auto_start.get('camera', True):
                self.camera = CameraInterface()
                if not self.camera.start():
                    logger.warning("Camera failed to start")
                else:
                    logger.info("✓ Camera ready")
            
            # AI Detector
            if auto_start.get('ai', True):
                self.detector = ObjectDetector()
                logger.info("✓ AI Detector ready")
            
            # Serial Communication
            self.comm = SerialCommunication()
            if self.comm.connect():
                logger.info("✓ Serial communication ready")
            else:
                logger.warning("Serial communication failed (normal on test systems)")
            
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
        """Xử lý một frame"""
        # Read camera frame
        if self.camera is None:
            time.sleep(0.1)
            return
        
        frame = self.camera.read_frame()
        if frame is None:
            return
        
        self.frame_count += 1
        
        # AI Detection (mỗi N frames để save CPU)
        process_interval = 2  # Process every 2 frames
        if self.detector and (self.frame_count % process_interval == 0):
            detections = self.detector.detect(frame)
            
            if detections:
                logger.debug(f"Detected {len(detections)} objects")
                
                # Log detections
                if self.data_logger:
                    self.data_logger.log_detection(detections)
                
                # Draw boxes (if needed for streaming/recording)
                # frame = self.detector.draw_detections(frame, detections)
        
        # Read telemetry from FC
        if self.comm and self.comm.is_connected:
            telemetry = self.comm.read_telemetry()
            
            if telemetry and self.data_logger:
                self.data_logger.log_telemetry(telemetry)
                
                # Extract GPS if available
                if 'lat' in telemetry and 'lon' in telemetry:
                    self.data_logger.log_gps(
                        telemetry['lat'],
                        telemetry['lon'],
                        telemetry.get('alt', 0)
                    )
        
        # Log frame info periodically
        if self.frame_count % 300 == 0:  # Every 300 frames (~10s at 30fps)
            logger.info(f"Processed {self.frame_count} frames")
    
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
