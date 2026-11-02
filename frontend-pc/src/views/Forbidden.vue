<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="state-page">
    <div class="code">403</div>
    <h2>没有访问权限</h2>
    <p>当前账号未被授权访问该页面，如需使用请联系管理员调整角色或菜单可见范围。</p>
    <div class="actions">
      <el-button type="primary" @click="router.replace('/dashboard')">返回工作台</el-button>
      <el-button @click="router.back()">返回上一页</el-button>
    </div>
  </div>
</template>

<style scoped>
.state-page {
  min-height: 60vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 20px;
}
.code {
  font-size: 76px;
  font-weight: 800;
  line-height: 1;
  background: linear-gradient(135deg, #1677ff, #7cc0ff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  letter-spacing: 2px;
}
h2 {
  margin-top: 16px;
  font-size: 20px;
}
p {
  margin-top: 10px;
  max-width: 420px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.8;
}
.actions {
  display: flex;
  gap: 10px;
  margin-top: 22px;
}
</style>
