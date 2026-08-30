import axios, { AxiosError, type AxiosRequestConfig } from 'axios'

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

const ACCESS_KEY = 'token'
const REFRESH_KEY = 'refresh_token'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY)
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

// 请求拦截器：注入 access token
client.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 单例刷新：并发 401 时只发起一次 refresh，其余请求共享同一 Promise
let refreshPromise: Promise<string | null> | null = null

async function tryRefresh(): Promise<string | null> {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    const refresh = localStorage.getItem(REFRESH_KEY)
    if (!refresh) return null
    try {
      // 不走本实例拦截器，避免递归
      const resp = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh })
      const data = resp.data.data
      setTokens(data.access_token, data.refresh_token)
      return data.access_token
    } catch {
      clearTokens()
      return null
    } finally {
      refreshPromise = null
    }
  })()
  return refreshPromise
}

// 响应拦截器：统一解包 + 401 自动刷新重试一次
client.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 0) {
        return Promise.reject(new Error(body.message || '请求失败'))
      }
      return body.data
    }
    return body
  },
  async (error: AxiosError) => {
    const original = error.config as (AxiosRequestConfig & { _retried?: boolean }) | undefined

    // 401 且未重试过 → 尝试刷新后重放原请求一次
    if (error.response?.status === 401 && original && !original._retried) {
      const newToken = await tryRefresh()
      if (newToken) {
        original._retried = true
        original.headers = { ...original.headers, Authorization: `Bearer ${newToken}` }
        return client.request(original)
      }
      // 刷新失败：清除并引导登录
      clearTokens()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }

    const message =
      (error.response?.data as { message?: string } | undefined)?.message ||
      error.message ||
      '网络错误'
    return Promise.reject(new Error(message))
  },
)

export default client
