import time
from pymavlink import mavutil

# Connection string
CONNECTION_STRING = "tcp:127.0.0.1:5762"

def stop_weaving():
    print(f"Connecting to SITL at {CONNECTION_STRING}...")
    try:
        master = mavutil.mavlink_connection(CONNECTION_STRING)
        master.wait_heartbeat(timeout=5)
        print("Connected to SITL!")

        # Stronger fix for "Shuriken" pattern (S-turning/Weaving)
        params = {
            "NAVL1_PERIOD": 30,     # Much slower navigation (was 22). Prevents tight turns.
            "NAVL1_DAMPING": 0.9,   # High damping to stop overshooting the path.
            "RLL_RATE_P": 0.08,     # Further reduce Roll P to stop aggressive banking.
            "RLL_RATE_I": 0.05,     # Reduce I term to prevent "wind-up" overshoots.
            "PTCH_RATE_P": 0.08,    # Keep pitch gentle.
            "LIM_ROLL_CD": 4000,    # Hard limit roll to 40 degrees (4000 centi-degrees).
            "RUDD_DT_GAIN": 0.05    # Minimal yaw authority to prevent fighting the turn.
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

        print("\nAnti-weaving parameters sent!")
        print("The plane should now fly a smooth, wide circle.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    stop_weaving()
