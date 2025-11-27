"""
Geolocation Utility
Tính toán tọa độ GPS của một mục tiêu dựa trên vị trí của nó trong ảnh.

GIẢ ĐỊNH QUAN TRỌNG:
1.  CAMERA: Giả định là Raspberry Pi Camera v1 với:
    -   Góc nhìn ngang (HFOV): 54 độ
    -   Góc nhìn dọc (VFOV): 41 độ
2.  GẮN CAMERA: Giả định camera được gắn cố định:
    -   Góc Pitch (nghiêng lên/xuống): -20 độ (hơi chúi xuống)
    -   Góc Roll (nghiêng trái/phải): 0 độ
    -   Góc Yaw (hướng trái/phải): 0 độ (hướng thẳng về phía trước)
3.  MẶT ĐẤT: Giả định mặt đất là một mặt phẳng ở mực nước biển (altitude = 0).

Các giả định này có thể được thay đổi trong các hằng số bên dưới.
"""

import math
import numpy as np
from typing import Optional, Dict, Any

# --- Cấu hình có thể thay đổi ---
# Thông số camera (cho Raspberry Pi Camera Module v1)
CAMERA_HFOV_DEG = 54.0  # Góc nhìn ngang (độ)
CAMERA_VFOV_DEG = 41.0  # Góc nhìn dọc (độ)

# Góc gắn camera so với thân máy bay (độ)
CAMERA_PITCH_DEG = -20.0 # Âm là chúi xuống
CAMERA_ROLL_DEG = 0.0
CAMERA_YAW_DEG = 0.0
# ---------------------------------

def get_target_geolocation(
    detection_result: Dict[str, Any],
    uav_telemetry: Dict[str, Any],
    image_width: int,
    image_height: int
) -> Optional[Dict[str, float]]:
    """
    Hàm chính để tính toán vị trí GPS của mục tiêu.

    Args:
        detection_result: Dict chứa thông tin phát hiện từ AI, bao gồm 'bbox'.
        uav_telemetry: Dict chứa dữ liệu bay của UAV (lat, lon, alt, roll, pitch, yaw).
        image_width: Chiều rộng của ảnh (pixels).
        image_height: Chiều cao của ảnh (pixels).

    Returns:
        Một dict chứa 'lat' và 'lon' của mục tiêu, hoặc None nếu không thể tính toán.
    """
    try:
        # Lấy các giá trị cần thiết từ telemetry
        uav_lat = uav_telemetry.get('lat')
        uav_lon = uav_telemetry.get('lon')
        uav_alt_msl = uav_telemetry.get('alt') # Altitude Mean Sea Level
        
        # Radian
        uav_roll_rad = math.radians(uav_telemetry.get('roll', 0))
        uav_pitch_rad = math.radians(uav_telemetry.get('pitch', 0))
        uav_yaw_rad = math.radians(uav_telemetry.get('yaw', 0))
        
        if any(v is None for v in [uav_lat, uav_lon, uav_alt_msl]):
            return None

        # Lấy trung tâm của bounding box làm điểm mục tiêu trong ảnh
        bbox = detection_result['bbox']
        target_px = (bbox[0] + bbox[2]) / 2
        target_py = (bbox[1] + bbox[3]) / 2

        # 1. Chuyển đổi tọa độ pixel thành góc trong hệ quy chiếu camera
        # Góc lệch ngang và dọc so với quang tâm của camera
        angle_x_rad = math.radians(((target_px / image_width) - 0.5) * CAMERA_HFOV_DEG)
        angle_y_rad = math.radians(((target_py / image_height) - 0.5) * CAMERA_VFOV_DEG)

        # 2. Tạo vector chỉ hướng từ camera đến mục tiêu trong hệ quy chiếu camera
        # (X: phải, Y: dưới, Z: trước)
        cam_vector = np.array([
            math.tan(angle_x_rad),
            math.tan(angle_y_rad),
            1.0
        ])
        cam_vector /= np.linalg.norm(cam_vector)

        # 3. Xoay vector từ hệ quy chiếu camera sang hệ quy chiếu thân máy bay (body frame)
        # (X: trước, Y: phải, Z: dưới)
        
        # Ma trận xoay cho góc gắn camera
        cam_pitch_rad = math.radians(CAMERA_PITCH_DEG)
        cam_roll_rad = math.radians(CAMERA_ROLL_DEG)
        cam_yaw_rad = math.radians(CAMERA_YAW_DEG)

        R_cam_to_body = _euler_to_rotation_matrix(cam_roll_rad, cam_pitch_rad, cam_yaw_rad)
        
        # Chuyển đổi hệ quy chiếu từ camera (OpenCV) sang body (aerospace)
        # OpenCV (X-phải, Y-dưới, Z-trước) -> Aerospace (X-trước, Y-phải, Z-dưới)
        # x_aero = z_cv, y_aero = x_cv, z_aero = y_cv
        cam_vector_aerospace = np.array([cam_vector[2], cam_vector[0], cam_vector[1]])
        
        body_vector = R_cam_to_body @ cam_vector_aerospace

        # 4. Xoay vector từ hệ quy chiếu thân máy bay sang hệ quy chiếu Trái Đất (NED: North-East-Down)
        R_body_to_ned = _euler_to_rotation_matrix(uav_roll_rad, uav_pitch_rad, uav_yaw_rad)
        ned_vector = R_body_to_ned @ body_vector

        # 5. Tính toán giao điểm của vector chỉ hướng và mặt đất
        # Giả định mặt đất ở độ cao 0m so với mực nước biển (MSL)
        target_alt_msl = 0.0
        
        # Kiểm tra xem vector có hướng xuống không, nếu không sẽ không bao giờ cắt mặt đất
        if ned_vector[2] <= 0:
            return None # Vector hướng lên hoặc song song mặt đất

        # Tính khoảng cách trên mặt đất (ground distance)
        # d = h / cos(theta) = h / (vector_z)
        # scale = h / vector_z
        scale = (uav_alt_msl - target_alt_msl) / ned_vector[2]
        
        # Giao điểm trong hệ NED so với UAV
        north_offset = ned_vector[0] * scale
        east_offset = ned_vector[1] * scale

        # 6. Chuyển đổi offset (mét) thành chênh lệch lat/lon
        earth_radius = 6378137.0
        
        d_lat = north_offset / earth_radius
        d_lon = east_offset / (earth_radius * math.cos(math.radians(uav_lat)))

        # 7. Tính tọa độ GPS cuối cùng của mục tiêu
        target_lat = uav_lat + math.degrees(d_lat)
        target_lon = uav_lon + math.degrees(d_lon)

        return {'lat': target_lat, 'lon': target_lon}

    except Exception as e:
        # Ghi log lỗi nếu có vấn đề trong quá trình tính toán
        # import traceback; traceback.print_exc()
        return None


def _euler_to_rotation_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """Tạo ma trận xoay từ các góc Euler (rad)."""
    
    cos_r, sin_r = math.cos(roll), math.sin(roll)
    cos_p, sin_p = math.cos(pitch), math.sin(pitch)
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)

    R_x = np.array([[1, 0, 0], [0, cos_r, -sin_r], [0, sin_r, cos_r]]) # Roll
    R_y = np.array([[cos_p, 0, sin_p], [0, 1, 0], [-sin_p, 0, cos_p]]) # Pitch
    R_z = np.array([[cos_y, -sin_y, 0], [sin_y, cos_y, 0], [0, 0, 1]])   # Yaw

    # Thứ tự xoay Z-Y-X (Yaw, Pitch, Roll) cho hệ body-to-NED
    return R_z @ R_y @ R_x

def calculate_target_geolocation(bbox, uav_telemetry, image_width, image_height):
    """
    Tính toán vị trí địa lý (lat/lon) của mục tiêu dựa trên bounding box AI, trạng thái UAV và thông số camera.
    
    Args:
        bbox: (x1, y1, x2, y2) - bounding box của mục tiêu trong ảnh (pixels)
        uav_telemetry: dict chứa lat, lon, alt, roll, pitch, yaw của UAV
        image_width: chiều rộng ảnh (pixels)
        image_height: chiều cao ảnh (pixels)
    Returns:
        dict {'lat': ..., 'lon': ...} hoặc None nếu không tính được
    Giải thích:
        - Hàm này là bước đầu tiên trong pipeline tracking chuyên nghiệp: chuyển đổi vị trí pixel sang vị trí địa lý thực tế.
        - Sử dụng các giả định về camera, attitude UAV, và mặt đất phẳng để tính toán nhanh, phù hợp cho UAV nhỏ.
    """
    detection_result = {'bbox': bbox}
    return get_target_geolocation(detection_result, uav_telemetry, image_width, image_height)
