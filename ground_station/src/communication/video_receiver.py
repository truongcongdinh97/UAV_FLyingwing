"""
Video Receiver cho Ground Control Station
Nhận RTSP stream từ companion computer
"""

import cv2
import threading
import time
from typing import Optional, Callable
from loguru import logger
import numpy as np


class VideoReceiver:
    """Receive RTSP video stream"""
    
    def __init__(self, rtsp_url: str = "rtsp://192.168.1.100:8554/video"):
        self.rtsp_url = rtsp_url
        self.cap: Optional[cv2.VideoCapture] = None
        self.connected = False
        
        # Threading
        self.receiver_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Frame buffer
        self.current_frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()
        
        # Stats
        self.frame_count = 0
        self.fps = 0.0
        self.last_fps_time = time.time()
        
        # Callbacks
        self.frame_callback: Optional[Callable] = None
        
    def connect(self, timeout: float = 10.0) -> bool:
        """Connect to RTSP stream"""
        try:
            logger.info(f"Connecting to {self.rtsp_url}...")
            
            # Open video capture
            self.cap = cv2.VideoCapture(self.rtsp_url)
            
            # Set buffer size (reduce latency)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Wait for first frame
            start_time = time.time()
            while time.time() - start_time < timeout:
                ret, frame = self.cap.read()
                if ret:
                    logger.success("Video stream connected")
                    self.connected = True
                    
                    # Start receiver thread
                    self.running = True
                    self.receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
                    self.receiver_thread.start()
                    
                    return True
                time.sleep(0.1)
            
            logger.error("Timeout waiting for video stream")
            return False
            
        except Exception as e:
            logger.error(f"Video connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect video stream"""
        logger.info("Disconnecting video...")
        self.running = False
        
        if self.receiver_thread:
            self.receiver_thread.join(timeout=2.0)
        
        if self.cap:
            self.cap.release()
        
        self.connected = False
        logger.info("Video disconnected")
    
    def _receiver_loop(self):
        """Background thread to receive video frames"""
        logger.info("Video receiver started")
        
        frame_times = []
        
        while self.running:
            try:
                ret, frame = self.cap.read()
                if ret:
                    # Update frame buffer
                    with self.frame_lock:
                        self.current_frame = frame
                    
                    # Update stats
                    self.frame_count += 1
                    current_time = time.time()
                    frame_times.append(current_time)
                    
                    # Calculate FPS (over last second)
                    frame_times = [t for t in frame_times if current_time - t < 1.0]
                    self.fps = len(frame_times)
                    
                    # Call callback
                    if self.frame_callback:
                        try:
                            self.frame_callback(frame)
                        except Exception as e:
                            logger.error(f"Error in frame callback: {e}")
                else:
                    logger.warning("Failed to read frame")
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error receiving frame: {e}")
                if not self.running:
                    break
                time.sleep(0.1)
        
        logger.info("Video receiver stopped")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get latest frame"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None
    
    def register_callback(self, callback: Callable):
        """Register callback for new frames"""
        self.frame_callback = callback
        logger.debug("Registered frame callback")
    
    def get_fps(self) -> float:
        """Get current FPS"""
        return self.fps
    
    def get_resolution(self) -> Optional[tuple]:
        """Get video resolution (width, height)"""
        if not self.cap:
            return None
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (width, height)
    
    def save_frame(self, filepath: str) -> bool:
        """Save current frame to file"""
        frame = self.get_frame()
        if frame is not None:
            cv2.imwrite(filepath, frame)
            logger.info(f"Saved frame to {filepath}")
            return True
        return False


# Example usage
if __name__ == "__main__":
    receiver = VideoReceiver("rtsp://192.168.1.100:8554/video")
    
    if receiver.connect(timeout=10):
        logger.info("Video connected!")
        
        # Display video
        cv2.namedWindow("GCS Video", cv2.WINDOW_NORMAL)
        
        try:
            while True:
                frame = receiver.get_frame()
                if frame is not None:
                    # Draw FPS
                    fps_text = f"FPS: {receiver.get_fps():.1f}"
                    cv2.putText(frame, fps_text, (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    cv2.imshow("GCS Video", frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            logger.info("Stopping...")
        finally:
            receiver.disconnect()
            cv2.destroyAllWindows()
    else:
        logger.error("Video connection failed")
