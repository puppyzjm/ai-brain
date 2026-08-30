import client from './client'

export interface Conversation {
  id: number
  title: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  role: string
  content: string
  model: string | null
  created_at: string
  /** 多模态：用户消息携带的聊天图片文件名列表 */
  images?: string[] | null
  /** 前端本地字段：图片 blob URL（历史加载时填充，非后端返回） */
  _imageUrls?: string[]
}

export async function listConversations(): Promise<Conversation[]> {
  return (await client.get('/conversations')) as unknown as Promise<Conversation[]>
}

export async function createConversation(title?: string): Promise<Conversation> {
  return (await client.post('/conversations', { title })) as unknown as Promise<Conversation>
}

export async function renameConversation(id: number, title: string): Promise<Conversation> {
  return (await client.patch(`/conversations/${id}`, { title })) as unknown as Promise<Conversation>
}

export async function deleteConversation(id: number): Promise<void> {
  await client.delete(`/conversations/${id}`)
}

export async function getMessages(id: number): Promise<Message[]> {
  return (await client.get(`/conversations/${id}/messages`)) as unknown as Promise<Message[]>
}
