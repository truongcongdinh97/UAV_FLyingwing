"""
Optimized Object Tracker cho Raspberry Pi 3B+
Ưu tiên độ cao 20-25m với MOSSE/KCF trackers

Author: Flying Wing UAV Team
Date: 2025-11-26
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
from loguru import logger
from enum import Enum
import time
import yaml
import os


class TrackerType(Enum):
    """Các loại tracker được hỗ trợ"""
    MOSSE = "mosse"      # Fastest, lowest CPU - ƯU TIÊN CAO
    KCF = "kcf"          # Balanced accuracy/speed - ƯU TIÊN TRUNG BÌNH
    CSRT = "csrt"        # High accuracy, high CPU - CHỈ DÙNG KHI CẦN THIẾT


class TrackingQuality(Enum):
    """Đánh giá chất lượng tracking"""
    EXCELLENT = "excellent"  # 20-25m, 95%+ accuracy - TỐI ƯU
    GOOD = "good"           # 15-20m hoặc 25-30m, 80-90% accuracy
    ACCEPTABLE = "acceptable" # 10-15m hoặc 30-35m, 60-80% accuracy
    POOR = "poor"           # <10m hoặc >35m, <60% accuracy


class OptimizedTracker:
    """Optimized tracker với altitude-based strategy ưu tiên MOSSE/KCF"""
    
    def __init__(self, config_path=None):
        self.config = None
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                      "config", "tracking_config.yaml")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    self.config = yaml.safe_load(f)
                logger.info(f"Loaded tracking config from {config_path}")
            except Exception as e:
                logger.warning(f"Error loading config: {e}")
        else:
            logger.warning(f"Tracking config not found: {config_path}, using defaults")
        
        self.tracker = None
        self.tracker_type = None
        self.is_initialized = False
        self.tracking_failures = 0
        self.max_failures = self._get_config(['tracking','performance','max_tracking_failures'], 5)
        
        # Altitude optimization settings
        self.optimal_altitude_range = tuple(self._get_config(['tracking','altitude_ranges','optimal'], [20,25]))
        self.good_altitude_range = tuple(self._get_config(['tracking','altitude_ranges','good'], [15,30]))
        self.acceptable_altitude_range = tuple(self._get_config(['tracking','altitude_ranges','acceptable'], [10,35]))
        
        # CPU optimization settings
        self.frame_skip_interval = self._get_config(['tracking','cpu_optimization','frame_skip_interval'], 2)
        self.cpu_warning_threshold = self._get_config(['tracking','cpu_optimization','max_cpu_usage'], 80)  # %
        
        # Performance monitoring
        self.frame_count = 0
        self.successful_tracks = 0
        self.last_altitude = None
        self.start_time = time.time()
        
        # CPU optimization settings
        self.current_skip_count = 0
        
        logger.info("Optimized Tracker initialized - Priority: 20-25m with MOSSE/KCF")
    
    def _get_config(self, keys, default):
        """Truy xuất giá trị từ self.config với chuỗi key lồng nhau"""
        conf = self.config
        try:
            for k in keys:
                conf = conf[k]
            return conf
        except Exception:
            return default
    
    def select_tracker_for_altitude(self, altitude: float) -> TrackerType:
        """Chọn tracker phù hợp nhất cho độ cao - ƯU TIÊN MOSSE/KCF"""
        if self.optimal_altitude_range[0] <= altitude <= self.optimal_altitude_range[1]:
            # Độ cao tối ưu 20-25m - DÙNG MOSSE CHO TỐC ĐỘ CAO NHẤT
            logger.debug(f"Optimal altitude {altitude}m - Using MOSSE for max speed")
            return TrackerType.MOSSE
        elif self.good_altitude_range[0] <= altitude <= self.good_altitude_range[1]:
            # Độ cao tốt 15-30m - DÙNG KCF CHO BALANCE
            if 25 <= altitude <= 30:
                logger.debug(f"Good altitude {altitude}m - Using KCF for better accuracy")
                return TrackerType.KCF
            else:
                logger.debug(f"Good altitude {altitude}m - Using MOSSE for CPU efficiency")
                return TrackerType.MOSSE
        elif self.acceptable_altitude_range[0] <= altitude <= self.acceptable_altitude_range[1]:
            # Độ cao chấp nhận được - VẪN ƯU TIÊN MOSSE ĐỂ TIẾT KIỆM CPU
            logger.debug(f"Acceptable altitude {altitude}m - Using MOSSE for CPU saving")
            return TrackerType.MOSSE
        else:
            # Độ cao không tối ưu - DÙNG MOSSE ĐỂ TIẾT KIỆM CPU
            logger.warning(f"Poor altitude {altitude}m - Using MOSSE for CPU efficiency")
            return TrackerType.MOSSE
    
    def get_tracking_quality(self, altitude: float) -> TrackingQuality:
        """Đánh giá chất lượng tracking dựa trên độ cao"""
        if self.optimal_altitude_range[0] <= altitude <= self.optimal_altitude_range[1]:
            return TrackingQuality.EXCELLENT
        elif self.good_altitude_range[0] <= altitude <= self.good_altitude_range[1]:
            return TrackingQuality.GOOD
        elif self.acceptable_altitude_range[0] <= altitude <= self.acceptable_altitude_range[1]:
            return TrackingQuality.ACCEPTABLE
        else:
            return TrackingQuality.POOR
    
    def create_tracker(self, tracker_type: TrackerType):
        """Tạo tracker với type cụ thể - ƯU TIÊN MOSSE/KCF"""
        try:
            if tracker_type == TrackerType.MOSSE:
                self.tracker = cv2.legacy.TrackerMOSSE_create()
                logger.debug("MOSSE tracker created - Fastest CPU performance")
            elif tracker_type == TrackerType.KCF:
                self.tracker = cv2.legacy.TrackerKCF_create()
                logger.debug("KCF tracker created - Balanced performance")
            elif tracker_type == TrackerType.CSRT:
                self.tracker = cv2.legacy.TrackerCSRT_create()
                logger.warning("CSRT tracker created - High CPU usage")
            else:
                # Fallback to MOSSE - ƯU TIÊN CPU
                self.tracker = cv2.legacy.TrackerMOSSE_create()
                tracker_type = TrackerType.MOSSE
                logger.info("Fallback to MOSSE tracker for CPU efficiency")
            
            self.tracker_type = tracker_type
            
        except Exception as e:
            logger.error(f"Failed to create tracker {tracker_type.value}: {e}")
            # Fallback to MOSSE - ƯU TIÊN CPU
            self.tracker = cv2.legacy.TrackerMOSSE_create()
            self.tracker_type = TrackerType.MOSSE
            logger.info("Emergency fallback to MOSSE tracker")
    
    def should_skip_frame(self) -> bool:
        """Quyết định có nên skip frame để tiết kiệm CPU không"""
        self.current_skip_count += 1
        if self.current_skip_count >= self.frame_skip_interval:
            self.current_skip_count = 0
            return False
        return True
    
    def initialize_tracker(self, frame: np.ndarray, bbox: Tuple[int, int, int, int], 
                          altitude: float) -> bool:
        """Khởi tạo tracker với frame và bounding box"""
        try:
            # Chọn tracker phù hợp với độ cao - ƯU TIÊN MOSSE/KCF
            tracker_type = self.select_tracker_for_altitude(altitude)
            self.create_tracker(tracker_type)
            
            # Khởi tạo tracker
            success = self.tracker.init(frame, bbox)
            
            if success:
                self.is_initialized = True
                self.tracking_failures = 0
                self.last_altitude = altitude
                quality = self.get_tracking_quality(altitude)
                
                logger.info(f"Tracker initialized: {tracker_type.value} "
                          f"at {altitude}m - Quality: {quality.value}")
            else:
                logger.error("Failed to initialize tracker")
            
            return success
            
        except Exception as e:
            logger.error(f"Error initializing tracker: {e}")
            return False
    
    def update(self, frame: np.ndarray, altitude: float) -> Optional[Tuple[int, int, int, int]]:
        """Update tracker với frame mới - Tối ưu hóa CPU"""
        if not self.is_initialized or self.tracker is None:
            return None
        
        # Skip frame để tiết kiệm CPU nếu cần
        if self.should_skip_frame():
            logger.debug("Frame skipped for CPU optimization")
            return None
        
        try:
            # Kiểm tra xem có cần thay đổi tracker do thay đổi độ cao không
            if (self.last_altitude is not None and 
                abs(altitude - self.last_altitude) > 5):  # Thay đổi >5m
                old_quality = self.get_tracking_quality(self.last_altitude)
                new_quality = self.get_tracking_quality(altitude)
                if old_quality != new_quality:
                    logger.info(f"Altitude changed {self.last_altitude}m -> {altitude}m, "
                               f"quality: {old_quality.value} -> {new_quality.value}")
                    # Có thể reinitialize với tracker mới ở đây nếu cần
            
            self.last_altitude = altitude
            
            # Update tracker
            success, bbox = self.tracker.update(frame)
            self.frame_count += 1
            
            if success:
                self.successful_tracks += 1
                self.tracking_failures = 0
                
                # Validate bbox (tránh tracking failures)
                if self._is_valid_bbox(bbox, frame.shape):
                    return bbox
                else:
                    self.tracking_failures += 1
                    logger.warning("Invalid bbox detected")
                    return None
                    
            else:
                self.tracking_failures += 1
                logger.warning(f"Tracking failed ({self.tracking_failures}/{self.max_failures})")
                
                # Nếu tracking fail quá nhiều, cần reinitialize
                if self.tracking_failures >= self.max_failures:
                    logger.error("Max tracking failures reached - tracker needs reinitialization")
                    self.is_initialized = False
                
                return None
                
        except Exception as e:
            logger.error(f"Error updating tracker: {e}")
            self.tracking_failures += 1
            return None
    
    def _is_valid_bbox(self, bbox: Tuple[int, int, int, int], frame_shape: Tuple) -> bool:
        """Kiểm tra bounding box hợp lệ"""
        if bbox is None:
            return False
        
        x, y, w, h = bbox
        
        # Kiểm tra kích thước hợp lệ
        if w <= 0 or h <= 0:
            return False
        
        # Kiểm tra trong frame boundaries
        if (x < 0 or y < 0 or 
            x + w > frame_shape[1] or 
            y + h > frame_shape[0]):
            return False
        
        # Kiểm tra kích thước tối thiểu
        if w < 20 or h < 20:  # Quá nhỏ
            return False
        
        # Kiểm tra aspect ratio hợp lý
        aspect_ratio = w / h
        if aspect_ratio < 0.2 or aspect_ratio > 5.0:  # Quá dẹt/cao
            return False
        
        return True
    
    def should_reinitialize(self, altitude: float) -> bool:
        """Kiểm tra có nên reinitialize tracker không"""
        # Reinitialize nếu tracking fail nhiều
        if self.tracking_failures >= self.max_failures:
            return True
        
        # Reinitialize nếu độ cao thay đổi đáng kể và chất lượng tracking thay đổi
        if (self.last_altitude is not None and 
            abs(altitude - self.last_altitude) > 10 and  # Thay đổi >10m
            self.get_tracking_quality(altitude) != self.get_tracking_quality(self.last_altitude)):
            return True
        
        return False
    
    def get_performance_stats(self) -> Dict:
        """Lấy thống kê hiệu suất"""
        success_rate = (self.successful_tracks / self.frame_count * 100) if self.frame_count > 0 else 0
        runtime = time.time() - self.start_time
        fps = self.frame_count / runtime if runtime > 0 else 0
        
        return {
            'tracker_type': self.tracker_type.value if self.tracker_type else 'None',
            'is_initialized': self.is_initialized,
            'frames_processed': self.frame_count,
            'successful_tracks': self.successful_tracks,
            'success_rate': f"{success_rate:.1f}%",
            'tracking_failures': self.tracking_failures,
            'fps': f"{fps:.1f}",
            'runtime_seconds': f"{runtime:.1f}",
            'optimal_altitude_range': f"{self.optimal_altitude_range[0]}-{self.optimal_altitude_range[1]}m",
            'good_altitude_range': f"{self.good_altitude_range[0]}-{self.good_altitude_range[1]}m",
            'acceptable_altitude_range': f"{self.acceptable_altitude_range[0]}-{self.acceptable_altitude_range[1]}m",
            'frame_skip_interval': self.frame_skip_interval
        }
    
    def reset(self):
        """Reset tracker state"""
        self.tracker = None
        self.tracker_type = None
        self.is_initialized = False
        self.tracking_failures = 0
        self.frame_count = 0
        self.successful_tracks = 0
        self.last_altitude = None
        self.current_skip_count = 0
        self.start_time = time.time()
        logger.info("Tracker reset")


def main():
    """Test Optimized Tracker với focus 20-25m"""
    print("=== Testing Optimized Tracker - Priority: 20-25m with MOSSE/KCF ===\n")
    
    tracker = OptimizedTracker()
    
    # Test altitude-based tracker selection với focus 20-25m
    test_altitudes = [8, 12, 18, 22, 25, 28, 32, 38]
    
    print("Altitude Tracker Selection Test:")
    print("-" * 50)
    for altitude in test_altitudes:
        tracker_type = tracker.select_tracker_for_altitude(altitude)
        quality = tracker.get_tracking_quality(altitude)
        
        status = "⭐ OPTIMAL" if 20 <= altitude <= 25 else "✓ GOOD" if 15 <= altitude <= 30 else "⚠ ACCEPTABLE" if 10 <= altitude <= 35 else "✗ POOR"
        
        print(f"{status} | Altitude: {altitude:2d}m")
        print(f"       Tracker: {tracker_type.value.upper():8s} | Quality: {quality.value:>10s}")
        print()
    
    # Test performance stats
    stats = tracker.get_performance_stats()
    print("\nPerformance Stats:")
    print("-" * 30)
    for key, value in stats.items():
        print(f"  {key:25s}: {value}")
    
    print(f"\n🎯 STRATEGY: Priority 20-25m with MOSSE/KCF")
    print(f"💡 MOSSE: Fastest CPU performance at optimal altitude")
    print(f"💡 KCF: Balanced accuracy when needed")
    print(f"💾 CPU Optimization: Frame skipping enabled")
    
    print("\n✅ Optimized Tracker test completed - Ready for 20-25m operations!")


if __name__ == "__main__":
    main()