<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="state">
    <van-empty image="search" description="页面不存在或已被移动">
      <van-button round type="primary" class="btn" @click="router.replace('/')">回到首页</van-button>
    </van-empty>
  </div>
</template>

<style scoped>
.state {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: var(--bg);
  padding: 20px;
}

.btn {
  width: 180px;
}
</style>
