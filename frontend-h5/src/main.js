import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Vant from 'vant'
import 'vant/lib/index.css'
import './styles/index.css'
import App from './App.vue'
import router from './router'
import { setMustChangeHandler, setUnauthorizedHandler } from './api/http'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Vant)

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
