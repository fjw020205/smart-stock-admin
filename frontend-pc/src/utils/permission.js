import { useAuthStore } from '../stores/auth'

export function can(code) {
  const auth = useAuthStore()
  if (auth.isAdmin) return true
  if (Array.isArray(code)) return code.some((item) => auth.permissionSet.has(item))
  return auth.permissionSet.has(code)
}
