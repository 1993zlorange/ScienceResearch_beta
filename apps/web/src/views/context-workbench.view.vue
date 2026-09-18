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
      <ContextSummary :context="context" :expanded="contextSummaryExpanded" @toggle="contextSummaryExpanded = !contextSummaryExpanded" />
      <div v-if="disclosureError" class="state-error" role="alert" data-testid="disclosure-error">{{ disclosureError }}</div>

      <div v-if="workflowsQuery.isLoading.value" class="state-loading" role="status">课题结构加载中…</div>
      <div v-else-if="workflowsQuery.error.value" class="state-error" role="alert">
        <p>{{ errorMessage(workflowsQuery.error.value, '课题结构加载失败') }}</p>
        <button type="button" data-testid="workflows-retry" @click="workflowsQuery.refetch()">重试</button>
      </div>
      <div v-else-if="catalogQuery.isLoading.value" class="state-loading" role="status">研究方面加载中…</div>
      <div v-else-if="catalogQuery.error.value" class="state-error" role="alert">
        <p>{{ errorMessage(catalogQuery.error.value, '研究方面加载失败') }}</p>
        <button type="button" data-testid="catalog-retry" @click="catalogQuery.refetch()">重试</button>
      </div>

      <template v-else-if="workflows && catalog">
        <div v-if="allItems.length === 0" class="empty-state" data-testid="workbench-empty-workflows" role="status">
          <h2>当前课题没有可用工作包</h2>
          <p>请返回课题列表创建新的课题，或检查课题工作流快照。</p>
          <RouterLink to="/contexts">返回课题列表</RouterLink>
        </div>

        <template v-else>
          <nav class="workbench-view-switch" aria-label="课题详情视图">
            <button type="button" :class="{ active: !workflowsView }" :aria-current="!workflowsView ? 'true' : undefined" data-testid="show-package-view" @click="showPackageView">工作包详情</button>
            <button type="button" :class="{ active: workflowsView }" :aria-current="workflowsView ? 'true' : undefined" data-testid="show-workflow-view" @click="showWorkflowView">12 工作流详情</button>
            <button
              type="button"
              class="workspace-toggle"
              data-testid="workspace-expand-toggle"
              :aria-pressed="workspaceAllExpanded ? 'true' : 'false'"
              :disabled="workspaceControlsDisabled"
              @click="toggleWorkspaceAll"
            >{{ workspaceAllExpanded ? '一键全部收起' : '一键全部展开' }}</button>
          </nav>

          <ContextFiltersPanel :filters="filters" :area-names="catalog.areas.map((area) => area.name)" :result-count="filteredItems.length" :expanded="filtersExpanded" @apply="applyFilters" @clear="clearFilters" @toggle="filtersExpanded = !filtersExpanded" />
          <ContextProgressPanel :progress="workflows.progress" :expanded="progressExpanded" :visible-cards="visibleCards" @toggle="toggleProgress" />

          <div class="context-body" :class="{ 'left-collapsed': !leftPaneExpanded, 'right-collapsed': !rightPaneExpanded, 'both-collapsed': !leftPaneExpanded && !rightPaneExpanded }" data-testid="context-body-two-columns">
            <section class="context-left-pane" :aria-label="leftPaneExpanded ? '课题卡片目录' : '课题卡片目录已收起'">
              <div v-if="!leftPaneExpanded" class="collapsed-pane-rail">
                <button type="button" data-testid="expand-package-pane" @click="leftPaneExpanded = true">
                  <span aria-hidden="true">›</span><span>展开工作包栏</span>
                </button>
              </div>
              <template v-else>
                <div class="pane-control-bar">
                  <span>工作包卡片</span>
                  <button type="button" data-testid="collapse-package-pane" @click="leftPaneExpanded = false">收起工作包栏<span aria-hidden="true">‹</span></button>
                </div>
                <WorkPackageDirectory v-if="!workflowsView" :catalog="catalog" :items="filteredItems" :all-count="allItems.length" :unassigned-count="unassignedWorkflows.length" :selected-work-package-id="selectedWorkPackageIdValue" :expanded-area-ids="expandedAreaIds" :expanded-package-ids="expandedPackageIds" :directory-expanded="directoryExpanded" :important-only="filters.important" @toggle-directory="toggleDirectory" @toggle-area="toggleArea" @toggle-package="toggleWorkPackageCards" @select="selectWorkPackage">
                  <template #default="{ item }">
                    <WorkPackageCardsPanel :key="item.package.id" :workflow="item.workflow" :expanded-card-ids="expandedCardIds" :importance-busy="importanceBusy" :importance-card-id="importanceCardId" :importance-error="importanceError" :importance-success-card-id="importanceSuccessCardId" :attachment-busy="attachmentBusy" :attachment-card-id="attachmentCardId" :attachment-error="attachmentError" :attachment-success-card-id="attachmentSuccessCardId" :active-preview-id="urlState.preview" @toggle-card="toggleCard" @toggle-importance="setCardImportance" @upload-attachment="uploadAttachment" @preview-attachment="openPreview" />
                  </template>
                </WorkPackageDirectory>
              </template>

              <template v-if="workflowsView">
                <div v-if="workflowMapQuery.isLoading.value" class="state-loading" role="status">12 工作流卡片加载中…</div>
                <div v-else-if="workflowMapQuery.error.value" class="state-error" role="alert">
                  <p>{{ errorMessage(workflowMapQuery.error.value, '12 工作流卡片加载失败') }}</p>
                  <button type="button" data-testid="workflow-map-retry" @click="workflowMapQuery.refetch()">重试</button>
                </div>
                <ResearchWorkflowMapPanel v-else-if="workflowMap" :workflow-items="workflowViewItems" :selected-workflow-id="selectedWorkflowEntry?.workflow.id"
                  :selected-work-package-id="selectedWorkPackageIdValue"
                  :bulk-command="workflowBulkCommand"
                  @all-expanded-change="workflowMapAllExpanded = $event"
                  @select-workflow="selectWorkflow" @open-work-package="selectWorkPackageFromWorkflow" />
              </template>
            </section>

            <div v-if="!leftPaneExpanded && !rightPaneExpanded" class="collapsed-main-spacer" aria-hidden="true"></div>
            <section class="context-right-pane" :aria-label="rightPaneExpanded ? '当前详情' : '当前详情已收起'">
              <div v-if="!rightPaneExpanded" class="collapsed-pane-rail right">
                <button type="button" data-testid="expand-detail-pane" @click="expandDetailPane"><span aria-hidden="true">‹</span><span>展开详情栏</span></button>
              </div>
              <template v-else>
                <div class="pane-control-bar detail">
                  <span>当前详情</span>
                  <button type="button" data-testid="collapse-detail-pane" @click="rightPaneExpanded = false">收起详情栏<span aria-hidden="true">›</span></button>
                </div>

                <template v-if="workflowsView">
                  <section v-if="selectedWorkflowEntry" class="detail-panel" data-testid="workflow-detail">
                    <header class="panel-head">
                      <div>
                        <p class="eyebrow">{{ stageLabel(selectedWorkflowEntry.workflow.stage) }}</p>
                        <h2>{{ selectedWorkflowEntry.workflow.id }} · {{ selectedWorkflowEntry.workflow.name }}</h2>
                      </div>
                      <span class="badge">{{ selectedWorkflowEntry.items.length }} 个工作包</span>
                    </header>
                    <dl class="detail-fields">
                      <div><dt>主责角色</dt><dd>{{ selectedWorkflowEntry.workflow.owner_role }}</dd></div>
                      <div><dt>教学解释</dt><dd>{{ selectedWorkflowEntry.workflow.description }}</dd></div>
                      <div><dt>关键输出</dt><dd>{{ selectedWorkflowEntry.workflow.outputs.join('；') }}</dd></div>
                    </dl>
                    <section v-if="workflowDetailItem" class="workflow-package-preview" data-testid="workflow-package-preview">
                      <header class="panel-head">
                        <h3>当前工作包预览</h3>
                        <span class="badge">{{ workflowDetailItem.package.id }}</span>
                      </header>
                      <WorkPackageDetail :key="workflowDetailItem.package.id" :workflow="workflowDetailItem.workflow" :package="workflowDetailItem.package" v-bind="detailBindings" :show-cards="false" :show-create-card="true" @toggle-importance="setCardImportance" @upload-attachment="uploadAttachment" @preview-attachment="openPreview" @toggle-card="toggleCard" @complete="setCompletion(true)" @cancel-completion="setCompletion(false)" @create-card="submitCard" />
                    </section>
                    <p v-else class="muted" data-testid="workflow-package-preview-empty">已选择工作流。请在左侧点击要预览的工作包；切换工作流不会自动改选工作包。</p>
                  </section>
                  <p v-else class="muted detail-panel" data-testid="workflow-select-empty">请在左侧选择一个工作流。</p>
                </template>

                <section v-else-if="packageDetailItem" class="detail-panel" data-testid="package-detail-panel">
                  <div class="detail-disclosure-head">
                    <button type="button" data-testid="package-detail-toggle" :aria-expanded="packageDetailExpanded ? 'true' : 'false'" aria-controls="package-detail-body" @click="packageDetailExpanded = !packageDetailExpanded">
                      <span>工作包详情</span><span aria-hidden="true">{{ packageDetailExpanded ? '−' : '+' }}</span>
                    </button>
                  </div>
                  <div v-show="packageDetailExpanded" id="package-detail-body" data-testid="package-detail-body">
                    <WorkPackageDetail :key="packageDetailItem.package.id" :workflow="packageDetailItem.workflow" :package="packageDetailItem.package" v-bind="detailBindings" :show-cards="false" :show-create-card="true" @toggle-importance="setCardImportance" @upload-attachment="uploadAttachment" @preview-attachment="openPreview" @toggle-card="toggleCard" @complete="setCompletion(true)" @cancel-completion="setCompletion(false)" @create-card="submitCard" />
                  </div>
                </section>

                <div v-if="previewPresent" class="preview-toolbar">
                  <button type="button" data-testid="preview-close" @click="closePreview">关闭附件预览</button>
                </div>
                <section v-if="previewPresent" class="preview-empty-state" data-preview-state="ACTIVE" data-testid="workbench-preview-state" aria-label="附件原文预览">
                  <h2>附件原文预览</h2>
                  <div v-if="attachmentPreviewQuery.isLoading.value" class="state-loading" role="status">附件预览加载中…</div>
                  <div v-else-if="attachmentPreviewQuery.error.value" class="state-error" role="alert">
                    <p data-testid="preview-error">{{ attachmentErrorMessage(attachmentPreviewQuery.error.value) }}</p>
                    <button type="button" @click="attachmentPreviewQuery.refetch()">重试</button>
                  </div>
                  <iframe v-else title="附件原文预览" data-testid="attachment-preview-frame" :src="achievementAttachmentPreviewUrl(urlState.preview)"></iframe>
                </section>
              </template>
            </section>
          </div>
        </template>
      </template>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCatalogQuery, useResearchWorkflowMapQuery } from '../features/catalog/use-catalog-query'
import { ApiError, achievementAttachmentPreviewUrl, achievementCardsFromWorkflow, type AchievementAttachment, type AchievementCard } from '../features/contexts/context-service'
import ContextFiltersPanel from '../features/context-workbench/components/context-filters-panel.vue'
import ContextProgressPanel from '../features/context-workbench/components/context-progress-panel.vue'
import ContextSummary from '../features/context-workbench/components/context-summary.vue'
import ContextToolbar from '../features/context-workbench/components/context-toolbar.vue'
import ResearchWorkflowMapPanel from '../features/context-workbench/components/research-workflow-map-panel.vue'
import WorkPackageDirectory from '../features/context-workbench/components/work-package-directory.vue'
import WorkPackageCardsPanel from '../features/context-workbench/components/work-package-cards-panel.vue'
import WorkPackageDetail from '../features/context-workbench/components/work-package-detail.vue'
import { buildWorkbenchItems, filterWorkbenchItems, readWorkbenchFilters, readWorkbenchUrlState, selectedWorkPackageId, visibleCardSummaries, type WorkbenchFilters, type WorkbenchItem } from '../features/context-workbench/context-workbench-model'
import { useAchievementAttachmentQuery, useAchievementAttachmentUploadMutation, useAchievementCardImportanceMutation, useContextDetailQuery, useContextDisclosurePreferencesQuery, useContextWorkbenchWorkflowsQuery, useDisclosurePreferenceMutation, useWorkflowCompletionMutation } from '../features/context-workbench/use-context-workbench-queries'
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
  const normalizedWorkflows = workflows.value.workflows.map((workflow) => ({ ...workflow, achievement_cards: achievementCardsFromWorkflow(workflow) }))
  return buildWorkbenchItems(catalog.value, normalizedWorkflows)
})
const allItems = computed(() => workbenchData.value?.items ?? [])
const unassignedWorkflows = computed(() => workbenchData.value?.unassigned ?? [])
const filteredItems = computed(() => filterWorkbenchItems(allItems.value, filters.value))
const explicitWorkPackageId = computed(() => {
  const requested = urlState.value.wp
  return requested && allItems.value.some((item) => item.package.id === requested) ? requested : ''
})
const selectedWorkPackageIdValue = computed(() => explicitWorkPackageId.value || selectedWorkPackageId(urlState.value.wp, allItems.value))
const visibleCards = computed(() => visibleCardSummaries(filteredItems.value, filters.value))
const previewPresent = computed(() => urlState.value.preview.length > 0)
const attachmentPreviewQuery = useAchievementAttachmentQuery(previewPresent ? urlState.value.preview : '')
const uploadAttachmentMutation = useAchievementAttachmentUploadMutation()
const workflowMap = computed(() => workflowMapQuery.data.value ?? null)
const workflowBulkCommand = ref<{ action: 'expand' | 'collapse'; token: number }>({ action: 'expand', token: 0 })
const workflowMapAllExpanded = ref(false)

const persistedExpanded = (kind: string, subject: string) => {
  const row = preferenceVersion.value.get(`${kind}:${subject}`)
  return row ? row.is_expanded : kind === 'directory'
}
const directoryFocusExpanded = ref(false)
const directoryOverride = ref<boolean | null>(null)
const directoryExpanded = computed(() => directoryOverride.value ?? (persistedExpanded('directory', 'context-directory') || directoryFocusExpanded.value))
const progressOverride = ref<boolean | null>(null)
const progressExpanded = computed(() => progressOverride.value ?? persistedExpanded('progress', 'context-progress'))
const contextSummaryExpanded = ref(true)
const filtersExpanded = ref(true)
const leftPaneExpanded = ref(true)
const rightPaneExpanded = ref(true)
const packageDetailExpanded = ref(true)
const manuallyCollapsedPackageIds = ref(new Set<string>())
const expandedAreaIds = shallowRef(new Set<string>())
const expandedPackageIds = shallowRef(new Set<string>())
const expandedCardIds = shallowRef(new Set<string>())
const disclosureBusy = ref(false)
const disclosureError = ref('')
let disclosureQueue: Promise<void> = Promise.resolve()
let hydratedPreferences = false

watch([catalog, disclosureQuery.data], ([value, preferenceList]) => {
  if (!value || hydratedPreferences) return
  const areaRows = new Set(value.areas.map((area) => area.id))
  for (const row of preferenceList?.preferences.filter((item) => item.disclosure_kind === 'area') ?? []) {
    if (row.is_expanded) areaRows.add(row.stable_subject_id)
    else areaRows.delete(row.stable_subject_id)
  }
  expandedAreaIds.value = areaRows
  const packagePreferences = new Map((preferenceList?.preferences ?? []).filter((item) => item.disclosure_kind === 'work_package').map((item) => [item.stable_subject_id, item.is_expanded]))
  const packageRows = new Set([...packagePreferences.entries()].filter(([, isExpanded]) => isExpanded).map(([id]) => id))
  const selected = selectedWorkPackageIdValue.value
  if (selected && !packagePreferences.has(selected) && !manuallyCollapsedPackageIds.value.has(selected)) packageRows.add(selected)
  expandedPackageIds.value = packageRows
  hydratedPreferences = true
}, { immediate: true })

watch([disclosureQuery.data, urlState], ([preferenceList, state]) => {
  const cards = new Set(preferenceList?.preferences.filter((row) => row.disclosure_kind === 'card' && row.is_expanded).map((row) => row.stable_subject_id) ?? [])
  if (state?.card) cards.add(state.card)
  expandedCardIds.value = cards
}, { immediate: true })

const stageLabel = (stage: string): string => (stage === 'Explore' ? '探索 Explore' : stage === 'Execute' ? '执行 Execute' : '表达 Express')
const selectedItem = computed(() => allItems.value.find((item) => item.package.id === selectedWorkPackageIdValue.value))
const workflowViewItems = computed(() => {
  if (!workflowMap.value) return []
  const itemByPackageId = new Map(filteredItems.value.map((item) => [item.package.id, item]))
  return workflowMap.value.workflows.map((workflow) => ({ workflow, items: workflow.work_package_ids.flatMap((workPackageId) => { const item = itemByPackageId.get(workPackageId); return item ? [item] : [] }) }))
})
const selectedWorkflowEntry = computed(() => {
  const requested = urlState.value.workflow
  const explicitEntry = workflowViewItems.value.find((entry) => entry.workflow.id === requested)
  if (explicitEntry) return explicitEntry
  if (explicitWorkPackageId.value) return workflowViewItems.value.find((entry) => entry.items.some((item) => item.package.id === explicitWorkPackageId.value)) ?? null
  return null
})
const workflowDetailItem = computed<WorkbenchItem | null>(() => {
  const entry = selectedWorkflowEntry.value
  if (!entry || !explicitWorkPackageId.value) return null
  return entry.items.find((item) => item.package.id === explicitWorkPackageId.value) ?? null
})
const packageDetailItem = computed<WorkbenchItem | null>(() => workflowsView.value ? null : selectedItem.value ?? null)
const activeDetailItem = computed(() => workflowsView.value ? workflowDetailItem.value : packageDetailItem.value)
const detailBindings = computed(() => ({
  expandedCardIds: expandedCardIds.value,
  completionBusy: completionBusy.value,
  completionError: completionError.value,
  completionSuccess: completionSuccessPackageId.value === activeDetailItem.value?.package.id,
  cardCreateBusy: cardCreateBusy.value,
  cardCreateError: cardCreateError.value,
  cardCreateSuccess: cardCreateSuccessPackageId.value === activeDetailItem.value?.package.id,
  cardForm: cardFormFor(activeDetailItem.value),
  cardFormInvalid: activeDetailItem.value ? cardFormInvalidFor(activeDetailItem.value) : true,
  importanceBusy: importanceBusy.value,
  importanceCardId: importanceCardId.value,
  importanceError: importanceError.value,
  importanceSuccessCardId: importanceSuccessCardId.value,
  attachmentBusy: attachmentBusy.value,
  attachmentCardId: attachmentCardId.value,
  attachmentError: attachmentError.value,
  attachmentSuccessCardId: attachmentSuccessCardId.value,
  activePreviewId: urlState.value.preview,
}))

watch([allItems, urlState], ([items, state]) => {
  if (workflowsView.value || !state.card) return
  const owningPackageId = items.find((item) => item.workflow.achievement_cards.some((card) => card.id === state.card))?.package.id
  if (!owningPackageId || expandedPackageIds.value.has(owningPackageId)) return
  const next = new Set(expandedPackageIds.value); next.add(owningPackageId); expandedPackageIds.value = next
}, { immediate: true })

watch(selectedWorkPackageIdValue, async (workPackageId, previousWorkPackageId) => {
  if (!workPackageId || workPackageId === previousWorkPackageId) return
  const collapsed = new Set(manuallyCollapsedPackageIds.value); collapsed.delete(workPackageId); manuallyCollapsedPackageIds.value = collapsed
  const owningItem = allItems.value.find((item) => item.package.id === workPackageId)
  if (owningItem) { const areas = new Set(expandedAreaIds.value); areas.add(owningItem.area.id); expandedAreaIds.value = areas }
  const packages = new Set(expandedPackageIds.value); packages.add(workPackageId); expandedPackageIds.value = packages
  directoryFocusExpanded.value = true
  leftPaneExpanded.value = true
  await scrollWorkbenchTargetTop(workPackageId)
}, { immediate: true })

watch(
  [workflowsView, workflowMap, selectedWorkPackageIdValue],
  async ([enabled, map, workPackageId]) => {
    if (!workPackageId || (enabled && !map)) return
    await scrollWorkbenchTargetTop(workPackageId)
  },
  { immediate: true },
)

watch(previewPresent, (present) => { if (present) packageDetailExpanded.value = false }, { immediate: true })

const workspaceAllAreas = computed(() => !catalog.value || catalog.value.areas.every(area => expandedAreaIds.value.has(area.id)))
const workspaceAllPackages = computed(() => filteredItems.value.every(item => expandedPackageIds.value.has(item.package.id)))
const workspaceAllCards = computed(() => filteredItems.value.every(item => item.workflow.achievement_cards.every(card => expandedCardIds.value.has(card.id))))
const workspaceAllWorkflows = computed(() => !workflowsView.value || workflowMapAllExpanded.value)
const workspaceControlsDisabled = computed(() => workflowsView.value && (!workflowMap.value || workflowMapQuery.isLoading.value || Boolean(workflowMapQuery.error.value)))
const workspaceAllExpanded = computed(() => {
  const panelsVisible = contextSummaryExpanded.value && filtersExpanded.value && progressExpanded.value && leftPaneExpanded.value && rightPaneExpanded.value && packageDetailExpanded.value && directoryExpanded.value
  return panelsVisible && workspaceAllAreas.value && workspaceAllPackages.value && workspaceAllCards.value && workspaceAllWorkflows.value
})

watch([workflowsView, workflowMap, explicitWorkPackageId, urlState], ([enabled, map, workPackageId, state]) => {
  if (!enabled || !map || state.workflow || !workPackageId) return
  const entry = workflowViewItems.value.find((item) => item.items.some((workItem) => workItem.package.id === workPackageId))
  if (entry) void pushQuery({ workflow: entry.workflow.id })
}, { immediate: true })

watch([allItems, urlState], ([items, state]) => {
  if (!items.length || workflowsView.value) return
  if (state.wp && items.some((item) => item.package.id === state.wp)) return
  const fallback = selectedWorkPackageId(state.wp, items)
  if (fallback && fallback !== state.wp) void pushQuery({ wp: fallback })
}, { immediate: true })

function buildQuery(overrides: Partial<{ wp: string | undefined; area: string | undefined; status: string | undefined; query: string | undefined; important: boolean | undefined; card: string | undefined; preview: string | undefined; view: 'packages' | 'workflows'; workflow: string | undefined }> = {}): Record<string, string> {
  const merged = { wp: urlState.value.wp || selectedWorkPackageIdValue.value || '', area: filters.value.area, status: filters.value.status, query: filters.value.query, important: filters.value.important, card: urlState.value.card, preview: urlState.value.preview, view: urlState.value.view, workflow: urlState.value.workflow, ...overrides }
  const query: Record<string, string> = {}
  const set = (key: string, value: string | boolean | undefined) => { if (value === true) query[key] = 'true'; else if (typeof value === 'string' && value) query[key] = value }
  set('wp', merged.wp); set('area', merged.area); set('status', merged.status); set('query', merged.query); set('important', merged.important); set('card', merged.card); set('preview', merged.preview); set('view', merged.view === 'workflows' ? merged.view : ''); set('workflow', merged.workflow)
  return query
}
async function pushQuery(overrides?: Parameters<typeof buildQuery>[0]) { await router.push({ path: route.path, query: buildQuery(overrides) }) }
function applyFilters(nextFilters: WorkbenchFilters) { void pushQuery({ area: nextFilters.area, status: nextFilters.status, query: nextFilters.query, important: nextFilters.important }) }
function clearFilters() { void pushQuery({ area: '', status: '', query: '', important: false }) }
function toggleWorkspaceAll(): void {
  const expandAll = !workspaceAllExpanded.value
  directoryOverride.value = expandAll
  progressOverride.value = expandAll
  contextSummaryExpanded.value = expandAll
  filtersExpanded.value = expandAll
  leftPaneExpanded.value = expandAll
  rightPaneExpanded.value = expandAll
  packageDetailExpanded.value = expandAll
  expandedAreaIds.value = new Set(expandAll ? (catalog.value?.areas.map(area => area.id) ?? []) : [])
  expandedPackageIds.value = new Set(expandAll ? allItems.value.map(item => item.package.id) : [])
  expandedCardIds.value = new Set(expandAll ? allItems.value.flatMap(item => item.workflow.achievement_cards.map(card => card.id)) : [])
  manuallyCollapsedPackageIds.value = new Set(expandAll ? [] : allItems.value.map(item => item.package.id))
  if (expandAll) { directoryFocusExpanded.value = true }
  workflowMapAllExpanded.value = expandAll
  workflowBulkCommand.value = { action: expandAll ? 'expand' : 'collapse', token: workflowBulkCommand.value.token + 1 }
  if (urlState.value.card) void pushQuery({ card: '' })
}

function showPackageView() { void pushQuery({ view: 'packages' }) }
function expandDetailPane(): void { rightPaneExpanded.value = true; scrollDetailTop() }
function scrollDetailTop(): void {
  void nextTick(() => {
    const detail = document.querySelector('[data-testid="package-detail-panel"], [data-testid="workflow-detail"]')
    if (typeof detail?.scrollIntoView === 'function') detail.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}
function scrollSelectedPackageCardTop(workPackageId: string): boolean {
  const selector = workflowsView.value ? `[data-testid="research-workflow-package-${workPackageId}"]` : `[data-testid="work-package-card-${workPackageId}"]`
  const card = document.querySelector(selector)
  if (typeof card?.scrollIntoView !== 'function') return false
  card.scrollIntoView({ behavior: 'smooth', block: 'start' })
  return true
}

async function scrollWorkbenchTargetTop(workPackageId: string): Promise<boolean> {
  await nextTick()
  for (let attempt = 0; attempt < 12; attempt += 1) {
    if (scrollSelectedPackageCardTop(workPackageId)) return true
    await new Promise(resolve => setTimeout(resolve, 50))
  }
  return false
}
function showWorkflowView() {
  const requested = urlState.value.workflow
  const requestedIsValid = workflowViewItems.value.some((entry) => entry.workflow.id === requested)
  const containing = explicitWorkPackageId.value ? workflowViewItems.value.find((entry) => entry.items.some((item) => item.package.id === explicitWorkPackageId.value)) : undefined
  const workflowId = requestedIsValid ? requested : containing?.workflow.id ?? selectedWorkflowEntry.value?.workflow.id ?? ''
  void pushQuery({ view: 'workflows', workflow: workflowId })
}
function selectWorkflow(workflowId: string) { void pushQuery({ view: 'workflows', workflow: workflowId }) }
function selectWorkPackage(workPackageId: string) { void pushQuery({ wp: workPackageId }) }
function selectWorkPackageFromWorkflow(workPackageId: string) { void pushQuery({ view: 'workflows', workflow: selectedWorkflowEntry.value?.workflow.id ?? '', wp: workPackageId, preview: '' }) }

async function saveExpanded(kind: 'directory' | 'progress' | 'area' | 'work_package' | 'card', subject: string, expanded: boolean): Promise<void> {
  const run = async (): Promise<void> => {
    disclosureBusy.value = true; disclosureError.value = ''
    const existing = preferenceVersion.value.get(`${kind}:${subject}`)
    try {
      await saveDisclosure.mutateAsync({ disclosure_kind: kind, stable_subject_id: subject, requested_is_expanded: expanded, expected_version: existing?.row_version ?? 0 })
    } catch (error) {
      if (error instanceof ApiError && (error.status === 409 || error.code === 'VERSION_CONFLICT')) {
        await disclosureQuery.refetch()
        const latest = preferenceVersion.value.get(`${kind}:${subject}`)
        if (latest?.is_expanded === expanded) return
        if (latest) { await saveDisclosure.mutateAsync({ disclosure_kind: kind, stable_subject_id: subject, requested_is_expanded: expanded, expected_version: latest.row_version }); return }
      }
      disclosureError.value = error instanceof ApiError && error.status === 503 ? '服务暂时不可用，偏好未保存，请稍后重试。' : errorMessage(error, '披露偏好保存失败')
    } finally { disclosureBusy.value = false }
  }
  disclosureQueue = disclosureQueue.then(run, run); await disclosureQueue
}
function toggleDirectory() { const expanded = !directoryExpanded.value; directoryOverride.value = expanded; void saveExpanded('directory', 'context-directory', expanded) }
function toggleArea(areaId: string) { const expanded = !expandedAreaIds.value.has(areaId); const next = new Set(expandedAreaIds.value); if (expanded) next.add(areaId); else next.delete(areaId); expandedAreaIds.value = next; void saveExpanded('area', areaId, expanded) }
function toggleWorkPackageCards(workPackageId: string) {
  const expanded = !expandedPackageIds.value.has(workPackageId); const next = new Set(expandedPackageIds.value); const manuallyCollapsed = new Set(manuallyCollapsedPackageIds.value)
  if (expanded) { next.add(workPackageId); manuallyCollapsed.delete(workPackageId) } else { next.delete(workPackageId); manuallyCollapsed.add(workPackageId) }
  expandedPackageIds.value = next; manuallyCollapsedPackageIds.value = manuallyCollapsed
  if (expanded) void pushQuery({ wp: workPackageId })
  void saveExpanded('work_package', workPackageId, expanded)
}
function toggleProgress() { const expanded = !progressExpanded.value; progressOverride.value = expanded; void saveExpanded('progress', 'context-progress', expanded) }
function toggleCard(cardId: string) { const expanded = !expandedCardIds.value.has(cardId); const next = new Set(expandedCardIds.value); if (expanded) next.add(cardId); else next.delete(cardId); expandedCardIds.value = next; void pushQuery({ card: expanded ? cardId : '' }); void saveExpanded('card', cardId, expanded) }
function closePreview() { void pushQuery({ preview: '' }) }
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
async function setCompletion(completed: boolean) {
  const item = activeDetailItem.value
  if (!item) return
  completionSuccessPackageId.value = ''; completionTargetId.value = item.package.id
  try { await completeWorkflowMutation.mutateAsync({ workflowId: item.workflow.id, expectedVersion: item.workflow.row_version, completed }); completionSuccessPackageId.value = item.package.id } catch { }
}
interface CardFormState { event_date: string; event_name: string; description: string; important: boolean }
const cardForms = ref<Record<string, CardFormState>>({})
const cardCreateTargetId = ref('')
const cardCreateBusy = computed(() => createCardMutation.isPending.value)
const cardCreateError = computed(() => createCardMutation.error.value ? errorMessage(createCardMutation.error.value, '成效卡创建失败') : '')
const cardCreateSuccessPackageId = ref('')
function cardFormFor(item: WorkbenchItem | null): CardFormState {
  const fallback: CardFormState = { event_date: new Date().toISOString().slice(0, 10), event_name: '', description: '', important: false }
  if (!item) return fallback
  const existing = cardForms.value[item.package.id]
  if (existing) return existing
  cardForms.value[item.package.id] = fallback; return fallback
}
function cardFormInvalidFor(item: WorkbenchItem | null): boolean { if (!item) return true; const form = cardFormFor(item); return !form.event_date || !form.event_name.trim() }
async function submitCard() {
  const item = activeDetailItem.value; const form = cardFormFor(item)
  if (!item || cardFormInvalidFor(item)) return
  cardCreateSuccessPackageId.value = ''; cardCreateTargetId.value = item.package.id
  try {
    await createCardMutation.mutateAsync({ context_id: item.workflow.context_id, workflow_id: item.workflow.id, event_date: form.event_date, event_name: form.event_name.trim(), description: form.description.trim(), important: form.important })
    cardCreateSuccessPackageId.value = item.package.id; form.event_name = ''; form.description = ''; form.important = false
  } catch { }
}
const attachmentCardId = ref('')
const attachmentBusy = computed(() => uploadAttachmentMutation.isPending.value)
const attachmentError = ref('')
const attachmentSuccessCardId = ref('')
async function uploadAttachment(cardId: string, file: File) {
  attachmentError.value = ''; attachmentSuccessCardId.value = ''; attachmentCardId.value = cardId
  try {
    await uploadAttachmentMutation.mutateAsync({ cardId, file, actor: 'author', requestId: crypto.randomUUID(), idempotencyKey: crypto.randomUUID() }); attachmentSuccessCardId.value = cardId
  } catch (error) { attachmentError.value = attachmentErrorMessage(error) }
}
function openPreview(attachment: AchievementAttachment) {
  const owningItem = allItems.value.find((item) => item.workflow.achievement_cards.some((card) => card.id === attachment.card_id))
  void pushQuery({ wp: owningItem?.package.id ?? selectedWorkPackageIdValue.value, card: attachment.card_id, preview: attachment.id })
}
const importanceCardId = ref('')
const importanceBusy = computed(() => toggleImportanceMutation.isPending.value)
const importanceError = ref('')
const importanceSuccessCardId = ref('')
async function setCardImportance(card: AchievementCard, important: boolean) {
  importanceError.value = ''; importanceSuccessCardId.value = ''; importanceCardId.value = card.id
  try { await toggleImportanceMutation.mutateAsync({ workflowId: card.workflow_id, cardId: card.id, isImportant: important, expectedVersion: card.row_version }); importanceSuccessCardId.value = card.id } catch (error) { importanceError.value = errorMessage(error, '成效卡标记保存失败') }
}
</script>


<style>

.context-summary{margin-bottom:14px;padding:18px;border:1px solid #c9dfe8;border-radius:14px;background:linear-gradient(135deg,#fff,#f2f8fb 58%,#eaf4f9);box-shadow:0 14px 34px #173b5717}.summary-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.summary-eyebrow{margin:0 0 4px;color:#b46b2f;font-size:.7rem;font-weight:900;letter-spacing:.1em;text-transform:uppercase}h2{margin:0;color:#173b57;font-size:clamp(1.25rem,2vw,1.75rem);line-height:1.25}.summary-problem{margin:5px 0 0;color:#5d707c}.summary-toggle{display:inline-flex;align-items:center;gap:7px;flex:0 0 auto;min-height:34px;padding:6px 11px;border:1px solid #c9dfe8;border-radius:999px;background:#fff;color:#17668e;font-size:.78rem;font-weight:800;cursor:pointer}.summary-toggle:hover{background:#e3f2fa}.summary-body{display:grid;grid-template-columns:minmax(0,1fr) minmax(260px,.7fr);gap:14px;margin-top:15px;padding-top:14px;border-top:1px solid #dbe9ef}dl{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin:0}dl div{padding:9px 10px;border:1px solid #dbe9ef;border-radius:9px;background:#fff}dt{color:#718792;font-size:.72rem;font-weight:850}dd{margin:3px 0 0;color:#173b57;font-weight:750;overflow-wrap:anywhere}.context-goal{margin:0;padding:11px 13px;border-left:4px solid #d4772e;border-radius:0 9px 9px 0;background:#fff7ed;color:#7c4a12;overflow-wrap:anywhere}@media(max-width:800px){.summary-head{align-items:stretch;flex-direction:column}.summary-body,dl{grid-template-columns:1fr}}.workbench-page{min-width:0}.state-loading,.state-error,.empty-state,.detail-panel,.preview-empty-state{min-width:0;margin-bottom:14px;padding:16px;border:1px solid var(--wb-border, #c9dfe8);border-radius:12px;background:#fff;box-shadow:0 10px 26px #0f30400f}.state-error{border-color:#dfa3a3;color:#8f2f2f}.workbench-view-switch{display:inline-flex;gap:6px;margin-bottom:14px;padding:5px;border:1px solid #c9dfe8;border-radius:999px;background:#fff}.workbench-view-switch button{min-height:32px;padding:5px 13px;border:0;border-radius:999px;background:transparent;color:#52646d;font-weight:750;cursor:pointer}.workbench-view-switch button.active{background:#e3f2fa;color:#17668e}.panel-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid #dbe9ef}.panel-head h2,.panel-head h3{margin:0;color:#102f3d}.eyebrow{margin:0 0 4px;color:#b46b2f;font-size:.72rem;font-weight:850;text-transform:uppercase}.badge{padding:5px 9px;border-radius:999px;background:#e3f2fa;color:#17668e;font-size:.72rem;font-weight:800;white-space:nowrap}.detail-panel,.workflow-package-preview,.workbench-page .work-package-detail{scroll-margin-top:24px}.detail-fields{display:grid;margin:0 0 14px;border:1px solid #dbe9ef;border-radius:10px;overflow:hidden}.detail-fields div{display:grid;grid-template-columns:88px minmax(0,1fr);gap:10px;padding:10px}.detail-fields div+div{border-top:1px solid #dbe9ef}.detail-fields dt{color:#718792;font-size:.76rem;font-weight:800}.detail-fields dd{margin:0;overflow-wrap:anywhere}.workflow-package-preview{margin-top:16px}.preview-toolbar{display:flex;justify-content:flex-end;margin-bottom:8px}.preview-empty-state iframe{display:block;width:100%;min-height:min(68vh,700px);border:1px solid #c9dfe8;border-radius:8px;background:#fff}.workbench-page .context-filters.collapsed{margin-bottom:10px}.workbench-page .filters-head{display:flex;align-items:center;justify-content:space-between;gap:10px}.workbench-page .filters-toggle{display:inline-flex;align-items:center;gap:7px;min-height:34px;padding:5px 10px;border:1px solid #c9dfe8;border-radius:999px;background:#fff;color:#17668e;font-size:.79rem;font-weight:850}.workbench-page .filters-form{display:grid;grid-template-columns:minmax(220px,1.2fr) repeat(2,minmax(140px,.65fr)) auto auto;gap:10px;align-items:end}.workbench-page .filters-form label{display:grid;gap:4px;color:#667382;font-size:.74rem;font-weight:800}.workbench-page .filters-form input,.workbench-page .filters-form select{min-width:0;padding:8px 9px;border:1px solid #c9dfe8;border-radius:7px;font:inherit}.pane-control-bar{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px;padding:8px 10px;border:1px solid #c9dfe8;border-radius:8px;background:#fff;color:#173b57;font-size:.78rem;font-weight:850}.pane-control-bar button,.collapsed-pane-rail button{display:inline-flex;align-items:center;gap:5px;min-height:30px;padding:4px 9px;border:1px solid #c9dfe8;border-radius:999px;background:#e3f2fa;color:#17668e;font-size:.73rem;font-weight:850;cursor:pointer;white-space:nowrap}.collapsed-pane-rail{display:flex;justify-content:center;width:100%}.collapsed-pane-rail button{flex-direction:column;min-height:96px}.context-body.left-collapsed{grid-template-columns:58px minmax(0,1fr)}.context-body.right-collapsed{grid-template-columns:minmax(0,1fr) 58px}.collapsed-main-spacer{min-width:0}.context-body.both-collapsed{grid-template-columns:58px minmax(0,1fr) 58px}.context-body{display:grid;grid-template-columns:minmax(360px,1fr) minmax(420px,.86fr);gap:16px;align-items:start}.context-left-pane,.context-right-pane{min-width:0}.context-right-pane{position:sticky;top:18px}.workbench-page .work-package-directory,.workbench-page .research-workflow-map{min-width:0;max-height:min(78vh,1000px);overflow:auto;padding:16px;border:1px solid #c9dfe8;border-radius:12px;background:#fff;box-shadow:0 10px 26px #0f30400f}.workbench-page .directory-body,.workbench-page .workflow-stage-list{display:grid;gap:12px}.workbench-page .context-area,.workbench-page .workflow-stage{min-width:0}.workbench-page .context-area h3,.workbench-page .workflow-stage h3{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:0 0 8px}.workbench-page .area-toggle,.workbench-page .area-toggle:hover{padding:5px 0;border:0;background:transparent;color:#173b57;font-size:.92rem;font-weight:800}.workbench-page .context-wp-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.workbench-page .work-package-card{display:grid;align-content:start;gap:6px;min-width:0;padding:11px;border:1px solid #dce3e8;border-radius:9px;background:#fbfdfe;box-shadow:0 3px 10px #102f3d0a}.workbench-page .work-package-card.state-complete{border-color:#91c7ae;background:linear-gradient(180deg,#f1faf5,#fff 70%)}.workbench-page .work-package-card.state-has-cards{border-color:#dfc26d;background:linear-gradient(180deg,#fffbef,#fff 70%)}.workbench-page .work-package-card[data-card-count="0"]{border-color:#dce3e8;background:#fbfdfe}.workbench-page .wp-heading{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:5px;align-items:center;padding:0;border:0;background:transparent;text-align:left}.workbench-page .wp-heading[aria-current=true]{outline:2px solid #17668e;outline-offset:2px}.workbench-page .wp-code{color:#17668e;font-size:.68rem;font-weight:900;letter-spacing:.04em}.workbench-page .wp-heading strong{min-width:0;overflow-wrap:anywhere;color:#173b57;font-size:.82rem;line-height:1.3}.workbench-page .wp-status,.workbench-page .card-count,.workbench-page .important-mark{display:inline-flex;align-items:center;min-height:21px;padding:2px 7px;border-radius:999px;font-size:.68rem;font-weight:850;white-space:nowrap}.workbench-page .wp-status{background:#eaf1f4;color:#49626d}.workbench-page .state-complete .wp-status{background:#e5f5ed;color:#23664a}.workbench-page .state-has-cards .wp-status{background:#fff3d7;color:#8a5d10}.workbench-page .card-count{background:#eef2f8;color:#49626d}.workbench-page .important-mark{background:#ffe8c9;color:#96590a}.workbench-page .work-package-card>p{margin:0;color:#667382;font-size:.78rem;line-height:1.45;overflow-wrap:anywhere}.workbench-page .wp-select{justify-self:start;min-height:28px;padding:4px 9px;border:1px solid #c9dfe8;border-radius:999px;background:#e3f2fa;color:#17668e;font-size:.74rem;font-weight:800}.workbench-page .research-workflow-card{margin-bottom:9px;padding:10px;border:1px solid #dce3e8;border-radius:9px;background:#fbfdfe}.workbench-page .research-workflow-card.selected{border-color:#17668e;background:#f2f8fb;box-shadow:inset 4px 0 #17668e}.workbench-page .workflow-toggle{display:grid;gap:3px;width:100%;padding:0;border:0;background:transparent;color:#173b57;text-align:left}.workbench-page .workflow-code{color:#17668e;font-size:.7rem;font-weight:900}.workbench-page .workflow-toggle small,.workbench-page .workflow-package small{color:#667382}.workbench-page .workflow-outputs{display:flex;flex-wrap:wrap;gap:5px;margin:7px 0 0}.workbench-page .workflow-outputs span{padding:2px 7px;border-radius:999px;background:#e3f2fa;color:#17668e;font-size:.68rem;font-weight:800}.workbench-page .workflow-package-list{margin-top:9px;padding-top:8px;border-top:1px dashed #dce3e8}.workbench-page .workflow-package{margin-bottom:7px;padding:7px;border:1px solid #dce3e8;border-radius:7px;background:#fff}.workbench-page .workflow-package button{display:grid;gap:3px;width:100%;border:0;background:transparent;color:#173b57;text-align:left}.workbench-page .workflow-package button span{color:#17668e;font-size:.68rem;font-weight:900}.workbench-page .workflow-card-summary{margin:6px 0 0;padding-left:18px;color:#667382;font-size:.75rem}.workbench-page .work-package-card:has(.package-card-expansion){grid-column:1 / -1;border-color:#8db8c6;box-shadow:0 10px 24px #173b571f}.workbench-page .package-card-expansion{margin-top:4px;padding:12px;border:1px solid #dbe9ef;border-radius:10px;background:#fff}.workbench-page .package-cards-panel{display:grid;gap:12px}.workbench-page .card-create-panel,.workbench-page .selected-cards{min-width:0;padding:12px;border:1px solid #dbe9ef;border-radius:10px;background:#fbfdfe}.workbench-page .card-create-panel h3,.workbench-page .selected-cards h3{margin:0 0 10px;color:#173b57;font-size:.92rem}.workbench-page .card-create-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;align-items:end}.workbench-page .card-create-form label{display:grid;gap:4px;color:#667382;font-size:.76rem;font-weight:750}.workbench-page .card-create-form input,.workbench-page .card-create-form textarea{min-width:0;padding:8px 9px;border:1px solid #c9dfe8;border-radius:7px;font:inherit}.workbench-page .card-create-form .checkbox-label{flex-direction:row;align-items:center;color:#173b57}.workbench-page .card-create-form button{min-height:36px;border:0;border-radius:7px;background:#d4772e;color:#fff;font-weight:800}.workbench-page .achievement-card{margin:8px 0;border:1px solid #dbe9ef;border-radius:9px;background:#fff}.workbench-page .achievement-card.important{border-color:#dfc26d;box-shadow:inset 4px 0 #d4772e}.workbench-page .card-heading{padding:0 10px}.workbench-page .card-toggle{width:100%;min-height:40px;padding:8px 0;border:0;background:transparent;color:#173b57;text-align:left}.workbench-page .card-summary-meta{margin:0 10px 8px;color:#667382;font-size:.74rem}.workbench-page .card-actions{padding:0 10px 10px;border-top:1px dashed #dbe9ef}.workbench-page .card-facts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin:10px 0}.workbench-page .card-facts div{padding:7px 8px;border-radius:7px;background:#f6f8fa}.workbench-page .attachments{margin-top:10px}.workbench-page .attachment-list{display:grid;gap:6px;margin:0;padding:0;list-style:none}.workbench-page .attachment-row{display:flex;gap:7px;align-items:center;flex-wrap:wrap;padding:7px 8px;border:1px solid #dbe9ef;border-radius:7px;background:#fff}@media(max-width:900px){.workbench-page .filters-form{grid-template-columns:1fr}}@media(max-width:700px){.workbench-page .card-create-form{grid-template-columns:1fr}}@media(max-width:1000px){.context-body{grid-template-columns:1fr}.context-right-pane{position:static}.workbench-page .work-package-directory,.workbench-page .research-workflow-map{max-height:none}}@media(max-width:700px){.detail-fields div{grid-template-columns:1fr}.preview-empty-state iframe{min-height:520px}}

.workbench-view-switch{flex-wrap:wrap;width:min(100%,760px)}.workbench-view-switch .workspace-toggle{margin-left:auto;border:1px solid #c9dfe8;background:#f2f8fb;color:#17668e;min-height:32px;padding:5px 12px;font-weight:850}.workbench-view-switch .workspace-toggle:hover{background:#e3f2fa}.detail-disclosure-head{display:flex;justify-content:flex-end;margin-bottom:10px}
.detail-disclosure-head button{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border:1px solid #d7e4ea;border-radius:8px;background:#fff;color:#26455a;cursor:pointer}
.detail-disclosure-head button:hover{background:#f2f8fa}
</style>
