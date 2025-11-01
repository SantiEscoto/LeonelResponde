import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'
import type { QueryRequest, QueryResponse, StatusResponse } from '../types'

// Configuración de la API
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_TIMEOUT = 30000

// Cliente HTTP configurado
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  }
})

// Request interceptor para autenticación
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor para manejo de errores
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API endpoints
export const chatAPI = {
  /**
   * Enviar mensaje al asistente
   */
  sendMessage: async (message: string, context?: string): Promise<QueryResponse> => {
    try {
      const request: QueryRequest = {
        query: message,
        context,
        use_knowledge_base: true,
        use_memory: true,
        stream: false
      }
      
      const response = await apiClient.post<QueryResponse>('/query', request)
      return response.data
    } catch (error) {
      console.error('Error sending message:', error)
      throw error
    }
  },
  
  /**
   * Limpiar memoria de conversación
   */
  clearMemory: async (): Promise<{ status: string; message: string }> => {
    try {
      const response = await apiClient.post('/clear-memory')
      return response.data
    } catch (error) {
      console.error('Error clearing memory:', error)
      throw error
    }
  },
  
  /**
   * Agregar documento a la base de conocimiento
   */
  addDocument: async (content: string, title?: string): Promise<{ status: string; message: string }> => {
    try {
      const response = await apiClient.post('/add-document', {
        content,
        title
      })
      return response.data
    } catch (error) {
      console.error('Error adding document:', error)
      throw error
    }
  },
  
  /**
   * Obtener estado del sistema
   */
  getStatus: async (): Promise<StatusResponse> => {
    try {
      const response = await apiClient.get<StatusResponse>('/status')
      return response.data
    } catch (error) {
      console.error('Error getting status:', error)
      throw error
    }
  },
  
  /**
   * Verificar salud del sistema
   */
  healthCheck: async (): Promise<{ status: string; timestamp: number }> => {
    try {
      await apiClient.get('/')
      return {
        status: 'healthy',
        timestamp: Date.now()
      }
    } catch (error) {
      console.error('Health check failed:', error)
      throw error
    }
  }
}

// Autenticación
export const authAPI = {
  /**
   * Login de usuario
   */
  login: async (username: string, password: string): Promise<{ access_token: string; token_type: string }> => {
    try {
      const response = await apiClient.post('/auth/login', {
        username,
        password
      })
      
      const { access_token } = response.data
      localStorage.setItem('auth_token', access_token)
      
      return response.data
    } catch (error) {
      console.error('Login error:', error)
      throw error
    }
  },
  
  /**
   * Logout de usuario
   */
  logout: (): void => {
    localStorage.removeItem('auth_token')
    window.location.href = '/login'
  },
  
  /**
   * Verificar si el usuario está autenticado
   */
  isAuthenticated: (): boolean => {
    return !!localStorage.getItem('auth_token')
  },
  
  /**
   * Obtener token de autenticación
   */
  getToken: (): string | null => {
    return localStorage.getItem('auth_token')
  }
}

// Utilidades de API
export const apiUtils = {
  /**
   * Manejar errores de API
   */
  handleError: (error: unknown): string => {
    if (axios.isAxiosError(error)) {
      const detail = (error.response?.data as { detail?: string } | undefined)?.detail
      if (detail) return detail
      if (error.message) return error.message
    }
    if (error instanceof Error) {
      return error.message
    }
    return 'Error desconocido'
  },
  
  /**
   * Verificar si es error de red
   */
  isNetworkError: (error: unknown): boolean => {
    if (axios.isAxiosError(error)) {
      return !error.response && Boolean(error.request)
    }
    return false
  },
  
  /**
   * Verificar si es error de timeout
   */
  isTimeoutError: (error: unknown): boolean => {
    if (axios.isAxiosError(error)) {
      return error.code === 'ECONNABORTED'
    }
    return false
  }
}
