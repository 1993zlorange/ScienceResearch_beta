<template>
<nav class="structure-tree" data-testid="context-navigation-tree" aria-label="课题结构树">
    <RouterLink
      class="tree-root-link"
      to="/contexts"
      :aria-current="route.path === '/contexts' ? 'page' : undefined"
    >课题列表</RouterLink>

    <template v-if="contextsQuery.isLoading.value">
          <p class="tree-muted">课题加载中…</p>
        </template>
        <p v-else-if="contextsQuery.error.value" class="tree-error" role="alert">课题树加载失败</p>
        <template v-else>
          <div v-for="context in contexts" :key="context.id" class="tree-node">
            <button
              type="button"
              class="tree-toggle"
              :class="{ active: context.id === currentContextId }"
              :aria-expanded="expanded.has(`context:${context.id}`) ? 'true' : 'false'"
              :aria-controls="`structure-context-${context.id}`"
              :data-testid="`structure-toggle-context-${context.id}`"
              @click="selectContext(context.id)"
            >
              <span>{{ context.name }}</span>
              <span aria-hidden="true">{{ expanded.has(`context:${context.id}`) ? '−' : '+' }}</span>
            </button>
            <div
              v-if="context.id === currentContextId && expanded.has(`context:${context.id}`)"
              :id="`structure-context-${context.id}`"
              class="tree-children"
            >
              <p v-if="structureLoading" class="tree-muted">课题结构加载中…</p>
              <p v-else-if="structureError" class="tree-error" role="alert">课题结构加载失败</p>
              <template v-else>
                <div class="tree-node">
                  <button
                    type="button"
                    class="tree-toggle"
                    :aria-expanded="expanded.has('aspects') ? 'true' : 'false'"
                    aria-controls="structure-aspects"
                    data-testid="structure-toggle-aspects"
                    @click="toggle('aspects')"
                  >
                    <span>研究方面</span>
                    <span aria-hidden="true">{{ expanded.has('aspects') ? '−' : '+' }}</span>
                  </button>
                  <div v-if="expanded.has('aspects')" id="structure-aspects" class="tree-children">
                    <div v-for="area in areaGroups" :key="area.id" class="tree-node">
                      <button
                        type="button"
                        class="tree-toggle"
                        :aria-expanded="expanded.has(`area:${area.id}`) ? 'true' : 'false'"
                        :aria-controls="`structure-area-${area.id}`"
                        :data-testid="`structure-toggle-area-${area.id}`"
                        @click="toggle(`area:${area.id}`)"
                      >
                        <span>{{ area.name }}</span>
                        <small>{{ area.items.length }}</small>
                      </button>
                      <div
                        v-if="expanded.has(`area:${area.id}`)"
                        :id="`structure-area-${area.id}`"
                        class="tree-children"
                      >
                        <button
                          v-for="item in area.items"
                          :key="item.package.id"
                          type="button"
                          class="tree-link tree-package"
                          :class="{ active: isPackageSelected(item.package.id) }"
                          :aria-current="isPackageSelected(item.package.id) ? 'true' : undefined"
                          :data-testid="`structure-package-${item.package.id}`"
                          @click="selectPackage(item.package.id, '')"
                        >
                          <span>{{ item.package.id }}</span>
                          <strong>{{ item.package.name }}</strong>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="tree-node">
                  <button
                    type="button"
                    class="tree-toggle"
                    :aria-expanded="expanded.has('workflows') ? 'true' : 'false'"
                    aria-controls="structure-workflows"
                    data-testid="structure-toggle-workflows"
                    @click="toggle('workflows')"
                  >
                    <span>12 工作流</span>
                    <span aria-hidden="true">{{ expanded.has('workflows') ? '−' : '+' }}</span>
                  </button>
                  <div v-if="expanded.has('workflows')" id="structure-workflows" class="tree-children">
                    <div v-for="stage in stages" :key="stage" class="tree-node">
                      <button
                        type="button"
                        class="tree-toggle"
                        :aria-expanded="expanded.has(`stage:${stage}`) ? 'true' : 'false'"
                        :aria-controls="`structure-stage-${stage}`"
                        :data-testid="`structure-toggle-stage-${stage}`"
                        @click="toggle(`stage:${stage}`)"
                      >
                        <span>{{ stageLabel(stage) }}</span>
                      </button>
                      <div
                        v-if="expanded.has(`stage:${stage}`)"
                        :id="`structure-stage-${stage}`"
                        class="tree-children"
                      >
                        <div
                          v-for="workflow in workflowsByStage[stage]"
                          :key="workflow.id"
                          class="tree-node"
                        >
                          <button
                            type="button"
                            class="tree-toggle"
                            :class="{ active: workflow.id === selectedWorkflowId }"
                            :aria-expanded="expanded.has(`workflow:${workflow.id}`) ? 'true' : 'false'"
                            :aria-controls="`structure-workflow-${workflow.id}`"
                            :data-testid="`structure-toggle-workflow-${workflow.id}`"
                            @click="selectWorkflow(workflow.id)"
                          >
                            <span>{{ workflow.id }}</span>
                            <small>{{ workflow.name }}</small>
                          </button>
                          <div
                            v-if="expanded.has(`workflow:${workflow.id}`)"
                            :id="`structure-workflow-${workflow.id}`"
                            class="tree-children"
                          >
                            <button
                              v-for="item in workflowPackageItems(workflow)"
                              :key="item.package.id"
                              type="button"
                              class="tree-link tree-package"
                              :class="{ active: isPackageSelected(item.package.id) }"
                              :aria-current="isPackageSelected(item.package.id) ? 'true' : undefined"
                              :data-testid="`structure-workflow-package-${item.package.id}`"
                              @click="selectPackage(item.package.id, workflow.id)"
                            >
                              <span>{{ item.package.id }}</span>
                              <strong>{{ item.package.name }}</strong>
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </template>
  </nav>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { achievementCardsFromWorkflow } from '../features/contexts/context-service'
import { useContextsQuery } from '../features/contexts/use-context-queries'
import { useCatalogQuery, useResearchWorkflowMapQuery } from '../features/catalog/use-catalog-query'
import { useContextWorkbenchWorkflowsQuery } from '../features/context-workbench/use-context-workbench-queries'
import {
  buildWorkbenchItems,
  readRouteValue,
  type WorkbenchItem,
} from '../features/context-workbench/context-workbench-model'

const route = useRoute()
const router = useRouter()
const contextsQuery = useContextsQuery()
const currentContextId = computed(() => String(route.params.contextId ?? ''))
const currentContextWorkflowsQuery = useContextWorkbenchWorkflowsQuery(currentContextId)
const catalogQuery = useCatalogQuery()
const workflowMapQuery = useResearchWorkflowMapQuery()

const contexts = computed(() => contextsQuery.data.value?.contexts ?? [])
const isContextFlow = computed(() => route.path === '/contexts' || route.path.startsWith('/contexts/'))
const contextFlowExpanded = computed(() => expanded.value.has('context-flow'))
const structureLoading = computed(
  () => currentContextWorkflowsQuery.isLoading.value || catalogQuery.isLoading.value,
)
const structureError = computed(
  () => Boolean(currentContextWorkflowsQuery.error.value || catalogQuery.error.value),
)

const expanded = ref(new Set<string>(['context-flow', 'aspects', 'workflows']))

const normalizedWorkflows = computed(() => {
  const workflowList = currentContextWorkflowsQuery.data.value
  if (!workflowList) return []
  return workflowList.workflows.map((workflow) => ({
    ...workflow,
    achievement_cards: achievementCardsFromWorkflow(workflow),
  }))
})

const workbenchItems = computed<WorkbenchItem[]>(() => {
  if (!catalogQuery.data.value || !currentContextWorkflowsQuery.data.value) return []
  return buildWorkbenchItems(catalogQuery.data.value, normalizedWorkflows.value).items
})

const areaGroups = computed(() =>
  (catalogQuery.data.value?.areas ?? []).map((area) => ({
    id: area.id,
    name: area.name,
    items: workbenchItems.value.filter((item) => item.area.id === area.id),
  })),
)

const workflowMap = computed(() => workflowMapQuery.data.value ?? null)
const stages = ['Explore', 'Execute', 'Express'] as const
const workflowsByStage = computed(() => {
  const result: Record<(typeof stages)[number], Array<{ id: string; name: string; work_package_ids: string[] }>> = {
    Explore: [],
    Execute: [],
    Express: [],
  }
  for (const workflow of workflowMap.value?.workflows ?? []) {
    if (workflow.stage === 'Explore') result.Explore.push(workflow)
    else if (workflow.stage === 'Execute') result.Execute.push(workflow)
    else result.Express.push(workflow)
  }
  return result
})

const itemByPackageId = computed(() => new Map(workbenchItems.value.map((item) => [item.package.id, item])))
const selectedWorkflowId = computed(() => readRouteValue(route.query.workflow))
const selectedWorkPackageId = computed(() => readRouteValue(route.query.wp))

function stageLabel(stage: (typeof stages)[number]): string {
  if (stage === 'Explore') return '探索 Explore'
  if (stage === 'Execute') return '执行 Execute'
  return '表达 Express'
}

function workflowPackageItems(workflow: { work_package_ids: string[] }): WorkbenchItem[] {
  return workflow.work_package_ids.flatMap((workPackageId) => {
    const item = itemByPackageId.value.get(workPackageId)
    return item ? [item] : []
  })
}

function toggle(key: string): void {
  const next = new Set(expanded.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expanded.value = next
}

function isPackageSelected(workPackageId: string): boolean {
  return selectedWorkPackageId.value === workPackageId
}

function selectContext(contextId: string): void {
  if (route.params.contextId === contextId) {
    toggle(`context:${contextId}`)
    return
  }
  const next = new Set(expanded.value)
  next.add(`context:${contextId}`)
  next.add('aspects')
  expanded.value = next
  void router.push({ path: `/contexts/${encodeURIComponent(contextId)}` })
}

function selectWorkflow(workflowId: string): void {
  if (selectedWorkflowId.value === workflowId) {
    toggle(`workflow:${workflowId}`)
    return
  }
  const next = new Set(expanded.value)
  next.add(`workflow:${workflowId}`)
  expanded.value = next
  void router.push({
    path: route.path,
    query: { ...route.query, view: 'workflows', workflow: workflowId },
  })
}

function containingWorkflowId(workPackageId: string): string {
  return (
    Object.values(workflowsByStage.value)
      .flat()
      .find(workflow => workflow.work_package_ids.includes(workPackageId))?.id ?? ''
  )
}

function selectPackage(workPackageId: string, workflowId: string): void {
  const query: Record<string, string> = {}
  for (const [key, value] of Object.entries(route.query)) {
    if (typeof value === 'string' && value) query[key] = value
  }
  query.wp = workPackageId
  const targetWorkflowId = workflowId || containingWorkflowId(workPackageId)
  if (targetWorkflowId) query.workflow = targetWorkflowId
  if (query.view === 'workflows') {
    query.view = 'workflows'
    query.workflow = targetWorkflowId
  }
  delete query.preview
  delete query.preview_rail
  void router.push({ path: route.path, query })
}

watch(
  currentContextId,
  (contextId) => {
    if (!contextId) return
    const key = `context:${contextId}`
    if (!expanded.value.has(key)) {
      const next = new Set(expanded.value)
      next.add(key)
      expanded.value = next
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.structure-tree {
  display: grid;
  gap: 5px;
  font-size: 0.82rem;
}

.tree-root-link,
.tree-link,
.tree-toggle {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 7px;
  width: 100%;
  padding: 7px 8px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #dcecf2;
  font: inherit;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
}

.tree-root-link:hover,
.tree-link:hover,
.tree-toggle:hover {
  background: #2b5d78;
}

.tree-root-link.router-link-active,
.tree-link.active,
.tree-toggle.active {
  background: #2b5d78;
  color: #fff;
  font-weight: 800;
}

.tree-children {
  display: grid;
  gap: 3px;
  margin: 3px 0 3px 12px;
  padding-left: 8px;
  border-left: 1px solid #43718d;
}

.tree-package {
  align-items: flex-start;
  flex-direction: column;
  gap: 1px;
}

.tree-package span {
  color: #a9c4d2;
  font-size: 0.68rem;
  font-weight: 850;
}

.tree-package strong {
  overflow-wrap: anywhere;
  font-size: 0.78rem;
  line-height: 1.3;
}

.tree-toggle span:first-child {
  min-width: 0;
  overflow-wrap: anywhere;
}

.tree-toggle small {
  color: #a9c4d2;
  overflow-wrap: anywhere;
  white-space: normal;
}

.tree-muted,
.tree-error {
  margin: 4px 0;
  padding: 0 8px;
  color: #b9d0db;
  font-size: 0.75rem;
}

.tree-error {
  color: #ffd7d7;
}
</style>



