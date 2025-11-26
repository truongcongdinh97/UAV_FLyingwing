import sys
import os
import time
import cv2
import numpy as np

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from camera.camera_interface import CameraInterface
from ai.object_detector import ObjectDetector

def main():
    print("--- Android AI Detection Test ---")
    
    # 1. Setup Camera
    default_url = "http://192.168.1.102:8080/video"
    print(f"Enter IP Webcam URL (default: {default_url}):")
    user_url = input("> ").strip()
    
    if not user_url:
        user_url = default_url
    
    # Auto-fix URL
    if not user_url.startswith("http"):
        user_url = "http://" + user_url
    if "/video" not in user_url and user_url.count(":") == 2:
        user_url = user_url + "/video"

    print(f"Connecting to {user_url}...")
    
    cam = CameraInterface()
    cam.config['source'] = 'ip_webcam'
    cam.config['ip_url'] = user_url
    cam.config['resolution'] = {'width': 640, 'height': 480}
    
    if not cam.start():
        print("Failed to connect to camera!")
        return

    # 2. Setup Detector
    print("Initializing AI...")
    detector = ObjectDetector()
    
    # Fallback to Face Detection if TFLite model is missing
    use_face_fallback = False
    face_cascade = None
    
    if not detector.is_initialized:
        print("WARNING: TFLite model not found. Switching to OpenCV Face Detection (Demo Mode).")
        use_face_fallback = True
        try:
            cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
            face_cascade = cv2.CascadeClassifier(cascade_path)
            if face_cascade.empty():
                print("Error: Could not load Haar Cascade xml.")
                use_face_fallback = False # This will cause it to fall back to broken TFLite
                # Let's fix this logic
                print("FATAL: No detectors available.")
        except Exception as e:
            print(f"Error loading cascade: {e}")
            use_face_fallback = False

    print("Starting loop. Press 'q' to quit.")
    
    try:
        while True:
            frame = cam.read_frame()
            
            if frame is not None:
                start_time = time.time()
                
                # Logic fix: Explicitly check what to run
                if detector.is_initialized:
                    # Use TFLite Object Detector
                    detections = detector.detect(frame)
                    frame = detector.draw_detections(frame, detections)
                    info = f"Objects: {len(detections)}"
                elif use_face_fallback and face_cascade and not face_cascade.empty():
                    # Use OpenCV Face Detector
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                    
                    for (x, y, w, h) in faces:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                        cv2.putText(frame, "Face", (x, y-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
                    info = f"Faces: {len(faces)}"
                else:
                    info = "No Detector Available"

                # Calculate FPS
                fps = 1.0 / (time.time() - start_time)
                cv2.putText(frame, f"FPS: {fps:.1f} | {info}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                cv2.imshow("Android AI Test", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        cam.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
