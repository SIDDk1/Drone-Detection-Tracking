import React, { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Grid,
  Typography,
  Paper,
  AppBar,
  Toolbar,
  IconButton
} from '@mui/material'
import { Videocam, Dashboard } from '@mui/icons-material'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'

import VideoFeed from './components/VideoFeed'
import ControlPanel from './components/ControlPanel'
import DetectionTable from './components/DetectionTable'
import DroneMap from './components/DroneMap'
import Notifications from './components/Notifications'
import useWebSocket from './hooks/useWebSocket'
import { getCameraStatus, getTodayDetections } from './services/api'

import './App.css'

function App() {
  const [cameraStatus, setCameraStatus] = useState({
    is_running: false,
    message: '',
    total_detections_today: 0
  })
  const [detections, setDetections] = useState([])
  const [loading, setLoading] = useState(true)

  // WebSocket connection
  const { lastMessage, sendMessage } = useWebSocket('ws://localhost:8000/ws')

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage.data)
        console.log('WebSocket message:', data)
        
        switch (data.event) {
          case 'camera_started':
          case 'camera_stopped':
          case 'status_update':
            setCameraStatus({
              is_running: data.is_running,
              message: data.message,
              total_detections_today: data.total_detections_today
            })
            break
          case 'new_drone':
            // Refresh detections when new drone is detected
            loadDetections()
            break
          default:
            break
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }
  }, [lastMessage])

  const loadCameraStatus = async () => {
    try {
      const status = await getCameraStatus()
      setCameraStatus(status)
    } catch (error) {
      console.error('Error loading camera status:', error)
    }
  }

  const loadDetections = async () => {
    try {
      setLoading(true)
      const data = await getTodayDetections()
      setDetections(data)
    } catch (error) {
      console.error('Error loading detections:', error)
    } finally {
      setLoading(false)
    }
  }

  // Load initial data
  useEffect(() => {
    loadCameraStatus()
    loadDetections()
  }, [])

  // Refresh detections every 30 seconds
  useEffect(() => {
    const interval = setInterval(loadDetections, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static" sx={{ mb: 3 }}>
        <Toolbar>
          <IconButton
            size="large"
            edge="start"
            color="inherit"
            aria-label="drone"
            sx={{ mr: 2 }}
          >
            <Videocam />
          </IconButton>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Drone Tracking Dashboard
          </Typography>
          <Typography variant="body2" sx={{ mr: 2 }}>
            Today: {cameraStatus.total_detections_today} detections
          </Typography>
          <IconButton
            size="large"
            color="inherit"
            aria-label="dashboard"
          >
            <Dashboard />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl">
        <Grid container spacing={3}>
          {/* Control Panel and Video Feed */}
          <Grid item xs={12} lg={8}>
            <Paper elevation={3} sx={{ p: 2, mb: 3 }}>
              <ControlPanel 
                cameraStatus={cameraStatus}
                onStatusChange={loadCameraStatus}
              />
            </Paper>
            
            <Paper elevation={3} sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Live Video Feed
              </Typography>
              <VideoFeed cameraStatus={cameraStatus} />
            </Paper>
          </Grid>

          {/* Detection Map */}
          <Grid item xs={12} lg={4}>
            <Paper elevation={3} sx={{ p: 2, height: 'fit-content' }}>
              <Typography variant="h6" gutterBottom>
                Detection Map
              </Typography>
              <DroneMap detections={detections} />
            </Paper>
          </Grid>

          {/* Detection Table */}
          <Grid item xs={12}>
            <Paper elevation={3} sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Today's Detections
              </Typography>
              <DetectionTable 
                detections={detections} 
                loading={loading}
                onRefresh={loadDetections}
              />
            </Paper>
          </Grid>
        </Grid>
      </Container>

      {/* Notifications */}
      <Notifications />
      
      {/* Toast Container */}
      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />
    </Box>
  )
}

export default App