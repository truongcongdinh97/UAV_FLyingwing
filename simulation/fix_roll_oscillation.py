import time
from pymavlink import mavutil

# Connection string
CONNECTION_STRING = "tcp:127.0.0.1:5762"

def fix_roll_oscillation():
    print(f"Connecting to SITL at {CONNECTION_STRING}...")
    try:
        master = mavutil.mavlink_connection(CONNECTION_STRING)
        master.wait_heartbeat(timeout=5)
        print("Connected to SITL!")

        # Fix Roll Oscillation (Wing Rock)
        params = {
            "RLL_RATE_P": 0.1,      # Drastically reduce Roll P Gain (was 0.25) - Main culprit
            "RLL_RATE_I": 0.1,      # Reduce I term to prevent wind-up
            "RLL_RATE_D": 0.005,    # Reduce D term to reduce noise
            "NAVL1_PERIOD": 22,     # Relax navigation (smoother path)
            "LIM_ROLL_CD": 4500     # Limit max roll angle to 45 degrees (safety)
        }

        for param_name, value in params.items():
            print(f"Setting {param_name} to {value}...")
            master.mav.param_set_send(
                master.target_system,
                master.target_component,
                param_name.encode('utf-8'),
                value,
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32
            )
            time.sleep(0.1)

        print("\nRoll fix parameters sent!")
        print("The plane should stop rocking side-to-side now.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_roll_oscillation()
