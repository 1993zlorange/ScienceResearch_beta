<template>
  <main class="technical-manual-page" data-testid="technical-manual-page">
    <header class="page-header">
      <nav class="manual-return" aria-label="返回导航">
        <RouterLink class="return-link" to="/technical-docs" data-testid="technical-manual-back-index">返回技术说明</RouterLink>
        <RouterLink class="return-link" to="/" data-testid="technical-manual-back-home">返回主目录</RouterLink>
      </nav>
      <p class="eyebrow">ScienceResearch 技术说明</p>
      <h1>{{ manual?.title ?? '技术手册' }}</h1>
      <p v-if="manual" class="manual-meta">
        项目内运行期资产 · {{ manual.version }} · {{ formatSize(manual.size_bytes) }} · {{ manual.url }}
      </p>
    </header>

    <div v-if="manifestQuery.isLoading.value" class="state-loading" role="status">技术手册加载中…</div>
    <div v-else-if="manifestQuery.error.value" class="state-error" role="alert">
      <p>{{ manualLoadError(manifestQuery.error.value, '技术说明清单') }}</p>
      <button type="button" data-testid="technical-manual-retry" @click="manifestQuery.refetch()">重试</button>
    </div>
    <div v-else-if="!manual" class="state-error" role="alert" data-testid="technical-manual-invalid">
      <p>未找到技术手册。</p>
      <RouterLink class="return-link" to="/technical-docs">返回技术说明</RouterLink>
    </div>
    <section v-else class="manual-viewer" aria-label="技术手册内容">
      <iframe
        :key="manual.id"
        :title="manual.title"
        :data-testid="`technical-manual-frame-${manual.id}`"
        :src="manual.url"
        sandbox="allow-scripts"
        loading="lazy"
        referrerpolicy="no-referrer"
      ></iframe>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useTechnicalManualManifestQuery } from '../features/technical-docs/use-technical-docs-query'

const route = useRoute()
const manifestQuery = useTechnicalManualManifestQuery()
const manual = computed(() => {
  const manualId = String(route.params.manualId ?? '')
  return manifestQuery.data.value?.manuals.find((item) => item.id === manualId) ?? null
})

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
.technical-manual-page {
  max-width: 1500px;
}

.page-header {
  margin-bottom: 16px;
}

.manual-return {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.return-link {
  padding: 7px 11px;
  border: 1px solid #dce3e8;
  border-radius: 6px;
  background: #fff;
  color: #173b57;
  font-size: 0.8rem;
  font-weight: 750;
  text-decoration: none;
}

.return-link:hover {
  background: #f2f8fb;
}

.eyebrow {
  margin: 0;
  color: #d4772e;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 4px 0 7px;
  color: #173b57;
}

.manual-meta {
  margin: 0;
  color: #667382;
  overflow-wrap: anywhere;
}

.manual-viewer {
  min-width: 0;
  padding: 12px;
  border: 1px solid #dce3e8;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 30px rgb(23 59 87 / 0.08);
}

.manual-viewer iframe {
  display: block;
  width: 100%;
  min-height: min(76vh, 860px);
  border: 0;
  background: #fff;
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

@media (max-width: 700px) {
  .manual-viewer iframe {
    min-height: 560px;
  }
}
</style>
