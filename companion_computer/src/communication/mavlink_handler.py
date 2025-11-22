"""
MAVLink Protocol Handler
Implementation của communication protocol cho Raspberry Pi
"""

from pymavlink import mavutil
from typing import Dict, Callable, Optional, Any
from loguru import logger
import time
import threading


class MAVLinkHandler:
    """Handler cho MAVLink communication với Flight Controller"""
    
    # Message IDs
    MSG_HEARTBEAT = 0
    MSG_SYS_STATUS = 1
    MSG_GPS_RAW_INT = 24
    MSG_ATTITUDE = 30
    MSG_GLOBAL_POSITION_INT = 33
    MSG_COMMAND_LONG = 76
    MSG_COMMAND_ACK = 77
    
    # Custom message IDs
    MSG_TWIN_ENGINE_CONTROL = 10001
    MSG_AI_DETECTION = 10002
    MSG_COMPANION_HEALTH = 10003
    
    def __init__(self, port: str = '/dev/serial0', baudrate: int = 115200):
        """
        Khởi tạo MAVLink handler
        
        Args:
            port: Serial port
            baudrate: Baudrate
        """
        self.port = port
        self.baudrate = baudrate
        self.master = None
        self.is_connected = False
        
        # Message callbacks
        self.callbacks: Dict[str, list] = {}
        
        # Last received data
        self.last_heartbeat = 0
        self.last_attitude = {}
        self.last_gps = {}
        self.last_battery = {}
        
        # Receiver thread
        self.receiver_thread = None
        self.running = False
        
        logger.info("MAVLink handler initialized")
    
    def connect(self) -> bool:
        """
        Kết nối với FC
        
        Returns:
            True nếu thành công
        """
        try:
            logger.info(f"Connecting to FC at {self.port}:{self.baudrate}")
            
            self.master = mavutil.mavlink_connection(
                self.port,
                baud=self.baudrate
            )
            
            # Wait for heartbeat (timeout 5s)
            logger.info("Waiting for heartbeat...")
            self.master.wait_heartbeat(timeout=5)
            
            self.is_connected = True
            logger.info(f"Connected to system {self.master.target_system}, component {self.master.target_component}")
            
            # Request data streams
            self._request_data_streams()
            
            # Start receiver thread
            self._start_receiver()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def _request_data_streams(self):
        """Request telemetry data streams từ FC"""
        logger.info("Requesting data streams...")
        
        # Request all streams at 10 Hz
        self.master.mav.request_data_stream_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_ALL,
            10,  # Hz
            1    # Start streaming
        )
        
        logger.info("Data streams requested")
    
    def _start_receiver(self):
        """Bắt đầu receiver thread"""
        self.running = True
        self.receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self.receiver_thread.start()
        logger.info("Receiver thread started")
    
    def _receiver_loop(self):
        """Main receiver loop - chạy trong thread riêng"""
        logger.info("Receiver loop started")
        
        while self.running and self.is_connected:
            try:
                # Receive message (non-blocking với timeout ngắn)
                msg = self.master.recv_match(blocking=True, timeout=0.1)
                
                if msg is None:
                    continue
                
                # Process message
                self._process_message(msg)
                
            except Exception as e:
                logger.error(f"Error in receiver loop: {e}")
                time.sleep(0.1)
        
        logger.info("Receiver loop stopped")
    
    def _process_message(self, msg):
        """Process received message"""
        msg_type = msg.get_type()
        
        # Update last received data
        if msg_type == 'HEARTBEAT':
            self.last_heartbeat = time.time()
        
        elif msg_type == 'ATTITUDE':
            self.last_attitude = {
                'roll': msg.roll,
                'pitch': msg.pitch,
                'yaw': msg.yaw,
                'rollspeed': msg.rollspeed,
                'pitchspeed': msg.pitchspeed,
                'yawspeed': msg.yawspeed,
            }
        
        elif msg_type == 'GPS_RAW_INT':
            self.last_gps = {
                'lat': msg.lat / 1e7,
                'lon': msg.lon / 1e7,
                'alt': msg.alt / 1000.0,
                'fix_type': msg.fix_type,
                'satellites': msg.satellites_visible,
            }
        
        elif msg_type == 'SYS_STATUS':
            self.last_battery = {
                'voltage': msg.voltage_battery / 1000.0,
                'current': msg.current_battery / 100.0,
                'remaining': msg.battery_remaining,
            }
        
        # Call registered callbacks
        if msg_type in self.callbacks:
            for callback in self.callbacks[msg_type]:
                try:
                    callback(msg)
                except Exception as e:
                    logger.error(f"Error in callback for {msg_type}: {e}")
    
    def register_callback(self, msg_type: str, callback: Callable):
        """
        Register callback cho message type
        
        Args:
            msg_type: Message type (e.g., 'ATTITUDE', 'GPS_RAW_INT')
            callback: Callback function(msg)
        """
        if msg_type not in self.callbacks:
            self.callbacks[msg_type] = []
        
        self.callbacks[msg_type].append(callback)
        logger.debug(f"Registered callback for {msg_type}")
    
    def send_command(self, command: int, param1: float = 0, param2: float = 0,
                    param3: float = 0, param4: float = 0, param5: float = 0,
                    param6: float = 0, param7: float = 0) -> bool:
        """
        Gửi command đến FC
        
        Args:
            command: MAV_CMD_* command ID
            param1-7: Command parameters
            
        Returns:
            True nếu command được gửi
        """
        if not self.is_connected:
            logger.warning("Not connected - cannot send command")
            return False
        
        try:
            self.master.mav.command_long_send(
                self.master.target_system,
                self.master.target_component,
                command,
                0,  # confirmation
                param1, param2, param3, param4,
                param5, param6, param7
            )
            
            logger.info(f"Sent command {command}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            return False
    
    def send_takeoff(self, altitude: float = 10.0) -> bool:
        """
        Gửi lệnh takeoff
        
        Args:
            altitude: Target altitude (m)
        """
        return self.send_command(
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            param7=altitude
        )
    
    def send_land(self) -> bool:
        """Gửi lệnh land"""
        return self.send_command(mavutil.mavlink.MAV_CMD_NAV_LAND)
    
    def send_rth(self) -> bool:
        """Gửi lệnh Return to Home"""
        return self.send_command(mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH)
    
    def return_to_home(self) -> bool:
        """Alias for send_rth (for geofencing compatibility)"""
        return self.send_rth()
    
    def land(self) -> bool:
        """Alias for send_land (for geofencing compatibility)"""
        return self.send_land()
    
    def set_mode(self, mode: str) -> bool:
        """
        Set flight mode
        
        Args:
            mode: Mode name (e.g., 'LOITER', 'AUTO', 'MANUAL')
        """
        if not self.is_connected:
            logger.warning("Not connected - cannot set mode")
            return False
        
        try:
            # Get mode ID
            mode_id = self.master.mode_mapping().get(mode.upper())
            if mode_id is None:
                logger.error(f"Unknown mode: {mode}")
                return False
            
            # Send mode change command
            self.master.mav.set_mode_send(
                self.master.target_system,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                mode_id
            )
            
            logger.info(f"Set mode to {mode}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set mode: {e}")
            return False
    
    def send_waypoint(self, lat: float, lon: float, alt: float) -> bool:
        """
        Send single waypoint for guided mode navigation
        
        Args:
            lat: Latitude (degrees)
            lon: Longitude (degrees)
            alt: Altitude (meters MSL)
        """
        if not self.is_connected:
            logger.warning("Not connected - cannot send waypoint")
            return False
        
        try:
            # Send waypoint as MISSION_ITEM
            self.master.mav.mission_item_send(
                self.master.target_system,
                self.master.target_component,
                0,  # seq
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                2,  # current (2 = guided mode waypoint)
                1,  # autocontinue
                0, 0, 0, 0,  # params 1-4
                lat, lon, alt
            )
            
            logger.info(f"Sent guided waypoint: ({lat:.6f}, {lon:.6f}, {alt:.1f}m)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send waypoint: {e}")
            return False
    
    def send_arm(self) -> bool:
        """Arm motors"""
        return self.send_command(
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            param1=1  # 1 = arm
        )
    
    def send_disarm(self) -> bool:
        """Disarm motors"""
        return self.send_command(
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            param1=0  # 0 = disarm
        )
    
    def get_attitude(self) -> Dict[str, float]:
        """Lấy attitude data cuối cùng"""
        return self.last_attitude.copy()
    
    def get_gps(self) -> Dict[str, Any]:
        """Lấy GPS data cuối cùng"""
        return self.last_gps.copy()
    
    def get_battery(self) -> Dict[str, float]:
        """Lấy battery data cuối cùng"""
        return self.last_battery.copy()
    
    def is_heartbeat_active(self, timeout: float = 3.0) -> bool:
        """
        Check xem có nhận heartbeat gần đây không
        
        Args:
            timeout: Timeout (seconds)
        """
        if self.last_heartbeat == 0:
            return False
        
        return (time.time() - self.last_heartbeat) < timeout
    
    def disconnect(self):
        """Ngắt kết nối"""
        logger.info("Disconnecting...")
        
        self.running = False
        
        if self.receiver_thread:
            self.receiver_thread.join(timeout=1.0)
        
        if self.master:
            self.master.close()
        
        self.is_connected = False
        logger.info("Disconnected")
    
    def __del__(self):
        """Destructor"""
        self.disconnect()


def main():
    """Test MAVLink handler"""
    print("Testing MAVLink Handler...")
    
    handler = MAVLinkHandler()
    
    # Register callbacks
    def on_attitude(msg):
        print(f"Attitude: Roll={msg.roll:.2f}, Pitch={msg.pitch:.2f}, Yaw={msg.yaw:.2f}")
    
    def on_gps(msg):
        lat = msg.lat / 1e7
        lon = msg.lon / 1e7
        print(f"GPS: ({lat:.6f}, {lon:.6f}), Sats={msg.satellites_visible}")
    
    handler.register_callback('ATTITUDE', on_attitude)
    handler.register_callback('GPS_RAW_INT', on_gps)
    
    # Try to connect
    if not handler.connect():
        print("❌ Failed to connect - this is normal without hardware")
        print("Deploy to Raspberry Pi to test with actual Flight Controller")
        return
    
    print("✅ Connected successfully!")
    
    # Monitor for 10 seconds
    try:
        for i in range(10):
            print(f"\n--- Second {i+1} ---")
            
            # Check heartbeat
            if handler.is_heartbeat_active():
                print("✅ Heartbeat active")
            else:
                print("⚠️  No heartbeat")
            
            # Print latest data
            attitude = handler.get_attitude()
            if attitude:
                print(f"Latest attitude: {attitude}")
            
            gps = handler.get_gps()
            if gps:
                print(f"Latest GPS: {gps}")
            
            battery = handler.get_battery()
            if battery:
                print(f"Latest battery: {battery}")
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        handler.disconnect()
        print("Test completed")


if __name__ == "__main__":
    main()
