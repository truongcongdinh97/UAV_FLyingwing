"""
GPS Denial Detection & Dead Reckoning Navigation System
Phát hiện GPS Jamming/Spoofing và điều hướng khi mất GPS

Author: Trương Công Định & Đặng Duy Long
Date: 2025-12-01

⚠️ LƯU Ý QUAN TRỌNG - TRIẾT LÝ MỚI (01/12/2025):
==================================================
File này được giữ lại cho mục đích NGHIÊN CỨU và THAM KHẢO.

Trong thực tế bay, KHÔNG NÊN:
- Tự động Dead Reckoning trên Pi (sai số tích lũy nhanh)
- Gửi Position Command khi mất GPS (nguy hiểm)
- Tự động Escape Maneuver (có thể bay sai hướng)

THAY VÀO ĐÓ, sử dụng file mới: gps_monitor.py
- Pi CHỈ phát hiện GPS lost và cảnh báo phi công
- Phi công chuyển FBWA/AltHold và lái tay về nhà
- Tin tưởng EKF3 của Flight Controller

Xem: docs/PROJECT_PORTFOLIO.md phần "GPS Denial Response System"
==================================================

Kịch bản xử lý (CHỈ CHO NGHIÊN CỨU):
1. Phát hiện GPS bất thường (jamming/spoofing)
2. Chuyển sang Dead Reckoning navigation
3. Thực hiện escape maneuver (bay ngược hướng cũ)
4. Cảnh báo pilot qua telemetry
5. Tự động phục hồi khi GPS trở lại
"""

import time
import math
from typing import Optional, Tuple, List, Dict, Deque
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from loguru import logger
import threading


class GPSState(Enum):
    """Trạng thái GPS"""
    NORMAL = "normal"
    DEGRADED = "degraded"          # Chất lượng kém nhưng vẫn dùng được
    SUSPECTED_JAM = "suspected"    # Nghi ngờ bị jam
    CONFIRMED_JAM = "confirmed"    # Xác nhận bị jam
    SUSPECTED_SPOOF = "spoofed"    # Nghi ngờ bị spoof (GPS giả)
    RECOVERED = "recovered"        # Vừa phục hồi


class EscapeAction(Enum):
    """Hành động thoát khi bị jam"""
    REVERSE_HEADING = "reverse"    # Bay ngược hướng cũ
    CLIMB_AND_REVERSE = "climb"    # Tăng độ cao + bay ngược
    LOITER = "loiter"              # Lượn vòng tại chỗ
    CONTINUE_MISSION = "continue"  # Tiếp tục (nếu gần home)
    EMERGENCY_LAND = "land"        # Hạ cánh khẩn cấp


@dataclass
class GPSReading:
    """Một lần đọc GPS"""
    timestamp: float
    lat: float
    lon: float
    alt: float
    ground_speed: float      # m/s
    heading: float           # degrees
    satellites: int
    hdop: float
    fix_type: int           # 0=no fix, 2=2D, 3=3D
    
    def is_valid(self) -> bool:
        return self.fix_type >= 3 and self.satellites >= 6


@dataclass
class IMUReading:
    """Đọc từ IMU (qua MAVLink từ FC)"""
    timestamp: float
    roll: float             # radians
    pitch: float            # radians
    yaw: float              # radians (heading)
    roll_rate: float        # rad/s
    pitch_rate: float       # rad/s
    yaw_rate: float         # rad/s
    accel_x: float          # m/s^2
    accel_y: float          # m/s^2
    accel_z: float          # m/s^2


@dataclass
class DeadReckonPosition:
    """Vị trí ước lượng từ Dead Reckoning"""
    lat: float
    lon: float
    alt: float
    heading: float
    confidence: float       # 0-1, giảm theo thời gian
    time_since_gps: float   # seconds since last valid GPS
    estimated_error: float  # meters


@dataclass
class GPSDenialEvent:
    """Sự kiện GPS denial để logging/analysis"""
    start_time: float
    end_time: Optional[float]
    start_position: Tuple[float, float, float]  # lat, lon, alt
    denial_type: GPSState
    escape_action: EscapeAction
    max_dr_error: float
    recovered: bool


class GPSAnomalyDetector:
    """
    Phát hiện GPS jamming và spoofing
    
    Detection methods:
    1. Position jump detection (vị trí nhảy đột ngột)
    2. Velocity validation (tốc độ không khớp với IMU)
    3. Satellite count anomaly (số vệ tinh thay đổi bất thường)
    4. HDOP spike (độ chính xác giảm đột ngột)
    5. Carrier-to-noise ratio (C/N0) - nếu có
    6. Cross-check với IMU dead reckoning
    """
    
    def __init__(self):
        # History buffers
        self.gps_history: Deque[GPSReading] = deque(maxlen=100)
        self.imu_history: Deque[IMUReading] = deque(maxlen=500)
        
        # Detection thresholds
        self.max_position_jump = 50.0       # meters - max jump trong 1 update
        self.max_velocity_mismatch = 10.0   # m/s - max sai lệch GPS vs IMU
        self.min_satellites = 6             # Minimum satellites
        self.max_hdop = 3.0                 # Maximum HDOP
        self.satellite_drop_threshold = 4   # Số vệ tinh giảm đột ngột
        
        # State
        self.anomaly_score = 0.0            # 0-100, cao = nghi ngờ hơn
        self.consecutive_anomalies = 0
        self.last_valid_gps: Optional[GPSReading] = None
        
        logger.info("GPS Anomaly Detector initialized")
    
    def update_gps(self, reading: GPSReading) -> Tuple[bool, float, str]:
        """
        Cập nhật GPS reading và kiểm tra anomaly
        
        Returns:
            (is_anomaly, anomaly_score, reason)
        """
        anomalies = []
        score_delta = 0.0
        
        if self.gps_history:
            prev = self.gps_history[-1]
            dt = reading.timestamp - prev.timestamp
            
            if dt > 0:
                # 1. Position jump detection
                distance = self._haversine(prev.lat, prev.lon, reading.lat, reading.lon)
                expected_distance = prev.ground_speed * dt
                
                if distance > self.max_position_jump and distance > expected_distance * 3:
                    anomalies.append(f"Position jump: {distance:.1f}m")
                    score_delta += 30
                
                # 2. Velocity validation với IMU
                if self.imu_history:
                    imu_velocity = self._estimate_velocity_from_imu(dt)
                    velocity_diff = abs(reading.ground_speed - imu_velocity)
                    
                    if velocity_diff > self.max_velocity_mismatch:
                        anomalies.append(f"Velocity mismatch: GPS={reading.ground_speed:.1f}, IMU={imu_velocity:.1f}")
                        score_delta += 20
                
                # 3. Satellite count anomaly
                sat_drop = prev.satellites - reading.satellites
                if sat_drop >= self.satellite_drop_threshold:
                    anomalies.append(f"Satellite drop: {prev.satellites} -> {reading.satellites}")
                    score_delta += 25
                
                # 4. HDOP spike
                if reading.hdop > self.max_hdop and prev.hdop < self.max_hdop:
                    anomalies.append(f"HDOP spike: {prev.hdop:.1f} -> {reading.hdop:.1f}")
                    score_delta += 15
        
        # 5. Absolute checks
        if reading.satellites < self.min_satellites:
            anomalies.append(f"Low satellites: {reading.satellites}")
            score_delta += 10
        
        if reading.fix_type < 3:
            anomalies.append(f"No 3D fix: type={reading.fix_type}")
            score_delta += 20
        
        # Update anomaly score với decay
        self.anomaly_score = max(0, self.anomaly_score * 0.9 + score_delta)
        
        if anomalies:
            self.consecutive_anomalies += 1
        else:
            self.consecutive_anomalies = 0
            if reading.is_valid():
                self.last_valid_gps = reading
        
        # Add to history
        self.gps_history.append(reading)
        
        is_anomaly = self.anomaly_score > 50 or self.consecutive_anomalies >= 3
        reason = "; ".join(anomalies) if anomalies else "OK"
        
        return is_anomaly, self.anomaly_score, reason
    
    def update_imu(self, reading: IMUReading):
        """Cập nhật IMU reading"""
        self.imu_history.append(reading)
    
    def _estimate_velocity_from_imu(self, dt: float) -> float:
        """Ước lượng tốc độ từ IMU (simplified)"""
        if len(self.imu_history) < 2:
            return 0.0
        
        # Lấy acceleration trung bình
        recent_imu = list(self.imu_history)[-10:]
        avg_accel_x = sum(r.accel_x for r in recent_imu) / len(recent_imu)
        avg_accel_y = sum(r.accel_y for r in recent_imu) / len(recent_imu)
        
        # Tốc độ = tích hợp gia tốc (simplified, cần proper rotation)
        accel_horizontal = math.sqrt(avg_accel_x**2 + avg_accel_y**2)
        
        # Nếu có GPS history, dùng làm baseline
        if self.last_valid_gps:
            return self.last_valid_gps.ground_speed + accel_horizontal * dt
        
        return accel_horizontal * dt
    
    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Tính khoảng cách giữa 2 điểm GPS (meters)"""
        R = 6371000  # Earth radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def get_state(self) -> GPSState:
        """Lấy trạng thái GPS hiện tại"""
        if self.anomaly_score < 20:
            return GPSState.NORMAL
        elif self.anomaly_score < 50:
            return GPSState.DEGRADED
        elif self.consecutive_anomalies >= 5:
            return GPSState.CONFIRMED_JAM
        else:
            return GPSState.SUSPECTED_JAM


class DeadReckoningNavigator:
    """
    Dead Reckoning navigation khi mất GPS
    
    Sử dụng:
    - Last known GPS position
    - IMU integration (accelerometer, gyro)
    - Compass heading
    - Airspeed (nếu có) hoặc estimated từ throttle
    - Wind estimation (từ GPS trước khi mất)
    """
    
    # Earth constants
    EARTH_RADIUS = 6371000  # meters
    
    def __init__(self):
        # Last known good position
        self.last_gps: Optional[GPSReading] = None
        self.last_gps_time: float = 0
        
        # Current estimated position
        self.current_lat: float = 0
        self.current_lon: float = 0
        self.current_alt: float = 0
        self.current_heading: float = 0
        
        # Velocity estimates
        self.velocity_north: float = 0  # m/s
        self.velocity_east: float = 0   # m/s
        self.velocity_down: float = 0   # m/s
        
        # Wind estimation (from GPS history before denial)
        self.wind_north: float = 0
        self.wind_east: float = 0
        
        # Error tracking
        self.estimated_error: float = 0  # meters
        self.error_growth_rate: float = 2.0  # m/s error accumulation
        
        # Confidence (decreases over time)
        self.confidence: float = 1.0
        self.confidence_decay_rate: float = 0.02  # per second
        
        # Maximum DR time before giving up
        self.max_dr_time: float = 120.0  # 2 minutes
        
        self.is_active: bool = False
        self.dr_start_time: float = 0
        
        logger.info("Dead Reckoning Navigator initialized")
    
    def start_dead_reckoning(self, last_gps: GPSReading, 
                              estimated_wind: Tuple[float, float] = (0, 0)):
        """Bắt đầu Dead Reckoning từ vị trí GPS cuối"""
        self.last_gps = last_gps
        self.last_gps_time = last_gps.timestamp
        
        self.current_lat = last_gps.lat
        self.current_lon = last_gps.lon
        self.current_alt = last_gps.alt
        self.current_heading = last_gps.heading
        
        # Initialize velocity from GPS
        heading_rad = math.radians(last_gps.heading)
        self.velocity_north = last_gps.ground_speed * math.cos(heading_rad)
        self.velocity_east = last_gps.ground_speed * math.sin(heading_rad)
        
        self.wind_north, self.wind_east = estimated_wind
        
        self.estimated_error = 0
        self.confidence = 1.0
        self.is_active = True
        self.dr_start_time = time.time()
        
        logger.warning(f"🚨 Dead Reckoning STARTED from ({last_gps.lat:.6f}, {last_gps.lon:.6f})")
    
    def update(self, imu: IMUReading, airspeed: float = 15.0) -> DeadReckonPosition:
        """
        Cập nhật vị trí Dead Reckoning
        
        Args:
            imu: IMU reading
            airspeed: Airspeed in m/s (từ sensor hoặc estimated)
        
        Returns:
            DeadReckonPosition with estimated position
        """
        if not self.is_active or self.last_gps is None:
            return DeadReckonPosition(0, 0, 0, 0, 0, 0, float('inf'))
        
        current_time = time.time()
        dt = 0.02  # Assume 50Hz update rate
        time_since_gps = current_time - self.last_gps_time
        
        # Update heading from IMU (gyro integration + magnetometer)
        self.current_heading = math.degrees(imu.yaw)
        if self.current_heading < 0:
            self.current_heading += 360
        
        # Estimate ground velocity = airspeed vector + wind
        heading_rad = math.radians(self.current_heading)
        
        # Airspeed vector (in body frame -> NED frame)
        air_velocity_north = airspeed * math.cos(heading_rad)
        air_velocity_east = airspeed * math.sin(heading_rad)
        
        # Ground velocity = air velocity + wind
        self.velocity_north = air_velocity_north + self.wind_north
        self.velocity_east = air_velocity_east + self.wind_east
        
        # Integrate acceleration for velocity correction
        # Transform body accelerations to NED frame
        cos_roll = math.cos(imu.roll)
        cos_pitch = math.cos(imu.pitch)
        sin_roll = math.sin(imu.roll)
        sin_pitch = math.sin(imu.pitch)
        cos_yaw = math.cos(imu.yaw)
        sin_yaw = math.sin(imu.yaw)
        
        # Simplified rotation (proper DCM needed for accuracy)
        accel_north = imu.accel_x * cos_yaw - imu.accel_y * sin_yaw
        accel_east = imu.accel_x * sin_yaw + imu.accel_y * cos_yaw
        
        # Apply acceleration correction (small dt)
        self.velocity_north += accel_north * dt
        self.velocity_east += accel_east * dt
        
        # Update position (integrate velocity)
        # Convert velocity to lat/lon change
        dlat = (self.velocity_north * dt) / self.EARTH_RADIUS
        dlon = (self.velocity_east * dt) / (self.EARTH_RADIUS * math.cos(math.radians(self.current_lat)))
        
        self.current_lat += math.degrees(dlat)
        self.current_lon += math.degrees(dlon)
        
        # Altitude from barometer (via IMU/FC) - more stable than GPS
        # For now, assume constant or use accelerometer z
        self.velocity_down += (imu.accel_z + 9.81) * dt  # Remove gravity
        self.current_alt -= self.velocity_down * dt
        
        # Update error estimate
        self.estimated_error += self.error_growth_rate * dt
        
        # Decay confidence
        self.confidence = max(0.1, self.confidence - self.confidence_decay_rate * dt)
        
        # Log periodically
        if int(time_since_gps) % 5 == 0 and int(time_since_gps * 10) % 50 == 0:
            logger.info(f"DR Position: ({self.current_lat:.6f}, {self.current_lon:.6f}), "
                       f"Error: ±{self.estimated_error:.0f}m, Confidence: {self.confidence:.0%}")
        
        return DeadReckonPosition(
            lat=self.current_lat,
            lon=self.current_lon,
            alt=self.current_alt,
            heading=self.current_heading,
            confidence=self.confidence,
            time_since_gps=time_since_gps,
            estimated_error=self.estimated_error
        )
    
    def stop_dead_reckoning(self, recovered_gps: GPSReading):
        """Dừng DR khi GPS phục hồi"""
        if self.is_active:
            # Calculate actual error
            actual_error = self._haversine(
                self.current_lat, self.current_lon,
                recovered_gps.lat, recovered_gps.lon
            )
            
            logger.success(f"✅ GPS RECOVERED! DR ran for {time.time() - self.dr_start_time:.1f}s")
            logger.info(f"DR estimated: ({self.current_lat:.6f}, {self.current_lon:.6f})")
            logger.info(f"Actual GPS:   ({recovered_gps.lat:.6f}, {recovered_gps.lon:.6f})")
            logger.info(f"DR Error: {actual_error:.1f}m (estimated: {self.estimated_error:.1f}m)")
            
            self.is_active = False
    
    def get_distance_traveled(self) -> float:
        """Khoảng cách đã bay từ điểm mất GPS"""
        if not self.last_gps:
            return 0
        return self._haversine(
            self.last_gps.lat, self.last_gps.lon,
            self.current_lat, self.current_lon
        )
    
    def get_heading_to_last_gps(self) -> float:
        """Hướng bay ngược về vị trí GPS cuối"""
        if not self.last_gps:
            return 0
        return self._calculate_bearing(
            self.current_lat, self.current_lon,
            self.last_gps.lat, self.last_gps.lon
        )
    
    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Khoảng cách giữa 2 điểm (meters)"""
        R = 6371000
        lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    @staticmethod
    def _calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Tính bearing từ điểm 1 đến điểm 2 (degrees)"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon = math.radians(lon2 - lon1)
        
        x = math.sin(dlon) * math.cos(lat2_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
        
        bearing = math.atan2(x, y)
        return (math.degrees(bearing) + 360) % 360


class GPSDenialHandler:
    """
    Main handler cho GPS denial situations
    
    Coordinates:
    - Anomaly detection
    - Dead reckoning navigation
    - Escape maneuvers
    - Pilot alerts
    - Recovery procedures
    """
    
    def __init__(self, mavlink_handler):
        """
        Initialize GPS Denial Handler
        
        Args:
            mavlink_handler: MAVLink handler để gửi lệnh đến FC
        """
        self.mavlink = mavlink_handler
        
        # Sub-systems
        self.detector = GPSAnomalyDetector()
        self.navigator = DeadReckoningNavigator()
        
        # State
        self.current_state = GPSState.NORMAL
        self.previous_state = GPSState.NORMAL
        self.denial_events: List[GPSDenialEvent] = []
        self.current_event: Optional[GPSDenialEvent] = None
        
        # Home position (for distance calculations)
        self.home_lat: float = 0
        self.home_lon: float = 0
        self.home_alt: float = 0
        
        # Configuration
        self.escape_action = EscapeAction.CLIMB_AND_REVERSE
        self.escape_altitude_gain = 30  # meters to climb
        self.escape_heading_time = 30   # seconds to fly reverse heading
        self.min_confidence_for_navigation = 0.3
        
        # Alert cooldown
        self.last_alert_time = 0
        self.alert_cooldown = 10  # seconds
        
        # Monitoring thread
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        logger.info("GPS Denial Handler initialized")
    
    def set_home(self, lat: float, lon: float, alt: float):
        """Set home position"""
        self.home_lat = lat
        self.home_lon = lon
        self.home_alt = alt
        logger.info(f"Home set: ({lat:.6f}, {lon:.6f}, {alt:.1f}m)")
    
    def update_gps(self, lat: float, lon: float, alt: float, 
                   ground_speed: float, heading: float,
                   satellites: int, hdop: float, fix_type: int):
        """
        Update GPS reading và check for anomalies
        
        Gọi hàm này mỗi khi nhận GPS update từ MAVLink
        """
        reading = GPSReading(
            timestamp=time.time(),
            lat=lat, lon=lon, alt=alt,
            ground_speed=ground_speed,
            heading=heading,
            satellites=satellites,
            hdop=hdop,
            fix_type=fix_type
        )
        
        # Check for anomalies
        is_anomaly, score, reason = self.detector.update_gps(reading)
        
        # Update state
        self.previous_state = self.current_state
        self.current_state = self.detector.get_state()
        
        # Handle state transitions
        self._handle_state_transition(reading, reason)
        
        # If in DR mode, update navigator
        if self.navigator.is_active:
            # GPS recovered?
            if self.current_state == GPSState.NORMAL:
                self._handle_gps_recovery(reading)
    
    def update_imu(self, roll: float, pitch: float, yaw: float,
                   roll_rate: float, pitch_rate: float, yaw_rate: float,
                   accel_x: float, accel_y: float, accel_z: float):
        """Update IMU reading"""
        reading = IMUReading(
            timestamp=time.time(),
            roll=roll, pitch=pitch, yaw=yaw,
            roll_rate=roll_rate, pitch_rate=pitch_rate, yaw_rate=yaw_rate,
            accel_x=accel_x, accel_y=accel_y, accel_z=accel_z
        )
        
        self.detector.update_imu(reading)
        
        # If in DR mode, update position
        if self.navigator.is_active:
            dr_position = self.navigator.update(reading)
            
            # Check if should execute escape
            if dr_position.confidence >= self.min_confidence_for_navigation:
                self._update_escape_maneuver(dr_position)
            else:
                logger.warning(f"DR confidence too low ({dr_position.confidence:.0%}), cannot navigate")
    
    def _handle_state_transition(self, gps: GPSReading, reason: str):
        """Handle state changes"""
        if self.previous_state == GPSState.NORMAL:
            # Entering denial state
            if self.current_state in [GPSState.SUSPECTED_JAM, GPSState.CONFIRMED_JAM]:
                self._start_denial_response(gps, reason)
        
        elif self.current_state == GPSState.NORMAL:
            # Exiting denial state
            if self.previous_state in [GPSState.SUSPECTED_JAM, GPSState.CONFIRMED_JAM]:
                self._handle_gps_recovery(gps)
    
    def _start_denial_response(self, last_gps: GPSReading, reason: str):
        """Bắt đầu xử lý GPS denial"""
        logger.error(f"🚨 GPS DENIAL DETECTED: {reason}")
        
        # Start dead reckoning
        wind_estimate = self._estimate_wind()
        self.navigator.start_dead_reckoning(last_gps, wind_estimate)
        
        # Create event
        self.current_event = GPSDenialEvent(
            start_time=time.time(),
            end_time=None,
            start_position=(last_gps.lat, last_gps.lon, last_gps.alt),
            denial_type=self.current_state,
            escape_action=self.escape_action,
            max_dr_error=0,
            recovered=False
        )
        
        # Alert pilot
        self._alert_pilot("GPS JAMMING DETECTED! Initiating escape maneuver.")
        
        # Execute escape maneuver
        self._execute_escape_maneuver(last_gps)
    
    def _execute_escape_maneuver(self, last_gps: GPSReading):
        """Thực hiện escape maneuver"""
        logger.warning(f"🛫 Executing escape: {self.escape_action.value}")
        
        if self.escape_action == EscapeAction.REVERSE_HEADING:
            # Bay ngược hướng cũ
            reverse_heading = (last_gps.heading + 180) % 360
            self._command_heading(reverse_heading)
            
        elif self.escape_action == EscapeAction.CLIMB_AND_REVERSE:
            # Tăng độ cao trước, sau đó bay ngược
            target_alt = last_gps.alt + self.escape_altitude_gain
            reverse_heading = (last_gps.heading + 180) % 360
            
            logger.info(f"Climbing to {target_alt:.0f}m, then heading {reverse_heading:.0f}°")
            self._command_altitude(target_alt)
            self._command_heading(reverse_heading)
            
        elif self.escape_action == EscapeAction.LOITER:
            # Switch to LOITER mode
            self._command_mode("LOITER")
            
        elif self.escape_action == EscapeAction.EMERGENCY_LAND:
            # Emergency land
            self._command_land()
    
    def _update_escape_maneuver(self, dr_position: DeadReckonPosition):
        """Cập nhật escape maneuver dựa trên vị trí DR"""
        if not self.current_event:
            return
        
        # Update max error
        self.current_event.max_dr_error = max(
            self.current_event.max_dr_error,
            dr_position.estimated_error
        )
        
        # Check if should adjust heading (pointing toward last GPS)
        heading_to_safety = self.navigator.get_heading_to_last_gps()
        
        # Re-command heading periodically
        if int(dr_position.time_since_gps) % 10 == 0:
            self._command_heading(heading_to_safety)
            logger.info(f"Adjusting heading to {heading_to_safety:.0f}° (toward last known position)")
    
    def _handle_gps_recovery(self, gps: GPSReading):
        """Xử lý khi GPS phục hồi"""
        self.navigator.stop_dead_reckoning(gps)
        
        if self.current_event:
            self.current_event.end_time = time.time()
            self.current_event.recovered = True
            self.denial_events.append(self.current_event)
            self.current_event = None
        
        # Alert pilot
        duration = time.time() - self.navigator.dr_start_time if self.navigator.dr_start_time else 0
        self._alert_pilot(f"GPS RECOVERED after {duration:.0f}s! Resuming normal navigation.")
        
        # Could auto-RTH here or resume mission
        # For now, switch to LOITER to let pilot decide
        self._command_mode("LOITER")
    
    def _estimate_wind(self) -> Tuple[float, float]:
        """Ước lượng gió từ GPS history"""
        # Simple: so sánh ground speed vs airspeed
        # Cần airspeed sensor để làm đúng
        # Tạm thời return (0, 0)
        return (0.0, 0.0)
    
    def _alert_pilot(self, message: str):
        """Gửi cảnh báo đến pilot qua MAVLink STATUSTEXT"""
        current_time = time.time()
        if current_time - self.last_alert_time >= self.alert_cooldown:
            logger.warning(f"📢 PILOT ALERT: {message}")
            
            # Gửi qua MAVLink
            if hasattr(self.mavlink, 'send_statustext'):
                self.mavlink.send_statustext(message, severity=2)  # CRITICAL
            
            self.last_alert_time = current_time
    
    def _command_heading(self, heading: float):
        """Gửi lệnh heading đến FC"""
        logger.info(f"Commanding heading: {heading:.0f}°")
        if hasattr(self.mavlink, 'set_heading'):
            self.mavlink.set_heading(heading)
    
    def _command_altitude(self, altitude: float):
        """Gửi lệnh altitude đến FC"""
        logger.info(f"Commanding altitude: {altitude:.0f}m")
        if hasattr(self.mavlink, 'set_altitude'):
            self.mavlink.set_altitude(altitude)
    
    def _command_mode(self, mode: str):
        """Gửi lệnh mode đến FC"""
        logger.info(f"Commanding mode: {mode}")
        if hasattr(self.mavlink, 'set_mode'):
            self.mavlink.set_mode(mode)
    
    def _command_land(self):
        """Gửi lệnh land đến FC"""
        logger.warning("Commanding EMERGENCY LAND")
        if hasattr(self.mavlink, 'land'):
            self.mavlink.land()
    
    def get_status(self) -> Dict:
        """Get current status"""
        return {
            "gps_state": self.current_state.value,
            "anomaly_score": self.detector.anomaly_score,
            "dr_active": self.navigator.is_active,
            "dr_confidence": self.navigator.confidence if self.navigator.is_active else 1.0,
            "dr_error_estimate": self.navigator.estimated_error if self.navigator.is_active else 0,
            "dr_time": time.time() - self.navigator.dr_start_time if self.navigator.is_active else 0,
            "total_denial_events": len(self.denial_events)
        }


# ============================================================================
# Example usage and testing
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("GPS DENIAL HANDLER - TEST")
    print("=" * 70)
    
    # Mock MAVLink handler
    class MockMAVLink:
        def set_mode(self, mode):
            print(f"  → FC Mode: {mode}")
        
        def set_heading(self, heading):
            print(f"  → FC Heading: {heading:.0f}°")
        
        def set_altitude(self, alt):
            print(f"  → FC Altitude: {alt:.0f}m")
        
        def land(self):
            print(f"  → FC: LAND command")
        
        def send_statustext(self, msg, severity):
            print(f"  → STATUSTEXT [{severity}]: {msg}")
    
    handler = GPSDenialHandler(MockMAVLink())
    handler.set_home(21.028, 105.804, 10)
    
    print("\n1. Normal GPS updates...")
    for i in range(10):
        handler.update_gps(
            lat=21.028 + i * 0.0001,
            lon=105.804 + i * 0.0001,
            alt=50 + i,
            ground_speed=15,
            heading=45,
            satellites=12,
            hdop=0.8,
            fix_type=3
        )
        handler.update_imu(0.05, -0.02, math.radians(45), 0, 0, 0, 0.1, -0.1, -9.8)
        time.sleep(0.1)
    
    print(f"\nStatus: {handler.get_status()}")
    
    print("\n2. Simulating GPS JAMMING (satellites drop, position jump)...")
    # Simulate jamming: sudden satellite drop + position jump
    handler.update_gps(
        lat=21.030,  # Jump!
        lon=105.810,  # Jump!
        alt=50,
        ground_speed=15,
        heading=45,
        satellites=3,  # Low!
        hdop=5.0,  # High!
        fix_type=2  # Lost 3D fix
    )
    
    print(f"\nStatus after jam: {handler.get_status()}")
    
    print("\n3. Continuing with dead reckoning...")
    for i in range(20):
        handler.update_imu(0.05, -0.02, math.radians(225), 0, 0, 0.01, 0.1, -0.1, -9.8)
        time.sleep(0.1)
    
    print(f"\nStatus during DR: {handler.get_status()}")
    
    print("\n4. GPS RECOVERED!")
    handler.update_gps(
        lat=21.029,
        lon=105.805,
        alt=80,
        ground_speed=15,
        heading=225,
        satellites=14,
        hdop=0.7,
        fix_type=3
    )
    
    print(f"\nFinal status: {handler.get_status()}")
    print(f"\nDenial events: {len(handler.denial_events)}")
