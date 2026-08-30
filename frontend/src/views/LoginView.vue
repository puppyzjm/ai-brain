<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <template #header>登录 AI Brain</template>
      <el-form label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="用户名 / 邮箱">
          <el-input v-model="form.account" placeholder="请输入用户名或邮箱" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
          />
        </el-form-item>
        <el-button
          type="primary"
          native-type="submit"
          :loading="loading"
          style="width: 100%"
        >
          登录
        </el-button>
      </el-form>
      <p class="tip">
        还没有账号？
        <router-link to="/register">去注册</router-link>
      </p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const form = reactive({ account: '', password: '' })

async function handleLogin() {
  if (!form.account || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    await authStore.login(form.account, form.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  overflow-y: auto;
  padding: 0 20px;
}
/* 位置偏上：上留白 3.7 / 下留白 6.3 */
.auth-page::before {
  content: '';
  flex-grow: 3.7;
  flex-basis: 0;
  flex-shrink: 0;
}
.auth-page::after {
  content: '';
  flex-grow: 6.3;
  flex-basis: 0;
  flex-shrink: 0;
}
.auth-card {
  width: 420px;
}
.tip {
  text-align: center;
  margin-top: 12px;
}
</style>
