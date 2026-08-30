import client, { getAccessToken } from './client'

export async function uploadChatImage(blob: Blob): Promise<string> {
  const form = new FormData()
  form.append('file', blob, 'image.jpg')
  const data = await client.post('/chat-images', form)
  return (data as { name: string }).name
}

/** 历史图片鉴权加载：fetch + blob URL（<img> 无法携带 Authorization 头） */
export async function loadChatImageUrl(name: string): Promise<string> {
  const token = getAccessToken()
  const resp = await fetch(`/api/v1/chat-images/${name}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!resp.ok) throw new Error('图片加载失败')
  return URL.createObjectURL(await resp.blob())
}
