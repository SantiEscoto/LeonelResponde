import React from 'react'
import type { Message } from '../types'

interface MessageBubbleProps {
  message: Message
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user'
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`message-bubble ${
        isUser ? 'message-user' : 'message-assistant'
      }`}>
        <div className="flex flex-col">
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          
          <div className={`text-xs mt-1 flex items-center space-x-2 ${
            isUser ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'
          }`}>
            <span>{message.timestamp.toLocaleTimeString()}</span>
            
            {message.status === 'sending' && (
              <div className="flex space-x-1">
                <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            )}
            
            {message.status === 'error' && (
              <span className="text-red-500">⚠️ Error</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default MessageBubble
