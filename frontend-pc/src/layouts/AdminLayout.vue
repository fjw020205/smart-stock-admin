<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { resolveIcon } from '../utils/icons'
import { initials, todayLabel } from '../utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const collapsed = ref(localStorage.getItem('ss_sidebar') === '1')
const narrow = ref(false)

const menus = computed(() => auth.menus || [])
const activePath = computed(() => route.path)
const today = todayLabel()

function toggleSidebar() {
  collapsed.value = !collapsed.value
  if (!narrow.value) localStorage.setItem('ss_sidebar', collapsed.value ? '1' : '0')
}

function handleResize() {
  narrow.value = window.innerWidth < 1180
  if (narrow.value) collapsed.value = true
}

onMounted(() => {
  handleResize()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => window.removeEventListener('resize', handleResize))

async function onCommand(command) {
  if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'password') {
    router.push('/change-password')
  } else if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '退出登录', {
        confirmButtonText: '退出',
        cancelButtonText: '取消',
        type: 'warning'
      })
    } catch (error) {
      return
    }
    await auth.logout()
    ElMessage.success('已退出登录')
    router.replace('/login')
  }
}
</script>

<template>
  <div class="admin" :class="{ collapsed }">
    <aside class="sidebar" :class="{ narrow }">
      <div class="brand">
        <div class="mark">仓</div>
        <div v-show="!collapsed" class="brand-text">
          <strong>智仓</strong>
          <span>库存管理后台</span>
        </div>
      </div>

      <el-scrollbar class="menu-scroll">
        <el-menu
          :default-active="activePath"
          :collapse="collapsed"
          :collapse-transition="false"
          unique-opened
          router
          class="side-menu"
        >
          <template v-for="item in menus" :key="item.id">
            <el-sub-menu v-if="item.children && item.children.length" :index="item.path">
              <template #title>
                <el-icon><component :is="resolveIcon(item.icon)" /></el-icon>
                <span>{{ item.name }}</span>
              </template>
              <el-menu-item
                v-for="child in item.children"
                :key="child.id"
                :index="child.path"
              >
                <el-icon><component :is="resolveIcon(child.icon)" /></el-icon>
                <template #title>{{ child.name }}</template>
              </el-menu-item>
            </el-sub-menu>

            <el-menu-item v-else :index="item.path">
              <el-icon><component :is="resolveIcon(item.icon)" /></el-icon>
              <template #title>{{ item.name }}</template>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>

      <div v-show="!collapsed" class="side-foot">
        <div class="version">v1.0.0</div>
        <div class="copy">© 2026 智仓</div>
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <button class="icon-btn" type="button" :title="collapsed ? '展开菜单' : '收起菜单'" @click="toggleSidebar">
          <el-icon :size="18"><component :is="collapsed ? 'Expand' : 'Fold'" /></el-icon>
        </button>
        <div class="crumb">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>智仓</el-breadcrumb-item>
            <el-breadcrumb-item>{{ route.meta.title || '工作台' }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="spacer" />
        <div class="today">{{ today }}</div>
        <el-dropdown trigger="click" @command="onCommand">
          <div class="user">
            <div class="avatar">{{ initials(auth.user?.real_name) }}</div>
            <div class="meta">
              <strong>{{ auth.user?.real_name || '-' }}</strong>
              <span>{{ auth.user?.role?.name || '' }}</span>
            </div>
            <el-icon class="caret"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon> 个人中心
              </el-dropdown-item>
              <el-dropdown-item command="password">
                <el-icon><Key /></el-icon> 修改密码
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon> 退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>

      <main class="content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg);
}

.sidebar {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 224px;
  flex: 0 0 auto;
  background:
    radial-gradient(420px 220px at 0% 0%, rgba(22, 119, 255, 0.28), transparent 65%),
    linear-gradient(180deg, #0b1b33 0%, #0a1628 100%);
  transition: width 0.22s ease;
  z-index: 20;
}

.admin.collapsed .sidebar {
  width: 72px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 64px;
  padding: 0 18px;
  flex: 0 0 auto;
  overflow: hidden;
}

.mark {
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #1677ff, #3aa0ff);
  color: #fff;
  font-weight: 700;
  font-size: 16px;
  display: grid;
  place-items: center;
  box-shadow: 0 8px 20px -6px rgba(22, 119, 255, 0.8);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  white-space: nowrap;
}

.brand-text strong {
  color: #fff;
  font-size: 17px;
  letter-spacing: 2px;
}

.brand-text span {
  color: #7f96b5;
  font-size: 11px;
  letter-spacing: 0.5px;
  margin-top: 4px;
}

.menu-scroll {
  flex: 1;
  padding: 6px 10px 10px;
}

.side-menu {
  border-right: none;
  background: transparent;
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.06);
  --el-menu-text-color: #a9bcd6;
  --el-menu-active-color: #ffffff;
  --el-menu-item-height: 44px;
  --el-menu-sub-item-height: 40px;
}

.side-menu :deep(.el-menu-item),
.side-menu :deep(.el-sub-menu__title) {
  border-radius: 8px;
  margin: 2px 0;
}

.side-menu :deep(.el-menu-item:hover),
.side-menu :deep(.el-sub-menu__title:hover) {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.side-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(22, 119, 255, 0.95), rgba(22, 119, 255, 0.72));
  color: #fff;
  box-shadow: 0 8px 18px -10px rgba(22, 119, 255, 0.9);
}

.side-menu :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: #fff;
}

.side-menu :deep(.el-menu--inline) {
  background: transparent;
}

.side-foot {
  padding: 14px 18px 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.side-foot .version {
  color: #b7c7dd;
  font-size: 12px;
}

.side-foot .copy {
  color: #5f7694;
  font-size: 11px;
  margin-top: 4px;
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.topbar {
  height: 60px;
  flex: 0 0 60px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid var(--line);
}

.icon-btn {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: #fff;
  color: #475569;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.icon-btn:hover {
  color: var(--brand);
  border-color: #bfd8ff;
  background: var(--brand-50);
}

.spacer {
  flex: 1;
}

.today {
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
}

.user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 8px 5px 5px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.user:hover {
  background: #f4f7fb;
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
  font-size: 14px;
}

.meta {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.meta strong {
  font-size: 13px;
  color: var(--ink);
}

.meta span {
  font-size: 11px;
  color: var(--muted);
}

.caret {
  color: #94a3b8;
  font-size: 12px;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 22px 28px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(4px);
}

.fade-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .sidebar {
    width: 72px;
  }
  .brand-text,
  .side-foot {
    display: none;
  }
  .content {
    padding: 14px;
  }
  .today {
    display: none;
  }
}
</style>
