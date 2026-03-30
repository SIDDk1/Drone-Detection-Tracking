import cv2
import numpy as np
import datetime
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import threading
import json
import os
import queue
import time
from sqlmodel import Session, select
from database import engine
from models import Detection, DetectionCreate
from typing import Optional, Callable
import asyncio
import logging
# Add this for device detection
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DroneTracker:
    def __init__(self, model_path: str, confidence_threshold: float = 0.5, video_source=0):
        # Initialize YOLO model
        self.device = 'cpu' #self._detect_device()
        self.video_source = video_source
        self.model = YOLO(model_path)
        self.model.to(self.device)
        self.confidence_threshold = confidence_threshold
        
        # Initialize DeepSORT tracker
        self.tracker = DeepSort(
            max_age=5,        # Keep tracks for 50 frames without detection          # Require 3 consecutive detections to confirm track
            max_cosine_distance=0.4,  # Increase distance threshold
            nn_budget=None,    # No limit on stored features
            bgr=True,
            

            
        )
        # Tracking variables
        self.daily_id_counter = 0
        self.tracked_objects = {}
        self.current_date = datetime.date.today()
        self.first_detection_alert_shown = False
        
        # Threading and streaming variables
        self.is_running = False
        self.thread = None
        self.cap = None
        self.frame_queue = queue.Queue(maxsize=10)
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        
        # Callback for new detections (WebSocket broadcasting)
        self.on_new_detection: Optional[Callable] = None
        self.on_status_update: Optional[Callable] = None
        
        # Load existing daily data
        self.load_daily_data()

    def _detect_device(self):
        """Detect the best available device for inference"""
        try:
            import torch
            
            if torch.cuda.is_available():
                device = 'cuda'
                device_name = torch.cuda.get_device_name(0)
                logger.info(f"Using CUDA GPU: {device_name}")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = 'mps'  # Apple Silicon GPU
                logger.info("Using Apple Silicon GPU (MPS)")
            else:
                device = 'cpu'
                logger.info("Using CPU for inference")
                
            return device
            
        except ImportError:
            logger.warning("PyTorch not available, defaulting to CPU")
            return 'cpu'
        except Exception as e:
            logger.error(f"Error detecting device: {e}, defaulting to CPU")
            return 'cpu'

        
    def set_callbacks(self, on_new_detection: Optional[Callable] = None, 
                     on_status_update: Optional[Callable] = None):
        """Set callback functions for WebSocket broadcasting"""
        self.on_new_detection = on_new_detection
        self.on_status_update = on_status_update
        
    def load_daily_data(self):
        """Load existing daily tracking data from database"""
        try:
            with Session(engine) as session:
                # Get today's detections
                today = datetime.date.today()
                statement = select(Detection).where(Detection.detection_date == today)
                results = session.exec(statement).all()
                
                if results:
                    # Find the highest daily_id for today
                    self.daily_id_counter = max([d.daily_id for d in results])
                    logger.info(f"Loaded {len(results)} existing detections for today. Counter at {self.daily_id_counter}")
                else:
                    self.daily_id_counter = 0
                    logger.info("No existing detections found for today")
                    
        except Exception as e:
            logger.error(f"Error loading daily data: {e}")
            self.daily_id_counter = 0
            
    def get_bounding_box_center(self, bbox):
        """Calculate center coordinates of bounding box"""
        x1, y1, x2, y2 = bbox
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        return center_x, center_y
        
    def process_detections(self, results, frame):
        """Process YOLO detections and prepare for DeepSORT tracking"""
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    confidence = float(box.conf[0])
                    logger.debug(f"Detected box with confidence: {confidence}")
                    
                    if confidence and confidence >= self.confidence_threshold:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                        width = x2 - x1
                        height = y2 - y1
                        if width > 0 and height > 0:
                            # DeepSort expects [x, y, w, h] format
                            detection = ([x1, y1, width, height], confidence, 'drone')
                            detections.append(detection)
                            logger.debug(f"Valid detection: bbox=[{x1}, {y1}, {width}, {height}], conf={confidence:.3f}")
                       
                        
        return detections
        
    def save_detection_to_db(self, daily_id: int, center_x: int, center_y: int, 
                           start_time: datetime.datetime, confidence: float = None):
        """Save detection to database"""
        print(daily_id,center_x,center_y,start_time,start_time.date(),confidence)
        try:
            if confidence is None:
                confidence = 0.5 

           
            with Session(engine) as session:
                detection = Detection(
                    daily_id=daily_id,
                    center_x=center_x,
                    center_y=center_y,
                    start_time=start_time,
                    detection_date=start_time.date(),
                    confidence=confidence
                )
                session.add(detection)
                session.commit()
                logger.info(f"Saved detection {daily_id} to database")
                
        except Exception as e:
            logger.error(f"Error saving detection to database: {e}")
            
    def update_tracking_info(self, track_id, bbox, confidence=None):
        """Update tracking information for each drone"""
        current_time = datetime.datetime.now()
        
        if track_id not in self.tracked_objects:
            # New drone detected - assign daily ID
            self.daily_id_counter += 1
            center_x, center_y = self.get_bounding_box_center(bbox)
            
            self.tracked_objects[track_id] = {
                'daily_id': self.daily_id_counter,
                'start_time': current_time,
                'end_time': current_time,
                'last_seen': current_time,
                'center_x': center_x,
                'center_y': center_y,
                'confidence': confidence
            }
            
            # Save to database
            self.save_detection_to_db(
                self.daily_id_counter, center_x, center_y, current_time, confidence
            )
            
            # Show first detection alert
            if self.daily_id_counter == 1:
                self.show_first_detection_alert()
                
            # Trigger callback for WebSocket broadcasting
            if self.on_new_detection:
                detection_data = {
                    "event": "new_drone",
                    "daily_id": self.daily_id_counter,
                    "center": [center_x, center_y],
                    "timestamp": current_time.isoformat(),
                    "confidence": confidence
                }
                # Schedule callback in thread-safe manner
                threading.Thread(target=self._async_callback, 
                               args=(self.on_new_detection, detection_data)).start()
                
            logger.info(f"New drone detected - Daily ID: {self.daily_id_counter}")
            
        else:
            # Update existing drone info
            self.tracked_objects[track_id]['end_time'] = current_time
            self.tracked_objects[track_id]['last_seen'] = current_time
            
    def _async_callback(self, callback, data):
        """Execute callback in a thread-safe manner"""
        try:
            if asyncio.iscoroutinefunction(callback):
                # Run async callback
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(callback(data))
                loop.close()
            else:
                callback(data)
        except Exception as e:
            logger.error(f"Error in callback: {e}")
            
    def show_first_detection_alert(self):
        """Show alert for first detection of the day"""
        if not self.first_detection_alert_shown:
            logger.info("🚨 ALERT: First drone detected today! 🚨")
            self.first_detection_alert_shown = True
            
    def draw_tracking_info(self, frame, tracks):
        """Draw bounding boxes and tracking information on frame"""
        for track in tracks:
            if not track.is_confirmed():
                continue
            track_id = track.track_id
            bbox = track.to_ltwh()
            
            x1 = int(bbox[0])
            y1 = int(bbox[1])
            x2 = int(bbox[0] + bbox[2])
            y2 = int(bbox[1] + bbox[3])
            
            # Update tracking info
            self.update_tracking_info(track_id, [x1, y1, x2, y2])
            
            center_x, center_y = self.get_bounding_box_center([x1, y1, x2, y2])
            daily_id = self.tracked_objects[track_id]['daily_id']
            start_time = self.tracked_objects[track_id]['start_time']
            current_time = datetime.datetime.now()
            duration = current_time - start_time
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw center point
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            
            # Draw tracking information
            info_text = f"Drone ID: {daily_id}"
            time_text = f"Duration: {str(duration).split('.')[0]}"
            center_text = f"Center: ({center_x}, {center_y})"
            
            cv2.putText(frame, info_text, (x1, y1-40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, time_text, (x1, y1-25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(frame, center_text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
    def cleanup_inactive_tracks(self):
        """Remove tracks that haven't been seen for a while"""
        current_time = datetime.datetime.now()
        inactive_threshold = datetime.timedelta(seconds=5)
        
        inactive_tracks = []
        for track_id, info in self.tracked_objects.items():
            if current_time - info['last_seen'] > inactive_threshold:
                inactive_tracks.append(track_id)
                
        for track_id in inactive_tracks:
            info = self.tracked_objects[track_id]
            total_duration = info['end_time'] - info['start_time']
            logger.info(f"Drone ID {info['daily_id']} left | Total Duration: {str(total_duration).split('.')[0]}")
            del self.tracked_objects[track_id]
            
    def capture_frames(self):
        """Main camera capture loop running in separate thread"""
        self.cap = cv2.VideoCapture(self.video_source)
        # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        if not self.cap.isOpened():
            logger.error("Failed to open camera")
            self.is_running = False
            return
            
        logger.info("Camera started successfully")
        
        while self.is_running:
            try:
                # Check if date has changed
                if datetime.date.today() != self.current_date:
                    self.current_date = datetime.date.today()
                    self.daily_id_counter = 0
                    self.tracked_objects = {}
                    self.first_detection_alert_shown = False
                    logger.info(f"New day started: {self.current_date}")
                    
                ret, frame = self.cap.read()
                if not ret:
                    if self.video_source != 0 and isinstance(self.video_source, str):
                        logger.info("Restarting video loop")
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        logger.error("Failed to grab frame from webcam")
                        break
                    
                # Run YOLO detection
                results = self.model(frame, verbose=False,device=self.device)
                
                # Process detections for DeepSORT
                detections = self.process_detections(results, frame)
                
                # Update tracker with detections
                tracks = self.tracker.update_tracks(detections, frame=frame)
                
                # Draw tracking information
                if tracks:
                    self.draw_tracking_info(frame, tracks)
                    
                # Cleanup inactive tracks
                self.cleanup_inactive_tracks()
                
                # Add status information to frame
                status_text = f"Date: {self.current_date} | Drones detected today: {self.daily_id_counter}"
                cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # Store latest frame for streaming
                with self.frame_lock:
                    self.latest_frame = frame.copy()
                    
                # Small delay to prevent overwhelming the system
                time.sleep(0.011)  # ~30 FPS
                
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                break
                
        # Cleanup
        if self.cap:
            self.cap.release()
        logger.info("Camera capture stopped")
        
    def get_latest_frame(self):
        """Get the latest frame for streaming"""
        with self.frame_lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None
            
    def start(self):
        """Start the camera capture in a separate thread"""
        if self.is_running:
            logger.warning("Camera is already running")
            return False
            
        self.is_running = True
        self.thread = threading.Thread(target=self.capture_frames)
        self.thread.daemon = True
        self.thread.start()
        
        # Trigger status update callback
        if self.on_status_update:
            status_data = {
                "event": "camera_started",
                "message": "Camera started successfully",
                "is_running": True,
                "total_detections_today": self.daily_id_counter
            }
            threading.Thread(target=self._async_callback, 
                           args=(self.on_status_update, status_data)).start()
            
        return True
        
    def stop(self):
        """Stop the camera capture"""
        if not self.is_running:
            logger.warning("Camera is not running")
            return False
            
        self.is_running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
            
        # Trigger status update callback
        if self.on_status_update:
            status_data = {
                "event": "camera_stopped",
                "message": "Camera stopped successfully",
                "is_running": False,
                "total_detections_today": self.daily_id_counter
            }
            threading.Thread(target=self._async_callback, 
                           args=(self.on_status_update, status_data)).start()
            
        logger.info("Camera tracking stopped")
        return True
        
    def is_camera_running(self):
        """Check if camera is currently running"""
        return self.is_running
        
    def get_today_detection_count(self):
        """Get total detections for today"""
        return self.daily_id_counter
