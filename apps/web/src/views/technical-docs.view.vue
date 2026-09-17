<template>
  <main class="technical-docs-page" data-testid="technical-docs">
    <header class="page-header">
      <p class="eyebrow">ScienceResearch 技术说明</p>
      <h1>技术说明</h1>
      <p>三份手册已打包为本机运行期资产，可离线查看。</p>
      <nav class="page-navigation" aria-label="技术说明导航">
        <RouterLink to="/" data-testid="technical-docs-back-home">返回主目录</RouterLink>
      </nav>
    </header>

    <div v-if="manifestQuery.isLoading.value" class="state-loading" role="status">技术说明清单加载中…</div>
    <div v-else-if="manifestQuery.error.value" class="state-error" role="alert">
      <p>{{ manifestQuery.error.value instanceof Error ? manifestQuery.error.value.message : '技术说明加载失败。' }}</p>
      <button type="button" data-testid="technical-docs-retry" @click="manifestQuery.refetch()">重试</button>
    </div>

    <template v-else-if="manifest">
      <section class="manual-card-list" aria-label="可选择的技术手册">
        <article
          v-for="manual in manifest.manuals"
          :key="manual.id"
          class="manual-card"
          :class="{ selected: manual.id === activeManualId }"
        >
          <button
            type="button"
            :data-testid="`technical-manual-${manual.id}`"
            :aria-current="manual.id === activeManualId ? 'true' : undefined"
            @click="selectManual(manual.id)"
          >
            <span>{{ manual.title }}</span>
            <small>{{ manual.version }} · {{ formatSize(manual.size_bytes) }}</small>
          </button>
          <p>{{ manual.description }}</p>
          <dl>
            <div><dt>来源</dt><dd>{{ manual.source }}</dd></div>
            <div><dt>SHA-256</dt><dd>{{ manual.sha256 }}</dd></div>
          </dl>
        </article>
      </section>

      <section class="manual-viewer" aria-label="技术手册内容">
        <header>
          <h2>{{ activeManual?.title ?? '技术手册' }}</h2>
          <p v-if="activeManual">项目内运行期资产 · {{ activeManual.url }}</p>
        </header>
        <iframe
          v-if="activeManual"
          :key="activeManual.id"
          :title="activeManual.title"
          :data-testid="`technical-manual-frame-${activeManual.id}`"
          :src="activeManual.url"
          sandbox="allow-scripts allow-same-origin"
          loading="lazy"
          referrerpolicy="no-referrer"
        ></iframe>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTechnicalManualManifestQuery } from '../features/technical-docs/use-technical-docs-query'

const route = useRoute()
const router = useRouter()
const manifestQuery = useTechnicalManualManifestQuery()
const manifest = computed(() => manifestQuery.data.value ?? null)
const activeManualId = computed(() => {
  const requested = Array.isArray(route.query.manual) ? route.query.manual[0] : route.query.manual
  if (typeof requested === 'string' && manifest.value?.manuals.some((manual) => manual.id === requested)) {
    return requested
  }
  return manifest.value?.manuals[0]?.id ?? ''
})
const activeManual = computed(() =>
  manifest.value?.manuals.find((manual) => manual.id === activeManualId.value) ?? null,
)

function selectManual(manualId: string) {
  void router.push({ path: '/technical-docs', query: { manual: manualId } })
}

function formatSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<style scoped>
.technical-docs-page {
  max-width: 1500px;
  margin: 0 auto;
  padding: 28px 34px 60px;
}

.page-header {
  margin-bottom: 18px;
}

.eyebrow {
  margin: 0;
  color: #b46b2f;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1,
h2 {
  margin: 4px 0 7px;
  color: #102f3d;
}

.page-header > p:not(.eyebrow) {
  margin: 0;
  color: #52646d;
}

.page-navigation {
  margin-top: 12px;
}

.manual-card-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.manual-card,
.manual-viewer {
  min-width: 0;
  padding: 15px;
  border: 1px solid #c9dfe8;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 8px 22px rgb(15 48 64 / 0.05);
}

.manual-card.selected {
  border-color: #2578a6;
  box-shadow: inset 4px 0 0 #2578a6;
}

.manual-card button {
  display: grid;
  gap: 4px;
  width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  color: #16232d;
  font: inherit;
  text-align: left;
}

.manual-card button span {
  font-weight: 800;
}

.manual-card button small,
.manual-card p,
.manual-card dd {
  color: #52646d;
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
  color: #728a95;
  font-size: 0.74rem;
  font-weight: 800;
}

.manual-card dd {
  margin: 0;
  overflow-wrap: anywhere;
}

.manual-viewer header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 10px;
}

.manual-viewer p {
  margin: 0;
  color: #52646d;
  font-size: 0.8rem;
  overflow-wrap: anywhere;
}

.manual-viewer iframe {
  display: block;
  width: 100%;
  min-height: min(74vh, 780px);
  border: 1px solid #c9dfe8;
  border-radius: 8px;
  background: #fff;
}

.state-loading,
.state-error {
  padding: 20px;
  border-radius: 9px;
  background: #fff;
  box-shadow: 0 7px 20px rgb(15 48 64 / 0.05);
}

.state-error {
  border: 1px solid #dfa3a3;
  color: #8f2f2f;
}

@media (max-width: 1100px) {
  .manual-card-list {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .technical-docs-page {
    padding: 18px 14px 36px;
  }

  .manual-viewer header {
    align-items: start;
    flex-direction: column;
  }

  .manual-viewer iframe {
    min-height: 560px;
  }
}
</style>


