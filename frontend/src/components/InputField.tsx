import React, { useState, useRef, useEffect } from 'react'
import type { KeyboardEvent } from 'react'
import MicButton from './MicButton'

interface InputFieldProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  onKeyPress?: (e: KeyboardEvent) => void
  disabled?: boolean
  placeholder?: string
  maxLength?: number
  // Nuevo: envío directo cuando hay texto final de voz
  onFinalSend?: (value: string) => void
}

const InputField: React.FC<InputFieldProps> = ({
  value,
  onChange,
  onSend,
  onKeyPress,
  disabled = false,
  placeholder = "Escribe tu mensaje...",
  maxLength = 2000,
  onFinalSend,
}) => {
  const [isComposing, setIsComposing] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [value])

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault()
      onSend()
    }
    onKeyPress?.(e)
  }
  
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value
    if (newValue.length <= maxLength) {
      onChange(newValue)
    }
  }
  
  const handleCompositionStart = () => {
    setIsComposing(true)
  }
  
  const handleCompositionEnd = () => {
    setIsComposing(false)
  }
  
  return (
    <div className="flex items-end space-x-2">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyPress={handleKeyPress}
          onCompositionStart={handleCompositionStart}
          onCompositionEnd={handleCompositionEnd}
          disabled={disabled}
          placeholder={placeholder}
          className="input-field resize-none"
          rows={1}
          style={{ 
            minHeight: '40px', 
            maxHeight: '120px',
            lineHeight: '1.5'
          }}
        />
        
        {/* Character counter */}
        {value.length > 0 && (
          <div className="absolute bottom-1 right-2 text-xs text-gray-400">
            {value.length}/{maxLength}
          </div>
        )}
      </div>
      
      <MicButton
        onPartialText={(t) => onChange(t)}
        onFinalText={(t) => {
          // Actualiza el input y, si está definido, envía directo
          onChange(t)
          if (t.trim()) {
            // Evita leer estado desactualizado en padre, ofrece canal directo
            onFinalSend?.(t.trim())
          }
        }}
      />
      
      <button
        onClick={onSend}
        disabled={disabled || !value.trim()}
        className="btn-primary flex items-center space-x-2"
        title="Enviar mensaje (Enter)"
      >
        <svg 
          className="w-4 h-4" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" 
          />
        </svg>
        <span>Enviar</span>
      </button>
    </div>
  )
}

export default InputField
