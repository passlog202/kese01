// HTTP API 客户端：纯调用后端 FastAPI 契约接口（docs/前后端契约.md）
import axios from 'axios'
import { getToken, logout } from '@/auth'

const http = axios.create({
  // 生产环境 nginx 将 /api 反代到后端；开发环境 vite 代理转发
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 30000,
})

// 请求拦截：统一注入 Bearer Token
http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一解包 / 错误处理 / 401 自动登出
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const body = err.response?.data
    const code = body?.error?.code
    const message = body?.error?.message || err.message || '网络异常，请确认后端服务已启动'
    // 登录失效：清除本地状态并跳转登录页
    if (err.response?.status === 401) {
      logout()
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(new Error(message))
  },
)

export const api = {
  health: () => http.get('/health'),
  meta: () => http.get('/meta'),

  // 认证
  captcha: () => http.get('/auth/captcha'),
  register: (username, password, email = null, captcha_id = null, captcha_code = null) =>
    http.post('/auth/register', { username, password, email, captcha_id, captcha_code }),
  login: (identifier, password, captcha_id = null, captcha_code = null) =>
    http.post('/auth/login', { username: identifier, password, captcha_id, captcha_code }),
  me: () => http.get('/auth/me'),
  sendCode: (email, purpose = 'register') => http.post('/auth/send-code', { email, purpose }),
  verifyCode: (email, code, purpose = 'register') => http.post('/auth/verify-code', { email, code, purpose }),
  resetPassword: (email, code, new_password) => http.post('/auth/reset-password', { email, code, new_password }),

  // 业务
  products: (params) => http.get('/products', { params }),
  recommend: (payload) => http.post('/recommend', payload),
  parse: (text) => http.post('/parse', { text }),
  verify: (text) => http.post('/standards/verify', { text }),
  favorites: () => http.get('/favorites'),
  addFavorite: (product_id) => http.post('/favorites', { product_id }),
  removeFavorite: (product_id) => http.delete(`/favorites/${product_id}`),
  history: (limit = 100) => http.get('/history/recommendations', { params: { limit } }),
}
