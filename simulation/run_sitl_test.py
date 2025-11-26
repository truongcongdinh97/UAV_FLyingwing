"""
SITL Test Runner for Flying Wing UAV
Kết nối code Companion Computer với ArduPilot SITL (Simulation)
"""

import sys
import os
import time
import threading
import argparse
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'companion_computer', 'src'))

from communication.mavlink_handler import MAVLinkHandler
from safety.geofencing import GeofencingSystem, GeoPoint

class SITLRunner:
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.mav = MAVLinkHandler(port=connection_string)
        self.running = False
        
    def start(self):
        logger.info(f"Connecting to SITL at {self.connection_string}...")
        if not self.mav.connect():
            logger.error("Failed to connect to SITL. Make sure ArduPilot SITL is running.")
            return
            
        self.running = True
        logger.success("Connected to SITL!")
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        try:
            while self.running:
                cmd = input("\nCommands: [status, arm, takeoff, mode <mode>, quit] > ")
                self._handle_command(cmd)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _monitor_loop(self):
        """Monitor telemetry from SITL"""
        while self.running:
            if self.mav.is_connected:
                att = self.mav.get_attitude()
                gps = self.mav.get_gps()
                bat = self.mav.get_battery()
                
                status_str = "STATUS: "
                if att: status_str += f"Roll={att['roll']:.1f} Pitch={att['pitch']:.1f} "
                if gps: status_str += f"Alt={gps['alt']:.1f}m "
                if bat: status_str += f"Bat={bat['voltage']:.1f}V"
                
                # Print status on same line (simple dashboard)
                # sys.stdout.write(f"\r{status_str}")
                # sys.stdout.flush()
            
            time.sleep(1)

    def _handle_command(self, cmd):
        parts = cmd.strip().split()
        if not parts: return
        
        action = parts[0].lower()
        
        if action == 'quit':
            self.running = False
            
        elif action == 'status':
            logger.info(f"GPS: {self.mav.get_gps()}")
            logger.info(f"Attitude: {self.mav.get_attitude()}")
            logger.info(f"Battery: {self.mav.get_battery()}")
            
        elif action == 'arm':
            logger.info("Arming motors...")
            self.mav.send_arm()
            
        elif action == 'takeoff':
            alt = float(parts[1]) if len(parts) > 1 else 50
            logger.info(f"Taking off to {alt}m...")
            
            # For ArduPlane, switching to TAKEOFF mode is often more reliable
            logger.info("Attempting to switch to TAKEOFF mode...")
            self.mav.set_mode('TAKEOFF')
            
            # Also send the command as backup (for Copter or Guided mode)
            # self.mav.send_takeoff(alt)
            
        elif action == 'mode':
            if len(parts) > 1:
                mode = parts[1].upper()
                logger.info(f"Switching to mode {mode}...")
                self.mav.set_mode(mode)

    def stop(self):
        self.running = False
        self.mav.disconnect()
        logger.info("Disconnected")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SITL Test Runner")
    parser.add_argument("--connect", default="tcp:127.0.0.1:5762", help="Connection string (e.g., tcp:127.0.0.1:5760)")
    args = parser.parse_args()
    
    runner = SITLRunner(args.connect)
    runner.start()
