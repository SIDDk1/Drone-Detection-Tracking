import React, { useEffect } from 'react'
import { toast } from 'react-toastify'
import { Box } from '@mui/material'
import useWebSocket from '../hooks/useWebSocket'
import { getWebSocketUrl } from '../services/api'

const Notifications = () => {
  const { lastMessage, isConnected, connectionError } = useWebSocket(getWebSocketUrl(), {
    onOpen: () => {
      console.log('Notifications WebSocket connected')
      toast.info('🔗 Connected to real-time updates', {
        position: 'bottom-right',
        autoClose: 2000,
      })
    },
    onClose: () => {
      console.log('Notifications WebSocket disconnected')
    },
    onError: (error) => {
      console.error('Notifications WebSocket error:', error)
      toast.error('❌ Connection lost - retrying...', {
        position: 'bottom-right',
        autoClose: 3000,
      })
    },
    shouldReconnect: true,
    reconnectInterval: 3000,
    maxReconnectAttempts: 5,
  })

  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage.data)
        handleWebSocketMessage(data)
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }
  }, [lastMessage])

  const handleWebSocketMessage = (data) => {
    console.log('Received WebSocket message:', data)

    switch (data.event) {
      case 'new_drone':
        showNewDroneNotification(data)
        break
      
      case 'camera_started':
        toast.success('📹 Camera started successfully!', {
          position: 'top-right',
          autoClose: 3000,
          icon: '🚁',
        })
        break
      
      case 'camera_stopped':
        toast.info('⏹️ Camera stopped', {
          position: 'top-right',
          autoClose: 3000,
        })
        break
      
      case 'status_update':
        // Handle general status updates if needed
        break
      
      case 'pong':
        // Handle pong response to keep connection alive
        break
      
      default:
        console.log('Unknown WebSocket event:', data.event)
        break
    }
  }

  const showNewDroneNotification = (data) => {
    const { daily_id, center, timestamp, confidence } = data
    
    // Create notification content
    const notificationContent = (
      <Box>
        <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
          🚁 New Drone Detected!
        </div>
        <div>ID: #{daily_id}</div>
        {center && (
          <div>Position: ({center[0]}, {center[1]})</div>
        )}
        {confidence && (
          <div>Confidence: {(confidence * 100).toFixed(1)}%</div>
        )}
        <div style={{ fontSize: '0.875rem', color: '#666', marginTop: 4 }}>
          {new Date(timestamp).toLocaleTimeString()}
        </div>
      </Box>
    )

    // Show toast notification
    toast.success(notificationContent, {
      position: 'top-right',
      autoClose: 8000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
      style: {
        background: 'linear-gradient(90deg, #28a745 0%, #20c997 100%)',
        color: 'white',
      },
      progressStyle: {
        background: 'rgba(255, 255, 255, 0.3)',
      },
    })

    // Play notification sound (optional)
    playNotificationSound()
    
    // Show desktop notification if permission granted
    showDesktopNotification(daily_id, center, timestamp)
  }

  const playNotificationSound = () => {
    try {
      // Create audio context for notification sound
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      
      // Create a simple beep sound
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()
      
      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)
      
      oscillator.frequency.value = 800
      oscillator.type = 'sine'
      
      gainNode.gain.setValueAtTime(0.1, audioContext.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3)
      
      oscillator.start(audioContext.currentTime)
      oscillator.stop(audioContext.currentTime + 0.3)
    } catch (error) {
      console.log('Could not play notification sound:', error)
    }
  }

  const showDesktopNotification = (daily_id, center, timestamp) => {
    // Check if notifications are supported and permission is granted
    if ('Notification' in window && Notification.permission === 'granted') {
      const notification = new Notification('🚁 New Drone Detected!', {
        body: `Drone #${daily_id} detected at position (${center?.[0] || 0}, ${center?.[1] || 0})`,
        icon: '/drone-icon.png', // Add a drone icon to your public folder
        badge: '/drone-badge.png',
        tag: `drone-${daily_id}`, // Prevent duplicate notifications
        timestamp: new Date(timestamp).getTime(),
        requireInteraction: false,
        silent: false,
      })

      // Auto-close after 5 seconds
      setTimeout(() => {
        notification.close()
      }, 5000)

      // Handle click event
      notification.onclick = () => {
        window.focus()
        notification.close()
      }
    }
  }

  // Request notification permission on component mount
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          toast.info('🔔 Desktop notifications enabled', {
            position: 'bottom-right',
            autoClose: 3000,
          })
        }
      })
    }
  }, [])

  // Show connection status updates
  useEffect(() => {
    if (connectionError) {
      toast.error('🔌 Real-time connection lost - some features may not work', {
        position: 'bottom-right',
        autoClose: 5000,
      })
    }
  }, [connectionError])

  // This component doesn't render anything visible
  return null
}

export default Notifications