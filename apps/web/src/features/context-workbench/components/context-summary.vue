<template>
  <section class="context-summary" data-testid="context-summary">
    <div>
      <h2>{{ context.name }}</h2>
      <p>{{ context.problem }}</p>
      <dl>
        <div><dt>课题 ID</dt><dd>{{ context.id }}</dd></div>
        <div><dt>负责人</dt><dd>{{ context.owner }}</dd></div>
        <div><dt>生命周期</dt><dd>{{ context.lifecycle_state }}</dd></div>
      </dl>
    </div>
    <p class="context-goal">目标：{{ context.goal || '未填写' }}</p>
  </section>
</template>

<script setup lang="ts">
import type { Context } from '../context-workbench-types'

defineProps<{ context: Context }>()
</script>
