# 🎨 Fase 5: Frontend y UI

## Estado Actual
- Frontend iniciado: React + TypeScript + Vite con estructura `src/components`, `src/store`, `src/services`, `src/hooks`.
- UI de chat activa: `ChatInterface`, `MessageBubble`, `InputField`, `Header`, `StatusIndicator` y `TechBadges`.
- Estado global con Zustand operativo: `chatStore.ts` y `settingsStore.ts` (devtools y persist).
- Servicio WebSocket con `socket.io-client`, reconexión exponencial e integración con `useChatStore`.
- Clientes de voz por WS listos en frontend: `VoiceWsClient.tsx` (STT) y `TtsWsClient.tsx` (TTS).
- Cliente REST con Axios implementado: `/query`, `/clear-memory`, `/add-document`, `/status`, `/health`.
- Próximos pasos: añadir TanStack Query (cache/sync), pulir UI/estados y completar testing.
- No iniciado: UI y frontend pendientes de implementación.
- Backend voz operando vía WS (`/ws/tts`, `/ws/stt`) y backend LLM en proceso; API REST aún por definir.
- Próximos pasos: scaffold React + Vite, componentes base (ChatInterface, MessageBubble) y estado global con Zustand; integración REST/WS.

## 🎯 Objetivos de esta Fase

- **Implementar interfaz React** moderna y responsiva
- **Sistema de chat** intuitivo y funcional
- **Gestión de estado** global con Zustand
- **Integración con backend** via API REST y WebSocket
- **Testing completo** del frontend

## ⏱️ Tiempo Estimado

**2 semanas** (10 días de trabajo)

## 📋 Checklist de Tareas

### **Semana 1: Core Frontend**
- [x] Configurar React + TypeScript + Vite
- [x] Implementar componentes base (ChatInterface, MessageBubble, InputField, Header)
- [x] Configurar Tailwind CSS; Framer Motion pendiente
- [x] Sistema de estado global con Zustand
- [x] Integración con API REST (Axios cliente)

### **Semana 2: Funcionalidades Avanzadas**
- [x] WebSocket para tiempo real
- [ ] Sistema de atención social
- [ ] Interfaz de desarrollador para personalización
- [ ] Testing completo del frontend
- [ ] Optimización y build

## 🔧 Herramientas Necesarias

### **Frontend Core**
- **React 18+**: Framework principal
- **TypeScript**: Tipado estático
- **Vite**: Build tool moderno
- **Tailwind CSS**: Estilos
- **Framer Motion**: Animaciones

### **Estado y Comunicación**
- **Zustand**: Estado global
- **Axios**: Cliente HTTP
- **Socket.io**: WebSocket
- **React Query**: Cache y sincronización

### **Testing**
- **Jest**: Testing unitario
- **React Testing Library**: Testing de componentes
- **Playwright**: Testing e2e
- **MSW**: Mock de API

## 🏗️ Arquitectura del Frontend

### **📐 Componentes Principales**

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────┤
│  React + TypeScript + Vite + Tailwind CSS                 │
│  • Componentes modulares y reutilizables                   │
│  • Estado global con Zustand                               │
│  • Animaciones con Framer Motion                          │
│  • Integración con backend via API REST + WebSocket       │
└─────────────────────────────────────────────────────────────┘
                                ↕️
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND INTEGRATION                     │
├─────────────────────────────────────────────────────────────┤
│  FastAPI + WebSocket + REST API                          │
│  • Comunicación en tiempo real                            │
│  • Sincronización de estado                               │
│  • Gestión de sesiones                                    │
│  • Manejo de errores                                      │
└─────────────────────────────────────────────────────────────┘
```

### **🔄 Flujo de Datos**

```
User Input → React Component → Zustand Store → API Call → Backend → Response → UI Update
```

## 🚀 Implementación

### **1. Configuración del Proyecto**

```bash
# Crear proyecto React con Vite
npm create vite@latest frontend -- --template react-ts
cd frontend

# Instalar dependencias
npm install
npm install -D @types/node

# Dependencias principales
npm install zustand axios socket.io-client @tanstack/react-query
npm install framer-motion lucide-react
npm install -D tailwindcss postcss autoprefixer
npm install -D @tailwindcss/forms @tailwindcss/typography

# Testing
npm install -D jest @testing-library/react @testing-library/jest-dom
npm install -D @testing-library/user-event
npm install -D playwright @playwright/test
npm install -D msw
```

### **2. Configuración de Tailwind CSS**

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        secondary: {
          50: '#f8fafc',
          500: '#64748b',
          600: '#475569',
        }
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'bounce-gentle': 'bounceGentle 2s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        bounceGentle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        }
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
```

### **3. Store Global con Zustand**

```typescript
// src/store/chatStore.ts
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export interface Message {
  id: string
  content: string
  sender: 'user' | 'assistant'
  timestamp: Date
  metadata?: {
    sources?: string[]
    confidence?: number
    processing_time?: number
  }
}

export interface ChatSession {
  id: string
  messages: Message[]
  isActive: boolean
  createdAt: Date
  updatedAt: Date
}

interface ChatState {
  // Estado
  sessions: ChatSession[]
  currentSessionId: string | null
  isConnected: boolean
  isTyping: boolean
  
  // Acciones
  createSession: () => string
  setCurrentSession: (id: string) => void
  addMessage: (sessionId: string, message: Message) => void
  setTyping: (typing: boolean) => void
  setConnected: (connected: boolean) => void
  clearSession: (sessionId: string) => void
}

export const useChatStore = create<ChatState>()(
  devtools(
    (set, get) => ({
      // Estado inicial
      sessions: [],
      currentSessionId: null,
      isConnected: false,
      isTyping: false,
      
      // Acciones
      createSession: () => {
        const newSession: ChatSession = {
          id: `session_${Date.now()}`,
          messages: [],
          isActive: true,
          createdAt: new Date(),
          updatedAt: new Date()
        }
        
        set((state) => ({
          sessions: [...state.sessions, newSession],
          currentSessionId: newSession.id
        }))
        
        return newSession.id
      },
      
      setCurrentSession: (id: string) => {
        set({ currentSessionId: id })
      },
      
      addMessage: (sessionId: string, message: Message) => {
        set((state) => ({
          sessions: state.sessions.map(session =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: [...session.messages, message],
                  updatedAt: new Date()
                }
              : session
          )
        }))
      },
      
      setTyping: (typing: boolean) => {
        set({ isTyping: typing })
      },
      
      setConnected: (connected: boolean) => {
        set({ isConnected: connected })
      },
      
      clearSession: (sessionId: string) => {
        set((state) => ({
          sessions: state.sessions.filter(session => session.id !== sessionId)
        }))
      }
    }),
    { name: 'chat-store' }
  )
)
```

### **4. Servicio de API**

```typescript
// src/services/api.ts
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor para manejar errores
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export interface ChatRequest {
  content: string
  session_id?: string
}

export interface ChatResponse {
  message: string
  session_id: string
  timestamp: string
  metadata?: {
    sources?: string[]
    confidence?: number
    processing_time?: number
  }
}

export const chatApi = {
  sendMessage: async (data: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post('/api/chat/send', data)
    return response.data
  },
  
  getSessions: async () => {
    const response = await api.get('/api/chat/sessions')
    return response.data
  },
  
  getSession: async (sessionId: string) => {
    const response = await api.get(`/api/chat/sessions/${sessionId}`)
    return response.data
  }
}
```

### **5. WebSocket Service**

```typescript
// src/services/websocket.ts
import { io, Socket } from 'socket.io-client'

class WebSocketService {
  private socket: Socket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5

  connect(): void {
    if (this.socket?.connected) return

    this.socket = io(import.meta.env.VITE_WS_URL || 'http://localhost:8000', {
      transports: ['websocket'],
      timeout: 20000,
    })

    this.socket.on('connect', () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
    })

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected')
      this.handleReconnect()
    })

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error)
    })
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      setTimeout(() => {
        console.log(`Reconnecting... attempt ${this.reconnectAttempts}`)
        this.connect()
      }, 1000 * this.reconnectAttempts)
    }
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  onMessage(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on('message', callback)
    }
  }

  onTyping(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on('typing', callback)
    }
  }

  sendMessage(message: string, sessionId?: string): void {
    if (this.socket) {
      this.socket.emit('message', { content: message, session_id: sessionId })
    }
  }

  isConnected(): boolean {
    return this.socket?.connected || false
  }
}

export const wsService = new WebSocketService()
```

### **6. Componente ChatInterface**

```typescript
// src/components/ChatInterface.tsx
import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useChatStore } from '../store/chatStore'
import { MessageBubble } from './MessageBubble'
import { InputField } from './InputField'
import { StatusIndicator } from './StatusIndicator'
import { wsService } from '../services/websocket'
import { chatApi } from '../services/api'

export const ChatInterface: React.FC = () => {
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const {
    sessions,
    currentSessionId,
    isConnected,
    isTyping,
    createSession,
    setCurrentSession,
    addMessage,
    setTyping,
    setConnected
  } = useChatStore()

  const currentSession = sessions.find(s => s.id === currentSessionId)

  useEffect(() => {
    // Conectar WebSocket
    wsService.connect()
    setConnected(wsService.isConnected())

    // Crear sesión inicial si no existe
    if (!currentSessionId) {
      const sessionId = createSession()
      setCurrentSession(sessionId)
    }

    // Configurar listeners de WebSocket
    wsService.onMessage((data) => {
      if (data.sender === 'assistant') {
        addMessage(currentSessionId!, {
          id: `msg_${Date.now()}`,
          content: data.content,
          sender: 'assistant',
          timestamp: new Date(data.timestamp),
          metadata: data.metadata
        })
        setTyping(false)
        setIsLoading(false)
      }
    })

    wsService.onTyping((data) => {
      setTyping(data.typing)
    })

    return () => {
      wsService.disconnect()
    }
  }, [])

  useEffect(() => {
    // Scroll automático al final
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentSession?.messages])

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !currentSessionId) return

    const userMessage = {
      id: `msg_${Date.now()}`,
      content: inputValue,
      sender: 'user' as const,
      timestamp: new Date()
    }

    // Agregar mensaje del usuario
    addMessage(currentSessionId, userMessage)
    setInputValue('')
    setIsLoading(true)
    setTyping(true)

    try {
      // Enviar mensaje
      if (wsService.isConnected()) {
        wsService.sendMessage(inputValue, currentSessionId)
      } else {
        // Fallback a API REST
        const response = await chatApi.sendMessage({
          content: inputValue,
          session_id: currentSessionId
        })
        
        addMessage(currentSessionId, {
          id: `msg_${Date.now()}`,
          content: response.message,
          sender: 'assistant',
          timestamp: new Date(response.timestamp),
          metadata: response.metadata
        })
        setTyping(false)
        setIsLoading(false)
      }
    } catch (error) {
      console.error('Error sending message:', error)
      setTyping(false)
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-900">
            Asistente de IA
          </h1>
          <StatusIndicator 
            isConnected={isConnected}
            isTyping={isTyping}
          />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="space-y-4">
          <AnimatePresence>
            {currentSession?.messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                <MessageBubble message={message} />
              </motion.div>
            ))}
          </AnimatePresence>
          
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center space-x-2 text-gray-500"
            >
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
              <span>El asistente está escribiendo...</span>
            </motion.div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="bg-white border-t px-6 py-4">
        <InputField
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSendMessage}
          disabled={isLoading}
        />
      </div>
    </div>
  )
}
```

### **7. Componente MessageBubble**

```typescript
// src/components/MessageBubble.tsx
import React from 'react'
import { motion } from 'framer-motion'
import { Message } from '../store/chatStore'
import { format } from 'date-fns'

interface MessageBubbleProps {
  message: Message
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.sender === 'user'
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
          isUser
            ? 'bg-blue-500 text-white'
            : 'bg-white text-gray-900 border border-gray-200'
        }`}
      >
        <p className="text-sm">{message.content}</p>
        
        {message.metadata?.sources && (
          <div className="mt-2 text-xs opacity-75">
            <p>Fuentes: {message.metadata.sources.join(', ')}</p>
          </div>
        )}
        
        <div className="mt-1 text-xs opacity-75">
          {format(message.timestamp, 'HH:mm')}
        </div>
      </div>
    </motion.div>
  )
}
```

### **8. Componente InputField**

```typescript
// src/components/InputField.tsx
import React, { useState, KeyboardEvent } from 'react'
import { motion } from 'framer-motion'
import { Send, Mic, MicOff } from 'lucide-react'

interface InputFieldProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled?: boolean
}

export const InputField: React.FC<InputFieldProps> = ({
  value,
  onChange,
  onSend,
  disabled = false
}) => {
  const [isRecording, setIsRecording] = useState(false)

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  const handleSend = () => {
    if (value.trim() && !disabled) {
      onSend()
    }
  }

  const toggleRecording = () => {
    setIsRecording(!isRecording)
    // TODO: Implementar grabación de voz
  }

  return (
    <div className="flex items-end space-x-2">
      <div className="flex-1 relative">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Escribe tu mensaje..."
          disabled={disabled}
          className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          rows={1}
          style={{ minHeight: '48px', maxHeight: '120px' }}
        />
        
        <button
          onClick={toggleRecording}
          className={`absolute right-12 top-1/2 transform -translate-y-1/2 p-2 rounded-full transition-colors ${
            isRecording
              ? 'bg-red-100 text-red-600'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
        </button>
      </div>
      
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={handleSend}
        disabled={!value.trim() || disabled}
        className={`p-3 rounded-lg transition-colors ${
          value.trim() && !disabled
            ? 'bg-blue-500 text-white hover:bg-blue-600'
            : 'bg-gray-200 text-gray-400 cursor-not-allowed'
        }`}
      >
        <Send size={16} />
      </motion.button>
    </div>
  )
}
```

### **9. Componente StatusIndicator**

```typescript
// src/components/StatusIndicator.tsx
import React from 'react'
import { motion } from 'framer-motion'
import { Wifi, WifiOff, Loader } from 'lucide-react'

interface StatusIndicatorProps {
  isConnected: boolean
  isTyping: boolean
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  isConnected,
  isTyping
}) => {
  return (
    <div className="flex items-center space-x-2">
      {isConnected ? (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="flex items-center space-x-1 text-green-600"
        >
          <Wifi size={16} />
          <span className="text-sm">Conectado</span>
        </motion.div>
      ) : (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="flex items-center space-x-1 text-red-600"
        >
          <WifiOff size={16} />
          <span className="text-sm">Desconectado</span>
        </motion.div>
      )}
      
      {isTyping && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="flex items-center space-x-1 text-blue-600"
        >
          <Loader className="animate-spin" size={16} />
          <span className="text-sm">Escribiendo...</span>
        </motion.div>
      )}
    </div>
  )
}
```

## 🧪 Testing del Frontend

### **1. Tests Unitarios**

```typescript
// src/components/__tests__/ChatInterface.test.tsx
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ChatInterface } from '../ChatInterface'
import { useChatStore } from '../../store/chatStore'

// Mock del store
jest.mock('../../store/chatStore')
jest.mock('../../services/websocket')
jest.mock('../../services/api')

describe('ChatInterface', () => {
  beforeEach(() => {
    (useChatStore as jest.Mock).mockReturnValue({
      sessions: [],
      currentSessionId: null,
      isConnected: true,
      isTyping: false,
      createSession: jest.fn(() => 'session_1'),
      setCurrentSession: jest.fn(),
      addMessage: jest.fn(),
      setTyping: jest.fn(),
      setConnected: jest.fn(),
      clearSession: jest.fn()
    })
  })

  it('renders chat interface', () => {
    render(<ChatInterface />)
    
    expect(screen.getByText('Asistente de IA')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Escribe tu mensaje...')).toBeInTheDocument()
  })

  it('sends message when enter is pressed', async () => {
    render(<ChatInterface />)
    
    const input = screen.getByPlaceholderText('Escribe tu mensaje...')
    fireEvent.change(input, { target: { value: 'Hello' } })
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter' })
    
    await waitFor(() => {
      expect(useChatStore().addMessage).toHaveBeenCalled()
    })
  })
})
```

### **2. Tests de Integración**

```typescript
// src/__tests__/integration/chat.test.tsx
import { test, expect } from '@playwright/test'

test('chat flow works correctly', async ({ page }) => {
  await page.goto('/')
  
  // Verificar que la interfaz se carga
  await expect(page.getByText('Asistente de IA')).toBeVisible()
  
  // Enviar mensaje
  await page.fill('[placeholder="Escribe tu mensaje..."]', 'Hola, ¿cómo estás?')
  await page.press('[placeholder="Escribe tu mensaje..."]', 'Enter')
  
  // Verificar que el mensaje se envía
  await expect(page.getByText('Hola, ¿cómo estás?')).toBeVisible()
  
  // Verificar indicador de escritura
  await expect(page.getByText('Escribiendo...')).toBeVisible()
})
```

## 📊 Métricas de Éxito

### **🎯 Objetivos Técnicos**
- **Tiempo de Carga**: < 2s
- **Tiempo de Respuesta**: < 100ms
- **Bundle Size**: < 1MB
- **Lighthouse Score**: > 90
- **Accesibilidad**: WCAG 2.1 AA

### **🎯 Objetivos de Funcionalidad**
- **Interfaz Responsiva**: Funciona en todos los dispositivos
- **Estado Global**: Sincronización correcta
- **WebSocket**: Comunicación en tiempo real
- **Testing**: > 90% cobertura de código
- **UX**: Interfaz intuitiva y fluida

## ✅ Criterios de Éxito

### **📋 Checklist de Validación**
- [x] **React + TypeScript** configurado correctamente
- [x] **Componentes base** funcionando
- [x] **Estado global** con Zustand operativo
- [x] **API REST** integrada (mock backend en `http://localhost:8001`)
- [x] **WebSocket** funcionando
- [ ] **Testing completo** pasando
- [ ] **Build optimizado** funcionando
- [x] **Preparación** para siguiente fase

### **🎯 Entregables de esta Fase**
- [ ] **Frontend React** completamente funcional
- [ ] **Sistema de chat** intuitivo
- [ ] **Estado global** sincronizado
- [ ] **Integración con backend** operativa
- [ ] **Testing suite** completa
- [ ] **Build optimizado** para producción
- [ ] **Documentación** técnica
- [ ] **Preparación** para características opcionales

## 🚀 Siguiente Fase

Una vez completada esta fase, continuar con [**Fase 6: Sistema de Voz**](./06-voz-audio.md) (Opcional)

### **📋 Preparación para Fase 6**
- [ ] Frontend funcionando
- [ ] Sistema de chat estable
- [ ] WebSocket operativo
- [ ] Testing completo
- [ ] Documentación actualizada

---

**🎉 ¡Con esta fase tendrás una interfaz moderna y funcional!**

*Recuerda: El frontend es la cara de tu asistente. Invierte el tiempo necesario para hacerlo intuitivo y atractivo.* 🚀

# 🖥️ Fase 5: Frontend UI

## 🎯 Objetivos de esta Fase

- **Implementar interfaz React** moderna y responsiva
- **Sistema de chat** intuitivo y funcional
- **Gestión de estado** global con Zustand
- **Integración con backend** via API REST y WebSocket
- **Testing completo** del frontend

## ⏱️ Tiempo Estimado

**2 semanas** (10 días de trabajo)

## 📋 Checklist de Tareas

### **Semana 1: Core Frontend**
- [x] Configurar React + TypeScript + Vite
- [x] Implementar componentes base (ChatInterface, MessageBubble, InputField, Header)
- [x] Configurar Tailwind CSS; Framer Motion pendiente
- [x] Sistema de estado global con Zustand
- [x] Integración con API REST (Axios cliente)

### **Semana 2: Funcionalidades Avanzadas**
- [x] WebSocket para tiempo real
- [ ] Sistema de atención social
- [ ] Interfaz de desarrollador para personalización
- [ ] Testing completo del frontend
- [ ] Optimización y build

## 🔧 Herramientas Necesarias

### **Frontend Core**
- **React 18+**: Framework principal
- **TypeScript**: Tipado estático
- **Vite**: Build tool moderno
- **Tailwind CSS**: Estilos
- **Framer Motion**: Animaciones

### **Estado y Comunicación**
- **Zustand**: Estado global
- **Axios**: Cliente HTTP
- **Socket.io**: WebSocket
- **React Query**: Cache y sincronización

### **Testing**
- **Jest**: Testing unitario
- **React Testing Library**: Testing de componentes
- **Playwright**: Testing e2e
- **MSW**: Mock de API

## 🏗️ Arquitectura del Frontend

### **📐 Componentes Principales**

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────┤
│  React + TypeScript + Vite + Tailwind CSS                 │
│  • Componentes modulares y reutilizables                   │
│  • Estado global con Zustand                               │
│  • Animaciones con Framer Motion                          │
│  • Integración con backend via API REST + WebSocket       │
└─────────────────────────────────────────────────────────────┘
                                ↕️
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND INTEGRATION                     │
├─────────────────────────────────────────────────────────────┤
│  FastAPI + WebSocket + REST API                          │
│  • Comunicación en tiempo real                            │
│  • Sincronización de estado                               │
│  • Gestión de sesiones                                    │
│  • Manejo de errores                                      │
└─────────────────────────────────────────────────────────────┘
```

### **🔄 Flujo de Datos**

```
User Input → React Component → Zustand Store → API Call → Backend → Response → UI Update
```

## 🚀 Implementación

### **1. Configuración del Proyecto**

```bash
# Crear proyecto React con Vite
npm create vite@latest frontend -- --template react-ts
cd frontend

# Instalar dependencias
npm install
npm install -D @types/node

# Dependencias principales
npm install zustand axios socket.io-client @tanstack/react-query
npm install framer-motion lucide-react
npm install -D tailwindcss postcss autoprefixer
npm install -D @tailwindcss/forms @tailwindcss/typography

# Testing
npm install -D jest @testing-library/react @testing-library/jest-dom
npm install -D @testing-library/user-event
npm install -D playwright @playwright/test
npm install -D msw
```

### **2. Configuración de Tailwind CSS**

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        secondary: {
          50: '#f8fafc',
          500: '#64748b',
          600: '#475569',
        }
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'bounce-gentle': 'bounceGentle 2s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        bounceGentle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        }
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
```

### **3. Store Global con Zustand**

```typescript
// src/store/chatStore.ts
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export interface Message {
  id: string
  content: string
  sender: 'user' | 'assistant'
  timestamp: Date
  metadata?: {
    sources?: string[]
    confidence?: number
    processing_time?: number
  }
}

export interface ChatSession {
  id: string
  messages: Message[]
  isActive: boolean
  createdAt: Date
  updatedAt: Date
}

interface ChatState {
  // Estado
  sessions: ChatSession[]
  currentSessionId: string | null
  isConnected: boolean
  isTyping: boolean
  
  // Acciones
  createSession: () => string
  setCurrentSession: (id: string) => void
  addMessage: (sessionId: string, message: Message) => void
  setTyping: (typing: boolean) => void
  setConnected: (connected: boolean) => void
  clearSession: (sessionId: string) => void
}

export const useChatStore = create<ChatState>()(
  devtools(
    (set, get) => ({
      // Estado inicial
      sessions: [],
      currentSessionId: null,
      isConnected: false,
      isTyping: false,
      
      // Acciones
      createSession: () => {
        const newSession: ChatSession = {
          id: `session_${Date.now()}`,
          messages: [],
          isActive: true,
          createdAt: new Date(),
          updatedAt: new Date()
        }
        
        set((state) => ({
          sessions: [...state.sessions, newSession],
          currentSessionId: newSession.id
        }))
        
        return newSession.id
      },
      
      setCurrentSession: (id: string) => {
        set({ currentSessionId: id })
      },
      
      addMessage: (sessionId: string, message: Message) => {
        set((state) => ({
          sessions: state.sessions.map(session =>
            session.id === sessionId
              ? {
                  ...session,
                  messages: [...session.messages, message],
                  updatedAt: new Date()
                }
              : session
          )
        }))
      },
      
      setTyping: (typing: boolean) => {
        set({ isTyping: typing })
      },
      
      setConnected: (connected: boolean) => {
        set({ isConnected: connected })
      },
      
      clearSession: (sessionId: string) => {
        set((state) => ({
          sessions: state.sessions.filter(session => session.id !== sessionId)
        }))
      }
    }),
    { name: 'chat-store' }
  )
)
```

### **4. Servicio de API**

```typescript
// src/services/api.ts
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor para manejar errores
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export interface ChatRequest {
  content: string
  session_id?: string
}

export interface ChatResponse {
  message: string
  session_id: string
  timestamp: string
  metadata?: {
    sources?: string[]
    confidence?: number
    processing_time?: number
  }
}

export const chatApi = {
  sendMessage: async (data: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post('/api/chat/send', data)
    return response.data
  },
  
  getSessions: async () => {
    const response = await api.get('/api/chat/sessions')
    return response.data
  },
  
  getSession: async (sessionId: string) => {
    const response = await api.get(`/api/chat/sessions/${sessionId}`)
    return response.data
  }
}
```

### **5. WebSocket Service**

```typescript
// src/services/websocket.ts
import { io, Socket } from 'socket.io-client'

class WebSocketService {
  private socket: Socket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5

  connect(): void {
    if (this.socket?.connected) return

    this.socket = io(import.meta.env.VITE_WS_URL || 'http://localhost:8000', {
      transports: ['websocket'],
      timeout: 20000,
    })

    this.socket.on('connect', () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
    })

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected')
      this.handleReconnect()
    })

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error)
    })
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      setTimeout(() => {
        console.log(`Reconnecting... attempt ${this.reconnectAttempts}`)
        this.connect()
      }, 1000 * this.reconnectAttempts)
    }
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  onMessage(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on('message', callback)
    }
  }

  onTyping(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on('typing', callback)
    }
  }

  sendMessage(message: string, sessionId?: string): void {
    if (this.socket) {
      this.socket.emit('message', { content: message, session_id: sessionId })
    }
  }

  isConnected(): boolean {
    return this.socket?.connected || false
  }
}

export const wsService = new WebSocketService()
```

### **6. Componente ChatInterface**

```typescript
// src/components/ChatInterface.tsx
import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useChatStore } from '../store/chatStore'
import { MessageBubble } from './MessageBubble'
import { InputField } from './InputField'
import { StatusIndicator } from './StatusIndicator'
import { wsService } from '../services/websocket'
import { chatApi } from '../services/api'

export const ChatInterface: React.FC = () => {
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const {
    sessions,
    currentSessionId,
    isConnected,
    isTyping,
    createSession,
    setCurrentSession,
    addMessage,
    setTyping,
    setConnected
  } = useChatStore()

  const currentSession = sessions.find(s => s.id === currentSessionId)

  useEffect(() => {
    // Conectar WebSocket
    wsService.connect()
    setConnected(wsService.isConnected())

    // Crear sesión inicial si no existe
    if (!currentSessionId) {
      const sessionId = createSession()
      setCurrentSession(sessionId)
    }

    // Configurar listeners de WebSocket
    wsService.onMessage((data) => {
      if (data.sender === 'assistant') {
        addMessage(currentSessionId!, {
          id: `msg_${Date.now()}`,
          content: data.content,
          sender: 'assistant',
          timestamp: new Date(data.timestamp),
          metadata: data.metadata
        })
        setTyping(false)
        setIsLoading(false)
      }
    })

    wsService.onTyping((data) => {
      setTyping(data.typing)
    })

    return () => {
      wsService.disconnect()
    }
  }, [])

  useEffect(() => {
    // Scroll automático al final
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentSession?.messages])

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !currentSessionId) return

    const userMessage = {
      id: `msg_${Date.now()}`,
      content: inputValue,
      sender: 'user' as const,
      timestamp: new Date()
    }

    // Agregar mensaje del usuario
    addMessage(currentSessionId, userMessage)
    setInputValue('')
    setIsLoading(true)
    setTyping(true)

    try {
      // Enviar mensaje
      if (wsService.isConnected()) {
        wsService.sendMessage(inputValue, currentSessionId)
      } else {
        // Fallback a API REST
        const response = await chatApi.sendMessage({
          content: inputValue,
          session_id: currentSessionId
        })
        
        addMessage(currentSessionId, {
          id: `msg_${Date.now()}`,
          content: response.message,
          sender: 'assistant',
          timestamp: new Date(response.timestamp),
          metadata: response.metadata
        })
        setTyping(false)
        setIsLoading(false)
      }
    } catch (error) {
      console.error('Error sending message:', error)
      setTyping(false)
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-900">
            Asistente de IA
          </h1>
          <StatusIndicator 
            isConnected={isConnected}
            isTyping={isTyping}
          />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="space-y-4">
          <AnimatePresence>
            {currentSession?.messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                <MessageBubble message={message} />
              </motion.div>
            ))}
          </AnimatePresence>
          
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center space-x-2 text-gray-500"
            >
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
              <span>El asistente está escribiendo...</span>
            </motion.div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="bg-white border-t px-6 py-4">
        <InputField
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSendMessage}
          disabled={isLoading}
        />
      </div>
    </div>
  )
}
```

### **7. Componente MessageBubble**

```typescript
// src/components/MessageBubble.tsx
import React from 'react'
import { motion } from 'framer-motion'
import { Message } from '../store/chatStore'
import { format } from 'date-fns'

interface MessageBubbleProps {
  message: Message
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.sender === 'user'
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
          isUser
            ? 'bg-blue-500 text-white'
            : 'bg-white text-gray-900 border border-gray-200'
        }`}
      >
        <p className="text-sm">{message.content}</p>
        
        {message.metadata?.sources && (
          <div className="mt-2 text-xs opacity-75">
            <p>Fuentes: {message.metadata.sources.join(', ')}</p>
          </div>
        )}
        
        <div className="mt-1 text-xs opacity-75">
          {format(message.timestamp, 'HH:mm')}
        </div>
      </div>
    </motion.div>
  )
}
```

### **8. Componente InputField**

```typescript
// src/components/InputField.tsx
import React, { useState, KeyboardEvent } from 'react'
import { motion } from 'framer-motion'
import { Send, Mic, MicOff } from 'lucide-react'

interface InputFieldProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled?: boolean
}

export const InputField: React.FC<InputFieldProps> = ({
  value,
  onChange,
  onSend,
  disabled = false
}) => {
  const [isRecording, setIsRecording] = useState(false)

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  const handleSend = () => {
    if (value.trim() && !disabled) {
      onSend()
    }
  }

  const toggleRecording = () => {
    setIsRecording(!isRecording)
    // TODO: Implementar grabación de voz
  }

  return (
    <div className="flex items-end space-x-2">
      <div className="flex-1 relative">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Escribe tu mensaje..."
          disabled={disabled}
          className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          rows={1}
          style={{ minHeight: '48px', maxHeight: '120px' }}
        />
        
        <button
          onClick={toggleRecording}
          className={`absolute right-12 top-1/2 transform -translate-y-1/2 p-2 rounded-full transition-colors ${
            isRecording
              ? 'bg-red-100 text-red-600'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
        </button>
      </div>
      
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={handleSend}
        disabled={!value.trim() || disabled}
        className={`p-3 rounded-lg transition-colors ${
          value.trim() && !disabled
            ? 'bg-blue-500 text-white hover:bg-blue-600'
            : 'bg-gray-200 text-gray-400 cursor-not-allowed'
        }`}
      >
        <Send size={16} />
      </motion.button>
    </div>
  )
}
```

### **9. Componente StatusIndicator**

```typescript
// src/components/StatusIndicator.tsx
import React from 'react'
import { motion } from 'framer-motion'
import { Wifi, WifiOff, Loader } from 'lucide-react'

interface StatusIndicatorProps {
  isConnected: boolean
  isTyping: boolean
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  isConnected,
  isTyping
}) => {
  return (
    <div className="flex items-center space-x-2">
      {isConnected ? (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="flex items-center space-x-1 text-green-600"
        >
          <Wifi size={16} />
          <span className="text-sm">Conectado</span>
        </motion.div>
      ) : (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="flex items-center space-x-1 text-red-600"
        >
          <WifiOff size={16} />
          <span className="text-sm">Desconectado</span>
        </motion.div>
      )}
      
      {isTyping && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="flex items-center space-x-1 text-blue-600"
        >
          <Loader className="animate-spin" size={16} />
          <span className="text-sm">Escribiendo...</span>
        </motion.div>
      )}
    </div>
  )
}
```

## 🧪 Testing del Frontend

### **1. Tests Unitarios**

```typescript
// src/components/__tests__/ChatInterface.test.tsx
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ChatInterface } from '../ChatInterface'
import { useChatStore } from '../../store/chatStore'

// Mock del store
jest.mock('../../store/chatStore')
jest.mock('../../services/websocket')
jest.mock('../../services/api')

describe('ChatInterface', () => {
  beforeEach(() => {
    (useChatStore as jest.Mock).mockReturnValue({
      sessions: [],
      currentSessionId: null,
      isConnected: true,
      isTyping: false,
      createSession: jest.fn(() => 'session_1'),
      setCurrentSession: jest.fn(),
      addMessage: jest.fn(),
      setTyping: jest.fn(),
      setConnected: jest.fn(),
      clearSession: jest.fn()
    })
  })

  it('renders chat interface', () => {
    render(<ChatInterface />)
    
    expect(screen.getByText('Asistente de IA')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Escribe tu mensaje...')).toBeInTheDocument()
  })

  it('sends message when enter is pressed', async () => {
    render(<ChatInterface />)
    
    const input = screen.getByPlaceholderText('Escribe tu mensaje...')
    fireEvent.change(input, { target: { value: 'Hello' } })
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter' })
    
    await waitFor(() => {
      expect(useChatStore().addMessage).toHaveBeenCalled()
    })
  })
})
```

### **2. Tests de Integración**

```typescript
// src/__tests__/integration/chat.test.tsx
import { test, expect } from '@playwright/test'

test('chat flow works correctly', async ({ page }) => {
  await page.goto('/')
  
  // Verificar que la interfaz se carga
  await expect(page.getByText('Asistente de IA')).toBeVisible()
  
  // Enviar mensaje
  await page.fill('[placeholder="Escribe tu mensaje..."]', 'Hola, ¿cómo estás?')
  await page.press('[placeholder="Escribe tu mensaje..."]', 'Enter')
  
  // Verificar que el mensaje se envía
  await expect(page.getByText('Hola, ¿cómo estás?')).toBeVisible()
  
  // Verificar indicador de escritura
  await expect(page.getByText('Escribiendo...')).toBeVisible()
})
```

## 📊 Métricas de Éxito

### **🎯 Objetivos Técnicos**
- **Tiempo de Carga**: < 2s
- **Tiempo de Respuesta**: < 100ms
- **Bundle Size**: < 1MB
- **Lighthouse Score**: > 90
- **Accesibilidad**: WCAG 2.1 AA

### **🎯 Objetivos de Funcionalidad**
- **Interfaz Responsiva**: Funciona en todos los dispositivos
- **Estado Global**: Sincronización correcta
- **WebSocket**: Comunicación en tiempo real
- **Testing**: > 90% cobertura de código
- **UX**: Interfaz intuitiva y fluida

## ✅ Criterios de Éxito

### **📋 Checklist de Validación**
- [x] **React + TypeScript** configurado correctamente
- [x] **Componentes base** funcionando
- [x] **Estado global** con Zustand operativo
- [x] **API REST** integrada (mock backend en `http://localhost:8001`)
- [x] **WebSocket** funcionando
- [ ] **Testing completo** pasando
- [ ] **Build optimizado** funcionando
- [x] **Preparación** para siguiente fase

### **🎯 Entregables de esta Fase**
- [ ] **Frontend React** completamente funcional
- [ ] **Sistema de chat** intuitivo
- [ ] **Estado global** sincronizado
- [ ] **Integración con backend** operativa
- [ ] **Testing suite** completa
- [ ] **Build optimizado** para producción
- [ ] **Documentación** técnica
- [ ] **Preparación** para características opcionales

## 🚀 Siguiente Fase

Una vez completada esta fase, continuar con [**Fase 6: Sistema de Voz**](./06-voz-audio.md) (Opcional)

### **📋 Preparación para Fase 6**
- [ ] Frontend funcionando
- [ ] Sistema de chat estable
- [ ] WebSocket operativo
- [ ] Testing completo
- [ ] Documentación actualizada

---

**🎉 ¡Con esta fase tendrás una interfaz moderna y funcional!**

*Recuerda: El frontend es la cara de tu asistente. Invierte el tiempo necesario para hacerlo intuitivo y atractivo.* 🚀

## Checklist (avance)

### Semana 1: Core Frontend
- [x] Configurar React + TypeScript + Vite
- [x] Implementar componentes base (ChatInterface, MessageBubble)
- [x] Sistema de estado global con Zustand
- [x] Configurar Tailwind CSS y Framer Motion
- [x] Integración con API REST (endpoint `/query` no streaming)

### Semana 2: Tiempo real
- [x] WebSocket de voz operativo para STT (puerto 8010)
- [ ] WebSocket de chat en tiempo real (mensajería general)

### Semana 1: Core Frontend
- [x] Configurar React + TypeScript + Vite
- [x] Implementar componentes base (ChatInterface, MessageBubble)
- [x] Sistema de estado global con Zustand
- [x] Configurar Tailwind CSS y Framer Motion
- [x] Integración con API REST (endpoint `/query` no streaming)

### Semana 2: Tiempo real
- [x] WebSocket de voz operativo para STT (puerto 8010)
- [ ] WebSocket de chat en tiempo real (mensajería general)

### Semana 1: Core Frontend
- [x] Configurar React + TypeScript + Vite
- [x] Implementar componentes base (ChatInterface, MessageBubble)
- [x] Sistema de estado global con Zustand
- [x] Configurar Tailwind CSS y Framer Motion
- [x] Integración con API REST (endpoint `/query` no streaming)

### Semana 2: Tiempo real
- [x] WebSocket de voz operativo para STT (puerto 8010)
- [ ] WebSocket de chat en tiempo real (mensajería general)
