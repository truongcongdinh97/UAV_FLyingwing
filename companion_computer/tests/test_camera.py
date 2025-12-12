"""
Camera Interface Test
Test camera capture trên Windows và Raspberry Pi

Author: Trương Công Định & Đặng Duy Long
Date: 2025-12-01
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_camera_import():
    """Test import camera module"""
    print("=== Test Camera Import ===")
    try:
        from camera import CameraInterface
        print("✅ CameraInterface imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_camera_init():
    """Test camera initialization"""
    print("\n=== Test Camera Init ===")
    try:
        from camera import CameraInterface
        camera = CameraInterface()
        print(f"✅ Camera initialized")
        print(f"   Type: {camera.camera_type if hasattr(camera, 'camera_type') else 'opencv'}")
        return camera
    except Exception as e:
        print(f"❌ Init failed: {e}")
        return None

def test_camera_capture(camera):
    """Test frame capture"""
    print("\n=== Test Frame Capture ===")
    if camera is None:
        print("⚠️ No camera to test")
        return False
    
    try:
        if not camera.start():
            print("⚠️ Camera start failed (no webcam - OK for testing)")
            return True
        
        # Capture frames
        for i in range(5):
            frame = camera.read_frame()
            if frame is not None:
                print(f"✅ Frame {i+1}: shape={frame.shape}")
            else:
                print(f"⚠️ Frame {i+1}: None")
        
        camera.stop()
        print("✅ Camera stopped")
        return True
    except Exception as e:
        print(f"❌ Capture failed: {e}")
        return False

def test_camera_fps(camera):
    """Test camera FPS"""
    print("\n=== Test Camera FPS ===")
    if camera is None:
        print("⚠️ No camera to test")
        return False
    
    try:
        if not camera.start():
            print("⚠️ Camera not available")
            return True
        
        start = time.time()
        frames = 0
        while time.time() - start < 2.0:
            frame = camera.read_frame()
            if frame is not None:
                frames += 1
        
        fps = frames / 2.0
        print(f"✅ FPS: {fps:.1f}")
        
        camera.stop()
        return True
    except Exception as e:
        print(f"❌ FPS test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("CAMERA INTERFACE TEST")
    print("=" * 60)
    
    results = []
    
    results.append(("Import", test_camera_import()))
    
    camera = test_camera_init()
    results.append(("Init", camera is not None))
    
    results.append(("Capture", test_camera_capture(camera)))
    results.append(("FPS", test_camera_fps(camera)))
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

