#!/usr/bin/env python3
# Configuration parameters
MIN_WIDTH = 1000  # Minimum image width in pixels
MIN_HEIGHT = 1000  # Minimum image height in pixels
MIN_DPI = 72  # Minimum dots per inch
BRISQUE_THRESHOLD = 50  # BRISQUE score threshold (0-100, lower is better)

"""
Image Quality Check Script

This script checks an image for various quality parameters:
- Validates that the file is actually an image
- Checks minimum dimensions
- Checks DPI
- Uses image-quality library to assess image quality

Usage:
    python image_quality_check.py <image_filename>

Output:
    FAIL/OK status and description if failed
"""

import sys
import os
from PIL import Image
import numpy as np
from imagequality.metrics import Metrics

def check_is_image(image_path):
    """Check if the file is a valid image."""
    try:
        with Image.open(image_path) as img:
            # Force load image data
            img.load()
        return True, ""
    except Exception as e:
        return False, f"Not a valid image file: {str(e)}"

def check_min_dimensions(image_path):
    """Check if the image meets minimum dimension requirements."""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            if width < MIN_WIDTH or height < MIN_HEIGHT:
                return False, f"Image dimensions too small: {width}x{height}, minimum required: {MIN_WIDTH}x{MIN_HEIGHT}"
            return True, ""
    except Exception as e:
        return False, f"Error checking dimensions: {str(e)}"

def check_dpi(image_path):
    """Check if the image has sufficient DPI."""
    try:
        with Image.open(image_path) as img:
            # Get DPI information if available
            if 'dpi' in img.info:
                dpi_x, dpi_y = img.info['dpi']
                if dpi_x < MIN_DPI or dpi_y < MIN_DPI:
                    return False, f"Image DPI too low: {dpi_x}x{dpi_y}, minimum required: {MIN_DPI}"
                return True, ""
            else:
                # Some images might not have DPI information
                return True, "DPI information not available in image"
    except Exception as e:
        return False, f"Error checking DPI: {str(e)}"

def check_image_quality(image_path):
    """Check image quality using image-quality library."""
    try:
        # Open image and convert to numpy array for image-quality library
        with Image.open(image_path) as img:
            # Convert to RGB if needed (some metrics require RGB)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Convert to numpy array
            img_array = np.array(img)
            
            # Initialize metrics
            metrics = Metrics()
            
            # Calculate quality metrics
            brisque_score = metrics.brisque(img_array)
            
            # BRISQUE score ranges from 0 (best) to 100 (worst)
            # Lower is better, so we'll use a threshold
            if brisque_score > BRISQUE_THRESHOLD:
                return False, f"Poor image quality (BRISQUE score: {brisque_score:.2f})"
            
            return True, ""
    except Exception as e:
        return False, f"Error checking image quality: {str(e)}"

def main():
    if len(sys.argv) != 2:
        print("FAIL")
        print("Usage: python image_quality_check.py <image_filename>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(image_path):
        print("FAIL")
        print(f"File not found: {image_path}")
        sys.exit(1)
    
    # Run all checks
    checks = [
        check_is_image(image_path),
        check_min_dimensions(image_path),
        check_dpi(image_path),
        check_image_quality(image_path)
    ]
    
    # Collect failed checks
    failures = [desc for success, desc in checks if not success]
    
    # Output result
    if failures:
        print("FAIL")
        for failure in failures:
            print(failure)
    else:
        print("OK")
        print("Image passed all quality checks")

if __name__ == "__main__":
    main()
