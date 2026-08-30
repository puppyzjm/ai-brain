import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, logout as logoutApi, register as registerApi } from '../api/auth'
import { fetchMe, type User } from '../api/user'
import { clearTokens, getAccessToken, setTokens } from '../api/client'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getAccessToken())
  const user = ref<User | null>(null)

  async function login(account: string, password: string) {
    const res = await loginApi({ account, password })
    setTokens(res.access_token, res.refresh_token)
    token.value = res.access_token
    await loadUser()
  }

  async function registerUser(username: string, email: string, password: string) {
    await registerApi({ username, email, password })
  }

  async function loadUser() {
    if (!token.value) return
    user.value = await fetchMe()
  }

  async function logout() {
    try {
      // 撤销服务端 refresh token（使轮换链断裂，安全登出）
      await logoutApi()
    } catch {
      /* 即使服务端撤销失败，也清空本地会话 */
    }
    token.value = null
    user.value = null
    clearTokens()
  }

  return { token, user, login, registerUser, loadUser, logout }
})
