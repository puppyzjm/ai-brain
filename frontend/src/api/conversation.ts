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
