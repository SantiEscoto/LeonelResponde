import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { apiClient, chatAPI } from '../services/api'

export interface LlmStatus {
  is_loaded?: boolean
  model_path?: string
  model_name?: string
  [key: string]: unknown
}

export interface ApiStatusResponse {
  status?: string
  llm?: LlmStatus
  uptime?: number
  [key: string]: unknown
}

function fetchStatus(): Promise<ApiStatusResponse> {
  const apiWithMaybeGetStatus = chatAPI as unknown as {
    getStatus?: () => Promise<ApiStatusResponse>
  }
  if (typeof apiWithMaybeGetStatus.getStatus === 'function') {
    return apiWithMaybeGetStatus.getStatus()
  }
  return apiClient
    .get<ApiStatusResponse>('/status')
    .then((r) => r?.data ?? ({} as ApiStatusResponse))
}

export function useApiStatusQuery(): UseQueryResult<ApiStatusResponse, unknown> {
  return useQuery<ApiStatusResponse, unknown>({
    queryKey: ['status'],
    queryFn: fetchStatus,
    refetchInterval: 10000,
    staleTime: 5000,
    retry: 2,
  })
}