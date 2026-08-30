import client, { getAccessToken } from './client'

export interface User {
  id: number
  username: string
  email: string | null
  role: string
  avatar: string | null
  created_at: string
}

export async function fetchMe(): Promise<User> {
  return (await client.get('/users/me')) as unknown as Promise<User>
}

export async function uploadAvatar(blob: Blob): Promise<string> {
  const form = new FormData()
  form.append('file', blob, 'avatar.jpg')
  const data = await client.post('/users/avatar', form)
  return (data as { avatar: string }).avatar
}

export async function deleteAvatar(): Promise<void> {
  await client.delete('/users/avatar')
}

/** 头像鉴权加载：fetch + blob URL（<img> 无法携带 Authorization 头） */
export async function loadAvatarUrl(name: string): Promise<string> {
  const token = getAccessToken()
  const resp = await fetch(`/api/v1/users/avatar/${name}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!resp.ok) throw new Error('头像加载失败')
  return URL.createObjectURL(await resp.blob())
}
