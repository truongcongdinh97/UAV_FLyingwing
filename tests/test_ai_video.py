
import cv2
import time
import os
from loguru import logger
from companion_computer.src.ai.object_detector import ObjectDetector

def test_video_detection(video_path: str, output_path: str = None):
    """
    Test object detection on a video file
    """
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return

    # Initialize detector
    detector = ObjectDetector()
    if not detector.is_initialized:
        logger.error("Failed to initialize detector. Check model path.")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Could not open video file")
        return

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    # Setup writer if output path provided
    writer = None
    if output_path:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    logger.info(f"Processing video: {video_path} ({width}x{height} @ {fps}fps)")
    
    frame_count = 0
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Run detection
            detections = detector.detect(frame)
            
            # Draw results
            result_frame = detector.draw_detections(frame, detections)
            
            # Write to file or show
            if writer:
                writer.write(result_frame)
            else:
                # Resize for display if too large
                display_frame = cv2.resize(result_frame, (1280, 720))
                cv2.imshow('Detection Test', display_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            frame_count += 1
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps_current = frame_count / elapsed
                logger.info(f"Processed {frame_count} frames. FPS: {fps_current:.1f}")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        cap.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()
        logger.info("Done")

if __name__ == "__main__":
    # Example usage:
    # Create a 'test_videos' folder and put a video file there
    # python test_ai_video.py
    
    # For now, just print instructions
    print("To run this test:")
    print("1. Place a video file (e.g., 'test.mp4') in the project root")
    print("2. Edit this file to point to your video:")
    print("   test_video_detection('test.mp4', 'output.mp4')")
