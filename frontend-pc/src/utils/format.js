import dayjs from 'dayjs'

export function formatDateTime(value) {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm')
}

export function formatDate(value) {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD')
}

export function formatMoney(value) {
  const number = Number(value || 0)
  return number.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN')
}

export function todayLabel() {
  const date = dayjs()
  const week = ['日', '一', '二', '三', '四', '五', '六'][date.day()]
  return `${date.format('YYYY年M月D日')} 星期${week}`
}

export function initials(name) {
  if (!name) return '?'
  return name.trim().slice(0, 1).toUpperCase()
}
