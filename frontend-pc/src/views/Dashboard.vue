<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { dashboardApi } from '../api'
import StatCard from '../components/StatCard.vue'
import { formatNumber, todayLabel } from '../utils/format'

const router = useRouter()
const loading = ref(false)
const data = ref(null)
const chartRef = ref(null)
let chart = null

const cards = ref({
  product_total: 0,
  stock_total: 0,
  today_in: 0,
  today_out: 0,
  low_stock_count: 0
})

function renderChart() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const trend = data.value?.trend || []
  chart.setOption({
    grid: { left: 12, right: 16, top: 42, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(15,23,42,.92)',
      borderWidth: 0,
      textStyle: { color: '#e2e8f0', fontSize: 12 }
    },
    legend: {
      right: 8,
      top: 4,
      icon: 'roundRect',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: '#64748b', fontSize: 12 },
      data: ['入库', '出库']
    },
    xAxis: {
      type: 'category',
      data: trend.map((item) => item.label),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#e8edf5' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 }
    },
    series: [
      {
        name: '入库',
        type: 'bar',
        barWidth: 14,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#4da3ff' },
            { offset: 1, color: '#1677ff' }
          ])
        },
        data: trend.map((item) => item.in)
      },
      {
        name: '出库',
        type: 'bar',
        barWidth: 14,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#ffc36b' },
            { offset: 1, color: '#f59e0b' }
          ])
        },
        data: trend.map((item) => item.out)
      }
    ]
  })
}

async function load() {
  loading.value = true
  try {
    const response = await dashboardApi.summary()
    data.value = response.data
    cards.value = response.data.cards
    await nextTick()
    renderChart()
  } catch (error) {
    /* 提示已统一处理 */
  } finally {
    loading.value = false
  }
}

function resize() {
  chart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})

function goInbound(productId) {
  router.push({ path: '/stock/in', query: { productId } })
}
</script>

<template>
  <div class="page" v-loading="loading">
    <div class="page-head">
      <div>
        <h2>工作台</h2>
        <p class="sub">{{ todayLabel() }} · 库存概览与待办提醒</p>
      </div>
      <div class="actions">
        <el-button :icon="'Refresh'" @click="load">刷新数据</el-button>
        <el-button type="primary" :icon="'Plus'" v-perm="'stock:in'" @click="router.push('/stock/in')">
          快速入库
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="cards.low_stock_count > 0"
      type="warning"
      show-icon
      :closable="false"
      class="low-alert"
    >
      <template #title>
        有 <b>{{ cards.low_stock_count }}</b> 种商品低于安全库存，建议尽快补货
        <el-button link type="warning" @click="router.push('/products?low_stock=1')">
          查看商品
        </el-button>
      </template>
    </el-alert>

    <div class="stat-grid">
      <StatCard label="商品总数" :value="formatNumber(cards.product_total)" unit="种" icon="Goods" tone="blue" hint="在售商品" />
      <StatCard label="库存总量" :value="formatNumber(cards.stock_total)" unit="件" icon="Box" tone="green" hint="全部商品库存合计" />
      <StatCard label="今日入库" :value="formatNumber(cards.today_in)" unit="件" icon="Download" tone="violet" hint="今日累计入库数量" />
      <StatCard label="今日出库" :value="formatNumber(cards.today_out)" unit="件" icon="Upload" tone="orange" hint="今日累计出库数量" />
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-head">
          <div class="card-title">近 7 日出入库趋势 <small>单位：件</small></div>
          <el-tag size="small" type="info" effect="plain">每日汇总</el-tag>
        </div>
        <div ref="chartRef" class="chart" />
      </div>

      <div class="card low-card">
        <div class="card-head">
          <div class="card-title">
            低库存预警
            <el-tag v-if="cards.low_stock_count" size="small" type="danger" effect="light">
              {{ cards.low_stock_count }}
            </el-tag>
          </div>
          <el-button link type="primary" @click="router.push('/products?low_stock=1')">全部</el-button>
        </div>
        <div class="low-body">
          <template v-if="data?.low_stock?.length">
            <div v-for="item in data.low_stock" :key="item.id" class="low-row">
              <div class="info">
                <div class="name">{{ item.name }}</div>
                <div class="code">{{ item.code }} · 安全库存 {{ item.safety_stock }}{{ item.unit }}</div>
              </div>
              <div class="right">
                <div class="stock">
                  <b>{{ item.stock }}</b><span>{{ item.unit }}</span>
                </div>
                <el-button
                  v-perm="'stock:in'"
                  size="small"
                  type="primary"
                  plain
                  @click="goInbound(item.id)"
                >
                  去入库
                </el-button>
              </div>
            </div>
          </template>
          <div v-else class="empty-block">
            <el-icon :size="30" color="#cbd5e1"><CircleCheck /></el-icon>
            <div style="margin-top: 8px">库存充足，暂无预警</div>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-head">
        <div class="card-title">最近操作</div>
        <el-button link type="primary" @click="router.push('/stock/records')">查看全部记录</el-button>
      </div>
      <el-table :data="data?.recent || []" style="width: 100%" empty-text="暂无出入库记录">
        <el-table-column prop="order_no" label="单号" width="170">
          <template #default="{ row }"><span class="mono">{{ row.order_no }}</span></template>
        </el-table-column>
        <el-table-column prop="product_name" label="商品" min-width="160" show-overflow-tooltip />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag :type="row.type === 'IN' ? 'success' : 'warning'" size="small" effect="light">
              {{ row.type === 'IN' ? '入库' : '出库' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="100" align="right">
          <template #default="{ row }">
            <span :class="row.type === 'IN' ? 'qty-in' : 'qty-out'">
              {{ row.type === 'IN' ? '+' : '-' }}{{ row.quantity }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="after_stock" label="变动后库存" width="110" align="right" />
        <el-table-column prop="operator_name" label="操作人" width="110" />
        <el-table-column prop="created_at" label="时间" width="165" />
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.low-alert {
  border-radius: 10px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.grid-2 {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(320px, 1fr);
  gap: 16px;
}

.chart {
  height: 306px;
  padding: 8px 12px 6px;
}

.low-body {
  padding: 6px 8px;
  max-height: 300px;
  overflow-y: auto;
}

.low-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  transition: background 0.15s ease;
}

.low-row:hover {
  background: #f8fafc;
}

.info {
  min-width: 0;
}

.name {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.code {
  margin-top: 4px;
  font-size: 11px;
  color: var(--muted);
}

.right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
}

.stock {
  text-align: right;
  color: #ef4444;
}

.stock b {
  font-size: 18px;
}

.stock span {
  font-size: 11px;
  margin-left: 2px;
  color: var(--muted);
}

.qty-in {
  color: #16a34a;
  font-weight: 600;
}

.qty-out {
  color: #f59e0b;
  font-weight: 600;
}

@media (max-width: 1180px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .grid-2 {
    grid-template-columns: 1fr;
  }
}
</style>
