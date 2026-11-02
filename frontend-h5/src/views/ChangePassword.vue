<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showSuccessToast, showToast } from 'vant'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(false)
const form = reactive({ old_password: '', new_password: '', confirm: '' })

async function submit() {
  if (!form.old_password) {
    showToast('请输入原密码')
    return
  }
  if (!/^(?=.*[A-Za-z])(?=.*\d).{8,20}$/.test(form.new_password)) {
    showToast('新密码需 8-20 位，且包含字母和数字')
    return
  }
  if (form.new_password !== form.confirm) {
    showToast('两次输入的密码不一致')
    return
  }
  loading.value = true
  try {
    await auth.changePassword({
      old_password: form.old_password,
      new_password: form.new_password
    })
    showSuccessToast('密码修改成功')
    router.replace('/home')
  } catch (error) {
    /* 已提示 */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="pwd">
    <van-nav-bar
      title="修改密码"
      :left-arrow="!auth.mustChangePassword"
      fixed
      placeholder
      @click-left="router.back()"
    />

    <div class="body">
      <div class="banner">
        <div class="banner-icon">
          <van-icon name="shield-o" size="24" />
        </div>
        <div>
          <div class="banner-title">
            {{ auth.mustChangePassword ? '请设置新的登录密码' : '定期更换密码更安全' }}
          </div>
          <div class="banner-sub">
            {{ auth.mustChangePassword ? '首次登录必须修改初始密码后才能继续使用' : '建议 3 个月更换一次密码' }}
          </div>
        </div>
      </div>

      <div class="card form">
        <van-field
          v-model="form.old_password"
          type="password"
          label="原密码"
          placeholder="请输入原密码"
          autocomplete="current-password"
        />
        <van-field
          v-model="form.new_password"
          type="password"
          label="新密码"
          placeholder="8-20 位，字母 + 数字"
          autocomplete="new-password"
        />
        <van-field
          v-model="form.confirm"
          type="password"
          label="确认密码"
          placeholder="请再次输入新密码"
          autocomplete="new-password"
        />
      </div>

      <van-button block round type="primary" :loading="loading" class="submit" @click="submit">
        确认修改
      </van-button>

      <p class="tip">修改成功后，其他设备上的登录状态会自动失效</p>
    </div>
  </div>
</template>

<style scoped>
.pwd {
  min-height: 100vh;
  background: var(--bg);
}

.body {
  padding: 14px;
}

.banner {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, #0b1b33, #144a8f);
  color: #fff;
}

.banner-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.14);
  display: grid;
  place-items: center;
  flex: 0 0 42px;
}

.banner-title {
  font-size: 15px;
  font-weight: 600;
}

.banner-sub {
  margin-top: 5px;
  font-size: 11px;
  color: #a9c1e2;
  line-height: 1.6;
}

.form {
  margin-top: 12px;
  padding: 4px 4px;
}

.form :deep(.van-cell) {
  padding: 14px 12px;
}

.form :deep(.van-field__label) {
  width: 74px;
  color: var(--muted);
}

.submit {
  margin-top: 18px;
  height: 48px;
}

.tip {
  margin-top: 14px;
  text-align: center;
  font-size: 10px;
  color: #94a3b8;
}
</style>
