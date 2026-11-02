<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { menuApi, roleApi } from '../api'
import { formatDateTime } from '../utils/format'

const loading = ref(false)
const roles = ref([])
const selectedId = ref(null)
const permissions = ref([])
const modules = ref([])
const menuTree = ref([])
const checkedPerms = ref([])
const checkedMenus = ref([])
const menuTreeRef = ref(null)
const activeTab = ref('permissions')
const savingPerm = ref(false)
const savingMenu = ref(false)

const createDialog = reactive({ visible: false, saving: false })
const createFormRef = ref(null)
const createForm = reactive({ code: '', name: '', description: '' })
const createRules = {
  code: [
    { required: true, message: '请输入角色标识', trigger: 'blur' },
    { pattern: /^[a-z][a-z0-9_]{1,19}$/, message: '小写字母开头，2-20 位', trigger: 'blur' }
  ],
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }]
}

const editDialog = reactive({ visible: false, saving: false })
const editForm = reactive({ name: '', description: '' })

const current = computed(() => roles.value.find((role) => role.id === selectedId.value) || null)
const readonly = computed(() => Boolean(current.value?.is_builtin || current.value?.is_admin))

const groupedPermissions = computed(() =>
  modules.value.map((module) => ({
    module,
    items: permissions.value.filter((item) => item.module === module)
  }))
)

const leafMenuIds = computed(() => {
  const ids = new Set()
  const walk = (items) => {
    for (const item of items) {
      if (item.permission) ids.add(item.id)
      if (item.children?.length) walk(item.children)
    }
  }
  walk(menuTree.value)
  return ids
})

async function load() {
  loading.value = true
  try {
    const [roleResponse, permissionResponse, menuResponse] = await Promise.all([
      roleApi.list(),
      roleApi.permissions(),
      menuApi.list()
    ])
    roles.value = roleResponse.data.items
    permissions.value = permissionResponse.data.items
    modules.value = permissionResponse.data.modules
    menuTree.value = menuResponse.data.items

    if (!roles.value.find((role) => role.id === selectedId.value)) {
      selectedId.value = roles.value[0]?.id || null
    }
    syncCurrent()
  } catch (error) {
    /* 已提示 */
  } finally {
    loading.value = false
  }
}

function syncCurrent() {
  if (!current.value) return
  checkedPerms.value = [...(current.value.permissions || [])]
  checkedMenus.value = (current.value.menu_ids || []).filter((id) => leafMenuIds.value.has(id))
  nextTick(() => {
    menuTreeRef.value?.setCheckedKeys(checkedMenus.value)
  })
}

watch(selectedId, syncCurrent)
watch(activeTab, (tab) => {
  if (tab === 'menus') {
    nextTick(() => menuTreeRef.value?.setCheckedKeys(checkedMenus.value))
  }
})

function moduleState(module) {
  const items = permissions.value.filter((item) => item.module === module)
  const checked = items.filter((item) => checkedPerms.value.includes(item.code)).length
  return {
    all: items.length > 0 && checked === items.length,
    some: checked > 0 && checked < items.length
  }
}

function toggleModule(module, value) {
  const codes = permissions.value.filter((item) => item.module === module).map((item) => item.code)
  if (value) {
    checkedPerms.value = Array.from(new Set([...checkedPerms.value, ...codes]))
  } else {
    checkedPerms.value = checkedPerms.value.filter((code) => !codes.includes(code))
  }
}

async function savePermissions() {
  if (!current.value) return
  savingPerm.value = true
  try {
    const response = await roleApi.savePermissions(current.value.id, checkedPerms.value)
    Object.assign(current.value, response.data)
    ElMessage.success('功能权限已保存，相关用户下次请求即生效')
  } catch (error) {
    /* 已提示 */
  } finally {
    savingPerm.value = false
  }
}

async function saveMenus() {
  if (!current.value || !menuTreeRef.value) return
  savingMenu.value = true
  try {
    const ids = [
      ...menuTreeRef.value.getCheckedKeys(),
      ...menuTreeRef.value.getHalfCheckedKeys()
    ]
    const response = await roleApi.saveMenus(current.value.id, ids)
    Object.assign(current.value, response.data)
    ElMessage.success('菜单权限已保存，相关用户刷新后生效')
  } catch (error) {
    /* 已提示 */
  } finally {
    savingMenu.value = false
  }
}

function openCreate() {
  Object.assign(createForm, { code: '', name: '', description: '' })
  createDialog.visible = true
}

async function submitCreate() {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
  } catch (error) {
    return
  }
  createDialog.saving = true
  try {
    const response = await roleApi.create({
      code: createForm.code.trim(),
      name: createForm.name.trim(),
      description: createForm.description.trim()
    })
    ElMessage.success('角色已创建，请继续配置权限')
    createDialog.visible = false
    await load()
    selectedId.value = response.data.id
    activeTab.value = 'permissions'
  } catch (error) {
    /* 已提示 */
  } finally {
    createDialog.saving = false
  }
}

function openEdit() {
  if (!current.value) return
  editForm.name = current.value.name
  editForm.description = current.value.description
  editDialog.visible = true
}

async function submitEdit() {
  if (!current.value) return
  if (!editForm.name.trim()) {
    ElMessage.warning('角色名称不能为空')
    return
  }
  editDialog.saving = true
  try {
    const response = await roleApi.update(current.value.id, {
      name: editForm.name.trim(),
      description: editForm.description.trim()
    })
    Object.assign(current.value, response.data)
    ElMessage.success('角色已更新')
    editDialog.visible = false
  } catch (error) {
    /* 已提示 */
  } finally {
    editDialog.saving = false
  }
}

async function removeRole() {
  if (!current.value) return
  try {
    await ElMessageBox.confirm(
      `确定删除角色「${current.value.name}」吗？该角色下不能有用户。`,
      '删除角色',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch (error) {
    return
  }
  try {
    await roleApi.remove(current.value.id)
    ElMessage.success('角色已删除')
    selectedId.value = null
    await load()
  } catch (error) {
    /* 已提示 */
  }
}

onMounted(async () => {
  await load()
  syncCurrent()
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>权限管理</h2>
        <p class="sub">角色决定「能做什么」与「看得见什么」，员工账号默认只有出入库相关权限</p>
      </div>
      <div class="actions">
        <el-button type="primary" :icon="'Plus'" @click="openCreate">新建角色</el-button>
      </div>
    </div>

    <div class="role-layout" v-loading="loading">
      <div class="card role-list">
        <div class="list-head">
          <span>角色列表</span>
          <el-tag size="small" effect="plain">{{ roles.length }}</el-tag>
        </div>
        <div class="roles">
          <button
            v-for="role in roles"
            :key="role.id"
            type="button"
            class="role-item"
            :class="{ active: role.id === selectedId }"
            @click="selectedId = role.id"
          >
            <div class="role-top">
              <span class="role-name">{{ role.name }}</span>
              <el-tag v-if="role.is_admin" size="small" type="danger" effect="plain">超级</el-tag>
              <el-tag v-else-if="role.is_builtin" size="small" type="info" effect="plain">内置</el-tag>
            </div>
            <div class="role-code mono">{{ role.code }}</div>
            <div class="role-meta">
              <span>{{ role.user_count }} 位用户</span>
              <span>{{ role.permissions?.length || 0 }} 项权限</span>
            </div>
          </button>
        </div>
      </div>

      <div v-if="current" class="card role-detail">
        <div class="detail-head">
          <div>
            <div class="detail-title">
              {{ current.name }}
              <el-tag v-if="current.is_builtin" size="small" type="info" effect="plain">内置角色</el-tag>
            </div>
            <p class="detail-desc">{{ current.description || '暂无描述' }}</p>
            <div class="detail-meta">
              <span class="mono">{{ current.code }}</span>
              <span>·</span>
              <span>{{ current.user_count }} 位用户</span>
              <span>·</span>
              <span>创建于 {{ formatDateTime(current.created_at) }}</span>
            </div>
          </div>
          <div class="detail-actions">
            <el-button size="small" @click="openEdit">编辑资料</el-button>
            <el-button v-if="!current.is_builtin" size="small" type="danger" plain @click="removeRole">
              删除角色
            </el-button>
          </div>
        </div>

        <el-alert
          v-if="readonly"
          type="info"
          show-icon
          :closable="false"
          class="readonly-alert"
          title="内置角色不可修改权限"
          description="超级管理员固定拥有全部权限；普通员工为内置示例角色，如需自定义请新建角色。"
        />

        <el-tabs v-model="activeTab" class="role-tabs">
          <el-tab-pane label="功能权限" name="permissions">
            <div class="tab-tip">控制接口与按钮：没有勾选的权限，前端不会显示对应按钮，后端也会拒绝请求。</div>
            <div class="module-list">
              <div v-for="group in groupedPermissions" :key="group.module" class="module-card">
                <div class="module-head">
                  <div class="module-name">{{ group.module }}</div>
                  <el-checkbox
                    :model-value="moduleState(group.module).all"
                    :indeterminate="moduleState(group.module).some"
                    :disabled="readonly"
                    @change="(value) => toggleModule(group.module, value)"
                  >
                    全选
                  </el-checkbox>
                </div>
                <el-checkbox-group v-model="checkedPerms" :disabled="readonly" class="perm-grid">
                  <el-checkbox v-for="item in group.items" :key="item.code" :value="item.code">
                    {{ item.name }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>
            </div>
            <div class="save-bar">
              <el-button type="primary" :disabled="readonly" :loading="savingPerm" @click="savePermissions">
                保存功能权限
              </el-button>
            </div>
          </el-tab-pane>

          <el-tab-pane label="菜单权限" name="menus">
            <div class="tab-tip">
              控制侧边栏可见范围；勾选页面菜单会自动补齐对应页面权限。取消勾选只影响可见性，不会删除功能权限。
            </div>
            <el-tree
              ref="menuTreeRef"
              :data="menuTree"
              node-key="id"
              show-checkbox
              default-expand-all
              :props="{ label: 'name', children: 'children' }"
              class="menu-tree"
            >
              <template #default="{ data }">
                <span class="tree-node">
                  <span>{{ data.name }}</span>
                  <span v-if="data.permission" class="tree-perm mono">{{ data.permission }}</span>
                </span>
              </template>
            </el-tree>
            <div class="save-bar">
              <el-button type="primary" :disabled="readonly" :loading="savingMenu" @click="saveMenus">
                保存菜单权限
              </el-button>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <div v-else class="card empty-role">
        <div class="empty-block">请选择左侧角色查看权限</div>
      </div>
    </div>

    <el-dialog v-model="createDialog.visible" title="新建角色" width="480px">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="createForm.name" maxlength="32" placeholder="例如：仓库主管" />
        </el-form-item>
        <el-form-item label="角色标识" prop="code">
          <el-input v-model="createForm.code" maxlength="20" placeholder="小写字母，例如：manager" />
        </el-form-item>
        <el-form-item label="角色说明">
          <el-input v-model="createForm.description" type="textarea" :rows="2" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="createDialog.saving" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialog.visible" title="编辑角色资料" width="480px">
      <el-form :model="editForm" label-width="90px">
        <el-form-item label="角色名称">
          <el-input v-model="editForm.name" maxlength="32" />
        </el-form-item>
        <el-form-item label="角色说明">
          <el-input v-model="editForm.description" type="textarea" :rows="2" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="editDialog.saving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.role-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.role-list {
  overflow: hidden;
}

.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 16px;
  border-bottom: 1px solid var(--line);
  font-weight: 600;
  font-size: 14px;
}

.roles {
  padding: 8px;
  display: grid;
  gap: 4px;
}

.role-item {
  text-align: left;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 10px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.role-item:hover {
  background: #f7faff;
}

.role-item.active {
  background: #f0f7ff;
  border-color: #c9dfff;
  box-shadow: inset 3px 0 0 var(--brand);
}

.role-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.role-name {
  font-weight: 600;
  color: var(--ink);
  font-size: 14px;
}

.role-code {
  margin-top: 3px;
  color: #94a3b8;
  font-size: 11px;
}

.role-meta {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  font-size: 11px;
  color: var(--muted);
}

.role-detail {
  min-height: 520px;
}

.detail-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 20px;
  border-bottom: 1px solid var(--line);
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
}

.detail-desc {
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
}

.detail-meta {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  color: #94a3b8;
  font-size: 11px;
  flex-wrap: wrap;
}

.detail-actions {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.readonly-alert {
  margin: 16px 20px 0;
  border-radius: 10px;
}

.role-tabs {
  padding: 0 20px 20px;
}

.tab-tip {
  margin: 4px 0 16px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.8;
}

.module-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.module-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px 16px;
  background: #fbfdff;
}

.module-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.module-name {
  font-weight: 600;
  font-size: 13px;
  color: var(--ink);
}

.perm-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 10px;
}

.perm-grid :deep(.el-checkbox) {
  margin-right: 0;
  height: 26px;
}

.menu-tree {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px;
  max-height: 460px;
  overflow: auto;
}

.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 10px;
}

.tree-perm {
  color: #94a3b8;
  font-size: 11px;
}

.save-bar {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
}

.empty-role {
  min-height: 320px;
  display: grid;
  place-items: center;
}

@media (max-width: 1180px) {
  .role-layout {
    grid-template-columns: 1fr;
  }
  .module-list {
    grid-template-columns: 1fr;
  }
}
</style>
