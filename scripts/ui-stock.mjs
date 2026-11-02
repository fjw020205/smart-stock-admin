/**
 * 开发辅助：走一遍 PC 出入库表单，验证前端提交链路。
 * 用法：TOKEN=xxx MODE=in PRODUCT_ID=2 node scripts/ui-stock.mjs
 */
import fs from 'node:fs'

const PORT = Number(process.env.CDP_PORT || 9222)
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8000'
const TOKEN = process.env.TOKEN || ''
const MODE = process.env.MODE === 'out' ? 'out' : 'in'
const PRODUCT_ID = process.env.PRODUCT_ID || '2'
const TARGET = process.env.TARGET === 'h5' ? 'h5' : 'pc'
const OUT = process.env.OUT || ''
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
const target = targets.find((item) => item.type === 'page')
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
    message.error ? reject(new Error(message.error.message)) : resolve(message.result)
    return
  }
  if (message.method === 'Runtime.exceptionThrown') {
    problems.push(message.params.exceptionDetails?.exception?.description || 'exception')
  }
})

await new Promise((resolve) => socket.addEventListener('open', resolve, { once: true }))
await send('Page.enable')
await send('Runtime.enable')
await send('Emulation.setDeviceMetricsOverride', {
  width: TARGET === 'pc' ? 1440 : 390,
  height: TARGET === 'pc' ? 900 : 844,
  deviceScaleFactor: 1,
  mobile: TARGET !== 'pc'
})

await send('Page.navigate', { url: `${BASE}${TARGET === 'pc' ? '/pc/login' : '/m/login'}` })
await sleep(1200)
await send('Runtime.evaluate', {
  expression: `localStorage.setItem(${JSON.stringify(TARGET === 'pc' ? 'ss_token' : 'ss_token_m')}, ${JSON.stringify(TOKEN)}); 'ok'`
})
await send('Page.navigate', {
  url: `${BASE}${TARGET === 'pc' ? '/pc' : '/m'}/stock/${MODE}?productId=${PRODUCT_ID}`
})
await sleep(3200)

const before = await send('Runtime.evaluate', {
  expression: `document.body.innerText.slice(0, 400)`,
  returnByValue: true
})
console.log('before:', before.result.value.replace(/\\n/g, ' | ').slice(0, 300))

const clicked = await send('Runtime.evaluate', {
  expression: `
(() => {
  const buttons = [...document.querySelectorAll('button')];
  const target = buttons.find((b) => (b.innerText || '').replace(/\\s/g, '').includes('确认${MODE === 'in' ? '入库' : '出库'}'));
  if (!target) return 'no-submit';
  target.click();
  return 'clicked';
})()
`,
  returnByValue: true
})
console.log('action:', clicked.result.value)
await sleep(2500)

const after = await send('Runtime.evaluate', {
  expression: `JSON.stringify({ body: document.body.innerText.slice(0, 300), toast: !!document.querySelector('.el-message') })`,
  returnByValue: true
})
console.log('after:', after.result.value)
console.log('problems:', problems.length ? problems : 'none')

if (OUT) {
  const { data } = await send('Page.captureScreenshot', { format: 'png' })
  fs.writeFileSync(OUT, Buffer.from(data, 'base64'))
}
socket.close()
