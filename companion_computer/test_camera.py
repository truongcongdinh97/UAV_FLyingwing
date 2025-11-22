"""
Simple Camera Test
Test camera với visualization window
"""

import sys
import os
import cv2

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from camera import CameraInterface

def main():
    print("=" * 70)
    print("CAMERA TEST - Press 'q' to quit")
    print("=" * 70)
    
    camera = CameraInterface()
    
    if not camera.start():
        print("❌ Failed to start camera")
        print("Note: This is normal if you don't have a webcam")
        return
    
    print("✅ Camera started")
    print(f"📐 Resolution: {camera.get_frame_dimensions()}")
    print("\n💡 Press 'q' to quit\n")
    
    frame_count = 0
    
    try:
        while True:
            frame = camera.read_frame()
            
            if frame is not None:
                frame_count += 1
                
                # Add info overlay
                cv2.putText(frame, f"Frame: {frame_count}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           1, (0, 255, 0), 2)
                
                cv2.putText(frame, "Press 'q' to quit", 
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (0, 255, 255), 2)
                
                # Show frame
                cv2.imshow('Flying Wing UAV - Camera Test', frame)
                
                # Print info every 30 frames
                if frame_count % 30 == 0:
                    print(f"✅ Captured {frame_count} frames")
            else:
                print("⚠️  No frame available")
                break
            
            # Exit on 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    
    finally:
        camera.stop()
        cv2.destroyAllWindows()
        print(f"\n✅ Test completed - Total frames: {frame_count}")

if __name__ == "__main__":
    main()
