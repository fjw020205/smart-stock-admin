<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productApi, stockApi } from '../api'
import { can } from '../utils/permission'
import { formatMoney } from '../utils/format'
import { formatNumber } from '../utils/number'

const route = useRoute()
const router = useRouter()

const product = ref(null)
const records = ref([])
const loading = ref(true)

const lowStock = computed(
  () => product.value && product.value.stock < product.value.safety_stock
)

async function load() {
  loading.value = true
  try {
    const response = await productApi.detail(route.params.id)
    product.value = response.data
    const recordResponse = await stockApi.records({
      product_id: response.data.id,
      page_size: 5
    })
    records.value = recordResponse.data.items
  } catch (error) {
    /* 已提示 */
  } finally {
    loading.value = false
  }
}

function go(mode) {
  router.push({ path: `/stock/${mode}`, query: { productId: product.value.id } })
}

onMounted(load)
</script>

<template>
  <div class="detail">
    <van-nav-bar
      title="商品详情"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <div v-if="loading" class="skeleton-block">
      <van-skeleton title avatar :row="6" />
    </div>

    <template v-else-if="product">
      <div class="body">
        <div class="card hero">
          <div class="tags">
            <span v-if="product.category" class="pill blue">{{ product.category }}</span>
            <span v-if="lowStock" class="pill red">低库存</span>
            <span v-if="!product.status" class="pill gray">已停用</span>
          </div>
          <h1>{{ product.name }}</h1>
          <div class="code mono">{{ product.code }}<span v-if="product.spec"> · {{ product.spec }}</span></div>

          <div class="stock-row">
            <div class="stock-main">
              <span class="label">当前库存</span>
              <div class="value" :class="{ low: lowStock }">
                {{ formatNumber(product.stock) }}<i>{{ product.unit }}</i>
              </div>
            </div>
            <div class="divider" />
            <div class="stock-side">
              <span class="label">安全库存</span>
              <div class="value small">{{ product.safety_stock }}<i>{{ product.unit }}</i></div>
            </div>
          </div>
        </div>

        <div class="card info">
          <div class="info-title">商品信息</div>
          <van-cell title="商品分类" :value="product.category || '-'" />
          <van-cell title="规格" :value="product.spec || '-'" />
          <van-cell title="单位" :value="product.unit" />
          <van-cell title="售价" :value="`¥${formatMoney(product.sale_price)}`" />
          <van-cell title="成本价" :value="`¥${formatMoney(product.cost_price)}`" />
          <van-cell title="更新时间" :value="product.updated_at" />
          <van-cell v-if="product.remark" title="备注" :label="product.remark" />
        </div>

        <div class="card">
          <div class="section-head">
            <span class="info-title">最近出入库</span>
            <span class="section-link" @click="router.push('/records')">全部记录</span>
          </div>
          <div v-if="records.length" class="records">
            <div v-for="item in records" :key="item.id" class="record">
              <span class="type" :class="item.type === 'IN' ? 'in' : 'out'">
                {{ item.type === 'IN' ? '入' : '出' }}
              </span>
              <div class="record-main">
                <div class="record-qty" :class="item.type === 'IN' ? 'in' : 'out'">
                  {{ item.type === 'IN' ? '+' : '-' }}{{ item.quantity }}
                  <span>→ {{ item.after_stock }} {{ product.unit }}</span>
                </div>
                <div class="record-meta">{{ item.created_at }} · {{ item.operator_name }}</div>
              </div>
            </div>
          </div>
          <div v-else class="empty-records">暂无出入库记录</div>
        </div>
      </div>

      <div class="bottom">
        <van-button
          v-if="can('stock:in')"
          type="primary"
          block
          round
          icon="down"
          @click="go('in')"
        >
          入库
        </van-button>
        <van-button
          v-if="can('stock:out')"
          type="warning"
          block
          round
          icon="upgrade"
          @click="go('out')"
        >
          出库
        </van-button>
      </div>
    </template>

    <van-empty v-else description="商品不存在或已删除" />
  </div>
</template>

<style scoped>
.detail {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: calc(84px + env(safe-area-inset-bottom));
}

.body {
  padding: 12px 14px 20px;
  display: grid;
  gap: 12px;
}

.hero {
  padding: 18px;
}

.tags {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}

h1 {
  font-size: 21px;
  font-weight: 700;
  line-height: 1.35;
}

.code {
  margin-top: 6px;
  color: var(--muted);
  font-size: 11px;
}

.stock-row {
  display: flex;
  align-items: center;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px dashed #e8eef7;
}

.stock-main {
  flex: 1;
}

.label {
  font-size: 11px;
  color: var(--muted);
}

.value {
  margin-top: 4px;
  font-size: 34px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -1px;
  line-height: 1.1;
}

.value i {
  font-style: normal;
  font-size: 12px;
  font-weight: 400;
  color: var(--muted);
  margin-left: 3px;
}

.value.low {
  color: #ef4444;
}

.value.small {
  font-size: 20px;
}

.divider {
  width: 1px;
  height: 46px;
  background: #eef2f8;
  margin: 0 18px;
}

.info-title {
  font-size: 14px;
  font-weight: 600;
}

.info {
  padding: 16px 16px 4px;
}

.info :deep(.van-cell) {
  padding-left: 0;
  padding-right: 0;
  font-size: 13px;
}

.info :deep(.van-cell__title) {
  color: var(--muted);
}

.info :deep(.van-cell__value) {
  color: var(--ink);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.section-link {
  font-size: 11px;
  color: var(--muted);
}

.record {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
}

.record + .record {
  border-top: 1px solid var(--line);
}

.type {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 700;
}

.type.in {
  background: #e8f7ee;
  color: #16a34a;
}

.type.out {
  background: #fef4e2;
  color: #d97706;
}

.record-main {
  flex: 1;
}

.record-qty {
  font-size: 14px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.record-qty span {
  font-size: 10px;
  font-weight: 400;
  color: var(--muted);
  margin-left: 4px;
}

.record-qty.in {
  color: #16a34a;
}

.record-qty.out {
  color: #f59e0b;
}

.record-meta {
  margin-top: 3px;
  font-size: 10px;
  color: var(--muted);
}

.empty-records {
  padding: 16px 0 12px;
  text-align: center;
  font-size: 12px;
  color: var(--muted);
}

.bottom {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 0;
  width: 100%;
  max-width: 640px;
  display: flex;
  gap: 10px;
  padding: 10px 14px calc(10px + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--line);
}

.bottom :deep(.van-button) {
  flex: 1;
  height: 46px;
}
</style>
