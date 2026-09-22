// ❤️ 收藏商品
<script setup>
import { computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { useFetch } from '@/utils/display'
import ProductCard from '@/components/ProductCard.vue'

const favs = useFetch(api.favorites, { count: 0, items: [] })
const favIds = computed(() => new Set((favs.data?.items || []).map((p) => p.id)))

onMounted(() => favs.run())

async function toggleFavorite(p) {
  try {
    await api.removeFavorite(p.id)
    ElMessage.success(`已取消收藏「${p.name}」`)
    favs.run()
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<template>
  <div class="page">
    <h1 class="page-title">❤️ 收藏商品</h1>
    <p class="page-sub">共收藏 {{ favs.data?.count ?? 0 }} 件商品</p>

    <div v-loading="favs.loading">
      <el-empty v-if="!favs.loading && !favs.data?.items?.length" description="还没有收藏任何商品，去商品中心或智能导购看看吧" />
      <div v-else class="grid">
        <ProductCard
          v-for="p in favs.data?.items"
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
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
}
</style>
