// HTTP API 客户端：纯调用后端 FastAPI 契约接口（docs/前后端契约.md）
import axios from 'axios'

const http = axios.create({
  // 生产环境 nginx 将 /api 反代到后端；开发环境 vite 代理转发
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 30000,
})

// 把 axios 异常统一成可读信息
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const e = err.response?.data?.error
    const message = e?.message || err.message || '网络异常，请确认后端服务已启动'
    return Promise.reject(new Error(message))
  },
)

export const api = {
  health: () => http.get('/health'),
  meta: () => http.get('/meta'),
  products: (params) => http.get('/products', { params }),
  recommend: (payload) => http.post('/recommend', payload),
  parse: (text) => http.post('/parse', { text }),
  verify: (text) => http.post('/standards/verify', { text }),
  favorites: () => http.get('/favorites'),
  addFavorite: (product_id) => http.post('/favorites', { product_id }),
  removeFavorite: (product_id) => http.delete(`/favorites/${product_id}`),
  history: (limit = 100) => http.get('/history/recommendations', { params: { limit } }),
}
