"""
Adaptive Object Detector với RC Mode Integration
Tự động điều chỉnh detection parameters dựa trên AI mission mode từ RC

Author: Flying Wing UAV Team  
Date: 2025-11-26
"""

import time
import numpy as np
from typing import List, Optional, Dict
from loguru import logger
from collections import deque

from .object_detector import ObjectDetector, Detection
from .rc_mode_controller import RCModeController, AIMissionMode, DetectionFrequency


class AdaptiveDetector:
    """Adaptive object detector với RC mode integration"""
    
    def __init__(self, mavlink_handler, config_path: str = "config/ai_config.yaml"):
        """
        Khởi tạo adaptive detector
        
        Args:
            mavlink_handler: MAVLink handler instance
            config_path: Đường dẫn đến AI config
        """
        # Core detector
        self.detector = ObjectDetector(config_path)
        
        # RC mode controller
        self.mode_controller = RCModeController(mavlink_handler)
        self.mode_controller.register_mode_change_callback(self._on_mode_changed)
        
        # Tracking state
        self.is_tracking = False
        self.tracked_objects: List[Detection] = []
        self.frame_count = 0
        
        # Performance monitoring (giới hạn bộ nhớ, tránh memory leak)
        self.detection_times = deque(maxlen=1000)
        self.tracking_times = deque(maxlen=1000)
        
        # Current configuration
        self.current_config = self.mode_controller.get_current_config()
        
        logger.info("Adaptive Detector initialized")
    
    def _on_mode_changed(self, new_mode: AIMissionMode, config):
        """Callback khi AI mode thay đổi"""
        logger.info(f"AdaptiveDetector: Mode changed to {new_mode.value}")
        
        # Update configuration
        self.current_config = config
        
        # Reset tracking state khi mode thay đổi
        self._reset_tracking_state()
        
        # Apply mode-specific optimizations
        self._apply_mode_optimizations(new_mode)
    
    def _reset_tracking_state(self):
        """Reset tracking state khi mode thay đổi"""
        self.is_tracking = False
        self.tracked_objects.clear()
        logger.debug("Tracking state reset due to mode change")
    
    def _apply_mode_optimizations(self, mode: AIMissionMode):
        """Áp dụng optimizations cụ thể cho từng mode"""
        if mode == AIMissionMode.SEARCH_RESCUE:
            # Search & Rescue: Ưu tiên detection accuracy
            self.detector.config['confidence_threshold'] = 0.7
            logger.info("Search & Rescue mode: High confidence threshold")
            
        elif mode == AIMissionMode.PEOPLE_COUNTING:
            # People Counting: Ưu tiên counting accuracy
            self.detector.config['confidence_threshold'] = 0.6
            logger.info("People Counting mode: Medium confidence threshold")
            
        elif mode == AIMissionMode.VEHICLE_COUNTING:
            # Vehicle Counting: Ưu tiên vehicle detection
            self.detector.config['confidence_threshold'] = 0.6
            logger.info("Vehicle Counting mode: Vehicle-focused detection")
            
        elif mode == AIMissionMode.RECONNAISSANCE:
            # Reconnaissance: Balance detection và tracking
            self.detector.config['confidence_threshold'] = 0.5
            logger.info("Reconnaissance mode: Balanced detection/tracking")
    
    def process_frame(self, frame: np.ndarray) -> List[Detection]:
        """
        Xử lý frame với adaptive detection strategy
        
        Args:
            frame: Input frame
            
        Returns:
            List of detections
        """
        self.frame_count += 1
        
        # Lấy detection interval từ current mode
        detection_interval = self.mode_controller.get_detection_interval()
        
        detections = []
        
        # Strategy: Detect Once, Track Forever
        if not self.is_tracking or self.frame_count % detection_interval == 0:
            # Run detection
            start_time = time.time()
            detections = self._run_detection(frame)
            detection_time = time.time() - start_time
            
            self.detection_times.append(detection_time)
            
            if detections:
                # Start tracking với detections mới
                self._start_tracking(detections)
                
                # Mode-specific post-processing
                detections = self._apply_mode_post_processing(detections)
                
                logger.debug(f"Detection: {len(detections)} objects, time: {detection_time:.3f}s")
            
        else:
            # Tracking only mode - rất nhẹ
            start_time = time.time()
            detections = self._run_tracking(frame)
            tracking_time = time.time() - start_time
            
            self.tracking_times.append(tracking_time)
            
            if not detections:
                # Tracking lost - sẽ detect lại ở frame tiếp theo
                self.is_tracking = False
                logger.debug("Tracking lost - will re-detect")
        
        # Performance monitoring
        self._monitor_performance()
        
        return detections
    
    def _run_detection(self, frame: np.ndarray) -> List[Detection]:
        """Chạy object detection với current configuration"""
        try:
            # Apply target classes filter
            original_targets = self.detector.config.get('target_classes', None)
            
            # Override với mode-specific targets
            mode_targets = self.current_config.target_classes
            if mode_targets:
                self.detector.config['target_classes'] = mode_targets
            
            # Run detection
            detections = self.detector.detect(frame)
            
            # Restore original targets
            self.detector.config['target_classes'] = original_targets
            
            return detections
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []
    
    def _start_tracking(self, detections: List[Detection]):
        """Bắt đầu tracking với detections mới"""
        if not detections:
            return
        
        # Filter detections based on mode requirements
        filtered_detections = self._filter_detections_for_tracking(detections)
        
        if filtered_detections:
            self.tracked_objects = filtered_detections
            self.is_tracking = True
            
            logger.info(f"Started tracking {len(filtered_detections)} objects")
    
    def _filter_detections_for_tracking(self, detections: List[Detection]) -> List[Detection]:
        """Filter detections phù hợp với tracking"""
        filtered = []
        
        for detection in detections:
            # Check confidence threshold
            if detection.confidence < self.current_config.confidence_threshold:
                continue
            
            # Check bbox size (tránh tracking object quá nhỏ/lớn)
            bbox = detection.bbox
            bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            
            if bbox_area < 400:  # Quá nhỏ (<20x20 pixels)
                continue
            if bbox_area > 100000:  # Quá lớn (> tiêu cực)
                continue
            
            filtered.append(detection)
        
        return filtered
    
    def _run_tracking(self, frame: np.ndarray) -> List[Detection]:
        """Chạy tracking trên frame hiện tại"""
        # TODO: Implement actual tracking algorithm
        # Hiện tại return empty - sẽ implement tracking sau
        return []
    
    def _apply_mode_post_processing(self, detections: List[Detection]) -> List[Detection]:
        """Áp dụng post-processing cụ thể cho từng mode"""
        mode = self.mode_controller.current_mode
        
        if mode == AIMissionMode.SEARCH_RESCUE:
            # Search & Rescue: Ưu tiên person detection
            return [d for d in detections if d.class_name == 'person']
            
        elif mode == AIMissionMode.PEOPLE_COUNTING:
            # People Counting: Chỉ people
            return [d for d in detections if d.class_name == 'person']
            
        elif mode == AIMissionMode.VEHICLE_COUNTING:
            # Vehicle Counting: Chỉ vehicles
            vehicle_classes = ['car', 'truck', 'bus', 'motorcycle']
            return [d for d in detections if d.class_name in vehicle_classes]
        
        # Reconnaissance: Giữ tất cả detections
        return detections
    
    def _monitor_performance(self):
        """Monitor performance và điều chỉnh nếu cần"""
        # Log performance định kỳ
        if self.frame_count % 100 == 0:
            avg_detection_time = np.mean(self.detection_times[-10:]) if self.detection_times else 0
            avg_tracking_time = np.mean(self.tracking_times[-50:]) if self.tracking_times else 0
            
            logger.info(f"Performance: Detection={avg_detection_time:.3f}s, "
                       f"Tracking={avg_tracking_time:.3f}s, "
                       f"Mode={self.mode_controller.current_mode.value}")
    
    def get_status(self) -> Dict:
        """Lấy current status"""
        mode_status = self.mode_controller.get_status()
        
        return {
            **mode_status,
            'is_tracking': self.is_tracking,
            'tracked_objects_count': len(self.tracked_objects),
            'frame_count': self.frame_count,
            'avg_detection_time': np.mean(self.detection_times[-10:]) if self.detection_times else 0,
            'avg_tracking_time': np.mean(self.tracking_times[-50:]) if self.tracking_times else 0
        }
    
    def emergency_stop(self):
        """Dừng khẩn cấp tất cả AI operations"""
        logger.warning("EMERGENCY STOP: Stopping all AI operations")
        
        self.is_tracking = False
        self.tracked_objects.clear()
        
        # TODO: Stop any running detection/tracking processes


def main():
    """Test Adaptive Detector"""
    print("=== Testing Adaptive Detector ===\n")
    
    # Mock MAVLink handler
    class MockMAVLinkHandler:
        def __init__(self):
            self.callbacks = {}
        
        def register_callback(self, msg_type, callback):
            if msg_type not in self.callbacks:
                self.callbacks[msg_type] = []
            self.callbacks[msg_type].append(callback)
    
    mock_mavlink = MockMAVLinkHandler()
    
    # Create adaptive detector
    detector = AdaptiveDetector(mock_mavlink)
    
    print("Initial status:")
    status = detector.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Adaptive Detector test completed")


if __name__ == "__main__":
    main()