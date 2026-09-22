import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { title: '首页' } },
  { path: '/products', name: 'products', component: () => import('@/views/ProductsView.vue'), meta: { title: '商品中心' } },
  { path: '/guide', name: 'guide', component: () => import('@/views/GuideView.vue'), meta: { title: '智能导购' } },
  { path: '/comparison', name: 'comparison', component: () => import('@/views/ComparisonView.vue'), meta: { title: '商品对比' } },
  { path: '/favorites', name: 'favorites', component: () => import('@/views/FavoritesView.vue'), meta: { title: '收藏商品' } },
  { path: '/history', name: 'history', component: () => import('@/views/HistoryView.vue'), meta: { title: '推荐历史' } },
  { path: '/analytics', name: 'analytics', component: () => import('@/views/AnalyticsView.vue'), meta: { title: '数据分析' } },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
