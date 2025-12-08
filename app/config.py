"""
Configuration settings loaded from environment variables.
"""

import os
from typing import List


class Settings:
    """Application settings from environment variables."""
    
    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "7860"))  # HuggingFace Spaces default port
    
    # CORS configuration
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # MongoDB configuration
    MONGODB_URL: str = os.getenv("MONGODB_URL", "")
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "flower_classifications")
    
    # Upload directory (for temporary processing only - images stored in MongoDB)
    UPLOAD_DIR: str = os.getenv(
        "UPLOAD_DIR",
        os.path.join(os.getcwd(), "uploads/images")
    )
    
    # Ensure upload directory exists
    @classmethod
    def ensure_upload_dir(cls):
        """Create upload directory if it doesn't exist."""
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)


settings = Settings()

