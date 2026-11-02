<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { menuApi } from '../api'
import { ICON_OPTIONS, resolveIcon } from '../utils/icons'

const loading = ref(false)
const rows = ref([])
const roles = ref([])
const registry = ref({ pages: [], available: [] })

const dialog = reactive({ visible: false, mode: 'create', id: null })
const formRef = ref(null)
const saving = ref(false)
const form = reactive({
  type: 'page',
  path: '',
  name: '',
  icon: 'Menu',
  sort: 50,
  visible: true,
  parent_id: null
})

const roleDialog = reactive({ visible: false, menu: null, role_ids: [], saving: false })

const rules = {
  name: [{ required: true, message: '请输入菜单名称', trigger: 'blur' }],
  path: [
    {
      validator: (rule, value, callback) => {
        if (dialog.mode === 'edit') return callback()
        if (form.type === 'page' && !value) return callback(new Error('请选择页面'))
        callback()
      },
      trigger: 'change'
    }
  ]
}

const groupOptions = computed(() => {
  const result = []
  const walk = (items) => {
    for (const item of items) {
      if (!item.permission) result.push({ id: item.id, name: item.name })
      if (item.children?.length) walk(item.children)
    }
  }
  walk(rows.value)
  return result
})

const pageOptions = computed(() => {
  const available = registry.value.available || []
  if (dialog.mode === 'edit') {
    return registry.value.pages
  }
  return available
})

async function load() {
  loading.value = true
  try {
    const [menuResponse, registryResponse] = await Promise.all([
      menuApi.list(),
      menuApi.registry()
    ])
    rows.value = menuResponse.data.items
    roles.value = menuResponse.data.roles
    registry.value = registryResponse.data
  } catch (error) {
    /* 已提示 */
  } finally {
    loading.value = false
  }
}

function openCreate() {
  dialog.mode = 'create'
  dialog.id = null
  Object.assign(form, {
    type: 'page',
    path: '',
    name: '',
    icon: 'Menu',
    sort: 50,
    visible: true,
    parent_id: null
  })
  dialog.visible = true
}

function openEdit(row) {
  dialog.mode = 'edit'
  dialog.id = row.id
  Object.assign(form, {
    type: row.permission ? 'page' : 'group',
    path: row.path,
    name: row.name,
    icon: row.icon,
    sort: row.sort,
    visible: row.visible,
    parent_id: row.parent_id
  })
  dialog.visible = true
}

function onPageChange(path) {
  const page = registry.value.pages.find((item) => item.path === path)
  if (page) {
    form.name = page.name
    form.icon = page.icon
  }
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
    if (dialog.mode === 'create') {
      await menuApi.create({
        type: form.type,
        path: form.path,
        name: form.name.trim(),
        icon: form.icon,
        sort: form.sort,
        visible: form.visible,
        parent_id: form.parent_id
      })
      ElMessage.success('菜单已创建')
    } else {
      await menuApi.update(dialog.id, {
        name: form.name.trim(),
        icon: form.icon,
        sort: form.sort,
        visible: form.visible,
        parent_id: form.parent_id
      })
      ElMessage.success('菜单已更新')
    }
    dialog.visible = false
    load()
  } catch (error) {
    /* 已提示 */
  } finally {
    saving.value = false
  }
}

async function toggleVisible(row) {
  try {
    await menuApi.update(row.id, { visible: row.visible })
    ElMessage.success(row.visible ? '菜单已显示' : '菜单已隐藏')
  } catch (error) {
    row.visible = !row.visible
  }
}

async function removeMenu(row) {
  try {
    await ElMessageBox.confirm(`确定删除菜单「${row.name}」吗？`, '删除菜单', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch (error) {
    return
  }
  try {
    await menuApi.remove(row.id)
    ElMessage.success('菜单已删除')
    load()
  } catch (error) {
    /* 已提示 */
  }
}

function openRoles(row) {
  roleDialog.menu = row
  roleDialog.role_ids = [...(row.role_ids || [])]
  roleDialog.visible = true
}

async function saveRoles() {
  if (!roleDialog.menu) return
  roleDialog.saving = true
  try {
    await menuApi.saveRoles(roleDialog.menu.id, roleDialog.role_ids)
    ElMessage.success('可见范围已保存')
    roleDialog.visible = false
    load()
  } catch (error) {
    /* 已提示 */
  } finally {
    roleDialog.saving = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>菜单管理</h2>
        <p class="sub">维护侧边栏结构、名称图标与排序，并配置每个菜单对哪些角色可见</p>
      </div>
      <div class="actions">
        <el-button type="primary" :icon="'Plus'" @click="openCreate">新增菜单</el-button>
      </div>
    </div>

    <el-alert type="info" :closable="false" show-icon class="tip">
      <template #title>
        内置页面菜单不可删除，可改名、换图标、调整排序或隐藏；新增菜单支持「已注册页面」和自定义分组。
      </template>
    </el-alert>

    <div class="card">
      <el-table
        v-loading="loading"
        :data="rows"
        row-key="id"
        :tree-props="{ children: 'children' }"
        default-expand-all
        style="width: 100%"
        empty-text="暂无菜单"
      >
        <el-table-column label="菜单名称" min-width="240">
          <template #default="{ row }">
            <div class="menu-cell">
              <span class="m-icon"><el-icon :size="15"><component :is="resolveIcon(row.icon)" /></el-icon></span>
              <span class="m-name">{{ row.name }}</span>
              <el-tag v-if="row.is_builtin" size="small" type="info" effect="plain">内置</el-tag>
              <el-tag v-if="!row.permission" size="small" effect="plain">分组</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="路径" min-width="170">
          <template #default="{ row }"><span class="mono muted">{{ row.path }}</span></template>
        </el-table-column>
        <el-table-column label="页面权限码" width="170">
          <template #default="{ row }">
            <span v-if="row.permission" class="mono perm">{{ row.permission }}</span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="排序" width="80" align="center" prop="sort" />
        <el-table-column label="显示" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.visible" @change="toggleVisible(row)" />
          </template>
        </el-table-column>
        <el-table-column label="可见角色" min-width="180">
          <template #default="{ row }">
            <div class="role-tags">
              <el-tag
                v-for="name in (row.role_names || []).slice(0, 3)"
                :key="name"
                size="small"
                effect="plain"
              >
                {{ name }}
              </el-tag>
              <el-tag v-if="(row.role_names || []).length > 3" size="small" type="info" effect="plain">
                +{{ row.role_names.length - 3 }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button link type="success" @click="openRoles(row)">可见范围</el-button>
              <el-button v-if="!row.is_builtin" link type="danger" @click="removeMenu(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增菜单' : '编辑菜单'" width="540px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-form-item v-if="dialog.mode === 'create'" label="菜单类型">
          <el-radio-group v-model="form.type">
            <el-radio value="page">页面菜单</el-radio>
            <el-radio value="group">分组</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="form.type === 'page' && dialog.mode === 'create'" label="选择页面" prop="path">
          <el-select v-model="form.path" placeholder="选择已注册页面" style="width: 100%" @change="onPageChange">
            <el-option
              v-for="page in pageOptions"
              :key="page.path"
              :label="`${page.name}（${page.path}）`"
              :value="page.path"
            />
          </el-select>
          <div v-if="!pageOptions.length" class="field-tip">全部已注册页面都已在菜单中，可新增分组。</div>
        </el-form-item>

        <el-form-item label="菜单名称" prop="name">
          <el-input v-model="form.name" maxlength="32" placeholder="例如：库存作业" />
        </el-form-item>

        <el-form-item label="图标">
          <el-select v-model="form.icon" style="width: 100%">
            <el-option v-for="icon in ICON_OPTIONS" :key="icon" :label="icon" :value="icon">
              <span class="icon-option">
                <el-icon><component :is="resolveIcon(icon)" /></el-icon>
                {{ icon }}
              </span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="上级菜单">
          <el-select v-model="form.parent_id" clearable placeholder="顶级菜单" style="width: 100%">
            <el-option v-for="item in groupOptions" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" :max="999" controls-position="right" />
          <span class="field-tip inline">数字越小越靠前</span>
        </el-form-item>

        <el-form-item label="是否显示">
          <el-switch v-model="form.visible" active-text="显示" inactive-text="隐藏" />
        </el-form-item>

        <el-form-item v-if="form.type === 'page' && dialog.mode === 'edit'" label="路径">
          <el-input v-model="form.path" disabled />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="roleDialog.visible" title="配置可见角色" width="480px">
      <p class="dialog-tip">
        「{{ roleDialog.menu?.name }}」将对勾选的角色可见。超级管理员始终可见，不受此配置影响。
      </p>
      <el-checkbox-group v-model="roleDialog.role_ids" class="role-checks">
        <el-checkbox v-for="role in roles" :key="role.id" :value="role.id" :disabled="role.code === 'admin'">
          {{ role.name }} <span class="muted">（{{ role.code }}）</span>
        </el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="roleDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="roleDialog.saving" @click="saveRoles">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.tip {
  border-radius: 10px;
}

.menu-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.m-icon {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  display: grid;
  place-items: center;
  background: #f0f7ff;
  color: var(--brand);
}

.m-name {
  font-weight: 600;
}

.perm {
  color: #475569;
  background: #f1f5f9;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 11px;
}

.role-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.dialog-tip {
  margin-bottom: 16px;
  font-size: 12px;
  color: var(--muted);
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 12px;
  line-height: 1.7;
}

.role-checks {
  display: grid;
  gap: 4px;
}

.field-tip {
  font-size: 11px;
  color: var(--muted);
  line-height: 1.6;
  margin-top: 4px;
}

.field-tip.inline {
  margin: 0 0 0 10px;
}

.icon-option {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
