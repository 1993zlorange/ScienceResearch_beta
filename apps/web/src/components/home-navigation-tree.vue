<template>
  <nav class="nav" aria-label="主导航">
    <div v-for="item in navigationItems" :key="item.id" class="nav-item">
      <div v-if="item.expandable" class="nav-entry">
        <RouterLink
          class="nav-link"
          :to="item.path"
          :aria-current="isItemActive(item) ? 'page' : undefined"
          :data-testid="`home-nav-${item.id}`"
        >{{ item.label }}</RouterLink>
        <button
          type="button"
          class="nav-expander"
          :aria-expanded="contextFlowExpanded ? 'true' : 'false'"
          :aria-controls="`home-nav-${item.id}-children`"
          :data-testid="`home-nav-expander-${item.id}`"
          @click="toggle('context-flow')"
        >
          <span aria-hidden="true">{{ contextFlowExpanded ? '−' : '+' }}</span>
          <span class="sr-only">{{ contextFlowExpanded ? `收起${item.label}` : `展开${item.label}` }}</span>
        </button>
      </div>
      <RouterLink
        v-else
        class="nav-link"
        :to="item.path"
        :aria-current="isItemActive(item) ? 'page' : undefined"
        :data-testid="`home-nav-${item.id}`"
      >{{ item.label }}</RouterLink>

      <div
        v-if="item.expandable && contextFlowExpanded"
        :id="`home-nav-${item.id}-children`"
        class="nav-children"
      >
        <ContextNavigationTree />
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import navigationConfig from '../../../../config/main-navigation.json'
import { useContextsQuery } from '../features/contexts/use-context-queries'
import ContextNavigationTree from './context-navigation-tree.vue'

const route = useRoute()
const navigationItems = navigationConfig.items
const contextsQuery = useContextsQuery()
const expanded = ref(new Set<string>(['context-flow']))

const isContextRoute = computed(() => route.path === '/contexts' || route.path.startsWith('/contexts/'))
const contextFlowExpanded = computed(() => expanded.value.has('context-flow'))

function isItemActive(item: typeof navigationItems[number]): boolean {
  if (item.id === 'home') return route.path === '/'
  if (item.id === 'technical-docs') return route.path === '/technical-docs' || route.path.startsWith('/technical-docs/')
  if (item.id === 'contexts') return isContextRoute.value
  return route.path === item.path
}

function toggle(key: string): void {
  const next = new Set(expanded.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expanded.value = next
}
</script>

<style scoped>
.nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  min-width: 0;
}

.nav-entry {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 30px;
  gap: 3px;
  align-items: stretch;
}

.nav-link,
.nav-expander {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  min-height: 36px;
  padding: 8px 10px;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  color: #dcecf2;
  font: inherit;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
}

.nav-expander {
  justify-content: center;
  padding: 0;
}

.nav-link:hover,
.nav-expander:hover,
.nav-link.router-link-active,
.nav-link.active,
.nav-expander[aria-expanded='true'] {
  background: #2b5d78;
  border-color: #75a9c4;
  color: #fff;
}

.nav-children {
  margin-top: 3px;
  color: #dcecf2;
}
</style>
