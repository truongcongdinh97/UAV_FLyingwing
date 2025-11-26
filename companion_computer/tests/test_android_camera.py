import sys
import os
import time
import cv2

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from camera.camera_interface import CameraInterface

def main():
    print("--- Android Camera Test (IP Webcam) ---")
    
    # Default URL
    default_url = "http://192.168.1.169:8080/video"
    
    print(f"Enter IP Webcam URL (default: {default_url}):")
    user_url = input("> ").strip()
    
    if not user_url:
        user_url = default_url
    
    # Auto-fix URL format
    if not user_url.startswith("http"):
        user_url = "http://" + user_url
    
    if "/video" not in user_url and user_url.count(":") == 2: # simple check for http://ip:port
        user_url = user_url + "/video"
        
    print(f"Connecting to {user_url}...")
    
    # Initialize camera interface
    cam = CameraInterface()
    
    # Override config for testing
    cam.config['source'] = 'ip_webcam'
    cam.config['ip_url'] = user_url
    cam.config['resolution'] = {'width': 640, 'height': 480}
    
    if not cam.start():
        print("Failed to connect to camera!")
        return

    print("Camera connected! Press 'q' to quit.")
    
    try:
        while True:
            frame = cam.read_frame()
            
            if frame is not None:
                cv2.imshow("Android Camera Feed", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        cam.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
