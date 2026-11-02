/**
 * UI 页面巡检：按角色遍历 PC 与 H5 页面，校验关键内容、无 JS 异常、无横向溢出。
 * 依赖 build/test-artifacts/api-results.json 中的 token。
 */
import fs from 'node:fs'
import path from 'node:path'

const PORT = Number(process.env.CDP_PORT || 9222)
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8000'
const ARTIFACTS = process.env.ARTIFACTS || 'build/test-artifacts'
const SHOT_DIR = path.join(ARTIFACTS, 'ui')

fs.mkdirSync(SHOT_DIR, { recursive: true })

const apiResults = JSON.parse(fs.readFileSync(path.join(ARTIFACTS, 'api-results.json'), 'utf-8'))
const TOKENS = apiResults.tokens

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
const target = targets.find((item) => item.type === 'page')
if (!target) throw new Error('未找到浏览器页面')

const socket = new WebSocket(target.webSocketDebuggerUrl)
const pending = new Map()
let messageId = 0

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++messageId
    pending.set(id, { resolve, reject })
    socket.send(JSON.stringify({ id, method, params }))
  })
}

let runtimeErrors = []
socket.addEventListener('message', (event) => {
  const message = JSON.parse(event.data)
  if (message.id && pending.has(message.id)) {
    const { resolve, reject } = pending.get(message.id)
    pending.delete(message.id)
    message.error ? reject(new Error(message.error.message)) : resolve(message.result)
    return
  }
  if (message.method === 'Runtime.exceptionThrown') {
    runtimeErrors.push(message.params.exceptionDetails?.exception?.description || 'unknown exception')
    return
  }
  if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') {
    runtimeErrors.push(message.params.args.map((arg) => arg.value || arg.description).join(' '))
  }
})

await new Promise((resolve) => socket.addEventListener('open', resolve, { once: true }))
await send('Page.enable')
await send('Runtime.enable')

const MOBILE_UA =
  'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'

const results = []

async function setViewport(width, height, mobile, ua = '') {
  await send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile
  })
  await send('Emulation.setUserAgentOverride', {
    userAgent: ua || (mobile ? MOBILE_UA : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
  })
}

async function evaluate(expression) {
  const { result } = await send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true
  })
  return result.value
}

async function runScenario(scenario) {
  runtimeErrors = []
  const isMobile = scenario.width < 600
  await setViewport(scenario.width, scenario.height, isMobile, scenario.ua)
  await send('Page.navigate', { url: `${BASE}/pc/login` })
  await sleep(700)
  await evaluate(`localStorage.setItem('ss_token', ''); localStorage.setItem('ss_token_m', ''); 'ok'`)
  if (scenario.token) {
    await evaluate(
      `localStorage.setItem(${JSON.stringify(isMobile ? 'ss_token_m' : 'ss_token')}, ${JSON.stringify(scenario.token)}); 'ok'`
    )
  }
  await send('Page.navigate', { url: BASE + scenario.path })
  await sleep(scenario.wait || 2200)

  const state = await evaluate(`JSON.stringify({
    path: location.pathname,
    text: (document.body.innerText || '').replace(/\\s+/g, ' ').trim(),
    overflow: document.documentElement.scrollWidth - window.innerWidth,
    title: document.title
  })`)
  const data = JSON.parse(state)
  const missing = (scenario.expect || []).filter((word) => !data.text.includes(word))
  const found = (scenario.forbid || []).filter((word) => data.text.includes(word))
  const overflow = data.overflow > 2
  const errors = [...runtimeErrors]
  if (scenario.expectPath && !data.path.startsWith(scenario.expectPath)) {
    errors.push(`路径为 ${data.path}，期望 ${scenario.expectPath}`)
  }
  const pass = missing.length === 0 && found.length === 0 && !overflow && errors.length === 0

  results.push({
    name: scenario.name,
    path: scenario.path,
    status: pass ? 'PASS' : 'FAIL',
    missing,
    forbiddenFound: found,
    overflow: overflow ? data.overflow : 0,
    errors,
    finalPath: data.path
  })

  if (scenario.shot) {
    const { data: shot } = await send('Page.captureScreenshot', { format: 'png' })
    fs.writeFileSync(path.join(SHOT_DIR, scenario.shot), Buffer.from(shot, 'base64'))
  }

  const flag = pass ? 'PASS' : 'FAIL'
  const detail = pass ? '' : `missing=${missing} forbidden=${found} overflow=${data.overflow} errors=${errors}`
  console.log(`[${flag}] ${scenario.name} ${detail}`)
  return pass
}

const admin = TOKENS.admin
const staff = TOKENS.staff

const scenarios = [
  { name: '入口页按 UA 分流到 PC', path: '/', width: 1440, height: 900, expectPath: '/pc/', wait: 2200 },
  { name: '入口页按 UA 分流到 H5', path: '/', width: 390, height: 844, ua: MOBILE_UA, expectPath: '/m/', wait: 2400 },
  { name: 'PC 工作台（管理员）', path: '/pc/dashboard', token: admin, width: 1440, height: 900, expect: ['工作台', '低库存预警', '商品总数', '最近操作'], shot: 'pc-dashboard.png' },
  { name: 'PC 商品管理（管理员）', path: '/pc/products', token: admin, width: 1440, height: 900, expect: ['商品管理', '新增商品', '低库存'], shot: 'pc-products.png' },
  { name: 'PC 入库办理', path: '/pc/stock/in?productId=2', token: admin, width: 1440, height: 900, expect: ['入库办理', '当前库存', '确认入库'], shot: 'pc-stock-in.png' },
  { name: 'PC 出库办理', path: '/pc/stock/out?productId=2', token: admin, width: 1440, height: 900, expect: ['出库办理', '操作后库存', '确认出库'] },
  { name: 'PC 出入库记录', path: '/pc/stock/records', token: admin, width: 1440, height: 900, expect: ['出入库记录', '单号', '操作人'], shot: 'pc-records.png' },
  { name: 'PC 用户管理', path: '/pc/system/users', token: admin, width: 1440, height: 900, expect: ['用户管理', '新增用户', '张小明'], shot: 'pc-users.png' },
  { name: 'PC 权限管理', path: '/pc/system/roles', token: admin, width: 1440, height: 900, expect: ['权限管理', '角色列表', '功能权限', '菜单权限'], shot: 'pc-roles.png' },
  { name: 'PC 菜单管理', path: '/pc/system/menus', token: admin, width: 1440, height: 900, expect: ['菜单管理', '新增菜单', '可见角色'], shot: 'pc-menus.png' },
  { name: 'PC 个人中心', path: '/pc/profile', token: admin, width: 1440, height: 900, expect: ['个人中心', '功能权限', '修改密码'] },
  { name: 'PC 员工工作台（无系统管理）', path: '/pc/dashboard', token: staff, width: 1440, height: 900, forbid: ['用户管理', '权限管理', '菜单管理'], expect: ['张小明', '普通员工'], shot: 'pc-staff-dashboard.png' },
  { name: 'PC 员工越权访问返回 403', path: '/pc/system/users', token: staff, width: 1440, height: 900, expect: ['没有访问权限'], shot: 'pc-403.png' },
  { name: 'H5 首页（员工）', path: '/m/home', token: staff, width: 390, height: 844, expect: ['张小明', '低库存预警', '最近操作'], shot: 'h5-home.png' },
  { name: 'H5 商品列表', path: '/m/products', token: staff, width: 390, height: 844, expect: ['商品', '安全库存'], shot: 'h5-products.png' },
  { name: 'H5 商品详情', path: '/m/products/2', token: staff, width: 390, height: 844, expect: ['商品详情', '当前库存', '最近出入库'], shot: 'h5-product-detail.png' },
  { name: 'H5 入库办理', path: '/m/stock/in?productId=2', token: staff, width: 390, height: 844, expect: ['入库办理', '确认入库', '当前库存'], shot: 'h5-stock-in.png' },
  { name: 'H5 出库办理', path: '/m/stock/out?productId=2', token: staff, width: 390, height: 844, expect: ['出库办理', '确认出库'] },
  { name: 'H5 出入库记录', path: '/m/records', token: staff, width: 390, height: 844, expect: ['出入库记录', '全部', '入库'], shot: 'h5-records.png' },
  { name: 'H5 我的（员工无用户管理）', path: '/m/mine', token: staff, width: 390, height: 844, expect: ['张小明', '修改密码'], forbid: ['用户管理'], shot: 'h5-mine.png' },
  { name: 'H5 用户管理（管理员）', path: '/m/users', token: admin, width: 390, height: 844, expect: ['用户管理', '重置密码'], shot: 'h5-users.png' },
  { name: 'H5 修改密码', path: '/m/change-password', token: staff, width: 390, height: 844, expect: ['修改密码', '确认修改'], shot: 'h5-change-password.png' },
  { name: 'H5 360px 小屏首页适配', path: '/m/home', token: staff, width: 360, height: 800, expect: ['张小明', '低库存预警'] },
  { name: 'H5 430px 大屏商品列表适配', path: '/m/products', token: staff, width: 430, height: 932, expect: ['商品', '安全库存'] }
]

let passed = 0
for (const scenario of scenarios) {
  if (await runScenario(scenario)) passed += 1
}

const summary = {
  total: results.length,
  passed,
  failed: results.length - passed,
  results
}
fs.writeFileSync(path.join(ARTIFACTS, 'ui-results.json'), JSON.stringify(summary, null, 2), 'utf-8')
console.log('\n' + '='.repeat(64))
console.log(`UI 巡检合计 ${summary.total} 项，通过 ${passed} 项，失败 ${summary.failed} 项`)
for (const item of results.filter((r) => r.status !== 'PASS')) {
  console.log(`  FAIL ${item.name}: ${JSON.stringify(item)}`)
}
socket.close()
process.exit(summary.failed ? 1 : 0)
