import { useAuthStore } from '../stores/auth'

/**
 * v-perm="'product:create'" 或 v-perm="['a','b']"
 * 无权限时直接把元素从 DOM 移除，避免"看得见点不了"。
 */
export default {
  mounted(el, binding) {
    const auth = useAuthStore()
    const required = Array.isArray(binding.value) ? binding.value : [binding.value]
    const allowed =
      auth.isAdmin || required.some((code) => auth.permissionSet.has(code))
    if (!allowed && el.parentNode) {
      el.parentNode.removeChild(el)
    }
  }
}
