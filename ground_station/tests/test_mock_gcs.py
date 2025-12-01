"""
Test Ground Control Station without real hardware
Mock MAVLink and video data for development
"""

import sys
import time
import os
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock data generators
class MockMAVLink:
    """Mock MAVLink data for testing"""
    
    def __init__(self):
        self.altitude = 50.0
        self.speed = 15.0
        self.battery = 100.0
        self.lat = 21.028511
        self.lon = 105.804817
        
    def get_telemetry(self):
        """Generate mock telemetry"""
        # Simulate flight
        self.altitude += (time.time() % 10 - 5) * 0.1
        self.speed = 15.0 + (time.time() % 5)
        self.battery -= 0.01
        
        return {
            "altitude": max(0, self.altitude),
            "speed": self.speed,
            "battery": max(0, self.battery),
            "lat": self.lat + (time.time() % 100) * 0.0001,
            "lon": self.lon + (time.time() % 100) * 0.0001,
            "roll": (time.time() % 20 - 10) * 2,
            "pitch": (time.time() % 10 - 5),
            "yaw": (time.time() % 360),
        }


def test_gcs_mock():
    """Test GCS with mock data"""
    logger.info("=== Ground Control Station Mock Test ===")
    
    mock = MockMAVLink()
    
    logger.info("Simulating flight for 30 seconds...")
    logger.info("Commands: Press Ctrl+C to stop\n")
    
    try:
        for i in range(30):
            telemetry = mock.get_telemetry()
            
            logger.info(f"[{i+1}s] Alt: {telemetry['altitude']:.1f}m | "
                       f"Speed: {telemetry['speed']:.1f}m/s | "
                       f"Battery: {telemetry['battery']:.1f}% | "
                       f"GPS: {telemetry['lat']:.6f}, {telemetry['lon']:.6f}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\nTest stopped by user")
    
    logger.success("Mock test complete!")


if __name__ == "__main__":
    test_gcs_mock()
