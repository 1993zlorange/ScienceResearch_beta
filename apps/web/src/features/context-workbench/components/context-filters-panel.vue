<template>
  <section
    class="context-filters"
    :class="{ collapsed: !expanded }"
    data-testid="context-filters"
    aria-label="工作包筛选"
  >
    <header class="filters-head">
      <button
        type="button"
        class="filters-toggle"
        :aria-expanded="expanded ? 'true' : 'false'"
        aria-controls="context-filters-body"
        data-testid="context-filters-toggle"
        @click="$emit('toggle')"
      >
        <span>搜索与筛选</span>
        <span aria-hidden="true">{{ expanded ? '−' : '+' }}</span>
      </button>
      <span data-testid="workbench-filter-count" role="status">{{ resultCount }} 个工作包匹配</span>
    </header>
    <div v-if="expanded" id="context-filters-body" class="filters-body">
      <form class="filters-form" @submit.prevent="applyFilters">
        <label>
          搜索
          <input
            v-model="query"
            name="query"
            type="search"
            placeholder="名称、行动或交付物"
            data-testid="workbench-filter-query"
          >
        </label>
        <label>
          方面
          <select v-model="area" name="area" data-testid="workbench-filter-area">
            <option value="">全部方面</option>
            <option v-for="areaName in areaNames" :key="areaName" :value="areaName">{{ areaName }}</option>
          </select>
        </label>
        <label>
          状态
          <select v-model="status" name="status" data-testid="workbench-filter-status">
            <option value="">全部</option>
            <option value="complete">已完成</option>
            <option value="has-cards">有成效</option>
            <option value="not-started">未开始</option>
          </select>
        </label>
        <label class="important-filter">
          <input v-model="important" name="important" type="checkbox" value="true" />
          仅看重点成效
        </label>
        <div class="filter-actions">
          <button class="primary" type="submit" data-testid="apply-workbench-filters">筛选</button>
          <button type="button" data-testid="clear-workbench-filters" @click="clearFilters">清除筛选</button>
        </div>
      </form>
      <p class="batch-note">筛选仅保存在网址；目录与进展展开状态会持久化。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { WorkbenchFilters } from '../context-workbench-model'

const props = defineProps<{
  filters: WorkbenchFilters
  areaNames: string[]
  resultCount: number
  expanded: boolean
}>()

const emit = defineEmits<{
  apply: [filters: WorkbenchFilters]
  clear: []
  toggle: []
}>()

const query = ref(props.filters.query)
const area = ref(props.filters.area)
const status = ref(props.filters.status)
const important = ref(props.filters.important)

watch(
  () => props.filters,
  (filters) => {
    query.value = filters.query
    area.value = filters.area
    status.value = filters.status
    important.value = filters.important
  },
  { deep: true },
)

function applyFilters() {
  emit('apply', {
    area: area.value,
    status: status.value,
    query: query.value,
    important: important.value,
  })
}

function clearFilters() {
  query.value = ''
  area.value = ''
  status.value = ''
  important.value = false
  emit('clear')
}
</script>
