<template>
  <el-container class="layout">
    <el-header class="header">
      <span class="title">AI Brain</span>
      <div class="nav">
        <router-link to="/" class="nav-item" exact-active-class="router-link-active">
          首页
        </router-link>
        <template v-if="token">
          <router-link to="/chat" class="nav-item">对话</router-link>
          <router-link to="/knowledge-bases" class="nav-item">知识库</router-link>
          <router-link to="/tasks" class="nav-item">任务</router-link>
          <router-link to="/stats" class="nav-item">统计</router-link>
          <router-link to="/profile" class="nav-item">个人资料</router-link>
          <router-link to="/profile" class="user-chip">
            <el-avatar :size="28" :src="avatarUrl || undefined" class="user-avatar">
              {{ user?.username?.[0] ?? '?' }}
            </el-avatar>
            <span class="username">{{ user?.username }}</span>
          </router-link>
          <el-button link type="primary" @click="handleLogout">退出</el-button>
        </template>
        <template v-else>
          <router-link to="/login" class="nav-item">登录</router-link>
          <router-link to="/register" class="nav-item">注册</router-link>
        </template>
        <span class="theme-toggle" :title="isDark ? '切换到浅色模式' : '切换到深色模式'" @click="handleToggleTheme">
          {{ isDark ? '☀️' : '🌙' }}
        </span>
      </div>
    </el-header>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { currentTheme, toggleTheme } from '../utils/theme'
import { loadAvatarUrl } from '../api/user'

const authStore = useAuthStore()
const { token, user } = storeToRefs(authStore)
const router = useRouter()
const isDark = ref(currentTheme() === 'dark')
const avatarUrl = ref('')

// 页面刷新后恢复用户信息
if (authStore.token && !authStore.user) {
  authStore.loadUser().catch(() => authStore.logout())
}

// 用户资料（含头像）就绪后加载头像图片
watch(
  () => user.value?.avatar,
  async (name) => {
    if (!name) {
      avatarUrl.value = ''
      return
    }
    try {
      avatarUrl.value = await loadAvatarUrl(name)
    } catch {
      avatarUrl.value = ''
    }
  },
  { immediate: true },
)

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

function handleToggleTheme() {
  isDark.value = toggleTheme() === 'dark'
}
</script>

<style scoped>
/* 视口锁定：header 固定、main 填满剩余空间，页面内部自行滚动 */
.layout {
  height: 100vh;
  overflow: hidden;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--el-border-color-light);
  flex-shrink: 0;
}
.title {
  font-size: 20px;
  font-weight: 700;
  color: var(--el-color-primary);
}
.nav {
  display: flex;
  align-items: center;
  gap: 18px;
}
.nav-item {
  color: var(--el-text-color-primary);
  text-decoration: none;
}
.nav-item.router-link-active {
  color: var(--el-color-primary);
  font-weight: 600;
}
.username {
  color: var(--el-text-color-secondary);
}
.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
}
.user-avatar {
  background: var(--el-color-primary);
  color: #fff;
  font-weight: 600;
  flex-shrink: 0;
}
.theme-toggle {
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  padding: 4px;
  border-radius: 6px;
}
.theme-toggle:hover {
  background: var(--el-fill-color-light);
}
.main {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.main > :deep(*) {
  flex: 1;
  min-height: 0;
}
</style>
