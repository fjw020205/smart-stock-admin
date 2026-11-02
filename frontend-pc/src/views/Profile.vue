<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { formatDateTime, initials } from '../utils/format'

const auth = useAuthStore()
const router = useRouter()

const permissions = computed(() => auth.permissions || [])
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2>个人中心</h2>
        <p class="sub">查看账号信息与权限范围</p>
      </div>
      <div class="actions">
        <el-button type="primary" @click="router.push('/change-password')">修改密码</el-button>
      </div>
    </div>

    <div class="profile-grid">
      <div class="card">
        <div class="cover">
          <div class="avatar">{{ initials(auth.user?.real_name) }}</div>
        </div>
        <div class="info">
          <h3>{{ auth.user?.real_name }}</h3>
          <div class="account">@{{ auth.user?.username }}</div>
          <el-tag :type="auth.isAdmin ? 'danger' : 'primary'" effect="light" size="small">
            {{ auth.user?.role?.name }}
          </el-tag>

          <el-divider />

          <div class="field">
            <span>手机号</span>
            <b>{{ auth.user?.phone || '-' }}</b>
          </div>
          <div class="field">
            <span>最后登录</span>
            <b>{{ auth.user?.last_login_at || '-' }}</b>
          </div>
          <div class="field">
            <span>创建时间</span>
            <b>{{ formatDateTime(auth.user?.created_at) }}</b>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-head">
          <div class="card-title">当前拥有的功能权限</div>
          <el-tag size="small" effect="plain">{{ permissions.length }} 项</el-tag>
        </div>
        <div class="perm-body">
          <div v-if="auth.isAdmin" class="admin-note">
            <el-icon><Star /></el-icon>
            超级管理员拥有系统全部权限
          </div>
          <div class="perm-list">
            <el-tag v-for="code in permissions" :key="code" size="small" effect="plain" class="perm-tag">
              {{ code }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-grid {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.cover {
  height: 96px;
  background:
    radial-gradient(320px 180px at 10% 0%, rgba(22, 119, 255, 0.55), transparent 70%),
    linear-gradient(135deg, #0b1b33, #123a6b);
  position: relative;
}

.avatar {
  position: absolute;
  left: 24px;
  bottom: -28px;
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: linear-gradient(135deg, #1677ff, #5ca9ff);
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  display: grid;
  place-items: center;
  border: 3px solid #fff;
  box-shadow: 0 10px 24px -12px rgba(15, 23, 42, 0.5);
}

.info {
  padding: 40px 24px 24px;
}

.info h3 {
  font-size: 19px;
  font-weight: 700;
}

.account {
  margin: 4px 0 10px;
  color: var(--muted);
  font-size: 12px;
}

.field {
  display: flex;
  justify-content: space-between;
  padding: 9px 0;
  font-size: 13px;
}

.field span {
  color: var(--muted);
}

.field b {
  color: var(--ink);
  font-weight: 500;
}

.perm-body {
  padding: 18px 20px 24px;
}

.admin-note {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fff7ed;
  color: #b45309;
  font-size: 12px;
  margin-bottom: 14px;
}

.perm-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.perm-tag {
  font-family: Consolas, monospace;
  font-size: 11px;
}

@media (max-width: 980px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
}
</style>
