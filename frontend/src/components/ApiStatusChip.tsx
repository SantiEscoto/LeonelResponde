import React from 'react'
import { useApiStatusQuery } from '../hooks/useApiStatusQuery'
import type { ApiStatusResponse, LlmStatus } from '../hooks/useApiStatusQuery'

const ApiStatusChip: React.FC = () => {
  const { data, isLoading, error, refetch } = useApiStatusQuery()

  const llm = (data as ApiStatusResponse | undefined)?.llm as LlmStatus | undefined
  const isMock = !!(llm?.model_name === 'mock-llm')
  const isReal = !!(llm && !isMock && ((typeof llm.is_loaded !== 'undefined') || (typeof llm.model_path !== 'undefined')))
  const isLoaded = !!llm?.is_loaded
  const modelName = llm?.model_path ? String(llm.model_path).split(/[\\/]/).pop() : llm?.model_name

  let color = 'bg-gray-200 text-gray-800'
  let label = 'API: verificando...'
  let title = ''

  if (isLoading) {
    color = 'bg-gray-200 text-gray-800'
    label = 'API: verificando...'
  } else if (error) {
    color = 'bg-red-100 text-red-800'
    label = 'API: error'
    title = error instanceof Error ? error.message : 'Error desconocido'
  } else if (data) {
    if (isMock) {
      color = 'bg-yellow-100 text-yellow-800'
      label = 'API: mock'
      title = 'Backend de pruebas (mock-llm)'
    } else if (isReal) {
      if (isLoaded) {
        color = 'bg-green-100 text-green-800'
        label = 'API: LLM activo'
      } else {
        color = 'bg-yellow-100 text-yellow-800'
        label = 'API: LLM no cargado'
      }
      if (modelName) {
        title = `Modelo: ${modelName}`
      }
    } else {
      color = 'bg-yellow-100 text-yellow-800'
      label = 'API: desconocida'
      title = 'No se detectó estado de LLM'
    }
  }

  return (
    <button
      onClick={() => refetch()}
      className={`px-2 py-1 rounded text-xs font-medium ${color}`}
      title={title || undefined}
    >
      {label}
    </button>
  )
}

export default ApiStatusChip