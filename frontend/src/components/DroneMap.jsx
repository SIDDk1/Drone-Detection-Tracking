import React, { useEffect, useState, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet'
import { Box, Typography, Chip, Alert, FormControlLabel, Switch } from '@mui/material'
import { LocationOn } from '@mui/icons-material'
import L from 'leaflet'
import { format, parseISO, differenceInMinutes } from 'date-fns'

// Fix for default markers in react-leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
})

// Custom drone icon
const createDroneIcon = (color = '#ff0000', size = 'small') => {
  const iconSize = size === 'large' ? 25 : size === 'medium' ? 20 : 15
  return L.divIcon({
    html: `<div style="
      background-color: ${color};
      width: ${iconSize}px;
      height: ${iconSize}px;
      border-radius: 50%;
      border: 2px solid white;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: ${iconSize - 8}px;
      color: white;
      font-weight: bold;
    ">🚁</div>`,
    className: 'custom-drone-icon',
    iconSize: [iconSize, iconSize],
    iconAnchor: [iconSize / 2, iconSize / 2],
    popupAnchor: [0, -iconSize / 2],
  })
}

const DroneMap = ({ detections }) => {
  const [showRecent, setShowRecent] = useState(true)
  const [showOld, setShowOld] = useState(true)
  const [mapCenter, setMapCenter] = useState([27.135304, 78.001874]) // Default to NYC

  // Process detections for map display
  const processedDetections = useMemo(() => {
    if (!detections || detections.length === 0) return []

    return detections.map(detection => {
      const minutesAgo = differenceInMinutes(new Date(), parseISO(detection.start_time))
      
      // Convert pixel coordinates to approximate lat/lng (this is a simple approximation)
      // In a real application, you would need proper coordinate transformation
      const lat = mapCenter[0] + (detection.center_y - 360) * 0.0001 // Approximate conversion
      const lng = mapCenter[1] + (detection.center_x - 640) * 0.0001 // Approximate conversion
      
      let color, size, category
      if (minutesAgo < 5) {
        color = '#ff0000' // Red for very recent
        size = 'large'
        category = 'recent'
      } else if (minutesAgo < 30) {
        color = '#ff7700' // Orange for recent
        size = 'medium'
        category = 'active'
      } else {
        color = '#0077ff' // Blue for old
        size = 'small'
        category = 'old'
      }

      return {
        ...detection,
        lat,
        lng,
        color,
        size,
        category,
        minutesAgo,
        formattedTime: format(parseISO(detection.start_time), 'HH:mm:ss'),
        formattedDate: format(parseISO(detection.start_time), 'MMM dd, yyyy')
      }
    })
  }, [detections, mapCenter])

  // Filter detections based on user preferences
  const filteredDetections = useMemo(() => {
    return processedDetections.filter(detection => {
      if (detection.category === 'recent' || detection.category === 'active') {
        return showRecent
      }
      return showOld
    })
  }, [processedDetections, showRecent, showOld])

  // Calculate map bounds to fit all markers
  const mapBounds = useMemo(() => {
    if (filteredDetections.length === 0) return null

    const lats = filteredDetections.map(d => d.lat)
    const lngs = filteredDetections.map(d => d.lng)
    
    return [
      [Math.min(...lats), Math.min(...lngs)],
      [Math.max(...lats), Math.max(...lngs)]
    ]
  }, [filteredDetections])

  const getCategoryStats = () => {
    const recent = processedDetections.filter(d => d.category === 'recent' || d.category === 'active').length
    const old = processedDetections.filter(d => d.category === 'old').length
    return { recent, old, total: processedDetections.length }
  }

  const stats = getCategoryStats()

  if (!detections || detections.length === 0) {
    return (
      <Box sx={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Box textAlign="center">
          <LocationOn sx={{ fontSize: 60, color: 'text.secondary' }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No detections to display
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Drone locations will appear here after detection
          </Typography>
        </Box>
      </Box>
    )
  }

  return (
    <Box>
      {/* Map Controls */}
      <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
        <Typography variant="subtitle2" gutterBottom>
          Map Settings
        </Typography>
        
        <Box display="flex" flexDirection="column" gap={1}>
          <FormControlLabel
            control={
              <Switch
                checked={showRecent}
                onChange={(e) => setShowRecent(e.target.checked)}
                size="small"
              />
            }
            label={
              <Box display="flex" alignItems="center" gap={1}>
                <span>Recent detections</span>
                <Chip size="small" label={stats.recent} color="error" />
              </Box>
            }
          />
          
          <FormControlLabel
            control={
              <Switch
                checked={showOld}
                onChange={(e) => setShowOld(e.target.checked)}
                size="small"
              />
            }
            label={
              <Box display="flex" alignItems="center" gap={1}>
                <span>Older detections</span>
                <Chip size="small" label={stats.old} />
              </Box>
            }
          />
        </Box>
      </Box>

      {/* Legend */}
      <Box display="flex" gap={2} mb={2} flexWrap="wrap">
        <Box display="flex" alignItems="center" gap={1}>
          <div style={{
            width: 12,
            height: 12,
            borderRadius: '50%',
            backgroundColor: '#ff0000'
          }} />
          <Typography variant="caption">Recent ({"<"}5 min)</Typography>
        </Box>
        
        <Box display="flex" alignItems="center" gap={1}>
          <div style={{
            width: 12,
            height: 12,
            borderRadius: '50%',
            backgroundColor: '#ff7700'
          }} />
          <Typography variant="caption">Active ({"<"}30 min)</Typography>
        </Box>
        
        <Box display="flex" alignItems="center" gap={1}>
          <div style={{
            width: 12,
            height: 12,
            borderRadius: '50%',
            backgroundColor: '#0077ff'
          }} />
          <Typography variant="caption">Completed ({">"}30 min)</Typography>
        </Box>
      </Box>

      {filteredDetections.length === 0 ? (
        <Alert severity="info">
          No detections match the current filter settings
        </Alert>
      ) : (
        <>
          {/* Map */}
          <Box className="map-container" sx={{ height: 400, borderRadius: 2, overflow: 'hidden' }}>
            <MapContainer
              center={mapCenter}
              zoom={15}
              style={{ height: '100%', width: '100%' }}
              bounds={mapBounds}
              boundsOptions={{ padding: [20, 20] }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              />
              
              {filteredDetections.map((detection) => (
                <Marker
                  key={detection.id}
                  position={[detection.lat, detection.lng]}
                  icon={createDroneIcon(detection.color, detection.size)}
                >
                  <Popup>
                    <Box sx={{ minWidth: 200 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        🚁 Drone #{detection.daily_id}
                      </Typography>
                      
                      <Typography variant="body2" gutterBottom>
                        <strong>Detected:</strong> {detection.formattedDate}
                      </Typography>
                      
                      <Typography variant="body2" gutterBottom>
                        <strong>Time:</strong> {detection.formattedTime}
                      </Typography>
                      
                      <Typography variant="body2" gutterBottom>
                        <strong>Position:</strong> ({detection.center_x}, {detection.center_y})
                      </Typography>
                      
                      <Typography variant="body2" gutterBottom>
                        <strong>Duration:</strong> {detection.duration_seconds ? `${detection.duration_seconds}s` : 'N/A'}
                      </Typography>
                      
                      <Chip
                        size="small"
                        label={
                          detection.minutesAgo < 5
                            ? `${detection.minutesAgo}m ago (Recent)`
                            : detection.minutesAgo < 30
                            ? `${detection.minutesAgo}m ago (Active)`
                            : `${detection.minutesAgo}m ago (Completed)`
                        }
                        color={
                          detection.minutesAgo < 5
                            ? 'error'
                            : detection.minutesAgo < 30
                            ? 'warning'
                            : 'default'
                        }
                        sx={{ mt: 1 }}
                      />
                    </Box>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </Box>

          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Note: Coordinates are approximated from pixel positions. For accurate GPS mapping, integrate with a positioning system.
          </Typography>
        </>
      )}
    </Box>
  )
}

export default DroneMap