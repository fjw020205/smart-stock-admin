<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { dashboardApi } from '../api'
import { useAuthStore } from '../stores/auth'
import { can } from '../utils/permission'
import { formatDateTime, greeting, initials, todayText } from '../utils/format'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const refreshing = ref(false)
const summary = ref(null)

const cards = computed(() => summary.value?.cards || {})
const lowStock = computed(() => summary.value?.low_stock || [])
const recent = computed(() => summary.value?.recent || [])

function n(value) {
  return Number(value || 0).toLocaleString('zh-CN')
}

async function load() {
  try {
    const response = await dashboardApi.summary()
    summary.value = response.data
  } catch (error) {
    /* 已提示 */
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function onRefresh() {
  refreshing.value = true
  load()
}

onMounted(load)
</script>

<template>
  <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
    <div class="home">
      <header class="hero">
        <div class="hero-glow" />
        <div class="hero-top">
          <div>
            <div class="greet">{{ greeting() }}，{{ auth.user?.real_name }}</div>
            <div class="sub">{{ todayText() }} · {{ auth.user?.role?.name }}</div>
          </div>
          <div class="avatar">{{ initials(auth.user?.real_name) }}</div>
        </div>

        <div v-if="can('stock:in') || can('stock:out')" class="hero-actions">
          <button v-if="can('stock:in')" type="button" @click="router.push('/stock/in')">
            <van-icon name="down" /> 入库
          </button>
          <button v-if="can('stock:out')" type="button" @click="router.push('/stock/out')">
            <van-icon name="upgrade" /> 出库
          </button>
        </div>
      </header>

      <div class="stats">
        <van-skeleton v-if="loading && !summary" avatar :row="2" class="stat-skeleton" />
        <template v-else>
          <div class="stat">
            <span>商品总数</span>
            <b>{{ n(cards.product_total) }}<i>种</i></b>
          </div>
          <div class="stat">
            <span>库存总量</span>
            <b>{{ n(cards.stock_total) }}<i>件</i></b>
          </div>
          <div class="stat">
            <span>今日入库</span>
            <b class="green">{{ n(cards.today_in) }}<i>件</i></b>
          </div>
          <div class="stat">
            <span>今日出库</span>
            <b class="orange">{{ n(cards.today_out) }}<i>件</i></b>
          </div>
        </template>
      </div>

      <div class="page-pad">
        <section v-if="lowStock.length" class="section">
          <div class="section-head">
            <div class="section-title">
              <van-icon name="warning-o" color="#f59e0b" />
              低库存预警
              <span class="count">{{ lowStock.length }}</span>
            </div>
            <span class="section-link" @click="router.push('/products')">全部商品</span>
          </div>

          <div class="card low-card">
            <div v-for="item in lowStock.slice(0, 4)" :key="item.id" class="low-item">
              <div class="low-info">
                <div class="low-name">{{ item.name }}</div>
                <div class="low-meta">{{ item.code }} · 安全库存 {{ item.safety_stock }}{{ item.unit }}</div>
              </div>
              <div class="low-right">
                <div class="low-stock">{{ item.stock }}<span>{{ item.unit }}</span></div>
                <van-button
                  v-if="can('stock:in')"
                  size="mini"
                  type="primary"
                  plain
                  round
                  @click="router.push({ path: '/stock/in', query: { productId: item.id } })"
                >
                  补货
                </van-button>
              </div>
            </div>
          </div>
        </section>

        <section class="section">
          <div class="section-head">
            <div class="section-title">最近操作</div>
            <span class="section-link" @click="router.push('/records')">查看全部</span>
          </div>

          <div class="card recent-card">
            <van-skeleton v-if="loading && !summary" :row="4" />
            <template v-else-if="recent.length">
              <div v-for="item in recent.slice(0, 5)" :key="item.id" class="recent-item">
                <span class="type-icon" :class="item.type === 'IN' ? 'in' : 'out'">
                  <van-icon :name="item.type === 'IN' ? 'down' : 'upgrade'" />
                </span>
                <div class="recent-info">
                  <div class="recent-name">{{ item.product_name }}</div>
                  <div class="recent-meta">{{ formatDateTime(item.created_at) }} · {{ item.operator_name }}</div>
                </div>
                <div class="recent-qty" :class="item.type === 'IN' ? 'in' : 'out'">
                  {{ item.type === 'IN' ? '+' : '-' }}{{ item.quantity }}
                  <span>→ {{ item.after_stock }}</span>
                </div>
              </div>
            </template>
            <van-empty v-else image="search" description="今天还没有出入库记录" :image-size="80" />
          </div>
        </section>
      </div>
    </div>
  </van-pull-refresh>
</template>

<style scoped>
.home {
  min-height: 100vh;
  background: var(--bg);
}

.hero {
  position: relative;
  overflow: hidden;
  padding: calc(24px + env(safe-area-inset-top)) 20px 54px;
  color: #fff;
  background:
    radial-gradient(360px 240px at 92% -10%, rgba(22, 119, 255, 0.55), transparent 65%),
    linear-gradient(160deg, #0b1b33 0%, #123a6b 100%);
  border-radius: 0 0 26px 26px;
}

.hero-glow {
  position: absolute;
  right: -70px;
  top: -80px;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  border: 1px solid rgba(120, 180, 255, 0.2);
  box-shadow: 0 0 0 40px rgba(22, 119, 255, 0.05);
}

.hero-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  position: relative;
  z-index: 1;
}

.greet {
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.sub {
  margin-top: 6px;
  font-size: 11px;
  color: #9db4d1;
}

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4da3ff, #1677ff);
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 16px;
  border: 2px solid rgba(255, 255, 255, 0.35);
}

.hero-actions {
  display: flex;
  gap: 10px;
  margin-top: 18px;
  position: relative;
  z-index: 1;
}

.hero-actions button {
  flex: 1;
  height: 40px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  backdrop-filter: blur(4px);
}

.hero-actions button:active {
  background: rgba(255, 255, 255, 0.22);
}

.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: -34px 14px 0;
  position: relative;
  z-index: 2;
}

.stat {
  background: #fff;
  border-radius: 14px;
  padding: 13px 14px;
  box-shadow: 0 10px 26px -20px rgba(15, 23, 42, 0.5);
}

.stat span {
  font-size: 11px;
  color: var(--muted);
}

.stat b {
  display: block;
  margin-top: 6px;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.3px;
  font-variant-numeric: tabular-nums;
}

.stat b i {
  font-style: normal;
  font-size: 10px;
  font-weight: 400;
  color: var(--muted);
  margin-left: 3px;
}

.stat b.green {
  color: #16a34a;
}

.stat b.orange {
  color: #f59e0b;
}

.stat-skeleton {
  grid-column: 1 / -1;
  background: #fff;
  border-radius: 14px;
  padding: 16px;
}

.section {
  margin-top: 18px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 9px;
  padding: 0 4px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
}

.count {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: #fdecec;
  color: #ef4444;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.section-link {
  font-size: 12px;
  color: var(--muted);
}

.low-card {
  padding: 4px 14px;
}

.low-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 0;
}

.low-item + .low-item {
  border-top: 1px solid var(--line);
}

.low-info {
  min-width: 0;
}

.low-name {
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.low-meta {
  margin-top: 4px;
  font-size: 10px;
  color: var(--muted);
}

.low-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
}

.low-stock {
  color: #ef4444;
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.low-stock span {
  font-size: 10px;
  color: var(--muted);
  font-weight: 400;
  margin-left: 2px;
}

.recent-card {
  padding: 4px 14px;
}

.recent-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
}

.recent-item + .recent-item {
  border-top: 1px solid var(--line);
}

.type-icon {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  flex: 0 0 30px;
  font-size: 14px;
}

.type-icon.in {
  background: #e8f7ee;
  color: #16a34a;
}

.type-icon.out {
  background: #fef4e2;
  color: #d97706;
}

.recent-info {
  flex: 1;
  min-width: 0;
}

.recent-name {
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-meta {
  margin-top: 3px;
  font-size: 10px;
  color: var(--muted);
}

.recent-qty {
  font-size: 14px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.recent-qty span {
  display: block;
  font-size: 10px;
  font-weight: 400;
  color: var(--muted);
  text-align: right;
  margin-top: 2px;
}

.recent-qty.in {
  color: #16a34a;
}

.recent-qty.out {
  color: #f59e0b;
}
</style>
