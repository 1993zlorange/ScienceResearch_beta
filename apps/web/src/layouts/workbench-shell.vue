<template>
  <div class="workbench-shell" data-testid="workbench-shell">
    <header class="workbench-topbar">
      <RouterLink class="brand" to="/" data-testid="shell-home">科研工作台</RouterLink>
      <nav class="top-links" aria-label="主导航">
        <RouterLink to="/" data-testid="shell-nav-home">主目录</RouterLink>
        <RouterLink to="/technical-docs" data-testid="shell-nav-technical-docs">技术说明</RouterLink>
        <RouterLink to="/contexts" data-testid="shell-nav-contexts">课题流程</RouterLink>
      </nav>
    </header>
    <div class="workbench-shell-body">
      <aside class="structure-rail" aria-label="结构树">
        <AppStructureTree />
      </aside>
      <main class="workbench-main">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppStructureTree from '../components/app-structure-tree.vue'
</script>

<style scoped>
.workbench-shell {
  min-height: 100vh;
  background: #eef4f7;
}

.workbench-topbar {
  position: sticky;
  top: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 54px;
  padding: 10px clamp(14px, 3vw, 28px);
  border-bottom: 1px solid #c9dfe8;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(8px);
}

.brand {
  color: #102f3d;
  font-size: 1rem;
  font-weight: 850;
  text-decoration: none;
}

.top-links {
  display: flex;
  gap: 6px;
  overflow-x: auto;
}

.top-links a {
  padding: 7px 11px;
  border-radius: 999px;
  color: #52646d;
  font-size: 0.82rem;
  font-weight: 750;
  text-decoration: none;
  white-space: nowrap;
}

.top-links a.router-link-active {
  background: #e3f2fa;
  color: #17668e;
}

.workbench-shell-body {
  display: grid;
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
  width: min(1680px, 100%);
  margin: 0 auto;
  padding: clamp(12px, 2vw, 22px);
}

.structure-rail {
  position: sticky;
  top: 68px;
  max-height: calc(100vh - 86px);
  overflow: auto;
  padding: 12px;
  border: 1px solid #c9dfe8;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 26px rgb(15 48 64 / 0.06);
}

.workbench-main {
  min-width: 0;
}

@media (max-width: 1000px) {
  .workbench-shell-body {
    grid-template-columns: 1fr;
  }

  .structure-rail {
    position: static;
    max-height: none;
  }
}
</style>
