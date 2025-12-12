"""
MAVLink Client cho Ground Control Station
Kết nối tới companion computer qua TCP
"""

import socket
import threading
import time
from typing import Callable, Dict, Optional
from loguru import logger

try:
    from pymavlink import mavutil
    MAVLINK_AVAILABLE = True
except ImportError:
    logger.warning("pymavlink not installed, running in mock mode")
    MAVLINK_AVAILABLE = False


class MAVLinkClient:
    """MAVLink client for GCS"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 14550):
        self.host = host
        self.port = port
        self.connection: Optional[mavutil.mavlink_connection] = None
        self.connected = False
        
        # Threading
        self.receiver_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Callbacks
        self.callbacks: Dict[str, Callable] = {}
        
        # Telemetry cache
        self.last_heartbeat = 0
        self.last_attitude = None
        self.last_gps = None
        self.last_battery = None
        self.last_vfr_hud = None
        
        # System info
        self.system_id = 1
        self.component_id = 1
        
    def connect(self, timeout: float = 5.0) -> bool:
        """Connect to companion computer via TCP"""
        if not MAVLINK_AVAILABLE:
            logger.error("pymavlink not available")
            return False
            
        try:
            # Create MAVLink connection
            connection_string = f"tcp:{self.host}:{self.port}"
            logger.info(f"Connecting to {connection_string}...")
            
            self.connection = mavutil.mavlink_connection(
                connection_string,
                source_system=255,  # GCS system ID
                source_component=190  # GCS component ID
            )
            
            # Wait for heartbeat
            logger.info("Waiting for heartbeat...")
            msg = self.connection.wait_heartbeat(timeout=timeout)
            if msg:
                self.system_id = msg.get_srcSystem()
                self.component_id = msg.get_srcComponent()
                logger.success(f"Connected to system {self.system_id}, component {self.component_id}")
                
                self.connected = True
                
                # Start receiver thread
                self.running = True
                self.receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
                self.receiver_thread.start()
                
                return True
            else:
                logger.error("No heartbeat received")
                return False
                
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from companion computer"""
        logger.info("Disconnecting...")
        self.running = False
        
        if self.receiver_thread:
            self.receiver_thread.join(timeout=2.0)
        
        if self.connection:
            self.connection.close()
        
        self.connected = False
        logger.info("Disconnected")
    
    def _receiver_loop(self):
        """Background thread to receive MAVLink messages"""
        logger.info("MAVLink receiver started")
        
        while self.running:
            try:
                msg = self.connection.recv_match(blocking=True, timeout=1.0)
                if msg:
                    self._handle_message(msg)
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                if not self.running:
                    break
        
        logger.info("MAVLink receiver stopped")
    
    def _handle_message(self, msg):
        """Handle received MAVLink message"""
        msg_type = msg.get_type()
        
        # Update cache
        if msg_type == "HEARTBEAT":
            self.last_heartbeat = time.time()
        elif msg_type == "ATTITUDE":
            self.last_attitude = msg
        elif msg_type == "GLOBAL_POSITION_INT":
            self.last_gps = msg
        elif msg_type == "BATTERY_STATUS":
            self.last_battery = msg
        elif msg_type == "VFR_HUD":
            self.last_vfr_hud = msg
        
        # Call registered callbacks
        if msg_type in self.callbacks:
            try:
                self.callbacks[msg_type](msg)
            except Exception as e:
                logger.error(f"Error in callback for {msg_type}: {e}")
    
    def register_callback(self, msg_type: str, callback: Callable):
        """Register callback for specific message type"""
        self.callbacks[msg_type] = callback
        logger.debug(f"Registered callback for {msg_type}")
    
    # ===== Command Methods =====
    
    def send_command_long(self, command: int, param1: float = 0, param2: float = 0,
                         param3: float = 0, param4: float = 0, param5: float = 0,
                         param6: float = 0, param7: float = 0):
        """Send MAVLink COMMAND_LONG"""
        if not self.connected or not self.connection:
            logger.warning("Not connected")
            return False
        
        self.connection.mav.command_long_send(
            self.system_id,
            self.component_id,
            command,
            0,  # confirmation
            param1, param2, param3, param4, param5, param6, param7
        )
        logger.debug(f"Sent command {command}")
        return True
    
    def arm(self) -> bool:
        """Arm motors"""
        logger.info("Arming...")
        return self.send_command_long(
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            1,  # arm
            0, 0, 0, 0, 0, 0
        )
    
    def disarm(self) -> bool:
        """Disarm motors"""
        logger.info("Disarming...")
        return self.send_command_long(
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,  # disarm
            0, 0, 0, 0, 0, 0
        )
    
    def takeoff(self, altitude: float) -> bool:
        """Command takeoff to altitude (meters)"""
        logger.info(f"Takeoff to {altitude}m...")
        return self.send_command_long(
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0, 0, 0, 0, 0, 0, altitude
        )
    
    def land(self) -> bool:
        """Command landing"""
        logger.info("Landing...")
        return self.send_command_long(
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            0, 0, 0, 0, 0, 0, 0
        )
    
    def return_to_launch(self) -> bool:
        """Command Return to Home"""
        logger.info("Return to Launch...")
        return self.send_command_long(
            mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
            0, 0, 0, 0, 0, 0, 0
        )
    
    def set_mode(self, mode: str) -> bool:
        """Set flight mode"""
        logger.info(f"Setting mode to {mode}...")
        
        # Map mode names to MAVLink mode numbers (iNav specific)
        mode_map = {
            "MANUAL": 0,
            "STABILIZE": 1,
            "ALTITUDE_HOLD": 2,
            "AUTO": 3,
            "LOITER": 5,
            "RTH": 6,
        }
        
        if mode not in mode_map:
            logger.error(f"Unknown mode: {mode}")
            return False
        
        return self.send_command_long(
            mavutil.mavlink.MAV_CMD_DO_SET_MODE,
            1,  # MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
            mode_map[mode],
            0, 0, 0, 0, 0
        )
    
    def goto_location(self, lat: float, lon: float, alt: float) -> bool:
        """Goto GPS location"""
        logger.info(f"Goto location: {lat}, {lon}, {alt}m")
        
        if not self.connected or not self.connection:
            return False
        
        self.connection.mav.mission_item_send(
            self.system_id,
            self.component_id,
            0,  # seq
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            2,  # current (guided mode)
            1,  # autocontinue
            0, 0, 0, 0,  # params 1-4
            lat, lon, alt
        )
        return True
    
    # ===== Telemetry Getters =====
    
    def get_attitude(self) -> Optional[Dict]:
        """Get current attitude (roll, pitch, yaw)"""
        if not self.last_attitude:
            return None
        
        return {
            "roll": self.last_attitude.roll,
            "pitch": self.last_attitude.pitch,
            "yaw": self.last_attitude.yaw,
            "rollspeed": self.last_attitude.rollspeed,
            "pitchspeed": self.last_attitude.pitchspeed,
            "yawspeed": self.last_attitude.yawspeed,
        }
    
    def get_gps(self) -> Optional[Dict]:
        """Get GPS position"""
        if not self.last_gps:
            return None
        
        return {
            "lat": self.last_gps.lat / 1e7,
            "lon": self.last_gps.lon / 1e7,
            "alt": self.last_gps.alt / 1000.0,  # mm to m
            "relative_alt": self.last_gps.relative_alt / 1000.0,
            "vx": self.last_gps.vx / 100.0,  # cm/s to m/s
            "vy": self.last_gps.vy / 100.0,
            "vz": self.last_gps.vz / 100.0,
            "heading": self.last_gps.hdg / 100.0,  # centidegrees
        }
    
    def get_battery(self) -> Optional[Dict]:
        """Get battery status"""
        if not self.last_battery:
            return None
        
        return {
            "voltage": self.last_battery.voltages[0] / 1000.0,  # mV to V
            "current": self.last_battery.current_battery / 100.0,  # cA to A
            "remaining": self.last_battery.battery_remaining,  # percent
        }
    
    def get_vfr_hud(self) -> Optional[Dict]:
        """Get VFR HUD data (airspeed, groundspeed, altitude, etc.)"""
        if not self.last_vfr_hud:
            return None
        
        return {
            "airspeed": self.last_vfr_hud.airspeed,
            "groundspeed": self.last_vfr_hud.groundspeed,
            "heading": self.last_vfr_hud.heading,
            "throttle": self.last_vfr_hud.throttle,
            "altitude": self.last_vfr_hud.alt,
            "climb": self.last_vfr_hud.climb,
        }
    
    def is_heartbeat_active(self, timeout: float = 3.0) -> bool:
        """Check if heartbeat is active"""
        if self.last_heartbeat == 0:
            return False
        return (time.time() - self.last_heartbeat) < timeout


# Example usage
if __name__ == "__main__":
    client = MAVLinkClient("192.168.1.100", 14550)
    
    if client.connect(timeout=10):
        logger.info("Connected!")
        
        # Register callback
        def on_gps(msg):
            gps = client.get_gps()
            if gps:
                logger.info(f"GPS: {gps['lat']:.6f}, {gps['lon']:.6f}, Alt: {gps['alt']:.1f}m")
        
        client.register_callback("GLOBAL_POSITION_INT", on_gps)
        
        # Keep running
        try:
            while True:
                if client.is_heartbeat_active():
                    logger.info("Heartbeat OK")
                else:
                    logger.warning("No heartbeat!")
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping...")
        finally:
            client.disconnect()
    else:
        logger.error("Connection failed")
