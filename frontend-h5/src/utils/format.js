import dayjs from 'dayjs'

export function formatDateTime(value) {
  if (!value) return '-'
  return dayjs(value).format('MM-DD HH:mm')
}

export function formatFullTime(value) {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm')
}

export function formatMoney(value) {
  return Number(value || 0).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

export function greeting() {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 11) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
}

export function todayText() {
  const date = dayjs()
  const week = ['日', '一', '二', '三', '四', '五', '六'][date.day()]
  return `${date.format('M月D日')} 星期${week}`
}

export function initials(name) {
  if (!name) return '?'
  return name.trim().slice(0, 1).toUpperCase()
}
