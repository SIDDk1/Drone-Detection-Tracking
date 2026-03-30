from ultralytics import YOLO

model = YOLO("yolov8n.pt")

results = model.predict(source = "0", show = True)

for r in results:
    print(r.boxes)

print(results)