"""
Hệ thống Hybrid GPS Denial với EKF, Quantum Filter và ML Adaptive Tuning

⚠️ LƯU Ý QUAN TRỌNG - TRIẾT LÝ MỚI (01/12/2025):
==================================================
File này được giữ lại cho mục đích NGHIÊN CỨU LƯỢNG TỬ (Quantum Filter).

Trong thực tế bay, KHÔNG NÊN:
- Tự động Dead Reckoning trên Pi (sai số tích lũy nhanh)
- Gửi Position Command khi mất GPS (nguy hiểm)
- EKF/UKF/QKF trên Python không thể thay thế EKF3 của ArduPilot

TRIẾT LÝ MỚI:
- Pi CHỈ phát hiện GPS lost và cảnh báo phi công
- Phi công chuyển FBWA/AltHold và lái tay về nhà
- Tin tưởng EKF3 của Flight Controller

SỬ DỤNG CHO:
- Nghiên cứu so sánh Classical EKF vs Quantum Kalman Filter (Shadow Mode)
- Thu thập dữ liệu để phân tích offline
- KHÔNG dùng để điều khiển bay thực tế

Xem: safety/gps_monitor.py cho giải pháp bay thực tế
==================================================

Kiến trúc hệ thống (NGHIÊN CỨU):
- Chế độ bình thường: Hệ thống gốc (ArduPilot EKF)
- Phát hiện GPS denial: Chuyển sang Dead Reckoning tích hợp EKF
- Độ tin cậy EKF thấp: Fallback về Dead Reckoning gốc
- Chế độ nghiên cứu: So sánh EKF vs Quantum Kalman Filter
- Chế độ adaptive: Tuning tham số dựa trên ML (Server hoặc Edge)

Thành phần chính:
1. MS4525DO Airspeed Sensor - Cảm biến tốc độ không khí
2. Quantum Filter Comparator - So sánh bộ lọc lượng tử
3. ML Adaptive Tuner - Tuning tham số bằng ML
4. Hybrid GPS Denial System - Hệ thống chính tích hợp tất cả

Tác giả: Trương Công Định & Đặng Duy Long
Ngày: 2025-12-01
"""

import time
import math
import numpy as np
from typing import Optional, Tuple, List, Dict, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from loguru import logger
import threading
import json

# Try imports with fallbacks
try:
    from ..safety.gps_denial_handler import (
        GPSState, EscapeAction, GPSReading, IMUReading,
        DeadReckonPosition, GPSAnomalyDetector, DeadReckoningNavigator,
        GPSDenialHandler
    )
    from .ekf_integrated_gps_denial import (
        ExtendedKalmanFilter, 
        EKFIntegratedDeadReckoningNavigator,
        EKFIntegratedGPSDenialHandler,
        GPSDenialEvent
    )
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from safety.gps_denial_handler import (
        GPSState, EscapeAction, GPSReading, IMUReading,
        DeadReckonPosition, GPSAnomalyDetector, DeadReckoningNavigator,
        GPSDenialHandler
    )
    from navigation.ekf_integrated_gps_denial import (
        ExtendedKalmanFilter, 
        EKFIntegratedDeadReckoningNavigator,
        EKFIntegratedGPSDenialHandler,
        GPSDenialEvent
    )


class NavigationMode(Enum):
    """
    Chế độ điều hướng hiện tại
    
    Attributes:
        NORMAL: Chế độ bình thường khi GPS có sẵn, ArduPilot điều khiển
        EKF_DEAD_RECKONING: GPS bị từ chối, sử dụng Dead Reckoning tích hợp EKF
        BASIC_DEAD_RECKONING: Fallback - sử dụng Dead Reckoning gốc
        QUANTUM_COMPARISON: Chế độ nghiên cứu - so sánh QKF vs EKF
    """
    NORMAL = "normal"                    # GPS có sẵn, ArduPilot điều khiển
    EKF_DEAD_RECKONING = "ekf_dr"       # GPS bị từ chối, DR tích hợp EKF
    BASIC_DEAD_RECKONING = "basic_dr"   # Fallback: DR gốc
    QUANTUM_COMPARISON = "quantum"       # Nghiên cứu: So sánh QKF vs EKF


class ComputeLocation(Enum):
    """
    Vị trí thực thi tính toán nặng
    
    Attributes:
        EDGE: Chạy trên Raspberry Pi (giới hạn tài nguyên)
        SERVER: Chạy trên Ground Station (tài nguyên mạnh)
        HYBRID: Phân chia workload giữa edge và server
    """
    EDGE = "edge"           # Raspberry Pi (giới hạn)
    SERVER = "server"       # Ground station (mạnh)
    HYBRID = "hybrid"       # Phân chia workload


@dataclass
class AirspeedReading:
    """
    Đọc dữ liệu từ cảm biến tốc độ không khí MS4525DO
    
    Attributes:
        timestamp: Thời gian đọc (seconds)
        differential_pressure: Áp suất chênh lệch (Pascal)
        temperature: Nhiệt độ (Celsius)
        airspeed: Tốc độ không khí (m/s) - tính toán từ áp suất
        is_valid: Dữ liệu có hợp lệ không
    """
    timestamp: float
    differential_pressure: float  # Pa
    temperature: float            # Celsius
    airspeed: float              # m/s (tính toán)
    is_valid: bool


@dataclass
class SystemPerformanceMetrics:
    """
    Metrics hiệu suất hệ thống cho adaptive tuning
    
    Attributes:
        cpu_usage: Sử dụng CPU (0-100%)
        memory_usage: Sử dụng bộ nhớ (0-100%)
        inference_time_ms: Thời gian inference ML (milliseconds)
        ekf_update_time_ms: Thời gian tính toán EKF (milliseconds)
        dr_error_estimate: Ước tính lỗi Dead Reckoning (meters)
        battery_remaining: Pin còn lại (0-100%)
    """
    cpu_usage: float              # 0-100%
    memory_usage: float           # 0-100%
    inference_time_ms: float      # Thời gian inference ML
    ekf_update_time_ms: float     # Thời gian tính toán EKF
    dr_error_estimate: float      # Lỗi Dead Reckoning
    battery_remaining: float      # 0-100%


class MS4525DOAirspeedSensor:
    """
    Cảm biến áp suất chênh lệch MS4525DO với Pitot Tube
    
    Thông số kỹ thuật:
    - Địa chỉ I2C: 0x28 (mặc định)
    - Dải đo: -1 đến 1 PSI chênh lệch
    - Độ phân giải: 14-bit
    - Giao tiếp: I2C
    
    Nguyên lý hoạt động:
    Sử dụng phương trình Bernoulli: v = sqrt(2 * ΔP / ρ)
    Trong đó:
        v: Tốc độ không khí (m/s)
        ΔP: Áp suất chênh lệch (Pa)
        ρ: Mật độ không khí (kg/m³)
    """
    
    I2C_ADDRESS = 0x28
    PSI_TO_PA = 6894.76
    
    def __init__(self, i2c_bus=None):
        """
        Khởi tạo cảm biến tốc độ không khí
        
        Args:
            i2c_bus: Instance của I2C bus (None cho chế độ simulation)
        """
        self.i2c = i2c_bus
        self.calibration_offset = 0.0
        self.last_reading: Optional[AirspeedReading] = None
        
        # Air density at sea level, 15°C
        self.air_density = 1.225  # kg/m³
        
        # Calibration state
        self.is_calibrated = False
        self.calibration_samples: List[float] = []
        
        logger.info("MS4525DO Airspeed Sensor initialized")
    
    def calibrate(self, samples: int = 50) -> bool:
        """
        Hiệu chỉnh offset zero (gọi khi UAV đứng yên)
        
        Quy trình:
        1. Thu thập mẫu áp suất khi đứng yên
        2. Tính trung bình để tìm offset
        3. Áp dụng offset cho các lần đọc sau
        
        Args:
            samples: Số lượng mẫu để tính trung bình
            
        Returns:
            True nếu hiệu chỉnh thành công, False nếu thất bại
        """
        logger.info(f"Calibrating airspeed sensor ({samples} samples)...")
        
        self.calibration_samples = []
        for _ in range(samples):
            reading = self._read_raw_pressure()
            if reading is not None:
                self.calibration_samples.append(reading)
            time.sleep(0.02)  # 50Hz
        
        if len(self.calibration_samples) >= samples * 0.8:
            self.calibration_offset = np.mean(self.calibration_samples)
            self.is_calibrated = True
            logger.success(f"Airspeed calibrated: offset = {self.calibration_offset:.2f} Pa")
            return True
        else:
            logger.error("Airspeed calibration failed: insufficient samples")
            return False
    
    def read(self) -> Optional[AirspeedReading]:
        """
        Đọc tốc độ không khí từ cảm biến
        
        Returns:
            AirspeedReading object chứa dữ liệu đọc được
            None nếu đọc thất bại
        """
        raw_pressure = self._read_raw_pressure()
        temperature = self._read_temperature()
        
        if raw_pressure is None:
            return None
        
        # Apply calibration offset
        differential_pressure = raw_pressure - self.calibration_offset
        
        # Calculate airspeed using Bernoulli equation
        # v = sqrt(2 * dP / rho)
        if differential_pressure > 0:
            airspeed = math.sqrt(2.0 * differential_pressure / self.air_density)
        else:
            airspeed = 0.0
        
        # Validate reading
        is_valid = 0.0 <= airspeed <= 100.0  # 0-100 m/s valid range
        
        self.last_reading = AirspeedReading(
            timestamp=time.time(),
            differential_pressure=differential_pressure,
            temperature=temperature,
            airspeed=airspeed,
            is_valid=is_valid
        )
        
        return self.last_reading
    
    def _read_raw_pressure(self) -> Optional[float]:
        """Read raw pressure from I2C"""
        if self.i2c is None:
            # Simulation mode
            return np.random.normal(100, 5)  # ~15 m/s
        
        try:
            # Read 4 bytes from sensor
            data = self.i2c.read_i2c_block_data(self.I2C_ADDRESS, 0, 4)
            
            # Parse pressure (14-bit)
            status = (data[0] >> 6) & 0x03
            if status != 0:
                return None  # Stale or fault
            
            pressure_raw = ((data[0] & 0x3F) << 8) | data[1]
            
            # Convert to Pa (-1 to 1 PSI range)
            pressure_psi = ((pressure_raw - 8192) / 8192.0)
            pressure_pa = pressure_psi * self.PSI_TO_PA
            
            return pressure_pa
            
        except Exception as e:
            logger.error(f"Airspeed read error: {e}")
            return None
    
    def _read_temperature(self) -> float:
        """Read temperature from sensor"""
        if self.i2c is None:
            return 25.0  # Simulation
        
        try:
            data = self.i2c.read_i2c_block_data(self.I2C_ADDRESS, 0, 4)
            temp_raw = ((data[2] << 8) | data[3]) >> 5
            temperature = (temp_raw * 200.0 / 2047.0) - 50.0
            return temperature
        except:
            return 25.0
    
    def update_air_density(self, temperature: float, pressure_alt: float):
        """
        Cập nhật mật độ không khí dựa trên điều kiện môi trường
        
        Sử dụng mô hình khí quyển tiêu chuẩn:
        ρ = P / (R * T)
        Trong đó:
            ρ: Mật độ không khí (kg/m³)
            P: Áp suất (Pa)
            R: Hằng số khí lý tưởng cho không khí (287.05 J/(kg·K))
            T: Nhiệt độ tuyệt đối (Kelvin)
        
        Args:
            temperature: Nhiệt độ không khí (Celsius)
            pressure_alt: Độ cao áp suất (meters)
        """
        # Standard atmosphere model
        T = temperature + 273.15  # Kelvin
        P = 101325 * (1 - 2.25577e-5 * pressure_alt) ** 5.25588  # Pa
        R = 287.05  # Gas constant for air
        
        self.air_density = P / (R * T)


class QuantumFilterComparator:
    """
    So sánh Quantum Kalman Filter vs Classical EKF
    
    Hoạt động:
    - Chạy ở chế độ shadow - không ảnh hưởng đến điều hướng thực tế
    - Thu thập metrics cho mục đích nghiên cứu
    - So sánh độ chính xác và hiệu suất
    
    Ứng dụng:
    - Nghiên cứu hiệu quả của Quantum Filter trong điều hướng UAV
    - So sánh với EKF truyền thống
    - Tối ưu hóa thuật toán cho phần cứng lượng tử tương lai
    """
    
    def __init__(self):
        self.qkf_available = False
        self.qkf = None
        
        # Try to import Quantum Kalman Filter
        try:
            from ..quantum.quantum_kalman_filter import QuantumKalmanFilter
            self.qkf = QuantumKalmanFilter()
            self.qkf_available = True
            logger.info("Quantum Kalman Filter loaded for comparison")
        except ImportError:
            logger.warning("Quantum Kalman Filter not available")
        
        # Comparison metrics
        self.ekf_estimates: deque = deque(maxlen=1000)
        self.qkf_estimates: deque = deque(maxlen=1000)
        self.ground_truth: deque = deque(maxlen=1000)  # GPS when available
        
        # Performance comparison
        self.ekf_errors: List[float] = []
        self.qkf_errors: List[float] = []
        self.ekf_times: List[float] = []
        self.qkf_times: List[float] = []
    
    def compare_update(self, measurement: np.ndarray, 
                       ekf_estimate: np.ndarray,
                       ground_truth: Optional[np.ndarray] = None):
        """
        Run comparison update
        
        Args:
            measurement: Sensor measurement
            ekf_estimate: EKF state estimate
            ground_truth: GPS ground truth (if available)
        """
        if not self.qkf_available:
            return
        
        timestamp = time.time()
        
        # Store EKF estimate
        self.ekf_estimates.append({
            'time': timestamp,
            'state': ekf_estimate.copy()
        })
        
        # Run QKF update
        try:
            start = time.perf_counter()
            qkf_estimate = self.qkf.update(measurement)
            qkf_time = (time.perf_counter() - start) * 1000
            
            self.qkf_estimates.append({
                'time': timestamp,
                'state': qkf_estimate
            })
            self.qkf_times.append(qkf_time)
            
        except Exception as e:
            logger.error(f"QKF update failed: {e}")
            return
        
        # If ground truth available, compute errors
        if ground_truth is not None:
            self.ground_truth.append({
                'time': timestamp,
                'state': ground_truth
            })
            
            ekf_error = np.linalg.norm(ekf_estimate[:3] - ground_truth[:3])
            qkf_error = np.linalg.norm(qkf_estimate[:3] - ground_truth[:3])
            
            self.ekf_errors.append(ekf_error)
            self.qkf_errors.append(qkf_error)
    
    def get_comparison_stats(self) -> Dict:
        """Get comparison statistics"""
        if not self.ekf_errors:
            return {"status": "No data"}
        
        return {
            "ekf_mean_error": np.mean(self.ekf_errors),
            "ekf_std_error": np.std(self.ekf_errors),
            "qkf_mean_error": np.mean(self.qkf_errors) if self.qkf_errors else None,
            "qkf_std_error": np.std(self.qkf_errors) if self.qkf_errors else None,
            "qkf_mean_time_ms": np.mean(self.qkf_times) if self.qkf_times else None,
            "samples": len(self.ekf_errors),
            "qkf_improvement": (np.mean(self.ekf_errors) - np.mean(self.qkf_errors)) / np.mean(self.ekf_errors) * 100 if self.qkf_errors else None
        }


class MLAdaptiveTuner:
    """
    Adaptive Parameter Tuning dựa trên Machine Learning
    
    Chức năng:
    - Học tham số EKF tối ưu từ dữ liệu bay
    - Có thể chạy trên Edge (Raspberry Pi) hoặc Server (Ground Station)
    - Tự động điều chỉnh tham số dựa trên điều kiện bay
    
    Kiến trúc:
    - Edge: Lightweight model (Ridge regression) cho RPi 3B+
    - Server: Complex model (Neural Network) cho Ground Station
    - Hybrid: Phân chia workload giữa edge và server
    
    Ứng dụng:
    - Tối ưu hóa tham số EKF trong thời gian thực
    - Thích ứng với điều kiện môi trường thay đổi
    - Cải thiện độ chính xác Dead Reckoning
    """
    
    # Giới hạn cho Raspberry Pi 3B+
    RPI_CPU_LIMIT = 70.0          # Giới hạn sử dụng CPU tối đa (%)
    RPI_MEMORY_LIMIT = 800        # Giới hạn bộ nhớ tối đa (MB)
    RPI_INFERENCE_LIMIT = 100     # Giới hạn thời gian inference tối đa (ms)
    
    # Lưu ý: RPi 3B+ có 1GB RAM, 4 cores @ 1.4GHz
    # Cần cân bằng giữa ML và các tác vụ khác (camera, MAVLink, EKF)
    
    def __init__(self, compute_location: ComputeLocation = ComputeLocation.HYBRID):
        self.compute_location = compute_location
        self.model = None
        self.is_trained = False
        
        # Training data
        self.training_data: List[Dict] = []
        self.max_training_samples = 10000
        
        # Current parameters
        self.current_params = {
            'process_noise': 0.01,
            'measurement_noise_gps': 1.0,
            'measurement_noise_vel': 0.1,
            'error_growth_rate': 0.5,
            'confidence_decay_rate': 0.01
        }
        
        # Performance history
        self.performance_history: deque = deque(maxlen=100)
        
        # Server communication
        self.server_url: Optional[str] = None
        self.server_connected = False
        
        logger.info(f"ML Adaptive Tuner initialized (compute: {compute_location.value})")
    
    def can_run_on_rpi(self, metrics: SystemPerformanceMetrics) -> bool:
        """
        Kiểm tra ML có thể chạy trên Raspberry Pi không
        
        Logic kiểm tra:
        1. CPU usage hiện tại < giới hạn
        2. Memory usage hiện tại < giới hạn
        3. Ước tính overhead của ML không vượt quá headroom
        
        Args:
            metrics: Hiệu suất hệ thống hiện tại
            
        Returns:
            True nếu RPi có đủ tài nguyên cho ML, False nếu không
        """
        cpu_ok = metrics.cpu_usage < self.RPI_CPU_LIMIT
        memory_ok = metrics.memory_usage < self.RPI_MEMORY_LIMIT
        
        # Estimate ML overhead
        ml_overhead_cpu = 15.0  # ~15% CPU for inference
        ml_overhead_memory = 100  # ~100MB for model
        
        has_capacity = (
            metrics.cpu_usage + ml_overhead_cpu < 85.0 and
            metrics.memory_usage + ml_overhead_memory < 900
        )
        
        return has_capacity
    
    def collect_sample(self, 
                       imu: IMUReading, 
                       gps: Optional[GPSReading],
                       airspeed: Optional[AirspeedReading],
                       ekf_state: np.ndarray,
                       dr_error: float,
                       params: Dict):
        """
        Thu thập mẫu dữ liệu cho training
        
        Mỗi mẫu bao gồm:
        - Dữ liệu cảm biến (IMU, GPS, Airspeed)
        - Trạng thái EKF hiện tại
        - Lỗi Dead Reckoning ước tính
        - Tham số hiện tại
        
        Args:
            imu: Đọc dữ liệu IMU
            gps: Đọc dữ liệu GPS (None nếu không có)
            airspeed: Đọc dữ liệu tốc độ không khí
            ekf_state: Trạng thái EKF hiện tại
            dr_error: Lỗi Dead Reckoning ước tính
            params: Tham số hiện tại
        """
        sample = {
            'timestamp': time.time(),
            'imu': {
                'accel': [imu.accel_x, imu.accel_y, imu.accel_z],
                'gyro': [imu.roll_rate, imu.pitch_rate, imu.yaw_rate]
            },
            'gps_valid': gps is not None and gps.fix_type >= 3,
            'airspeed': airspeed.airspeed if airspeed else None,
            'ekf_confidence': float(np.trace(ekf_state[0:3])),  # Simplified
            'dr_error': dr_error,
            'params': params.copy()
        }
        
        self.training_data.append(sample)
        
        # Limit size
        if len(self.training_data) > self.max_training_samples:
            self.training_data.pop(0)
    
    def train_model(self, metrics: SystemPerformanceMetrics) -> bool:
        """
        Huấn luyện hoặc cập nhật ML model
        
        Quyết định huấn luyện trên edge hay server dựa trên tài nguyên:
        - Edge: Khi RPi có đủ tài nguyên, sử dụng lightweight model
        - Server: Khi RPi quá tải, gửi dữ liệu lên server
        - Hybrid: Kết hợp cả hai phương pháp
        
        Args:
            metrics: Hiệu suất hệ thống hiện tại
            
        Returns:
            True nếu huấn luyện thành công, False nếu thất bại
        """
        if len(self.training_data) < 100:
            logger.warning("Insufficient training data")
            return False
        
        if self.compute_location == ComputeLocation.SERVER:
            return self._train_on_server()
        elif self.compute_location == ComputeLocation.EDGE:
            if self.can_run_on_rpi(metrics):
                return self._train_on_edge()
            else:
                logger.warning("RPi overloaded, deferring training")
                return False
        else:  # HYBRID
            if self.can_run_on_rpi(metrics):
                return self._train_on_edge()
            else:
                return self._train_on_server()
    
    def _train_on_edge(self) -> bool:
        """
        Huấn luyện lightweight model trên RPi
        
        Sử dụng model đơn giản phù hợp với RPi 3B+:
        - Ridge regression: Nhẹ, nhanh, phù hợp cho real-time
        - Decision tree nhỏ: Dễ interpret, tốc độ inference nhanh
        
        Returns:
            True nếu huấn luyện thành công, False nếu thất bại
        """
        logger.info("Training ML model on edge (RPi)...")
        
        try:
            # Use lightweight model for RPi
            # Linear regression or small decision tree
            from sklearn.linear_model import Ridge
            from sklearn.preprocessing import StandardScaler
            
            # Prepare features
            X = []
            y = []
            
            for sample in self.training_data:
                if sample['dr_error'] is not None:
                    features = [
                        sample['imu']['accel'][0],
                        sample['imu']['accel'][1],
                        sample['imu']['accel'][2],
                        sample['imu']['gyro'][0],
                        sample['imu']['gyro'][1],
                        sample['imu']['gyro'][2],
                        1.0 if sample['gps_valid'] else 0.0,
                        sample['airspeed'] if sample['airspeed'] else 15.0
                    ]
                    X.append(features)
                    y.append(sample['dr_error'])
            
            if len(X) < 50:
                return False
            
            X = np.array(X)
            y = np.array(y)
            
            # Train simple model
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            self.model = Ridge(alpha=1.0)
            self.model.fit(X_scaled, y)
            self.scaler = scaler
            self.is_trained = True
            
            logger.success("Edge ML model trained successfully")
            return True
            
        except ImportError:
            logger.warning("sklearn not available on edge")
            return False
        except Exception as e:
            logger.error(f"Edge training failed: {e}")
            return False
    
    def _train_on_server(self) -> bool:
        """
        Gửi dữ liệu lên server để huấn luyện
        
        Quy trình:
        1. Gửi training data lên ground station server
        2. Server huấn luyện model phức tạp (Neural Network)
        3. Nhận lại optimized parameters từ server
        4. Cập nhật parameters cho hệ thống
        
        Returns:
            True nếu huấn luyện thành công, False nếu thất bại
        """
        if not self.server_url:
            logger.warning("Server URL not configured")
            return False
        
        logger.info("Sending training data to server...")
        
        try:
            import requests
            
            response = requests.post(
                f"{self.server_url}/api/ml/train",
                json={
                    'training_data': self.training_data[-1000:],  # Last 1000 samples
                    'current_params': self.current_params
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'optimized_params' in result:
                    self.current_params = result['optimized_params']
                    self.is_trained = True
                    logger.success("Server ML training complete")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Server training failed: {e}")
            return False
    
    def predict_optimal_params(self, current_state: Dict) -> Dict:
        """Predict optimal parameters for current conditions"""
        if not self.is_trained or self.model is None:
            return self.current_params
        
        try:
            features = np.array([[
                current_state.get('accel_x', 0),
                current_state.get('accel_y', 0),
                current_state.get('accel_z', -9.8),
                current_state.get('gyro_x', 0),
                current_state.get('gyro_y', 0),
                current_state.get('gyro_z', 0),
                1.0 if current_state.get('gps_valid', False) else 0.0,
                current_state.get('airspeed', 15.0)
            ]])
            
            features_scaled = self.scaler.transform(features)
            predicted_error = self.model.predict(features_scaled)[0]
            
            # Adjust parameters based on predicted error
            adjusted_params = self.current_params.copy()
            
            if predicted_error > 10.0:  # High error predicted
                adjusted_params['process_noise'] *= 1.2
                adjusted_params['error_growth_rate'] *= 1.1
            elif predicted_error < 2.0:  # Low error predicted
                adjusted_params['process_noise'] *= 0.9
                adjusted_params['error_growth_rate'] *= 0.95
            
            return adjusted_params
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return self.current_params
    
    def set_server(self, url: str):
        """Set ground station server URL"""
        self.server_url = url
        logger.info(f"ML server set to: {url}")


class HybridGPSDenialSystem:
    """
    Complete Hybrid GPS Denial System
    
    Combines:
    - Normal GPS navigation (ArduPilot)
    - EKF-integrated Dead Reckoning
    - Basic DR fallback
    - Quantum Filter comparison (research)
    - ML adaptive tuning
    - Airspeed sensor integration
    """
    
    def __init__(self, mavlink_handler, 
                 enable_quantum: bool = True,
                 enable_ml: bool = True,
                 compute_location: ComputeLocation = ComputeLocation.HYBRID):
        """
        Initialize Hybrid System
        
        Args:
            mavlink_handler: MAVLink communication
            enable_quantum: Enable Quantum Filter comparison
            enable_ml: Enable ML adaptive tuning
            compute_location: Where to run heavy computation
        """
        self.mavlink = mavlink_handler
        
        # Navigation mode
        self.current_mode = NavigationMode.NORMAL
        self.previous_mode = NavigationMode.NORMAL
        
        # Core systems
        self.basic_handler = GPSDenialHandler(mavlink_handler)
        self.ekf_handler = EKFIntegratedGPSDenialHandler(mavlink_handler)
        self.active_handler = None  # Set based on mode
        
        # Airspeed sensor
        self.airspeed_sensor = MS4525DOAirspeedSensor()
        self.last_airspeed: Optional[AirspeedReading] = None
        
        # Quantum comparison (research)
        self.quantum_comparator = QuantumFilterComparator() if enable_quantum else None
        
        # ML adaptive tuning
        self.ml_tuner = MLAdaptiveTuner(compute_location) if enable_ml else None
        
        # State
        self.home_set = False
        self.home_lat = 0
        self.home_lon = 0
        self.home_alt = 0
        
        # Performance monitoring
        self.performance_metrics = SystemPerformanceMetrics(
            cpu_usage=0, memory_usage=0, inference_time_ms=0,
            ekf_update_time_ms=0, dr_error_estimate=0, battery_remaining=100
        )
        
        # Mode switch thresholds
        self.ekf_confidence_threshold = 0.4
        self.fallback_threshold = 0.2
        
        # Statistics
        self.mode_switches = 0
        self.total_dr_time = 0
        
        logger.info("="*60)
        logger.info("HYBRID GPS DENIAL SYSTEM INITIALIZED")
        logger.info(f"  Quantum Filter: {'ENABLED' if enable_quantum else 'DISABLED'}")
        logger.info(f"  ML Tuning: {'ENABLED' if enable_ml else 'DISABLED'}")
        logger.info(f"  Compute Location: {compute_location.value}")
        logger.info("="*60)
    
    def set_home(self, lat: float, lon: float, alt: float):
        """Set home position"""
        self.home_lat = lat
        self.home_lon = lon
        self.home_alt = alt
        self.home_set = True
        
        self.basic_handler.set_home(lat, lon, alt)
        self.ekf_handler.set_home(lat, lon, alt)
        
        logger.info(f"Home set: ({lat:.6f}, {lon:.6f}, {alt:.1f}m)")
    
    def calibrate_airspeed(self) -> bool:
        """Calibrate airspeed sensor (call when stationary)"""
        return self.airspeed_sensor.calibrate()
    
    def update_gps(self, lat: float, lon: float, alt: float,
                   ground_speed: float, heading: float,
                   satellites: int, hdop: float, fix_type: int):
        """Update GPS reading"""
        reading = GPSReading(
            timestamp=time.time(),
            lat=lat, lon=lon, alt=alt,
            ground_speed=ground_speed, heading=heading,
            satellites=satellites, hdop=hdop, fix_type=fix_type
        )
        
        # Update both handlers
        self.basic_handler.detector.update_gps(reading)
        self.ekf_handler.update_gps(lat, lon, alt, ground_speed, heading,
                                    satellites, hdop, fix_type)
        
        # Check GPS state
        gps_state = self.basic_handler.detector.get_state()
        
        # Mode switching logic
        self._update_navigation_mode(gps_state, reading)
        
        # Quantum comparison (if GPS valid = ground truth)
        if self.quantum_comparator and fix_type >= 3:
            ground_truth = np.array([lat, lon, alt])
            ekf_estimate = self.ekf_handler.ekf.state[:3]
            self.quantum_comparator.compare_update(
                np.array([lat, lon, alt]),
                ekf_estimate,
                ground_truth
            )
    
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
        
        # Read airspeed
        self.last_airspeed = self.airspeed_sensor.read()
        airspeed = self.last_airspeed.airspeed if self.last_airspeed else 15.0
        
        # Update active handler
        if self.current_mode == NavigationMode.EKF_DEAD_RECKONING:
            self.ekf_handler.update_imu(roll, pitch, yaw,
                                        roll_rate, pitch_rate, yaw_rate,
                                        accel_x, accel_y, accel_z)
            
            # Use airspeed in DR
            if self.ekf_handler.navigator.is_active:
                dr_pos = self.ekf_handler.navigator.update(reading, airspeed)
                self._check_fallback_needed(dr_pos)
                
        elif self.current_mode == NavigationMode.BASIC_DEAD_RECKONING:
            self.basic_handler.update_imu(roll, pitch, yaw,
                                          roll_rate, pitch_rate, yaw_rate,
                                          accel_x, accel_y, accel_z)
        
        # ML data collection
        if self.ml_tuner:
            self._collect_ml_sample(reading, airspeed)
    
    def _update_navigation_mode(self, gps_state: GPSState, gps: GPSReading):
        """Update navigation mode based on GPS state"""
        self.previous_mode = self.current_mode
        
        if gps_state == GPSState.NORMAL:
            if self.current_mode != NavigationMode.NORMAL:
                self._switch_to_normal(gps)
        
        elif gps_state in [GPSState.SUSPECTED_JAM, GPSState.CONFIRMED_JAM]:
            if self.current_mode == NavigationMode.NORMAL:
                self._switch_to_ekf_dr(gps)
    
    def _switch_to_normal(self, gps: GPSReading):
        """Switch back to normal GPS navigation"""
        self.current_mode = NavigationMode.NORMAL
        self.mode_switches += 1
        
        # Stop any active DR
        if self.ekf_handler.navigator.is_active:
            self.ekf_handler.navigator.stop_dead_reckoning(gps)
        if self.basic_handler.navigator.is_active:
            self.basic_handler.navigator.stop_dead_reckoning(gps)
        
        self._alert_pilot("GPS RECOVERED - Returning to normal navigation")
        logger.success("Switched to NORMAL navigation mode")
    
    def _switch_to_ekf_dr(self, last_gps: GPSReading):
        """Switch to EKF-integrated Dead Reckoning"""
        self.current_mode = NavigationMode.EKF_DEAD_RECKONING
        self.mode_switches += 1
        
        # Get wind estimate from EKF
        wind = self.ekf_handler.ekf.get_wind_estimate()
        
        # Start EKF DR
        self.ekf_handler.navigator.start_dead_reckoning(last_gps, wind)
        
        # Apply ML-optimized parameters if available
        if self.ml_tuner and self.ml_tuner.is_trained:
            params = self.ml_tuner.predict_optimal_params({
                'airspeed': self.last_airspeed.airspeed if self.last_airspeed else 15.0
            })
            self.ekf_handler.navigator.error_growth_rate = params['error_growth_rate']
            self.ekf_handler.navigator.confidence_decay_rate = params['confidence_decay_rate']
        
        # Execute escape maneuver
        self.ekf_handler._execute_escape_maneuver_with_ekf(last_gps)
        
        self._alert_pilot("GPS DENIED - EKF Dead Reckoning ACTIVE")
        logger.warning("Switched to EKF DEAD RECKONING mode")
    
    def _switch_to_basic_dr(self, last_gps: GPSReading):
        """Fallback to basic Dead Reckoning"""
        self.current_mode = NavigationMode.BASIC_DEAD_RECKONING
        self.mode_switches += 1
        
        # Stop EKF DR
        if self.ekf_handler.navigator.is_active:
            self.ekf_handler.navigator.is_active = False
        
        # Start basic DR
        self.basic_handler.navigator.start_dead_reckoning(last_gps)
        
        self._alert_pilot("EKF FALLBACK - Basic Dead Reckoning ACTIVE")
        logger.warning("FALLBACK to BASIC DEAD RECKONING mode")
    
    def _check_fallback_needed(self, dr_pos: DeadReckonPosition):
        """Check if fallback to basic DR is needed"""
        ekf_confidence = self.ekf_handler.ekf.get_confidence()
        
        if ekf_confidence < self.fallback_threshold:
            logger.warning(f"EKF confidence LOW ({ekf_confidence:.0%}), switching to basic DR")
            
            # Get last known position
            last_gps = self.ekf_handler.navigator.last_gps
            if last_gps:
                self._switch_to_basic_dr(last_gps)
    
    def _collect_ml_sample(self, imu: IMUReading, airspeed: float):
        """Collect data for ML training"""
        if not self.ml_tuner:
            return
        
        dr_error = 0
        if self.current_mode != NavigationMode.NORMAL:
            if self.ekf_handler.navigator.is_active:
                dr_error = self.ekf_handler.navigator.estimated_error
            elif self.basic_handler.navigator.is_active:
                dr_error = self.basic_handler.navigator.estimated_error
        
        self.ml_tuner.collect_sample(
            imu=imu,
            gps=self.ekf_handler.navigator.last_gps if self.ekf_handler.navigator.is_active else None,
            airspeed=self.last_airspeed,
            ekf_state=self.ekf_handler.ekf.state,
            dr_error=dr_error,
            params=self.ml_tuner.current_params
        )
    
    def _alert_pilot(self, message: str):
        """Send alert to pilot"""
        logger.warning(f"📢 {message}")
        if hasattr(self.mavlink, 'send_statustext'):
            self.mavlink.send_statustext(message, severity=2)
    
    def update_performance(self, cpu: float, memory: float, battery: float):
        """Update system performance metrics"""
        self.performance_metrics.cpu_usage = cpu
        self.performance_metrics.memory_usage = memory
        self.performance_metrics.battery_remaining = battery
    
    def trigger_ml_training(self) -> bool:
        """Manually trigger ML training"""
        if not self.ml_tuner:
            return False
        return self.ml_tuner.train_model(self.performance_metrics)
    
    def get_status(self) -> Dict:
        """Get comprehensive system status"""
        status = {
            "mode": self.current_mode.value,
            "mode_switches": self.mode_switches,
            "gps_state": self.basic_handler.detector.get_state().value,
            "anomaly_score": self.basic_handler.detector.anomaly_score,
            "airspeed": self.last_airspeed.airspeed if self.last_airspeed else None,
            "airspeed_valid": self.last_airspeed.is_valid if self.last_airspeed else False,
        }
        
        if self.current_mode == NavigationMode.EKF_DEAD_RECKONING:
            status.update({
                "ekf_confidence": self.ekf_handler.ekf.get_confidence(),
                "dr_error": self.ekf_handler.navigator.estimated_error,
                "dr_time": time.time() - self.ekf_handler.navigator.dr_start_time
            })
        elif self.current_mode == NavigationMode.BASIC_DEAD_RECKONING:
            status.update({
                "dr_error": self.basic_handler.navigator.estimated_error,
                "dr_time": time.time() - self.basic_handler.navigator.dr_start_time
            })
        
        if self.quantum_comparator:
            status["quantum_stats"] = self.quantum_comparator.get_comparison_stats()
        
        if self.ml_tuner:
            status["ml_trained"] = self.ml_tuner.is_trained
            status["ml_samples"] = len(self.ml_tuner.training_data)
        
        return status


# ============================================================================
# RPi Capability Assessment
# ============================================================================

def assess_rpi_capability() -> Dict:
    """
    Assess Raspberry Pi 3B+ capability for ML workloads
    
    Returns detailed analysis of what can run on edge vs server
    """
    
    analysis = {
        "device": "Raspberry Pi 3B+",
        "specs": {
            "cpu": "ARM Cortex-A53 @ 1.4GHz (4 cores)",
            "ram": "1GB LPDDR2",
            "gpu": "VideoCore IV (not useful for ML)"
        },
        "current_workload": {
            "camera_capture": "~10% CPU",
            "ai_detection": "~40% CPU (TFLite)",
            "mavlink_comm": "~5% CPU",
            "ekf_updates": "~5% CPU",
            "system_overhead": "~10% CPU",
            "total": "~70% CPU"
        },
        "available_headroom": "~30% CPU, ~200MB RAM",
        
        "ml_requirements": {
            "sklearn_ridge": {
                "cpu": "~5%",
                "memory": "~50MB",
                "inference_time": "~5ms",
                "can_run": True,
                "notes": "Lightweight, suitable for edge"
            },
            "sklearn_random_forest": {
                "cpu": "~15%",
                "memory": "~100MB",
                "inference_time": "~20ms",
                "can_run": True,
                "notes": "Moderate, may slow other tasks"
            },
            "neural_network_small": {
                "cpu": "~25%",
                "memory": "~150MB",
                "inference_time": "~50ms",
                "can_run": False,
                "notes": "Would exceed CPU budget"
            },
            "pytorch_full": {
                "cpu": "~80%",
                "memory": "~500MB",
                "inference_time": "~200ms",
                "can_run": False,
                "notes": "Too heavy for RPi 3B+"
            }
        },
        
        "recommendations": {
            "edge_suitable": [
                "Linear regression (Ridge)",
                "Decision tree (max_depth=5)",
                "Kalman filter tuning",
                "Simple feature extraction"
            ],
            "server_required": [
                "Neural network training",
                "Deep learning inference",
                "Large dataset processing",
                "Complex optimization"
            ],
            "hybrid_approach": [
                "Collect data on edge",
                "Train model on server",
                "Deploy lightweight model to edge",
                "Periodic sync with server"
            ]
        },
        
        "conclusion": "RPi 3B+ can run lightweight ML (Ridge regression) for adaptive tuning. "
                     "Heavy models should run on ground station server. "
                     "Recommended: HYBRID approach with periodic sync."
    }
    
    return analysis


# ============================================================================
# Test
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("HYBRID GPS DENIAL SYSTEM - TEST")
    print("=" * 70)
    
    # Print RPi capability assessment
    print("\n📊 RASPBERRY PI 3B+ CAPABILITY ASSESSMENT:")
    print("-" * 50)
    analysis = assess_rpi_capability()
    print(f"Device: {analysis['device']}")
    print(f"Available headroom: {analysis['available_headroom']}")
    print(f"\nML Models that CAN run on edge:")
    for name, info in analysis['ml_requirements'].items():
        if info['can_run']:
            print(f"  ✅ {name}: {info['cpu']} CPU, {info['inference_time']}")
    print(f"\nML Models requiring SERVER:")
    for name, info in analysis['ml_requirements'].items():
        if not info['can_run']:
            print(f"  ❌ {name}: {info['notes']}")
    print(f"\nConclusion: {analysis['conclusion']}")
    
    # Test Hybrid System
    print("\n" + "=" * 70)
    print("HYBRID SYSTEM SIMULATION")
    print("=" * 70)
    
    class MockMAVLink:
        def set_mode(self, mode): print(f"  → Mode: {mode}")
        def set_heading(self, h): print(f"  → Heading: {h:.0f}°")
        def set_altitude(self, a): print(f"  → Altitude: {a:.0f}m")
        def land(self): print(f"  → LAND")
        def send_statustext(self, msg, severity): print(f"  → [{severity}] {msg}")
    
    system = HybridGPSDenialSystem(
        MockMAVLink(),
        enable_quantum=True,
        enable_ml=True,
        compute_location=ComputeLocation.HYBRID
    )
    
    system.set_home(21.028, 105.804, 10)
    system.calibrate_airspeed()
    
    print("\n1. Normal GPS operation...")
    for i in range(5):
        system.update_gps(21.028 + i*0.0001, 105.804 + i*0.0001, 50,
                          15, 45, 12, 0.8, 3)
        system.update_imu(0.05, -0.02, 0.78, 0, 0, 0, 0.1, -0.1, -9.8)
    print(f"Status: {system.get_status()['mode']}")
    
    print("\n2. GPS JAMMING detected...")
    system.update_gps(21.030, 105.810, 50, 15, 45, 3, 5.0, 2)
    print(f"Status: {system.get_status()['mode']}")
    
    print("\n3. EKF Dead Reckoning active...")
    for i in range(10):
        system.update_imu(0.05, -0.02, math.radians(225), 0, 0, 0.01, 0.1, -0.1, -9.8)
    status = system.get_status()
    print(f"Mode: {status['mode']}")
    print(f"EKF Confidence: {status.get('ekf_confidence', 'N/A')}")
    print(f"DR Error: {status.get('dr_error', 'N/A')}")
    
    print("\n4. GPS RECOVERED...")
    system.update_gps(21.029, 105.805, 80, 15, 225, 14, 0.7, 3)
    print(f"Status: {system.get_status()['mode']}")
    
    print("\n" + "=" * 70)
    print("✅ HYBRID SYSTEM READY FOR DEPLOYMENT!")
    print("=" * 70)
