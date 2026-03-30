import React, { useState, useMemo } from 'react'
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Paper,
  Typography,
  IconButton,
  Chip,
  Button,
  CircularProgress,
  Tooltip,
  TableSortLabel
} from '@mui/material'
import {
  Refresh,
  Delete,
  LocationOn,
  Schedule
} from '@mui/icons-material'
import { format, parseISO, differenceInMinutes } from 'date-fns'

const DetectionTable = ({ detections, loading, onRefresh, onDeleteDetection }) => {
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [orderBy, setOrderBy] = useState('start_time')
  const [order, setOrder] = useState('desc')

  // Sort detections
  const sortedDetections = useMemo(() => {
    return [...detections].sort((a, b) => {
      let aValue = a[orderBy]
      let bValue = b[orderBy]

      // Handle date sorting
      if (orderBy === 'start_time' || orderBy === 'end_time') {
        aValue = new Date(aValue).getTime()
        bValue = new Date(bValue).getTime()
      }

      if (order === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0
      }
    })
  }, [detections, orderBy, order])

  // Paginated detections
  const paginatedDetections = useMemo(() => {
    const startIndex = page * rowsPerPage
    return sortedDetections.slice(startIndex, startIndex + rowsPerPage)
  }, [sortedDetections, page, rowsPerPage])

  const handleSort = (property) => {
    const isAsc = orderBy === property && order === 'asc'
    setOrder(isAsc ? 'desc' : 'asc')
    setOrderBy(property)
  }

  const handleChangePage = (event, newPage) => {
    setPage(newPage)
  }

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10))
    setPage(0)
  }

  const formatDateTime = (dateString) => {
    try {
      return format(parseISO(dateString), 'MMM dd, yyyy HH:mm:ss')
    } catch (error) {
      return dateString
    }
  }

  const formatTime = (dateString) => {
    try {
      return format(parseISO(dateString), 'HH:mm:ss')
    } catch (error) {
      return dateString
    }
  }

  const getDurationMinutes = (startTime, endTime) => {
    try {
      if (!endTime) return 0
      return differenceInMinutes(parseISO(endTime), parseISO(startTime))
    } catch (error) {
      return 0
    }
  }

  const getRecentnessColor = (startTime) => {
    try {
      const minutes = differenceInMinutes(new Date(), parseISO(startTime))
      if (minutes < 5) return 'error' // Red for very recent (< 5 min)
      if (minutes < 30) return 'warning' // Orange for recent (< 30 min)
      return 'default' // Default for older
    } catch (error) {
      return 'default'
    }
  }

  if (loading && detections.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" p={4}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading detections...</Typography>
      </Box>
    )
  }

  return (
    <Box>
      {/* Header with refresh button */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="body2" color="text.secondary">
          {detections.length} detection{detections.length !== 1 ? 's' : ''} found
        </Typography>
        
        <Button
          startIcon={loading ? <CircularProgress size={20} /> : <Refresh />}
          onClick={onRefresh}
          disabled={loading}
          size="small"
        >
          Refresh
        </Button>
      </Box>

      {detections.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No detections today
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Start the camera to begin detecting drones
          </Typography>
        </Paper>
      ) : (
        <>
          <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>
                    <TableSortLabel
                      active={orderBy === 'daily_id'}
                      direction={orderBy === 'daily_id' ? order : 'asc'}
                      onClick={() => handleSort('daily_id')}
                    >
                      Drone ID
                    </TableSortLabel>
                  </TableCell>
                  
                  <TableCell>
                    <TableSortLabel
                      active={orderBy === 'start_time'}
                      direction={orderBy === 'start_time' ? order : 'asc'}
                      onClick={() => handleSort('start_time')}
                    >
                      Detection Time
                    </TableSortLabel>
                  </TableCell>
                  
                  <TableCell>
                    <TableSortLabel
                      active={orderBy === 'center_x'}
                      direction={orderBy === 'center_x' ? order : 'asc'}
                      onClick={() => handleSort('center_x')}
                    >
                      Center Position
                    </TableSortLabel>
                  </TableCell>
                  
                  <TableCell>Duration</TableCell>
                  
                  <TableCell>Status</TableCell>
                  
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              
              <TableBody>
                {paginatedDetections.map((detection) => (
                  <TableRow 
                    key={detection.id} 
                    hover
                    sx={{ '&:nth-of-type(odd)': { backgroundColor: 'action.hover' } }}
                  >
                    <TableCell>
                      <Chip
                        label={`#${detection.daily_id}`}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    </TableCell>
                    
                    <TableCell>
                      <Box>
                        <Typography variant="body2">
                          {formatDateTime(detection.start_time)}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {formatTime(detection.start_time)}
                        </Typography>
                      </Box>
                    </TableCell>
                    
                    <TableCell>
                      <Box display="flex" alignItems="center" gap={1}>
                        <LocationOn fontSize="small" color="action" />
                        <Typography variant="body2">
                          ({detection.center_x}, {detection.center_y})
                        </Typography>
                      </Box>
                    </TableCell>
                    
                    <TableCell>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Schedule fontSize="small" color="action" />
                        <Typography variant="body2">
                          {detection.duration_seconds 
                            ? `${Math.round(detection.duration_seconds)}s`
                            : getDurationMinutes(detection.start_time, detection.end_time) > 0
                            ? `${getDurationMinutes(detection.start_time, detection.end_time)}m`
                            : 'Active'
                          }
                        </Typography>
                      </Box>
                    </TableCell>
                    
                    <TableCell>
                      <Chip
                        label={
                          differenceInMinutes(new Date(), parseISO(detection.start_time)) < 5
                            ? 'Recent'
                            : differenceInMinutes(new Date(), parseISO(detection.start_time)) < 30
                            ? 'Active'
                            : 'Completed'
                        }
                        size="small"
                        color={getRecentnessColor(detection.start_time)}
                      />
                    </TableCell>
                    
                    <TableCell>
                      {onDeleteDetection && (
                        <Tooltip title="Delete detection">
                          <IconButton
                            size="small"
                            onClick={() => onDeleteDetection(detection.id)}
                            color="error"
                          >
                            <Delete fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Pagination */}
          <TablePagination
            rowsPerPageOptions={[5, 10, 25, 50]}
            component="div"
            count={detections.length}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
          />
        </>
      )}
    </Box>
  )
}

export default DetectionTable