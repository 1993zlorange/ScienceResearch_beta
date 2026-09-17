<template>
  <section class="research-workflow-map" data-testid="research-workflow-map" aria-label="12 个科研工作流">
    <header class="panel-head">
      <div>
        <h2>12 个科研工作流</h2>
        <p>按责任边界聚合当前课题的工作包与成效卡；不改变 68 条执行快照。</p>
      </div>
      <span class="badge">{{ workflowItems.length }} / 12</span>
    </header>
    <div class="workflow-stage-list">
      <section
        v-for="stage in stages"
        :key="stage"
        class="workflow-stage"
        :data-stage="stage"
        :aria-label="`${stage} 工作流`"
      >
        <h3>{{ stageName(stage) }}</h3>
        <article
          v-for="entry in workflowItems.filter((item) => item.workflow.stage === stage)"
          :key="entry.workflow.id"
          class="research-workflow-card"
          :data-workflow-id="entry.workflow.id"
          :class="{ selected: entry.workflow.id === selectedWorkflowId }"
        >
          <div class="workflow-heading">
            <button
              type="button"
              class="workflow-toggle"
              :data-testid="`research-workflow-toggle-${entry.workflow.id}`"
              :aria-expanded="entry.workflow.id === selectedWorkflowId ? 'true' : 'false'"
              :aria-controls="`research-workflow-body-${entry.workflow.id}`"
              @click="$emit('selectWorkflow', entry.workflow.id)"
            >
              <span class="workflow-code">{{ entry.workflow.id }}</span>
              <strong>{{ entry.workflow.name }}</strong>
              <small>{{ entry.workflow.owner_role }} · {{ entry.items.length }} 个工作包</small>
            </button>
          </div>
          <p>{{ entry.workflow.description }}</p>
          <p class="workflow-outputs">
            <span v-for="output in entry.workflow.outputs" :key="output">{{ output }}</span>
          </p>
          <div
            v-if="entry.workflow.id === selectedWorkflowId"
            :id="`research-workflow-body-${entry.workflow.id}`"
            class="workflow-package-list"
          >
            <p v-if="entry.items.length === 0" class="muted">当前筛选条件下没有映射工作包。</p>
            <article
              v-for="item in entry.items"
              :key="item.package.id"
              class="workflow-package"
              :data-work-package="item.package.id"
              :data-status="item.status"
            >
              <button
                type="button"
                :data-testid="`research-workflow-package-${item.package.id}`"
                @click="$emit('openWorkPackage', item.package.id)"
              >
                <span>{{ item.package.id }}</span>
                <strong>{{ item.package.name }}</strong>
                <small>{{ workflowStatusLabel(item.status) }} · {{ item.workflow.achievement_cards.length }} 张成效卡</small>
              </button>
              <ul v-if="item.workflow.achievement_cards.length" class="workflow-card-summary">
                <li
                  v-for="card in item.workflow.achievement_cards.filter(card => card.is_important).slice(0, 3)"
                  :key="card.id"
                >
                  <strong>重点</strong> {{ card.event_date }} · {{ card.event_name }}
                </li>
              </ul>
            </article>
          </div>
        </article>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { workflowStatusLabel, type ResearchWorkflowViewItem } from '../context-workbench-model'

const props = defineProps<{
  workflowItems: ResearchWorkflowViewItem[]
  selectedWorkflowId?: string
}>()

defineEmits<{
  selectWorkflow: [workflowId: string]
  openWorkPackage: [workPackageId: string]
}>()

const stages = ['Explore', 'Execute', 'Express'] as const

function stageName(stage: (typeof stages)[number]): string {
  if (stage === 'Explore') return '探索 Explore'
  if (stage === 'Execute') return '执行 Execute'
  return '表达 Express'
}

const workflowItems = computed(() => props.workflowItems)
</script>
