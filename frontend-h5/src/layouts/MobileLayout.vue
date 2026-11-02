<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()

const showTabbar = computed(() => !route.meta.hideTab)

const tabs = computed(() =>
  [
    { name: 'home', to: '/home', icon: 'wap-home-o', title: '首页', show: auth.allowedPaths.has('/dashboard') },
    { name: 'products', to: '/products', icon: 'apps-o', title: '商品', show: auth.allowedPaths.has('/products') },
    { name: 'records', to: '/records', icon: 'orders-o', title: '记录', show: auth.allowedPaths.has('/stock/records') },
    { name: 'mine', to: '/mine', icon: 'user-o', title: '我的', show: true }
  ].filter((tab) => tab.show)
)
</script>

<template>
  <div class="shell" :class="{ 'with-tabbar': showTabbar }">
    <router-view v-slot="{ Component }">
      <transition name="mobile-fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>

    <van-tabbar v-if="showTabbar" route fixed placeholder safe-area-inset-bottom active-color="#1677ff">
      <van-tabbar-item
        v-for="tab in tabs"
        :key="tab.name"
        :to="tab.to"
        :icon="tab.icon"
      >
        {{ tab.title }}
      </van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<style scoped>
.mobile-fade-enter-active,
.mobile-fade-leave-active {
  transition: opacity 0.16s ease;
}
.mobile-fade-enter-from,
.mobile-fade-leave-to {
  opacity: 0;
}
</style>
