import { computed, toValue, type Ref } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import {
  createCompletionAuthorization,
  createUiSession,
  fetchDisclosurePreferences,
  setAchievementCardImportance,
  setWorkflowCompletion,
  upsertDisclosurePreference,
  type DisclosurePreferenceInput,
} from '../contexts/context-service'
import {
  fetchWorkbenchAchievementAttachment,
  fetchWorkbenchContext,
  fetchWorkbenchWorkflows,
  uploadWorkbenchAchievementAttachment,
} from './context-workbench-service'

export function workbenchContextQueryKey(contextId: string) {
  return ['context', contextId] as const
}

export function workbenchWorkflowsQueryKey(contextId: string) {
  return ['context', contextId, 'workflows'] as const
}

export function useContextDetailQuery(contextId: MaybeRefOrGetter<string>) {
  const resolvedContextId = computed(() => toValue(contextId))
  return useQuery({
    queryKey: computed(() => workbenchContextQueryKey(resolvedContextId.value)),
    queryFn: ({ signal }) => fetchWorkbenchContext(resolvedContextId.value, signal),
    enabled: computed(() => resolvedContextId.value.length > 0),
    staleTime: 15_000,
    retry: 1,
  })
}

export function useContextWorkbenchWorkflowsQuery(contextId: MaybeRefOrGetter<string>) {
  const resolvedContextId = computed(() => toValue(contextId))
  return useQuery({
    queryKey: computed(() => workbenchWorkflowsQueryKey(resolvedContextId.value)),
    queryFn: ({ signal }) => fetchWorkbenchWorkflows(resolvedContextId.value, signal),
    enabled: computed(() => resolvedContextId.value.length > 0),
    staleTime: 15_000,
    retry: 1,
  })
}

export function workbenchDisclosureQueryKey(contextId: string) {
  return ['context', contextId, 'disclosure-preferences'] as const
}

export function useContextDisclosurePreferencesQuery(contextId: MaybeRefOrGetter<string>) {
  const resolvedContextId = computed(() => toValue(contextId))
  return useQuery({
    queryKey: computed(() => workbenchDisclosureQueryKey(resolvedContextId.value)),
    queryFn: ({ signal }) => fetchDisclosurePreferences(resolvedContextId.value, signal),
    enabled: computed(() => resolvedContextId.value.length > 0),
    staleTime: Infinity,
    retry: 1,
  })
}

export function useDisclosurePreferenceMutation(contextId: MaybeRefOrGetter<string>) {
  const queryClient = useQueryClient()
  const resolvedContextId = computed(() => toValue(contextId))
  return useMutation({
    mutationFn: (input: DisclosurePreferenceInput) =>
      upsertDisclosurePreference(resolvedContextId.value, input),
    onSuccess: async (preference) => {
      queryClient.setQueryData(
        workbenchDisclosureQueryKey(resolvedContextId.value),
        (current: Awaited<ReturnType<typeof fetchDisclosurePreferences>> | undefined) => {
          if (!current) return current
          const preferences = current.preferences.filter((item) => !(
            item.disclosure_kind === preference.disclosure_kind &&
            item.stable_subject_id === preference.stable_subject_id
          ))
          preferences.push(preference)
          preferences.sort((left, right) =>
            left.disclosure_kind.localeCompare(right.disclosure_kind) ||
            left.stable_subject_id.localeCompare(right.stable_subject_id),
          )
          return { ...current, preferences }
        },
      )
    },
  })
}

export function achievementAttachmentQueryKey(attachmentId: string) {
  return ['achievement-attachment', attachmentId] as const
}

export function useAchievementAttachmentQuery(attachmentId: MaybeRefOrGetter<string>) {
  const resolvedAttachmentId = computed(() => toValue(attachmentId))
  return useQuery({
    queryKey: computed(() => achievementAttachmentQueryKey(resolvedAttachmentId.value)),
    queryFn: ({ signal }) => fetchWorkbenchAchievementAttachment(resolvedAttachmentId.value, signal),
    enabled: computed(() => resolvedAttachmentId.value.length > 0),
    staleTime: 15_000,
    retry: 0,
  })
}

export function useAchievementAttachmentUploadMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: {
      cardId: string
      file: File
      actor?: string
      requestId?: string
      idempotencyKey?: string
    }) => uploadWorkbenchAchievementAttachment(input.cardId, input.file, {
      actor: input.actor,
      requestId: input.requestId,
      idempotencyKey: input.idempotencyKey,
    }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['context'] })
    },
  })
}

export function useWorkflowCompletionMutation(
  contextId: MaybeRefOrGetter<string>,
  uiSessionId: Ref<string | null>,
) {
  const queryClient = useQueryClient()
  const resolvedContextId = computed(() => toValue(contextId))
  return useMutation({
    mutationFn: async (input: { workflowId: string; expectedVersion: number; completed: boolean }) => {
      let sessionId = uiSessionId.value
      if (!sessionId) {
        const session = await createUiSession({ actor: 'author', display_label: '作者' })
        sessionId = session.session_id
        uiSessionId.value = sessionId
      }
      const authorization = await createCompletionAuthorization(input.workflowId, {
        expected_version: input.expectedVersion,
        operation: input.completed ? 'complete' : 'cancel',
        session_id: sessionId,
      })
      const workflow = await setWorkflowCompletion(input.workflowId, {
        completed: input.completed,
        expected_version: input.expectedVersion,
        session_id: sessionId,
        nonce_id: authorization.nonce_id,
        nonce_hash: authorization.nonce_hash,
      })
      return workflow
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['context', resolvedContextId.value, 'workflows'] })
    },
  })
}

export function useAchievementCardImportanceMutation(
  contextId: MaybeRefOrGetter<string>,
) {
  const queryClient = useQueryClient()
  const resolvedContextId = computed(() => toValue(contextId))
  return useMutation({
    mutationFn: (input: {
      workflowId: string
      cardId: string
      isImportant: boolean
      expectedVersion: number
    }) => setAchievementCardImportance(
      resolvedContextId.value,
      input.workflowId,
      input.cardId,
      {
        is_important: input.isImportant,
        expected_version: input.expectedVersion,
        actor: 'author',
      },
    ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['context', resolvedContextId.value, 'workflows'] })
    },
  })
}