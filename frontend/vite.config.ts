import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

// Only a loopback API target is accepted. No credentials are exposed to client code.
const target = process.env.S01_API_TARGET || 'http://127.0.0.1:8000'
const url = new URL(target)
if (!['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname) || url.protocol !== 'http:') throw new Error('LOOPBACK_API_REQUIRED')
export default defineConfig({ plugins: [vue()], server: {
  host: 'localhost', port: 5173, strictPort: true,
  proxy: { '/api': { target, changeOrigin: false } },
}, test: { include: ['tests/unit/**/*.test.ts'], environment: 'node' } })
