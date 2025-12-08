"""
Pydantic models for API request/response validation.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates in [x_min, y_min, x_max, y_max] format."""
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class FlowerDetection(BaseModel):
    """A single flower detection with bounding box and stage classification."""
    bounding_box: List[float] = Field(
        ..., 
        description="Bounding box as [x_min, y_min, x_max, y_max]",
        min_length=4,
        max_length=4
    )
    stage: int = Field(
        ..., 
        ge=0, 
        le=2, 
        description="Flower stage: 0=bud, 1=anthesis, 2=post-anthesis"
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Model confidence score"
    )


class Location(BaseModel):
    """GPS location coordinates."""
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class ClassificationRequest(BaseModel):
    """Request body for classification (location can be provided manually)."""
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class ClassificationResponse(BaseModel):
    """Response from the classification endpoint."""
    id: str
    image_path: str
    location: Location
    timestamp: datetime
    flowers: List[FlowerDetection]
    flower_count: int
    stage_summary: dict = Field(
        ..., 
        description="Count of flowers at each stage: {0: n, 1: n, 2: n}"
    )


class HeatmapDataPoint(BaseModel):
    """A single data point for the heatmap."""
    id: str
    latitude: Optional[float]
    longitude: Optional[float]
    timestamp: datetime
    flowers: List[FlowerDetection]
    total_flowers: int
    stage_counts: dict


class HeatmapResponse(BaseModel):
    """Response containing all data points for heatmap visualization."""
    total_records: int
    data_points: List[HeatmapDataPoint]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    timestamp: datetime


class JobStatusResponse(BaseModel):
    """Response for async job status."""
    job_id: str
    status: str = Field(..., description="Job status: queued, processing, completed, failed")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Processing progress percentage")
    message: Optional[str] = Field(None, description="Status message or error details")
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[dict] = Field(None, description="Classification result when completed")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated seconds remaining")


class FrameStatistics(BaseModel):
    """Statistics for a single video frame."""
    frame_number: int = Field(..., description="Frame number (0-indexed)")
    detections: List[FlowerDetection] = Field(
        default_factory=list,
        description="All flower detections in this frame"
    )
    stage_counts: dict = Field(
        default_factory=lambda: {0: 0, 1: 0, 2: 0},
        description="Count of flowers at each stage in this frame: {0: n, 1: n, 2: n}"
    )


class VideoClassificationResponse(BaseModel):
    """Response from video classification endpoint."""
    id: str
    video_path: str = Field(..., description="API endpoint to retrieve the annotated video")
    location: Location
    timestamp: datetime
    total_frames: int = Field(..., description="Total number of frames in the video")
    fps: float = Field(..., description="Frames per second")
    duration_seconds: float = Field(..., description="Video duration in seconds")
    
    # Aggregated statistics across all frames
    total_detections: int = Field(..., description="Total flower detections across all frames")
    average_flowers_per_frame: float = Field(..., description="Average number of flowers per frame")
    stage_summary: dict = Field(
        ..., 
        description="Overall count of flowers at each stage: {0: n, 1: n, 2: n}"
    )
    
    # Frame-by-frame breakdown (optional, can be large)
    frame_statistics: Optional[List[FrameStatistics]] = Field(
        None,
        description="Detailed statistics for each frame (may be omitted for large videos)"
    )

