import { streamSSE, type SSEEvent } from '../utils/sse'

export interface ChatRequest {
  conversation_id?: number | null
  content: string
  knowledge_base_ids?: number[] | null
  /** 多模态：聊天图片文件名列表（先经 /chat-images 上传） */
  images?: string[] | null
}

export interface Source {
  chunk_id: number
  document_id: number
  filename: string
  content_preview: string
  similarity: number
  page?: number | null
}

export interface ToolEvent {
  name: string
  status: 'running' | 'done' | 'failed'
  message?: string
}

export function sendChatMessage(
  payload: ChatRequest,
  onDelta: (text: string) => void,
  onSources: (sources: Source[]) => void,
  onTool: (event: ToolEvent) => void,
  onDone: (event: SSEEvent) => void,
  onError: (message: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  return streamSSE(
    '/api/v1/chat',
    payload,
    (event) => {
      if (event.type === 'delta' && typeof event.content === 'string') {
        onDelta(event.content)
      } else if (event.type === 'sources') {
        onSources((event.sources as Source[]) ?? [])
      } else if (event.type === 'tool') {
        onTool({
          name: String(event.name ?? 'tool'),
          status: (event.status as ToolEvent['status']) ?? 'running',
          message: typeof event.message === 'string' ? event.message : undefined,
        })
      } else if (event.type === 'done') {
        onDone(event)
      } else if (event.type === 'error') {
        onError(typeof event.message === 'string' ? event.message : 'AI 服务错误')
      }
    },
    signal,
  )
}
