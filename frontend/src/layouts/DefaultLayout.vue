<template>
  <el-container class="layout">
    <el-header class="header">
      <span class="title">AI Brain</span>
      <div class="nav">
        <router-link to="/" class="nav-item">首页</router-link>
        <template v-if="token">
          <router-link to="/chat" class="nav-item">对话</router-link>
          <router-link to="/knowledge-bases" class="nav-item">知识库</router-link>
          <router-link to="/tasks" class="nav-item">任务</router-link>
          <router-link to="/stats" class="nav-item">统计</router-link>
          <router-link to="/profile" class="nav-item">个人资料</router-link>
          <span class="nav-item username">{{ user?.username }}</span>
          <el-button link type="primary" @click="handleLogout">退出</el-button>
        </template>
        <template v-else>
          <router-link to="/login" class="nav-item">登录</router-link>
          <router-link to="/register" class="nav-item">注册</router-link>
        </template>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const { token, user } = storeToRefs(authStore)
const router = useRouter()

// 页面刷新后恢复用户信息
if (authStore.token && !authStore.user) {
  authStore.loadUser().catch(() => authStore.logout())
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #eee;
}
.title {
  font-size: 18px;
  font-weight: 600;
}
.nav {
  display: flex;
  align-items: center;
  gap: 16px;
}
.nav-item {
  color: #333;
  text-decoration: none;
}
.username {
  color: #999;
}
</style>
