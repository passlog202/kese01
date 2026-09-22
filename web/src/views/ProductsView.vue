// 🛍️ 商品中心：搜索 / 筛选 / 收藏
<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { useFetch } from '@/utils/display'
import ProductCard from '@/components/ProductCard.vue'

const meta = useFetch(api.meta, { categories: [], brands: [], tags: [] })
const favs = useFetch(api.favorites, { count: 0, items: [] })
const products = useFetch(api.products, { count: 0, items: [] })

const category = ref('')
const keyword = ref('')

const favIds = computed(() => new Set((favs.data?.items || []).map((p) => p.id)))

const loadProducts = () =>
  products.run({ category: category.value || undefined, keyword: keyword.value || undefined })

const loadFavs = () => favs.run()

onMounted(() => {
  meta.run()
  loadProducts()
  loadFavs()
})

// 输入关键词防抖
let timer = null
watch(keyword, () => {
  clearTimeout(timer)
  timer = setTimeout(loadProducts, 300)
})

const toggleFavorite = async (p) => {
  try {
    if (favIds.value.has(p.id)) {
      await api.removeFavorite(p.id)
      ElMessage.success(`已取消收藏「${p.name}」`)
    } else {
      await api.addFavorite(p.id)
      ElMessage.success(`已收藏「${p.name}」`)
    }
    loadFavs()
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<template>
  <div class="page">
    <h1 class="page-title">🛍️ 商品中心</h1>
    <p class="page-sub">浏览、搜索、按类别筛选商品，查看执行标准核验状态</p>

    <el-card shadow="never" class="filter-bar">
      <div class="filter-row">
        <el-select v-model="category" clearable placeholder="全部类别" style="width: 180px" @change="loadProducts">
          <el-option v-for="c in meta.data?.categories" :key="c" :label="c" :value="c" />
        </el-select>
        <el-input
          v-model="keyword"
          clearable
          placeholder="搜索商品 / 品牌 / 标签"
          style="flex: 1; max-width: 420px"
        >
          <template #prefix>🔍</template>
        </el-input>
        <span class="count">共 {{ products.data?.count ?? 0 }} 件商品</span>
      </div>
    </el-card>

    <div v-loading="products.loading" class="grid-wrap">
      <el-empty v-if="products.error" :description="products.error" />
      <el-empty
        v-else-if="!products.loading && !(products.data?.items || []).length"
        description="没有符合条件的商品"
      />
      <div v-else class="grid">
        <ProductCard
          v-for="p in products.data?.items"
          :key="p.id"
          :product="p"
          :fav-ids="favIds"
          @toggle-favorite="toggleFavorite"
        />
      </div>
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
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.count {
  margin-left: auto;
  color: #8c96a6;
  font-size: 13px;
}
.grid-wrap {
  min-height: 260px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
}
</style>
