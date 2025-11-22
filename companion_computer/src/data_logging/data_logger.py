"""
Data Logging Module
Ghi log telemetry, GPS, video, và các sự kiện
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger
import yaml


class DataLogger:
    """Data logging cho UAV"""
    
    def __init__(self, config_path: str = "config/system_config.yaml"):
        """
        Khởi tạo data logger
        
        Args:
            config_path: Đường dẫn đến file config
        """
        self.config = self._load_config(config_path)
        self.log_dir = self.config.get('log_dir', 'logs')
        self.session_id = self._generate_session_id()
        self.session_dir = None
        
        # Create log directory
        self._setup_logging()
        
        # Log files
        self.telemetry_log = None
        self.gps_log = None
        self.events_log = None
        
        logger.info(f"Data logger initialized - Session: {self.session_id}")
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config['system']['logging']
        else:
            return {'enabled': True, 'log_dir': 'logs', 'log_level': 'INFO'}
    
    def _generate_session_id(self) -> str:
        """Tạo session ID duy nhất"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _setup_logging(self):
        """Setup logging directory và files"""
        if not self.config.get('enabled', True):
            logger.info("Logging disabled")
            return
        
        # Create log directory
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create session directory
        self.session_dir = os.path.join(self.log_dir, self.session_id)
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Setup loguru
        log_file = os.path.join(self.session_dir, "system.log")
        logger.add(
            log_file,
            rotation="10 MB",
            retention="10 days",
            level=self.config.get('log_level', 'INFO')
        )
        
        # Open log files
        if self.config.get('log_telemetry', True):
            telemetry_file = os.path.join(self.session_dir, "telemetry.jsonl")
            self.telemetry_log = open(telemetry_file, 'a')
        
        if self.config.get('log_gps', True):
            gps_file = os.path.join(self.session_dir, "gps.jsonl")
            self.gps_log = open(gps_file, 'a')
        
        events_file = os.path.join(self.session_dir, "events.jsonl")
        self.events_log = open(events_file, 'a')
        
        logger.info(f"Logging to: {self.session_dir}")
    
    def log_telemetry(self, data: Dict[str, Any]):
        """
        Ghi telemetry data
        
        Args:
            data: Telemetry dictionary
        """
        if self.telemetry_log is None:
            return
        
        try:
            # Add timestamp if not present
            if 'timestamp' not in data:
                data['timestamp'] = time.time()
            
            # Write as JSON line
            json_line = json.dumps(data) + '\n'
            self.telemetry_log.write(json_line)
            self.telemetry_log.flush()
            
        except Exception as e:
            logger.error(f"Failed to log telemetry: {e}")
    
    def log_gps(self, lat: float, lon: float, alt: float, 
                additional_data: Optional[Dict] = None):
        """
        Ghi GPS data
        
        Args:
            lat: Latitude
            lon: Longitude
            alt: Altitude (m)
            additional_data: Additional GPS data
        """
        if self.gps_log is None:
            return
        
        try:
            data = {
                'timestamp': time.time(),
                'lat': lat,
                'lon': lon,
                'alt': alt,
            }
            
            if additional_data:
                data.update(additional_data)
            
            json_line = json.dumps(data) + '\n'
            self.gps_log.write(json_line)
            self.gps_log.flush()
            
        except Exception as e:
            logger.error(f"Failed to log GPS: {e}")
    
    def log_event(self, event_type: str, description: str, 
                  data: Optional[Dict] = None):
        """
        Ghi event
        
        Args:
            event_type: Loại event (e.g., "TAKEOFF", "LANDING", "ERROR")
            description: Mô tả event
            data: Additional data
        """
        if self.events_log is None:
            return
        
        try:
            event = {
                'timestamp': time.time(),
                'event_type': event_type,
                'description': description,
            }
            
            if data:
                event['data'] = data
            
            json_line = json.dumps(event) + '\n'
            self.events_log.write(json_line)
            self.events_log.flush()
            
            logger.info(f"Event: {event_type} - {description}")
            
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
    
    def log_detection(self, detections: list):
        """
        Ghi AI detections
        
        Args:
            detections: List of Detection objects
        """
        if not detections:
            return
        
        try:
            data = {
                'timestamp': time.time(),
                'detections': [
                    {
                        'class': det.class_name,
                        'confidence': det.confidence,
                        'bbox': det.bbox,
                    }
                    for det in detections
                ]
            }
            
            self.log_event('DETECTION', f"Detected {len(detections)} objects", data)
            
        except Exception as e:
            logger.error(f"Failed to log detection: {e}")
    
    def get_session_dir(self) -> Optional[str]:
        """Lấy đường dẫn session directory"""
        return self.session_dir
    
    def close(self):
        """Đóng tất cả log files"""
        if self.telemetry_log:
            self.telemetry_log.close()
            self.telemetry_log = None
        
        if self.gps_log:
            self.gps_log.close()
            self.gps_log = None
        
        if self.events_log:
            self.events_log.close()
            self.events_log = None
        
        logger.info("Data logger closed")
    
    def __del__(self):
        """Destructor"""
        self.close()


def main():
    """Test data logger"""
    print("Testing Data Logger...")
    
    logger_obj = DataLogger()
    
    # Log some test data
    logger_obj.log_event("TEST", "Data logger test started")
    
    # Telemetry
    logger_obj.log_telemetry({
        'roll': 0.1,
        'pitch': -0.05,
        'yaw': 1.57,
        'altitude': 100.5,
    })
    
    # GPS
    logger_obj.log_gps(10.762622, 106.660172, 10.0, {
        'satellites': 12,
        'hdop': 0.8,
    })
    
    # Event
    logger_obj.log_event("TAKEOFF", "UAV takeoff", {
        'battery': 95,
        'mode': 'AUTO',
    })
    
    print(f"Logs saved to: {logger_obj.get_session_dir()}")
    
    logger_obj.close()
    print("Data logger test completed")


if __name__ == "__main__":
    main()
