import cv2
import numpy as np
import datetime
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import threading
import json
import os

class DroneTracker:
    def __init__(self, model_path, confidence_threshold=0.5):
        # Initialize YOLO model
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        
        # Initialize DeepSORT tracker
        self.tracker = DeepSort(max_age=20, n_init=2)
        
        # Tracking variables
        self.daily_id_counter = 0
        self.tracked_objects = {}  # {track_id: {'daily_id': int, 'start_time': datetime, 'end_time': datetime}}
        self.current_date = datetime.date.today()
        self.first_detection_alert_shown = False
        
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
                    # Load tracked objects but reset active tracking
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
            
            # Optional: Add sound alert (uncomment if you have playsound installed)
            # threading.Thread(target=self.play_alert_sound).start()
            
    def play_alert_sound(self):
        """Play alert sound (optional)"""
        try:
            # You can add a sound file here
            # playsound('alert.wav')
            print("🔊 Alert sound would play here")
        except:
            pass
            
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
                    # Get confidence and class
                    confidence = float(box.conf[0])
                    
                    # Only process if confidence is above threshold
                    if confidence >= self.confidence_threshold:
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        
                        # Convert to format expected by DeepSORT
                        detection = ([x1, y1, x2-x1, y2-y1], confidence, 'drone')
                        detections.append(detection)
                        
        return detections
        
    def update_tracking_info(self, track_id, bbox):
        """Update tracking information for each drone"""
        current_time = datetime.datetime.now()
        
        if track_id not in self.tracked_objects:
            # New drone detected - assign daily ID
            self.daily_id_counter += 1
            self.tracked_objects[track_id] = {
                'daily_id': self.daily_id_counter,
                'start_time': current_time,
                'end_time': current_time,
                'last_seen': current_time
            }
            
            # Show first detection alert
            if self.daily_id_counter == 1:
                self.show_first_detection_alert()
                
            print(f"🆕 New drone detected - Daily ID: {self.daily_id_counter}")
            print(f"   Start Time: {current_time.strftime('%H:%M:%S')}")
            
        else:
            # Update existing drone info
            self.tracked_objects[track_id]['end_time'] = current_time
            self.tracked_objects[track_id]['last_seen'] = current_time
            
    def draw_tracking_info(self, frame, tracks):
        """Draw bounding boxes and tracking information on frame"""
        for track in tracks:
            track_id = track.track_id
            bbox = track.to_ltwh()  # left, top, width, height
            
            # Convert to x1, y1, x2, y2 format
            x1 = int(bbox[0])
            y1 = int(bbox[1])
            x2 = int(bbox[0] + bbox[2])
            y2 = int(bbox[1] + bbox[3])
            
            # Update tracking info
            self.update_tracking_info(track_id, [x1, y1, x2, y2])
            
            # Get center coordinates
            center_x, center_y = self.get_bounding_box_center([x1, y1, x2, y2])
            
            # Get daily ID
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
            
            # Position text above bounding box
            cv2.putText(frame, info_text, (x1, y1-40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, time_text, (x1, y1-25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(frame, center_text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            # Print continuous tracking info to console
            print(f"🎯 Drone ID: {daily_id} | Center: ({center_x}, {center_y}) | "
                  f"Duration: {str(duration).split('.')[0]} | "
                  f"Time: {current_time.strftime('%H:%M:%S')}")
                  
    def cleanup_inactive_tracks(self):
        """Remove tracks that haven't been seen for a while"""
        current_time = datetime.datetime.now()
        inactive_threshold = datetime.timedelta(seconds=5)  # 5 seconds
        
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
        # Initialize webcam
        cap = cv2.VideoCapture(0)  # Use 0 for default webcam
        
        # Set webcam properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        print("🚁 Starting drone tracking...")
        print(f"📅 Date: {self.current_date}")
        print("Press 'q' to quit")
        
        while True:
            # Check if date has changed (for daily reset)
            if datetime.date.today() != self.current_date:
                self.save_daily_data()
                self.current_date = datetime.date.today()
                self.daily_id_counter = 0
                self.tracked_objects = {}
                self.first_detection_alert_shown = False
                print(f"📅 New day started: {self.current_date}")
                
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame from webcam")
                break
                
            # Run YOLO detection
            results = self.model(frame, verbose=False)
            
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
            
            # Display frame
            cv2.imshow('Drone Tracking', frame)
            
            # Break on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        self.save_daily_data()
        print("🔚 Tracking stopped and data saved")

# Usage example
if __name__ == "__main__":
    # Replace 'path/to/your/drone_model.pt' with your trained YOLOv8n drone model path
    MODEL_PATH = "best.pt"  # Change this to your model path
    
    # Initialize drone tracker
    tracker = DroneTracker(MODEL_PATH, confidence_threshold=0.5)
    
    # Start webcam tracking
    try:
        tracker.run_webcam_tracking()
    except KeyboardInterrupt:
        print("\n🛑 Tracking interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
