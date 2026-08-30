<template>
  <div class="chat-page">
    <!-- 会话侧边栏 -->
    <div class="sidebar">
      <el-button type="primary" style="width: 100%" @click="startNewChat">
        + 新建对话
      </el-button>
      <div class="conv-list">
        <div
          v-for="c in conversations"
          :key="c.id"
          class="conv-item"
          :class="{ active: c.id === activeId }"
          @click="selectConversation(c)"
        >
          <span class="conv-title">{{ c.title }}</span>
          <el-dropdown
            trigger="click"
            @command="(cmd: string) => handleConvAction(cmd, c)"
          >
            <span class="conv-menu" @click.stop>⋯</span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="rename">重命名</el-dropdown-item>
                <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <el-empty v-if="!conversations.length" description="暂无对话" :image-size="60" />
      </div>
    </div>

    <!-- 消息主区 -->
    <div class="chat-main">
      <!-- 知识库选择（RAG 模式开关）-->
      <div class="rag-bar">
        <el-select
          v-model="selectedKbIds"
          multiple
          collapse-tags
          clearable
          filterable
          placeholder="选择知识库进行 RAG 问答（不选为普通对话）"
          style="width: 100%"
        >
          <el-option
            v-for="kb in kbs"
            :key="kb.id"
            :label="kb.name"
            :value="kb.id"
          />
        </el-select>
      </div>

      <div ref="messageListRef" class="message-list">
        <div v-for="m in messages" :key="m.id" class="msg-row" :class="m.role">
          <div class="msg-bubble">
            <div
              v-if="m.role === 'user' && m._imageUrls?.length"
              class="msg-images"
            >
              <el-image
                v-for="(url, i) in m._imageUrls"
                :key="i"
                :src="url"
                :preview-src-list="m._imageUrls"
                preview-teleported
                fit="cover"
                class="msg-img"
              />
            </div>
            <div v-if="m.role === 'assistant'" class="md-body" v-html="renderMarkdown(m.content)" />
            <div v-else class="plain-body">{{ m.content }}</div>
          </div>
        </div>
        <div v-if="streaming" class="msg-row assistant">
          <div class="msg-bubble">
            <div v-if="toolNotice" class="tool-notice">{{ toolNotice }}</div>
            <div v-else class="md-body" v-html="renderMarkdown(streamText)" />
          </div>
        </div>
        <el-empty
          v-if="!messages.length && !streaming"
          description="开始你的第一段对话吧"
          :image-size="80"
        />
      </div>

      <!-- 引用来源 -->
      <div v-if="currentSources.length" class="sources-bar">
        <div class="sources-title">参考来源</div>
        <div v-for="(s, i) in currentSources" :key="s.chunk_id" class="source-item">
          <span class="source-index">[{{ i + 1 }}]</span>
          <span class="source-file">{{ s.filename }}</span>
          <span v-if="s.page" class="source-page">第 {{ s.page }} 页</span>
          <span class="source-sim">相似度 {{ (s.similarity * 100).toFixed(1) }}%</span>
          <div class="source-preview">{{ s.content_preview }}…</div>
        </div>
      </div>

      <div class="input-area">
        <!-- 待发送图片预览 -->
        <div v-if="pendingImages.length" class="pending-images">
          <div v-for="(img, i) in pendingImages" :key="img.name" class="pending-img-wrap">
            <el-image :src="img.url" fit="cover" class="pending-img" />
            <span class="pending-remove" @click="removeImage(i)">×</span>
          </div>
        </div>
        <el-input
          v-model="input"
          type="textarea"
          :rows="3"
          resize="none"
          placeholder="输入消息，Enter 发送，Shift+Enter 换行；支持粘贴截图提问"
          @keydown.enter.exact.prevent="send"
          @paste="onPaste"
        />
        <div class="input-actions">
          <span class="input-tip">
            <el-tooltip
              :content="selectedKbIds.length ? 'RAG 模式暂不支持图片' : '支持粘贴截图（Ctrl+V）或选择图片，最多 3 张'"
              placement="top"
            >
              <el-button
                :disabled="selectedKbIds.length > 0 || pendingImages.length >= 3 || streaming"
                @click="pickImage"
              >
                🖼 图片
              </el-button>
            </el-tooltip>
            <input
              ref="fileInputRef"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              multiple
              style="display: none"
              @change="onPickFiles"
            />
          </span>
          <el-button
            v-if="!streaming"
            type="primary"
            :disabled="!input.trim() && !pendingImages.length"
            @click="send"
          >
            发送
          </el-button>
          <el-button v-else type="danger" @click="stop">停止</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { renderMarkdown } from '../utils/markdown'
import { sendChatMessage, type Source, type ToolEvent } from '../api/chat'
import { loadChatImageUrl, uploadChatImage } from '../api/chatImages'
import {
  deleteConversation,
  getMessages,
  listConversations,
  renameConversation,
  type Conversation,
  type Message,
} from '../api/conversation'
import { listKnowledgeBases, type KnowledgeBase } from '../api/knowledgeBase'

const MAX_IMAGES = 3
const MAX_IMAGE_SIZE = 10 * 1024 * 1024 // 原始图 10MB 上限（压缩后通常远小于 5MB）
const MAX_EDGE = 1280 // 压缩后最长边

interface PendingImage {
  name: string // 服务端存储文件名（上传成功后）
  url: string // 本地 blob URL（预览用）
}

const conversations = ref<Conversation[]>([])
const messages = ref<Message[]>([])
const activeId = ref<number | null>(null)
const input = ref('')
const streaming = ref(false)
const streamText = ref('')
const messageListRef = ref<HTMLElement | null>(null)
const kbs = ref<KnowledgeBase[]>([])
const selectedKbIds = ref<number[]>([])
const currentSources = ref<Source[]>([])
const toolNotice = ref('')
const pendingImages = ref<PendingImage[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)
let abortController: AbortController | null = null

onMounted(() => {
  loadConversations()
  loadKbs()
})

async function loadConversations() {
  try {
    conversations.value = await listConversations()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function loadKbs() {
  try {
    kbs.value = await listKnowledgeBases()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function selectConversation(c: Conversation) {
  activeId.value = c.id
  try {
    messages.value = await getMessages(c.id)
    loadHistoryImages()
    scrollToBottom()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

/** 历史消息图片鉴权加载（<img> 带不了 Authorization，用 fetch 换 blob URL） */
async function loadHistoryImages() {
  for (const m of messages.value) {
    if (m.role !== 'user' || !m.images?.length) continue
    const urls: string[] = []
    for (const name of m.images) {
      try {
        urls.push(await loadChatImageUrl(name))
      } catch {
        urls.push('')
      }
    }
    m._imageUrls = urls
  }
}

function startNewChat() {
  activeId.value = null
  messages.value = []
  streamText.value = ''
  currentSources.value = []
  pendingImages.value = []
}

/** Ctrl+V 粘贴截图 */
function onPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items || streaming.value) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        e.preventDefault()
        addImage(file)
      }
      break
    }
  }
}

function pickImage() {
  fileInputRef.value?.click()
}

function onPickFiles(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (!files) return
  for (const file of Array.from(files)) {
    addImage(file)
  }
  ;(e.target as HTMLInputElement).value = ''
}

/** 压缩（最长边 ≤1280，JPEG 0.8）后上传，成功后加入待发列表 */
async function addImage(file: File) {
  if (pendingImages.value.length >= MAX_IMAGES) {
    ElMessage.warning(`最多支持 ${MAX_IMAGES} 张图片`)
    return
  }
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('仅支持图片文件')
    return
  }
  if (file.size > MAX_IMAGE_SIZE) {
    ElMessage.warning('图片超过 10MB，请压缩后再试')
    return
  }
  try {
    const compressed = await compressImage(file)
    const name = await uploadChatImage(compressed)
    pendingImages.value.push({ name, url: URL.createObjectURL(compressed) })
  } catch (err) {
    ElMessage.error((err as Error).message || '图片上传失败')
  }
}

function removeImage(index: number) {
  const [img] = pendingImages.value.splice(index, 1)
  if (img) URL.revokeObjectURL(img.url)
}

function compressImage(file: File): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      const scale = Math.min(1, MAX_EDGE / Math.max(img.width, img.height))
      const w = Math.max(1, Math.round(img.width * scale))
      const h = Math.max(1, Math.round(img.height * scale))
      const canvas = document.createElement('canvas')
      canvas.width = w
      canvas.height = h
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('浏览器不支持图片处理'))
        return
      }
      ctx.drawImage(img, 0, 0, w, h)
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error('图片压缩失败'))),
        'image/jpeg',
        0.8,
      )
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('图片读取失败'))
    }
    img.src = url
  })
}

async function send() {
  const content = input.value.trim()
  const imageNames = pendingImages.value.map((p) => p.name)
  if ((!content && !imageNames.length) || streaming.value) return
  if (imageNames.length && selectedKbIds.value.length) {
    ElMessage.warning('RAG 知识库问答暂不支持图片，请切换到普通对话')
    return
  }
  input.value = ''
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content,
    model: null,
    created_at: new Date().toISOString(),
    images: imageNames,
    _imageUrls: pendingImages.value.map((p) => p.url),
  })
  pendingImages.value = []
  streamText.value = ''
  currentSources.value = []
  toolNotice.value = ''
  streaming.value = true
  abortController = new AbortController()
  scrollToBottom()
  try {
    await sendChatMessage(
      {
        conversation_id: activeId.value,
        content,
        knowledge_base_ids: selectedKbIds.value.length ? selectedKbIds.value : null,
        images: imageNames.length ? imageNames : null,
      },
      (delta) => {
        streamText.value += delta
        scrollToBottom()
      },
      (sources) => {
        currentSources.value = sources
      },
      (tool: ToolEvent) => {
        const toolNameText: Record<string, string> = {
          create_task: '创建任务',
          list_tasks: '查询任务',
          update_task: '修改任务',
          delete_task: '删除任务',
          search_knowledge: '检索知识库',
        }
        const label = toolNameText[tool.name] ?? tool.name
        if (tool.status === 'running') {
          toolNotice.value = `正在${label}…`
        } else if (tool.status === 'done') {
          toolNotice.value = `${label}完成`
        } else {
          toolNotice.value = `${label}失败：${tool.message ?? '未知错误'}`
        }
        scrollToBottom()
      },
      (event) => {
        if (typeof event.conversation_id === 'number') {
          activeId.value = event.conversation_id
        }
        toolNotice.value = ''
        if (streamText.value) {
          messages.value.push({
            id: (event.message_id as number) ?? Date.now(),
            role: 'assistant',
            content: streamText.value,
            model: null,
            created_at: new Date().toISOString(),
          })
        }
        streamText.value = ''
        streaming.value = false
        loadConversations()
      },
      (message) => {
        ElMessage.error(message)
        toolNotice.value = ''
        streaming.value = false
        streamText.value = ''
      },
      abortController.signal,
    )
  } catch (e) {
    if ((e as Error).name !== 'AbortError') {
      ElMessage.error((e as Error).message)
    }
    streaming.value = false
  }
}

function stop() {
  abortController?.abort()
}

function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

async function handleConvAction(cmd: string, c: Conversation) {
  if (cmd === 'rename') {
    try {
      const { value } = await ElMessageBox.prompt('请输入新标题', '重命名', {
        inputValue: c.title,
      })
      await renameConversation(c.id, value.trim() || c.title)
      ElMessage.success('已重命名')
      loadConversations()
    } catch {
      /* 用户取消 */
    }
  } else if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm('确定删除该会话？', '删除', { type: 'warning' })
      await deleteConversation(c.id)
      ElMessage.success('已删除')
      if (activeId.value === c.id) startNewChat()
      loadConversations()
    } catch {
      /* 用户取消 */
    }
  }
}
</script>

<style scoped>
.chat-page {
  display: flex;
  height: calc(100vh - 60px);
}
.sidebar {
  width: 260px;
  border-right: 1px solid #eee;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.conv-list {
  flex: 1;
  overflow-y: auto;
}
.conv-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
}
.conv-item:hover {
  background: #f5f7fa;
}
.conv-item.active {
  background: #ecf5ff;
}
.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.conv-menu {
  cursor: pointer;
  padding: 0 4px;
  color: #999;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.rag-bar {
  padding: 10px 20px 0;
}
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.msg-row {
  display: flex;
  margin-bottom: 14px;
}
.msg-row.user {
  justify-content: flex-end;
}
.msg-row.assistant {
  justify-content: flex-start;
}
.msg-bubble {
  max-width: 76%;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.6;
}
.msg-row.user .msg-bubble {
  background: #409eff;
  color: #fff;
}
.msg-row.assistant .msg-bubble {
  background: #f5f7fa;
  color: #333;
}
.md-body :deep(pre) {
  background: #f6f8fa;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}
.md-body :deep(code) {
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
}
.tool-notice {
  color: #909399;
  font-size: 13px;
  font-style: italic;
}
.sources-bar {
  border-top: 1px dashed #e0e0e0;
  padding: 10px 20px;
  max-height: 160px;
  overflow-y: auto;
  background: #fafafa;
}
.sources-title {
  font-size: 13px;
  font-weight: 600;
  color: #666;
  margin-bottom: 6px;
}
.source-item {
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
}
.source-index {
  color: #409eff;
  font-weight: 600;
}
.source-file {
  font-weight: 600;
  margin: 0 6px;
}
.source-page {
  color: #999;
  margin-right: 6px;
}
.source-sim {
  color: #67c23a;
}
.source-preview {
  color: #999;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.input-area {
  border-top: 1px solid #eee;
  padding: 12px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.pending-images {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.pending-img-wrap {
  position: relative;
  width: 64px;
  height: 64px;
}
.pending-img {
  width: 64px;
  height: 64px;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
}
.pending-remove {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 18px;
  height: 18px;
  line-height: 16px;
  text-align: center;
  background: #f56c6c;
  color: #fff;
  border-radius: 50%;
  cursor: pointer;
  font-size: 13px;
}
.input-tip {
  display: inline-flex;
  align-items: center;
}
.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.msg-images {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.msg-img {
  width: 120px;
  height: 120px;
  border-radius: 6px;
  cursor: pointer;
}
.msg-row.user .msg-img {
  border: 1px solid rgba(255, 255, 255, 0.5);
}
</style>
