import { computed, toValue } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import {
  createAchievementCard,
  createContext,
  fetchContexts,
  fetchContextWorkflows,
  type CreateAchievementCardInput,
  type CreateContextInput,
} from './context-service'

export const contextsQueryKey = ['contexts'] as const
export const contextWorkflowsQueryRootKey = ['contexts', 'workflows'] as const

export function contextWorkflowsQueryKey(contextId: string) {
  return [...contextWorkflowsQueryRootKey, contextId] as const
}

export function useContextsQuery() {
  return useQuery({
    queryKey: contextsQueryKey,
    queryFn: ({ signal }) => fetchContexts(signal),
    staleTime: 30_000,
    retry: 1,
  })
}

export function useContextWorkflowsQuery(contextId: MaybeRefOrGetter<string | undefined>) {
  const resolvedContextId = computed(() => toValue(contextId) ?? '')
  return useQuery({
    queryKey: computed(() => contextWorkflowsQueryKey(resolvedContextId.value)),
    queryFn: ({ signal }) => {
      if (!resolvedContextId.value) {
        throw new Error('未选择课题')
      }
      return fetchContextWorkflows(resolvedContextId.value, signal)
    },
    enabled: computed(() => Boolean(resolvedContextId.value)),
    staleTime: 15_000,
    retry: 1,
  })
}

export function useCreateContextMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateContextInput) => createContext(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: contextsQueryKey })
    },
  })
}

export function useCreateAchievementCardMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateAchievementCardInput) => createAchievementCard(input),
    onSuccess: async () => {
      // Native workbench workflows use the singular context-scoped key; the
      // explicit prefix also refreshes any future context workflow views.
      await queryClient.invalidateQueries({ queryKey: ['context'] })
      await queryClient.invalidateQueries({ queryKey: contextWorkflowsQueryRootKey })
    },
  })
}

