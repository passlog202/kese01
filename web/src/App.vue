// 🛒 智能导购系统 · 应用根组件
// 左侧品牌导航 + 右侧路由视图；登录后展示业务页，未登录显示登录页
<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { useFetch } from '@/utils/display'
import { useNav } from '@/composables/useNav'
import { fmtNumber } from '@/utils/format'
import { authState } from '@/store'
import { logout } from '@/auth'

const route = useRoute()
const router = useRouter()
const { groups, activePath, pageTitle, go } = useNav()

const health = useFetch(api.health, null)
if (authState.isAuthed) health.run()

const stats = computed(() => {
  if (!health.data) return { products: '-', standards: '-' }
  return { products: fmtNumber(health.data.products), standards: fmtNumber(health.data.standards) }
})

// 登录页不渲染外壳
const isLoginPage = computed(() => route.meta.public === true)

function doLogout() {
  logout()
  authState.clear()
  ElMessage.success('已退出登录')
  router.replace('/login')
}
</script>

<template>
  <router-view v-if="isLoginPage" />

  <el-container v-else class="shell">
    <!-- 侧边栏 -->
    <el-aside width="230px" class="aside">
      <div class="brand" @click="go('/')">
        <div class="brand-logo">🛒</div>
        <div class="brand-name">智能导购系统</div>
      </div>

      <el-menu :default-active="activePath" class="menu" router @select="(p) => go(p)">
        <template v-for="group in groups" :key="group.label">
          <div class="menu-group">{{ group.label }}</div>
          <el-menu-item v-for="item in group.items" :key="item.name" :index="item.path">
            <span class="menu-icon">{{ item.icon }}</span>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>

      <div class="aside-foot">
        <div class="foot-item"><span class="dot" :class="{ ok: health.data }"></span><span>{{ health.data ? '服务在线' : '连接中…' }}</span></div>
        <div class="foot-item">商品 {{ stats.products }} · 标准 {{ stats.standards }}</div>
      </div>
    </el-aside>

    <!-- 主区 -->
    <el-container class="main">
      <el-header class="topbar" height="56px">
        <div class="topbar-title">{{ pageTitle }}</div>
        <div class="topbar-right">
          <span class="topbar-sub">执行标准辅助智能导购</span>
          <el-dropdown trigger="click">
            <span class="user-chip">
              <span class="user-avatar">{{ (authState.user?.username || 'U').slice(0, 1).toUpperCase() }}</span>
              <span class="user-name">{{ authState.user?.username }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>账号：{{ authState.user?.username }}</el-dropdown-item>
                <el-dropdown-item divided @click="doLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.shell {
  height: 100%;
}

/* 侧边栏 */
.aside {
  background: #fff;
  border-right: 1px solid #eef0f4;
  display: flex;
  flex-direction: column;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 22px 20px 18px;
  cursor: pointer;
}
.brand-logo {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #ff8a5c, #ff6b35);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 21px;
  box-shadow: 0 6px 16px rgba(255, 107, 53, 0.35);
}
.brand-name {
  font-weight: 700;
  font-size: 16px;
}
.menu {
  border-right: none;
  flex: 1;
  padding: 0 10px;
}
.menu-group {
  font-size: 12px;
  color: #a6afbd;
  padding: 14px 14px 6px;
  letter-spacing: 1px;
}
.menu :deep(.el-menu-item) {
  height: 44px;
  border-radius: 10px;
  margin: 2px 0;
  color: #49525f;
}
.menu :deep(.el-menu-item:hover) {
  background: #fff3ee;
}
.menu :deep(.el-menu-item.is-active) {
  background: #fff3ee;
  color: #ff6b35;
  font-weight: 600;
}
.menu-icon {
  margin-right: 8px;
  font-size: 16px;
}
.aside-foot {
  padding: 14px 18px;
  border-top: 1px solid #eef0f4;
  font-size: 12px;
  color: #a6afbd;
}
.foot-item {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 3px 0;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d3d9e2;
}
.dot.ok {
  background: #16a34a;
}

/* 主区 */
.main {
  background: #f5f7fa;
}
.topbar {
  background: #fff;
  border-bottom: 1px solid #eef0f4;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.topbar-title {
  font-size: 17px;
  font-weight: 700;
}
.topbar-sub {
  font-size: 12px;
  color: #a6afbd;
}
.topbar-right {
  display: flex;
  align-items: center;
  gap: 20px;
}
.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 20px;
  background: #f6f8fb;
  transition: background 0.15s;
}
.user-chip:hover {
  background: #fff3ee;
}
.user-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ff8a5c, #ff6b35);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
}
.user-name {
  font-size: 13px;
  font-weight: 600;
}

.content {
  overflow-y: auto;
  padding: 6px 0 40px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 760px) {
  .aside {
    width: 66px !important;
  }
  .brand-name,
  .menu-group,
  .menu :deep(.el-menu-item span:last-child),
  .aside-foot,
  .topbar-sub {
    display: none;
  }
}
</style>
