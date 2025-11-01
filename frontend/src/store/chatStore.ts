import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { Message, ChatState } from '../types'

interface ChatStore extends ChatState {
  // Actions
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => string
  updateMessage: (id: string, updates: Partial<Message>) => void
  clearMessages: () => void
  setLoading: (loading: boolean) => void
  setConnected: (connected: boolean) => void
  setUser: (user: string | null) => void
  
  // Computed values
  getLastMessage: () => Message | undefined
  getMessageCount: () => number
  getMessagesByRole: (role: 'user' | 'assistant') => Message[]
}

export const useChatStore = create<ChatStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      messages: [],
      isLoading: false,
      isConnected: false,
      currentUser: null,
      
      // Actions
      addMessage: (message) => {
        const id = crypto.randomUUID()
        const newMessage: Message = {
          ...message,
          id,
          timestamp: new Date()
        }
        set((state) => ({
          messages: [...state.messages, newMessage]
        }))
        return id
      },
      
      updateMessage: (id, updates) => {
        set((state) => ({
          messages: state.messages.map(msg =>
            msg.id === id ? { ...msg, ...updates } : msg
          )
        }))
      },
      
      clearMessages: () => set({ messages: [] }),
      
      setLoading: (loading) => set({ isLoading: loading }),
      
      setConnected: (connected) => set({ isConnected: connected }),
      
      setUser: (user) => set({ currentUser: user }),
      
      // Computed values
      getLastMessage: () => {
        const messages = get().messages
        return messages[messages.length - 1]
      },
      
      getMessageCount: () => {
        return get().messages.length
      },
      
      getMessagesByRole: (role) => {
        return get().messages.filter(msg => msg.role === role)
      }
    }),
    { name: 'chat-store' }
  )
)
