<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showSuccessToast, showToast } from 'vant'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const loading = ref(false)
const showPassword = ref(false)
const form = reactive({ username: '', password: '' })

onMounted(() => {
  form.username = localStorage.getItem('ss_remember_m') || ''
})

function fill(username, password) {
  form.username = username
  form.password = password
}

async function submit() {
  if (!form.username.trim() || !form.password) {
    showToast('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    const data = await auth.login({
      username: form.username.trim(),
      password: form.password
    })
    localStorage.setItem('ss_remember_m', form.username.trim())
    if (data.user.must_change_password) {
      showToast('请先修改初始密码')
      router.replace('/change-password')
      return
    }
    showSuccessToast(`欢迎回来，${data.user.real_name}`)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/home'
    router.replace(redirect)
  } catch (error) {
    /* 已提示 */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login">
    <div class="hero">
      <div class="hero-glow" />
      <div class="brand">
        <div class="mark">仓</div>
        <div class="brand-text">
          <strong>智仓</strong>
          <span>SMART STOCK</span>
        </div>
      </div>
      <h1>库存管理<br />装进口袋</h1>
      <p class="lead">查库存、办出入库、看预警，手机随时处理</p>
    </div>

    <section class="panel">
      <div class="panel-head">
        <h2>账号登录</h2>
        <span class="muted">电脑端与手机端账号通用</span>
      </div>

      <van-form @submit="submit">
        <div class="field">
          <span class="field-label">账号</span>
          <van-field
            v-model="form.username"
            name="username"
            placeholder="请输入登录账号"
            left-icon="user-o"
            clearable
            autocomplete="username"
            :rules="[{ required: true, message: '请输入账号' }]"
          />
        </div>

        <div class="field">
          <span class="field-label">密码</span>
          <van-field
            v-model="form.password"
            name="password"
            :type="showPassword ? 'text' : 'password'"
            placeholder="请输入登录密码"
            left-icon="lock"
            autocomplete="current-password"
            :right-icon="showPassword ? 'eye-o' : 'closed-eye'"
            :rules="[{ required: true, message: '请输入密码' }]"
            @click-right-icon="showPassword = !showPassword"
          />
        </div>

        <van-button
          block
          round
          type="primary"
          native-type="submit"
          :loading="loading"
          loading-text="登录中…"
          class="submit"
        >
          登 录
        </van-button>
      </van-form>

      <div class="demo">
        <div class="demo-title">演示账号 · 点击填充</div>
        <div class="demo-chips">
          <button type="button" @click="fill('admin', 'Admin@123456')">管理员</button>
          <button type="button" @click="fill('staff', 'Staff@123456')">普通员工</button>
        </div>
        <p class="demo-tip">首次使用管理员账号需修改初始密码</p>
      </div>
    </section>

    <footer class="foot">
      <span>电脑端访问：同一地址打开 /pc/</span>
      <span class="ver">v1.0.0</span>
    </footer>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  min-height: 100dvh;
  background: #f5f7fa;
  display: flex;
  flex-direction: column;
  max-width: 640px;
  margin: 0 auto;
}

.hero {
  position: relative;
  overflow: hidden;
  padding: calc(38px + env(safe-area-inset-top)) 26px 64px;
  color: #fff;
  background:
    radial-gradient(420px 300px at 10% -10%, rgba(22, 119, 255, 0.55), transparent 65%),
    linear-gradient(165deg, #071527 0%, #0b1b33 55%, #123a6b 100%);
  border-radius: 0 0 28px 28px;
}

.hero-glow {
  position: absolute;
  right: -90px;
  top: -90px;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  border: 1px solid rgba(120, 180, 255, 0.25);
  box-shadow: 0 0 0 50px rgba(22, 119, 255, 0.06), 0 0 0 100px rgba(22, 119, 255, 0.04);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mark {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: linear-gradient(135deg, #1677ff, #4da3ff);
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 16px;
  box-shadow: 0 10px 22px -8px rgba(22, 119, 255, 0.9);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-text strong {
  font-size: 17px;
  letter-spacing: 2px;
}

.brand-text span {
  font-size: 9px;
  letter-spacing: 2px;
  color: #7f9cc0;
  margin-top: 3px;
}

.hero h1 {
  margin: 38px 0 0;
  font-size: 32px;
  line-height: 1.3;
  font-weight: 700;
  letter-spacing: 1px;
}

.lead {
  margin: 14px 0 0;
  color: #9db4d1;
  font-size: 13px;
  line-height: 1.7;
}

.panel {
  flex: 1;
  margin: -38px 16px 0;
  position: relative;
  z-index: 2;
  background: #fff;
  border-radius: 22px;
  padding: 24px 20px;
  box-shadow: 0 18px 40px -28px rgba(15, 23, 42, 0.5);
}

.panel-head {
  margin-bottom: 20px;
}

.panel-head h2 {
  font-size: 20px;
  font-weight: 700;
}

.panel-head span {
  display: block;
  margin-top: 6px;
  font-size: 12px;
}

.field {
  margin-bottom: 14px;
  background: #f6f8fb;
  border-radius: 12px;
  padding: 8px 12px 2px;
}

.field-label {
  font-size: 11px;
  color: #64748b;
  padding-left: 2px;
}

.field :deep(.van-field) {
  padding: 4px 0 8px;
  background: transparent;
}

.field :deep(.van-field__left-icon) {
  margin-right: 8px;
  color: #94a3b8;
}

.field :deep(.van-field__control) {
  font-size: 15px;
}

.field :deep(.van-cell::after) {
  display: none;
}

.submit {
  margin-top: 20px;
  height: 48px;
  font-size: 16px;
  letter-spacing: 3px;
  box-shadow: 0 12px 24px -12px rgba(22, 119, 255, 0.7);
}

.demo {
  margin-top: 22px;
  padding: 14px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px dashed #dbe5f1;
}

.demo-title {
  font-size: 11px;
  color: #64748b;
  margin-bottom: 10px;
}

.demo-chips {
  display: flex;
  gap: 8px;
}

.demo-chips button {
  flex: 1;
  border: 1px solid #dbe5f1;
  background: #fff;
  border-radius: 9px;
  padding: 9px 0;
  font-size: 12px;
  color: #334155;
}

.demo-chips button:active {
  background: #eff6ff;
  color: #1677ff;
}

.demo-tip {
  margin: 10px 0 0;
  font-size: 10px;
  color: #94a3b8;
  line-height: 1.7;
}

.foot {
  display: flex;
  justify-content: space-between;
  padding: 18px 22px calc(18px + env(safe-area-inset-bottom));
  font-size: 10px;
  color: #94a3b8;
}

.ver {
  font-variant-numeric: tabular-nums;
}
</style>
