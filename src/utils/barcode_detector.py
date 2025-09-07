import cv2
import logging
import numpy as np
from PIL import Image
import io
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to set the library path for pyzbar if it's installed with Homebrew
if 'DYLD_LIBRARY_PATH' not in os.environ and os.path.exists('/opt/homebrew/lib'):
    os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'
    logger.info("Added Homebrew lib path to DYLD_LIBRARY_PATH")

# Try to import pyzbar, but provide a fallback if it doesn't work
try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    PYZBAR_AVAILABLE = True
    logger.info("Successfully imported pyzbar")
except ImportError as e:
    PYZBAR_AVAILABLE = False
    logger.warning(f"pyzbar import failed ({str(e)}); falling back to OpenCV QR code detection")

def decode_with_opencv(image_np):
    """Fallback barcode detection using OpenCV's QR code detector"""
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(image_np)
    if data:
        return [{'type': 'QR_CODE', 'data': data}]
    return []

def detect_barcode_from_image(image_data):
    """
    Detect a barcode from an image and extract its code.
    
    Args:
        image_data: Image data, can be PIL Image, numpy array, or bytes
        
    Returns:
        dict: Dictionary with barcode data or None if no barcode is detected
    """
    try:
        # Convert to a format we can use
        if isinstance(image_data, bytes):
            image = Image.open(io.BytesIO(image_data))
            image_np = np.array(image)
        elif isinstance(image_data, Image.Image):
            image_np = np.array(image_data)
        elif isinstance(image_data, np.ndarray):
            image_np = image_data
        else:
            logger.error(f"Unsupported image data type: {type(image_data)}")
            return None
        
        # Convert to grayscale if needed
        if len(image_np.shape) == 3 and image_np.shape[2] == 3:
            gray_image = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            gray_image = image_np
            
        # Detect and decode barcodes
        barcode_data = []
        if PYZBAR_AVAILABLE:
            barcodes = pyzbar_decode(gray_image)
            for barcode in barcodes:
                data = barcode.data.decode('utf-8')
                barcode_type = barcode.type
                logger.info(f"Detected {barcode_type} barcode: {data}")
                barcode_data.append({"type": barcode_type, "data": data})
        else:
            # Fallback to OpenCV QR code detection
            barcode_data = decode_with_opencv(gray_image)
        
        if not barcode_data:
            logger.info("No barcode detected in the image")
            return None
            
        # Always return a dictionary with a consistent structure
        if barcode_data and len(barcode_data) > 0:
            return barcode_data[0]
        return None
        
    except Exception as e:
        logger.error(f"Error detecting barcode: {str(e)}")
        return None

def has_barcode(image_data):
    """
    Check if an image contains a barcode.
    
    Args:
        image_data: Image data in various formats
        
    Returns:
        bool: True if barcode is detected, False otherwise
    """
    result = detect_barcode_from_image(image_data)
    return result is not None
