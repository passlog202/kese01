// 📊 数据分析：价格分布、品牌/类别、评分-价格、标准核验统计
<script setup>
import { computed, watch } from 'vue'
import { api } from '@/api'
import { useFetch } from '@/utils/display'
import { useEChart } from '@/composables/useEChart'

const products = useFetch(() => api.products(), { count: 0, items: [] })
products.run()

const items = computed(() => products.data?.items || [])

const priceChart = useEChart()
const brandChart = useEChart()
const scatterChart = useEChart()
const standardChart = useEChart()

const STATUS_COLORS = { 现行: '#16A34A', 废止: '#E11D48', 未收录: '#F59E0B', 未标注: '#9CA3AF', 无法识别: '#9CA3AF' }
const POINT_COLOR = 'rgba(75, 123, 236, 0.72)'

watch(
  items,
  (list) => {
    if (!list.length) return

    // 1) 价格分布直方图
    const prices = list.map((p) => p.price)
    const min = Math.min(...prices)
    const max = Math.max(...prices)
    const step = Math.max((max - min) / 22, 1)
    const bins = {}
    prices.forEach((v) => {
      const k = Math.floor(v / step) * step
      bins[k] = (bins[k] || 0) + 1
    })
    priceChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 44, right: 16, top: 24, bottom: 34 },
      xAxis: { type: 'category', data: Object.keys(bins).map((k) => `${k}`), name: '价格(元)' },
      yAxis: { type: 'value', name: '商品数' },
      series: [{
        type: 'bar',
        barWidth: '72%',
        itemStyle: { color: '#ff6b35', borderRadius: [4, 4, 0, 0] },
        data: Object.values(bins),
      }],
    })

    // 2) 品牌商品数量
    const brandCount = {}
    list.forEach((p) => { brandCount[p.brand] = (brandCount[p.brand] || 0) + 1 })
    const brandEntries = Object.entries(brandCount).sort((a, b) => b[1] - a[1]).slice(0, 12)
    brandChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 80, right: 24, top: 12, bottom: 30 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: brandEntries.map((e) => e[0]).reverse() },
      series: [{
        type: 'bar',
        barWidth: '58%',
        itemStyle: { color: '#4b7bec', borderRadius: [0, 4, 4, 0] },
        data: brandEntries.map((e) => e[1]).reverse(),
      }],
    })

    // 3) 评分 - 价格 散点（气泡 = 销量）
    scatterChart.setOption({
      tooltip: {
        formatter: (p) => `${p.data[3]}<br/>价格 ¥${p.data[0]} · 评分 ${p.data[1]} · 销量 ${p.data[2].toLocaleString()}`,
      },
      grid: { left: 50, right: 24, top: 24, bottom: 40 },
      xAxis: { type: 'value', name: '价格(元)' },
      yAxis: { type: 'value', name: '评分', min: 4.0, max: 5.0 },
      series: [{
        type: 'scatter',
        symbolSize: (val) => Math.max(7, Math.min(30, Math.sqrt(val[2]) / 26)),
        data: list.map((p) => [p.price, p.rating, p.sales, p.name]),
        itemStyle: { color: POINT_COLOR, borderColor: '#fff', borderWidth: 1 },
      }],
    })

    // 4) 标准核验分布
    const statusCount = {}
    list.forEach((p) => { statusCount[p.standard_status] = (statusCount[p.standard_status] || 0) + 1 })
    const statusEntries = Object.entries(statusCount)
    standardChart.setOption({
      color: statusEntries.map(([k]) => STATUS_COLORS[k] || '#9CA3AF'),
      tooltip: { trigger: 'item', formatter: '{b}: {c} 件 ({d}%)' },
      legend: { bottom: 0, icon: 'circle', itemWidth: 10, itemHeight: 10 },
      series: [{
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['50%', '44%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: statusEntries.map(([name, value]) => ({ name, value })),
      }],
    })
  },
)
</script>

<template>
  <div class="page">
    <h1 class="page-title">📊 数据分析</h1>
    <p class="page-sub">价格分布、品牌排行、评分-价格关系与执行标准核验统计</p>

    <el-alert v-if="products.error" :title="products.error" type="error" :closable="false" show-icon class="err" />

    <div v-loading="products.loading">
      <el-row :gutter="16">
        <el-col :xs="24" :md="12">
          <el-card shadow="never" class="panel">
            <template #header><b>商品价格分布</b></template>
            <div ref="priceChart.chartRef" class="chart" />
          </el-card>
        </el-col>
        <el-col :xs="24" :md="12">
          <el-card shadow="never" class="panel">
            <template #header><b>品牌商品数量 TOP</b></template>
            <div ref="brandChart.chartRef" class="chart" />
          </el-card>
        </el-col>
        <el-col :xs="24" :md="12">
          <el-card shadow="never" class="panel">
            <template #header><b>评分 vs 价格（气泡为销量）</b></template>
            <div ref="scatterChart.chartRef" class="chart" />
          </el-card>
        </el-col>
        <el-col :xs="24" :md="12">
          <el-card shadow="never" class="panel">
            <template #header><b>执行标准核验分布</b></template>
            <div ref="standardChart.chartRef" class="chart" />
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<style scoped>
.panel {
  border-radius: 14px;
  border: 1px solid #eef0f4;
  margin-bottom: 16px;
}
.chart {
  height: 300px;
  width: 100%;
}
.err {
  margin-bottom: 14px;
}
</style>
