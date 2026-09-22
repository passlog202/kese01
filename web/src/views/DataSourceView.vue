// 📥 数据源同步：一键从「拼多多开放平台 / Mock」抓取商品写入商品中心
<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api'

const loading = ref(false)
const keyword = ref('保鲜盒')
const limit = ref(40)
const result = ref(null)

const sourceLabel = computed(() => (result.value?.configuration?.source || 'mock'))
const sourceText = computed(() =>
  sourceLabel.value === 'pdd' ? '拼多多开放平台（真实数据）' : 'Mock 种子数据（演示）',
)

async function sync() {
  loading.value = true
  result.value = null
  try {
    const res = await api.syncDataSource(keyword.value.trim(), limit.value)
    result.value = res.data
    ElMessage.success(`同步完成：入库 ${res.data.fetched} 条`)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="intro">
      <div class="intro-title">📥 数据源同步</div>
      <div class="intro-sub">
        一键从当前数据源抓取商品，写入「商品中心」，供智能导购 / 对比 / 收藏使用。
        当前数据源为 <b>{{ sourceText }}</b>。
      </div>
    </el-card>

    <el-card shadow="never">
      <div class="form-row">
        <div class="form-item">
          <label>搜索关键词</label>
          <el-input v-model="keyword" placeholder="如：保鲜盒 / 保温杯" size="large" />
        </div>
        <div class="form-item">
          <label>抓取条数（≤ 200）</label>
          <el-input-number v-model="limit" :min="1" :max="200" size="large" style="width: 100%" />
        </div>
        <el-button type="primary" size="large" class="sync-btn" :loading="loading" @click="sync">
          {{ loading ? '抓取中…' : '开始同步' }}
        </el-button>
      </div>

      <el-alert
        v-if="result && result.configuration?.source === 'pdd' && result.configuration?.configured === false"
        title="未配置拼多多凭据"
        type="warning"
        :closable="false"
        show-icon
        class="tip"
        description="后端未设置 KESE_PDD_CLIENT_ID / KESE_PDD_CLIENT_SECRET，切换 pdd 数据源会返回错误。请先在开放平台申请应用并在后端环境变量里配置。"
      />

      <el-alert
        title="真实数据说明"
        type="info"
        :closable="false"
        show-icon
        class="tip"
        description="拼多多搜索接口不返回执行标准号/材质等字段，这些字段会如实标记为「未标注」，不会编造。接入 OCR 识别包装标准号后即可补齐核验链路。"
      />

      <el-table v-if="result" :data="[{ ...result }]" border class="result-table" size="large">
        <el-table-column label="数据源" width="120">
          <template #default>{{ result.source }}</template>
        </el-table-column>
        <el-table-column label="关键词" prop="keyword" width="150" />
        <el-table-column label="抓取入库" prop="fetched" width="110" />
        <el-table-column label="跳过" prop="skipped" width="90" />
        <el-table-column label="商品总数" prop="product_total" width="110" />
        <el-table-column label="耗时(ms)" prop="elapsed_ms" width="110" />
        <el-table-column label="信息">
          <template #default><span v-for="m in result.messages" :key="m" class="msg">{{ m }}</span></template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.page {
  max-width: 880px;
  margin: 0 auto;
  padding: 24px 20px;
}
.intro {
  margin-bottom: 16px;
}
.intro-title {
  font-size: 18px;
  font-weight: 700;
}
.intro-sub {
  margin-top: 6px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.7;
}
.form-row {
  display: flex;
  gap: 14px;
  align-items: flex-end;
  flex-wrap: wrap;
}
.form-item {
  flex: 1;
  min-width: 180px;
}
.form-item label {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 6px;
}
.sync-btn {
  min-width: 120px;
}
.tip {
  margin-top: 16px;
}
.result-table {
  margin-top: 18px;
}
.msg {
  display: inline-block;
  margin-right: 8px;
}
</style>
