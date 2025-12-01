import time
from pymavlink import mavutil

# Connection string
CONNECTION_STRING = "tcp:127.0.0.1:5762"

def fix_accel_calibration():
    print(f"Connecting to SITL at {CONNECTION_STRING}...")
    try:
        master = mavutil.mavlink_connection(CONNECTION_STRING)
        master.wait_heartbeat(timeout=5)
        print("Connected to SITL!")

        print("Resetting Accelerometer Calibration to Perfect SITL defaults...")
        
        # List of parameters to reset calibration
        # Offsets -> 0, Scaling -> 1
        params = [
            "INS_ACCOFFS_X", "INS_ACCOFFS_Y", "INS_ACCOFFS_Z",
            "INS_ACC2OFFS_X", "INS_ACC2OFFS_Y", "INS_ACC2OFFS_Z",
            "INS_ACC3OFFS_X", "INS_ACC3OFFS_Y", "INS_ACC3OFFS_Z",
        ]
        
        scales = [
            "INS_ACCSCAL_X", "INS_ACCSCAL_Y", "INS_ACCSCAL_Z",
            "INS_ACC2SCAL_X", "INS_ACC2SCAL_Y", "INS_ACC2SCAL_Z",
            "INS_ACC3SCAL_X", "INS_ACC3SCAL_Y", "INS_ACC3SCAL_Z",
        ]

        # Set Offsets to 0
        for param in params:
            master.mav.param_set_send(
                master.target_system,
                master.target_component,
                param.encode('utf-8'),
                0.0,
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32
            )
            time.sleep(0.05)

        # Set Scales to 1
        for param in scales:
            master.mav.param_set_send(
                master.target_system,
                master.target_component,
                param.encode('utf-8'),
                1.0,
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32
            )
            time.sleep(0.05)

        print("Calibration reset sent!")
        
        # Reboot to apply changes
        print("Sending Reboot command to apply fixes...")
        master.mav.command_long_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN,
            0,
            1, 0, 0, 0, 0, 0, 0
        )
        print("SITL is rebooting. Please wait 10 seconds before reconnecting.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_accel_calibration()
