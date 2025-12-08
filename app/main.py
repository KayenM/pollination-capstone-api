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
from concurrent.futures import ProcessPoolExecutor
import asyncio

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import Response, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from .database_mongodb import (
    connect_to_mongodb,
    close_mongodb_connection,
    create_indexes,
    ClassificationRecord,
    VideoClassificationRecord,
    JobRecord,
    get_database,
)
from .models import (
    ClassificationResponse,
    HeatmapResponse,
    HeatmapDataPoint,
    FlowerDetection,
    Location,
    HealthResponse,
    VideoClassificationResponse,
    FrameStatistics,
    JobStatusResponse,
)
from .ml_model import (
    classify_image,
    generate_annotated_image,
    classify_video,
    generate_annotated_video,
)
from .utils import extract_gps_coordinates
from .config import settings

# Ensure upload directory exists (for temporary processing only)
settings.ensure_upload_dir()

# Initialize ProcessPoolExecutor for async video processing
# Use max 4 workers to avoid overwhelming the system (suitable for HF Spaces)
executor = ProcessPoolExecutor(max_workers=int(os.getenv("MAX_WORKERS", "4")))

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
    """Close MongoDB connection and executor on shutdown."""
    await close_mongodb_connection()
    executor.shutdown(wait=True)

@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

@app.get("/health", response_model=HealthResponse)
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
    
    # Convert to string keys for consistency
    stage_summary = {str(k): v for k, v in stage_summary.items()}

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
        
        # Convert to string keys for consistency
        stage_counts = {str(k): v for k, v in stage_counts.items()}

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
    
    # Convert to string keys for consistency
    stage_summary = {str(k): v for k, v in stage_summary.items()}

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


# ============================================================================
# VIDEO CLASSIFICATION ENDPOINTS
# ============================================================================

@app.post("/api/classify-video", response_model=VideoClassificationResponse)
async def classify_flower_video(
    file: UploadFile = File(..., description="Video file of tomato plant"),
    latitude: Optional[float] = Form(None, description="Manual latitude override"),
    longitude: Optional[float] = Form(None, description="Manual longitude override"),
    include_frame_details: bool = Form(False, description="Include per-frame statistics in response"),
):
    """
    Upload a video of a tomato plant and get flower classifications across all frames.
    
    The endpoint will:
    1. Process each frame of the video with the ML model
    2. Generate an annotated video with bounding boxes and labels
    3. Store the annotated video in MongoDB (using GridFS for large files)
    4. Return aggregated statistics and optionally frame-by-frame details
    
    Note: Video processing can take several minutes depending on video length.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail="File must be a video (MP4, AVI, MOV, etc.)",
        )

    # Read video contents
    video_bytes = await file.read()
    
    # Generate unique ID
    record_id = str(uuid.uuid4())
    temp_dir = "/tmp"
    temp_video_path = os.path.join(temp_dir, f"{record_id}_input.mp4")
    temp_output_path = os.path.join(temp_dir, f"{record_id}_output.mp4")

    try:
        # Save uploaded video to temporary file
        with open(temp_video_path, 'wb') as f:
            f.write(video_bytes)

        # Run classification on video
        try:
            classification_result = classify_video(temp_video_path)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error running video classification: {str(e)}",
            )

        # Generate annotated video with bounding boxes
        try:
            generate_annotated_video(
                temp_video_path,
                temp_output_path,
                confidence_threshold=0.25
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating annotated video: {str(e)}",
            )

        # Read the annotated video
        if not os.path.exists(temp_output_path):
            raise HTTPException(
                status_code=500,
                detail="Annotated video was not generated successfully",
            )
        
        with open(temp_output_path, 'rb') as f:
            annotated_video_bytes = f.read()

        # Store in MongoDB (using GridFS for large files)
        try:
            await VideoClassificationRecord.create(
                record_id=record_id,
                video_bytes=annotated_video_bytes,
                latitude=latitude,
                longitude=longitude,
                frame_results=classification_result['frame_results'],
                video_metadata={
                    'total_frames': classification_result['total_frames'],
                    'fps': classification_result['fps'],
                    'duration': classification_result['duration']
                },
                filename=file.filename or "video.mp4"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error saving to database: {str(e)}",
            )

        # Get the saved record to build response
        record = await VideoClassificationRecord.get_by_id(record_id)

        # Build frame statistics if requested
        frame_statistics_list = None
        if include_frame_details:
            frame_statistics_list = []
            for frame_num, frame_detections in enumerate(classification_result['frame_results']):
                # Calculate stage counts for this frame
                stage_counts = {0: 0, 1: 0, 2: 0}
                for det in frame_detections:
                    stage = det['stage']
                    stage_counts[stage] = stage_counts.get(stage, 0) + 1
                
                # Build FlowerDetection objects
                flowers = [
                    FlowerDetection(
                        bounding_box=d["bounding_box"],
                        stage=d["stage"],
                        confidence=d["confidence"],
                    )
                    for d in frame_detections
                ]
                
                frame_statistics_list.append(
                    FrameStatistics(
                        frame_number=frame_num,
                        detections=flowers,
                        stage_counts=stage_counts,
                    )
                )

        return VideoClassificationResponse(
            id=record_id,
            video_path=f"/api/videos/{record_id}",
            location=Location(latitude=latitude, longitude=longitude),
            timestamp=record["timestamp"],
            total_frames=record["total_frames"],
            fps=record["fps"],
            duration_seconds=record["duration_seconds"],
            total_detections=record["total_detections"],
            average_flowers_per_frame=record["average_flowers_per_frame"],
            stage_summary=record["stage_summary"],
            frame_statistics=frame_statistics_list,
        )

    finally:
        # Cleanup temporary files
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)


@app.get("/api/videos/{record_id}")
async def get_video(record_id: str):
    """
    Retrieve the annotated video (with bounding boxes and labels) for a video classification.
    
    Note: Only annotated videos are stored. The video includes bounding boxes,
    stage labels, and confidence scores drawn on each frame.
    """
    try:
        video_bytes = await VideoClassificationRecord.get_video_bytes(record_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving video: {str(e)}",
        )

    if not video_bytes:
        raise HTTPException(status_code=404, detail="Video not found")

    # Get record for filename
    record = await VideoClassificationRecord.get_by_id(record_id)
    filename = record.get("video_filename", "video.mp4") if record else "video.mp4"

    return Response(
        content=video_bytes,
        media_type="video/mp4",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Accept-Ranges": "bytes",  # Enable video seeking
        }
    )


@app.get("/api/video-classifications/{record_id}", response_model=VideoClassificationResponse)
async def get_video_classification(
    record_id: str,
    include_frame_details: bool = False
):
    """
    Get a specific video classification result by ID.
    
    Args:
        record_id: The video classification ID
        include_frame_details: Include detailed per-frame statistics (may be large)
    """
    try:
        record = await VideoClassificationRecord.get_by_id(record_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving video classification: {str(e)}",
        )

    if not record:
        raise HTTPException(status_code=404, detail="Video classification not found")

    # Build frame statistics if requested
    frame_statistics_list = None
    if include_frame_details:
        frame_results = record.get("frame_results", [])
        frame_statistics_list = []
        
        for frame_num, frame_detections in enumerate(frame_results):
            # Calculate stage counts for this frame
            stage_counts = {0: 0, 1: 0, 2: 0}
            for det in frame_detections:
                stage = det['stage']
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
            
            # Build FlowerDetection objects
            flowers = [
                FlowerDetection(
                    bounding_box=d["bounding_box"],
                    stage=d["stage"],
                    confidence=d["confidence"],
                )
                for d in frame_detections
            ]
            
            frame_statistics_list.append(
                FrameStatistics(
                    frame_number=frame_num,
                    detections=flowers,
                    stage_counts=stage_counts,
                )
            )

    return VideoClassificationResponse(
        id=record["id"],
        video_path=f"/api/videos/{record_id}",
        location=Location(
            latitude=record.get("latitude"),
            longitude=record.get("longitude")
        ),
        timestamp=record["timestamp"],
        total_frames=record["total_frames"],
        fps=record["fps"],
        duration_seconds=record["duration_seconds"],
        total_detections=record["total_detections"],
        average_flowers_per_frame=record["average_flowers_per_frame"],
        stage_summary=record["stage_summary"],
        frame_statistics=frame_statistics_list,
    )


@app.get("/api/video-classifications", response_model=list)
async def list_video_classifications():
    """
    Get a list of all video classification records (metadata only, no frame details).
    """
    try:
        records = await VideoClassificationRecord.get_all()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving video classifications: {str(e)}",
        )

    results = []
    for record in records:
        results.append({
            "id": record["id"],
            "video_path": f"/api/videos/{record['id']}",
            "location": {
                "latitude": record.get("latitude"),
                "longitude": record.get("longitude")
            },
            "timestamp": record["timestamp"],
            "total_frames": record["total_frames"],
            "fps": record["fps"],
            "duration_seconds": record["duration_seconds"],
            "total_detections": record["total_detections"],
            "average_flowers_per_frame": record["average_flowers_per_frame"],
            "stage_summary": record["stage_summary"],
        })

    return results


@app.delete("/api/video-classifications/{record_id}")
async def delete_video_classification(record_id: str):
    """
    Delete a video classification and its associated video from MongoDB.
    """
    try:
        deleted = await VideoClassificationRecord.delete_by_id(record_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting video classification: {str(e)}",
        )

    if not deleted:
        raise HTTPException(status_code=404, detail="Video classification not found")

    return {"message": "Video classification deleted successfully", "id": record_id}


# ============================================================================
# SHORT VIDEO DEMO ENDPOINT
# ============================================================================

@app.post("/api/classify/short-video")
async def classify_short_video_demo(
    file: UploadFile = File(..., description="Short video file for demo"),
):
    """
    Demo endpoint that simulates processing by sleeping and then returns
    the first annotated video currently stored.
    """
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail="File must be a video (MP4, AVI, MOV, etc.)",
        )

    # Read and discard the uploaded video to fully receive the payload
    await file.read()

    # Simulate processing delay for demo purposes
    await asyncio.sleep(12)

    try:
        records = await VideoClassificationRecord.get_all()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving stored videos: {str(e)}",
        )

    if not records:
        raise HTTPException(
            status_code=404,
            detail="No annotated videos are available yet.",
        )

    # get_all is sorted by timestamp desc; return the first (most recent) video
    first_record = records[0]
    record_id = first_record["id"]

    video_bytes = await VideoClassificationRecord.get_video_bytes(record_id)
    if not video_bytes:
        raise HTTPException(status_code=404, detail="Annotated video not found")

    filename = first_record.get("video_filename", "video.mp4")
    media_type = first_record.get("video_content_type", "video/mp4")

    return Response(
        content=video_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Accept-Ranges": "bytes",
        },
    )


# ============================================================================
# ASYNC VIDEO CLASSIFICATION ENDPOINTS (ProcessPoolExecutor)
# ============================================================================

@app.post("/api/classify-video-async", response_model=JobStatusResponse)
async def classify_video_async(
    file: UploadFile = File(..., description="Video file of tomato plant"),
    latitude: Optional[float] = Form(None, description="Manual latitude override"),
    longitude: Optional[float] = Form(None, description="Manual longitude override"),
):
    """
    Upload a video for ASYNC processing (non-blocking).
    
    This endpoint returns immediately with a job_id. The video is processed
    in the background using ProcessPoolExecutor. Use the job_id to check
    processing status via GET /api/jobs/{job_id}.
    
    Benefits over synchronous endpoint:
    - API remains responsive during processing
    - Multiple videos can be processed concurrently (up to 4 workers)
    - Suitable for long videos or high traffic
    - Progress tracking available
    
    Returns:
        JobStatusResponse with job_id and status endpoint
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail="File must be a video (MP4, AVI, MOV, etc.)",
        )

    # Read video contents
    video_bytes = await file.read()
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    temp_dir = "/tmp"
    temp_video_path = os.path.join(temp_dir, f"{job_id}_input.mp4")
    temp_output_path = os.path.join(temp_dir, f"{job_id}_output.mp4")

    # Save uploaded video to temporary file
    with open(temp_video_path, 'wb') as f:
        f.write(video_bytes)

    # Create job record in database
    try:
        await JobRecord.create(
            job_id=job_id,
            job_type="video_classification",
            status="queued",
            metadata={
                "filename": file.filename,
                "latitude": latitude,
                "longitude": longitude,
                "file_size": len(video_bytes),
            }
        )
    except Exception as e:
        # Clean up temp file if job creation fails
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        raise HTTPException(
            status_code=500,
            detail=f"Error creating job record: {str(e)}",
        )

    # Submit job to ProcessPoolExecutor
    try:
        from .video_worker import process_video_sync
        
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            executor,
            process_video_sync,
            job_id,
            temp_video_path,
            temp_output_path,
            latitude,
            longitude,
            file.filename or "video.mp4",
            settings.MONGODB_URL,
            settings.MONGODB_DATABASE,
        )
    except Exception as e:
        # Clean up on error
        await JobRecord.update_status(
            job_id,
            status="failed",
            message=f"Error submitting job: {str(e)}"
        )
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        raise HTTPException(
            status_code=500,
            detail=f"Error submitting processing job: {str(e)}",
        )

    # Return job status immediately
    job = await JobRecord.get_by_id(job_id)
    
    return JobStatusResponse(
        job_id=job_id,
        status="queued",
        progress=0,
        message="Video queued for processing. Check status endpoint for progress.",
        created_at=job["created_at"],
        estimated_time_remaining=60,  # Rough estimate: 30-60 seconds
    )


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of an async video processing job.
    
    Poll this endpoint to check if your video has been processed.
    Once status is 'completed', use the result.video_path to access
    the annotated video.
    
    Status values:
    - queued: Job is waiting to be processed
    - processing: Video is being analyzed (check progress field)
    - completed: Processing finished (result field contains data)
    - failed: Processing failed (message field contains error)
    
    Returns:
        JobStatusResponse with current status and results if completed
    """
    try:
        job = await JobRecord.get_by_id(job_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving job status: {str(e)}",
        )

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Calculate estimated time remaining
    estimated_time = None
    if job["status"] == "processing":
        # Rough estimate based on progress
        progress = job.get("progress", 0)
        if progress > 0:
            elapsed = (datetime.utcnow() - job["created_at"]).total_seconds()
            estimated_total = elapsed / (progress / 100)
            estimated_time = int(estimated_total - elapsed)

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job.get("progress", 0),
        message=job.get("message"),
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        result=job.get("result"),
        estimated_time_remaining=estimated_time,
    )


@app.get("/api/jobs", response_model=list)
async def list_active_jobs():
    """
    List all active (queued or processing) jobs.
    
    Useful for monitoring the processing queue.
    """
    try:
        jobs = await JobRecord.get_active_jobs()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving jobs: {str(e)}",
        )

    return [
        {
            "job_id": job["job_id"],
            "status": job["status"],
            "progress": job.get("progress", 0),
            "created_at": job["created_at"],
            "message": job.get("message"),
        }
        for job in jobs
    ]


@app.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel/delete a job record.
    
    Note: This only removes the job record from the database.
    If the job is already processing in a worker, it will continue
    until completion (the result just won't be saved).
    """
    try:
        deleted = await JobRecord.delete_by_id(job_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting job: {str(e)}",
        )

    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"message": "Job deleted successfully", "job_id": job_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
