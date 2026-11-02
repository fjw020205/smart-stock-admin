import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/Login.vue'),
    meta: { public: true, title: '登录' }
  },
  {
    path: '/change-password',
    name: 'change-password',
    component: () => import('../views/ChangePassword.vue'),
    meta: { title: '修改密码' }
  },
  {
    path: '/',
    component: () => import('../layouts/MobileLayout.vue'),
    redirect: '/home',
    children: [
      {
        path: 'home',
        name: 'home',
        component: () => import('../views/Home.vue'),
        meta: { title: '首页', menu: '/dashboard' }
      },
      {
        path: 'products',
        name: 'products',
        component: () => import('../views/Products.vue'),
        meta: { title: '商品', menu: '/products' }
      },
      {
        path: 'products/:id',
        name: 'product-detail',
        component: () => import('../views/ProductDetail.vue'),
        meta: { title: '商品详情', menu: '/products', hideTab: true }
      },
      {
        path: 'stock/in',
        name: 'stock-in',
        component: () => import('../views/StockOperate.vue'),
        props: { mode: 'in' },
        meta: { title: '入库', menu: '/stock/in', hideTab: true }
      },
      {
        path: 'stock/out',
        name: 'stock-out',
        component: () => import('../views/StockOperate.vue'),
        props: { mode: 'out' },
        meta: { title: '出库', menu: '/stock/out', hideTab: true }
      },
      {
        path: 'records',
        name: 'records',
        component: () => import('../views/Records.vue'),
        meta: { title: '出入库记录', menu: '/stock/records' }
      },
      {
        path: 'mine',
        name: 'mine',
        component: () => import('../views/Mine.vue'),
        meta: { title: '我的' }
      },
      {
        path: 'users',
        name: 'users',
        component: () => import('../views/Users.vue'),
        meta: { title: '用户管理', menu: '/system/users', hideTab: true }
      }
    ]
  },
  {
    path: '/403',
    name: 'forbidden',
    component: () => import('../views/Forbidden.vue'),
    meta: { title: '无访问权限' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFound.vue'),
    meta: { public: true, title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory('/m/'),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.public) {
    if (auth.isLoggedIn && to.name === 'login') {
      return auth.mustChangePassword ? '/change-password' : '/home'
    }
    return true
  }

  if (!auth.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (!auth.loaded) {
    try {
      await auth.fetchMe()
    } catch (error) {
      auth.reset()
      return '/login'
    }
  }

  if (auth.mustChangePassword && to.path !== '/change-password') {
    return '/change-password'
  }

  if (to.meta.menu && !auth.isAdmin && !auth.allowedPaths.has(to.meta.menu)) {
    if (to.path === '/home') {
      for (const candidate of ['/products', '/records']) {
        if (auth.allowedPaths.has(candidate)) return candidate
      }
    }
    return '/403'
  }

  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 智仓` : '智仓 · 库存管理'
})

export default router
