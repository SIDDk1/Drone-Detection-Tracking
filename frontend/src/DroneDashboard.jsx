import React, { useState } from 'react';
import './DroneDashboard.css';

const detections = [
  {
    droneId: 'DRN-001',
    duration: '15s',
    startTime: '2025-06-08 01:05:34',
    confidence: 0.759,
  },
  {
    droneId: 'DRN-002',
    duration: '12s',
    startTime: '2025-06-08 01:05:35',
    confidence: 0.891,
  },
  {
    droneId: 'DRN-003',
    duration: '10s',
    startTime: '2025-06-08 01:05:35',
    confidence: 0.725,
  },
  {
    droneId: 'DRN-004',
    duration: '20s',
    startTime: '2025-06-08 01:05:34',
    confidence: 0.509,
  },
  {
    droneId: 'DRN-005',
    duration: '8s',
    startTime: '2025-06-08 01:05:36',
    confidence: 0.777,
  },
];

function DroneDashboard() {
  const [selectedDrone, setSelectedDrone] = useState(null);

  const openGraphPopup = (drone) => {
    setSelectedDrone(drone);
  };

  const closeGraphPopup = () => {
    setSelectedDrone(null);
  };

  return (
    <div className="dashboard-container">
      <h1 className='d-dashboard'>Drone Detection System Dashboard</h1>
      <br />

      <div className="top-section">
        <div className="system-metrics">
          <h3>System Metrics</h3>
          <p>Total Detections: 85</p>
          <p>True Positives: 70</p>
          <p style={{ color: 'red' }}>False Positives: 15</p>
          <p>Average Processing Time: <span style={{ color: 'orange' }}>70.80 ms</span></p>
          <p>Sensor Uptime:</p>
          <ul>
            <li>RF Sensor: 4.25 s</li>
            <li>LIDAR Sensor: 8.50 s</li>
            <li>Camera Sensor: 12.75 s</li>
            <li>Radar Sensor: 17.00 s</li>
          </ul>
          <p>System Uptime: 12 minutes</p>
        </div>
      </div>

      <div className="buttons">
        <button className="green">System Online</button>
        <button className="yellow">Pause System</button>
        <button className="red">Clear Detections</button>
      </div>

      <div className="detections-table">
        <h3>Real-time Detections</h3>
        <br />
        <table>
          <thead>
            <tr>
              <th>Drone ID</th>
              <th>Graph</th>
              <th>Duration</th>
              <th>Start Time</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {detections.map((det, index) => (
              <tr key={index}>
                <td>{det.droneId}</td>
                <td>
                  <button onClick={() => window.open(`/graph.html?droneId=${det.droneId}`, '_blank')}>Map</button>
                </td>
                <td>{det.duration}</td>
                <td>{det.startTime}</td>
                <td>{det.confidence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedDrone && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h2>Graph for {selectedDrone.droneId}</h2>
            {/* Placeholder image for matplotlib graph */}
            <img
              src="https://via.placeholder.com/500x300.png?text=Matplotlib+Graph+Here"
              alt="Graph"
            />
            <br /><br />
            <button onClick={closeGraphPopup}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default DroneDashboard;
