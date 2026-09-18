<template>
  <div
    class="home-shell"
    :class="{ 'rail-collapsed': !railExpanded }"
    data-testid="home-shell"
  >
    <aside class="side" :aria-label="railExpanded ? '主页结构树' : '主页结构树已收起'">
      <div v-if="railExpanded" class="side-content">
        <div class="brand">科研工作台<small>科研工作分解 · 每周组会</small></div>
        <div class="side-note">问题 → 行动 → 证据 → 结论 → 下一步<br>离线运行 · 作者确认优先</div>
        <HomeNavigationTree />
      </div>
      <button
        type="button"
        class="rail-toggle"
        :aria-expanded="railExpanded ? 'true' : 'false'"
        :title="railExpanded ? '收起结构树' : '展开结构树'"
        data-testid="home-shell-rail-toggle"
        @click="railExpanded = !railExpanded"
      >
        <span aria-hidden="true">{{ railExpanded ? '‹' : '›' }}</span>
        <span class="sr-only">{{ railExpanded ? '收起结构树' : '展开结构树' }}</span>
      </button>
    </aside>
    <main class="home-main" id="home-main-content" tabindex="-1">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import HomeNavigationTree from '../components/home-navigation-tree.vue'

const railExpanded = ref(true)
</script>

<style scoped>
.home-shell {
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr);
  min-height: 100vh;
  background: #f6f8fa;
  color: #17212b;
  font: 14px/1.6 "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
}

.home-shell.rail-collapsed {
  grid-template-columns: 58px minmax(0, 1fr);
}

.side {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: auto;
  padding: 16px 10px;
  background: #173b57;
  color: #eef5f8;
}

.side-content {
  display: grid;
  gap: 10px;
}

.brand {
  font-size: 20px;
  font-weight: 700;
}

.brand small {
  display: block;
  margin-top: 2px;
  color: #a9c4d2;
  font-size: 12px;
  font-weight: 400;
}

.side-note {
  margin: 12px 4px;
  color: #b9d0db;
  font-size: 12px;
}

.rail-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  min-height: 36px;
  border: 1px solid #43718d;
  border-radius: 8px;
  background: #173b57;
  color: #dcecf2;
  font-size: 20px;
  cursor: pointer;
}

.rail-toggle:hover {
  background: #2b5d78;
}

.home-shell.rail-collapsed .rail-toggle {
  width: 100%;
}

.home-main {
  min-width: 0;
  padding: 28px 34px 60px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 1000px) {
  .home-shell,
  .home-shell.rail-collapsed {
    grid-template-columns: 1fr;
  }

  .side {
    position: relative;
    height: auto;
    padding: 10px;
  }

  .side-content {
    gap: 8px;
  }
}
</style>
