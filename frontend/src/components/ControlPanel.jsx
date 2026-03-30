import React, { useState } from 'react'
import {
  Box,
  Button,
  Typography,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Chip,
  Divider
} from '@mui/material'
import {
  PlayArrow,
  Stop,
  Videocam,
  VideocamOff,
  TrendingUp
} from '@mui/icons-material'
import { toast } from 'react-toastify'
import { startCamera, stopCamera } from '../services/api'

const ControlPanel = ({ cameraStatus, onStatusChange }) => {
  const [loading, setLoading] = useState(false)
  const [operation, setOperation] = useState(null) // 'start' or 'stop'

  const handleStartCamera = async () => {
    setLoading(true)
    setOperation('start')
    
    try {
      const response = await startCamera()
      toast.success(response.message || 'Camera started successfully', {
        icon: '🚁'
      })
      
      // Refresh camera status
      if (onStatusChange) {
        onStatusChange()
      }
    } catch (error) {
      console.error('Error starting camera:', error)
      toast.error(error.message || 'Failed to start camera', {
        icon: '❌'
      })
    } finally {
      setLoading(false)
      setOperation(null)
    }
  }

  const handleStopCamera = async () => {
    setLoading(true)
    setOperation('stop')
    
    try {
      const response = await stopCamera()
      toast.success(response.message || 'Camera stopped successfully', {
        icon: '⏹️'
      })
      
      // Refresh camera status
      if (onStatusChange) {
        onStatusChange()
      }
    } catch (error) {
      console.error('Error stopping camera:', error)
      toast.error(error.message || 'Failed to stop camera', {
        icon: '❌'
      })
    } finally {
      setLoading(false)
      setOperation(null)
    }
  }

  const getStatusColor = () => {
    return cameraStatus.is_running ? 'success' : 'error'
  }

  const getStatusIcon = () => {
    if (loading) {
      return <CircularProgress size={20} />
    }
    return cameraStatus.is_running ? <Videocam /> : <VideocamOff />
  }

  const getStatusText = () => {
    if (loading) {
      return operation === 'start' ? 'Starting camera...' : 'Stopping camera...'
    }
    return cameraStatus.is_running ? 'Camera is running' : 'Camera is stopped'
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
        Camera Control Panel
      </Typography>

      <Grid container spacing={3}>
        {/* Status Card */}
        <Grid item xs={12} md={6}>
          <Card elevation={2}>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                {getStatusIcon()}
                <Typography variant="h6">
                  System Status
                </Typography>
              </Box>
              
              <Chip
                label={getStatusText()}
                color={loading ? 'default' : getStatusColor()}
                variant="outlined"
                sx={{ mb: 2, fontWeight: 'bold' }}
              />
              
              <Typography variant="body2" color="text.secondary">
                {cameraStatus.message}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Statistics Card */}
        <Grid item xs={12} md={6}>
          <Card elevation={2}>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <TrendingUp color="primary" />
                <Typography variant="h6">
                  Detection Statistics
                </Typography>
              </Box>
              
              <Typography variant="h4" color="primary" sx={{ mb: 1 }}>
                {cameraStatus.total_detections_today}
              </Typography>
              
              <Typography variant="body2" color="text.secondary">
                Total drones detected today
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Control Buttons */}
        <Grid item xs={12}>
          <Divider sx={{ my: 2 }} />
          
          <Box 
            display="flex" 
            gap={2} 
            justifyContent="center"
            flexWrap="wrap"
          >
            <Button
              variant="contained"
              color="success"
              size="large"
              startIcon={loading && operation === 'start' ? <CircularProgress size={20} /> : <PlayArrow />}
              onClick={handleStartCamera}
              disabled={loading || cameraStatus.is_running}
              sx={{ minWidth: 140 }}
            >
              {loading && operation === 'start' ? 'Starting...' : 'Start Camera'}
            </Button>

            <Button
              variant="contained"
              color="error"
              size="large"
              startIcon={loading && operation === 'stop' ? <CircularProgress size={20} /> : <Stop />}
              onClick={handleStopCamera}
              disabled={loading || !cameraStatus.is_running}
              sx={{ minWidth: 140 }}
            >
              {loading && operation === 'stop' ? 'Stopping...' : 'Stop Camera'}
            </Button>
          </Box>

          {/* Help Text */}
          <Typography 
            variant="caption" 
            color="text.secondary" 
            sx={{ mt: 2, display: 'block', textAlign: 'center' }}
          >
            Click "Start Camera" to begin real-time drone detection and tracking
          </Typography>
        </Grid>
      </Grid>

      {/* Additional Info */}
      <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
        <Typography variant="body2" color="text.secondary">
          <strong>Instructions:</strong>
        </Typography>
        <Typography variant="body2" color="text.secondary" component="div">
          <ul style={{ paddingLeft: '20px', margin: '8px 0' }}>
            <li>Ensure your camera is connected and accessible</li>
            <li>Click "Start Camera" to begin drone detection</li>
            <li>New drone detections will appear as notifications</li>
            <li>View live detection data in the table below</li>
            <li>Check the map for drone location visualization</li>
          </ul>
        </Typography>
      </Box>
    </Box>
  )
}

export default ControlPanel