<template>
  <section class="package-cards-panel" :data-testid="`package-cards-${workflow.work_package_id}`" aria-label="当前工作包成效卡">
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
        :importance-success-card-id="importanceSuccessCardId === card.id"
        :attachment-busy="attachmentBusy && attachmentCardId === card.id"
        :attachment-error="attachmentCardId === card.id ? attachmentError : ''"
        :attachment-success-card-id="attachmentSuccessCardId === card.id"
        :active-preview-id="activePreviewId"
        @toggle="$emit('toggleCard', $event)"
        @set-importance="important => $emit('toggleImportance', card, important)"
        @upload="file => $emit('uploadAttachment', card.id, file)"
        @preview="attachment => $emit('previewAttachment', attachment)"
      />
    </section>
  </section>
</template>

<script setup lang="ts">
import AchievementCardItem from './achievement-card-item.vue'
import type {
  AchievementAttachment,
  WorkbenchWorkflow,
} from '../context-workbench-types'

defineProps<{
  workflow: WorkbenchWorkflow
  expandedCardIds: Set<string>
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
  toggleImportance: [card: WorkbenchWorkflow['achievement_cards'][number], important: boolean]
  uploadAttachment: [cardId: string, file: File]
  previewAttachment: [attachment: AchievementAttachment]
}>()
</script>
