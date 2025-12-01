# Hướng Dẫn Training Model cho Flying Wing UAV

## 📋 Tổng Quan

Hướng dẫn này cung cấp các bước chi tiết để training custom object detection models cho ứng dụng UAV. Models được tối ưu hóa cho edge inference trên Raspberry Pi với TensorFlow Lite.

## 📁 Cấu Trúc Thư Mục Models

```
models/
├── README.md                    # Tài liệu models hiện có
├── TRAINING_GUIDE.md           # Hướng dẫn này
├── coco_labels.txt             # COCO dataset labels
├── mobilenet_ssd_v2.tflite     # Pretrained model
├── training/                   # Scripts và configs cho training
│   ├── configs/               # Training configurations
│   ├── scripts/               # Training scripts
│   └── utils/                 # Utility functions
├── pretrained/                # Pretrained models từ các frameworks
│   ├── tensorflow/
│   ├── pytorch/
│   └── yolov5/
├── custom/                    # Custom trained models
│   ├── uav_people_detector/
│   ├── vehicle_detector/
│   └── search_rescue/
├── datasets/                  # Training datasets
│   ├── raw/                  # Raw images và annotations
│   ├── processed/            # Processed data cho training
│   └── splits/               # Train/val/test splits
├── checkpoints/              # Training checkpoints
│   ├── best_weights/
│   └── last_weights/
└── exported/                 # Exported models ready for deployment
    ├── tflite/              # TensorFlow Lite models
    ├── onnx/                # ONNX format
    └── openvino/            # OpenVINO format
```

## 🚀 Quick Start: Training Custom Model

### Bước 1: Chuẩn Bị Môi Trường

```bash
# Tạo virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Cài đặt dependencies
pip install tensorflow==2.13.0
pip install opencv-python==4.8.1
pip install pillow==10.0.0
pip install matplotlib==3.7.2
pip install pycocotools==2.0.7
pip install tqdm==4.66.1
```

### Bước 2: Chuẩn Bị Dataset

1. **Collect Images**: Thu thập ảnh từ UAV flights
2. **Annotation**: Label objects với bounding boxes
3. **Format**: Chuyển đổi sang COCO format hoặc Pascal VOC

**Dataset Structure**:
```
datasets/uav_custom/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
└── annotations/
    ├── train.json  # COCO format
    ├── val.json
    └── test.json
```

### Bước 3: Training với TensorFlow

```python
# training/train_tensorflow.py
import tensorflow as tf
from tensorflow import keras

# Load pretrained model
base_model = keras.applications.EfficientNetB0(
    include_top=False,
    weights='imagenet',
    input_shape=(320, 320, 3)
)

# Add detection head
# ... (xem script đầy đủ trong training/scripts/)
```

### Bước 4: Convert sang TensorFlow Lite

```python
# training/export_tflite.py
import tensorflow as tf

# Load trained model
model = tf.keras.models.load_model('checkpoints/best_model.h5')

# Convert to TFLite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.target_spec.supported_types = [tf.float16]  # FP16 quantization

tflite_model = converter.convert()

# Save
with open('exported/tflite/custom_model.tflite', 'wb') as f:
    f.write(tflite_model)
```

## 📊 Dataset Preparation

### 1. Data Collection từ UAV

**Recommended Tools**:
- **LabelImg**: GUI tool cho annotation
- **CVAT**: Web-based annotation tool
- **Roboflow**: Cloud-based platform

**Classes cho UAV Applications**:
```yaml
classes:
  - person
  - car
  - truck
  - boat
  - airplane
  - bicycle
  - motorcycle
  - bird
  - dog
  - cat
  - sheep
  - cow
  - horse
```

### 2. Data Augmentation

```python
# training/utils/augmentation.py
import albumentations as A

transform = A.Compose([
    A.HorizontalFlip(p=0.5),
    A.RandomBrightnessContrast(p=0.2),
    A.Rotate(limit=15, p=0.3),
    A.RandomScale(scale_limit=0.2, p=0.3),
    A.HueSaturationValue(p=0.3),
], bbox_params=A.BboxParams(format='coco'))
```

### 3. Dataset Splits

```python
# training/utils/split_dataset.py
# Split: 70% train, 15% validation, 15% test
# Đảm bảo class distribution balanced
```

## 🏋️‍♂️ Training Strategies

### 1. Transfer Learning

```python
# Sử dụng pretrained backbone
base_model = tf.keras.applications.MobileNetV2(
    input_shape=(320, 320, 3),
    include_top=False,
    weights='imagenet'
)

# Freeze early layers
for layer in base_model.layers[:100]:
    layer.trainable = False
```

### 2. Multi-Stage Training

**Stage 1**: Fine-tune detection head
**Stage 2**: Fine-tune middle layers
**Stage 3**: Fine-tune entire model với learning rate thấp

### 3. Hyperparameter Tuning

```yaml
# training/configs/hyperparams.yaml
hyperparameters:
  batch_size: 16
  learning_rate: 0.001
  epochs: 100
  optimizer: "adam"
  loss: "focal_loss"
  
  # Learning rate schedule
  lr_schedule:
    warmup_epochs: 5
    cosine_decay: true
    
  # Data augmentation
  augmentation:
    horizontal_flip: 0.5
    rotation: 15
    brightness: 0.2
    contrast: 0.2
```

## 🔧 Model Architectures

### 1. MobileNet SSD (Recommended cho Raspberry Pi)

**Ưu điểm**:
- Nhẹ, fast inference
- Phù hợp cho real-time detection
- Tốt cho edge devices

**Training Command**:
```bash
python training/scripts/train_mobilenet_ssd.py \
  --dataset datasets/uav_custom \
  --epochs 100 \
  --batch_size 16 \
  --output checkpoints/mobilenet_ssd
```

### 2. EfficientDet Lite

**Ưu điểm**:
- Balance accuracy và speed
- State-of-the-art cho mobile devices
- Scalable (Lite0 đến Lite4)

### 3. YOLOv5 Nano

**Ưu điểm**:
- Rất nhanh
- Good accuracy cho small objects
- Dễ training

## 📈 Evaluation Metrics

### 1. Standard Metrics
```python
# training/utils/evaluation.py
metrics = {
    "mAP@0.5": "Mean Average Precision at IoU 0.5",
    "mAP@0.5:0.95": "mAP across IoU thresholds",
    "precision": "TP / (TP + FP)",
    "recall": "TP / (TP + FN)",
    "F1_score": "2 * (precision * recall) / (precision + recall)"
}
```

### 2. UAV-Specific Metrics
```python
metrics_uav = {
    "altitude_robustness": "Performance across altitudes",
    "small_object_detection": "Detection of small objects từ high altitude",
    "real_time_fps": "Frames per second trên Raspberry Pi",
    "memory_usage": "RAM consumption"
}
```

## 🚀 Deployment Pipeline

### 1. Model Optimization

```python
# training/optimize_model.py
def optimize_for_edge(model_path):
    # Quantization
    converter = tf.lite.TFLiteConverter.from_saved_model(model_path)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    
    # Representative dataset for quantization
    def representative_dataset():
        for _ in range(100):
            data = np.random.rand(1, 320, 320, 3).astype(np.float32)
            yield [data]
    
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.uint8
    converter.inference_output_type = tf.uint8
    
    return converter.convert()
```

### 2. Edge TPU Compilation (Nếu có Coral TPU)

```bash
# Compile cho Edge TPU
edgetpu_compiler custom_model.tflite --out_dir exported/edgetpu
```

### 3. Integration với UAV System

```python
# companion_computer/src/ai/object_detector.py
class CustomObjectDetector(ObjectDetector):
    def __init__(self, model_path="models/custom/uav_model.tflite"):
        # Load optimized model
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        
    def detect(self, frame):
        # Preprocess
        input_tensor = self.preprocess(frame)
        
        # Inference
        self.interpreter.set_tensor(self.input_details[0]['index'], input_tensor)
        self.interpreter.invoke()
        
        # Post-process
        boxes = self.interpreter.get_tensor(self.output_details[0]['index'])
        classes = self.interpreter.get_tensor(self.output_details[1]['index'])
        scores = self.interpreter.get_tensor(self.output_details[2]['index'])
        
        return self.postprocess(boxes, classes, scores)
```

## 📋 Training Checklist

### Trước Training
- [ ] Dataset đã được labeled và reviewed
- [ ] Class distribution balanced
- [ ] Train/val/test splits created
- [ ] Data augmentation pipeline ready
- [ ] Evaluation metrics defined

### Trong Training
- [ ] Monitor training loss và validation metrics
- [ ] Check for overfitting/underfitting
- [ ] Save best checkpoints
- [ ] TensorBoard logging enabled

### Sau Training
- [ ] Evaluate trên test set
- [ ] Optimize model cho edge deployment
- [ ] Test inference speed trên target hardware
- [ ] Document model performance

## 🛠️ Utility Scripts

### 1. Dataset Preparation
```bash
python training/scripts/prepare_dataset.py \
  --input datasets/raw \
  --output datasets/processed \
  --format coco
```

### 2. Training
```bash
python training/scripts/train.py \
  --config training/configs/mobilenet_ssd.yaml \
  --gpu 0
```

### 3. Evaluation
```bash
python training/scripts/evaluate.py \
  --model checkpoints/best_model.h5 \
  --dataset datasets/test
```

### 4. Export
```bash
python training/scripts/export_model.py \
  --checkpoint checkpoints/best_model.h5 \
  --output exported/tflite \
  --quantize int8
```

## 🔍 Debugging Tips

### 1. Common Issues
- **Low Accuracy**: Thử data augmentation, increase dataset size
- **Overfitting**: Thêm regularization, dropout, hoặc reduce model complexity
- **Slow Inference**: Reduce input size, quantization, hoặc sử dụng lighter model
- **Memory Issues**: Reduce batch size, sử dụng gradient accumulation

### 2. Performance Optimization
```python
# Enable XLA compilation
tf.config.optimizer.set_jit(True)

# Mixed precision training
tf.keras.mixed_precision.set_global_policy('mixed_float16')

# GPU memory growth
gpus = tf.config.experimental.list_physical_devices('GPU')
for gpu in gpus:
    tf.config.experimental.set_memory_growth(gpu, True)
```

## 📚 Resources

### 1. Pretrained Models
- [TensorFlow Model Zoo](https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/tf2_detection_zoo.md)
- [PyTorch Vision Models](https://pytorch.org/vision/stable/models.html)
- [Ultralytics YOLOv5](https://github.com/ultralytics/yolov5)

### 2. Annotation Tools
- [LabelImg](https://github.com/tzutalin/labelImg)
- [CVAT](https://github.com/openvinotoolkit/cvat)
- [Roboflow](https://roboflow.com)

### 3. Training Platforms
- [Google Colab](https://colab.research.google.com/)
- [Kaggle Notebooks](https://www.kaggle.com/notebooks)
- [AWS SageMaker](https://aws.amazon.com/sagemaker/)

## 🎯 Best Practices cho UAV Models

### 1. Altitude-Aware Training
- Train với images từ multiple altitudes
- Augment với scale variations
- Test across altitude ranges

### 2. Real-Time Constraints
- Target FPS > 15 cho real-time tracking
- Model size < 50MB cho Raspberry Pi
- CPU usage < 80% để tránh overheating

### 3. Field Validation
- Test trong real flight conditions
- Validate với different lighting conditions
- Test với motion blur từ UAV movement

## 📞 Support

1. **Issues**: Tạo issue trên GitHub repository
2. **Questions**: Check documentation và examples
3. **Contributions**: Pull requests welcome!

---

**Lưu ý**: Luôn test model thoroughly trước khi deploy lên UAV. Safety first!

*Last Updated: December 2025*
*Version: 1.0.0*
