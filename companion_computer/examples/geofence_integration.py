"""
Geofence Integration Example
Shows how to integrate geofencing with main companion computer system
"""

import time
from loguru import logger

# Import modules
from safety.geofencing import (
    GeoPoint, GeofencingSystem, GeofenceMonitor, 
    GeofenceTemplates, FenceAction
)
from communication.mavlink_handler import MAVLinkHandler


class GeofenceIntegration:
    """Integrate geofencing with companion computer"""
    
    def __init__(self, mavlink_port: str = "/dev/ttyS0"):
        # Initialize MAVLink
        self.mavlink = MAVLinkHandler(port=mavlink_port, baudrate=57600)
        
        # Initialize geofencing (will set home after GPS lock)
        self.geo_system = None
        self.geo_monitor = None
        
        self.home_set = False
        self.gps_fix = False
        
    def setup_geofencing(self, home: GeoPoint, max_distance: float = 1000.0):
        """Setup geofencing system with home position"""
        self.geo_system = GeofencingSystem(home, max_distance)
        self.geo_monitor = GeofenceMonitor(self.geo_system, self.mavlink)
        
        logger.info(f"🛡️ Geofencing setup complete: Home={home}, Max={max_distance}m")
        self.home_set = True
    
    def load_geofences_from_file(self, filename: str = "geofence_config.json"):
        """Load geofence configuration from file"""
        if not self.home_set:
            logger.error("Cannot load geofences: home position not set")
            return False
        
        try:
            self.geo_system.load_from_file(filename)
            logger.success(f"✓ Geofences loaded from {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to load geofences: {e}")
            return False
    
    def add_example_fences(self):
        """Add example geofences for testing"""
        if not self.home_set:
            logger.error("Cannot add fences: home position not set")
            return
        
        home = self.geo_system.home
        
        # Example 1: Star-shaped military base exclusion zone
        military = GeoPoint(home.lat + 0.002, home.lon + 0.002)  # ~200m north-east
        star = GeofenceTemplates.create_star_exclusion(
            military, 
            radius=100.0,
            name="Military Base - Star Pattern"
        )
        self.geo_system.add_fence(star)
        
        # Example 2: Circular restricted area
        restricted = GeoPoint(home.lat - 0.001, home.lon - 0.001)  # ~100m south-west
        circle = GeofenceTemplates.create_circular_exclusion(
            restricted,
            radius=60.0,
            name="Restricted Area - Circle"
        )
        self.geo_system.add_fence(circle)
        
        # Example 3: Rectangular no-fly zone
        sw = GeoPoint(home.lat + 0.003, home.lon - 0.002)
        ne = GeoPoint(home.lat + 0.004, home.lon - 0.001)
        rect = GeofenceTemplates.create_rectangle_exclusion(sw, ne, "Airport Zone")
        self.geo_system.add_fence(rect)
        
        logger.success(f"✓ Added {len(self.geo_system.fences)} example geofences")
    
    def start_monitoring(self):
        """Start geofence monitoring"""
        if not self.home_set:
            logger.error("Cannot start monitoring: geofencing not setup")
            return False
        
        # Start monitoring
        self.geo_monitor.start_monitoring()
        
        # Setup MAVLink GPS callback
        self.mavlink.register_callback('GPS_RAW_INT', self._handle_gps_update)
        
        logger.success("🛡️ Geofence monitoring ACTIVE")
        return True
    
    def _handle_gps_update(self, msg):
        """Handle GPS updates from MAVLink"""
        # Extract GPS data
        lat = msg.lat / 1e7  # Scale from int32 to degrees
        lon = msg.lon / 1e7
        alt = msg.alt / 1000.0  # Scale from mm to meters
        
        fix_type = msg.fix_type
        
        # Check GPS fix
        if fix_type >= 3:  # 3D fix
            self.gps_fix = True
            
            # Auto-set home on first GPS lock
            if not self.home_set:
                home = GeoPoint(lat, lon)
                self.setup_geofencing(home, max_distance=1000.0)
                logger.success(f"🏠 Auto-set home position: {home}")
        else:
            self.gps_fix = False
            logger.warning(f"No GPS fix (type={fix_type})")
            return
        
        # Update geofence monitor
        if self.home_set and self.geo_monitor.is_monitoring:
            self.geo_monitor.update_position(lat, lon, alt)
    
    def run(self):
        """Main run loop"""
        logger.info("🚀 Starting geofence integration...")
        
        # Connect to MAVLink
        if not self.mavlink.connect():
            logger.error("Failed to connect to MAVLink")
            return
        
        # Wait for GPS lock and home position
        logger.info("⏳ Waiting for GPS lock...")
        while not self.home_set:
            time.sleep(1)
        
        logger.success("✓ Home position set")
        
        # Load or create geofences
        if not self.load_geofences_from_file():
            logger.info("Creating example geofences...")
            self.add_example_fences()
            
            # Save for next time
            self.geo_system.save_to_file("geofence_config.json")
        
        # Start monitoring
        if not self.start_monitoring():
            logger.error("Failed to start monitoring")
            return
        
        # Main loop
        logger.info("🛡️ Geofence monitoring active. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
                
                # Periodic status
                if self.geo_monitor.current_position:
                    pos = self.geo_monitor.current_position
                    alt = self.geo_monitor.current_altitude
                    
                    # Check position
                    is_safe, message, _ = self.geo_system.check_position(pos, alt)
                    
                    if is_safe:
                        logger.debug(f"✓ Position: {pos}, Alt: {alt:.1f}m - SAFE")
                    else:
                        logger.error(f"🚨 Position: {pos}, Alt: {alt:.1f}m - {message}")
        
        except KeyboardInterrupt:
            logger.info("\n⏹️ Stopping geofence monitoring...")
            self.geo_monitor.stop_monitoring()
            self.mavlink.disconnect()
            logger.success("✓ Geofence integration stopped")


# Standalone test
if __name__ == "__main__":
    print("=== Geofence Integration Test ===\n")
    print("This will:")
    print("1. Connect to iNav via MAVLink")
    print("2. Wait for GPS lock")
    print("3. Set home position")
    print("4. Load/create geofences")
    print("5. Monitor position continuously")
    print("\nPress Ctrl+C to stop\n")
    
    integration = GeofenceIntegration(mavlink_port="/dev/ttyS0")
    integration.run()
