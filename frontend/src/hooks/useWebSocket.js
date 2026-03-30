import { useState, useEffect, useRef, useCallback } from 'react'

const useWebSocket = (url, options = {}) => {
  const [socket, setSocket] = useState(null)
  const [lastMessage, setLastMessage] = useState(null)
  const [readyState, setReadyState] = useState(0) // 0: CONNECTING, 1: OPEN, 2: CLOSING, 3: CLOSED
  const [connectionError, setConnectionError] = useState(null)
  const [retryCount, setRetryCount] = useState(0)
  
  const {
    onOpen = () => {},
    onClose = () => {},
    onMessage = () => {},
    onError = () => {},
    shouldReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    protocols = [],
  } = options

  const reconnectTimeoutRef = useRef(null)
  const shouldReconnectRef = useRef(shouldReconnect)
  const reconnectIntervalRef = useRef(reconnectInterval)
  const maxReconnectAttemptsRef = useRef(maxReconnectAttempts)

  // Update refs when options change
  useEffect(() => {
    shouldReconnectRef.current = shouldReconnect
  }, [shouldReconnect])

  useEffect(() => {
    reconnectIntervalRef.current = reconnectInterval
  }, [reconnectInterval])

  useEffect(() => {
    maxReconnectAttemptsRef.current = maxReconnectAttempts
  }, [maxReconnectAttempts])

  const connect = useCallback(() => {
    try {
      setConnectionError(null)
      const ws = new WebSocket(url, protocols)
      
      ws.onopen = (event) => {
        console.log('WebSocket connected:', url)
        setSocket(ws)
        setReadyState(1) // OPEN
        setRetryCount(0)
        setConnectionError(null)
        onOpen(event)
      }

      ws.onmessage = (event) => {
        setLastMessage(event)
        onMessage(event)
      }

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        setSocket(null)
        setReadyState(3) // CLOSED
        onClose(event)

        // Attempt to reconnect if enabled and not a normal closure
        if (
          shouldReconnectRef.current &&
          event.code !== 1000 &&
          retryCount < maxReconnectAttemptsRef.current
        ) {
          console.log(`Attempting to reconnect in ${reconnectIntervalRef.current}ms (attempt ${retryCount + 1}/${maxReconnectAttemptsRef.current})`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            setRetryCount(prev => prev + 1)
            connect()
          }, reconnectIntervalRef.current)
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        const error = new Error('WebSocket connection error')
        setConnectionError(error)
        onError(error)
      }

      setReadyState(0) // CONNECTING

    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      setConnectionError(error)
      onError(error)
    }
  }, [url, protocols, onOpen, onMessage, onClose, onError, retryCount])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (socket) {
      socket.close(1000, 'Manual disconnect')
    }
    
    shouldReconnectRef.current = false
    setSocket(null)
    setReadyState(3) // CLOSED
  }, [socket])

  const sendMessage = useCallback((message) => {
    if (socket && readyState === 1) {
      try {
        socket.send(typeof message === 'string' ? message : JSON.stringify(message))
        return true
      } catch (error) {
        console.error('Failed to send message:', error)
        setConnectionError(error)
        return false
      }
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message)
      return false
    }
  }, [socket, readyState])

  // Send ping to keep connection alive
  const sendPing = useCallback(() => {
    return sendMessage('ping')
  }, [sendMessage])

  // Connect on mount
  useEffect(() => {
    if (url) {
      connect()
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (socket) {
        socket.close(1000, 'Component unmounting')
      }
    }
  }, [url]) // Only reconnect when URL changes

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [])

  // Set up ping interval to keep connection alive
  useEffect(() => {
    if (readyState === 1) {
      const pingInterval = setInterval(() => {
        sendPing()
      }, 30000) // Ping every 30 seconds

      return () => clearInterval(pingInterval)
    }
  }, [readyState, sendPing])

  return {
    socket,
    lastMessage,
    readyState,
    connectionError,
    retryCount,
    sendMessage,
    sendPing,
    connect,
    disconnect,
    // Connection state helpers
    isConnecting: readyState === 0,
    isConnected: readyState === 1,
    isClosing: readyState === 2,
    isClosed: readyState === 3,
  }
}

export default useWebSocket