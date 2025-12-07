"""
Tomato Plant Flower Classification API

This API provides endpoints for:
1. Uploading images and getting flower classifications
2. Retrieving heatmap data for visualization
3. Accessing stored classification results

Uses MongoDB for persistent storage.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

from .database_mongodb import (
    connect_to_mongodb,
    close_mongodb_connection,
    create_indexes,
    ClassificationRecord,
    get_database,
)
from .models import (
    ClassificationResponse,
    HeatmapResponse,
    HeatmapDataPoint,
    FlowerDetection,
    Location,
    HealthResponse,
)
from .ml_model import classify_image, generate_annotated_image
from .utils import extract_gps_coordinates
from .config import settings

# Ensure upload directory exists (for temporary processing only)
settings.ensure_upload_dir()

# Initialize FastAPI app
app = FastAPI(
    title="Tomato Plant Flower Classification API",
    description="API for detecting and classifying tomato plant flowers by growth stage",
    version="1.0.0",
)

# Add CORS middleware for frontend integration
cors_origins = ["*"] if "*" in settings.CORS_ORIGINS else settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize MongoDB connection on startup."""
    try:
        await connect_to_mongodb()
        await create_indexes()
        print("MongoDB connected and indexes created successfully")
    except Exception as e:
        print(f"Warning: Failed to connect to MongoDB: {e}")
        print("API will still start, but database operations will fail until MongoDB is configured.")


@app.on_event("shutdown")
async def shutdown_event():
    """Close MongoDB connection on shutdown."""
    await close_mongodb_connection()


@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        db = get_database()
        # Test MongoDB connection by running a simple command
        await db.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy",
        database=db_status,
        timestamp=datetime.utcnow(),
    )


@app.post("/api/classify", response_model=ClassificationResponse)
async def classify_flower_image(
    file: UploadFile = File(..., description="Image file of tomato plant"),
    latitude: Optional[float] = Form(None, description="Manual latitude override"),
    longitude: Optional[float] = Form(None, description="Manual longitude override"),
):
    """
    Upload an image of a tomato plant and get flower classifications.
    
    The endpoint will:
    1. Extract GPS coordinates from image EXIF data (or use provided coordinates)
    2. Run the ML model to detect flowers and classify their stages
    3. Store the results in MongoDB (including the image)
    4. Return the classification results
    
    Flower stages:
    - 0: Bud
    - 1: Anthesis (flowering)
    - 2: Post-Anthesis
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File must be an image (JPEG, PNG, etc.)",
        )

    # Read file contents
    image_bytes = await file.read()

    # Extract GPS coordinates from EXIF if not provided manually
    if latitude is None or longitude is None:
        exif_lat, exif_lon = extract_gps_coordinates(image_bytes)
        latitude = latitude if latitude is not None else exif_lat
        longitude = longitude if longitude is not None else exif_lon

    # Generate unique ID
    record_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename or "image.jpg")[1] or ".jpg"
    image_filename = f"{record_id}{file_extension}"

    # Run ML model classification
    try:
        detections = classify_image(image_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running classification model: {str(e)}",
        )

    # Generate annotated image with bounding boxes
    # This is what we'll store (not the original image)
    try:
        annotated_image_bytes = generate_annotated_image(image_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating annotated image: {str(e)}",
        )

    # Calculate stage summary
    stage_summary = {0: 0, 1: 0, 2: 0}
    for detection in detections:
        stage = detection["stage"]
        stage_summary[stage] = stage_summary.get(stage, 0) + 1

    # Save to MongoDB (only annotated image is stored)
    try:
        await ClassificationRecord.create(
            record_id=record_id,
            image_bytes=annotated_image_bytes,  # Store annotated image only
            latitude=latitude,
            longitude=longitude,
            flowers=detections,
            filename=image_filename,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving to database: {str(e)}",
        )

    # Build response
    flower_detections = [
        FlowerDetection(
            bounding_box=d["bounding_box"],
            stage=d["stage"],
            confidence=d["confidence"],
        )
        for d in detections
    ]

    # Get the saved record to get timestamp
    record = await ClassificationRecord.get_by_id(record_id)

    return ClassificationResponse(
        id=record_id,
        image_path=f"/api/images/{record_id}",  # API endpoint for image
        location=Location(latitude=latitude, longitude=longitude),
        timestamp=record["timestamp"],
        flowers=flower_detections,
        flower_count=len(detections),
        stage_summary=stage_summary,
    )


@app.get("/api/heatmap-data", response_model=HeatmapResponse)
async def get_heatmap_data():
    """
    Get all classification data for heatmap visualization.
    
    Returns raw data with:
    - Location coordinates
    - Timestamp
    - All flower detections with stages
    - Stage counts per location
    """
    try:
        records = await ClassificationRecord.get_all()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving data: {str(e)}",
        )

    data_points = []
    for record in records:
        flowers_data = record.get("flowers", [])
        
        # Calculate stage counts
        stage_counts = {0: 0, 1: 0, 2: 0}
        for flower in flowers_data:
            stage = flower.get("stage", 0)
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

        flowers = [
            FlowerDetection(
                bounding_box=f.get("bounding_box", []),
                stage=f.get("stage", 0),
                confidence=f.get("confidence", 0.0),
            )
            for f in flowers_data
        ]

        data_points.append(
            HeatmapDataPoint(
                id=record["id"],
                latitude=record.get("latitude"),
                longitude=record.get("longitude"),
                timestamp=record["timestamp"],
                flowers=flowers,
                total_flowers=len(flowers),
                stage_counts=stage_counts,
            )
        )

    return HeatmapResponse(
        total_records=len(data_points),
        data_points=data_points,
    )


@app.get("/api/classifications/{record_id}", response_model=ClassificationResponse)
async def get_classification(record_id: str):
    """
    Get a specific classification result by ID.
    """
    try:
        record = await ClassificationRecord.get_by_id(record_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving classification: {str(e)}",
        )

    if not record:
        raise HTTPException(status_code=404, detail="Classification not found")

    flowers_data = record.get("flowers", [])
    
    # Calculate stage summary
    stage_summary = {0: 0, 1: 0, 2: 0}
    for flower in flowers_data:
        stage = flower.get("stage", 0)
        stage_summary[stage] = stage_summary.get(stage, 0) + 1

    flowers = [
        FlowerDetection(
            bounding_box=f.get("bounding_box", []),
            stage=f.get("stage", 0),
            confidence=f.get("confidence", 0.0),
        )
        for f in flowers_data
    ]

    return ClassificationResponse(
        id=record["id"],
        image_path=f"/api/images/{record_id}",
        location=Location(
            latitude=record.get("latitude"),
            longitude=record.get("longitude")
        ),
        timestamp=record["timestamp"],
        flowers=flowers,
        flower_count=len(flowers),
        stage_summary=stage_summary,
    )


@app.get("/api/images/{record_id}")
async def get_image(record_id: str):
    """
    Get the annotated image (with bounding boxes and labels) for a classification.
    
    Note: Only annotated images are stored. The image includes bounding boxes,
    stage labels, and confidence scores drawn on it.
    """
    try:
        record = await ClassificationRecord.get_by_id(record_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving image: {str(e)}",
        )

    if not record:
        raise HTTPException(status_code=404, detail="Classification not found")

    # Decode image from base64
    try:
        image_bytes = ClassificationRecord.decode_image(record["image_base64"])
        content_type = record.get("image_content_type", "image/jpeg")
        
        return Response(
            content=image_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{record.get("image_filename", "image.jpg")}"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error decoding image: {str(e)}",
        )


@app.delete("/api/classifications/{record_id}")
async def delete_classification(record_id: str):
    """
    Delete a classification and its associated image from MongoDB.
    """
    try:
        deleted = await ClassificationRecord.delete_by_id(record_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting classification: {str(e)}",
        )

    if not deleted:
        raise HTTPException(status_code=404, detail="Classification not found")

    return {"message": "Classification deleted successfully", "id": record_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
