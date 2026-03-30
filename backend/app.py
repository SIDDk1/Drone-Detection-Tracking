from fastapi import FastAPI, UploadFile, File, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from celery import Celery
import os
import uuid
import redis
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

celery_app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

redis_client = redis.Redis(host='localhost', port=6379, db=0)

UPLOAD_DIR = "../data/uploaded_videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload/")
async def upload_video(file: UploadFile = File(...)):
    if not file.filename.endswith(('.mp4', '.avi', '.mov')):
        raise HTTPException(status_code=400, detail="Unsupported file format")

    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.mp4")

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    task = celery_app.send_task("process_video", args=[file_path, file_id])

    return {"task_id": task.id, "file_id": file_id}

@app.get("/result/{task_id}")
def get_result(task_id: str):
    task = celery_app.AsyncResult(task_id)
    return {"state": task.state, "result": task.result}

@app.websocket("/ws/drone")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    pubsub = redis_client.pubsub()
    pubsub.subscribe("drone_detection")

    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                await websocket.send_json(data)
    finally:
        pubsub.unsubscribe()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)