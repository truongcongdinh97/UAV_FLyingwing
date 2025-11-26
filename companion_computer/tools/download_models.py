import os
import urllib.request
import zipfile
import shutil
from loguru import logger

def download_file(url, dest_path):
    logger.info(f"Downloading {url} to {dest_path}...")
    try:
        urllib.request.urlretrieve(url, dest_path)
        logger.info("Download complete.")
        return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False

def main():
    # Base paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(base_dir, "models")
    
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)
        
    # Model URL (MobileNet SSD v2 COCO)
    # Using a reliable source for the TFLite model
    # This is the quantized version which is faster on Pi
    model_url = "https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip"
    zip_path = os.path.join(models_dir, "model.zip")
    
    # Download
    if download_file(model_url, zip_path):
        # Extract
        logger.info("Extracting model...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(models_dir)
            
        # Rename/Cleanup
        extracted_model = os.path.join(models_dir, "detect.tflite")
        target_model = os.path.join(models_dir, "mobilenet_ssd_v2.tflite")
        
        if os.path.exists(extracted_model):
            if os.path.exists(target_model):
                os.remove(target_model)
            os.rename(extracted_model, target_model)
            logger.info(f"Model setup complete: {target_model}")
        else:
            logger.error(f"Could not find expected model file in zip: {extracted_model}")
            
        # Cleanup zip
        os.remove(zip_path)
        
        # Check labels
        label_file = os.path.join(models_dir, "labelmap.txt")
        target_labels = os.path.join(models_dir, "coco_labels.txt")
        if os.path.exists(label_file):
            if os.path.exists(target_labels):
                os.remove(target_labels)
            os.rename(label_file, target_labels)
            logger.info(f"Labels setup complete: {target_labels}")

if __name__ == "__main__":
    main()
