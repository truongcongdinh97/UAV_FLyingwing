"""
Flying Wing UAV - Aerodynamics Calculator
Tính toán các thông số khí động học cho thiết kế UAV cánh bay động cơ kép

Author: Flying Wing UAV Team
Date: 2025-11-22
"""

import math
import json
import os
from typing import Dict, Tuple


class AerodynamicsCalculator:
    """Tính toán các thông số khí động học cho Flying Wing UAV"""
    
    def __init__(self):
        # Thông số thiết kế mục tiêu
        self.target_flight_time = 27.5  # minutes (giữa 25-30)
        self.target_speed = 65  # km/h (giữa 50-80)
        self.target_payload = 3.75  # kg (giữa 3.5-4.0)
        
        # Thông số vật lý ( theo file thiết kế)
        self.wing_area = 0.162  # m² ( CAD)
        self.wing_span = 0.9  # m (CAD)
        self.chord_length = 0.18  # m (chord trung bình)
        
        # Hằng số
        self.air_density = 1.225  # kg/m³
        self.gravity = 9.81  # m/s²
        
        # Hệ số khí động (ước tính cho flying wing)
        self.cl_max = 1.2  # Coefficient of lift tối đa
        self.cl_cruise = 0.6  # Coefficient of lift khi bay
        self.cd_0 = 0.025  # Drag coefficient parasitic
        self.oswald_efficiency = 0.75  # Oswald efficiency factor
        
        # Thông số động cơ
        self.motor_specs = {
            'model': 'DXW D4250 800KV',
            'kv': 800,  # RPM per volt
            'max_power': 550,  # watts (ước tính)
            'quantity': 2,
            'voltage_4s': 14.8,  # V (4S nominal)
            'propeller_diameter': 0.254,  # m (10 inch - ước tính)
            'propeller_pitch': 0.127,  # m (5 inch - ước tính)
        }
        
        # Thông số pin
        self.battery_specs = {
            'configuration': '4S2P',
            'voltage_nominal': 14.8,  # V
            'voltage_max': 16.8,  # V (4S fully charged)
            'voltage_min': 13.2,  # V (4S cutoff)
            'capacity': 10400,  # mAh (2x 5200mAh)
            'discharge_rate': 65,  # C rating
            'weight': 0.800,  # kg (estimate for 2x 5200mAh 4S)
        }
        
        # Khối lượng các component (từ BOM)
        self.component_weights = self._get_component_weights()
        
    def _get_component_weights(self) -> Dict[str, float]:
        """Ước tính khối lượng các component từ BOM (kg)"""
        return {
            'flight_controller': 0.025,  # LANRC F4 V3S
            'gps_module': 0.020,  # Beitian BN-220
            'compass': 0.005,  # HMC5883
            'distance_sensor': 0.010,  # VL53L1X
            'receiver': 0.005,  # Radiomaster XR1 Nano
            'esp32_cam': 0.010,  # ESP32-CAM với accessories
            'imu_gy9250': 0.005,
            'sd_card': 0.002,
            'wifi_module': 0.050,  # 5G Hotspot với pin độc lập
            'ultrasonic': 0.015,  # HC-SR04
            'raspberry_pi': 0.045,  # Raspberry Pi 3B+
            'camera_ov5647': 0.003,  # Pi Camera
            'motors': 0.180,  # 2x D4250 (~90g each)
            'esc': 0.100,  # 2x ESC 50A (~50g each)
            'servos': 0.110,  # 2x MG996R (~55g each)
            'propellers': 0.040,  # 2x props (estimate)
            'battery': 0.800,  # 2x 5200mAh 4S
            'ubec': 0.020,  # Hobbywing 3A UBEC
            'buck_converters': 0.010,  # 2x Mini-360
            'wiring': 0.100,  # Dây điện, connectors
            'frame_3d_printed': 0.600,  # Khung máy bay in 3D (estimate)
            'carbon_rods': 0.150,  # Thanh carbon
            'glue_fasteners': 0.050,  # Keo, vít
        }
    
    def calculate_total_weight(self) -> Dict[str, float]:
        """Tính tổng khối lượng UAV"""
        total_components = sum(self.component_weights.values())
        total_with_payload = total_components + self.target_payload
        
        return {
            'components_weight_kg': total_components,
            'payload_weight_kg': self.target_payload,
            'total_weight_kg': total_with_payload,
            'total_weight_g': total_with_payload * 1000,
        }
    
    def calculate_wing_loading(self) -> Dict[str, float]:
        """Tính Wing Loading (W/S)"""
        weights = self.calculate_total_weight()
        total_weight_n = weights['total_weight_kg'] * self.gravity
        
        wing_loading = total_weight_n / self.wing_area
        wing_loading_kg_m2 = weights['total_weight_kg'] / self.wing_area
        
        return {
            'wing_loading_n_m2': wing_loading,
            'wing_loading_kg_m2': wing_loading_kg_m2,
            'wing_area_m2': self.wing_area,
            'total_weight_kg': weights['total_weight_kg'],
        }
    
    def calculate_stall_speed(self) -> Dict[str, float]:
        """Tính tốc độ thất tốc (stall speed)"""
        weights = self.calculate_total_weight()
        weight_n = weights['total_weight_kg'] * self.gravity
        
        # V_stall = sqrt(2 * W / (ρ * S * CL_max))
        v_stall_ms = math.sqrt(
            (2 * weight_n) / (self.air_density * self.wing_area * self.cl_max)
        )
        v_stall_kmh = v_stall_ms * 3.6
        
        # Tốc độ bay an toàn = 1.3 * V_stall
        v_safe_ms = v_stall_ms * 1.3
        v_safe_kmh = v_safe_ms * 3.6
        
        return {
            'stall_speed_ms': v_stall_ms,
            'stall_speed_kmh': v_stall_kmh,
            'safe_cruise_speed_ms': v_safe_ms,
            'safe_cruise_speed_kmh': v_safe_kmh,
        }
    
    def calculate_thrust_to_weight_ratio(self) -> Dict[str, float]:
        """Tính tỷ lệ lực đẩy/trọng lượng"""
        weights = self.calculate_total_weight()
        weight_n = weights['total_weight_kg'] * self.gravity
        
        # Ước tính thrust (cần test thực tế)
        # Giả định motor efficiency ~70%, prop efficiency ~50%
        total_motor_power = self.motor_specs['max_power'] * self.motor_specs['quantity']
        available_power = total_motor_power * 0.7 * 0.5  # watts mechanical
        
        # Static thrust estimate (very rough)
        # P = F * v, assuming v = 10 m/s for initial estimate
        estimated_thrust_n = available_power / 10
        
        twr = estimated_thrust_n / weight_n
        
        return {
            'estimated_thrust_n': estimated_thrust_n,
            'estimated_thrust_kgf': estimated_thrust_n / self.gravity,
            'weight_n': weight_n,
            'weight_kg': weights['total_weight_kg'],
            'thrust_to_weight_ratio': twr,
            'is_adequate': twr >= 0.5,  # Flying wing cần ít nhất 0.5
        }
    
    def calculate_lift_to_drag_ratio(self, speed_ms: float) -> float:
        """Tính tỷ lệ lift/drag ở tốc độ nhất định"""
        aspect_ratio = self.wing_span ** 2 / self.wing_area
        
        # Induced drag coefficient
        cd_i = self.cl_cruise ** 2 / (math.pi * aspect_ratio * self.oswald_efficiency)
        
        # Total drag coefficient
        cd_total = self.cd_0 + cd_i
        
        # L/D ratio
        ld_ratio = self.cl_cruise / cd_total
        
        return ld_ratio
    
    def calculate_power_required(self, speed_ms: float) -> float:
        """Tính công suất cần thiết để duy trì tốc độ (watts)"""
        weights = self.calculate_total_weight()
        weight_n = weights['total_weight_kg'] * self.gravity
        
        # Calculate drag
        aspect_ratio = self.wing_span ** 2 / self.wing_area
        cd_i = self.cl_cruise ** 2 / (math.pi * aspect_ratio * self.oswald_efficiency)
        cd_total = self.cd_0 + cd_i
        
        # Drag force: D = 0.5 * ρ * V² * S * CD
        drag_n = 0.5 * self.air_density * (speed_ms ** 2) * self.wing_area * cd_total
        
        # Power = Drag * Velocity
        power_required = drag_n * speed_ms
        
        # Account for propeller efficiency (~50%) and motor efficiency (~85%)
        total_efficiency = 0.50 * 0.85
        power_from_battery = power_required / total_efficiency
        
        return power_from_battery
    
    def estimate_flight_time(self) -> Dict[str, float]:
        """Ước tính thời gian bay"""
        cruise_speed_ms = self.target_speed / 3.6  # Convert km/h to m/s
        
        # Công suất tiêu thụ
        power_watts = self.calculate_power_required(cruise_speed_ms)
        current_amps = power_watts / self.battery_specs['voltage_nominal']
        
        # Dung lượng pin khả dụng (80% để an toàn)
        usable_capacity_ah = (self.battery_specs['capacity'] * 0.8) / 1000
        
        # Thời gian bay
        flight_time_hours = usable_capacity_ah / current_amps
        flight_time_minutes = flight_time_hours * 60
        
        # Quãng đường
        range_km = (cruise_speed_ms * 3.6) * flight_time_hours
        
        return {
            'power_required_watts': power_watts,
            'current_draw_amps': current_amps,
            'battery_capacity_mah': self.battery_specs['capacity'],
            'usable_capacity_mah': self.battery_specs['capacity'] * 0.8,
            'flight_time_minutes': flight_time_minutes,
            'flight_time_hours': flight_time_hours,
            'cruise_speed_kmh': self.target_speed,
            'estimated_range_km': range_km,
            'meets_target': flight_time_minutes >= 25,
        }
    
    def generate_performance_report(self) -> Dict:
        """Tạo báo cáo hiệu suất tổng hợp"""
        weights = self.calculate_total_weight()
        wing_loading = self.calculate_wing_loading()
        stall_speed = self.calculate_stall_speed()
        twr = self.calculate_thrust_to_weight_ratio()
        flight_time = self.estimate_flight_time()
        ld_ratio = self.calculate_lift_to_drag_ratio(self.target_speed / 3.6)
        
        report = {
            'design_parameters': {
                'target_flight_time_min': self.target_flight_time,
                'target_speed_kmh': self.target_speed,
                'target_payload_kg': self.target_payload,
                'wing_area_m2': self.wing_area,
                'wing_span_m': self.wing_span,
            },
            'weight_analysis': weights,
            'wing_loading': wing_loading,
            'stall_speed': stall_speed,
            'thrust_to_weight': twr,
            'flight_performance': flight_time,
            'lift_to_drag_ratio': ld_ratio,
        }
        
        return report
    
    def print_report(self):
        """In báo cáo ra console"""
        report = self.generate_performance_report()
        
        print("=" * 70)
        print(" FLYING WING UAV - AERODYNAMICS ANALYSIS REPORT")
        print("=" * 70)
        
        print("\n📐 THÔNG SỐ THIẾT KẾ:")
        print(f"  Thời gian bay mục tiêu: {report['design_parameters']['target_flight_time_min']:.1f} phút")
        print(f"  Tốc độ mục tiêu: {report['design_parameters']['target_speed_kmh']:.1f} km/h")
        print(f"  Tải trọng: {report['design_parameters']['target_payload_kg']:.2f} kg")
        print(f"  Diện tích cánh: {report['design_parameters']['wing_area_m2']:.2f} m²")
        print(f"  Sải cánh: {report['design_parameters']['wing_span_m']:.2f} m")
        
        print("\n⚖️  PHÂN TÍCH KHỐI LƯỢNG:")
        print(f"  Khối lượng components: {report['weight_analysis']['components_weight_kg']:.3f} kg")
        print(f"  Khối lượng payload: {report['weight_analysis']['payload_weight_kg']:.3f} kg")
        print(f"  Tổng khối lượng: {report['weight_analysis']['total_weight_kg']:.3f} kg ({report['weight_analysis']['total_weight_g']:.0f} g)")
        
        print("\n🪽 WING LOADING:")
        print(f"  Wing Loading: {report['wing_loading']['wing_loading_kg_m2']:.2f} kg/m²")
        print(f"  (Lý tưởng cho flying wing: 15-25 kg/m²)")
        
        print("\n🚁 TỐC ĐỘ THẤT TỐC:")
        print(f"  Stall Speed: {report['stall_speed']['stall_speed_kmh']:.1f} km/h")
        print(f"  Tốc độ bay an toàn tối thiểu: {report['stall_speed']['safe_cruise_speed_kmh']:.1f} km/h")
        
        print("\n⚡ LỰC ĐẨY / TRỌNG LƯỢNG:")
        print(f"  Lực đẩy ước tính: {report['thrust_to_weight']['estimated_thrust_kgf']:.2f} kgf")
        print(f"  Trọng lượng: {report['thrust_to_weight']['weight_kg']:.3f} kg")
        print(f"  T/W Ratio: {report['thrust_to_weight']['thrust_to_weight_ratio']:.2f}")
        status = "✅ ĐỦ" if report['thrust_to_weight']['is_adequate'] else "❌ KHÔNG ĐỦ"
        print(f"  Đánh giá: {status} (cần >= 0.5 cho flying wing)")
        
        print("\n✈️  HIỆU SUẤT BAY:")
        print(f"  Công suất tiêu thụ: {report['flight_performance']['power_required_watts']:.1f} W")
        print(f"  Dòng điện: {report['flight_performance']['current_draw_amps']:.2f} A")
        print(f"  Thời gian bay ước tính: {report['flight_performance']['flight_time_minutes']:.1f} phút")
        print(f"  Quãng đường ước tính: {report['flight_performance']['estimated_range_km']:.1f} km")
        status = "✅ ĐẠT" if report['flight_performance']['meets_target'] else "❌ CHƯA ĐẠT"
        print(f"  Đánh giá: {status} mục tiêu (>= 25 phút)")
        
        print(f"\n🎯 LIFT/DRAG RATIO: {report['lift_to_drag_ratio']:.1f}")
        print(f"  (Tốt cho flying wing: 10-15)")
        
        print("\n" + "=" * 70)
        print("=" * 70)
        
        return report


def main():
    """Main function"""
    calc = AerodynamicsCalculator()
    report = calc.print_report()
    
    # Save to JSON - use absolute path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, 'aerodynamics_report.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Báo cáo đã được lưu vào: {output_file}")


if __name__ == "__main__":
    main()
