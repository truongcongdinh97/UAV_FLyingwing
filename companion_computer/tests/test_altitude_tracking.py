"""
Test Altitude-Based Tracking System
Kiểm tra tracking với strategy ưu tiên độ cao 20-25m và MOSSE/KCF

Author: Flying Wing UAV Team
Date: 2025-11-26
"""

import sys
import os
import cv2
import numpy as np
from loguru import logger

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai.optimized_tracker import OptimizedTracker, TrackerType, TrackingQuality
from camera.camera_interface import CameraInterface


class AltitudeTrackingTester:
    """Tester cho altitude-based tracking system"""
    
    def __init__(self):
        self.tracker = OptimizedTracker()
        self.camera = CameraInterface()
        self.test_results = []
        
    def test_tracker_selection(self):
        """Test việc chọn tracker dựa trên độ cao"""
        print("\n🧪 TEST 1: Tracker Selection by Altitude")
        print("=" * 60)
        
        test_cases = [
            (8, "POOR - Too low"),
            (12, "ACCEPTABLE - Low"),
            (18, "GOOD - Near optimal"),
            (22, "EXCELLENT - Optimal"),
            (25, "EXCELLENT - Optimal"),
            (28, "GOOD - Near optimal"),
            (32, "ACCEPTABLE - High"),
            (38, "POOR - Too high")
        ]
        
        for altitude, description in test_cases:
            tracker_type = self.tracker.select_tracker_for_altitude(altitude)
            quality = self.tracker.get_tracking_quality(altitude)
            
            print(f"\nAltitude: {altitude:2d}m - {description}")
            print(f"  Selected Tracker: {tracker_type.value.upper()}")
            print(f"  Expected Quality: {quality.value}")
            
            # Verify MOSSE/KCF priority
            if 20 <= altitude <= 25:
                assert tracker_type == TrackerType.MOSSE, f"Should use MOSSE at {altitude}m"
                print(f"  ✅ MOSSE priority confirmed at optimal altitude")
            elif 25 < altitude <= 30:
                assert tracker_type == TrackerType.KCF, f"Should use KCF at {altitude}m"
                print(f"  ✅ KCF priority confirmed at good altitude")
            else:
                assert tracker_type == TrackerType.MOSSE, f"Should use MOSSE for CPU saving at {altitude}m"
                print(f"  ✅ MOSSE for CPU saving confirmed")
    
    def test_tracking_simulation(self):
        """Test tracking với frame simulation"""
        print("\n\n🧪 TEST 2: Tracking Simulation")
        print("=" * 60)
        
        # Tạo mock frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Test với các độ cao khác nhau
        altitude_test_cases = [22, 25, 28]  # Focus on 20-25m range
        
        for altitude in altitude_test_cases:
            print(f"\n--- Testing at {altitude}m ---")
            
            # Tạo bounding box giả
            bbox = (200, 150, 100, 80)  # x, y, w, h
            
            # Khởi tạo tracker
            success = self.tracker.initialize_tracker(frame, bbox, altitude)
            
            if success:
                print(f"  ✅ Tracker initialized successfully")
                print(f"  Tracker Type: {self.tracker.tracker_type.value.upper()}")
                
                # Test update với vài frame
                for i in range(3):
                    # Tạo frame mới với noise nhẹ
                    new_frame = frame.copy()
                    noise = np.random.randint(-10, 10, frame.shape, dtype=np.int16)
                    new_frame = np.clip(new_frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
                    
                    # Update tracker
                    result_bbox = self.tracker.update(new_frame, altitude)
                    
                    if result_bbox:
                        print(f"  Frame {i+1}: Tracking successful")
                    else:
                        print(f"  Frame {i+1}: Tracking failed/skipped")
                
                # Show performance stats
                stats = self.tracker.get_performance_stats()
                print(f"  Success Rate: {stats['success_rate']}")
                print(f"  FPS: {stats['fps']}")
                
                self.tracker.reset()
            else:
                print(f"  ❌ Failed to initialize tracker")
    
    def test_cpu_optimization(self):
        """Test các tính năng tối ưu hóa CPU"""
        print("\n\n🧪 TEST 3: CPU Optimization Features")
        print("=" * 60)
        
        stats = self.tracker.get_performance_stats()
        
        print("\nCPU Optimization Features:")
        print(f"  • Frame Skip Interval: {stats['frame_skip_interval']}")
        print(f"  • MOSSE Priority: Always for CPU efficiency")
        print(f"  • KCF Usage: Only at 25-30m for better accuracy")
        print(f"  • CSRT Avoidance: High CPU usage - rarely used")
        
        # Test frame skipping
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        bbox = (200, 150, 100, 80)
        
        self.tracker.initialize_tracker(frame, bbox, 22)
        
        results = []
        for i in range(6):  # Test 6 frames
            result = self.tracker.update(frame, 22)
            results.append((i, "Processed" if result is not None else "Skipped"))
        
        print("\nFrame Processing Test (6 frames):")
        for frame_num, status in results:
            print(f"  Frame {frame_num}: {status}")
        
        # Verify frame skipping pattern
        skipped_count = sum(1 for _, status in results if status == "Skipped")
        assert skipped_count >= 2, "Frame skipping should work"
        print(f"  ✅ Frame skipping confirmed: {skipped_count}/6 frames skipped")
    
    def run_all_tests(self):
        """Chạy tất cả tests"""
        print("🚀 Starting Altitude-Based Tracking Tests")
        print("🎯 Strategy: Priority 20-25m with MOSSE/KCF")
        print("💾 Focus: Low CPU usage with acceptable accuracy\n")
        
        try:
            self.test_tracker_selection()
            self.test_tracking_simulation()
            self.test_cpu_optimization()
            
            print("\n" + "=" * 60)
            print("🎉 ALL TESTS PASSED!")
            print("✅ Tracking system optimized for 20-25m altitude")
            print("✅ MOSSE/KCF priority implemented")
            print("✅ CPU optimization features working")
            print("✅ Ready for real-world testing!")
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            raise


def main():
    """Main test function"""
    tester = AltitudeTrackingTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()