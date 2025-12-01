"""
Simple Logging Test
Test data logger và xem output files
"""

import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_logging import DataLogger

def main():
    print("=" * 70)
    print("DATA LOGGER TEST")
    print("=" * 70)
    
    logger = DataLogger()
    
    print(f"\n📁 Session ID: {logger.session_id}")
    print(f"💾 Log directory: {logger.get_session_dir()}")
    print()
    
    # Test different types of logging
    print("1️⃣  Logging events...")
    logger.log_event("STARTUP", "Test started")
    logger.log_event("TEST", "Testing data logger functionality")
    
    print("2️⃣  Logging telemetry data...")
    for i in range(5):
        logger.log_telemetry({
            'timestamp': time.time(),
            'roll': i * 0.1,
            'pitch': i * 0.05,
            'yaw': i * 0.15,
            'altitude': 100 + i,
            'battery': 100 - i,
        })
        print(f"   ✅ Telemetry #{i+1} logged")
    
    print("3️⃣  Logging GPS data...")
    # Simulate flight path (Saigon area)
    base_lat = 10.762622
    base_lon = 106.660172
    
    for i in range(5):
        lat = base_lat + i * 0.001
        lon = base_lon + i * 0.001
        alt = 10.0 + i * 5
        
        logger.log_gps(lat, lon, alt, {
            'satellites': 12,
            'hdop': 0.8,
            'speed': 15.0 + i,
        })
        print(f"   ✅ GPS #{i+1} logged: ({lat:.6f}, {lon:.6f}, {alt:.1f}m)")
    
    print("4️⃣  Logging events with data...")
    logger.log_event("TAKEOFF", "UAV takeoff initiated", {
        'location': {'lat': base_lat, 'lon': base_lon},
        'battery': 95,
        'mode': 'AUTO',
    })
    
    logger.log_event("WAYPOINT", "Waypoint 1 reached", {
        'waypoint_id': 1,
        'time_elapsed': 60.5,
    })
    
    logger.log_event("LANDING", "Landing sequence started", {
        'battery': 75,
        'altitude': 5.0,
    })
    
    print()
    print("=" * 70)
    print("✅ Test completed!")
    print("=" * 70)
    print()
    print(f"📂 Check log files in: {logger.get_session_dir()}")
    print()
    print("Files created:")
    
    session_dir = logger.get_session_dir()
    if session_dir and os.path.exists(session_dir):
        for filename in os.listdir(session_dir):
            filepath = os.path.join(session_dir, filename)
            size = os.path.getsize(filepath)
            print(f"   - {filename} ({size} bytes)")
    
    logger.close()

if __name__ == "__main__":
    main()
