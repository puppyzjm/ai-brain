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
        <el-input
          v-model="input"
          type="textarea"
          :rows="3"
          resize="none"
          placeholder="输入消息，Enter 发送，Shift+Enter 换行"
          @keydown.enter.exact.prevent="send"
        />
        <div class="input-actions">
          <el-button
            v-if="!streaming"
            type="primary"
            :disabled="!input.trim()"
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
import {
  deleteConversation,
  getMessages,
  listConversations,
  renameConversation,
  type Conversation,
  type Message,
} from '../api/conversation'
import { listKnowledgeBases, type KnowledgeBase } from '../api/knowledgeBase'

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
    scrollToBottom()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

function startNewChat() {
  activeId.value = null
  messages.value = []
  streamText.value = ''
  currentSources.value = []
}

async function send() {
  const content = input.value.trim()
  if (!content || streaming.value) return
  input.value = ''
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content,
    model: null,
    created_at: new Date().toISOString(),
  })
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
.input-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
