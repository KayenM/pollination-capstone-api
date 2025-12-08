"""
MongoDB database setup and models for storing classification results.
Uses Motor (async MongoDB driver) for FastAPI integration.
"""

import os
import base64
from datetime import datetime
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import logging

from .config import settings

logger = logging.getLogger(__name__)

# MongoDB connection settings
MONGODB_URL = settings.MONGODB_URL
DATABASE_NAME = settings.MONGODB_DATABASE

# Global MongoDB client
mongodb_client: Optional[AsyncIOMotorClient] = None
mongodb_db = None
gridfs_bucket = None


async def connect_to_mongodb():
    """Connect to MongoDB database."""
    global mongodb_client, mongodb_db, gridfs_bucket
    
    if not MONGODB_URL:
        raise ValueError(
            "MONGODB_URL environment variable is not set. "
            "Please set it to your MongoDB connection string."
        )
    
    try:
        from motor.motor_asyncio import AsyncIOMotorGridFSBucket
        
        mongodb_client = AsyncIOMotorClient(MONGODB_URL)
        # Test connection
        await mongodb_client.admin.command('ping')
        mongodb_db = mongodb_client[DATABASE_NAME]
        
        # Initialize GridFS bucket for large file storage (videos)
        gridfs_bucket = AsyncIOMotorGridFSBucket(mongodb_db)
        
        logger.info(f"Connected to MongoDB database: {DATABASE_NAME}")
        return mongodb_db
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongodb_connection():
    """Close MongoDB connection."""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        logger.info("MongoDB connection closed")


def get_database():
    """Get MongoDB database instance."""
    if mongodb_db is None:
        raise RuntimeError("MongoDB database not initialized. Call connect_to_mongodb() first.")
    return mongodb_db


def get_gridfs_bucket():
    """Get GridFS bucket for large file storage."""
    if gridfs_bucket is None:
        raise RuntimeError("GridFS bucket not initialized. Call connect_to_mongodb() first.")
    return gridfs_bucket


async def create_indexes():
    """Create database indexes for better query performance."""
    db = get_database()
    
    # Image classifications collection
    collection = db["classifications"]
    await collection.create_index("id", unique=True)
    await collection.create_index("timestamp")
    await collection.create_index([("latitude", 1), ("longitude", 1)])
    
    # Video classifications collection
    video_collection = db["video_classifications"]
    await video_collection.create_index("id", unique=True)
    await video_collection.create_index("timestamp")
    await video_collection.create_index([("latitude", 1), ("longitude", 1)])
    
    logger.info("MongoDB indexes created successfully")


class ClassificationRecord:
    """
    MongoDB document model for classification results.
    """
    
    @staticmethod
    def encode_image(image_bytes: bytes) -> str:
        """Encode image bytes to base64 string for MongoDB storage."""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    @staticmethod
    def decode_image(image_base64: str) -> bytes:
        """Decode base64 string back to image bytes."""
        return base64.b64decode(image_base64.encode('utf-8'))
    
    @staticmethod
    async def create(
        record_id: str,
        image_bytes: bytes,
        latitude: Optional[float],
        longitude: Optional[float],
        flowers: List[Dict[str, Any]],
        filename: str = "image.jpg"
    ) -> Dict[str, Any]:
        """Create a new classification record in MongoDB.
        
        Note: Only stores the annotated image (with bounding boxes), not the original.
        """
        db = get_database()
        collection = db["classifications"]
        
        # Encode annotated image to base64
        image_base64 = ClassificationRecord.encode_image(image_bytes)
        
        document = {
            "id": record_id,
            "image_base64": image_base64,
            "image_filename": filename,
            "image_content_type": "image/jpeg",
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": datetime.utcnow(),
            "flowers": flowers,
        }
        
        result = await collection.insert_one(document)
        return document
    
    @staticmethod
    async def get_by_id(record_id: str) -> Optional[Dict[str, Any]]:
        """Get classification record by ID."""
        db = get_database()
        collection = db["classifications"]
        return await collection.find_one({"id": record_id})
    
    @staticmethod
    async def get_all() -> List[Dict[str, Any]]:
        """Get all classification records, sorted by timestamp."""
        db = get_database()
        collection = db["classifications"]
        cursor = collection.find({}).sort("timestamp", -1)
        return await cursor.to_list(length=None)
    
    @staticmethod
    async def delete_by_id(record_id: str) -> bool:
        """Delete classification record by ID."""
        db = get_database()
        collection = db["classifications"]
        result = await collection.delete_one({"id": record_id})
        return result.deleted_count > 0
    
    @staticmethod
    async def count() -> int:
        """Get total number of classification records."""
        db = get_database()
        collection = db["classifications"]
        return await collection.count_documents({})


class VideoClassificationRecord:
    """
    MongoDB document model for video classification results.
    Uses GridFS for storing large video files.
    """
    
    @staticmethod
    async def create(
        record_id: str,
        video_bytes: bytes,
        latitude: Optional[float],
        longitude: Optional[float],
        frame_results: List[List[Dict[str, Any]]],
        video_metadata: Dict[str, Any],
        filename: str = "video.mp4"
    ) -> Dict[str, Any]:
        """
        Create a new video classification record in MongoDB.
        
        Stores video in GridFS (for large files) and metadata in regular collection.
        
        Args:
            record_id: Unique identifier for the record
            video_bytes: Raw video bytes (annotated)
            latitude: GPS latitude
            longitude: GPS longitude
            frame_results: List of detection lists (one per frame)
            video_metadata: Dict with 'total_frames', 'fps', 'duration'
            filename: Original filename
            
        Returns:
            Created document
        """
        db = get_database()
        bucket = get_gridfs_bucket()
        collection = db["video_classifications"]
        
        # Store video in GridFS
        video_id = await bucket.upload_from_stream(
            filename,
            video_bytes,
            metadata={
                "record_id": record_id,
                "content_type": "video/mp4",
                "uploaded_at": datetime.utcnow()
            }
        )
        
        # Aggregate statistics across all frames
        stage_summary = {0: 0, 1: 0, 2: 0}
        total_detections = 0
        
        for frame_detections in frame_results:
            total_detections += len(frame_detections)
            for det in frame_detections:
                stage = det['stage']
                stage_summary[stage] = stage_summary.get(stage, 0) + 1
        
        # Convert integer keys to strings for MongoDB compatibility
        stage_summary = {str(k): v for k, v in stage_summary.items()}
        
        # Calculate average flowers per frame
        total_frames = video_metadata.get('total_frames', len(frame_results))
        avg_flowers = total_detections / total_frames if total_frames > 0 else 0
        
        # Store metadata in regular collection
        document = {
            "id": record_id,
            "video_gridfs_id": video_id,
            "video_filename": filename,
            "video_content_type": "video/mp4",
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": datetime.utcnow(),
            "total_frames": total_frames,
            "fps": video_metadata.get('fps', 0),
            "duration_seconds": video_metadata.get('duration', 0),
            "frame_results": frame_results,  # Store all frame-by-frame detections
            "stage_summary": stage_summary,
            "total_detections": total_detections,
            "average_flowers_per_frame": avg_flowers,
        }
        
        await collection.insert_one(document)
        logger.info(f"Video classification record created: {record_id}")
        return document
    
    @staticmethod
    async def get_by_id(record_id: str) -> Optional[Dict[str, Any]]:
        """Get video classification record by ID."""
        db = get_database()
        collection = db["video_classifications"]
        return await collection.find_one({"id": record_id})
    
    @staticmethod
    async def get_all() -> List[Dict[str, Any]]:
        """Get all video classification records, sorted by timestamp."""
        db = get_database()
        collection = db["video_classifications"]
        cursor = collection.find({}).sort("timestamp", -1)
        return await cursor.to_list(length=None)
    
    @staticmethod
    async def get_video_bytes(record_id: str) -> Optional[bytes]:
        """
        Retrieve video bytes from GridFS.
        
        Args:
            record_id: Record identifier
            
        Returns:
            Video bytes or None if not found
        """
        record = await VideoClassificationRecord.get_by_id(record_id)
        if not record:
            return None
        
        bucket = get_gridfs_bucket()
        video_id = record.get('video_gridfs_id')
        
        if not video_id:
            logger.error(f"No video_gridfs_id found for record {record_id}")
            return None
        
        try:
            # Download from GridFS
            grid_out = await bucket.open_download_stream(video_id)
            video_bytes = await grid_out.read()
            return video_bytes
        except Exception as e:
            logger.error(f"Error downloading video from GridFS: {e}")
            return None
    
    @staticmethod
    async def delete_by_id(record_id: str) -> bool:
        """
        Delete video classification record by ID.
        Also deletes the video file from GridFS.
        """
        db = get_database()
        bucket = get_gridfs_bucket()
        collection = db["video_classifications"]
        
        # Get record first to get GridFS ID
        record = await VideoClassificationRecord.get_by_id(record_id)
        if not record:
            return False
        
        # Delete video from GridFS
        video_id = record.get('video_gridfs_id')
        if video_id:
            try:
                await bucket.delete(video_id)
                logger.info(f"Deleted video from GridFS: {video_id}")
            except Exception as e:
                logger.error(f"Error deleting video from GridFS: {e}")
        
        # Delete metadata document
        result = await collection.delete_one({"id": record_id})
        return result.deleted_count > 0
    
    @staticmethod
    async def count() -> int:
        """Get total number of video classification records."""
        db = get_database()
        collection = db["video_classifications"]
        return await collection.count_documents({})

