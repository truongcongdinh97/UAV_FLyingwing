"""
Module tích hợp Quantum Kalman Filter vào companion computer
Hoạt động ở chế độ Shadow Mode - xử lý dữ liệu IMU thực song song với EKF tiêu chuẩn

Chức năng chính:
- So sánh hiệu suất thời gian thực giữa QKF và EKF
- Thu thập dữ liệu nghiên cứu về hiệu quả lọc nhiễu
- Không can thiệp vào hệ thống điều khiển chính
"""

import time
import threading
from typing import Dict, List, Optional
from loguru import logger

from .quantum_kalman_filter import (
    QuantumKalmanFilter, 
    ShadowModeComparator,
    SensorData,
    FilterComparison
)


class QuantumFilteringIntegration:
    """Integration of quantum filtering into companion computer system"""
    
    def __init__(self, config_path: str = "config/quantum_config.yaml"):
        self.config = self._load_config(config_path)
        self.comparator = ShadowModeComparator()
        self.is_running = False
        self.processing_thread = None
        
        # Data buffers
        self.imu_buffer = []
        self.ekf_buffer = []
        self.max_buffer_size = 100
        
        # Performance tracking
        self.performance_stats = {
            'total_processed': 0,
            'quantum_success_rate': 0,
            'average_processing_time': 0
        }
        
        logger.info("Quantum Filtering Integration initialized")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load quantum filtering configuration"""
        # Default configuration
        return {
            'enabled': True,
            'shadow_mode': True,
            'processing_interval': 0.1,  # seconds
            'max_buffer_size': 100,
            'log_comparisons': True,
            'performance_report_interval': 60  # seconds
        }
    
    def start_shadow_mode(self):
        """Start shadow mode processing"""
        if not self.config['enabled']:
            logger.info("Quantum filtering disabled in config")
            return
        
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info("Quantum filtering shadow mode started")
    
    def stop_shadow_mode(self):
        """Stop shadow mode processing"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        logger.info("Quantum filtering shadow mode stopped")
    
    def add_imu_data(self, sensor_data: Dict):
        """Add raw IMU data to processing buffer"""
        if not self.config['enabled']:
            return
        
        # Convert to SensorData format
        imu_data = SensorData(
            timestamp=time.time(),
            accel_x=sensor_data.get('accel_x', 0),
            accel_y=sensor_data.get('accel_y', 0),
            accel_z=sensor_data.get('accel_z', 9.8),
            gyro_x=sensor_data.get('gyro_x', 0),
            gyro_y=sensor_data.get('gyro_y', 0),
            gyro_z=sensor_data.get('gyro_z', 0),
            mag_x=sensor_data.get('mag_x', 0),
            mag_y=sensor_data.get('mag_y', 0),
            mag_z=sensor_data.get('mag_z', 0)
        )
        
        self.imu_buffer.append(imu_data)
        
        # Maintain buffer size
        if len(self.imu_buffer) > self.max_buffer_size:
            self.imu_buffer.pop(0)
    
    def add_ekf_data(self, ekf_state: np.ndarray, confidence: float, processing_time: float):
        """Add EKF state data for comparison"""
        if not self.config['enabled']:
            return
        
        self.ekf_buffer.append({
            'timestamp': time.time(),
            'state': ekf_state,
            'confidence': confidence,
            'processing_time': processing_time
        })
        
        # Maintain buffer size
        if len(self.ekf_buffer) > self.max_buffer_size:
            self.ekf_buffer.pop(0)
    
    def _processing_loop(self):
        """Main processing loop for shadow mode"""
        last_performance_report = time.time()
        
        while self.is_running:
            try:
                # Process available data pairs
                self._process_available_data()
                
                # Generate periodic performance reports
                current_time = time.time()
                if current_time - last_performance_report > self.config['performance_report_interval']:
                    self._generate_performance_report()
                    last_performance_report = current_time
                
                # Sleep to avoid excessive CPU usage
                time.sleep(self.config['processing_interval'])
                
            except Exception as e:
                logger.error(f"Error in quantum processing loop: {e}")
                time.sleep(1)  # Prevent tight error loop
    
    def _process_available_data(self):
        """Process available IMU and EKF data pairs"""
        if not self.imu_buffer or not self.ekf_buffer:
            return
        
        # Use the most recent data
        imu_data = self.imu_buffer[-1]
        ekf_data = self.ekf_buffer[-1]
        
        # Process comparison
        comparison = self.comparator.process_comparison(
            sensor_data=imu_data,
            ekf_state=ekf_data['state'],
            ekf_confidence=ekf_data['confidence'],
            ekf_processing_time=ekf_data['processing_time']
        )
        
        # Update performance stats
        self.performance_stats['total_processed'] += 1
        
        # Log significant differences
        if self.config['log_comparisons']:
            state_diff = np.linalg.norm(comparison.qkf_state - comparison.ekf_state)
            if state_diff > 0.1:  # Threshold for significant difference
                logger.info(f"Significant state difference: {state_diff:.4f}")
    
    def _generate_performance_report(self):
        """Generate and log performance report"""
        report = self.comparator.generate_performance_report()
        
        if report:
            logger.info("=== Quantum Filtering Performance Report ===")
            logger.info(f"Total comparisons: {report['total_comparisons']}")
            logger.info(f"Average processing times - QKF: {report['average_processing_times']['qkf']:.4f}s, "
                       f"EKF: {report['average_processing_times']['ekf']:.4f}s")
            logger.info(f"Processing time ratio (QKF/EKF): {report['average_processing_times']['ratio']:.2f}")
            logger.info(f"Mean state difference: {report['state_difference_analysis']['mean']:.4f}")
            logger.info(f"Confidence - QKF: {report['confidence_analysis']['qkf_mean']:.3f}, "
                       f"EKF: {report['confidence_analysis']['ekf_mean']:.3f}")
            logger.info("============================================")
    
    def get_latest_comparison(self) -> Optional[FilterComparison]:
        """Get the most recent filter comparison"""
        if self.comparator.comparison_history:
            return self.comparator.comparison_history[-1]
        return None
    
    def get_performance_stats(self) -> Dict:
        """Get current performance statistics"""
        return {
            **self.performance_stats,
            'comparison_count': len(self.comparator.comparison_history)
        }


# Global instance for easy integration
quantum_integration = QuantumFilteringIntegration()


def integrate_with_companion_computer():
    """
    Integration function to be called from main companion computer
    This shows how to integrate quantum filtering into the existing system
    """
    
    # Example integration points:
    # 1. In the main processing loop, call quantum_integration.add_imu_data() with raw IMU data
    # 2. When EKF state is available, call quantum_integration.add_ekf_data()
    # 3. Start shadow mode when system is ready
    
    logger.info("Quantum filtering integration ready")
    return quantum_integration


def main():
    """Test integration"""
    print("Testing Quantum Filtering Integration...")
    
    integration = QuantumFilteringIntegration()
    
    # Test with sample data
    sample_imu = {
        'accel_x': 0.1, 'accel_y': -0.05, 'accel_z': 9.81,
        'gyro_x': 0.01, 'gyro_y': 0.02, 'gyro_z': 0.05,
        'mag_x': 0.1, 'mag_y': 0.2, 'mag_z': 0.3
    }
    
    sample_ekf_state = np.array([0.1, -0.05, 9.81, 0.05])
    
    integration.add_imu_data(sample_imu)
    integration.add_ekf_data(sample_ekf_state, 0.8, 0.001)
    
    print("Integration test completed")


if __name__ == "__main__":
    main()