import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

/**
 * 侧边导航菜单项。图标用 emoji 保持轻量美观。
 */
export function useNav() {
  const router = useRouter()
  const route = useRoute()

  const groups = [
    {
      label: '导购',
      items: [
        { name: 'home', path: '/', icon: '🏠', title: '首页' },
        { name: 'guide', path: '/guide', icon: '🤖', title: '智能导购' },
        { name: 'products', path: '/products', icon: '🛍️', title: '商品中心' },
        { name: 'comparison', path: '/comparison', icon: '⚖️', title: '商品对比' },
      ],
    },
    {
      label: '我的',
      items: [
        { name: 'favorites', path: '/favorites', icon: '❤️', title: '收藏商品' },
        { name: 'history', path: '/history', icon: '🕘', title: '推荐历史' },
      ],
    },
    {
      label: '洞察',
      items: [{ name: 'analytics', path: '/analytics', icon: '📊', title: '数据分析' }],
    },
  ]

  const activePath = computed(() => route.path)
  const pageTitle = computed(() => route.meta.title || '智能导购系统')

  const go = (path) => {
    if (route.path !== path) router.push(path)
  }

  return { groups, activePath, pageTitle, go }
}
