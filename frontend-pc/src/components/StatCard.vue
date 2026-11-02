<script setup>
import { computed } from 'vue'
import { resolveIcon } from '../utils/icons'

const props = defineProps({
  label: { type: String, default: '' },
  value: { type: [Number, String], default: 0 },
  unit: { type: String, default: '' },
  icon: { type: String, default: 'DataLine' },
  tone: { type: String, default: 'blue' },
  hint: { type: String, default: '' }
})

const iconComponent = computed(() => resolveIcon(props.icon))
</script>

<template>
  <div class="stat" :class="tone">
    <div class="top">
      <span class="label">{{ label }}</span>
      <span class="icon"><el-icon :size="18"><component :is="iconComponent" /></el-icon></span>
    </div>
    <div class="value num">
      {{ value }}<small v-if="unit">{{ unit }}</small>
    </div>
    <div v-if="hint" class="hint">{{ hint }}</div>
  </div>
</template>

<style scoped>
.stat {
  position: relative;
  overflow: hidden;
  padding: 18px 20px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.75);
  box-shadow: var(--shadow-sm);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.stat:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.stat::after {
  content: '';
  position: absolute;
  right: -30px;
  top: -40px;
  width: 130px;
  height: 130px;
  border-radius: 50%;
  opacity: 0.1;
  background: var(--tone);
  z-index: 0;
}

.top,
.value,
.hint {
  position: relative;
  z-index: 1;
}

.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--muted);
}

.label {
  font-size: 13px;
}

.icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: var(--tone);
  color: #fff;
  box-shadow: 0 8px 16px -8px var(--tone);
}

.icon :deep(svg) {
  color: #fff;
}

.value {
  margin-top: 10px;
  font-size: 30px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--ink);
  letter-spacing: -0.5px;
}

.value small {
  font-size: 12px;
  font-weight: 500;
  color: var(--muted);
  margin-left: 5px;
  letter-spacing: 0;
}

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--muted);
}

.blue { --tone: #1677ff; --tone-soft: #e8f1ff; }
.green { --tone: #16a34a; --tone-soft: #e7f7ee; }
.orange { --tone: #f59e0b; --tone-soft: #fef4e2; }
.red { --tone: #ef4444; --tone-soft: #fdecec; }
.violet { --tone: #7c3aed; --tone-soft: #f1eafe; }

.blue .value, .green .value, .orange .value, .red .value, .violet .value {
  color: var(--ink);
}
</style>
