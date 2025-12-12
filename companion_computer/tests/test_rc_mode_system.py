"""
Test Script for RC-Based Mode Switching System
Kiểm tra tích hợp giữa RadioMaster, ArduPilot và AI mode switching

Author: Trương Công Định & Đặng Duy Long
Date: 2025-11-26
"""

import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from ai.rc_mode_controller import RCModeController, AIMissionMode
    from ai.adaptive_detector import AdaptiveDetector
    RC_MODE_AVAILABLE = True
except ImportError as e:
    print(f"RC Mode modules not available: {e}")
    RC_MODE_AVAILABLE = False


class RCSystemTester:
    """Tester cho toàn bộ RC mode switching system"""
    
    def __init__(self):
        self.test_results = {}
        
    def test_basic_mode_switching(self):
        """Test basic mode switching functionality"""
        print("\n=== Test 1: Basic Mode Switching ===")
        
        if not RC_MODE_AVAILABLE:
            print("❌ RC Mode modules not available")
            return False
        
        # Mock MAVLink handler
        class MockMAVLink:
            def __init__(self):
                self.callbacks = {}
            
            def register_callback(self, msg_type, callback):
                if msg_type not in self.callbacks:
                    self.callbacks[msg_type] = []
                self.callbacks[msg_type].append(callback)
            
            def simulate_rc(self, chan5, chan6, chan7, chan8):
                class MockMsg:
                    def __init__(self, ch5, ch6, ch7, ch8):
                        self.chan5_raw = ch5
                        self.chan6_raw = ch6
                        self.chan7_raw = ch7
                        self.chan8_raw = ch8
                
                msg = MockMsg(chan5, ch6, ch7, ch8)
                if 'RC_CHANNELS' in self.callbacks:
                    for cb in self.callbacks['RC_CHANNELS']:
                        cb(msg)
        
        mock_mavlink = MockMAVLink()
        
        # Create RC mode controller
        controller = RCModeController(mock_mavlink)
        
        # Test scenarios
        test_cases = [
            # (CH5, CH6, CH7, CH8, expected_mode, description)
            (1000, 1500, 1500, 1500, AIMissionMode.SEARCH_RESCUE, "SWA DOWN - Search & Rescue"),
            (2000, 1500, 1500, 1500, AIMissionMode.PEOPLE_COUNTING, "SWA UP - People Counting"),
            (1500, 1500, 1500, 1500, AIMissionMode.RECONNAISSANCE, "SWA MIDDLE - Reconnaissance"),
            (1500, 1500, 1000, 1500, AIMissionMode.RECONNAISSANCE, "SWC DOWN - Low Frequency"),
            (1500, 1500, 2000, 1500, AIMissionMode.RECONNAISSANCE, "SWC UP - High Frequency"),
            (1500, 1500, 1500, 2000, AIMissionMode.EMERGENCY, "SWD UP - Emergency Override"),
        ]
        
        passed = 0
        total = len(test_cases)
        
        for ch5, ch6, ch7, ch8, expected_mode, description in test_cases:
            print(f"\nTesting: {description}")
            print(f"  Channels: CH5={ch5}, CH6={ch6}, CH7={ch7}, CH8={ch8}")
            
            # Simulate RC input
            mock_mavlink.simulate_rc(ch5, ch6, ch7, ch8)
            time.sleep(0.1)  # Allow processing time
            
            # Check result
            current_mode = controller.current_mode
            status = controller.get_status()
            
            print(f"  Expected: {expected_mode.value}")
            print(f"  Actual: {current_mode.value}")
            print(f"  Frequency: {status['detection_frequency']}")
            
            if current_mode == expected_mode:
                print("  ✅ PASS")
                passed += 1
            else:
                print("  ❌ FAIL")
        
        success_rate = (passed / total) * 100
        print(f"\n📊 Results: {passed}/{total} passed ({success_rate:.1f}%)")
        
        self.test_results['basic_mode_switching'] = {
            'passed': passed,
            'total': total,
            'success_rate': success_rate
        }
        
        return passed == total
    
    def test_adaptive_detector_integration(self):
        """Test integration với adaptive detector"""
        print("\n=== Test 2: Adaptive Detector Integration ===")
        
        if not RC_MODE_AVAILABLE:
            print("❌ RC Mode modules not available")
            return False
        
        # Mock MAVLink handler
        class MockMAVLink:
            def __init__(self):
                self.callbacks = {}
            
            def register_callback(self, msg_type, callback):
                if msg_type not in self.callbacks:
                    self.callbacks[msg_type] = []
                self.callbacks[msg_type].append(callback)
        
        mock_mavlink = MockMAVLink()
        
        try:
            # Create adaptive detector
            detector = AdaptiveDetector(mock_mavlink)
            
            # Check initial status
            status = detector.get_status()
            print("Initial detector status:")
            for key, value in status.items():
                print(f"  {key}: {value}")
            
            # Test mode change callback
            mode_changes = []
            
            def on_mode_change(new_mode, config):
                mode_changes.append(new_mode)
                print(f"  🔔 Mode changed to: {new_mode.value}")
            
            detector.mode_controller.register_mode_change_callback(on_mode_change)
            
            print("\n✅ Adaptive Detector integration test passed")
            
            self.test_results['adaptive_detector'] = {
                'status': 'PASS',
                'initial_mode': status['current_mode'],
                'callbacks_registered': True
            }
            
            return True
            
        except Exception as e:
            print(f"❌ Adaptive Detector integration failed: {e}")
            self.test_results['adaptive_detector'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            return False
    
    def test_performance_characteristics(self):
        """Test performance characteristics của từng mode"""
        print("\n=== Test 3: Performance Characteristics ===")
        
        if not RC_MODE_AVAILABLE:
            print("❌ RC Mode modules not available")
            return False
        
        # Mock MAVLink handler
        class MockMAVLink:
            def __init__(self):
                self.callbacks = {}
            
            def register_callback(self, msg_type, callback):
                if msg_type not in self.callbacks:
                    self.callbacks[msg_type] = []
                self.callbacks[msg_type].append(callback)
        
        mock_mavlink = MockMAVLink()
        
        controller = RCModeController(mock_mavlink)
        
        # Analyze each mode's characteristics
        modes = [
            AIMissionMode.SEARCH_RESCUE,
            AIMissionMode.PEOPLE_COUNTING, 
            AIMissionMode.VEHICLE_COUNTING,
            AIMissionMode.RECONNAISSANCE
        ]
        
        print("\nMode Performance Analysis:")
        print("-" * 60)
        print(f"{'Mode':<20} {'CPU Limit':<12} {'Battery':<12} {'Detection Freq'}")
        print("-" * 60)
        
        performance_data = {}
        
        for mode in modes:
            # Temporarily switch to this mode for analysis
            controller.current_mode = mode
            config = controller.get_current_config()
            
            cpu_limit = f"{config.cpu_usage_limit*100:.0f}%"
            battery_impact = config.battery_impact.upper()
            detection_interval = controller.get_detection_interval()
            
            print(f"{mode.value:<20} {cpu_limit:<12} {battery_impact:<12} Every {detection_interval} frames")
            
            performance_data[mode.value] = {
                'cpu_limit': config.cpu_usage_limit,
                'battery_impact': config.battery_impact,
                'detection_interval': detection_interval,
                'confidence_threshold': config.confidence_threshold
            }
        
        self.test_results['performance_analysis'] = performance_data
        
        print("\n✅ Performance analysis completed")
        return True
    
    def run_all_tests(self):
        """Chạy tất cả tests"""
        print("🚀 Flying Wing UAV - RC Mode Switching System Test")
        print("=" * 70)
        
        tests = [
            self.test_basic_mode_switching,
            self.test_adaptive_detector_integration,
            self.test_performance_characteristics
        ]
        
        results = []
        
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with error: {e}")
                results.append(False)
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(results)
        total = len(results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! RC Mode Switching System is ready for deployment.")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Please check implementation.")
        
        return all(results)


def main():
    """Main test runner"""
    tester = RCSystemTester()
    success = tester.run_all_tests()
    
    # Save detailed results
    import json
    results_file = "rc_mode_test_results.json"
    
    with open(results_file, 'w') as f:
        json.dump(tester.test_results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())