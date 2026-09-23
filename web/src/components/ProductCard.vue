// 🛍️ 商品卡片：商品信息 + 标准核验状态 + 收藏操作 + 评分/销量
// 复用于商品中心、推荐结果、收藏列表等多个页面。

<script setup>
import { computed } from 'vue'
import { STANDARD_STATES, scoreType } from '@/utils/display'
import { fmtPrice, fmtNumber } from '@/utils/format'

const props = defineProps({
  product: { type: Object, default: null },
  favIds: { type: Set, default: () => new Set() },
  score: { type: Number, default: null }, // 推荐模式下的匹配度
  showFavorite: { type: Boolean, default: true },
  loading: { type: Boolean, default: false },
  hoverable: { type: Boolean, default: true },
})

const emit = defineEmits(['toggle-favorite'])

const statusMeta = computed(
  () => STANDARD_STATES[props.product?.standard_status] || STANDARD_STATES['未标注'],
)
const isFav = computed(() => props.favIds.has(props.product?.id))
const scorePercent = computed(() => Math.max(0, Math.min(100, Number(props.score) || 0)))
const scoreColor = computed(() => (props.score == null ? '' : scoreType(props.score)))
</script>

<template>
  <el-card class="pcard" :class="{ hoverable }" shadow="hover">
    <el-skeleton v-if="loading" :rows="5" animated />

    <template v-else-if="product">
      <div class="pcard-head">
        <span class="pcard-cat">{{ product.category }}</span>
        <el-tag :type="statusMeta.type" size="small" effect="light" round>
          {{ statusMeta.icon }} 标准 {{ statusMeta.label }}
        </el-tag>
      </div>

      <div class="pcard-name" :title="product.name">{{ product.name }}</div>
      <div class="pcard-desc">{{ product.description || '暂无描述' }}</div>

      <div class="pcard-tags">
        <el-tag v-for="t in (product.tags || []).slice(0, 4)" :key="t" size="small" class="pcard-tag" effect="plain">
          {{ t }}
        </el-tag>
      </div>

      <div class="pcard-meta">
        <span>品牌 {{ product.brand }}</span>
        <span>材质 {{ product.material }}</span>
        <span>店铺 {{ product.shop_type }}</span>
      </div>

      <el-divider class="pcard-divider" />

      <div class="pcard-bottom">
        <div>
          <div class="pcard-price">{{ fmtPrice(product.price) }}</div>
          <div class="pcard-small">评分 {{ product.rating }} · 销量 {{ fmtNumber(product.sales) }}</div>
        </div>
        <el-button
          v-if="showFavorite"
          :type="isFav ? 'danger' : 'default'"
          circle
          @click.stop="emit('toggle-favorite', product)"
          :title="isFav ? '取消收藏' : '收藏'"
        >
          {{ isFav ? '★' : '☆' }}
        </el-button>
      </div>

      <div v-if="score != null" class="pcard-score">
        <div class="pcard-score-top">
          <span>综合匹配度</span>
          <b :class="`txt-${scoreColor}`">{{ scorePercent.toFixed(1) }}%</b>
        </div>
        <el-progress
          :percentage="scorePercent"
          :stroke-width="8"
          :show-text="false"
          :color="scoreColor === 'danger' ? '#E11D48' : scoreColor === 'warning' ? '#F59E0B' : '#16A34A'"
        />
      </div>
    </template>
  </el-card>
</template>

<style scoped>
.pcard {
  border-radius: 14px;
  border: 1px solid #eef0f4;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  width: 100%;
}
.pcard.hoverable:hover {
  transform: translateY(-4px);
}
.pcard-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.pcard-cat {
  font-size: 12px;
  color: #a6afbd;
}
.pcard-name {
  font-weight: 600;
  font-size: 15px;
  line-height: 1.4;
  min-height: 42px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.pcard-desc {
  color: #8c96a6;
  font-size: 12.5px;
  margin: 6px 0 10px;
  min-height: 18px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.pcard-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  min-height: 24px;
  margin-bottom: 10px;
}
.pcard-tag {
  border-radius: 6px;
}
.pcard-meta {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: #8c96a6;
  flex-wrap: wrap;
}
.pcard-divider {
  margin: 10px 0;
}
.pcard-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pcard-price {
  font-size: 18px;
  font-weight: 700;
  color: #e11d48;
}
.pcard-small {
  font-size: 12px;
  color: #a6afbd;
  margin-top: 2px;
}
.pcard-score {
  margin-top: 12px;
  padding: 10px 12px;
  background: #fafbfd;
  border-radius: 10px;
}
.pcard-score-top {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 6px;
}
.txt-danger { color: #e11d48; }
.txt-warning { color: #f59e0b; }
.txt-success { color: #16a34a; }
</style>
