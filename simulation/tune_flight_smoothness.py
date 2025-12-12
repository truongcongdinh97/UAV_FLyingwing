import time
from pymavlink import mavutil

# Connection string
CONNECTION_STRING = "tcp:127.0.0.1:5762"

def tune_smoothness():
    print(f"Connecting to SITL at {CONNECTION_STRING}...")
    try:
        master = mavutil.mavlink_connection(CONNECTION_STRING)
        master.wait_heartbeat(timeout=5)
        print("Connected to SITL!")

        # Parameters for smoother flight
        params = {
            "NAVL1_PERIOD": 20,     # Slower navigation response (smoother turns)
            "NAVL1_DAMPING": 0.8,   # Higher damping for navigation
            "RLL_RATE_P": 0.2,      # Reduce Roll P gain
            "PTCH_RATE_P": 0.1      # Reduce Pitch P gain
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

        print("\nSmoothness parameters sent!")
        print("The flight path should look much better now.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    tune_smoothness()
