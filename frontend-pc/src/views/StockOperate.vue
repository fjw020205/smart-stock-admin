<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { productApi, stockApi } from '../api'
import { formatDateTime, formatNumber } from '../utils/format'

const props = defineProps({
  mode: { type: String, default: 'in' }
})

const route = useRoute()
const router = useRouter()

const isIn = computed(() => props.mode === 'in')
const title = computed(() => (isIn.value ? '入库办理' : '出库办理'))
const subtitle = computed(() =>
  isIn.value
    ? '采购到货、退货入库等场景，提交后库存立即增加'
    : '领用、销售出库等场景，提交后库存立即扣减，库存不足会被拦截'
)

const options = ref([])
const product = ref(null)
const quantity = ref(1)
const remark = ref('')
const submitting = ref(false)
const searching = ref(false)
const recent = ref([])
const recentLoading = ref(false)
const formRef = ref(null)

const afterStock = computed(() => {
  if (!product.value) return 0
  return isIn.value ? product.value.stock + quantity.value : product.value.stock - quantity.value
})

const insufficient = computed(
  () => !isIn.value && product.value && quantity.value > product.value.stock
)

const quantityRules = [
  {
    validator: (rule, value, callback) => {
      if (!product.value) return callback(new Error('请先选择商品'))
      if (!Number.isInteger(value) || value <= 0) return callback(new Error('数量需为正整数'))
      if (!isIn.value && value > product.value.stock) {
        return callback(new Error(`库存不足，当前仅剩 ${product.value.stock} ${product.value.unit}`))
      }
      callback()
    },
    trigger: 'change'
  }
]

async function searchProducts(keyword = '') {
  searching.value = true
  try {
    const response = await productApi.list({
      keyword: keyword || undefined,
      status: '1',
      page_size: 30
    })
    options.value = response.data.items
  } catch (error) {
    /* 已提示 */
  } finally {
    searching.value = false
  }
}

async function selectProduct(id) {
  if (!id) {
    product.value = null
    return
  }
  try {
    const response = await productApi.detail(id)
    product.value = response.data
    quantity.value = 1
  } catch (error) {
    product.value = null
  }
}

async function loadRecent() {
  recentLoading.value = true
  try {
    const response = await stockApi.records({
      type: isIn.value ? 'IN' : 'OUT',
      page_size: 8
    })
    recent.value = response.data.items
  } catch (error) {
    /* 已提示 */
  } finally {
    recentLoading.value = false
  }
}

function fillQuantity(step) {
  quantity.value = Math.max(1, Number(quantity.value || 0) + step)
}

async function submit() {
  if (!product.value) {
    ElMessage.warning('请先选择商品')
    return
  }
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch (error) {
    return
  }

  submitting.value = true
  try {
    const api = isIn.value ? stockApi.inbound : stockApi.outbound
    const response = await api({
      product_id: product.value.id,
      quantity: quantity.value,
      remark: remark.value
    })
    ElMessage.success(response.message)
    product.value.stock = response.data.stock
    quantity.value = 1
    remark.value = ''
    formRef.value?.clearValidate()
    loadRecent()
    searchProducts('')
  } catch (error) {
    /* 已提示 */
  } finally {
    submitting.value = false
  }
}

function init() {
  product.value = null
  quantity.value = 1
  remark.value = ''
  searchProducts('')
  loadRecent()
  const preset = route.query.productId
  if (preset) {
    selectProduct(Number(preset))
  }
}

onMounted(init)
watch(() => props.mode, init)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>{{ title }}</h2>
        <p class="sub">{{ subtitle }}</p>
      </div>
      <div class="actions">
        <el-button :icon="'Tickets'" @click="router.push('/stock/records')">查看全部记录</el-button>
      </div>
    </div>

    <div class="stock-grid">
      <div class="card card-pad">
        <div class="form-head">
          <div class="badge" :class="isIn ? 'in' : 'out'">
            <el-icon :size="18"><component :is="isIn ? 'Download' : 'Upload'" /></el-icon>
          </div>
          <div>
            <h3>{{ isIn ? '新增入库单' : '新增出库单' }}</h3>
            <p>填写商品与数量，提交后自动更新库存并记录流水</p>
          </div>
        </div>

        <el-form ref="formRef" :model="{ quantity }" label-position="top" @submit.prevent>
          <el-form-item label="选择商品" required>
            <el-select
              v-model="product"
              value-key="id"
              filterable
              remote
              clearable
              reserve-keyword
              placeholder="输入名称或编码搜索商品"
              :remote-method="searchProducts"
              :loading="searching"
              style="width: 100%"
              @change="(val) => selectProduct(val?.id)"
            >
              <el-option
                v-for="item in options"
                :key="item.id"
                :label="`${item.name}（${item.code}）`"
                :value="item"
              >
                <div class="option-row">
                  <span>{{ item.name }}</span>
                  <span class="option-stock">库存 {{ item.stock }} {{ item.unit }}</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>

          <div v-if="product" class="product-card">
            <div class="pc-top">
              <div>
                <div class="pc-name">{{ product.name }}</div>
                <div class="pc-code mono">{{ product.code }} · {{ product.spec || '无规格' }}</div>
              </div>
              <el-tag v-if="product.low_stock" type="danger" effect="light" size="small">低库存</el-tag>
            </div>
            <div class="pc-stats">
              <div><span>当前库存</span><b>{{ formatNumber(product.stock) }} {{ product.unit }}</b></div>
              <div><span>安全库存</span><b>{{ product.safety_stock }} {{ product.unit }}</b></div>
              <div>
                <span>操作后库存</span>
                <b :class="{ danger: afterStock < 0, success: isIn }">{{ formatNumber(afterStock) }} {{ product.unit }}</b>
              </div>
            </div>
          </div>

          <el-form-item label="数量" prop="quantity" :rules="quantityRules">
            <div class="qty-row">
              <el-input-number
                v-model="quantity"
                :min="1"
                :max="isIn ? 999999 : Math.max(product?.stock || 1, 1)"
                size="large"
                controls-position="right"
                style="width: 180px"
              />
              <div class="quick">
                <button type="button" @click="fillQuantity(1)">+1</button>
                <button type="button" @click="fillQuantity(5)">+5</button>
                <button type="button" @click="fillQuantity(10)">+10</button>
              </div>
            </div>
            <div v-if="insufficient" class="warn-text">
              库存不足，当前仅剩 {{ product.stock }} {{ product.unit }}
            </div>
          </el-form-item>

          <el-form-item label="备注">
            <el-input
              v-model="remark"
              type="textarea"
              :rows="2"
              maxlength="200"
              show-word-limit
              :placeholder="isIn ? '例如：供应商到货、批次号等' : '例如：门店领用、销售出库等'"
            />
          </el-form-item>

          <el-button
            :type="isIn ? 'primary' : 'warning'"
            size="large"
            class="submit"
            :loading="submitting"
            :disabled="!product || insufficient"
            @click="submit"
          >
            {{ isIn ? '确认入库' : '确认出库' }}
          </el-button>
        </el-form>
      </div>

      <div class="card">
        <div class="card-head">
          <div class="card-title">最近{{ isIn ? '入库' : '出库' }}记录</div>
          <el-button link type="primary" @click="router.push('/stock/records')">全部</el-button>
        </div>
        <div v-loading="recentLoading" class="recent-list">
          <div v-for="item in recent" :key="item.id" class="recent-row">
            <div class="recent-main">
              <div class="recent-name">{{ item.product_name }}</div>
              <div class="recent-meta">
                {{ item.operator_name }} · {{ formatDateTime(item.created_at) }}
              </div>
            </div>
            <div class="recent-qty" :class="isIn ? 'in' : 'out'">
              {{ isIn ? '+' : '-' }}{{ item.quantity }}
              <span>→ {{ item.after_stock }}</span>
            </div>
          </div>
          <div v-if="!recent.length && !recentLoading" class="empty-block">暂无记录</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stock-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 16px;
  align-items: start;
}

.form-head {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 22px;
}

.form-head h3 {
  font-size: 16px;
  font-weight: 700;
}

.form-head p {
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted);
}

.badge {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: #fff;
}

.badge.in {
  background: linear-gradient(135deg, #16a34a, #4ade80);
  box-shadow: 0 10px 22px -12px rgba(22, 163, 74, 0.9);
}

.badge.out {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
  box-shadow: 0 10px 22px -12px rgba(245, 158, 11, 0.9);
}

.option-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.option-stock {
  color: #94a3b8;
  font-size: 12px;
}

.product-card {
  padding: 14px 16px;
  border-radius: 12px;
  background: linear-gradient(180deg, #f8fbff, #f3f8ff);
  border: 1px solid #e3eefc;
  margin-bottom: 18px;
}

.pc-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.pc-name {
  font-weight: 600;
  font-size: 15px;
}

.pc-code {
  margin-top: 4px;
  color: var(--muted);
  font-size: 11px;
}

.pc-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #dbe8f8;
}

.pc-stats div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pc-stats span {
  font-size: 11px;
  color: var(--muted);
}

.pc-stats b {
  font-size: 15px;
  color: var(--ink);
}

.pc-stats b.danger {
  color: #ef4444;
}

.pc-stats b.success {
  color: #16a34a;
}

.qty-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.quick {
  display: flex;
  gap: 6px;
}

.quick button {
  border: 1px solid #dbe5f1;
  background: #fff;
  border-radius: 8px;
  padding: 7px 12px;
  cursor: pointer;
  color: #475569;
  font-size: 12px;
}

.quick button:hover {
  color: var(--brand);
  border-color: #b7d4ff;
  background: #f0f7ff;
}

.warn-text {
  color: #ef4444;
  font-size: 12px;
  margin-top: 6px;
}

.submit {
  width: 100%;
  height: 46px;
  font-size: 15px;
  font-weight: 600;
  margin-top: 4px;
}

.recent-list {
  padding: 8px 12px;
  max-height: 560px;
  overflow-y: auto;
}

.recent-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
}

.recent-row:hover {
  background: #f8fafc;
}

.recent-name {
  font-size: 13px;
  font-weight: 600;
}

.recent-meta {
  margin-top: 4px;
  font-size: 11px;
  color: var(--muted);
}

.recent-qty {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.recent-qty span {
  font-weight: 400;
  font-size: 11px;
  color: var(--muted);
  margin-left: 6px;
}

.recent-qty.in {
  color: #16a34a;
}

.recent-qty.out {
  color: #f59e0b;
}

@media (max-width: 1180px) {
  .stock-grid {
    grid-template-columns: 1fr;
  }
}
</style>
