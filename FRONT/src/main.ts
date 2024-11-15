/**
 * main.ts
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

// Plugins
import { registerPlugins } from '@/plugins'

// Components
import App from './App.vue'

// Composables
import { createApp } from 'vue'

const app = createApp(App)

registerPlugins(app)

app.mount('#app')

console.log("Quelles actions TotalEnergies entreprend-elle pour lutter contre la corruption? \n Comment TotalEnergies soutient-elle la santé et la sécurité de ses employés? \n Quels sont les principaux indicateurs de performance extra-financière de TotalEnergies?\nQue fait TotalEnergies en matière de prévention des risques accidentels de pollution ?\n")
