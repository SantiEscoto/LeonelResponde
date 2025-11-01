import React, { useState } from 'react'
import { useSettingsStore } from '../store/settingsStore'
import StatusIndicator from './StatusIndicator'

interface HeaderProps {
  onClearMessages: () => void
  messageCount: number
}

const Header: React.FC<HeaderProps> = ({ onClearMessages, messageCount }) => {
  const [showMenu, setShowMenu] = useState(false)
  const { theme, setTheme, getEffectiveTheme } = useSettingsStore()
  
  const handleThemeToggle = () => {
    const newTheme = theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light'
    setTheme(newTheme)
  }
  
  const getThemeIcon = () => {
    const effectiveTheme = getEffectiveTheme()
    if (effectiveTheme === 'dark') {
      return '🌙'
    }
    return '☀️'
  }
  
  const getThemeLabel = () => {
    switch (theme) {
      case 'light': return 'Claro'
      case 'dark': return 'Oscuro'
      case 'system': return 'Sistema'
      default: return 'Sistema'
    }
  }
  
  return (
    <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
      <div className="px-4 py-3 flex items-center justify-between">
        {/* Logo y título */}
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">LR</span>
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              Leonel Responde
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Asistente de IA Offline
            </p>
          </div>
        </div>
        
        {/* Controles */}
        <div className="flex items-center space-x-4">
          {/* Contador de mensajes */}
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {messageCount} mensajes
          </div>
          
          {/* Indicador de estado */}
          <StatusIndicator connected={true} showText={false} />
          
          {/* Menú */}
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title="Menú"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
            </button>
            
            {showMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10">
                <div className="py-1">
                  {/* Tema */}
                  <button
                    onClick={handleThemeToggle}
                    className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                  >
                    <span>{getThemeIcon()}</span>
                    <span>Tema: {getThemeLabel()}</span>
                  </button>
                  
                  {/* Separador */}
                  <div className="border-t border-gray-200 dark:border-gray-700 my-1"></div>
                  
                  {/* Limpiar conversación */}
                  <button
                    onClick={() => {
                      onClearMessages()
                      setShowMenu(false)
                    }}
                    className="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                  >
                    <span>🗑️</span>
                    <span>Limpiar conversación</span>
                  </button>
                  
                  {/* Información */}
                  <button
                    onClick={() => setShowMenu(false)}
                    className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                  >
                    <span>ℹ️</span>
                    <span>Acerca de</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Header
