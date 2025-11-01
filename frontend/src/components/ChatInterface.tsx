import React, { useState, useRef, useEffect } from 'react'
import { useChatStore } from '../store/chatStore'
import { useSettingsStore } from '../store/settingsStore'
import { useWebSocket } from '../services/websocket'
import MessageBubble from './MessageBubble'
import InputField from './InputField'
import StatusIndicator from './StatusIndicator'
import Header from './Header'
import ApiStatusChip from './ApiStatusChip'
import { useSendMessageMutation } from '../hooks/useChatMutation'
import { chatAPI } from '../services/api'

const ChatInterface: React.FC = () => {
  const [inputValue, setInputValue] = useState('')
  const [, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const {
    messages,
    isLoading,
    isConnected,
    clearMessages
  } = useChatStore()
  
  const { getEffectiveTheme } = useSettingsStore()
  const { isConnected: wsConnected } = useWebSocket()
  const { mutateAsync: sendMessage } = useSendMessageMutation()

  // Scroll automático al final de los mensajes
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }
  
  useEffect(() => {
    scrollToBottom()
  }, [messages])
  
  // Aplicar tema
  useEffect(() => {
    const theme = getEffectiveTheme()
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [getEffectiveTheme])

  // Envío genérico usando el estado actual
  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return
    setIsTyping(true)
    await sendMessage({ message: inputValue.trim() })
    setIsTyping(false)
    setInputValue('')
  }

  // Envío directo con texto proporcionado (desde voz)
  const handleSendMessageWithText = async (text: string) => {
    if (!text.trim() || isLoading) return
    setIsTyping(true)
    await sendMessage({ message: text.trim() })
    setIsTyping(false)
    setInputValue('')
  }

  // Manejar limpieza de mensajes
  const handleClearMessages = async () => {
    try {
      await chatAPI.clearMemory()
      clearMessages()
    } catch (error) {
      console.error('Error clearing messages:', error)
    }
  }
  
  // handleKeyPress eliminado para evitar doble envío// handleKeyPress eliminado (InputField maneja Enter)

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <Header 
        onClearMessages={handleClearMessages}
        messageCount={messages.length}
      />
      
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-hide">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="max-w-md">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                ¡Hola! Soy Leonel Responde
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Tu asistente de IA offline. Puedo ayudarte con preguntas, conversaciones y mucho más.
              </p>
              <div className="space-y-2 text-sm text-gray-500 dark:text-gray-400">
                <p>💬 Escribe tu mensaje abajo</p>
                <p>🧠 Tengo acceso a mi base de conocimiento</p>
                <p>💾 Recuerdo nuestras conversaciones</p>
              </div>
            </div>
          </div>
        )}
        
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="message-bubble message-assistant">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input */}
      <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center space-x-2">
          <StatusIndicator connected={isConnected && wsConnected()} />
          <ApiStatusChip />
          <div className="flex-1">
            <InputField
              value={inputValue}
              onChange={setInputValue}
              onSend={handleSendMessage}
              onFinalSend={handleSendMessageWithText}
              // onKeyPress eliminado para evitar doble envío
              disabled={isLoading}
              placeholder="Escribe tu mensaje..."
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface
