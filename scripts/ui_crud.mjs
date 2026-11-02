/**
 * UI 表单交互测试：PC 端通过抽屉新增商品。
 */
import fs from 'node:fs'
import path from 'node:path'

const PORT = Number(process.env.CDP_PORT || 9222)
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8000'
const ARTIFACTS = process.env.ARTIFACTS || 'build/test-artifacts'
const TOKEN = JSON.parse(fs.readFileSync(path.join(ARTIFACTS, 'api-results.json'), 'utf-8')).tokens.admin
const NAME = `UI测试商品${Date.now().toString().slice(-5)}`
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
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })

const evaluate = async (expression) => {
  const { result } = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  return result.value
}

await send('Page.navigate', { url: `${BASE}/pc/login` })
await sleep(1000)
await evaluate(`localStorage.setItem('ss_token', ${JSON.stringify(TOKEN)}); 'ok'`)
await send('Page.navigate', { url: `${BASE}/pc/products` })
await sleep(2500)

let action = await evaluate(`
(() => {
  const btn = [...document.querySelectorAll('button')].find((b) => (b.innerText || '').includes('新增商品'));
  if (!btn) return 'no-create-button';
  btn.click();
  return 'opened';
})()
`)
console.log('open drawer:', action)
await sleep(1000)

action = await evaluate(`
(() => {
  const input = [...document.querySelectorAll('.el-drawer input')].find((i) => (i.placeholder || '').includes('青提茉莉'));
  if (!input) return 'no-name-input';
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(input, ${JSON.stringify(NAME)});
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
  const save = [...document.querySelectorAll('.el-drawer button')].find((b) => (b.innerText || '').trim() === '保存');
  if (!save) return 'no-save-button';
  save.click();
  return 'submitted';
})()
`)
console.log('fill & submit:', action)
await sleep(2600)

const state = await evaluate(`
JSON.stringify({
  hasRow: (document.body.innerText || '').includes(${JSON.stringify(NAME)}),
  text: (document.body.innerText || '').replace(/\\s+/g, ' ').slice(0, 300),
  hasToast: !!document.querySelector('.el-message')
})
`)
console.log('result:', state)
console.log('problems:', problems.length ? problems : 'none')

const { data } = await send('Page.captureScreenshot', { format: 'png' })
fs.writeFileSync(path.join(ARTIFACTS, 'ui', 'pc-product-created.png'), Buffer.from(data, 'base64'))

const parsed = JSON.parse(state)
const passed = parsed.hasRow && problems.length === 0
console.log(passed ? 'PASS PC 新增商品表单' : 'FAIL PC 新增商品表单')
socket.close()
process.exit(passed ? 0 : 1)
