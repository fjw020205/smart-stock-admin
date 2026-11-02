/**
 * 开发辅助：无头浏览器走一遍登录流程，验证前端与后端联调。
 */
import fs from 'node:fs'

const PORT = Number(process.env.CDP_PORT || 9222)
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8000'
const USERNAME = process.env.USERNAME || 'staff'
const PASSWORD = process.env.PASSWORD || 'Staff@123456'
const TARGET = process.env.TARGET || 'pc'
const OUT = process.env.OUT || ''
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()
const target = targets.find((item) => item.type === 'page')
if (!target) throw new Error('未找到页面 target')

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

const loginPath = TARGET === 'pc' ? '/pc/login' : '/m/login'
await send('Page.navigate', { url: `${BASE}${loginPath}` })
await sleep(1200)
await send('Runtime.evaluate', { expression: 'localStorage.clear()' })
await send('Page.navigate', { url: `${BASE}${loginPath}` })
await sleep(1800)

const fillScript = `
(() => {
  const inputs = [...document.querySelectorAll('input')];
  if (inputs.length < 2) return 'no-inputs';
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(inputs[0], ${JSON.stringify(USERNAME)});
  inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
  setter.call(inputs[1], ${JSON.stringify(PASSWORD)});
  inputs[1].dispatchEvent(new Event('input', { bubbles: true }));
  const button = [...document.querySelectorAll('button')].find((item) =>
    (item.innerText || '').replace(/\\s/g, '').includes('登录')
  );
  if (!button) return 'no-button';
  button.click();
  return 'clicked';
})()
`
const clicked = await send('Runtime.evaluate', { expression: fillScript, returnByValue: true })
console.log('action:', clicked.result.value)
await sleep(3200)

const state = await send('Runtime.evaluate', {
  expression: `JSON.stringify({
    path: location.pathname,
    token: !!localStorage.getItem('ss_token') || !!localStorage.getItem('ss_token_m'),
    body: (document.body.innerText || '').slice(0, 160)
  })`,
  returnByValue: true
})
console.log('state:', state.result.value)
console.log('problems:', problems.length ? problems : 'none')

if (OUT) {
  const { data } = await send('Page.captureScreenshot', { format: 'png' })
  fs.writeFileSync(OUT, Buffer.from(data, 'base64'))
  console.log('saved', OUT)
}

socket.close()
