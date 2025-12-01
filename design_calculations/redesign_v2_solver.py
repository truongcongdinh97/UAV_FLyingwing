
import math

class AdvancedRedesignCalculator:
    def __init__(self):
        # 1. Fixed Mass (Khối lượng không đổi)
        self.mass_fixed = {
            'battery': 1.2,      # 6S2P 10400mAh
            'payload': 3.75,     # Camera, Gimbal, Sensors
            'electronics': 0.8,  # Motors, ESC, FC, Pi, Wiring
        }
        self.total_fixed_mass = sum(self.mass_fixed.values()) # 5.75 kg

        # 2. Material Density (Mật độ vật liệu)
        # LW-PLA (Lightweight PLA) with 5-8% infill + Carbon spars
        self.wing_density = 1.5  # kg/m2 (Realistic for LW-PLA structure)
        
        # 3. Aerodynamics Constants
        self.rho = 1.225
        self.cl_max = 1.2       # Max Lift Coefficient (Airfoil dependent)
        self.cl_cruise = 0.5    # Target CL for cruise
        self.cd0 = 0.025        # Parasitic Drag
        self.e = 0.8            # Oswald Efficiency
        self.g = 9.81

        # 4. Constraints (UPDATED per user request)
        # Target Wing Loading: 80-90 g/dm2 -> 8.0 - 9.0 kg/m2
        self.target_wing_loading_g_dm2 = 85.0 
        self.target_wing_loading_kg_m2 = 8.5 
        
        # Aspect Ratio Constraints for 3D Printed Flying Wing
        self.min_aspect_ratio = 5.0
        self.max_aspect_ratio = 7.0
        
    def solve_for_span(self, span_candidates):
        print(f"{'SPAN (m)':<10} | {'AREA (m2)':<10} | {'AR':<6} | {'WEIGHT (kg)':<12} | {'WL (g/dm2)':<12} | {'STALL (km/h)':<12} | {'STATUS'}")
        print("-" * 95)

        best_solution = None

        # Calculate Required Area based on Wing Loading Target
        # S = W_fixed / (Wing_Loading_Target - density)
        if self.target_wing_loading_kg_m2 <= self.wing_density:
             print("Error: Target Wing Loading is lower than material density. Impossible.")
             return None

        required_area = self.total_fixed_mass / (self.target_wing_loading_kg_m2 - self.wing_density)
        total_weight = self.total_fixed_mass + required_area * self.wing_density
        actual_wl_g_dm2 = (total_weight / required_area) * 10 # Convert kg/m2 to g/dm2

        print(f"Target Wing Loading: {self.target_wing_loading_g_dm2} g/dm2 ({self.target_wing_loading_kg_m2} kg/m2)")
        print(f"Required Wing Area: {required_area:.3f} m2")
        print(f"Estimated Total Weight: {total_weight:.2f} kg")
        print("-" * 95)

        for b in span_candidates:
            # Calculate AR for this span with the required area
            ar = b**2 / required_area
            
            # Calculate Stall Speed
            # V_stall = sqrt( 2 * W / (rho * S * CL_max) )
            v_stall = math.sqrt((2 * total_weight * self.g) / (self.rho * required_area * self.cl_max)) * 3.6
            
            # Check AR Constraints
            status = "✅ Optimal"
            if ar < self.min_aspect_ratio:
                status = "❌ AR too low (Inefficient)"
            elif ar > self.max_aspect_ratio:
                status = "❌ AR too high (Structural Risk)"
            
            # Calculate L/D for reference
            cd = self.cd0 + (self.cl_cruise**2) / (math.pi * ar * self.e)
            ld_ratio = self.cl_cruise / cd

            print(f"{b:<10.1f} | {required_area:<10.3f} | {ar:<6.2f} | {total_weight:<12.2f} | {actual_wl_g_dm2:<12.1f} | {v_stall:<12.1f} | {status}")
            
            if "Optimal" in status:
                 if best_solution is None or ld_ratio > best_solution['ld']:
                    best_solution = {
                        'span': b,
                        'area': required_area,
                        'ar': ar,
                        'weight': total_weight,
                        'ld': ld_ratio,
                        'stall': v_stall
                    }

        return best_solution

calc = AdvancedRedesignCalculator()
print("=== ADVANCED AERODYNAMICS SOLVER (HEAVY LIFT CONFIG) ===")
print(f"Fixed Mass: {calc.total_fixed_mass} kg")
print(f"Wing Density: {calc.wing_density} kg/m2 (LW-PLA)")
print(f"Target Wing Loading: {calc.target_wing_loading_g_dm2} g/dm2")
print(f"Aspect Ratio Limit: {calc.min_aspect_ratio} - {calc.max_aspect_ratio}")
print("\nRunning Solver...")

spans = [1.8, 2.0, 2.2, 2.4, 2.5, 2.6]
best = calc.solve_for_span(spans)

if best:
    print("\n=== RECOMMENDATION ===")
    print(f"Optimal Span: {best['span']} m")
    print(f"Wing Area: {best['area']:.3f} m2")
    print(f"Aspect Ratio: {best['ar']:.2f}")
    print(f"Total Weight: {best['weight']:.2f} kg")
    print(f"Stall Speed: {best['stall']:.1f} km/h")
    print(f"Est. L/D Ratio: {best['ld']:.1f}")
    
    # Chord calculation
    avg_chord = best['area'] / best['span']
    print(f"Average Chord: {avg_chord*100:.1f} cm")
    
    # Propeller check
    print("\n=== PROPELLER CHECK ===")
    print("Motor: 600KV @ 6S (22.2V)")
    print("Recommended Prop: 12x6 or 13x4")
else:
    print("\n❌ No viable solution found within constraints.")
