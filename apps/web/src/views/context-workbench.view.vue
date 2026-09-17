<template>
  <main class="workbench-page" data-testid="context-workbench">
    <div v-if="detailQuery.isLoading.value" class="state-loading" role="status">课题详情加载中…</div>
    <div v-else-if="detailQuery.error.value" class="state-error" role="alert">
      <p>{{ errorMessage(detailQuery.error.value, '课题详情加载失败') }}</p>
      <button type="button" data-testid="context-detail-retry" @click="detailQuery.refetch()">重试</button>
      <RouterLink to="/contexts">返回课题列表</RouterLink>
    </div>

    <template v-else-if="context">
      <ContextToolbar :context-id="context.id" />
      <ContextSummary :context="context" />
      <div v-if="disclosureError" class="state-error" role="alert" data-testid="disclosure-error">{{ disclosureError }}</div>

      <div v-if="workflowsQuery.isLoading.value" class="state-loading" role="status">工作包目录加载中…</div>
      <div v-else-if="workflowsQuery.error.value" class="state-error" role="alert">
        <p>{{ errorMessage(workflowsQuery.error.value, '工作包目录加载失败') }}</p>
        <button type="button" data-testid="workflows-retry" @click="workflowsQuery.refetch()">重试</button>
      </div>
      <div v-else-if="catalogQuery.isLoading.value" class="state-loading" role="status">研究方面目录加载中…</div>
      <div v-else-if="catalogQuery.error.value" class="state-error" role="alert">
        <p>{{ errorMessage(catalogQuery.error.value, '研究方面目录加载失败') }}</p>
        <button type="button" data-testid="catalog-retry" @click="catalogQuery.refetch()">重试</button>
      </div>

      <template v-else-if="workflows && catalog">
        <ContextFiltersPanel
          :filters="filters"
          :area-names="catalog.areas.map((area) => area.name)"
          :result-count="filteredItems.length"
          @apply="applyFilters"
          @clear="clearFilters"
        />
        <ContextProgressPanel
          :progress="workflows.progress"
          :expanded="progressExpanded"
          :visible-cards="visibleCards"
          @toggle="toggleProgress"
        />

        <nav class="workbench-view-switch" aria-label="课题工作台视图">
          <button
            type="button"
            :class="{ active: !workflowsView }"
            :aria-current="!workflowsView ? 'true' : undefined"
            data-testid="show-package-view"
            @click="showPackageView"
          >工作包视图</button>
          <button
            type="button"
            :class="{ active: workflowsView }"
            :aria-current="workflowsView ? 'true' : undefined"
            data-testid="show-workflow-view"
            @click="showWorkflowView"
          >12 工作流视图</button>
        </nav>

        <div
          v-if="allItems.length === 0"
          class="empty-state"
          data-testid="workbench-empty-workflows"
          role="status"
        >
          <h2>当前课题没有可用工作包</h2>
          <p>请返回课题列表创建新的课题，或检查课题工作流快照。</p>
          <RouterLink to="/contexts">返回课题列表</RouterLink>
        </div>

        <template v-else-if="workflowsView">
          <div v-if="workflowMapQuery.isLoading.value" class="state-loading" role="status">12 工作流地图加载中…</div>
          <div v-else-if="workflowMapQuery.error.value" class="state-error" role="alert">
            <p>{{ errorMessage(workflowMapQuery.error.value, '12 工作流地图加载失败') }}</p>
            <button type="button" data-testid="workflow-map-retry" @click="workflowMapQuery.refetch()">重试</button>
          </div>
          <ResearchWorkflowMapPanel
            v-else-if="workflowMap"
            :workflow-items="workflowViewItems"
            :selected-workflow-id="selectedWorkflowIdValue"
            @select-workflow="selectResearchWorkflow"
            @open-work-package="openWorkPackageFromWorkflow"
          />
        </template>

        <div v-else class="context-v5" :class="{ 'preview-active': previewPresent }" data-renderer-version="context-v5-b2">
          <WorkPackageDirectory
            :catalog="catalog"
            :items="filteredItems"
            :all-count="allItems.length"
            :unassigned-count="unassignedWorkflows.length"
            :selected-work-package-id="selectedWorkPackageIdValue"
            :expanded-area-ids="expandedAreaIds"
            :expanded-package-ids="expandedPackageIds"
            :directory-expanded="directoryExpanded"
            :important-only="filters.important"
            @toggle-directory="toggleDirectory"
            @toggle-area="toggleArea"
            @toggle-package="togglePackage"
            @select="selectWorkPackage"
          >
            <template #default="{ item }">
              <WorkPackageDetail
                :key="item.package.id"
                :workflow="item.workflow"
                :package="item.package"
                :expanded-card-ids="expandedCardIds"
                :completion-busy="completionBusy && completionTargetId === item.package.id"
                :completion-error="completionTargetId === item.package.id ? completionError : ''"
                :completion-success="completionSuccessPackageId === item.package.id"
                :card-create-busy="cardCreateBusy && cardCreateTargetId === item.package.id"
                :card-create-error="cardCreateTargetId === item.package.id ? cardCreateError : ''"
                :card-create-success="cardCreateSuccessPackageId === item.package.id"
                :card-form="cardFormFor(item)"
                :card-form-invalid="cardFormInvalidFor(item)"
                :importance-busy="importanceBusy"
                :importance-card-id="importanceCardId"
                :importance-error="importanceError"
                :importance-success-card-id="importanceSuccessCardId"
                :attachment-busy="attachmentBusy"
                :attachment-card-id="attachmentCardId"
                :attachment-error="attachmentError"
                :attachment-success-card-id="attachmentSuccessCardId"
                :active-preview-id="urlState.preview"
                @toggle-importance="setCardImportance"
                @upload-attachment="uploadAttachment"
                @preview-attachment="openPreview"
                @toggle-card="toggleCard"
                @complete="setCompletion(true, item)"
                @cancel-completion="setCompletion(false, item)"
                @create-card="submitCard(item)"
              />
            </template>
          </WorkPackageDirectory>

          <section v-if="previewPresent" class="context-main-pane">
            <div class="preview-toolbar">
              <button
                type="button"
                data-testid="preview-rail-toggle"
                :aria-expanded="urlState.previewRail === 'auto_compact' ? 'false' : 'true'"
                aria-controls="work-package-directory"
                @click="togglePreviewRail"
              >{{ urlState.previewRail === 'auto_compact' ? '展开工作包目录' : '紧凑工作包目录' }}</button>
              <button type="button" data-testid="preview-close" @click="closePreview">关闭预览，返回工作包</button>
            </div>
            <section
              class="preview-empty-state"
              data-preview-state="ACTIVE"
              data-testid="workbench-preview-state"
              aria-label="附件原文预览"
            >
              <h2>附件原文预览</h2>
              <div v-if="attachmentPreviewQuery.isLoading.value" class="state-loading" role="status">附件预览加载中…</div>
              <div v-else-if="attachmentPreviewQuery.error.value" class="state-error" role="alert">
                <p data-testid="preview-error">{{ attachmentErrorMessage(attachmentPreviewQuery.error.value) }}</p>
                <button type="button" @click="attachmentPreviewQuery.refetch()">重试</button>
              </div>
              <iframe
                v-else
                title="附件原文预览"
                data-testid="attachment-preview-frame"
                :src="achievementAttachmentPreviewUrl(urlState.preview)"
              ></iframe>
            </section>
          </section>
        </div>
      </template>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCatalogQuery, useResearchWorkflowMapQuery } from '../features/catalog/use-catalog-query'
import {
  ApiError,
  achievementAttachmentPreviewUrl,
  achievementCardsFromWorkflow,
  type AchievementAttachment,
  type AchievementCard,
} from '../features/contexts/context-service'
import ContextFiltersPanel from '../features/context-workbench/components/context-filters-panel.vue'
import ContextProgressPanel from '../features/context-workbench/components/context-progress-panel.vue'
import ContextSummary from '../features/context-workbench/components/context-summary.vue'
import ContextToolbar from '../features/context-workbench/components/context-toolbar.vue'
import ResearchWorkflowMapPanel from '../features/context-workbench/components/research-workflow-map-panel.vue'
import WorkPackageDirectory from '../features/context-workbench/components/work-package-directory.vue'
import WorkPackageDetail from '../features/context-workbench/components/work-package-detail.vue'
import {
  buildWorkbenchItems,
  filterWorkbenchItems,
  readWorkbenchFilters,
  readWorkbenchUrlState,
  buildResearchWorkflowViewItems,
  selectedResearchWorkflowId,
  selectedWorkPackageId,
  visibleCardSummaries,
  type WorkbenchFilters,
  type WorkbenchItem,
} from '../features/context-workbench/context-workbench-model'
import {
  useAchievementAttachmentQuery,
  useAchievementAttachmentUploadMutation,
  useAchievementCardImportanceMutation,
  useContextDetailQuery,
  useContextDisclosurePreferencesQuery,
  useContextWorkbenchWorkflowsQuery,
  useDisclosurePreferenceMutation,
  useWorkflowCompletionMutation,
} from '../features/context-workbench/use-context-workbench-queries'
import { useCreateAchievementCardMutation } from '../features/contexts/use-context-queries'

const route = useRoute()
const router = useRouter()
const contextId = computed(() => String(route.params.contextId ?? ''))
const detailQuery = useContextDetailQuery(contextId)
const workflowsQuery = useContextWorkbenchWorkflowsQuery(contextId)
const catalogQuery = useCatalogQuery()
const disclosureQuery = useContextDisclosurePreferencesQuery(contextId)
const saveDisclosure = useDisclosurePreferenceMutation(contextId)
const uiSessionId = ref<string | null>(null)
const completeWorkflowMutation = useWorkflowCompletionMutation(contextId, uiSessionId)
const createCardMutation = useCreateAchievementCardMutation()
const toggleImportanceMutation = useAchievementCardImportanceMutation(contextId)

const context = computed(() => detailQuery.data.value ?? null)
const workflows = computed(() => workflowsQuery.data.value ?? null)
const catalog = computed(() => catalogQuery.data.value ?? null)

const urlState = computed(() => readWorkbenchUrlState(route.query))
const filters = computed(() => readWorkbenchFilters(route.query))
const workflowsView = computed(() => urlState.value.view === 'workflows')
const workflowMapQuery = useResearchWorkflowMapQuery({ enabled: workflowsView })

const preferenceVersion = computed(() => {
  const rows = disclosureQuery.data.value?.preferences ?? []
  return new Map(rows.map((row) => [`${row.disclosure_kind}:${row.stable_subject_id}`, row]))
})

const workbenchData = computed(() => {
  if (!catalog.value || !workflows.value) return null
  const normalizedWorkflows = workflows.value.workflows.map((workflow) => ({
    ...workflow,
    achievement_cards: achievementCardsFromWorkflow(workflow),
  }))
  return buildWorkbenchItems(catalog.value, normalizedWorkflows)
})
const allItems = computed(() => workbenchData.value?.items ?? [])
const unassignedWorkflows = computed(() => workbenchData.value?.unassigned ?? [])
const filteredItems = computed(() => filterWorkbenchItems(allItems.value, filters.value))
const selectedWorkPackageIdValue = computed(() => selectedWorkPackageId(urlState.value.wp, allItems.value))
const visibleCards = computed(() => visibleCardSummaries(filteredItems.value, filters.value))
const previewPresent = computed(() => urlState.value.preview.length > 0)
const workflowMap = computed(() => workflowMapQuery.data.value ?? null)
const workflowViewItems = computed(() =>
  workflowMap.value ? buildResearchWorkflowViewItems(workflowMap.value, filteredItems.value) : [],
)
const selectedWorkflowIdValue = computed(() => selectedResearchWorkflowId(urlState.value.workflow, workflowMap.value))
const attachmentPreviewQuery = useAchievementAttachmentQuery(previewPresent ? urlState.value.preview : '')
const uploadAttachmentMutation = useAchievementAttachmentUploadMutation()

const persistedExpanded = (kind: string, subject: string) => {
  const row = preferenceVersion.value.get(`${kind}:${subject}`)
  return row ? row.is_expanded : kind === 'directory'
}
const directoryPersisted = computed(() => persistedExpanded('directory', 'context-directory'))
const directoryExpanded = computed(() => {
  if (urlState.value.previewRail === 'auto_compact') return false
  // Explicit URL state is a deep-link override; persisted state applies only
  // when directory is not present in the URL.
  if (urlState.value.directory === 'expanded') return true
  if (urlState.value.directory === 'collapsed') return false
  if (urlState.value.previewRail === 'user_expanded') return true
  return directoryPersisted.value
})
const progressExpanded = computed(() => persistedExpanded('progress', 'context-progress'))
const expandedAreaIds = shallowRef(new Set<string>())
const expandedPackageIds = shallowRef(new Set<string>())
const expandedCardIds = shallowRef(new Set<string>())
const disclosureBusy = ref(false)
const disclosureError = ref('')
let disclosureQueue: Promise<void> = Promise.resolve()
let hydratedPreferences = false

watch(
  [catalog, disclosureQuery.data],
  ([value, preferenceList]) => {
    if (!value || hydratedPreferences) return
    // Context v5 exposes catalogue areas by default; persisted rows then override
    // individual areas without making a missing row mean "collapsed".
    const areaRows = new Set(value.areas.map((area) => area.id))
    const rows = preferenceList?.preferences ?? []
    for (const row of rows.filter((row) => row.disclosure_kind === 'area')) {
      if (row.is_expanded) areaRows.add(row.stable_subject_id)
      else areaRows.delete(row.stable_subject_id)
    }
    const packageRows = new Set(
      rows
        .filter((row) => row.disclosure_kind === 'work_package' && row.is_expanded)
        .map((row) => row.stable_subject_id),
    )
    expandedAreaIds.value = areaRows
    expandedPackageIds.value = packageRows
    hydratedPreferences = true
  },
  { immediate: true },
)

watch(
  [allItems, selectedWorkPackageIdValue],
  ([items, selectedId]) => {
    if (!items.length || !selectedId) return
    if (expandedPackageIds.value.has(selectedId)) return
    const next = new Set(expandedPackageIds.value)
    next.add(selectedId)
    expandedPackageIds.value = next
  },
  { immediate: true },
)

watch(
  [disclosureQuery.data, urlState],
  ([preferenceList, state]) => {
    const cards = new Set(
      preferenceList?.preferences
        .filter((row) => row.disclosure_kind === 'card' && row.is_expanded)
        .map((row) => row.stable_subject_id) ?? [],
    )
    if (state?.card) cards.add(state.card)
    expandedCardIds.value = cards
  },
  { immediate: true },
)

watch(
  [allItems, urlState],
  ([items, state]) => {
    if (!items.length) return
    if (state.wp && items.some((item) => item.package.id === state.wp)) return
    const fallback = selectedWorkPackageId(state.wp, items)
    if (fallback && fallback !== state.wp) void pushQuery({ wp: fallback })
  },
  { immediate: true },
)

function buildQuery(overrides: Partial<{
  wp: string | undefined
  area: string | undefined
  status: string | undefined
  query: string | undefined
  important: boolean | undefined
  card: string | undefined
  directory: 'expanded' | 'collapsed'
  preview: string | undefined
  previewRail: '' | 'auto_compact' | 'user_expanded'
  view: 'packages' | 'workflows'
  workflow: string | undefined
}> = {}): Record<string, string> {
  const merged = {
    wp: selectedWorkPackageIdValue.value ?? '',
    area: filters.value.area,
    status: filters.value.status,
    query: filters.value.query,
    important: filters.value.important,
    card: urlState.value.card,
    directory: urlState.value.directory,
    preview: urlState.value.preview,
    previewRail: urlState.value.previewRail,
    view: urlState.value.view,
    workflow: urlState.value.workflow,
    ...overrides,
  }

  const query: Record<string, string> = {}
  const set = (key: string, value: string | boolean | undefined) => {
    if (value === true) query[key] = 'true'
    else if (typeof value === 'string' && value) query[key] = value
  }
  set('wp', merged.wp)
  set('area', merged.area)
  set('status', merged.status)
  set('query', merged.query)
  set('important', merged.important)
  set('card', merged.card)
  set('directory', merged.directory === 'collapsed' ? merged.directory : '')
  set('preview', merged.preview)
  set('preview_rail', merged.preview ? merged.previewRail : '')
  set('view', merged.view === 'workflows' ? merged.view : '')
  set('workflow', merged.view === 'workflows' ? merged.workflow : '')
  return query
}

async function pushQuery(overrides?: Parameters<typeof buildQuery>[0]) {
  await router.push({ path: route.path, query: buildQuery(overrides) })
}

function applyFilters(nextFilters: WorkbenchFilters) {
  void pushQuery({
    area: nextFilters.area,
    status: nextFilters.status,
    query: nextFilters.query,
    important: nextFilters.important,
  })
}

function clearFilters() {
  void pushQuery({ area: '', status: '', query: '', important: false })
}

function ensurePackageExpanded(workPackageId: string, persist: boolean) {
  const next = new Set(expandedPackageIds.value)
  if (persist) next.delete(selectedWorkPackageIdValue.value ?? '')
  next.add(workPackageId)
  expandedPackageIds.value = next
  if (persist) void saveExpanded('work_package', workPackageId, true)
}

function selectWorkPackage(workPackageId: string) {
  ensurePackageExpanded(workPackageId, true)
  void pushQuery({
    wp: workPackageId,
    card: '',
    preview: '',
    previewRail: '',
  })
}

function showPackageView() {
  void pushQuery({ view: 'packages' })
}

function showWorkflowView() {
  void pushQuery({ view: 'workflows' })
}

function selectResearchWorkflow(workflowId: string) {
  void pushQuery({ workflow: workflowId, view: 'workflows' })
}

function openWorkPackageFromWorkflow(workPackageId: string) {
  ensurePackageExpanded(workPackageId, true)
  void pushQuery({
    view: 'packages',
    workflow: '',
    wp: workPackageId,
    card: '',
    preview: '',
    previewRail: '',
  })
}

async function saveExpanded(
  kind: 'directory' | 'progress' | 'area' | 'work_package' | 'card',
  subject: string,
  expanded: boolean,
): Promise<void> {
  const run = async (): Promise<void> => {
    disclosureBusy.value = true
    disclosureError.value = ''
    const existing = preferenceVersion.value.get(`${kind}:${subject}`)
    try {
      await saveDisclosure.mutateAsync({
        disclosure_kind: kind,
        stable_subject_id: subject,
        requested_is_expanded: expanded,
        expected_version: existing?.row_version ?? 0,
      })
    } catch (error) {
      if (error instanceof ApiError && (error.status === 409 || error.code === 'VERSION_CONFLICT')) {
        await disclosureQuery.refetch()
        const latest = preferenceVersion.value.get(`${kind}:${subject}`)
        if (latest?.is_expanded === expanded) return
        if (latest) {
          await saveDisclosure.mutateAsync({
            disclosure_kind: kind,
            stable_subject_id: subject,
            requested_is_expanded: expanded,
            expected_version: latest.row_version,
          })
          return
        }
      }
      if (error instanceof ApiError && error.status === 503) {
        disclosureError.value = '服务暂时不可用，偏好未保存，请稍后重试。'
      } else {
        disclosureError.value = errorMessage(error, '披露偏好保存失败')
      }
    } finally {
      disclosureBusy.value = false
    }
  }
  disclosureQueue = disclosureQueue.then(run, run)
  await disclosureQueue
}

function toggleDirectory() {
  const next = !directoryExpanded.value
  void pushQuery({
    directory: next ? 'expanded' : 'collapsed',
    previewRail: '',
  })
  void saveExpanded('directory', 'context-directory', next)
}

function toggleProgress() {
  void saveExpanded('progress', 'context-progress', !progressExpanded.value)
}

function toggleArea(areaId: string) {
  const expanded = !expandedAreaIds.value.has(areaId)
  const next = new Set(expandedAreaIds.value)
  if (expanded) next.add(areaId)
  else next.delete(areaId)
  expandedAreaIds.value = next
  void saveExpanded('area', areaId, expanded)
}

function togglePackage(workPackageId: string) {
  if (workPackageId === selectedWorkPackageIdValue.value) return
  const expanded = !expandedPackageIds.value.has(workPackageId)
  const next = new Set(expandedPackageIds.value)
  if (expanded) next.add(workPackageId)
  else next.delete(workPackageId)
  expandedPackageIds.value = next
  void saveExpanded('work_package', workPackageId, expanded)
}

function toggleCard(cardId: string) {
  const expanded = !expandedCardIds.value.has(cardId)
  const next = new Set(expandedCardIds.value)
  if (expanded) next.add(cardId)
  else next.delete(cardId)
  expandedCardIds.value = next
  void pushQuery({ card: expanded ? cardId : '' })
  void saveExpanded('card', cardId, expanded)
}

function togglePreviewRail() {
  void pushQuery({
    previewRail: urlState.value.previewRail === 'auto_compact' ? 'user_expanded' : 'auto_compact',
  })
}

function closePreview() {
  void pushQuery({ preview: '', previewRail: '' })
}

function attachmentErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return error.code === 'NOT_FOUND' ? '附件不存在，可能已被删除。' : '附件文件缺失，请联系维护人员。'
    if (error.status === 403) return '没有权限执行附件操作。'
    if (error.status === 409) return '附件校验不一致，请重新上传。'
    if (error.code === 'FILE_TOO_LARGE') return '附件超过系统允许的大小。'
    if (error.code === 'INVALID_FILENAME') return '附件文件名无效，请重命名后上传。'
    if (error.code === 'EXTENSION_NOT_ALLOWED') return '不支持该附件扩展名。'
    if (error.code === 'MIME_TYPE_NOT_ALLOWED') return '附件内容类型与扩展名不一致。'
    if (error.code === 'SIGNATURE_MISMATCH') return '附件内容校验失败，请检查文件是否损坏。'
    if (error.code === 'ATTACHMENT_LIMIT') return '当前成效卡附件数量已达上限。'
    if (error.code === 'DUPLICATE_FILENAME') return '同名附件已存在。'
    return errorMessage(error, '附件操作失败')
  }
  if (error instanceof TypeError) return '网络连接失败，请检查服务后重试。'
  return '附件操作失败'
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    if (error.status === 409 || error.code === 'VERSION_CONFLICT') return '数据已被其他操作更新，请刷新后重试。'
    if (error.status === 403) return '授权无效或已过期，请刷新页面后重试。'
    if (error.status === 404) return '课题不存在或已被删除。'
    if (error.status === 422) return '提交内容无效，请检查必填字段后重试。'
    return error.detail || fallback
  }
  return fallback
}

const completionTargetId = ref('')
const completionBusy = computed(() => completeWorkflowMutation.isPending.value)
const completionError = computed(() => completeWorkflowMutation.error.value ? errorMessage(completeWorkflowMutation.error.value, '完成状态保存失败') : '')
const completionSuccessPackageId = ref('')

async function setCompletion(completed: boolean, item: WorkbenchItem) {
  completionSuccessPackageId.value = ''
  completionTargetId.value = item.package.id
  try {
    await completeWorkflowMutation.mutateAsync({
      workflowId: item.workflow.id,
      expectedVersion: item.workflow.row_version,
      completed,
    })
    completionSuccessPackageId.value = item.package.id
  } catch {
    // Mutation state owns the displayed error; this boundary prevents an
    // unhandled rejection while the button remains interactive-safe.
  }
}

interface CardFormState {
  event_date: string
  event_name: string
  description: string
  important: boolean
}

const cardForms = ref<Record<string, CardFormState>>({})
const cardCreateTargetId = ref('')
const cardCreateBusy = computed(() => createCardMutation.isPending.value)
const cardCreateError = computed(() => createCardMutation.error.value ? errorMessage(createCardMutation.error.value, '成效卡创建失败') : '')
const cardCreateSuccessPackageId = ref('')

function cardFormFor(item: WorkbenchItem): CardFormState {
  const existing = cardForms.value[item.package.id]
  if (existing) return existing
  const created: CardFormState = {
    event_date: new Date().toISOString().slice(0, 10),
    event_name: '',
    description: '',
    important: false,
  }
  cardForms.value[item.package.id] = created
  return created
}

function cardFormInvalidFor(item: WorkbenchItem): boolean {
  const form = cardFormFor(item)
  return !form.event_date || !form.event_name.trim()
}

async function submitCard(item: WorkbenchItem) {
  const form = cardFormFor(item)
  if (cardFormInvalidFor(item)) return
  cardCreateSuccessPackageId.value = ''
  cardCreateTargetId.value = item.package.id
  try {
    await createCardMutation.mutateAsync({
      context_id: item.workflow.context_id,
      workflow_id: item.workflow.id,
      event_date: form.event_date,
      event_name: form.event_name.trim(),
      description: form.description.trim(),
      important: form.important,
    })
    cardCreateSuccessPackageId.value = item.package.id
    form.event_name = ''
    form.description = ''
    form.important = false
  } catch {
    // Mutation state owns the displayed error.
  }
}

const attachmentCardId = ref('')
const attachmentBusy = computed(() => uploadAttachmentMutation.isPending.value)
const attachmentError = ref('')
const attachmentSuccessCardId = ref('')

async function uploadAttachment(cardId: string, file: File) {
  attachmentError.value = ''
  attachmentSuccessCardId.value = ''
  attachmentCardId.value = cardId
  try {
    await uploadAttachmentMutation.mutateAsync({
      cardId,
      file,
      actor: 'author',
      requestId: crypto.randomUUID(),
      idempotencyKey: crypto.randomUUID(),
    })
    attachmentSuccessCardId.value = cardId
  } catch (error) {
    attachmentError.value = attachmentErrorMessage(error)
  }
}

function openPreview(attachment: AchievementAttachment) {
  const owningItem = allItems.value.find((item) =>
    item.workflow.achievement_cards.some((card) => card.id === attachment.card_id),
  )
  void pushQuery({
    wp: owningItem?.package.id ?? selectedWorkPackageIdValue.value,
    card: attachment.card_id,
    preview: attachment.id,
  })
}

const importanceCardId = ref('')
const importanceBusy = computed(() => toggleImportanceMutation.isPending.value)
const importanceError = ref('')
const importanceSuccessCardId = ref('')

async function setCardImportance(card: AchievementCard, important: boolean) {
  importanceError.value = ''
  importanceSuccessCardId.value = ''
  importanceCardId.value = card.id
  try {
    await toggleImportanceMutation.mutateAsync({
      workflowId: card.workflow_id,
      cardId: card.id,
      isImportant: important,
      expectedVersion: card.row_version,
    })
    importanceSuccessCardId.value = card.id
  } catch (error) {
    importanceError.value = errorMessage(error, '成效卡标记保存失败')
  }
}
</script>

<style scoped>
.workbench-page {
  --wb-bg: #eef4f7;
  --wb-bg-2: #f7fafb;
  --wb-panel: #ffffff;
  --wb-soft: #f5f9fb;
  --wb-ink: #16232d;
  --wb-title: #102f3d;
  --wb-muted: #64757f;
  --wb-border: #dbe7ec;
  --wb-border-strong: #c4d6dd;
  --wb-primary: #176b8f;
  --wb-primary-dark: #0f5371;
  --wb-primary-soft: #e7f2f7;
  --wb-accent: #c96d21;
  --wb-success: #22744f;
  --wb-success-soft: #e9f7ef;
  --wb-warning: #825d09;
  --wb-warning-soft: #fff4d9;
  --wb-danger: #a52c28;
  --wb-danger-soft: #fff3f2;
  --wb-radius-lg: 18px;
  --wb-radius-md: 12px;
  --wb-radius-sm: 8px;
  --wb-shadow: 0 18px 45px rgb(15 48 64 / 0.09);
  --wb-line: #e6eef2;
  position: relative;
  width: min(1560px, calc(100% - 32px));
  margin: 18px auto 40px;
  padding: 24px 26px 32px;
  overflow: hidden;
  color: var(--wb-ink);
  background:
    radial-gradient(circle at 92% 4%, rgb(23 107 143 / 0.10), transparent 26rem),
    linear-gradient(135deg, var(--wb-bg) 0%, var(--wb-bg-2) 48%, #eef7f3 100%);
  border: 1px solid rgb(255 255 255 / 0.72);
  border-radius: 24px;
  box-shadow: var(--wb-shadow);
}

.workbench-page :deep(*) {
  box-sizing: border-box;
}

.workbench-page :deep(h2),
.workbench-page :deep(h3),
.workbench-page :deep(h4) {
  margin: 0;
  color: var(--wb-title);
  font-weight: 800;
  letter-spacing: -0.015em;
}

.workbench-page :deep(button) {
  font: inherit;
  transition: border-color 0.18s ease, background-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.workbench-page :deep(button:focus-visible),
.workbench-page :deep(a:focus-visible),
.workbench-page :deep(input:focus-visible),
.workbench-page :deep(select:focus-visible),
.workbench-page :deep(textarea:focus-visible) {
  outline: 3px solid rgb(23 107 143 / 0.32);
  outline-offset: 2px;
}

.workbench-page :deep(input:not([type='checkbox'])),
.workbench-page :deep(select),
.workbench-page :deep(textarea) {
  width: 100%;
  min-height: 38px;
  padding: 8px 11px;
  border: 1px solid var(--wb-border-strong);
  border-radius: var(--wb-radius-sm);
  background: #fff;
  color: var(--wb-ink);
  box-shadow: inset 0 1px 2px rgb(16 43 58 / 0.04);
}

.workbench-page :deep(input::placeholder),
.workbench-page :deep(textarea::placeholder) {
  color: #90a1aa;
}

.workbench-page :deep(.primary) {
  min-height: 38px;
  padding: 9px 16px;
  border: 0;
  border-radius: var(--wb-radius-sm);
  background: linear-gradient(135deg, var(--wb-primary), var(--wb-primary-dark));
  color: #fff;
  font-weight: 750;
  box-shadow: 0 7px 18px rgb(15 83 113 / 0.18);
}

.workbench-page :deep(.primary:hover:not(:disabled)) {
  background: linear-gradient(135deg, #1a7ca6, var(--wb-primary-dark));
  transform: translateY(-1px);
}

.workbench-page :deep(button[type='button']:not(.primary):not(.card-toggle):not(.area-toggle):not(.wp-toggle):not(.disclosure-toggle)) {
  min-height: 34px;
  padding: 7px 12px;
  border: 1px solid var(--wb-border-strong);
  border-radius: var(--wb-radius-sm);
  background: #fff;
  color: #31505e;
  font-weight: 650;
}

.workbench-page :deep(button[type='button']:not(.primary):hover:not(:disabled)) {
  border-color: #95b8c4;
  background: #f8fcfd;
  color: var(--wb-primary-dark);
  transform: translateY(-1px);
}

.workbench-page :deep(button:disabled) {
  cursor: not-allowed;
  opacity: 0.58;
  transform: none !important;
  box-shadow: none !important;
}

/* Toolbar */
.workbench-page :deep(.context-toolbar) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.workbench-page :deep(.back-link) {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 8px 14px;
  border: 1px solid rgb(255 255 255 / 0.8);
  border-radius: 999px;
  background: rgb(255 255 255 / 0.82);
  color: var(--wb-primary-dark);
  font-weight: 750;
  text-decoration: none;
  box-shadow: 0 5px 16px rgb(16 47 61 / 0.06);
}

.workbench-page :deep(.back-link:hover) {
  background: #fff;
  transform: translateY(-1px);
}

.workbench-page :deep(.back-link::before) {
  content: '←';
  font-size: 0.95em;
}

.workbench-page :deep(.delete-area) {
  display: grid;
  gap: 5px;
  justify-items: end;
}

.workbench-page :deep(.delete-button) {
  min-height: 36px;
  padding: 8px 14px;
  border: 1px solid #e4b6b2;
  border-radius: var(--wb-radius-sm);
  background: var(--wb-danger-soft);
  color: var(--wb-danger);
  font-weight: 720;
}

.workbench-page :deep(.delete-button:hover:not(:disabled)) {
  border-color: #d28b85;
  background: #ffeae8;
  transform: translateY(-1px);
}

/* Context hero */
.workbench-page :deep(.context-summary) {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 34%);
  gap: 22px;
  align-items: center;
  margin-bottom: 18px;
  padding: 24px 26px;
  overflow: hidden;
  position: relative;
  border: 1px solid #215c74;
  border-radius: var(--wb-radius-lg);
  background:
    radial-gradient(circle at 100% 0%, rgb(255 255 255 / 0.16), transparent 20rem),
    linear-gradient(125deg, #10404f 0%, #176b8f 58%, #258a99 100%);
  color: #f7fcfd;
  box-shadow: 0 18px 38px rgb(9 52 68 / 0.22);
}

.workbench-page :deep(.context-summary::after) {
  content: '';
  position: absolute;
  right: -64px;
  bottom: -82px;
  width: 220px;
  height: 220px;
  border: 28px solid rgb(255 255 255 / 0.055);
  border-radius: 50%;
  pointer-events: none;
}

.workbench-page :deep(.context-summary > div) {
  min-width: 0;
}

.workbench-page :deep(.context-summary h2) {
  margin-bottom: 7px;
  color: #fff;
  font-size: clamp(1.45rem, 2.2vw, 2.05rem);
  line-height: 1.2;
}

.workbench-page :deep(.context-summary > div > p) {
  margin: 0;
  max-width: 70ch;
  color: rgb(234 247 250 / 0.9);
  font-size: 0.96rem;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.workbench-page :deep(.context-summary dl) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 18px 0 0;
}

.workbench-page :deep(.context-summary dl div) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 1px solid rgb(255 255 255 / 0.16);
  border-radius: 999px;
  background: rgb(255 255 255 / 0.11);
  color: #ecf8fa;
  font-size: 0.79rem;
}

.workbench-page :deep(.context-summary dt) {
  color: rgb(229 245 249 / 0.72);
  font-weight: 650;
}

.workbench-page :deep(.context-summary dd) {
  margin: 0;
  font-weight: 750;
  overflow-wrap: anywhere;
}

.workbench-page :deep(.context-goal) {
  position: relative;
  z-index: 1;
  margin: 0;
  padding: 18px 18px 17px;
  border: 1px solid rgb(255 255 255 / 0.12);
  border-radius: var(--wb-radius-md);
  background: rgb(9 44 56 / 0.2);
  color: #fff;
  font-size: 0.92rem;
  line-height: 1.65;
  backdrop-filter: blur(6px);
}

.workbench-page :deep(.context-goal)::first-line {
  font-weight: 800;
}

/* Filters and progress */
.workbench-page :deep(.context-filters) {
  display: grid;
  grid-template-columns: minmax(190px, 1.25fr) minmax(145px, 0.85fr) minmax(135px, 0.75fr) minmax(150px, 0.8fr) auto;
  gap: 14px;
  align-items: end;
  margin-bottom: 14px;
  padding: 16px 18px;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-lg);
  background: var(--wb-panel);
  box-shadow: 0 8px 22px rgb(15 48 64 / 0.05);
}

.workbench-page :deep(.context-filters label) {
  gap: 7px;
  color: #415863;
  font-size: 0.78rem;
  font-weight: 750;
  text-transform: uppercase;
}

.workbench-page :deep(.important-filter) {
  display: flex !important;
  align-items: center;
  align-self: end;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid var(--wb-border-strong);
  border-radius: var(--wb-radius-sm);
  background: var(--wb-soft);
  text-transform: none;
}

.workbench-page :deep(.important-filter input) {
  width: 16px;
  height: 16px;
  min-height: 0;
  accent-color: var(--wb-primary);
}

.workbench-page :deep(.filter-actions) {
  display: flex;
  gap: 8px;
  align-items: end;
  min-height: 38px;
}

.workbench-page :deep(.batch-note),
.workbench-page :deep([data-testid='workbench-filter-count']) {
  grid-column: 1 / -1;
  margin: 0;
  color: var(--wb-muted);
  font-size: 0.78rem;
}

.workbench-page :deep([data-testid='workbench-filter-count']) {
  padding-left: 10px;
  border-left: 3px solid #a9cdd9;
  font-weight: 700;
  color: var(--wb-primary-dark);
}

.workbench-page :deep(.progress-panel) {
  margin-bottom: 16px;
  padding: 15px 18px;
  border: 1px solid #cfe2d8;
  border-left: 5px solid #3f8d69;
  border-radius: var(--wb-radius-lg);
  background: linear-gradient(90deg, #f4faf6, #fff 38%);
  box-shadow: 0 7px 20px rgb(15 48 64 / 0.05);
}

.workbench-page :deep(.disclosure-toggle) {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #20694a;
  font-size: 0.92rem;
}

.workbench-page :deep(.disclosure-toggle)::before {
  content: '';
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #489d70;
  box-shadow: 0 0 0 4px #dcefe5;
}

.workbench-page :deep(.progress-panel [data-testid='workbench-progress-value']) {
  display: inline-flex;
  margin: 12px 0 0;
  padding: 7px 11px;
  border-radius: 999px;
  background: #e8f4ee;
  color: #23664a;
  font-weight: 800;
}

.workbench-page :deep(.progress-cards) {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #dcebe3;
}

.workbench-page :deep(.progress-cards h3) {
  font-size: 0.87rem;
}

.workbench-page :deep(.progress-cards ul) {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
  margin: 9px 0 0;
  padding: 0;
  list-style: none;
}

.workbench-page :deep(.progress-cards li) {
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid #dcebe3;
  border-radius: var(--wb-radius-sm);
  background: #fff;
}

.workbench-page :deep(.progress-cards span) {
  display: block;
  overflow-wrap: anywhere;
  font-weight: 700;
}

.workbench-page :deep(.progress-cards small) {
  display: block;
  margin-top: 2px;
  color: var(--wb-muted);
  overflow-wrap: anywhere;
}

.workbench-page :deep(.warning) {
  padding: 7px 9px;
  border-radius: var(--wb-radius-sm);
  background: var(--wb-warning-soft);
  color: var(--wb-warning);
}

/* Inline workspace; preview restores a two-column rail */
.workbench-page :deep(.context-v5) {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
  align-items: start;
  margin-top: 0;
}

.workbench-page :deep(.work-package-directory),
.workbench-page :deep(.work-package-detail),
.workbench-page :deep(.preview-empty-state) {
  min-width: 0;
  padding: 18px;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-lg);
  background: var(--wb-panel);
  box-shadow: 0 12px 30px rgb(15 48 64 / 0.06);
}

.workbench-page :deep(.panel-head) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 11px;
  border-bottom: 1px solid var(--wb-line);
}

.workbench-page :deep(.panel-head .badge) {
  padding: 5px 9px;
  border-radius: 999px;
  background: var(--wb-primary-soft);
  color: var(--wb-primary-dark);
  font-size: 0.75rem;
  font-weight: 750;
}

.workbench-page :deep(.work-package-directory .disclosure-toggle),
.workbench-page :deep(.work-package-detail h2) {
  font-size: 1.02rem;
}

.workbench-page :deep(.directory-body) {
  max-height: min(74vh, 900px);
  overflow: auto;
  padding-right: 5px;
  scrollbar-width: thin;
}

.workbench-page :deep(.context-area) {
  margin-top: 16px;
}

.workbench-page :deep(.context-area:first-child) {
  margin-top: 14px;
}

.workbench-page :deep(.context-area h3),
.workbench-page :deep(.area-heading) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin: 0 0 9px;
}

.workbench-page :deep(.area-toggle) {
  padding: 5px 0;
  color: var(--wb-title);
  font-size: 0.95rem;
}

.workbench-page :deep(.badge) {
  white-space: nowrap;
}

.workbench-page :deep(.context-wp-list) {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.workbench-page :deep(.work-package-card) {
  width: 100%;
  min-width: 0;
  min-height: 104px;
  display: grid;
  align-content: start;
  gap: 5px;
  padding-bottom: 11px;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-md);
  background: #fff;
  box-shadow: 0 3px 10px rgb(16 47 61 / 0.04);
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.workbench-page :deep(.work-package-card:hover),
.workbench-page :deep(.work-package-card:focus-within) {
  border-color: #8db8c6;
  box-shadow: 0 9px 22px rgb(23 59 87 / 0.1);
  transform: translateY(-1px);
}

.workbench-page :deep(.work-package-card.state-has-cards) {
  background: linear-gradient(180deg, #fffdf5, #fff 68%);
  border-color: #e7d092;
}

.workbench-page :deep(.work-package-card.state-complete) {
  background: linear-gradient(180deg, #f3fbf6, #fff 68%);
  border-color: #a7cbb7;
}

.workbench-page :deep(.work-package-card:has([aria-current='true'])) {
  border-color: var(--wb-primary);
  background: linear-gradient(180deg, #f3fafd, #fff 72%);
  box-shadow: inset 4px 0 0 var(--wb-primary), 0 9px 22px rgb(15 83 113 / 0.12);
}

.workbench-page :deep(.wp-heading) {
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 5px;
  padding: 10px 11px 0;
}

.workbench-page :deep(.wp-toggle) {
  display: grid;
  gap: 3px;
  color: var(--wb-ink);
}

.workbench-page :deep(.wp-code) {
  color: var(--wb-accent);
  font-size: 0.71rem;
  font-weight: 850;
  letter-spacing: 0.045em;
}

.workbench-page :deep(.wp-toggle strong) {
  min-width: 0;
  overflow-wrap: anywhere;
  line-height: 1.35;
}

.workbench-page :deep(.wp-status) {
  justify-self: end;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eaf1f4;
  color: #49626d;
  font-size: 0.7rem;
  font-weight: 800;
  white-space: nowrap;
}

.workbench-page :deep(.state-has-cards .wp-status) {
  background: var(--wb-warning-soft);
  color: var(--wb-warning);
}

.workbench-page :deep(.state-complete .wp-status) {
  background: var(--wb-success-soft);
  color: var(--wb-success);
}

.workbench-page :deep(.wp-select) {
  grid-column: 1 / -1;
  justify-self: start;
  min-height: 28px;
  padding: 4px 9px;
  border: 1px solid #c9dfe8;
  border-radius: 999px;
  background: var(--wb-primary-soft);
  color: var(--wb-primary-dark);
  font-size: 0.76rem;
  font-weight: 750;
}

.workbench-page :deep(.work-package-card > p) {
  margin: 0;
  padding: 0 11px;
  color: #52646d;
  font-size: 0.8rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.workbench-page :deep(.directory-card-list) {
  margin: 5px 0 0;
  padding: 0 11px 0 26px;
  color: var(--wb-muted);
  font-size: 0.78rem;
}

.workbench-page :deep(.empty-group),
.workbench-page :deep(.muted) {
  color: var(--wb-muted);
  font-size: 0.8rem;
}

.workbench-page :deep(.unassigned-workflows) {
  padding: 12px;
  border: 1px dashed #d9c091;
  border-radius: var(--wb-radius-md);
  background: #fffaf0;
}

/* Detail pane */
.workbench-page :deep(.work-package-detail) {
  position: static;
  max-height: none;
  overflow: visible;
  margin: 10px 0 0;
}

.workbench-page :deep(.detail-fields) {
  gap: 0;
  margin: 14px 0 0;
  padding: 3px 0 0;
  border: 1px solid var(--wb-line);
  border-radius: var(--wb-radius-md);
  background: #fbfdfe;
  overflow: hidden;
}

.workbench-page :deep(.detail-fields div) {
  grid-template-columns: 94px minmax(0, 1fr);
  gap: 10px;
  padding: 9px 11px;
}

.workbench-page :deep(.detail-fields div + div) {
  border-top: 1px solid var(--wb-line);
}

.workbench-page :deep(.detail-fields dt) {
  color: var(--wb-muted);
  font-size: 0.79rem;
  font-weight: 750;
}

.workbench-page :deep(.detail-fields dd) {
  margin: 0;
  font-size: 0.87rem;
  overflow-wrap: anywhere;
}

.workbench-page :deep(.detail-actions) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 13px;
}

.workbench-page :deep(.detail-block) {
  margin-top: 18px;
}

.workbench-page :deep(.detail-label) {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 16px 0 5px;
  color: var(--wb-primary-dark);
  font-size: 0.74rem;
  letter-spacing: 0.055em;
  text-transform: uppercase;
}

.workbench-page :deep(.detail-label)::before {
  content: '';
  width: 5px;
  height: 14px;
  border-radius: 2px;
  background: linear-gradient(#2d94b8, var(--wb-primary-dark));
}

.workbench-page :deep(.detail-block > p:not(.detail-label)) {
  margin: 0;
  padding: 10px 12px;
  border-left: 3px solid #d8e8ee;
  border-radius: 0 var(--wb-radius-sm) var(--wb-radius-sm) 0;
  background: #fafcfd;
  color: #384b55;
  font-size: 0.88rem;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

/* Card create and achievement cards */
.workbench-page :deep(.card-create-panel) {
  margin-top: 20px;
  padding: 14px 14px 16px;
  border: 1px solid #cfe3ea;
  border-radius: var(--wb-radius-md);
  background: linear-gradient(180deg, #f8fcfd, #fff 70%);
}

.workbench-page :deep(.card-create-panel h3),
.workbench-page :deep(.selected-cards h3) {
  margin-bottom: 10px;
  font-size: 0.95rem;
}

.workbench-page :deep(.card-create-form) {
  display: grid;
  grid-template-columns: minmax(145px, 0.8fr) minmax(190px, 1.2fr);
  gap: 11px;
  margin-top: 0;
}

.workbench-page :deep(.card-create-form label) {
  gap: 6px;
  color: #4a616b;
  font-size: 0.8rem;
  font-weight: 720;
}

.workbench-page :deep(.card-create-form textarea),
.workbench-page :deep(.checkbox-label) {
  grid-column: 1 / -1;
}

.workbench-page :deep(.card-create-form textarea) {
  min-height: 76px;
  resize: vertical;
}

.workbench-page :deep(.checkbox-label) {
  display: flex !important;
  align-items: center;
  gap: 8px !important;
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid var(--wb-border-strong);
  border-radius: var(--wb-radius-sm);
  background: var(--wb-soft);
}

.workbench-page :deep(.checkbox-label input) {
  width: 16px;
  height: 16px;
  min-height: 0;
  accent-color: var(--wb-primary);
}

.workbench-page :deep(.card-create-form button[type='submit']) {
  grid-column: 1 / -1;
  justify-self: start;
}

.workbench-page :deep(.achievement-card) {
  overflow: hidden;
  margin-top: 10px;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-md);
  background: #fff;
  box-shadow: 0 4px 12px rgb(16 47 61 / 0.045);
}

.workbench-page :deep(.achievement-card.important) {
  border-color: #b7d8ab;
  background: linear-gradient(180deg, #f5fbf1, #fff 72%);
  box-shadow: inset 4px 0 0 #6da75e, 0 4px 14px rgb(64 112 53 / 0.07);
}

.workbench-page :deep(.card-heading) {
  min-height: 44px;
  align-items: center;
}

.workbench-page :deep(.card-toggle) {
  flex: 1;
  display: grid;
  gap: 3px;
  padding: 10px 12px;
  color: var(--wb-ink);
  text-align: left;
}

.workbench-page :deep(.card-toggle strong) {
  overflow-wrap: anywhere;
}

.workbench-page :deep(.card-toggle span) {
  width: fit-content;
  padding: 3px 7px;
  border-radius: 999px;
  background: #eef4f6;
  color: #516a74;
  font-size: 0.7rem;
  font-weight: 750;
}

.workbench-page :deep(.important .card-toggle span) {
  background: #e4f2dc;
  color: #3d7133;
}

.workbench-page :deep(.card-description) {
  margin: 0;
  padding: 0 12px 11px;
  color: #52646d;
  font-size: 0.84rem;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.workbench-page :deep(.card-actions) {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 12px;
  border-top: 1px solid var(--wb-line);
  background: #fafcfd;
}

.workbench-page :deep(.card-facts) {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
  margin: 0;
}

.workbench-page :deep(.card-facts div) {
  grid-template-columns: auto minmax(0, 1fr);
  gap: 5px;
  padding: 7px 9px;
  border: 1px solid var(--wb-line);
  border-radius: var(--wb-radius-sm);
  background: #fff;
}

.workbench-page :deep(.card-facts dt) {
  color: var(--wb-muted);
  font-size: 0.76rem;
  font-weight: 750;
}

.workbench-page :deep(.card-facts dd) {
  margin: 0;
  overflow-wrap: anywhere;
}

.workbench-page :deep(.importance-actions) {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 0;
}

.workbench-page :deep(.importance-actions button) {
  border: 1px solid #d9c689;
  border-radius: var(--wb-radius-sm);
  background: #fff8e3;
  color: #7b5a08;
  font-weight: 720;
}

.workbench-page :deep(.attachments) {
  padding-top: 11px;
  border-top: 1px dashed #d7e4e9;
}

.workbench-page :deep(.attachments h4) {
  margin-bottom: 7px;
  font-size: 0.85rem;
}

.workbench-page :deep(.attachment-list) {
  display: grid;
  gap: 6px;
  margin: 7px 0;
  padding: 0;
  list-style: none;
}

.workbench-page :deep(.attachment-row) {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border: 1px solid var(--wb-line);
  border-radius: var(--wb-radius-sm);
  background: #fff;
}

.workbench-page :deep(.attachment-preview) {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workbench-page :deep(.attachment-upload) {
  gap: 9px;
  margin-top: 8px;
}

.workbench-page :deep(.attachment-file-label) {
  gap: 6px;
  color: #4a616b;
  font-size: 0.8rem;
  font-weight: 720;
}

.workbench-page :deep(.attachment-upload input) {
  padding: 6px 8px;
  background: #fff;
}

.workbench-page :deep(.attachment-upload button) {
  justify-self: start;
}

.workbench-page :deep(.attachment-size) {
  color: var(--wb-muted);
  font-size: 0.75rem;
}

/* Status and preview */
.workbench-page :deep(.state-success),
.workbench-page :deep(.state-error),
.workbench-page :deep(.state-loading),
.workbench-page :deep(.empty-state) {
  margin: 0 0 12px;
  padding: 12px;
  border-radius: var(--wb-radius-md);
}

.workbench-page :deep(.state-success) {
  border: 1px solid #a9d7bd;
  background: var(--wb-success-soft);
  color: var(--wb-success);
  font-weight: 700;
}

.workbench-page :deep(.state-error) {
  border: 1px solid #e4b8b5;
  background: var(--wb-danger-soft);
  color: var(--wb-danger);
}

.workbench-page :deep(.state-loading),
.workbench-page :deep(.empty-state) {
  border: 1px dashed #b7cdd6;
  background: rgb(255 255 255 / 0.72);
  color: #4e636d;
}

.workbench-page :deep(.empty-state h2) {
  margin-bottom: 6px;
}

.workbench-page :deep(.preview-toolbar) {
  display: flex;
  margin-bottom: 10px;
}

.workbench-page :deep(.preview-empty-state) {
  border-left: 5px solid #4a8d9c;
}

.workbench-page :deep(.preview-empty-state iframe) {
  width: 100%;
  min-height: min(68vh, 700px);
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-md);
  background: #fff;
}


.workbench-page :deep(.context-v5.preview-active) {
  grid-template-columns: minmax(360px, 1fr) minmax(440px, 0.9fr);
}

.workbench-page :deep(.workbench-view-switch) {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  margin: 0 0 14px;
  padding: 5px;
  border: 1px solid var(--wb-border);
  border-radius: 999px;
  background: var(--wb-panel);
}

.workbench-page :deep(.workbench-view-switch button) {
  min-height: 32px;
  padding: 5px 13px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--wb-muted);
  font-weight: 750;
  cursor: pointer;
}

.workbench-page :deep(.workbench-view-switch button.active) {
  background: var(--wb-primary-soft);
  color: var(--wb-primary-dark);
}

.workbench-page :deep(.wp-inline-detail) {
  margin: 8px 11px 12px;
}

.workbench-page :deep(.work-package-card:has(.work-package-detail)) {
  grid-column: 1 / -1;
}

.workbench-page :deep(.wp-collapse) {
  justify-self: end;
  align-self: start;
  min-height: 26px;
  padding: 3px 8px;
  border: 1px solid #c9dfe8;
  border-radius: 999px;
  background: #fff;
  color: var(--wb-muted);
  font-size: 0.72rem;
}

.workbench-page :deep(.research-workflow-map),
.workbench-page :deep(.workflow-stage),
.workbench-page :deep(.research-workflow-card),
.workbench-page :deep(.workflow-package) {
  min-width: 0;
}

.workbench-page :deep(.research-workflow-map) {
  padding: 18px;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-lg);
  background: var(--wb-panel);
  box-shadow: 0 12px 30px rgb(15 48 64 / 0.06);
}

.workbench-page :deep(.research-workflow-map .panel-head) {
  align-items: flex-start;
}

.workbench-page :deep(.research-workflow-map .panel-head p) {
  margin: 4px 0 0;
  color: var(--wb-muted);
}

.workbench-page :deep(.workflow-stage-list) {
  display: grid;
  gap: 16px;
  margin-top: 14px;
}

.workbench-page :deep(.workflow-stage h3) {
  margin: 0 0 9px;
  color: var(--wb-title);
}

.workbench-page :deep(.research-workflow-card) {
  margin-bottom: 10px;
  padding: 12px;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-md);
  background: #fff;
}

.workbench-page :deep(.research-workflow-card.selected) {
  border-color: var(--wb-primary);
  box-shadow: inset 4px 0 0 var(--wb-primary);
}

.workbench-page :deep(.workflow-toggle) {
  display: grid;
  gap: 3px;
  width: 100%;
  text-align: left;
  color: var(--wb-ink);
}

.workbench-page :deep(.workflow-code) {
  color: var(--wb-accent);
  font-size: 0.72rem;
  font-weight: 850;
}

.workbench-page :deep(.workflow-toggle small) {
  color: var(--wb-muted);
}

.workbench-page :deep(.research-workflow-card > p) {
  margin: 7px 0 0;
  color: #52646d;
  font-size: 0.82rem;
}

.workbench-page :deep(.workflow-outputs) {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.workbench-page :deep(.workflow-outputs span) {
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--wb-primary-soft);
  color: var(--wb-primary-dark);
  font-size: 0.7rem;
  font-weight: 750;
}

.workbench-page :deep(.workflow-package-list) {
  margin-top: 11px;
  padding-top: 10px;
  border-top: 1px dashed var(--wb-line);
}

.workbench-page :deep(.workflow-package) {
  margin-bottom: 8px;
  padding: 8px;
  border: 1px solid var(--wb-line);
  border-radius: var(--wb-radius-sm);
  background: #fbfdfe;
}

.workbench-page :deep(.workflow-package button) {
  display: grid;
  gap: 3px;
  width: 100%;
  text-align: left;
  color: var(--wb-ink);
}

.workbench-page :deep(.workflow-package button span) {
  color: var(--wb-accent);
  font-size: 0.71rem;
  font-weight: 850;
}

.workbench-page :deep(.workflow-package button small) {
  color: var(--wb-muted);
}

.workbench-page :deep(.workflow-card-summary) {
  margin: 7px 0 0;
  padding-left: 18px;
  color: var(--wb-muted);
  font-size: 0.78rem;
}

@media (max-width: 1280px) {
  .workbench-page {
    padding: 20px;
  }

  .workbench-page :deep(.context-v5.preview-active) {
    grid-template-columns: minmax(330px, 0.95fr) minmax(400px, 1fr);
  }
}

@media (max-width: 1000px) {
  .workbench-page :deep(.context-summary) {
    grid-template-columns: 1fr;
  }

  .workbench-page :deep(.context-v5),
  .workbench-page :deep(.context-v5.preview-active) {
    grid-template-columns: 1fr;
  }

  .workbench-page :deep(.work-package-detail) {
    position: static;
    max-height: none;
    overflow: visible;
  }

  .workbench-page :deep(.context-filters) {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 680px) {
  .workbench-page {
    width: min(100%, calc(100% - 16px));
    margin-top: 10px;
    padding: 16px 14px 24px;
    border-radius: 18px;
  }

  .workbench-page :deep(.context-toolbar) {
    align-items: stretch;
    flex-direction: column;
  }

  .workbench-page :deep(.delete-area),
  .workbench-page :deep(.back-link) {
    justify-items: stretch;
    justify-content: center;
    text-align: center;
  }

  .workbench-page :deep(.context-summary) {
    padding: 19px;
  }

  .workbench-page :deep(.context-filters),
  .workbench-page :deep(.card-create-form),
  .workbench-page :deep(.progress-cards ul) {
    grid-template-columns: 1fr;
  }

  .workbench-page :deep(.context-wp-list) {
    grid-template-columns: 1fr;
  }
}
</style>
