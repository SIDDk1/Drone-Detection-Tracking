from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
import time
from contextlib import asynccontextmanager
from database import get_session
from models import (
    Detection, DetectionResponse, DetectionCreate, 
    CameraStatus, WebSocketMessage
)
from tracker import DroneTracker
import cv2
import json
import asyncio
import logging
from datetime import date, datetime
from typing import List, Optional
import os
from pathlib import Path
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_model_path() -> Optional[str]:
    """Resolve YOLO weights: MODEL_PATH env, backend/best.pt, or HF_MODEL_REPO download."""
    env_model = os.getenv("MODEL_PATH")
    if env_model:
        p = Path(env_model)
        if not p.is_absolute():
            p = Path(BASE_DIR) / p
        if p.is_file():
            return str(p)
        logger.warning("MODEL_PATH is set but file not found: %s", p)

    default = Path(BASE_DIR) / "best.pt"
    if default.is_file():
        return str(default)

    repo = os.getenv("HF_MODEL_REPO", "").strip()
    if not repo:
        return None

    filename = os.getenv("HF_MODEL_FILE", "best.pt").strip() or "best.pt"
    try:
        from huggingface_hub import hf_hub_download

        token = os.getenv("HF_TOKEN") or None
        path = hf_hub_download(
            repo_id=repo,
            filename=filename,
            local_dir=BASE_DIR,
            token=token,
        )
        logger.info("Downloaded model from Hugging Face: %s", path)
        return str(path)
    except Exception as e:
        logger.error("Failed to download model from Hugging Face (HF_MODEL_REPO=%s): %s", repo, e)
        return None


def resolve_video_path() -> str:
    env_v = os.getenv("VIDEO_PATH", "").strip()
    if env_v and os.path.isfile(env_v):
        return env_v
    rel = os.path.join(BASE_DIR, "..", "V_DRONE_FIRST_4_MIN.mp4")
    if os.path.isfile(rel):
        return rel
    home_candidate = os.path.join(os.path.expanduser("~"), "V_DRONE_FIRST_4_MIN.mp4")
    if os.path.isfile(home_candidate):
        return home_candidate
    return rel

# This function will run during startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    # --- Startup ---
    global tracker, manager
    logger.info("🚀 Application starting up...")
    
    # Initialize WebSocket Manager
    manager = ConnectionManager()
    logger.info("WebSocket Manager initialized.")

    # Initialize Drone Tracker
    try:
        model_path = resolve_model_path()
        video_path = resolve_video_path()
        if not model_path:
            raise RuntimeError(
                "No model weights found. Add backend/best.pt to the repo, set MODEL_PATH, "
                "or set HF_MODEL_REPO (and optional HF_MODEL_FILE) on the Space to download weights."
            )
        if not os.path.isfile(video_path):
            logger.warning("Video file not found at %s — camera start may fail.", video_path)

        tracker = DroneTracker(
            model_path, confidence_threshold=0.5, video_source=video_path
        )

        async def on_new_detection(data):
            await manager.broadcast(json.dumps(data))

        async def on_status_update(data):
            await manager.broadcast(json.dumps(data))

        tracker.set_callbacks(on_new_detection, on_status_update)
        logger.info("✅ DroneTracker initialized successfully.")

    except Exception as e:
        logger.error(f"💥 Failed to initialize DroneTracker: {e}", exc_info=True)
        tracker = None

    yield  # The application runs here

    # --- Shutdown ---
    logger.info("🛑 Application shutting down...")
    if tracker and tracker.is_camera_running():
        tracker.stop()
        logger.info("Tracker stopped on shutdown.")

# Initialize FastAPI app
app = FastAPI(
    title="Drone Tracking API",
    description="Real-time drone detection and tracking system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

tracker: Optional[DroneTracker] = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to client: {e}")
                disconnected.append(connection)
                
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


manager: Optional[ConnectionManager] = None


def generate_frames():
    """Generate video frames for streaming"""
    try:
        while True:
            if tracker is None:
                status_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(
                    status_frame,
                    "Tracker unavailable — add best.pt or HF_MODEL_REPO",
                    (20, 240),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 0, 255),
                    2,
                )
                ret, buffer = cv2.imencode(".jpg", status_frame)
                if ret:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                    )
            elif tracker.is_camera_running():
                frame = tracker.get_latest_frame()
                if frame is not None:
                    # Encode frame to JPEG
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    else:
                        logger.error("Failed to encode frame to JPEG")
                else:
                    # Create error frame using numpy (not cv2)
                    error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(error_frame, "No camera feed", (200, 240), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    
                    ret, buffer = cv2.imencode('.jpg', error_frame)
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # Camera not running - create status frame
                status_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(status_frame, "Camera Stopped", (180, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                
                ret, buffer = cv2.imencode('.jpg', status_frame)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            time.sleep(0.033)  # ~30 FPS
            
    except Exception as e:
        logger.error(f"Error generating frame: {e}")
        # Create final error frame
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_frame, "Stream Error", (200, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        ret, buffer = cv2.imencode('.jpg', error_frame)
        if ret:
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# API Routes

from fastapi.responses import FileResponse
import os

@app.get("/")
async def root():
    """Root endpoint serving the React frontend"""
    index_path = os.path.join(BASE_DIR, "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "Drone Tracking API",
        "version": "1.0.0",
        "endpoints": [
            "/video - Video stream",
            "/camera/{action} - Camera control",
            "/detections/today - Today's detections",
            "/detections/ - All detections",
            "/ws - WebSocket connection"
        ]
    }

@app.exception_handler(404)
async def custom_404_handler(request, exc):
    """Fallback to index.html for React Router"""
    if request.url.path.startswith("/api/") or request.url.path.startswith("/ws"):
        return {"detail": "Not Found"}
    index_path = os.path.join(BASE_DIR, "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Not Found"}

@app.get("/video")
async def video_feed():
    logger.info("streaming video feed")
    
    """Stream video feed with drone detection overlay"""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache", 
            "Expires": "0",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.post("/camera/{action}")
async def camera_control(action: str) -> CameraStatus:
    """Control camera (start/stop)"""
    global tracker
    
    if not tracker:
        raise HTTPException(status_code=503, detail="Tracker not initialized")
    
    if action.lower() == "start":
        if tracker.is_camera_running():
            return CameraStatus(
                is_running=True,
                message="Camera is already running",
                total_detections_today=tracker.get_today_detection_count()
            )
        
        success = tracker.start()
        if success:
            return CameraStatus(
                is_running=True,
                message="Camera started successfully",
                total_detections_today=tracker.get_today_detection_count()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to start camera")
            
    elif action.lower() == "stop":
        if not tracker.is_camera_running():
            return CameraStatus(
                is_running=False,
                message="Camera is already stopped",
                total_detections_today=tracker.get_today_detection_count()
            )
        
        success = tracker.stop()
        if success:
            return CameraStatus(
                is_running=False,
                message="Camera stopped successfully",
                total_detections_today=tracker.get_today_detection_count()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to stop camera")
            
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'start' or 'stop'")

@app.get("/camera/status")
async def camera_status() -> CameraStatus:
    """Get current camera status"""
    global tracker
    
    if not tracker:
        return CameraStatus(
            is_running=False,
            message="Tracker not initialized",
            total_detections_today=0
        )
    
    return CameraStatus(
        is_running=tracker.is_camera_running(),
        message="Camera status retrieved",
        total_detections_today=tracker.get_today_detection_count()
    )

@app.get("/detections/today", response_model=List[DetectionResponse])
async def get_today_detections(session: Session = Depends(get_session)):
    """Get all detections for today"""
    today = date.today()
    statement = select(Detection).where(Detection.detection_date == today).order_by(Detection.start_time.desc())
    detections = session.exec(statement).all()
    logger.info(f"Retrieved {len(detections)} detections for today: {today}")
    return detections

@app.get("/detections/", response_model=List[DetectionResponse])
async def get_all_detections(
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_session)
):
    """Get all detections with pagination"""
    statement = select(Detection).order_by(Detection.start_time.desc()).offset(offset).limit(limit)
    detections = session.exec(statement).all()
    return detections

@app.get("/detections/date/{detection_date}", response_model=List[DetectionResponse])
async def get_detections_by_date(detection_date: date, session: Session = Depends(get_session)):
    """Get detections for specific date"""
    statement = select(Detection).where(Detection.detection_date == detection_date).order_by(Detection.start_time.desc())
    detections = session.exec(statement).all()
    logger.info(f"Retrieved {len(detections)} detections for date: {detection_date}")
    return detections

@app.post("/detections/", response_model=DetectionResponse)
async def create_detection(detection: DetectionCreate, session: Session = Depends(get_session)):
    """Create a new detection (mainly for testing)"""
    db_detection = Detection.from_orm(detection)
    session.add(db_detection)
    session.commit()
    session.refresh(db_detection)
    return db_detection

@app.delete("/detections/{detection_id}")
async def delete_detection(detection_id: int, session: Session = Depends(get_session)):
    """Delete a detection"""
    detection = session.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    session.delete(detection)
    session.commit()
    return {"message": "Detection deleted successfully"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        # Send initial status
        global tracker
        if tracker:
            status_message = {
                "event": "status_update",
                "is_running": tracker.is_camera_running(),
                "total_detections_today": tracker.get_today_detection_count(),
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_text(json.dumps(status_message))
        
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back or handle specific commands if needed
            if data == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "timestamp": datetime.now().isoformat()}))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Serve static files for development
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global tracker
    return {
        "status": "healthy",
        "tracker_initialized": tracker is not None,
        "camera_running": tracker.is_camera_running() if tracker else False,
        "timestamp": datetime.now().isoformat()
    }

# Development static file serving
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
