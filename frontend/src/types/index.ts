// Tipos principales para la aplicación

export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  status?: 'sending' | 'sent' | 'error'
}

export interface ChatState {
  messages: Message[]
  isLoading: boolean
  isConnected: boolean
  currentUser: string | null
}

export interface QueryRequest {
  query: string
  context?: string
  use_knowledge_base?: boolean
  use_memory?: boolean
  stream?: boolean
}

export interface QueryResponse {
  response: string
  processing_time: number
  tokens_used?: number
  context_used?: boolean
}

export interface StatusResponse {
  status: string
  llm: {
    model_name: string
    is_loaded: boolean
    device: string
  }
  memory?: {
    total_users: number
    total_interactions: number
    short_term_entries: number
    long_term_entries: number
  }
  knowledge_base?: {
    total_documents: number
    index_size: number
  }
  uptime: number
}

export interface ApiError {
  detail: string
  status_code: number
}

// Payloads para WebSocket
export interface WSMessagePayload {
  content: string
  role: 'user' | 'assistant'
  timestamp?: string | Date
}

export interface WSStatusPayload {
  [key: string]: unknown
}

export interface WSErrorPayload {
  message?: string
  code?: string
  [key: string]: unknown
}

export interface WSBase {
  timestamp: Date
}

export interface WSMessage extends WSBase {
  type: 'message'
  data: WSMessagePayload
}

export interface WSStatus extends WSBase {
  type: 'status'
  data: WSStatusPayload
}

export interface WSError extends WSBase {
  type: 'error'
  data: WSErrorPayload
}

export type WebSocketMessage = WSMessage | WSStatus | WSError

export interface User {
  id: string
  username: string
  email?: string
  isAuthenticated: boolean
}

export interface AppSettings {
  theme: 'light' | 'dark' | 'system'
  language: string
  autoSave: boolean
  notifications: boolean
  soundEnabled: boolean
}

export interface FileUpload {
  file: File
  name: string
  size: number
  type: string
  status: 'pending' | 'uploading' | 'success' | 'error'
  progress: number
}
