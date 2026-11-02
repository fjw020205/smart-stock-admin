<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { productApi } from '../api'
import { formatNumber } from '../utils/number'

const router = useRouter()

const keyword = ref('')
const filter = ref('all')
const categories = ref([])
const items = ref([])
const page = ref(1)
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const firstLoaded = ref(false)

const chips = computed(() => [
  { key: 'all', label: '全部' },
  { key: 'low', label: '低库存' },
  ...categories.value.map((name) => ({ key: name, label: name }))
])

async function fetchPage(reset = false) {
  if (reset) {
    page.value = 1
    finished.value = false
    items.value = []
  }
  loading.value = true
  try {
    const params = { page: page.value, page_size: 10 }
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    if (filter.value === 'low') params.low_stock = 1
    else if (filter.value !== 'all') params.category = filter.value

    const response = await productApi.list(params)
    items.value = reset ? response.data.items : [...items.value, ...response.data.items]
    if (response.data.categories?.length) categories.value = response.data.categories
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

function selectFilter(key) {
  if (filter.value === key) return
  filter.value = key
  reset()
}

function onRefresh() {
  refreshing.value = true
  reset()
}

onMounted(reset)
</script>

<template>
  <div class="products">
    <div class="top">
      <div class="title-row">
        <h1>商品</h1>
        <span class="count">{{ items.length }} 种</span>
      </div>
      <van-search
        v-model="keyword"
        placeholder="搜索商品名称 / 编码"
        shape="round"
        background="transparent"
        @search="reset"
        @clear="reset"
      />
      <div class="chips">
        <button
          v-for="chip in chips"
          :key="chip.key"
          type="button"
          :class="{ active: filter === chip.key }"
          @click="selectFilter(chip.key)"
        >
          {{ chip.label }}
        </button>
      </div>
    </div>

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh" class="list-wrap">
      <van-list
        v-model:loading="loading"
        :finished="finished"
        finished-text="没有更多商品了"
        :immediate-check="false"
        @load="fetchPage(false)"
      >
        <div class="list">
          <div
            v-for="item in items"
            :key="item.id"
            class="product-card"
            @click="router.push(`/products/${item.id}`)"
          >
            <div class="p-head">
              <div class="p-name">
                {{ item.name }}
                <span v-if="item.low_stock" class="pill red">低库存</span>
                <span v-if="!item.status" class="pill gray">停用</span>
              </div>
              <van-icon name="arrow" color="#cbd5e1" />
            </div>
            <div class="p-meta">
              <span class="mono">{{ item.code }}</span>
              <span v-if="item.spec">· {{ item.spec }}</span>
              <span v-if="item.category">· {{ item.category }}</span>
            </div>
            <div class="p-foot">
              <div class="stock" :class="{ low: item.low_stock }">
                {{ formatNumber(item.stock) }}<span>{{ item.unit }}</span>
              </div>
              <div class="safety">安全库存 {{ item.safety_stock }}{{ item.unit }}</div>
            </div>
          </div>
        </div>
      </van-list>

      <van-empty
        v-if="firstLoaded && !items.length && !loading"
        description="没有找到商品"
        image="search"
        :image-size="90"
      />
    </van-pull-refresh>
  </div>
</template>

<style scoped>
.products {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: 8px;
}

.top {
  position: sticky;
  top: 0;
  z-index: 10;
  padding: calc(16px + env(safe-area-inset-top)) 6px 10px;
  background: linear-gradient(180deg, #ffffff 78%, rgba(255, 255, 255, 0.92));
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(238, 242, 248, 0.9);
}

.title-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 0 14px;
}

.title-row h1 {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.count {
  font-size: 11px;
  color: var(--muted);
}

.top :deep(.van-search) {
  padding: 6px 8px 4px;
}

.top :deep(.van-search__content) {
  background: #f4f7fb;
}

.chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 6px 14px 2px;
  scrollbar-width: none;
}

.chips::-webkit-scrollbar {
  display: none;
}

.chips button {
  flex: 0 0 auto;
  height: 28px;
  padding: 0 12px;
  border-radius: 14px;
  border: 1px solid #e5ecf6;
  background: #fff;
  color: #475569;
  font-size: 12px;
}

.chips button.active {
  background: #1677ff;
  border-color: #1677ff;
  color: #fff;
  font-weight: 600;
}

.list-wrap {
  min-height: 60vh;
}

.list {
  padding: 12px 14px 0;
  display: grid;
  gap: 10px;
}

.product-card {
  background: #fff;
  border-radius: 14px;
  padding: 14px;
  box-shadow: 0 6px 18px -16px rgba(15, 23, 42, 0.4);
}

.product-card:active {
  transform: scale(0.995);
}

.p-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.p-name {
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.p-meta {
  margin-top: 6px;
  font-size: 10px;
  color: var(--muted);
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.p-foot {
  margin-top: 12px;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.stock {
  font-size: 24px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.5px;
}

.stock span {
  font-size: 11px;
  color: var(--muted);
  font-weight: 400;
  margin-left: 3px;
}

.stock.low {
  color: #ef4444;
}

.safety {
  font-size: 10px;
  color: #94a3b8;
}
</style>
