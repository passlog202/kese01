// 🔐 登录 / 注册页
<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { setToken, setUser } from '@/auth'
import { authState } from '@/store'

const router = useRouter()
const route = useRoute()

const mode = ref('login') // login | register
const loading = ref(false)
const form = reactive({ username: '', password: '', confirm: '' })

function switchMode(m) {
  mode.value = m
  form.password = ''
  form.confirm = ''
}

async function submit() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  if (mode.value === 'register') {
    if (form.password.length < 6) {
      ElMessage.warning('密码至少 6 位')
      return
    }
    if (form.password !== form.confirm) {
      ElMessage.warning('两次输入的密码不一致')
      return
    }
  }

  loading.value = true
  try {
    const res = mode.value === 'register'
      ? await api.register(form.username.trim(), form.password)
      : await api.login(form.username.trim(), form.password)
    setToken(res.data.token)
    setUser(res.data.user)
    authState.setAuth(res.data.token, res.data.user)
    ElMessage.success(mode.value === 'register' ? '注册成功，已自动登录' : '登录成功')
    const redirect = route.query.redirect || '/'
    router.replace(redirect)
  } catch (e) {
    ElMessage.error(e.message)
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
      <p class="login-sub">执行标准辅助智能导购 · 请先登录</p>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="3~32 位字母/数字/下划线/中文" size="large" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" size="large" @keyup.enter="submit" />
        </el-form-item>
        <el-form-item v-if="mode === 'register'" label="确认密码">
          <el-input v-model="form.confirm" type="password" show-password placeholder="再次输入密码" size="large" @keyup.enter="submit" />
        </el-form-item>

        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="submit">
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>

      <div class="switch">
        <template v-if="mode === 'login'">
          还没有账号？<a @click="switchMode('register')">立即注册</a>
        </template>
        <template v-else>
          已有账号？<a @click="switchMode('login')">返回登录</a>
        </template>
      </div>

      <div class="demo-tip">
        💡 演示提示：首次使用时直接「注册」任意账号即可体验
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
  width: 400px;
  background: #fff;
  border-radius: 18px;
  padding: 36px 34px 28px;
  box-shadow: 0 18px 48px rgba(31, 41, 55, 0.12);
  text-align: center;
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
}
.login-sub {
  color: #a6afbd;
  font-size: 13px;
  margin: 6px 0 22px;
}
.submit-btn {
  width: 100%;
  margin-top: 6px;
}
.switch {
  margin-top: 16px;
  font-size: 13px;
  color: #8c96a6;
}
.switch a {
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
  text-align: left;
}
</style>
