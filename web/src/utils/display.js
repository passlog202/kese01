import { computed, ref } from 'vue'

export * from './format'

/** 执行标准核验状态 → 展示配置 */
export const STANDARD_STATES = {
  现行: { label: '现行', type: 'success', icon: '✓' },
  废止: { label: '已废止', type: 'danger', icon: '✕' },
  未收录: { label: '未收录', type: 'warning', icon: '?' },
  未标注: { label: '未标注', type: 'info', icon: '—' },
  无法识别: { label: '无法识别', type: 'info', icon: '?' },
}

/** 通用数据加载组合式函数 */
export function useFetch(fetcher, initial = null) {
  const data = ref(initial)
  const loading = ref(false)
  const error = ref('')

  const run = async (...args) => {
    loading.value = true
    error.value = ''
    try {
      data.value = await fetcher(...args)
      return data.value
    } catch (e) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }
  return { data, loading, error, run }
}

/** 把 0~100 的维度得分折算为进度百分比（供 el-progress） */
export const toPercent = (v) => Math.max(0, Math.min(100, Number(v) || 0))

/** 由得分推导配色 */
export function scoreType(score) {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

/** 按分值大小排序的评分维度中文名固定顺序 */
export const BREAKDOWN_ORDER = [
  '相似度',
  '标准核验',
  '价格匹配',
  '用户评分',
  '销量',
  '品牌匹配',
  '店铺信誉',
]
