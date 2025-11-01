import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query'
import { chatAPI, apiUtils } from '../services/api'
import { useChatStore } from '../store/chatStore'

interface SendMessageVariables {
  message: string
}

interface SendMessageContext {
  assistantMessageId: string
}

export function useSendMessageMutation(): UseMutationResult<{ response: string }, unknown, SendMessageVariables, SendMessageContext> {
  const queryClient = useQueryClient()
  const { addMessage, updateMessage, setLoading } = useChatStore()

  return useMutation<{ response: string }, unknown, SendMessageVariables, SendMessageContext>({
    mutationKey: ['chat', 'sendMessage'],
    mutationFn: async ({ message }: SendMessageVariables) => {
      return await chatAPI.sendMessage(message)
    },
    onMutate: async ({ message }: SendMessageVariables): Promise<SendMessageContext> => {
      await queryClient.cancelQueries({ queryKey: ['chat'] })
      setLoading(true)
      addMessage({ content: message, role: 'user' })
      const assistantMessageId = addMessage({ content: '', role: 'assistant', status: 'sending' })
      return { assistantMessageId }
    },
    onSuccess: (data: { response: string }, _vars: SendMessageVariables, ctx?: SendMessageContext) => {
      if (ctx?.assistantMessageId) {
        updateMessage(ctx.assistantMessageId, {
          content: data.response,
          status: 'sent'
        })
      }
    },
    onError: (error: unknown, _vars: SendMessageVariables, ctx?: SendMessageContext) => {
      const errorMessage = apiUtils.handleError(error)
      if (ctx?.assistantMessageId) {
        updateMessage(ctx.assistantMessageId, {
          content: `Lo siento, hubo un error al procesar tu mensaje: ${errorMessage}`,
          status: 'error'
        })
      }
    },
    onSettled: async () => {
      setLoading(false)
      await queryClient.invalidateQueries({ queryKey: ['status'] })
    }
  })
}