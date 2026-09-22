// 极简响应式登录态（仅用 reactive，避免引入 pinia）
import { reactive } from 'vue'
import { getUser, getToken } from '@/auth'

export const authState = reactive({
  user: getUser(),
  token: getToken(),
  setAuth(token, user) {
    this.token = token
    this.user = user
  },
  clear() {
    this.token = ''
    this.user = null
  },
  get isAuthed() {
    return !!this.token
  },
})
