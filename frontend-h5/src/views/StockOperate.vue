<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showSuccessToast, showToast } from 'vant'
import { productApi, stockApi } from '../api'
import { formatNumber } from '../utils/number'

const props = defineProps({
  mode: { type: String, default: 'in' }
})

const route = useRoute()
const router = useRouter()

const isIn = computed(() => props.mode === 'in')
const title = computed(() => (isIn.value ? '入库办理' : '出库办理'))

const product = ref(null)
const quantity = ref(1)
const remark = ref('')
const submitting = ref(false)

const pickerVisible = ref(false)
const keyword = ref('')
const options = ref([])
const searching = ref(false)
let searchTimer = null

const afterStock = computed(() => {
  if (!product.value) return 0
  return isIn.value ? product.value.stock + quantity.value : product.value.stock - quantity.value
})

const insufficient = computed(
  () => !isIn.value && product.value && quantity.value > product.value.stock
)

async function fetchOptions(keywordValue = '') {
  searching.value = true
  try {
    const response = await productApi.list({
      keyword: keywordValue || undefined,
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

function openPicker() {
  pickerVisible.value = true
  if (!options.value.length) fetchOptions('')
}

function onSearch(value) {
  keyword.value = value
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => fetchOptions(value), 300)
}

function choose(item) {
  product.value = item
  quantity.value = 1
  pickerVisible.value = false
}

function fillQuantity(step) {
  quantity.value = Math.max(1, Number(quantity.value || 0) + step)
}

async function loadPreset() {
  const preset = Number(route.query.productId || 0)
  if (!preset) return
  try {
    const response = await productApi.detail(preset)
    product.value = response.data
  } catch (error) {
    /* 已提示 */
  }
}

async function submit() {
  if (!product.value) {
    showToast('请先选择商品')
    return
  }
  if (!Number.isInteger(quantity.value) || quantity.value <= 0) {
    showToast('请输入正确的数量')
    return
  }
  if (insufficient.value) {
    showToast(`库存不足，当前仅剩 ${product.value.stock} ${product.value.unit}`)
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
    showSuccessToast(response.message)
    product.value.stock = response.data.stock
    quantity.value = 1
    remark.value = ''
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
  loadPreset()
}

onMounted(() => {
  init()
  fetchOptions('')
})

watch(() => props.mode, init)
</script>

<template>
  <div class="operate" :class="isIn ? 'is-in' : 'is-out'">
    <van-nav-bar
      :title="title"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <div class="body">
      <div class="card picker" @click="openPicker">
        <div class="picker-label">选择商品</div>
        <div v-if="product" class="picked">
          <div class="picked-main">
            <div class="picked-name">{{ product.name }}</div>
            <div class="picked-meta mono">{{ product.code }} · {{ product.spec || '无规格' }}</div>
          </div>
          <div class="picked-stock">
            {{ formatNumber(product.stock) }}<span>{{ product.unit }}</span>
          </div>
          <van-icon name="arrow" color="#cbd5e1" />
        </div>
        <div v-else class="placeholder">
          <van-icon name="search" />
          <span>点击搜索并选择商品</span>
          <van-icon name="arrow" color="#cbd5e1" />
        </div>
      </div>

      <div v-if="!product" class="card guide">
        <div class="guide-title">三步完成{{ isIn ? '入库' : '出库' }}</div>
        <ol>
          <li><span>1</span>点击上方选择商品</li>
          <li><span>2</span>填写数量，可点 +1 / +5 / +10 快速调整</li>
          <li><span>3</span>确认后库存立即更新，并生成一条流水</li>
        </ol>
      </div>

      <div v-if="product" class="card">
        <div class="stock-grid">
          <div>
            <span>当前库存</span>
            <b>{{ formatNumber(product.stock) }}<i>{{ product.unit }}</i></b>
          </div>
          <div>
            <span>安全库存</span>
            <b class="muted">{{ product.safety_stock }}<i>{{ product.unit }}</i></b>
          </div>
          <div>
            <span>操作后</span>
            <b :class="{ danger: afterStock < 0, ok: isIn }">
              {{ formatNumber(afterStock) }}<i>{{ product.unit }}</i>
            </b>
          </div>
        </div>

        <div class="qty-block">
          <div class="qty-head">
            <span>数量</span>
            <span class="qty-unit">单位：{{ product.unit }}</span>
          </div>
          <div class="qty-row">
            <van-stepper
              v-model="quantity"
              :min="1"
              :max="isIn ? 999999 : Math.max(product.stock, 1)"
              :decimal-length="0"
              button-size="34"
              input-width="64"
              theme="round"
            />
            <div class="quick">
              <button type="button" @click="fillQuantity(1)">+1</button>
              <button type="button" @click="fillQuantity(5)">+5</button>
              <button type="button" @click="fillQuantity(10)">+10</button>
            </div>
          </div>
          <div v-if="insufficient" class="warn">
            库存不足，当前仅剩 {{ product.stock }} {{ product.unit }}
          </div>
        </div>
      </div>

      <div v-if="product" class="card remark-card">
        <van-field
          v-model="remark"
          type="textarea"
          rows="2"
          maxlength="200"
          show-word-limit
          autosize
          :placeholder="isIn ? '备注：供应商、批次号等（选填）' : '备注：领用部门、用途等（选填）'"
          class="remark-field"
        />
      </div>

      <div v-if="product" class="hint">
        <van-icon name="info-o" />
        <span>
          {{ isIn ? '入库成功后库存自动增加' : '出库成功后库存自动扣减，库存不足会被拦截' }}，
          流水记录可在「记录」中查看。
        </span>
      </div>
    </div>

    <div class="bottom">
      <van-button
        block
        round
        :type="isIn ? 'primary' : 'warning'"
        :loading="submitting"
        :disabled="!product || insufficient"
        @click="submit"
      >
        {{ isIn ? '确认入库' : '确认出库' }}
      </van-button>
    </div>

    <van-popup v-model:show="pickerVisible" position="bottom" round :style="{ height: '74%' }">
      <div class="picker-popup">
        <div class="popup-head">
          <span>选择商品</span>
          <van-icon name="cross" @click="pickerVisible = false" />
        </div>
        <van-search
          v-model="keyword"
          placeholder="搜索名称或编码"
          shape="round"
          @update:model-value="onSearch"
          @search="fetchOptions(keyword)"
        />
        <div class="popup-list">
          <van-loading v-if="searching" class="popup-loading" />
          <template v-else>
            <div
              v-for="item in options"
              :key="item.id"
              class="option"
              @click="choose(item)"
            >
              <div class="option-main">
                <div class="option-name">
                  {{ item.name }}
                  <span v-if="item.low_stock" class="pill red">低</span>
                </div>
                <div class="option-meta mono">{{ item.code }} · {{ item.spec || '无规格' }}</div>
              </div>
              <div class="option-stock">
                {{ item.stock }}<span>{{ item.unit }}</span>
              </div>
            </div>
            <van-empty v-if="!options.length" description="没有找到商品" :image-size="70" />
          </template>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.operate {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: calc(84px + env(safe-area-inset-bottom));
}

.body {
  padding: 12px 14px;
  display: grid;
  gap: 12px;
}

.picker-label {
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 10px;
}

.picker {
  padding: 14px 16px;
}

.picked {
  display: flex;
  align-items: center;
  gap: 10px;
}

.picked-main {
  flex: 1;
  min-width: 0;
}

.picked-name {
  font-size: 15px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.picked-meta {
  margin-top: 4px;
  color: var(--muted);
}

.picked-stock {
  font-size: 18px;
  font-weight: 700;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.picked-stock span {
  font-size: 10px;
  color: var(--muted);
  font-weight: 400;
  margin-left: 2px;
}

.placeholder {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #94a3b8;
  font-size: 14px;
  padding: 4px 0;
}

.placeholder span {
  flex: 1;
}

.stock-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding-bottom: 14px;
  border-bottom: 1px dashed #e8eef7;
}.stock-grid span {
  font-size: 10px;
  color: var(--muted);
}

.stock-grid b {
  display: block;
  margin-top: 5px;
  font-size: 19px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.stock-grid b i {
  font-style: normal;
  font-size: 10px;
  font-weight: 400;
  color: var(--muted);
  margin-left: 2px;
}

.stock-grid b.danger {
  color: #ef4444;
}

.stock-grid b.ok {
  color: #16a34a;
}

.stock-grid b.muted {
  color: #475569;
}

.qty-block {
  padding-top: 14px;
}

.qty-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
}

.qty-unit {
  font-size: 10px;
  font-weight: 400;
  color: var(--muted);
}

.qty-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
}

.qty-row :deep(.van-stepper__input) {
  font-size: 17px;
  font-weight: 700;
}

.quick {
  display: flex;
  gap: 6px;
}

.quick button {
  height: 32px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid #e2eaf5;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
}

.quick button:active {
  background: #eff6ff;
  color: #1677ff;
}

.warn {
  margin-top: 10px;
  color: #ef4444;
  font-size: 11px;
}

.remark-card {
  padding: 4px 12px;
}

.remark-field {
  padding: 10px 0;
}

.remark-field :deep(.van-field__control) {
  font-size: 13px;
}

.guide {
  padding: 16px;
}

.guide-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.guide ol {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.guide li {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.5;
}

.guide li span {
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  border-radius: 50%;
  background: #eff6ff;
  color: #1677ff;
  font-size: 10px;
  font-weight: 700;
  display: grid;
  place-items: center;
}

.hint {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  padding: 2px 6px;
  font-size: 11px;
  line-height: 1.7;
  color: #94a3b8;
}

.hint :deep(.van-icon) {
  margin-top: 2px;
  flex: 0 0 auto;
}

.bottom {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 0;
  width: 100%;
  max-width: 640px;
  padding: 10px 14px calc(10px + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--line);
}

.bottom :deep(.van-button) {
  height: 48px;
  font-size: 16px;
  box-shadow: 0 10px 22px -14px rgba(22, 119, 255, 0.8);
}

.picker-popup {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.popup-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 18px 8px;
  font-size: 16px;
  font-weight: 600;
}

.popup-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px calc(16px + env(safe-area-inset-bottom));
}

.popup-loading {
  display: flex;
  justify-content: center;
  padding: 30px 0;
}

.option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 10px;
  border-radius: 10px;
}

.option:active {
  background: #f5f9ff;
}

.option-main {
  flex: 1;
  min-width: 0;
}

.option-name {
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.option-meta {
  margin-top: 4px;
  color: var(--muted);
}

.option-stock {
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.option-stock span {
  font-size: 10px;
  color: var(--muted);
  font-weight: 400;
  margin-left: 2px;
}
</style>
