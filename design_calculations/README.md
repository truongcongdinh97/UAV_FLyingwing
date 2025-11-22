# Design Calculations

Thư mục này chứa các script tính toán thiết kế cho Flying Wing UAV.

## Scripts

### `aerodynamics_calculator.py`
Tính toán các thông số khí động học:
- Wing Loading (tải trọng trên cánh)
- Thrust-to-Weight Ratio
- Stall Speed
- Maximum Speed
- Flight Time Estimation

### `cg_calculator.py`
Tính toán Center of Gravity (CG):
- Xác định vị trí CG dựa trên BOM
- Phân bố khối lượng các component
- Kiểm tra CG có nằm trong phạm vi an toàn

## Dữ Liệu Đầu Vào

Các thông số được lấy từ BOM:
- Động cơ: DXW D4250 800KV (2x)
- Pin: 4S2P 10400mAh
- Flight Controller: LANRC F4 V3S
- Raspberry Pi 3B+
- Camera, sensors, và các component khác

## Usage

```python
# Chạy tính toán
python aerodynamics_calculator.py
python cg_calculator.py
```
