import {
  fetchAchievementAttachment,
  fetchContextDetail,
  fetchContextWorkflows,
  uploadAchievementAttachment,
  type Context,
  type WorkflowList,
} from '../contexts/context-service'

export async function fetchWorkbenchContext(contextId: string, signal?: AbortSignal): Promise<Context> {
  return fetchContextDetail(contextId, signal)
}

export async function fetchWorkbenchWorkflows(contextId: string, signal?: AbortSignal): Promise<WorkflowList> {
  return fetchContextWorkflows(contextId, signal)
}

export async function fetchWorkbenchAchievementAttachment(
  attachmentId: string,
  signal?: AbortSignal,
): Promise<ReturnType<typeof fetchAchievementAttachment>> {
  return fetchAchievementAttachment(attachmentId, signal)
}

export async function uploadWorkbenchAchievementAttachment(
  cardId: string,
  file: File,
  options: { actor?: string; requestId?: string; idempotencyKey?: string } = {},
  signal?: AbortSignal,
): Promise<ReturnType<typeof uploadAchievementAttachment>> {
  return uploadAchievementAttachment(cardId, file, options, signal)
}
