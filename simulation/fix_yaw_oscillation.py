import time
from pymavlink import mavutil

# Connection string
CONNECTION_STRING = "tcp:127.0.0.1:5762"

def fix_yaw_oscillation():
    print(f"Connecting to SITL at {CONNECTION_STRING}...")
    try:
        master = mavutil.mavlink_connection(CONNECTION_STRING)
        master.wait_heartbeat(timeout=5)
        print("Connected to SITL!")

        # List of parameters to fix Yaw Oscillation
        params = {
            "RUDD_DT_GAIN": 0.1,    # Drastically reduce Differential Thrust Gain (was 5 or 1)
            "KFF_RDDRMIX": 0.0,     # Disable Rudder Mix into Elevons
            "YAW2SRV_DAMP": 0.0,    # Disable Yaw Damper
            "YAW2SRV_INT": 0.0,     # Disable Yaw Integrator
            "RTL_ALTITUDE": 50,     # Set RTL Altitude to 50m
            "ACRO_YAW_RATE": 0      # Disable Acro Yaw Rate
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
            time.sleep(0.1) # Give it a moment

        print("\nAll parameters sent!")
        print("Please try taking off again.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_yaw_oscillation()
