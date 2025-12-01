import time
from pymavlink import mavutil

# Connection string
CONNECTION_STRING = "tcp:127.0.0.1:5762"

def tune_balanced():
    print(f"Connecting to SITL at {CONNECTION_STRING}...")
    try:
        master = mavutil.mavlink_connection(CONNECTION_STRING)
        master.wait_heartbeat(timeout=5)
        print("Connected to SITL!")

        # Balanced Parameters (Accuracy vs Smoothness)
        params = {
            "NAVL1_PERIOD": 15,     # Faster response (was 20, default is often 20-25 but for small wings 15 is tighter)
            "NAVL1_DAMPING": 0.8,   # Keep high damping to prevent weaving
            "RLL_RATE_P": 0.25,     # Increase Roll authority slightly (was 0.2)
            "PTCH_RATE_P": 0.15,    # Restore some Pitch authority (was 0.1)
            "RUDD_DT_GAIN": 0.1     # Keep Yaw gain low (Critical for stability)
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

        print("\nBalanced parameters sent!")
        print("The plane should track the yellow line better now.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    tune_balanced()
