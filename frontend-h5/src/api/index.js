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
  update: (id, data) => http.put(`/products/${id}`, data)
}

export const stockApi = {
  inbound: (data) => http.post('/stock/in', data),
  outbound: (data) => http.post('/stock/out', data),
  records: (params) => http.get('/stock/records', { params })
}

export const userApi = {
  list: (params) => http.get('/users', { params }),
  toggle: (id, status) => http.patch(`/users/${id}/status`, { status }),
  resetPassword: (id, data) => http.post(`/users/${id}/reset-password`, data)
}
