<template>
  <section
    class="context-summary"
    :class="{ collapsed: !expanded }"
    data-testid="context-summary"
  >
    <header class="summary-head">
      <div>
        <p class="summary-eyebrow">Research Context</p>
        <h2>{{ context.name }}</h2>
        <p class="summary-problem">{{ context.problem }}</p>
      </div>
      <button
        type="button"
        class="summary-toggle"
        :aria-expanded="expanded ? 'true' : 'false'"
        aria-controls="context-summary-body"
        data-testid="context-summary-toggle"
        @click="$emit('toggle')"
      >
        <span>{{ expanded ? '收起课题详情' : '展开课题详情' }}</span>
        <span aria-hidden="true">{{ expanded ? '−' : '+' }}</span>
      </button>
    </header>
    <div v-if="expanded" id="context-summary-body" class="summary-body">
      <dl>
        <div><dt>课题 ID</dt><dd>{{ context.id }}</dd></div>
        <div><dt>负责人</dt><dd>{{ context.owner }}</dd></div>
        <div><dt>生命周期</dt><dd>{{ context.lifecycle_state }}</dd></div>
      </dl>
      <p class="context-goal">目标：{{ context.goal || '未填写' }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Context } from '../context-workbench-types'

defineProps<{
  context: Context
  expanded: boolean
}>()

defineEmits<{
  toggle: []
}>()
</script>

<style scoped>
.context-summary {
  margin-bottom: 14px;
  padding: 18px;
  border: 1px solid #c9dfe8;
  border-radius: 14px;
  background: linear-gradient(135deg, #ffffff 0%, #f2f8fb 58%, #eaf4f9 100%);
  box-shadow: 0 14px 34px rgb(23 59 87 / 0.09);
}

.summary-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.summary-eyebrow {
  margin: 0 0 4px;
  color: #b46b2f;
  font-size: 0.7rem;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h2 {
  margin: 0;
  color: #173b57;
  font-size: clamp(1.25rem, 2vw, 1.75rem);
  line-height: 1.25;
}

.summary-problem {
  margin: 5px 0 0;
  color: #5d707c;
}

.summary-toggle {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex: 0 0 auto;
  min-height: 34px;
  padding: 6px 11px;
  border: 1px solid #c9dfe8;
  border-radius: 999px;
  background: #fff;
  color: #17668e;
  font-size: 0.78rem;
  font-weight: 800;
  cursor: pointer;
}

.summary-toggle:hover {
  background: #e3f2fa;
}

.summary-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, .7fr);
  gap: 14px;
  margin-top: 15px;
  padding-top: 14px;
  border-top: 1px solid #dbe9ef;
}

dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 9px;
  margin: 0;
}

dl div {
  padding: 9px 10px;
  border: 1px solid #dbe9ef;
  border-radius: 9px;
  background: #fff;
}

dt {
  color: #718792;
  font-size: 0.72rem;
  font-weight: 850;
}

dd {
  margin: 3px 0 0;
  color: #173b57;
  font-weight: 750;
  overflow-wrap: anywhere;
}

.context-goal {
  margin: 0;
  padding: 11px 13px;
  border-left: 4px solid #d4772e;
  border-radius: 0 9px 9px 0;
  background: #fff7ed;
  color: #7c4a12;
  overflow-wrap: anywhere;
}

@media (max-width: 800px) {
  .summary-head {
    align-items: stretch;
    flex-direction: column;
  }

  .summary-body,
  dl {
    grid-template-columns: 1fr;
  }
}
</style>
