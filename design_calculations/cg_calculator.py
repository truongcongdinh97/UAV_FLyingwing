"""
Flying Wing UAV - Center of Gravity (CG) Calculator
Tính toán vị trí Center of Gravity và phân bố khối lượng

Author: Flying Wing UAV Team
Date: 2025-11-22
"""

import math
import json
import os
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import numpy as np


class CGCalculator:
    """Tính toán Center of Gravity cho Flying Wing UAV"""
    
    def __init__(self):
        # Tham chiếu: Leading Edge của cánh (x=0, y=0, z=0)
        # x: Hướng về phía đuôi máy bay (positive = về sau)
        # y: Hướng ngang (positive = sang phải khi nhìn từ phía sau)
        # z: Hướng lên trên (positive = lên trên)
        
        # Thông số cánh (cần cập nhật từ CAD)
        self.wing_chord = 0.30  # m - chord trung bình
        self.wing_span = 1.50  # m
        self.wing_area = 0.45  # m²
        
        # CG lý tưởng cho flying wing: 25-30% MAC (Mean Aerodynamic Chord)
        self.cg_target_min = 0.25  # 25% MAC
        self.cg_target_max = 0.30  # 30% MAC
        
        # Components với vị trí ước tính (x, y, z) tính từ leading edge (m)
        # [x, y, z, weight_kg]
        self.components = self._define_component_positions()
        
    def _define_component_positions(self) -> Dict[str, Dict]:
        """
        Định nghĩa vị trí các component
        Vị trí cần được đo chính xác từ CAD model thực tế
        """
        components = {
            # Flight Electronics Bay (trung tâm, phía trước)
            'flight_controller': {
                'x': 0.12,  # 12cm từ leading edge
                'y': 0.00,  # Giữa máy bay
                'z': 0.05,
                'weight': 0.025,
                'description': 'LANRC F4 V3S Plus'
            },
            'gps_module': {
                'x': 0.08,
                'y': 0.00,
                'z': 0.08,  # Phía trên để tín hiệu tốt
                'weight': 0.020,
                'description': 'Beitian BN-220'
            },
            'compass': {
                'x': 0.10,
                'y': 0.00,
                'z': 0.07,
                'weight': 0.005,
                'description': 'HMC5883'
            },
            'receiver': {
                'x': 0.14,
                'y': 0.00,
                'z': 0.04,
                'weight': 0.005,
                'description': 'Radiomaster XR1 Nano'
            },
            
            # Sensor Bay
            'distance_sensor': {
                'x': 0.05,
                'y': 0.00,
                'z': -0.02,  # Dưới thân, hướng xuống
                'weight': 0.010,
                'description': 'VL53L1X'
            },
            'ultrasonic': {
                'x': 0.06,
                'y': 0.00,
                'z': -0.02,
                'weight': 0.015,
                'description': 'HC-SR04'
            },
            
            # ESP32 Data Logger
            'esp32_cam': {
                'x': 0.16,
                'y': 0.05,
                'z': 0.03,
                'weight': 0.010,
                'description': 'ESP32-CAM với SD card'
            },
            'imu_gy9250': {
                'x': 0.15,
                'y': 0.05,
                'z': 0.03,
                'weight': 0.005,
                'description': 'GY-9250 IMU'
            },
            
            # Raspberry Pi Companion Computer (trung tâm)
            'raspberry_pi': {
                'x': 0.18,
                'y': 0.00,
                'z': 0.04,
                'weight': 0.045,
                'description': 'Raspberry Pi 3B+'
            },
            'camera_ov5647': {
                'x': 0.10,
                'y': 0.00,
                'z': -0.03,  # Hướng xuống để quay
                'weight': 0.003,
                'description': 'OV5647 Camera'
            },
            
            # Communication Module
            'wifi_module': {
                'x': 0.20,
                'y': 0.00,
                'z': 0.06,
                'weight': 0.050,
                'description': '5G Hotspot module'
            },
            
            # Motor System - Left Motor (động cơ trái)
            'motor_left': {
                'x': 0.15,
                'y': -0.30,  # 30cm sang trái
                'z': 0.00,
                'weight': 0.090,
                'description': 'DXW D4250 800KV Left'
            },
            'esc_left': {
                'x': 0.18,
                'y': -0.28,
                'z': 0.00,
                'weight': 0.050,
                'description': 'ESC 50A Left'
            },
            'propeller_left': {
                'x': 0.10,
                'y': -0.30,
                'z': 0.00,
                'weight': 0.020,
                'description': 'Propeller Left'
            },
            
            # Motor System - Right Motor (động cơ phải)
            'motor_right': {
                'x': 0.15,
                'y': 0.30,  # 30cm sang phải
                'z': 0.00,
                'weight': 0.090,
                'description': 'DXW D4250 800KV Right'
            },
            'esc_right': {
                'x': 0.18,
                'y': 0.28,
                'z': 0.00,
                'weight': 0.050,
                'description': 'ESC 50A Right'
            },
            'propeller_right': {
                'x': 0.10,
                'y': 0.30,
                'z': 0.00,
                'weight': 0.020,
                'description': 'Propeller Right'
            },
            
            # Servos (Elevons)
            'servo_left': {
                'x': 0.25,
                'y': -0.40,
                'z': 0.00,
                'weight': 0.055,
                'description': 'MG996R Servo Left'
            },
            'servo_right': {
                'x': 0.25,
                'y': 0.40,
                'z': 0.00,
                'weight': 0.055,
                'description': 'MG996R Servo Right'
            },
            
            # Battery Pack (trung tâm, phía sau CG mục tiêu)
            'battery': {
                'x': 0.22,  # Có thể điều chỉnh để balance CG
                'y': 0.00,
                'z': -0.02,
                'weight': 0.800,
                'description': '4S2P 10400mAh'
            },
            
            # Power Distribution
            'ubec': {
                'x': 0.20,
                'y': 0.08,
                'z': 0.02,
                'weight': 0.020,
                'description': 'Hobbywing 3A UBEC'
            },
            'buck_converters': {
                'x': 0.19,
                'y': 0.08,
                'z': 0.02,
                'weight': 0.010,
                'description': '2x Mini-360'
            },
            
            # Structural (distributed)
            'frame_front': {
                'x': 0.10,
                'y': 0.00,
                'z': 0.00,
                'weight': 0.200,
                'description': 'Frame front section'
            },
            'frame_center': {
                'x': 0.20,
                'y': 0.00,
                'z': 0.00,
                'weight': 0.200,
                'description': 'Frame center section'
            },
            'frame_rear': {
                'x': 0.28,
                'y': 0.00,
                'z': 0.00,
                'weight': 0.200,
                'description': 'Frame rear section'
            },
            'carbon_rods': {
                'x': 0.15,
                'y': 0.00,
                'z': 0.00,
                'weight': 0.150,
                'description': 'Carbon reinforcement'
            },
            
            # Miscellaneous
            'wiring': {
                'x': 0.18,
                'y': 0.00,
                'z': 0.00,
                'weight': 0.100,
                'description': 'Wiring harness'
            },
            'fasteners': {
                'x': 0.18,
                'y': 0.00,
                'z': 0.00,
                'weight': 0.050,
                'description': 'Glue, fasteners'
            },
        }
        
        return components
    
    def calculate_cg(self, include_payload: bool = True, 
                     payload_position: Tuple[float, float, float] = (0.15, 0.00, 0.03),
                     payload_weight: float = 3.75) -> Dict:
        """
        Tính toán Center of Gravity
        
        Args:
            include_payload: Có tính payload không
            payload_position: Vị trí payload (x, y, z)
            payload_weight: Khối lượng payload (kg)
        """
        # Tính tổng moment và weight
        total_weight = 0
        moment_x = 0
        moment_y = 0
        moment_z = 0
        
        for name, comp in self.components.items():
            weight = comp['weight']
            total_weight += weight
            moment_x += comp['x'] * weight
            moment_y += comp['y'] * weight
            moment_z += comp['z'] * weight
        
        # Thêm payload nếu cần
        if include_payload:
            total_weight += payload_weight
            moment_x += payload_position[0] * payload_weight
            moment_y += payload_position[1] * payload_weight
            moment_z += payload_position[2] * payload_weight
        
        # Tính CG
        cg_x = moment_x / total_weight
        cg_y = moment_y / total_weight
        cg_z = moment_z / total_weight
        
        # Tính % MAC
        cg_percent_mac = (cg_x / self.wing_chord) * 100
        
        # Kiểm tra có trong phạm vi an toàn không
        is_safe = self.cg_target_min <= (cg_x / self.wing_chord) <= self.cg_target_max
        
        return {
            'cg_position': {
                'x': cg_x,
                'y': cg_y,
                'z': cg_z,
            },
            'cg_percent_mac': cg_percent_mac,
            'target_range_percent': [self.cg_target_min * 100, self.cg_target_max * 100],
            'is_safe': is_safe,
            'total_weight_kg': total_weight,
            'wing_chord_m': self.wing_chord,
        }
    
    def analyze_cg_range(self) -> Dict:
        """Phân tích phạm vi CG với các cấu hình khác nhau"""
        results = {}
        
        # 1. Without payload
        results['without_payload'] = self.calculate_cg(include_payload=False)
        
        # 2. With minimum payload
        results['min_payload'] = self.calculate_cg(
            include_payload=True,
            payload_weight=3.5
        )
        
        # 3. With target payload
        results['target_payload'] = self.calculate_cg(
            include_payload=True,
            payload_weight=3.75
        )
        
        # 4. With maximum payload
        results['max_payload'] = self.calculate_cg(
            include_payload=True,
            payload_weight=4.0
        )
        
        # 5. With payload moved forward
        results['payload_forward'] = self.calculate_cg(
            include_payload=True,
            payload_position=(0.10, 0.00, 0.03),
            payload_weight=3.75
        )
        
        # 6. With payload moved backward
        results['payload_backward'] = self.calculate_cg(
            include_payload=True,
            payload_position=(0.20, 0.00, 0.03),
            payload_weight=3.75
        )
        
        return results
    
    def calculate_moment_of_inertia(self) -> Dict:
        """Tính moment of inertia (cần cho stability analysis)"""
        cg = self.calculate_cg()
        cg_x = cg['cg_position']['x']
        cg_y = cg['cg_position']['y']
        cg_z = cg['cg_position']['z']
        
        # Tính moment of inertia về CG
        ixx = 0  # Roll axis
        iyy = 0  # Pitch axis
        izz = 0  # Yaw axis
        
        for name, comp in self.components.items():
            dx = comp['x'] - cg_x
            dy = comp['y'] - cg_y
            dz = comp['z'] - cg_z
            m = comp['weight']
            
            ixx += m * (dy**2 + dz**2)
            iyy += m * (dx**2 + dz**2)
            izz += m * (dx**2 + dy**2)
        
        return {
            'ixx_kg_m2': ixx,
            'iyy_kg_m2': iyy,
            'izz_kg_m2': izz,
        }
    
    def suggest_battery_position(self, target_cg_percent: float = 27.5) -> Dict:
        """
        Đề xuất vị trí pin để đạt CG mục tiêu
        
        Args:
            target_cg_percent: % MAC mong muốn (25-30%)
        """
        target_cg_x = (target_cg_percent / 100) * self.wing_chord
        
        # Tính CG không có pin
        components_without_battery = {k: v for k, v in self.components.items() 
                                      if k != 'battery'}
        
        total_weight = 0
        moment_x = 0
        
        for name, comp in components_without_battery.items():
            weight = comp['weight']
            total_weight += weight
            moment_x += comp['x'] * weight
        
        # Thêm payload
        payload_weight = 3.75
        payload_x = 0.15
        total_weight += payload_weight
        moment_x += payload_x * payload_weight
        
        # Tính vị trí pin cần thiết
        battery_weight = self.components['battery']['weight']
        battery_x_required = (target_cg_x * (total_weight + battery_weight) - moment_x) / battery_weight
        
        # Kiểm tra có khả thi không (trong phạm vi máy bay)
        is_feasible = 0.0 <= battery_x_required <= self.wing_chord
        
        return {
            'target_cg_percent': target_cg_percent,
            'target_cg_x_m': target_cg_x,
            'suggested_battery_x_m': battery_x_required,
            'current_battery_x_m': self.components['battery']['x'],
            'adjustment_needed_cm': (battery_x_required - self.components['battery']['x']) * 100,
            'is_feasible': is_feasible,
        }
    
    def generate_report(self) -> Dict:
        """Tạo báo cáo tổng hợp"""
        cg_analysis = self.analyze_cg_range()
        inertia = self.calculate_moment_of_inertia()
        battery_suggestion = self.suggest_battery_position()
        
        return {
            'cg_analysis': cg_analysis,
            'moment_of_inertia': inertia,
            'battery_position_suggestion': battery_suggestion,
            'components': self.components,
        }
    
    def print_report(self):
        """In báo cáo ra console"""
        report = self.generate_report()
        
        print("=" * 70)
        print(" FLYING WING UAV - CENTER OF GRAVITY ANALYSIS")
        print("=" * 70)
        
        print("\n📏 THÔNG SỐ CÁNH:")
        print(f"  Wing Chord (MAC): {self.wing_chord:.2f} m")
        print(f"  Wing Span: {self.wing_span:.2f} m")
        print(f"  Wing Area: {self.wing_area:.2f} m²")
        print(f"  CG Target Range: {self.cg_target_min*100:.0f}% - {self.cg_target_max*100:.0f}% MAC")
        
        print("\n📊 PHÂN TÍCH CG THEO CẤU HÌNH:")
        
        configs = [
            ('without_payload', 'Không có payload'),
            ('min_payload', 'Payload tối thiểu (3.5 kg)'),
            ('target_payload', 'Payload mục tiêu (3.75 kg)'),
            ('max_payload', 'Payload tối đa (4.0 kg)'),
        ]
        
        for key, label in configs:
            data = report['cg_analysis'][key]
            status = "✅" if data['is_safe'] else "❌"
            print(f"\n  {label}:")
            print(f"    CG Position: x={data['cg_position']['x']:.3f}m, "
                  f"y={data['cg_position']['y']:.3f}m, z={data['cg_position']['z']:.3f}m")
            print(f"    CG % MAC: {data['cg_percent_mac']:.1f}% {status}")
            print(f"    Total Weight: {data['total_weight_kg']:.3f} kg")
        
        print("\n🔄 ẢNH HƯỞNG VỊ TRÍ PAYLOAD:")
        
        payload_configs = [
            ('payload_forward', 'Payload ở phía trước (x=0.10m)'),
            ('target_payload', 'Payload ở vị trí chuẩn (x=0.15m)'),
            ('payload_backward', 'Payload ở phía sau (x=0.20m)'),
        ]
        
        for key, label in payload_configs:
            data = report['cg_analysis'][key]
            status = "✅" if data['is_safe'] else "❌"
            print(f"  {label}:")
            print(f"    CG % MAC: {data['cg_percent_mac']:.1f}% {status}")
        
        print("\n🔋 ĐỀ XUẤT VỊ TRÍ PIN:")
        battery_data = report['battery_position_suggestion']
        print(f"  Vị trí hiện tại: x={battery_data['current_battery_x_m']:.3f}m")
        print(f"  Vị trí đề xuất: x={battery_data['suggested_battery_x_m']:.3f}m")
        print(f"  Cần điều chỉnh: {battery_data['adjustment_needed_cm']:+.1f} cm")
        print(f"  Khả thi: {'✅ CÓ' if battery_data['is_feasible'] else '❌ KHÔNG'}")
        
        print("\n🌀 MOMENT OF INERTIA:")
        inertia = report['moment_of_inertia']
        print(f"  Ixx (Roll):  {inertia['ixx_kg_m2']:.4f} kg⋅m²")
        print(f"  Iyy (Pitch): {inertia['iyy_kg_m2']:.4f} kg⋅m²")
        print(f"  Izz (Yaw):   {inertia['izz_kg_m2']:.4f} kg⋅m²")
        
        print("\n" + "=" * 70)
        print("⚠️  LƯU Ý:")
        print("  - Vị trí components cần đo chính xác từ CAD model")
        print("  - Sau khi lắp ráp, cần đo CG thực tế và điều chỉnh")
        print("  - Pin nên có thể di chuyển để fine-tune CG")
        print("  - Test bay cần kiểm tra stability và điều chỉnh nếu cần")
        print("=" * 70)
        
        return report
    
    def visualize_cg(self, save_path: str = None):
        """
        Vẽ biểu đồ phân bố khối lượng và CG
        (Requires matplotlib)
        """
        try:
            cg_data = self.calculate_cg()
            cg_x = cg_data['cg_position']['x']
            cg_y = cg_data['cg_position']['y']
            
            # Prepare data
            names = []
            x_pos = []
            y_pos = []
            weights = []
            
            for name, comp in self.components.items():
                names.append(name)
                x_pos.append(comp['x'])
                y_pos.append(comp['y'])
                weights.append(comp['weight'] * 1000)  # Convert to grams
            
            # Create figure
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Top view (X-Y plane)
            scatter1 = ax1.scatter(x_pos, y_pos, s=weights, alpha=0.6, c=weights, cmap='viridis')
            ax1.scatter(cg_x, cg_y, s=200, c='red', marker='x', linewidths=3, label='CG')
            ax1.axvline(x=self.cg_target_min * self.wing_chord, color='green', 
                       linestyle='--', alpha=0.5, label='CG Target Min')
            ax1.axvline(x=self.cg_target_max * self.wing_chord, color='green', 
                       linestyle='--', alpha=0.5, label='CG Target Max')
            ax1.set_xlabel('X - Longitudinal (m)')
            ax1.set_ylabel('Y - Lateral (m)')
            ax1.set_title('Top View - Component Distribution')
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            ax1.set_aspect('equal')
            plt.colorbar(scatter1, ax=ax1, label='Weight (g)')
            
            # Side view (X-Z plane - simplified)
            ax2.barh(range(len(names)), x_pos, height=0.5)
            ax2.axvline(x=cg_x, color='red', linewidth=2, label=f'CG: {cg_x:.3f}m')
            ax2.axvline(x=self.cg_target_min * self.wing_chord, color='green', 
                       linestyle='--', alpha=0.5)
            ax2.axvline(x=self.cg_target_max * self.wing_chord, color='green', 
                       linestyle='--', alpha=0.5, label='Target Range')
            ax2.set_xlabel('X - Longitudinal Position (m)')
            ax2.set_ylabel('Components')
            ax2.set_title('Longitudinal Position Distribution')
            ax2.legend()
            ax2.grid(True, alpha=0.3, axis='x')
            
            plt.tight_layout()
            
            # Use absolute path
            if save_path is None:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                save_path = os.path.join(script_dir, 'cg_visualization.png')
            
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Biểu đồ đã được lưu: {save_path}")
            
            plt.close()
            
        except ImportError:
            print("⚠️  Cần cài đặt matplotlib để vẽ biểu đồ:")
            print("    pip install matplotlib")
        except Exception as e:
            print(f"❌ Lỗi khi vẽ biểu đồ: {e}")


def main():
    """Main function"""
    calc = CGCalculator()
    report = calc.print_report()
    
    # Save to JSON - use absolute path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, 'cg_analysis_report.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Báo cáo đã được lưu vào: {output_file}")
    
    # Try to create visualization
    print("\n📊 Đang tạo biểu đồ...")
    calc.visualize_cg()


if __name__ == "__main__":
    main()
