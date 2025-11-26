"""
RC-Based AI Mode Switching Controller
Nhận RC channels từ ArduPilot qua MAVLink và chuyển thành AI mission modes

Channel Mapping:
- CH5 (AUX1/SWA): Primary AI Mission Mode
- CH6 (AUX2/SWB): AI Sub-mode / Functions  
- CH7 (AUX3/SWC): Detection Frequency
- CH8 (AUX4/SWD): Emergency Override

Author: Flying Wing UAV Team
Date: 2025-11-26
"""

import time
from typing import Dict, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from loguru import logger


class AIMissionMode(Enum):
    """Các chế độ AI mission có thể chọn"""
    SEARCH_RESCUE = "search_rescue"
    PEOPLE_COUNTING = "people_counting" 
    VEHICLE_COUNTING = "vehicle_counting"
    RECONNAISSANCE = "reconnaissance"
    MANUAL = "manual"
    EMERGENCY = "emergency"


class DetectionFrequency(Enum):
    """Tần suất detection"""
    HIGH = "high"      # Detect mỗi 5 frames
    MEDIUM = "medium"  # Detect mỗi 15 frames
    LOW = "low"        # Detect mỗi 30 frames


@dataclass
class AIModeConfig:
    """Configuration cho từng AI mode"""
    mode: AIMissionMode
    detection_frequency: DetectionFrequency
    target_classes: list
    confidence_threshold: float
    tracking_aggressiveness: str
    cpu_usage_limit: float  # % CPU tối đa
    battery_impact: str     # low, medium, high


class RCModeController:
    """Controller xử lý RC-based AI mode switching"""
    
    def __init__(self, mavlink_handler):
        """
        Khởi tạo RC mode controller
        
        Args:
            mavlink_handler: MAVLink handler instance
        """
        self.mavlink = mavlink_handler
        self.current_mode = AIMissionMode.RECONNAISSANCE  # Default
        self.previous_mode = None
        self.detection_freq = DetectionFrequency.MEDIUM
        
        # RC channel thresholds (PWM values)
        self.pwm_thresholds = {
            'low': 1300,    # Switch DOWN
            'middle': 1500, # Switch MIDDLE  
            'high': 1700    # Switch UP
        }
        
        # Mode configurations
        self.mode_configs = self._initialize_mode_configs()
        
        # Callbacks
        self.mode_change_callbacks = []
        
        # Register MAVLink callback
        self.mavlink.register_callback('RC_CHANNELS', self._on_rc_channels)
        
        logger.info("RC Mode Controller initialized")
    
    def _initialize_mode_configs(self) -> Dict[AIMissionMode, AIModeConfig]:
        """Khởi tạo configuration cho từng mode"""
        return {
            AIMissionMode.SEARCH_RESCUE: AIModeConfig(
                mode=AIMissionMode.SEARCH_RESCUE,
                detection_frequency=DetectionFrequency.HIGH,
                target_classes=['person', 'boat', 'vehicle'],
                confidence_threshold=0.7,
                tracking_aggressiveness='medium',
                cpu_usage_limit=0.7,
                battery_impact='high'
            ),
            AIMissionMode.PEOPLE_COUNTING: AIModeConfig(
                mode=AIMissionMode.PEOPLE_COUNTING,
                detection_frequency=DetectionFrequency.LOW,
                target_classes=['person'],
                confidence_threshold=0.6,
                tracking_aggressiveness='low',
                cpu_usage_limit=0.4,
                battery_impact='low'
            ),
            AIMissionMode.VEHICLE_COUNTING: AIModeConfig(
                mode=AIMissionMode.VEHICLE_COUNTING,
                detection_frequency=DetectionFrequency.LOW,
                target_classes=['car', 'truck', 'bus'],
                confidence_threshold=0.6,
                tracking_aggressiveness='low',
                cpu_usage_limit=0.4,
                battery_impact='low'
            ),
            AIMissionMode.RECONNAISSANCE: AIModeConfig(
                mode=AIMissionMode.RECONNAISSANCE,
                detection_frequency=DetectionFrequency.MEDIUM,
                target_classes=['person', 'vehicle', 'building'],
                confidence_threshold=0.5,
                tracking_aggressiveness='high',
                cpu_usage_limit=0.6,
                battery_impact='medium'
            ),
            AIMissionMode.MANUAL: AIModeConfig(
                mode=AIMissionMode.MANUAL,
                detection_frequency=DetectionFrequency.LOW,
                target_classes=[],
                confidence_threshold=0.0,
                tracking_aggressiveness='none',
                cpu_usage_limit=0.1,
                battery_impact='low'
            )
        }
    
    def _on_rc_channels(self, msg):
        """Callback khi nhận RC channels từ MAVLink"""
        try:
            # Extract AUX channels
            aux_channels = {
                'aux1': getattr(msg, 'chan5_raw', 1500),  # SWA - Primary Mode
                'aux2': getattr(msg, 'chan6_raw', 1500),  # SWB - Sub-mode
                'aux3': getattr(msg, 'chan7_raw', 1500),  # SWC - Frequency
                'aux4': getattr(msg, 'chan8_raw', 1500)   # SWD - Emergency
            }
            
            # Process mode switching
            self._process_mode_switching(aux_channels)
            
        except Exception as e:
            logger.error(f"Error processing RC channels: {e}")
    
    def _process_mode_switching(self, aux_channels: Dict[str, int]):
        """Xử lý switching dựa trên AUX channels"""
        # Decode primary mission mode từ AUX1 (SWA)
        new_mode = self._decode_primary_mode(aux_channels['aux1'])
        
        # Decode detection frequency từ AUX3 (SWC)
        new_freq = self._decode_detection_frequency(aux_channels['aux3'])
        
        # Check for emergency override từ AUX4 (SWD)
        if self._is_emergency_override(aux_channels['aux4']):
            new_mode = AIMissionMode.EMERGENCY
        
        # Apply mode changes
        self._apply_mode_changes(new_mode, new_freq)
    
    def _decode_primary_mode(self, aux1_pwm: int) -> AIMissionMode:
        """Decode primary AI mission mode từ AUX1"""
        if aux1_pwm < self.pwm_thresholds['low']:
            return AIMissionMode.SEARCH_RESCUE      # SWA DOWN
        elif aux1_pwm > self.pwm_thresholds['high']:
            return AIMissionMode.PEOPLE_COUNTING    # SWA UP
        else:
            return AIMissionMode.RECONNAISSANCE     # SWA MIDDLE
    
    def _decode_detection_frequency(self, aux3_pwm: int) -> DetectionFrequency:
        """Decode detection frequency từ AUX3"""
        if aux3_pwm < self.pwm_thresholds['low']:
            return DetectionFrequency.LOW      # SWC DOWN
        elif aux3_pwm > self.pwm_thresholds['high']:
            return DetectionFrequency.HIGH     # SWC UP
        else:
            return DetectionFrequency.MEDIUM   # SWC MIDDLE
    
    def _is_emergency_override(self, aux4_pwm: int) -> bool:
        """Check emergency override từ AUX4"""
        return aux4_pwm > self.pwm_thresholds['high']  # SWD UP
    
    def _apply_mode_changes(self, new_mode: AIMissionMode, new_freq: DetectionFrequency):
        """Áp dụng mode changes với safety checks"""
        mode_changed = new_mode != self.current_mode
        freq_changed = new_freq != self.detection_freq
        
        if not (mode_changed or freq_changed):
            return  # No changes
        
        # Safety check: không switch mode khi đang critical operation
        if mode_changed and self._is_critical_operation():
            logger.warning(f"Mode switch deferred - critical operation in progress")
            return
        
        # Apply changes
        if mode_changed:
            self._switch_mission_mode(new_mode)
        
        if freq_changed:
            self._switch_detection_frequency(new_freq)
    
    def _switch_mission_mode(self, new_mode: AIMissionMode):
        """Switch mission mode với graceful transition"""
        logger.info(f"AI Mission Mode: {self.current_mode.value} → {new_mode.value}")
        
        self.previous_mode = self.current_mode
        self.current_mode = new_mode
        
        # Notify callbacks
        self._notify_mode_change()
        
        # Log mode transition
        self._log_mode_transition()
    
    def _switch_detection_frequency(self, new_freq: DetectionFrequency):
        """Switch detection frequency"""
        logger.info(f"Detection Frequency: {self.detection_freq.value} → {new_freq.value}")
        self.detection_freq = new_freq
    
    def _is_critical_operation(self) -> bool:
        """Check nếu đang có critical operation không nên interrupt"""
        # TODO: Implement based on current AI operations
        # Ví dụ: đang tracking emergency target, đang gửi alert, etc.
        return False
    
    def _notify_mode_change(self):
        """Notify all registered callbacks về mode change"""
        for callback in self.mode_change_callbacks:
            try:
                callback(self.current_mode, self.get_current_config())
            except Exception as e:
                logger.error(f"Error in mode change callback: {e}")
    
    def _log_mode_transition(self):
        """Log mode transition để debug và analysis"""
        config = self.get_current_config()
        logger.info(f"Mode Config: {config}")
        
        # Gửi status qua MAVLink về Ground Station
        self._send_mode_status()
    
    def _send_mode_status(self):
        """Gửi AI mode status qua MAVLink về Ground Station"""
        try:
            status_msg = {
                'mode': self.current_mode.value,
                'frequency': self.detection_freq.value,
                'timestamp': time.time(),
                'battery_impact': self.get_current_config().battery_impact
            }
            
            # Gửi custom MAVLink message
            # self.mavlink.send_custom_message('AI_MODE_STATUS', status_msg)
            logger.debug(f"Mode status sent: {status_msg}")
            
        except Exception as e:
            logger.error(f"Failed to send mode status: {e}")
    
    def register_mode_change_callback(self, callback: Callable):
        """Register callback cho mode changes"""
        self.mode_change_callbacks.append(callback)
        logger.debug(f"Registered mode change callback: {callback.__name__}")
    
    def get_current_config(self) -> AIModeConfig:
        """Lấy current mode configuration"""
        return self.mode_configs.get(self.current_mode, self.mode_configs[AIMissionMode.RECONNAISSANCE])
    
    def get_detection_interval(self) -> int:
        """Lấy detection interval dựa trên current frequency"""
        intervals = {
            DetectionFrequency.HIGH: 5,    # Mỗi 5 frames
            DetectionFrequency.MEDIUM: 15, # Mỗi 15 frames
            DetectionFrequency.LOW: 30     # Mỗi 30 frames
        }
        return intervals.get(self.detection_freq, 15)
    
    def get_status(self) -> Dict:
        """Lấy current status"""
        config = self.get_current_config()
        return {
            'current_mode': self.current_mode.value,
            'detection_frequency': self.detection_freq.value,
            'detection_interval': self.get_detection_interval(),
            'target_classes': config.target_classes,
            'confidence_threshold': config.confidence_threshold,
            'cpu_usage_limit': config.cpu_usage_limit,
            'battery_impact': config.battery_impact
        }


def main():
    """Test RC Mode Controller"""
    print("=== Testing RC Mode Controller ===\n")
    
    # Mock MAVLink handler for testing
    class MockMAVLinkHandler:
        def __init__(self):
            self.callbacks = {}
        
        def register_callback(self, msg_type, callback):
            if msg_type not in self.callbacks:
                self.callbacks[msg_type] = []
            self.callbacks[msg_type].append(callback)
        
        def simulate_rc_message(self, chan5, chan6, chan7, chan8):
            """Simulate RC channels message"""
            class MockMessage:
                def __init__(self, channels):
                    self.chan5_raw = channels[0]
                    self.chan6_raw = channels[1]
                    self.chan7_raw = channels[2]
                    self.chan8_raw = channels[3]
            
            msg = MockMessage([chan5, chan6, chan7, chan8])
            if 'RC_CHANNELS' in self.callbacks:
                for callback in self.callbacks['RC_CHANNELS']:
                    callback(msg)
    
    # Create controller
    mock_mavlink = MockMAVLinkHandler()
    controller = RCModeController(mock_mavlink)
    
    # Test callback
    def on_mode_change(new_mode, config):
        print(f"🔔 CALLBACK: Mode changed to {new_mode.value}")
        print(f"   Config: {config}")
    
    controller.register_mode_change_callback(on_mode_change)
    
    # Test scenarios
    test_scenarios = [
        (1000, 1500, 1500, 1500),  # SWA DOWN -> Search & Rescue
        (2000, 1500, 1500, 1500),  # SWA UP -> People Counting  
        (1500, 1500, 1500, 1500),  # SWA MIDDLE -> Reconnaissance
        (1500, 1500, 1000, 1500),  # SWC DOWN -> Low Frequency
        (1500, 1500, 2000, 1500),  # SWC UP -> High Frequency
        (1500, 1500, 1500, 2000),  # SWD UP -> Emergency Override
    ]
    
    print("Testing mode switching scenarios:\n")
    
    for i, (ch5, ch6, ch7, ch8) in enumerate(test_scenarios):
        print(f"Scenario {i+1}: CH5={ch5}, CH6={ch6}, CH7={ch7}, CH8={ch8}")
        mock_mavlink.simulate_rc_message(ch5, ch6, ch7, ch8)
        
        status = controller.get_status()
        print(f"   Current: {status['current_mode']}, Freq: {status['detection_frequency']}")
        print()
        
        time.sleep(0.5)
    
    print("✅ RC Mode Controller test completed")


if __name__ == "__main__":
    main()