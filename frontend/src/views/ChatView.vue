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
            <span class="conv-menu" @click.stop>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <circle cx="3" cy="8" r="1.7" />
              <circle cx="8" cy="8" r="1.7" />
              <circle cx="13" cy="8" r="1.7" />
            </svg>
          </span>
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
        <div class="message-inner" @click="onMessageClick">
          <div v-for="m in messages" :key="m.id" class="msg-row" :class="m.role">
            <el-avatar :size="34" class="msg-avatar" :class="m.role">
              <img v-if="m.role === 'user' && avatarUrl" :src="avatarUrl" alt="" />
              <img v-else-if="m.role === 'assistant'" :src="aiAvatar" alt="AI" />
              <span v-else>{{ user?.username?.[0] ?? '我' }}</span>
            </el-avatar>
            <div class="msg-content">
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
            <el-avatar :size="34" class="msg-avatar assistant">
              <img :src="aiAvatar" alt="AI" />
            </el-avatar>
            <div class="msg-content">
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
        <!-- 悬浮卡片式输入框 -->
        <div class="input-card" :class="{ focused: inputFocused }">
          <el-input
            v-model="input"
            type="textarea"
            :rows="2"
            resize="none"
            class="chat-textarea"
            placeholder="输入消息，Enter 发送，Shift+Enter 换行；支持粘贴截图"
            @focus="inputFocused = true"
            @blur="inputFocused = false"
            @keydown.enter.exact.prevent="send"
            @paste="onPaste"
          />
          <div class="input-card-bar">
            <el-tooltip
              :content="selectedKbIds.length ? 'RAG 模式暂不支持图片' : '支持粘贴截图（Ctrl+V）或选择图片，最多 3 张'"
              placement="top"
            >
              <span>
                <el-button
                  class="icon-btn"
                  :disabled="selectedKbIds.length > 0 || pendingImages.length >= 3 || streaming"
                  @click="pickImage"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="5" width="18" height="14" rx="2.5" />
                    <circle cx="8.5" cy="10" r="1.5" fill="currentColor" stroke="none" />
                    <path d="M5.5 17.5l4.5-4.5 3 3 3-3 3.5 3.5" />
                  </svg>
                </el-button>
              </span>
            </el-tooltip>
            <input
              ref="fileInputRef"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              multiple
              style="display: none"
              @change="onPickFiles"
            />
            <el-button
              v-if="!streaming"
              type="primary"
              circle
              class="send-btn"
              :disabled="!input.trim() && !pendingImages.length"
              @click="send"
            >
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 19V6M6 11.5l6-6 6 6" />
              </svg>
            </el-button>
            <el-button v-else type="danger" circle class="send-btn" @click="stop">
              <svg width="14" height="14" viewBox="0 0 24 24">
                <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
              </svg>
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { renderMarkdown } from '../utils/markdown'
import { sendChatMessage, type Source, type ToolEvent } from '../api/chat'
import { loadChatImageUrl, uploadChatImage } from '../api/chatImages'
import { loadAvatarUrl } from '../api/user'
import aiAvatar from '../assets/ai-avatar.png'
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

const authStore = useAuthStore()
const { user } = storeToRefs(authStore)
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
const inputFocused = ref(false)
const avatarUrl = ref('')
let abortController: AbortController | null = null

// 加载用户头像（消息气泡头像用）
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

/** 消息区点击委托：代码块复制按钮 */
function onMessageClick(e: MouseEvent) {
  const btn = (e.target as HTMLElement).closest('.copy-btn')
  if (!btn) return
  const code = btn.closest('.code-block')?.querySelector('code')?.textContent ?? ''
  if (!code) return
  copyToClipboard(code, btn as HTMLElement)
}

/** 复制文本：优先 Clipboard API（需 https/localhost），http 环境降级 execCommand */
async function copyToClipboard(text: string, btn: HTMLElement) {
  const markDone = () => {
    btn.textContent = '✓ 已复制'
    btn.classList.add('copied')
    setTimeout(() => {
      btn.textContent = '复制'
      btn.classList.remove('copied')
    }, 1500)
  }
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    markDone()
  } catch {
    ElMessage.error('复制失败，请手动选择复制')
  }
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
/* 视口锁定：继承 layout 的 main 高度，输入栏永远钉在底部 */
.chat-page {
  display: flex;
  height: 100%;
  min-height: 0;
}
.sidebar {
  width: 260px;
  border-right: 1px solid var(--el-border-color-light);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex-shrink: 0;
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
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
}
.conv-item:hover {
  background: var(--el-fill-color-light);
}
.conv-item.active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary-dark-2);
}
.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 15px;
}
.conv-menu {
  cursor: pointer;
  padding: 0 4px;
  color: var(--el-text-color-secondary);
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.rag-bar {
  padding: 10px 20px 0;
  flex-shrink: 0;
}
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  min-height: 0;
}
/* Cherry 式中央窄栏：消息列居中 */
.message-inner {
  max-width: 860px;
  margin: 0 auto;
}
.msg-row {
  display: flex;
  gap: 12px;
  margin-bottom: 22px;
  align-items: center;
}
.msg-row.user {
  flex-direction: row-reverse;
}
.msg-avatar {
  flex-shrink: 0;
  font-weight: 600;
  font-size: 15px;
}
.msg-avatar.user {
  background: var(--el-color-primary);
  color: #fff;
}
.msg-avatar.assistant {
  background: linear-gradient(135deg, var(--el-color-primary), var(--el-color-primary-light-3));
  color: #fff;
}
.msg-avatar :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.msg-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.msg-row.user .msg-content {
  align-items: flex-end;
}
.plain-body {
  line-height: 1.7;
  font-size: 15.5px;
  color: var(--el-text-color-primary);
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-row.user .plain-body {
  text-align: right;
}
.md-body {
  line-height: 1.75;
  color: var(--el-text-color-primary);
  word-break: break-word;
}
.md-body :deep(pre) {
  background: var(--el-fill-color-lighter);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
}
/* 代码块复制按钮（悬停显示，右上角） */
.md-body :deep(.code-block) {
  position: relative;
}
.md-body :deep(.code-block .copy-btn) {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  font-size: 12.5px;
  line-height: 1;
  padding: 5px 10px;
  border-radius: 6px;
  border: 1px solid var(--el-border-color);
  background: var(--el-bg-color-overlay);
  color: var(--el-text-color-secondary);
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s;
  font-family: var(--aibrain-font);
}
.md-body :deep(.code-block:hover .copy-btn),
.md-body :deep(.code-block .copy-btn.copied) {
  opacity: 1;
}
.md-body :deep(.code-block .copy-btn:hover) {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary);
}
.md-body :deep(.code-block .copy-btn.copied) {
  color: #67c23a;
  border-color: #67c23a;
}
.md-body :deep(code) {
  font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, Monaco, monospace;
  font-size: 14.5px;
}
.tool-notice {
  color: var(--el-text-color-secondary);
  font-size: 14.5px;
  font-style: italic;
}
.sources-bar {
  border-top: 1px dashed var(--el-border-color);
  padding: 10px 20px;
  max-height: 180px;
  overflow-y: auto;
  background: var(--el-fill-color-lighter);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.sources-bar > * {
  width: 100%;
  max-width: 860px;
}
.sources-title {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 6px;
}
.source-item {
  font-size: 13.5px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}
.source-index {
  color: var(--el-color-primary);
  font-weight: 600;
}
.source-file {
  font-weight: 600;
  color: var(--el-text-color-regular);
  margin: 0 6px;
}
.source-page {
  color: var(--el-text-color-secondary);
  margin-right: 6px;
}
.source-sim {
  color: #67c23a;
}
.source-preview {
  color: var(--el-text-color-secondary);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.input-area {
  border-top: 1px solid var(--el-border-color-light);
  padding: 12px 20px 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  background: var(--el-bg-color);
}
/* Cherry 式中央窄栏：输入框与图片预览居中 */
.input-area > * {
  width: 100%;
  max-width: 860px;
}
/* 悬浮卡片式输入框 */
.input-card {
  border: 1px solid var(--el-border-color);
  border-radius: 16px;
  background: var(--el-fill-color-light);
  padding: 6px 8px 6px 12px;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}
.input-card.focused {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 3px var(--el-color-primary-light-8);
}
.chat-textarea :deep(.el-textarea__inner) {
  border: none;
  box-shadow: none !important;
  background: transparent;
  padding: 6px 2px;
  font-size: 16px;
  line-height: 1.6;
}
.input-card-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 2px;
}
.icon-btn {
  border: none;
  background: transparent;
  color: var(--el-text-color-secondary);
  padding: 6px 8px;
  border-radius: 8px;
}
.icon-btn:hover:not(:disabled) {
  color: var(--el-color-primary);
  background: var(--el-fill-color);
}
.icon-btn:disabled {
  opacity: 0.45;
}
.send-btn {
  width: 38px;
  height: 38px;
}
.pending-images {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.pending-img-wrap {
  position: relative;
  width: 68px;
  height: 68px;
}
.pending-img {
  width: 68px;
  height: 68px;
  border-radius: 8px;
  border: 1px solid var(--el-border-color);
}
.pending-remove {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 19px;
  height: 19px;
  line-height: 17px;
  text-align: center;
  background: #f56c6c;
  color: #fff;
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
}
.msg-images {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.msg-img {
  width: 130px;
  height: 130px;
  border-radius: 8px;
  cursor: pointer;
}
.msg-row.user .msg-img {
  border: 1px solid rgba(255, 255, 255, 0.5);
}
</style>
