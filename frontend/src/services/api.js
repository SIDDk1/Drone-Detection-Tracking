import axios from 'axios'
import { API_BASE_URL, API_ENDPOINTS, CAMERA_ACTIONS } from '../utils/constants'

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.status, error.message)
    return Promise.reject(error)
  }
)

// Camera Control API
export const startCamera = async () => {
  try {
    const response = await api.post(`${API_ENDPOINTS.CAMERA_CONTROL}/${CAMERA_ACTIONS.START}`)
    return response.data
  } catch (error) {
    throw new Error(`Failed to start camera: ${error.response?.data?.detail || error.message}`)
  }
}

export const stopCamera = async () => {
  try {
    const response = await api.post(`${API_ENDPOINTS.CAMERA_CONTROL}/${CAMERA_ACTIONS.STOP}`)
    return response.data
  } catch (error) {
    throw new Error(`Failed to stop camera: ${error.response?.data?.detail || error.message}`)
  }
}

export const getCameraStatus = async () => {
  try {
    const response = await api.get(API_ENDPOINTS.CAMERA_STATUS)
    return response.data
  } catch (error) {
    throw new Error(`Failed to get camera status: ${error.response?.data?.detail || error.message}`)
  }
}

// Detection API
export const getTodayDetections = async () => {
  try {
    const response = await api.get(API_ENDPOINTS.DETECTIONS_TODAY)
    return response.data
  } catch (error) {
    throw new Error(`Failed to get today's detections: ${error.response?.data?.detail || error.message}`)
  }
}

export const getAllDetections = async (limit = 100, offset = 0) => {
  try {
    const response = await api.get(API_ENDPOINTS.DETECTIONS_ALL, {
      params: { limit, offset }
    })
    return response.data
  } catch (error) {
    throw new Error(`Failed to get detections: ${error.response?.data?.detail || error.message}`)
  }
}

export const getDetectionsByDate = async (date) => {
  try {
    const response = await api.get(`${API_ENDPOINTS.DETECTIONS_ALL}/date/${date}`)
    return response.data
  } catch (error) {
    throw new Error(`Failed to get detections for date ${date}: ${error.response?.data?.detail || error.message}`)
  }
}

export const deleteDetection = async (detectionId) => {
  try {
    const response = await api.delete(`${API_ENDPOINTS.DETECTIONS_ALL}/${detectionId}`)
    return response.data
  } catch (error) {
    throw new Error(`Failed to delete detection: ${error.response?.data?.detail || error.message}`)
  }
}

// Health Check API
export const getHealthStatus = async () => {
  try {
    const response = await api.get(API_ENDPOINTS.HEALTH)
    return response.data
  } catch (error) {
    throw new Error(`Failed to get health status: ${error.response?.data?.detail || error.message}`)
  }
}

// Utility function to get video stream URL
export const getVideoStreamUrl = () => {
  console.log("Fetching video stream URL")
  return `${API_BASE_URL}${API_ENDPOINTS.VIDEO}`
}

// Utility function to get WebSocket URL
export const getWebSocketUrl = () => {
  const wsProtocol = API_BASE_URL.startsWith('https') ? 'wss' : 'ws'
  const wsHost = API_BASE_URL.replace(/^https?:\/\//, '')
  return `${wsProtocol}://${wsHost}${API_ENDPOINTS.WEBSOCKET}`
}

// Error handling utility
export const handleApiError = (error) => {
  if (error.response) {
    // Server responded with error status
    return {
      type: 'server_error',
      status: error.response.status,
      message: error.response.data?.detail || error.response.statusText,
      data: error.response.data
    }
  } else if (error.request) {
    // Request was made but no response received
    return {
      type: 'network_error',
      message: 'Network error - please check your connection',
      data: null
    }
  } else {
    // Something else happened
    return {
      type: 'client_error',
      message: error.message,
      data: null
    }
  }
}

export default api