/** 使用 fetch 消费 SSE 流（支持 POST + Authorization header + 中断）。 */
export interface SSEEvent {
  type: string
  content?: string
  [key: string]: unknown
}

export async function streamSSE(
  url: string,
  body: unknown,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = localStorage.getItem('token')
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok || !response.body) {
    let message = `请求失败 (${response.status})`
    try {
      const data = await response.json()
      message = (data.message as string) || message
    } catch {
      /* 非 JSON 响应，使用默认信息 */
    }
    throw new Error(message)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''
    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue
      const payload = line.slice(5).trim()
      if (!payload) continue
      try {
        const event = JSON.parse(payload) as SSEEvent
        onEvent(event)
      } catch {
        /* 忽略无法解析的行 */
      }
    }
  }
}
