"""
Ground Control Station - ML Training Server

Server chạy trên Laptop/PC để:
1. Nhận flight data từ UAV (qua 5G/WiFi)
2. Train model phức tạp (Neural Network, Random Forest)
3. Export lightweight model cho RPi
4. Sync model về UAV khi có kết nối

Chạy: python ml_server.py --port 8080

Author: Trương Công Định & Đặng Duy Long
Date: 2025-12-01
"""

import os
import json
import time
import pickle
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import numpy as np

# Flask for REST API
try:
    from flask import Flask, request, jsonify, send_file
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️ Flask not installed. Run: pip install flask")

# ML Libraries
try:
    from sklearn.linear_model import Ridge
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, r2_score
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ scikit-learn not installed. Run: pip install scikit-learn")

# Optional: PyTorch for advanced models
try:
    import torch
    import torch.nn as nn
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False


# ==============================================================================
# Configuration
# ==============================================================================

@dataclass
class ServerConfig:
    """Server configuration"""
    host: str = "0.0.0.0"
    port: int = 8080
    data_dir: str = "./flight_data"
    model_dir: str = "./models"
    min_samples_for_training: int = 100
    auto_train_interval: int = 300  # 5 minutes
    model_type: str = "gradient_boosting"  # ridge, random_forest, gradient_boosting, neural_network


# ==============================================================================
# Data Storage
# ==============================================================================

class FlightDataStore:
    """Store and manage flight data from multiple UAVs"""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory buffer
        self.buffer: List[Dict] = []
        self.max_buffer_size = 10000
        
        # Statistics
        self.total_samples = 0
        self.flights_received = 0
        
        # Load existing data
        self._load_existing_data()
    
    def _load_existing_data(self):
        """Load previously saved data"""
        for file in self.data_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.buffer.extend(data[-1000:])  # Last 1000 per file
                        self.total_samples += len(data)
            except Exception as e:
                print(f"Error loading {file}: {e}")
        
        print(f"📂 Loaded {self.total_samples} existing samples")
    
    def add_samples(self, samples: List[Dict], uav_id: str = "default"):
        """Add new samples from UAV"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Add to buffer
        self.buffer.extend(samples)
        self.total_samples += len(samples)
        self.flights_received += 1
        
        # Trim buffer if too large
        if len(self.buffer) > self.max_buffer_size:
            self.buffer = self.buffer[-self.max_buffer_size:]
        
        # Save to file
        filename = self.data_dir / f"flight_{uav_id}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(samples, f)
        
        print(f"📥 Received {len(samples)} samples from UAV {uav_id}")
        return len(samples)
    
    def get_training_data(self) -> tuple:
        """Get data ready for training"""
        if len(self.buffer) < 50:
            return None, None
        
        X = []
        y = []
        
        for sample in self.buffer:
            try:
                # Extract features
                imu = sample.get('imu', {})
                features = [
                    imu.get('accel', [0, 0, -9.8])[0],
                    imu.get('accel', [0, 0, -9.8])[1],
                    imu.get('accel', [0, 0, -9.8])[2],
                    imu.get('gyro', [0, 0, 0])[0],
                    imu.get('gyro', [0, 0, 0])[1],
                    imu.get('gyro', [0, 0, 0])[2],
                    1.0 if sample.get('gps_valid', False) else 0.0,
                    sample.get('airspeed', 15.0) or 15.0
                ]
                
                # Target: DR error
                dr_error = sample.get('dr_error', None)
                if dr_error is not None:
                    X.append(features)
                    y.append(dr_error)
                    
            except Exception:
                continue
        
        if len(X) < 50:
            return None, None
        
        return np.array(X), np.array(y)
    
    def get_stats(self) -> Dict:
        """Get data statistics"""
        return {
            "total_samples": self.total_samples,
            "buffer_size": len(self.buffer),
            "flights_received": self.flights_received
        }


# ==============================================================================
# Model Training
# ==============================================================================

class ModelTrainer:
    """Train and manage ML models"""
    
    def __init__(self, model_dir: str, model_type: str = "gradient_boosting"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Training history
        self.training_history = []
        
        # Load existing model
        self._load_model()
    
    def _load_model(self):
        """Load previously trained model"""
        model_path = self.model_dir / "current_model.joblib"
        scaler_path = self.model_dir / "current_scaler.joblib"
        
        if model_path.exists() and scaler_path.exists():
            try:
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                self.is_trained = True
                print(f"📦 Loaded existing model: {self.model_type}")
            except Exception as e:
                print(f"Error loading model: {e}")
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Train model on data"""
        if X is None or len(X) < 50:
            return {"error": "Insufficient data"}
        
        print(f"\n🎓 Training {self.model_type} model on {len(X)} samples...")
        start_time = time.time()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Create model based on type
        if self.model_type == "ridge":
            self.model = Ridge(alpha=1.0)
        elif self.model_type == "random_forest":
            self.model = RandomForestRegressor(
                n_estimators=50, 
                max_depth=10,
                n_jobs=-1,
                random_state=42
            )
        elif self.model_type == "gradient_boosting":
            self.model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
        else:
            self.model = Ridge(alpha=1.0)
        
        # Train
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        training_time = time.time() - start_time
        
        # Save model
        self._save_model()
        
        # Record history
        result = {
            "model_type": self.model_type,
            "samples": len(X),
            "mse": float(mse),
            "rmse": float(np.sqrt(mse)),
            "r2": float(r2),
            "training_time": training_time,
            "timestamp": datetime.now().isoformat()
        }
        self.training_history.append(result)
        self.is_trained = True
        
        print(f"✅ Training complete!")
        print(f"   MSE: {mse:.4f}, RMSE: {np.sqrt(mse):.4f}, R²: {r2:.4f}")
        print(f"   Time: {training_time:.2f}s")
        
        return result
    
    def _save_model(self):
        """Save model to disk"""
        joblib.dump(self.model, self.model_dir / "current_model.joblib")
        joblib.dump(self.scaler, self.model_dir / "current_scaler.joblib")
        
        # Also save as timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        joblib.dump(self.model, self.model_dir / f"model_{timestamp}.joblib")
    
    def export_lightweight_model(self) -> Optional[Dict]:
        """Export lightweight model for RPi"""
        if not self.is_trained:
            return None
        
        # For Ridge: export coefficients directly
        if self.model_type == "ridge" or isinstance(self.model, Ridge):
            return {
                "type": "ridge",
                "coefficients": self.model.coef_.tolist(),
                "intercept": float(self.model.intercept_),
                "scaler_mean": self.scaler.mean_.tolist(),
                "scaler_scale": self.scaler.scale_.tolist()
            }
        
        # For tree models: export full model (larger)
        else:
            model_bytes = pickle.dumps({
                "model": self.model,
                "scaler": self.scaler
            })
            
            return {
                "type": self.model_type,
                "model_bytes": model_bytes.hex(),
                "size_kb": len(model_bytes) / 1024
            }
    
    def get_optimized_params(self, X_sample: np.ndarray) -> Dict:
        """Get optimized parameters based on current conditions"""
        if not self.is_trained:
            return {
                'process_noise': 0.01,
                'measurement_noise_gps': 1.0,
                'measurement_noise_vel': 0.1,
                'error_growth_rate': 0.5,
                'confidence_decay_rate': 0.01
            }
        
        try:
            X_scaled = self.scaler.transform(X_sample.reshape(1, -1))
            predicted_error = self.model.predict(X_scaled)[0]
            
            # Adjust parameters based on predicted error
            base_params = {
                'process_noise': 0.01,
                'measurement_noise_gps': 1.0,
                'measurement_noise_vel': 0.1,
                'error_growth_rate': 0.5,
                'confidence_decay_rate': 0.01
            }
            
            if predicted_error > 10.0:
                base_params['process_noise'] *= 1.5
                base_params['error_growth_rate'] *= 1.3
            elif predicted_error < 2.0:
                base_params['process_noise'] *= 0.7
                base_params['error_growth_rate'] *= 0.8
            
            return base_params
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return {
                'process_noise': 0.01,
                'measurement_noise_gps': 1.0,
                'measurement_noise_vel': 0.1,
                'error_growth_rate': 0.5,
                'confidence_decay_rate': 0.01
            }


# ==============================================================================
# Flask REST API Server
# ==============================================================================

def create_app(config: ServerConfig) -> Flask:
    """Create Flask application"""
    app = Flask(__name__)
    
    # Initialize components
    data_store = FlightDataStore(config.data_dir)
    trainer = ModelTrainer(config.model_dir, config.model_type)
    
    # Auto-training thread
    def auto_train_loop():
        while True:
            time.sleep(config.auto_train_interval)
            if data_store.total_samples >= config.min_samples_for_training:
                X, y = data_store.get_training_data()
                if X is not None:
                    trainer.train(X, y)
    
    training_thread = threading.Thread(target=auto_train_loop, daemon=True)
    training_thread.start()
    
    # Routes
    @app.route('/api/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify({
            "status": "ok",
            "server": "Flying Wing UAV ML Server",
            "model_trained": trainer.is_trained,
            "data_samples": data_store.total_samples
        })
    
    @app.route('/api/ml/upload', methods=['POST'])
    def upload_data():
        """Receive flight data from UAV"""
        try:
            data = request.json
            samples = data.get('training_data', [])
            uav_id = data.get('uav_id', 'default')
            
            count = data_store.add_samples(samples, uav_id)
            
            return jsonify({
                "status": "ok",
                "samples_received": count,
                "total_samples": data_store.total_samples
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route('/api/ml/train', methods=['POST'])
    def train_model():
        """Train model with uploaded data"""
        try:
            # Also accept inline data
            data = request.json or {}
            if 'training_data' in data:
                samples = data['training_data']
                data_store.add_samples(samples, data.get('uav_id', 'api'))
            
            # Get training data
            X, y = data_store.get_training_data()
            
            if X is None:
                return jsonify({
                    "error": "Insufficient data",
                    "samples": data_store.total_samples,
                    "required": config.min_samples_for_training
                }), 400
            
            # Train
            result = trainer.train(X, y)
            
            # Return optimized params
            result['optimized_params'] = trainer.get_optimized_params(X[0])
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/ml/model', methods=['GET'])
    def get_model():
        """Download lightweight model for RPi"""
        model_data = trainer.export_lightweight_model()
        
        if model_data is None:
            return jsonify({"error": "No trained model available"}), 404
        
        return jsonify(model_data)
    
    @app.route('/api/ml/params', methods=['POST'])
    def get_params():
        """Get optimized parameters for current conditions"""
        try:
            data = request.json
            features = np.array([
                data.get('accel_x', 0),
                data.get('accel_y', 0),
                data.get('accel_z', -9.8),
                data.get('gyro_x', 0),
                data.get('gyro_y', 0),
                data.get('gyro_z', 0),
                1.0 if data.get('gps_valid', False) else 0.0,
                data.get('airspeed', 15.0)
            ])
            
            params = trainer.get_optimized_params(features)
            return jsonify({"optimized_params": params})
            
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route('/api/stats', methods=['GET'])
    def get_stats():
        """Get server statistics"""
        return jsonify({
            "data": data_store.get_stats(),
            "model": {
                "type": trainer.model_type,
                "is_trained": trainer.is_trained,
                "training_history": trainer.training_history[-10:]
            }
        })
    
    @app.route('/api/ml/force_train', methods=['POST'])
    def force_train():
        """Force immediate training"""
        X, y = data_store.get_training_data()
        if X is not None:
            result = trainer.train(X, y)
            return jsonify(result)
        return jsonify({"error": "No data available"}), 400
    
    return app


# ==============================================================================
# Main Entry Point
# ==============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Flying Wing UAV - ML Training Server")
    parser.add_argument('--host', default='0.0.0.0', help='Server host')
    parser.add_argument('--port', type=int, default=8080, help='Server port')
    parser.add_argument('--data-dir', default='./flight_data', help='Flight data directory')
    parser.add_argument('--model-dir', default='./models', help='Model directory')
    parser.add_argument('--model-type', default='gradient_boosting', 
                       choices=['ridge', 'random_forest', 'gradient_boosting'],
                       help='Model type to train')
    
    args = parser.parse_args()
    
    if not FLASK_AVAILABLE:
        print("❌ Flask is required. Install with: pip install flask")
        return
    
    if not SKLEARN_AVAILABLE:
        print("❌ scikit-learn is required. Install with: pip install scikit-learn")
        return
    
    config = ServerConfig(
        host=args.host,
        port=args.port,
        data_dir=args.data_dir,
        model_dir=args.model_dir,
        model_type=args.model_type
    )
    
    print("=" * 60)
    print("   FLYING WING UAV - ML TRAINING SERVER")
    print("=" * 60)
    print(f"   Host: {config.host}:{config.port}")
    print(f"   Model: {config.model_type}")
    print(f"   Data: {config.data_dir}")
    print("=" * 60)
    print("\n📡 API Endpoints:")
    print(f"   GET  /api/health       - Health check")
    print(f"   POST /api/ml/upload    - Upload flight data")
    print(f"   POST /api/ml/train     - Train model")
    print(f"   GET  /api/ml/model     - Download model for RPi")
    print(f"   POST /api/ml/params    - Get optimized params")
    print(f"   GET  /api/stats        - Server statistics")
    print("=" * 60)
    
    app = create_app(config)
    app.run(host=config.host, port=config.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
