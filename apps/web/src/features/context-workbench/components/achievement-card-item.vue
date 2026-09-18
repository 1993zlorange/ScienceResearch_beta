<template>
  <article class="achievement-card" :class="{ important: card.is_important }">
    <div class="card-heading">
      <button
        class="card-toggle"
        type="button"
        :data-testid="`achievement-card-toggle-${card.id}`"
        :aria-expanded="expanded ? 'true' : 'false'"
        :aria-controls="`achievement-card-detail-${card.id}`"
        @click="$emit('toggle', card.id)"
      >
        <strong>{{ card.event_date }} · {{ card.event_name }}</strong>
        <span>{{ card.is_important ? '重点成效' : '成效卡' }}</span>
      </button>
    </div>
    <p class="card-summary-meta">附件 {{ card.attachments.length }} 件</p>
    <div
      v-if="expanded"
      :id="`achievement-card-detail-${card.id}`"
      class="card-actions"
      :data-card-id="card.id"
      :data-card-expanded="expanded ? 'true' : 'false'"
    >
      <p class="card-description">{{ card.description || '无描述' }}</p>
      <dl class="card-facts">
        <div><dt>状态</dt><dd>{{ card.status }}</dd></div>
        <div><dt>附件数量</dt><dd>{{ card.attachments.length }}</dd></div>
      </dl>
      <div class="importance-actions">
        <button
          type="button"
          :data-testid="`achievement-card-importance-${card.id}`"
          :disabled="importanceBusy"
          @click="$emit('setImportance', !card.is_important)"
        >{{ importanceBusy ? '保存中…' : card.is_important ? '取消重点标记' : '标记为重点' }}</button>
        <span v-if="importanceError" role="alert">{{ importanceError }}</span>
        <span v-else-if="importanceSuccess" role="status">标记已保存。</span>
      </div>

      <section class="attachments" aria-label="附件与证据" :data-attachment-state="attachmentBusy ? 'UPLOADING' : 'READY'">
        <h4>附件与证据</h4>
        <p v-if="attachments.length === 0" class="muted">暂无附件。</p>
        <ul v-else class="attachment-list" :data-testid="`attachment-list-${card.id}`">
          <li v-for="attachment in attachments" :key="attachment.id" class="attachment-row">
            <button
              type="button"
              class="attachment-preview"
              :data-testid="`attachment-preview-${attachment.id}`"
              :aria-current="attachment.id === activePreviewId ? 'true' : undefined"
              @click="$emit('preview', attachment)"
            >预览 {{ attachment.original_name }}</button>
            <a
              :href="achievementAttachmentDownloadUrl(attachment.id)"
              :download="attachment.original_name"
              :data-testid="`attachment-download-${attachment.id}`"
            >下载</a>
            <span class="attachment-size">{{ formatSize(attachment.size_bytes) }}</span>
          </li>
        </ul>
        <form class="attachment-upload" data-testid="attachment-upload-form" @submit.prevent="submitFile">
          <label class="attachment-file-label">
            选择附件
            <input
              ref="fileInput"
              type="file"
              required
              data-testid="attachment-file-input"
              @change="selectFile"
            >
          </label>
          <button type="submit" :disabled="attachmentBusy || !selectedFile">
            {{ attachmentBusy ? '上传中…' : '上传附件' }}
          </button>
        </form>
        <p v-if="attachmentBusy" role="status">附件上传中…</p>
        <p v-else-if="attachmentError" role="alert" data-testid="attachment-error">{{ attachmentError }}</p>
        <p v-else-if="attachmentSuccess" role="status" data-testid="attachment-success">附件已上传。</p>
      </section>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AchievementAttachment, AchievementCard } from '../context-workbench-types'
import { achievementAttachmentDownloadUrl } from '../../contexts/context-service'

const props = defineProps<{
  card: AchievementCard
  expanded: boolean
  activePreviewId?: string
  importanceBusy?: boolean
  importanceError?: string
  importanceSuccess?: boolean
  attachmentBusy?: boolean
  attachmentError?: string
  attachmentSuccess?: boolean
}>()

const attachments = computed(() => props.card.attachments as AchievementAttachment[])

const emit = defineEmits<{
  toggle: [cardId: string]
  setImportance: [important: boolean]
  upload: [file: File]
  preview: [attachment: AchievementAttachment]
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)

function selectFile(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

function submitFile() {
  if (!selectedFile.value || props.attachmentBusy) return
  emit('upload', selectedFile.value)
  selectedFile.value = null
  if (fileInput.value) fileInput.value.value = ''
}

function formatSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}
</script>
