# Testing Guide - Windows

Hướng dẫn test code Companion Computer trên Windows trước khi deploy lên Raspberry Pi.

## 📦 Setup

### 1. Install Dependencies

```powershell
cd companion_computer
pip install numpy opencv-python PyYAML loguru pyserial requests python-dateutil
```

### 2. Verify Installation

```powershell
python test_windows.py
```

Kết quả mong đợi: Tất cả modules import thành công ✅

## 🧪 Test Scripts

### 1. Full System Test
```powershell
python test_windows.py
```
Test tất cả modules cùng lúc.

### 2. Camera Test
```powershell
python test_camera.py
```
- Test camera interface
- Hiển thị video window (nếu có webcam)
- Press 'q' để thoát

**Note**: Nếu không có webcam, camera sẽ fail gracefully - OK cho testing.

### 3. Logging Test
```powershell
python test_logging.py
```
- Test data logger
- Tạo test logs trong `logs/` directory
- Check log files sau khi chạy

### 4. View Configuration
```powershell
python view_config.py
```
Hiển thị tất cả configuration files với format dễ đọc.

## 📝 Test Results

### Expected Behavior on Windows:

✅ **Camera Module**
- Import thành công
- Fallback to OpenCV mode
- Warning về picamera2 (normal - chỉ có trên Pi)

✅ **AI Module**
- Import thành công
- Warning về TFLite (normal - model sẽ download trên Pi)
- Labels loaded OK

✅ **Communication Module**
- Import thành công
- Warning về pymavlink (optional)
- Serial config loaded OK

✅ **Logging Module**
- Import thành công
- Creates log directory
- Writes test data successfully

✅ **Configuration**
- All YAML files load correctly
- Settings parsed properly

## ⚠️ Expected Warnings

Những warnings này là **bình thường** trên Windows:

1. **picamera2 not available**
   - ✅ OK - chỉ có trên Raspberry Pi
   - Camera fallback to OpenCV

2. **TFLite runtime not available**
   - ✅ OK - sẽ install trên Pi
   - AI detector works without model (testing)

3. **pymavlink not available**
   - ✅ OK - optional dependency
   - Serial communication works with pyserial

4. **Camera index out of range**
   - ✅ OK - no webcam connected
   - Camera interface functions normally

5. **Failed to read frame**
   - ✅ OK - no camera hardware
   - Logic tested successfully

## 🐛 Actual Errors to Fix

Chỉ những errors này cần fix:

❌ **Import errors** (modules not found)
❌ **Syntax errors**
❌ **Configuration parsing errors**
❌ **Logic errors** (crashes, exceptions)

## 📊 Log Files

Sau khi chạy test, check logs:

```powershell
# List log sessions
ls logs

# View latest session
cd logs\<session_id>
cat system.log
cat telemetry.jsonl
cat gps.jsonl
cat events.jsonl
```

## 🔍 Debug Mode

Để xem chi tiết hơn:

```powershell
# Run with debug logging
python src/main.py --debug

# Or edit config
# config/system_config.yaml -> system.debug: true
```

## 📦 Module Testing

Test từng module riêng:

```powershell
# Camera
cd src/camera
python camera_interface.py

# AI
cd src/ai
python object_detector.py

# Communication
cd src/communication
python serial_comm.py

# Logging
cd src/data_logging
python data_logger.py
```

## ✅ Success Criteria

Code ready to deploy nếu:

- ✅ All modules import successfully
- ✅ No syntax errors
- ✅ Configuration files load correctly
- ✅ Logging creates files properly
- ✅ No unexpected crashes

Warnings về hardware (camera, serial, TFLite) là OK!

## 🚀 Next Steps

Sau khi test pass trên Windows:

1. Review code và config
2. Prepare Raspberry Pi
3. Follow `DEPLOYMENT.md` để deploy
4. Test trên Pi với actual hardware

## 💡 Tips

- **Git**: Commit working code trước khi deploy
- **Backup**: Save configurations
- **Document**: Note any custom changes
- **Test**: Test thoroughly on Pi before flight

## 🆘 Troubleshooting

### Import errors
```powershell
pip install --upgrade <package>
```

### YAML errors
- Check indentation (spaces, not tabs)
- Validate YAML syntax

### Path errors
- Use absolute paths in config
- Check file/directory existence

### Module not found
- Verify `src` directory structure
- Check `__init__.py` files exist
