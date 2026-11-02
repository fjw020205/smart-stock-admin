import { defineStore } from 'pinia'
import { authApi } from '../api'
import { flattenMenus } from '../utils/menu'

const TOKEN_KEY = 'ss_token_m'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: null,
    menus: [],
    permissions: [],
    loaded: false
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    isAdmin: (state) => state.user?.role?.code === 'admin',
    mustChangePassword: (state) => Boolean(state.user?.must_change_password),
    permissionSet: (state) => new Set(state.permissions),
    allowedPaths: (state) =>
      new Set(flattenMenus(state.menus).filter((item) => item.permission).map((item) => item.path))
  },
  actions: {
    apply(data) {
      this.token = data.token || this.token
      if (this.token) localStorage.setItem(TOKEN_KEY, this.token)
      this.user = data.user
      this.menus = data.menus || []
      this.permissions = data.permissions || []
      this.loaded = true
    },
    async login(payload) {
      const response = await authApi.login(payload)
      this.apply(response.data)
      return response.data
    },
    async fetchMe() {
      const response = await authApi.me()
      this.apply(response.data)
      return response.data
    },
    async changePassword(payload) {
      const response = await authApi.changePassword(payload)
      this.apply(response.data)
      return response.data
    },
    async logout() {
      try {
        await authApi.logout()
      } catch (error) {
        /* 忽略 */
      }
      this.reset()
    },
    reset() {
      this.token = ''
      this.user = null
      this.menus = []
      this.permissions = []
      this.loaded = false
      localStorage.removeItem(TOKEN_KEY)
    }
  }
})
