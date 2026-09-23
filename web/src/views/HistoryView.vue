// 🕘 推荐历史
<script setup>
import { onMounted } from 'vue'
import { api } from '@/api'
import { useFetch, STANDARD_STATES, scoreType } from '@/utils/display'
import { fmtTime, parseQuery, parseResult } from '@/utils/format'

const history = useFetch(() => api.history(100), { count: 0, items: [] })
onMounted(() => history.run())
</script>

<template>
  <div class="page">
    <h1 class="page-title">🕘 推荐历史</h1>
    <p class="page-sub">SQLite 持久化的历史推荐记录，方便演示与回看</p>

    <div v-loading="history.loading">
      <el-empty v-if="!history.loading && !history.data?.items?.length" description="暂无推荐记录，先去「智能导购」生成一次吧" />

      <el-timeline v-else class="timeline">
        <el-timeline-item
          v-for="r in history.data?.items"
          :key="r.id"
          :timestamp="fmtTime(r.created_at)"
          type="primary"
          hollow
        >
          <el-card shadow="never" class="hist-card">
            <div class="hist-meta">
              <el-tag type="info" effect="plain">类别 {{ parseQuery(r.query_json).category || '全部' }}</el-tag>
              <el-tag type="info" effect="plain">
                预算 {{ parseQuery(r.query_json).budget_min ?? 0 }} ~ {{ parseQuery(r.query_json).budget_max ?? '不限' }} 元
              </el-tag>
              <el-tag type="info" effect="plain">品牌 {{ parseQuery(r.query_json).brand || '不限' }}</el-tag>
              <el-tag type="warning" effect="plain">推荐 {{ parseResult(r.result_json).items?.length ?? 0 }} 件</el-tag>
            </div>

            <div v-for="it in parseResult(r.result_json).items || []" :key="it.product.id" class="hist-item">
              <span class="hist-name">{{ it.product.name }}</span>
              <span class="hist-price">{{ '¥' + it.product.price.toFixed(2) }}</span>
              <el-tag
                :type="(STANDARD_STATES[it.standard_evidence?.[0]?.status] || {}).type"
                size="small"
                effect="light"
              >{{ it.standard_evidence?.[0]?.status }}</el-tag>
              <span class="hist-score" :class="`txt-${scoreType(it.score)}`">{{ it.score.toFixed(1) }}%</span>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </div>
  </div>
</template>

<style scoped>
.timeline {
  padding-left: 6px;
}
.hist-card {
  border-radius: 12px;
  border: 1px solid #eef0f4;
  margin-bottom: 6px;
}
.hist-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.hist-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 0;
  border-top: 1px dashed #eef0f4;
  font-size: 13px;
}
.hist-name {
  flex: 1;
  font-weight: 500;
}
.hist-price {
  color: #e11d48;
  font-weight: 700;
}
.hist-score {
  font-weight: 700;
  min-width: 48px;
  text-align: right;
}
.txt-danger { color: #e11d48; }
.txt-warning { color: #f59e0b; }
.txt-success { color: #16a34a; }
</style>
