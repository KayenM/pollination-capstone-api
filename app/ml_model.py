"""
ML Model interface for tomato plant flower detection and classification.

Uses YOLOv8 from ultralytics for flower detection and stage classification.

Expected model output:
- Input: Image (PIL Image or bytes)
- Output: List of detections with bounding boxes [x_min, y_min, x_max, y_max] 
          and stage classification (0=bud, 1=anthesis, 2=post-anthesis)
"""

import os
from typing import List, Dict, Any, Optional
from PIL import Image
import io
import logging
import cv2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Stage labels for reference
STAGE_LABELS = {
    0: "bud",
    1: "anthesis", 
    2: "post-anthesis"
}

# Global model cache (load once, reuse for all requests)
_model_cache: Optional[Any] = None

# Hugging Face model configuration
HF_REPO_ID = "deenp03/tomato_pollination_stage_classifier"
HF_MODEL_FILENAME = "best.pt"


def load_model(model_path: Optional[str] = None, force_reload: bool = False):
    """
    Load the YOLO model from Hugging Face Hub.
    
    Always fetches the latest model from Hugging Face to ensure up-to-date predictions.
    
    Args:
        model_path: Optional local path to model file (if None, downloads from HF)
        force_reload: Force reload even if model is cached
        
    Returns:
        Loaded YOLO model ready for inference
    """
    global _model_cache
    
    # Return cached model if available
    if _model_cache is not None and not force_reload:
        logger.info("Using cached YOLO model")
        return _model_cache
    
    try:
        from ultralytics import YOLO
        from huggingface_hub import hf_hub_download
    except ImportError as e:
        raise ImportError(
            "Required packages not installed. Install with: pip install ultralytics huggingface_hub"
        ) from e
    
    # Download model from Hugging Face if no local path provided
    if model_path is None:
        logger.info(f"Downloading latest model from Hugging Face: {HF_REPO_ID}/{HF_MODEL_FILENAME}")
        try:
            model_path = hf_hub_download(
                repo_id=HF_REPO_ID,
                filename=HF_MODEL_FILENAME
            )
            logger.info(f"Model downloaded to: {model_path}")
        except Exception as e:
            logger.error(f"Failed to download model from Hugging Face: {e}")
            # Fallback to local model if available
            local_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml_model.pt")
            if os.path.exists(local_path):
                logger.warning(f"Falling back to local model: {local_path}")
                model_path = local_path
            else:
                raise RuntimeError(
                    f"Failed to download model from Hugging Face and no local fallback found"
                ) from e
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at: {model_path}")
    
    logger.info(f"Loading YOLO model from: {model_path}")
    
    # Load the YOLO model
    model = YOLO(model_path)
    
    # Cache the model
    _model_cache = model
    
    logger.info("YOLO model loaded successfully")
    return model


def parse_yolo_results(results, confidence_threshold: float = 0.25) -> List[Dict[str, Any]]:
    """
    Parse YOLO results into our API format.
    
    Args:
        results: YOLO prediction results
        confidence_threshold: Minimum confidence to include detection
        
    Returns:
        List of detections in API format:
        [
            {
                "bounding_box": [x_min, y_min, x_max, y_max],
                "stage": 0|1|2,
                "confidence": 0.0-1.0
            }
        ]
    """
    detections = []
    
    # YOLO returns a list of Results objects (one per image)
    # Since we process one image at a time, we get the first result
    if not results or len(results) == 0:
        logger.warning("No results from YOLO model")
        return detections
    
    result = results[0]  # Get first result
    
    # Check if any boxes were detected
    if result.boxes is None or len(result.boxes) == 0:
        logger.info("No flowers detected in image")
        return detections
    
    # Extract boxes, confidences, and classes
    boxes = result.boxes.xyxy.cpu().numpy()  # [N, 4] - x_min, y_min, x_max, y_max
    confidences = result.boxes.conf.cpu().numpy()  # [N] - confidence scores
    classes = result.boxes.cls.cpu().numpy()  # [N] - class indices
    
    # Convert to our format
    for box, conf, cls in zip(boxes, confidences, classes):
        # Filter by confidence threshold
        if conf < confidence_threshold:
            continue
        
        # Convert class index to stage (0, 1, 2)
        # Assuming the model outputs class indices 0, 1, 2 for the three stages
        stage = int(cls)
        
        # Validate stage is in expected range
        if stage not in [0, 1, 2]:
            logger.warning(f"Unexpected class index {stage}, mapping to stage 0")
            stage = 0
        
        detection = {
            "bounding_box": [
                float(box[0]),  # x_min
                float(box[1]),  # y_min
                float(box[2]),  # x_max
                float(box[3])   # y_max
            ],
            "stage": stage,
            "confidence": float(conf)
        }
        
        detections.append(detection)
    
    logger.info(f"Detected {len(detections)} flowers (filtered by conf >= {confidence_threshold})")
    
    return detections


def classify_image(
    image_bytes: bytes,
    confidence_threshold: float = 0.25,
    model_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Main function to classify flowers in an image using YOLO.
    
    This is the primary interface that will be called by the API.
    
    Args:
        image_bytes: Raw image bytes
        confidence_threshold: Minimum confidence for detections (default: 0.25)
        model_path: Optional path to model file
        
    Returns:
        List of flower detections with bounding boxes and stage classifications
        
    Raises:
        Exception: If model loading or inference fails
    """
    try:
        # Load image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
        if image.mode != "RGB":
            logger.info(f"Converting image from {image.mode} to RGB")
            image = image.convert("RGB")
        
        # Load model (uses cached model if available)
        model = load_model(model_path)
        
        # Run inference
        # Note: YOLO's predict() can handle PIL Images directly
        logger.info(f"Running inference on image of size {image.size}")
        results = model.predict(
            source=image,
            conf=confidence_threshold,
            verbose=False  # Suppress YOLO's verbose output
        )
        
        # Parse results to our format
        detections = parse_yolo_results(results, confidence_threshold)
        
        return detections
        
    except Exception as e:
        logger.error(f"Error in classify_image: {str(e)}")
        raise


def generate_annotated_image(
    image_bytes: bytes,
    confidence_threshold: float = 0.25,
    model_path: Optional[str] = None
) -> bytes:
    """
    Generate an annotated image with bounding boxes and labels.
    
    Uses YOLO's built-in plotting functionality to draw boxes and labels.
    
    Args:
        image_bytes: Raw image bytes
        confidence_threshold: Minimum confidence for detections
        model_path: Optional path to model file
        
    Returns:
        Annotated image as bytes (JPEG format)
        
    Raises:
        Exception: If model loading or inference fails
    """
    try:
        # Load image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if image.mode != "RGB":
            logger.info(f"Converting image from {image.mode} to RGB")
            image = image.convert("RGB")
        
        # Load model (uses cached model if available)
        model = load_model(model_path)
        
        # Run inference
        logger.info(f"Running inference for annotated image, size {image.size}")
        results = model.predict(
            source=image,
            conf=confidence_threshold,
            verbose=False
        )
        
        # Use YOLO's built-in plot() method to generate annotated image
        # This draws bounding boxes, labels, and confidence scores
        if results and len(results) > 0:
            result = results[0]
            
            # Plot the results on the image
            # The plot() method returns a numpy array in BGR format (OpenCV style)
            annotated_array_bgr = result.plot(
                conf=True,  # Show confidence scores
                labels=True,  # Show class labels
                boxes=True,  # Show bounding boxes
                line_width=2,  # Box line width
            )
            
            # Convert BGR to RGB (YOLO's plot() returns BGR, PIL expects RGB)
            annotated_array_rgb = cv2.cvtColor(annotated_array_bgr, cv2.COLOR_BGR2RGB)
            
            # Convert numpy array back to PIL Image
            annotated_image = Image.fromarray(annotated_array_rgb)
            
            # Convert to bytes
            output_buffer = io.BytesIO()
            annotated_image.save(output_buffer, format='JPEG', quality=95)
            annotated_bytes = output_buffer.getvalue()
            
            logger.info(f"Generated annotated image with {len(result.boxes) if result.boxes else 0} detections")
            return annotated_bytes
        else:
            # No detections, return original image
            logger.info("No detections found, returning original image")
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', quality=95)
            return output_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error in generate_annotated_image: {str(e)}")
        raise


def get_stage_label(stage: int) -> str:
    """Get human-readable label for a stage number."""
    return STAGE_LABELS.get(stage, "unknown")


def get_model_info() -> Dict[str, Any]:
    """
    Get information about the loaded model.
    
    Returns:
        Dictionary with model information
    """
    try:
        model = load_model()
        
        info = {
            "model_type": "YOLOv8",
            "library": "ultralytics",
            "source": "Hugging Face Hub",
            "repo_id": HF_REPO_ID,
            "loaded": _model_cache is not None,
            "stages": STAGE_LABELS,
        }
        
        # Try to get model names if available
        if hasattr(model, 'names'):
            info["class_names"] = model.names
        
        return info
        
    except Exception as e:
        return {
            "error": str(e),
            "loaded": False
        }
