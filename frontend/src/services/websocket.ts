import { io } from 'socket.io-client'
import type { Socket } from 'socket.io-client'
import { useChatStore } from '../store/chatStore'
import type { WebSocketMessage } from '../types'

class WebSocketService {
  private socket: Socket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private isConnecting = false
  
  /**
   * Conectar al servidor WebSocket
   */
  connect(): void {
    if (this.isConnecting || this.socket?.connected) {
      return
    }
    
    // Permitir deshabilitar WebSocket vía env: VITE_WS_URL=disabled
    const wsEnv = import.meta.env.VITE_WS_URL
    if (wsEnv === 'disabled') {
      useChatStore.getState().setConnected(false)
      return
    }

    this.isConnecting = true
    const serverUrl = wsEnv || 'http://localhost:8000'
    
    try {
      this.socket = io(serverUrl, {
        transports: ['websocket'],
        autoConnect: true,
        timeout: 10000,
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: this.reconnectDelay
      })
      
      this.setupEventListeners()
      
    } catch (error) {
      console.error('Error connecting to WebSocket:', error)
      this.isConnecting = false
    }
  }

  /**
   * Configurar event listeners
   */
  private setupEventListeners(): void {
    if (!this.socket) return
    
    this.socket.on('connect', () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
      this.isConnecting = false
      useChatStore.getState().setConnected(true)
    })
    
    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason)
      useChatStore.getState().setConnected(false)
      this.isConnecting = false
    })
    
    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error)
      this.isConnecting = false
      this.handleReconnect()
    })
    
    this.socket.on('message', (data: WebSocketMessage) => {
      console.log('Message received:', data)
      this.handleMessage(data)
    })
    
    this.socket.on('status', (data) => {
      console.log('Status update:', data)
      // Manejar actualizaciones de estado
    })
    
    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error)
    })
  }

  /**
   * Manejar reconexión automática
   */
  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
      
      console.log(`Reconnecting... attempt ${this.reconnectAttempts} in ${delay}ms`)
      
      setTimeout(() => {
        this.connect()
      }, delay)
    } else {
      console.error('Max reconnection attempts reached')
      useChatStore.getState().setConnected(false)
    }
  }

  /**
   * Manejar mensajes recibidos
   */
  private handleMessage(data: WebSocketMessage): void {
    switch (data.type) {
      case 'message':
        // Manejar mensajes del asistente
        if (data.data.role === 'assistant') {
          useChatStore.getState().addMessage({
            content: data.data.content,
            role: 'assistant',
            status: 'sent'
          })
        }
        break
        
      case 'status':
        // Manejar actualizaciones de estado
        console.log('Status update:', data.data)
        break
        
      case 'error':
        // Manejar errores
        console.error('WebSocket error:', data.data)
        break
    }
  }

  /**
   * Desconectar del servidor
   */
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.isConnecting = false
      this.reconnectAttempts = 0
      useChatStore.getState().setConnected(false)
    }
  }
  
  /**
   * Enviar mensaje al servidor
   */
  sendMessage(message: string): void {
    if (this.socket?.connected) {
      this.socket.emit('message', {
        type: 'message',
        data: {
          content: message,
          role: 'user',
          timestamp: new Date()
        }
      })
    } else {
      console.warn('WebSocket not connected')
    }
  }
  
  /**
   * Verificar si está conectado
   */
  isConnected(): boolean {
    return this.socket?.connected || false
  }
  
  /**
   * Obtener estado de conexión
   */
  getConnectionState(): string {
    if (!this.socket) return 'disconnected'
    return this.socket.connected ? 'connected' : 'disconnected'
  }
  
  /**
   * Obtener intentos de reconexión
   */
  getReconnectAttempts(): number {
    return this.reconnectAttempts
  }
}

// Instancia singleton del servicio WebSocket
export const websocketService = new WebSocketService()

// Hook para usar WebSocket en componentes
export const useWebSocket = () => {
  return {
    connect: () => websocketService.connect(),
    disconnect: () => websocketService.disconnect(),
    sendMessage: (message: string) => websocketService.sendMessage(message),
    isConnected: () => websocketService.isConnected(),
    getConnectionState: () => websocketService.getConnectionState(),
    getReconnectAttempts: () => websocketService.getReconnectAttempts()
  }
}
