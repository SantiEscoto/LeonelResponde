import React, { useEffect } from 'react'
import { useSettingsStore } from './store/settingsStore'
import { useWebSocket } from './services/websocket'
import ChatInterface from './components/ChatInterface'
import VoiceWsClient from './components/VoiceWsClient'
import TtsWsClient from './components/TtsWsClient'
import TechBadges from './components/TechBadges'
import './index.css'

const App: React.FC = () => {
  const { getEffectiveTheme } = useSettingsStore()
  const { connect } = useWebSocket()
  
  // Aplicar tema al cargar
  useEffect(() => {
    const theme = getEffectiveTheme()
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [getEffectiveTheme])
  
  // Conectar WebSocket al cargar
  useEffect(() => {
    connect()
  }, [connect])
  
  // Escuchar cambios de tema del sistema
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      const theme = getEffectiveTheme()
      document.documentElement.classList.toggle('dark', theme === 'dark')
    }
    
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [getEffectiveTheme])
  
  return (
    <div className="App">
      <TechBadges />
      <ChatInterface />
      <div>
        <VoiceWsClient />
        <TtsWsClient />
      </div>
    </div>
  )
}

export default App