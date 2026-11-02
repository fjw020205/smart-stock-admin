<script setup>
import { onMounted, reactive, ref } from 'vue'
import { stockApi } from '../api'
import { formatNumber } from '../utils/format'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const filters = reactive({
  type: '',
  keyword: '',
  range: []
})
const pager = reactive({ page: 1, page_size: 10 })

async function load() {
  loading.value = true
  try {
    const params = {
      page: pager.page,
      page_size: pager.page_size
    }
    if (filters.type) params.type = filters.type
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    if (filters.range?.length === 2) {
      params.date_from = filters.range[0]
      params.date_to = filters.range[1]
    }
    const response = await stockApi.records(params)
    rows.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    /* 已提示 */
  } finally {
    loading.value = false
  }
}

function search() {
  pager.page = 1
  load()
}

function changePageSize() {
  pager.page = 1
  load()
}

function reset() {
  filters.type = ''
  filters.keyword = ''
  filters.range = []
  pager.page = 1
  load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>出入库记录</h2>
        <p class="sub">每一次库存变动都有据可查，记录只读、不可修改</p>
      </div>
    </div>

    <div class="card">
      <div class="filter-bar" style="padding: 16px 20px 4px">
        <el-radio-group v-model="filters.type" @change="search">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="IN">入库</el-radio-button>
          <el-radio-button value="OUT">出库</el-radio-button>
        </el-radio-group>
        <el-date-picker
          v-model="filters.range"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
          @change="search"
        />
        <el-input
          v-model="filters.keyword"
          placeholder="单号 / 商品名称 / 编码"
          clearable
          :prefix-icon="'Search'"
          @keyup.enter="search"
          @clear="search"
        />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" style="width: 100%" empty-text="没有符合条件的记录">
        <el-table-column prop="order_no" label="单号" width="180">
          <template #default="{ row }"><span class="mono">{{ row.order_no }}</span></template>
        </el-table-column>
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag :type="row.type === 'IN' ? 'success' : 'warning'" size="small" effect="light">
              {{ row.type_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="商品" min-width="190">
          <template #default="{ row }">
            <div class="p-name">{{ row.product_name }}</div>
            <div class="p-code mono">{{ row.product_code }}</div>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="100" align="right">
          <template #default="{ row }">
            <span :class="row.type === 'IN' ? 'in' : 'out'">
              {{ row.type === 'IN' ? '+' : '-' }}{{ formatNumber(row.quantity) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="变动前" width="100" align="right">
          <template #default="{ row }">{{ formatNumber(row.before_stock) }}</template>
        </el-table-column>
        <el-table-column label="变动后" width="100" align="right">
          <template #default="{ row }"><b>{{ formatNumber(row.after_stock) }}</b></template>
        </el-table-column>
        <el-table-column prop="operator_name" label="操作人" width="110" />
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pager.page"
        v-model:page-size="pager.page_size"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="load"
        @size-change="changePageSize"
      />
    </div>
  </div>
</template>

<style scoped>
.p-name {
  font-weight: 600;
  color: var(--ink);
}

.p-code {
  color: var(--muted);
  margin-top: 2px;
}

.in {
  color: #16a34a;
  font-weight: 600;
}

.out {
  color: #f59e0b;
  font-weight: 600;
}
</style>
