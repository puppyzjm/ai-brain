<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <template #header>注册 AI Brain</template>
      <el-form label-position="top" @submit.prevent="handleRegister">
        <el-form-item label="用户名（3-50 字符）">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱（可选）">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码（至少 6 位）">
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
          注册
        </el-button>
      </el-form>
      <p class="tip">
        已有账号？
        <router-link to="/login">去登录</router-link>
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
const form = reactive({ username: '', email: '', password: '' })

async function handleRegister() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await authStore.registerUser(
      form.username,
      form.email || undefined,
      form.password,
    )
    ElMessage.success('注册成功，请登录')
    router.push('/login')
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
