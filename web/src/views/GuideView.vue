// 🤖 智能导购：需求录入（含自然语言解析）→ 推荐结果 + 评分明细
<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { useFetch } from '@/utils/display'
import { BREAKDOWN_ORDER, STANDARD_STATES, scoreType, toPercent } from '@/utils/display'
import ProductCard from '@/components/ProductCard.vue'

const meta = useFetch(api.meta, { categories: [], brands: [], tags: [] })
const favs = useFetch(api.favorites, { count: 0, items: [] })

const form = ref({
  category: '',
  budget_min: 0,
  budget_max: 1000,
  preferences: [],
  brand: '',
  require_standard: true,
  top_n: 5,
})

const rawText = ref('')
const parsing = ref(false)

const recommending = ref(false)
const result = ref(null)
const errorMsg = ref('')
const detailTarget = ref(null) // 评分明细抽屉目标

const favIds = computed(() => new Set((favs.data?.items || []).map((p) => p.id)))

const breakdownOf = (it) => BREAKDOWN_ORDER.map((k) => ({ key: k, value: it.breakdown?.[k] ?? 0 }))

onMounted(() => {
  meta.run()
  favs.run()
})

// 自然语言 → 一键填充
async function parseText() {
  if (!rawText.value.trim()) return
  parsing.value = true
  try {
    const d = await api.parse(rawText.value.trim())
    if (!d.ok) throw new Error('解析失败')
    const data = d.data
    form.value.category = data.category || ''
    form.value.brand = data.brand || ''
    if (data.budget_min != null) form.value.budget_min = data.budget_min
    if (data.budget_max != null) form.value.budget_max = data.budget_max
    form.value.preferences = data.preferences || []
    ElMessage.success('已解析并填充表单')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    parsing.value = false
  }
}

async function runRecommend() {
  recommending.value = true
  errorMsg.value = ''
  result.value = null
  try {
    const payload = {
      category: form.value.category || null,
      budget_min: Number(form.value.budget_min) || 0,
      budget_max: Number(form.value.budget_max) || null,
      preferences: form.value.preferences || [],
      brand: form.value.brand || null,
      require_standard: form.value.require_standard,
      top_n: form.value.top_n || 5,
    }
    const d = await api.recommend(payload)
    if (!d.ok) throw new Error('推荐失败')
    result.value = d.data
    if (!d.data.items.length) {
      ElMessage.warning('没有符合条件的商品，请放宽预算或减少筛选条件')
    }
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    recommending.value = false
  }
}

async function toggleFavorite(p) {
  try {
    if (favIds.value.has(p.id)) {
      await api.removeFavorite(p.id)
    } else {
      await api.addFavorite(p.id)
    }
    favs.run()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

function showDetail(it) {
  detailTarget.value = it
}

const drawerVisible = computed({
  get: () => !!detailTarget.value,
  set: (v) => {
    if (!v) detailTarget.value = null
  },
})

function querySummary() {
  if (!result.value) return ''
  const q = result.value.query || {}
  const parts = [
    q.category ? `类别 ${q.category}` : '全部类别',
    `预算 ${q.budget_min ?? 0}~${q.budget_max ?? '不限'} 元`,
    q.brand ? `品牌 ${q.brand}` : '品牌不限',
  ]
  return parts.join(' · ')
}
</script>

<template>
  <div class="page">
    <h1 class="page-title">🤖 智能导购</h1>
    <p class="page-sub">输入需求，系统结合执行标准核验与多因素评分，生成可解释的个性化推荐</p>

    <el-row :gutter="16">
      <!-- 左侧：需求录入 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="panel">
          <template #header><b>需求录入</b></template>

          <el-form label-position="top">
            <el-form-item label="商品类别">
              <el-select v-model="form.category" clearable placeholder="全部类别" style="width: 100%">
                <el-option v-for="c in meta.data?.categories" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>

            <el-form-item label="预算区间（元）">
              <div class="budget-row">
                <el-input-number v-model="form.budget_min" :min="0" :step="10" controls-position="right" style="width: 48%" />
                <span class="tilde">~</span>
                <el-input-number v-model="form.budget_max" :min="0" :step="10" controls-position="right" style="width: 48%" />
              </div>
              <div class="hint">上限填 0 或清空表示不设上限</div>
            </el-form-item>

            <el-form-item label="偏好标签">
              <el-select v-model="form.preferences" multiple filterable placeholder="选择偏好" style="width: 100%">
                <el-option v-for="t in meta.data?.tags" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>

            <el-form-item label="品牌偏好">
              <el-select v-model="form.brand" clearable placeholder="不限" style="width: 100%">
                <el-option v-for="b in meta.data?.brands" :key="b" :label="b" :value="b" />
              </el-select>
            </el-form-item>

            <el-form-item label="推荐数量 Top-N">
              <el-slider v-model="form.top_n" :min="3" :max="10" show-stops />
            </el-form-item>

            <el-checkbox v-model="form.require_standard" class="std-check">
              仅看通过标准核验（现行标准）的商品
            </el-checkbox>

            <el-button
              type="primary"
              size="large"
              style="width: 100%; margin-top: 14px"
              :loading="recommending"
              @click="runRecommend"
            >
              🚀 开始智能推荐
            </el-button>
          </el-form>

          <el-divider><span class="divider-text">或</span></el-divider>

          <div class="nl-title">💬 一句话描述需求</div>
          <el-input
            v-model="rawText"
            type="textarea"
            :rows="3"
            placeholder="例如：150 以内 防漏耐高温的保鲜盒，最好是乐扣乐扣"
          />
          <el-button
            size="small"
            style="margin-top: 10px; width: 100%"
            :loading="parsing"
            @click="parseText"
          >
            ✨ 智能解析并填充
          </el-button>
        </el-card>
      </el-col>

      <!-- 右侧：结果区 -->
      <el-col :xs="24" :md="16">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="res-head">
              <b>推荐结果</b>
              <span v-if="result" class="res-meta">{{ querySummary() }} · {{ result.count }} 条</span>
            </div>
          </template>

          <el-alert v-if="errorMsg" :title="errorMsg" type="error" :closable="false" show-icon class="res-alert" />

          <div v-if="!result && !recommending" class="empty-state">
            <div class="empty-emoji">🎯</div>
            <p>填写左侧需求，点击「开始智能推荐」<br />推荐结果将显示在这里</p>
          </div>

          <div v-if="recommending" v-loading="true" class="loading-state" />

          <div v-if="result && result.items.length" class="rec-grid">
            <div v-for="(it, i) in result.items" :key="it.product.id" class="rec-item">
              <div class="rec-rank" :class="`rank-${i + 1}`">{{ i + 1 }}</div>
              <ProductCard
                :product="it.product"
                :score="it.score"
                :fav-ids="favIds"
                :hoverable="false"
                @toggle-favorite="toggleFavorite"
              />
              <div class="rec-reasons">
                <div class="rec-reasons-title">推荐理由</div>
                <div v-for="(r, k) in it.reasons.slice(0, 5)" :key="k" class="rec-reason">{{ r }}</div>
                <el-button text type="primary" size="small" @click="showDetail(it)">查看评分明细 →</el-button>
              </div>
            </div>
          </div>

          <el-empty v-if="result && !result.items.length && !recommending" description="没有符合条件的商品，请调整条件" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 评分明细抽屉 -->
      <el-drawer v-model="drawerVisible" :title="detailTarget?.product?.name || '评分明细'" size="360px">
      <div v-if="detailTarget">
        <div class="detail-score">
          <div class="detail-score-num" :class="`txt-${scoreType(detailTarget.score)}`">
            {{ detailTarget.score.toFixed(1) }}
          </div>
          <div class="detail-score-label">综合匹配度</div>
        </div>

        <el-divider content-position="left">维度得分</el-divider>
        <div v-for="d in breakdownOf(detailTarget)" :key="d.key" class="dim-row">
          <div class="dim-name">{{ d.key }}</div>
          <el-progress
            :percentage="toPercent(d.value)"
            :stroke-width="8"
            :show-text="false"
            style="flex: 1"
            :color="d.value >= 80 ? '#16A34A' : d.value >= 60 ? '#F59E0B' : '#E11D48'"
          />
          <div class="dim-val">{{ d.value.toFixed(1) }}</div>
        </div>

        <el-divider content-position="left">执行标准核验</el-divider>
        <div v-for="(ev, k) in detailTarget.standard_evidence" :key="k" class="std-box">
          <el-tag :type="(STANDARD_STATES[ev.status] || {}).type" size="small">{{ ev.status }}</el-tag>
          <span class="std-code">{{ ev.normalized || '未标注' }}</span>
          <div v-if="ev.record" class="std-rec">
            {{ ev.record.name }}（{{ ev.record.code }} · {{ ev.record.category }}）
          </div>
        </div>

        <el-divider content-position="left">全部推荐理由</el-divider>
        <div v-for="(r, k) in detailTarget.reasons" :key="k" class="rec-reason">{{ r }}</div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.panel {
  border-radius: 14px;
  border: 1px solid #eef0f4;
}
.budget-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.tilde {
  color: #a6afbd;
}
.hint {
  font-size: 12px;
  color: #a6afbd;
  margin-top: 4px;
}
.std-check {
  margin-top: 4px;
}
.divider-text {
  color: #a6afbd;
  font-size: 12px;
}
.nl-title {
  font-size: 13px;
  margin-bottom: 8px;
  font-weight: 500;
}

.res-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.res-meta {
  font-size: 12.5px;
  color: #8c96a6;
}
.res-alert {
  margin-bottom: 14px;
}
.empty-state {
  text-align: center;
  color: #a6afbd;
  padding: 60px 0;
}
.empty-emoji {
  font-size: 44px;
  margin-bottom: 10px;
}
.loading-state {
  height: 300px;
}

.rec-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
}
.rec-item {
  position: relative;
}
.rec-rank {
  position: absolute;
  top: -8px;
  left: -8px;
  z-index: 5;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.12);
}
.rank-1 { background: linear-gradient(135deg, #ffd76e, #ff9f1a); }
.rank-2 { background: linear-gradient(135deg, #d7dde6, #aeb8c6); }
.rank-3 { background: linear-gradient(135deg, #eab58a, #c98a55); }
.rank-4, .rank-5 { background: #8c96a6; }
.rec-reasons {
  margin-top: 10px;
  font-size: 13px;
}
.rec-reasons-title {
  font-weight: 600;
  margin-bottom: 6px;
  font-size: 13px;
}
.rec-reason {
  color: #49525f;
  line-height: 1.9;
  padding-left: 2px;
}

.detail-score {
  text-align: center;
  padding: 10px 0 4px;
}
.detail-score-num {
  font-size: 42px;
  font-weight: 800;
}
.detail-score-label {
  color: #8c96a6;
  font-size: 13px;
}
.dim-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 10px 0;
}
.dim-name {
  width: 60px;
  font-size: 12.5px;
  color: #49525f;
}
.dim-val {
  width: 44px;
  text-align: right;
  font-size: 13px;
  font-weight: 600;
}
.std-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 0;
}
.std-code {
  font-weight: 600;
  font-size: 13px;
}
.std-rec {
  font-size: 12px;
  color: #8c96a6;
}
.txt-danger { color: #e11d48; }
.txt-warning { color: #f59e0b; }
.txt-success { color: #16a34a; }
</style>
