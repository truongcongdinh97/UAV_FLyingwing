"""
Serial Communication Module
Giao tiếp với Flight Controller qua UART/Serial
Hỗ trợ MAVLink protocol
"""

import serial
from typing import Optional, Dict, Any
from loguru import logger
import yaml
import os
import time

# MAVLink
try:
    from pymavlink import mavutil
    MAVLINK_AVAILABLE = True
except ImportError:
    logger.warning("pymavlink not available")
    MAVLINK_AVAILABLE = False


class SerialCommunication:
    """Serial communication với Flight Controller"""
    
    def __init__(self, config_path: str = "config/system_config.yaml"):
        """
        Khởi tạo serial communication
        
        Args:
            config_path: Đường dẫn đến file config
        """
        self.config = self._load_config(config_path)
        self.connection = None
        self.is_connected = False
        
        logger.info("Serial communication initialized")
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config['system']['serial']
        else:
            logger.warning(f"Config not found: {config_path}")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """Default configuration"""
        return {
            'port': '/dev/serial0',
            'baudrate': 115200,
            'timeout': 1.0,
            'protocol': 'mavlink',
        }
    
    def connect(self) -> bool:
        """
        Kết nối với Flight Controller
        
        Returns:
            True nếu thành công
        """
        if self.is_connected:
            logger.warning("Already connected")
            return True
        
        try:
            port = self.config['port']
            baudrate = self.config['baudrate']
            protocol = self.config['protocol']
            
            if protocol == 'mavlink' and MAVLINK_AVAILABLE:
                self._connect_mavlink(port, baudrate)
            else:
                self._connect_serial(port, baudrate)
            
            self.is_connected = True
            logger.info(f"Connected to {port} at {baudrate} baud")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def _connect_mavlink(self, port: str, baudrate: int):
        """Kết nối với MAVLink"""
        self.connection = mavutil.mavlink_connection(
            port,
            baud=baudrate
        )
        
        # Wait for heartbeat
        logger.info("Waiting for heartbeat...")
        self.connection.wait_heartbeat()
        logger.info("Heartbeat received")
    
    def _connect_serial(self, port: str, baudrate: int):
        """Kết nối serial thông thường"""
        self.connection = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=self.config.get('timeout', 1.0)
        )
    
    def send_command(self, command: str) -> bool:
        """
        Gửi command đến FC
        
        Args:
            command: Command string
            
        Returns:
            True nếu thành công
        """
        if not self.is_connected:
            logger.warning("Not connected")
            return False
        
        try:
            if isinstance(self.connection, serial.Serial):
                self.connection.write(command.encode())
                return True
            else:
                logger.warning("Command sending not implemented for MAVLink")
                return False
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            return False
    
    def read_telemetry(self) -> Optional[Dict[str, Any]]:
        """
        Đọc telemetry từ FC
        
        Returns:
            Dictionary chứa telemetry data hoặc None
        """
        if not self.is_connected:
            return None
        
        try:
            if MAVLINK_AVAILABLE and hasattr(self.connection, 'recv_match'):
                return self._read_mavlink_telemetry()
            else:
                return self._read_serial_data()
        except Exception as e:
            logger.error(f"Failed to read telemetry: {e}")
            return None
    
    def _read_mavlink_telemetry(self) -> Optional[Dict[str, Any]]:
        """Đọc MAVLink telemetry"""
        msg = self.connection.recv_match(blocking=False)
        
        if msg is None:
            return None
        
        # Parse common MAVLink messages
        telemetry = {
            'timestamp': time.time(),
            'message_type': msg.get_type(),
        }
        
        # Attitude
        if msg.get_type() == 'ATTITUDE':
            telemetry.update({
                'roll': msg.roll,
                'pitch': msg.pitch,
                'yaw': msg.yaw,
                'rollspeed': msg.rollspeed,
                'pitchspeed': msg.pitchspeed,
                'yawspeed': msg.yawspeed,
            })
        
        # GPS
        elif msg.get_type() == 'GPS_RAW_INT':
            telemetry.update({
                'lat': msg.lat / 1e7,
                'lon': msg.lon / 1e7,
                'alt': msg.alt / 1000.0,
                'gps_fix': msg.fix_type,
                'satellites': msg.satellites_visible,
            })
        
        # Battery
        elif msg.get_type() == 'SYS_STATUS':
            telemetry.update({
                'battery_voltage': msg.voltage_battery / 1000.0,
                'battery_current': msg.current_battery / 100.0,
                'battery_remaining': msg.battery_remaining,
            })
        
        return telemetry
    
    def _read_serial_data(self) -> Optional[Dict[str, Any]]:
        """Đọc raw serial data"""
        if self.connection.in_waiting > 0:
            data = self.connection.readline().decode('utf-8', errors='ignore').strip()
            return {'raw_data': data, 'timestamp': time.time()}
        return None
    
    def send_gps_data(self, lat: float, lon: float, alt: float) -> bool:
        """
        Gửi GPS data đến FC (nếu cần inject GPS từ companion)
        
        Args:
            lat: Latitude
            lon: Longitude  
            alt: Altitude (m)
            
        Returns:
            True nếu thành công
        """
        if not self.is_connected or not MAVLINK_AVAILABLE:
            return False
        
        try:
            # Send GPS_INPUT message
            self.connection.mav.gps_input_send(
                int(time.time() * 1e6),  # timestamp (us)
                0,  # GPS ID
                0,  # ignore flags
                0,  # time since boot (ms)
                3,  # fix type (3D fix)
                int(lat * 1e7),
                int(lon * 1e7),
                alt,
                1.0,  # hdop
                1.0,  # vdop
                0,  # velocity (m/s)
                0,  # course
                10,  # satellites visible
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send GPS data: {e}")
            return False
    
    def disconnect(self):
        """Ngắt kết nối"""
        if not self.is_connected:
            return
        
        try:
            if isinstance(self.connection, serial.Serial):
                self.connection.close()
            elif hasattr(self.connection, 'close'):
                self.connection.close()
            
            self.is_connected = False
            logger.info("Disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    def __del__(self):
        """Destructor"""
        self.disconnect()


def main():
    """Test serial communication"""
    print("Testing Serial Communication...")
    
    comm = SerialCommunication()
    
    # Note: This will fail on Windows unless you have a serial device
    if comm.connect():
        print("Connected successfully")
        
        # Read some telemetry
        for i in range(10):
            telemetry = comm.read_telemetry()
            if telemetry:
                print(f"Telemetry: {telemetry}")
            time.sleep(0.1)
        
        comm.disconnect()
    else:
        print("Failed to connect - this is normal on Windows without hardware")
        print("Deploy to Raspberry Pi to test with actual Flight Controller")


if __name__ == "__main__":
    main()
