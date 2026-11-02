import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import './styles/index.css'
import App from './App.vue'
import router from './router'
import permission from './directives/permission'
import { setMustChangeHandler, setUnauthorizedHandler } from './api/http'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}
app.directive('perm', permission)

setUnauthorizedHandler(() => {
  const auth = useAuthStore(pinia)
  auth.reset()
  if (router.currentRoute.value.path !== '/login') {
    router.replace('/login')
  }
})

setMustChangeHandler(() => {
  if (router.currentRoute.value.path !== '/change-password') {
    router.replace('/change-password')
  }
})

app.mount('#app')
