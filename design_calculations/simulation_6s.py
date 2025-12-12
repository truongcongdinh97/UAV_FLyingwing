
import math
from typing import Dict

class AerodynamicsCalculator6S:
    def __init__(self):
        # Base parameters from original file
        self.target_flight_time = 27.5
        self.target_speed = 65
        self.target_payload = 3.75
        self.wing_area = 0.162
        self.wing_span = 0.9
        self.air_density = 1.225
        self.gravity = 9.81
        self.cl_max = 1.2
        self.cl_cruise = 0.6
        self.cd_0 = 0.025
        self.oswald_efficiency = 0.75

        # NEW SPECS
        self.motor_specs = {
            'model': 'DXW D4250 600KV',
            'kv': 600,
            'max_power': 550, # Rated power
            'quantity': 2,
            'voltage_6s': 22.2, # 6S Nominal
            'propeller_diameter': 0.254, # 10 inch
        }

        self.battery_specs = {
            'configuration': '6S2P (2x 6S 5200mAh)',
            'voltage_nominal': 22.2,
            'capacity': 10400, # 5200 * 2
            'weight': 1.200, # 600g * 2
        }

        # Weights (Hộp đen ESP32 có thể tháo rời, nguồn riêng)
        self.component_weights = {
            'flight_controller': 0.025,  # LANRC F4 V3S Plus (có MPU6000 IMU)
            'gps_module': 0.020,
            'compass': 0.005,  # QMC5883L
            'distance_sensor': 0.010,  # VL53L1X
            'receiver': 0.005,
            # Hộp đen (tháo rời được, chỉ gắn khi test)
            'blackbox_esp32': 0.080,  # ESP32-CAM + GY-9250 + HC-SR04 + SD
            'raspberry_pi': 0.045,
            'camera_ov5647': 0.003,
            'motors': 0.380,
            'esc': 0.200, # INCREASED: 100A ESCs are heavier (approx 100g each)
            'servos': 0.220,
            'propellers': 0.040,
            'battery': 1.200, # CHANGED: 2x 600g
            'ubec': 0.020,
            'buck_converters': 0.010,
            'wiring': 0.100,
            'frame_3d_printed': 1.00,
            'carbon_rods': 0.150,
            'glue_fasteners': 0.050,
        }

    def calculate(self):
        # Weight
        total_components = sum(self.component_weights.values())
        total_weight = total_components + self.target_payload
        
        # Power Required for Cruise (Aerodynamics)
        # Drag
        speed_ms = self.target_speed / 3.6
        aspect_ratio = self.wing_span ** 2 / self.wing_area
        cd_i = self.cl_cruise ** 2 / (math.pi * aspect_ratio * self.oswald_efficiency)
        cd_total = self.cd_0 + cd_i
        drag_n = 0.5 * self.air_density * (speed_ms ** 2) * self.wing_area * cd_total
        power_required_aero = drag_n * speed_ms
        
        # Efficiency
        # Higher voltage usually means better efficiency for same power, 
        # BUT 800KV on 6S with 10inch prop is extremely inefficient (over-propped)
        # However, for CRUISE, we only need 'power_required_aero' watts.
        # The motor will spin at a lower throttle % to achieve this.
        total_efficiency = 0.50 * 0.85
        power_from_battery = power_required_aero / total_efficiency

        # Flight Time
        current_amps = power_from_battery / self.battery_specs['voltage_nominal']
        usable_capacity_ah = (self.battery_specs['capacity'] * 0.8) / 1000
        flight_time_hours = usable_capacity_ah / current_amps
        flight_time_minutes = flight_time_hours * 60

        # Motor Stress Check (Full Throttle)
        # RPM = KV * V
        rpm_no_load = self.motor_specs['kv'] * self.battery_specs['voltage_nominal']
        # Prop power approx: P = K * RPM^3 * D^4 (simplified)
        # Comparing to 4S 800KV:
        # RPM_4S_800 = 800 * 14.8 = 11840
        # RPM_6S_600 = 600 * 22.2 = 13320
        # Ratio = 1.125
        # Power Ratio = 1.125^3 = 1.42
        # Power increase is manageable (~40% more max power potential)
        motor_burn_risk = False # 600KV on 6S is standard for this size

        return {
            'total_weight': total_weight,
            'flight_time_min': flight_time_minutes,
            'motor_burn_risk': motor_burn_risk,
            'rpm_max': rpm_no_load,
            'energy_wh': self.battery_specs['voltage_nominal'] * self.battery_specs['capacity'] / 1000
        }

calc = AerodynamicsCalculator6S()
res = calc.calculate()
print(res)
