import client from './client'

export interface User {
  id: number
  username: string
  email: string | null
  role: string
  created_at: string
}

export async function fetchMe(): Promise<User> {
  return (await client.get('/users/me')) as unknown as Promise<User>
}
