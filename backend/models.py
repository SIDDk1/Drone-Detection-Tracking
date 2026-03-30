from sqlmodel import SQLModel, Field
from datetime import datetime, date
from typing import Optional


class Detection(SQLModel, table=True):
    """Database model for drone detections"""
    id: Optional[int] = Field(default=None, primary_key=True)
    daily_id: int = Field(index=True)
    center_x: int
    center_y: int
    start_time: datetime 
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    detection_date: date = Field(index=True)  # ✅ Renamed from 'date' to 'detection_date'
    confidence: Optional[float] = None
    
class DetectionResponse(SQLModel):
    """Response model for API endpoints"""
    id: int
    daily_id: int
    center_x: int
    center_y: int
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    detection_date: date  # ✅ Updated here too
    confidence: Optional[float]


class DetectionCreate(SQLModel):
    """Model for creating new detections"""
    daily_id: int
    center_x: int
    center_y: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    detection_date: date  # ✅ Updated here too
    confidence: Optional[float] = None


class CameraStatus(SQLModel):
    """Model for camera status response"""
    is_running: bool
    message: str
    total_detections_today: int


class WebSocketMessage(SQLModel):
    """Model for WebSocket messages"""
    event: str
    daily_id: Optional[int] = None
    center: Optional[list] = None
    timestamp: Optional[str] = None
    message: Optional[str] = None
