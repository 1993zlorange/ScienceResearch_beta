<template>
  <main class="technical-docs-page" data-testid="technical-docs">
    <header class="page-header">
      <p class="eyebrow">ScienceResearch 技术说明</p>
      <h1>技术说明</h1>
      <p>请选择一份手册。手册内容将在独立页面打开。</p>
    </header>

    <div v-if="manifestQuery.isLoading.value" class="state-loading" role="status">技术说明清单加载中…</div>
    <div v-else-if="manifestQuery.error.value" class="state-error" role="alert">
      <p>{{ manualLoadError(manifestQuery.error.value, '技术说明清单') }}</p>
      <button type="button" data-testid="technical-docs-retry" @click="manifestQuery.refetch()">重试</button>
    </div>

    <section v-else-if="manifest" class="manual-card-list" aria-label="可选择的技术手册">
      <article v-for="manual in manifest.manuals" :key="manual.id" class="manual-card">
        <RouterLink
          class="manual-open"
          :to="`/technical-docs/${manual.id}`"
          :data-testid="`technical-manual-${manual.id}`"
        >
          <span>{{ manual.title }}</span>
          <small>{{ manual.version }} · {{ formatSize(manual.size_bytes) }}</small>
        </RouterLink>
        <p>{{ manual.description }}</p>
        <dl>
          <div><dt>来源</dt><dd>{{ manual.source }}</dd></div>
          <div><dt>SHA-256</dt><dd>{{ manual.sha256 }}</dd></div>
        </dl>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTechnicalManualManifestQuery } from '../features/technical-docs/use-technical-docs-query'

const router = useRouter()
const manifestQuery = useTechnicalManualManifestQuery()
const manifest = computed(() => manifestQuery.data.value ?? null)

function manualLoadError(error: unknown, subject: string): string {
  if (error instanceof Error && error.message.includes('HTTP 404')) {
    return `${subject}不存在。请在项目根目录执行 npm run docs:build 后重试。`
  }
  return error instanceof Error ? error.message : `${subject}加载失败。`
}

function formatSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<style scoped>
.technical-docs-page {
  max-width: 1240px;
}

.page-header {
  margin-bottom: 18px;
}

.eyebrow {
  margin: 0;
  color: #d4772e;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1,
h2 {
  margin: 4px 0 7px;
  color: #173b57;
}

.page-header > p:not(.eyebrow) {
  margin: 0;
  color: #667382;
}

.manual-card-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.manual-card {
  min-width: 0;
  padding: 15px;
  border: 1px solid #dce3e8;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 30px rgb(23 59 87 / 0.08);
}

.manual-open {
  display: grid;
  gap: 4px;
  color: #173b57;
  font-weight: 800;
  text-decoration: none;
}

.manual-open:hover {
  color: #17668e;
}

.manual-open small {
  color: #667382;
  font-size: 0.76rem;
  font-weight: 500;
}

.manual-card p,
.manual-card dd {
  color: #667382;
  font-size: 0.8rem;
}

.manual-card p {
  margin: 9px 0 10px;
}

.manual-card dl {
  display: grid;
  gap: 6px;
  margin: 0;
}

.manual-card div {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 7px;
}

.manual-card dt {
  color: #667382;
  font-size: 0.74rem;
  font-weight: 800;
}

.manual-card dd {
  margin: 0;
  overflow-wrap: anywhere;
}

.state-loading,
.state-error {
  padding: 20px;
  border: 1px solid #dce3e8;
  border-radius: 8px;
  background: #fff;
}

.state-error {
  border-color: #dfa3a3;
  color: #9b2c2c;
}

@media (max-width: 1100px) {
  .manual-card-list {
    grid-template-columns: 1fr;
  }
}
</style>
