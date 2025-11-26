
import math

class RedesignCalculator:
    def __init__(self):
        # Fixed Parameters
        self.battery_weight = 1.2  # 6S2P
        self.payload = 3.75
        self.electronics_weight = 0.8 # Motors, ESC, FC, Pi, etc (approx from previous)
        
        # Variable Parameters (Estimates for 1.4m span)
        self.span = 1.4 # m
        self.frame_weight_est = 1.5 # Increased from 1.0kg for 0.9m span
        
        self.total_weight = self.battery_weight + self.payload + self.electronics_weight + self.frame_weight_est
        
        # Aerodynamics
        self.rho = 1.225
        self.cl_max = 1.2 # Airfoil max lift
        self.cd0 = 0.02 # Parasitic drag (cleaner shape)
        self.e = 0.8 # Oswald efficiency (better aspect ratio)
        
        # Motor
        self.kv = 600
        self.voltage = 22.2
        
    def calculate_optimal_wing_area(self):
        # Goal: Manageable Stall Speed (e.g., 45 km/h = 12.5 m/s)
        # W = 0.5 * rho * V^2 * S * CL_max
        # S = 2W / (rho * V^2 * CL_max)
        
        weight_n = self.total_weight * 9.81
        v_stall_target = 12.5 # m/s
        
        s_stall_limited = (2 * weight_n) / (self.rho * (v_stall_target**2) * self.cl_max)
        
        # Goal: Max Efficiency at Cruise (65 km/h = 18 m/s)
        # Max L/D condition: CD0 = CDi
        # CD0 = CL^2 / (pi * AR * e)
        # CL_opt = sqrt(CD0 * pi * AR * e)
        # Also CL_cruise = 2W / (rho * V^2 * S)
        # So 2W / (rho * V^2 * S) = sqrt(CD0 * pi * (b^2/S) * e)
        # Solve for S
        
        v_cruise = 18.0 # m/s
        # (2W / (rho * V^2))^2 * (1/S^2) = CD0 * pi * b^2 * e * (1/S)
        # (2W / (rho * V^2))^2 * (1/S) = CD0 * pi * b^2 * e
        # S_opt_cruise = (2W / (rho * V^2))^2 / (CD0 * pi * b^2 * e)
        
        term1 = (2 * weight_n) / (self.rho * v_cruise**2)
        s_opt_cruise = (term1**2) / (self.cd0 * math.pi * self.span**2 * self.e)
        
        return {
            'weight_kg': self.total_weight,
            's_stall_limited': s_stall_limited,
            's_opt_cruise': s_opt_cruise,
            'stall_speed_at_opt': math.sqrt((2*weight_n)/(self.rho * s_opt_cruise * self.cl_max)) * 3.6
        }

    def analyze_propeller(self):
        # 600KV, 6S (22.2V)
        rpm_noload = self.kv * self.voltage
        rpm_loaded = rpm_noload * 0.85 # Approx
        
        # Propeller selection guide (Empirical)
        # For 600KV 6S, typically 11x7, 12x6, 13x4
        # We need enough thrust for T/W > 0.5
        target_thrust = self.total_weight * 0.5 * 9.81 # Newtons
        target_thrust_per_motor = target_thrust / 2
        
        # Simplified Thrust Formula: T (N) approx = C_t * rho * n^2 * D^4
        # This is hard to estimate without specific prop data.
        # Using rule of thumb: 
        # 12x6 prop at 10,000 RPM -> ~2kg thrust
        
        return {
            'rpm_max': rpm_noload,
            'rpm_loaded': rpm_loaded,
            'recommended_size': "11x7 or 12x6"
        }

calc = RedesignCalculator()
res = calc.calculate_optimal_wing_area()
prop = calc.analyze_propeller()

print("=== REDESIGN ANALYSIS (1.4m Span) ===")
print(f"Total Weight Est: {res['weight_kg']:.2f} kg")
print(f"1. Optimal Wing Area for Cruise Efficiency: {res['s_opt_cruise']:.3f} m2")
print(f"   -> Stall Speed at this area: {res['stall_speed_at_opt']:.1f} km/h")
print(f"2. Wing Area for 45km/h Stall Speed: {res['s_stall_limited']:.3f} m2")
print("-" * 30)
print("RECOMMENDATION:")
recommended_area = max(res['s_opt_cruise'], res['s_stall_limited'])
print(f"Selected Wing Area: {recommended_area:.3f} m2")
ar = calc.span**2 / recommended_area
print(f"Resulting Aspect Ratio: {ar:.2f}")
wing_loading = res['weight_kg'] / recommended_area
print(f"Wing Loading: {wing_loading:.1f} kg/m2")

print("\n=== PROPELLER ===")
print(f"Motor: 600KV on 6S")
print(f"Max RPM: {prop['rpm_max']:.0f}")
print(f"Recommended Prop Size: {prop['recommended_size']}")
print("Note: With 1.4m span, you can fit up to 13 inch props easily.")
