import time
from pymavlink import mavutil

# Connection string
CONNECTION_STRING = "tcp:127.0.0.1:5762"

def tune_stability():
    print(f"Connecting to SITL at {CONNECTION_STRING}...")
    try:
        master = mavutil.mavlink_connection(CONNECTION_STRING)
        master.wait_heartbeat(timeout=5)
        print("Connected to SITL!")

        # Stability Parameters for Flying Wing
        params = {
            "YAW2SRV_DAMP": 0.2,    # Re-enable Yaw Damping (gently) to stop wobbling
            "YAW2SRV_SLIP": 1.5,    # Enable Sideslip control (helps coordinate turns)
            "YAW2SRV_INT": 0.1,     # Allow small integrator to fix heading drift
            "RUDD_DT_GAIN": 0.2     # Slightly increase authority for the damper to work
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

        print("\nStability parameters sent!")
        print("The plane should feel more 'locked in' (đầm hơn) now.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    tune_stability()
