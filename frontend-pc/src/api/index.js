import http from './http'

export const authApi = {
  login: (data) => http.post('/auth/login', data),
  logout: () => http.post('/auth/logout', null, { silent: true }),
  me: () => http.get('/auth/me'),
  changePassword: (data) => http.put('/auth/password', data)
}

export const dashboardApi = {
  summary: () => http.get('/dashboard/summary')
}

export const productApi = {
  list: (params) => http.get('/products', { params }),
  detail: (id) => http.get(`/products/${id}`),
  create: (data) => http.post('/products', data),
  update: (id, data) => http.put(`/products/${id}`, data),
  remove: (id) => http.delete(`/products/${id}`)
}

export const stockApi = {
  inbound: (data) => http.post('/stock/in', data),
  outbound: (data) => http.post('/stock/out', data),
  records: (params) => http.get('/stock/records', { params }),
  recent: (limit = 10) => http.get('/stock/records/recent', { params: { limit } })
}

export const userApi = {
  list: (params) => http.get('/users', { params }),
  create: (data) => http.post('/users', data),
  update: (id, data) => http.put(`/users/${id}`, data),
  remove: (id) => http.delete(`/users/${id}`),
  toggle: (id, status) => http.patch(`/users/${id}/status`, { status }),
  resetPassword: (id, data) => http.post(`/users/${id}/reset-password`, data),
  menus: (id) => http.get(`/users/${id}/menus`),
  saveMenus: (id, data) => http.put(`/users/${id}/menus`, data)
}

export const roleApi = {
  list: () => http.get('/roles'),
  permissions: () => http.get('/roles/permissions'),
  create: (data) => http.post('/roles', data),
  update: (id, data) => http.put(`/roles/${id}`, data),
  remove: (id) => http.delete(`/roles/${id}`),
  savePermissions: (id, permissions) => http.put(`/roles/${id}/permissions`, { permissions }),
  saveMenus: (id, menu_ids) => http.put(`/roles/${id}/menus`, { menu_ids })
}

export const menuApi = {
  list: () => http.get('/menus'),
  registry: () => http.get('/menus/registry'),
  create: (data) => http.post('/menus', data),
  update: (id, data) => http.put(`/menus/${id}`, data),
  remove: (id) => http.delete(`/menus/${id}`),
  saveRoles: (id, role_ids) => http.put(`/menus/${id}/roles`, { role_ids })
}
