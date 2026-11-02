<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="state-page">
    <div class="code">404</div>
    <h2>页面走丢了</h2>
    <p>你访问的地址不存在，或者已经被移动。</p>
    <div class="actions">
      <el-button type="primary" @click="router.replace('/')">回到首页</el-button>
    </div>
  </div>
</template>

<style scoped>
.state-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 20px;
  background: var(--bg);
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
  color: var(--muted);
  font-size: 13px;
}
.actions {
  margin-top: 22px;
}
</style>
