<template>
  <section class="progress-panel" data-testid="context-workbench-progress">
    <button
      class="disclosure-toggle"
      type="button"
      data-testid="progress-toggle"
      :aria-expanded="expanded ? 'true' : 'false'"
      aria-controls="workbench-progress-body"
      @click="$emit('toggle')"
    >课题进展</button>
    <div v-show="expanded" id="workbench-progress-body">
      <p data-testid="workbench-progress-value">
        {{ progress.completed }}/{{ progress.total }} 已完成 ·
        {{ progress.ratio === null ? '—' : `${progress.ratio}%` }}
      </p>
      <p v-if="progress.snapshot_incomplete" class="warning">目录快照不完整，请核对工作包。</p>
      <div class="progress-cards" data-testid="visible-card-summaries">
        <h3>当前筛选可见成效</h3>
        <p v-if="visibleCards.length === 0">当前筛选条件下没有可见成效卡。</p>
        <ul v-else>
          <li v-for="summary in visibleCards.slice(0, 6)" :key="summary.card.id">
            <span>{{ summary.card.event_date }} · {{ summary.card.event_name }}</span>
            <small>{{ summary.workPackageId }} · {{ summary.workPackageName }}</small>
          </li>
        </ul>
        <p v-if="visibleCards.length > 6">另有 {{ visibleCards.length - 6 }} 张成效卡可在目录中查看。</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { AchievementCard, Progress } from '../context-workbench-types'

export interface VisibleCardSummary {
  card: AchievementCard
  workPackageId: string
  workPackageName: string
}

defineProps<{
  progress: Progress
  expanded: boolean
  visibleCards: VisibleCardSummary[]
}>()

defineEmits<{ toggle: [] }>()
</script>

