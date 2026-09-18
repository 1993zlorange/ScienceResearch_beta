<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import HomeShell from './layouts/home-shell.vue'

const locale = computed(() => zhCn)
const route = useRoute()
const useHomeLayout = computed(() =>
  route.matched.some((record) => record.meta.layout === 'home'),
)
</script>

<template>
  <ElConfigProvider :locale="locale">
    <HomeShell v-if="useHomeLayout">
      <RouterView />
    </HomeShell>
    <RouterView v-else />
  </ElConfigProvider>
</template>
