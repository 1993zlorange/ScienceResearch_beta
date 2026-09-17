<template>
  <main class="delete-page" data-testid="context-delete-page">
    <div class="context-toolbar">
      <RouterLink class="back-link" data-testid="back-to-context" :to="`/contexts/${contextId}`">返回课题</RouterLink>
      <RouterLink class="back-link" data-testid="back-to-contexts" to="/contexts">返回课题列表</RouterLink>
    </div>

    <div v-if="loading" class="state-loading" role="status">课题详情加载中…</div>
    <div v-else-if="loadError" class="state-error" role="alert">
      <p data-testid="delete-load-error">{{ loadError }}</p>
      <button type="button" data-testid="delete-reload" @click="loadContext">重试</button>
    </div>

    <template v-else-if="context">
      <section class="context-summary" data-testid="delete-context-summary">
        <h1>删除课题</h1>
        <h2>{{ context.name }}</h2>
        <p>{{ context.problem }}</p>
        <dl>
          <div><dt>课题 ID</dt><dd>{{ context.id }}</dd></div>
          <div><dt>负责人</dt><dd>{{ context.owner }}</dd></div>
          <div><dt>当前版本</dt><dd>{{ context.row_version }}</dd></div>
        </dl>
      </section>

      <section class="branches" aria-label="附件处理分支">
        <h2>选择附件处理方式</h2>
        <div class="branch-actions">
          <button
            type="button"
            data-testid="select-retain-branch"
            :disabled="deleting || preparation !== null"
            @click="prepare(true)"
          >保留附件文件并归档后删除</button>
          <button
            type="button"
            class="danger"
            data-testid="select-permanent-branch"
            :disabled="deleting || preparation !== null"
            @click="prepare(false)"
          >不保留附件文件，永久删除</button>
        </div>
      </section>

      <section v-if="preparation" class="impact" data-testid="deletion-impact">
        <h2>删除影响面</h2>
        <ul>
          <li>工作包快照：{{ preparation.entity_counts.workflows }}</li>
          <li>成效卡：{{ preparation.entity_counts.achievement_cards }}</li>
          <li>附件：{{ preparation.entity_counts.achievement_attachments }}</li>
          <li>工作流事件：{{ preparation.entity_counts.workflow_events }}</li>
          <li>成效卡事件：{{ preparation.entity_counts.achievement_card_events }}</li>
          <li>归档 artifact：{{ preparation.entity_counts.artifacts }}</li>
        </ul>
        <p>
          {{ preparation.retain_files
            ? '系统将先把附件复制到受控归档目录，再删除课题数据库记录。'
            : '系统将在数据库提交后永久清理附件文件，此操作不能从普通页面撤销。' }}
        </p>
        <label v-if="!preparation.retain_files" class="confirm-permanent">
          <input v-model="permanentConfirmed" type="checkbox" data-testid="confirm-permanent-deletion">
          我确认永久删除附件文件和课题
        </label>
        <div class="execute-actions">
          <button
            type="button"
            data-testid="execute-deletion"
            :disabled="deleting || (!preparation.retain_files && !permanentConfirmed)"
            @click="execute"
          >{{ deleting ? '正在删除…' : preparation.retain_files ? '执行删除并保留附件归档' : '确认永久删除' }}</button>
          <RouterLink class="cancel-link" data-testid="cancel-deletion" :to="`/contexts/${contextId}`">取消</RouterLink>
        </div>
      </section>

      <p v-if="deletionError" class="state-error" role="alert" data-testid="deletion-error">{{ deletionError }}</p>
      <p v-if="success" class="state-success" role="status" data-testid="deletion-success">
        课题已删除，正在返回课题列表…
      </p>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ApiError,
  commitContextDeletion,
  createUiSession,
  fetchContextDetail,
  prepareContextDeletion,
  type Context,
  type ContextDeletionPrepare,
} from '../features/contexts/context-service'

const route = useRoute()
const router = useRouter()
const contextId = computed(() => String(route.params.contextId ?? ''))
const context = ref<Context | null>(null)
const loading = ref(false)
const loadError = ref('')
const preparation = ref<ContextDeletionPrepare | null>(null)
const deletionSessionId = ref('')
const permanentConfirmed = ref(false)
const deleting = ref(false)
const deletionError = ref('')
const success = ref(false)

function message(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return '课题或删除票据不存在。'
    if (error.status === 403) return '删除确认无效或无权限执行。'
    if (error.status === 409) return '课题已变化或删除票据过期，请重新准备后重试。'
    if (error.status === 422) return '删除请求校验失败。'
    if (error.status === 503) return '删除服务暂时不可用，请稍后重试。'
    return error.detail
  }
  return fallback
}

async function loadContext(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    context.value = await fetchContextDetail(contextId.value)
  } catch (error) {
    loadError.value = message(error, '课题详情加载失败')
  } finally {
    loading.value = false
  }
}

async function prepare(retainFiles: boolean): Promise<void> {
  if (!context.value || deleting.value) return
  deleting.value = true
  deletionError.value = ''
  success.value = false
  permanentConfirmed.value = false
  try {
    const session = await createUiSession({ actor: 'author', display_label: '作者' })
    deletionSessionId.value = session.session_id
    preparation.value = await prepareContextDeletion(context.value.id, {
      retain_files: retainFiles,
      expected_version: context.value.row_version,
      session_id: session.session_id,
    })
  } catch (error) {
    preparation.value = null
    deletionError.value = message(error, '删除准备失败')
  } finally {
    deleting.value = false
  }
}

async function execute(): Promise<void> {
  const ticket = preparation.value
  if (!ticket || deleting.value || (!ticket.retain_files && !permanentConfirmed.value)) return
  deleting.value = true
  deletionError.value = ''
  try {
    const result = await commitContextDeletion(contextId.value, {
      operation_id: ticket.operation_id,
      confirmation: ticket.confirmation,
      session_id: deletionSessionId.value,
    })
    if (result.state === 'CLEANUP_PENDING') {
      deletionError.value = '课题记录已删除，但附件清理未完成，需要人工恢复。'
      return
    }
    success.value = true
    preparation.value = null
    window.setTimeout(() => {
      void router.push('/contexts')
    }, 900)
  } catch (error) {
    deletionError.value = message(error, '课题删除失败')
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  void loadContext()
})
</script>

<style scoped>
.delete-page {
  width: min(920px, calc(100% - 32px));
  margin: 20px auto;
  display: grid;
  gap: 16px;
}
.context-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.back-link,
.cancel-link {
  color: #17587a;
  font-weight: 700;
  text-decoration: none;
}
.context-summary,
.branches,
.impact {
  padding: 18px;
  border: 1px solid #d9e5e9;
  border-radius: 10px;
  background: #fff;
}
.branch-actions,
.execute-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.branch-actions button,
.execute-actions button {
  border: 1px solid #b7ccd3;
  border-radius: 7px;
  background: #fff;
  color: #17425c;
  padding: 9px 14px;
  font-weight: 700;
}
button.danger {
  color: #a12622;
  border-color: #dcb3b1;
  background: #fff6f5;
}
button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.confirm-permanent {
  display: flex;
  gap: 8px;
  align-items: center;
  font-weight: 700;
}
.impact ul {
  margin: 10px 0;
  padding-left: 20px;
}
.state-loading,
.state-success {
  color: #245c3f;
  font-weight: 700;
}
.state-error {
  color: #a12622;
  font-weight: 700;
}
@media (max-width: 640px) {
  .context-toolbar,
  .branch-actions,
  .execute-actions {
    align-items: stretch;
    flex-direction: column;
  }
  .back-link,
  .cancel-link,
  .branch-actions button,
  .execute-actions button {
    text-align: center;
  }
}
</style>