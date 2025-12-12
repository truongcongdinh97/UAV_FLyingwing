"""
Adaptive Object Detector với RC Mode Integration
Tự động điều chỉnh detection parameters dựa trên AI mission mode từ RC

Author: Trương Công Định & Đặng Duy Long
Date: 2025-11-26
"""

import time
import numpy as np
from typing import List, Optional, Dict, Tuple
from loguru import logger
from collections import deque
import yaml
import os

import cv2

from .object_detector import ObjectDetector, Detection
from .rc_mode_controller import RCModeController, AIMissionMode, DetectionFrequency
from .optimized_tracker import OptimizedTracker, TrackerType

import threading
import queue


class HybridVerifier:
    """
    TRUE Asynchronous Verification System với Time Machine Buffer
    
    Tracker: Nhanh (40 FPS) nhưng dễ drift - chạy trên MAIN THREAD
    Detector: Chậm (300ms) nhưng chính xác - chạy trên BACKGROUND THREAD
    
    Vấn đề Latency Mismatch: Detector xử lý frame 100, Tracker đã ở frame 110
    Giải pháp: 
    1. Time Machine Buffer + Motion Prediction
    2. TRUE ASYNC: Detector chạy riêng thread, không block tracker
    """
    
    def __init__(self, tracker, detector, verify_interval=30):
        """
        Args:
            tracker: OptimizedTracker instance 
            detector: ObjectDetector instance 
            verify_interval: Số frames giữa mỗi lần verify (default: 30 = ~1 giây)
        """
        self.tracker = tracker
        self.detector = detector
        self.verify_interval = verify_interval
        
        # IoU thresholds theo đề xuất của bạn
        self.iou_excellent_threshold = 0.5  # IoU > 0.5: Tuyệt vời
        self.iou_warning_threshold = 0.3    # IoU < 0.3: Cảnh báo
        self.iou_danger_threshold = 0.1     # IoU < 0.1: Nguy hiểm
        
        # Grace period cho occlusion (2 giây = 60 frames @ 30 FPS)
        self.grace_period_frames = 60
        self.current_grace_frames = 0
        
        # Frame counter cho asynchronous verification
        self.frame_counter = 0
        
        # Tracking state
        self.is_tracking = False
        self.current_tracker_bbox = None
        self.tracking_confidence = 1.0
        
        # Verification history
        self.verification_results = deque(maxlen=100)
        
        # ========== TIME MACHINE BUFFER ==========
        # Lưu trữ tracker bbox theo thời gian để giải quyết latency mismatch
        self.time_machine_buffer = deque(maxlen=50)  # Lưu 50 frames gần nhất
        # Mỗi entry: (frame_id, timestamp, bbox, velocity)
        
        # ========== MOTION PREDICTION ==========
        self.motion_history = deque(maxlen=10)  # Lưu 10 bbox gần nhất để tính velocity
        self.current_velocity = (0, 0)  # (vx, vy) pixels/frame
        self.prediction_horizon = 5  # Dự đoán 5 frames về tương lai
        
        # Detector latency estimation (300ms = ~9 frames @ 30 FPS)
        self.detector_latency_frames = 9
        
        # ========== TRUE ASYNC VERIFICATION ==========
        # Queue để gửi frame cho detector thread
        self._verify_queue = queue.Queue(maxsize=2)  # Chỉ giữ 2 frame mới nhất
        # Queue để nhận kết quả từ detector thread
        self._result_queue = queue.Queue(maxsize=10)
        # Flag để dừng background thread
        self._stop_event = threading.Event()
        # Trạng thái verification đang chạy
        self._verification_in_progress = False
        # Kết quả verification mới nhất (để xử lý trong main thread)
        self._latest_verification_result = None
        self._result_lock = threading.Lock()
        
        # Start background verification thread
        self._verify_thread = threading.Thread(target=self._verification_worker, daemon=True)
        self._verify_thread.start()
        
        logger.info(f"HybridVerifier initialized: verify every {verify_interval} frames")
        logger.info(f"IoU thresholds: Excellent>{self.iou_excellent_threshold}, "
                   f"Warning<{self.iou_warning_threshold}, Danger<{self.iou_danger_threshold}")
        logger.info(f"Time Machine Buffer: {self.time_machine_buffer.maxlen} frames")
        logger.info(f"Motion Prediction: {self.prediction_horizon} frames horizon")
        logger.info(f"Detector latency compensation: {self.detector_latency_frames} frames")
        logger.info("TRUE ASYNC: Detector runs on background thread (non-blocking)")
    
    def _verification_worker(self):
        """
        Background thread worker cho detector verification
        Chạy liên tục, xử lý frame từ queue
        """
        logger.info("Verification worker thread started")
        
        while not self._stop_event.is_set():
            try:
                # Chờ frame từ main thread (timeout 0.1s để check stop_event)
                try:
                    work_item = self._verify_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                frame, tracker_bbox, frame_id = work_item
                
                # Chạy verification (chậm nhưng không block main thread)
                result = self._do_verification(frame, tracker_bbox, frame_id)
                
                # Lưu kết quả
                with self._result_lock:
                    self._latest_verification_result = result
                    self._verification_in_progress = False
                
                # Cũng put vào result queue cho logging
                try:
                    self._result_queue.put_nowait(result)
                except queue.Full:
                    pass  # Queue đầy, bỏ qua
                    
            except Exception as e:
                logger.error(f"Verification worker error: {e}")
                self._verification_in_progress = False
        
        logger.info("Verification worker thread stopped")
    
    def _do_verification(self, frame, tracker_bbox, frame_id) -> Dict:
        """
        Thực hiện verification (chạy trên background thread)
        """
        # Detector chạy (chậm nhưng chính xác)
        try:
            detections = self.detector.detect(frame)
        except Exception as e:
            logger.error(f"Detector error during verification: {e}")
            return {"status": "ERROR", "iou": 0.0, "action": "CONTINUE", "frame_id": frame_id}
        
        if not detections:
            self.current_grace_frames += 1
            
            if self.current_grace_frames > self.grace_period_frames:
                return {
                    "status": "NO_DETECTION",
                    "iou": 0.0,
                    "action": "STOP_TRACKING",
                    "message": f"Object lost for {self.grace_period_frames} frames",
                    "frame_id": frame_id
                }
            else:
                return {
                    "status": "NO_DETECTION",
                    "iou": 0.0,
                    "action": "CONTINUE",
                    "message": f"Grace period: {self.current_grace_frames}/{self.grace_period_frames}",
                    "frame_id": frame_id
                }
        
        # Reset grace period
        self.current_grace_frames = 0
        
        # Lấy tracker bbox từ Time Machine Buffer
        detector_frame_id = frame_id - self.detector_latency_frames
        tracker_bbox_for_comparison = self._get_tracker_bbox_at_frame(detector_frame_id)
        
        if tracker_bbox_for_comparison is None:
            tracker_bbox_for_comparison = tracker_bbox
        
        # Tìm best IoU match
        best_iou = 0.0
        best_detection = None
        
        for detection in detections:
            iou = self.calculate_iou(tracker_bbox_for_comparison, detection.bbox)
            if iou > best_iou:
                best_iou = iou
                best_detection = detection
        
        # Motion-compensated verification
        if best_iou < self.iou_excellent_threshold and best_detection:
            predicted_current_bbox = self._predict_bbox(best_detection.bbox, self.detector_latency_frames)
            predicted_iou = self.calculate_iou(tracker_bbox, predicted_current_bbox)
            if predicted_iou > best_iou:
                best_iou = predicted_iou
        
        # Return result based on IoU thresholds
        if best_iou > self.iou_excellent_threshold:
            return {
                "status": "EXCELLENT",
                "iou": best_iou,
                "action": "RESET_TRACKER",
                "detector_bbox": best_detection.bbox if best_detection else None,
                "message": f"Tracker accurate (IoU={best_iou:.2f})",
                "frame_id": frame_id
            }
        elif best_iou > self.iou_warning_threshold:
            return {
                "status": "WARNING",
                "iou": best_iou,
                "action": "CONTINUE",
                "message": f"Tracker drifting (IoU={best_iou:.2f})",
                "frame_id": frame_id
            }
        elif best_iou > self.iou_danger_threshold:
            return {
                "status": "DANGER",
                "iou": best_iou,
                "action": "WARN_PILOT",
                "message": f"Tracker may be wrong (IoU={best_iou:.2f})",
                "frame_id": frame_id
            }
        else:
            return {
                "status": "CRITICAL",
                "iou": best_iou,
                "action": "REINITIALIZE_TRACKER",
                "detector_bbox": best_detection.bbox if best_detection else None,
                "message": f"Tracker completely wrong (IoU={best_iou:.2f})",
                "frame_id": frame_id
            }
    
    def stop(self):
        """Dừng background verification thread"""
        self._stop_event.set()
        if self._verify_thread.is_alive():
            self._verify_thread.join(timeout=1.0)
        logger.info("HybridVerifier stopped")
    
    def calculate_iou(self, bbox1: Tuple, bbox2: Tuple) -> float:
        """Calculate Intersection over Union (IoU) giữa hai bounding boxes"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Tính diện tích giao nhau
        x_left = max(x1_1, x1_2)
        y_top = max(y1_1, y1_2)
        x_right = min(x2_1, x2_2)
        y_bottom = min(y2_1, y2_2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        
        # Tính diện tích hợp nhất
        bbox1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        bbox2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = bbox1_area + bbox2_area - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0
    
    def _update_time_machine_buffer(self, frame_id: int, bbox: Tuple):
        """Cập nhật Time Machine Buffer với tracker bbox mới"""
        timestamp = time.time()
        
        # Tính velocity từ motion history
        if self.motion_history:
            last_bbox = self.motion_history[-1][2]  # (frame_id, timestamp, bbox)
            vx = (bbox[0] + bbox[2])/2 - (last_bbox[0] + last_bbox[2])/2
            vy = (bbox[1] + bbox[3])/2 - (last_bbox[1] + last_bbox[3])/2
            self.current_velocity = (vx, vy)
        else:
            self.current_velocity = (0, 0)
        
        # Thêm vào motion history
        self.motion_history.append((frame_id, timestamp, bbox))
        
        # Thêm vào time machine buffer
        self.time_machine_buffer.append({
            'frame_id': frame_id,
            'timestamp': timestamp,
            'bbox': bbox,
            'velocity': self.current_velocity
        })
    
    def _predict_bbox(self, bbox: Tuple, frames_ahead: int) -> Tuple:
        """
        Dự đoán bbox ở tương lai dựa trên velocity hiện tại
        
        Args:
            bbox: Bbox hiện tại (x1, y1, x2, y2)
            frames_ahead: Số frames cần dự đoán về tương lai
            
        Returns:
            Predicted bbox
        """
        if frames_ahead <= 0:
            return bbox
        
        vx, vy = self.current_velocity
        predicted_center_x = (bbox[0] + bbox[2])/2 + vx * frames_ahead
        predicted_center_y = (bbox[1] + bbox[3])/2 + vy * frames_ahead
        
        # Giữ nguyên kích thước bbox
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        
        predicted_bbox = (
            int(predicted_center_x - width/2),
            int(predicted_center_y - height/2),
            int(predicted_center_x + width/2),
            int(predicted_center_y + height/2)
        )
        
        return predicted_bbox
    
    def _get_tracker_bbox_at_frame(self, target_frame_id: int) -> Optional[Tuple]:
        """
        Lấy tracker bbox ở frame cụ thể từ Time Machine Buffer
        
        Args:
            target_frame_id: Frame ID cần lấy bbox
            
        Returns:
            Tracker bbox tại frame đó, hoặc None nếu không tìm thấy
        """
        if not self.time_machine_buffer:
            return None
        
        # Tìm bbox gần nhất với target_frame_id
        best_match = None
        min_frame_diff = float('inf')
        
        for entry in self.time_machine_buffer:
            frame_diff = abs(entry['frame_id'] - target_frame_id)
            if frame_diff < min_frame_diff:
                min_frame_diff = frame_diff
                best_match = entry
        
        if best_match and min_frame_diff <= 5:  # Cho phép sai số 5 frames
            # Nếu cần, dự đoán thêm để bù latency
            if best_match['frame_id'] < target_frame_id:
                frames_ahead = target_frame_id - best_match['frame_id']
                return self._predict_bbox(best_match['bbox'], frames_ahead)
            return best_match['bbox']
        
        return None
    
    def verify_tracker(self, frame: np.ndarray, current_tracker_bbox: Tuple) -> Dict:
        """
        Verify tracker với detector - Có Time Machine Buffer để giải quyết latency mismatch
        
        Returns:
            Dict với kết quả verification:
            - status: "EXCELLENT", "WARNING", "DANGER", "NO_DETECTION"
            - iou: IoU score
            - action: Hành động thực hiện
        """
        # Detector chạy (chậm nhưng chính xác) - frame hiện tại
        try:
            detections = self.detector.detect(frame)
        except Exception as e:
            logger.error(f"Detector error during verification: {e}")
            return {"status": "ERROR", "iou": 0.0, "action": "CONTINUE"}
        
        if not detections:
            # Detector không thấy gì cả
            self.current_grace_frames += 1
            
            if self.current_grace_frames > self.grace_period_frames:
                # Đã 2 giây không thấy object - hủy tracking
                return {
                    "status": "NO_DETECTION",
                    "iou": 0.0,
                    "action": "STOP_TRACKING",
                    "message": f"Object lost for {self.grace_period_frames} frames"
                }
            else:
                # Vẫn trong grace period
                return {
                    "status": "NO_DETECTION",
                    "iou": 0.0,
                    "action": "CONTINUE",
                    "message": f"Grace period: {self.current_grace_frames}/{self.grace_period_frames}"
                }
        
        # Reset grace period khi detector thấy object
        self.current_grace_frames = 0
        
        # ========== TIME MACHINE BUFFER MATCHING ==========
        # Detector đang xử lý frame từ quá khứ (do latency)
        # Ước lượng frame ID mà detector thực sự đang xử lý
        detector_frame_id = self.frame_counter - self.detector_latency_frames
        
        # Lấy tracker bbox ở cùng thời điểm với detector
        tracker_bbox_for_comparison = self._get_tracker_bbox_at_frame(detector_frame_id)
        
        if tracker_bbox_for_comparison is None:
            # Không tìm thấy bbox trong buffer, dùng bbox hiện tại
            tracker_bbox_for_comparison = current_tracker_bbox
            logger.warning(f"Time Machine Buffer: No match for frame {detector_frame_id}, using current bbox")
        else:
            logger.debug(f"Time Machine Buffer: Matched frame {detector_frame_id} with buffer entry")
        
        # Tìm detector bbox gần nhất với tracker bbox (đã được time-aligned)
        best_iou = 0.0
        best_detection = None
        
        for detection in detections:
            iou = self.calculate_iou(tracker_bbox_for_comparison, detection.bbox)
            if iou > best_iou:
                best_iou = iou
                best_detection = detection
        
        # ========== MOTION-COMPENSATED VERIFICATION ==========
        # Nếu IoU thấp, thử dự đoán vị trí object hiện tại
        if best_iou < self.iou_excellent_threshold and best_detection:
            # Dự đoán vị trí object hiện tại từ detector bbox
            predicted_current_bbox = self._predict_bbox(best_detection.bbox, self.detector_latency_frames)
            
            # Tính IoU giữa tracker bbox hiện tại và predicted bbox
            predicted_iou = self.calculate_iou(current_tracker_bbox, predicted_current_bbox)
            
            if predicted_iou > best_iou:
                logger.debug(f"Motion prediction improved IoU: {best_iou:.2f} -> {predicted_iou:.2f}")
                best_iou = predicted_iou
                # Sử dụng predicted bbox cho verification tiếp theo
                best_detection.bbox = predicted_current_bbox
        
        # Áp dụng IoU thresholds của bạn
        if best_iou > self.iou_excellent_threshold:
            # ✅ Tuyệt vời: Tracker đang bám đúng (có thể đã được time-aligned)
            # Reset tracker vào vị trí detector (sửa drift nhỏ)
            if best_detection:
                try:
                    # Reinitialize tracker với detector bbox (đã được motion-compensated)
                    self.tracker.reinitialize(frame, best_detection.bbox)
                    action = "RESET_TRACKER"
                    message = f"Tracker accurate (Time-aligned IoU={best_iou:.2f})"
                except Exception as e:
                    logger.error(f"Failed to reset tracker: {e}")
                    action = "CONTINUE"
                    message = f"Tracker accurate but reset failed (IoU={best_iou:.2f})"
            else:
                action = "CONTINUE"
                message = f"Tracker accurate (IoU={best_iou:.2f})"
            
            return {
                "status": "EXCELLENT",
                "iou": best_iou,
                "action": action,
                "message": message
            }
        
        elif best_iou > self.iou_warning_threshold:
            # ⚠️ Cảnh báo: Tracker đang drift nhẹ
            return {
                "status": "WARNING",
                "iou": best_iou,
                "action": "CONTINUE",
                "message": f"Tracker drifting (Time-aligned IoU={best_iou:.2f})"
            }
        
        elif best_iou > self.iou_danger_threshold:
            # ⚠️⚠️ Nguy hiểm: Tracker đang drift nhiều
            # Có thể tracker đang bám vào bụi cây/cái bóng
            return {
                "status": "DANGER",
                "iou": best_iou,
                "action": "WARN_PILOT",
                "message": f"Tracker may be wrong (Time-aligned IoU={best_iou:.2f})"
            }
        
        else:
            # ❌ Rất nguy hiểm: Tracker hoàn toàn sai
            # Hủy tracker cũ, bám theo detector mới (đã được motion-compensated)
            if best_detection:
                try:
                    self.tracker.reinitialize(frame, best_detection.bbox)
                    action = "REINITIALIZE_TRACKER"
                    message = f"Tracker completely wrong, reinitialized (Time-aligned IoU={best_iou:.2f})"
                except Exception as e:
                    logger.error(f"Failed to reinitialize tracker: {e}")
                    action = "STOP_TRACKING"
                    message = f"Tracker completely wrong, reinit failed (IoU={best_iou:.2f})"
            else:
                action = "STOP_TRACKING"
                message = f"Tracker completely wrong, no detection (IoU={best_iou:.2f})"
            
            return {
                "status": "CRITICAL",
                "iou": best_iou,
                "action": action,
                "message": message
            }
    
    def _process_verification_result(self, result: Dict):
        """
        Xử lý kết quả verification từ background thread
        Chạy trên MAIN THREAD - nhanh, không block
        """
        if result is None:
            return
        
        self.verification_results.append(result)
        status = result.get("status", "UNKNOWN")
        action = result.get("action", "CONTINUE")
        
        if status == "EXCELLENT":
            logger.debug(f"✅ Async Verification: {result.get('message', '')}")
            self.tracking_confidence = min(1.0, self.tracking_confidence + 0.1)
            
            # Reset tracker với detector bbox (nếu có)
            detector_bbox = result.get("detector_bbox")
            if detector_bbox and self.tracker:
                try:
                    self.tracker.reinitialize(None, detector_bbox)  # frame không cần thiết
                except Exception as e:
                    logger.warning(f"Failed to reset tracker: {e}")
        
        elif status == "WARNING":
            logger.warning(f"⚠️ Async Verification: {result.get('message', '')}")
            self.tracking_confidence = max(0.3, self.tracking_confidence - 0.05)
        
        elif status == "DANGER":
            logger.error(f"🚨 Async Verification: {result.get('message', '')}")
            self.tracking_confidence = max(0.1, self.tracking_confidence - 0.2)
        
        elif status == "CRITICAL":
            logger.critical(f"💀 Async Verification: {result.get('message', '')}")
            
            if action == "REINITIALIZE_TRACKER":
                detector_bbox = result.get("detector_bbox")
                if detector_bbox and self.tracker:
                    try:
                        self.tracker.reinitialize(None, detector_bbox)
                        logger.info("Tracker reinitialized with detector bbox")
                    except Exception as e:
                        logger.error(f"Failed to reinitialize: {e}")
                        self.is_tracking = False
            elif action == "STOP_TRACKING":
                self.is_tracking = False
                logger.error("Stopping tracking due to critical verification failure")
        
        elif status == "NO_DETECTION":
            if action == "STOP_TRACKING":
                self.is_tracking = False
                logger.error(f"Stopping tracking: {result.get('message', '')}")
    
    def update(self, frame: np.ndarray) -> Optional[Tuple]:
        """
        Update tracker với TRUE ASYNC verification
        
        Tracker chạy ĐỒNG BỘ (nhanh, ~2ms)
        Detector chạy BẤT ĐỒNG BỘ (chậm, ~300ms, không block)
        
        Returns:
            Tracker bbox nếu tracking thành công, None nếu thất bại
        """
        if not self.is_tracking:
            return None
        
        # ========== CHECK ASYNC VERIFICATION RESULT ==========
        # Kiểm tra nếu có kết quả từ background thread (non-blocking)
        with self._result_lock:
            if self._latest_verification_result is not None:
                result = self._latest_verification_result
                self._latest_verification_result = None
                self._process_verification_result(result)
                
                # Check if tracking was stopped
                if not self.is_tracking:
                    return None
        
        # ========== TRACKER UPDATE (FAST - MAIN THREAD) ==========
        # Tracker update nhanh (40 FPS) - KHÔNG BLOCK
        tracker_bbox = self.tracker.update(frame)
        
        if tracker_bbox is None:
            self.is_tracking = False
            logger.warning("Tracker failed - stopping verification")
            return None
        
        self.current_tracker_bbox = tracker_bbox
        
        # ========== UPDATE TIME MACHINE BUFFER ==========
        self._update_time_machine_buffer(self.frame_counter, tracker_bbox)
        
        self.frame_counter += 1
        
        # ========== TRIGGER ASYNC VERIFICATION ==========
        # Mỗi verify_interval frames, gửi frame cho background thread
        if self.frame_counter >= self.verify_interval and not self._verification_in_progress:
            self.frame_counter = 0
            
            # Gửi work item cho background thread (non-blocking)
            try:
                # Clear old items if queue is full
                while not self._verify_queue.empty():
                    try:
                        self._verify_queue.get_nowait()
                    except queue.Empty:
                        break
                
                # Put new work item
                work_item = (frame.copy(), tracker_bbox, self.frame_counter)
                self._verify_queue.put_nowait(work_item)
                self._verification_in_progress = True
                logger.debug("Async verification triggered (background thread)")
                
            except queue.Full:
                logger.warning("Verification queue full - skipping this cycle")
        
        return tracker_bbox
    
    def start_tracking(self, frame: np.ndarray, bbox: Tuple):
        """Bắt đầu tracking với initial bbox"""
        try:
            # Clear any pending verification results
            with self._result_lock:
                self._latest_verification_result = None
            self._verification_in_progress = False
            
            # Clear queues
            while not self._verify_queue.empty():
                try:
                    self._verify_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Initialize tracker
            success = self.tracker.initialize_tracker(frame, bbox, altitude=20.0)
            
            if success:
                self.is_tracking = True
                self.current_tracker_bbox = bbox
                self.frame_counter = 0
                self.current_grace_frames = 0
                self.tracking_confidence = 1.0
                
                # Initialize Time Machine Buffer
                self._update_time_machine_buffer(0, bbox)
                
                logger.info(f"Hybrid tracking started with bbox: {bbox}")
            else:
                logger.error("Failed to initialize tracker")
                self.is_tracking = False
                
        except Exception as e:
            logger.error(f"Error starting hybrid tracking: {e}")
            self.is_tracking = False
    
    def stop_tracking(self):
        """Dừng tracking và cleanup"""
        self.is_tracking = False
        self.current_tracker_bbox = None
        self.tracking_confidence = 0.0
        self._verification_in_progress = False
        
        # Clear buffers
        self.time_machine_buffer.clear()
        self.motion_history.clear()
        
        logger.info("Hybrid tracking stopped")
    
    def get_status(self) -> Dict:
        """Lấy trạng thái hiện tại"""
        return {
            "is_tracking": self.is_tracking,
            "tracking_confidence": self.tracking_confidence,
            "frame_counter": self.frame_counter,
            "verify_interval": self.verify_interval,
            "grace_period": f"{self.current_grace_frames}/{self.grace_period_frames}",
            "recent_verifications": len(self.verification_results),
            "current_bbox": self.current_tracker_bbox,
            "time_machine_buffer_size": len(self.time_machine_buffer),
            "motion_history_size": len(self.motion_history),
            "current_velocity": f"({self.current_velocity[0]:.1f}, {self.current_velocity[1]:.1f}) px/frame",
            "detector_latency_compensation": f"{self.detector_latency_frames} frames",
            "async_verification_in_progress": self._verification_in_progress,
            "verify_thread_alive": self._verify_thread.is_alive() if hasattr(self, '_verify_thread') else False
        }


class AdaptiveDetector:
    """Adaptive object detector với RC mode integration và TRUE ASYNC Hybrid Verification"""
    
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
        
        # TRUE ASYNC Hybrid verification system
        # Tracker: Main thread (40 FPS, không block)
        # Detector: Background thread (300ms, không block main)
        self.tracker = OptimizedTracker()
        self.hybrid_verifier = HybridVerifier(
            tracker=self.tracker,
            detector=self.detector,
            verify_interval=30  # Verify mỗi 30 frames (~1 giây)
        )
        
        # Tracking state
        self.is_tracking = False
        self.tracked_objects: List[Detection] = []
        self.trackers: List[Optional[cv2.Tracker]] = []  # OpenCV trackers (legacy)
        self.frame_count = 0
        
        # Performance monitoring (giới hạn bộ nhớ, tránh memory leak)
        self.detection_times = deque(maxlen=1000)
        self.tracking_times = deque(maxlen=1000)
        
        # Emergency state
        self.is_emergency = False
        self.emergency_target = None
        
        # Tracking configuration
        self.tracker_type = self._load_tracker_config(config_path)  # Load from config
        self.tracking_lost_threshold = 5  # Frames before considering tracking lost
        
        # Tracking confidence tracking
        self.tracking_confidences: Dict[int, float] = {}  # Object ID -> confidence score
        self.prev_bboxes: Dict[int, Tuple] = {}  # Object ID -> previous bbox
        self.object_counter = 0  # For generating unique object IDs
        
        # Current configuration
        self.current_config = self.mode_controller.get_current_config()
        
        logger.info(f"Adaptive Detector initialized with {self.tracker_type} tracker")
        logger.info("Hybrid Verification System: Tracker (40 FPS) + Detector verification (1 Hz)")
    
    def _on_mode_changed(self, new_mode: AIMissionMode, config):
        """Callback khi AI mode thay đổi"""
        logger.info(f"AdaptiveDetector: Mode changed to {new_mode.value}")
        
        # Update configuration
        self.current_config = config
        
        # Reset tracking state khi mode thay đổi
        self._reset_tracking_state()
        
        # Apply mode-specific optimizations
        self._apply_mode_optimizations(new_mode)
    
    def _load_tracker_config(self, config_path: str) -> str:
        """Load tracker configuration from config file
        
        OpenCV 4.12.0 Tracker Support:
        - VIT (primary): 47 FPS on RPi, requires ONNX model
        - MIL (fallback): 5 FPS on RPi, built-in
        
        Removed (unavailable models):
        - NANO: Model not publicly available
        - DASIAMRPN: Model downloads corrupt
        """
        self.model_paths = {}  # Store model paths for deep learning trackers
        
        try:
            # Try to load from tracking config
            tracking_config_path = "config/tracking_config.yaml"
            if os.path.exists(tracking_config_path):
                with open(tracking_config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Load model paths
                model_paths_config = config.get('model_paths', {})
                self.model_paths = model_paths_config
                
                # Get tracker priority from config - VIT primary, MIL fallback
                tracker_priority = config.get('tracking', {}).get('tracker_priority', ['vit', 'mil'])
                
                # Try each tracker in priority order
                for tracker_type in tracker_priority:
                    tracker_type_upper = tracker_type.upper()
                    try:
                        # Test if tracker is available in OpenCV 4.12.0
                        if tracker_type_upper == "MIL":
                            cv2.TrackerMIL_create()
                            logger.info(f"Using tracker type: MIL (fallback, 5 FPS on RPi)")
                            return "MIL"
                        elif tracker_type_upper == "VIT":
                            model_path = self.model_paths.get('vit', '')
                            if model_path and os.path.exists(model_path):
                                params = cv2.TrackerVit_Params()
                                params.net = model_path
                                cv2.TrackerVit_create(params)
                                logger.info(f"Using tracker type: VIT with model (47 FPS on RPi)")
                                return "VIT"
                            else:
                                logger.warning(f"VIT model not found at {model_path}")
                                continue
                        
                    except Exception as e:
                        logger.debug(f"Tracker {tracker_type_upper} not available: {e}")
                        continue
                
                # Fallback to MIL if none available
                logger.warning(f"No configured trackers available, falling back to MIL")
                return "MIL"
            
        except Exception as e:
            logger.error(f"Error loading tracker config: {e}")
        
        # Default to MIL (Most stable in OpenCV 4.12.0)
        return "MIL"
    
    def set_tracker_type(self, tracker_type: str):
        """Switch tracker type dynamically (can be called via RC channel)
        
        Valid types:
        - VIT: 47 FPS on RPi, requires ONNX model
        - MIL: 5 FPS on RPi, built-in (fallback)
        """
        valid_trackers = ["MIL", "VIT"]
        tracker_type_upper = tracker_type.upper()
        
        if tracker_type_upper not in valid_trackers:
            logger.error(f"Invalid tracker type: {tracker_type}. Valid options: {valid_trackers}")
            return False
        
        try:
            # Test if tracker is available in OpenCV 4.12.0
            if tracker_type_upper == "MIL":
                cv2.TrackerMIL_create()
            elif tracker_type_upper == "VIT":
                model_path = self.model_paths.get('vit', '')
                if model_path and os.path.exists(model_path):
                    params = cv2.TrackerVit_Params()
                    params.net = model_path
                    cv2.TrackerVit_create(params)
                else:
                    logger.error(f"VIT model not found at {model_path}")
                    return False
            
            # Switch tracker type
            old_tracker = self.tracker_type
            self.tracker_type = tracker_type_upper
            
            # Reinitialize trackers with new type
            if self.is_tracking and self.tracked_objects:
                logger.info(f"Switching tracker from {old_tracker} to {tracker_type_upper}")
                # Note: Trackers will be reinitialized on next tracking call
            
            logger.info(f"Tracker type switched to: {tracker_type_upper}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch to tracker {tracker_type_upper}: {e}")
            return False
    
    def _reset_tracking_state(self):
        """Reset tracking state khi mode thay đổi"""
        # Clear critical operations
        if self.is_emergency:
            self.mode_controller.set_critical_operation('emergency_tracking', False)
        
        self.is_tracking = False
        self.is_emergency = False
        self.emergency_target = None
        self.tracked_objects.clear()
        self.trackers.clear()  # Clear OpenCV trackers
        self.tracking_confidences.clear()
        self.prev_bboxes.clear()
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
            # Assign unique IDs to detections for tracking confidence calculation
            for i, detection in enumerate(filtered_detections):
                detection.id = self.object_counter
                self.object_counter += 1
                self.tracking_confidences[detection.id] = 1.0  # Start with full confidence
                self.prev_bboxes[detection.id] = detection.bbox
            
            self.tracked_objects = filtered_detections
            self.is_tracking = True
            
            # Note: Trackers will be initialized in first tracking call with actual frame
            
            # Set critical operation flag if tracking emergency target
            if self.mode_controller.current_mode == AIMissionMode.SEARCH_RESCUE:
                # Check if we're tracking a person (potential rescue target)
                for detection in filtered_detections:
                    if detection.class_name == 'person':
                        self.is_emergency = True
                        self.emergency_target = detection
                        self.mode_controller.set_critical_operation('emergency_tracking', True)
                        logger.warning("🚨 Emergency tracking started - person detected in search & rescue mode")
                        break
            
            logger.info(f"Started tracking {len(filtered_detections)} objects with {self.tracker_type} tracker")
    
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
    
    def _initialize_trackers(self, frame: np.ndarray, detections: List[Detection]):
        """Khởi tạo OpenCV trackers cho mỗi detection với frame hiện tại
        
        OpenCV 4.12.0 Tracker Support:
        - VIT (primary): 47 FPS on RPi, requires ONNX model
        - MIL (fallback): 5 FPS on RPi, built-in
        """
        self.trackers.clear()
        
        for detection in detections:
            try:
                # Create tracker based on configuration (OpenCV 4.12.0 API)
                tracker = None
                
                if self.tracker_type == "VIT":
                    model_path = self.model_paths.get('vit', '')
                    if model_path and os.path.exists(model_path):
                        params = cv2.TrackerVit_Params()
                        params.net = model_path
                        tracker = cv2.TrackerVit_create(params)
                        logger.debug(f"VIT tracker created with model: {model_path}")
                    else:
                        # Fallback to MIL if VIT model not found
                        tracker = cv2.TrackerMIL_create()
                        logger.warning(f"VIT model not found, falling back to MIL")
                elif self.tracker_type == "MIL":
                    tracker = cv2.TrackerMIL_create()
                    logger.debug("MIL tracker created (5 FPS on RPi)")
                else:
                    tracker = cv2.TrackerMIL_create()  # Default to MIL
                
                # Convert bbox to OpenCV format (x, y, width, height)
                bbox = detection.bbox
                opencv_bbox = (int(bbox[0]), int(bbox[1]), 
                              int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1]))
                
                # Initialize tracker với frame hiện tại
                success = tracker.init(frame, opencv_bbox)
                if success:
                    self.trackers.append(tracker)
                else:
                    logger.warning(f"Failed to initialize tracker for {detection.class_name}")
                    self.trackers.append(None)
                
            except Exception as e:
                logger.error(f"Failed to initialize tracker for detection {detection.class_name}: {e}")
                self.trackers.append(None)
    
    def _calculate_iou(self, bbox1: Tuple, bbox2: Tuple) -> float:
        """Calculate Intersection over Union (IoU) between two bounding boxes"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection area
        x_left = max(x1_1, x1_2)
        y_top = max(y1_1, y1_2)
        x_right = min(x2_1, x2_2)
        y_bottom = min(y2_1, y2_2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        
        # Calculate union area
        bbox1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        bbox2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = bbox1_area + bbox2_area - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0
    
    def _update_tracking_confidence(self, detection_id: int, new_bbox: Tuple) -> float:
        """Update tracking confidence based on bbox overlap with previous frame"""
        if detection_id not in self.prev_bboxes:
            self.prev_bboxes[detection_id] = new_bbox
            return 1.0  # First frame, assume full confidence
        
        prev_bbox = self.prev_bboxes[detection_id]
        iou = self._calculate_iou(prev_bbox, new_bbox)
        
        # Update confidence using exponential moving average
        current_confidence = self.tracking_confidences.get(detection_id, 1.0)
        alpha = 0.7  # Weight for new IoU value
        new_confidence = alpha * iou + (1 - alpha) * current_confidence
        
        # Update stored values
        self.tracking_confidences[detection_id] = new_confidence
        self.prev_bboxes[detection_id] = new_bbox
        
        return new_confidence
    
    def _run_tracking(self, frame: np.ndarray) -> List[Detection]:
        """Chạy tracking trên frame hiện tại với OpenCV trackers"""
        if not self.is_tracking or not self.tracked_objects:
            return []
        
        # Initialize trackers on first tracking call if not already initialized
        if not self.trackers:
            self._initialize_trackers(frame, self.tracked_objects)
            if not self.trackers:  # Still no trackers after initialization
                self.is_tracking = False
                return []
        
        updated_detections = []
        valid_trackers = []
        valid_detections = []
        
        # Update each tracker and get new bounding box
        for i, (detection, tracker) in enumerate(zip(self.tracked_objects, self.trackers)):
            if tracker is None:
                continue
            
            try:
                # Update tracker with current frame
                success, bbox = tracker.update(frame)
                
                if success:
                    # Convert OpenCV bbox format (x, y, width, height) to our format (x1, y1, x2, y2)
                    x, y, w, h = [int(v) for v in bbox]
                    new_bbox = (x, y, x + w, y + h)
                    
                    # Calculate tracking confidence based on bbox overlap
                    if hasattr(detection, 'id'):
                        tracking_confidence = self._update_tracking_confidence(detection.id, new_bbox)
                    else:
                        tracking_confidence = 1.0  # Default if no ID
                    
                    # Create updated detection with new bbox and tracking confidence
                    updated_detection = Detection(
                        bbox=new_bbox,
                        confidence=detection.confidence,
                        class_name=detection.class_name,
                        class_id=detection.class_id
                    )
                    # Add tracking confidence as attribute
                    updated_detection.tracking_confidence = tracking_confidence
                    if hasattr(detection, 'id'):
                        updated_detection.id = detection.id
                    
                    # Log low confidence tracking
                    if tracking_confidence < 0.3:
                        logger.warning(f"Low tracking confidence ({tracking_confidence:.2f}) for {detection.class_name}")
                    
                    updated_detections.append(updated_detection)
                    valid_trackers.append(tracker)
                    valid_detections.append(updated_detection)
                    
                else:
                    # Tracking failed for this object
                    logger.debug(f"Tracking lost for {detection.class_name}")
                    continue
                    
            except Exception as e:
                logger.error(f"Tracker update error for {detection.class_name}: {e}")
                continue
        
        # Update internal state
        self.tracked_objects = valid_detections
        self.trackers = valid_trackers
        
        # If we lost all trackers, disable tracking
        if not self.tracked_objects:
            self.is_tracking = False
            logger.debug("All trackers lost - will re-detect")
        
        return updated_detections
    
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
        
        # Calculate average tracking confidence
        avg_tracking_confidence = 0.0
        if self.tracking_confidences:
            avg_tracking_confidence = np.mean(list(self.tracking_confidences.values()))
        
        return {
            **mode_status,
            'is_tracking': self.is_tracking,
            'is_emergency': self.is_emergency,
            'tracked_objects_count': len(self.tracked_objects),
            'frame_count': self.frame_count,
            'avg_detection_time': np.mean(self.detection_times[-10:]) if self.detection_times else 0,
            'avg_tracking_time': np.mean(self.tracking_times[-50:]) if self.tracking_times else 0,
            'avg_tracking_confidence': avg_tracking_confidence,
            'tracker_type': self.tracker_type,
            'emergency_target': self.emergency_target.class_name if self.emergency_target else None
        }
    
    def emergency_stop(self):
        """Dừng khẩn cấp tất cả AI operations"""
        logger.warning("🚨 EMERGENCY STOP: Stopping all AI operations")
        
        # Clear all critical operations
        self.mode_controller.set_critical_operation('emergency_tracking', False)
        self.mode_controller.set_critical_operation('alert_sending', False)
        self.mode_controller.set_critical_operation('target_geolocation', False)
        self.mode_controller.set_critical_operation('data_upload', False)
        
        # Stop tracking
        self.is_tracking = False
        self.is_emergency = False
        self.emergency_target = None
        self.tracked_objects.clear()
        self.trackers.clear()  # Clear OpenCV trackers
        
        # Stop detector processes if available
        if hasattr(self.detector, 'stop'):
            try:
                self.detector.stop()
                logger.info("Detector processes stopped")
            except Exception as e:
                logger.error(f"Error stopping detector: {e}")
        
        # Clear performance tracking
        self.detection_times.clear()
        self.tracking_times.clear()
        
        logger.info("✅ All AI operations stopped")


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
