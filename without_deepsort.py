import cv2
import numpy as np
import datetime
from ultralytics import YOLO
# Try different import methods for DeepSort

DeepSort = None

import threading
import json
import os

class DroneTracker:
    def __init__(self, model_path, confidence_threshold=0.5):
        # Initialize YOLO model
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        
        # Initialize DeepSORT tracker if available
        if DeepSort is not None:
            self.tracker = DeepSort(max_age=50, n_init=2)
            self.use_deepsort = True
        else:
            self.tracker = None
            self.use_deepsort = False
            print("Using YOLO built-in tracking instead of DeepSort")
        
        # Tracking variables
        self.daily_id_counter = 0
        self.tracked_objects = {}
        self.current_date = datetime.date.today()
        self.first_detection_alert_shown = False
        self.yolo_track_to_daily_id = {}  # For YOLO tracking fallback
        
        # Load or initialize daily tracking data
        self.load_daily_data()
        
    def load_daily_data(self):
        """Load existing daily tracking data or create new file for today"""
        filename = f"drone_tracking_{self.current_date}.json"
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                    self.daily_id_counter = data.get('daily_id_counter', 0)
                    self.tracked_objects = {}
            except:
                self.daily_id_counter = 0
                
    def save_daily_data(self):
        """Save daily tracking data to file"""
        filename = f"drone_tracking_{self.current_date}.json"
        data = {
            'date': str(self.current_date),
            'daily_id_counter': self.daily_id_counter,
            'total_drones_detected': self.daily_id_counter
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
            
    def show_first_detection_alert(self):
        """Show alert for first detection of the day"""
        if not self.first_detection_alert_shown:
            print("🚨 ALERT: First drone detected today! 🚨")
            print(f"Alert Time: {datetime.datetime.now().strftime('%H:%M:%S')}")
            self.first_detection_alert_shown = True
            
    def get_bounding_box_center(self, bbox):
        """Calculate center coordinates of bounding box"""
        x1, y1, x2, y2 = bbox
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        return center_x, center_y
        
    def process_detections_deepsort(self, results, frame):
        """Process YOLO detections for DeepSORT tracking"""
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    confidence = float(box.conf[0])
                    
                    if confidence >= self.confidence_threshold:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        detection = ([x1, y1, x2-x1, y2-y1], confidence, 'drone')
                        detections.append(detection)
                        
        return detections
        
    def update_tracking_info(self, track_id, bbox):
        """Update tracking information for each drone"""
        current_time = datetime.datetime.now()
        
        if track_id not in self.tracked_objects:
            self.daily_id_counter += 1
            self.tracked_objects[track_id] = {
                'daily_id': self.daily_id_counter,
                'start_time': current_time,
                'end_time': current_time,
                'last_seen': current_time
            }
            
            if self.daily_id_counter == 1:
                self.show_first_detection_alert()
                
            print(f"🆕 New drone detected - Daily ID: {self.daily_id_counter}")
            print(f"   Start Time: {current_time.strftime('%H:%M:%S')}")
            
        else:
            self.tracked_objects[track_id]['end_time'] = current_time
            self.tracked_objects[track_id]['last_seen'] = current_time
            
    def draw_tracking_info_deepsort(self, frame, tracks):
        """Draw bounding boxes and tracking information on frame for DeepSort"""
        for track in tracks:
            track_id = track.track_id
            bbox = track.to_ltwh()
            
            x1 = int(bbox[0])
            y1 = int(bbox[1])
            x2 = int(bbox[0] + bbox[2])
            y2 = int(bbox[1] + bbox[3])
            
            self.update_tracking_info(track_id, [x1, y1, x2, y2])
            center_x, center_y = self.get_bounding_box_center([x1, y1, x2, y2])
            
            daily_id = self.tracked_objects[track_id]['daily_id']
            start_time = self.tracked_objects[track_id]['start_time']
            current_time = datetime.datetime.now()
            duration = current_time - start_time
            
            # Draw bounding box and info
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            
            info_text = f"Drone ID: {daily_id}"
            time_text = f"Duration: {str(duration).split('.')[0]}"
            center_text = f"Center: ({center_x}, {center_y})"
            
            cv2.putText(frame, info_text, (x1, y1-40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, time_text, (x1, y1-25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(frame, center_text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            print(f"🎯 Drone ID: {daily_id} | Center: ({center_x}, {center_y}) | "
                  f"Duration: {str(duration).split('.')[0]} | "
                  f"Time: {current_time.strftime('%H:%M:%S')}")
                  
    def draw_tracking_info_yolo(self, frame, results):
        """Draw bounding boxes and tracking information using YOLO tracking"""
        for result in results:
            boxes = result.boxes
            if boxes is not None and boxes.id is not None:
                for box in boxes:
                    confidence = float(box.conf[0])
                    
                    if confidence >= self.confidence_threshold:
                        # Get YOLO track ID
                        yolo_track_id = int(box.id[0])
                        
                        # Map to daily ID
                        if yolo_track_id not in self.yolo_track_to_daily_id:
                            self.daily_id_counter += 1
                            self.yolo_track_to_daily_id[yolo_track_id] = self.daily_id_counter
                            
                            if self.daily_id_counter == 1:
                                self.show_first_detection_alert()
                                
                            print(f"🆕 New drone detected - Daily ID: {self.daily_id_counter}")
                            print(f"   Start Time: {datetime.datetime.now().strftime('%H:%M:%S')}")
                        
                        daily_id = self.yolo_track_to_daily_id[yolo_track_id]
                        
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                        center_x, center_y = self.get_bounding_box_center([x1, y1, x2, y2])
                        
                        # Draw bounding box and info
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                        
                        info_text = f"Drone ID: {daily_id}"
                        center_text = f"Center: ({center_x}, {center_y})"
                        conf_text = f"Conf: {confidence:.2f}"
                        
                        cv2.putText(frame, info_text, (x1, y1-40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        cv2.putText(frame, center_text, (x1, y1-25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                        cv2.putText(frame, conf_text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                        
                        current_time = datetime.datetime.now()
                        print(f"🎯 Drone ID: {daily_id} | Center: ({center_x}, {center_y}) | "
                              f"Confidence: {confidence:.2f} | Time: {current_time.strftime('%H:%M:%S')}")
                              
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
            print(f"📤 Drone ID {info['daily_id']} left | "
                  f"Total Duration: {str(total_duration).split('.')[0]}")
            del self.tracked_objects[track_id]
            
    def run_webcam_tracking(self):
        """Main function to run webcam tracking"""
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        print("🚁 Starting drone tracking...")
        print(f"📅 Date: {self.current_date}")
        print(f"🔧 Using {'DeepSort' if self.use_deepsort else 'YOLO'} tracking")
        print("Press 'q' to quit")
        
        while True:
            if datetime.date.today() != self.current_date:
                self.save_daily_data()
                self.current_date = datetime.date.today()
                self.daily_id_counter = 0
                self.tracked_objects = {}
                self.yolo_track_to_daily_id = {}
                self.first_detection_alert_shown = False
                print(f"📅 New day started: {self.current_date}")
                
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame from webcam")
                break
                
            if self.use_deepsort:
                # Use DeepSort tracking
                results = self.model(frame, verbose=False)
                detections = self.process_detections_deepsort(results, frame)
                tracks = self.tracker.update_tracks(detections, frame=frame)
                
                if tracks:
                    self.draw_tracking_info_deepsort(frame, tracks)
                    
                self.cleanup_inactive_tracks()
                
            else:
                # Use YOLO built-in tracking
                results = self.model.track(frame, persist=True, verbose=False)
                self.draw_tracking_info_yolo(frame, results)
            
            # Add status information to frame
            status_text = f"Date: {self.current_date} | Drones detected today: {self.daily_id_counter}"
            tracking_method = f"Tracking: {'DeepSort' if self.use_deepsort else 'YOLO'}"
            cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, tracking_method, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            cv2.imshow('Drone Tracking', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        cap.release()
        cv2.destroyAllWindows()
        self.save_daily_data()
        print("🔚 Tracking stopped and data saved")

# Usage example
if __name__ == "__main__":
    # Replace with your trained YOLOv8n drone model path
    MODEL_PATH = "path/to/your/drone_model.pt"  # Change this to your model path
    
    # Initialize drone tracker
    tracker = DroneTracker(MODEL_PATH, confidence_threshold=0.5)
    
    # Start webcam tracking
    try:
        tracker.run_webcam_tracking()
    except KeyboardInterrupt:
        print("\n🛑 Tracking interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
