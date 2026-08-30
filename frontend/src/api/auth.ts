import client from './client'
import type { User } from './user'

export interface RegisterPayload {
  username: string
  email?: string
  password: string
}

export interface LoginPayload {
  account: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export async function register(payload: RegisterPayload): Promise<User> {
  return (await client.post('/auth/register', payload)) as unknown as Promise<User>
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  return (await client.post('/auth/login', payload)) as unknown as Promise<TokenResponse>
}

export async function logout(): Promise<void> {
  const refresh = localStorage.getItem('refresh_token')
  if (refresh) {
    await client.post('/auth/logout', { refresh_token: refresh })
  }
}
