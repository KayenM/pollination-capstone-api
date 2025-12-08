"""
Video processing worker for ProcessPoolExecutor.

This module contains functions that run in separate processes to handle
video classification without blocking the main API.
"""

import os
import sys
import logging
from typing import Dict, Any
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_video_sync(
    job_id: str,
    video_path: str,
    output_path: str,
    latitude: float,
    longitude: float,
    filename: str,
    mongodb_url: str,
    mongodb_database: str
) -> Dict[str, Any]:
    """
    Process video synchronously in a separate process.
    
    This function is designed to be run in a ProcessPoolExecutor.
    It must be at module level (not nested) for pickling.
    
    Args:
        job_id: Unique job identifier
        video_path: Path to input video file
        output_path: Path to save annotated video
        latitude: GPS latitude
        longitude: GPS longitude
        filename: Original filename
        mongodb_url: MongoDB connection string
        mongodb_database: Database name
        
    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Worker process started for job {job_id}")
        
        # Import here to avoid issues with multiprocessing
        from .ml_model import classify_video, generate_annotated_video
        
        # Update job status to processing
        asyncio.run(_update_job_status(
            job_id, mongodb_url, mongodb_database,
            status="processing", progress=10, message="Analyzing video frames..."
        ))
        
        # Step 1: Classify video (frame-by-frame analysis)
        logger.info(f"Job {job_id}: Starting video classification")
        classification_result = classify_video(
            video_path,
            confidence_threshold=0.25
        )
        
        asyncio.run(_update_job_status(
            job_id, mongodb_url, mongodb_database,
            status="processing", progress=50, message="Generating annotated video..."
        ))
        
        # Step 2: Generate annotated video with bounding boxes
        logger.info(f"Job {job_id}: Generating annotated video")
        generate_annotated_video(
            video_path,
            output_path,
            confidence_threshold=0.25
        )
        
        asyncio.run(_update_job_status(
            job_id, mongodb_url, mongodb_database,
            status="processing", progress=80, message="Saving to database..."
        ))
        
        # Step 3: Save to MongoDB
        logger.info(f"Job {job_id}: Saving to MongoDB")
        with open(output_path, 'rb') as f:
            annotated_video_bytes = f.read()
        
        # Save using async function
        asyncio.run(_save_video_to_mongodb(
            job_id=job_id,
            video_bytes=annotated_video_bytes,
            latitude=latitude,
            longitude=longitude,
            frame_results=classification_result['frame_results'],
            video_metadata={
                'total_frames': classification_result['total_frames'],
                'fps': classification_result['fps'],
                'duration': classification_result['duration']
            },
            filename=filename,
            mongodb_url=mongodb_url,
            mongodb_database=mongodb_database
        ))
        
        # Step 4: Cleanup temporary files
        logger.info(f"Job {job_id}: Cleaning up temporary files")
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        
        # Calculate statistics for response
        total_detections = sum(len(frame) for frame in classification_result['frame_results'])
        avg_per_frame = total_detections / classification_result['total_frames'] if classification_result['total_frames'] > 0 else 0
        
        # Calculate stage summary
        stage_summary = {"0": 0, "1": 0, "2": 0}
        for frame_detections in classification_result['frame_results']:
            for det in frame_detections:
                stage = str(det['stage'])
                stage_summary[stage] = stage_summary.get(stage, 0) + 1
        
        result = {
            "job_id": job_id,
            "video_path": f"/api/videos/{job_id}",
            "total_frames": classification_result['total_frames'],
            "fps": classification_result['fps'],
            "duration_seconds": classification_result['duration'],
            "total_detections": total_detections,
            "average_flowers_per_frame": avg_per_frame,
            "stage_summary": stage_summary
        }
        
        # Update job to completed
        asyncio.run(_update_job_status(
            job_id, mongodb_url, mongodb_database,
            status="completed", progress=100, message="Video processing completed",
            result=result
        ))
        
        logger.info(f"Job {job_id}: Processing completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Job {job_id}: Error during processing: {str(e)}", exc_info=True)
        
        # Update job to failed
        asyncio.run(_update_job_status(
            job_id, mongodb_url, mongodb_database,
            status="failed", progress=0, message=f"Error: {str(e)}",
            error=str(e)
        ))
        
        # Cleanup on error
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        
        raise


async def _update_job_status(
    job_id: str,
    mongodb_url: str,
    mongodb_database: str,
    status: str,
    progress: int,
    message: str,
    result: Dict[str, Any] = None,
    error: str = None
):
    """Update job status in MongoDB."""
    try:
        client = AsyncIOMotorClient(mongodb_url)
        db = client[mongodb_database]
        collection = db["jobs"]
        
        from datetime import datetime
        update_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "updated_at": datetime.utcnow(),
        }
        
        if result is not None:
            update_data["result"] = result
        if error is not None:
            update_data["error"] = error
        if status in ["completed", "failed"]:
            update_data["completed_at"] = datetime.utcnow()
        
        await collection.update_one(
            {"job_id": job_id},
            {"$set": update_data}
        )
        
        client.close()
    except Exception as e:
        logger.error(f"Error updating job status: {e}")


async def _save_video_to_mongodb(
    job_id: str,
    video_bytes: bytes,
    latitude: float,
    longitude: float,
    frame_results: list,
    video_metadata: dict,
    filename: str,
    mongodb_url: str,
    mongodb_database: str
):
    """Save video classification to MongoDB."""
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
    from datetime import datetime
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[mongodb_database]
    bucket = AsyncIOMotorGridFSBucket(db)
    collection = db["video_classifications"]
    
    # Store video in GridFS
    video_id = await bucket.upload_from_stream(
        filename,
        video_bytes,
        metadata={
            "record_id": job_id,
            "content_type": "video/mp4",
            "uploaded_at": datetime.utcnow()
        }
    )
    
    # Aggregate statistics
    stage_summary = {0: 0, 1: 0, 2: 0}
    total_detections = 0
    
    for frame_detections in frame_results:
        total_detections += len(frame_detections)
        for det in frame_detections:
            stage = det['stage']
            stage_summary[stage] = stage_summary.get(stage, 0) + 1
    
    # Convert integer keys to strings for MongoDB
    stage_summary = {str(k): v for k, v in stage_summary.items()}
    
    # Calculate average
    total_frames = video_metadata.get('total_frames', len(frame_results))
    avg_flowers = total_detections / total_frames if total_frames > 0 else 0
    
    # Store metadata
    document = {
        "id": job_id,
        "video_gridfs_id": video_id,
        "video_filename": filename,
        "video_content_type": "video/mp4",
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": datetime.utcnow(),
        "total_frames": total_frames,
        "fps": video_metadata.get('fps', 0),
        "duration_seconds": video_metadata.get('duration', 0),
        "frame_results": frame_results,
        "stage_summary": stage_summary,
        "total_detections": total_detections,
        "average_flowers_per_frame": avg_flowers,
    }
    
    await collection.insert_one(document)
    client.close()

