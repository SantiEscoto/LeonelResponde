import React from 'react'

const Badge: React.FC<{ label: string; color?: string }> = ({ label, color = 'bg-blue-600' }) => (
  <span className={`${color} text-white text-xs px-2 py-1 rounded-md mr-2 mb-2 inline-flex items-center`}>{label}</span>
)

const TechBadges: React.FC = () => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  return (
    <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Tecnologías activas en esta UI</h3>
      <div className="flex flex-wrap">
        {/* Frontend stack */}
        <Badge label="React" color="bg-blue-600" />
        <Badge label="TypeScript" color="bg-indigo-600" />
        <Badge label="Vite" color="bg-purple-600" />
        <Badge label="Zustand" color="bg-teal-600" />
        <Badge label="TailwindCSS" color="bg-cyan-600" />

        {/* Integración */}
        <Badge label={`REST API (${apiUrl})`} color="bg-gray-700" />
        <Badge label="WS Voice" color="bg-gray-700" />

        {/* Voz */}
        <Badge label="STT: Vosk + VAD (16 kHz)" color="bg-green-600" />
        <Badge label="TTS: Coqui XTTS v2" color="bg-green-600" />
        <Badge label="TTS fallback: pyttsx3" color="bg-green-600" />

        {/* Endpoints visibles */}
        <Badge label="WS STT: ws://localhost:8010/ws/stt" color="bg-orange-600" />
        <Badge label="WS TTS: ws://localhost:8010/ws/tts" color="bg-orange-600" />
      </div>
      <p className="text-xs text-gray-600 dark:text-gray-300 mt-2">
        Los módulos de voz están operativos via WebSocket. Puedes probar STT y TTS abajo.
      </p>
    </div>
  )
}

export default TechBadges