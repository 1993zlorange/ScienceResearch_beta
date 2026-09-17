import type { components } from '../../../../../packages/contracts/scienceresearch-api'

export type Context = components['schemas']['ContextDTO']
export type ContextList = components['schemas']['ContextListDTO']
export type CreatedContext = components['schemas']['CreatedContextDTO']
export type Workflow = components['schemas']['WorkflowDTO']
export type WorkflowList = components['schemas']['WorkflowListDTO']
export type Progress = components['schemas']['ProgressDTO']
export type AchievementAttachment = components['schemas']['AchievementAttachmentDTO']
export type AchievementCard = components['schemas']['AchievementCardDTO']
export type DisclosurePreference = components['schemas']['DisclosurePreferenceDTO']
export type DisclosurePreferenceList = components['schemas']['DisclosurePreferenceListDTO']
export type UiSession = components['schemas']['UiSessionIssueResultDTO']
export type CompletionAuthorization = components['schemas']['CompletionAuthorizationResultDTO']
export type WorkflowRecord = components['schemas']['WorkflowRecordDTO']
export type ContextDeletionPrepare = components['schemas']['ContextDeletionPrepareResultDTO']
export type ContextDeletionCommitResult = components['schemas']['ContextDeletionCommitResultDTO']

export interface DisclosurePreferenceInput {
  disclosure_kind: 'area' | 'progress' | 'work_package' | 'card' | 'directory'
  stable_subject_id: string
  requested_is_expanded: boolean
  local_user_key?: string
  expected_version: number
}

export interface CreateUiSessionInput {
  actor?: string
  display_label?: string
}

export interface CreateCompletionAuthorizationInput {
  expected_version: number
  operation: 'complete' | 'cancel'
  session_id: string
}

export interface CreateContextInput {
  type?: string
  name?: string
  problem: string
  goal?: string
  owner?: string
}

export interface CreateAchievementCardInput {
  context_id: string
  workflow_id: string
  event_date: string
  event_name: string
  description?: string
  actor?: string
  important?: boolean
}

const JSON_CONTENT_TYPE = 'application/json'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly detail: string

  constructor(status: number, code: string, detail: string) {
    super(detail || code)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.detail = detail || code
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function problemText(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
}

async function readError(response: Response, fallback: string): Promise<ApiError> {
  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }
  if (isRecord(payload)) {
    const code = problemText(payload.code) ?? `HTTP_${response.status}`
    const detail = problemText(payload.detail) ?? fallback
    return new ApiError(response.status, code, detail)
  }
  return new ApiError(response.status, `HTTP_${response.status}`, fallback)
}

async function requestJson<T>(path: string, init: RequestInit, fallbackError: string): Promise<T> {
  const response = await fetch(path, { credentials: 'same-origin', ...init })
  if (!response.ok) {
    throw await readError(response, fallbackError)
  }
  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError(response.status, 'INVALID_RESPONSE', '服务返回了无效 JSON')
  }
}

export function achievementCardsFromWorkflow(workflow: Workflow): AchievementCard[] {
  return workflow.achievement_cards.map((rawCard) => {
    if (!isRecord(rawCard)) {
      throw new ApiError(200, 'INVALID_RESPONSE', '成效卡数据格式无效')
    }
    if (!isAchievementCardShape(rawCard)) {
      throw new ApiError(200, 'INVALID_RESPONSE', '成效卡数据格式无效')
    }
    return rawCard
  })
}

function isAchievementCardShape(value: Record<string, unknown>): value is AchievementCard {
  return (
    typeof value.id === 'string' &&
    typeof value.context_id === 'string' &&
    typeof value.workflow_id === 'string' &&
    typeof value.work_package_id === 'string' &&
    (typeof value.week_item_id === 'string' || value.week_item_id === null) &&
    typeof value.event_date === 'string' &&
    typeof value.event_name === 'string' &&
    typeof value.description === 'string' &&
    typeof value.status === 'string' &&
    typeof value.is_important === 'boolean' &&
    typeof value.row_version === 'number' &&
    typeof value.created_at === 'string' &&
    typeof value.updated_at === 'string' &&
    Array.isArray(value.attachments)
  )
}

export async function fetchContexts(signal?: AbortSignal): Promise<ContextList> {
  return requestJson<ContextList>('/api/v1/contexts', { signal }, '课题列表加载失败')
}

export async function createContext(input: CreateContextInput, signal?: AbortSignal): Promise<CreatedContext> {
  return requestJson<CreatedContext>('/api/v1/contexts', {
    method: 'POST',
    headers: { 'content-type': JSON_CONTENT_TYPE },
    body: JSON.stringify(input),
    signal,
  }, '课题创建失败')
}

export async function fetchContextDetail(contextId: string, signal?: AbortSignal): Promise<Context> {
  return requestJson<Context>(
    `/api/v1/contexts/${encodeURIComponent(contextId)}`,
    { signal },
    '课题详情加载失败',
  )
}

export async function fetchContextWorkflows(contextId: string, signal?: AbortSignal): Promise<WorkflowList> {
  return requestJson<WorkflowList>(
    `/api/v1/contexts/${encodeURIComponent(contextId)}/workflows`,
    { signal },
    '工作流加载失败',
  )
}

export async function createAchievementCard(
  input: CreateAchievementCardInput,
  signal?: AbortSignal,
): Promise<AchievementCard> {
  return requestJson<AchievementCard>('/api/v1/achievement-cards', {
    method: 'POST',
    headers: { 'content-type': JSON_CONTENT_TYPE },
    body: JSON.stringify(input),
    signal,
  }, '成效卡创建失败')
}



export async function uploadAchievementAttachment(
  cardId: string,
  file: File,
  options: { actor?: string; requestId?: string; idempotencyKey?: string } = {},
  signal?: AbortSignal,
): Promise<AchievementAttachment> {
  const body = new FormData()
  body.append('file', file)
  body.append('actor', options.actor || 'author')
  if (options.requestId) body.append('request_id', options.requestId)
  if (options.idempotencyKey) body.append('idempotency_key', options.idempotencyKey)
  const response = await fetch(
    `/api/v1/achievement-cards/${encodeURIComponent(cardId)}/attachments`,
    { method: 'POST', credentials: 'same-origin', body, signal },
  )
  if (!response.ok) throw await readError(response, '附件上传失败')
  try {
    return (await response.json()) as AchievementAttachment
  } catch {
    throw new ApiError(response.status, 'INVALID_RESPONSE', '服务返回了无效 JSON')
  }
}

export async function fetchAchievementAttachment(
  attachmentId: string,
  signal?: AbortSignal,
): Promise<AchievementAttachment> {
  return requestJson<AchievementAttachment>(
    `/api/v1/achievement-attachments/${encodeURIComponent(attachmentId)}`,
    { signal },
    '附件加载失败',
  )
}

export function achievementAttachmentDownloadUrl(attachmentId: string): string {
  return `/api/v1/achievement-attachments/${encodeURIComponent(attachmentId)}/download`
}

export function achievementAttachmentPreviewUrl(
  attachmentId: string,
  representation: 'metadata' | 'document' = 'document',
): string {
  return `/api/v1/achievement-attachments/${encodeURIComponent(attachmentId)}/preview?representation=${representation}`
}

export async function fetchDisclosurePreferences(
  contextId: string,
  signal?: AbortSignal,
): Promise<DisclosurePreferenceList> {
  return requestJson<DisclosurePreferenceList>(
    `/api/v1/contexts/${encodeURIComponent(contextId)}/disclosure-preferences`,
    { signal },
    '披露偏好加载失败',
  )
}

export async function upsertDisclosurePreference(
  contextId: string,
  input: DisclosurePreferenceInput,
  signal?: AbortSignal,
): Promise<DisclosurePreference> {
  return requestJson<DisclosurePreference>(
    `/api/v1/contexts/${encodeURIComponent(contextId)}/disclosure-preferences`,
    {
      method: 'POST',
      headers: { 'content-type': JSON_CONTENT_TYPE },
      body: JSON.stringify(input),
      signal,
    },
    '披露偏好保存失败',
  )
}

export async function createUiSession(
  input: CreateUiSessionInput = {},
  signal?: AbortSignal,
): Promise<UiSession> {
  return requestJson<UiSession>('/api/v1/ui/session', {
    method: 'POST',
    headers: { 'content-type': JSON_CONTENT_TYPE },
    body: JSON.stringify(input),
    signal,
  }, '工作会话创建失败')
}

export async function createCompletionAuthorization(
  workflowId: string,
  input: CreateCompletionAuthorizationInput,
  signal?: AbortSignal,
): Promise<CompletionAuthorization> {
  return requestJson<CompletionAuthorization>(
    `/api/v1/workflows/${encodeURIComponent(workflowId)}/completion-authorization`,
    {
      method: 'POST',
      headers: { 'content-type': JSON_CONTENT_TYPE },
      body: JSON.stringify(input),
      signal,
    },
    '完成授权获取失败',
  )
}

export async function setWorkflowCompletion(
  workflowId: string,
  input: {
    completed: boolean
    expected_version: number
    session_id: string
    nonce_id: string
    nonce_hash: string
  },
  signal?: AbortSignal,
): Promise<WorkflowRecord> {
  return requestJson<WorkflowRecord>(
    `/api/v1/workflows/${encodeURIComponent(workflowId)}/completion`,
    {
      method: 'POST',
      headers: { 'content-type': JSON_CONTENT_TYPE },
      body: JSON.stringify(input),
      signal,
    },
    '工作包状态保存失败',
  )
}

export async function setAchievementCardImportance(
  contextId: string,
  workflowId: string,
  cardId: string,
  input: { is_important: boolean; expected_version: number; actor?: string },
  signal?: AbortSignal,
): Promise<{ card_id: string; is_important: boolean; changed: boolean; row_version: number }> {
  return requestJson(
    `/api/v1/contexts/${encodeURIComponent(contextId)}/workflows/${encodeURIComponent(workflowId)}/achievement-cards/${encodeURIComponent(cardId)}/importance`,
    {
      method: 'PATCH',
      headers: { 'content-type': JSON_CONTENT_TYPE },
      body: JSON.stringify(input),
      signal,
    },
    '成效卡标记保存失败',
  )
}

export async function prepareContextDeletion(
  contextId: string,
  input: { retain_files: boolean; expected_version: number; session_id: string },
  signal?: AbortSignal,
): Promise<ContextDeletionPrepare> {
  return requestJson<ContextDeletionPrepare>(
    `/api/v1/contexts/${encodeURIComponent(contextId)}/deletion/prepare`,
    {
      method: 'POST',
      headers: { 'content-type': JSON_CONTENT_TYPE },
      body: JSON.stringify(input),
      signal,
    },
    '删除准备失败',
  )
}

export async function commitContextDeletion(
  contextId: string,
  input: { operation_id: string; confirmation: string; session_id: string },
  signal?: AbortSignal,
): Promise<ContextDeletionCommitResult> {
  return requestJson<ContextDeletionCommitResult>(
    `/api/v1/contexts/${encodeURIComponent(contextId)}/deletion/commit`,
    {
      method: 'POST',
      headers: { 'content-type': JSON_CONTENT_TYPE },
      body: JSON.stringify(input),
      signal,
    },
    '课题删除失败',
  )
}
