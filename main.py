import cv2
import numpy as np
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import time
from datetime import datetime
import threading
import queue

class DroneTracker:
    def __init__(self, model_path='yolov8n.pt', confidence_threshold=0.5):
        """
        Initialize the drone tracking system
        
        Args:
            model_path: Path to YOLOv8 model file
            confidence_threshold: Minimum confidence for detections
        """
        # Load YOLOv8 model
        self.model = YOLO(model_path)
        
        # Initialize DeepSORT tracker
        self.tracker = DeepSort(max_age=50, n_init=3)
        
        # Configuration
        self.confidence_threshold = confidence_threshold
        self.target_classes = ['drone','drones']  # Add more drone-related classes if needed
        
        # Tracking state
        self.tracked_drones = {}  # Dictionary to store drone information
        self.frame_count = 0
        self.fps = 0
        self.last_time = time.time()
        
        # Output queue for logging
        self.output_queue = queue.Queue()
        
        # Start logging thread
        self.logging_thread = threading.Thread(target=self._log_output, daemon=True)
        self.logging_thread.start()
    
    def _get_timestamp(self):
        """Get current timestamp string"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def _log_output(self):
        """Background thread for logging output"""
        while True:
            try:
                message = self.output_queue.get(timeout=1)
                print(message)
                self.output_queue.task_done()
            except queue.Empty:
                continue
    
    def _is_drone_class(self, class_name):
        """Check if detected class is a drone"""
        # YOLOv8 might not have specific drone classes, so we'll check for common objects
        # that might be drones or modify this based on your trained model
        drone_keywords = ['drone', 'quadcopter', 'uav', 'aircraft', 'helicopter']
        return any(keyword in class_name.lower() for keyword in drone_keywords)
    
    def _extract_detections(self, results):
        """Extract detection boxes and confidences from YOLOv8 results"""
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = self.model.names[class_id]
                    
                    # Filter by confidence and class
                    if confidence >= self.confidence_threshold:
                        # For now, we'll track all objects with high confidence
                        # You can modify this to only track specific drone classes
                        detections.append({
                            'bbox': [x1, y1, x2, y2],
                            'confidence': confidence,
                            'class_name': class_name,
                            'class_id': class_id
                        })
        
        return detections
    
    def _format_detection_for_deepsort(self, detections):
        """Format detections for DeepSORT input"""
        if not detections:
            return [], []
        
        bboxes = []
        confidences = []
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            # Convert to [x, y, w, h] format for DeepSORT
            bbox = [x1, y1, x2 - x1, y2 - y1]
            bboxes.append(bbox)
            confidences.append(det['confidence'])
        
        return bboxes, confidences
    
    def _calculate_center(self, bbox):
        """Calculate center point of bounding box"""
        x1, y1, x2, y2 = bbox
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        return center_x, center_y
    
    def process_frame(self, frame):
        """Process a single frame for drone detection and tracking"""
        self.frame_count += 1
        current_time = time.time()
        
        # Calculate FPS
        if current_time - self.last_time >= 1.0:
            self.fps = self.frame_count / (current_time - self.last_time)
            self.frame_count = 0
            self.last_time = current_time
        
        # Run YOLOv8 detection
        results = self.model(frame, verbose=False)
        detections = self._extract_detections(results)
        
        # Format detections for DeepSORT
        bboxes, confidences = self._format_detection_for_deepsort(detections)
        
        # Update tracker
        tracks = self.tracker.update_tracks(bboxes, confidences, frame)
        
        # Process tracks
        current_drone_ids = set()
        
        for track in tracks:
            if not track.is_confirmed():
                continue
                
            track_id = track.track_id
            bbox = track.to_ltrb()  # Get bounding box in [x1, y1, x2, y2] format
            
            # Calculate center position
            center_x, center_y = self._calculate_center(bbox)
            
            current_drone_ids.add(track_id)
            timestamp = self._get_timestamp()
            
            # Check if this is a new drone
            if track_id not in self.tracked_drones:
                self.tracked_drones[track_id] = {
                    'first_detected': timestamp,
                    'last_seen': timestamp,
                    'center_x': center_x,
                    'center_y': center_y
                }
                
                # Log first detection
                message = f"[{timestamp}] DRONE DETECTED - ID: {track_id}, Position: ({center_x}, {center_y})"
                self.output_queue.put(message)
            else:
                # Update existing drone
                self.tracked_drones[track_id]['last_seen'] = timestamp
                self.tracked_drones[track_id]['center_x'] = center_x
                self.tracked_drones[track_id]['center_y'] = center_y
                
                # Log position update
                message = f"[{timestamp}] DRONE TRACKING - ID: {track_id}, Position: ({center_x}, {center_y})"
                self.output_queue.put(message)
        
        # Check for drones that have left the frame
        drones_to_remove = []
        for drone_id in self.tracked_drones:
            if drone_id not in current_drone_ids:
                timestamp = self._get_timestamp()
                last_seen = self.tracked_drones[drone_id]['last_seen']
                
                # Log drone left frame
                message = f"[{timestamp}] DRONE LEFT FRAME - ID: {drone_id}, Last seen: {last_seen}"
                self.output_queue.put(message)
                
                drones_to_remove.append(drone_id)
        
        # Remove drones that left the frame
        for drone_id in drones_to_remove:
            del self.tracked_drones[drone_id]
        
        # Draw tracking information on frame
        annotated_frame = self._draw_tracks(frame, tracks)
        
        return annotated_frame
    
    def _draw_tracks(self, frame, tracks):
        """Draw tracking information on frame"""
        for track in tracks:
            if not track.is_confirmed():
                continue
                
            track_id = track.track_id
            bbox = track.to_ltrb()
            x1, y1, x2, y2 = map(int, bbox)
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw center point
            center_x, center_y = self._calculate_center(bbox)
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            
            # Draw ID and position
            label = f"ID: {track_id} ({center_x}, {center_y})"
            cv2.putText(frame, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw FPS
        cv2.putText(frame, f"FPS: {self.fps:.1f}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw active drone count
        active_count = len(self.tracked_drones)
        cv2.putText(frame, f"Active Drones: {active_count}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame
    
    def run(self, camera_index=0):
        """Run the drone tracking system"""
        # Initialize camera
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print("Error: Could not open camera")
            return
        
        print("Drone Detection and Tracking System Started")
        print("Press 'q' to quit")
        print("-" * 50)
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Error: Could not read frame")
                    break
                
                # Process frame
                annotated_frame = self.process_frame(frame)
                
                # Display frame
                cv2.imshow('Drone Detection and Tracking', annotated_frame)
                
                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            print("\nStopping drone tracker...")
        
        finally:
            # Cleanup
            cap.release()
            cv2.destroyAllWindows()
            
            # Log final status for all tracked drones
            timestamp = self._get_timestamp()
            for drone_id in self.tracked_drones:
                message = f"[{timestamp}] SYSTEM SHUTDOWN - Drone ID: {drone_id} was being tracked"
                self.output_queue.put(message)

def main():
    """Main function to run the drone tracker"""
    # Initialize tracker
    # You can specify a custom YOLOv8 model path if you have a drone-specific model
    tracker = DroneTracker(
        model_path='yolov',  # Change to your drone detection model
        confidence_threshold=0.5
    )
    
    # Run the tracking system
    tracker.run(camera_index=0)  # Change camera index if needed

if __name__ == "__main__":
    main()