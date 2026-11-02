<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { roleApi, userApi } from '../api'
import { can } from '../utils/permission'
import { formatDateTime, initials } from '../utils/format'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const roles = ref([])
const filters = reactive({ keyword: '', role_id: '', status: '' })
const pager = reactive({ page: 1, page_size: 10 })

const dialog = reactive({ visible: false, mode: 'create', id: null })
const saving = ref(false)
const formRef = ref(null)
const form = reactive({
  username: '',
  real_name: '',
  phone: '',
  role_id: null,
  password: '',
  status: true,
  must_change_password: true
})

const resetDialog = reactive({ visible: false, id: null, name: '', password: '' })
const resetRef = ref(null)
const resetRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { pattern: /^(?=.*[A-Za-z])(?=.*\d).{8,20}$/, message: '8-20 位，需包含字母和数字', trigger: 'blur' }
  ]
}

const menuDrawer = reactive({
  visible: false,
  user: null,
  mode: 'inherit',
  tree: [],
  checked: [],
  roleChecked: [],
  loading: false,
  saving: false
})
const treeRef = ref(null)
const treeKey = ref(0)

const rules = {
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9_]{3,20}$/, message: '3-20 位字母、数字或下划线', trigger: 'blur' }
  ],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role_id: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [
    {
      validator: (rule, value, callback) => {
        if (dialog.mode === 'edit') return callback()
        if (!value) return callback(new Error('请输入初始密码'))
        if (!/^(?=.*[A-Za-z])(?=.*\d).{8,20}$/.test(value)) {
          return callback(new Error('8-20 位，需包含字母和数字'))
        }
        callback()
      },
      trigger: 'blur'
    }
  ]
}

async function load() {
  loading.value = true
  try {
    const params = { page: pager.page, page_size: pager.page_size }
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    if (filters.role_id) params.role_id = filters.role_id
    if (filters.status !== '') params.status = filters.status
    const response = await userApi.list(params)
    rows.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    /* 已提示 */
  } finally {
    loading.value = false
  }
}

async function loadRoles() {
  try {
    const response = await roleApi.list()
    roles.value = response.data.items
  } catch (error) {
    roles.value = []
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
  filters.role_id = ''
  filters.status = ''
  pager.page = 1
  load()
}

function openCreate() {
  dialog.mode = 'create'
  dialog.id = null
  Object.assign(form, {
    username: '',
    real_name: '',
    phone: '',
    role_id: roles.value.find((role) => role.code === 'staff')?.id || roles.value[0]?.id || null,
    password: '',
    status: true,
    must_change_password: true
  })
  dialog.visible = true
}

function openEdit(row) {
  dialog.mode = 'edit'
  dialog.id = row.id
  Object.assign(form, {
    username: row.username,
    real_name: row.real_name,
    phone: row.phone,
    role_id: row.role?.id || null,
    password: '',
    status: row.status,
    must_change_password: false
  })
  dialog.visible = true
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
      await userApi.create({
        username: form.username.trim(),
        real_name: form.real_name.trim(),
        phone: form.phone.trim(),
        role_id: form.role_id,
        password: form.password,
        status: form.status,
        must_change_password: form.must_change_password
      })
      ElMessage.success('用户已创建')
    } else {
      await userApi.update(dialog.id, {
        real_name: form.real_name.trim(),
        phone: form.phone.trim(),
        role_id: form.role_id
      })
      ElMessage.success('用户已更新')
    }
    dialog.visible = false
    load()
  } catch (error) {
    /* 已提示 */
  } finally {
    saving.value = false
  }
}

async function toggleStatus(row) {
  try {
    await userApi.toggle(row.id, row.status)
    ElMessage.success(row.status ? '账号已启用' : '账号已停用')
  } catch (error) {
    row.status = !row.status
  }
}

async function removeUser(row) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.real_name}（${row.username}）」吗？`, '删除用户', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch (error) {
    return
  }
  try {
    await userApi.remove(row.id)
    ElMessage.success('用户已删除')
    load()
  } catch (error) {
    /* 已提示 */
  }
}

function openReset(row) {
  resetDialog.id = row.id
  resetDialog.name = row.real_name
  resetDialog.password = ''
  resetDialog.visible = true
}

async function submitReset() {
  if (!resetRef.value) return
  try {
    await resetRef.value.validate()
  } catch (error) {
    return
  }
  try {
    await userApi.resetPassword(resetDialog.id, { new_password: resetDialog.password })
    ElMessage.success('密码已重置，该用户下次登录需修改密码')
    resetDialog.visible = false
  } catch (error) {
    /* 已提示 */
  }
}

async function openMenus(row) {
  menuDrawer.user = row
  menuDrawer.visible = true
  menuDrawer.loading = true
  menuDrawer.tree = []
  menuDrawer.checked = []
  menuDrawer.roleChecked = []
  try {
    const response = await userApi.menus(row.id)
    menuDrawer.mode = response.data.mode
    menuDrawer.tree = response.data.menus
    menuDrawer.roleChecked = response.data.role_menu_ids
    menuDrawer.checked = response.data.mode === 'custom' ? response.data.menu_ids : response.data.role_menu_ids
    menuDrawer.roleChecked = response.data.role_menu_ids
    treeKey.value += 1
    await nextTick()
    applyChecked()
  } catch (error) {
    menuDrawer.visible = false
  } finally {
    menuDrawer.loading = false
  }
}

function applyChecked() {
  if (!treeRef.value) return
  treeRef.value.setCheckedKeys(menuDrawer.checked)
}

function switchMode(mode) {
  menuDrawer.mode = mode
  nextTick(() => {
    if (!treeRef.value) return
    treeRef.value.setCheckedKeys(mode === 'custom' ? menuDrawer.checked : menuDrawer.roleChecked)
  })
}

async function saveMenus() {
  if (!treeRef.value || !menuDrawer.user) return
  menuDrawer.saving = true
  try {
    if (menuDrawer.mode === 'custom') {
      const ids = [...treeRef.value.getCheckedKeys(), ...treeRef.value.getHalfCheckedKeys()]
      if (!ids.length) {
        ElMessage.warning('自定义菜单至少选择一个页面，或改为跟随角色')
        menuDrawer.saving = false
        return
      }
      await userApi.saveMenus(menuDrawer.user.id, { mode: 'custom', menu_ids: ids })
    } else {
      await userApi.saveMenus(menuDrawer.user.id, { mode: 'inherit' })
    }
    ElMessage.success('菜单权限已保存，该用户刷新后生效')
    menuDrawer.visible = false
  } catch (error) {
    /* 已提示 */
  } finally {
    menuDrawer.saving = false
  }
}

onMounted(() => {
  loadRoles()
  load()
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>用户管理</h2>
        <p class="sub">管理登录账号、所属角色，并可单独调整某个人的可见菜单</p>
      </div>
      <div class="actions">
        <el-button v-perm="'user:create'" type="primary" :icon="'Plus'" @click="openCreate">
          新增用户
        </el-button>
      </div>
    </div>

    <div class="card">
      <div class="filter-bar" style="padding: 16px 20px 4px">
        <el-input
          v-model="filters.keyword"
          placeholder="姓名 / 账号 / 手机"
          clearable
          :prefix-icon="'Search'"
          @keyup.enter="search"
          @clear="search"
        />
        <el-select v-model="filters.role_id" placeholder="全部角色" clearable @change="search">
          <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
        </el-select>
        <el-select v-model="filters.status" placeholder="全部状态" @change="search">
          <el-option label="正常" value="1" />
          <el-option label="停用" value="0" />
        </el-select>
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="resetFilters">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" style="width: 100%" empty-text="暂无用户">
        <el-table-column label="用户" min-width="200">
          <template #default="{ row }">
            <div class="user-cell">
              <div class="avatar">{{ initials(row.real_name) }}</div>
              <div>
                <div class="uname">
                  {{ row.real_name }}
                  <el-tag v-if="row.is_self" size="small" effect="plain">我</el-tag>
                  <el-tag v-if="row.protected" size="small" type="warning" effect="plain">内置</el-tag>
                </div>
                <div class="uid">@{{ row.username }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="130">
          <template #default="{ row }">
            <el-tag :type="row.role?.code === 'admin' ? 'danger' : 'primary'" effect="light" size="small">
              {{ row.role?.name || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" width="140">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              :disabled="row.is_self || row.protected || !can('user:update')"
              @change="toggleStatus(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="最后登录" width="160">
          <template #default="{ row }">{{ row.last_login_at || '从未登录' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="150">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="285" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button v-if="can('user:update')" link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button v-if="can('user:reset')" link type="warning" @click="openReset(row)">重置密码</el-button>
              <el-button
                v-if="can('user:grant') && !row.protected"
                link
                type="success"
                @click="openMenus(row)"
              >
                菜单权限
              </el-button>
              <el-button
                v-if="can('user:delete') && !row.protected && !row.is_self"
                link
                type="danger"
                @click="removeUser(row)"
              >
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

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增用户' : '编辑用户'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-form-item label="登录账号" prop="username">
          <el-input v-model="form.username" :disabled="dialog.mode === 'edit'" maxlength="20" placeholder="字母、数字或下划线" />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="form.real_name" maxlength="32" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" maxlength="20" />
        </el-form-item>
        <el-form-item label="角色" prop="role_id">
          <el-select v-model="form.role_id" placeholder="请选择角色" style="width: 100%">
            <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="dialog.mode === 'create'" label="初始密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="8-20 位，包含字母和数字" />
        </el-form-item>
        <el-form-item v-if="dialog.mode === 'create'" label="首次改密">
          <el-switch v-model="form.must_change_password" active-text="登录后强制修改" />
        </el-form-item>
        <el-form-item v-if="dialog.mode === 'create'" label="账号状态">
          <el-switch v-model="form.status" active-text="正常" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetDialog.visible" title="重置密码" width="460px">
      <p class="dialog-tip">
        将为「{{ resetDialog.name }}」设置新的登录密码，该用户下次登录时会被要求修改密码。
      </p>
      <el-form ref="resetRef" :model="resetDialog" :rules="resetRules" label-width="90px">
        <el-form-item label="新密码" prop="password">
          <el-input v-model="resetDialog.password" type="password" show-password placeholder="8-20 位，包含字母和数字" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitReset">确认重置</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="menuDrawer.visible" :size="480" title="菜单权限">
      <div v-loading="menuDrawer.loading">
        <div class="menu-user">
          <div class="avatar">{{ initials(menuDrawer.user?.real_name) }}</div>
          <div>
            <b>{{ menuDrawer.user?.real_name }}</b>
            <div class="muted">@{{ menuDrawer.user?.username }} · {{ menuDrawer.user?.role?.name }}</div>
          </div>
        </div>

        <el-radio-group v-model="menuDrawer.mode" class="mode-group" @change="switchMode">
          <el-radio value="inherit">跟随角色</el-radio>
          <el-radio value="custom">单独配置</el-radio>
        </el-radio-group>

        <div class="mode-tip">
          {{
            menuDrawer.mode === 'inherit'
              ? '当前继承所属角色的菜单可见范围，角色调整后该用户同步变化。'
              : '为该用户单独指定可见菜单，不再受角色菜单变化影响（权限仍由角色决定）。'
          }}
        </div>

        <el-tree
          :key="treeKey"
          ref="treeRef"
          :data="menuDrawer.tree"
          node-key="id"
          show-checkbox
          default-expand-all
          :props="{ label: 'name', children: 'children' }"
          class="menu-tree"
          :class="{ readonly: menuDrawer.mode === 'inherit' }"
        >
          <template #default="{ data }">
            <span class="tree-node">
              <span>{{ data.name }}</span>
              <span v-if="data.permission" class="tree-perm mono">{{ data.permission }}</span>
            </span>
          </template>
        </el-tree>
      </div>

      <template #footer>
        <el-button @click="menuDrawer.visible = false">取消</el-button>
        <el-button type="primary" :loading="menuDrawer.saving" @click="saveMenus">保存</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1677ff, #5ca9ff);
  color: #fff;
  font-weight: 600;
  display: grid;
  place-items: center;
  font-size: 13px;
  flex: 0 0 34px;
}

.uname {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.uid {
  font-size: 11px;
  color: var(--muted);
  margin-top: 2px;
}

.dialog-tip {
  margin-bottom: 16px;
  font-size: 12px;
  line-height: 1.8;
  color: var(--muted);
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 12px;
}

.menu-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 2px 14px;
  border-bottom: 1px solid var(--line);
}

.mode-group {
  margin-top: 16px;
}

.mode-tip {
  margin: 10px 0 14px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f8fafc;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
}

.menu-tree {
  --el-tree-node-hover-bg-color: #f4f8ff;
}

.menu-tree.readonly {
  pointer-events: none;
  opacity: 0.68;
}

.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 8px;
}

.tree-perm {
  color: #94a3b8;
  font-size: 11px;
}

@media (max-width: 900px) {
  .filter-bar .el-input,
  .filter-bar .el-select {
    width: 100%;
  }
}
</style>
