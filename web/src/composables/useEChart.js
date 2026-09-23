import { onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import * as echarts from 'echarts'

/**
 * ECharts 组合式封装：自动初始化、随容器 resize、组件卸载时销毁。
 * 用法：const { chartRef, setOption } = useEChart()
 *       容器绑定 <div ref="chartRef" style="height:320px">
 */
export function useEChart() {
  const chartRef = ref(null)
  const chart = shallowRef(null)

  const setOption = (option) => {
    if (!chart.value) return
    chart.value.setOption(option, true)
  }

  const resize = () => chart.value?.resize()

  onMounted(() => {
    if (chartRef.value) {
      chart.value = echarts.init(chartRef.value)
    }
    window.addEventListener('resize', resize)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('resize', resize)
    chart.value?.dispose()
  })

  return { chartRef, setOption, resize }
}

/** 品牌主色系（与设计规范一致） */
export const KESE_COLORS = [
  '#ff6b35', '#4b7bec', '#16a34a', '#f59e0b', '#8e7cc3',
  '#0fb9b1', '#e11d48', '#5f7a9a', '#d35400', '#27ae60',
]
