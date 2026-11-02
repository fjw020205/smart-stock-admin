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
    component: () => import('../layouts/AdminLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '工作台', menu: '/dashboard' }
      },
      {
        path: 'products',
        name: 'products',
        component: () => import('../views/Products.vue'),
        meta: { title: '商品管理', menu: '/products' }
      },
      {
        path: 'stock/in',
        name: 'stock-in',
        component: () => import('../views/StockOperate.vue'),
        props: { mode: 'in' },
        meta: { title: '入库办理', menu: '/stock/in' }
      },
      {
        path: 'stock/out',
        name: 'stock-out',
        component: () => import('../views/StockOperate.vue'),
        props: { mode: 'out' },
        meta: { title: '出库办理', menu: '/stock/out' }
      },
      {
        path: 'stock/records',
        name: 'stock-records',
        component: () => import('../views/StockRecords.vue'),
        meta: { title: '出入库记录', menu: '/stock/records' }
      },
      {
        path: 'system/users',
        name: 'users',
        component: () => import('../views/Users.vue'),
        meta: { title: '用户管理', menu: '/system/users' }
      },
      {
        path: 'system/roles',
        name: 'roles',
        component: () => import('../views/Roles.vue'),
        meta: { title: '权限管理', menu: '/system/roles' }
      },
      {
        path: 'system/menus',
        name: 'menus',
        component: () => import('../views/Menus.vue'),
        meta: { title: '菜单管理', menu: '/system/menus' }
      },
      {
        path: 'profile',
        name: 'profile',
        component: () => import('../views/Profile.vue'),
        meta: { title: '个人中心' }
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
  history: createWebHistory('/pc/'),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.public) {
    if (auth.isLoggedIn && to.name === 'login') {
      return auth.mustChangePassword ? '/change-password' : '/dashboard'
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
    return '/403'
  }

  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 智仓` : '智仓 · 库存管理后台'
})

export default router
