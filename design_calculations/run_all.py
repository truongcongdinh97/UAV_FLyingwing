"""
Flying Wing UAV - Design Calculations Package
Chạy tất cả các script tính toán và tạo báo cáo tổng hợp
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aerodynamics_calculator import AerodynamicsCalculator
from cg_calculator import CGCalculator


def main():
    """Chạy tất cả các tính toán"""
    print("🚀 FLYING WING UAV - DESIGN CALCULATIONS")
    print("=" * 70)
    print()
    
    # 1. Aerodynamics Analysis
    print("1️⃣  KHỞI ĐỘNG: Aerodynamics Calculator...")
    print()
    aero_calc = AerodynamicsCalculator()
    aero_report = aero_calc.print_report()
    print()
    
    # 2. CG Analysis
    print("\n2️⃣  KHỞI ĐỘNG: Center of Gravity Calculator...")
    print()
    cg_calc = CGCalculator()
    cg_report = cg_calc.print_report()
    print()
    
    # 3. Visualization
    print("\n3️⃣  TẠO BIỂU ĐỒ...")
    cg_calc.visualize_cg()
    
    print("\n✅ HOÀN TẤT TẤT CẢ TÍNH TOÁN!")
    print("=" * 70)
    
    # Show actual file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print("\n📁 Các file output:")
    print(f"  - {os.path.join(script_dir, 'aerodynamics_report.json')}")
    print(f"  - {os.path.join(script_dir, 'cg_analysis_report.json')}")
    print(f"  - {os.path.join(script_dir, 'cg_visualization.png')}")
    print()


if __name__ == "__main__":
    main()
