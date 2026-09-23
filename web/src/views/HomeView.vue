// 🏠 首页：系统概览 + 能力说明 + 类别分布
<script setup>
import { computed, watch } from 'vue'
import { api } from '@/api'
import { useFetch } from '@/utils/display'
import { useEChart, KESE_COLORS } from '@/composables/useEChart'
import { fmtNumber } from '@/utils/format'

const health = useFetch(api.health, null)
const products = useFetch(() => api.products(), { count: 0, items: [] })

health.run()
products.run()

const healthData = computed(() => health.data || { products: 0, standards: 0, categories: [] })

// 类别分布 ECharts 环形图
const { chartRef, setOption } = useEChart()

watch(
  products.data,
  (data) => {
    if (!data?.items?.length) return
    const counts = {}
    data.items.forEach((p) => {
      counts[p.category] = (counts[p.category] || 0) + 1
    })
    const entries = Object.entries(counts).sort((a, b) => b[1] - a[1])
    setOption({
      color: KESE_COLORS,
      tooltip: { trigger: 'item', formatter: '{b}: {c} 件 ({d}%)' },
      legend: { bottom: 0, type: 'scroll', itemWidth: 12, itemHeight: 12, textStyle: { fontSize: 11 } },
      series: [
        {
          type: 'pie',
          radius: ['48%', '72%'],
          center: ['50%', '44%'],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 13, fontWeight: 600 } },
          data: entries.map(([name, value]) => ({ name, value })),
        },
      ],
    })
  },
  { deep: false },
)

const cards = [
  { icon: '🛒', title: '商品总数', value: fmtNumber(healthData.value.products) },
  { icon: '🗂️', title: '商品类别', value: fmtNumber(healthData.value.categories.length) },
  { icon: '📋', title: '标准库收录', value: fmtNumber(healthData.value.standards) },
  { icon: '🔎', title: '标准核验', value: '现行/废止/未收录', small: true },
]

const features = [
  { icon: '🤖', title: '智能导购', desc: '条件过滤 + TF-IDF 余弦相似度 + 多因素加权评分，输出可解释推荐。' },
  { icon: '✅', title: '执行标准核验', desc: '识别 GB / GB·T / QB·T 编号，核对现行、废止、未收录状态。' },
  { icon: '⚖️', title: '商品对比', desc: '同类别商品并排对比，指标最优自动高亮。' },
  { icon: '📊', title: '数据分析', desc: '价格分布、品牌排行、标准合规等交互式图表。' },
]
</script>

<template>
  <div class="page">
    <div class="hero">
      <div class="hero-left">
        <h1>🛒 智能导购系统</h1>
        <p>食品接触类日用品 · 执行标准辅助智能导购</p>
        <p class="hero-sub">
          基于 Vue 3 + Element Plus + ECharts 前端，调用 FastAPI 契约服务（TF-IDF + 相似度 + 多因素加权评分）。
        </p>
      </div>
    </div>

    <el-row :gutter="16" class="stat-row">
      <el-col v-for="c in cards" :key="c.title" :xs="12" :sm="12" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-icon">{{ c.icon }}</div>
          <div class="stat-body">
            <div class="stat-title">{{ c.title }}</div>
            <div class="stat-value" :class="{ small: c.small }">{{ c.value }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="body-row">
      <el-col :xs="24" :md="14">
        <el-card shadow="never" class="panel">
          <template #header><b>系统能力</b></template>
          <div class="feature-grid">
            <div v-for="f in features" :key="f.title" class="feature">
              <div class="feature-icon">{{ f.icon }}</div>
              <div>
                <div class="feature-title">{{ f.title }}</div>
                <div class="feature-desc">{{ f.desc }}</div>
              </div>
            </div>
          </div>
          <div class="cta">
            <router-link to="/guide"><el-button type="primary" size="large">🤖 开始智能导购</el-button></router-link>
            <router-link to="/products"><el-button size="large">🛍️ 浏览商品中心</el-button></router-link>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="10">
        <el-card shadow="never" class="panel">
          <template #header><b>类别商品分布</b></template>
          <div v-if="products.loading" v-loading="true" class="chart-box" />
          <div v-else-if="products.error" class="chart-box chart-empty">{{ products.error }}</div>
          <div v-else ref="chartRef" class="chart-box" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.hero {
  padding: 26px 8px 20px;
}
.hero h1 {
  margin: 0 0 8px;
  font-size: 26px;
  letter-spacing: 0.5px;
}
.hero p {
  margin: 4px 0;
  color: #49525f;
}
.hero-sub {
  color: #a6afbd !important;
  font-size: 13px;
}

.stat-row {
  margin-bottom: 16px;
}
.stat-card {
  border-radius: 14px;
  border: 1px solid #eef0f4;
}
.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px;
}
.stat-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background: #fff3ee;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}
.stat-title {
  font-size: 12.5px;
  color: #8c96a6;
}
.stat-value {
  font-size: 20px;
  font-weight: 700;
}
.stat-value.small {
  font-size: 14px;
  font-weight: 600;
}

.panel {
  border-radius: 14px;
  border: 1px solid #eef0f4;
  height: 100%;
}
.feature-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 22px;
}
.feature {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.feature-icon {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: #f6f8fb;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}
.feature-title {
  font-weight: 600;
  font-size: 13.5px;
}
.feature-desc {
  font-size: 12px;
  color: #8c96a6;
  line-height: 1.6;
}
.cta {
  margin-top: 18px;
  display: flex;
  gap: 12px;
}

.chart-box {
  height: 300px;
}
.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a6afbd;
}
</style>
