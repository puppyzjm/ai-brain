<template>
  <div class="profile-page">
    <el-card>
      <template #header>个人资料</template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">
          {{ user?.username ?? '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="邮箱">
          {{ user?.email ?? '未填写' }}
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">
          {{ user?.created_at ?? '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const { user } = storeToRefs(authStore)

onMounted(() => {
  if (!authStore.user) {
    authStore.loadUser().catch(() => authStore.logout())
  }
})
</script>

<style scoped>
.profile-page {
  max-width: 640px;
  margin: 0 auto;
}
</style>
