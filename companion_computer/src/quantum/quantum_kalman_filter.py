"""
Quantum-inspired Kalman Filter với Variational Quantum Circuits
Tập trung vào lọc nhiễu phi tuyến tính cho cảm biến MEMS rẻ tiền
Hoạt động ở chế độ Shadow Mode để so sánh thời gian thực với EKF tiêu chuẩn

Mục tiêu nghiên cứu: Kiểm chứng khả năng lọc nhiễu của mạng lượng tử
cho dữ liệu cảm biến MEMS trên phần cứng cổ điển (Raspberry Pi)
"""

import numpy as np
import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from loguru import logger

# Quantum computing libraries
try:
    import qiskit
    from qiskit import QuantumCircuit, Aer, execute
    from qiskit.circuit import Parameter
    from qiskit.quantum_info import SparsePauliOp
    from qiskit_algorithms import VQE
    from qiskit_algorithms.optimizers import COBYLA
    from qiskit.primitives import Estimator
    QISKIT_AVAILABLE = True
except ImportError:
    logger.warning("Qiskit not available - quantum filtering disabled")
    QISKIT_AVAILABLE = False


@dataclass
class SensorData:
    """Container chứa dữ liệu cảm biến IMU"""
    timestamp: float          # Thời gian lấy mẫu
    accel_x: float           # Gia tốc trục X (m/s²)
    accel_y: float           # Gia tốc trục Y (m/s²)
    accel_z: float           # Gia tốc trục Z (m/s²)
    gyro_x: float            # Vận tốc góc trục X (rad/s)
    gyro_y: float            # Vận tốc góc trục Y (rad/s)
    gyro_z: float            # Vận tốc góc trục Z (rad/s) - quan trọng cho flying wing
    mag_x: float             # Từ trường trục X (μT)
    mag_y: float             # Từ trường trục Y (μT)
    mag_z: float             # Từ trường trục Z (μT)


@dataclass
class FilterComparison:
    """Kết quả so sánh giữa QKF và EKF"""
    timestamp: float          # Thời điểm so sánh
    qkf_state: np.ndarray     # Trạng thái ước lượng từ Quantum Kalman Filter
    ekf_state: np.ndarray     # Trạng thái ước lượng từ Extended Kalman Filter
    qkf_confidence: float     # Độ tin cậy của QKF (0-1)
    ekf_confidence: float     # Độ tin cậy của EKF (0-1)
    processing_time_qkf: float # Thời gian xử lý của QKF (giây)
    processing_time_ekf: float # Thời gian xử lý của EKF (giây)


class VariationalQuantumCircuit:
    """Variational Quantum Circuit cho ước lượng trạng thái"""
    
    def __init__(self, num_qubits: int = 4):
        self.num_qubits = num_qubits        # Số lượng qubit (4 qubits cho 4 trạng thái)
        self.circuit = None                 # Mạch lượng tử
        self.parameters = []                # Các tham số biến phân
        self.backend = Aer.get_backend('statevector_simulator') if QISKIT_AVAILABLE else None
        
    def build_circuit(self, initial_state: np.ndarray) -> QuantumCircuit:
        """Xây dựng mạch lượng tử biến phân cho ước lượng trạng thái"""
        if not QISKIT_AVAILABLE:
            return None
            
        # Tạo mạch lượng tử
        qc = QuantumCircuit(self.num_qubits)
        
        # Khởi tạo với dữ liệu cổ điển (angle encoding)
        # Mã hóa trạng thái ban đầu vào các góc quay của qubit
        for i in range(min(len(initial_state), self.num_qubits)):
            qc.ry(initial_state[i] * np.pi, i)  # Quay quanh trục Y theo giá trị trạng thái
        
        # Các lớp biến phân
        num_layers = 3
        for layer in range(num_layers):
            # Cổng quay với các tham số biến phân
            for i in range(self.num_qubits):
                param = Parameter(f'θ_{layer}_{i}')
                self.parameters.append(param)
                qc.ry(param, i)  # Tham số hóa các cổng quay
            
            # Cổng entangling (làm rối lượng tử)
            for i in range(self.num_qubits - 1):
                qc.cx(i, i + 1)  # CNOT gate để tạo entanglement
        
        self.circuit = qc
        return qc
    
    def run_vqe(self, observable: SparsePauliOp, initial_point: np.ndarray) -> float:
        """Chạy Variational Quantum Eigensolver cho ước lượng trạng thái"""
        if not QISKIT_AVAILABLE:
            return 0.0
            
        # Sử dụng optimizer COBYLA cho tối ưu hóa không cần gradient
        optimizer = COBYLA(maxiter=100)
        # Tạo VQE với mạch ansatz đã xây dựng
        vqe = VQE(Estimator(), ansatz=self.circuit, optimizer=optimizer)
        # Tính toán eigenvalue nhỏ nhất (ước lượng trạng thái tối ưu)
        result = vqe.compute_minimum_eigenvalue(observable, initial_point=initial_point)
        return result.eigenvalue.real  # Trả về giá trị thực


class QuantumKalmanFilter:
    """Quantum-inspired Kalman Filter cho sensor fusion MEMS"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.vqc = VariationalQuantumCircuit(num_qubits=4)  # 4 qubits cho 4 trạng thái
        
        # Vector trạng thái: [accel_x, accel_y, accel_z, gyro_z]
        # Chọn 4 thông số quan trọng nhất cho flying wing
        self.state = np.zeros(4)
        self.covariance = np.eye(4) * 0.1  # Ma trận hiệp phương sai khởi tạo
        
        # Nhiễu quá trình và nhiễu đo lường
        self.Q = np.eye(4) * self.config['process_noise']    # Nhiễu quá trình
        self.R = np.eye(4) * self.config['measurement_noise'] # Nhiễu đo lường
        
        # Lịch sử để phân tích
        self.state_history = []
        self.measurement_history = []
        
        logger.info("Quantum Kalman Filter đã khởi tạo")
    
    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            'process_noise': 0.01,
            'measurement_noise': 0.1,
            'quantum_layers': 3,
            'max_iterations': 50,
            'convergence_threshold': 1e-4
        }
    
    def predict(self, dt: float) -> np.ndarray:
        """Bước dự đoán với động lực học lượng tử"""
        # Mô hình động học đơn giản (giả định không có thay đổi)
        F = np.eye(4)  # Ma trận chuyển trạng thái (identity vì giả định không thay đổi)
        
        # Dự đoán trạng thái
        self.state = F @ self.state
        # Cập nhật ma trận hiệp phương sai
        self.covariance = F @ self.covariance @ F.T + self.Q
        
        return self.state.copy()
    
    def update_quantum(self, measurement: np.ndarray, dt: float) -> np.ndarray:
        """Bước cập nhật sử dụng Variational Quantum Circuit"""
        if not QISKIT_AVAILABLE:
            return self.update_classical(measurement, dt)
        
        start_time = time.time()
        
        try:
            # Xây dựng mạch lượng tử với trạng thái hiện tại
            initial_state = np.concatenate([self.state, measurement])
            qc = self.vqc.build_circuit(initial_state[:4])  # Lấy 4 giá trị đầu
            
            if qc is None:
                return self.update_classical(measurement, dt)
            
            # Định nghĩa observable cho ước lượng trạng thái
            # Sử dụng Pauli-Z measurement trên tất cả qubits
            observable = SparsePauliOp.from_list([("Z" * self.vqc.num_qubits, 1.0)])
            
            # Chạy VQE cho ước lượng trạng thái tối ưu
            initial_point = np.random.random(len(self.vqc.parameters))
            quantum_estimate = self.vqc.run_vqe(observable, initial_point)
            
            # Chuyển đổi kết quả lượng tử thành cập nhật trạng thái
            innovation = measurement - self.state  # Sai số giữa đo lường và dự đoán
            quantum_gain = np.tanh(quantum_estimate)  # Chuẩn hóa về [-1, 1]
            
            # Áp dụng hiệu chỉnh lượng tử
            K_quantum = self.covariance @ np.eye(4) * quantum_gain
            self.state += K_quantum @ innovation
            
            # Cập nhật ma trận hiệp phương sai
            I = np.eye(4)
            self.covariance = (I - K_quantum) @ self.covariance
            
            processing_time = time.time() - start_time
            logger.debug(f"Cập nhật lượng tử hoàn thành trong {processing_time:.4f}s")
            
            return self.state.copy()
            
        except Exception as e:
            logger.warning(f"Cập nhật lượng tử thất bại: {e}, chuyển sang phương pháp cổ điển")
            return self.update_classical(measurement, dt)
    
    def update_classical(self, measurement: np.ndarray, dt: float) -> np.ndarray:
        """Classical Kalman update (fallback)"""
        # Kalman gain
        S = self.covariance + self.R
        K = self.covariance @ np.linalg.inv(S)
        
        # State update
        innovation = measurement - self.state
        self.state += K @ innovation
        
        # Covariance update
        I = np.eye(4)
        self.covariance = (I - K) @ self.covariance
        
        return self.state.copy()
    
    def process_sensor_data(self, sensor_data: SensorData) -> Dict:
        """Process IMU data through quantum filter"""
        # Extract relevant measurements
        measurement = np.array([
            sensor_data.accel_x,
            sensor_data.accel_y, 
            sensor_data.accel_z,
            sensor_data.gyro_z  # Most important for flying wing
        ])
        
        # Assume fixed time step for now
        dt = 0.01
        
        # Prediction step
        predicted_state = self.predict(dt)
        
        # Quantum update step
        start_time = time.time()
        filtered_state = self.update_quantum(measurement, dt)
        quantum_time = time.time() - start_time
        
        # Store history
        self.state_history.append({
            'timestamp': sensor_data.timestamp,
            'raw_measurement': measurement.tolist(),
            'filtered_state': filtered_state.tolist(),
            'quantum_processing_time': quantum_time
        })
        
        return {
            'timestamp': sensor_data.timestamp,
            'filtered_state': filtered_state,
            'quantum_confidence': self._calculate_confidence(),
            'processing_time': quantum_time
        }
    
    def _calculate_confidence(self) -> float:
        """Calculate confidence based on covariance matrix"""
        # Use determinant of covariance as confidence measure
        cov_det = np.linalg.det(self.covariance)
        confidence = 1.0 / (1.0 + cov_det)  # Map to [0, 1]
        return float(confidence)


class ShadowModeComparator:
    """Compare QKF performance with standard EKF in shadow mode"""
    
    def __init__(self):
        self.qkf = QuantumKalmanFilter()
        self.comparison_history = []
        self.performance_metrics = {
            'qkf_processing_times': [],
            'ekf_processing_times': [],
            'state_differences': [],
            'confidence_scores': []
        }
    
    def process_comparison(self, sensor_data: SensorData, ekf_state: np.ndarray, 
                          ekf_confidence: float, ekf_processing_time: float) -> FilterComparison:
        """Process data through both filters and compare results"""
        
        # Process through Quantum Kalman Filter
        qkf_start = time.time()
        qkf_result = self.qkf.process_sensor_data(sensor_data)
        qkf_time = time.time() - qkf_start
        
        # Create comparison
        comparison = FilterComparison(
            timestamp=sensor_data.timestamp,
            qkf_state=qkf_result['filtered_state'],
            ekf_state=ekf_state,
            qkf_confidence=qkf_result['quantum_confidence'],
            ekf_confidence=ekf_confidence,
            processing_time_qkf=qkf_time,
            processing_time_ekf=ekf_processing_time
        )
        
        # Update performance metrics
        self._update_metrics(comparison)
        self.comparison_history.append(comparison)
        
        return comparison
    
    def _update_metrics(self, comparison: FilterComparison):
        """Update performance metrics"""
        self.performance_metrics['qkf_processing_times'].append(comparison.processing_time_qkf)
        self.performance_metrics['ekf_processing_times'].append(comparison.processing_time_ekf)
        
        state_diff = np.linalg.norm(comparison.qkf_state - comparison.ekf_state)
        self.performance_metrics['state_differences'].append(state_diff)
        
        confidence_diff = abs(comparison.qkf_confidence - comparison.ekf_confidence)
        self.performance_metrics['confidence_scores'].append({
            'qkf': comparison.qkf_confidence,
            'ekf': comparison.ekf_confidence,
            'difference': confidence_diff
        })
    
    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        if not self.comparison_history:
            return {}
        
        metrics = self.performance_metrics
        
        report = {
            'total_comparisons': len(self.comparison_history),
            'average_processing_times': {
                'qkf': np.mean(metrics['qkf_processing_times']),
                'ekf': np.mean(metrics['ekf_processing_times']),
                'ratio': np.mean(metrics['qkf_processing_times']) / np.mean(metrics['ekf_processing_times'])
            },
            'state_difference_analysis': {
                'mean': np.mean(metrics['state_differences']),
                'std': np.std(metrics['state_differences']),
                'max': np.max(metrics['state_differences'])
            },
            'confidence_analysis': {
                'qkf_mean': np.mean([c['qkf'] for c in metrics['confidence_scores']]),
                'ekf_mean': np.mean([c['ekf'] for c in metrics['confidence_scores']]),
                'mean_difference': np.mean([c['difference'] for c in metrics['confidence_scores']])
            }
        }
        
        return report


def main():
    """Test quantum kalman filter"""
    print("Testing Quantum Kalman Filter...")
    
    if not QISKIT_AVAILABLE:
        print("Qiskit not available - install with: pip install qiskit")
        print("This is normal on resource-constrained systems")
        return
    
    # Create test sensor data
    test_data = SensorData(
        timestamp=time.time(),
        accel_x=0.1, accel_y=-0.05, accel_z=9.8,
        gyro_x=0.01, gyro_y=0.02, gyro_z=0.05,
        mag_x=0.1, mag_y=0.2, mag_z=0.3
    )
    
    # Test quantum filter
    qkf = QuantumKalmanFilter()
    result = qkf.process_sensor_data(test_data)
    
    print(f"Quantum Filter Result:")
    print(f"  Filtered State: {result['filtered_state']}")
    print(f"  Confidence: {result['quantum_confidence']:.3f}")
    print(f"  Processing Time: {result['processing_time']:.4f}s")


if __name__ == "__main__":
    main()