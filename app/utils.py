"""
Utility functions for image processing and EXIF data extraction.
"""

from typing import Optional, Tuple
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import io


def get_exif_data(image: Image.Image) -> dict:
    """
    Extract EXIF data from an image.
    
    Args:
        image: PIL Image object
        
    Returns:
        Dictionary of EXIF tags and values
    """
    exif_data = {}
    
    try:
        exif_info = image._getexif()
        if exif_info is None:
            return exif_data
            
        for tag_id, value in exif_info.items():
            tag_name = TAGS.get(tag_id, tag_id)
            exif_data[tag_name] = value
            
    except (AttributeError, KeyError, IndexError):
        pass
        
    return exif_data


def get_gps_info(exif_data: dict) -> dict:
    """
    Extract GPS information from EXIF data.
    
    Args:
        exif_data: Dictionary of EXIF data
        
    Returns:
        Dictionary of GPS tags and values
    """
    gps_info = {}
    
    if "GPSInfo" not in exif_data:
        return gps_info
        
    for tag_id, value in exif_data["GPSInfo"].items():
        tag_name = GPSTAGS.get(tag_id, tag_id)
        gps_info[tag_name] = value
        
    return gps_info


def convert_to_degrees(value) -> float:
    """
    Convert GPS coordinates from degrees/minutes/seconds to decimal degrees.
    
    Args:
        value: Tuple of (degrees, minutes, seconds)
        
    Returns:
        Decimal degrees as float
    """
    try:
        # Handle IFDRational or tuple format
        if hasattr(value[0], 'numerator'):
            d = float(value[0].numerator) / float(value[0].denominator)
            m = float(value[1].numerator) / float(value[1].denominator)
            s = float(value[2].numerator) / float(value[2].denominator)
        else:
            d, m, s = float(value[0]), float(value[1]), float(value[2])
            
        return d + (m / 60.0) + (s / 3600.0)
    except (TypeError, IndexError, ZeroDivisionError):
        return 0.0


def extract_gps_coordinates(image_bytes: bytes) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract GPS latitude and longitude from image EXIF data.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Tuple of (latitude, longitude) or (None, None) if not available
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        exif_data = get_exif_data(image)
        gps_info = get_gps_info(exif_data)
        
        if not gps_info:
            return None, None
            
        # Extract latitude
        lat = None
        if "GPSLatitude" in gps_info and "GPSLatitudeRef" in gps_info:
            lat = convert_to_degrees(gps_info["GPSLatitude"])
            if gps_info["GPSLatitudeRef"] == "S":
                lat = -lat
                
        # Extract longitude
        lon = None
        if "GPSLongitude" in gps_info and "GPSLongitudeRef" in gps_info:
            lon = convert_to_degrees(gps_info["GPSLongitude"])
            if gps_info["GPSLongitudeRef"] == "W":
                lon = -lon
                
        return lat, lon
        
    except Exception as e:
        print(f"Error extracting GPS data: {e}")
        return None, None


def get_image_dimensions(image_bytes: bytes) -> Tuple[int, int]:
    """
    Get image width and height.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Tuple of (width, height)
    """
    image = Image.open(io.BytesIO(image_bytes))
    return image.size

