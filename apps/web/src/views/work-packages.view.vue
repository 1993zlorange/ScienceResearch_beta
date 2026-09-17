<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElAlert, ElButton, ElInput, ElProgress, ElTable, ElTableColumn } from 'element-plus'
import { useCatalogQuery } from '../features/catalog/use-catalog-query'

type CatalogRow = {
  areaName: string
  id: string
  name: string
  action: string
  deliverable: string
}

const keyword = ref('')
const { data, error, isPending, refetch } = useCatalogQuery()

const rows = computed<CatalogRow[]>(() =>
  (data.value?.areas ?? []).flatMap((area) =>
    area.work_packages.map((workPackage) => ({
      areaName: area.name,
      id: workPackage.id,
      name: workPackage.name,
      action: workPackage.action,
      deliverable: workPackage.deliverable,
    })),
  ),
)

const filteredRows = computed(() => {
  const needle = keyword.value.trim().toLowerCase()
  if (!needle) return rows.value
  return rows.value.filter((row) =>
    [row.areaName, row.id, row.name, row.action, row.deliverable].some((value) => value.toLowerCase().includes(needle)),
  )
})
</script>

<template>
  <main class="work-packages-page" data-runtime="vue-target-stack">
    <header class="page-header">
      <p class="eyebrow">Vue 3 · TypeScript · TanStack Query</p>
      <h1>工作包目录</h1>`r`n      <nav class="page-navigation" aria-label="原生页面导航">`r`n        <RouterLink class="text-link" to="/contexts" data-testid="contexts-link">进入研究上下文</RouterLink>`r`n      </nav>
      <p v-if="isPending" class="page-status" role="status">正在加载目录…</p>
      <ElProgress v-if="isPending" :percentage="100" :show-text="false" :stroke-width="4" />
    </header>
    <div v-if="isPending" class="page-loading" role="status">目录请求进行中</div>
    <div v-else-if="error" class="page-error" role="alert">
      <ElAlert type="error" title="目录加载失败" show-icon :closable="false" />
      <p>{{ error instanceof Error ? error.message : '请稍后重试。' }}</p>
      <ElButton type="primary" @click="() => refetch()">重试</ElButton>
    </div>
    <div v-else class="table-shell">
      <ElInput v-model="keyword" clearable placeholder="搜索方面、编号、名称、行动或交付物" aria-label="搜索工作包" />
      <p class="result-count" role="status">{{ filteredRows.length }} / {{ rows.length }} 个工作包</p>
      <ElTable :data="filteredRows" row-key="id" data-testid="work-package-table">
        <ElTableColumn prop="areaName" label="研究方面" min-width="160" />
        <ElTableColumn prop="id" label="编号" min-width="120" />
        <ElTableColumn prop="name" label="工作包" min-width="220" />
        <ElTableColumn prop="action" label="关键行动" min-width="260" />
        <ElTableColumn prop="deliverable" label="交付物" min-width="220" />
      </ElTable>
    </div>
  </main>
</template>

