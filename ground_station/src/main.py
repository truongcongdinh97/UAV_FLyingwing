"""
Ground Control Station - Main Entry Point
Simple terminal-based GCS for testing
"""

import sys
import time
import os
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from communication.mavlink_client import MAVLinkClient
from communication.video_receiver import VideoReceiver


class GroundControlStation:
    """Simple terminal-based Ground Control Station"""
    
    def __init__(self, host: str = "192.168.1.100"):
        self.host = host
        self.mavlink = MAVLinkClient(host, 14550)
        self.video = VideoReceiver(f"rtsp://{host}:8554/video")
        
        self.running = False
    
    def connect(self) -> bool:
        """Connect to UAV"""
        logger.info("=== Ground Control Station ===")
        logger.info(f"Connecting to UAV at {self.host}...")
        
        # Connect MAVLink
        if not self.mavlink.connect(timeout=10):
            logger.error("MAVLink connection failed")
            return False
        
        logger.success("MAVLink connected")
        
        # Connect video (optional)
        logger.info("Connecting video stream...")
        if self.video.connect(timeout=5):
            logger.success("Video connected")
        else:
            logger.warning("Video connection failed (continuing without video)")
        
        return True
    
    def disconnect(self):
        """Disconnect from UAV"""
        logger.info("Disconnecting...")
        self.mavlink.disconnect()
        self.video.disconnect()
        logger.info("Disconnected")
    
    def run(self):
        """Main loop"""
        self.running = True
        
        logger.info("\n=== Commands ===")
        logger.info("a - Arm")
        logger.info("d - Disarm")
        logger.info("t - Takeoff (50m)")
        logger.info("l - Land")
        logger.info("r - Return to Launch")
        logger.info("s - Status")
        logger.info("q - Quit")
        logger.info("================\n")
        
        try:
            while self.running:
                # Print status every 2 seconds
                self.print_status()
                time.sleep(2)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.disconnect()
    
    def print_status(self):
        """Print telemetry status"""
        logger.info("=== Status ===")
        
        # Heartbeat
        if self.mavlink.is_heartbeat_active():
            logger.info("✓ Heartbeat OK")
        else:
            logger.warning("✗ No heartbeat")
        
        # GPS
        gps = self.mavlink.get_gps()
        if gps:
            logger.info(f"GPS: {gps['lat']:.6f}, {gps['lon']:.6f}, Alt: {gps['alt']:.1f}m")
        else:
            logger.info("GPS: No data")
        
        # Attitude
        attitude = self.mavlink.get_attitude()
        if attitude:
            logger.info(f"Attitude: Roll: {attitude['roll']:.1f}°, Pitch: {attitude['pitch']:.1f}°, Yaw: {attitude['yaw']:.1f}°")
        
        # Battery
        battery = self.mavlink.get_battery()
        if battery:
            logger.info(f"Battery: {battery['voltage']:.2f}V, {battery['current']:.2f}A, {battery['remaining']}%")
        
        # VFR HUD
        vfr = self.mavlink.get_vfr_hud()
        if vfr:
            logger.info(f"Speed: {vfr['groundspeed']:.1f} m/s, Heading: {vfr['heading']}°, Throttle: {vfr['throttle']}%")
        
        # Video
        if self.video.connected:
            logger.info(f"Video: {self.video.get_fps():.1f} FPS")
        
        logger.info("==============\n")
    
    def handle_command(self, cmd: str):
        """Handle user command"""
        cmd = cmd.lower().strip()
        
        if cmd == 'a':
            self.mavlink.arm()
        elif cmd == 'd':
            self.mavlink.disarm()
        elif cmd == 't':
            self.mavlink.takeoff(50.0)
        elif cmd == 'l':
            self.mavlink.land()
        elif cmd == 'r':
            self.mavlink.return_to_launch()
        elif cmd == 's':
            self.print_status()
        elif cmd == 'q':
            self.running = False
        else:
            logger.warning(f"Unknown command: {cmd}")


def main():
    """Main entry point"""
    # Configure logger
    logger.remove()
    logger.add(sys.stdout, level="INFO")
    logger.add("logs/gcs_{time}.log", level="DEBUG", rotation="10 MB")
    
    # Parse command line
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.100"
    
    # Create GCS
    gcs = GroundControlStation(host)
    
    # Connect
    if gcs.connect():
        # Run
        gcs.run()
    else:
        logger.error("Failed to connect")
        sys.exit(1)


if __name__ == "__main__":
    main()
