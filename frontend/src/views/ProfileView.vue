<template>
  <div class="profile-page">
    <el-card class="avatar-card">
      <template #header>头像</template>
      <div class="avatar-row">
        <el-avatar :size="96" :src="avatarUrl || undefined" class="avatar">
          {{ user?.username?.[0] ?? '?' }}
        </el-avatar>
        <div class="avatar-actions">
          <el-button type="primary" :loading="uploading" @click="pickAvatar">
            上传头像
          </el-button>
          <el-button v-if="user?.avatar" type="danger" plain @click="handleDelete">
            删除头像
          </el-button>
          <div class="avatar-tip">支持 PNG / JPG / WebP，≤5MB，自动裁剪为方形</div>
        </div>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          style="display: none"
          @change="onPickFile"
        />
      </div>
    </el-card>

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
          {{ formatDate(user?.created_at) }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { deleteAvatar, loadAvatarUrl, uploadAvatar } from '../api/user'

const authStore = useAuthStore()
const { user } = storeToRefs(authStore)
const uploading = ref(false)
const avatarUrl = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)

onMounted(() => {
  loadUserInfo()
})

async function loadUserInfo() {
  if (!authStore.user) {
    try {
      await authStore.loadUser()
    } catch {
      authStore.logout()
      return
    }
  }
  if (user.value?.avatar) {
    try {
      avatarUrl.value = await loadAvatarUrl(user.value.avatar)
    } catch {
      avatarUrl.value = ''
    }
  }
}

function pickAvatar() {
  fileInputRef.value?.click()
}

/** ISO 时间戳格式化为本地可读时间（避免原始字符串"乱码"） */
function formatDate(iso: string | undefined | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function onPickFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) {
    ElMessage.warning('未读取到文件，请重新选择（建议使用普通图片文件）')
    return
  }
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('仅支持图片文件')
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.warning('图片超过 10MB，请先压缩')
    return
  }
  uploading.value = true
  try {
    const cropped = await cropSquare(file, 256)
    const name = await uploadAvatar(cropped)
    user.value!.avatar = name
    avatarUrl.value = URL.createObjectURL(cropped)
    ElMessage.success('头像已更新')
  } catch (err) {
    ElMessage.error((err as Error).message || '头像上传失败')
  } finally {
    uploading.value = false
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm('确定删除当前头像？', '删除头像', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteAvatar()
    user.value!.avatar = null
    avatarUrl.value = ''
    ElMessage.success('头像已删除')
  } catch (err) {
    ElMessage.error((err as Error).message || '删除失败')
  }
}

/** 中心方形裁剪 + 缩放（头像统一尺寸）；8 秒超时兜底防静默卡死 */
function cropSquare(file: File, size: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('图片处理超时，请换一张图片')), 8000)
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      clearTimeout(timer)
      URL.revokeObjectURL(url)
      const side = Math.min(img.width, img.height)
      const sx = (img.width - side) / 2
      const sy = (img.height - side) / 2
      const canvas = document.createElement('canvas')
      canvas.width = size
      canvas.height = size
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('浏览器不支持图片处理'))
        return
      }
      ctx.drawImage(img, sx, sy, side, side, 0, 0, size, size)
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error('图片裁剪失败'))),
        'image/jpeg',
        0.85,
      )
    }
    img.onerror = () => {
      clearTimeout(timer)
      URL.revokeObjectURL(url)
      reject(new Error('图片读取失败，请换一张图片'))
    }
    img.src = url
  })
}
</script>

<style scoped>
.profile-page {
  max-width: 680px;
  margin: 0 auto;
  padding: 24px 20px;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
/* 内容整组垂直居中 */
.profile-page::before {
  content: '';
  flex-grow: 3.7;
  flex-basis: 0;
  flex-shrink: 0;
}
.profile-page::after {
  content: '';
  flex-grow: 6.3;
  flex-basis: 0;
  flex-shrink: 0;
}
.avatar-row {
  display: flex;
  align-items: center;
  gap: 20px;
}
.avatar {
  background: var(--el-color-primary);
  color: #fff;
  font-size: 32px;
  font-weight: 600;
  flex-shrink: 0;
}
.avatar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.avatar-tip {
  font-size: 13.5px;
  color: var(--el-text-color-secondary);
  width: 100%;
}
</style>
