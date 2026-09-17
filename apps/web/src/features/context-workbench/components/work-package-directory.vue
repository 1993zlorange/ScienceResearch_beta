<template>
  <section
    class="work-package-directory"
    :class="{ collapsed: !directoryExpanded }"
    data-testid="work-package-directory"
    aria-label="工作包目录"
  >
    <header class="panel-head">
      <button
        class="disclosure-toggle"
        type="button"
        data-testid="directory-toggle"
        :aria-expanded="directoryExpanded ? 'true' : 'false'"
        aria-controls="workbench-directory-body"
        @click="$emit('toggleDirectory')"
      >工作包目录</button>
      <span data-testid="work-package-visible-count">{{ items.length }} / {{ allCount }}</span>
    </header>

    <div v-show="directoryExpanded" id="workbench-directory-body" class="directory-body">
      <section
        v-for="area in catalog.areas"
        :key="area.id"
        class="context-area"
        :data-area-id="area.id"
        :data-area-name="area.name"
      >
        <h3>
          <button
            class="area-toggle"
            type="button"
            :data-testid="`area-toggle-${area.id}`"
            :aria-expanded="expandedAreaIds.has(area.id) ? 'true' : 'false'"
            :aria-controls="`area-body-${area.id}`"
            @click="$emit('toggleArea', area.id)"
          >{{ area.name }}</button>
          <span class="badge">{{ items.filter(item => item.area.id === area.id).length }} 项</span>
        </h3>
        <div v-show="expandedAreaIds.has(area.id)" :id="`area-body-${area.id}`" class="context-wp-list">
          <p
            v-if="items.filter(item => item.area.id === area.id).length === 0"
            class="empty-group"
          >当前筛选条件下没有工作包。</p>
          <article
            v-for="item in items.filter(item => item.area.id === area.id)"
            :key="item.package.id"
            class="work-package-card"
            :class="`state-${item.status}`"
            :data-work-package="item.package.id"
            :data-status="item.status"
            :data-area="item.area.name"
          >
            <div
              class="wp-heading"
              :data-testid="`work-package-card-${item.package.id}`"
              role="button"
              tabindex="0"
              :aria-current="item.package.id === selectedWorkPackageId ? 'true' : undefined"
              @click="$emit('select', item.package.id)"
              @keydown.enter.prevent="$emit('select', item.package.id)"
              @keydown.space.prevent="$emit('select', item.package.id)"
            >
              <button
                class="wp-toggle"
                type="button"
                :data-testid="`work-package-toggle-${item.package.id}`"
                :aria-expanded="expandedPackageIds.has(item.package.id) ? 'true' : 'false'"
                :aria-controls="`wp-directory-detail-${item.package.id}`"
                @click.stop="$emit('select', item.package.id)"
              >
                <span class="wp-code">{{ item.package.id }}</span>
                <strong>{{ item.package.name }}</strong>
              </button>
              <span class="wp-status" :data-wp-status="item.status">{{ workflowStatusLabel(item.status) }}</span>
              <button
              v-if="expandedPackageIds.has(item.package.id) && item.package.id !== selectedWorkPackageId"
                class="wp-collapse"
                type="button"
                :data-testid="`work-package-collapse-${item.package.id}`"
                @click.stop="$emit('togglePackage', item.package.id)"
              >收起</button>
              <button
                v-else
                class="wp-select"
                type="button"
                :data-testid="`work-package-option-${item.package.id}`"
                @click.stop="$emit('select', item.package.id)"
              >查看详情</button>
            </div>
            <p>{{ item.package.deliverable }}</p>
            <div
              v-if="expandedPackageIds.has(item.package.id)"
              :id="`wp-directory-detail-${item.package.id}`"
              class="wp-inline-detail"
            >
              <slot :item="item" />
            </div>
          </article>
        </div>
      </section>

      <section v-if="unassignedCount > 0" class="context-area unassigned-workflows" data-area-id="UNASSIGNED">
        <div class="area-heading">
          <strong>未分配方面的工作包</strong>
          <span class="badge">{{ unassignedCount }} 项</span>
        </div>
        <p class="muted">这些工作包的方面快照缺失；请在数据治理后重新关联，当前不伪造方面归属。</p>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Catalog } from '../context-workbench-types'
import { workflowStatusLabel, type WorkbenchItem } from '../context-workbench-model'

defineProps<{
  catalog: Catalog
  items: WorkbenchItem[]
  allCount: number
  unassignedCount: number
  selectedWorkPackageId?: string
  expandedAreaIds: Set<string>
  expandedPackageIds: Set<string>
  directoryExpanded: boolean
  importantOnly: boolean
}>()

defineEmits<{
  toggleDirectory: []
  toggleArea: [areaId: string]
  togglePackage: [workPackageId: string]
  select: [workPackageId: string]
}>()
</script>

