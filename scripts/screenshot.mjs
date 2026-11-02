/**
 * 开发辅助：用 Edge 无头模式打开页面、注入登录态并截图。
 * 用法：TOKEN=xxx PAGE_PATH=/pc/dashboard OUT=shot.png node scripts/screenshot.mjs
 */
import fs from 'node:fs'

const PORT = Number(process.env.CDP_PORT || 9222)
const OUT = process.env.OUT || 'shot.png'
const TOKEN = process.env.TOKEN || ''
const PAGE_PATH = process.env.PAGE_PATH || '/pc/dashboard'
const WIDTH = Number(process.env.WIDTH || 1440)
const HEIGHT = Number(process.env.HEIGHT || 900)
const MOBILE = process.env.MOBILE === '1'
const TOKEN_KEY = process.env.TOKEN_KEY || 'ss_token'
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8000'

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
const target = targets.find((item) => item.type === 'page')
if (!target) throw new Error('未找到可用的页面 target')

const socket = new WebSocket(target.webSocketDebuggerUrl)
const pending = new Map()
let messageId = 0
const problems = []

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++messageId
    pending.set(id, { resolve, reject })
    socket.send(JSON.stringify({ id, method, params }))
  })
}

socket.addEventListener('message', (event) => {
  const message = JSON.parse(event.data)
  if (message.id && pending.has(message.id)) {
    const { resolve, reject } = pending.get(message.id)
    pending.delete(message.id)
    if (message.error) reject(new Error(message.error.message))
    else resolve(message.result)
    return
  }
  if (message.method === 'Runtime.exceptionThrown') {
    problems.push(message.params.exceptionDetails?.exception?.description || 'unknown exception')
  }
  if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') {
    problems.push(message.params.args.map((arg) => arg.value || arg.description).join(' '))
  }
})

await new Promise((resolve) => socket.addEventListener('open', resolve, { once: true }))

await send('Page.enable')
await send('Runtime.enable')
await send('Emulation.setDeviceMetricsOverride', {
  width: WIDTH,
  height: HEIGHT,
  deviceScaleFactor: 1,
  mobile: MOBILE
})

try {
  await send('Page.navigate', { url: `${BASE}/pc/login` })
  await sleep(1600)
  if (!TOKEN) {
    await send('Runtime.evaluate', {
      expression:
        "localStorage.removeItem('ss_token'); localStorage.removeItem('ss_token_m'); localStorage.removeItem('ss_remember_m'); localStorage.removeItem('ss_remember_user'); 'ok'"
    })
    await send('Page.navigate', { url: `${BASE}${PAGE_PATH}` })
    await sleep(1800)
  }
  if (TOKEN) {
    await send('Runtime.evaluate', {
      expression: `localStorage.setItem(${JSON.stringify(TOKEN_KEY)}, ${JSON.stringify(TOKEN)}); 'ok'`,
      awaitPromise: true
    })
  }
  await send('Page.navigate', { url: `${BASE}${PAGE_PATH}` })
  await sleep(3800)
  const { data } = await send('Page.captureScreenshot', { format: 'png' })
  fs.writeFileSync(OUT, Buffer.from(data, 'base64'))
  console.log(`saved ${OUT}`)
  if (problems.length) {
    console.log('page errors:')
    problems.forEach((item) => console.log(' -', item))
  } else {
    console.log('no page errors')
  }
} finally {
  socket.close()
}
