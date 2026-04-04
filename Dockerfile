FROM python:3.9-slim

# OpenCV / headless GUI deps (Bookworm+ dropped libgl1-mesa-glx; use libgl1)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user (Required by Hugging Face Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Copy backend files and set permissions
COPY --chown=user backend/ $HOME/app/
# Copy the video file to the parent directory so `../` paths resolve correctly
COPY --chown=user V_DRONE_FIRST_4_MIN.mp4 $HOME/V_DRONE_FIRST_4_MIN.mp4

# Expose Hugging Face default port
EXPOSE 7860

# Start FastAPI server on port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
