import React from 'react'

interface StatusIndicatorProps {
  connected: boolean
  showText?: boolean
  size?: 'sm' | 'md' | 'lg'
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ 
  connected, 
  showText = true,
  size = 'sm'
}) => {
  const sizeClasses = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3',
    lg: 'w-4 h-4'
  }
  
  const textSizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base'
  }
  
  return (
    <div className="flex items-center space-x-2">
      <div className={`${sizeClasses[size]} rounded-full ${
        connected 
          ? 'bg-green-500 animate-pulse' 
          : 'bg-red-500'
      }`} />
      
      {showText && (
        <span className={`${textSizeClasses[size]} ${
          connected 
            ? 'text-green-600 dark:text-green-400' 
            : 'text-red-600 dark:text-red-400'
        }`}>
          {connected ? 'Conectado' : 'Desconectado'}
        </span>
      )}
    </div>
  )
}

export default StatusIndicator
