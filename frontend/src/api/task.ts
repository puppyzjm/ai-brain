import client from './client'

export type TaskStatus = 'todo' | 'in_progress' | 'done'
export type TaskPriority = 'high' | 'medium' | 'low'

export interface Task {
  id: number
  title: string
  description: string | null
  status: TaskStatus
  priority: TaskPriority
  due_date: string | null
  created_at: string
  updated_at: string
}

export interface TaskPayload {
  title: string
  description?: string
  status?: TaskStatus
  priority?: TaskPriority
  due_date?: string
}

export async function listTasks(params?: {
  status?: TaskStatus
  priority?: TaskPriority
}): Promise<Task[]> {
  return (await client.get('/tasks', { params })) as unknown as Promise<Task[]>
}

export async function createTask(payload: TaskPayload): Promise<Task> {
  return (await client.post('/tasks', payload)) as unknown as Promise<Task>
}

export async function updateTask(id: number, payload: Partial<TaskPayload>): Promise<Task> {
  return (await client.patch(`/tasks/${id}`, payload)) as unknown as Promise<Task>
}

export async function deleteTask(id: number): Promise<void> {
  await client.delete(`/tasks/${id}`)
}
