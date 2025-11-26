import sys
import time
from pymavlink import mavutil

# Connection string (match your setup)
CONNECTION_STRING = "tcp:127.0.0.1:5762"

def reboot_sitl():
    print(f"Connecting to SITL at {CONNECTION_STRING}...")
    try:
        # Connect to the SITL
        master = mavutil.mavlink_connection(CONNECTION_STRING)
        master.wait_heartbeat(timeout=5)
        print("Connected to SITL!")

        # Send Reboot Command
        # MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN = 246
        # Param1 = 1 (Reboot autopilot)
        print("Sending Reboot command...")
        master.mav.command_long_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN,
            0,
            1, 0, 0, 0, 0, 0, 0
        )
        print("Reboot command sent! SITL should restart now.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reboot_sitl()
