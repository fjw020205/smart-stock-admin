<script setup>
import { useRouter } from 'vue-router'
import { showConfirmDialog, showDialog, showSuccessToast, showToast } from 'vant'
import { useAuthStore } from '../stores/auth'
import { can } from '../utils/permission'
import { initials } from '../utils/format'

const router = useRouter()
const auth = useAuthStore()

async function logout() {
  try {
    await showConfirmDialog({
      title: '退出登录',
      message: '确定要退出当前账号吗？',
      confirmButtonText: '退出',
      cancelButtonText: '取消'
    })
  } catch (error) {
    return
  }
  await auth.logout()
  showToast('已退出登录')
  router.replace('/login')
}

function about() {
  showDialog({
    title: '关于智仓',
    message:
      '智仓 · 库存管理后台 v1.0.0\n\n数据保存在本机 data/app.db，无需服务器与外部数据库。\n手机与电脑在同一局域网即可同时使用。'
  })
}
</script>

<template>
  <div class="mine">
    <header class="header">
      <div class="glow" />
      <div class="avatar">{{ initials(auth.user?.real_name) }}</div>
      <div class="name">{{ auth.user?.real_name }}</div>
      <div class="sub">@{{ auth.user?.username }} · {{ auth.user?.role?.name }}</div>
      <div class="badges">
        <span class="badge">手机端</span>
        <span v-if="auth.isAdmin" class="badge admin">管理员</span>
        <span v-else class="badge">员工</span>
      </div>
    </header>

    <div class="page-pad">
      <div class="card cells">
        <van-cell
          v-if="can('user:view')"
          title="用户管理"
          icon="friends-o"
          is-link
          @click="router.push('/users')"
        />
        <van-cell
          title="修改密码"
          icon="lock"
          is-link
          @click="router.push('/change-password')"
        />
        <van-cell title="关于智仓" icon="info-o" is-link @click="about" />
      </div>

      <div class="card cells">
        <van-cell title="数据存储" value="本机 SQLite" />
        <van-cell title="登录账号" :value="auth.user?.username" />
        <van-cell title="当前版本" value="v1.0.0" />
      </div>

      <van-button class="logout" block round plain type="danger" @click="logout">
        退出登录
      </van-button>

      <div class="copy">© 2026 智仓 · 库存管理</div>
    </div>
  </div>
</template>

<style scoped>
.mine {
  min-height: 100vh;
  background: var(--bg);
}

.header {
  position: relative;
  overflow: hidden;
  padding: calc(34px + env(safe-area-inset-top)) 20px 32px;
  color: #fff;
  background:
    radial-gradient(320px 220px at 88% -10%, rgba(22, 119, 255, 0.55), transparent 65%),
    linear-gradient(160deg, #0b1b33 0%, #123a6b 100%);
  border-radius: 0 0 26px 26px;
  text-align: center;
}

.glow {
  position: absolute;
  right: -70px;
  top: -80px;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  border: 1px solid rgba(120, 180, 255, 0.2);
  box-shadow: 0 0 0 40px rgba(22, 119, 255, 0.05);
}

.avatar {
  width: 64px;
  height: 64px;
  margin: 0 auto;
  border-radius: 50%;
  background: linear-gradient(135deg, #4da3ff, #1677ff);
  display: grid;
  place-items: center;
  font-size: 24px;
  font-weight: 700;
  border: 3px solid rgba(255, 255, 255, 0.3);
  position: relative;
  z-index: 1;
}

.name {
  margin-top: 12px;
  font-size: 19px;
  font-weight: 700;
  position: relative;
  z-index: 1;
}

.sub {
  margin-top: 5px;
  font-size: 11px;
  color: #9db4d1;
}

.badges {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 12px;
}

.badge {
  font-size: 10px;
  padding: 3px 9px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.12);
  color: #d7e6fb;
}

.badge.admin {
  background: rgba(22, 119, 255, 0.35);
  color: #cfe4ff;
}

.page-pad {
  padding: 14px 14px 24px;
}

.cells {
  padding: 4px 4px;
  margin-bottom: 12px;
}

.cells :deep(.van-cell) {
  border-radius: 10px;
}

.cells :deep(.van-cell__left-icon) {
  color: #64748b;
}

.cells :deep(.van-cell::after) {
  left: 16px;
  right: 16px;
}

.logout {
  margin-top: 8px;
  height: 46px;
}

.copy {
  margin-top: 22px;
  text-align: center;
  font-size: 10px;
  color: #94a3b8;
}
</style>
