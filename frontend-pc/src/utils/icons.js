import * as Icons from '@element-plus/icons-vue'

export function resolveIcon(name) {
  if (name && Icons[name]) return Icons[name]
  return Icons.Menu
}

export const ICON_OPTIONS = [
  'Odometer',
  'Goods',
  'Box',
  'Download',
  'Upload',
  'Tickets',
  'User',
  'Lock',
  'Menu',
  'Setting',
  'Folder',
  'Grid',
  'DataLine',
  'Histogram',
  'ShoppingCart',
  'Files',
  'PieChart',
  'Van',
  'OfficeBuilding'
]
