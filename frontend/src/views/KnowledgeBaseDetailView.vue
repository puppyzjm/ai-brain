<template>
  <div class="doc-page">
    <div class="doc-header">
      <el-button link @click="$router.push('/knowledge-bases')">← 返回知识库</el-button>
      <h2>文档管理</h2>
    </div>

    <el-card class="upload-card">
      <el-upload
        drag
        :auto-upload="true"
        :show-file-list="false"
        :http-request="handleUpload"
        accept=".pdf,.txt,.md"
      >
        <div class="upload-inner">
          <p>将 PDF / TXT / Markdown 文件拖到此处，或点击上传</p>
          <p class="upload-tip">单个文件不超过 20MB</p>
        </div>
      </el-upload>
    </el-card>

    <el-table :data="documents" style="width: 100%" v-loading="loading">
      <el-table-column prop="filename" label="文件名" min-width="200" show-overflow-tooltip />
      <el-table-column label="类型" width="90">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.file_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="分块数" width="90">
        <template #default="{ row }">{{ row.chunk_count }}</template>
      </el-table-column>
      <el-table-column label="大小" width="100">
        <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'ready'"
            size="small"
            type="success"
            :loading="summarizingId === row.id"
            @click="handleSummarize(row)"
          >
            总结
          </el-button>
          <el-button
            v-if="row.status === 'failed'"
            size="small"
            type="warning"
            @click="handleReprocess(row)"
          >
            重新解析
          </el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!documents.length && !loading" description="暂无文档，上传第一个文件吧" />

    <el-dialog v-model="summaryVisible" title="文档总结" width="640px">
      <div v-loading="summarizingId !== null">
        <div class="summary-body" v-html="renderMarkdown(summaryText)" />
      </div>
      <template #footer>
        <el-button @click="summaryVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import {
  deleteDocument,
  listDocuments,
  reprocessDocument,
  summarizeDocument,
  uploadDocument,
  type Document,
} from '../api/knowledgeBase'
import { renderMarkdown } from '../utils/markdown'

const route = useRoute()
const kbId = Number(route.params.id)
const documents = ref<Document[]>([])
const loading = ref(false)
const summarizingId = ref<number | null>(null)
const summaryVisible = ref(false)
const summaryText = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await load()
  startPollingIfNeeded()
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

async function load() {
  loading.value = true
  try {
    documents.value = await listDocuments(kbId)
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

async function handleUpload(options: UploadRequestOptions) {
  try {
    await uploadDocument(kbId, options.file as File)
    ElMessage.success('上传成功，正在解析…')
    await load()
    startPollingIfNeeded()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function handleDelete(row: Document) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.filename}」？`, '删除', { type: 'warning' })
    await deleteDocument(row.id)
    ElMessage.success('已删除')
    load()
  } catch {
    /* 用户取消 */
  }
}

async function handleReprocess(row: Document) {
  try {
    await reprocessDocument(row.id)
    ElMessage.success('已重新开始解析')
    await load()
    startPollingIfNeeded()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function handleSummarize(row: Document) {
  if (summarizingId.value !== null) return
  summarizingId.value = row.id
  summaryText.value = ''
  summaryVisible.value = true
  try {
    const result = await summarizeDocument(row.id)
    summaryText.value = result.summary
  } catch (e) {
    summaryText.value = ''
    ElMessage.error((e as Error).message)
  } finally {
    summarizingId.value = null
  }
}

function startPollingIfNeeded() {
  const hasParsing = documents.value.some(
    (d) => d.status === 'uploaded' || d.status === 'parsing',
  )
  if (hasParsing && !pollTimer) {
    pollTimer = setInterval(async () => {
      await load()
      const stillParsing = documents.value.some(
        (d) => d.status === 'uploaded' || d.status === 'parsing',
      )
      if (!stillParsing && pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
      }
    }, 2000)
  }
}

function statusText(status: string): string {
  const map: Record<string, string> = {
    uploaded: '待解析',
    parsing: '解析中',
    ready: '已完成',
    failed: '失败',
  }
  return map[status] ?? status
}

function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'ready') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'parsing') return 'warning'
  return 'info'
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<style scoped>
.doc-page {
  max-width: 900px;
  margin: 0 auto;
}
.doc-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.upload-card {
  margin-bottom: 20px;
}
.upload-inner {
  padding: 12px 0;
}
.upload-tip {
  color: #999;
  font-size: 12px;
}
.summary-body {
  line-height: 1.7;
  font-size: 14px;
  max-height: 60vh;
  overflow-y: auto;
}
</style>
