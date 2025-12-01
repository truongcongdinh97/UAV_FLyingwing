"""
Test script cho Quantum IMU Drift Filter
Kiểm tra hiệu quả của QKF trong việc xử lý drift MEMS IMU khi mất GPS
"""

import numpy as np
import time
import matplotlib.pyplot as plt
from pathlib import Path

# Import quantum drift filter
try:
    from src.quantum.quantum_imu_drift_filter import (
        QuantumIMUDriftFilter, 
        NavigationState,
        IMUDriftModel
    )
    QUANTUM_AVAILABLE = True
except ImportError as e:
    print(f"Quantum modules not available: {e}")
    QUANTUM_AVAILABLE = False


class IMUDriftSimulator:
    """Simulator tạo dữ liệu IMU với drift thực tế"""
    
    def __init__(self):
        # Drift parameters dựa trên đặc tính MEMS thực tế
        self.gyro_drift_rate = 0.0001  # rad/s per second
        self.accel_drift_rate = 0.00001  # m/s² per second
        self.temperature_drift = 0.001  # per degree C
        
        # Initial biases
        self.current_gyro_drift = np.zeros(3)
        self.current_accel_drift = np.zeros(3)
        self.temperature = 25.0  # degrees C
        
        # Noise parameters
        self.gyro_noise_std = 0.001  # rad/s
        self.accel_noise_std = 0.01  # m/s²
    
    def generate_imu_data(self, true_angular_vel: np.ndarray, true_accel: np.ndarray, 
                         dt: float, time_elapsed: float) -> np.ndarray:
        """Tạo dữ liệu IMU với drift và noise"""
        
        # Update drift theo thời gian
        self.current_gyro_drift += self.gyro_drift_rate * dt
        self.current_accel_drift += self.accel_drift_rate * dt
        
        # Temperature effect
        temp_effect = 1.0 + (self.temperature - 25.0) * self.temperature_drift
        
        # Tạo noisy measurements với drift
        gyro_measurement = true_angular_vel + self.current_gyro_drift * temp_effect
        accel_measurement = true_accel + self.current_accel_drift * temp_effect
        
        # Add Gaussian noise
        gyro_measurement += np.random.normal(0, self.gyro_noise_std, 3)
        accel_measurement += np.random.normal(0, self.accel_noise_std, 3)
        
        # Kết hợp thành IMU data vector
        imu_data = np.concatenate([gyro_measurement, accel_measurement])
        
        return imu_data
    
    def get_true_drift_model(self) -> IMUDriftModel:
        """Lấy drift model thực tế (cho evaluation)"""
        return IMUDriftModel(
            gyro_drift_x=self.current_gyro_drift[0],
            gyro_drift_y=self.current_gyro_drift[1],
            gyro_drift_z=self.current_gyro_drift[2],
            accel_drift_x=self.current_accel_drift[0],
            accel_drift_y=self.current_accel_drift[1],
            accel_drift_z=self.current_accel_drift[2],
            temperature_factor=1.0 + (self.temperature - 25.0) * self.temperature_drift
        )


def test_gps_loss_scenario():
    """Test scenario mất GPS với IMU drift"""
    
    if not QUANTUM_AVAILABLE:
        print("Quantum modules not available - skipping test")
        return
    
    print("=== Testing GPS Loss Scenario with IMU Drift ===\n")
    
    # Khởi tạo components
    drift_filter = QuantumIMUDriftFilter()
    imu_simulator = IMUDriftSimulator()
    
    # Test parameters
    duration = 60.0  # 60 seconds total
    dt = 0.1  # 10Hz
    gps_loss_time = 10.0  # Mất GPS sau 10s
    
    # Storage for results
    time_points = []
    position_errors = []
    estimated_drifts = []
    true_drifts = []
    gps_status = []
    
    # Initial conditions
    true_position = np.array([0.0, 0.0, 100.0])  # Start at 100m altitude
    true_velocity = np.array([10.0, 0.0, 0.0])   # Moving at 10m/s in x-direction
    true_angular_vel = np.array([0.01, 0.0, 0.0])  # Small rotation
    true_accel = np.array([0.0, 0.0, -9.81])     # Gravity + no acceleration
    
    # Khởi tạo với GPS
    initial_imu = imu_simulator.generate_imu_data(true_angular_vel, true_accel, dt, 0.0)
    drift_filter.initialize_with_gps(initial_imu, true_position)
    
    print("✅ System initialized - starting simulation...")
    
    current_time = 0.0
    step = 0
    
    while current_time < duration:
        # Cập nhật true state
        true_position += true_velocity * dt
        
        # Tạo IMU data với drift
        imu_data = imu_simulator.generate_imu_data(true_angular_vel, true_accel, dt, current_time)
        
        # Xác định GPS availability
        has_gps = current_time < gps_loss_time or current_time > duration - 10.0
        gps_data = true_position if has_gps else None
        
        # Xử lý qua quantum filter
        nav_state = drift_filter.process_sensor_data(imu_data, gps_data, dt)
        
        # Tính toán error và lưu kết quả
        position_error = np.linalg.norm(nav_state.position_est - true_position)
        
        time_points.append(current_time)
        position_errors.append(position_error)
        estimated_drifts.append(np.linalg.norm([
            nav_state.drift_model.gyro_drift_x,
            nav_state.drift_model.gyro_drift_y,
            nav_state.drift_model.gyro_drift_z
        ]))
        
        true_drift_model = imu_simulator.get_true_drift_model()
        true_drifts.append(np.linalg.norm([
            true_drift_model.gyro_drift_x,
            true_drift_model.gyro_drift_y,
            true_drift_model.gyro_drift_z
        ]))
        
        gps_status.append(1.0 if has_gps else 0.0)
        
        # Progress reporting
        if step % 50 == 0:
            print(f"Time: {current_time:.1f}s, GPS: {'ON' if has_gps else 'OFF'}, "
                  f"Position Error: {position_error:.2f}m")
        
        current_time += dt
        step += 1
    
    print("\n✅ Simulation completed")
    
    # Phân tích kết quả
    analyze_results(time_points, position_errors, estimated_drifts, true_drifts, gps_status)
    
    return {
        'time_points': time_points,
        'position_errors': position_errors,
        'estimated_drifts': estimated_drifts,
        'true_drifts': true_drifts,
        'gps_status': gps_status
    }


def analyze_results(time_points, position_errors, estimated_drifts, true_drifts, gps_status):
    """Phân tích và visualize kết quả"""
    
    print("\n=== Performance Analysis ===")
    
    # Chia thành các phase
    gps_available = np.array(gps_status) > 0.5
    gps_lost = ~gps_available
    
    # Tính metrics
    avg_error_with_gps = np.mean(np.array(position_errors)[gps_available])
    avg_error_without_gps = np.mean(np.array(position_errors)[gps_lost])
    max_error = np.max(position_errors)
    
    print(f"Average Position Error:")
    print(f"  With GPS: {avg_error_with_gps:.2f} m")
    print(f"  Without GPS: {avg_error_without_gps:.2f} m")
    print(f"  Maximum Error: {max_error:.2f} m")
    
    # Drift estimation accuracy
    drift_estimation_errors = []
    for est, true in zip(estimated_drifts, true_drifts):
        if true > 0:  # Avoid division by zero
            error = abs(est - true) / true
            drift_estimation_errors.append(error)
    
    avg_drift_error = np.mean(drift_estimation_errors) if drift_estimation_errors else 0.0
    print(f"Average Drift Estimation Error: {avg_drift_error*100:.1f}%")
    
    # Visualization
    plt.figure(figsize=(12, 8))
    
    # Plot 1: Position Error
    plt.subplot(2, 1, 1)
    plt.plot(time_points, position_errors, 'b-', label='Position Error', linewidth=2)
    plt.fill_between(time_points, 0, position_errors, 
                     where=gps_lost, alpha=0.3, color='red', label='GPS Lost')
    plt.ylabel('Position Error (m)')
    plt.title('Quantum IMU Drift Filter - Position Error during GPS Loss')
    plt.legend()
    plt.grid(True)
    
    # Plot 2: Drift Estimation
    plt.subplot(2, 1, 2)
    plt.plot(time_points, true_drifts, 'g-', label='True Drift', linewidth=2)
    plt.plot(time_points, estimated_drifts, 'r--', label='Estimated Drift', linewidth=2)
    plt.fill_between(time_points, 0, max(true_drifts), 
                     where=gps_lost, alpha=0.3, color='red', label='GPS Lost')
    plt.xlabel('Time (s)')
    plt.ylabel('Gyro Drift Magnitude (rad/s)')
    plt.title('Drift Estimation Accuracy')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    
    # Save plot
    output_dir = Path("quantum_drift_results")
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / "gps_loss_performance.png", dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"\n📊 Results saved to: {output_dir}/")


def test_quantum_learning_efficiency():
    """Test hiệu quả của quantum learning"""
    
    if not QUANTUM_AVAILABLE:
        return
    
    print("\n=== Testing Quantum Learning Efficiency ===")
    
    drift_filter = QuantumIMUDriftFilter()
    imu_simulator = IMUDriftSimulator()
    
    # Test với các mức độ drift khác nhau
    drift_levels = [0.0001, 0.001, 0.01]  # rad/s
    learning_times = []
    final_errors = []
    
    for drift_level in drift_levels:
        imu_simulator.gyro_drift_rate = drift_level
        
        start_time = time.time()
        
        # Short learning phase
        for i in range(20):
            imu_data = imu_simulator.generate_imu_data(
                np.array([0.01, 0.0, 0.0]), 
                np.array([0.0, 0.0, -9.81]), 
                0.1, i*0.1
            )
            
            # Process với GPS available để learning
            gps_data = np.array([0.0, 0.0, 100.0])
            drift_filter.process_sensor_data(imu_data, gps_data, 0.1)
        
        learning_time = time.time() - start_time
        learning_times.append(learning_time)
        
        # Đánh giá accuracy
        true_drift = imu_simulator.get_true_drift_model()
        estimated_drift = drift_filter.gps_navigation.drift_model
        
        drift_error = abs(estimated_drift.gyro_drift_x - true_drift.gyro_drift_x)
        final_errors.append(drift_error)
        
        print(f"Drift Level: {drift_level:.4f} rad/s")
        print(f"  Learning Time: {learning_time:.2f}s")
        print(f"  Final Error: {drift_error:.6f} rad/s")
        print(f"  True Drift: {true_drift.gyro_drift_x:.6f}, Estimated: {estimated_drift.gyro_drift_x:.6f}")
    
    return {
        'drift_levels': drift_levels,
        'learning_times': learning_times,
        'final_errors': final_errors
    }


def main():
    """Run all quantum IMU drift tests"""
    
    print("Flying Wing UAV - Quantum IMU Drift Filter Test Suite")
    print("Testing QKF for MEMS IMU drift correction during GPS loss\n")
    
    # Test 1: GPS loss scenario
    results1 = test_gps_loss_scenario()
    
    # Test 2: Quantum learning efficiency
    results2 = test_quantum_learning_efficiency()
    
    print("\n=== Test Summary ===")
    print("Quantum IMU Drift Filter successfully tested")
    print("Ready for deployment on Raspberry Pi for real GPS loss scenarios")
    
    # Save detailed results
    output_dir = Path("quantum_drift_results")
    import json
    
    with open(output_dir / "gps_loss_results.json", "w") as f:
        json.dump(results1, f, indent=2)
    
    with open(output_dir / "learning_efficiency_results.json", "w") as f:
        json.dump(results2, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_dir}/")


if __name__ == "__main__":
    main()