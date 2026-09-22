// 🔐 登录 / 注册 / 找回密码 页（邮箱验证码）
<script setup>
import { reactive, ref, computed, onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { setToken, setUser } from '@/auth'
import { authState } from '@/store'

const router = useRouter()
const route = useRoute()

const mode = ref('login') // login | register | reset
const loading = ref(false)

const form = reactive({
  identifier: '',   // 登录：用户名或邮箱
  username: '',     // 注册
  email: '',        // 注册 / 找回密码
  code: '',
  captcha: '',
  password: '',
  confirm: '',
})

// 图形验证码
const captcha = reactive({ id: '', image: '' })
const captchaLoading = ref(false)

// 验证码倒计时
const countdown = ref(0)
const sending = ref(false)
let timer = null

const debugCode = ref('') // 调试模式下后端回显的验证码

async function loadCaptcha() {
  captchaLoading.value = true
  try {
    const res = await api.captcha()
    captcha.id = res.data.id
    captcha.image = res.data.image
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    captchaLoading.value = false
  }
}

// 看不清换一张：清空已输入内容并重新获取
function refreshCaptcha() {
  form.captcha = ''
  loadCaptcha()
}

function switchMode(m) {
  mode.value = m
  form.password = ''
  form.confirm = ''
  form.code = ''
  debugCode.value = ''
  clearTimer()
  loadCaptcha()
}

function clearTimer() {
  if (timer) { clearInterval(timer); timer = null }
  countdown.value = 0
}
onBeforeUnmount(clearTimer)
onMounted(loadCaptcha)

const AUTH_EMAIL = computed(() => (mode.value === 'reset' ? form.email : form.email))

async function sendCode() {
  const email = form.email.trim()
  if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    ElMessage.warning('请输入正确的邮箱地址')
    return
  }
  const purpose = mode.value === 'reset' ? 'reset' : 'register'
  sending.value = true
  try {
    const res = await api.sendCode(email, purpose)
    if (res.data?.debug) {
      debugCode.value = res.data.code
      form.code = res.data.code
      ElMessage.success(`验证码已发送（调试模式）：${res.data.code}`)
    } else {
      ElMessage.success('验证码已发送，请查收邮箱')
    }
    countdown.value = 60
    timer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) clearTimer()
    }, 1000)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    sending.value = false
  }
}

async function submit() {
  if (mode.value === 'login') {
    if (!form.identifier.trim() || !form.password) {
      ElMessage.warning('请输入账号和密码')
      return
    }
    if (!form.captcha.trim()) {
      ElMessage.warning('请输入图形验证码')
      return
    }
  } else if (mode.value === 'register') {
    if (!form.username.trim() || form.username.trim().length < 3) {
      ElMessage.warning('用户名至少 3 位')
      return
    }
    if (!form.email.trim()) {
      ElMessage.warning('请输入邮箱')
      return
    }
    if (!form.code.trim() || form.code.trim().length !== 6) {
      ElMessage.warning('请输入 6 位邮箱验证码')
      return
    }
    if (form.password.length < 6) {
      ElMessage.warning('密码至少 6 位')
      return
    }
    if (form.password !== form.confirm) {
      ElMessage.warning('两次输入的密码不一致')
      return
    }
  } else {
    if (!form.email.trim() || !form.code.trim()) {
      ElMessage.warning('请输入邮箱和验证码')
      return
    }
    if (form.password.length < 6 || form.password !== form.confirm) {
      ElMessage.warning(form.password.length < 6 ? '密码至少 6 位' : '两次输入的密码不一致')
      return
    }
  }

  loading.value = true
  try {
    let res
    if (mode.value === 'login') {
      res = await api.login(form.identifier.trim(), form.password, captcha.id, form.captcha.trim())
    } else if (mode.value === 'register') {
      if (!form.captcha.trim()) {
        ElMessage.warning('请输入图形验证码')
        return
      }
      await api.verifyCode(form.email.trim(), form.code.trim(), 'register')
      res = await api.register(form.username.trim(), form.password, form.email.trim(), captcha.id, form.captcha.trim())
    } else {
      res = await api.resetPassword(form.email.trim(), form.code.trim(), form.password)
    }

    setToken(res.data.token)
    setUser(res.data.user)
    authState.setAuth(res.data.token, res.data.user)
    ElMessage.success(mode.value === 'reset' ? '密码已重置，已自动登录' : mode.value === 'register' ? '注册成功，已自动登录' : '登录成功')
    router.replace(route.query.redirect || '/')
  } catch (e) {
    ElMessage.error(e.message)
    // 图形验证码错误后自动刷新
    if (/验证码/.test(e.message)) {
      loadCaptcha()
      form.captcha = ''
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-logo">🛒</div>
      <h1>智能导购系统</h1>
      <p class="login-sub">
        {{ mode === 'login' ? '执行标准辅助智能导购 · 请登录'
          : mode === 'register' ? '邮箱注册 · 验证码激活账号' : '通过邮箱验证码重置密码' }}
      </p>

      <!-- 登录 -->
      <el-form v-if="mode === 'login'" label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名 / 邮箱">
          <el-input v-model="form.identifier" placeholder="用户名或邮箱" size="large" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="密码" size="large" @keyup.enter="submit" />
        </el-form-item>
        <el-form-item label="图形验证码">
          <div class="captcha-row">
            <el-input v-model="form.captcha" placeholder="4 位验证码" maxlength="4" size="large" style="flex:1" @keyup.enter="submit" />
            <div class="captcha-img" :class="{ loading: captchaLoading }" @click="loadCaptcha" title="点击刷新">
              <img v-if="captcha.image" :src="captcha.image" alt="captcha" />
              <span v-else class="captcha-placeholder">加载中…</span>
            </div>
          </div>
        </el-form-item>
        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="submit">登 录</el-button>
        <div class="links">
          <a @click="switchMode('register')">邮箱注册</a>
          <a @click="switchMode('reset')">忘记密码？</a>
        </div>
      </el-form>

      <!-- 注册 -->
      <el-form v-else-if="mode === 'register'" label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="3~32 位字母/数字/下划线/中文" size="large" />
        </el-form-item>
        <el-form-item label="邮箱">
          <div class="code-row">
            <el-input v-model="form.email" placeholder="用于接收验证码" size="large" />
            <el-button size="large" :disabled="countdown > 0" :loading="sending" @click="sendCode">
              {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="邮箱验证码">
          <el-input v-model="form.code" placeholder="6 位数字" maxlength="6" size="large" />
          <div v-if="debugCode" class="debug-hint">💡 调试模式，验证码：{{ debugCode }}</div>
        </el-form-item>
        <el-form-item label="图形验证码">
          <div class="captcha-row">
            <div class="captcha-input">
              <el-input v-model="form.captcha" placeholder="4 位验证码" maxlength="4" size="large" @keyup.enter="submit" />
              <el-button link type="primary" class="captcha-refresh-text" @click="refreshCaptcha">看不清？换一张</el-button>
            </div>
            <div class="captcha-img" :class="{ loading: captchaLoading }" @click="refreshCaptcha" title="点击刷新">
              <img v-if="captcha.image" :src="captcha.image" alt="captcha" />
              <span v-else class="captcha-placeholder">加载中…</span>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" size="large" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="form.confirm" type="password" show-password placeholder="再次输入密码" size="large" @keyup.enter="submit" />
        </el-form-item>
        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="submit">注 册</el-button>
        <div class="links"><a @click="switchMode('login')">返回登录</a></div>
      </el-form>

      <!-- 找回密码 -->
      <el-form v-else label-position="top" @submit.prevent="submit">
        <el-form-item label="注册邮箱">
          <div class="code-row">
            <el-input v-model="form.email" placeholder="注册时使用的邮箱" size="large" />
            <el-button size="large" :disabled="countdown > 0" :loading="sending" @click="sendCode">
              {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="邮箱验证码">
          <el-input v-model="form.code" placeholder="6 位数字" maxlength="6" size="large" />
          <div v-if="debugCode" class="debug-hint">💡 调试模式，验证码：{{ debugCode }}</div>
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" size="large" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="form.confirm" type="password" show-password placeholder="再次输入新密码" size="large" @keyup.enter="submit" />
        </el-form-item>
        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="submit">重置密码</el-button>
        <div class="links"><a @click="switchMode('login')">返回登录</a></div>
      </el-form>

      <div class="demo-tip">
        💡 演示提示：后端未配置 SMTP 时处于调试模式，验证码会在输入框上方直接回显，注册即可完整体验邮箱验证流程
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fff3ee 0%, #f5f7fa 60%, #eef3fb 100%);
  padding: 20px;
}
.login-card {
  width: 420px;
  background: #fff;
  border-radius: 18px;
  padding: 34px 34px 26px;
  box-shadow: 0 18px 48px rgba(31, 41, 55, 0.12);
}
.login-logo {
  width: 56px;
  height: 56px;
  margin: 0 auto 12px;
  border-radius: 16px;
  background: linear-gradient(135deg, #ff8a5c, #ff6b35);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  box-shadow: 0 8px 20px rgba(255, 107, 53, 0.35);
}
h1 {
  margin: 0;
  font-size: 20px;
  text-align: center;
}
.login-sub {
  color: #a6afbd;
  font-size: 13px;
  margin: 6px 0 20px;
  text-align: center;
}
.code-row {
  display: flex;
  gap: 10px;
  width: 100%;
}
.captcha-row {
  display: flex;
  gap: 10px;
  align-items: center;
  width: 100%;
}
.captcha-input {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  flex: 1;
  min-width: 0;
}
.captcha-input .el-input {
  width: 100%;
}
.captcha-refresh-text {
  font-size: 12px;
  padding: 0;
  height: auto;
  line-height: 1.4;
}
.captcha-img {
  width: 120px;
  height: 44px;
  border-radius: 8px;
  border: 1px solid #eef0f4;
  overflow: hidden;
  cursor: pointer;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f6f8fb;
}
.captcha-img.loading {
  opacity: 0.6;
  pointer-events: none;
}
.captcha-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.captcha-placeholder {
  font-size: 12px;
  color: #a6afbd;
}
.code-row .el-button {
  flex-shrink: 0;
  width: 116px;
}
.debug-hint {
  font-size: 12px;
  color: #f59e0b;
  margin-top: 6px;
}
.submit-btn {
  width: 100%;
  margin-top: 4px;
}
.links {
  margin-top: 14px;
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}
.links a {
  color: #ff6b35;
  cursor: pointer;
  font-weight: 600;
}
.demo-tip {
  margin-top: 18px;
  padding: 10px;
  background: #fafbfd;
  border-radius: 10px;
  font-size: 12px;
  color: #a6afbd;
}
</style>
