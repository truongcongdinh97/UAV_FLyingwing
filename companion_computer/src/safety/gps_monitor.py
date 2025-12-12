"""
GPS Monitor - Phát hiện GPS Lost và Cảnh báo Phi công

Triết lý thiết kế:
- KHÔNG tính toán vị trí trên Pi (tin tưởng FC's EKF3)
- KHÔNG gửi Position Command khi mất GPS (nguy hiểm)
- CHỈ phát hiện GPS anomaly và cảnh báo phi công
- PHI CÔNG quyết định: Chuyển FBWA/AltHold, lái tay về nhà

Tác giả: Trương Công Định & Đặng Duy Long
Ngày: 2025-12-01
"""

import time
import math
from typing import Optional, Tuple, Callable, Deque
from dataclasses import dataclass
from enum import Enum
from collections import deque
from loguru import logger


class GPSStatus(Enum):
    """Trạng thái GPS đơn giản"""
    OK = "ok"                   # GPS hoạt động bình thường
    DEGRADED = "degraded"       # Chất lượng kém nhưng dùng được  
    LOST = "lost"               # Mất GPS - Cần cảnh báo phi công
    RECOVERED = "recovered"     # Vừa phục hồi


@dataclass
class GPSData:
    """Dữ liệu GPS từ MAVLink"""
    timestamp: float
    lat: float
    lon: float
    alt: float
    ground_speed: float     # m/s
    heading: float          # degrees
    satellites: int
    hdop: float
    fix_type: int           # 0=no fix, 2=2D, 3=3D
    
    def is_valid(self) -> bool:
        """Kiểm tra GPS có đủ tốt không"""
        return self.fix_type >= 3 and self.satellites >= 6 and self.hdop < 3.0


class GPSMonitor:
    """
    Giám sát GPS và cảnh báo khi mất tín hiệu
    
    Chức năng:
    1. Phát hiện GPS anomaly (HDOP, satellites, position jump)
    2. Cảnh báo phi công qua callback
    3. Tính toán hướng về nhà để hiển thị OSD
    
    KHÔNG làm:
    - Tính toán vị trí Dead Reckoning
    - Gửi lệnh điều khiển tự động
    - Tự động RTH
    """
    
    def __init__(
        self,
        home_lat: float = 0.0,
        home_lon: float = 0.0,
        on_gps_lost: Optional[Callable[[], None]] = None,
        on_gps_recovered: Optional[Callable[[], None]] = None,
        on_status_change: Optional[Callable[[GPSStatus, str], None]] = None
    ):
        """
        Khởi tạo GPS Monitor
        
        Args:
            home_lat: Vĩ độ home (để tính hướng về nhà)
            home_lon: Kinh độ home
            on_gps_lost: Callback khi mất GPS
            on_gps_recovered: Callback khi GPS phục hồi
            on_status_change: Callback khi trạng thái thay đổi
        """
        self.home_lat = home_lat
        self.home_lon = home_lon
        
        # Callbacks
        self.on_gps_lost = on_gps_lost
        self.on_gps_recovered = on_gps_recovered
        self.on_status_change = on_status_change
        
        # GPS history (để phát hiện anomaly)
        self.gps_history: Deque[GPSData] = deque(maxlen=50)
        
        # Trạng thái hiện tại
        self.current_status = GPSStatus.OK
        self.last_valid_gps: Optional[GPSData] = None
        self.gps_lost_time: Optional[float] = None
        
        # Anomaly detection
        self.anomaly_score: float = 0.0
        self.consecutive_bad: int = 0
        
        # Thresholds
        self.max_position_jump = 50.0       # meters
        self.min_satellites = 6
        self.max_hdop = 3.0
        self.satellite_drop_threshold = 4
        self.anomaly_threshold = 50.0       # Score để xác nhận mất GPS
        
        logger.info("GPS Monitor initialized (Pilot-Assisted Mode)")
    
    def set_home(self, lat: float, lon: float):
        """Cập nhật vị trí home"""
        self.home_lat = lat
        self.home_lon = lon
        logger.info(f"Home position set: {lat:.6f}, {lon:.6f}")
    
    def update(self, gps: GPSData) -> Tuple[GPSStatus, str]:
        """
        Cập nhật dữ liệu GPS và kiểm tra trạng thái
        
        Args:
            gps: Dữ liệu GPS mới từ MAVLink
            
        Returns:
            (status, message) - Trạng thái và thông báo
        """
        prev_status = self.current_status
        anomalies = []
        score_delta = 0.0
        
        # Kiểm tra với GPS trước đó
        if self.gps_history:
            prev = self.gps_history[-1]
            dt = gps.timestamp - prev.timestamp
            
            if dt > 0 and dt < 5.0:  # Ignore if too long gap
                # 1. Position jump
                distance = self._haversine(prev.lat, prev.lon, gps.lat, gps.lon)
                expected = prev.ground_speed * dt * 2  # Allow 2x
                
                if distance > self.max_position_jump and distance > expected:
                    anomalies.append(f"Nhảy vị trí: {distance:.0f}m")
                    score_delta += 30
                
                # 2. Satellite drop
                sat_drop = prev.satellites - gps.satellites
                if sat_drop >= self.satellite_drop_threshold:
                    anomalies.append(f"Mất vệ tinh: {prev.satellites}->{gps.satellites}")
                    score_delta += 25
                
                # 3. HDOP spike
                if gps.hdop > self.max_hdop and prev.hdop <= self.max_hdop:
                    anomalies.append(f"HDOP tăng: {gps.hdop:.1f}")
                    score_delta += 15
        
        # Kiểm tra tuyệt đối
        if gps.satellites < self.min_satellites:
            anomalies.append(f"Ít vệ tinh: {gps.satellites}")
            score_delta += 10
        
        if gps.fix_type < 3:
            anomalies.append(f"Không có 3D fix")
            score_delta += 30
        
        # Cập nhật anomaly score (có decay)
        self.anomaly_score = max(0, self.anomaly_score * 0.85 + score_delta)
        
        # Cập nhật history
        self.gps_history.append(gps)
        
        # Xác định trạng thái
        if self.anomaly_score >= self.anomaly_threshold:
            self.consecutive_bad += 1
            if self.consecutive_bad >= 3:
                self.current_status = GPSStatus.LOST
                if self.gps_lost_time is None:
                    self.gps_lost_time = time.time()
        elif self.anomaly_score >= 30:
            self.current_status = GPSStatus.DEGRADED
            self.consecutive_bad = 0
        else:
            self.consecutive_bad = 0
            if self.current_status == GPSStatus.LOST:
                self.current_status = GPSStatus.RECOVERED
                self.gps_lost_time = None
            else:
                self.current_status = GPSStatus.OK
            
            if gps.is_valid():
                self.last_valid_gps = gps
        
        # Tạo message
        if anomalies:
            message = "; ".join(anomalies)
        elif self.current_status == GPSStatus.OK:
            message = f"GPS OK - {gps.satellites} sats, HDOP {gps.hdop:.1f}"
        elif self.current_status == GPSStatus.RECOVERED:
            message = "GPS đã phục hồi!"
        else:
            message = f"Score: {self.anomaly_score:.0f}"
        
        # Gọi callbacks nếu trạng thái thay đổi
        if prev_status != self.current_status:
            self._handle_status_change(prev_status, self.current_status, message)
        
        return self.current_status, message
    
    def _handle_status_change(self, prev: GPSStatus, new: GPSStatus, message: str):
        """Xử lý khi trạng thái thay đổi"""
        logger.warning(f"GPS Status: {prev.value} -> {new.value}: {message}")
        
        if new == GPSStatus.LOST and self.on_gps_lost:
            self.on_gps_lost()
        elif new == GPSStatus.RECOVERED and self.on_gps_recovered:
            self.on_gps_recovered()
        
        if self.on_status_change:
            self.on_status_change(new, message)
    
    def get_heading_to_home(self) -> Optional[float]:
        """
        Tính hướng về nhà từ vị trí GPS cuối cùng
        
        Dùng để hiển thị OSD cho phi công khi lái tay
        
        Returns:
            Heading (degrees) hoặc None nếu không có dữ liệu
        """
        if not self.last_valid_gps or self.home_lat == 0:
            return None
        
        return self._bearing(
            self.last_valid_gps.lat, self.last_valid_gps.lon,
            self.home_lat, self.home_lon
        )
    
    def get_distance_to_home(self) -> Optional[float]:
        """
        Tính khoảng cách về nhà (meters)
        
        Returns:
            Khoảng cách hoặc None
        """
        if not self.last_valid_gps or self.home_lat == 0:
            return None
        
        return self._haversine(
            self.last_valid_gps.lat, self.last_valid_gps.lon,
            self.home_lat, self.home_lon
        )
    
    def get_time_since_gps_lost(self) -> Optional[float]:
        """Thời gian kể từ khi mất GPS (seconds)"""
        if self.gps_lost_time is None:
            return None
        return time.time() - self.gps_lost_time
    
    def get_alert_message(self) -> str:
        """
        Tạo thông báo cảnh báo cho phi công
        
        Returns:
            Thông báo ngắn gọn để hiển thị OSD
        """
        if self.current_status == GPSStatus.LOST:
            time_lost = self.get_time_since_gps_lost() or 0
            heading = self.get_heading_to_home()
            distance = self.get_distance_to_home()
            
            msg = f"⚠️ GPS LOST {time_lost:.0f}s"
            if heading is not None:
                msg += f" | HOME: {heading:.0f}°"
            if distance is not None:
                msg += f" {distance/1000:.1f}km"
            msg += " | SWITCH FBWA!"
            return msg
        
        elif self.current_status == GPSStatus.DEGRADED:
            return f"⚠️ GPS DEGRADED - Score: {self.anomaly_score:.0f}"
        
        elif self.current_status == GPSStatus.RECOVERED:
            return "✅ GPS RECOVERED - RTL available"
        
        return ""
    
    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Tính khoảng cách giữa 2 điểm (meters)"""
        R = 6371000
        lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    @staticmethod
    def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Tính hướng từ điểm 1 đến điểm 2 (degrees)"""
        lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
        dlon = math.radians(lon2 - lon1)
        
        x = math.sin(dlon) * math.cos(lat2_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
        
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360


class PilotAlertManager:
    """
    Quản lý cảnh báo cho phi công
    
    Gửi cảnh báo qua:
    - MAVLink STATUSTEXT (hiển thị trên GCS)
    - OSD overlay (nếu có)
    - Audio alert (nếu có)
    """
    
    def __init__(
        self,
        send_statustext: Optional[Callable[[str, int], None]] = None,
        play_audio: Optional[Callable[[str], None]] = None
    ):
        """
        Args:
            send_statustext: Callback gửi MAVLink STATUSTEXT(message, severity)
            play_audio: Callback phát âm thanh cảnh báo
        """
        self.send_statustext = send_statustext
        self.play_audio = play_audio
        self.last_alert_time: float = 0
        self.alert_interval: float = 5.0  # seconds between alerts
    
    def alert_gps_lost(self, heading_home: Optional[float] = None):
        """Cảnh báo mất GPS"""
        now = time.time()
        if now - self.last_alert_time < self.alert_interval:
            return
        
        self.last_alert_time = now
        
        msg = "GPS LOST! Switch FBWA and fly manually"
        if heading_home is not None:
            msg += f" | Home bearing: {heading_home:.0f}deg"
        
        if self.send_statustext:
            self.send_statustext(msg, 2)  # CRITICAL severity
        
        if self.play_audio:
            self.play_audio("gps_lost")
        
        logger.critical(msg)
    
    def alert_gps_recovered(self):
        """Thông báo GPS phục hồi"""
        msg = "GPS RECOVERED! RTL available"
        
        if self.send_statustext:
            self.send_statustext(msg, 4)  # WARNING -> INFO
        
        if self.play_audio:
            self.play_audio("gps_ok")
        
        logger.info(msg)
    
    def alert_gps_degraded(self, score: float):
        """Cảnh báo GPS kém chất lượng"""
        now = time.time()
        if now - self.last_alert_time < self.alert_interval * 2:
            return
        
        self.last_alert_time = now
        
        msg = f"GPS DEGRADED - Anomaly score: {score:.0f}"
        
        if self.send_statustext:
            self.send_statustext(msg, 3)  # WARNING severity
        
        logger.warning(msg)
