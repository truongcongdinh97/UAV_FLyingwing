"""
Test Companion Computer modules without hardware
Mock camera and sensors for development
"""

import sys
import os
import time
import numpy as np
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from camera.camera_interface import CameraInterface
from data_logging.data_logger import DataLogger


def test_camera_mock():
    """Test camera interface with mock/webcam"""
    logger.info("=== Camera Interface Test ===")
    
    camera = CameraInterface()
    
    if camera.start():
        logger.success("Camera started")
        
        for i in range(10):
            frame = camera.read_frame()
            if frame is not None:
                logger.info(f"Frame {i+1}: {frame.shape}")
            else:
                logger.warning(f"Frame {i+1}: Failed to read")
            
            time.sleep(0.5)
        
        camera.stop()
        logger.success("Camera test complete")
    else:
        logger.error("Camera failed to start")


def test_data_logger():
    """Test data logging"""
    logger.info("\n=== Data Logger Test ===")
    
    data_logger = DataLogger()
    
    # Log telemetry
    for i in range(5):
        telemetry = {
            "altitude": 50.0 + i,
            "speed": 15.0,
            "battery_voltage": 16.8 - i * 0.1,
            "battery_current": 10.0,
        }
        data_logger.log_telemetry(telemetry)
        logger.info(f"Logged telemetry {i+1}")
        time.sleep(0.2)
    
    # Log GPS
    data_logger.log_gps(
        lat=21.028511,
        lon=105.804817,
        alt=50.0
    )
    logger.info("Logged GPS data")
    
    # Log events
    data_logger.log_event("test_start", {"message": "Test started"})
    data_logger.log_event("test_complete", {"message": "Test complete"})
    
    logger.success(f"Data logged to: {data_logger.session_dir}")


def test_mock_flight():
    """Simulate complete flight"""
    logger.info("\n=== Mock Flight Simulation ===")
    
    data_logger = DataLogger()
    
    # Takeoff
    logger.info("🛫 Takeoff...")
    data_logger.log_event("takeoff", {})
    
    for altitude in range(0, 50, 5):
        telemetry = {
            "altitude": altitude,
            "speed": 10.0,
            "battery_voltage": 16.8,
            "battery_current": 15.0,
        }
        data_logger.log_telemetry(telemetry)
        logger.info(f"  Climbing: {altitude}m")
        time.sleep(0.3)
    
    # Cruise
    logger.info("✈️  Cruising...")
    for i in range(10):
        telemetry = {
            "altitude": 50.0,
            "speed": 15.0,
            "battery_voltage": 16.8 - i * 0.05,
            "battery_current": 10.0,
        }
        data_logger.log_telemetry(telemetry)
        
        data_logger.log_gps(
            lat=21.028511 + i * 0.0001,
            lon=105.804817 + i * 0.0001,
            alt=50.0
        )
        
        time.sleep(0.3)
    
    # Landing
    logger.info("🛬 Landing...")
    data_logger.log_event("landing", {})
    
    for altitude in range(50, -1, -5):
        telemetry = {
            "altitude": max(0, altitude),
            "speed": 5.0,
            "battery_voltage": 16.0,
            "battery_current": 8.0,
        }
        data_logger.log_telemetry(telemetry)
        logger.info(f"  Descending: {altitude}m")
        time.sleep(0.3)
    
    data_logger.log_event("landed", {})
    logger.success("Flight simulation complete!")
    logger.info(f"Data saved to: {data_logger.session_dir}")


if __name__ == "__main__":
    # Test camera
    test_camera_mock()
    
    # Test data logger
    test_data_logger()
    
    # Simulate flight
    test_mock_flight()
    
    logger.success("\n🎉 All tests complete!")
