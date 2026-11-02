import axios from 'axios'
import { showFailToast, showToast } from 'vant'

let unauthorizedHandler = null
let mustChangeHandler = null

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

export function setMustChangeHandler(handler) {
  mustChangeHandler = handler
}

const http = axios.create({
  baseURL: '/api',
  timeout: 20000
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('ss_token_m')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const body = error.response?.data || {}
    const message =
      body.message || (status ? `请求失败（${status}）` : '无法连接服务，请确认程序已启动')
    const url = String(error.config?.url || '')

    if (status === 401) {
      if (!url.includes('/auth/login')) {
        showToast(message || '登录已失效')
        if (unauthorizedHandler) unauthorizedHandler()
      } else {
        showFailToast(message)
      }
    } else if (status === 403 && body.code === 1002) {
      showToast(message)
      if (mustChangeHandler) mustChangeHandler()
    } else if (!error.config?.silent) {
      showFailToast(message)
    }

    const wrapped = new Error(message)
    wrapped.status = status
    wrapped.code = body.code
    return Promise.reject(wrapped)
  }
)

export default http
