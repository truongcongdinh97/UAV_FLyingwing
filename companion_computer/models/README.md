# AI Models Directory

Thư mục này chứa các AI models cho edge inference trên Raspberry Pi.

## Models Được Đề Xuất

### 1. MobileNet SSD v2 (COCO)
- **File**: `mobilenet_ssd_v2.tflite`
- **Input**: 300x300 RGB
- **Classes**: 90 (COCO dataset)
- **Use case**: General object detection
- **Download**: 
  ```bash
  wget https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
  unzip coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
  mv detect.tflite mobilenet_ssd_v2.tflite
  ```

### 2. EfficientDet Lite (Nếu cần accuracy cao hơn)
- **File**: `efficientdet_lite0.tflite`
- **Input**: 320x320 RGB
- **Classes**: 90 (COCO)
- **Download**: https://tfhub.dev/tensorflow/efficientdet/lite0/detection/1

### 3. Custom Model (Nếu train riêng)
- Train model riêng cho specific objects (người, xe, động vật, etc.)
- Convert sang TFLite format
- Optimize cho edge devices

## Model Format

Models phải ở dạng TensorFlow Lite (`.tflite`) để chạy trên Raspberry Pi.

## Conversion

Nếu bạn có PyTorch hoặc TensorFlow model, convert sang TFLite:

```python
import tensorflow as tf

# Load model
model = tf.keras.models.load_model('model.h5')

# Convert
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]  # Quantization
tflite_model = converter.convert()

# Save
with open('model.tflite', 'wb') as f:
    f.write(tflite_model)
```

## Performance Tips

- **Quantization**: Sử dụng INT8 quantization để tăng tốc độ
- **Input Size**: Giảm input size (e.g., 300x300 thay vì 640x640) để tăng FPS
- **Edge TPU**: Nếu có Google Coral Edge TPU, compile model cho TPU để tăng tốc 10-20x

## Testing

Test model trước khi deploy:

```python
cd companion_computer
python src/ai/object_detector.py
```
