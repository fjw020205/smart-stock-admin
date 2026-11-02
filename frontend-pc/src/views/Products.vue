<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { productApi } from '../api'
import { can } from '../utils/permission'
import { formatDateTime, formatMoney, formatNumber } from '../utils/format'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const rows = ref([])
const categories = ref([])
const total = ref(0)
const filters = reactive({
  keyword: '',
  category: '',
  status: '',
  low_stock: false
})
const pager = reactive({ page: 1, page_size: 10 })

const drawer = reactive({ visible: false, mode: 'create', id: null })
const saving = ref(false)
const formRef = ref(null)
const form = reactive({
  code: '',
  name: '',
  category: '',
  spec: '',
  unit: '件',
  safety_stock: 5,
  cost_price: 0,
  sale_price: 0,
  initial_stock: 0,
  status: true,
  remark: ''
})
const currentStock = ref(0)

const rules = {
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  unit: [{ required: true, message: '请输入单位', trigger: 'blur' }]
}

function resetForm() {
  Object.assign(form, {
    code: '',
    name: '',
    category: '',
    spec: '',
    unit: '件',
    safety_stock: 5,
    cost_price: 0,
    sale_price: 0,
    initial_stock: 0,
    status: true,
    remark: ''
  })
  currentStock.value = 0
}

async function load() {
  loading.value = true
  try {
    const params = {
      page: pager.page,
      page_size: pager.page_size
    }
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    if (filters.category) params.category = filters.category
    if (filters.status !== '') params.status = filters.status
    if (filters.low_stock) params.low_stock = 1

    const response = await productApi.list(params)
    rows.value = response.data.items
    total.value = response.data.total
    categories.value = response.data.categories
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

function resetFilters() {
  filters.keyword = ''
  filters.category = ''
  filters.status = ''
  filters.low_stock = false
  pager.page = 1
  load()
}

function openCreate() {
  drawer.mode = 'create'
  drawer.id = null
  resetForm()
  drawer.visible = true
}

function openEdit(row) {
  drawer.mode = 'edit'
  drawer.id = row.id
  resetForm()
  Object.assign(form, {
    code: row.code,
    name: row.name,
    category: row.category,
    spec: row.spec,
    unit: row.unit,
    safety_stock: row.safety_stock,
    cost_price: row.cost_price,
    sale_price: row.sale_price,
    status: row.status,
    remark: row.remark
  })
  currentStock.value = row.stock
  drawer.visible = true
}

async function submit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch (error) {
    return
  }
  saving.value = true
  try {
    const payload = {
      code: form.code.trim(),
      name: form.name.trim(),
      category: form.category,
      spec: form.spec,
      unit: form.unit,
      safety_stock: form.safety_stock,
      cost_price: form.cost_price,
      sale_price: form.sale_price,
      status: form.status,
      remark: form.remark
    }
    if (drawer.mode === 'create') {
      payload.initial_stock = form.initial_stock
      await productApi.create(payload)
      ElMessage.success('商品已创建')
    } else {
      await productApi.update(drawer.id, payload)
      ElMessage.success('商品已更新')
    }
    drawer.visible = false
    load()
  } catch (error) {
    /* 已提示 */
  } finally {
    saving.value = false
  }
}

async function removeProduct(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${row.name}」吗？已有出入库记录的商品只能停用，不能删除。`,
      '删除商品',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch (error) {
    return
  }
  try {
    await productApi.remove(row.id)
    ElMessage.success('商品已删除')
    if (rows.value.length === 1 && pager.page > 1) pager.page -= 1
    load()
  } catch (error) {
    /* 已提示 */
  }
}

function goStock(row, mode) {
  router.push({ path: `/stock/${mode}`, query: { productId: row.id } })
}

onMounted(() => {
  if (route.query.low_stock === '1') filters.low_stock = true
  if (typeof route.query.keyword === 'string') filters.keyword = route.query.keyword
  load()
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>商品管理</h2>
        <p class="sub">维护商品档案与安全库存，库存数量由出入库自动变更</p>
      </div>
      <div class="actions">
        <el-button v-perm="'product:create'" type="primary" :icon="'Plus'" @click="openCreate">
          新增商品
        </el-button>
      </div>
    </div>

    <div class="card">
      <div class="filter-bar" style="padding: 16px 20px 4px">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索名称 / 编码 / 规格"
          clearable
          :prefix-icon="'Search'"
          @keyup.enter="search"
          @clear="search"
        />
        <el-select v-model="filters.category" placeholder="全部分类" clearable @change="search">
          <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.status" placeholder="全部状态" @change="search">
          <el-option label="在售" value="1" />
          <el-option label="停用" value="0" />
        </el-select>
        <el-checkbox v-model="filters.low_stock" @change="search">仅看低库存</el-checkbox>
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="resetFilters">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" style="width: 100%" empty-text="暂无商品">
        <el-table-column label="商品" min-width="220">
          <template #default="{ row }">
            <div class="product-cell">
              <div class="pname">
                {{ row.name }}
                <el-tag v-if="row.low_stock" size="small" type="danger" effect="light">低库存</el-tag>
                <el-tag v-if="!row.status" size="small" type="info" effect="plain">已停用</el-tag>
              </div>
              <div class="pcode mono">{{ row.code }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="120">
          <template #default="{ row }">{{ row.category || '-' }}</template>
        </el-table-column>
        <el-table-column prop="spec" label="规格" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.spec || '-' }}</template>
        </el-table-column>
        <el-table-column label="库存" width="110" align="right">
          <template #default="{ row }">
            <span class="stock-value" :class="{ low: row.low_stock }">
              {{ formatNumber(row.stock) }}
            </span>
            <span class="unit">{{ row.unit }}</span>
          </template>
        </el-table-column>
        <el-table-column label="安全库存" width="100" align="right">
          <template #default="{ row }">{{ row.safety_stock }}</template>
        </el-table-column>
        <el-table-column label="售价" width="100" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.sale_price) }}</template>
        </el-table-column>
        <el-table-column label="更新时间" width="150">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button v-if="can('product:update')" link type="primary" @click="openEdit(row)">
                编辑
              </el-button>
              <el-button v-if="can('stock:in')" link type="success" @click="goStock(row, 'in')">
                入库
              </el-button>
              <el-button v-if="can('stock:out')" link type="warning" @click="goStock(row, 'out')">
                出库
              </el-button>
              <el-button v-if="can('product:delete')" link type="danger" @click="removeProduct(row)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pager.page"
        v-model:page-size="pager.page_size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="load"
        @size-change="changePageSize"
      />
    </div>

    <el-drawer v-model="drawer.visible" :size="520" :title="drawer.mode === 'create' ? '新增商品' : '编辑商品'">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <div class="form-grid">
          <el-form-item label="商品编码" :class="{ full: drawer.mode === 'create' }">
            <el-input
              v-model="form.code"
              :disabled="drawer.mode === 'edit'"
              placeholder="留空自动生成"
              maxlength="32"
            />
          </el-form-item>
          <el-form-item v-if="drawer.mode === 'edit'" label="当前库存">
            <el-input :model-value="`${currentStock} ${form.unit}`" disabled />
          </el-form-item>
          <el-form-item label="商品名称" prop="name" class="full">
            <el-input v-model="form.name" placeholder="例如：青提茉莉冷萃原液" maxlength="64" />
          </el-form-item>
          <el-form-item label="分类">
            <el-select v-model="form.category" filterable allow-create default-first-option placeholder="选择或输入">
              <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="单位" prop="unit">
            <el-input v-model="form.unit" maxlength="16" />
          </el-form-item>
          <el-form-item label="规格">
            <el-input v-model="form.spec" placeholder="例如：500ml/瓶" maxlength="64" />
          </el-form-item>
          <el-form-item label="安全库存（低于该值预警）">
            <el-input-number v-model="form.safety_stock" :min="0" :max="999999" controls-position="right" style="width: 100%" />
          </el-form-item>
          <el-form-item label="成本价（元）">
            <el-input-number v-model="form.cost_price" :min="0" :precision="2" :step="1" controls-position="right" style="width: 100%" />
          </el-form-item>
          <el-form-item label="售价（元）">
            <el-input-number v-model="form.sale_price" :min="0" :precision="2" :step="1" controls-position="right" style="width: 100%" />
          </el-form-item>
          <el-form-item v-if="drawer.mode === 'create'" label="期初库存" class="full">
            <el-input-number v-model="form.initial_stock" :min="0" :max="999999" controls-position="right" style="width: 100%" />
            <div class="field-tip">大于 0 时会自动生成一条「期初入库」记录；后续库存只能通过出入库变更。</div>
          </el-form-item>
          <el-form-item label="状态">
            <el-switch v-model="form.status" active-text="在售" inactive-text="停用" />
          </el-form-item>
          <el-form-item label="备注" class="full">
            <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="200" show-word-limit />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="drawer.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.product-cell .pname {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--ink);
}

.pcode {
  color: var(--muted);
  margin-top: 3px;
}

.stock-value {
  font-weight: 700;
  font-size: 15px;
}

.stock-value.low {
  color: #ef4444;
}

.unit {
  margin-left: 3px;
  font-size: 11px;
  color: var(--muted);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.form-grid .full {
  grid-column: 1 / -1;
}

.field-tip {
  font-size: 11px;
  color: var(--muted);
  line-height: 1.7;
  margin-top: 4px;
}
</style>
