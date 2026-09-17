<template>
  <div class="context-toolbar">
    <RouterLink class="back-link" data-testid="back-to-home" to="/">返回主目录</RouterLink>
    <RouterLink class="back-link" data-testid="back-to-contexts" to="/contexts">课题列表</RouterLink>
    <RouterLink
      class="delete-button"
      data-testid="delete-context"
      :to="`/contexts/${contextId}/delete`"
    >删除课题</RouterLink>
  </div>
</template>

<script setup lang="ts">
defineProps<{ contextId: string }>()
</script>

