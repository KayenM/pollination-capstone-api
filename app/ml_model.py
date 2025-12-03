"""
ML Model interface for tomato plant flower detection and classification.

This module contains a dummy implementation that will be replaced with the
actual PyTorch model when ready.

Expected model interface:
- Input: Image tensor
- Output: List of detections with bounding boxes [x_min, y_min, x_max, y_max] 
          and stage classification (0=bud, 1=anthesis, 2=post-anthesis)
"""

import random
from typing import List, Dict, Any
from PIL import Image
import io


# Stage labels for reference
STAGE_LABELS = {
    0: "bud",
    1: "anthesis", 
    2: "post-anthesis"
}


def load_model(model_path: str = None):
    """
    Load the PyTorch model from disk.
    
    Args:
        model_path: Path to the .pt model file
        
    Returns:
        Loaded model ready for inference
        
    TODO: Replace with actual model loading:
        import torch
        model = torch.load(model_path)
        model.eval()
        return model
    """
    # Dummy implementation - returns None as placeholder
    print(f"[DUMMY] Would load model from: {model_path}")
    return None


def preprocess_image(image: Image.Image) -> Any:
    """
    Preprocess image for model inference.
    
    Args:
        image: PIL Image object
        
    Returns:
        Preprocessed tensor ready for model input
        
    TODO: Replace with actual preprocessing:
        from torchvision import transforms
        transform = transforms.Compose([
            transforms.Resize((640, 640)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        return transform(image).unsqueeze(0)
    """
    # Dummy implementation - just return image size for generating fake boxes
    return image.size


def run_inference(model: Any, preprocessed_input: Any) -> List[Dict[str, Any]]:
    """
    Run model inference on preprocessed input.
    
    Args:
        model: Loaded PyTorch model
        preprocessed_input: Preprocessed image tensor
        
    Returns:
        List of detections, each containing:
        - bounding_box: [x_min, y_min, x_max, y_max]
        - stage: 0, 1, or 2
        - confidence: float between 0 and 1
        
    TODO: Replace with actual inference:
        with torch.no_grad():
            outputs = model(preprocessed_input)
        return parse_model_outputs(outputs)
    """
    # Dummy implementation - generate random flower detections
    image_width, image_height = preprocessed_input
    
    # Generate 2-6 random flower detections
    num_flowers = random.randint(2, 6)
    detections = []
    
    for _ in range(num_flowers):
        # Generate random bounding box within image bounds
        box_width = random.randint(30, 100)
        box_height = random.randint(30, 100)
        
        x_min = random.randint(0, max(1, image_width - box_width))
        y_min = random.randint(0, max(1, image_height - box_height))
        x_max = x_min + box_width
        y_max = y_min + box_height
        
        detection = {
            "bounding_box": [x_min, y_min, x_max, y_max],
            "stage": random.randint(0, 2),
            "confidence": round(random.uniform(0.7, 0.99), 2)
        }
        detections.append(detection)
    
    return detections


def classify_image(image_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Main function to classify flowers in an image.
    
    This is the primary interface that will be called by the API.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        List of flower detections with bounding boxes and stage classifications
    """
    # Load image
    image = Image.open(io.BytesIO(image_bytes))
    
    # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    # Load model (in production, this should be cached/singleton)
    model = load_model()
    
    # Preprocess
    preprocessed = preprocess_image(image)
    
    # Run inference
    detections = run_inference(model, preprocessed)
    
    return detections


def get_stage_label(stage: int) -> str:
    """Get human-readable label for a stage number."""
    return STAGE_LABELS.get(stage, "unknown")

