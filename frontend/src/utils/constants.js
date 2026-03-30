// API Base URLs
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'

// API Endpoints
export const API_ENDPOINTS = {
  VIDEO: '/video',
  CAMERA_CONTROL: '/camera',
  CAMERA_STATUS: '/camera/status',
  DETECTIONS_TODAY: '/detections/today',
  DETECTIONS_ALL: '/detections',
  WEBSOCKET: '/ws',
  HEALTH: '/health'
}

// WebSocket Events
export const WS_EVENTS = {
  CAMERA_STARTED: 'camera_started',
  CAMERA_STOPPED: 'camera_stopped',
  NEW_DRONE: 'new_drone',
  STATUS_UPDATE: 'status_update',
  PING: 'ping',
  PONG: 'pong'
}

// Camera Actions
export const CAMERA_ACTIONS = {
  START: 'start',
  STOP: 'stop'
}

// Map Configuration
export const MAP_CONFIG = {
  DEFAULT_CENTER: [40.7128, -74.0060], // New York City
  DEFAULT_ZOOM: 13,
  MAX_ZOOM: 18,
  MIN_ZOOM: 1
}

// Toast Notification Settings
export const TOAST_CONFIG = {
  SUCCESS: {
    position: 'top-right',
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    type: 'success'
  },
  ERROR: {
    position: 'top-right',
    autoClose: 5000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    type: 'error'
  },
  WARNING: {
    position: 'top-right',
    autoClose: 4000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    type: 'warning'
  },
  INFO: {
    position: 'top-right',
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    type: 'info'
  }
}

// Table Configuration
export const TABLE_CONFIG = {
  ROWS_PER_PAGE: 10,
  ROWS_PER_PAGE_OPTIONS: [5, 10, 25, 50],
  REFRESH_INTERVAL: 30000 // 30 seconds
}

// Video Feed Configuration
export const VIDEO_CONFIG = {
  RETRY_INTERVAL: 3000, // 3 seconds
  MAX_RETRIES: 5,
  CONNECTION_TIMEOUT: 10000 // 10 seconds
}

// Date/Time Formats
export const DATE_FORMATS = {
  DISPLAY: 'MMM dd, yyyy HH:mm:ss',
  SHORT: 'HH:mm:ss',
  DATE_ONLY: 'MMM dd, yyyy',
  ISO: "yyyy-MM-dd'T'HH:mm:ss"
}

// Colors
export const COLORS = {
  SUCCESS: '#28a745',
  ERROR: '#dc3545',
  WARNING: '#ffc107',
  INFO: '#17a2b8',
  PRIMARY: '#007bff',
  SECONDARY: '#6c757d'
}

// Drone Detection Colors for Map
export const DETECTION_COLORS = {
  RECENT: '#ff0000',      // Red for recent detections
  MEDIUM: '#ff7700',      // Orange for medium-age detections
  OLD: '#0077ff'          // Blue for old detections
}

// Timeframes for detection coloring (in minutes)
export const DETECTION_TIMEFRAMES = {
  RECENT: 5,    // Last 5 minutes
  MEDIUM: 30    // Last 30 minutes
}