import { createApp } from 'vue'
import App from './PlatformApp.vue'
import './styles.css'
import './workspace.css'
import './v3.css'
import './workflow.css'
import { startRouter } from './router'
startRouter()
createApp(App).mount('#app')
