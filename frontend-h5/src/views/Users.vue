<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showSuccessToast, showToast } from 'vant'
import { userApi } from '../api'
import { initials } from '../utils/format'

const router = useRouter()

const keyword = ref('')
const items = ref([])
const loading = ref(false)
const finished = ref(false)
const page = ref(1)
const firstLoaded = ref(false)

const resetSaving = ref(false)
const resetPopupVisible = ref(false)
const resetUser = ref(null)
const resetPassword = ref('')

async function fetchPage(reset = false) {
  if (reset) {
    page.value = 1
    items.value = []
    finished.value = false
  }
  loading.value = true
  try {
    const params = { page: page.value, page_size: 15 }
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    const response = await userApi.list(params)
    items.value = reset ? response.data.items : [...items.value, ...response.data.items]
    page.value += 1
    finished.value = items.value.length >= response.data.total
    firstLoaded.value = true
  } catch (error) {
    finished.value = true
  } finally {
    loading.value = false
  }
}

function reset() {
  fetchPage(true)
}

async function toggleStatus(item) {
  try {
    await userApi.toggle(item.id, item.status)
    showSuccessToast(item.status ? '已启用' : '已停用')
  } catch (error) {
    item.status = !item.status
  }
}

function openReset(item) {
  resetUser.value = item
  resetPassword.value = ''
  resetPopupVisible.value = true
}

async function submitReset() {
  if (!/^(?=.*[A-Za-z])(?=.*\d).{8,20}$/.test(resetPassword.value)) {
    showToast('密码需 8-20 位，且包含字母和数字')
    return
  }
  resetSaving.value = true
  try {
    await userApi.resetPassword(resetUser.value.id, { new_password: resetPassword.value })
    showSuccessToast('密码已重置')
    resetPopupVisible.value = false
  } catch (error) {
    /* 已提示 */
  } finally {
    resetSaving.value = false
  }
}

onMounted(reset)
</script>

<template>
  <div class="users">
    <van-nav-bar title="用户管理" left-arrow fixed placeholder @click-left="router.back()" />

    <div class="search-bar">
      <van-search
        v-model="keyword"
        placeholder="搜索姓名 / 账号"
        shape="round"
        background="transparent"
        @search="reset"
        @clear="reset"
      />
    </div>

    <van-list
      v-model:loading="loading"
      :finished="finished"
      finished-text="没有更多用户了"
      :immediate-check="false"
      @load="fetchPage(false)"
    >
      <div class="list">
        <div v-for="item in items" :key="item.id" class="user-card">
          <div class="avatar">{{ initials(item.real_name) }}</div>
          <div class="user-main">
            <div class="user-name">
              {{ item.real_name }}
              <span v-if="item.is_self" class="pill blue">我</span>
              <span v-if="item.protected" class="pill orange">内置</span>
            </div>
            <div class="user-meta">@{{ item.username }} · {{ item.role?.name }}</div>
            <div class="user-meta">{{ item.phone || '未填写手机号' }}</div>
          </div>
          <div class="user-side">
            <van-switch
              v-model="item.status"
              size="20"
              :disabled="item.is_self || item.protected"
              @change="toggleStatus(item)"
            />
            <button type="button" class="reset-btn" @click="openReset(item)">重置密码</button>
          </div>
        </div>
      </div>
    </van-list>

    <van-empty
      v-if="firstLoaded && !items.length && !loading"
      description="没有找到用户"
      :image-size="80"
    />

    <van-popup v-model:show="resetPopupVisible" position="bottom" round>
      <div class="reset-popup">
        <div class="popup-title">重置密码</div>
        <p class="popup-tip">
          为「{{ resetUser?.real_name }}」设置新密码，该用户下次登录需要修改密码。
        </p>
        <van-field
          v-model="resetPassword"
          type="password"
          placeholder="8-20 位，包含字母和数字"
          class="popup-field"
        />
        <van-button block round type="primary" :loading="resetSaving" @click="submitReset">
          确认重置
        </van-button>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.users {
  min-height: 100vh;
  background: var(--bg);
}

.search-bar {
  position: sticky;
  top: 46px;
  z-index: 9;
  background: #fff;
  padding: 4px 6px 8px;
  border-bottom: 1px solid var(--line);
}

.search-bar :deep(.van-search__content) {
  background: #f4f7fb;
}

.list {
  padding: 12px 14px 0;
  display: grid;
  gap: 10px;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 11px;
  background: #fff;
  border-radius: 14px;
  padding: 13px 14px;
}

.avatar {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1677ff, #5ca9ff);
  color: #fff;
  font-weight: 700;
  display: grid;
  place-items: center;
  font-size: 15px;
}

.user-main {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.user-meta {
  margin-top: 3px;
  font-size: 10px;
  color: var(--muted);
}

.user-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.reset-btn {
  border: none;
  background: transparent;
  color: #1677ff;
  font-size: 11px;
  padding: 0;
}

.reset-popup {
  padding: 20px 20px calc(20px + env(safe-area-inset-bottom));
}

.popup-title {
  font-size: 17px;
  font-weight: 700;
}

.popup-tip {
  margin: 8px 0 16px;
  font-size: 11px;
  color: var(--muted);
  line-height: 1.7;
}

.popup-field {
  background: #f6f8fb;
  border-radius: 10px;
  margin-bottom: 16px;
}
</style>
