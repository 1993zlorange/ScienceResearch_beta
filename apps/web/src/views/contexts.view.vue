<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElInput,
  ElProgress,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus'
import type { FormInstance, FormRules, TableInstance } from 'element-plus'
import {
  ApiError,
  achievementCardsFromWorkflow,
  type AchievementCard,
  type Context,
  type CreatedContext,
  type Workflow,
} from '../features/contexts/context-service'
import {
  useCreateAchievementCardMutation,
  useCreateContextMutation,
  useContextsQuery,
  useContextWorkflowsQuery,
} from '../features/contexts/use-context-queries'

interface WorkflowRow extends Workflow {
  card_count: number
}

interface AreaRow {
  areaId: string
  total: number
  completed: number
  cardCount: number
}

const contextFormRef = ref<FormInstance>()
const contextsTableRef = ref<TableInstance>()
const selectedContextId = ref('')
const selectedWorkflowId = ref('')
const lastCreatedCard = ref<AchievementCard | null>(null)

const contextForm = reactive({
  name: '',
  problem: '',
  goal: '',
  owner: '',
})
const contextRules: FormRules = {
  problem: [{ required: true, message: '研究问题必填', trigger: 'blur' }],
}

const cardFormRef = ref<FormInstance>()
const cardForm = reactive({
  eventDate: '',
  eventName: '',
  description: '',
  important: false,
})
const cardRules: FormRules = {
  eventDate: [
    { required: true, message: '事件日期必填', trigger: 'blur' },
    { pattern: /^\d{4}-\d{2}-\d{2}$/, message: '请使用 YYYY-MM-DD', trigger: 'blur' },
  ],
  eventName: [{ required: true, message: '事件名必填', trigger: 'blur' }],
}

const contextsQuery = useContextsQuery()
const workflowsQuery = useContextWorkflowsQuery(selectedContextId)
const createContextMutation = useCreateContextMutation()
const createCardMutation = useCreateAchievementCardMutation()

const contexts = computed(() => contextsQuery.data.value?.contexts ?? [])
const workflows = computed(() => workflowsQuery.data.value?.workflows ?? [])

const cardProjection = computed(() => {
  const cardsByWorkflow = new Map<string, AchievementCard[]>()
  let projectionError: string | null = null
  for (const workflow of workflows.value) {
    try {
      cardsByWorkflow.set(workflow.id, achievementCardsFromWorkflow(workflow))
    } catch (error) {
      projectionError = error instanceof ApiError ? error.detail : '成效卡数据格式无效'
    }
  }
  return { cardsByWorkflow, projectionError }
})

const workflowRows = computed<WorkflowRow[]>(() =>
  workflows.value.map((workflow) => ({
    ...workflow,
    card_count: cardProjection.value.cardsByWorkflow.get(workflow.id)?.length ?? 0,
  })),
)

const selectedWorkflow = computed(() => workflows.value.find((workflow) => workflow.id === selectedWorkflowId.value))
const selectedCards = computed(() =>
  selectedWorkflow.value ? cardProjection.value.cardsByWorkflow.get(selectedWorkflow.value.id) ?? [] : [],
)

const areaRows = computed<AreaRow[]>(() => {
  const areas = new Map<string, AreaRow>()
  for (const workflow of workflows.value) {
    const areaId = workflow.area_id ?? 'UNASSIGNED'
    const row = areas.get(areaId) ?? { areaId, total: 0, completed: 0, cardCount: 0 }
    row.total += 1
    row.completed += Number(workflow.is_completed)
    row.cardCount += cardProjection.value.cardsByWorkflow.get(workflow.id)?.length ?? 0
    areas.set(areaId, row)
  }
  return [...areas.values()].sort((left, right) => left.areaId.localeCompare(right.areaId))
})

const totalCards = computed(() =>
  workflows.value.reduce((total, workflow) => total + (cardProjection.value.cardsByWorkflow.get(workflow.id)?.length ?? 0), 0),
)
const progress = computed(() => workflowsQuery.data.value?.progress)
const progressPercentage = computed(() => progress.value?.ratio ?? 0)

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.detail
  return error instanceof Error && error.message ? error.message : fallback
}

function contextWorkbenchPath(contextId: string): string {
  return `/contexts/${encodeURIComponent(contextId)}`
}

function selectContext(context: Context | null): void {
  selectedContextId.value = context?.id ?? ''
  selectedWorkflowId.value = ''
  resetCardForm()
}

async function submitContext(): Promise<void> {
  const form = contextFormRef.value
  if (!form) return
  try {
    await form.validate()
  } catch {
    return
  }
  let created: CreatedContext
  try {
    created = await createContextMutation.mutateAsync({
      type: 'topic',
      name: contextForm.name.trim(),
      problem: contextForm.problem.trim(),
      goal: contextForm.goal.trim(),
      owner: contextForm.owner.trim() || 'author',
    })
  } catch {
    return
  }
  selectedContextId.value = created.id
  selectedWorkflowId.value = ''
  resetCardForm()
  contextForm.name = ''
  contextForm.problem = ''
  contextForm.goal = ''
  contextForm.owner = ''
  requestAnimationFrame(() => {
    const createdContext = contexts.value.find((item) => item.id === created.id)
    if (createdContext) contextsTableRef.value?.setCurrentRow(createdContext)
  })
}

function resetCardForm(): void {
  lastCreatedCard.value = null
  cardForm.eventDate = ''
  cardForm.eventName = ''
  cardForm.description = ''
  cardForm.important = false
  cardFormRef.value?.clearValidate()
}

function selectWorkflow(workflow: WorkflowRow | null): void {
  selectedWorkflowId.value = workflow?.id ?? ''
  lastCreatedCard.value = null
  cardFormRef.value?.clearValidate()
}

async function submitAchievementCard(): Promise<void> {
  const form = cardFormRef.value
  const workflow = selectedWorkflow.value
  if (!form || !workflow || !selectedContextId.value) return
  try {
    await form.validate()
  } catch {
    return
  }
  let card: AchievementCard
  try {
    card = await createCardMutation.mutateAsync({
      context_id: selectedContextId.value,
      workflow_id: workflow.id,
      event_date: cardForm.eventDate.trim(),
      event_name: cardForm.eventName.trim(),
      description: cardForm.description.trim(),
      actor: 'author',
      important: cardForm.important,
    })
  } catch {
    return
  }
  lastCreatedCard.value = card
  cardForm.eventDate = ''
  cardForm.eventName = ''
  cardForm.description = ''
  cardForm.important = false
  form.clearValidate()
}

</script>

<template>
  <main class="contexts-page" data-runtime="vue-target-stack">
    <header class="page-header">
      <p class="eyebrow">课题流程 · 原生目标栈</p>
      <h1>课题与研究流程</h1>
      <p class="page-description">
        选择课题概览后，点击“打开课题流程”进入与历史版本一致的工作包目录、筛选器、详情操作和成效卡附件工作台。
      </p>
      <nav class="page-navigation" aria-label="原生页面导航">
        <RouterLink class="text-link" to="/work-packages">返回工作包目录</RouterLink>
      </nav>
    </header>

    <section class="context-layout" aria-label="课题与工作流">
      <section class="context-list-panel" aria-labelledby="context-list-title">
        <ElCard shadow="never">
          <template #header>
            <div class="panel-header">
              <h2 id="context-list-title">课题列表</h2>
              <ElTag type="info" effect="plain">{{ contexts.length }} 个课题</ElTag>
            </div>
          </template>

          <div v-if="contextsQuery.isPending.value" class="state-box" role="status">
            <ElProgress :percentage="100" :show-text="false" :stroke-width="4" />
            <p>正在加载课题列表…</p>
          </div>
          <div v-else-if="contextsQuery.error.value" class="state-box state-error" role="alert">
            <ElAlert type="error" title="课题列表加载失败" show-icon :closable="false" />
            <p>{{ errorMessage(contextsQuery.error.value, '请稍后重试。') }}</p>
            <ElButton type="primary" @click="() => contextsQuery.refetch()">重试</ElButton>
          </div>
          <ElEmpty v-else-if="contexts.length === 0" description="暂无课题，请先创建研究上下文。" />
          <ElTable
            v-else
            ref="contextsTableRef"
            :data="contexts"
            row-key="id"
            highlight-current-row
            data-testid="context-table"
            @current-change="selectContext"
          >
            <ElTableColumn prop="name" label="名称" min-width="150" show-overflow-tooltip />
            <ElTableColumn prop="problem" label="研究问题" min-width="220" show-overflow-tooltip />
            <ElTableColumn prop="owner" label="负责人" width="100" />
            <ElTableColumn prop="lifecycle_state" label="状态" width="100" />
            <ElTableColumn label="课题流程" width="140" fixed="right">
              <template #default="{ row }">
                <RouterLink
                  class="context-workbench-link"
                  :to="contextWorkbenchPath(String(row.id))"
                  data-testid="open-context-workbench"
                >
                  打开课题流程
                </RouterLink>
              </template>
            </ElTableColumn>
          </ElTable>
        </ElCard>

        <ElCard shadow="never" class="create-context-card">
          <template #header><h2>创建课题</h2></template>
          <ElForm ref="contextFormRef" :model="contextForm" :rules="contextRules" label-position="top">
            <ElFormItem label="课题名称" prop="name">
              <ElInput v-model="contextForm.name" name="context-name" placeholder="例如：博士研究主线" />
            </ElFormItem>
            <ElFormItem label="研究问题" prop="problem" required>
              <ElInput
                v-model="contextForm.problem"
                type="textarea"
                :rows="3"
                name="context-problem"
                placeholder="必填：说明要解决的研究问题"
              />
            </ElFormItem>
            <ElFormItem label="研究目标" prop="goal">
              <ElInput v-model="contextForm.goal" type="textarea" :rows="2" name="context-goal" />
            </ElFormItem>
            <ElFormItem label="负责人" prop="owner">
              <ElInput v-model="contextForm.owner" name="context-owner" placeholder="默认 author" />
            </ElFormItem>
            <ElButton
              type="primary"
              :loading="createContextMutation.isPending.value"
              data-testid="create-context-button"
              @click="submitContext"
            >
              创建课题
            </ElButton>
            <p v-if="createContextMutation.error.value" class="mutation-error" role="alert">
              {{ errorMessage(createContextMutation.error.value, '课题创建失败，请重试。') }}
            </p>
          </ElForm>
        </ElCard>
      </section>

      <section class="workflow-panel" aria-labelledby="workflow-title">
        <ElCard shadow="never">
          <template #header>
            <div class="panel-header">
              <h2 id="workflow-title">8 方面 · 68 流程</h2>
              <ElTag type="success" effect="plain">{{ workflows.length }} / 68</ElTag>
            </div>
          </template>

          <ElEmpty v-if="!selectedContextId" description="选择或创建课题后加载工作流。" />
          <div v-else-if="workflowsQuery.isPending.value" class="state-box" role="status">
            <ElProgress :percentage="100" :show-text="false" :stroke-width="4" />
            <p>正在加载 68 条工作流…</p>
          </div>
          <div v-else-if="workflowsQuery.error.value" class="state-box state-error" role="alert">
            <ElAlert type="error" title="工作流加载失败" show-icon :closable="false" />
            <p>{{ errorMessage(workflowsQuery.error.value, '请稍后重试。') }}</p>
            <ElButton type="primary" @click="() => workflowsQuery.refetch()">重试</ElButton>
          </div>
          <template v-else>
            <div class="progress-grid" data-testid="context-progress">
              <article>
                <span>完成进度</span>
                <strong>{{ progress?.completed ?? 0 }} / {{ progress?.total ?? 0 }}</strong>
                <ElProgress :percentage="progressPercentage" :stroke-width="10" />
              </article>
              <article>
                <span>研究方面</span>
                <strong>{{ areaRows.length }}</strong>
                <p>按 workflow area_id 汇总</p>
              </article>
              <article>
                <span>工作流</span>
                <strong>{{ workflows.length }}</strong>
                <p>期望 {{ progress?.expected_total ?? 68 }}</p>
              </article>
              <article>
                <span>成效卡</span>
                <strong>{{ totalCards }}</strong>
                <p>当前课题累计</p>
              </article>
            </div>

            <ElAlert
              v-if="progress?.snapshot_incomplete"
              class="snapshot-warning"
              type="warning"
              title="工作流快照不完整"
              show-icon
              :closable="false"
            />
            <ElAlert
              v-if="cardProjection.projectionError"
              class="snapshot-warning"
              type="error"
              :title="cardProjection.projectionError"
              show-icon
              :closable="false"
            />

            <h3>方面进度</h3>
            <ElTable :data="areaRows" row-key="areaId" data-testid="area-progress-table">
              <ElTableColumn prop="areaId" label="方面 ID" min-width="130" />
              <ElTableColumn prop="total" label="流程数" width="90" />
              <ElTableColumn prop="completed" label="完成" width="80" />
              <ElTableColumn prop="cardCount" label="成效卡" width="90" />
            </ElTable>

            <h3>工作流与成效卡</h3>
            <ElTable
              :data="workflowRows"
              row-key="id"
              highlight-current-row
              data-testid="workflow-table"
              @current-change="selectWorkflow"
            >
              <ElTableColumn prop="work_package_id" label="工作包" min-width="120" />
              <ElTableColumn prop="area_id" label="方面" min-width="120" />
              <ElTableColumn prop="status" label="状态" width="100" />
              <ElTableColumn prop="card_count" label="成效卡" width="90" />
              <ElTableColumn prop="selection_status" label="选择状态" width="110" />
            </ElTable>

            <section class="card-workbench" aria-labelledby="selected-workflow-title">
              <header>
                <h3 id="selected-workflow-title">成效卡</h3>
                <p v-if="selectedWorkflow">当前流程：{{ selectedWorkflow.work_package_id }}（{{ selectedWorkflow.id }}）</p>
                <p v-else>请在上方表格选择一个 workflow。</p>
              </header>

              <ElForm
                ref="cardFormRef"
                :model="cardForm"
                :rules="cardRules"
                label-position="top"
                :disabled="!selectedWorkflow"
                class="card-form"
              >
                <ElFormItem label="日期" prop="eventDate" required>
                  <ElInput v-model="cardForm.eventDate" name="card-date" placeholder="YYYY-MM-DD" />
                </ElFormItem>
                <ElFormItem label="事件名" prop="eventName" required>
                  <ElInput v-model="cardForm.eventName" name="card-event-name" placeholder="例如：阶段成果确认" />
                </ElFormItem>
                <ElFormItem label="描述" prop="description">
                  <ElInput v-model="cardForm.description" type="textarea" :rows="3" name="card-description" />
                </ElFormItem>
                <ElFormItem label="重要" prop="important">
                  <ElSwitch v-model="cardForm.important" name="card-important" />
                </ElFormItem>
                <ElButton
                  type="primary"
                  :disabled="!selectedWorkflow"
                  :loading="createCardMutation.isPending.value"
                  data-testid="create-card-button"
                  @click="submitAchievementCard"
                >
                  创建成效卡
                </ElButton>
                <p v-if="createCardMutation.error.value" class="mutation-error" role="alert">
                  {{ errorMessage(createCardMutation.error.value, '成效卡创建失败，请重试。') }}
                </p>
                <p v-if="lastCreatedCard" class="mutation-success" role="status">
                  已创建：{{ lastCreatedCard.event_date }} · {{ lastCreatedCard.event_name }}
                </p>
              </ElForm>

              <div class="card-list">
                <ElEmpty v-if="selectedCards.length === 0" description="当前流程暂无成效卡。" />
                <ul v-else data-testid="achievement-card-list">
                  <li v-for="card in selectedCards" :key="card.id">
                    <strong>{{ card.event_date }} · {{ card.event_name }}</strong>
                    <span>{{ card.description || '无描述' }}</span>
                    <ElTag v-if="card.is_important" type="danger" effect="plain">重要</ElTag>
                  </li>
                </ul>
              </div>
            </section>
          </template>
        </ElCard>
      </section>
    </section>
  </main>
</template>




