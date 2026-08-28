import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, register as registerApi } from '../api/auth'
import { fetchMe, type User } from '../api/user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)

  async function login(account: string, password: string) {
    const res = await loginApi({ account, password })
    token.value = res.access_token
    localStorage.setItem('token', res.access_token)
    await loadUser()
  }

  async function registerUser(username: string, email: string, password: string) {
    await registerApi({ username, email, password })
  }

  async function loadUser() {
    if (!token.value) return
    user.value = await fetchMe()
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, login, registerUser, loadUser, logout }
})
