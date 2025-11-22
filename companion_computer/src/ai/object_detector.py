"""
AI Object Detection Module
Sử dụng TensorFlow Lite để detect objects tại biên
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from loguru import logger
import yaml
import os

# TensorFlow Lite
try:
    import tflite_runtime.interpreter as tflite
    TFLITE_AVAILABLE = True
except ImportError:
    logger.warning("TFLite runtime not available")
    TFLITE_AVAILABLE = False


class Detection:
    """Class đại diện cho một detection"""
    
    def __init__(self, bbox: Tuple[int, int, int, int], 
                 class_id: int, class_name: str, 
                 confidence: float):
        """
        Args:
            bbox: (x1, y1, x2, y2) - tọa độ bounding box
            class_id: ID của class
            class_name: Tên class
            confidence: Confidence score (0-1)
        """
        self.bbox = bbox
        self.class_id = class_id
        self.class_name = class_name
        self.confidence = confidence
    
    def __repr__(self):
        return f"Detection({self.class_name}, conf={self.confidence:.2f})"


class ObjectDetector:
    """AI Object Detection với TensorFlow Lite"""
    
    def __init__(self, config_path: str = "config/ai_config.yaml"):
        """
        Khởi tạo object detector
        
        Args:
            config_path: Đường dẫn đến file config
        """
        self.config = self._load_config(config_path)
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.labels = []
        self.is_initialized = False
        
        # Load model và labels
        if TFLITE_AVAILABLE:
            self._load_model()
            self._load_labels()
        else:
            logger.warning("TFLite not available - detector disabled")
        
        logger.info("Object detector initialized")
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config['ai']
        else:
            logger.warning(f"Config not found: {config_path}")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """Default configuration"""
        return {
            'model_path': 'models/mobilenet_ssd_v2.tflite',
            'labels_path': 'models/coco_labels.txt',
            'confidence_threshold': 0.5,
            'input_size': [300, 300],
            'num_threads': 4,
        }
    
    def _load_model(self):
        """Load TFLite model"""
        model_path = self.config['model_path']
        
        if not os.path.exists(model_path):
            logger.error(f"Model not found: {model_path}")
            return
        
        try:
            # Create interpreter
            self.interpreter = tflite.Interpreter(
                model_path=model_path,
                num_threads=self.config.get('num_threads', 4)
            )
            self.interpreter.allocate_tensors()
            
            # Get input and output details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            self.is_initialized = True
            logger.info(f"Model loaded: {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
    
    def _load_labels(self):
        """Load class labels"""
        labels_path = self.config['labels_path']
        
        if not os.path.exists(labels_path):
            logger.warning(f"Labels not found: {labels_path}")
            # Use default COCO labels
            self.labels = [f"class_{i}" for i in range(90)]
            return
        
        try:
            with open(labels_path, 'r') as f:
                self.labels = [line.strip() for line in f.readlines()]
            logger.info(f"Loaded {len(self.labels)} labels")
        except Exception as e:
            logger.error(f"Failed to load labels: {e}")
            self.labels = []
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Tiền xử lý ảnh cho model
        
        Args:
            image: Input image (BGR)
            
        Returns:
            Preprocessed image tensor
        """
        # Get input size
        input_size = self.config['input_size']
        
        # Resize
        input_image = cv2.resize(image, tuple(input_size))
        
        # Convert BGR to RGB
        input_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
        
        # Normalize (0-255 to 0-1 nếu model yêu cầu)
        # Kiểm tra input details để xác định
        if self.input_details[0]['dtype'] == np.float32:
            input_image = input_image.astype(np.float32) / 255.0
        else:
            input_image = input_image.astype(np.uint8)
        
        # Add batch dimension
        input_image = np.expand_dims(input_image, axis=0)
        
        return input_image
    
    def detect(self, image: np.ndarray) -> List[Detection]:
        """
        Detect objects trong image
        
        Args:
            image: Input image (BGR format)
            
        Returns:
            List of Detection objects
        """
        if not self.is_initialized:
            return []
        
        try:
            # Preprocess
            input_tensor = self.preprocess_image(image)
            
            # Run inference
            self.interpreter.set_tensor(
                self.input_details[0]['index'], 
                input_tensor
            )
            self.interpreter.invoke()
            
            # Get outputs
            # Giả định model output format: [boxes, classes, scores, num_detections]
            boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
            classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
            scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]
            
            # Parse detections
            detections = self._parse_detections(
                boxes, classes, scores, image.shape
            )
            
            return detections
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []
    
    def _parse_detections(self, boxes: np.ndarray, classes: np.ndarray,
                         scores: np.ndarray, image_shape: Tuple) -> List[Detection]:
        """Parse model outputs thành Detection objects"""
        detections = []
        confidence_threshold = self.config['confidence_threshold']
        target_classes = self.config.get('target_classes', None)
        
        height, width = image_shape[:2]
        
        for i, score in enumerate(scores):
            if score < confidence_threshold:
                continue
            
            # Get class
            class_id = int(classes[i])
            if class_id >= len(self.labels):
                continue
            
            class_name = self.labels[class_id]
            
            # Filter target classes if specified
            if target_classes and class_name not in target_classes:
                continue
            
            # Get bbox (normalized coordinates: ymin, xmin, ymax, xmax)
            ymin, xmin, ymax, xmax = boxes[i]
            
            # Convert to pixel coordinates
            x1 = int(xmin * width)
            y1 = int(ymin * height)
            x2 = int(xmax * width)
            y2 = int(ymax * height)
            
            detection = Detection(
                bbox=(x1, y1, x2, y2),
                class_id=class_id,
                class_name=class_name,
                confidence=float(score)
            )
            
            detections.append(detection)
        
        return detections
    
    def draw_detections(self, image: np.ndarray, 
                       detections: List[Detection]) -> np.ndarray:
        """
        Vẽ bounding boxes lên ảnh
        
        Args:
            image: Input image
            detections: List of detections
            
        Returns:
            Image với bounding boxes
        """
        output = image.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            
            # Draw box
            color = self.config.get('box_color', [0, 255, 0])
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{det.class_name}: {det.confidence:.2f}"
            text_color = self.config.get('text_color', [255, 255, 255])
            
            # Background for text
            (text_w, text_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(output, (x1, y1 - text_h - 10), 
                         (x1 + text_w, y1), color, -1)
            
            # Text
            cv2.putText(output, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
        
        return output


def main():
    """Test object detector"""
    print("Testing Object Detector...")
    
    # Create dummy detector for testing
    detector = ObjectDetector()
    
    if not detector.is_initialized:
        print("Detector not initialized - model not available")
        print("This is normal on Windows. Deploy to Pi to test with actual model.")
        return
    
    print("Detector initialized successfully")
    print(f"Labels: {len(detector.labels)}")
    print(f"Confidence threshold: {detector.config['confidence_threshold']}")


if __name__ == "__main__":
    main()
