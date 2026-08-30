import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'

// 圆润字体：HarmonyOS Sans SC（中文全量）+ Nunito（英文数字）
import './utils/fonts'
import '@fontsource/nunito/400.css'
import '@fontsource/nunito/600.css'
import '@fontsource/nunito/700.css'

// 全局主题（深色默认 + 青绿品牌色 + 字号）
import './styles/theme.css'

import App from './App.vue'
import router from './router'
import { initTheme } from './utils/theme'

initTheme()

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
