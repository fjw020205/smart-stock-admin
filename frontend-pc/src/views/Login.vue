<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref(null)
const loading = ref(false)
const remember = ref(true)
const form = reactive({ username: '', password: '' })

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

onMounted(() => {
  const saved = localStorage.getItem('ss_remember_user')
  if (saved) {
    form.username = saved
    remember.value = true
  }
})

function fill(username, password) {
  form.username = username
  form.password = password
}

async function submit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch (error) {
    return
  }
  loading.value = true
  try {
    const data = await auth.login({ username: form.username.trim(), password: form.password })
    if (remember.value) {
      localStorage.setItem('ss_remember_user', form.username.trim())
    } else {
      localStorage.removeItem('ss_remember_user')
    }
    if (data.user.must_change_password) {
      ElMessage.warning('首次登录，请先修改初始密码')
      router.replace('/change-password')
      return
    }
    ElMessage.success(`欢迎回来，${data.user.real_name}`)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    router.replace(redirect)
  } catch (error) {
    /* 错误提示由 http 拦截器统一处理 */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login">
    <section class="brand">
      <div class="grid" aria-hidden="true" />
      <div class="glow" aria-hidden="true" />
      <div class="brand-inner">
        <div class="logo-row">
          <div class="mark">仓</div>
          <div class="name">
            <strong>智仓</strong>
            <span>SMART STOCK</span>
          </div>
        </div>

        <h1>让每一件库存<br />都清清楚楚</h1>
        <p class="lead">商品、出入库、权限与看板，一套系统管到底。无需服务器，双击即用。</p>

        <ul class="points">
          <li><span class="dot" /> 出入库实时扣减，库存永远对得上</li>
          <li><span class="dot" /> 低于安全库存自动预警，不再断货</li>
          <li><span class="dot" /> 管理员与员工分权，操作全程留痕</li>
        </ul>

        <div class="metrics">
          <div><b>7×24</b><span>本地运行</span></div>
          <div><b>0</b><span>额外安装</span></div>
          <div><b>双端</b><span>电脑 + 手机</span></div>
        </div>
      </div>
      <footer class="brand-foot">© 2026 智仓 · 库存管理后台 v1.0.0</footer>
    </section>

    <section class="panel">
      <div class="form-wrap">
        <div class="mobile-brand">
          <div class="mark">仓</div>
          <span>智仓 · 库存管理后台</span>
        </div>

        <h2>欢迎回来</h2>
        <p class="sub">登录后进入库存管理工作台</p>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
          <el-form-item label="账号" prop="username">
            <el-input
              v-model="form.username"
              size="large"
              placeholder="请输入账号"
              autocomplete="username"
              :prefix-icon="'User'"
              clearable
            />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              size="large"
              type="password"
              placeholder="请输入密码"
              autocomplete="current-password"
              :prefix-icon="'Lock'"
              show-password
              @keyup.enter="submit"
            />
          </el-form-item>

          <div class="row">
            <el-checkbox v-model="remember">记住账号</el-checkbox>
            <span class="muted">忘记密码请联系管理员重置</span>
          </div>

          <el-button class="submit" type="primary" size="large" :loading="loading" @click="submit">
            {{ loading ? '登录中…' : '登 录' }}
          </el-button>
        </el-form>

        <div class="demo">
          <div class="demo-title">演示账号 · 点击填充</div>
          <div class="chips">
            <button type="button" @click="fill('admin', 'Admin@123456')">
              管理员 admin
            </button>
            <button type="button" @click="fill('staff', 'Staff@123456')">
              普通员工 staff
            </button>
          </div>
          <p class="tip">首次使用管理员账号会要求修改初始密码</p>
        </div>

        <div class="mobile-foot">© 2026 智仓 · 库存管理后台</div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  min-height: 100vh;
  background: #fff;
}

.brand {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 48px 56px;
  color: #fff;
  background:
    radial-gradient(760px 520px at 8% 0%, rgba(22, 119, 255, 0.5), transparent 60%),
    radial-gradient(640px 480px at 95% 100%, rgba(13, 202, 240, 0.18), transparent 60%),
    linear-gradient(150deg, #071527 0%, #0b1b33 52%, #0a1f3d 100%);
}

.grid {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.045) 1px, transparent 1px);
  background-size: 54px 54px;
  mask-image: radial-gradient(circle at 40% 35%, #000 0%, transparent 78%);
}

.glow {
  position: absolute;
  width: 520px;
  height: 520px;
  right: -180px;
  top: -160px;
  border-radius: 50%;
  border: 1px solid rgba(90, 170, 255, 0.25);
  box-shadow: 0 0 0 80px rgba(22, 119, 255, 0.04), 0 0 0 160px rgba(22, 119, 255, 0.03);
}

.brand-inner {
  position: relative;
  z-index: 1;
  max-width: 540px;
}

.logo-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 64px;
}

.mark {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: linear-gradient(135deg, #1677ff, #4da3ff);
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 18px;
  box-shadow: 0 14px 30px -10px rgba(22, 119, 255, 0.9);
}

.name {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.name strong {
  font-size: 18px;
  letter-spacing: 3px;
}

.name span {
  font-size: 10px;
  color: #6f8db3;
  letter-spacing: 2px;
  margin-top: 3px;
}

h1 {
  font-size: 42px;
  line-height: 1.25;
  font-weight: 700;
  letter-spacing: 1px;
}

.lead {
  margin-top: 20px;
  color: #9fb5d1;
  font-size: 14px;
  line-height: 1.9;
  max-width: 420px;
}

.points {
  list-style: none;
  padding: 0;
  margin: 36px 0 0;
  display: grid;
  gap: 14px;
}

.points li {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #c6d7ec;
  font-size: 13px;
}

.points .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #4da3ff;
  box-shadow: 0 0 0 4px rgba(77, 163, 255, 0.14);
}

.metrics {
  display: flex;
  gap: 48px;
  margin-top: 54px;
  padding-top: 26px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.metrics div {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.metrics b {
  font-size: 22px;
  letter-spacing: 1px;
}

.metrics span {
  color: #7e98b8;
  font-size: 12px;
}

.brand-foot {
  position: relative;
  z-index: 1;
  color: #5d7799;
  font-size: 12px;
}

.panel {
  display: grid;
  place-items: center;
  padding: 40px 24px;
  background: #fff;
}

.form-wrap {
  width: 100%;
  max-width: 360px;
}

.mobile-brand {
  display: none;
  align-items: center;
  gap: 10px;
  margin-bottom: 28px;
  color: var(--ink);
  font-weight: 600;
  font-size: 14px;
}

.mobile-brand .mark {
  width: 34px;
  height: 34px;
  font-size: 15px;
  border-radius: 9px;
}

h2 {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.sub {
  margin: 8px 0 30px;
  color: var(--muted);
  font-size: 13px;
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 2px 0 22px;
  font-size: 12px;
}

.submit {
  width: 100%;
  height: 46px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 2px;
  border-radius: 10px;
}

.demo {
  margin-top: 30px;
  padding: 16px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px dashed #dbe5f1;
}

.demo-title {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 10px;
}

.chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chips button {
  border: 1px solid #dbe5f1;
  background: #fff;
  color: #334155;
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.chips button:hover {
  color: var(--brand);
  border-color: #b7d4ff;
  background: #f0f7ff;
}

.tip {
  margin-top: 10px;
  font-size: 11px;
  color: #94a3b8;
}

.mobile-foot {
  display: none;
  margin-top: 36px;
  text-align: center;
  color: #94a3b8;
  font-size: 11px;
}

@media (max-width: 980px) {
  .login {
    grid-template-columns: 1fr;
    background:
      radial-gradient(600px 380px at 50% -10%, rgba(22, 119, 255, 0.25), transparent 60%),
      linear-gradient(170deg, #0b1b33 0%, #f5f7fa 42%, #f5f7fa 100%);
    padding: 32px 18px;
    align-content: center;
  }
  .brand {
    display: none;
  }
  .panel {
    background: transparent;
    padding: 0;
  }
  .form-wrap {
    max-width: 420px;
    background: #fff;
    padding: 32px 26px;
    border-radius: 18px;
    box-shadow: 0 24px 60px -30px rgba(15, 23, 42, 0.45);
  }
  .mobile-brand,
  .mobile-foot {
    display: flex;
  }
  .mobile-foot {
    justify-content: center;
  }
  h2 {
    font-size: 23px;
  }
}
</style>
