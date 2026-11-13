<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import Workspace from './App.vue'
import { request, ApiError, errorText } from './api/client'
const mode = ref(''), checking = ref(true), authenticated = ref(false), busy = ref(false), error = ref('')
const username = ref('admin'), password = ref('')
function expired() { authenticated.value = false; password.value = ''; error.value = '会话已失效，请重新登录。' }
async function restore() {
  checking.value = true; error.value = ''
  try {
    const config = await request<{ mode: string }>('/auth/config'); mode.value = config.mode
    if (mode.value === 'PASSWORD') {
      try { await request('/session'); authenticated.value = true }
      catch (e) { if (!(e instanceof ApiError && e.status === 401)) throw e; error.value = '' }
    }
  } catch (e) { error.value = errorText(e) }
  finally { checking.value = false }
}
async function login() {
  if (busy.value) return
  busy.value = true; error.value = ''
  const secret = password.value; password.value = ''
  try { await request('/auth/login', { method: 'POST', body: JSON.stringify({ username: username.value, password: secret }) }); authenticated.value = true }
  catch (e) { error.value = e instanceof ApiError && e.status === 401 ? '账号或密码不正确，或暂时锁定。请核对后重试。' : errorText(e) }
  finally { busy.value = false }
}
onMounted(() => { window.addEventListener('commerce:unauthenticated', expired); void restore() })
onUnmounted(() => window.removeEventListener('commerce:unauthenticated', expired))
</script>
<template>
  <Workspace v-if="!checking && (mode === 'TRUSTED_BEARER' || authenticated)" :password-login="mode === 'PASSWORD'" @logged-out="authenticated = false; error = ''" />
  <main v-else class="login-shell">
    <section class="login-card" aria-label="平台登录">
      <div class="eyebrow">序衡 · COMMERCE OPERATIONS</div><h1>登录智慧电商平台</h1>
      <p class="muted">本地教学工作台 · 超级管理员</p>
      <p v-if="checking" role="status">正在核对服务与会话…</p>
      <p v-if="error" class="login-error" role="alert">{{ error }}</p>
      <form v-if="!checking && mode === 'PASSWORD'" @submit.prevent="login">
        <label class="field">账号<input v-model="username" autocomplete="username" maxlength="64" required :disabled="busy"></label>
        <label class="field">密码<input v-model="password" type="password" autocomplete="current-password" maxlength="256" required :disabled="busy"></label>
        <button class="button primary" :disabled="busy">{{ busy ? '正在登录…' : '登录' }}</button>
        <p class="micro-note">首次使用或忘记密码，请使用本机初始化 / 重置入口。登录不会自动开始业务分析。</p>
      </form>
      <button v-if="!checking && !mode" class="button" @click="restore">重新连接服务</button>
    </section>
  </main>
</template>
<style scoped>
.login-shell{min-height:100vh;display:grid;place-items:center;padding:24px;background:#f3f5f7}.login-card{width:min(100%,440px);padding:36px;background:white;border:1px solid #d9e2e9;border-radius:14px;box-shadow:0 14px 42px #1834440d}.login-card h1{font-size:25px;margin:14px 0}.login-card form{display:grid;gap:18px;margin-top:26px}.login-error{background:#fff1ed;padding:12px;color:#a4371d;border-radius:6px;overflow-wrap:anywhere}
</style>
