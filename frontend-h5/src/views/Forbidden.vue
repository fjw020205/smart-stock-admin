<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="state">
    <van-empty image="error" description="当前账号没有访问该页面的权限">
      <van-button round type="primary" class="btn" @click="router.replace('/home')">
        返回首页
      </van-button>
      <van-button round plain class="btn" @click="router.back()">返回上一页</van-button>
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
  margin: 8px 0;
}
</style>
