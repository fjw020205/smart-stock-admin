<script setup>
import { onMounted, ref } from 'vue'
import { stockApi } from '../api'
import { formatNumber } from '../utils/number'

const active = ref('ALL')
const items = ref([])
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const page = ref(1)
const firstLoaded = ref(false)

async function fetchPage(reset = false) {
  if (reset) {
    page.value = 1
    items.value = []
    finished.value = false
  }
  loading.value = true
  try {
    const params = { page: page.value, page_size: 12 }
    if (active.value !== 'ALL') params.type = active.value
    const response = await stockApi.records(params)
    items.value = reset ? response.data.items : [...items.value, ...response.data.items]
    page.value += 1
    finished.value = items.value.length >= response.data.total
    firstLoaded.value = true
  } catch (error) {
    finished.value = true
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function reset() {
  fetchPage(true)
}

function onRefresh() {
  refreshing.value = true
  fetchPage(true)
}

onMounted(reset)
</script>

<template>
  <div class="records">
    <div class="top">
      <h1>出入库记录</h1>
      <van-tabs v-model:active="active" shrink @change="reset">
        <van-tab title="全部" name="ALL" />
        <van-tab title="入库" name="IN" />
        <van-tab title="出库" name="OUT" />
      </van-tabs>
    </div>

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loading"
        :finished="finished"
        finished-text="没有更多记录了"
        :immediate-check="false"
        @load="fetchPage(false)"
      >
        <div class="list">
          <div v-for="item in items" :key="item.id" class="record">
            <div class="record-head">
              <span class="order mono">{{ item.order_no }}</span>
              <span class="pill" :class="item.type === 'IN' ? 'green' : 'orange'">
                {{ item.type_label }}
              </span>
            </div>
            <div class="record-body">
              <div class="record-info">
                <div class="name">{{ item.product_name }}</div>
                <div class="meta">{{ item.created_at }} · {{ item.operator_name }}</div>
              </div>
              <div class="qty" :class="item.type === 'IN' ? 'in' : 'out'">
                {{ item.type === 'IN' ? '+' : '-' }}{{ formatNumber(item.quantity) }}
                <span>{{ item.before_stock }} → {{ item.after_stock }}</span>
              </div>
            </div>
            <div v-if="item.remark" class="remark">{{ item.remark }}</div>
          </div>
        </div>
      </van-list>

      <van-empty
        v-if="firstLoaded && !items.length && !loading"
        description="还没有出入库记录"
        image="search"
        :image-size="90"
      />
    </van-pull-refresh>
  </div>
</template>

<style scoped>
.records {
  min-height: 100vh;
  background: var(--bg);
}

.top {
  position: sticky;
  top: 0;
  z-index: 10;
  padding: calc(16px + env(safe-area-inset-top)) 0 0;
  background: #fff;
  border-bottom: 1px solid var(--line);
}

.top h1 {
  font-size: 22px;
  font-weight: 700;
  padding: 0 16px 8px;
}

.top :deep(.van-tabs__line) {
  width: 20px;
  height: 3px;
  border-radius: 2px;
}

.list {
  padding: 12px 14px 0;
  display: grid;
  gap: 10px;
}

.record {
  background: #fff;
  border-radius: 14px;
  padding: 13px 14px;
  box-shadow: 0 6px 18px -16px rgba(15, 23, 42, 0.4);
}

.record-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.order {
  color: var(--muted);
  font-size: 10px;
}

.record-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 8px;
}

.record-info {
  min-width: 0;
}

.name {
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta {
  margin-top: 4px;
  font-size: 10px;
  color: var(--muted);
}

.qty {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}

.qty span {
  display: block;
  font-size: 10px;
  font-weight: 400;
  color: var(--muted);
  margin-top: 2px;
}

.qty.in {
  color: #16a34a;
}

.qty.out {
  color: #f59e0b;
}

.remark {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed #eef2f8;
  font-size: 11px;
  color: var(--muted);
}
</style>
