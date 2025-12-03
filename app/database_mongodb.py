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


async def connect_to_mongodb():
    """Connect to MongoDB database."""
    global mongodb_client, mongodb_db
    
    if not MONGODB_URL:
        raise ValueError(
            "MONGODB_URL environment variable is not set. "
            "Please set it to your MongoDB connection string."
        )
    
    try:
        mongodb_client = AsyncIOMotorClient(MONGODB_URL)
        # Test connection
        await mongodb_client.admin.command('ping')
        mongodb_db = mongodb_client[DATABASE_NAME]
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


async def create_indexes():
    """Create database indexes for better query performance."""
    db = get_database()
    collection = db["classifications"]
    
    # Create index on id field (unique)
    await collection.create_index("id", unique=True)
    
    # Create index on timestamp for sorting
    await collection.create_index("timestamp")
    
    # Create geospatial index for location queries (if needed in future)
    await collection.create_index([("latitude", 1), ("longitude", 1)])
    
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
        """Create a new classification record in MongoDB."""
        db = get_database()
        collection = db["classifications"]
        
        # Encode image to base64
        image_base64 = ClassificationRecord.encode_image(image_bytes)
        
        document = {
            "id": record_id,
            "image_base64": image_base64,
            "image_filename": filename,
            "image_content_type": "image/jpeg",  # Could be detected from file
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

