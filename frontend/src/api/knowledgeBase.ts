import client from './client'

export interface KnowledgeBase {
  id: number
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface Document {
  id: number
  knowledge_base_id: number
  filename: string
  file_type: string
  file_size: number
  status: string
  error_message: string | null
  chunk_count: number
  created_at: string
  updated_at: string
}

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  return (await client.get('/knowledge-bases')) as unknown as Promise<KnowledgeBase[]>
}

export async function createKnowledgeBase(
  name: string,
  description?: string,
): Promise<KnowledgeBase> {
  return (await client.post('/knowledge-bases', { name, description })) as unknown as Promise<KnowledgeBase>
}

export async function updateKnowledgeBase(
  id: number,
  name: string,
  description?: string,
): Promise<KnowledgeBase> {
  return (await client.patch(`/knowledge-bases/${id}`, { name, description })) as unknown as Promise<KnowledgeBase>
}

export async function deleteKnowledgeBase(id: number): Promise<void> {
  await client.delete(`/knowledge-bases/${id}`)
}

export async function listDocuments(kbId: number): Promise<Document[]> {
  return (await client.get(`/knowledge-bases/${kbId}/documents`)) as unknown as Promise<Document[]>
}

export async function uploadDocument(kbId: number, file: File): Promise<Document> {
  const form = new FormData()
  form.append('file', file)
  return (await client.post(`/knowledge-bases/${kbId}/documents`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })) as unknown as Promise<Document>
}

export async function deleteDocument(documentId: number): Promise<void> {
  await client.delete(`/documents/${documentId}`)
}

export async function reprocessDocument(documentId: number): Promise<Document> {
  return (await client.post(`/documents/${documentId}/reprocess`)) as unknown as Promise<Document>
}

export interface SummarizeResult {
  document_id: number
  summary: string
}

export async function summarizeDocument(documentId: number): Promise<SummarizeResult> {
  return (await client.post(`/documents/${documentId}/summarize`)) as unknown as Promise<SummarizeResult>
}
