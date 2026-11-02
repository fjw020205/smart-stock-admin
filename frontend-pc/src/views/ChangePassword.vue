<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref(null)
const loading = ref(false)
const form = reactive({ old_password: '', new_password: '', confirm: '' })

const validateConfirm = (rule, value, callback) => {
  if (value !== form.new_password) callback(new Error('两次输入的密码不一致'))
  else callback()
}

const rules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    {
      pattern: /^(?=.*[A-Za-z])(?=.*\d).{8,20}$/,
      message: '8-20 位，需同时包含字母和数字',
      trigger: 'blur'
    }
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' }
  ]
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
    await auth.changePassword({
      old_password: form.old_password,
      new_password: form.new_password
    })
    ElMessage.success('密码修改成功')
    router.replace('/dashboard')
  } catch (error) {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="pwd-page">
    <div class="grid" aria-hidden="true" />
    <div class="card">
      <div class="head">
        <div class="mark">仓</div>
        <div>
          <h2>{{ auth.mustChangePassword ? '设置新的登录密码' : '修改密码' }}</h2>
          <p>
            {{
              auth.mustChangePassword
                ? '为了账号安全，首次登录需要修改初始密码后才能继续使用'
                : '定期更换密码可以降低账号泄露风险'
            }}
          </p>
        </div>
      </div>

      <el-alert
        v-if="auth.mustChangePassword"
        type="warning"
        :closable="false"
        show-icon
        title="初始密码仅用于首次登录，请设置一个只有你自己知道的新密码"
        class="alert"
      />

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="form.old_password" type="password" show-password size="large" placeholder="请输入原密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" show-password size="large" placeholder="8-20 位，字母 + 数字" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm">
          <el-input v-model="form.confirm" type="password" show-password size="large" placeholder="请再次输入新密码" @keyup.enter="submit" />
        </el-form-item>

        <el-button type="primary" size="large" class="submit" :loading="loading" @click="submit">
          确认修改
        </el-button>
      </el-form>

      <div class="foot">
        <span class="user">{{ auth.user?.real_name }} · {{ auth.user?.username }}</span>
        <el-button v-if="!auth.mustChangePassword" link type="primary" @click="router.back()">返回上一页</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pwd-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(700px 500px at 20% 0%, rgba(22, 119, 255, 0.22), transparent 60%),
    linear-gradient(160deg, #071527 0%, #0b1b33 100%);
}

.grid {
  position: fixed;
  inset: 0;
  background-image: linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: radial-gradient(circle at 50% 30%, #000, transparent 75%);
  pointer-events: none;
}

.card {
  position: relative;
  width: min(460px, 100%);
  background: #fff;
  border-radius: 18px;
  padding: 30px 30px 22px;
  box-shadow: 0 40px 90px -40px rgba(0, 0, 0, 0.6);
}

.head {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.mark {
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  color: #fff;
  font-weight: 700;
  background: linear-gradient(135deg, #1677ff, #4da3ff);
}

h2 {
  font-size: 19px;
  font-weight: 700;
}

.head p {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--muted);
}

.alert {
  margin-bottom: 18px;
  border-radius: 10px;
}

.submit {
  width: 100%;
  height: 44px;
  margin-top: 4px;
  font-weight: 600;
}

.foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 18px;
  font-size: 12px;
  color: var(--muted);
}
</style>
