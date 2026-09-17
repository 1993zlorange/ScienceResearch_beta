<template>
  <section class="work-package-detail" data-testid="work-package-detail" aria-live="polite">
    <header class="panel-head">
      <h2>工作包详情</h2>
      <span class="badge">{{ workflow.work_package_id }}</span>
    </header>
    <div class="detail-block detail-overview">
      <h3>{{ package.name }}</h3>
      <dl class="detail-fields">
        <div><dt>流程 ID</dt><dd>{{ workflow.id }}</dd></div>
        <div><dt>状态</dt><dd>{{ workflow.is_completed ? '已完成' : '进行中' }}</dd></div>
        <div><dt>选择</dt><dd>{{ workflow.selection_status }}</dd></div>
        <div><dt>模式</dt><dd>{{ workflow.mode }}</dd></div>
      </dl>
      <div class="detail-actions">
        <button
          type="button"
          class="primary"
          data-testid="complete-workflow"
          :disabled="completionBusy || workflow.is_completed"
          @click="$emit('complete')"
        >{{ completionBusy ? '保存中…' : '标记完成' }}</button>
        <button
          type="button"
          data-testid="cancel-workflow-completion"
          :disabled="completionBusy || !workflow.is_completed"
          @click="$emit('cancelCompletion')"
        >取消完成</button>
      </div>
      <p v-if="completionError" class="state-error" role="alert">{{ completionError }}</p>
      <p v-else-if="completionSuccess" class="state-success" role="status">完成状态已保存。</p>
    </div>
    <div class="detail-block">
      <p class="detail-label">任务背景与动作</p>
      <p>{{ package.action }}</p>
      <p class="detail-label">可验收交付物</p>
      <p>{{ package.deliverable }}</p>
      <p class="detail-label">组会汇报措辞</p>
      <p>{{ templateReport }}</p>
      <p class="detail-label">研究示例</p>
      <p>{{ templateExample }}</p>
    </div>

    <section class="card-create-panel" aria-label="新增成效卡">
      <h3>新增成效卡</h3>
      <form class="card-create-form" data-testid="create-achievement-card-form" @submit.prevent="$emit('createCard')">
        <label>
          日期
          <input v-model="cardForm.event_date" type="date" data-testid="achievement-card-date" required>
        </label>
        <label>
          事件
          <input v-model="cardForm.event_name" type="text" data-testid="achievement-card-event" required placeholder="例如：完成实验验证">
        </label>
        <label>
          描述
          <textarea v-model="cardForm.description" rows="3" data-testid="achievement-card-description" placeholder="记录关键证据和结论"></textarea>
        </label>
        <label class="checkbox-label">
          <input v-model="cardForm.important" type="checkbox" data-testid="achievement-card-important">
          标记为重点成效
        </label>
        <button type="submit" class="primary" data-testid="create-card-submit" :disabled="cardCreateBusy || cardFormInvalid">
          {{ cardCreateBusy ? '创建中…' : '新增成效卡' }}
        </button>
      </form>
      <p v-if="cardFormInvalid" class="muted">日期和事件为必填。</p>
      <p v-if="cardCreateError" class="state-error" role="alert">{{ cardCreateError }}</p>
      <p v-else-if="cardCreateSuccess" class="state-success" role="status">成效卡已创建。</p>
    </section>

    <section class="selected-cards" aria-label="成效卡">
      <h3>当前工作包成效卡（{{ workflow.achievement_cards.length }}）</h3>
      <p v-if="workflow.achievement_cards.length === 0">当前工作包暂无成效卡。</p>
      <AchievementCardItem
        v-for="card in workflow.achievement_cards"
        :key="card.id"
        :card="card"
        :expanded="expandedCardIds.has(card.id)"
        :importance-busy="importanceBusy && importanceCardId === card.id"
        :importance-error="importanceCardId === card.id ? importanceError : ''"
        :importance-success="importanceSuccessCardId === card.id"
        :attachment-busy="attachmentBusy && attachmentCardId === card.id"
        :attachment-error="attachmentCardId === card.id ? attachmentError : ''"
        :attachment-success="attachmentSuccessCardId === card.id"
        :active-preview-id="activePreviewId"
        @toggle="$emit('toggleCard', $event)"
        @set-importance="importance => $emit('toggleImportance', card, importance)"
        @upload="file => $emit('uploadAttachment', card.id, file)"
        @preview="attachment => $emit('previewAttachment', attachment)"
      />
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AchievementCardItem from './achievement-card-item.vue'
import type {
  AchievementAttachment,
  CatalogWorkPackage,
  WorkbenchWorkflow,
} from '../context-workbench-types'

const props = defineProps<{
  workflow: WorkbenchWorkflow
  package: CatalogWorkPackage
  expandedCardIds: Set<string>
  completionBusy: boolean
  completionError: string
  completionSuccess: boolean
  cardCreateBusy: boolean
  cardCreateError: string
  cardCreateSuccess: boolean
  cardForm: {
    event_date: string
    event_name: string
    description: string
    important: boolean
  }
  cardFormInvalid: boolean
  importanceBusy: boolean
  importanceCardId: string
  importanceError: string
  importanceSuccessCardId: string
  attachmentBusy: boolean
  attachmentCardId: string
  attachmentError: string
  attachmentSuccessCardId: string
  activePreviewId: string
}>()

defineEmits<{
  toggleCard: [cardId: string]
  complete: []
  cancelCompletion: []
  createCard: []
  toggleImportance: [card: WorkbenchWorkflow['achievement_cards'][number], important: boolean]
  uploadAttachment: [cardId: string, file: File]
  previewAttachment: [attachment: AchievementAttachment]
}>()

const templateReport = computed(() => {
  const report = props.package.template.report
  return typeof report === 'string' && report ? report : '问题—行动—证据—结论—下一步'
})

const templateExample = computed(() => {
  const example = props.package.template.example
  return typeof example === 'string' && example ? example : '请结合当前课题记录具体研究示例。'
})
</script>
