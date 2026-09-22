import { createRouter, createWebHistory } from 'vue-router'
import { isAuthed } from '@/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { title: '登录', public: true } },
  { path: '/', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { title: '首页' } },
  { path: '/products', name: 'products', component: () => import('@/views/ProductsView.vue'), meta: { title: '商品中心' } },
  { path: '/guide', name: 'guide', component: () => import('@/views/GuideView.vue'), meta: { title: '智能导购' } },
  { path: '/comparison', name: 'comparison', component: () => import('@/views/ComparisonView.vue'), meta: { title: '商品对比' } },
  { path: '/favorites', name: 'favorites', component: () => import('@/views/FavoritesView.vue'), meta: { title: '收藏商品' } },
  { path: '/history', name: 'history', component: () => import('@/views/HistoryView.vue'), meta: { title: '推荐历史' } },
  { path: '/analytics', name: 'analytics', component: () => import('@/views/AnalyticsView.vue'), meta: { title: '数据分析' } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

// 全局守卫：未登录访问业务页 → 跳转登录
router.beforeEach((to) => {
  if (to.meta.public) {
    if (to.path === '/login' && isAuthed()) return { path: '/' }
    return true
  }
  if (!isAuthed()) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
