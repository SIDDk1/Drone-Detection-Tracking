import React, { useState, useRef, useEffect } from 'react';

function VideoUploader() {
  const [videoSrc, setVideoSrc] = useState(null);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [error, setError] = useState(null);
  const [availableCameras, setAvailableCameras] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState('');
  const videoRef = useRef(null);

  // Get available cameras
  useEffect(() => {
    const getCameras = async () => {
      try {
        await navigator.mediaDevices.getUserMedia({ video: true });

        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter((d) => d.kind === 'videoinput');

        setAvailableCameras(videoDevices);
        if (videoDevices.length > 0) {
          setSelectedCamera(videoDevices[0].deviceId);
        }
      } catch (err) {
        console.error('Camera access error:', err);
        setError('Could not access cameras: ' + err.message);
      }
    };

    getCameras();
  }, []);

  const startCamera = async () => {
    try {
      if (!selectedCamera) {
        setError('No camera selected');
        return;
      }

      const constraints = {
        video: {
          deviceId: selectedCamera ? { exact: selectedCamera } : true,
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 840 },
        },
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current.play().catch((e) => console.error('Play error:', e));
        };
      }

      setIsCameraOn(true);
      setError(null);
    } catch (err) {
      console.error('Camera error:', err);
      setError('Camera error: ' + err.message);
    }
  };

  const stopCamera = () => {
    const videoElement = videoRef.current;
    if (videoElement && videoElement.srcObject) {
      const stream = videoElement.srcObject;
      stream.getTracks().forEach((track) => track.stop());
      videoElement.srcObject = null;
    }

    setIsCameraOn(false);
  };

  useEffect(() => {
    return () => {
      stopCamera();
      if (videoSrc) URL.revokeObjectURL(videoSrc);
    };
  }, []);

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h2 style={{ color: 'white', display: 'flex', justifyContent: 'center' }}>
        REAL TIME DETECTION
      </h2>

      <div style={{ margin: '20px 0' }}>
        {availableCameras.length > 0 && (
          <select
            value={selectedCamera}
            onChange={(e) => setSelectedCamera(e.target.value)}
            style={{ padding: '8px', marginRight: '10px' }}
          >
            {availableCameras.map((camera) => (
              <option key={camera.deviceId} value={camera.deviceId}>
                {camera.label || `Camera ${camera.deviceId}`}
              </option>
            ))}
          </select>
        )}

        <button onClick={isCameraOn ? stopCamera : startCamera} style={{ padding: '8px 16px' }}>
          {isCameraOn ? 'Stop Camera' : 'Start Camera'}
        </button>
      </div>

      {error && (
        <div style={{ color: 'red', margin: '10px 0', padding: '10px', background: '#ffecec' }}>
          {error}
          {error.includes('permission') && (
            <p>Please allow camera access in your browser settings and refresh the page.</p>
          )}
        </div>
      )}

      <div
        style={{
          width: '100%',
          height: '500px',
          backgroundColor: '#000',
          position: 'relative',
          margin: '20px 0',
        }}
      >
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            transform: 'scaleX(-1)', // Mirror effect
          }}
        />

        {isCameraOn && !videoRef.current?.srcObject?.active && (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              color: 'white',
            }}
          >
            Camera is loading...
          </div>
        )}
      </div>
    </div>
  );
}

export default VideoUploader;
