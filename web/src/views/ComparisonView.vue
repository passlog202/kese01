// ⚖️ 商品对比：同类别商品并排对比，指标最优高亮
<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '@/api'
import { useFetch } from '@/utils/display'
import { STANDARD_STATES, scoreType } from '@/utils/display'
import { fmtPrice, fmtNumber } from '@/utils/format'

const meta = useFetch(api.meta, { categories: [], brands: [], tags: [] })
const products = useFetch(api.products, { count: 0, items: [] })

const category = ref('')
const chosen = ref([])

const list = computed(() => products.data?.items || [])
const byId = computed(() => Object.fromEntries(list.value.map((p) => [p.id, p])))

const rows = [
  { key: 'price', label: '价格', fmt: (v) => fmtPrice(v), better: 'min' },
  { key: 'rating', label: '评分', fmt: (v) => v, better: 'max' },
  { key: 'sales', label: '销量', fmt: (v) => fmtNumber(v), better: 'max' },
  { key: 'material', label: '材质', fmt: (v) => v, better: null },
  { key: 'brand', label: '品牌', fmt: (v) => v, better: null },
  { key: 'shop_type', label: '店铺类型', fmt: (v) => v, better: null },
  { key: 'standard_status', label: '执行标准状态', fmt: (v) => v, better: null },
  { key: 'standard_code', label: '执行标准', fmt: (v) => v || '未标注', better: null },
]

function load() {
  products.run({ category: category.value || undefined })
  chosen.value = []
}
onMounted(() => {
  meta.run()
  load()
})
watch(category, load)

function bestValue(row) {
  if (!row.better || chosen.value.length < 2) return null
  const vals = chosen.value.map((id) => byId.value[id]?.[row.key])
  if (vals.some((v) => v == null)) return null
  return row.better === 'min' ? Math.min(...vals) : Math.max(...vals)
}

function isBest(row, id) {
  const b = bestValue(row)
  if (b == null) return false
  return byId.value[id]?.[row.key] === b
}
</script>

<template>
  <div class="page">
    <h1 class="page-title">⚖️ 商品对比</h1>
    <p class="page-sub">选择类别，最多勾选 4 件商品并排对比，指标最优自动高亮</p>

    <el-card shadow="never" class="filter-bar">
      <div class="filter-row">
        <el-select v-model="category" placeholder="选择类别" style="width: 180px">
          <el-option v-for="c in meta.data?.categories" :key="c" :label="c" :value="c" />
        </el-select>
        <el-checkbox-group v-model="chosen" :max="4" class="chk-group">
          <el-checkbox v-for="p in list" :key="p.id" :value="p.id">
            {{ p.name }}
          </el-checkbox>
        </el-checkbox-group>
      </div>
    </el-card>

    <div v-loading="products.loading">
      <el-empty v-if="!chosen.length && !products.loading" description="请先选择类别并勾选要对比的商品" />

      <el-card v-else shadow="never" class="cmp-card">
        <el-table :data="rows" :show-header="false" border class="cmp-table">
          <el-table-column label="指标" width="110" fixed>
            <template #default="{ row }">
              <b>{{ row.label }}</b>
            </template>
          </el-table-column>
          <el-table-column v-for="id in chosen" :key="id" min-width="140">
            <template #header>
              <div class="cmp-head">
                <div class="cmp-name">{{ byId[id]?.name }}</div>
                <el-tag :type="(STANDARD_STATES[byId[id]?.standard_status] || {}).type" size="small" effect="light">
                  {{ (STANDARD_STATES[byId[id]?.standard_status] || {}).label }}
                </el-tag>
              </div>
            </template>
            <template #default="{ row }">
              <div class="cmp-cell" :class="{ best: isBest(row, id) }">
                <span :class="{ price: row.key === 'price' }">{{ row.fmt(byId[id]?.[row.key]) }}</span>
                <span v-if="isBest(row, id)" class="crown">🏆</span>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <div class="cmp-note">🏆 表示该指标中最优的商品（价格越低越好，其余越高越好）</div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.filter-bar {
  border-radius: 14px;
  border: 1px solid #eef0f4;
  margin-bottom: 18px;
}
.filter-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}
.chk-group {
  flex: 1;
  min-width: 320px;
}
.cmp-card {
  border-radius: 14px;
  border: 1px solid #eef0f4;
}
.cmp-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.cmp-name {
  font-size: 12.5px;
  line-height: 1.4;
  max-width: 220px;
}
.cmp-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.cmp-cell.best {
  font-weight: 700;
  color: #16a34a;
}
.cmp-note {
  font-size: 12px;
  color: #a6afbd;
  margin-top: 10px;
}
</style>
